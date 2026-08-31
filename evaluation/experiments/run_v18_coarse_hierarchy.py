#!/usr/bin/env python3
"""
Evaluation v18: Coarse-label Hierarchy Benchmark + Multi-seed Verification + Scorecard

CYCLE HYPOTHESIS (frozen before inspection)
--------------------------------------------
The v16 hierarchy_coherence FAIL (all reps < 0.7 purity) was attributed to
label granularity (105 unique labels in 1200 decisions). v17/v17b showed
normalization helps ~20% but still fails the 0.7 threshold with 55 unique labels.

ADVERSARIAL TEST: At BRANCH-LEVEL granularity (4 labels: oeffentliches_recht,
zivilrecht, strafrecht, sozialversicherungsrecht) the embedding space should
recover legal domain structure with purity > 0.7, because this is the level
users first encounter when navigating the map.

This tests whether the "Google Maps of law" zoom experience works at the
domain level — a product-critical question.

MULTI-SEED VERIFICATION: Re-run v17b normalization ratios with seeds [123, 456,
789] to test stability. If ratios are stable (std < 0.05 across seeds), promote
v17b from EXPLORATORY to REPRODUCED.

FROZEN SUCCESS RULES:
  1. coarse_hierarchy: best_purity >= 0.70 on branch-level labels for
     center_projected_64dim baseline
  2. multi_seed: v17b purity ratios reproducible across seeds (std < 0.05)

PRODUCT DECISION UNLOCKED:
  If coarse_hierarchy PASS: the domain-level zoom works; hierarchy IS present
  in the embedding space; v16 FAIL was purely a label-granularity artifact.
  If FAIL: the embeddings genuinely lack hierarchical legal structure at ANY
  level — fundamental product limitation.
"""

import json
import time
import sys
import numpy as np
import logging
from pathlib import Path
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.linear_model import Ridge
from sklearn.preprocessing import normalize as sk_normalize
from sklearn.neighbors import NearestNeighbors

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

FROZEN_CONFIG_HASH = "4323f833fa72366a"
CORPUS_PATH = Path("evaluation/data/bger_expanded_1200.jsonl")
METADATA_PATH = Path("evaluation/data/bger_expanded_1200_metadata.jsonl")
EMBEDDINGS_64_PATH = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")

# ====================================================================
# DATA LOADING (same as v16)
# ====================================================================

CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "I. Zivilrechtliche Abteilung": "zivilrecht",
    "II. Zivilrechtliche Abteilung": "zivilrecht",
    "I. Strafrechtliche Abteilung": "strafrecht",
    "II. Strafrechtliche Abteilung": "strafrecht",
    "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
    "IIe Cour de droit social": "sozialversicherungsrecht",
    "Ire Cour de droit public": "oeffentliches_recht",
    "IIe Cour de droit public": "oeffentliches_recht",
    "Ire Cour de droit civil": "zivilrecht",
    "IIe Cour de droit civil": "zivilrecht",
    "Ire Cour de droit pénal": "strafrecht",
    "IIe Cour de droit pénal": "strafrecht",
}

def assign_branch(chamber):
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    cl = chamber.lower()
    if any(kw in cl for kw in ["öffentlich", "public"]): return "oeffentliches_recht"
    if any(kw in cl for kw in ["zivil", "civil"]): return "zivilrecht"
    if any(kw in cl for kw in ["straf", "pénal", "penal"]): return "strafrecht"
    if any(kw in cl for kw in ["sozial", "social"]): return "sozialversicherungsrecht"
    return "unknown"

def norm_emb(emb):
    n = np.linalg.norm(emb, axis=1, keepdims=True)
    n[n == 0] = 1
    return emb / n

def cosine_nn(embeddings, k=20):
    nn = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine', n_jobs=-1)
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    return indices[:, 1:]

def load_data():
    decisions = []
    with open(CORPUS_PATH) as f:
        for line in f:
            if line.strip():
                decisions.append(json.loads(line))
    metadata = []
    with open(METADATA_PATH) as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    for m in metadata:
        chamber = m.get('chamber', '')
        m['branch'] = assign_branch(chamber) if chamber else m.get('branch', 'unknown')
    logger.info(f"Loaded {len(decisions)} decisions, {len(metadata)} metadata")
    return decisions, metadata

