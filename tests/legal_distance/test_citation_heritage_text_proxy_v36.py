#!/usr/bin/env python3
"""
Legal-distance v36 — citation-heritage TEXT-ONLY proxy verification tests.

SECTION A — committed-artifact smoke/consistency checks (relabelled; NOT falsifiable alone).
SECTION B — raw-input recompute (independent, falsifiable):
  Re-derives the v36 headline numbers FROM RAW INPUTS only, with an INDEPENDENT
  AUC implementation (trapezoidal ROC over unique thresholds) and a re-implemented
  dense assembly / center-projection / PCA-64 pipeline:
    * dense checkpoints   legal_distance/results/174k_dense_embeddings/checkpoints/
    * metadata            evaluation/data/174k/metadata_174k.json
    * TF-IDF reps         evaluation/results/174k/embeddings/*.npy
    * ORIG pairs          evaluation/results/174k_citation_heritage/citation_pairs_174k.json
    * frozen relation pairs (v36) legal_distance/results/citation_heritage_text_proxy_v36/relation_pairs_v36.json
    * citation graph      /tmp/lex_accepted/.../citation_graph_174k.json  (NOT repo-tracked;
                          graph-dependent jaccard/H2 checks are SKIPPED, not failed, when absent)
  and asserts they match the committed v36 results JSONs within float tolerance.

  The falsifiable content is: (i) the dense/text-only AUCs are recomputed from raw
  vectors, not read from the committed JSON; (ii) the margin and the H1/H1b verdicts
  (and the dense-only legs of H2) are re-derived from the recomputed numbers. If a
  committed JSON were fabricated, Section B would disagree.

Run:  python3 tests/legal_distance/test_citation_heritage_text_proxy_v36.py
Exits non-zero on any failed assertion.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
import os

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "legal_distance/results/citation_heritage_text_proxy_v36"
A_JSON = OUT / "text_proxy_results.json"
B_JSON = OUT / "relation_text_baselines_results.json"
REL_PAIRS = OUT / "relation_pairs_v36.json"

CKPT = ROOT / "legal_distance/results/174k_dense_embeddings/checkpoints"
FULL_META = ROOT / "evaluation/data/174k/metadata_174k.json"
TFIDF_DIR = ROOT / "evaluation/results/174k/embeddings"
PAIRS_ORIG = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k.json"

# The citation graph is NOT tracked in this repo; it lives in the ACCEPTED evaluation peer
# branch, mounted under /tmp/lex_accepted in the producer environment only. The auditor's
# environment does not mount it, so graph-dependent checks (SHARED2 jaccard, full H2) are
# SKIPPED when unavailable rather than failing. All dense/text-only AUC checks need only
# repo-tracked dense checkpoints, metadata, TF-IDF reps and the frozen pairs file.
GRAPH_CANDIDATES = [
    Path("/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_graph_174k.json"),
    Path("/tmp/lex_accepted/evaluation/results/174k_citation_heritage/citation_graph_174k.json"),
    ROOT / "evaluation/results/174k_citation_heritage/citation_graph_174k.json",
    ROOT / "legal_distance/results/174k_citation_heritage/citation_graph_174k.json",
]
# LEX_CITATION_GRAPH=<path> overrides resolution (e.g. point at a nonexistent path to exercise
# the auditor no-graph skip path, or at the accepted peer mount to run the full check set).
_env_graph = os.environ.get("LEX_CITATION_GRAPH")
if _env_graph:
    GRAPH_CANDIDATES = [Path(_env_graph)]
GRAPH = next((p for p in GRAPH_CANDIDATES if p.exists()), None)

DENSE_YEARS = list(range(2000, 2024))
TEXT_ONLY = ["full_text_tfidf_light", "regeste_tfidf",
             "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7"]
TOL = 5e-4
PASS, FAIL, SKIP = [], [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def skip(name, why):
    SKIP.append(name)
    print(f"  [SKIP] {name}  ({why})")


# --- independent AUC: trapezoidal ROC over unique thresholds (not average-rank) ---
def auc_trapz(y, s):
    y = np.asarray(y)
    s = np.asarray(s, dtype=np.float64)
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(-s, kind="mergesort")
    ys, ss = y[order], s[order]
    tpr, fpr = [0.0], [0.0]
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        tp = int(ys[:j + 1].sum())
        tp_frac = tp / n_pos
        fp_frac = (j + 1 - tp) / n_neg
        tpr.append(tp_frac)
        fpr.append(fp_frac)
        i = j + 1
    area = 0.0
    for k in range(1, len(fpr)):
        area += (fpr[k] - fpr[k - 1]) * (tpr[k] + tpr[k - 1]) / 2.0
    return float(area)


def cos(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def load_pipeline():
    meta = json.load(open(FULL_META))
    did2idx = {m["decision_id"]: i for i, m in enumerate(meta)}
    n = len(meta)
    D = np.zeros((n, 768), dtype=np.float32)
    has = np.zeros(n, dtype=bool)
    for y in DENSE_YEARS:
        m = json.load(open(CKPT / f"metadata_{y}.json"))
        E = np.load(CKPT / f"embeddings_{y}.npy")
        rows = [i for i, x in enumerate(m) if x["decision_id"] in did2idx]
        assert len(rows) == E.shape[0], f"{y}: {len(rows)} vs {E.shape[0]}"
        dids = [did2idx[m[i]["decision_id"]] for i in rows]
        D[dids] = E[rows]
        has[dids] = True
    # per-language centering (independent vectorization)
    langs = defaultdict(list)
    for i in np.nonzero(has)[0]:
        langs[meta[i].get("language", "?")].append(i)
    cp = D.copy()
    for _lg, idxs in langs.items():
        cp[idxs] -= cp[idxs].mean(axis=0)
    nrm = np.linalg.norm(cp, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    cp /= nrm
    X = cp[has]
    Xc = X - X.mean(axis=0, keepdims=True)
    cov = Xc.T @ Xc / Xc.shape[0]
    evals, evecs = np.linalg.eigh(cov.astype(np.float64))
    comps = evecs[:, np.argsort(evals)[::-1][:64]].astype(np.float32)
    P = Xc @ comps
    nrm = np.linalg.norm(P, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    P /= nrm
    rows = np.nonzero(has)[0]
    cp64 = {meta[rows[k]]["decision_id"]: P[k] for k in range(len(rows))}
    return meta, did2idx, cp64


def score_pairs(pairs, fn, label):
    ys, ss = [], []
    for a, b in pairs:
        v = fn(a, b)
        if v is not None:
            ys.append(label); ss.append(v)
    return ys, ss


def auc_on(pos, neg, fn):
    yp, sp = score_pairs(pos, fn, 1)
    yn, sn = score_pairs(neg, fn, 0)
    return auc_trapz(yp + yn, sp + sn), len(yp), len(yn)


# ============================================================ SECTION A
def section_a_smoke():
    print("SECTION A — committed-artifact smoke checks (relabelled; not falsifiable alone)")
    assert A_JSON.exists() and B_JSON.exists() and REL_PAIRS.exists()
    a = json.load(open(A_JSON)); b = json.load(open(B_JSON))
    check("pair_counts_orig_matched_no_self_606_834",
          a["pair_counts"]["ORIG_matched_no_self"] == {"pos": 606, "neg": 834},
          json.dumps(a["pair_counts"]["ORIG_matched_no_self"]))
    h1 = a["H1_ORIG_dense_vs_text_only"]
    check("H1_margin_ge_threshold", h1["margin"] >= 0.05, f"{h1['margin']:+.4f}")
    check("H1_bootstrap_ci_above_zero", h1["bootstrap"]["lo"] > 0,
          f"[{h1['bootstrap']['lo']:+.4f},{h1['bootstrap']['hi']:+.4f}]")
    h1b = b["H1b_DIRECT_dense_vs_text_only"]
    check("H1b_margin_ge_threshold", h1b["margin"] >= 0.05, f"{h1b['margin']:+.4f}")
    h2 = b["H2_eval_criterion_degenerate"]
    check("H2_rule_supported", h2["supported"] is True, json.dumps(h2))
    check("verdict_is_justified", a["verdict_summary"]["verdict"] == "DENSE_TEXT_PROXY_JUSTIFIED",
          a["verdict_summary"]["verdict"])


# ============================================================ SECTION B
def section_b_recompute():
    print("SECTION B — raw-input recompute (independent AUC + pipeline)")
    for p in (CKPT, FULL_META, PAIRS_ORIG, REL_PAIRS):
        assert Path(p).exists(), f"missing raw input {p}"
    if GRAPH is None:
        skip("graph_dependent_checks",
             "citation graph not mounted (not repo-tracked; /tmp/lex_accepted absent); "
             "H1/H1b/DIRECT dense+text and frozen pair counts still recomputed")
    else:
        print(f"  (citation graph found: {GRAPH})")

    meta, did2idx, cp64 = load_pipeline()
    dense_cov = set(cp64.keys())
    check("dense_assembly_158427", len(dense_cov) == 158427, f"{len(dense_cov)}")

    # cache TF-IDF rows lazily
    cache = {}

    def tfv(rep, did):
        arr = cache.get(rep)
        if arr is None:
            arr = np.load(TFIDF_DIR / f"{rep}.npy")
            cache[rep] = arr
        i = did2idx.get(did)
        return None if i is None else arr[i]

    def sc_cp64(a, b):
        va, vb = cp64.get(a), cp64.get(b)
        return None if va is None or vb is None else cos(va, vb)

    def mk_tf(rep):
        def f(a, b):
            va, vb = tfv(rep, a), tfv(rep, b)
            return None if va is None or vb is None else cos(va, vb)
        return f

    def sc_jac(d2t):
        def f(a, b):
            A, B = d2t.get(a, set()), d2t.get(b, set())
            u = len(A | B)
            return 0.0 if u == 0 else len(A & B) / u
        return f

    # ---- ORIG ----
    d = json.load(open(PAIRS_ORIG))
    o_pos = [tuple(x) for x in d["positive_pairs"]]
    o_neg = [tuple(x) for x in d["negative_pairs"]]
    m_pos = [p for p in o_pos if p[0] in dense_cov and p[1] in dense_cov and p[0] != p[1]]
    m_neg = [n for n in o_neg if n[0] in dense_cov and n[1] in dense_cov and n[0] != n[1]]
    check("orig_matched_no_self_counts_606_834", len(m_pos) == 606 and len(m_neg) == 834,
          f"{len(m_pos)}/{len(m_neg)}")

    committed = json.load(open(A_JSON))
    c_row = committed["protocol_results"]["ORIG_matched_no_self"]

    r_dense, npd, nnd = auc_on(m_pos, m_neg, sc_cp64)
    check("recompute_ORIG_dense_cp64_matches", abs(r_dense - c_row["dense_cp64"]["auc"]) <= TOL,
          f"recomputed={r_dense:.6f} committed={c_row['dense_cp64']['auc']:.6f}")

    text_aucs = {rep: auc_on(m_pos, m_neg, mk_tf(rep))[0] for rep in TEXT_ONLY}
    best_rep = max(text_aucs, key=text_aucs.get)
    best_text = text_aucs[best_rep]
    committed_best_rep = committed["H1_ORIG_dense_vs_text_only"]["best_text_only_rep"]
    check("recompute_ORIG_best_text_only_rep_matches", best_rep == committed_best_rep,
          f"recomputed={best_rep} committed={committed_best_rep}")
    check("recompute_ORIG_best_text_only_auc_matches",
          abs(best_text - c_row[best_rep]["auc"]) <= TOL,
          f"best={best_rep} recomputed={best_text:.6f} committed={c_row[best_rep]['auc']:.6f}")

    margin = r_dense - best_text
    check("recompute_ORIG_margin_ge_0.05", margin >= 0.05, f"{margin:+.4f}")
    check("recompute_ORIG_margin_matches_committed",
          abs(margin - committed["H1_ORIG_dense_vs_text_only"]["margin"]) <= TOL,
          f"{margin:+.6f} vs {committed['H1_ORIG_dense_vs_text_only']['margin']:+.6f}")

    r_text_full, _, _ = auc_on(m_pos, m_neg, mk_tf("full_text_tfidf_light"))
    check("recompute_full_text_tfidf_light_lower_than_dense", r_text_full < r_dense - 0.05,
          f"full_text_light={r_text_full:.4f} dense={r_dense:.4f}")

    r_cited, _, _ = auc_on(m_pos, m_neg, mk_tf("cited_decisions_tfidf"))
    check("recompute_ORIG_matched_no_self_cited_tfidf_matches",
          abs(r_cited - committed["reconciliation_eval_0.7296"]["this_run_ORIG_matched_no_self_cited_decisions_tfidf"]) <= TOL,
          f"{r_cited:.6f}")

    # ---- relation pairs (frozen dump) ----
    rel = json.load(open(REL_PAIRS))
    d2t = {}
    if GRAPH is not None:
        G = json.load(open(GRAPH))
        for s, ts in G.items():
            v = set(t for t in ts if t in did2idx)
            if v:
                d2t[s] = v

    for name, exp in (("DIRECT__NEG_hard_matched", (5255, 6008)),
                      ("SHARED2__NEG_hard_matched", (2875, 3627))):
        pos = [tuple(x) for x in rel[name]["positives"]]
        neg = [tuple(x) for x in rel[name]["negatives"]]
        check(f"frozen_pair_counts_{name}", (len(pos), len(neg)) == exp, f"{len(pos)}/{len(neg)}")

    # DIRECT
    dpos = [tuple(x) for x in rel["DIRECT__NEG_hard_matched"]["positives"]]
    dneg = [tuple(x) for x in rel["DIRECT__NEG_hard_matched"]["negatives"]]
    rd, _, _ = auc_on(dpos, dneg, sc_cp64)
    cdir = json.load(open(B_JSON))["matched_results"]["DIRECT__NEG_hard"]
    check("recompute_DIRECT_dense_cp64_matches", abs(rd - cdir["dense_cp64"]["auc"]) <= TOL,
          f"recomputed={rd:.6f} committed={cdir['dense_cp64']['auc']:.6f}")
    dtxt = {rep: auc_on(dpos, dneg, mk_tf(rep))[0] for rep in TEXT_ONLY}
    dbest_rep = max(dtxt, key=dtxt.get)
    dbest = dtxt[dbest_rep]
    check("recompute_DIRECT_best_text_matches",
          abs(dbest - cdir[dbest_rep]["auc"]) <= TOL,
          f"best={dbest_rep} recomputed={dbest:.6f} committed={cdir[dbest_rep]['auc']:.6f}")
    dmargin = rd - dbest
    check("recompute_DIRECT_margin_ge_0.05", dmargin >= 0.05, f"{dmargin:+.4f}")

    # SHARED2
    s2pos = [tuple(x) for x in rel["SHARED2__NEG_hard_matched"]["positives"]]
    s2neg = [tuple(x) for x in rel["SHARED2__NEG_hard_matched"]["negatives"]]
    rs2, _, _ = auc_on(s2pos, s2neg, sc_cp64)
    cs2 = json.load(open(B_JSON))["matched_results"]["SHARED2__NEG_hard"]
    check("recompute_SHARED2_dense_cp64_matches", abs(rs2 - cs2["dense_cp64"]["auc"]) <= TOL,
          f"recomputed={rs2:.6f} committed={cs2['dense_cp64']['auc']:.6f}")

    # ---- H2 reconstruction (graph-dependent jaccard part conditionally skipped) ----
    if GRAPH is not None:
        rjac, _, _ = auc_on(s2pos, s2neg, sc_jac(d2t))
        check("recompute_SHARED2_jaccard_matches", abs(rjac - cs2["citation_jaccard_full"]["auc"]) <= TOL,
              f"recomputed={rjac:.6f} committed={cs2['citation_jaccard_full']['auc']:.6f}")
        h2_supported = (rjac >= 0.99) and (rs2 >= 0.90) and (rd < 0.75)
        check("recompute_H2_criterion_degenerate", h2_supported,
              f"jaccard_S2={rjac:.4f} dense_S2={rs2:.4f} dense_DIRECT={rd:.4f}")
    else:
        # Without the graph we can still verify the two dense-only legs of H2.
        check("recompute_H2_dense_legs", (rs2 >= 0.90) and (rd < 0.75),
              f"dense_S2={rs2:.4f} dense_DIRECT={rd:.4f}; jaccard leg SKIPPED")


def main():
    section_a_smoke()
    section_b_recompute()
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed, {len(SKIP)} skipped")
    if SKIP:
        print("SKIPPED (environment-dependent, non-failing): " + ", ".join(SKIP))
    if FAIL:
        print("FAILED: " + ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
