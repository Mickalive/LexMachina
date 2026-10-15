"""Progressive query execution: first-page map, then background expansion.

Why this module exists
----------------------
The two-phase contract in ``pipeline.py`` was progressive in *name* only.
``run_query_initial`` still ran the **entire** multi-channel retrieval —
query variants, DE/FR/IT language pages, citation expansion and leading cases,
up to 40 upstream requests — before returning anything.  Measured live on
2026-10-15 (run 38665681083, real OpenCaseLaw, ``product/query_app.py``):

    GET /api/query/start   136.79 s  (upstream_retrieval_s 136.61, local_map_s 0.18)
    GET /api/query/enrich  150.70 s  (model 101.69, evidence hydration 49.00)

The owner/jurist doing the comparative human gate therefore stares at an empty
page for ~2.3 minutes before the first point is drawn.  QUERY_MAP_MVP §9A asks
for the opposite: render the first results immediately and expand toward
100-300 in the background.

This module adds the missing first stage without touching the accepted
``ocl_adapter`` component:

1. ``run_query_first_page``  — one bounded search stage (single upstream page),
   then local geometry.  This is the first thing the browser draws.
2. ``expand_query_bundle``  — the full retrieval, merged into the *same* map.

Map stability contract
----------------------
Refitting TF-IDF + SVD + KMeans on the larger candidate set would silently move
points the researcher already looked at.  Expansion therefore reconstructs the
fitted projection from the bundle that was actually shipped (texts -> vectorizer
/SVD -> shipped coordinates, cluster ids and labels) and projects the new
decisions into *that* space, attaching each to its nearest existing cluster.
Already-rendered points keep their exact ``x``, ``y``, ``cluster_id`` and
``is_outlier``; cluster labels are never re-invented.  The same
"enrichment must not move the map" rule that ``enrich_query_bundle`` enforces
for the answer stage is therefore also enforced across retrieval stages.

Everything reported here is measured and exported into
``provenance.progressive`` so an auditor can recompute it.
"""
from __future__ import annotations

import copy
import time
from typing import Any

from .bundle import build_bundle, validate_bundle
from .qmap import MapModel, build_map, fit_map_model

#: One upstream page is enough to draw a real map immediately.  The accepted
#: adapter returns at most ``page_size`` hits for it.
FIRST_PAGE_SIZE = 50

#: Product target for the finished map (QUERY_MAP_MVP: 100-300 decisions).
TARGET_MIN, TARGET_MAX = 100, 300

_GEOMETRY_KEYS = ("x", "y", "cluster_id", "is_outlier", "_outlier_dist")


def first_page_config(top_n: int, mode: str, page_size: int = FIRST_PAGE_SIZE):
    """A deliberately tiny adapter config: one search stage, no expansion.

    The product keeps its own retrieval budgeting (see
    ``pipeline._retrieval_config``) for the full pass; this one only has to be
    fast enough that a human sees the map in seconds.
    """
    from ocl_adapter import AdapterConfig

    from .cache_path import product_cache_dir

    return AdapterConfig(
        mode=mode,
        cache_dir=str(product_cache_dir()),
        target=max(20, min(int(top_n), page_size)),
        max_candidates=max(20, int(page_size)),
        page_size=max(10, min(int(page_size), 50)),
        max_pages_per_variant=1,
        lang_max_pages=0,
        max_requests=1,
        max_rps=4.0,
        stop_when_target_met=True,
        stages=("search",),
        citation_expansion=False,
        leading_cases=False,
    )


def _retrieve_first_page(query: str, top_n: int, mode: str) -> dict:
    from ocl_adapter import build_candidate_bundle
    from ocl_adapter.fixtures import fixture_config, replay_fixtures

    if mode == "fixture":
        cfg = fixture_config(
            mode="offline",
            target=min(max(40, top_n), 200),
            max_candidates=min(max(100, top_n), 200),
            stop_when_target_met=False,
        )
        return replay_fixtures(query, config=cfg, hydrate_top=0)
    cfg = first_page_config(top_n, mode)
    return build_candidate_bundle(query, config=cfg, hydrate_top=0, include_structure=True)