# ====================================================================
# REPRESENTATION BUILDING (same as v16)
# ====================================================================

def build_citation_tfidf(decisions, svd_dim=128):
    texts, idxs = [], []
    for i, d in enumerate(decisions):
        cites = d.get('cited_decisions', [])
        t = " ".join(str(c) for c in cites) if cites else ""
        if t.strip():
            texts.append(t); idxs.append(i)
    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim))
    vec = TfidfVectorizer(max_features=5000, min_df=2, max_df=0.95, sublinear_tf=True)
    tfidf = vec.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(svd_dim, tfidf.shape[1]-1), random_state=42)
    red = svd.fit_transform(tfidf)
    red = norm_emb(red)
    res = np.zeros((len(decisions), red.shape[1]))
    for j, idx in enumerate(idxs):
        res[idx] = red[j]
    return res

def build_outcome_tfidf(decisions, svd_dim=2):
    texts, idxs = [], []
    for i, d in enumerate(decisions):
        o = d.get('outcome', '')
        if o and o != 'null':
            texts.append(str(o)); idxs.append(i)
    if len(texts) < 5:
        return np.zeros((len(decisions), svd_dim))
    vec = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.95, sublinear_tf=True)
    tfidf = vec.fit_transform(texts)
    svd = TruncatedSVD(n_components=min(svd_dim, tfidf.shape[1]-1), random_state=42)
    red = svd.fit_transform(tfidf)
    red = norm_emb(red)
    res = np.zeros((len(decisions), red.shape[1]))
    for j, idx in enumerate(idxs):
        res[idx] = red[j]
    return res

def build_all_representations(decisions, cp_64):
    citation_emb = build_citation_tfidf(decisions, 128)
    outcome_emb = build_outcome_tfidf(decisions, 2)
    citation_64 = norm_emb(citation_emb[:, :64] if citation_emb.shape[1] > 64 else citation_emb)
    outcome_norm = norm_emb(outcome_emb)
    hybrid_raw = np.concatenate([citation_64, outcome_norm], axis=1)
    pca_h = PCA(n_components=min(64, hybrid_raw.shape[1]-1), random_state=42)
    hybrid_05 = norm_emb(pca_h.fit_transform(hybrid_raw))
    cp_norm = norm_emb(cp_64)
    c64_norm = citation_64
    concat_c = np.concatenate([cp_norm, c64_norm], axis=1)
    pca_c = PCA(n_components=min(192, concat_c.shape[1]-1), random_state=42)
    lin_cat = norm_emb(pca_c.fit_transform(concat_c))
    concat_h = np.concatenate([cp_norm, hybrid_05], axis=1)
    pca_h2 = PCA(n_components=min(194, concat_h.shape[1]-1), random_state=42)
    lin_hcat = norm_emb(pca_h2.fit_transform(concat_h))
    w3070 = 0.3 * cp_norm + 0.7 * c64_norm
    lin_w3070 = norm_emb(w3070)
    ridge = Ridge(alpha=1.0, random_state=42)
    ridge.fit(cp_norm, c64_norm)
    ridge_pred = ridge.predict(cp_norm)
    ridge_comb = 0.5 * cp_norm + 0.5 * ridge_pred
    pca_r = PCA(n_components=min(193, ridge_comb.shape[1]-1), random_state=42)
    lin_ridge = norm_emb(pca_r.fit_transform(ridge_comb))
    return {
        'center_projected_64dim': cp_64,
        'cited_outcome_hybrid_0.5': hybrid_05,
        'linear_citation_concat': lin_cat,
        'linear_hybrid05_concat': lin_hcat,
        'linear_citation_w3070': lin_w3070,
        'linear_citation_ridge': lin_ridge,
    }

# ====================================================================
# IMPORT v17 NORMALIZATION
# ====================================================================

from legal_area_normalize import normalize_legal_area

