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
    return out


def _map_bundle(product_bundle: dict, started_at: float) -> dict:
    mapped, clusters, relations = build_map(product_bundle["decisions"])
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
    candidate = _retrieve(query, top_n, mode=retrieval_mode, hydrate_top=0)
    if not candidate.get("candidates"):
        raise RuntimeError("OpenCaseLaw retrieval returned no decisions")
    product = _candidate_to_product(candidate)
    bundle = _map_bundle(product, t0)
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
    base_errors = validate_bundle(initial_bundle)
    if base_errors:
        raise ValueError(f"cannot enrich invalid bundle: {base_errors}")
    work = _merge_hydrated_evidence(initial_bundle, retrieval_mode=retrieval_mode, evidence_count=evidence_count)

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
    audited["provenance"]["enrichment_latency_seconds"] = round(time.time() - t0, 3)
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
