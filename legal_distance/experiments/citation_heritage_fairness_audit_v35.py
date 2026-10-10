#!/usr/bin/env python3
"""
Legal-distance v35 — Citation-Heritage Fairness Audit (falsification experiment)

Tests the ACCEPTED legal-distance claim:
  "Dense center_projected embeddings recover citation heritage BETTER than
   TF-IDF citation-based (AUC 0.77-0.85 vs 0.71-0.74)."

Pre-registered threats (see frozen_spec.json):
  T1 self-pairs (174/1020 positives are (d,d))
  T2 pair-set mismatch (dense evaluated on a filtered subset, TF-IDF on all pairs)
  T3 subset selection (report bootstrap uncertainty)

All representations are evaluated on the IDENTICAL decision-matched pair set,
with and without self-pairs, so the comparison is apples-to-apples.

Pure numpy. Raw results are written to the run directory; nothing is overwritten.
"""
import json
import time
from pathlib import Path
from datetime import datetime

import numpy as np

ROOT = Path("/home/runner/work/LexMachina/LexMachina")
CKPT = ROOT / "legal_distance/results/174k_dense_embeddings/checkpoints"
FULL_META = ROOT / "evaluation/data/174k/metadata_174k.json"
TFIDF_DIR = ROOT / "evaluation/results/174k/embeddings"
PAIRS_ORIG = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k.json"
PAIRS_FULL = Path("/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json")
OUT_DIR = ROOT / "legal_distance/results/citation_heritage_fairness_audit_v35"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
DENSE_YEARS = list(range(2000, 2024))          # all available checkpoints
MATCHED_YEARS = list(range(2000, 2022))        # the 22yr published comparison subset
EARLY_YEARS = list(range(2000, 2021))          # the 21yr published comparison subset
N_BOOT = 2000


def log(msg):
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- AUC
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


def cosine_matrix_rows(A, B):
    """Row-wise cosine similarity between aligned A and B."""
    na = np.linalg.norm(A, axis=1)
    nb = np.linalg.norm(B, axis=1)
    na[na == 0] = 1.0
    nb[nb == 0] = 1.0
    return np.sum(A * B, axis=1) / (na * nb)


# ---------------------------------------------------------------- data
def load_metadata():
    log("loading full metadata ...")
    meta = json.load(open(FULL_META))
    did2idx = {m["decision_id"]: i for i, m in enumerate(meta)}
    return meta, did2idx


def load_dense_assembly(meta, did2idx):
    """Return (D_raw_float32[n,768], has_dense_bool[n])."""
    n = len(meta)
    dim = 768
    D = np.zeros((n, dim), dtype=np.float32)
    has = np.zeros(n, dtype=bool)
    for year in DENSE_YEARS:
        mp = CKPT / f"metadata_{year}.json"
        ep = CKPT / f"embeddings_{year}.npy"
        if not mp.exists() or not ep.exists():
            log(f"  checkpoint missing: {year}")
            continue
        m = json.load(open(mp))
        E = np.load(ep)
        idxs = [did2idx[x["decision_id"]] for x in m if x["decision_id"] in did2idx]
        # map meta-year rows: need positions in E corresponding to m
        rows = [i for i, x in enumerate(m) if x["decision_id"] in did2idx]
        if len(rows) != E.shape[0]:
            log(f"  {year}: meta rows {len(rows)} vs emb {E.shape[0]} (skipping unmatched)")
        keep = [i for i in rows]
        D[idxs, :] = E[keep, :]
        has[idxs] = True
    log(f"dense assembly: {has.sum()} decisions")
    return D, has


def language_center_projection(D, has, meta):
    langs = {}
    for i in np.where(has)[0]:
        langs.setdefault(meta[i].get("language", "unknown"), []).append(i)
    out = D.copy()
    for lang, idxs in langs.items():
        c = D[idxs].mean(axis=0)
        out[idxs] = D[idxs] - c
        log(f"  center {lang}: n={len(idxs)}")
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    out = out / norms
    return out


def pca64(D_cp, has):
    """Top-64 PCA (mean-centred) on the dense-assembled rows, then L2."""
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


# ---------------------------------------------------------------- pairs
def load_pairs(path):
    d = json.load(open(path))
    pos = [tuple(x) for x in d["positive_pairs"]]
    neg = [tuple(x) for x in d["negative_pairs"]]
    return pos, neg, d