def _retrieval_provenance(candidate: dict) -> dict:
    languages: dict[str, int] = {}
    channels: dict[str, int] = {}
    for c in candidate.get("candidates", []):
        lang = c.get("language") or "?"
        languages[lang] = languages.get(lang, 0) + 1
        for channel in c.get("channels") or []:
            channels[channel] = channels.get(channel, 0) + 1
    return {
        "adapter": candidate.get("adapter"),
        "candidate_bundle_version": candidate.get("bundle_version"),
        "n_candidates": candidate.get("n_candidates"),
        "candidate_languages": languages,
        "candidate_channels": channels,
        "dedupe": candidate.get("dedupe"),
        "remote": candidate.get("provenance", {}),
    }


def map_model_from_bundle(bundle: dict) -> MapModel | None:
    """Rebuild a reusable projection whose geometry is what the client already has.

    The vectorizer/SVD come from a deterministic refit on the same texts in the
    same order; the coordinates, cluster ids and cluster labels are then taken
    from the shipped bundle, so the reconstructed model reproduces the rendered
    map exactly instead of merely approximating it.
    """
    decisions = bundle.get("decisions") or []
    if not decisions:
        return None
    texts = [{k: v for k, v in d.items() if k not in _GEOMETRY_KEYS} for d in decisions]
    model = fit_map_model(texts)
    if model is None:
        return None
    import numpy as np

    model.coords = np.array([[float(d.get("x") or 0.0), float(d.get("y") or 0.0)] for d in decisions])
    model.cluster_ids = np.array([int(d.get("cluster_id") or 0) for d in decisions], dtype=int)
    model.decision_ids = [d["decision_id"] for d in decisions]
    centroids: dict[int, Any] = {}
    for cid in sorted({int(c) for c in model.cluster_ids}):
        pts = np.array([
            [float(decisions[i].get("x") or 0.0), float(decisions[i].get("y") or 0.0)]
            for i in range(len(decisions))
            if int(decisions[i].get("cluster_id") or 0) == cid
        ])
        if len(pts):
            centroids[cid] = pts.mean(axis=0)
    model.centroids = centroids
    model.labels = {
        int(c["cluster_id"]): str(c.get("label") or "") for c in bundle.get("clusters") or []
    }
    model.outliers = {d["decision_id"]: bool(d.get("is_outlier")) for d in decisions}
    return model


