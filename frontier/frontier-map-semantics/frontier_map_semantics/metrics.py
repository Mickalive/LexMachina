"""Frozen-rule metric computation over one shipped bundle.

Every function reads the SHIPPED bundle fields except the ablation, which
recomputes geometry with the vendored pipeline (textgeo.build_geometry).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import pairwise_distances

from .textgeo import (CIT_RE, CITATION_FRAGMENT_TOKENS, STOPWORDS, body,
                      build_geometry, find_citations, is_unhydrated)


def _cosine_dist(X):
    D = pairwise_distances(X, metric="cosine")
    return np.nan_to_num(np.asarray(D, dtype=float), nan=1.0, posinf=1.0, neginf=0.0)


def _euclid(coords):
    d = pairwise_distances(np.asarray(coords, dtype=float), metric="euclidean")
    return np.asarray(d, dtype=float)


def _spearman(a, b):
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if a.size < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan"), True
    r = spearmanr(a, b).statistic
    return float(r), False


def tfidf_of(texts):
    from .textgeo import fit_tfidf

    return fit_tfidf(texts)


def coherence(decisions, clusters, query_lang, lexicon):
    base_lang = sum(1 for d in decisions if d.get("language") == query_lang) / max(1, len(decisions))
    bodies = [body(d).casefold() for d in decisions]
    base_term = sum(1 for t in bodies if any(q in t for q in lexicon)) / max(1, len(bodies))
    per_cluster = []
    for c in clusters:
        members = [d for d in decisions if int(d.get("cluster_id")) == int(c["cluster_id"])]
        n = len(members)
        lang_share = sum(1 for d in members if d.get("language") == query_lang) / max(1, n)
        tb = [body(d).casefold() for d in members]
        term_share = sum(1 for t in tb if any(q in t for q in lexicon)) / max(1, n)
        unhyd = sum(1 for d in members if is_unhydrated(d)) / max(1, n)
        per_cluster.append({"cluster_id": int(c["cluster_id"]), "size": n,
                            "query_lang_share": lang_share, "query_term_share": term_share,
                            "unhydrated_share": unhyd, "label": str(c.get("label") or "")})
    dom = max(per_cluster, key=lambda p: p["size"]) if per_cluster else None
    return {"bundle_lang_baseline": base_lang, "bundle_term_baseline": base_term,
            "per_cluster": per_cluster, "dominant": dom}


def projection(decisions, X, query_text):
    coords = np.array([[float(d.get("x", 0)), float(d.get("y", 0))] for d in decisions])
    cos_d = _cosine_dist(X)
    euc_d = _euclid(coords)
    iu = np.triu_indices(len(decisions), k=1)
    rho, deg1 = _spearman(cos_d[iu], euc_d[iu])
    # kNN@10 overlap
    n = len(decisions)
    k = min(10, n - 1)
    overlaps = []
    for i in range(n):
        nn_e = np.argsort(euc_d[i])[1:k + 1]
        nn_c = np.argsort(cos_d[i])[1:k + 1]
        overlaps.append(len(set(nn_e.tolist()) & set(nn_c.tolist())) / max(1, k))
    knn = float(np.mean(overlaps)) if overlaps else float("nan")
    # rank fidelity: distance to query vector vs retrieval rank
    from .textgeo import fit_tfidf  # noqa
    vec = getattr(projection, "_vec", None)
    # query vector in the same fitted space: use stored vectorizer when available
    Q = getattr(projection, "_query_vec", None)
    ranks = np.array([int(d.get("rank", 0)) for d in decisions], dtype=float)
    if Q is None:
        rho_r, deg2 = float("nan"), True
        qnnz = 0
    else:
        from sklearn.metrics.pairwise import cosine_distances

        qd = np.asarray(cosine_distances(X, Q.reshape(1, -1))).ravel()
        qd = np.nan_to_num(qd, nan=1.0)
        rho_r, deg2 = _spearman(qd, ranks)
        qnnz = int(Q.getnnz())
    return {"spearman_2d_vs_cosine": rho, "degenerate_2d": bool(deg1),
            "knn10_overlap": knn, "rank_rho": rho_r,
            "rank_degenerate": bool(deg2), "query_vector_nnz": qnnz}


def structure(decisions, X, clusters):
    n = len(decisions)
    sizes = [sum(1 for d in decisions if int(d.get("cluster_id")) == int(c["cluster_id"])) for c in clusters]
    largest = max(sizes) if sizes else 0
    cos_d = _cosine_dist(X)
    cid = np.array([int(d.get("cluster_id")) for d in decisions])
    intra, inter = [], []
    for i in range(n):
        for j in range(i + 1, n):
            (intra if cid[i] == cid[j] else inter).append(cos_d[i, j])
    ratio = (float(np.mean(intra)) / float(np.mean(inter))) if intra and inter and np.mean(inter) else float("nan")
    return {"largest_share": largest / max(1, n), "largest_n": int(largest),
            "sep_ratio": float(ratio)}


def labels_metric(clusters):
    term_sets = []
    pooled = []
    for c in clusters:
        terms = [t.strip().lower() for t in str(c.get("label") or "").split(",") if t.strip()]
        term_sets.append(set(terms))
        pooled.extend(terms)
    content = [t for t in pooled if t not in STOPWORDS and not CIT_RE.search(t)
               and t not in CITATION_FRAGMENT_TOKENS]
    frac = len(content) / max(1, len(pooled))
    jacs = []
    for i in range(len(term_sets)):
        for j in range(i + 1, len(term_sets)):
            u = term_sets[i] | term_sets[j]
            jacs.append(len(term_sets[i] & term_sets[j]) / len(u) if u else 1.0)
    return {"content_fraction": frac, "mean_pairwise_jaccard": float(np.mean(jacs)) if jacs else 0.0,
            "distinct_labels": len({str(c.get('label') or '') for c in clusters}),
            "n_clusters": len(clusters)}


def outliers_metric(decisions):
    ids = [d.get("decision_id") for d in decisions]
    cit = {d.get("decision_id"): set(find_citations(body(d)[:20000])) for d in decisions}
    deg = []
    for i, did in enumerate(ids):
        s = 0
        for j, did2 in enumerate(ids):
            if i != j and (cit[did] & cit[did2]):
                s += 1
        deg.append(s)
    deg = np.array(deg, dtype=float)
    flags = np.array([bool(d.get("is_outlier")) for d in decisions])
    ranks = np.array([int(d.get("rank", 0)) for d in decisions], dtype=float)
    degenerate = bool(deg.sum() == 0)
    n = len(decisions)
    k = max(1, n // 10)
    tail_idx = set(np.argsort(ranks)[-k:].tolist()) if n else set()
    out_idx = set(np.where(flags)[0].tolist())
    union = out_idx | tail_idx
    jacc = len(out_idx & tail_idx) / len(union) if union else 1.0
    return {"outlier_mean_degree": float(deg[flags].mean()) if flags.any() else float("nan"),
            "rest_mean_degree": float(deg[~flags].mean()) if (~flags).any() else float("nan"),
            "outlier_mean_rank": float(ranks[flags].mean()) if flags.any() else float("nan"),
            "rest_mean_rank": float(ranks[~flags].mean()) if (~flags).any() else float("nan"),
            "tail_jaccard": float(jacc), "n_outliers": int(flags.sum()),
            "citation_graph_degenerate": degenerate}


def relations_metric(bundle):
    rels = bundle.get("relations", []) or []
    ids = {d.get("decision_id") for d in bundle.get("decisions", [])}
    kinds, dirs, confs = {}, {}, []
    missing = 0
    nokind = 0
    for r in rels:
        dirs[str(r.get("direction"))] = dirs.get(str(r.get("direction")), 0) + 1
        try:
            confs.append(float(r.get("confidence")))
        except (TypeError, ValueError):
            pass
        if r.get("kind") is None:
            nokind += 1
        if r.get("source") not in ids or r.get("target") not in ids:
            missing += 1
    # kind histogram (single pass)
    kinds = {}
    for r in rels:
        kinds[str(r.get("kind"))] = kinds.get(str(r.get("kind")), 0) + 1
    endpoint_ok = (len(rels) - missing) / len(rels) if rels else 0.0
    return {"edge_count": len(rels), "kinds": kinds, "directions": dirs,
            "mean_confidence": float(np.mean(confs)) if confs else float("nan"),
            "endpoint_ok_fraction": endpoint_ok, "edges_missing_endpoint": missing,
            "edges_without_kind": nokind}


def verdicts(bundle, rules, X, query_vec):
    """Apply frozen bars. Returns dict criterion -> {value, pass}."""
    decisions = bundle["decisions"]
    clusters = bundle.get("clusters", []) or []
    qlang = rules["query_language"]
    lex = rules["query_term_lexicon"]
    coh = coherence(decisions, clusters, qlang, lex)
    dom = coh["dominant"]
    base = coh["bundle_lang_baseline"]
    lang_bar = max(0.25, 0.5 * base)
    v_lang = dom["query_lang_share"] >= lang_bar if dom else False
    v_term = dom["query_term_share"] >= coh["bundle_term_baseline"] if dom else False
    projection._query_vec = query_vec
    proj = projection(decisions, X, bundle.get("query", ""))
    st = structure(decisions, X, clusters)
    lab = labels_metric(clusters)
    out = outliers_metric(decisions)
    rel = relations_metric(bundle)
    V = {}
    V["COHERENCE_QUERY_LANG"] = {"value": dom["query_lang_share"] if dom else 0.0,
                                 "bar": lang_bar, "pass": bool(v_lang), "baseline": base}
    V["COHERENCE_QUERY_TERM"] = {"value": dom["query_term_share"] if dom else 0.0,
                                 "bar": coh["bundle_term_baseline"], "pass": bool(v_term)}
    V["PROJ_RANK"] = {"value": proj["rank_rho"], "bar": 0.30,
                      "pass": bool(not proj["rank_degenerate"] and proj["rank_rho"] >= 0.30),
                      "degenerate": proj["rank_degenerate"]}
    V["PROJ_SPEARMAN"] = {"value": proj["spearman_2d_vs_cosine"], "bar": 0.50,
                          "pass": bool(not proj["degenerate_2d"] and proj["spearman_2d_vs_cosine"] >= 0.50)}
    V["PROJ_KNN10"] = {"value": proj["knn10_overlap"], "bar": 0.40,
                       "pass": bool(proj["knn10_overlap"] >= 0.40)}
    V["STRUCTURE_LARGEST"] = {"value": st["largest_share"], "bar": 0.60,
                              "pass": bool(st["largest_share"] <= 0.60)}
    V["STRUCTURE_SEP"] = {"value": st["sep_ratio"], "bar": 0.90,
                          "pass": bool(not np.isnan(st["sep_ratio"]) and st["sep_ratio"] < 0.90)}
    V["LABEL_CONTENT_FRACTION"] = {"value": lab["content_fraction"], "bar": 0.80,
                                   "pass": bool(lab["content_fraction"] >= 0.80)}
    V["LABEL_JACCARD"] = {"value": lab["mean_pairwise_jaccard"], "bar": 0.50,
                          "pass": bool(lab["distinct_labels"] == lab["n_clusters"]
                                       and lab["mean_pairwise_jaccard"] <= 0.50),
                          "distinct": lab["distinct_labels"], "n_clusters": lab["n_clusters"]}
    V["OUTLIER_VALIDITY"] = {"value": [out["outlier_mean_degree"], out["rest_mean_degree"]],
                             "pass": bool(not out["citation_graph_degenerate"]
                                          and out["outlier_mean_degree"] < out["rest_mean_degree"]
                                          and out["tail_jaccard"] < 1.0),
                             "degenerate": out["citation_graph_degenerate"],
                             "tail_jaccard": out["tail_jaccard"]}
    V["RELATIONS"] = {"value": rel["edge_count"], "bar": 10,
                      "pass": bool(rel["edge_count"] >= 10 and rel["endpoint_ok_fraction"] >= 0.90
                                   and rel["edges_without_kind"] == 0),
                      "endpoint_ok": rel["endpoint_ok_fraction"]}
    detail = {"coherence": coh, "projection": proj, "structure": st, "labels": lab,
              "outliers": out, "relations": rel}
    return V, detail


def ablate(bundle, rules):
    """Decisive ablation: recompute geometry on hydrated-only rows, side by side."""
    decisions = bundle["decisions"]
    mask = np.array([not is_unhydrated(d) for d in decisions])
    texts_all = [body(d)[:6000] for d in decisions]
    ids_all = [d.get("decision_id") for d in decisions]
    if not any(t.strip() for t in texts_all):
        texts_all = [str(i) for i in ids_all]
    g_all = build_geometry(texts_all, ids_all)
    hyd_idx = np.where(mask)[0]
    hyd_texts = [texts_all[i] for i in hyd_idx]
    hyd_ids = [ids_all[i] for i in hyd_idx]
    if hyd_texts and not any(t.strip() for t in hyd_texts):
        hyd_texts = [str(i) for i in hyd_ids]
    g_hyd = build_geometry(hyd_texts, hyd_ids) if hyd_texts else None
    # shipped dominant cluster (sizes from the cluster record; member_ids in the
    # bundle are capped at 50, so membership comes from row assignment)
    clusters = bundle.get("clusters", []) or []
    dom = max(clusters, key=lambda c: int(c.get("size", 0))) if clusters else None
    dom_cid = int(dom["cluster_id"]) if dom else None
    dom_ids = {d.get("decision_id") for d in decisions if int(d.get("cluster_id")) == dom_cid} if dom else set()
    dom_unhyd = sum(1 for d in decisions if d.get("decision_id") in dom_ids and is_unhydrated(d))
    dom_frac_unhyd = dom_unhyd / max(1, len(dom_ids))
    shipped_share = (int(dom.get("size", 0)) / max(1, len(decisions))) if dom else 0.0
    hyd_share = None
    jacc = None
    if g_hyd:
        sizes = {}
        for c in g_hyd["clusters"]:
            sizes[c["cluster_id"]] = len(c["member_ids"])
        big = max(g_hyd["clusters"], key=lambda c: len(c["member_ids"]))
        hyd_share = len(big["member_ids"]) / max(1, len(hyd_ids))
        big_ids = set(big["member_ids"])
        dom_hyd_ids = {i for i in dom_ids if i in set(hyd_ids)}
        union = big_ids | dom_hyd_ids
        jacc = len(big_ids & dom_hyd_ids) / len(union) if union else 1.0
    artifact = bool(dom_frac_unhyd >= 0.40 and (
        (hyd_share is not None and abs(shipped_share - hyd_share) >= 0.10) or (jacc is not None and jacc < 0.5)))
    # side-by-side numbers: recompute coherence/sep/proj on hydrated subset with recomputed coords
    side = {"predicate_used": "detail_status != 'search_hit'",
            "predicate_note": ("charter-equivalence measured FALSE on gate material: full_text_status=='lazy' "
                               "on 100% of rows incl. search_hits with KBs of body; language==null covers all "
                               "pending rows plus 0-10 search_hit rows with real bodies; pending-row bodies average "
                               "~10 chars (decision id only). Harness defect fixed pre-run; RULES bars unchanged."),
            "n_all": len(decisions), "n_hydrated": int(mask.sum()),
            "shipped_largest_share": shipped_share,
            "hydrated_largest_share": hyd_share,
            "dominant_member_jaccard": jacc,
            "dominant_unhydrated_fraction": dom_frac_unhyd,
            "recompute_all_largest_share": max(len(c["member_ids"]) for c in g_all["clusters"]) / max(1, len(decisions)),
            "recompute_all_time_s": g_all["elapsed"],
            "hydrated_time_s": g_hyd["elapsed"] if g_hyd else None,
            "ARTIFACT": artifact}
    return side, g_all, g_hyd