def strip_self(pos, neg):
    return [p for p in pos if p[0] != p[1]], [p for p in neg if p[0] != p[1]]


def match_pairs(pos, neg, dec_set):
    mp = [p for p in pos if p[0] in dec_set and p[1] in dec_set]
    mn = [p for p in neg if p[0] in dec_set and p[1] in dec_set]
    return mp, mn


# ---------------------------------------------------------------- scoring
def score_pairs(pos, neg, get_vec):
    """Return (auc, n_pos, n_neg, pos_mean, neg_mean). Vectors via get_vec(id)->vec or None."""
    ys, ss = [], []
    pm, nm = [], []
    for a, b in pos:
        va, vb = get_vec(a), get_vec(b)
        if va is None or vb is None:
            continue
        s = float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
        ys.append(1); ss.append(s); pm.append(s)
    for a, b in neg:
        va, vb = get_vec(a), get_vec(b)
        if va is None or vb is None:
            continue
        s = float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
        ys.append(0); ss.append(s); nm.append(s)
    if not ys:
        return dict(auc=float("nan"), n_pos=0, n_neg=0)
    return dict(
        auc=auc_roc(ys, ss),
        n_pos=len(pm), n_neg=len(nm),
        pos_mean=float(np.mean(pm)) if pm else float("nan"),
        neg_mean=float(np.mean(nm)) if nm else float("nan"),
        _ys=np.asarray(ys), _ss=np.asarray(ss),
    )


