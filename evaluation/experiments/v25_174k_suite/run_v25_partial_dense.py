#!/usr/bin/env python3
"""
v25 174k formal suite runner for PARTIAL dense embeddings (years 2000-2002 ~7,652 decisions).

Runs the frozen v25 protocol benchmarks on the partial dense embeddings that have landed.
Uses exact k-NN (sklearn) since n=7,652 is small enough.

This gives early signal on dense embedding quality before full 174k lands.
"""

import argparse
import json
import time
import numpy as np
import logging
from pathlib import Path
from collections import Counter
from sklearn.metrics import normalized_mutual_info_score, roc_auc_score
from sklearn.neighbors import NearestNeighbors
import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path("/home/runner/work/LexMachina/LexMachina")
PARTIAL_EMB_DIR = ROOT / "results/evaluation/v25_174k_formal_suite/embeddings"
PARTIAL_META = PARTIAL_EMB_DIR / "metadata_partial_174k.json"
PARTIAL_EMB = PARTIAL_EMB_DIR / "center_projected_768dim_partial_174k.npy"
SUITE_OUT = ROOT / "results/evaluation/v25_174k_formal_suite/partial_dense_results"
CITE_PAIRS_PATH = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json"
CORPUS_DIR = Path("/tmp/opencode/lexcorpus2/out/canonical")

SEED = 42
REP_NAME = "center_projected_768dim_partial_2000_2002"
HNSW_PARAMS = {"M": 16, "ef_construction": 200, "ef_search": 100}
SUBSAMPLE_HIER = 5000  # Smaller for partial data
SUBSAMPLE_TEMP = 5000

# ---------------------------------------------------------------- data loading
def load_partial_metadata():
    with open(PARTIAL_META) as f:
        md = json.load(f)
    ids = [m["decision_id"] for m in md]
    lang = np.array([m.get("language") or "unknown" for m in md])
    branch = np.array([m.get("branch") or "unknown" for m in md])
    branch = np.array([b if b not in (None, "null", "") else "unknown" for b in branch])
    area = np.array([m.get("legal_area") for m in md])
    area = np.array([a if a not in (None, "null", "") else "unknown" for a in area])
    year = np.array([m.get("year") for m in md])
    return ids, lang, branch, area, year

def load_citation_pairs():
    with open(CITE_PAIRS_PATH) as f:
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
    """Apply v17b conservative cross-lingual legal_area normalization."""
    import sys
    sys.path.insert(0, str(ROOT / "evaluation/experiments"))
    from legal_area_normalize import normalize_legal_area
    return np.array([normalize_legal_area(x) if x not in (None, "unknown") else x for x in labels])

def make_hnsw(emb, ef_search=100):
    """For partial data, use exact sklearn NearestNeighbors instead of HNSW."""
    return NearestNeighbors(n_neighbors=min(20, len(emb)-1), metric='cosine', algorithm='brute').fit(emb)

def query_all(idx, emb, k=20, batch=5000):
    n, d = emb.shape
    k = min(k, n - 1)
    all_idx = np.zeros((n, k), dtype=np.int64)
    for s in range(0, n, batch):
        e = emb[s:s + batch]
        if len(e) == 0:
            continue
        distances, lbl = idx.kneighbors(e, n_neighbors=k+1)  # +1 to skip self
        all_idx[s:s + batch] = lbl[:, 1:]  # skip self
    return all_idx

