"""Query-conditioned clustering + deterministic 2D projection for the map.

Simple and correct beats sophisticated (lane directive): TF-IDF over the
retrieved set -> TruncatedSVD(2) with fixed random_state -> KMeans with k
chosen from set size -> top-term cluster labels -> centroid-distance outliers.
Citation edges: shared BGE/BGG reference patterns (e.g. 'BGE 130 III 1').
"""
from __future__ import annotations

import re

import numpy as np

CIT_RE = re.compile(r"\bBGE\s+\d+\s+[IVX]+\s+\d+|\bATF\s+\d+\s+[IVX]+\s+\d+", re.IGNORECASE)

# Function words in DE/FR/IT so cluster labels show content terms, not language.
STOPWORDS = frozenset("""
der die das und und der des den dem ein eine einer eines einem einen auch als
bei beim beim nach noch nur oder oder sehr vom von vor zum zur über für mit
sich sie sind ist war wird werden wurde wurden haben hat hatte hatten aus auf
an am im ins alle oder oder aber doch denn oder oder oder oder oder oder
le la les de des du de la un une des est sont et en dans que qui pour pas sur
plus par au aux il ils elle elles nous vous leur leurs son sa ses ce cette ces
dans en est que ne pas se plus tout tous toute toutes dont comme avait avec
di del della dello della che non una uno dei degli delle dal allo alla al ai
agli sul sulla per con come più sono era stato stata hanno aveva hanno perché
dei dal nel sul del cui alle quale quali questo questa questi queste anche tra
fra molto può possono deve devono essere stato ogni dove quando senza sopra
sotto dopo prima dopo mentre fino solo anche molto tale tali quale
the and for are with his her its from that this have has had were was will
bundesgericht tribunal tribunale federale federal recours beschwerde ricorso
arrêt urteil sentenza entscheid entscheidung considérant erwägung considerando
janvier février mars avril mai juin juillet août septembre octobre novembre
décembre januar februar märz april mai juni juli august september oktober
november dezember gennaio febbraio marzo aprile maggio giugno luglio agosto
settembre ottobre novembre dicembre art gesetz loi legge ordonnance verordnung
ordinanza code civile straf zivil droit recht diritto case law contra contre
""".split())


def find_citations(text: str) -> list[str]:
    return sorted(set(CIT_RE.findall(text or "")))[:20]


def build_map(ranked: list[dict], n_clusters: int = 0) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (decisions_with_xy, clusters, relations). Mutates copies."""
    from sklearn.cluster import KMeans
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    n = len(ranked)
    texts = [((d.get("full_text", "") or "")[:6000]) for d in ranked]
    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[^\W\d_]{2,}\b", lowercase=True,
                                 sublinear_tf=True, max_features=5000, max_df=0.9, min_df=1,
                                 stop_words=list(STOPWORDS))
    X = vectorizer.fit_transform(texts)
    dim = min(2, max(1, X.shape[1] - 0 if X.shape[1] > 1 else 1))
    if X.shape[1] >= 2:
        coords = TruncatedSVD(n_components=2, random_state=42).fit_transform(X)
    else:  # degenerate: place on a line deterministically
        coords = np.column_stack([np.linspace(-1, 1, n), np.zeros(n)])
    # normalize to [-1, 1]
    span = np.abs(coords).max() or 1.0
    coords = coords / span

    if n_clusters <= 0:
        n_clusters = max(2, min(8, n // 12 + 1)) if n >= 6 else 1
    n_clusters = max(1, min(n_clusters, n))
    if n_clusters > 1:
        labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(X)
    else:
        labels = np.zeros(n, dtype=int)

    terms = np.array(vectorizer.get_feature_names_out())
    centroids = []
    for c in range(n_clusters):
        idx = np.where(labels == c)[0]
        if len(idx) == 0:
            continue
        mean = np.asarray(X[idx].mean(axis=0)).ravel()
        top = terms[np.argsort(-mean)[:5]]
        centroids.append((c, idx, ", ".join(top)))

    # outlier = farthest from own cluster centroid in 2D
    decisions = []
    for i, d in enumerate(ranked):
        c = int(labels[i])
        members = np.where(labels == c)[0]
        center = coords[members].mean(axis=0)
        dist = float(np.linalg.norm(coords[i] - center))
        decisions.append({**d, "x": round(float(coords[i, 0]), 5),
                          "y": round(float(coords[i, 1]), 5),
                          "cluster_id": c, "_outlier_dist": dist})

    clusters = []
    for c, idx, label in centroids:
        dists = sorted((decisions[i]["_outlier_dist"], i) for i in idx)
        clusters.append({
            "cluster_id": c,
            "label": label,
            "size": len(idx),
            "member_ids": [decisions[i]["decision_id"] for i in idx][:50],
        })
    # mark top-10% most distant as outliers
    if n >= 10:
        order = sorted(range(n), key=lambda i: -decisions[i]["_outlier_dist"])
        for i in order[: max(1, n // 10)]:
            decisions[i]["is_outlier"] = True
    for d in decisions:
        d.setdefault("is_outlier", False)
        d.pop("_outlier_dist", None)

    # citation relations: shared BGE/ATF references between retrieved decisions
    cit_of = {d["decision_id"]: set(find_citations(d.get("full_text", "")[:20000])) for d in ranked}
    relations = []
    dlist = list(ranked)
    for i in range(len(dlist)):
        for j in range(i + 1, len(dlist)):
            shared = sorted(cit_of[dlist[i]["decision_id"]] & cit_of[dlist[j]["decision_id"]])
            if shared:
                relations.append({
                    "source": dlist[i]["decision_id"],
                    "target": dlist[j]["decision_id"],
                    "kind": "shared_citation",
                    "shared": shared[:5],
                })
    return decisions, clusters, relations[:500]
