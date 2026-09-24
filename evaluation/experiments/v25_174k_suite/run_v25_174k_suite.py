#!/usr/bin/env python3
"""
v25 174k formal suite runner (frozen protocol).

Runs, per representation:
  A. 12-benchmark formal suite (frozen v16 thresholds, config hash 4323f833fa72366a)
     with HNSW-backed k-NN at full corpus density (scale adaptation frozen in protocol).
  B. Dedicated citation_heritage benchmark on the FROZEN 137,314-pair pool.
  C. v17b label-normalization hierarchy-family comparison (raw vs normalized legal_area).

Usage:
  python evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py --rep <name> [--reps all]
  python evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py --parallel 4
"""
import argparse
import json
import time
import numpy as np
import logging
from pathlib import Path
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score, roc_auc_score
import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path("/home/runner/work/LexMachina/LexMachina")
EMB_DIR = ROOT / "results/evaluation/v25_174k_formal_suite/embeddings"
SUITE_OUT = ROOT / "results/evaluation/v25_174k_formal_suite/results"
CITE_OUT = ROOT / "results/evaluation/v25_174k_citation_heritage"
V17B_OUT = ROOT / "results/evaluation/v25_174k_v17b"
FIXED_OUT = ROOT / "results/evaluation/v25_174k_formal_suite/fixed_samples"
METADATA_PATH = ROOT / "evaluation/data/174k/metadata_174k.json"
PAIRS_PATH = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json"
CORPUS_DIR = Path("/tmp/opencode/lexcorpus2/out/canonical")

SEED = 42
REPS = [
    "cited_decisions_tfidf", "outcome_tfidf", "regeste_tfidf", "full_text_tfidf_light",
    "cited_outcome_hybrid_0.5", "cited_outcome_hybrid_0.7",
    "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7",
]
HNSW_PARAMS = {"M": 16, "ef_construction": 200, "ef_search": 100}
SUBSAMPLE_HIER = 15000
SUBSAMPLE_TEMP = 30000


# ---------------------------------------------------------------- data loading
def load_metadata():
    with open(METADATA_PATH) as f:
        md = json.load(f)
    ids = [m["decision_id"] for m in md]
    lang = np.array([m.get("language") or "unknown" for m in md])
    branch = np.array([m.get("branch") or "unknown" for m in md])
    branch = np.array([b if b not in (None, "null", "") else "unknown" for b in branch])
    area = np.array([m.get("legal_area") for m in md])
    area = np.array([a if a not in (None, "null", "") else "unknown" for a in area])
    return ids, lang, branch, area


def load_pairs():
    with open(PAIRS_PATH) as f:
        d = json.load(f)
    pos = d["positive_pairs"]
    neg = d["negative_pairs"]
    return pos, neg


# Fork-shared lightweight id -> full_text[:2000] map for boilerplate benchmark.
FT2K = {}


def load_corpus_texts(needed_ids):
    global FT2K
    wanted = set(needed_ids)
    FT2K = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_*.jsonl")):
        with open(year_file) as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                did = r["decision_id"]
                if did in wanted:
                    t = r.get("full_text") or ""
                    FT2K[did] = t[:2000]
                    if len(FT2K) >= len(wanted):
                        pass
    logger.info(f"loaded {len(FT2K)} full_text[:2000] entries")


def get_text(_recs, did, kind):
    return FT2K.get(did, "")


# ---------------------------------------------------------------- data transforms
def normalize_labels(labels):
    """Apply v17b conservative cross-lingual legal_area normalization (identity for coarse)."""
    import sys
    sys.path.insert(0, str(ROOT / "evaluation/experiments"))
    from legal_area_normalize import normalize_legal_area
    return np.array([normalize_legal_area(x) if x not in (None, "unknown") else x for x in labels])


def make_hnsw(emb, ef_search=100):
    import hnswlib
    n, d = emb.shape
    idx = hnswlib.Index(space="cosine", dim=d)
    idx.init_index(max_elements=n, ef_construction=HNSW_PARAMS["ef_construction"], M=HNSW_PARAMS["M"])
    idx.set_num_threads(1)
    idx.add_items(emb)
    idx.set_ef(ef_search)
    return idx


