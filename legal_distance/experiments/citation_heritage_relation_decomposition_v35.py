#!/usr/bin/env python3
"""Legal-distance v35 — citation-heritage relation decomposition (see frozen_spec_relation_decomposition.json)."""
import json, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import numpy as np

ROOT = Path("/home/runner/work/LexMachina/LexMachina")
CKPT = ROOT / "legal_distance/results/174k_dense_embeddings/checkpoints"
FULL_META = ROOT / "evaluation/data/174k/metadata_174k.json"
TFIDF_DIR = ROOT / "evaluation/results/174k/embeddings"
GRAPH = Path("/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_graph_174k.json")
OUT_DIR = ROOT / "legal_distance/results/citation_heritage_fairness_audit_v35"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 42
MAXPOS, MAXNEG = 50000, 50000
DENSE_YEARS = list(range(2000, 2024))


def log(m): print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {m}", flush=True)


def auc_roc(y, s):
    y = np.asarray(y); s = np.asarray(s, float)
    npos = int(y.sum()); nneg = len(y) - npos
    if npos == 0 or nneg == 0: return float("nan")
    order = np.argsort(s, kind="mergesort"); ss = s[order]
    ranks = np.empty(len(s)); i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]: j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0; i = j + 1
    return float((ranks[y == 1].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def load_dense(meta, did2idx):
    n = len(meta); D = np.zeros((n, 768), np.float32); has = np.zeros(n, bool)
    for y in DENSE_YEARS:
        m = json.load(open(CKPT / f"metadata_{y}.json")); E = np.load(CKPT / f"embeddings_{y}.npy")
        rows = [i for i, x in enumerate(m) if x["decision_id"] in did2idx]
        if len(rows) != E.shape[0]: log(f"  {y}: row mismatch")
        ids = [did2idx[m[i]["decision_id"]] for i in rows]
        D[ids] = E[rows]; has[ids] = True
    return D, has


def main():
    t0 = time.time()
    meta = json.load(open(FULL_META)); did2idx = {m["decision_id"]: i for i, m in enumerate(meta)}
    log("loading dense ..."); D, has = load_dense(meta, did2idx)
    # center projection
    langs = defaultdict(list)
    for i in np.where(has)[0]: langs[meta[i].get("language", "?")].append(i)
    Dcp = D.copy()
    for lg, idxs in langs.items(): Dcp[idxs] = D[idxs] - D[idxs].mean(0)
    nrm = np.linalg.norm(Dcp, axis=1, keepdims=True); nrm[nrm == 0] = 1; Dcp /= nrm
    # pca64
    X = Dcp[has].astype(np.float32); mu = X.mean(0); Xc = X - mu
    C = (Xc.T @ Xc) / Xc.shape[0]
    ev, evec = np.linalg.eigh(C.astype(np.float64)); comps = evec[:, np.argsort(ev)[::-1][:64]].astype(np.float32)
    P = Xc @ comps; nrm = np.linalg.norm(P, axis=1, keepdims=True); nrm[nrm == 0] = 1; P /= nrm
    cp64 = {meta[i]["decision_id"]: P[k] for k, i in enumerate(np.where(has)[0])}
    log("loading tfidf ...")
    tarr = np.load(TFIDF_DIR / "cited_decisions_tfidf.npy", mmap_mode="r")
    log("loading graph ...")
    G = json.load(open(GRAPH))
    d2t = {}
    for s, ts in G.items():
        if s in did2idx:
            v = set(t for t in ts if t in did2idx)
            if v: d2t[s] = v
    log(f"graph decisions in meta: {len(d2t)}")
    # shared counts
    cited_by = defaultdict(list)
    for s, ts in d2t.items():
        for t in ts: cited_by[t].append(s)
    from collections import Counter
    shared = Counter()
    for t, srcs in cited_by.items():
        srcs = sorted(set(srcs))
        for i in range(len(srcs)):
            for j in range(i + 1, len(srcs)):
                a, b = srcs[i], srcs[j]
                shared[(a, b)] += 1
    shared1 = set(shared.keys())
    shared2 = set(k for k, c in shared.items() if c >= 2)
    direct = set()
    for s, ts in d2t.items():
        for t in ts:
            if s != t: direct.add((s, t))
    log(f"DIRECT {len(direct)} SHARED1 {len(shared1)} SHARED2 {len(shared2)}")

    rng = np.random.default_rng(SEED)
    all_ids = list(did2idx.keys())

    def sample_pairs(pairs, cap):
        pairs = sorted(pairs)
        if len(pairs) > cap:
            idx = rng.choice(len(pairs), cap, replace=False)
            pairs = [pairs[i] for i in sorted(idx)]
        return pairs

    # negatives
    def rand_neg(k):
        out = set()
        while len(out) < k:
            i, j = rng.integers(0, len(all_ids), 2)
            if i == j: continue
            a, b = all_ids[i], all_ids[j]
            out.add((a, b) if a < b else (b, a))
        return list(out)

    def hard_neg(k):
        out = set(); attempts = 0
        while len(out) < k and attempts < k * 200:
            i, j = rng.integers(0, len(all_ids), 2)
            if i == j: continue
            a, b = all_ids[i], all_ids[j]
            key = (a, b) if a < b else (b, a)
            if key in shared1: attempts += 1; continue
            if (a, b) in direct or (b, a) in direct: attempts += 1; continue
            out.add(key); attempts += 1
        return list(out)

    n_pos = {k: len(v) for k, v in [("DIRECT", direct), ("SHARED1", shared1), ("SHARED2", shared2)]}
    u_shared2 = max(1, min(MAXPOS, len(shared2)))
    u_shared1 = max(1, min(MAXPOS, len(shared1)))
    neg_rand = {k: rand_neg(k) for k in [u_shared1, u_shared2, min(MAXPOS, len(direct))]}
    neg_hard = {k: hard_neg(k) for k in [u_shared1, u_shared2, min(MAXPOS, len(direct))]}
    log(f"positives: {n_pos}; neg sizes rand={ {k:len(v) for k,v in neg_rand.items()} }")
    log(f"hard neg sizes={ {k:len(v) for k,v in neg_hard.items()} }")

    def sc_dense_raw(a, b):
        ia, ib = did2idx[a], did2idx[b]
        if not has[ia] or not has[ib]: return None
        va, vb = D[ia], D[ib]; return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
    def sc_dense_cp(a, b):
        ia, ib = did2idx[a], did2idx[b]
        if not has[ia] or not has[ib]: return None
        va, vb = Dcp[ia], Dcp[ib]; return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
    def sc_cp64(a, b):
        va, vb = cp64.get(a), cp64.get(b)
        if va is None or vb is None: return None
        return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
    def sc_tfidf(a, b):
        ia, ib = did2idx[a], did2idx[b]
        va, vb = np.asarray(tarr[ia], float), np.asarray(tarr[ib], float)
        return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
    def sc_jac(a, b):
        A, B = d2t.get(a, set()), d2t.get(b, set())
        u = len(A | B)
        return 0.0 if u == 0 else len(A & B) / u

    reps = {"dense_raw_768": sc_dense_raw, "dense_cp_768": sc_dense_cp, "dense_cp64": sc_cp64,
            "tfidf_cited_decisions_128": sc_tfidf, "citation_jaccard_full": sc_jac}

    def evaluate(pos, neg):
        row = {}
        for name, fn in reps.items():
            ys, ss = [], []; used_p = used_n = 0
            for a, b in pos:
                v = fn(a, b)
                if v is None: continue
                ys.append(1); ss.append(v); used_p += 1
            for a, b in neg:
                v = fn(a, b)
                if v is None: continue
                ys.append(0); ss.append(v); used_n += 1
            row[name] = {"auc": auc_roc(ys, ss), "n_pos": used_p, "n_neg": used_n,
                         "pos_mean": float(np.mean(ss[:used_p])) if used_p else None,
                         "neg_mean": float(np.mean(ss[used_p:])) if used_n else None}
        return row

    out = {"run_id": "LEGAL_DISTANCE_V35_CITATION_HERITAGE_RELATION_DECOMPOSITION_38039706350",
           "frozen_spec": "legal_distance/results/citation_heritage_fairness_audit_v35/frozen_spec_relation_decomposition.json",
           "graph_stats": {"sources": len(d2t), "targets": len(cited_by), "direct": len(direct),
                           "shared1": len(shared1), "shared2": len(shared2)},
           "results": {}}

    # DIRECT
    dp = sample_pairs(direct, MAXPOS)
    log(f"evaluating DIRECT n={len(dp)}")
    out["results"]["DIRECT__NEG_rand"] = evaluate(dp, neg_rand[min(MAXPOS, len(direct))])
    out["results"]["DIRECT__NEG_hard"] = evaluate(dp, neg_hard[min(MAXPOS, len(direct))])
    # SHARED1
    s1 = sample_pairs(shared1, MAXPOS)
    log(f"evaluating SHARED1 n={len(s1)}")
    out["results"]["SHARED1__NEG_rand"] = evaluate(s1, neg_rand[u_shared1])
    out["results"]["SHARED1__NEG_hard"] = evaluate(s1, neg_hard[u_shared1])
    # SHARED2
    s2 = sample_pairs(shared2, MAXPOS)
    log(f"evaluating SHARED2 n={len(s2)}")
    out["results"]["SHARED2__NEG_rand"] = evaluate(s2, neg_rand[u_shared2])
    out["results"]["SHARED2__NEG_hard"] = evaluate(s2, neg_hard[u_shared2])

    for key, row in out["results"].items():
        log(f"--- {key}")
        for name, m in row.items():
            log(f"    {name:32s} AUC={m['auc']:.4f} (p={m['n_pos']},n={m['n_neg']})")

    out["duration_seconds"] = time.time() - t0
    json.dump(out, open(OUT_DIR / "relation_decomposition_results.json", "w"), indent=2, default=str)
    log("wrote relation_decomposition_results.json")


if __name__ == "__main__":
    main()