def make_label_variants(decisions, metadata):
    raw_labels = []
    norm_labels = []
    branch_labels = []
    for m in metadata:
        lbl = m.get('legal_area', m.get('branch', 'unknown'))
        if lbl is None or lbl == 'unknown':
            lbl = 'unknown'
        raw_labels.append(lbl)
        norm_labels.append(normalize_legal_area(lbl))
        branch_labels.append(m.get('branch', 'unknown'))
    return np.array(raw_labels), np.array(norm_labels), np.array(branch_labels)

# ====================================================================
# HIERARCHY BENCHMARKS (at multiple label granularities)
# ====================================================================

def _weighted_purity(vl, labels, k):
    total = len(vl)
    parts = []
    for cl in range(k):
        mask = labels == cl
        if mask.any():
            cluster_labels = vl[mask]
            unique, counts = np.unique(cluster_labels, return_counts=True)
            max_count = counts.max()
            parts.append(float(mask.sum() / total * max_count / mask.sum()))
    return float(np.sum(parts)) if parts else 0

def run_hierarchy_benchmark(emb, labels, label_name, seed, label_granularity):
    """Run hierarchy_coherence, zoom_coherence, legal_area_clustering at given granularity."""
    valid = np.array([la is not None and la != 'unknown' for la in labels])
    if valid.sum() < 50:
        return {"status": "SKIP", "reason": f"only {valid.sum()} valid labels"}
    ve = emb[valid]
    vl = labels[valid]
    n_unique = len(np.unique(vl))
    results = {}

    # 1. hierarchy_coherence
    best_purity = 0.0
    best_nmi = 0.0
    best_k = None
    for k in [3, 4, 5, 8, 10, 15, 20, 25, 30]:
        if k > len(ve) or k > n_unique:
            continue
        km = KMeans(n_clusters=k, random_state=seed, n_init=10)
        lab = km.fit_predict(ve)
        nmi = normalized_mutual_info_score(vl, lab)
        pur = _weighted_purity(vl, lab, k)
        if pur > best_purity:
            best_purity = pur
            best_nmi = nmi
            best_k = k
    results['hierarchy_coherence'] = {
        'best_purity': round(best_purity, 6),
        'best_nmi': round(best_nmi, 6),
        'best_k': best_k,
        'n_unique_labels': n_unique,
        'n_valid_samples': int(valid.sum()),
        'pass': best_purity > 0.7 and best_nmi > 0.3,
    }

    # 2. zoom_coherence
    def cluster_purity(emb2, labels2, k):
        km = KMeans(n_clusters=k, random_state=seed, n_init=10)
        cl = km.fit_predict(emb2)
        total = len(labels2)
        parts = []
        for c in range(k):
            m = cl == c
            if m.any():
                u, cnt = np.unique(labels2[m], return_counts=True)
                parts.append(float(m.sum() / total * cnt.max() / m.sum()))
        return float(np.mean(parts)) if parts else 0

    coarse_k = min(8, n_unique)
    fine_k = min(25, n_unique)
    coarse = cluster_purity(ve, vl, coarse_k)
    fine = cluster_purity(ve, vl, fine_k)
    improvement = ((fine - coarse) / max(coarse, 0.001)) * 100
    results['zoom_coherence'] = {
        'coarse_purity': round(coarse, 6),
        'fine_purity': round(fine, 6),
        'improvement_pct': round(improvement, 4),
        'pass': improvement > 0,
    }

    # 3. legal_area_clustering
    kla = min(50, n_unique)
    kmla = KMeans(n_clusters=kla, random_state=seed, n_init=10)
    labla = kmla.fit_predict(ve)
    nmila = normalized_mutual_info_score(vl, labla)
    purla_parts = []
    for c in range(kmla.n_clusters):
        m = labla == c
        if m.any():
            _, cnt = np.unique(vl[m], return_counts=True)
            purla_parts.append(float(m.sum() / len(vl) * cnt.max() / m.sum()))
    overall_purity = float(np.mean(purla_parts)) if purla_parts else 0
    results['legal_area_clustering'] = {
        'overall_purity': round(overall_purity, 6),
        'nmi': round(nmila, 6),
        'num_areas': n_unique,
        'pass': overall_purity > 0.5,
    }

    return results

# ====================================================================
# MAIN
# ====================================================================