def query_all(idx, emb, k=20, batch=5000):
    n, d = emb.shape
    k = min(k, n - 1)
    all_idx = np.zeros((n, k), dtype=np.int64)
    for s in range(0, n, batch):
        e = emb[s:s + batch]
        if len(e) == 0:
            continue
        lbl, dist = idx.knn_query(e, k=k)
        all_idx[s:s + batch] = lbl
    return all_idx


# ---------------------------------------------------------------- benchmarks (frozen v16 semantics)
def bm_citation_heritage(emb, ids, pos, neg):
    id2i = {did: i for i, did in enumerate(ids)}
    p = [(id2i[a], id2i[b]) for a, b in pos if a in id2i and b in id2i]
    ng = [(id2i[a], id2i[b]) for a, b in neg if a in id2i and b in id2i]
    if len(p) < 10 or len(ng) < 10:
        return {"status": "SKIP", "note": f"pos={len(p)} neg={len(ng)}"}
    pos_sims = np.array([float(np.dot(emb[i], emb[j])) for i, j in p])
    neg_sims = np.array([float(np.dot(emb[i], emb[j])) for i, j in ng])
    labels = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    scores = np.concatenate([pos_sims, neg_sims])
    auc = float(roc_auc_score(labels, scores))
    # nn citation rate from all-points k=10 (computed outside, passed in)
    return {
        "benchmark_id": "citation_heritage",
        "status": "PASS" if auc >= 0.65 else "FAIL",
        "metrics": {
            "auc_roc": auc,
            "n_positive": len(p),
            "n_negative": len(ng),
            "pos_mean_similarity": float(pos_sims.mean()),
            "neg_mean_similarity": float(neg_sims.mean()),
            "similarity_gap": float(pos_sims.mean() - neg_sims.mean()),
        },
        "threshold": 0.65,
    }


def bm_branch_knn_tf_metadata(emb, branch, nn10):
    n = len(branch)
    accs = {1: [], 3: [], 5: [], 10: []}
    for i in range(n):
        for k in [1, 3, 5, 10]:
            nb = branch[nn10[i][:k]]
            accs[k].append(float(np.sum(nb == branch[i])) / k)
    res = {f"knn_accuracy@{k}": float(np.mean(accs[k])) for k in accs}
    branch_knn = {
        "benchmark_id": "branch_knn",
        "status": "PASS" if res.get("knn_accuracy@5", 0) > 0.6333 else "FAIL",
        "metrics": res,
        "threshold": 0.6333,
    }
    tf = {
        "benchmark_id": "tf_metadata_human_indexing",
        "status": "PASS" if res.get("knn_accuracy@5", 0) >= 0.8 else "FAIL",
        "metrics": {f"recall@{k}": res[f"knn_accuracy@{k}"] for k in accs},
        "threshold": 0.8,
    }
    return branch_knn, tf


def bm_adversarial(emb, lang, branch, nn20):
    n = len(lang)
    ld, bc = [], []
    for i in range(n):
        nlang = lang[nn20[i]]
        nbranch = branch[nn20[i]]
        ld.append(float(np.sum(nlang == lang[i])) / len(nlang))
        bc.append(float(np.sum(nbranch == branch[i])) / len(nbranch))
    ld_mean, bc_mean = float(np.mean(ld)), float(np.mean(bc))
    status = "PASS" if ld_mean < 0.85 and bc_mean > 0.3 else "FAIL"
    return {
        "benchmark_id": "adversarial_falsification",
        "status": status,
        "metrics": {"language_dominance_mean": ld_mean, "branch_coherence_mean": bc_mean},
        "threshold": {"language_dominance_max": 0.85, "branch_coherence_min": 0.3},
    }


