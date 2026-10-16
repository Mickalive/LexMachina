"""At most three named alternatives under the identical frozen rule (§9A < 2 s)."""
from __future__ import annotations

import time

import numpy as np

from .textgeo import (STOPWORDS, VECTORIZER_PARAMS, body, cluster_kmeans,
                      label_terms, project_svd)


def _clusters_from_labels(raw, coords, ids, X, terms):
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
        _o, _idx, label, _x, _y = [m for m in meta if m[0] == old][0]
        clusters.append({"cluster_id": new, "label": label or f"Cluster {new}",
                         "member_ids": [ids[i] for i in idx]})
    center_of = {}
    for c in clusters:
        pts = coords[[ids.index(m) for m in c["member_ids"]]]
        center_of[c["cluster_id"]] = pts.mean(axis=0)
    dists = np.array([float(np.linalg.norm(coords[i] - center_of[int(labels[i])])) for i in range(len(ids))])
    is_out = np.zeros(len(ids), dtype=bool)
    if len(ids) >= 10:
        order = sorted(range(len(ids)), key=lambda i: (-dists[i], str(ids[i])))
        for i in order[:max(1, len(ids) // 10)]:
            is_out[i] = True
    return labels, clusters, is_out


def _tfidf(texts, **kw):
    from sklearn.feature_extraction.text import TfidfVectorizer

    params = dict(VECTORIZER_PARAMS)
    params.update(kw)
    vec = TfidfVectorizer(stop_words=list(STOPWORDS), **params)
    return vec, vec.fit_transform(texts)


def alt_A1(texts, ids):
    """Drop un-hydrated rows already done by caller; identical pipeline otherwise."""
    from .textgeo import build_geometry

    t0 = time.perf_counter()
    g = build_geometry(texts, ids)
    g["elapsed"] = time.perf_counter() - t0
    return g


def alt_A2(texts, ids, langs):
    """Language-aware: per-language TF-IDF blocks concatenated, then SVD+KMeans.

    One vocabulary fitted per language group (on that group's texts); EVERY row
    is transformed through EACH group's vectorizer, so blocks share row order
    and hstack is valid. A row in another language simply yields a sparse block.
    """
    t0 = time.perf_counter()
    groups = {}
    for i, lg in enumerate(langs):
        groups.setdefault(lg or "null", []).append(i)
    vecs = {}
    for lg in sorted(groups):
        try:
            vecs[lg], _Xb = _tfidf([texts[i] for i in groups[lg]])
        except ValueError:
            continue  # group vocabulary pruned to nothing; skip its block
    if not vecs:
        raise ValueError("A2: every per-language vocabulary pruned to nothing")
    from scipy.sparse import hstack

    blocks = [vecs[lg].transform(texts) for lg in sorted(groups)]
    X = hstack(blocks, format="csr")
    terms = [f"{lg}::{t}" for lg in sorted(groups) for t in vecs[lg].get_feature_names_out()]
    _svd, coords, _s = project_svd(X)
    raw, _k = cluster_kmeans(X, len(ids))
    labels, clusters, is_out = _clusters_from_labels(raw, coords, ids, X, terms)
    return {"coords": coords, "cluster_ids": labels, "clusters": clusters,
            "is_outlier": is_out, "elapsed": time.perf_counter() - t0, "X": X}


def alt_A3(texts, ids):
    """Metric MDS on cosine distance instead of TruncatedSVD(2)."""
    t0 = time.perf_counter()
    from sklearn.manifold import MDS

    _v, X = _tfidf(texts)
    from sklearn.metrics import pairwise_distances

    D = np.nan_to_num(np.asarray(pairwise_distances(X, metric="cosine"), dtype=float), nan=1.0)
    coords = MDS(n_components=2, dissimilarity="precomputed", random_state=42,
                 normalized_stress="auto", init="random").fit_transform(D)
    scale = float(np.abs(coords).max()) or 1.0
    coords = coords / scale
    raw, _k = cluster_kmeans(X, len(ids))
    terms = [str(t) for t in _v.get_feature_names_out()]
    labels, clusters, is_out = _clusters_from_labels(raw, coords, ids, X, terms)
    return {"coords": coords, "cluster_ids": labels, "clusters": clusters,
            "is_outlier": is_out, "elapsed": time.perf_counter() - t0, "X": X}