# ---------------------------------------------------------------- benchmarks (frozen v16 semantics)
def bm_citation_heritage(emb, ids, pos, neg):
    id2i = {did: i for i, did in enumerate(ids)}
    p = [(id2i[a], id2i[b]) for a, b in pos if a in id2i and b in id2i]
    ng = [(id2i[a], id2i[b]) for a, b in neg if a in id2i and b in id2i]
    if len(p) < 10 or len(ng) < 10:
        return {"status": "SKIP", "note": f"insufficient pairs in partial data: pos={len(p)} neg={len(ng)}", "metrics": {}}
    pos_sims = np.array([float(np.dot(emb[i], emb[j])) for i, j in p])
    neg_sims = np.array([float(np.dot(emb[i], emb[j])) for i, j in ng])
    labels = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    scores = np.concatenate([pos_sims, neg_sims])
    auc = float(roc_auc_score(labels, scores))
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
        return {"status": "SKIP", "note": "insufficient pairs or no corpus texts available", "metrics": {}}
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
        distances, lbl = idx.kneighbors(se, n_neighbors=min(6, len(se)))
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
    from sklearn.cluster import KMeans
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
        from sklearn.cluster import KMeans
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
        from sklearn.cluster import KMeans
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
    from sklearn.cluster import KMeans
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
    FIXED_OUT = ROOT / "results/evaluation/v25_174k_formal_suite/fixed_samples"
    FIXED_OUT.mkdir(parents=True, exist_ok=True)
    hier_path = FIXED_OUT / "partial_hierarchy_subsample_5000_seed42.npy"
    temp_path = FIXED_OUT / "partial_temporal_subsample_5000_seed42.npy"
    if hier_path.exists():
        hier = np.load(hier_path)
    else:
        known = np.where(area != "unknown")[0]
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
def run_partial_dense_evaluation():
    t0 = time.time()
    
    logger.info("=" * 70)
    logger.info("v25 FORMAL SUITE - PARTIAL DENSE EMBEDDINGS (2000-2002)")
    logger.info("=" * 70)
    
    # Load data
    ids, lang, branch, area, year = load_partial_metadata()
    pos, neg = load_citation_pairs()
    logger.info(f"metadata={len(ids)} pos={len(pos)} neg={len(neg)}")
    
    # Load embedding
    logger.info(f"Loading embedding from {PARTIAL_EMB}...")
    emb = np.load(PARTIAL_EMB)
    n = emb.shape[0]
    logger.info(f"Embedding shape: {emb.shape}")
    
    # L2 normalize
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    emb = emb / norms
    logger.info("L2 normalized embeddings")
    
    # Get frozen subsamples
    hier_idx, temp_idx = get_fixed_samples(branch, area)
    logger.info(f"hier subsample={len(hier_idx)} temp subsample={len(temp_idx)}")
    
    # Build exact NN index (since n=7652 is small)
    logger.info("Building exact NN index (sklearn brute force)...")
    nn_idx = make_hnsw(emb)
    nn20 = query_all(nn_idx, emb, k=20)
    nn10 = nn20[:, :10]
    
    # Load corpus texts for boilerplate benchmark
    load_corpus_texts(ids)
    logger.info(f"corpus texts loaded: {len(FT2K)}")
    
    results = []
    
    # 1. Citation heritage (on partial pairs)
    logger.info("Running citation_heritage...")
    r = bm_citation_heritage(emb, ids, pos, neg)
    results.append(r)
    # Store for later use in dedicated output
    citation_heritage_result = r
    
    # 2. Branch k-NN + TF metadata
    logger.info("Running branch_knn / tf_metadata...")
    bk, tf = bm_branch_knn_tf_metadata(emb, branch, nn10)
    results.append(bk)
    results.append(tf)
    
    # 3. Adversarial falsification
    logger.info("Running adversarial_falsification...")
    results.append(bm_adversarial(emb, lang, branch, nn20))
    
    # 4. Boilerplate resistance
    logger.info("Running boilerplate_resistance...")
    results.append(bm_boilerplate(emb, None, ids))
    
    # 5. Multilingual invariance
    logger.info("Running multilingual_invariance...")
    results.append(bm_multilingual(emb, lang, branch))
    
    # 6. Cross-language pairs
    logger.info("Running cross_language_pairs...")
    results.append(bm_cross_lang_pairs(emb, lang, branch))
    
    # 7. Collapse check
    logger.info("Running collapse_check...")
    results.append(bm_collapse(emb))
    
    # 8. Temporal stability
    logger.info("Running temporal_stability...")
    results.append(bm_temporal(emb, branch, temp_idx))
    
    # 9. Hierarchy family on frozen subsample with RAW labels
    logger.info("Running hierarchy family (raw labels)...")
    sub_emb = emb[hier_idx]
    sub_area = area[hier_idx]
    results.append(bm_hierarchy(sub_emb, sub_area))
    results.append(bm_zoom(sub_emb, sub_area))
    results.append(bm_legal_area(sub_emb, sub_area))
    
    n_pass = sum(1 for r_ in results if r_["status"] == "PASS")
    n_fail = sum(1 for r_ in results if r_["status"] == "FAIL")
    n_skip = sum(1 for r_ in results if r_["status"] == "SKIP")
    
    suite = {
        "representation": REP_NAME,
        "n_rows": n,
        "n_passed": n_pass,
        "n_failed": n_fail,
        "n_skipped": n_skip,
        "total_benchmarks": len(results),
        "benchmarks": results,
        "nn_backend": "sklearn_exact",
        "duration_seconds": round(time.time() - t0, 1),
        "config_hash_suite": "4323f833fa72366a",
        "note": "PARTIAL evaluation on 7,652 decisions (years 2000-2002 mix). Exact k-NN used instead of HNSW."
    }
    
    SUITE_OUT.mkdir(parents=True, exist_ok=True)
    with open(SUITE_OUT / f"{REP_NAME}.json", "w") as f:
        json.dump(suite, f, indent=2)
    
    # Dedicated citation heritage result
    cite_out = ROOT / "results/evaluation/v25_174k_citation_heritage/partial_dense"
    cite_out.mkdir(parents=True, exist_ok=True)
    with open(cite_out / f"{REP_NAME}.json", "w") as f:
        json.dump({
            "representation": REP_NAME,
            "benchmark": "citation_heritage_dedicated",
            "pairs_file": str(CITE_PAIRS_PATH),
            "status": citation_heritage_result["status"],
            "metrics": citation_heritage_result.get("metrics", {}),
            "threshold": 0.65,
            "duration_seconds": round(time.time() - t0, 1),
            "note": "PARTIAL evaluation on 7,652 decisions"
        }, f, indent=2)
    
    # v17b: normalized labels on same frozen subsample
    logger.info("Running v17b label normalization test...")
    norm_area = normalize_labels(area)
    sub_norm = norm_area[hier_idx]
    V17B_OUT = ROOT / "results/evaluation/v25_174k_v17b/partial_dense"
    V17B_OUT.mkdir(parents=True, exist_ok=True)
    v17b = {
        "representation": REP_NAME,
        "sample": "partial_hierarchy_subsample_5000_seed42 (fixed)",
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
    with open(V17B_OUT / f"{REP_NAME}.json", "w") as f:
        json.dump(v17b, f, indent=2)
    
    logger.info(f"DONE: {n_pass} PASS / {n_fail} FAIL / {n_skip} SKIP ({suite['duration_seconds']}s)")
    logger.info("=" * 70)
    
    # Print summary
    print(json.dumps(suite, indent=2))
    
    return suite

if __name__ == "__main__":
    run_partial_dense_evaluation()