def bm_boilerplate(emb, recs, ids, n_pairs=200):
    rng = np.random.RandomState(SEED)
    idxs = rng.choice(len(ids), size=min(n_pairs * 2, len(ids)), replace=False)
    text_sims, emb_sims = [], []
    for i in range(0, len(idxs) - 1, 2):
        a, b = int(idxs[i]), int(idxs[i + 1])
        wa = set(get_text(recs, ids[a], "full_text").lower().split())
        wb = set(get_text(recs, ids[b], "full_text").lower().split())
        if not wa or not wb:
            continue
        jac = len(wa & wb) / max(len(wa | wb), 1)
        es = float(np.dot(emb[a], emb[b]))
        text_sims.append(jac)
        emb_sims.append(es)
    if len(text_sims) < 10:
        return {"status": "SKIP", "note": "insufficient pairs"}
    corr = float(np.corrcoef(text_sims, emb_sims)[0, 1])
    return {
        "benchmark_id": "boilerplate_resistance_real_corpus",
        "status": "PASS" if corr > 0.1 else "FAIL",
        "metrics": {"text_emb_correlation": corr, "n_pairs": len(text_sims)},
        "threshold": 0.1,
    }


def bm_multilingual(emb, lang, branch):
    rng = np.random.RandomState(SEED)
    n = len(emb)
    cross_sb, same_sb, cross_b = [], [], []
    for _ in range(500):
        i, j = int(rng.randint(0, n)), int(rng.randint(0, n))
        if i == j:
            continue
        sim = float(np.dot(emb[i], emb[j]))
        if branch[i] == branch[j] and lang[i] != lang[j]:
            cross_sb.append(sim)
        elif branch[i] == branch[j] and lang[i] == lang[j]:
            same_sb.append(sim)
        elif branch[i] != branch[j]:
            cross_b.append(sim)
    if not cross_sb or not same_sb or not cross_b:
        return {"status": "SKIP", "note": "insufficient pairs"}
    csp, slp, cbp = float(np.mean(cross_sb)), float(np.mean(same_sb)), float(np.mean(cross_b))
    gap, sep = abs(csp - slp), csp - cbp
    status = "PASS" if sep >= 0 and gap < 0.2 else "FAIL"
    return {
        "benchmark_id": "multilingual_invariance",
        "status": status,
        "metrics": {"cross_lang_same_branch": csp, "same_lang_same_branch": slp,
                    "cross_branch": cbp, "invariance_gap": gap, "separation": sep},
        "threshold": {"separation_min": 0, "invariance_gap_max": 0.2},
    }


def bm_cross_lang_pairs(emb, lang, branch):
    rng = np.random.RandomState(SEED)
    n = len(emb)
    cross_sb, cross_b = [], []
    for _ in range(500):
        i, j = int(rng.randint(0, n)), int(rng.randint(0, n))
        if i == j:
            continue
        sim = float(np.dot(emb[i], emb[j]))
        if branch[i] == branch[j] and lang[i] != lang[j]:
            cross_sb.append(sim)
        elif branch[i] != branch[j]:
            cross_b.append(sim)
    if not cross_sb or not cross_b:
        return {"status": "SKIP"}
    csp, cbp = float(np.mean(cross_sb)), float(np.mean(cross_b))
    sep = csp - cbp
    return {
        "benchmark_id": "cross_language_pairs",
        "status": "PASS" if sep > 0 else "FAIL",
        "metrics": {"cross_lang_same_branch": csp, "cross_branch": cbp, "separation": sep},
        "threshold": 0,
    }


def bm_collapse(emb):
    rng = np.random.RandomState(SEED)
    n = min(500, len(emb))
    idxs = rng.choice(len(emb), n, replace=False)
    sub = emb[idxs]
    sims = np.dot(sub, sub.T)
    mask = np.triu(np.ones_like(sims, dtype=bool), k=1)
    upper = sims[mask]
    mean_sim, std_sim = float(np.mean(upper)), float(np.std(upper))
    collapsed = mean_sim >= 0.99 or std_sim <= 0.01
    return {
        "benchmark_id": "collapse_check",
        "status": "FAIL" if collapsed else "PASS",
        "metrics": {"mean_similarity": mean_sim, "std_similarity": std_sim, "collapsed": collapsed},
        "threshold": {"mean_sim_max": 0.99, "std_sim_min": 0.01},
    }