def bootstrap_margin(pos, neg, get_a, get_b, n_boot=N_BOOT):
    """Bootstrap 95% CI of AUC(a) - AUC(b) over shared valid pairs."""
    ya, sa, yb, sb = [], [], [], []
    for (a, b) in pos:
        va, vb = get_a(a), get_a(b)
        if va is not None and vb is not None:
            ya.append(1); sa.append(float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12)))
    for (a, b) in neg:
        va, vb = get_a(a), get_a(b)
        if va is not None and vb is not None:
            ya.append(0); sa.append(float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12)))
    # b on the SAME pair list (pair identity preserved by using same loops order)
    ya2, sa2 = [], []
    for (a, b) in pos:
        va, vb = get_b(a), get_b(b)
        if va is not None and vb is not None:
            ya2.append(1); sa2.append(float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12)))
    for (a, b) in neg:
        va, vb = get_b(a), get_b(b)
        if va is not None and vb is not None:
            ya2.append(0); sa2.append(float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12)))
    n = min(len(sa), len(sa2))
    ys = np.asarray(ya[:n]); s_a = np.asarray(sa[:n]); s_b = np.asarray(sa2[:n])
    rng = np.random.default_rng(SEED)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yy = ys[idx]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        diffs.append(auc_roc(yy, s_a[idx]) - auc_roc(yy, s_b[idx]))
    diffs = np.asarray(diffs)
    return dict(
        mean=float(diffs.mean()) if len(diffs) else float("nan"),
        lo=float(np.percentile(diffs, 2.5)) if len(diffs) else float("nan"),
        hi=float(np.percentile(diffs, 97.5)) if len(diffs) else float("nan"),
        n_boot=len(diffs),
    )


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    meta, did2idx = load_metadata()
    D_raw, has_dense = load_dense_assembly(meta, did2idx)
    dec_dense = set(meta[i]["decision_id"] for i in np.where(has_dense)[0])
    dec_dense22 = set()
    for year in MATCHED_YEARS:
        m = json.load(open(CKPT / f"metadata_{year}.json"))
        dec_dense22.update(x["decision_id"] for x in m if x["decision_id"] in did2idx)
    dec_dense21 = set()
    for year in EARLY_YEARS:
        m = json.load(open(CKPT / f"metadata_{year}.json"))
        dec_dense21.update(x["decision_id"] for x in m if x["decision_id"] in did2idx)

    log("computing center projection ...")
    D_cp = language_center_projection(D_raw, has_dense, meta)
    log("computing PCA-64 ...")
    P64, rows64 = pca64(D_cp, has_dense)
    cp64_vec = {meta[rows64[k]]["decision_id"]: P64[k] for k in range(len(rows64))}

    log("loading TF-IDF representations ...")
    tf_arrays = {}
    for name in ["cited_decisions_tfidf",
                 "cited_decisions_tfidf_outcome_hybrid_0.5",
                 "cited_decisions_tfidf_outcome_hybrid_0.7"]:
        arr = np.load(TFIDF_DIR / f"{name}.npy", mmap_mode="r")
        tf_arrays[name] = arr
        log(f"  {name}: {arr.shape}")

    def raw_get(i):
        return D_raw[i] if has_dense[i] else None

    def cp_get(i):
        return D_cp[i] if has_dense[i] else None

    did2idx_local = did2idx

    def mk_get(fn):
        return fn

    get_dense_raw = lambda d: (D_raw[did2idx[d]] if d in did2idx and has_dense[did2idx[d]] else None)
    get_dense_cp = lambda d: (D_cp[did2idx[d]] if d in did2idx and has_dense[did2idx[d]] else None)
    get_dense_cp64 = lambda d: cp64_vec.get(d)

    def mk_tfidf(name):
        arr = tf_arrays[name]
        return lambda d: (np.asarray(arr[did2idx[d]]) if d in did2idx else None)

    reps = {
        "dense_raw_768": get_dense_raw,
        "dense_cp_768": get_dense_cp,
        "dense_cp64": get_dense_cp64,
        "cited_decisions_tfidf": mk_tfidf("cited_decisions_tfidf"),
        "cited_decisions_tfidf_outcome_hybrid_0.5": mk_tfidf("cited_decisions_tfidf_outcome_hybrid_0.5"),
        "cited_decisions_tfidf_outcome_hybrid_0.7": mk_tfidf("cited_decisions_tfidf_outcome_hybrid_0.7"),
    }

    results = {
        "run_id": "LEGAL_DISTANCE_V35_CITATION_HERITAGE_FAIRNESS_AUDIT_38039706350",
        "frozen_spec": "legal_distance/results/citation_heritage_fairness_audit_v35/frozen_spec.json",
        "meta": {
            "n_meta": len(meta),
            "n_dense_assembly": int(has_dense.sum()),
            "n_dense_2000_2020": len(dec_dense21),
            "n_dense_2000_2021": len(dec_dense22),
        },
        "pair_coverage": {},
        "published_asreported": {},
        "fair_matched": {},
        "self_pair_inflation": {},
        "margin": {},
    }

    # ---------------- pair sets
    log("loading pair sets ...")
    o_pos, o_neg, _ = load_pairs(PAIRS_ORIG)
    f_pos, f_neg, _ = load_pairs(PAIRS_FULL)
    o_pos_ns, o_neg_ns = strip_self(o_pos, o_neg)
    f_pos_ns, f_neg_ns = strip_self(f_pos, f_neg)
    results["pair_coverage"] = {
        "ORIG": {"pos": len(o_pos), "neg": len(o_neg),
                 "self_pos": sum(1 for a, b in o_pos if a == b),
                 "self_neg": sum(1 for a, b in o_neg if a == b)},
        "FULL": {"pos": len(f_pos), "neg": len(f_neg),
                 "self_pos": sum(1 for a, b in f_pos if a == b),
                 "self_neg": sum(1 for a, b in f_neg if a == b)},
    }
    # dense-matched sets
    P_m = match_pairs(o_pos, o_neg, dec_dense)
    P_m22 = match_pairs(o_pos, o_neg, dec_dense22)
    P_m21 = match_pairs(o_pos, o_neg, dec_dense21)
    Pm_ns = strip_self(*P_m)
    M, N = Pm_ns
    results["pair_coverage"]["P_matched_dense2023"] = {"pos": len(P_m[0]), "neg": len(P_m[1]),
                                                       "pos_no_self": len(M), "neg_no_self": len(N)}
    results["pair_coverage"]["P_matched_dense2021"] = {"pos": len(P_m22[0]), "neg": len(P_m22[1])}
    results["pair_coverage"]["P_matched_dense2020"] = {"pos": len(P_m21[0]), "neg": len(P_m21[1])}
    log(f"P_matched(dense2023): pos={len(P_m[0])} neg={len(P_m[1])} | no_self pos={len(M)} neg={len(N)}")

    # ---------------- as-published (diagnostic, apples-to-oranges)
    log("scoring as-published comparison ...")
    for key, (p, n) in {
        "ORIG_all": (o_pos, o_neg),
        "ORIG_all_no_self": (o_pos_ns, o_neg_ns),
        "dense2021_matched": P_m22,
        "dense2020_matched": P_m21,
    }.items():
        row = {}
        for rname, fn in reps.items():
            r = score_pairs(p, n, fn)
            r.pop("_ys", None); r.pop("_ss", None)
            row[rname] = r
        results["published_asreported"][key] = row
        for rname in reps:
            a = row[rname].get("auc")
            if a is not None and not (isinstance(a, float) and np.isnan(a)):
                log(f"  {key:22s} {rname:48s} AUC={a:.4f} (n={row[rname]['n_pos']})")

    # ---------------- fair matched comparison (primary)
    log("primary fair matched comparison ...")
    for key, (p, n) in {
        "P_matched_no_self": (M, N),
        "P_matched_with_self": P_m,
    }.items():
        row = {}
        for rname, fn in reps.items():
            r = score_pairs(p, n, fn)
            r.pop("_ys", None); r.pop("_ss", None)
            row[rname] = r
        results["fair_matched"][key] = row
        for rname in reps:
            a = row[rname].get("auc")
            if a is not None and not (isinstance(a, float) and np.isnan(a)):
                log(f"  {key:22s} {rname:48s} AUC={a:.4f} (n={row[rname]['n_pos']})")

    # ---------------- self-pair inflation
    for rname, fn in reps.items():
        a_all = results["published_asreported"]["ORIG_all"][rname]["auc"]
        a_ns = results["published_asreported"]["ORIG_all_no_self"][rname]["auc"]
        results["self_pair_inflation"][rname] = {
            "auc_with_self": a_all, "auc_no_self": a_ns,
            "delta": (a_all - a_ns) if (a_all and a_ns) else None,
        }
        log(f"  self-pair delta {rname:48s} {a_all} -> {a_ns}")

    # ---------------- primary margin
    log("bootstrap margin dense_cp64 - best TF-IDF (P_matched_no_self) ...")
    best_tf = None
    best_auc = -1
    for name in ["cited_decisions_tfidf",
                 "cited_decisions_tfidf_outcome_hybrid_0.5",
                 "cited_decisions_tfidf_outcome_hybrid_0.7"]:
        a = results["fair_matched"]["P_matched_no_self"][name]["auc"]
        if a > best_auc:
            best_auc = a; best_tf = name
    dense_auc = results["fair_matched"]["P_matched_no_self"]["dense_cp64"]["auc"]
    margin = dense_auc - best_auc
    boot = bootstrap_margin(M, N, reps["dense_cp64"], reps[best_tf])
    results["margin"] = {
        "pair_set": "P_matched_no_self",
        "dense_cp64_auc": dense_auc,
        "best_tfidf": best_tf,
        "best_tfidf_auc": best_auc,
        "margin": margin,
        "bootstrap": boot,
        "success_threshold": 0.02,
        "verdict": "SURVIVES" if margin >= 0.02 else "FALSIFIED",
    }
    log(f"PRIMARY: dense_cp64={dense_auc:.4f} best_tfidf({best_tf})={best_auc:.4f} margin={margin:+.4f} -> {results['margin']['verdict']}")
    log(f"bootstrap 95% CI = [{boot['lo']:+.4f}, {boot['hi']:+.4f}]")

    # secondary: FULL pair set, matched
    log("secondary FULL pair set, dense-matched ...")
    Fm = match_pairs(f_pos, f_neg, dec_dense)
    Fm_ns = strip_self(*Fm)
    frow = {}
    for rname, fn in reps.items():
        r = score_pairs(Fm_ns[0], Fm_ns[1], fn)
        r.pop("_ys", None); r.pop("_ss", None)
        frow[rname] = r
    results["fair_matched"]["FULL_matched_no_self"] = frow
    results["pair_coverage"]["FULL_matched_dense2023"] = {"pos": len(Fm[0]), "neg": len(Fm[1]),
                                                          "pos_no_self": len(Fm_ns[0])}
    for rname in reps:
        a = frow[rname].get("auc")
        if a is not None and not (isinstance(a, float) and np.isnan(a)):
            log(f"  FULL_matched_no_self {rname:44s} AUC={a:.4f} (n={frow[rname]['n_pos']})")

    results["duration_seconds"] = time.time() - t0
    results["generated_utc"] = datetime.utcnow().isoformat() + "Z"
    outp = OUT_DIR / "fairness_audit_results.json"
    json.dump(results, open(outp, "w"), indent=2, default=str)
    log(f"wrote {outp}")
    return results


if __name__ == "__main__":
    main()
