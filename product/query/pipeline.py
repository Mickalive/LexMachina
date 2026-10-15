"""LEX v45 query pipeline: OpenCaseLaw retrieval -> immediate map -> lazy evidence -> generative audit.

The live path never mixes fixture decisions into user results.  Fixtures are
an explicit offline/test mode only.  Accepted Frontier components are consumed
through narrow adapters rather than reimplemented here.
"""
from __future__ import annotations

import copy
import sys
import time
from pathlib import Path
from typing import Any

from .answer import build_answer, counter_authority_pass
from .answer_contract import ensure_coverage
from .bundle import build_bundle, validate_bundle
from .qmap import build_map
from .relevance import rerank_product_bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_ROOT = REPO_ROOT / "frontier" / "frontier-query-retrieval"
GENAUDIT_ROOT = REPO_ROOT / "frontier" / "frontier-generative-audit"

from .cache_path import product_cache_dir  # noqa: E402  (scope-safe cache root)

for _p in (RETRIEVAL_ROOT, GENAUDIT_ROOT):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ocl_adapter import AdapterConfig, build_candidate_bundle, to_product_bundle  # noqa: E402
from ocl_adapter.fixtures import fixture_config, replay_fixtures  # noqa: E402
from generative_audit.integration_contract import run_generative_audit  # noqa: E402
from generative_audit.adversarial import AdversarialFinding  # noqa: E402

from .audit_seam import apply as _apply_audit_seam  # noqa: E402

# Product-owned knobs (adversarial wall-clock budget + free-model order). The
# applied configuration is exported into every bundle's provenance so the
# auditor can verify it instead of inferring it.
AUDIT_SEAM = _apply_audit_seam()

MIN_LIVE_RESULTS = 100
MAX_RESULTS = 300


def _text_for(d: dict) -> str:
    return str(d.get("full_text") or d.get("regeste") or d.get("snippet") or d.get("title") or "")


