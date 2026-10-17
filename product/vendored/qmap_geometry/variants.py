"""The two charter-mandated query-conditioned geometry variants (V1, V2).

Contract for both (charter acceptance test 2): a pure function of a bundle that
emits ``cluster_id``, ``member_ids``, ``label`` and coordinates in the shape
``product/query/qmap.py::build_map`` already emits.  Nothing under rendering,
colour or interaction is touched.

V1 ``hydrate_then_cluster``
    Cluster and project ONLY over rows that carry text (the accepted hydration
    predicate); un-hydrated shells stay on the map as explicitly-marked
    unclustered context with a negative ``cluster_id`` and ``unclustered=true``,
    and no cluster record is emitted for them, so no shell can form or swell a
    legal group.  Projection = 2-D spectral layout of the query-conditioned
    similarity graph (see geometry_core.project_spectral for the a-priori
    justification drawn from the accepted evidence).

V2 ``relevance_ordered``
    Same clusterable row set, but the layout is a relevance axis: x is the
    rerank score, y is the query-language band, clusters are renumbered in
    descending mean-score order so the highest-scoring group is cluster 0.
    Shells keep their score on the axis but sit in the unclustered band.
"""
from __future__ import annotations

import copy
from typing import Any, Callable

import numpy as np

from .geometry_core import (
    centroid_distance_outliers,
    fit_cluster_geometry,
    qmap_cluster_count,
)
from .hydration import hydration_mask
from .vendored.frontier_map_semantics.textgeo import body

VARIANT_NAMES = ("hydrate_then_cluster", "relevance_ordered")

SCORE_FIELD = "score"


def _texts(rows: list[dict]) -> list[str]:
    texts = [body(d)[:6000] for d in rows]
    if not any(t.strip() for t in texts):
        texts = [str(d.get("decision_id") or i) for i, d in enumerate(rows)]
    return texts


def _base_bundle(bundle: dict) -> dict:
    out = copy.deepcopy(bundle)
    out["decisions"] = [copy.deepcopy(d) for d in bundle.get("decisions") or []]
    out["clusters"] = []
    return out


def _halo_coords(n_shell: int, radius: float = 1.7) -> np.ndarray:
    """Deterministic unclustered-context ring outside the clustered hull."""
    if n_shell == 0:
        return np.zeros((0, 2))
    ang = 2.0 * np.pi * np.arange(n_shell) / n_shell
    return np.column_stack([radius * np.cos(ang), radius * np.sin(ang)])


def _apply_geometry(
    out: dict,
    clustered_idx: list[int],
    fit: dict,
    shell_idx: list[int],
    shell_coords: np.ndarray,
) -> None:
    n = len(out["decisions"])
    ids = [d["decision_id"] for d in out["decisions"]]
    coords = np.zeros((n, 2), dtype=float)
    cid = np.zeros(n, dtype=int)
    for j, i in enumerate(clustered_idx):
        coords[i] = fit["coords"][j]
        cid[i] = int(fit["cluster_ids"][j])
    for jj, i in enumerate(shell_idx):
        coords[i] = shell_coords[jj]
        cid[i] = -(jj + 1)
    is_out = centroid_distance_outliers(
        fit["coords"],
        np.array([int(fit["cluster_ids"][j]) for j in range(len(clustered_idx))], dtype=int),
        np.array(clustered_idx, dtype=int),
        fit["centroids"],
        n,
        ids,
        extra_coords={
            ids[i]: shell_coords[jj] for jj, i in enumerate(shell_idx)
        },
    )
    for i, d in enumerate(out["decisions"]):
        d["x"] = round(float(coords[i, 0]), 4)
        d["y"] = round(float(coords[i, 1]), 4)
        d["cluster_id"] = int(cid[i])
        d["is_outlier"] = bool(is_out[i])
        d["unclustered"] = bool(cid[i] < 0)
    out["clusters"] = copy.deepcopy(fit["clusters"])


def _hydrate_then_cluster(bundle: dict, *, query_language: str) -> dict:
    out = _base_bundle(bundle)
    decisions = out["decisions"]
    if not decisions:
        return out
    mask = hydration_mask(decisions)
    clustered_idx = [i for i, s in enumerate(mask) if not s]
    shell_idx = [i for i, s in enumerate(mask) if s]
    rows = [decisions[i] for i in clustered_idx]
    fit = fit_cluster_geometry(
        _texts(rows), [d["decision_id"] for d in rows], projection="spectral"
    )
    _apply_geometry(out, clustered_idx, fit, shell_idx, _halo_coords(len(shell_idx)))
    out["geometry_variant"] = {
        "name": "hydrate_then_cluster",
        "projection": "spectral_nearest_neighbors_k12",
        "clustered_rows": len(clustered_idx),
        "unclustered_context_rows": len(shell_idx),
        "n_clusters": len(out["clusters"]),
        "geometry_seconds": round(float(fit["elapsed"]), 4),
    }
    return out