REPS = [
    'center_projected_64dim',
    'cited_outcome_hybrid_0.5',
    'linear_citation_concat',
    'linear_hybrid05_concat',
    'linear_citation_w3070',
    'linear_citation_ridge',
]

# Multi-seed verification seeds (v17b used seed 42)
VERIFICATION_SEEDS = [123, 456, 789]

def main():
    t0 = time.time()
    decisions, metadata = load_data()

    cp_64_full = np.load(EMBEDDINGS_64_PATH)
    cp_64 = cp_64_full[:len(decisions)]
    reps = build_all_representations(decisions, cp_64)

    raw_labels, norm_labels, branch_labels = make_label_variants(decisions, metadata)

    n_raw_unique = len(np.unique(raw_labels))
    n_norm_unique = len(np.unique(norm_labels))
    n_branch_unique = len(np.unique(branch_labels))
    logger.info(f"Labels: raw={n_raw_unique}, normalized={n_norm_unique}, branch={n_branch_unique}")
    logger.info(f"Branch distribution: {Counter(branch_labels)}")

    # === PART A: Coarse-label hierarchy benchmark ===
    logger.info("\n" + "=" * 70)
    logger.info("PART A: COARSE-LABEL HIERARCHY BENCHMARK")
    logger.info("=" * 70)
    logger.info(f"Testing hierarchy at branch-level ({n_branch_unique} labels) vs "
                f"normalized ({n_norm_unique}) vs raw ({n_raw_unique})")

    # Frozen baseline
    RAW_BASELINE = {
        "hierarchy_coherence_best_purity": 0.3885017421602788,
        "hierarchy_coherence_best_nmi": 0.5217712299399205,
        "zoom_coherence_fine_purity": 0.01435540069686411,
        "legal_area_clustering_overall_purity": 0.008257839721254354,
    }

    coarse_results = {}
    for rep_name in REPS:
        emb = reps[rep_name]
        # Branch-level (4 labels)
        branch_res = run_hierarchy_benchmark(emb, branch_labels, "branch", seed=42, label_granularity="branch")
        # Normalized legal_area (~55 labels)
        norm_res = run_hierarchy_benchmark(emb, norm_labels, "normalized", seed=42, label_granularity="normalized")
        # Raw legal_area (~105 labels)
        raw_res = run_hierarchy_benchmark(emb, raw_labels, "raw", seed=42, label_granularity="raw")

        coarse_results[rep_name] = {
            "branch_level": branch_res,
            "normalized_level": norm_res,
            "raw_level": raw_res,
        }
        logger.info(f"\n{rep_name}:")
        for level, res in [("branch", branch_res), ("normalized", norm_res), ("raw", raw_res)]:
            hc = res.get('hierarchy_coherence', {})
            logger.info(f"  {level:>12}: purity={hc.get('best_purity', 'N/A'):.4f} "
                        f"nmi={hc.get('best_nmi', 'N/A'):.4f} k={hc.get('best_k', 'N/A')} "
                        f"labels={hc.get('n_unique_labels', 'N/A')} "
                        f"PASS={hc.get('pass', 'N/A')}")

    # Frozen success rule: branch-level purity >= 0.70 for center_projected_64dim
    cp_branch = coarse_results.get('center_projected_64dim', {}).get('branch_level', {})
    cp_branch_purity = cp_branch.get('hierarchy_coherence', {}).get('best_purity', 0)
    success_a = cp_branch_purity >= 0.70
    logger.info(f"\nFrozen success rule A: branch_purity={cp_branch_purity:.4f} >= 0.70? {'PASS' if success_a else 'FAIL'}")

    # Also check: how much branch labels improve over normalized
    cp_norm = coarse_results.get('center_projected_64dim', {}).get('normalized_level', {})
    cp_norm_purity = cp_norm.get('hierarchy_coherence', {}).get('best_purity', 0)
    branch_improvement = (cp_branch_purity / cp_norm_purity) if cp_norm_purity > 0 else float('inf')
    logger.info(f"Branch/normalized purity ratio: {branch_improvement:.2f}x")

    # All reps branch-level check
    all_branch_pass = all(
        r.get('branch_level', {}).get('hierarchy_coherence', {}).get('pass', False)
        for r in coarse_results.values()
    )
    logger.info(f"All reps branch-level PASS: {all_branch_pass}")

    # === PART B: Multi-seed verification of v17b normalization ratios ===
    logger.info("\n" + "=" * 70)
    logger.info("PART B: MULTI-SEED VERIFICATION OF V17B NORMALIZATION")
    logger.info("=" * 70)

    all_seeds = [42] + VERIFICATION_SEEDS  # seed 42 is v17b original
    seed_results = {}

    for seed in all_seeds:
        logger.info(f"\nSeed {seed}:")
        seed_ratios = {}
        for rep_name in ['center_projected_64dim', 'linear_hybrid05_concat']:
            emb = reps[rep_name]
            raw_r = run_hierarchy_benchmark(emb, raw_labels, "raw", seed=seed, label_granularity="raw")
            norm_r = run_hierarchy_benchmark(emb, norm_labels, "normalized", seed=seed, label_granularity="normalized")

            def ratio(a, b):
                return round(a / b, 4) if b else None

            ratios = {
                "hierarchy": ratio(
                    norm_r['hierarchy_coherence']['best_purity'],
                    raw_r['hierarchy_coherence']['best_purity']
                ),
                "zoom_fine": ratio(
                    norm_r['zoom_coherence']['fine_purity'],
                    raw_r['zoom_coherence']['fine_purity']
                ),
                "legal_area": ratio(
                    norm_r['legal_area_clustering']['overall_purity'],
                    raw_r['legal_area_clustering']['overall_purity']
                ),
            }
            seed_ratios[rep_name] = {
                "ratios": ratios,
                "raw_purity": raw_r['hierarchy_coherence']['best_purity'],
                "norm_purity": norm_r['hierarchy_coherence']['best_purity'],
            }
            logger.info(f"  {rep_name}: hierarchy_ratio={ratios['hierarchy']}, "
                        f"zoom_fine_ratio={ratios['zoom_fine']}, "
                        f"legal_area_ratio={ratios['legal_area']}")
        seed_results[seed] = seed_ratios

    # Stability analysis
    stability = {}
    for rep_name in ['center_projected_64dim', 'linear_hybrid05_concat']:
        hier_ratios = [seed_results[s][rep_name]['ratios']['hierarchy'] for s in all_seeds
                       if seed_results[s][rep_name]['ratios']['hierarchy'] is not None]
        zoom_ratios = [seed_results[s][rep_name]['ratios']['zoom_fine'] for s in all_seeds
                       if seed_results[s][rep_name]['ratios']['zoom_fine'] is not None]
        legal_ratios = [seed_results[s][rep_name]['ratios']['legal_area'] for s in all_seeds
                        if seed_results[s][rep_name]['ratios']['legal_area'] is not None]

        stability[rep_name] = {
            "hierarchy_ratio_mean": round(float(np.mean(hier_ratios)), 4),
            "hierarchy_ratio_std": round(float(np.std(hier_ratios)), 4),
            "zoom_fine_ratio_mean": round(float(np.mean(zoom_ratios)), 4),
            "zoom_fine_ratio_std": round(float(np.std(zoom_ratios)), 4),
            "legal_area_ratio_mean": round(float(np.mean(legal_ratios)), 4),
            "legal_area_ratio_std": round(float(np.std(legal_ratios)), 4),
            "n_seeds": len(all_seeds),
        }
        logger.info(f"\n{rep_name} stability across {len(all_seeds)} seeds:")
        logger.info(f"  hierarchy: mean={stability[rep_name]['hierarchy_ratio_mean']:.4f} "
                    f"std={stability[rep_name]['hierarchy_ratio_std']:.4f}")
        logger.info(f"  zoom_fine: mean={stability[rep_name]['zoom_fine_ratio_mean']:.4f} "
                    f"std={stability[rep_name]['zoom_fine_ratio_std']:.4f}")
        logger.info(f"  legal_area: mean={stability[rep_name]['legal_area_ratio_mean']:.4f} "
                    f"std={stability[rep_name]['legal_area_ratio_std']:.4f}")

    # Frozen success rule B: all ratios stable (std < 0.05) AND mean > 1.10
    success_b = all(
        s['hierarchy_ratio_std'] < 0.05 and s['hierarchy_ratio_mean'] > 1.10
        for s in stability.values()
    )
    logger.info(f"\nFrozen success rule B (multi-seed stability): {'PASS' if success_b else 'FAIL'}")

    # === PART C: Consolidated Evaluation Scorecard ===
    logger.info("\n" + "=" * 70)
    logger.info("PART C: CONSOLIDATED EVALUATION SCORECARD")
    logger.info("=" * 70)

    scorecard = build_scorecard(coarse_results, stability, all_seeds)

    # === ASSEMBLE OUTPUT ===
    finding = {
        "run_id": f"eval_v18_coarse_hierarchy_{int(time.time())}",
        "direction_version": 13,
        "config_hash": FROZEN_CONFIG_HASH,
        "github_run": "33376270601",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "frozen_hypothesis": (
            "The v16 hierarchy_coherence FAIL (all reps < 0.7 purity) is a label-granularity "
            "artifact: at branch-level (4 labels) the hierarchy IS recoverable with purity >= 0.7."
        ),
        "frozen_success_rules": {
            "rule_a_coarse_hierarchy": "branch_level best_purity >= 0.70 for center_projected_64dim",
            "rule_b_multi_seed": "v17b normalization ratios stable across 4 seeds (std < 0.05, mean > 1.10)",
        },
        "part_a_coarse_hierarchy": {
            "results": coarse_results,
            "success_a": success_a,
            "branch_purity_center_projected": cp_branch_purity,
            "norm_purity_center_projected": cp_norm_purity,
            "branch_improvement_ratio": round(branch_improvement, 2),
            "all_reps_branch_pass": all_branch_pass,
        },
        "part_b_multi_seed_verification": {
            "seeds": all_seeds,
            "seed_results": seed_results,
            "stability": stability,
            "success_b": success_b,
        },
        "part_c_scorecard": scorecard,
        "overall_success": success_a and success_b,
        "product_decision_unlocked": (
            "BRANCH-LEVEL HIERARCHY PASS: The embedding space DOES recover legal domain "
            "structure at the 4-branch level users first encounter. v16 FAIL was purely a "
            "label-granularity artifact. Product zoom from domains→subdomains IS feasible."
            if success_a else
            "BRANCH-LEVEL HIERARCHY FAIL: Even at 4-label branch granularity the hierarchy "
            "is not recoverable. The embedding space lacks hierarchical legal structure. "
            "Fundamental product limitation."
        ),
        "total_duration_seconds": round(time.time() - t0, 2),
    }

    # Save results
    out_dir = Path("results/evaluation/v18_coarse_hierarchy")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "v18_coarse_hierarchy_results.json", "w") as f:
        json.dump(finding, f, indent=2, default=str)
    with open(out_dir / "v18_coarse_hierarchy_latest.json", "w") as f:
        json.dump(finding, f, indent=2, default=str)

    logger.info(f"\n{'='*70}")
    logger.info("V18 RESULT SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Success A (coarse hierarchy): {success_a}")
    logger.info(f"Success B (multi-seed stability): {success_b}")
    logger.info(f"Overall: {finding['overall_success']}")
    logger.info(f"Duration: {finding['total_duration_seconds']:.1f}s")
    logger.info(f"Saved to {out_dir / 'v18_coarse_hierarchy_results.json'}")

    return finding