def bm_temporal(emb, branch, subsample_idx):
    rng = np.random.RandomState(SEED)
    sub_emb = emb[subsample_idx]
    sub_br = branch[subsample_idx]
    scores = []
    for s in range(5):
        perm = rng.choice(len(sub_emb), size=len(sub_emb), replace=False)
        se = sub_emb[perm]
        sb = sub_br[perm]
        idx = make_hnsw(se, ef_search=100)
        lbl, _ = idx.knn_query(se, k=min(6, len(se)))
        nn_br = sb[lbl[:, 1:]]
        acc = float(np.mean(np.sum(nn_br == sb[:, None], axis=1) / nn_br.shape[1]))
        scores.append(acc)
    std = float(np.std(scores))
    return {
        "benchmark_id": "temporal_stability",
        "status": "PASS" if std < 0.1 else "FAIL",
        "metrics": {"mean_knn_score": float(np.mean(scores)), "std_knn_score": std, "split_scores": scores},
        "threshold": 0.1,
    }


def cluster_purity(emb, labels, k):
    km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
    cl = km.fit_predict(emb)
    total = len(labels)
    parts = []
    for c in range(k):
        m = cl == c
        if m.any():
            _, counts = np.unique(labels[m], return_counts=True)
            parts.append(float(m.sum() / total * counts.max() / m.sum()))
    return float(np.sum(parts)) if parts else 0.0


def bm_hierarchy(emb, area_labels):
    valid = area_labels != "unknown"
    if not valid.any():
        return {"status": "SKIP", "note": "no valid labels"}
    ve, vl = emb[valid], area_labels[valid]
    best_purity, best_nmi = 0.0, 0.0
    ks = [5, 8, 10, 15, 20, 25, 30]
    ks = [k for k in ks if k < len(ve) and k <= len(np.unique(vl))]
    for k in ks:
        km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
        labels = km.fit_predict(ve)
        nmi = float(normalized_mutual_info_score(vl, labels))
        total = len(vl)
        parts = []
        for c in range(k):
            m = labels == c
            if m.any():
                _, counts = np.unique(vl[m], return_counts=True)
                parts.append(float(m.sum() / total * counts.max() / m.sum()))
        purity = float(np.sum(parts)) if parts else 0.0
        if purity > best_purity:
            best_purity, best_nmi = purity, nmi
    return {
        "benchmark_id": "hierarchy_coherence",
        "status": "PASS" if best_purity > 0.7 and best_nmi > 0.3 else "FAIL",
        "metrics": {"best_purity": best_purity, "best_nmi": best_nmi, "k_values_tried": ks},
        "threshold": {"purity_min": 0.7, "nmi_min": 0.3},
    }


def bm_zoom(emb, area_labels):
    valid = area_labels != "unknown"
    if not valid.any():
        return {"status": "SKIP"}
    ve, vl = emb[valid], area_labels[valid]

    def purity(emb_, labels_, k):
        km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
        cl = km.fit_predict(emb_)
        total = len(labels_)
        ps = []
        for c in range(k):
            m = cl == c
            if m.any():
                _, counts = np.unique(labels_[m], return_counts=True)
                ps.append(float(m.sum() / total * counts.max() / m.sum()))
        return float(np.sum(ps)) if ps else 0.0

    coarse = purity(ve, vl, 8)
    fine = purity(ve, vl, 25)
    improvement = ((fine - coarse) / max(coarse, 0.001)) * 100
    return {
        "benchmark_id": "zoom_coherence",
        "status": "PASS" if improvement > 0 else "FAIL",
        "metrics": {"coarse_purity": coarse, "fine_purity": fine, "improvement_pct": improvement},
        "threshold": 0,
    }


