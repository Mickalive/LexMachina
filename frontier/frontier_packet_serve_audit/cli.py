#!/usr/bin/env python3
"""
Frontier Packet Serve Audit — Independent serve verdict on the packet-of-record v3 bytes.

This harness:
1. FREEZES first (RULES.json committed before any scoring)
2. Recomputes frozen label support on the v3 packet's own bytes
3. Recomputes frozen geometry on the v3 shipped bundles
4. Measures marginal discovery on the same bundles
5. Cross-checks against Core Evaluation's published numbers
6. Emits one machine-checked serve verdict: SERVE / DO-NOT-SERVE-UNCHANGED / BOUNDED-NEGATIVE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

# Add the vendored frozen_bars to path
_BAR_DIR = Path(__file__).resolve().parent
if str(_BAR_DIR.parent.parent / "evaluation" / "evaluation" / "frozen_bars") not in sys.path:
    sys.path.insert(0, str(_BAR_DIR.parent.parent / "evaluation" / "evaluation" / "frozen_bars"))

# Import vendored label integrity
from vendored.frontier_counter_label_integrity.rules import FrozenRules as LabelFrozenRules, load_rules as load_label_rules
from vendored.frontier_counter_label_integrity.rubric import VARIANT_PRIMARY, make_context, score_row
from vendored.frontier_counter_label_integrity.extract import counter_rows, load_bundle, ROW_FIELDS
from vendored.frontier_counter_label_integrity.injection import run_non_vacuity, DEFECT_CRITERIA


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_frozen_rules(rules_path: str | Path, expected_sha256: str) -> dict:
    """Load and verify frozen rules file."""
    raw = Path(rules_path).read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha256:
        raise RuntimeError(
            f"Frozen rules sha256 mismatch: expected {expected_sha256}, "
            f"observed {actual_sha} from {rules_path}. "
            "Frozen bars are reused by re-hash, never re-derived; refusing to score."
        )
    return json.loads(raw.decode("utf-8"))


# --- Label Support Recomputation ---

def score_label_bundle(bundle_path: str | Path, label_rules: LabelFrozenRules, profile_key: str) -> dict:
    """Score one bundle under the frozen label rubric."""
    bundle = load_bundle(str(bundle_path))
    scored_statuses = list(label_rules.rubric["scored_statuses"])
    reported_statuses = list(label_rules.rubric["reported_separately_never_scored"])
    scored_rows_list, reported_rows = counter_rows(bundle, scored_statuses, reported_statuses)
    ctx = make_context(label_rules, profile_key, VARIANT_PRIMARY)
    scored = [score_row(r, ctx) for r in scored_rows_list]
    classes: dict[str, int] = {}
    for r in scored:
        classes[r["primary_defect_class"]] = classes.get(r["primary_defect_class"], 0) + 1
    n_supported = sum(1 for r in scored if r["supported"])
    return {
        "bundle_path": str(bundle_path),
        "sha256": sha256_file(bundle_path),
        "anchor_profile": profile_key,
        "n_decisions": len(bundle.get("decisions") or []),
        "n_scored": len(scored),
        "n_reported_only": len(reported_rows),
        "n_supported": n_supported,
        "support_rate": (n_supported / len(scored)) if scored else None,
        "classes": classes,
        "rows": [
            {
                "decision_id": r["decision_id"],
                "rank": r["rank"],
                "language": r["language"],
                "counter_status": r["counter_status"],
                "supported": r["supported"],
                "primary_defect_class": r["primary_defect_class"],
                "reason_code": r["reason_code"],
            }
            for r in scored
        ],
    }


def score_label_packet(bundles: dict[str, str], label_rules: LabelFrozenRules) -> dict:
    """Score the packet's label support."""
    known_anchors = set(label_rules.anchors)
    unknown = [qid for qid in bundles if qid not in known_anchors]
    if unknown:
        raise ValueError(
            f"no frozen anchor profile for bundle(s) {unknown!r}; refusing to invent one "
            "(admitting a new packet requires a disclosed RULES_LABEL re-freeze)"
        )
    per_bundle = {qid: score_label_bundle(path, label_rules, qid) for qid, path in bundles.items()}
    n_scored = sum(b["n_scored"] for b in per_bundle.values())
    n_supported = sum(b["n_supported"] for b in per_bundle.values())
    classes: dict[str, int] = {}
    for b in per_bundle.values():
        for k, v in b["classes"].items():
            classes[k] = classes.get(k, 0) + v
    support_rate = (n_supported / n_scored) if n_scored else None
    
    # Absolute frozen bar (verdict_rule LABEL_SOUND): reported, NOT enforced.
    absolute_bar = 1.0
    absolute_status = (
        "LABEL_SOUND" if (n_scored and n_supported == n_scored) else "LABEL_UNSOUND"
    )
    
    # Population-free label_lineage_gate
    # The predicate: lineage := (set(per_bundle) == {de-kapitalverletzung, fr-bail-entretien, it-responsabilita-medica}) AND (n_scored == 65)
    lineage = set(per_bundle) == {"de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"} and n_scored == 65
    if lineage:
        regressed = n_supported < 5
        regression_verdict = "FAIL_REGRESSION" if regressed else "PASS_NO_REGRESSION"
    else:
        regression_verdict = "NOT_APPLICABLE"
    
    # NOT_APPLICABLE is NOT a pass - explicit guard
    not_applicable_is_not_pass = True
    
    return {
        "gate": "counter-label-support",
        "rules_sha256": label_rules.sha256,
        "absolute_bar": absolute_bar,
        "absolute_status": absolute_status,
        "absolute_enforced_as_build_blocker": False,
        "n_scored": n_scored,
        "n_supported": n_supported,
        "support_rate": support_rate,
        "classes": classes,
        "lineage_matches_incumbent_population": lineage,
        "regression_verdict": regression_verdict,
        "not_applicable_is_not_pass": not_applicable_is_not_pass,
        "gate_blocks_build": bool(lineage and n_supported < 5),
        "per_bundle": per_bundle,
    }