def target_clusters(target: int) -> int:
    """Cluster count of the finished map, decided before the map is drawn.

    ``qmap.build_map`` derives this from the size of the set it is given.  The
    first page is a small set, so letting it decide would permanently cap the
    granularity of the expanded map (live run 38665681083: 4 clusters for 194
    decisions, where the single-shot map had 8).  Deriving it from the target
    instead keeps cluster count and granularity identical to the map the
    researcher would have got by waiting.
    """
    return max(2, min(8, int(target) // 12 + 1))


def run_query_first_page(query: str, top_n: int = 150, *, retrieval_mode: str = "live") -> dict:
    """Fastest stage: one upstream page -> a complete, renderable query map.

    Returns a valid ``query_result_bundle`` whose ``provenance.progressive``
    records that the map is still partial and how much more is coming.
    """
    from .pipeline import _candidate_to_product, _map_bundle

    t0 = time.time()
    query = (query or "").strip()
    if not query:
        raise ValueError("empty query")
    target = max(TARGET_MIN, min(TARGET_MAX, int(top_n)))
    t_up = time.time()
    candidate = _retrieve_first_page(query, target, retrieval_mode)
    upstream_s = time.time() - t_up
    if not candidate.get("candidates"):
        raise RuntimeError("OpenCaseLaw retrieval returned no decisions")
    product = _candidate_to_product(candidate)
    bundle = _map_bundle(product, t0, n_clusters=target_clusters(target))
    total_s = time.time() - t0
    prov = bundle["provenance"]
    prov["retrieval"] = _retrieval_provenance(candidate)
    prov["retrieval_first_page"] = prov["retrieval"]
    prov["fixture_mode"] = retrieval_mode == "fixture"
    prov["timing"] = {
        "upstream_retrieval_s": round(upstream_s, 4),
        "local_total_s": round(total_s, 4),
        "local_map_s": round(max(0.0, total_s - upstream_s), 4),
        "mode": retrieval_mode,
        "n_decisions": len(bundle.get("decisions") or []),
        "n_clusters": len(bundle.get("clusters") or []),
        "fixture_mode": retrieval_mode == "fixture",
    }
    prov["latency_seconds"] = round(total_s, 3)
    prov["progressive"] = {
        "stage": "first_page",
        "expanded": False,
        "target": target,
        "n_first_page": len(bundle.get("decisions") or []),
        "first_page_size": FIRST_PAGE_SIZE,
        "first_page_upstream_s": round(upstream_s, 4),
        "first_page_total_s": round(total_s, 4),
        "n_clusters": len(bundle.get("clusters") or []),
        "target_clusters": target_clusters(target),
        "map_stability": "not_applicable_single_pass",
    }
    errors = validate_bundle(bundle)
    if errors:
        raise RuntimeError(f"first-page query bundle invalid: {errors}")
    return bundle


def _merge_decisions(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], int]:
    """Merge two ranked decision lists, keeping already-shown records intact.

    Records are copied on write: the caller's first-page bundle is still the
    rendered map and must not be edited underneath it.
    """
    rank_by_id = {d["decision_id"]: d.get("rank") for d in incoming}
    order_by_id = {d["decision_id"]: i for i, d in enumerate(incoming)}
    merged: dict[str, dict] = {}
    for d in existing:
        merged[d["decision_id"]] = dict(d)
    added = 0
    for d in incoming:
        did = d["decision_id"]
        if did in merged:
            # Keep the record the client already has; retrieval may have added
            # richer text for it in the meantime.
            if not merged[did].get("full_text") and d.get("full_text"):
                merged[did]["full_text"] = d["full_text"]
            continue
        merged[did] = dict(d)
        added += 1

    def key(item):
        did = item["decision_id"]
        base = order_by_id.get(did)
        if base is None:
            base = 10**6 + int(item.get("rank") or 0)
        return (base, did)

    ordered = sorted(merged.values(), key=key)
    for i, d in enumerate(ordered, start=1):
        d["rank"] = i
    return ordered, added


def expand_query_bundle(
    initial_bundle: dict,
    *,
    retrieval_mode: str = "live",
    top_n: int | None = None,
) -> dict:
    """Background stage: full retrieval merged into the already-rendered map.

    Returns a new bundle.  Decisions, coordinates, cluster ids and cluster
    labels of the first-page map are preserved; new decisions are projected into
    the same space.  The answer stays ``pending``: the generative and
    counter-authority stages remain the separate ``enrich_query_bundle`` job.
    """
    from .pipeline import _candidate_to_product, _map_bundle, _retrieve, _retrieval_config

    base_errors = validate_bundle(initial_bundle)
    if base_errors:
        raise ValueError(f"cannot expand invalid bundle: {base_errors}")
    t0 = time.time()
    query = initial_bundle["query"]
    target = int(top_n or initial_bundle.get("provenance", {}).get("progressive", {}).get("target") or 150)
    target = max(TARGET_MIN, min(TARGET_MAX, target)) if retrieval_mode != "fixture" else max(40, min(200, target))

    t_up = time.time()
    candidate = _retrieve(query, target, mode=retrieval_mode, hydrate_top=0)
    upstream_s = time.time() - t_up
    if not candidate.get("candidates"):
        raise RuntimeError("OpenCaseLaw expansion returned no decisions")
    product = _candidate_to_product(candidate)

    incoming = list(product.get("decisions") or [])
    existing = list(initial_bundle.get("decisions") or [])
    merged, added = _merge_decisions(existing, incoming)

    frozen_before = {
        d["decision_id"]: (d.get("x"), d.get("y"), d.get("cluster_id"), bool(d.get("is_outlier")))
        for d in existing
    }
    model = map_model_from_bundle(initial_bundle)
    decisions, clusters, relations = build_map(merged, model=model)
    for d in decisions:
        d["counter_status"] = d.get("counter_status") or "none"
        d["counter_evidence"] = d.get("counter_evidence") or ""
        d["counter_uncertainty"] = d.get("counter_uncertainty")
    displaced = [
        d["decision_id"] for d in decisions
        if d["decision_id"] in frozen_before
        and (d.get("x"), d.get("y"), d.get("cluster_id"), bool(d.get("is_outlier"))) != frozen_before[d["decision_id"]]
    ]
    for d in decisions:
        if d["decision_id"] in frozen_before:
            d["x"], d["y"], d["cluster_id"], d["is_outlier"] = frozen_before[d["decision_id"]]
    after = {d["decision_id"]: (d.get("x"), d.get("y"), d.get("cluster_id"), bool(d.get("is_outlier")))
             for d in decisions}
    moved = [did for did, geo in frozen_before.items() if after.get(did) != geo]

    out = build_bundle(
        query=initial_bundle["query"],
        query_variants=list(initial_bundle.get("query_variants") or []),
        answer=copy.deepcopy(initial_bundle.get("answer") or {
            "prose": "", "statements": [], "cited_decision_ids": [],
            "method": "pending_generative_audit", "model": "", "status": "pending",
        }),
        decisions=decisions,
        clusters=clusters,
        relations=relations,
        provenance=copy.deepcopy(initial_bundle.get("provenance") or {}),
    )
    prov = out["provenance"]
    had_answer = (initial_bundle.get("answer") or {}).get("status") in {"ready", "degraded"}
    prov["phase"] = "complete" if had_answer else "map_expanded"
    prov["retrieval_first_page"] = prov.get("retrieval_first_page") or prov.get("retrieval")
    prov["retrieval"] = _retrieval_provenance(candidate)
    total_s = time.time() - t0
    timing = dict(prov.get("timing") or {})
    timing.update({
        "expand_upstream_s": round(upstream_s, 4),
        "expand_local_s": round(max(0.0, total_s - upstream_s), 4),
        "n_decisions": len(decisions),
        "n_clusters": len(clusters),
    })
    prov["timing"] = timing
    prov["latency_seconds"] = round(
        float(timing.get("local_total_s") or 0.0) + total_s, 3
    )
    first = dict(prov.get("progressive") or {})
    first.update({
        "stage": "expanded",
        "expanded": True,
        "n_before": len(existing),
        "n_after": len(decisions),
        "n_added": added,
        "expand_upstream_s": round(upstream_s, 4),
        "expand_total_s": round(total_s, 4),
        "map_stability": "geometry_preserved",
        "points_moved": len(moved),
        # Refitting the projection over the merged set can displace an already
        # rendered point; those coordinates are restored from the shipped map.
        # Both numbers are exported: the second is what the client saw.
        "points_displaced_by_refit": len(displaced),
        # The answer/counter fields of an already-enriched bundle survive the
        # merge, but saying so is part of the provenance the auditor reads.
        "expanded_after_answer": had_answer,
    })
    prov["progressive"] = first
    errors = validate_bundle(out)
    if errors:
        raise RuntimeError(f"expanded query bundle invalid: {errors}")
    return out


__all__ = [
    "FIRST_PAGE_SIZE", "TARGET_MIN", "TARGET_MAX",
    "first_page_config", "map_model_from_bundle",
    "run_query_first_page", "expand_query_bundle",
]