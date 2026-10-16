"""Shared text/geometry primitives vendored from the accepted product map.

Provenance: equivalent of product/query/qmap.py at accepted head 1668181a
as mounted for run 38839351403 (/tmp/lex_accepted/core/product). Hyperparameters
are identical (vectorizer, SVD, KMeans, label rule, outlier rule) so the
ablation/alternative recomputes are comparable to the shipped geometry.
Primary verdict metrics always read the SHIPPED bundle fields (x/y/cluster/
label), which is what the human gate renders.
"""
from __future__ import annotations

import html
import re
import time

import numpy as np

CIT_RE = re.compile(r"\bBGE\s+\d+\s+[IVX]+\s+\d+|\bATF\s+\d+\s+[IVX]+\s+\d+", re.IGNORECASE)

STOPWORDS = frozenset("""
der die das und des den dem ein eine einer eines einem einen auch als bei nach noch nur oder vom von
vor zum zur über für mit sich sie sind ist war wird werden wurde wurden haben hat hatte aus auf an am
im ins aber doch denn le la les de des du un une est sont et en dans que qui pour pas sur plus par
au aux il ils elle elles nous vous leur son sa ses ce cette ces dont comme avec di del della dello
che non uno dei degli delle dal allo alla al ai agli sul sulla per con come più sono era stato stata
hanno aveva perché nel cui alle quale quali questo questa questi queste anche tra fra può possono
deve devono essere ogni dove quando senza sopra sotto dopo prima mentre the and for are with from
that this have has had were was will bundesgericht tribunal tribunale federale recours beschwerde
ricorso arrêt urteil sentenza entscheid entscheidung considérant erwägung considerando art gesetz
loi legge ordonnance verordnung ordinanza code droit recht diritto mark regeste regesto consid
""".split())

CITATION_FRAGMENT_TOKENS = frozenset({"bge", "atf"})

VECTORIZER_PARAMS = dict(
    token_pattern=r"(?u)\b[^\W\d_]{2,}\b",
    lowercase=True,
    sublinear_tf=True,
    max_features=5000,
    max_df=0.9,
    min_df=1,
)

BODY_TRUNCATE = 6000


def body(d: dict) -> str:
    text = str(d.get("full_text") or d.get("regeste") or d.get("snippet")
               or d.get("title") or d.get("citation") or "")
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def find_citations(text: str) -> list[str]:
    return sorted(set(CIT_RE.findall(text or "")))[:20]


def is_unhydrated(d: dict) -> bool:
    # MEASURED (gate bundles 38799024807, run 38839351403): full_text_status is
    # 'lazy' on 100% of rows including search_hits with 3-4.7KB bodies, so it
    # does NOT indicate an empty shell; language is null on all pending rows
    # PLUS 0-10 search_hit rows that carry real bodies. The shell predicate is
    # therefore detail_status != 'search_hit' (pending rows carry ~10-char
    # bodies: the decision id only). See report predicate_note.
    return d.get("detail_status") != "search_hit"


def fit_tfidf(texts: list[str]):
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(stop_words=list(STOPWORDS), **VECTORIZER_PARAMS)
    X = vec.fit_transform(texts)
    return vec, X


def project_svd(X, random_state: int = 42):
    from sklearn.decomposition import TruncatedSVD

    n = X.shape[0]
    if X.shape[1] >= 2 and n >= 2:
        svd = TruncatedSVD(n_components=2, random_state=random_state)
        coords = svd.fit_transform(X)
        for axis in range(coords.shape[1]):
            col = coords[:, axis]
            if len(col):
                anchor = int(np.argmax(np.abs(col)))
                if col[anchor] < 0:
                    coords[:, axis] *= -1
    else:
        svd = None
        coords = np.column_stack([np.linspace(-1, 1, n), np.zeros(n)])
    scale = float(np.abs(coords).max()) or 1.0
    return svd, np.asarray(coords, dtype=float) / scale, scale


def cluster_kmeans(X, n: int, random_state: int = 42):
    from sklearn.cluster import KMeans

    if n >= 6:
        n_clusters = max(2, min(8, n // 12 + 1))
    else:
        n_clusters = 1
    n_clusters = max(1, min(n_clusters, n))
    if n_clusters > 1:
        labels = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10).fit_predict(X)
    else:
        labels = np.zeros(n, dtype=int)
    return labels, n_clusters


def label_terms(mean, terms, top_k: int = 5) -> list[str]:
    mean = np.asarray(mean, dtype=float).ravel()
    order = sorted(
        (i for i in range(len(terms)) if mean[i] > 0.0),
        key=lambda i: (-round(float(mean[i]), 9), str(terms[i])),
    )
    return [str(terms[i]) for i in order[:top_k]]


def build_geometry(texts: list[str], ids: list[str], random_state: int = 42) -> dict:
    """Vendored qmap-equivalent fit. Returns coords, cluster ids, labels, timing."""
    t0 = time.perf_counter()
    n = len(texts)
    vec, X = fit_tfidf(texts)
    svd, coords, _scale = project_svd(X, random_state)
    raw, _k = cluster_kmeans(X, n, random_state)
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
        _o, _idx, label, _x, _y = [m for m in meta if m[0] == old][0]
        clusters.append({"cluster_id": new, "label": label or f"Cluster {new}",
                         "member_ids": [ids[i] for i in idx]})
    # outlier flags: top decile by centroid distance
    center_of = {}
    for c in clusters:
        pts = coords[[ids.index(m) for m in c["member_ids"]]]
        center_of[c["cluster_id"]] = pts.mean(axis=0)
    dists = np.array([float(np.linalg.norm(coords[i] - center_of[int(labels[i])])) for i in range(n)])
    is_out = np.zeros(n, dtype=bool)
    if n >= 10:
        order = sorted(range(n), key=lambda i: (-dists[i], str(ids[i])))
        for i in order[:max(1, n // 10)]:
            is_out[i] = True
    elapsed = time.perf_counter() - t0
    return {"coords": coords, "cluster_ids": labels, "clusters": clusters,
            "is_outlier": is_out, "elapsed": elapsed, "X": X, "vectorizer": vec}
