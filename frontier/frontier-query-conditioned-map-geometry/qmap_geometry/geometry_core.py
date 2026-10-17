"""Shared geometry primitives for the query-conditioned variants.

Everything here is a pure function of texts/rows.  The vectorizer, the KMeans
rule, the label rule and the outlier rule are the accepted qmap.py rules
(only the ROW SET they are applied to changes); the projection operator is the
one deliberate difference between a variant and the shipped map.

Provenance: qmap rules vendored through
``vendored.frontier_map_semantics.textgeo`` (byte-identical copy of the
accepted product geometry as mounted for run 38839351403).
"""
from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from .vendored.frontier_map_semantics.textgeo import (
    body,
    cluster_kmeans,
    fit_tfidf,
    label_terms,
    project_svd,
)

NEIGHBORHOOD_K = 12
RANDOM_STATE = 42


def qmap_cluster_count(n: int) -> int:
    """The shipped qmap cluster-count rule (qmap.py build_map)."""
    k = max(2, min(8, n // 12 + 1)) if n >= 6 else 1
    return max(1, min(k, n))


def _canonicalise(coords: np.ndarray) -> np.ndarray:
    out = np.array(coords, dtype=float, copy=True)
    for axis in range(out.shape[1]):
        col = out[:, axis]
        if len(col) and col[int(np.argmax(np.abs(col)))] < 0:
            out[:, axis] *= -1
    scale = float(np.abs(out).max()) or 1.0
    return out / scale


def project_svd_qmap(X) -> np.ndarray:
    """Shipped projection: TruncatedSVD(2) + canonicalisation + max-abs scale."""
    _svd, coords, _scale = project_svd(X, random_state=RANDOM_STATE)
    return _canonicalise(np.asarray(coords, dtype=float))


def knn_similarity(X, n_neighbors: int = NEIGHBORHOOD_K):
    """Symmetrised k-nearest-neighbour similarity graph over cosine distance.

    Built explicitly, because ``SpectralEmbedding(affinity='nearest_neighbors')``
    silently falls back to a dense RBF affinity when handed sparse TF-IDF input
    (measured warning from scikit-learn 1.9.1 on this run).  The graph is the
    operator the variant claims to use, so it is constructed here and passed as
    ``affinity='precomputed'``.
    """
    from sklearn.metrics.pairwise import cosine_distances

    D = np.nan_to_num(np.asarray(cosine_distances(X), dtype=float), nan=1.0)
    n = D.shape[0]
    k = int(min(n_neighbors, max(1, n - 1)))
    S = np.zeros((n, n), dtype=float)
    for i in range(n):
        order = np.argsort(D[i], kind="stable")
        for j in order[1:k + 1]:
            j = int(j)
            w = 1.0 / (1.0 + float(D[i, j]))
            S[i, j] = max(S[i, j], w)
            S[j, i] = max(S[j, i], w)
    np.fill_diagonal(S, 0.0)
    return S


def project_spectral(X, n_neighbors: int = NEIGHBORHOOD_K) -> np.ndarray:
    """2-D spectral layout of the query-conditioned result set.

    Chosen a priori, before any frozen score was computed, because the ACCEPTED
    evidence already shows that a linear 2-D truncation of the TF-IDF space does
    not preserve query-conditioned similarity (PROJ_SPEARMAN -0.075 / 0.018 /
    0.054 against a 0.50 bar on the three served bundles).  A layout that keeps
    neighbourhoods together is the definition of the Master Prompt's
    "proximity = query-conditioned similarity", which is what this operator is
    for.  Deterministic: fixed kNN graph, fixed random_state.
    """
    from sklearn.manifold import SpectralEmbedding

    S = knn_similarity(X, n_neighbors)
    emb = SpectralEmbedding(
        n_components=2, affinity="precomputed", random_state=RANDOM_STATE
    )
    return _canonicalise(np.asarray(emb.fit_transform(S), dtype=float))


PROJECTIONS: dict[str, Callable[[Any], np.ndarray]] = {
    "svd": project_svd_qmap,
    "spectral": project_spectral,
}


def fit_cluster_geometry(
    texts: list[str],
    ids: list[str],
    *,
    projection: str = "spectral",
) -> dict:
    """Cluster + project one row set. Returns cluster records and coordinates.

    Mirrors qmap.build_map on the given row set: same vectorizer, same KMeans
    rule, same label rule, same member_ids[:50] truncation contract.  Only the
    projection operator is swappable.
    """
    t0 = time.perf_counter()
    n = len(texts)
    if n == 0:
        return {"coords": np.zeros((0, 2)), "cluster_ids": np.zeros(0, dtype=int),
                "clusters": [], "elapsed": 0.0, "vectorizer": None, "X": None,
                "n_clusters": 0}
    vec, X = fit_tfidf(texts)
    coords = PROJECTIONS[projection](X)
    raw, k = cluster_kmeans(X, n, random_state=RANDOM_STATE)
    terms = [str(t) for t in vec.get_feature_names_out()]
    meta = []
    for old in sorted(set(int(v) for v in raw)):
        idx = np.where(raw == old)[0]
        mean = np.asarray(X[idx].mean(axis=0)).ravel()
        label = ", ".join(label_terms(mean, terms))
        centroid = coords[idx].mean(axis=0)
        meta.append((old, idx, label, float(centroid[0]), float(centroid[1])))
    ordered = sorted(meta, key=lambda x: (x[2], round(x[3], 4), round(x[4], 4)))
    remap = {old: new for new, (old, *_r) in enumerate(ordered)}
    labels = np.array([remap[int(x)] for x in raw], dtype=int)
    clusters = []
    for old, new in sorted(remap.items(), key=lambda kv: kv[1]):
        idx = [i for i in np.where(raw == old)[0]]
        _o, _i, label, _x, _y = [m for m in meta if m[0] == old][0]
        clusters.append({
            "cluster_id": int(new),
            "label": label or f"Cluster {new}",
            "size": int(len(idx)),
            "member_ids": [ids[i] for i in idx][:50],
        })
    centroids = {
        int(new): coords[np.where(labels == new)[0]].mean(axis=0) for new in remap.values()
    }
    return {
        "coords": coords,
        "cluster_ids": labels,
        "clusters": clusters,
        "centroids": centroids,
        "n_clusters": len(clusters),
        "vectorizer": vec,
        "X": X,
        "elapsed": time.perf_counter() - t0,
    }


def centroid_distance_outliers(
    clusterable_coords: np.ndarray,
    clusterable_cids: np.ndarray,
    clusterable_rows: np.ndarray,
    centroids: dict[int, np.ndarray],
    n_total: int,
    all_ids: list[str],
    *,
    extra_coords: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    """Top-decile by distance to the owning cluster centroid (the qmap rule).

    ``clusterable_cids[j]`` / ``clusterable_rows[j]`` describe row
    ``clusterable_coords[j]``: its cluster id and its index in the full bundle.
    Rows outside the clustered set, when supplied through ``extra_coords``
    (decision_id -> xy), measure their distance to the NEAREST cluster
    centroid, because they have no owner; they compete for the same decile
    budget.  The budget is ``max(1, n_total // 10)`` over all rendered points,
    exactly as qmap applies it over the rendered set.
    """
    dists = np.full(n_total, np.inf, dtype=float)
    for j in range(len(clusterable_cids)):
        cid = int(clusterable_cids[j])
        i = int(clusterable_rows[j])
        if cid in centroids:
            dists[i] = float(np.linalg.norm(clusterable_coords[j] - centroids[cid]))
    if extra_coords:
        pos = {did: i for i, did in enumerate(all_ids)}
        for did, xy in extra_coords.items():
            dists[pos[did]] = min(
                (float(np.linalg.norm(xy - c)) for c in centroids.values()),
                default=0.0,
            )
    flags = np.zeros(n_total, dtype=bool)
    if n_total >= 10:
        order = sorted(range(n_total), key=lambda i: (-dists[i], str(all_ids[i])))
        for i in order[: max(1, n_total // 10)]:
            flags[i] = True
    return flags
