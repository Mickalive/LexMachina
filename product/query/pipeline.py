"""LEX v45 query pipeline: OpenCaseLaw retrieval -> immediate map -> lazy evidence -> generative audit.

The live path never mixes fixture decisions into user results.  Fixtures are
an explicit offline/test mode only.  Accepted Frontier components are consumed
through narrow adapters rather than reimplemented here.
"""
from __future__ import annotations

import copy
import re
import sys
import time
from pathlib import Path
from typing import Any

from .answer import build_answer, counter_authority_pass
from .answer_contract import ensure_coverage
from .answer_gap import ensure_cited_answer
from .bundle import build_bundle, validate_bundle
from .qmap import build_map
from .qmap_variants import apply_geometry_variant, selected_variant
from .relevance import rerank_product_bundle
from .adversarial_retrieval import (
    ADVERSARIAL_RETRIEVAL_VERSION,
    apply_adversarial_pass,
    fetch_adversarial_candidates,
    plan_adversarial_queries,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_ROOT = REPO_ROOT / "frontier" / "frontier-query-retrieval"
GENAUDIT_ROOT = REPO_ROOT / "frontier" / "frontier-generative-audit"

from .cache_path import product_cache_dir  # noqa: E402  (scope-safe cache root)

for _p in (RETRIEVAL_ROOT, GENAUDIT_ROOT):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ocl_adapter import AdapterConfig, build_candidate_bundle, to_product_bundle  # noqa: E402
from ocl_adapter.fixtures import fixture_config, replay_fixtures  # noqa: E402
from generative_audit.integration_contract import (  # noqa: E402
    run_adversarial_audit,
    run_generative_audit,
)
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


def replay_fixture_query(
    query: str,
    *,
    top_n: int,
    hydrate_top: int = 0,
    config_factory=None,
) -> dict:
    """Deterministic, network-free replay for ``retrieval_mode="fixture"``.

    Two content-addressed sources are tried in a fixed order, both with
    ``mode="offline"`` (cache-only; a miss degrades, it never hits the network):

    1. the canonical Frontier fixture scenario (``fixture_config``), which only
       ever recorded the frozen fixture query "Kündigung Mietvertrag Mietrecht"
       — unchanged historical behaviour for every pre-existing fixture test;
    2. the product-owned live cache (``results/product/query_cache``) replayed
       with the **same retrieval config the live run used**, because the
       adapter's request keys are config-shaped (page size, page counts,
       channel stages) — a differently-shaped config simply misses.

    Source 2 is what makes ``reality_check.py --mode fixture`` work for the
    four frozen reality legs: their envelopes were recorded by live runs of
    the exact same question and config, but never by the canonical scenario.
    Before this fallback, fixture mode raised "OpenCaseLaw retrieval returned
    no decisions" for every leg question (negative evidence preserved in
    ``results/product/reality_check/summary_fixture_20261016T165553Z.json`` and
    ``..._20261017T055734Z.json``).

    ``config_factory(top_n)`` lets a caller replay with its own live config
    shape (e.g. ``progressive.first_page_config``).
    """
    legacy_cfg = fixture_config(
        mode="offline",
        target=min(max(40, top_n), 200),
        max_candidates=min(max(100, top_n), 200),
        stop_when_target_met=False,
    )
    out = replay_fixtures(query, config=legacy_cfg, hydrate_top=hydrate_top)
    source = "canonical_frontier_fixture_scenario"
    if not out.get("candidates"):
        cfg = (config_factory or (lambda n: _retrieval_config(n, "offline")))(top_n)
        out = replay_fixtures(query, config=cfg, hydrate_top=hydrate_top)
        source = "product_query_cache_live_config_replay"
    prov = out.setdefault("provenance", {})
    prov["product_fixture_replay"] = {
        "source": source,
        "mode": "offline",
        "network": "none",
        "n_candidates": len(out.get("candidates") or []),
    }
    return out


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
        fixture_hydrate_top = hydrate_top or len(hydrate_ids or [])
        return replay_fixture_query(
            query, top_n=top_n, hydrate_top=fixture_hydrate_top
        )
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


def _decision_identity(decision: dict) -> tuple[str, str] | None:
    """(court, docket) identity of a row, or None when it has no docket.

    Upstream ids are not identity enough on their own: the same decision arrives
    both as ``bvger_A-1979_2024`` (from a citation edge) and as
    ``bvger_A-1979_2024_d20240326`` (from a search hit).  Court plus docket is
    what identifies it, and both are already product-row fields.
    """
    docket = str(decision.get("docket_number") or "").strip()
    if not docket:
        return None
    court = str(decision.get("court") or "").strip().lower()
    return (court, re.sub(r"[^a-z0-9]", "", docket.lower()))


def _row_strength(decision: dict) -> tuple[int, int, int, str]:
    """Deterministic preference between two rows of the same decision.

    1. real evidence beats a synthesised shell (a shell has no detail payload);
    2. a row whose own id embeds its own date beats one whose date contradicts
       it (``bvger_A-2789_2024_d20240318`` dated 2024-03-18 is the decision;
       ``bvger_A-2789_2024`` dated 2025-07-04 is the later appeal in the edge);
    3. better rank wins; then lexicographic id, so the order never depends on
       dict iteration order.
    """
    shell = 0 if _citation_shell(decision) else 1
    decision_id = str(decision.get("decision_id") or "")
    match = re.search(r"_d(\d{8})$", decision_id)
    date = str(decision.get("decision_date") or "").replace("-", "")
    consistent = 1 if (match and match.group(1) == date) else 0
    try:
        rank = int(decision.get("rank") or 10**9)
    except (TypeError, ValueError):
        rank = 10**9
    return (shell, consistent, -rank, decision_id)


def merge_duplicate_identities(decisions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Collapse rows that are the same decision under different upstream ids.

    Live run 38812599575 found ``bvger_A-2789_2024`` and
    ``bvger_A-2789_2024_d20240318`` on the same map - both citation-channel
    shells for docket A-2789/2024 - which is one decision counted twice and
    rendered as two points, and which the run-time admissibility check refuses
    (``citation_duplicates``).  Run 38799024807 shipped the same defect in a
    milder form (``bvger_A-1979_2024`` shell beside the hydrated
    ``..._d20240326`` row, carrying two different citation strings for one
    decision).

    Merging is product-owned because identity is the product's contract here -
    the same reason the citation repair below lives in this module rather than
    in the accepted adapter.  The kept row gains the other rows' channels, and
    the merge is exported so an auditor can see exactly which ids disappeared.
    """
    order: list[tuple[tuple[str, str], list[int]]] = []
    groups: dict[tuple[str, str], list[int]] = {}
    for index, decision in enumerate(decisions):
        key = _decision_identity(decision)
        if key is None:
            continue
        if key not in groups:
            groups[key] = []
            order.append((key, groups[key]))
        groups[key].append(index)

    dropped: set[int] = set()
    merges: list[dict] = []
    for key, indices in order:
        if len(indices) < 2:
            continue
        ranked = sorted(indices, key=lambda i: _row_strength(decisions[i]), reverse=True)
        keep = decisions[ranked[0]]
        merged_ids: list[str] = []
        channels = list(keep.get("channels") or [])
        for index in ranked[1:]:
            other = decisions[index]
            dropped.add(index)
            merged_ids.append(str(other.get("decision_id") or ""))
            for channel in other.get("channels") or []:
                if channel not in channels:
                    channels.append(channel)
            for field in ("full_text", "regeste", "snippet", "title", "source_url",
                          "decision_date", "canonical_url"):
                if not keep.get(field) and other.get(field):
                    keep[field] = other[field]
        keep["channels"] = channels
        keep["merged_duplicate_ids"] = merged_ids
        merges.append({
            "identity": {"court": key[0], "docket": key[1]},
            "kept_decision_id": str(keep.get("decision_id") or ""),
            "merged_decision_ids": merged_ids,
            "kept_detail_status": keep.get("detail_status"),
            "n_rows_before": len(indices),
        })
    if not merges:
        return decisions, []
    kept_rows = [d for i, d in enumerate(decisions) if i not in dropped]
    return kept_rows, merges


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
    decisions, merges = merge_duplicate_identities(out.get("decisions") or [])
    out["decisions"] = decisions
    for position, decision in enumerate(decisions, start=1):
        if decision.get("rank") is None:
            decision["rank"] = position
    if merges:
        out.setdefault("provenance", {})["identity_merge"] = {
            "method": "court_docket_identity_merge_v1",
            "n_merges": len(merges),
            "n_rows_removed": sum(len(m["merged_decision_ids"]) for m in merges),
            "merges": merges,
            "claim_ceiling": (
                "rows were collapsed because court + docket identify one decision; the kept id is "
                "deterministic and the dropped ids are listed per merge"
            ),
        }
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
    # Accepted-frontier adoption seam (v50 obligation 4).  OFF by default: an
    # operator opts in with LEXMACHINA_GEOMETRY_VARIANT=relevance_ordered to
    # serve the promoted query-conditioned geometry behind this same bundle.
    geometry_variant = ""
    try:
        geometry_variant = selected_variant()
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if geometry_variant:
        mapped, clusters, _variant_meta = apply_geometry_variant(
            mapped, clusters, str(product_bundle.get("query") or ""), geometry_variant,
        )
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
        "map_component": ("frontier-query-conditioned-map-geometry/" + geometry_variant
                          if geometry_variant else "query-conditioned-tfidf-v45"),
        "geometry_variant": geometry_variant or "incumbent",
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
    # Remote retrieval deliberately over-fetches across multilingual, leading-
    # case and citation channels.  The product must nevertheless honour top_n:
    # rerank locally against the user's question, then map only the strongest
    # requested slice.  Mapping the whole expansion pool was the direct cause
    # of 200+ point maps and off-domain counter-authority noise.
    product = rerank_product_bundle(product)
    before_cap = len(product.get("decisions") or [])
    product["decisions"] = list(product.get("decisions") or [])[:top_n]
    for rank, decision in enumerate(product["decisions"], start=1):
        decision["rank"] = rank
    product.setdefault("provenance", {})["product_selection"] = {
        "method": "legal_rerank_then_top_n_v1",
        "retrieved_pool": before_cap,
        "served_decisions": len(product["decisions"]),
        "requested_top_n": top_n,
        "dropped_after_rerank": max(0, before_cap - len(product["decisions"])),
    }
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
            # v55 render-truth fix: the flag is WRITTEN, never omitted.  A
            # label whose evidence sentence came back empty is unevidenced;
            # the map's render predicate reads this field and an absent key
            # would read as "not yet checked" instead of "checked, nothing
            # found".  False is the honest value (Master Prompt: never
            # classify without evidence the label's own row can support).
            d["counter_evidence_verified"] = bool(h.get("evidence_sentence"))
        elif d["decision_id"] in cited:
            d["counter_status"] = "cited"
            d["counter_evidence_verified"] = False
        else:
            d["counter_status"] = "none"
            d["counter_evidence_verified"] = False
    answer["status"] = "degraded"
    out["answer"] = answer
    out.setdefault("provenance", {})["generative_audit"] = {
        "degraded": True,
        "provider_error": error,
        "fallback": "extractive_tfidf_v1",
        "counter_fallback": counter_info,
    }
    return out


def adversarial_retrieval_pass(
    bundle: dict,
    *,
    retrieval_mode: str = "live",
    max_new: int = 40,
    hydrate_top: int = 12,
    max_intents: int = 4,
) -> dict:
    """Independent adversarial RETRIEVAL against the provisional answer.

    Run after the answer exists and before the bundle is returned, because the
    probes are built from the answer's own legal vocabulary: an adversarial pass
    that re-ranks the initial pool is classification, not retrieval, and the
    accepted measurement ``frontier-adversarial-discoverability``
    (CYCLE_38794235870, gate=PASS, verdict CLASSIFICATION_ONLY) already recorded
    that as the product's counter-authority behaviour.

    Degradation is explicit: an upstream failure contributes zero rows and is
    recorded in ``provenance.adversarial_retrieval.failures``.  It never removes
    rows the initial pass found and never raises.
    """
    plan = plan_adversarial_queries(
        bundle.get("query", ""),
        str((bundle.get("answer") or {}).get("prose") or ""),
        max_intents=max_intents,
    )
    if not plan:
        # Vacuous pass (cycle 38828034436 audit D4): the answer carries no
        # usable legal vocabulary, so no probe is fabricated and the pass is
        # recorded as skipped — not as "found nothing adversarial".
        out = copy.deepcopy(bundle)
        out.setdefault("provenance", {})["adversarial_retrieval"] = {
            "component": "adversarial_retrieval/2",
            "attempted": True,
            "skipped": True,
            "skip_reason": "vacuous_pass: the provisional answer carries no usable legal vocabulary; no probe fabricated",
            "n_new_rows": 0,
            "n_counter_rows": 0,
            "claim_ceiling": "no adversarial retrieval ran; no claim of independence is made",
        }
        return out
    existing_ids = {str(d.get("decision_id")) for d in bundle.get("decisions") or []}
    exclude_identities = set()
    for d in bundle.get("decisions") or []:
        ident = _decision_identity(d)
        if ident is not None:
            exclude_identities.add(ident)
    t_adv = time.time()
    try:
        fetched = fetch_adversarial_candidates(
            bundle.get("query", ""),
            plan,
            mode=retrieval_mode if retrieval_mode in {"live", "offline", "refresh"} else "offline",
            exclude_ids=existing_ids,
            exclude_identities=exclude_identities,
            max_new=max_new,
            hydrate_top=hydrate_top,
        )
        out = apply_adversarial_pass(
            bundle,
            list(fetched.get("candidates") or []),
            fetched.get("provenance"),
        )
        adv_prov = out.setdefault("provenance", {}).setdefault("adversarial_retrieval", {})
        adv_prov["pass_seconds"] = round(time.time() - t_adv, 4)
        adv_prov["fetch_seconds"] = adv_prov.get("seconds")
        return out
    except Exception as exc:
        # A non-critical stage must never cost the researcher their bundle. The
        # failure is recorded verbatim so it can never read as "found nothing".
        out = copy.deepcopy(bundle)
        out.setdefault("provenance", {})["adversarial_retrieval"] = {
            "component": ADVERSARIAL_RETRIEVAL_VERSION,
            "attempted": True,
            "degraded": True,
            "error": f"{type(exc).__name__}: {exc}",
            "n_new_rows": 0,
            "n_counter_rows": 0,
            "claim_ceiling": "the independent adversarial route did not complete; no claim of independence is made",
        }
        return out


def enrich_query_bundle(
    initial_bundle: dict,
    *,
    retrieval_mode: str = "live",
    evidence_count: int = 12,
    max_cites: int = 8,
    fixture_generation: bool = False,
    adversarial_retrieval: bool = True,
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
            defer_adversarial=bool(adversarial_retrieval),
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

    # Zero-citation contract: a sourced answer that cites nothing is either a
    # generator failure or an honest "the corpus does not cover this".  Measured
    # on the shipped gate packet (run 38799024807, question de-kapitalverletzung)
    # it was the second: 23 retrieved rows carry the employer's Fürsorgepflicht
    # and 0 carry *Kapitalverletzung*.  The product therefore surfaces the
    # covered concepts verbatim and cited, and states the uncovered ones with
    # their measured counts, instead of shipping an uncited answer (which the
    # gate-admissibility check blocks) or forcing a citation onto a proposition
    # the decision does not contain (the defect of run 38766812030).
    gap = ensure_cited_answer(audited)
    if gap.get("fired"):
        audited["provenance"]["answer_gap_contract"] = gap

    # Independent adversarial RETRIEVAL, run only now that a provisional answer
    # exists to attack.  It appends unseen rows and never moves a rendered point.
    if adversarial_retrieval:
        audited = adversarial_retrieval_pass(
            audited,
            retrieval_mode=retrieval_mode,
            max_new=0 if fixture_generation else 20,
            hydrate_top=0 if fixture_generation else 12,
        )
        # Now that answer-conditioned retrieval has produced the FINAL bounded
        # source set, classify counters once. This replaces the old ordering
        # where the LLM classified the initial pool and a heuristic labelled
        # newly fetched rows afterward.
        audited = run_adversarial_audit(
            audited,
            fixture_mode=fixture_generation,
            fixture_findings=fixture_findings,
        )

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