def _relevance_ordered(bundle: dict, *, query_language: str) -> dict:
    out = _base_bundle(bundle)
    decisions = out["decisions"]
    if not decisions:
        return out
    mask = hydration_mask(decisions)
    clustered_idx = [i for i, s in enumerate(mask) if not s]
    shell_idx = [i for i, s in enumerate(mask) if s]
    rows = [decisions[i] for i in clustered_idx]
    fit = fit_cluster_geometry(
        _texts(rows), [d["decision_id"] for d in rows], projection="svd"
    )

    scores = np.array(
        [float(d.get(SCORE_FIELD) or 0.0) for d in decisions], dtype=float
    )
    lo, hi = float(scores.min()), float(scores.max())
    span = (hi - lo) or 1.0
    x = 2.0 * (scores - lo) / span - 1.0

    # Language bands: the query language owns the top band, the other languages
    # are stacked deterministically below it, shells sit in the unclustered band.
    languages = sorted(
        {str(d.get("language")) for d in decisions}, key=lambda s: (s != query_language, s)
    )
    band_of = {
        lang: 0.6 - 0.35 * i if lang != "None" else -0.9
        for i, lang in enumerate(languages)
    }
    jitter = np.array(
        [((int(d.get("rank") or 0) * 2654435761) % 997) / 997.0 - 0.5 for d in decisions],
        dtype=float,
    )

    # Renumber clusters by descending mean rerank score (cluster 0 = strongest).
    score_by_id = {d["decision_id"]: float(d.get(SCORE_FIELD) or 0.0) for d in decisions}
    by_score = sorted(
        fit["clusters"],
        key=lambda c: -sum(score_by_id[m] for m in c["member_ids"]) / max(1, len(c["member_ids"])),
    )
    old_to_new = {int(c["cluster_id"]): k for k, c in enumerate(by_score)}
    clusters = []
    for new_id, c in enumerate(by_score):
        rec = copy.deepcopy(c)
        rec["cluster_id"] = new_id
        clusters.append(rec)
    row_cluster = np.array(
        [old_to_new[int(fit["cluster_ids"][j])] for j in range(len(clustered_idx))],
        dtype=int,
    )

    coords = np.column_stack([x, np.zeros(len(decisions))])
    cid = np.zeros(len(decisions), dtype=int)
    for j, i in enumerate(clustered_idx):
        d = decisions[i]
        lang = str(d.get("language"))
        coords[i, 1] = band_of.get(lang, -0.9) + 0.08 * jitter[i]
        cid[i] = int(row_cluster[j])
    for jj, i in enumerate(shell_idx):
        coords[i, 1] = -1.0 + 0.05 * jitter[i]
        cid[i] = -(jj + 1)

    centroids = {
        new: np.array(
            [coords[clustered_idx[j]] for j in range(len(clustered_idx)) if row_cluster[j] == new]
        ).mean(axis=0)
        for new in range(len(clusters))
    }
    is_out = centroid_distance_outliers(
        np.array([coords[i] for i in clustered_idx]),
        row_cluster,
        np.array(clustered_idx, dtype=int),
        centroids,
        len(decisions),
        [d["decision_id"] for d in decisions],
        extra_coords={
            decisions[i]["decision_id"]: coords[i] for i in shell_idx
        },
    )
    for i, d in enumerate(decisions):
        d["x"] = round(float(coords[i, 0]), 4)
        d["y"] = round(float(coords[i, 1]), 4)
        d["cluster_id"] = int(cid[i])
        d["is_outlier"] = bool(is_out[i])
        d["unclustered"] = bool(cid[i] < 0)
    out["clusters"] = clusters
    out["geometry_variant"] = {
        "name": "relevance_ordered",
        "projection": "rerank_score_axis_with_query_language_bands",
        "clustered_rows": len(clustered_idx),
        "unclustered_context_rows": len(shell_idx),
        "n_clusters": len(clusters),
        "geometry_seconds": round(float(fit["elapsed"]), 4),
    }
    return out


VARIANTS: dict[str, Callable[..., dict]] = {
    "hydrate_then_cluster": _hydrate_then_cluster,
    "relevance_ordered": _relevance_ordered,
}


def build_variant_geometry(bundle: dict, variant: str, *, query_language: str) -> dict:
    """Pure function: shipped bundle in, variant geometry bundle out."""
    if variant not in VARIANTS:
        raise KeyError(f"unknown variant {variant!r}; known: {sorted(VARIANTS)}")
    return VARIANTS[variant](bundle, query_language=query_language)
