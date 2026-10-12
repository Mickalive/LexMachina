"""End-to-end retrieval pipeline: question -> normalised candidate bundle.

Stage order (each bounded, each individually fault-isolated):

1. ``search``    relevance search over ``/decisions`` for the original and
                 lexicon-expanded query variants, paging with ``offset``
2. ``lang``      server-side ``language=de|fr|it`` filtered search passes
3. ``leading``   ``/leading-cases`` landmark candidates
4. ``citations`` bounded incoming/outgoing ``/citations`` neighbourhood

Then: deterministic dedupe -> optional lazy hydration -> bundle assembly.

A stage failure never aborts the bundle: it is recorded in
``provenance.failures`` and the bundle is marked ``degraded`` (acceptance 8).
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .bundle import build_candidate_bundle as assemble_bundle, rank_candidates
from .cache import FileCache
from .client import OCLClient
from .config import AdapterConfig
from .dedupe import dedupe, identity_key
from .errors import (
    OCLBudgetExceeded,
    OCLDecodeError,
    OCLError,
    OCLHTTPError,
    OCLTransportError,
)
from .expansion import build_variants, language_variants, search_variants
from .normalize import (
    CHANNEL_CITE_IN,
    CHANNEL_CITE_OUT,
    CHANNEL_LEADING,
    CHANNEL_LANG,
    CHANNEL_SEARCH,
    normalize_citation,
    normalize_decision_detail,
    normalize_leading_case,
    normalize_search_hit,
    structure_summary,
)
from .ratelimit import RateLimiter, RequestBudget
from .transport import CachedTransport, HttpTransport, Transport

DEFAULT_STAGES = ("search", "lang", "leading", "citations")


def _cache_stats(client: OCLClient) -> dict:
    """Best-effort cache statistics from whatever transport is installed."""
    transport = getattr(client, "transport", None)
    cache = getattr(transport, "cache", None)
    if cache is None:
        return {"available": False}
    try:
        stats = cache.stats()
    except Exception:
        return {"available": False}
    stats["available"] = True
    return stats


def make_transport(config: AdapterConfig, cache: Optional[FileCache] = None) -> CachedTransport:
    """Build the mode-aware transport stack for ``config``."""
    cache = cache or FileCache(config.cache_path())
    inner = HttpTransport(
        config.base_url,
        user_agent=config.user_agent,
        timeout=config.timeout,
        retries=config.retries,
        backoff_seconds=config.backoff_seconds,
        limiter=RateLimiter(config.max_rps),
    )
    return CachedTransport(inner, cache, mode=config.mode, ttl_seconds=config.cache_ttl_seconds)


def _safe_call(client: OCLClient, stage: str, fn, failures: List[dict]) -> Optional[Any]:
    before = len(client.failures)
    try:
        return fn()
    except OCLBudgetExceeded as exc:
        failures.append({"stage": stage, "error": str(exc), "kind": "budget"})
        return None
    except OCLError as exc:
        # client._call already appended a structured record for transport/HTTP
        # errors; only add a stage-level record when it did not.
        if len(client.failures) == before:
            failures.append({"stage": stage, "error": str(exc), "kind": type(exc).__name__})
        return None
    except Exception as exc:  # defensive: never let one stage kill the bundle
        failures.append({"stage": stage, "error": f"{type(exc).__name__}: {exc}", "kind": "unexpected"})
        return None


def _page_loop(
    client: OCLClient,
    *,
    stage: str,
    variant,
    query: str,
    channel: str,
    config: AdapterConfig,
    records: List[dict],
    search_log: List[dict],
    failures: List[dict],
    unique_count,
    max_pages: Optional[int] = None,
) -> int:
    """Page one variant until exhausted / capped. Returns unique count."""
    max_pages = config.max_pages_per_variant if max_pages is None else max_pages
    offset = 0
    page = 0
    language = getattr(variant, "language_filter", None)
    while page < max_pages:
        if client.budget.exhausted:
            failures.append({"stage": stage, "error": "request budget exhausted", "kind": "budget"})
            break
        payload = _safe_call(
            client,
            stage,
            lambda: client.search_page(
                query=variant.text,
                language=language,
                limit=config.page_size,
                offset=offset,
                stage=stage,
            ),
            failures,
        )
        if payload is None:
            break
        results = payload.get("results", [])
        entry = {
            "stage": stage,
            "variant_id": variant.variant_id,
            "kind": variant.kind,
            "language_filter": language,
            "page": page,
            "offset": offset,
            "limit": config.page_size,
            "total": payload.get("total"),
            "total_is_lower_bound": payload.get("total_is_lower_bound"),
            "returned": payload.get("returned", len(results)),
            "has_more": payload.get("has_more"),
            "next_offset": payload.get("next_offset"),
            "result_set_id": payload.get("result_set_id"),
            "remote_degraded": bool(payload.get("degraded")),
            "note": payload.get("note"),
        }
        search_log.append(entry)
        ch = CHANNEL_LANG if language else channel
        for raw in results:
            rec = normalize_search_hit(
                raw,
                channel=ch,
                query=query,
                variant_id=variant.variant_id,
                page=page,
                offset=offset,
                language_filter=language,
            )
            if rec:
                records.append(rec)
        if not results:
            break
        n = unique_count(records)
        if n >= config.max_candidates:
            break
        if config.stop_when_target_met and n >= config.target:
            break
        if not payload.get("has_more"):
            break
        nxt = payload.get("next_offset")
        if nxt is None or int(nxt) <= offset:
            break
        offset = int(nxt)
        page += 1
    return unique_count(records)


def build_candidate_bundle(
    query: str,
    *,
    config: Optional[AdapterConfig] = None,
    transport: Optional[Transport] = None,
    client: Optional[OCLClient] = None,
    cache: Optional[FileCache] = None,
    hydrate_ids: Optional[Sequence[str]] = None,
    hydrate_top: int = 0,
    include_structure: bool = True,
    stages: Optional[Sequence[str]] = None,
    clock=time.time,
) -> dict:
    """Run the full retrieval pipeline and return a candidate bundle dict."""
    t0 = clock()
    cfg = config or AdapterConfig()
    if stages is not None:
        cfg = cfg.replace(stages=tuple(stages))

    if client is None:
        tr = transport if transport is not None else make_transport(cfg, cache)
        client = OCLClient(
            tr,
            cfg,
            limiter=RateLimiter(cfg.max_rps),
            budget=RequestBudget(cfg.max_requests),
            clock=clock,
        )

    variants = build_variants(
        query,
        cfg.language_filters,
        max_terms=cfg.max_expansion_terms,
        include_language_filters="lang" in cfg.stages,
    )

    records: List[dict] = []
    search_log: List[dict] = []
    stage_notes: Dict[str, Any] = {}
    failures: List[dict] = []

    def unique_count(recs: Iterable[dict]) -> int:
        return len(dedupe(recs).candidates)

    def budget_left() -> bool:
        return not client.budget.exhausted

    # ---- stage: search -------------------------------------------------
    if "search" in cfg.stages:
        for variant in search_variants(variants):
            if not budget_left() or unique_count(records) >= cfg.max_candidates:
                break
            before = len(client.failures)
            _page_loop(
                client,
                stage="search",
                variant=variant,
                query=query,
                channel=CHANNEL_SEARCH,
                config=cfg,
                records=records,
                search_log=search_log,
                failures=failures,
                unique_count=unique_count,
            )
            if len(client.failures) > before:
                continue

    target_met = unique_count(records) >= cfg.target
    stop = cfg.stop_when_target_met and target_met

    # ---- stage: lang ---------------------------------------------------
    if "lang" in cfg.stages and not stop and budget_left() and unique_count(records) < cfg.max_candidates:
        for variant in language_variants(variants):
            if not budget_left() or unique_count(records) >= cfg.max_candidates:
                break
            _page_loop(
                client,
                stage="lang",
                variant=variant,
                query=query,
                channel=CHANNEL_LANG,
                config=cfg,
                records=records,
                search_log=search_log,
                failures=failures,
                unique_count=unique_count,
                max_pages=cfg.lang_max_pages,
            )
        stage_notes["lang"] = {
            "language_filters": list(cfg.language_filters),
            "note": "server-side language filter, no translation performed",
        }

    target_met = unique_count(records) >= cfg.target
    stop = cfg.stop_when_target_met and target_met

    # ---- stage: leading -------------------------------------------------
    if "leading" in cfg.stages and cfg.leading_cases and not stop and budget_left() \
            and unique_count(records) < cfg.max_candidates:
        payload = _safe_call(
            client,
            "leading",
            lambda: client.get_leading_cases(query=query, limit=cfg.leading_cases_limit),
            failures,
        )
        added = 0
        if payload is not None:
            for raw in payload.get("results", []) or []:
                if unique_count(records) >= cfg.max_candidates:
                    break
                rec = normalize_leading_case(raw, query=query, variant_id="leading-cases")
                if rec:
                    records.append(rec)
                    added += 1
        stage_notes["leading"] = {
            "endpoint": "/leading-cases",
            "requested_limit": cfg.leading_cases_limit,
            "received": added,
            "total": (payload or {}).get("total"),
        }

    target_met = unique_count(records) >= cfg.target
    stop = cfg.stop_when_target_met and target_met

    # ---- stage: citations -----------------------------------------------
    if "citations" in cfg.stages and cfg.citation_expansion and not stop and budget_left() \
            and unique_count(records) < cfg.max_candidates:
        stage_notes["citations"] = _citation_stage(
            client=client,
            query=query,
            config=cfg,
            records=records,
            failures=failures,
            unique_count=unique_count,
        )

    # ---- dedupe ---------------------------------------------------------
    dd = dedupe(records)
    candidates = dd.candidates

    # ---- enforce the documented hard candidate cap ------------------
    # The page loops check the cap *before* fetching, so one final
    # page can overshoot max_candidates by up to page_size records.
    # Trim to the highest-ranked candidates so the documented "hard
    # cap" holds exactly and deterministically (relevance first,
    # then score, then decision_id -- the same order the bundle
    # assembles). Pre-trim count is preserved in provenance.
    pre_trim_candidates = len(candidates)
    if pre_trim_candidates > cfg.max_candidates:
        candidates = rank_candidates(candidates)[: max(0, cfg.max_candidates)]

    # ---- optional lazy hydration ---------------------------------------
    lazy = {"full_text": "lazy", "structure": "lazy", "hydrated": [], "requested": []}
    todo: List[str] = []
    if hydrate_ids:
        todo.extend(str(x) for x in hydrate_ids)
    if hydrate_top:
        todo.extend(c.get("decision_id") for c in candidates[: max(0, int(hydrate_top))])
    if cfg.hydrate_needs_detail:
        flagged = [c.get("decision_id") for c in candidates if c.get("needs_detail")]
        todo.extend(flagged[: max(0, int(cfg.hydrate_needs_detail))])
    if todo:
        lazy["requested"] = todo
        _hydrate(
            client=client,
            candidates=candidates,
            ids=todo,
            include_structure=include_structure,
            failures=failures,
            lazy=lazy,
        )

    # ---- assemble -------------------------------------------------------
    prov = {
        "adapter": "ocl_adapter",
        "adapter_version": "1.0",
        "charter_version": 2,
        "team_id": "frontier-query-retrieval",
        "base_url": cfg.base_url,
        "mode": cfg.mode,
        "stages": list(cfg.stages),
        "query_variants": [v.to_dict() for v in variants],
        "expansion": {
            "lexicon_provenance": "accepted/product/product/query/retrieval.py#EXPANSION",
            "terms_added": sorted({t for v in variants for t in v.terms_added}),
            "machine_translation_used": False,
        },
        "searches": search_log,
        "stage_notes": stage_notes,
        "failures": failures + client.failures,
        "degraded": bool(failures or client.failures),
        "rate_limit": {
            "max_rps": cfg.max_rps,
            "min_interval_seconds": round(1.0 / cfg.max_rps, 4),
            "charter_max_rps": 5.0,
        },
        "request_summary": client.summary(),
        "cache_stats": _cache_stats(client),
        "targets": {
            "target": cfg.target,
            "max_candidates": cfg.max_candidates,
            "page_size": cfg.page_size,
            "max_pages_per_variant": cfg.max_pages_per_variant,
            "max_requests": cfg.max_requests,
            "target_reached": unique_count(records) >= cfg.target,
            "pre_trim_candidates": pre_trim_candidates,
            "trimmed_to_max_candidates": pre_trim_candidates > cfg.max_candidates,
        },
        "latency_seconds": round(clock() - t0, 3),
    }
    if prov["cache_stats"] is None:
        prov["cache_stats"] = {}

    bundle = assemble_bundle(
        query=query,
        query_variants=[v.to_dict() for v in variants],
        candidates=candidates,
        dedupe_stats=dd.stats,
        provenance=prov,
        lazy=lazy,
        generated_at=clock(),
        config_snapshot=cfg.to_dict(),
    )
    return bundle


def _citation_stage(
    *,
    client: OCLClient,
    query: str,
    config: AdapterConfig,
    records: List[dict],
    failures: List[dict],
    unique_count,
) -> dict:
    seen = set()
    for r in records:
        k = identity_key(r).split(":", 1)[-1]
        seen.add(k)
        if r.get("decision_id"):
            seen.add(r["decision_id"])
        if r.get("canonical_decision_id"):
            seen.add(r["canonical_decision_id"])

    # Seed selection is deterministic and duplicate-free. Prefer relevance
    # hits first, then the most-cited retrieved decisions (they are the ones
    # that actually have an incoming citation neighbourhood).
    def _relevance_key(r):
        return (-(r.get("score") or 0.0), str(r.get("decision_id")))

    def _cite_key(r):
        return (-(r.get("citation_count") or 0), str(r.get("decision_id")))

    relevance_pool = [r for r in records if r.get("score_kind") == "relevance"]
    cited_pool = [r for r in records if r.get("citation_count")]
    seeds: List[dict] = []
    seen_ids = set()
    for pool in (sorted(relevance_pool, key=_relevance_key), sorted(cited_pool, key=_cite_key)):
        for r in pool:
            did = r.get("decision_id")
            if not did or did in seen_ids:
                continue
            seen_ids.add(did)
            seeds.append(r)
            if len(seeds) >= max(0, config.citation_seeds):
                break
        if len(seeds) >= max(0, config.citation_seeds):
            break
    added_in = added_out = 0
    seed_reports = []
    for seed in seeds:
        if client.budget.exhausted:
            failures.append({"stage": "citations", "error": "request budget exhausted", "kind": "budget"})
            break
        if added_in + added_out >= config.max_new_from_citations:
            break
        if unique_count(records) >= config.max_candidates:
            break
        seed_id = seed["decision_id"]
        payload = _safe_call(
            client,
            "citations",
            lambda sid=seed_id: client.get_citations(
                sid,
                direction="both",
                limit=config.citation_page_size,
                min_confidence=config.citation_min_confidence,
            ),
            failures,
        )
        if payload is None:
            seed_reports.append({"seed": seed_id, "status": "failed"})
            continue
        n_in = n_out = 0
        for raw in payload.get("incoming", []) or []:
            if added_in + added_out >= config.max_new_from_citations or unique_count(records) >= config.max_candidates:
                break
            rec = normalize_citation(raw, direction="incoming", seed_id=seed_id, query=query)
            if rec and rec["decision_id"] not in seen:
                records.append(rec)
                seen.add(rec["decision_id"])
                added_in += 1
                n_in += 1
        for raw in payload.get("outgoing", []) or []:
            if added_in + added_out >= config.max_new_from_citations or unique_count(records) >= config.max_candidates:
                break
            rec = normalize_citation(raw, direction="outgoing", seed_id=seed_id, query=query)
            if rec and rec["decision_id"] not in seen:
                records.append(rec)
                seen.add(rec["decision_id"])
                added_out += 1
                n_out += 1
        seed_reports.append(
            {
                "seed": seed_id,
                "status": "ok",
                "incoming_total": payload.get("incoming_total"),
                "outgoing_total": payload.get("outgoing_total"),
                "added_incoming": n_in,
                "added_outgoing": n_out,
            }
        )
    return {
        "endpoint": "/citations",
        "seeds_requested": config.citation_seeds,
        "seeds_used": len([s for s in seed_reports if s.get("status") == "ok"]),
        "min_confidence": config.citation_min_confidence,
        "page_size": config.citation_page_size,
        "max_new_from_citations": config.max_new_from_citations,
        "added_incoming": added_in,
        "added_outgoing": added_out,
        "per_seed": seed_reports,
    }


def _hydrate(
    *,
    client: OCLClient,
    candidates: List[dict],
    ids: Sequence[str],
    include_structure: bool,
    failures: List[dict],
    lazy: dict,
) -> None:
    """Lazily fetch full decision text / structure for selected candidates."""
    by_id = {c.get("decision_id"): c for c in candidates}
    canonical_of = {c.get("canonical_decision_id"): c for c in candidates if c.get("canonical_decision_id")}
    hydrated = []
    for cid in dict.fromkeys(ids):  # deterministic, de-duplicated
        rec = by_id.get(cid) or canonical_of.get(cid)
        if rec is None:
            lazy.setdefault("unknown_ids", []).append(cid)
            continue
        did = rec["decision_id"]
        try:
            detail = client.get_decision(did, full_text=True)
        except OCLError as exc:
            if isinstance(exc, OCLHTTPError) and exc.status == 404:
                rec["detail_status"] = "not_found"
                rec["full_text_status"] = "unavailable"
                lazy.setdefault("not_found", []).append(did)
            else:
                failures.append({"stage": "hydrate", "decision_id": did, "error": str(exc)})
            continue
        norm = normalize_decision_detail(detail, channel=rec.get("channel", "decision_lookup"))
        if norm:
            text = norm.get("full_text")
            if text:
                rec["full_text"] = text
                rec["full_text_status"] = "fetched"
            rec["detail_status"] = "hydrated"
            for key in ("source_url", "pdf_url", "regeste", "title", "citation",
                        "citation_string_de", "citation_string_fr", "citation_string_it",
                        "statutes", "legal_area", "court_name", "court_level"):
                if not rec.get(key) and norm.get(key):
                    rec[key] = norm[key]
            rec.setdefault("provenance_events", []).append(
                {"channel": "decision_lookup", "endpoint": "/decisions/{id}", "decision_id": did}
            )
        if include_structure:
            try:
                struct = client.get_structure(did)
            except OCLError as exc:
                if isinstance(exc, OCLHTTPError) and exc.status == 404:
                    rec["structure_status"] = "unavailable"
                else:
                    failures.append({"stage": "hydrate.structure", "decision_id": did, "error": str(exc)})
                struct = None
            if struct:
                rec["structure"] = structure_summary(struct)
                rec["structure_status"] = "fetched"
                rec.setdefault("provenance_events", []).append(
                    {"channel": "decision_lookup", "endpoint": "/structure/{id}", "decision_id": did}
                )
        hydrated.append(did)
    lazy["hydrated"] = hydrated
    lazy["full_text"] = "fetched" if hydrated else "lazy"


__all__ = ["build_candidate_bundle", "make_transport", "DEFAULT_STAGES"]