def bm_legal_area(emb, area_labels):
    valid = area_labels != "unknown"
    if not valid.any():
        return {"status": "SKIP"}
    ve, vl = emb[valid], area_labels[valid]
    k = min(50, len(np.unique(vl)))
    km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
    labels = km.fit_predict(ve)
    nmi = float(normalized_mutual_info_score(vl, labels))
    total = len(vl)
    parts = []
    for c in range(k):
        m = labels == c
        if m.any():
            _, counts = np.unique(vl[m], return_counts=True)
            parts.append(float(m.sum() / total * counts.max() / m.sum()))
    purity = float(np.mean(parts)) if parts else 0.0
    return {
        "benchmark_id": "legal_area_clustering",
        "status": "PASS" if purity > 0.5 else "FAIL",
        "metrics": {"overall_purity": purity, "nmi": nmi, "num_areas": len(np.unique(vl))},
        "threshold": 0.5,
    }


# ---------------------------------------------------------------- frozen subsamples
def get_fixed_samples(branch, area):
    FIXED_OUT.mkdir(parents=True, exist_ok=True)
    hier_path = FIXED_OUT / "hierarchy_subsample_15000_seed42.npy"
    temp_path = FIXED_OUT / "temporal_subsample_30000_seed42.npy"
    if hier_path.exists():
        hier = np.load(hier_path)
    else:
        known = np.where(area != "unknown")[0]
        # stratify by branch
        rng = np.random.RandomState(SEED)
        chosen = []
        for b in np.unique(branch[known]):
            cand = known[branch[known] == b]
            per = max(1, int(round(SUBSAMPLE_HIER * len(cand) / len(known))))
            chosen.append(rng.choice(cand, size=min(per, len(cand)), replace=False))
        hier = np.concatenate(chosen)
        rng.shuffle(hier)
        hier = hier[:SUBSAMPLE_HIER]
        np.save(hier_path, hier)
    if temp_path.exists():
        temp = np.load(temp_path)
    else:
        rng = np.random.RandomState(SEED)
        temp = rng.choice(len(branch), size=SUBSAMPLE_TEMP, replace=False)
        np.save(temp_path, temp)
    return hier.astype(int), temp.astype(int)


# ---------------------------------------------------------------- main
GLOBALS = {}


def _worker(r):
    return run_rep(r, GLOBALS["ids"], GLOBALS["lang"], GLOBALS["branch"], GLOBALS["area"],
                   GLOBALS["pos"], GLOBALS["neg"], GLOBALS["hier_idx"], GLOBALS["temp_idx"])
