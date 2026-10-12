"""Deterministic query-conditioned map over one retrieved decision set."""
from __future__ import annotations

import re
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
loi legge ordonnance verordnung ordinanza code droit recht diritto
""".split())


def find_citations(text: str) -> list[str]:
    return sorted(set(CIT_RE.findall(text or "")))[:20]


def _body(d: dict) -> str:
    return str(d.get("full_text") or d.get("regeste") or d.get("snippet")
               or d.get("title") or d.get("citation") or "")


def _canonicalise_axes(coords: np.ndarray) -> np.ndarray:
    out = np.array(coords, dtype=float, copy=True)
    for axis in range(out.shape[1]):
        col = out[:, axis]
        if len(col):
            anchor = int(np.argmax(np.abs(col)))
            if col[anchor] < 0:
                out[:, axis] *= -1
    return out


def build_map(ranked: list[dict], n_clusters: int = 0) -> tuple[list[dict], list[dict], list[dict]]:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    n = len(ranked)
    if n == 0:
        return [], [], []

    texts = [_body(d)[:6000] for d in ranked]
    if not any(t.strip() for t in texts):
        texts = [str(d.get("decision_id") or i) for i, d in enumerate(ranked)]

    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b[^\W\d_]{2,}\b",
        lowercase=True,
        sublinear_tf=True,
        max_features=5000,
        max_df=0.9,
        min_df=1,
        stop_words=list(STOPWORDS),
    )
    X = vectorizer.fit_transform(texts)

    if X.shape[1] >= 2 and n >= 2:
        coords = TruncatedSVD(n_components=2, random_state=42).fit_transform(X)
        coords = _canonicalise_axes(coords)
    else:
        coords = np.column_stack([np.linspace(-1, 1, n), np.zeros(n)])
    coords = coords / (float(np.abs(coords).max()) or 1.0)

    if n_clusters <= 0:
        n_clusters = max(2, min(8, n // 12 + 1)) if n >= 6 else 1
    n_clusters = max(1, min(n_clusters, n))
    raw_labels = (
        KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(X)
        if n_clusters > 1 else np.zeros(n, dtype=int)
    )

    terms = np.array(vectorizer.get_feature_names_out())
    meta = []
    for old in range(n_clusters):
        idx = np.where(raw_labels == old)[0]
        if len(idx) == 0:
            continue
        mean = np.asarray(X[idx].mean(axis=0)).ravel()
        top = terms[np.argsort(-mean)[:5]]
        label = ", ".join(top)
        centroid = coords[idx].mean(axis=0)
        meta.append((old, idx, label, float(centroid[0]), float(centroid[1])))

    ordered = sorted(meta, key=lambda x: (x[2], round(x[3], 4), round(x[4], 4)))
    remap = {old: new for new, (old, *_rest) in enumerate(ordered)}
    labels = np.array([remap[int(x)] for x in raw_labels], dtype=int)

    decisions = []
    for i, d in enumerate(ranked):
        c = int(labels[i])
        members = np.where(labels == c)[0]
        center = coords[members].mean(axis=0)
        dist = float(np.linalg.norm(coords[i] - center))
        decisions.append({
            **d,
            "x": round(float(coords[i, 0]), 4),
            "y": round(float(coords[i, 1]), 4),
            "cluster_id": c,
            "_outlier_dist": dist,
        })

    meta_by_old = {old: (idx, label) for old, idx, label, _x, _y in meta}
    clusters = []
    for old, new in sorted(remap.items(), key=lambda kv: kv[1]):
        idx, label = meta_by_old[old]
        clusters.append({
            "cluster_id": new,
            "label": label or f"Cluster {new}",
            "size": len(idx),
            "member_ids": [ranked[i]["decision_id"] for i in idx][:50],
        })

    if n >= 10:
        order = sorted(
            range(n),
            key=lambda i: (-decisions[i]["_outlier_dist"], str(decisions[i]["decision_id"])),
        )
        for i in order[:max(1, n // 10)]:
            decisions[i]["is_outlier"] = True
    for d in decisions:
        d.setdefault("is_outlier", False)
        d.pop("_outlier_dist", None)

    cit_of = {d["decision_id"]: set(find_citations(_body(d)[:20000])) for d in ranked}
    relations = []
    for i in range(n):
        for j in range(i + 1, n):
            shared = sorted(cit_of[ranked[i]["decision_id"]] & cit_of[ranked[j]["decision_id"]])
            if shared:
                relations.append({
                    "source": ranked[i]["decision_id"],
                    "target": ranked[j]["decision_id"],
                    "kind": "shared_citation",
                    "shared": shared[:5],
                })
    return decisions, clusters, relations[:500]
