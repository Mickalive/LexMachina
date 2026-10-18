"""Deterministic query-conditioned map over one retrieved decision set."""
from __future__ import annotations

import html
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
loi legge ordonnance verordnung ordinanza code droit recht diritto mark regeste regesto consid\n""".split())


def find_citations(text: str) -> list[str]:
    return sorted(set(CIT_RE.findall(text or "")))[:20]


def _body(d: dict) -> str:
    text = str(d.get("full_text") or d.get("regeste") or d.get("snippet")
               or d.get("title") or d.get("citation") or "")
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def _canonicalise_axes(coords: np.ndarray) -> np.ndarray:
    out = np.array(coords, dtype=float, copy=True)
    for axis in range(out.shape[1]):
        col = out[:, axis]
        if len(col):
            anchor = int(np.argmax(np.abs(col)))
            if col[anchor] < 0:
                out[:, axis] *= -1
    return out


class MapModel:
    """A fitted query-conditioned projection that later decisions can join.

    The progressive product path renders a map from the first retrieved page and
    then patches in the rest of the retrieval.  Refitting TF-IDF + SVD + KMeans
    on the larger set would silently move points the researcher already looked
    at, so the projection is fitted **once** and later decisions are projected
    into that same space and attached to their nearest existing cluster.

    Fitting once also makes expansion cheap: new decisions cost one vectorizer
    transform and one SVD transform, not a full refit.
    """

    __slots__ = (
        "vectorizer", "svd", "scale", "coords", "cluster_ids", "centroids",
        "labels", "n_clusters", "decision_ids", "outliers",
    )

    def __init__(self, vectorizer, svd, scale: float, coords, cluster_ids,
                 centroids, labels, n_clusters: int, decision_ids, outliers=None):
        self.vectorizer = vectorizer
        self.svd = svd
        self.scale = scale
        self.coords = coords
        self.cluster_ids = cluster_ids
        self.centroids = centroids
        self.labels = labels
        self.n_clusters = n_clusters
        self.decision_ids = decision_ids
        self.outliers = dict(outliers or {})


def fit_map_model(ranked: list[dict], n_clusters: int = 0) -> MapModel | None:
    """Fit the projection/clusters for ``ranked`` and keep them reusable."""
    decisions, clusters, _relations = build_map(ranked, n_clusters=n_clusters)
    if not decisions:
        return None
    coords = np.array([[d["x"], d["y"]] for d in decisions], dtype=float)
    centroids = {}
    for c in clusters:
        pts = np.array(
            [[d["x"], d["y"]] for d in decisions if int(d["cluster_id"]) == int(c["cluster_id"])],
            dtype=float,
        )
        if len(pts):
            centroids[int(c["cluster_id"])] = pts.mean(axis=0)
    return MapModel(
        vectorizer=_LAST_FIT_VECTORIZER[0],
        svd=_LAST_FIT_SVD[0],
        scale=_LAST_FIT_SCALE[0],
        coords=coords,
        cluster_ids=np.array([int(d["cluster_id"]) for d in decisions], dtype=int),
        centroids=centroids,
        labels={int(c["cluster_id"]): str(c.get("label") or "") for c in clusters},
        n_clusters=len(clusters),
        decision_ids=[d["decision_id"] for d in decisions],
        outliers={d["decision_id"]: bool(d.get("is_outlier")) for d in decisions},
    )


def project_into_model(model: MapModel, new_ranked: list[dict]) -> list[dict]:
    """Project new decisions into an existing map and attach a cluster id.

    Returns copies of ``new_ranked`` with ``x``, ``y`` and ``cluster_id`` set.
    Decisions whose text is entirely empty still receive the decision id as a
    pseudo-term, exactly as ``build_map`` does, so they are never dropped.
    """
    if not new_ranked:
        return []
    texts = [_body(d)[:6000] for d in new_ranked]
    if not any(t.strip() for t in texts):
        texts = [str(d.get("decision_id") or i) for i, d in enumerate(new_ranked)]
    X = model.vectorizer.transform(texts)
    if model.svd is not None and X.shape[1] >= 2:
        coords = model.svd.transform(X)
    else:
        coords = np.column_stack([np.linspace(-1, 1, len(texts)), np.zeros(len(texts))])
    coords = np.asarray(coords, dtype=float) / (model.scale or 1.0)
    # The rendered map lives in [-1, 1] and the client maps it straight to
    # pixels.  A decision that projects outside that box is clipped rather than
    # rescaled, because rescaling would move points the researcher already saw.
    coords = np.clip(coords, -1.0, 1.0)

    out = []
    for i, d in enumerate(new_ranked):
        point = coords[i]
        cid = 0
        if model.centroids:
            cid = int(min(
                model.centroids,
                key=lambda k: (float(np.linalg.norm(point - model.centroids[k])), k),
            ))
        out.append({
            **d,
            "x": round(float(point[0]), 4),
            "y": round(float(point[1]), 4),
            "cluster_id": cid,
        })
    return out


def build_map(ranked: list[dict], n_clusters: int = 0, model: "MapModel | None" = None
              ) -> tuple[list[dict], list[dict], list[dict]]:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    n = len(ranked)
    if n == 0:
        return [], [], []
    if model is not None:
        return _build_map_with_model(ranked, model)

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

    svd = None
    if X.shape[1] >= 2 and n >= 2:
        svd = TruncatedSVD(n_components=2, random_state=42)
        coords = svd.fit_transform(X)
        coords = _canonicalise_axes(coords)
    else:
        coords = np.column_stack([np.linspace(-1, 1, n), np.zeros(n)])
    fit_scale = float(np.abs(coords).max()) or 1.0
    coords = coords / fit_scale

    if n_clusters <= 0:
        n_clusters = max(2, min(8, n // 12 + 1)) if n >= 6 else 1
    n_clusters = max(1, min(n_clusters, n))
    raw_labels = (
        KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(X)
        if n_clusters > 1 else np.zeros(n, dtype=int)
    )

    terms = [str(t) for t in vectorizer.get_feature_names_out()]
    meta = []
    for old in range(n_clusters):
        idx = np.where(raw_labels == old)[0]
        if len(idx) == 0:
            continue
        mean = np.asarray(X[idx].mean(axis=0)).ravel()
        label = ", ".join(label_terms(mean, terms))
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

    # Remember the fitted artefacts so progressive expansion can project later
    # decisions into this exact space instead of refitting and moving points.
    _LAST_FIT_VECTORIZER[0] = vectorizer
    _LAST_FIT_SVD[0] = svd
    _LAST_FIT_SCALE[0] = fit_scale

    return _finalise(ranked, decisions, clusters)


#: Artefacts of the most recent ``build_map`` fit (``fit_map_model`` reads them).
_LAST_FIT_VECTORIZER = [None]
_LAST_FIT_SVD = [None]
_LAST_FIT_SCALE = [1.0]


def _finalise(ranked: list[dict], decisions: list[dict], clusters: list[dict]
              ) -> tuple[list[dict], list[dict], list[dict]]:
    """Outlier flags + shared-citation relations over an already-projected set."""
    n = len(decisions)
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

    return decisions, clusters, shared_citation_relations(ranked)


def shared_citation_relations(ranked: list[dict], limit: int = 500) -> list[dict]:
    """Pairs of retrieved decisions that reference the same authority.

    Extracted from :func:`_finalise` so the map builder and the post-hydration
    refresh in ``enrich`` compute edges by *exactly* one rule.  At map-build time
    the input rows are pre-hydration, so this usually finds nothing; after the
    evidence subset is hydrated it can find real edges, which is why it is
    callable twice against the same bundle.
    """
    ranked = list(ranked or [])
    cit_of = {d["decision_id"]: set(find_citations(_body(d)[:20000])) for d in ranked}
    ids = [d["decision_id"] for d in ranked]
    relations = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            shared = sorted(cit_of[ids[i]] & cit_of[ids[j]])
            if shared:
                relations.append({
                    "source": ids[i],
                    "target": ids[j],
                    "kind": "shared_citation",
                    "shared": shared[:5],
                })
    return relations[:limit]


#: Cluster-label term means are rounded to this many decimals before ranking, and
#: only terms that actually occur in the cluster are eligible.
#:
#: Audit advisory F2 of cycle 38779139471: the committed bundle's sha256 was not
#: reproducible outside the environment that generated it — the same 154 decision
#: rows produced two different label orders elsewhere.  Root cause, measured on
#: the claim bundle rather than assumed: for a cluster of 1-5 decisions only a
#: handful of the 5000-vocabulary terms have a non-zero mean, so the 4th/5th label
#: slots were filled from *thousands of exactly tied zero-mean terms*, i.e. from
#: ``argsort``'s internal ordering rather than from the data.  Eligibility
#: (mean > 0) makes those slots meaningful, and ranking the remainder by
#: ``(-round(mean, LABEL_MEAN_DECIMALS), term)`` makes the label a pure function
#: of the cluster's text.
LABEL_MEAN_DECIMALS = 9
LABEL_TOP_K = 5


def label_terms(mean, terms, top_k: int = LABEL_TOP_K) -> list[str]:
    """The terms that explain one cluster, in a reproducible order.

    Shared by the initial fit (:func:`build_map`) and by the recompute-on-merge
    path (:func:`_cluster_label`), which previously ranked terms independently
    and could therefore disagree about the same cluster.
    """
    mean = np.asarray(mean, dtype=float).ravel()
    order = sorted(
        (i for i in range(len(terms)) if mean[i] > 0.0),
        key=lambda i: (-round(float(mean[i]), LABEL_MEAN_DECIMALS), str(terms[i])),
    )
    return [str(terms[i]) for i in order[:top_k]]


def _cluster_label(model: MapModel, members: list[dict], top_k: int = LABEL_TOP_K) -> str:
    """Top TF-IDF terms of a cluster's members, in the fitted vectorizer space.

    Recomputed from the merged membership whenever decisions are added: a label
    explains *why a group exists*, and more members are better evidence for it.
    The cluster id stays the same, so nothing the researcher already read moves.

    Only terms present in the cluster are eligible, and the order is
    ``(-round(mean, LABEL_MEAN_DECIMALS), term)`` — deterministic across
    environments.  Note the scope: that fixes the *label ordering*, which was
    the defect audit F2 of cycle 38779139471 found; it is not what makes the
    artifact reproducible.  Artifact identity is
    ``product/replay_bundle.py::content_sha256``, which since run 38789874982
    also excludes the machine's absolute cache root and is verified at two
    different checkout paths.  A cluster with fewer than ``top_k`` present terms
    is labelled with the terms it actually has rather than padded with absent
    ones.
    """
    if not members or model.vectorizer is None:
        return ""
    try:
        X = model.vectorizer.transform([_body(d)[:6000] for d in members])
        mean = np.asarray(X.mean(axis=0)).ravel()
        terms = [str(t) for t in model.vectorizer.get_feature_names_out()]
        return ", ".join(label_terms(mean, terms, top_k))
    except ValueError:  # empty vocabulary (e.g. every member is empty text)
        return ""


def _build_map_with_model(ranked: list[dict], model: MapModel
                          ) -> tuple[list[dict], list[dict], list[dict]]:
    """Map for ``ranked`` reusing an existing projection.

    Decisions the model already placed keep their coordinates and cluster id
    byte-for-byte (already-rendered points never move); new decisions are
    projected into the same space and attached to the nearest existing cluster.
    Cluster labels are recomputed from the merged membership, because more
    evidence for a group is better evidence, not a move.
    """
    n = len(ranked)
    if n == 0:
        return [], [], []
    frozen = {did: i for i, did in enumerate(model.decision_ids)}
    known = [(i, d) for i, d in enumerate(ranked) if d.get("decision_id") in frozen]
    fresh = [(i, d) for i, d in enumerate(ranked) if d.get("decision_id") not in frozen]
    projected = {d["decision_id"]: (p["x"], p["y"], p["cluster_id"])
                 for d, p in zip([d for _i, d in fresh],
                                 project_into_model(model, [d for _i, d in fresh]))}

    coords = np.zeros((n, 2), dtype=float)
    cluster_of = np.zeros(n, dtype=int)
    for i, d in enumerate(ranked):
        did = d.get("decision_id")
        if did in frozen:
            point = model.coords[frozen[did]]
            coords[i] = (float(point[0]), float(point[1]))
            cluster_of[i] = int(model.cluster_ids[frozen[did]])
        else:
            x, y, c = projected.get(did, (0.0, 0.0, 0))
            coords[i] = (float(x), float(y))
            cluster_of[i] = int(c)

    cluster_ids = sorted({int(c) for c in cluster_of})
    clusters = []
    for cid in cluster_ids:
        idx = np.where(cluster_of == cid)[0]
        clusters.append({
            "cluster_id": int(cid),
            "label": _cluster_label(model, [ranked[i] for i in idx]) or f"Cluster {int(cid)}",
            "size": int(len(idx)),
            "member_ids": [ranked[i]["decision_id"] for i in idx][:50],
        })

    decisions = []
    for i, d in enumerate(ranked):
        members = np.where(cluster_of == int(cluster_of[i]))[0]
        center = coords[members].mean(axis=0)
        dist = float(np.linalg.norm(coords[i] - center))
        decisions.append({
            **d,
            "x": round(float(coords[i, 0]), 4),
            "y": round(float(coords[i, 1]), 4),
            "cluster_id": int(cluster_of[i]),
            "_outlier_dist": dist,
        })
    decisions, clusters, relations = _finalise(ranked, decisions, clusters)
    # Outlier status is a statement about the rendered map ("weakly connected
    # result worth inspecting"), so a point already shown as an outlier keeps
    # that status; only newly added points are scored.
    for d in decisions:
        did = d.get("decision_id")
        if did in frozen and did in model.outliers:
            d["is_outlier"] = bool(model.outliers[did])
    return decisions, clusters, relations
