#!/usr/bin/env python3
"""
Legal-distance v36 — citation-heritage TEXT-ONLY proxy test + criterion reconciliation.

Frozen spec: legal_distance/results/citation_heritage_text_proxy_v36/frozen_spec.json
(pre-registered before outcome inspection; see run_id LEGAL_DISTANCE_V36_CITATION_HERITAGE_TEXT_PROXY_38051603155).

What is new vs v35:
  * v35 compared dense embeddings against the TF-IDF *citation* representation.
  * v36 asks the still-open product question: for a corpus WITHOUT a resolved citation
    graph, do dense text embeddings beat the strongest TEXT-ONLY baseline (full_text,
    regeste, and their hybrids) by a decisive margin? The proxy role survived v35 but was
    never tested against the correct comparator.
  * v36 also re-checks the relation-stratified behaviour (DIRECT / SHARED1 / SHARED2) with
    text-only baselines, to decide whether the evaluation lane's shared>=2 / 0.75 dense
    criterion is a valid capability gate (H2).

Outputs (new files only; nothing overwritten):
  legal_distance/results/citation_heritage_text_proxy_v36/text_proxy_results.json
  legal_distance/results/citation_heritage_text_proxy_v36/relation_text_baselines_results.json
"""
import json
import time
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path("/home/runner/work/LexMachina/LexMachina")
CKPT = ROOT / "legal_distance/results/174k_dense_embeddings/checkpoints"
FULL_META = ROOT / "evaluation/data/174k/metadata_174k.json"
TFIDF_DIR = ROOT / "evaluation/results/174k/embeddings"
PAIRS_ORIG = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k.json"
GRAPH = Path("/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_graph_174k.json")
OUT_DIR = ROOT / "legal_distance/results/citation_heritage_text_proxy_v36"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 42
N_BOOT = 2000
DENSE_YEARS = list(range(2000, 2024))
MAXPOS = 50000

# Text-only family (baseline the product could build without a citation graph).
TEXT_ONLY = ["full_text_tfidf_light", "regeste_tfidf",
             "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7"]
# Metadata-only (reported for context, NOT eligible as text baseline).
METADATA_ONLY = ["outcome_tfidf"]
# Citation-aware (context; cannot be built without a resolved citation graph).
CITATION_AWARE = ["cited_decisions_tfidf",
                  "cited_decisions_tfidf_outcome_hybrid_0.5",
                  "cited_decisions_tfidf_outcome_hybrid_0.7"]
TFIDF_REPS = TEXT_ONLY + METADATA_ONLY + CITATION_AWARE


def log(m):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def auc_roc(y, s):
    """AUC-ROC via Mann-Whitney U with average ranks (ties handled)."""
    y = np.asarray(y)
    s = np.asarray(s, dtype=np.float64)
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ss = s[order]
    ranks = np.empty(len(s), dtype=np.float64)
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def cos(a, b):
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------- dense
def load_dense(meta, did2idx):
    n = len(meta)
    D = np.zeros((n, 768), dtype=np.float32)
    has = np.zeros(n, dtype=bool)
    for y in DENSE_YEARS:
        m = json.load(open(CKPT / f"metadata_{y}.json"))
        E = np.load(CKPT / f"embeddings_{y}.npy")
        rows = [i for i, x in enumerate(m) if x["decision_id"] in did2idx]
        assert len(rows) == E.shape[0], f"{y}: meta rows {len(rows)} vs emb {E.shape[0]}"
        ids = [did2idx[m[i]["decision_id"]] for i in rows]
        D[ids] = E[rows]
        has[ids] = True
    return D, has