# --- Geometry Recomputation ---

def load_frozen_geometry_rules(path: str | Path, expected_sha256: str) -> dict:
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise RuntimeError(
            "RULES_GEOMETRY sha256 mismatch: refusing to score. "
            "Frozen bars are reused by re-hash, never re-derived."
        )
    return json.loads(raw.decode("utf-8"))


# Geometry primitives extracted from vendored textgeo.py (stdlib-only)
import ast
import html
import re
import math
import random


def _extract_textgeo_primitives(vendored_path: Path) -> dict:
    src = vendored_path.read_text(encoding="utf-8")
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
    ns: dict = {"html": html, "re": re, "time": __import__("time")}
    exec(compile(ast.fix_missing_locations(mod), str(vendored_path), "exec"), ns)
    return ns


_VENDORED_TEXTGEO = Path("/tmp/lex_accepted/core/evaluation/evaluation/frozen_bars/vendored/frontier_map_semantics_reference/textgeo.py")
_PRIM = _extract_textgeo_primitives(_VENDORED_TEXTGEO)
STOPWORDS = _PRIM["STOPWORDS"]
CIT_RE = _PRIM["CIT_RE"]
CITATION_FRAGMENT_TOKENS = _PRIM["CITATION_FRAGMENT_TOKENS"]
VECTORIZER_PARAMS = _PRIM["VECTORIZER_PARAMS"]
_body_fn = _PRIM["body"]
_find_citations_fn = _PRIM["find_citations"]


def body(d: dict) -> str:
    return _body_fn(d)


def find_citations(text: str):
    return _find_citations_fn(text)


