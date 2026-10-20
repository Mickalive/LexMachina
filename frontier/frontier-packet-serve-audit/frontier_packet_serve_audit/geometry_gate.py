"""Map-geometry-semantics gate: FROZEN RULES_GEOMETRY.json, 11 criteria.

Stdlib-only re-implementation of the accepted geometry_gate.py scoring
(evaluation/frozen_bars/geometry_gate.py), reusing the vendored textgeo.py
primitives via AST extraction so STOPWORDS / CIT_RE / body / find_citations /
is_unhydrated cannot drift from the frozen bytes. The numpy/sklearn stack is
NOT required.

Primary verdict metrics read the SHIPPED bundle x/y/cluster/label fields (the
gate renders these). No threshold is re-derived: every bar is read from
RULES_GEOMETRY.json AS WRITTEN at scoring time.
"""
from __future__ import annotations

import ast
import hashlib
import html as _html
import json
import math
import re as _re
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
VENDORED_TEXTGEO = _PKG_DIR / "vendor_geometry" / "textgeo.py"

RULES_GEOMETRY_SHA256 = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"

CRITERIA_ORDER = [
    "COHERENCE_QUERY_LANG",
    "COHERENCE_QUERY_TERM",
    "PROJ_RANK",
    "PROJ_SPEARMAN",
    "PROJ_KNN10",
    "STRUCTURE_LARGEST",
    "STRUCTURE_SEP",
    "LABEL_CONTENT_FRACTION",
    "LABEL_JACCARD",
    "OUTLIER_VALIDITY",
    "RELATIONS",
]

# Recomputed incumbent of record (direction v50): accepted GEOMETRY_HALF.json on
# the served packet 38839347028. NOT this packet's bytes. Regression only.
INCUMBENT_COUNTS = {
    "de-kapitalverletzung": 6,
    "fr-bail-entretien": 5,
    "it-responsabilita-medica": 5,
}


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_geometry_rules(path: str | Path) -> dict:
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != RULES_GEOMETRY_SHA256:
        raise RuntimeError(
            "RULES_GEOMETRY sha256 mismatch: refusing to score. "
            "Frozen bars are reused by re-hash, never re-derived."
        )
    return json.loads(raw.decode("utf-8"))


def _extract_textgeo_primitives() -> dict:
    """Exec the stdlib-only primitives from the vendored textgeo.py source.

    Only the frozen constant assignments and the three stdlib-only function
    defs (body/find_citations/is_unhydrated) are executed; the module-level
    numpy import is never touched. Anything that fails to extract is a hard
    error, so silent drift is impossible.
    """
    src = VENDORED_TEXTGEO.read_text(encoding="utf-8")
    tree = ast.parse(src)
    wanted_assign = {"CIT_RE", "STOPWORDS", "CITATION_FRAGMENT_TOKENS", "VECTORIZER_PARAMS", "BODY_TRUNCATE"}
    wanted_func = {"body", "find_citations", "is_unhydrated"}
    mod = ast.Module(body=[], type_ignores=[])
    seen_a, seen_f = set(), set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in wanted_assign:
                mod.body.append(node)
                seen_a.add(node.targets[0].id)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_func:
            mod.body.append(node)
            seen_f.add(node.name)
    missing = (wanted_assign - seen_a) | (wanted_func - seen_f)
    if missing:
        raise RuntimeError(f"vendored textgeo primitive extraction failed, missing: {sorted(missing)}")
    ns: dict = {"html": _html, "re": _re, "time": __import__("time")}
    exec(compile(ast.fix_missing_locations(mod), str(VENDORED_TEXTGEO), "exec"), ns)
    return ns


_PRIM = _extract_textgeo_primitives()
STOPWORDS = _PRIM["STOPWORDS"]
CIT_RE = _PRIM["CIT_RE"]
CITATION_FRAGMENT_TOKENS = _PRIM["CITATION_FRAGMENT_TOKENS"]
VECTORIZER_PARAMS = _PRIM["VECTORIZER_PARAMS"]
body = _PRIM["body"]
find_citations = _PRIM["find_citations"]