def build_scorecard(coarse_results, stability, all_seeds):
    """Build a consolidated evaluation scorecard across all evidence."""
    scorecard = {
        "version": "v18",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "direction_version": 13,
        "frozen_benchmarks": {
            "branch_knn": {"threshold": 0.6333, "type": "classification"},
            "tf_metadata_human_indexing": {"threshold": 0.8, "type": "retrieval"},
            "adversarial_falsification": {"threshold": {"language_dominance_max": 0.85, "branch_coherence_min": 0.3}},
            "boilerplate_resistance_real_corpus": {"threshold": 0.1, "type": "correlation"},
            "multilingual_invariance": {"threshold": {"separation_min": 0, "invariance_gap_max": 0.2}},
            "cross_language_pairs": {"threshold": 0, "type": "separation"},
            "collapse_check": {"threshold": {"mean_sim_max": 0.99, "std_sim_min": 0.01}},
            "temporal_stability": {"threshold": 0.1, "type": "stability"},
            "citation_heritage": {"threshold": 0.65, "type": "auc_roc", "note": "SKIPPED: no internal citations resolved"},
            "hierarchy_coherence": {"threshold": {"purity_min": 0.7, "nmi_min": 0.3}},
            "zoom_coherence": {"threshold": 0, "type": "improvement_pct"},
            "legal_area_clustering": {"threshold": 0.5, "type": "purity"},
        },
        "representations": {},
        "evidence_tiers": {
            "center_projected_64dim": "REPRODUCED",
            "cited_outcome_hybrid_0.5": "ACCEPTED",
            "linear_citation_concat": "ACCEPTED",
            "linear_hybrid05_concat": "ACCEPTED",
            "linear_citation_w3070": "ACCEPTED",
            "linear_citation_ridge": "ACCEPTED",
        },
        "v16_benchmark_results": {
            "center_projected_64dim": {"passed": 7, "failed": 4, "skipped": 1, "tf_recall@5": 0.9308},
            "cited_outcome_hybrid_0.5": {"passed": 6, "failed": 5, "skipped": 1, "tf_recall@5": 0.7135},
            "linear_citation_concat": {"passed": 7, "failed": 4, "skipped": 1, "tf_recall@5": 0.9127},
            "linear_hybrid05_concat": {"passed": 7, "failed": 4, "skipped": 1, "tf_recall@5": 0.9000},
            "linear_citation_w3070": {"passed": 6, "failed": 5, "skipped": 1, "tf_recall@5": 0.7930},
            "linear_citation_ridge": {"passed": 7, "failed": 4, "skipped": 1, "tf_recall@5": 0.9208},
        },
        "v18_coarse_hierarchy": {},
        "v17b_normalization_stability": {},
        "universal_passes": ["branch_knn", "adversarial_falsification", "multilingual_invariance",
                           "cross_language_pairs", "collapse_check", "temporal_stability"],
        "universal_failures": ["boilerplate_resistance_real_corpus", "hierarchy_coherence",
                             "zoom_coherence", "legal_area_clustering"],
        "v18_new_evidence": {},
    }

    # Add coarse hierarchy results
    for rep_name in REPS:
        cr = coarse_results.get(rep_name, {})
        scorecard["v18_coarse_hierarchy"][rep_name] = {
            "branch_purity": cr.get('branch_level', {}).get('hierarchy_coherence', {}).get('best_purity'),
            "branch_nmi": cr.get('branch_level', {}).get('hierarchy_coherence', {}).get('best_nmi'),
            "normalized_purity": cr.get('normalized_level', {}).get('hierarchy_coherence', {}).get('best_purity'),
            "raw_purity": cr.get('raw_level', {}).get('hierarchy_coherence', {}).get('best_purity'),
            "branch_zoom_improvement": cr.get('branch_level', {}).get('zoom_coherence', {}).get('improvement_pct'),
        }

    # Add stability
    scorecard["v17b_normalization_stability"] = stability

    # Build per-representation consolidated view
    for rep_name in REPS:
        v16 = scorecard["v16_benchmark_results"].get(rep_name, {})
        v18 = scorecard["v18_coarse_hierarchy"].get(rep_name, {})
        scorecard["representations"][rep_name] = {
            "evidence_tier": scorecard["evidence_tiers"].get(rep_name, "UNKNOWN"),
            "v16_benchmarks": v16,
            "v18_branch_purity": v18.get('branch_purity'),
            "v18_normalized_purity": v18.get('normalized_purity'),
            "universal_passes": 6,
            "hierarchy_status": "FAIL_raw" if (v18.get('raw_purity', 0) or 0) < 0.7 else "PASS",
            "product_recommendation": "BEST STABLE" if rep_name == "linear_hybrid05_concat" else (
                "DEFAULT" if rep_name == "center_projected_64dim" else ""
            ),
        }

    return scorecard


if __name__ == "__main__":
    main()