def center_project(D, has, meta):
    langs = defaultdict(list)
    for i in np.where(has)[0]:
        langs[meta[i].get("language", "unknown")].append(i)
    out = D.copy()
    for _lang, idxs in langs.items():
        out[idxs] = D[idxs] - D[idxs].mean(axis=0)
    nrm = np.linalg.norm(out, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    return out / nrm


def pca64(Dcp, has):
    X = Dcp[has].astype(np.float32)
    mu = X.mean(axis=0, keepdims=True)
    Xc = X - mu
    C = (Xc.T @ Xc) / Xc.shape[0]
    ev, evec = np.linalg.eigh(C.astype(np.float64))
    comps = evec[:, np.argsort(ev)[::-1][:64]].astype(np.float32)
    P = Xc @ comps
    nrm = np.linalg.norm(P, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    return P / nrm


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    meta = json.load(open(FULL_META))
    did2idx = {m["decision_id"]: i for i, m in enumerate(meta)}
    log(f"metadata {len(meta)}")

    log("assembling dense checkpoints ...")
    D_raw, has = load_dense(meta, did2idx)
    log(f"dense covered {int(has.sum())}")

    log("center projection ...")
    Dcp = center_project(D_raw, has, meta)

    log("PCA-64 ...")
    P64 = pca64(Dcp, has)
    covered = np.where(has)[0]
    cp64 = {meta[covered[k]]["decision_id"]: P64[k] for k in range(len(covered))}
    dense_cov = set(cp64.keys())

    log("loading citation graph ...")
    G = json.load(open(GRAPH))
    d2t = {}
    for s, ts in G.items():
        if s in did2idx:
            v = set(t for t in ts if t in did2idx)
            if v:
                d2t[s] = v

    # TF-IDF row accessor: load a rep once, keep it (total ~8*89MB = 712MB max).
    tf_cache = {}

    def tf_row(rep, did):
        arr = tf_cache.get(rep)
        if arr is None:
            arr = np.load(TFIDF_DIR / f"{rep}.npy")
            tf_cache[rep] = arr
        i = did2idx.get(did)
        if i is None:
            return None
        return arr[i]

    # score functions ---------------------------------------------------
    def sc_dense_raw(a, b):
        ia, ib = did2idx[a], did2idx[b]
        if not has[ia] or not has[ib]:
            return None
        return cos(D_raw[ia], D_raw[ib])

    def sc_dense_cp(a, b):
        ia, ib = did2idx[a], did2idx[b]
        if not has[ia] or not has[ib]:
            return None
        return cos(Dcp[ia], Dcp[ib])

    def sc_cp64(a, b):
        va, vb = cp64.get(a), cp64.get(b)
        if va is None or vb is None:
            return None
        return cos(va, vb)

    def mk_tf(rep):
        def f(a, b):
            va, vb = tf_row(rep, a), tf_row(rep, b)
            if va is None or vb is None:
                return None
            return cos(va, vb)
        return f

    dense_reps = {"dense_raw_768": sc_dense_raw, "dense_cp_768": sc_dense_cp, "dense_cp64": sc_cp64}
    tf_reps = {rep: mk_tf(rep) for rep in TFIDF_REPS}

    def sc_jac(a, b):
        A, B = d2t.get(a, set()), d2t.get(b, set())
        u = len(A | B)
        return 0.0 if u == 0 else len(A & B) / u

    all_reps = dict(dense_reps)
    all_reps.update(tf_reps)
    all_reps["citation_jaccard_full"] = sc_jac

    def evaluate(pos, neg, reps):
        row = {}
        for name, fn in reps.items():
            ys, ss = [], []
            used_p = used_n = 0
            for a, b in pos:
                v = fn(a, b)
                if v is None:
                    continue
                ys.append(1)
                ss.append(v)
                used_p += 1
            for a, b in neg:
                v = fn(a, b)
                if v is None:
                    continue
                ys.append(0)
                ss.append(v)
                used_n += 1
            row[name] = {"auc": auc_roc(ys, ss), "n_pos": used_p, "n_neg": used_n,
                         "pos_mean": float(np.mean(ss[:used_p])) if used_p else None,
                         "neg_mean": float(np.mean(ss[used_p:])) if used_n else None}
        return row

    def pair_scores(pairs, fn):
        out = []
        ok = []
        for a, b in pairs:
            v = fn(a, b)
            ok.append(v is not None)
            out.append(v if v is not None else np.nan)
        return np.asarray(out), np.asarray(ok)

    def match_matrix(pos, neg, fn_a, fn_b):
        """Return y, score_a, score_b over pairs where BOTH fns are defined."""
        y, sa, sb = [], [], []
        for lab, pairs in ((1, pos), (0, neg)):
            va, oka = pair_scores(pairs, fn_a)
            vb, okb = pair_scores(pairs, fn_b)
            for k in range(len(pairs)):
                if oka[k] and okb[k]:
                    y.append(lab)
                    sa.append(va[k])
                    sb.append(vb[k])
        return np.asarray(y), np.asarray(sa), np.asarray(sb)

    def bootstrap_margin(y, sa, sb, n_boot=N_BOOT, seed=SEED):
        rng = np.random.default_rng(seed)
        diffs = []
        n = len(y)
        for _ in range(n_boot):
            idx = rng.integers(0, n, n)
            yy = y[idx]
            if yy.sum() == 0 or yy.sum() == n:
                continue
            diffs.append(auc_roc(yy, sa[idx]) - auc_roc(yy, sb[idx]))
        diffs = np.asarray(diffs)
        return {"mean": float(diffs.mean()), "lo": float(np.percentile(diffs, 2.5)),
                "hi": float(np.percentile(diffs, 97.5)), "n_boot": int(len(diffs))}

    # ======================================================== PART A: ORIG
    log("PART A — ORIG citation-heritage pairs")
    d = json.load(open(PAIRS_ORIG))
    o_pos = [tuple(x) for x in d["positive_pairs"]]
    o_neg = [tuple(x) for x in d["negative_pairs"]]

    m_pos = [p for p in o_pos if p[0] in dense_cov and p[1] in dense_cov]
    m_neg = [n for n in o_neg if n[0] in dense_cov and n[1] in dense_cov]
    mm_pos = [p for p in m_pos if p[0] != p[1]]
    mm_neg = [n for n in m_neg if n[0] != n[1]]
    nsf_pos = [p for p in o_pos if p[0] != p[1]]
    nsf_neg = [n for n in o_neg if n[0] != n[1]]
    log(f"ORIG all={len(o_pos)}/{len(o_neg)}; matched_no_self={len(mm_pos)}/{len(mm_neg)}; all_no_self={len(nsf_pos)}/{len(nsf_neg)}")

    A = {"run_id": "LEGAL_DISTANCE_V36_CITATION_HERITAGE_TEXT_PROXY_38051603155",
         "frozen_spec": "legal_distance/results/citation_heritage_text_proxy_v36/frozen_spec.json",
         "pair_counts": {
             "ORIG_all": {"pos": len(o_pos), "neg": len(o_neg)},
             "ORIG_matched_no_self": {"pos": len(mm_pos), "neg": len(mm_neg)},
             "ORIG_all_no_self": {"pos": len(nsf_pos), "neg": len(nsf_neg)}}}

    reps_for_orig = dense_reps.copy()
    reps_for_orig.update(tf_reps)
    reps_for_orig["citation_jaccard_full"] = sc_jac

    prot = {}
    prot["ORIG_all_with_self"] = evaluate(o_pos, o_neg, reps_for_orig)
    prot["ORIG_all_no_self"] = evaluate(nsf_pos, nsf_neg, reps_for_orig)
    prot["ORIG_matched_with_self"] = evaluate(m_pos, m_neg, reps_for_orig)
    prot["ORIG_matched_no_self"] = evaluate(mm_pos, mm_neg, reps_for_orig)
    A["protocol_results"] = prot

    # H1: dense_cp64 vs max text-only on the identical matched no-self pairs
    log("H1 — dense_cp64 vs best text-only on identical matched no-self ORIG pairs")
    text_only_best_name = max(TEXT_ONLY, key=lambda r: prot["ORIG_matched_no_self"][r]["auc"])
    text_only_best = prot["ORIG_matched_no_self"][text_only_best_name]["auc"]
    h1 = {"dense_cp64_auc": prot["ORIG_matched_no_self"]["dense_cp64"]["auc"],
          "best_text_only_rep": text_only_best_name,
          "best_text_only_auc": text_only_best,
          "margin": prot["ORIG_matched_no_self"]["dense_cp64"]["auc"] - text_only_best}
    y, sa, sb = match_matrix(mm_pos, mm_neg, sc_cp64, mk_tf(text_only_best_name))
    h1["bootstrap"] = bootstrap_margin(y, sa, sb)
    h1["n_pairs_used"] = int(len(y))
    h1["threshold"] = 0.05
    h1["pass"] = bool(h1["margin"] >= 0.05)
    A["H1_ORIG_dense_vs_text_only"] = h1
    log(f"   dense_cp64={h1['dense_cp64_auc']:.4f} best_text={text_only_best_name}={text_only_best:.4f} "
        f"margin={h1['margin']:+.4f} CI=[{h1['bootstrap']['lo']:+.4f},{h1['bootstrap']['hi']:+.4f}] pass={h1['pass']}")

    # Reconciliation of the evaluation lane's 0.7296 (with-self, mixed relation, cited TF-IDF)
    A["reconciliation_eval_0.7296"] = {
        "eval_lane_frozen_value": 0.7296,
        "eval_lane_protocol": "ORIG positives/negatives, with self-pairs, max_positive_sampled=1000/max_negative_sampled=2000, cited_decisions_tfidf",
        "this_run_ORIG_all_with_self_cited_decisions_tfidf": prot["ORIG_all_with_self"]["cited_decisions_tfidf"]["auc"],
        "this_run_ORIG_all_no_self_cited_decisions_tfidf": prot["ORIG_all_no_self"]["cited_decisions_tfidf"]["auc"],
        "this_run_ORIG_matched_no_self_cited_decisions_tfidf": prot["ORIG_matched_no_self"]["cited_decisions_tfidf"]["auc"],
        "interpretation": "0.7296 is a with-self mixed-relation ORIG number on a 1000/2000 sample; the matched self-pair-free number is lower. Dense and TF-IDF are indistinguishable once pair sets and self-pairs are matched (v35). The 0.75 dense threshold is therefore not comparable to 0.7296."}

    json.dump(A, open(OUT_DIR / "text_proxy_results.json", "w"), indent=2, default=str)
    log("wrote text_proxy_results.json")

    # ======================================================== PART B: relations
    log("PART B — relation decomposition with text-only baselines")
    cited_by = defaultdict(list)
    for s, ts in d2t.items():
        for t in ts:
            cited_by[t].append(s)
    shared = Counter()
    for t, srcs in cited_by.items():
        srcs = sorted(set(srcs))
        for i in range(len(srcs)):
            for j in range(i + 1, len(srcs)):
                shared[(srcs[i], srcs[j])] += 1
    shared1 = set(shared.keys())
    shared2 = set(k for k, c in shared.items() if c >= 2)
    direct = set()
    for s, ts in d2t.items():
        for t in ts:
            if s != t:
                direct.add((s, t))
    log(f"DIRECT {len(direct)} SHARED1 {len(shared1)} SHARED2 {len(shared2)}")

    rng = np.random.default_rng(SEED)
    all_ids = list(did2idx.keys())

    def sample_pairs(pairs, cap):
        pairs = sorted(pairs)
        if len(pairs) > cap:
            idx = rng.choice(len(pairs), cap, replace=False)
            pairs = [pairs[i] for i in sorted(idx)]
        return pairs

    def rand_neg(k):
        out = set()
        while len(out) < k:
            i, j = rng.integers(0, len(all_ids), 2)
            if i == j:
                continue
            a, b = all_ids[i], all_ids[j]
            out.add((a, b) if a < b else (b, a))
        return list(out)

    def hard_neg(k):
        out = set()
        attempts = 0
        while len(out) < k and attempts < k * 200:
            i, j = rng.integers(0, len(all_ids), 2)
            if i == j:
                continue
            a, b = all_ids[i], all_ids[j]
            key = (a, b) if a < b else (b, a)
            if key in shared1:
                attempts += 1
                continue
            if (a, b) in direct or (b, a) in direct:
                attempts += 1
                continue
            out.add(key)
            attempts += 1
        return list(out)

    u_shared2 = max(1, min(MAXPOS, len(shared2)))
    u_shared1 = max(1, min(MAXPOS, len(shared1)))
    u_direct = max(1, min(MAXPOS, len(direct)))
    neg_rand = {k: rand_neg(k) for k in [u_shared1, u_shared2, u_direct]}
    neg_hard = {k: hard_neg(k) for k in [u_shared1, u_shared2, u_direct]}

    def restrict_matched(pos, neg):
        p = [(a, b) for a, b in pos if a in dense_cov and b in dense_cov]
        n = [(a, b) for a, b in neg if a in dense_cov and b in dense_cov]
        return p, n

    B = {"run_id": "LEGAL_DISTANCE_V36_RELATION_TEXT_BASELINES_38051603155",
         "frozen_spec": "legal_distance/results/citation_heritage_text_proxy_v36/frozen_spec.json",
         "graph_stats": {"sources": len(d2t), "targets": len(cited_by), "direct": len(direct),
                         "shared1": len(shared1), "shared2": len(shared2)},
         "results": {}, "matched_results": {}}

    plan = [
        ("DIRECT", sample_pairs(direct, MAXPOS), neg_rand[u_direct], neg_hard[u_direct]),
        ("SHARED1", sample_pairs(shared1, MAXPOS), neg_rand[u_shared1], neg_hard[u_shared1]),
        ("SHARED2", sample_pairs(shared2, MAXPOS), neg_rand[u_shared2], neg_hard[u_shared2]),
    ]
    reps_rel = dense_reps.copy()
    reps_rel.update(tf_reps)
    reps_rel["citation_jaccard_full"] = sc_jac

    pair_dump = {}
    for rel, pos, nrand, nhard in plan:
        log(f"  {rel}: pos={len(pos)} nrand={len(nrand)} nhard={len(nhard)}")
        B["results"][f"{rel}__NEG_rand"] = evaluate(pos, nrand, reps_rel)
        B["results"][f"{rel}__NEG_hard"] = evaluate(pos, nhard, reps_rel)
        mp, mn = restrict_matched(pos, nhard)
        B["matched_results"][f"{rel}__NEG_hard"] = evaluate(mp, mn, reps_rel)
        B["matched_results"][f"{rel}__NEG_hard"]["_pair_counts"] = {"pos": len(mp), "neg": len(mn)}
        pair_dump[f"{rel}__NEG_hard_matched"] = {
            "positives": [list(p) for p in mp],
            "negatives": [list(n) for n in mn],
        }
    json.dump(pair_dump, open(OUT_DIR / "relation_pairs_v36.json", "w"))
    log("wrote relation_pairs_v36.json")

    # H1b / H2 decisions on matched hard-neg relations
    rel_hard = B["matched_results"]

    h1b_name = max(TEXT_ONLY, key=lambda r: rel_hard["DIRECT__NEG_hard"][r]["auc"])
    d_direct = rel_hard["DIRECT__NEG_hard"]["dense_cp64"]["auc"]
    t_direct = rel_hard["DIRECT__NEG_hard"][h1b_name]["auc"]
    direct_pos_matched = [(a, b) for (a, b) in plan[0][1] if a in dense_cov and b in dense_cov]
    direct_neg_matched = [(a, b) for (a, b) in plan[0][3] if a in dense_cov and b in dense_cov]
    y, sa, sb = match_matrix(direct_pos_matched, direct_neg_matched, sc_cp64, mk_tf(h1b_name))
    h1b = {"dense_cp64_auc": d_direct, "best_text_only_rep": h1b_name, "best_text_only_auc": t_direct,
           "margin": d_direct - t_direct, "bootstrap": bootstrap_margin(y, sa, sb),
           "n_pairs_used": int(len(y)), "threshold": 0.05, "pass": bool(d_direct - t_direct >= 0.05)}
    B["H1b_DIRECT_dense_vs_text_only"] = h1b
    log(f"  H1b DIRECT dense={d_direct:.4f} text={h1b_name}={t_direct:.4f} margin={h1b['margin']:+.4f} pass={h1b['pass']}")

    jac_s2 = rel_hard["SHARED2__NEG_hard"]["citation_jaccard_full"]["auc"]
    dense_s2 = rel_hard["SHARED2__NEG_hard"]["dense_cp64"]["auc"]
    dense_direct = rel_hard["DIRECT__NEG_hard"]["dense_cp64"]["auc"]
    h2 = {"citation_jaccard_full_SHARED2_auc": jac_s2,
          "dense_cp64_SHARED2_auc": dense_s2,
          "dense_cp64_DIRECT_auc": dense_direct,
          "rule": "jaccard_SHARED2>=0.99 AND dense_SHARED2>=0.90 AND dense_DIRECT<0.75",
          "supported": bool(jac_s2 >= 0.99 and dense_s2 >= 0.90 and dense_direct < 0.75)}
    B["H2_eval_criterion_degenerate"] = h2
    log(f"  H2 supported={h2['supported']} (jaccard_S2={jac_s2:.4f} dense_S2={dense_s2:.4f} dense_DIRECT={dense_direct:.4f})")

    h1_pass = A["H1_ORIG_dense_vs_text_only"]["pass"]
    h1b_pass = h1b["pass"]
    if h1_pass and h1b_pass:
        verdict = "DENSE_TEXT_PROXY_JUSTIFIED"
    elif h1_pass or h1b_pass:
        verdict = "DENSE_TEXT_PROXY_PARTIAL"
    else:
        verdict = "DENSE_TEXT_PROXY_NOT_JUSTIFIED"
    summary = {"H1_ORIG_pass": h1_pass, "H1b_DIRECT_pass": h1b_pass,
               "H2_criterion_degenerate": h2["supported"], "verdict": verdict}
    A["verdict_summary"] = summary
    B["verdict_summary"] = summary
    json.dump(A, open(OUT_DIR / "text_proxy_results.json", "w"), indent=2, default=str)
    json.dump(B, open(OUT_DIR / "relation_text_baselines_results.json", "w"), indent=2, default=str)
    log(f"verdict={verdict}")
    log(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