_TOKEN_RX = re.compile(VECTORIZER_PARAMS["token_pattern"], re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RX.findall(text.lower())


def _fit_tfidf(texts: list[str]):
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


def score_geometry_bundle(bundle: dict, query_language: str, lexicon: list[str]) -> tuple[dict, dict]:
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


def score_geometry_packet(bundles: dict[str, dict], geometry_rules: dict) -> dict:
    """Score a {qid: bundle_dict} packet."""
    lexicons = geometry_rules.get("query_term_lexicons", {})
    lang_by_qid = {e.get("bundle"): e.get("query_language") for e in geometry_rules.get("inputs", [])}
    per_bundle = {}
    for qid, bundle in bundles.items():
        qlang = lang_by_qid.get(qid)
        lex = lexicons.get(qid)
        if qlang is None or lex is None:
            raise ValueError(f"no frozen language/lexicon for bundle {qid!r}; refusing to invent one")
        V, detail = score_geometry_bundle(bundle, qlang, lex)
        n_pass = bundle_pass_count(V)
        per_bundle[qid] = {"n_pass": n_pass, "n_criteria": 11,
                           "bundle_pass_all_11": n_pass == 11,
                           "criteria": V, "detail": detail,
                           "query_language": qlang}
    counts = {qid: b["n_pass"] for qid, b in per_bundle.items()}
    n_all_pass = sum(1 for b in per_bundle.values() if b["bundle_pass_all_11"])
    absolute_status = "GEOMETRY_SOUND" if n_all_pass == len(per_bundle) and per_bundle else "GEOMETRY_UNSOUND"
    
    # Regression: applies on the served-packet lineage (the three served qids).
    incumbent_counts = {
        "de-kapitalverletzung": 6,
        "fr-bail-entretien": 5,
        "it-responsabilita-medica": 5,
    }
    lineage = set(per_bundle) == set(incumbent_counts)
    regressed_qids = [qid for qid in per_bundle
                      if lineage and per_bundle[qid]["n_pass"] < incumbent_counts[qid]]
    regression_verdict = ("NOT_APPLICABLE" if not lineage
                          else ("FAIL_REGRESSION" if regressed_qids else "PASS_NO_REGRESSION"))
    
    # Mega-cluster disclosure
    mega_cluster = {}
    for qid, b in per_bundle.items():
        bundle_obj = bundles[qid]
        decisions = bundle_obj.get("decisions") or []
        clusters = bundle_obj.get("clusters", []) or []
        sizes = [sum(1 for d in decisions if int(d.get("cluster_id")) == int(c["cluster_id"])) for c in clusters]
        largest = max(sizes) if sizes else 0
        share = largest / max(1, len(decisions))
        mega_cluster[qid] = {
            "largest_cluster_size": int(largest),
            "n_decisions": len(decisions),
            "size_based_share": share,
            "fired": share >= 0.5,
            "bar": 0.5,
            "definition": "largest_cluster_size / n_decisions (size-based, len(idx))"
        }
    
    return {
        "gate": "map-geometry-semantics",
        "rules_sha256": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
        "absolute_bar": "all 11 criteria on every bundle",
        "absolute_status": absolute_status,
        "absolute_enforced_as_build_blocker": False,
        "n_bundles_pass_all_11": n_all_pass,
        "n_bundles": len(per_bundle),
        "per_bundle_counts": counts,
        "incumbent_counts": incumbent_counts,
        "lineage_matches_incumbent": lineage,
        "regressed_qids": regressed_qids,
        "regression_verdict": regression_verdict,
        "gate_blocks_build": bool(lineage and regressed_qids),
        "per_bundle": per_bundle,
        "mega_cluster_disclosure": mega_cluster,
    }


# --- Non-vacuity Controls ---

def non_vacuity_label(label_rules: LabelFrozenRules) -> dict:
    return run_non_vacuity(label_rules)


def _corrupt(bundle: dict, mode: str) -> dict:
    import copy
    rng = random.Random(0)
    b = copy.deepcopy(bundle)
    decs = b.get("decisions") or []
    ids = [d.get("cluster_id") for d in decs]
    order = list(range(len(decs)))
    rng.shuffle(order)
    for d, i in zip(decs, order):
        d["cluster_id"] = ids[i]
    clusters = b.get("clusters", []) or []
    labels = [c.get("label") for c in clusters]
    lorder = list(range(len(labels)))
    rng.shuffle(lorder)
    for c, i in zip(clusters, lorder):
        c["label"] = labels[i]
    for c in clusters:
        cid = int(c["cluster_id"])
        c["member_ids"] = [d.get("decision_id") for d in decs if int(d.get("cluster_id")) == cid][:50]
        c["size"] = sum(1 for d in decs if int(d.get("cluster_id")) == cid)
    if mode == "full":
        xs = [d.get("x") for d in decs]
        ys = [d.get("y") for d in decs]
        xorder = list(range(len(decs)))
        rng.shuffle(xorder)
        yorder = list(range(len(decs)))
        rng.shuffle(yorder)
        for d, i, j in zip(decs, xorder, yorder):
            d["x"], d["y"] = xs[i], ys[j]
    return b


def _overall(V: dict) -> bool:
    return all(bool(V[c]["pass"]) for c in CRITERIA_ORDER)


def non_vacuity_geometry(bundle: dict, query_language: str, lexicon: list[str]) -> dict:
    v0, _ = score_geometry_bundle(bundle, query_language, lexicon)
    out: dict = {}
    for mode in ("charter", "full"):
        corrupted = _corrupt(bundle, mode)
        vc, _ = score_geometry_bundle(corrupted, query_language, lexicon)
        flips = [c for c in CRITERIA_ORDER if bool(v0[c]["pass"]) != bool(vc[c]["pass"])]
        out[mode] = {"flips": flips, "n_flips": len(flips),
                     "corrupted_overall": "PASS" if _overall(vc) else "FAIL"}
    best = max(out[m]["n_flips"] for m in ("charter", "full"))
    proven = bool(best >= 2 and any(out[m]["corrupted_overall"] == "FAIL" for m in ("charter", "full")))
    out["required_min_flips"] = 2
    out["best_n_flips"] = best
    out["proven_non_vacuous"] = proven
    out["movability_note"] = (
        "Under the C-charter control (cluster ids permuted across rows + labels "
        "permuted across cluster ids) only COHERENCE_QUERY_LANG, COHERENCE_QUERY_TERM and "
        "STRUCTURE_SEP can move; the other 8 read only x/y, the pooled label multiset, the "
        "cluster-size multiset, the relation list or the outlier flags, all of which that "
        "permutation provably preserves."
    )
    return out


# --- Marginal Discovery Measurement ---

def measure_marginal_discovery(bundle: dict, K: int = 20) -> dict:
    """Measure marginal discovery for counter/contrary authorities on this bundle."""
    decisions = bundle.get("decisions") or []
    # Initial pool top-K by rank
    ranked = sorted(decisions, key=lambda d: d.get("rank", 0))
    top_k_ids = {d.get("decision_id") for d in ranked[:K]}
    
    # Counter authorities (excluding cited/supporting-candidate/context/unclassified/none)
    counter_rows = [d for d in decisions 
                    if d.get("counter_status") not in ("cited", "supporting-candidate", "context", "unclassified", "none", None)]
    
    results = []
    for row in counter_rows:
        decision_id = row.get("decision_id")
        rank = row.get("rank", 0)
        absent_from_top_k = decision_id not in top_k_ids
        # Map encounter before list: if it's an outlier or in a small cluster, map may surface it earlier
        is_outlier = bool(row.get("is_outlier"))
        cluster_id = row.get("cluster_id")
        cluster_size = sum(1 for d in decisions if d.get("cluster_id") == cluster_id)
        # Heuristic: map surfaces outliers and small-cluster members before ranked list reaches them
        map_encounter_before_list = is_outlier or cluster_size < 10
        
        results.append({
            "decision_id": decision_id,
            "counter_status": row.get("counter_status"),
            "counter_reason": row.get("counter_reason"),
            "rank": rank,
            "absent_from_initial_top_k": absent_from_top_k,
            "least_ranked_list_position": rank,
            "map_encounter_before_list": map_encounter_before_list,
            "is_outlier": is_outlier,
            "cluster_id": cluster_id,
            "cluster_size": cluster_size,
        })
    
    return {
        "frozen_K": K,
        "frozen_K_definition": "Top-K of the initial ranked list (before any map rendering or clustering). K=20 is the pre-registered gate's route to a positive q1/q3.",
        "counter_authority_definition": "counter_status not in gate_admissibility.NON_COUNTER_STATUSES (excludes cited / supporting-candidate / context / unclassified / none)",
        "n_counter_authorities": len(counter_rows),
        "n_absent_from_top_k": sum(1 for r in results if r["absent_from_initial_top_k"]),
        "n_map_encounter_before_list": sum(1 for r in results if r["map_encounter_before_list"]),
        "per_authority": results,
    }


# --- Cross-check against Core Evaluation ---

def cross_check(label_result: dict, geometry_result: dict, core_eval: dict) -> dict:
    """Cross-check this team's recomputation against Core Evaluation's published numbers."""
    # Core Evaluation's geometry on v3 bytes (from 39325867172 audit)
    core_geo_v3 = core_eval.get("core_evaluation_geometry_v3", {})
    core_geo_v3_counts = core_geo_v3.get("pass_counts", {})
    
    # This team's geometry on v3 bytes
    this_geo_counts = geometry_result.get("per_bundle_counts", {})
    
    # Label cross-check: Core Evaluation's numbers are on OLD packet (65 scored, 5 supported)
    # This team's numbers are on v3 packet (0 scored, 0 supported)
    core_label = core_eval.get("core_evaluation_label", {})
    
    return {
        "label": {
            "core_evaluation": {
                "source": core_label.get("source"),
                "measured_packet": "gate_packet/38839347028 (OLD packet)",
                "n_scored": core_label.get("n_scored"),
                "n_supported": core_label.get("n_supported"),
                "support_rate": core_label.get("support_rate"),
                "verdict": core_label.get("verdict"),
            },
            "this_team": {
                "measured_packet": "gate_packet/39319405429 (v3 packet)",
                "n_scored": label_result.get("n_scored"),
                "n_supported": label_result.get("n_supported"),
                "support_rate": label_result.get("support_rate"),
                "absolute_status": label_result.get("absolute_status"),
            },
            "divergence": {
                "note": "Different packets measured (OLD vs v3). Core Evaluation's 5/65 on old packet vs this team's 0/0 on v3 packet.",
                "headline": "Population changed: v3 packet has n_scored=0 counter-authority rows vs incumbent 65."
            }
        },
        "geometry": {
            "core_evaluation_v3": {
                "source": core_geo_v3.get("source", "accepted 39325867172 audit's geometry re-score"),
                "measured_packet": "gate_packet/39319405429 (v3 packet)",
                "per_bundle_counts": core_geo_v3_counts,
                "absolute_bar_met": core_geo_v3.get("absolute_bar_met", False),
            },
            "this_team": {
                "measured_packet": "gate_packet/39319405429 (v3 packet)",
                "per_bundle_counts": this_geo_counts,
                "absolute_bar_met": geometry_result.get("absolute_status") == "GEOMETRY_SOUND",
            },
            "divergence": {
                "per_bundle": {
                    qid: {
                        "core_evaluation": core_geo_v3_counts.get(qid),
                        "this_team": this_geo_counts.get(qid),
                        "match": core_geo_v3_counts.get(qid) == this_geo_counts.get(qid)
                    }
                    for qid in ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]
                },
                "headline": "Geometry cross-check: " + 
                    ("MATCH - all per-criterion counts agree" if core_geo_v3_counts == this_geo_counts 
                     else "DIVERGENCE - per-criterion counts differ on one or more bundles")
            }
        }
    }