def _retrieval_config(top_n: int, mode: str) -> AdapterConfig:
    """Budget the candidate cap across independent retrieval channels.

    The accepted adapter stops a stage when max_candidates is full.  A single
    100-result lexical page could therefore crowd out language/citation passes.
    We deliberately use smaller one-page search slices so DE/FR/IT, leading
    cases and citation neighbours all get a chance before the 100-300 cap fills.
    """
    top_n = max(MIN_LIVE_RESULTS, min(MAX_RESULTS, int(top_n)))
    # Fetch a broader internal pool because multilingual/citation channels
    # overlap heavily.  The product target remains 100-300 decisions; this
    # headroom prevents dedupe from shrinking the map below the requested size.
    pool_cap = min(MAX_RESULTS, max(top_n + 80, int(top_n * 1.6)))
    page = max(25, min(50, top_n // 4))
    return AdapterConfig(
        mode=mode,
        cache_dir=str(product_cache_dir()),
        target=top_n,
        max_candidates=pool_cap,
        page_size=page,
        max_pages_per_variant=1,
        lang_max_pages=1,
        max_requests=40,
        max_rps=4.0,
        stop_when_target_met=False,
        citation_expansion=True,
        citation_seeds=3,
        citation_page_size=min(20, max(10, top_n // 10)),
        max_new_from_citations=min(60, max(25, top_n // 4)),
        leading_cases=True,
        leading_cases_limit=min(20, max(10, top_n // 10)),
    )


def _retrieve(
    query: str,
    top_n: int,
    *,
    mode: str = "live",
    hydrate_top: int = 0,
    hydrate_ids: list[str] | None = None,
) -> dict:
    if mode == "fixture":
        # Frozen OpenCaseLaw envelopes; deterministic and network-free.
        cfg = fixture_config(
            mode="offline",
            target=min(max(40, top_n), 200),
            max_candidates=min(max(100, top_n), 200),
            stop_when_target_met=False,
        )
        fixture_hydrate_top = hydrate_top or len(hydrate_ids or [])
        return replay_fixtures(query, config=cfg, hydrate_top=fixture_hydrate_top)
    if mode not in {"live", "offline", "refresh"}:
        raise ValueError(f"unsupported retrieval mode: {mode}")
    cfg = _retrieval_config(top_n, mode)
    return build_candidate_bundle(
        query,
        config=cfg,
        hydrate_top=hydrate_top,
        hydrate_ids=hydrate_ids,
        include_structure=True,
    )


#: Citation-expansion channels.  A record that only exists because of one of
#: these channels is a *shell*: it was synthesised from an edge payload, not
#: from the decision's own record (QUERY_MAP_MVP 2/10A: typed relations stay
#: provenance-preserving).
CITE_CHANNELS = frozenset({"citation.incoming", "citation.outgoing"})


def _citation_shell(c: dict) -> bool:
    """True when ``c`` is an unhydrated citation-expansion shell.

    Required-fix provenance: results/audit/product/CYCLE_38766812030_GATE.json
    (gate=REVISE, required_fixes[0] ``foreign_citation_on_citation_channel_rows``).
    The accepted adapter's ``normalize_citation()`` sets
    ``citation = raw['target_ref']``.  For an *incoming* edge ``target_ref``
    belongs to the CITED seed, not to the citing decision, so 13% of the claim
    bundle's rows displayed another decision's citation (``bger_6B_21_2023``
    rendered ``6B_31_2019``).  frontier/** is outside product write scope, so
    the product's own bundle assembly repairs the field here instead.
    """
    channels = set(c.get("channels") or ())
    return bool(
        c.get("record_kind") == "citation_neighbour"
        or c.get("detail_status") == "pending"
        or (channels and channels <= CITE_CHANNELS)
    )


def _candidate_to_product(candidate_bundle: dict) -> dict:
    out = to_product_bundle(candidate_bundle)
    by_id = {c.get("decision_id"): c for c in candidate_bundle.get("candidates", [])}
    for d in out.get("decisions", []):
        c = by_id.get(d.get("decision_id")) or {}
        # Preserve rich evidence as extra fields; required product fields remain unchanged.
        for key in (
            "title", "regeste", "full_text", "structure", "source_url", "pdf_url",
            "court_name", "legal_area", "channels", "detail_status", "full_text_status",
        ):
            if c.get(key) is not None:
                d[key] = copy.deepcopy(c.get(key))
        d["snippet"] = d.get("snippet") or c.get("regeste") or c.get("title") or ""
        d["counter_status"] = "none"
        if _citation_shell(c):
            # Never emit a citation that belongs to a different record: derive
            # this row's own identity instead (own docket number when the edge
            # payload carries it, else the row's own decision_id).  Hydrated
            # rows keep the API's own citation for the same decision.
            own = str(c.get("docket_number") or "").strip() or str(d.get("decision_id") or "").strip()
            if own:
                d["citation"] = own
    return out


def typed_citation_relations(candidates: list[dict], decisions: list[dict]) -> list[dict]:
    """Typed citation edges recovered from the adapter's own provenance events.

    The OpenCaseLaw ``/citations`` channel returns *typed* edges
    (seed -> direction -> other end, with confidence and mention count).  The
    accepted adapter stores each edge on the candidate row's
    ``provenance_events`` (``seed_decision_id`` + ``direction``), but
    ``to_product_bundle`` emits ``relations: []`` and the bundle contract has no
    adapter-owned relation list.  ``frontier/**`` is outside product write scope,
    so the product recovers the typed edges here.

    Without them the only relation source is ``find_citations`` string matching
    over decision bodies, which is necessarily empty on an unhydrated map
    (audit advisory F3 of cycle 38779139471: 0 relations for a query where
    retrieval had found 30 typed citation neighbours).  A map whose "reveal
    relations on selection" affordance is always empty hides exactly the
    citation structure QUERY_MAP_MVP 7 asks for.

    Direction semantics, normalised to one reading direction for the reader:
    an ``incoming`` row is a decision that *cites* the seed, an ``outgoing`` row
    is a decision *cited by* the seed.  Both are emitted as ``source`` cites
    ``target``.  Only edges whose two endpoints are both on the map are emitted,
    so the UI never renders a relation to a decision it cannot open.
    """
    on_map = {d.get("decision_id") for d in decisions if d.get("decision_id")}
    edges: dict[tuple[str, str, str], dict] = {}
    for c in candidates:
        channels = set(c.get("channels") or ())
        if not (channels & CITE_CHANNELS):
            continue
        other = str(c.get("decision_id") or "")
        if not other:
            continue
        for ev in c.get("provenance_events") or ():
            if not isinstance(ev, dict) or ev.get("endpoint") != "/citations":
                continue
            seed = str(ev.get("seed_decision_id") or "")
            direction = str(ev.get("direction") or "")
            if not seed or direction not in {"incoming", "outgoing"}:
                continue
            source, target = (other, seed) if direction == "incoming" else (seed, other)
            if source not in on_map or target not in on_map:
                continue
            edges.setdefault((source, target, "citation"), {
                "source": source,
                "target": target,
                "kind": "citation",
                "evidence": (
                    f"OpenCaseLaw /citations {direction} "
                    f"(seed {seed}, confidence {ev.get('confidence')})"
                ),
                "seed_decision_id": seed,
                "direction": direction,
                "confidence": ev.get("confidence"),
                "mention_count": ev.get("mention_count"),
            })
    typed = list(edges.values())
    typed.sort(key=lambda r: (r["source"], r["target"], r["kind"]))
    return typed


def _merge_relations(typed: list[dict], shared: list[dict], limit: int = 500) -> list[dict]:
    """Union of typed-citation and shared-citation edges, de-duplicated, capped.

    Typed edges are listed first because they carry the upstream confidence,
    while a shared-citation edge is only a text coincidence.  De-duplication is
    per *pair of decisions*, not per kind: the detail panel renders one line per
    relation, so the same pair arriving as both kinds must show once.
    """
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for rel in list(typed) + list(shared):
        key = (str(rel.get("source")), str(rel.get("target")))
        if key in seen:
            continue
        seen.add(key)
        out.append(rel)
        if len(out) >= limit:
            break
    return out


def _relations_provenance(candidates: list[dict] | None, typed: list[dict], shared: list[dict]) -> dict:
    """How the relation list was built, exported so an auditor need not infer it."""
    candidates = list(candidates or [])
    citation_rows = sum(
        1 for c in candidates if set(c.get("channels") or ()) & CITE_CHANNELS
    )
    ids = {r["source"] for r in typed} | {r["target"] for r in typed}
    return {
        "typed_citation_relations": len(typed),
        "shared_citation_relations": len(shared),
        "citation_channel_rows": citation_rows,
        "decisions_with_typed_relation": len(ids),
        "typed_source": "ocl_adapter provenance_events (endpoint=/citations, seed_decision_id + direction)",
        "claim_ceiling": (
            "typed edges are the upstream citation channel's own seed/direction records for this "
            "query; they are not a verified citation graph and are not re-derived from decision text"
        ),
    }


def _map_bundle(product_bundle: dict, started_at: float, n_clusters: int = 0,
                candidates: list[dict] | None = None) -> dict:
    mapped, clusters, shared_relations = build_map(product_bundle["decisions"], n_clusters=n_clusters)
    typed_relations = typed_citation_relations(list(candidates or []), mapped)
    relations = _merge_relations(typed_relations, shared_relations)
    decisions = []
    for d in mapped:
        decisions.append({
            **d,
            "counter_status": d.get("counter_status") or "none",
            "counter_evidence": d.get("counter_evidence") or "",
            "counter_uncertainty": d.get("counter_uncertainty"),
        })
    provenance = dict(product_bundle.get("provenance") or {})
    provenance.update({
        "bundle": "query_result_bundle v1.0",
        "phase": "map_ready",
        "latency_seconds": round(time.time() - started_at, 3),
        "retrieval_component": "frontier-query-retrieval/v2",
        "map_component": "query-conditioned-tfidf-v45",
        "fixture_mode": False,
        "relations_provenance": _relations_provenance(candidates, typed_relations, shared_relations),
    })
    return build_bundle(
        query=product_bundle["query"],
        query_variants=list(product_bundle.get("query_variants") or []),
        answer={
            "prose": "",
            "statements": [],
            "cited_decision_ids": [],
            "method": "pending_generative_audit",
            "model": "",
            "status": "pending",
        },
        decisions=decisions,
        clusters=clusters,
        relations=relations,
        provenance=provenance,
    )


def run_query_initial(query: str, top_n: int = 150, *, retrieval_mode: str = "live") -> dict:
    """Fast phase: retrieve/dedupe and return the query-conditioned map.

    No model call and no evidence hydration blocks this phase.
    """
    t0 = time.time()
    query = (query or "").strip()
    if not query:
        raise ValueError("empty query")
    top_n = max(MIN_LIVE_RESULTS, min(MAX_RESULTS, int(top_n))) if retrieval_mode != "fixture" else max(40, min(200, int(top_n)))
    t_upstream_start = time.time()
    candidate = _retrieve(query, top_n, mode=retrieval_mode, hydrate_top=0)
    upstream_s = time.time() - t_upstream_start
    if not candidate.get("candidates"):
        raise RuntimeError("OpenCaseLaw retrieval returned no decisions")
    product = _candidate_to_product(candidate)
    bundle = _map_bundle(product, t0, candidates=list(candidate.get("candidates") or []))
    candidate_languages = {}
    candidate_channels = {}
    for c in candidate.get("candidates", []):
        lang = c.get("language") or "?"
        candidate_languages[lang] = candidate_languages.get(lang, 0) + 1
        for channel in c.get("channels") or []:
            candidate_channels[channel] = candidate_channels.get(channel, 0) + 1
    bundle["provenance"]["retrieval"] = {
        "adapter": candidate.get("adapter"),
        "candidate_bundle_version": candidate.get("bundle_version"),
        "n_candidates": candidate.get("n_candidates"),
        "candidate_languages": candidate_languages,
        "candidate_channels": candidate_channels,
        "dedupe": candidate.get("dedupe"),
        "remote": candidate.get("provenance", {}),
    }
    bundle["provenance"]["fixture_mode"] = retrieval_mode == "fixture"
    # Upstream (OpenCaseLaw network) vs local (dedupe + query-conditioned
    # geometry + bundle assembly) split, so a latency report can never blame
    # local code for public-infrastructure time (QUERY_MAP_MVP 9A / lane
    # runtime performance mandate).  product/latency_budget.py consumes this.
    local_total_s = time.time() - t0
    bundle["provenance"]["timing"] = {
        "upstream_retrieval_s": round(upstream_s, 4),
        "local_total_s": round(local_total_s, 4),
        "local_map_s": round(max(0.0, local_total_s - upstream_s), 4),
        "mode": retrieval_mode,
        "n_decisions": len(bundle.get("decisions") or []),
        "n_clusters": len(bundle.get("clusters") or []),
        "fixture_mode": retrieval_mode == "fixture",
    }
    bundle["provenance"]["latency_seconds"] = round(local_total_s, 3)
    errors = validate_bundle(bundle)
    if errors:
        raise RuntimeError(f"initial query bundle invalid: {errors}")
    return bundle


def _merge_hydrated_evidence(bundle: dict, *, retrieval_mode: str, evidence_count: int) -> dict:
    out = copy.deepcopy(bundle)
    n = len(out.get("decisions", []))
    if n == 0 or evidence_count <= 0:
        return out
    try:
        requested_ids = [
            d["decision_id"]
            for d in sorted(out["decisions"], key=lambda row: row.get("rank") or 10**9)
            [: min(max(1, evidence_count), n)]
        ]
        hydrated = _retrieve(
            out["query"],
            n,
            mode=retrieval_mode,
            hydrate_top=0,
            hydrate_ids=requested_ids,
        )
        by_id = {c.get("decision_id"): c for c in hydrated.get("candidates", [])}
        hydrated_ids = []
        for d in out["decisions"]:
            c = by_id.get(d.get("decision_id")) or {}
            if c.get("full_text"):
                d["full_text"] = c["full_text"]
                d["snippet"] = d.get("snippet") or str(c["full_text"])[:1200]
                hydrated_ids.append(d["decision_id"])
            if c.get("structure"):
                d["structure"] = copy.deepcopy(c["structure"])
        out.setdefault("provenance", {})["evidence_hydration"] = {
            "requested": min(evidence_count, n),
            "hydrated_ids": hydrated_ids,
            "n_hydrated": len(hydrated_ids),
            "degraded": bool(hydrated.get("provenance", {}).get("degraded")),
        }
    except Exception as exc:
        out.setdefault("provenance", {})["evidence_hydration"] = {
            "requested": min(evidence_count, n),
            "hydrated_ids": [],
            "n_hydrated": 0,
            "degraded": True,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return out


def _extractive_degraded_fallback(bundle: dict, error: str, max_cites: int) -> dict:
    """Last-resort UI continuity only; never represented as the normal answer path."""
    out = copy.deepcopy(bundle)
    ranked = sorted(out["decisions"], key=lambda d: d.get("rank") or 10**9)
    answer = build_answer(out["query"], ranked, max_cites=max_cites)
    texts = {d["decision_id"]: _text_for(d) for d in ranked}
    hits, counter_info = counter_authority_pass(out["query"], ranked, texts)
    by_id = {h["decision_id"]: h for h in hits}
    cited = set(answer.get("cited_decision_ids") or [])
    for d in out["decisions"]:
        h = by_id.get(d["decision_id"])
        if h:
            d["counter_status"] = h["counter_status"]
            d["counter_evidence"] = h.get("evidence_sentence") or ""
            d["counter_markers"] = h.get("markers") or []
        elif d["decision_id"] in cited:
            d["counter_status"] = "cited"
        else:
            d["counter_status"] = "none"
    answer["status"] = "degraded"
    out["answer"] = answer
    out.setdefault("provenance", {})["generative_audit"] = {
        "degraded": True,
        "provider_error": error,
        "fallback": "extractive_tfidf_v1",
        "counter_fallback": counter_info,
    }
    return out


def enrich_query_bundle(
    initial_bundle: dict,
    *,
    retrieval_mode: str = "live",
    evidence_count: int = 12,
    max_cites: int = 8,
    fixture_generation: bool = False,
) -> dict:
    """Slow phase: lazily hydrate evidence, generate sourced answer, adversarially challenge it.

    Geometry is preserved byte-for-byte from the initial map.  Only answer,
    evidence and counter-authority fields are patched.
    """
    t0 = time.time()
    timing_local_enrich = 0.0
    base_errors = validate_bundle(initial_bundle)
    if base_errors:
        raise ValueError(f"cannot enrich invalid bundle: {base_errors}")
    work = _merge_hydrated_evidence(initial_bundle, retrieval_mode=retrieval_mode, evidence_count=evidence_count)
    timing_local_enrich = time.time() - t0

    try:
        fixture_ids = [d["decision_id"] for d in work["decisions"][:2]]
        fixture_findings = None
        if fixture_generation and len(work["decisions"]) >= 3:
            challenge = work["decisions"][2]
            evidence = str(challenge.get("full_text") or challenge.get("snippet") or "").strip()[:120]
            fixture_findings = [AdversarialFinding(
                decision_id=challenge["decision_id"],
                title=str(challenge.get("citation") or challenge["decision_id"]),
                reason="limiting",
                evidence_refs=[evidence] if evidence else [],
                uncertainty=0.2,
                confidence=0.9,
            )]
        audited = run_generative_audit(
            work,
            fixture_mode=fixture_generation,
            fixture_answer=("Fixture grounded answer " + " ".join(f"[{x}]" for x in fixture_ids)) if fixture_generation else None,
            fixture_cited_ids=fixture_ids if fixture_generation else None,
            fixture_findings=fixture_findings,
        )
        ga = audited.get("provenance", {}).get("generative_audit", {})
        provider_error = ga.get("provider_error")
        if provider_error or not str(audited.get("answer", {}).get("prose") or "").strip():
            raise RuntimeError(provider_error or "generative provider returned empty answer")
        audited["answer"]["status"] = "ready"
    except Exception as exc:
        audited = _extractive_degraded_fallback(work, f"{type(exc).__name__}: {exc}", max_cites=max_cites)

    # Answer-completeness contract: the model intermittently dropped the
    # Art. 257d(2) effective-dating condition (see results/product/reality_check/
    # 20261014T14{04,22,24}*).  Fill omitted conditions with verbatim sentences
    # from decisions already in the bundle — never with invented text — and
    # export the intervention into provenance for the auditor.
    coverage = ensure_coverage(audited)
    if coverage.get("changed"):
        audited["provenance"]["answer_coverage"] = coverage

    # The adversarial/generative stage must never move the already visible map.
    original_geo = {
        d["decision_id"]: (d.get("x"), d.get("y"), d.get("cluster_id"), d.get("is_outlier", False))
        for d in initial_bundle["decisions"]
    }
    for d in audited["decisions"]:
        if d["decision_id"] in original_geo:
            d["x"], d["y"], d["cluster_id"], d["is_outlier"] = original_geo[d["decision_id"]]

    audited.setdefault("provenance", {})["phase"] = "complete"
    audited["provenance"]["product_audit_seam"] = AUDIT_SEAM
    enriched_total_s = time.time() - t0
    audited["provenance"]["enrichment_latency_seconds"] = round(enriched_total_s, 3)
    # Enrichment runs strictly after the map is already rendered (QUERY_MAP_MVP
    # 9A: the initial map MUST NOT wait for generation), so its cost is reported
    # separately and is never folded into the map budgets.
    audited["provenance"].setdefault("timing", {})
    audited["provenance"]["timing"].update({
        "enrich_total_s": round(enriched_total_s, 4),
        "enrich_model_s": round(enriched_total_s - float(timing_local_enrich), 4),
        "enrich_non_model_s": round(float(timing_local_enrich), 4),
    })
    audited["provenance"]["latency_seconds_total"] = round(
        float(initial_bundle.get("provenance", {}).get("latency_seconds") or 0.0)
        + float(audited["provenance"]["enrichment_latency_seconds"]),
        3,
    )
    errors = validate_bundle(audited)
    if errors:
        raise RuntimeError(f"enriched query bundle invalid: {errors}")
    return audited


def run_query(
    query: str,
    top_n: int = 150,
    max_cites: int = 8,
    *,
    retrieval_mode: str = "live",
    fixture_generation: bool = False,
) -> dict:
    """One-shot convenience API. UI should prefer start -> enrich for progressive rendering."""
    initial = run_query_initial(query, top_n=top_n, retrieval_mode=retrieval_mode)
    return enrich_query_bundle(
        initial,
        retrieval_mode=retrieval_mode,
        max_cites=max_cites,
        fixture_generation=fixture_generation,
    )


__all__ = ["run_query", "run_query_initial", "enrich_query_bundle"]