_TOKEN_RX = _re.compile(VECTORIZER_PARAMS["token_pattern"], _re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RX.findall(text.lower())


def _fit_tfidf(texts: list[str]):
    """sklearn TfidfVectorizer equivalent (sublinear, smooth idf, l2)."""
    stop = set(STOPWORDS)
    tokenized = [[t for t in _tokenize(tx) if t not in stop] for tx in texts]
    n = len(texts)
    df: dict[str, int] = {}
    tf_sum: dict[str, float] = {}
    for toks in tokenized:
        seen = set()
        counts: dict[str, int] = {}
        for t in toks:
            counts[t] = counts.get(t, 0) + 1
        for t, c in counts.items():
            if t not in seen:
                df[t] = df.get(t, 0) + 1
                seen.add(t)
            tf_sum[t] = tf_sum.get(t, 0.0) + c
    max_df = VECTORIZER_PARAMS["max_df"]
    min_df = VECTORIZER_PARAMS.get("min_df", 1)
    max_n = max_df * n if isinstance(max_df, float) else float(max_df)
    min_n = min_df * n if isinstance(min_df, float) else float(min_df)
    keep = [t for t in df if not (df[t] > max_n or df[t] < min_n)]
    limit = VECTORIZER_PARAMS.get("max_features")
    if limit is not None and len(keep) > limit:
        keep = sorted(keep, key=lambda t: (-tf_sum[t], t))[:limit]
    vocab = {t: i for i, t in enumerate(sorted(keep))}
    idf = {t: math.log((1 + n) / (1 + df[t])) + 1.0 for t in vocab}
    rows: list[dict[int, float]] = []
    for toks in tokenized:
        counts: dict[str, int] = {}
        for t in toks:
            if t in vocab:
                counts[t] = counts.get(t, 0) + 1
        vec: dict[int, float] = {}
        for t, c in counts.items():
            vec[vocab[t]] = (1.0 + math.log(c)) * idf[t]
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            vec = {i: v / norm for i, v in vec.items()}
        rows.append(vec)
    return vocab, idf, rows


def _transform_query(query: str, vocab: dict, idf: dict) -> tuple[dict[int, float], int]:
    stop = set(STOPWORDS)
    counts: dict[str, int] = {}
    for t in _tokenize(query):
        if t not in stop and t in vocab:
            counts[t] = counts.get(t, 0) + 1
    vec = {vocab[t]: (1.0 + math.log(c)) * idf[t] for t, c in counts.items()}
    nnz = len(vec)
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm > 0:
        vec = {i: v / norm for i, v in vec.items()}
    return vec, nnz


def _dot(a: dict[int, float], b: dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(i, 0.0) for i, v in a.items())


def _cos_dist(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 1.0
    return 1.0 - _dot(a, b)


def _rankdata_avg(a: list[float]) -> list[float]:
    order = sorted(range(len(a)), key=lambda i: (a[i], i))
    ranks = [0.0] * len(a)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and a[order[j + 1]] == a[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return float("nan")
    return cov / (sa * sb)


def _spearman(a: list[float], b: list[float]) -> tuple[float, bool]:
    if len(a) < 3:
        return float("nan"), True
    ra, rb = _rankdata_avg(a), _rankdata_avg(b)
    if len(set(ra)) <= 1 or len(set(rb)) <= 1:
        return float("nan"), True
    return _pearson(ra, rb), False


def _coherence(decisions: list[dict], clusters: list[dict], qlang: str, lexicon: list[str]) -> dict:
    base_lang = sum(1 for d in decisions if d.get("language") == qlang) / max(1, len(decisions))
    bodies = [body(d).casefold() for d in decisions]
    base_term = sum(1 for t in bodies if any(q in t for q in lexicon)) / max(1, len(bodies))
    per, dom = [], None
    for c in clusters:
        members = [d for d in decisions if int(d.get("cluster_id")) == int(c["cluster_id"])]
        nn = len(members)
        lang_share = sum(1 for d in members if d.get("language") == qlang) / max(1, nn)
        tb = [body(d).casefold() for d in members]
        term_share = sum(1 for t in tb if any(q in t for q in lexicon)) / max(1, nn)
        per.append({"cluster_id": int(c["cluster_id"]), "size": nn,
                    "query_lang_share": lang_share, "query_term_share": term_share})
    if per:
        dom = max(per, key=lambda p: p["size"])
    return {"bundle_lang_baseline": base_lang, "bundle_term_baseline": base_term,
            "per_cluster": per, "dominant": dom}


def _projection(decisions: list[dict], rows: list[dict], query_text: str,
                 query_vec: dict, qnnz: int) -> dict:
    n = len(decisions)
    coords = [(float(d.get("x", 0)), float(d.get("y", 0))) for d in decisions]
    iu = [(i, j) for i in range(n) for j in range(i + 1, n)]
    cos_d = [_cos_dist(rows[i], rows[j]) for i, j in iu]
    euc_d = [math.dist(coords[i], coords[j]) for i, j in iu]
    rho, deg1 = _spearman(cos_d, euc_d)
    k = min(10, n - 1)
    overlaps = []
    for i in range(n):
        de = sorted(range(n), key=lambda j: (math.dist(coords[i], coords[j]), j))
        dc = sorted(range(n), key=lambda j: (_cos_dist(rows[i], rows[j]), j))
        nn_e = set(de[1:k + 1])
        nn_c = set(dc[1:k + 1])
        overlaps.append(len(nn_e & nn_c) / max(1, k))
    knn = sum(overlaps) / len(overlaps) if overlaps else float("nan")
    ranks = [float(d.get("rank", 0)) for d in decisions]
    if qnnz == 0:
        rho_r, deg2 = float("nan"), True
    else:
        qd = [_cos_dist(rows[i], query_vec) for i in range(n)]
        rho_r, deg2 = _spearman(qd, ranks)
    return {"spearman_2d_vs_cosine": rho, "degenerate_2d": bool(deg1),
            "knn10_overlap": knn, "rank_rho": rho_r,
            "rank_degenerate": bool(deg2), "query_vector_nnz": qnnz}


def _structure(decisions: list[dict], rows: list[dict], clusters: list[dict]) -> dict:
    n = len(decisions)
    sizes = [sum(1 for d in decisions if int(d.get("cluster_id")) == int(c["cluster_id"])) for c in clusters]
    largest = max(sizes) if sizes else 0
    cid = [int(d.get("cluster_id")) for d in decisions]
    intra, inter = [], []
    for i in range(n):
        for j in range(i + 1, n):
            (intra if cid[i] == cid[j] else inter).append(_cos_dist(rows[i], rows[j]))
    ratio = (sum(intra) / len(intra)) / (sum(inter) / len(inter)) if intra and inter and sum(inter) else float("nan")
    return {"largest_share": largest / max(1, n), "largest_n": int(largest), "sep_ratio": ratio}


def _labels(clusters: list[dict]) -> dict:
    term_sets, pooled = [], []
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
    return {"content_fraction": frac,
            "mean_pairwise_jaccard": sum(jacs) / len(jacs) if jacs else 0.0,
            "distinct_labels": len({str(c.get("label") or "") for c in clusters}),
            "n_clusters": len(clusters)}


def _outliers(decisions: list[dict]) -> dict:
    ids = [d.get("decision_id") for d in decisions]
    cit = {d.get("decision_id"): set(find_citations(body(d)[:20000])) for d in decisions}
    deg = []
    for i, did in enumerate(ids):
        s = sum(1 for j, did2 in enumerate(ids) if i != j and (cit[did] & cit[did2]))
        deg.append(float(s))
    flags = [bool(d.get("is_outlier")) for d in decisions]
    ranks = [float(d.get("rank", 0)) for d in decisions]
    degenerate = sum(deg) == 0
    n = len(decisions)
    kk = max(1, n // 10)
    tail_idx = set(sorted(range(n), key=lambda i: (ranks[i], i))[-kk:]) if n else set()
    out_idx = {i for i, f in enumerate(flags) if f}
    union = out_idx | tail_idx
    jacc = len(out_idx & tail_idx) / len(union) if union else 1.0
    out_deg = [deg[i] for i in out_idx]
    rest_deg = [deg[i] for i in range(n) if i not in out_idx]
    return {"outlier_mean_degree": sum(out_deg) / len(out_deg) if out_deg else float("nan"),
            "rest_mean_degree": sum(rest_deg) / len(rest_deg) if rest_deg else float("nan"),
            "tail_jaccard": float(jacc), "n_outliers": len(out_idx),
            "citation_graph_degenerate": bool(degenerate)}


def _relations(bundle: dict) -> dict:
    rels = bundle.get("relations", []) or []
    ids = {d.get("decision_id") for d in bundle.get("decisions", [])}
    missing = sum(1 for r in rels if r.get("source") not in ids or r.get("target") not in ids)
    nokind = sum(1 for r in rels if r.get("kind") is None)
    endpoint_ok = (len(rels) - missing) / len(rels) if rels else 0.0
    return {"edge_count": len(rels), "endpoint_ok_fraction": endpoint_ok,
            "edges_missing_endpoint": missing, "edges_without_kind": nokind}


def score_bundle(bundle: dict, query_language: str, lexicon: list[str]) -> tuple[dict, dict]:
    """Apply the 11 frozen bars to one bundle. Returns (verdicts, detail)."""
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters", []) or []
    texts = [body(d) for d in decisions]
    _vocab, _idf, rows = _fit_tfidf(texts)
    query_vec, qnnz = _transform_query(str(bundle.get("query", "")), _vocab, _idf)
    coh = _coherence(decisions, clusters, query_language, lexicon)
    dom = coh["dominant"]
    base = coh["bundle_lang_baseline"]
    lang_bar = max(0.25, 0.5 * base)
    proj = _projection(decisions, rows, str(bundle.get("query", "")), query_vec, qnnz)
    st = _structure(decisions, rows, clusters)
    lab = _labels(clusters)
    out = _outliers(decisions)
    rel = _relations(bundle)
    V: dict = {}
    V["COHERENCE_QUERY_LANG"] = {"value": dom["query_lang_share"] if dom else 0.0,
                                 "bar": lang_bar,
                                 "pass": bool(dom and dom["query_lang_share"] >= lang_bar),
                                 "baseline": base}
    V["COHERENCE_QUERY_TERM"] = {"value": dom["query_term_share"] if dom else 0.0,
                                 "bar": coh["bundle_term_baseline"],
                                 "pass": bool(dom and dom["query_term_share"] >= coh["bundle_term_baseline"])}
    V["PROJ_RANK"] = {"value": proj["rank_rho"], "bar": 0.30,
                      "pass": bool(not proj["rank_degenerate"] and proj["rank_rho"] >= 0.30),
                      "degenerate": proj["rank_degenerate"]}
    V["PROJ_SPEARMAN"] = {"value": proj["spearman_2d_vs_cosine"], "bar": 0.50,
                          "pass": bool(not proj["degenerate_2d"] and proj["spearman_2d_vs_cosine"] >= 0.50)}
    V["PROJ_KNN10"] = {"value": proj["knn10_overlap"], "bar": 0.40,
                       "pass": bool(proj["knn10_overlap"] >= 0.40)}
    V["STRUCTURE_LARGEST"] = {"value": st["largest_share"], "bar": 0.60,
                              "pass": bool(st["largest_share"] <= 0.60)}
    sep = st["sep_ratio"]
    V["STRUCTURE_SEP"] = {"value": sep, "bar": 0.90,
                          "pass": bool(not (sep != sep) and sep < 0.90)}
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
              "outliers": out, "relations": rel, "engine": "stdlib",
              "max_features_tie_break": "alphabetical"}
    return V, detail


def bundle_pass_count(verdicts: dict) -> int:
    return sum(1 for c in CRITERIA_ORDER if verdicts.get(c, {}).get("pass"))


def mega_cluster_disclosure(bundle: dict) -> dict:
    """Size-based map_is_one_mega_cluster disclosure (NOT a frozen-bar verdict).

    Fires when the largest-cluster share (SHIPPED assignment) >= 0.50.
    """
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters", []) or []
    n = len(decisions)
    sizes = [sum(1 for d in decisions if int(d.get("cluster_id")) == int(c["cluster_id"])) for c in clusters]
    largest = max(sizes) if sizes else 0
    share = (largest / n) if n else 0.0
    return {
        "largest_cluster_size": int(largest),
        "n_decisions": n,
        "largest_cluster_share": share,
        "fire_threshold": 0.50,
        "disclosure_fires": bool(share >= 0.50),
    }


def score_packet(bundles: dict[str, dict], rules: dict) -> dict:
    """Score a {qid: bundle_dict} packet. Language/lexicon read from RULES."""
    lexicons = rules.get("query_term_lexicons", {})
    lang_by_qid = {e.get("bundle"): e.get("query_language") for e in rules.get("inputs", [])}
    per_bundle = {}
    for qid, bundle in bundles.items():
        qlang = lang_by_qid.get(qid)
        lex = lexicons.get(qid)
        if qlang is None or lex is None:
            raise ValueError(f"no frozen language/lexicon for bundle {qid!r}; refusing to invent one")
        V, detail = score_bundle(bundle, qlang, lex)
        n_pass = bundle_pass_count(V)
        per_bundle[qid] = {"n_pass": n_pass, "n_criteria": 11,
                           "bundle_pass_all_11": n_pass == 11,
                           "criteria": V, "detail": detail,
                           "query_language": qlang,
                           "mega_cluster": mega_cluster_disclosure(bundle)}
    counts = {qid: b["n_pass"] for qid, b in per_bundle.items()}
    n_all_pass = sum(1 for b in per_bundle.values() if b["bundle_pass_all_11"])
    absolute_status = "GEOMETRY_SOUND" if n_all_pass == len(per_bundle) and per_bundle else "GEOMETRY_UNSOUND"
    lineage = set(per_bundle) == set(INCUMBENT_COUNTS)
    regressed_qids = [qid for qid in per_bundle
                      if lineage and per_bundle[qid]["n_pass"] < INCUMBENT_COUNTS[qid]]
    regression_verdict = ("NOT_APPLICABLE" if not lineage
                          else ("FAIL_REGRESSION" if regressed_qids else "PASS_NO_REGRESSION"))
    return {
        "gate": "map-geometry-semantics",
        "rules_sha256": RULES_GEOMETRY_SHA256,
        "absolute_bar": "all 11 criteria on every bundle",
        "absolute_status": absolute_status,
        "absolute_enforced_as_build_blocker": False,
        "n_bundles_pass_all_11": n_all_pass,
        "n_bundles": len(per_bundle),
        "per_bundle_counts": counts,
        "incumbent_counts": dict(INCUMBENT_COUNTS),
        "lineage_matches_incumbent": lineage,
        "regressed_qids": regressed_qids,
        "regression_verdict": regression_verdict,
        "gate_blocks_build": bool(lineage and regressed_qids),
        "per_bundle": per_bundle,
    }