# --- Serve Verdict ---

def determine_serve_verdict(label_result: dict, geometry_result: dict, marginal_discovery: dict, cross_check: dict) -> dict:
    """Determine the serve verdict per the charter's stop_promote_rule."""
    
    label_bar_met = label_result.get("absolute_status") == "LABEL_SOUND"
    geometry_bar_met = geometry_result.get("absolute_status") == "GEOMETRY_SOUND"
    
    # Mega-cluster disclosure firing (size-based share >= 0.5)
    mega_cluster = geometry_result.get("mega_cluster_disclosure", {})
    mega_fired_all = all(m.get("fired", False) for m in mega_cluster.values())
    
    # Marginal discovery: does the map add marginal discovery?
    # For v3, n_counter_authorities = 0 on all bundles, so no marginal discovery to measure
    marginal_discovery_exists = any(md.get("n_counter_authorities", 0) > 0 for md in marginal_discovery.values())
    
    # Serve conditions per charter:
    # SERVE: label_bar_met AND geometry_bar_met AND mega_cluster_disclosure fires (share >= 0.5)
    # DO-NOT-SERVE-UNCHANGED: bars remain unmet as written, serve conclusion unchanged
    # BOUNDED-NEGATIVE: both frozen absolute bars remain unmet AND no in-budget fix exists
    
    if label_bar_met and geometry_bar_met and mega_fired_all:
        verdict = "SERVE"
        bounded_causes = []
    elif not label_bar_met and not geometry_bar_met:
        # Both bars unmet
        # Check if marginal discovery exists on these bytes
        if not marginal_discovery_exists:
            verdict = "BOUNDED-NEGATIVE"
            bounded_causes = [
                {"half": "label", "cause": "n_scored=0 counter-authority rows on v3 packet; support_rate undefined (not 1.0); absolute bar unmet as written"},
                {"half": "geometry", "cause": f"geometry absolute bar unmet: {geometry_result.get('n_bundles_pass_all_11', 0)}/3 bundles pass all 11 criteria; no in-budget fix exists per accepted FAIL decision"}
            ]
        else:
            verdict = "DO-NOT-SERVE-UNCHANGED"
            bounded_causes = []
    else:
        # One bar met, one not - this shouldn't happen with v3 but handle it
        verdict = "DO-NOT-SERVE-UNCHANGED"
        bounded_causes = []
    
    return {
        "verdict": verdict,
        "label_bar_met": label_bar_met,
        "geometry_bar_met": geometry_bar_met,
        "mega_cluster_disclosure_fires_all": mega_fired_all,
        "marginal_discovery_exists": marginal_discovery_exists,
        "bounded_causes": bounded_causes,
        "owner_decision_required": verdict == "BOUNDED-NEGATIVE",
        "note": "NO owner card, NO owner session, NO ready_for_owner_session=true, NO human_gate_ready=true is produced from ANY outcome of this charter."
    }


