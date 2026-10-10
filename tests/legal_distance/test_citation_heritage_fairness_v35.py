#!/usr/bin/env python3
"""
Legal-distance v35 — citation-heritage fairness audit verification tests.

Two independent sections:

SECTION A — committed-artifact smoke/consistency checks (relabelled):
  Sanity-checks the internal consistency of the committed result artifacts
  (fairness_audit_results.json / relation_decomposition_results.json).
  NOTE: these assertions alone are NOT falsifiable evidence — they re-read the
  committed JSON — so they are explicitly labelled SMOKE checks.

SECTION B — raw-input recompute checks (independent, falsifiable):
  Re-derives the PRIMARY matched self-pair-free AUCs (dense_cp64 and
  cited_decisions_tfidf on the identical 606 positive / 834 negative pairs)
  FROM THE MOUNTED RAW INPUTS:
    * dense checkpoints      legal_distance/results/174k_dense_embeddings/checkpoints/
    * metadata               evaluation/data/174k/metadata_174k.json
    * TF-IDF representation  evaluation/results/174k/embeddings/cited_decisions_tfidf.npy
    * pair set               evaluation/results/174k_citation_heritage/citation_pairs_174k.json
  and asserts they match the committed values within float tolerance, that the
  pair counts are the frozen 606/834, and that the pre-registered success rule
  (dense >= best TF-IDF citation by +0.02 AUC on identical matched
  self-pair-free pairs) is violated => verdict FALSIFIED.

The recompute mirrors the frozen pipeline of
legal_distance/experiments/citation_heritage_fairness_audit_v35.py
(identical assembly, language center projection, PCA-64, pair matching and
AUC-ROC with average ranks). The pipeline is re-implemented here rather than
imported, so the check is independent of the committed JSON.

Run:  python3 tests/legal_distance/test_citation_heritage_fairness_v35.py
Exits non-zero on any failed assertion.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
AUD = ROOT / "legal_distance/results/citation_heritage_fairness_audit_v35/fairness_audit_results.json"
DEC = ROOT / "legal_distance/results/citation_heritage_fairness_audit_v35/relation_decomposition_results.json"

# --- raw inputs (all tracked in the repository, mounted in CI) ---
CKPT = ROOT / "legal_distance/results/174k_dense_embeddings/checkpoints"
FULL_META = ROOT / "evaluation/data/174k/metadata_174k.json"
TFIDF = ROOT / "evaluation/results/174k/embeddings/cited_decisions_tfidf.npy"
PAIRS_ORIG = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k.json"

DENSE_YEARS = list(range(2000, 2024))   # 24 checkpoint years (2000-2023), n=158,427
SEED = 42
N_BOOT = 2000
TOL = 1e-3                               # float/BLAS tolerance (observed delta: 0.0)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


# ============================================================ SECTION A
def section_a_smoke():
    print("SECTION A — committed-artifact smoke/consistency checks (relabelled; not falsifiable on their own)")
    assert AUD.exists(), f"missing {AUD}"
    assert DEC.exists(), f"missing {DEC}"
    a = json.load(open(AUD))
    d = json.load(open(DEC))

    cov = a["pair_coverage"]
    check("orig_self_pair_rate_material",
          cov["ORIG"]["self_pos"] >= 100 and cov["ORIG"]["self_pos"] / cov["ORIG"]["pos"] > 0.10,
          f"{cov['ORIG']['self_pos']}/{cov['ORIG']['pos']}")

    spi = a["self_pair_inflation"]
    for rep, m in spi.items():
        check(f"self_pair_inflation_ge_0.03__{rep}", m["delta"] >= 0.03, f"delta={m['delta']:.4f}")

    pub = a["published_asreported"]
    dense_pub = pub["ORIG_all"]["dense_cp64"]["auc"]
    tf_pub = pub["ORIG_all"]["cited_decisions_tfidf"]["auc"]
    check("as_published_dense_apparently_beats_tfidf", dense_pub - tf_pub > 0.02,
          f"dense={dense_pub:.4f} tfidf={tf_pub:.4f}")

    fair = a["fair_matched"]["P_matched_no_self"]
    d64 = fair["dense_cp64"]["auc"]
    tf = fair["cited_decisions_tfidf"]["auc"]
    check("fair_matched_dense_tfidf_within_0.02", abs(d64 - tf) < 0.02, f"dense={d64:.4f} tfidf={tf:.4f}")

    mg = a["margin"]
    check("primary_margin_below_success_threshold", mg["margin"] < mg["success_threshold"],
          f"margin={mg['margin']:+.4f} thr={mg['success_threshold']}")
    check("primary_verdict_falsified", mg["verdict"] == "FALSIFIED", mg["verdict"])
    check("bootstrap_ci_crosses_zero",
          mg["bootstrap"]["lo"] < 0 < mg["bootstrap"]["hi"],
          f"[{mg['bootstrap']['lo']:+.4f},{mg['bootstrap']['hi']:+.4f}]")

    check("fair_comparison_identical_pair_count",
          fair["dense_cp64"]["n_pos"] == fair["cited_decisions_tfidf"]["n_pos"] == 606,
          f"{fair['dense_cp64']['n_pos']} vs {fair['cited_decisions_tfidf']['n_pos']}")

    gs = d["graph_stats"]
    check("graph_stats_present", gs["sources"] == 5031 and gs["targets"] == 918,
          json.dumps(gs))

    direct_hard = d["results"]["DIRECT__NEG_hard"]
    check("faithful_citation_repr_beats_dense_on_direct",
          direct_hard["citation_jaccard_full"]["auc"] > direct_hard["dense_cp64"]["auc"],
          f"jaccard={direct_hard['citation_jaccard_full']['auc']:.4f} dense={direct_hard['dense_cp64']['auc']:.4f}")

    s2 = d["results"]["SHARED2__NEG_hard"]
    check("production_tfidf128_is_poor_citation_encoder",
          s2["tfidf_cited_decisions_128"]["auc"] < 0.72,
          f"tfidf128={s2['tfidf_cited_decisions_128']['auc']:.4f}")
    check("dense_recovers_shared2_relation",
          s2["dense_cp64"]["auc"] > 0.90,
          f"dense_cp64={s2['dense_cp64']['auc']:.4f}")
    check("citation_jaccard_oracle_on_shared",
          s2["citation_jaccard_full"]["auc"] >= 0.999,
          f"jaccard={s2['citation_jaccard_full']['auc']:.4f}")


# ============================================================ SECTION B
def auc_roc(y_true, scores):
    """AUC-ROC via Mann-Whitney U with average ranks (ties handled)."""
    y_true = np.asarray(y_true)
    scores = np.asarray(scores, dtype=np.float64)
    n_pos = int(y_true.sum())
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    s_sorted = scores[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg
        i = j + 1
    rank_sum_pos = ranks[y_true == 1].sum()
    return float((rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def load_metadata():
    meta = json.load(open(FULL_META))
    did2idx = {m["decision_id"]: i for i, m in enumerate(meta)}
    return meta, did2idx


def assemble_dense(meta, did2idx):
    """Assemble raw 768-dim embeddings from per-year checkpoints (2000-2023)."""
    n = len(meta)
    D = np.zeros((n, 768), dtype=np.float32)
    has = np.zeros(n, dtype=bool)
    for year in DENSE_YEARS:
        mp = CKPT / f"metadata_{year}.json"
        ep = CKPT / f"embeddings_{year}.npy"
        assert mp.exists() and ep.exists(), f"missing dense checkpoint for {year}"
        m = json.load(open(mp))
        E = np.load(ep)
        idxs = [did2idx[x["decision_id"]] for x in m if x["decision_id"] in did2idx]
        rows = [i for i, x in enumerate(m) if x["decision_id"] in did2idx]
        assert len(rows) == E.shape[0], f"{year}: meta rows {len(rows)} vs emb {E.shape[0]}"
        D[idxs, :] = E[rows, :]
        has[idxs] = True
    return D, has


def language_center_projection(D, has, meta):
    langs = {}
    for i in np.where(has)[0]:
        langs.setdefault(meta[i].get("language", "unknown"), []).append(i)
    out = D.copy()
    for lang, idxs in langs.items():
        c = D[idxs].mean(axis=0)
        out[idxs] = D[idxs] - c
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    out = out / norms
    return out


def pca64(D_cp, has):
    X = D_cp[has].astype(np.float32)
    mu = X.mean(axis=0, keepdims=True)
    Xc = X - mu
    C = (Xc.T @ Xc) / Xc.shape[0]
    evals, evecs = np.linalg.eigh(C.astype(np.float64))
    order = np.argsort(evals)[::-1][:64]
    comps = evecs[:, order].astype(np.float32)
    P = Xc @ comps
    norms = np.linalg.norm(P, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    P = P / norms
    return P, np.where(has)[0]


def load_pairs_and_match():
    d = json.load(open(PAIRS_ORIG))
    pos = [tuple(x) for x in d["positive_pairs"]]
    neg = [tuple(x) for x in d["negative_pairs"]]
    return pos, neg


def score_pairs(pos, neg, get_vec):
    ys, ss = [], []
    for a, b in pos:
        va, vb = get_vec(a), get_vec(b)
        if va is None or vb is None:
            continue
        s = float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
        ys.append(1); ss.append(s)
    for a, b in neg:
        va, vb = get_vec(a), get_vec(b)
        if va is None or vb is None:
            continue
        s = float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
        ys.append(0); ss.append(s)
    return dict(auc=auc_roc(ys, ss), n_pos=sum(1 for y in ys if y == 1),
                n_neg=sum(1 for y in ys if y == 0), ys=np.asarray(ys), ss=np.asarray(ss))


def bootstrap_margin_ci(pos, neg, get_a, get_b, n_boot=N_BOOT):
    """Bootstrap 95% CI of AUC(a) - AUC(b) over the SAME valid pair list."""
    ys_a, ss_a, ss_b = [], [], []
    for (a, b) in pos:
        va, vb = get_a(a), get_a(b)
        if va is not None and vb is not None:
            wa, wb = get_b(a), get_b(b)
            if wa is None or wb is None:
                continue
            ys_a.append(1)
            ss_a.append(float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12)))
            ss_b.append(float(np.dot(wa, wb) / (np.linalg.norm(wa) * np.linalg.norm(wb) + 1e-12)))
    for (a, b) in neg:
        va, vb = get_a(a), get_a(b)
        if va is not None and vb is not None:
            wa, wb = get_b(a), get_b(b)
            if wa is None or wb is None:
                continue
            ys_a.append(0)
            ss_a.append(float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12)))
            ss_b.append(float(np.dot(wa, wb) / (np.linalg.norm(wa) * np.linalg.norm(wb) + 1e-12)))
    ys = np.asarray(ys_a)
    s_a = np.asarray(ss_a)
    s_b = np.asarray(ss_b)
    rng = np.random.default_rng(SEED)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(ys), len(ys))
        yy = ys[idx]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        diffs.append(auc_roc(yy, s_a[idx]) - auc_roc(yy, s_b[idx]))
    diffs = np.asarray(diffs)
    return dict(mean=float(diffs.mean()), lo=float(np.percentile(diffs, 2.5)),
                hi=float(np.percentile(diffs, 97.5)), n_boot=len(diffs))


def section_b_recompute():
    print("SECTION B — raw-input recompute of the primary matched self-pair-free AUCs")
    for p in (CKPT, FULL_META, TFIDF, PAIRS_ORIG, AUD):
        assert Path(p).exists(), f"missing raw input {p}"

    meta, did2idx = load_metadata()
    D_raw, has_dense = assemble_dense(meta, did2idx)
    dec_dense = set(meta[i]["decision_id"] for i in np.where(has_dense)[0])
    check("dense_assembly_covers_158427", has_dense.sum() == 158427, f"{has_dense.sum()}")

    D_cp = language_center_projection(D_raw, has_dense, meta)
    P64, rows64 = pca64(D_cp, has_dense)
    cp64_vec = {meta[rows64[k]]["decision_id"]: P64[k] for k in range(len(rows64))}

    tf_arr = np.load(TFIDF, mmap_mode="r")

    def get_cp64(did):
        return cp64_vec.get(did)

    def get_tfidf(did):
        i = did2idx.get(did)
        if i is None:
            return None
        return np.asarray(tf_arr[i])

    o_pos, o_neg = load_pairs_and_match()
    P_m = ([p for p in o_pos if p[0] in dec_dense and p[1] in dec_dense],
           [n for n in o_neg if n[0] in dec_dense and n[1] in dec_dense])
    M = [p for p in P_m[0] if p[0] != p[1]]
    N = [n for n in P_m[1] if n[0] != n[1]]
    check("recomputed_pair_counts_606_834", len(M) == 606 and len(N) == 834,
          f"pos={len(M)} neg={len(N)}")

    r_dense = score_pairs(M, N, get_cp64)
    r_tfidf = score_pairs(M, N, get_tfidf)
    print(f"  recomputed dense_cp64 AUC={r_dense['auc']:.7f}  (n={r_dense['n_pos']}/{r_dense['n_neg']})")
    print(f"  recomputed cited_decisions_tfidf AUC={r_tfidf['auc']:.7f}  (n={r_tfidf['n_pos']}/{r_tfidf['n_neg']})")

    committed = json.load(open(AUD))["fair_matched"]["P_matched_no_self"]
    c_dense = committed["dense_cp64"]["auc"]
    c_tfidf = committed["cited_decisions_tfidf"]["auc"]
    check("recompute_matches_committed_dense_cp64", abs(r_dense["auc"] - c_dense) <= TOL,
          f"recomputed={r_dense['auc']:.4f} committed={c_dense:.4f}")
    check("recompute_matches_committed_cited_decisions_tfidf", abs(r_tfidf["auc"] - c_tfidf) <= TOL,
          f"recomputed={r_tfidf['auc']:.4f} committed={c_tfidf:.4f}")

    margin = r_dense["auc"] - r_tfidf["auc"]
    check("recomputed_margin_below_success_threshold", margin < 0.02, f"margin={margin:+.4f} thr=0.02")
    check("recomputed_verdict_falsified", margin < 0.02, "FALSIFIED (dense NOT >= TF-IDF +0.02)")

    # absolute criterion on the recomputed (no-self ORIG) numbers
    check("recomputed_no_self_dense_below_0.75",
          r_dense["auc"] < 0.75, f"dense_cp64={r_dense['auc']:.4f} (<0.75 => 'PASSED (AUC>0.75)' was pair-set/self-pair dependent)")

    boot = bootstrap_margin_ci(M, N, get_cp64, get_tfidf)
    check("recomputed_bootstrap_ci_crosses_zero", boot["lo"] < 0 < boot["hi"],
          f"[{boot['lo']:+.4f}, {boot['hi']:+.4f}] mean={boot['mean']:+.4f}")
    check("recomputed_bootstrap_matches_committed",
          abs(boot["lo"] - (-0.0343)) <= 0.002 and abs(boot["hi"] - 0.0366) <= 0.002,
          f"[{boot['lo']:+.4f}, {boot['hi']:+.4f}]")


def main():
    section_a_smoke()
    section_b_recompute()
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED: " + ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())