def run_rep(name, ids, lang, branch, area, pos, neg, hier_idx, temp_idx):
    t0 = time.time()
    logger.info(f"[{name}] loading embedding...")
    emb = np.load(EMB_DIR / f"{name}.npy")
    n = emb.shape[0]
    logger.info(f"[{name}] {emb.shape}")

    logger.info(f"[{name}] building HNSW + all-points queries...")
    idx = make_hnsw(emb)
    nn20 = query_all(idx, emb, k=20)
    nn10 = nn20[:, :10]

    results = []
    r = bm_citation_heritage(emb, ids, pos, neg)
    r["nn_citation_rate@10"] = compute_nn_citation_rate(ids, nn10, pos)
    results.append(r)
    bk, tf = bm_branch_knn_tf_metadata(emb, branch, nn10)
    results.append(bk)
    results.append(tf)
    results.append(bm_adversarial(emb, lang, branch, nn20))
    results.append(bm_boilerplate(emb, None, ids))
    results.append(bm_multilingual(emb, lang, branch))
    results.append(bm_cross_lang_pairs(emb, lang, branch))
    results.append(bm_collapse(emb))
    results.append(bm_temporal(emb, branch, temp_idx))

    # hierarchy family on frozen subsample with RAW labels
    sub_emb = emb[hier_idx]
    sub_area = area[hier_idx]
    results.append(bm_hierarchy(sub_emb, sub_area))
    results.append(bm_zoom(sub_emb, sub_area))
    results.append(bm_legal_area(sub_emb, sub_area))

    n_pass = sum(1 for r_ in results if r_["status"] == "PASS")
    n_fail = sum(1 for r_ in results if r_["status"] == "FAIL")
    n_skip = sum(1 for r_ in results if r_["status"] == "SKIP")

    suite = {
        "representation": name,
        "n_rows": n,
        "n_passed": n_pass,
        "n_failed": n_fail,
        "n_skipped": n_skip,
        "total_benchmarks": len(results),
        "benchmarks": results,
        "hnsw_params": HNSW_PARAMS,
        "duration_seconds": round(time.time() - t0, 1),
        "config_hash_suite": "4323f833fa72366a",
    }
    SUITE_OUT.mkdir(parents=True, exist_ok=True)
    with open(SUITE_OUT / f"{name}.json", "w") as f:
        json.dump(suite, f, indent=2)

    # dedicated citation heritage result (subset of suite metrics, standalone file)
    CITE_OUT.mkdir(parents=True, exist_ok=True)
    with open(CITE_OUT / f"{name}.json", "w") as f:
        json.dump({
            "representation": name,
            "benchmark": "citation_heritage_dedicated",
            "pairs_file": str(PAIRS_PATH),
            "status": r["status"],
            "metrics": r["metrics"],
            "nn_citation_rate@10": r["nn_citation_rate@10"],
            "threshold": 0.65,
            "duration_seconds": round(time.time() - t0, 1),
        }, f, indent=2)

    # v17b: normalized labels on same frozen subsample
    norm_area = normalize_labels(area)
    sub_norm = norm_area[hier_idx]
    V17B_OUT.mkdir(parents=True, exist_ok=True)
    v17b = {
        "representation": name,
        "sample": "hierarchy_subsample_15000_seed42 (fixed)",
        "raw": {
            "hierarchy_coherence": bm_hierarchy(sub_emb, sub_area),
            "zoom_coherence": bm_zoom(sub_emb, sub_area),
            "legal_area_clustering": bm_legal_area(sub_emb, sub_area),
        },
        "normalized": {
            "hierarchy_coherence": bm_hierarchy(sub_emb, sub_norm),
            "zoom_coherence": bm_zoom(sub_emb, sub_norm),
            "legal_area_clustering": bm_legal_area(sub_emb, sub_norm),
        },
    }
    with open(V17B_OUT / f"{name}.json", "w") as f:
        json.dump(v17b, f, indent=2)

    logger.info(f"[{name}] DONE: {n_pass} PASS / {n_fail} FAIL / {n_skip} SKIP ({suite['duration_seconds']}s)")
    return suite


def compute_nn_citation_rate(ids, nn10, pos):
    id2i = {did: i for i, did in enumerate(ids)}
    cited_by = {}
    for a, b in pos:
        if a in id2i and b in id2i:
            cited_by.setdefault(id2i[a], set()).add(id2i[b])
    hits = 0
    for i in range(len(ids)):
        cs = cited_by.get(i, set())
        if cs and any(j in cs for j in nn10[i]):
            hits += 1
    denom = max(sum(1 for i in range(len(ids)) if cited_by.get(i)), 1)
    return float(hits) / denom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", default=None, help="single representation name")
    ap.add_argument("--parallel", type=int, default=1)
    args = ap.parse_args()

    ids, lang, branch, area = load_metadata()
    pos, neg = load_pairs()
    logger.info(f"metadata={len(ids)} pos={len(pos)} neg={len(neg)}")
    hier_idx, temp_idx = get_fixed_samples(branch, area)
    logger.info(f"hier subsample={len(hier_idx)} temp subsample={len(temp_idx)}")

    reps = [args.rep] if args.rep else REPS
    reps = [r for r in reps if (EMB_DIR / f"{r}.npy").exists()]
    if not reps:
        logger.error("no embeddings found")
        return

    # per-rep loading of texts is heavy; load corpus once (lazy dict)
    load_corpus_texts(ids)
    logger.info(f"corpus texts loaded: {len(FT2K)}")

    if args.parallel > 1 and len(reps) > 1:
        from multiprocessing import Pool
        GLOBALS.update(ids=ids, lang=lang, branch=branch, area=area, pos=pos, neg=neg,
                       hier_idx=hier_idx, temp_idx=temp_idx)
        with Pool(args.parallel) as pool:
            pool.map(_worker, reps)
    else:
        for r in reps:
            run_rep(r, ids, lang, branch, area, pos, neg, hier_idx, temp_idx)


if __name__ == "__main__":
    main()