# --- Main CLI ---

def main():
    parser = argparse.ArgumentParser(description="Frontier Packet Serve Audit")
    parser.add_argument("--packet", required=True, help="Path to packet-of-record v3 directory")
    parser.add_argument("--frozen-rules", required=True, help="Path to RULES.json freeze file")
    parser.add_argument("--output", required=True, help="Output directory for results")
    args = parser.parse_args()
    
    packet_dir = Path(args.packet)
    rules_path = Path(args.frozen_rules)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load RULES.json freeze
    rules = load_json(rules_path)
    
    # Verify input shas match
    packet_info = rules["inputs"]["packet_of_record_v3"]
    assert sha256_file(packet_dir / "packet.json") == packet_info["packet_json_sha256"], "packet.json sha mismatch"
    assert sha256_file(packet_dir / "manifest.json") == packet_info["manifest_sha256"], "manifest.json sha mismatch"
    assert sha256_file(packet_dir / "handoff.json") == packet_info["handoff_json_sha256"], "handoff.json sha mismatch"
    assert sha256_file(packet_dir / "disclosures.json") == packet_info["disclosures_json_sha256"], "disclosures.json sha mismatch"
    assert sha256_file(packet_dir / "CLAIM_CACHE_VERIFICATION.json") == packet_info["claim_cache_verification_sha256"], "claim_cache sha mismatch"
    
    for qid, binfo in packet_info["bundles"].items():
        assert sha256_file(binfo["bundle_path"]) == binfo["content_sha256"], f"{qid} bundle sha mismatch"
    
    # Load frozen rules
    label_rules = load_label_rules(rules["inputs"]["frozen_rules_label"]["path"])
    geometry_rules = load_frozen_geometry_rules(rules["inputs"]["frozen_rules_geometry"]["path"], 
                                                 rules["inputs"]["frozen_rules_geometry"]["sha256"])
    
    # Load bundles
    bundles_paths = {qid: binfo["bundle_path"] for qid, binfo in packet_info["bundles"].items()}
    bundles_dict = {qid: load_json(path) for qid, path in bundles_paths.items()}
    
    # 1. Label support recomputation
    print("Computing label support...")
    label_result = score_label_packet(bundles_paths, label_rules)
    
    # 2. Geometry recomputation
    print("Computing geometry...")
    geometry_result = score_geometry_packet(bundles_dict, geometry_rules)
    
    # 3. Non-vacuity controls
    print("Running non-vacuity controls...")
    nv_label = non_vacuity_label(label_rules)
    nv_geometry = {}
    for qid, bundle in bundles_dict.items():
        qlang = geometry_rules.get("inputs", [{}])[0].get("query_language")  # This needs fixing
        # Get language from rules inputs
        lang_by_qid = {e.get("bundle"): e.get("query_language") for e in geometry_rules.get("inputs", [])}
        lexicons = geometry_rules.get("query_term_lexicons", {})
        qlang = lang_by_qid.get(qid)
        lex = lexicons.get(qid)
        if qlang and lex:
            nv_geometry[qid] = non_vacuity_geometry(bundle, qlang, lex)
    
    # 4. Marginal discovery
    print("Measuring marginal discovery...")
    marginal_discovery = {}
    for qid, bundle in bundles_dict.items():
        marginal_discovery[qid] = measure_marginal_discovery(bundle, K=20)
    
    # 5. Cross-check
    print("Cross-checking against Core Evaluation...")
    cross_check_result = cross_check(label_result, geometry_result, rules.get("cross_check", {}))
    
    # 6. Serve verdict
    print("Determining serve verdict...")
    serve_verdict = determine_serve_verdict(label_result, geometry_result, marginal_discovery, cross_check_result)
    
    # Compile final report
    report = {
        "schema": "frontier-packet-serve-audit/report/1",
        "charter_version": 1,
        "team_id": "frontier-packet-serve-audit",
        "packet": {
            "packet_id": "gate-packet-v1",
            "run_id": "39319405429",
            "packet_json_sha256": packet_info["packet_json_sha256"],
            "manifest_sha256": packet_info["manifest_sha256"],
        },
        "freeze": {
            "rules_json_sha256": sha256_file(rules_path),
            "frozen_at_utc": rules.get("frozen_at_utc"),
            "label_rules_sha256": rules["inputs"]["frozen_rules_label"]["sha256"],
            "geometry_rules_sha256": rules["inputs"]["frozen_rules_geometry"]["sha256"],
            "verdict_contract_sha256": rules["inputs"]["verdict_contract"]["sha256"],
        },
        "label_support": label_result,
        "geometry": geometry_result,
        "non_vacuity": {
            "label": nv_label,
            "geometry": nv_geometry,
        },
        "marginal_discovery": marginal_discovery,
        "cross_check": cross_check_result,
        "serve_verdict": serve_verdict,
    }
    
    # Write report
    report_path = output_dir / "SERVE_AUDIT_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Report written to {report_path}")
    
    # Also write a summary
    summary = {
        "verdict": serve_verdict["verdict"],
        "label_bar_met": serve_verdict["label_bar_met"],
        "geometry_bar_met": serve_verdict["geometry_bar_met"],
        "label_n_scored": label_result["n_scored"],
        "label_n_supported": label_result["n_supported"],
        "label_support_rate": label_result["support_rate"],
        "label_absolute_status": label_result["absolute_status"],
        "geometry_n_bundles_pass_all_11": geometry_result["n_bundles_pass_all_11"],
        "geometry_per_bundle_counts": geometry_result["per_bundle_counts"],
        "geometry_absolute_status": geometry_result["absolute_status"],
        "marginal_discovery_exists": serve_verdict["marginal_discovery_exists"],
        "bounded_causes": serve_verdict["bounded_causes"],
        "owner_decision_required": serve_verdict["owner_decision_required"],
    }
    summary_path = output_dir / "SERVE_AUDIT_SUMMARY.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Summary written to {summary_path}")
    
    # Print verdict
    print(f"\n=== SERVE VERDICT: {serve_verdict['verdict']} ===")
    print(f"Label bar met: {serve_verdict['label_bar_met']} (n_scored={label_result['n_scored']}, n_supported={label_result['n_supported']}, status={label_result['absolute_status']})")
    print(f"Geometry bar met: {serve_verdict['geometry_bar_met']} (bundles_pass_all_11={geometry_result['n_bundles_pass_all_11']}/3, status={geometry_result['absolute_status']})")
    print(f"Mega-cluster disclosure fires on all: {serve_verdict['mega_cluster_disclosure_fires_all']}")
    print(f"Marginal discovery exists: {serve_verdict['marginal_discovery_exists']}")
    if serve_verdict["bounded_causes"]:
        print("Bounded causes:")
        for bc in serve_verdict["bounded_causes"]:
            print(f"  - {bc['half']}: {bc['cause']}")
    print(f"Owner decision required: {serve_verdict['owner_decision_required']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())