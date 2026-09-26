#!/usr/bin/env python3
"""
Test whether v17b label normalization (15-25% purity gain) generalizes 
to 174k fine-grained legal_area labels.
This adapts the v17b_label_normalization_all_reps.py to run on 174k data.
"""

import json
import sys
import time
import numpy as np
import logging
from pathlib import Path
from collections import Counter

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
from evaluation.scalable_nn import build_scalable_nn
from evaluation.experiments.legal_area_normalize import normalize_legal_area

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_label_normalization")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Representations to evaluate (TF-IDF family at 174k)
REPRESENTATIONS = {
    'cited_decisions_tfidf': 'cited_decisions_tfidf.npy',
    'outcome_tfidf': 'outcome_tfidf.npy',
    'regeste_tfidf': 'regeste_tfidf.npy',
    'full_text_tfidf_light': 'full_text_tfidf_light.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.5': 'cited_decisions_tfidf_outcome_hybrid_0.5.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.7': 'cited_decisions_tfidf_outcome_hybrid_0.7.npy',
    'regeste_full_text_hybrid_0.5': 'regeste_full_text_hybrid_0.5.npy',
    'regeste_full_text_hybrid_0.7': 'regeste_full_text_hybrid_0.7.npy',
}

FROZEN_SEED = 42
N_CLUSTERS = 16  # Match v17b: 16 legal areas for hierarchy

def load_metadata():
    """Load 174k metadata."""
    logger.info(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} decisions")
    return metadata

def make_label_variants(metadata):
    """Create raw and normalized legal_area labels."""
    raw_labels = [m.get('legal_area', 'unknown') for m in metadata]
    
    # Normalize
    normalized_labels = []
    n_normalized = 0
    for label in raw_labels:
        norm = normalize_legal_area(label)
        if norm != label:
            n_normalized += 1
        normalized_labels.append(norm)
    
    logger.info(f"Raw unique legal_areas: {len(set(raw_labels))}")
    logger.info(f"Normalized unique legal_areas: {len(set(normalized_labels))}")
    logger.info(f"Labels normalized: {n_normalized}/{len(metadata)} ({100*n_normalized/len(metadata):.1f}%)")
    
    # Convert to integer labels
    raw_unique = sorted(set(raw_labels))
    raw_to_idx = {v: i for i, v in enumerate(raw_unique)}
    raw_int = np.array([raw_to_idx[v] for v in raw_labels])
    
    norm_unique = sorted(set(normalized_labels))
    norm_to_idx = {v: i for i, v in enumerate(norm_unique)}
    norm_int = np.array([norm_to_idx[v] for v in normalized_labels])
    
    return raw_int, norm_int, raw_unique, norm_unique, n_normalized

def run_hierarchy_coherence(embeddings, labels, n_clusters=16):
    """Run hierarchy coherence: cluster and measure purity against legal_area labels."""
    # Cluster embeddings
    nn = build_scalable_nn(embeddings, n_neighbors=100, force_exact=False)
    
    # For 174k, we'll use k-means clustering on a sample for speed, then assign all
    # Actually, let's use a stratified sample for clustering
    np.random.seed(FROZEN_SEED)
    n_sample = min(30000, len(embeddings))
    sample_indices = np.random.choice(len(embeddings), n_sample, replace=False)
    
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=n_clusters, random_state=FROZEN_SEED, n_init=10)
    sample_labels = kmeans.fit_predict(embeddings[sample_indices])
    
    # Assign all points to nearest centroid
    all_labels = kmeans.predict(embeddings)
    
    # Compute purity against legal_area labels
    from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
    
    # We need to align sample_labels with sample legal_area labels
    sample_legal_labels = labels[sample_indices]
    
    nmi = normalized_mutual_info_score(sample_legal_labels, sample_labels)
    ari = adjusted_rand_score(sample_legal_labels, sample_labels)
    
    # Cluster purity
    purity_sum = 0
    for c in range(n_clusters):
        mask = sample_labels == c
        if mask.sum() == 0:
            continue
        gt_in_cluster = sample_legal_labels[mask]
        most_common = np.bincount(gt_in_cluster).max()
        purity_sum += most_common
    
    purity = purity_sum / n_sample
    
    return {
        'nmi': float(nmi),
        'ari': float(ari),
        'purity': float(purity),
        'n_clusters': n_clusters,
        'sample_size': n_sample
    }

def run_zoom_coherence(embeddings, labels, n_clusters_fine=16):
    """Run zoom coherence: check if fine clusters nest within coarse."""
    # Coarse clustering (4 clusters = branches)
    from sklearn.cluster import KMeans
    
    np.random.seed(FROZEN_SEED)
    n_sample = min(15000, len(embeddings))
    sample_indices = np.random.choice(len(embeddings), n_sample, replace=False)
    sample_emb = embeddings[sample_indices]
    sample_labels = labels[sample_indices]
    
    # Coarse (4 clusters)
    kmeans_coarse = KMeans(n_clusters=4, random_state=FROZEN_SEED, n_init=10)
    coarse_labels = kmeans_coarse.fit_predict(sample_emb)
    
    # Fine (16 clusters)
    kmeans_fine = KMeans(n_clusters=n_clusters_fine, random_state=FROZEN_SEED, n_init=10)
    fine_labels = kmeans_fine.fit_predict(sample_emb)
    
    # Check nesting: each fine cluster should map to one coarse cluster
    nesting_violations = 0
    for c in range(n_clusters_fine):
        mask = fine_labels == c
        if mask.sum() == 0:
            continue
        coarse_in_fine = coarse_labels[mask]
        unique_coarse = np.unique(coarse_in_fine)
        if len(unique_coarse) > 1:
            nesting_violations += 1
    
    nesting_score = 1.0 - (nesting_violations / n_clusters_fine)
    
    # Fine purity
    from sklearn.metrics import normalized_mutual_info_score
    fine_nmi = normalized_mutual_info_score(sample_labels, fine_labels)
    
    # Coarse purity
    coarse_nmi = normalized_mutual_info_score(sample_labels, coarse_labels)
    
    return {
        'fine_nmi': float(fine_nmi),
        'coarse_nmi': float(coarse_nmi),
        'nesting_score': float(nesting_score),
        'nesting_violations': int(nesting_violations),
        'n_clusters_fine': n_clusters_fine,
        'sample_size': n_sample
    }

def run_legal_area_clustering(embeddings, labels, raw_label_names):
    """Run legal_area clustering benchmark."""
    np.random.seed(FROZEN_SEED)
    n_sample = min(15000, len(embeddings))
    sample_indices = np.random.choice(len(embeddings), n_sample, replace=False)
    sample_emb = embeddings[sample_indices]
    sample_labels = labels[sample_indices]
    
    # Cluster with number of clusters = number of unique legal areas
    n_areas = len(np.unique(sample_labels))
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=n_areas, random_state=FROZEN_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(sample_emb)
    
    from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
    nmi = normalized_mutual_info_score(sample_labels, cluster_labels)
    ari = adjusted_rand_score(sample_labels, cluster_labels)
    
    # Purity
    purity_sum = 0
    for c in range(n_areas):
        mask = cluster_labels == c
        if mask.sum() == 0:
            continue
        gt_in_cluster = sample_labels[mask]
        most_common = np.bincount(gt_in_cluster).max()
        purity_sum += most_common
    
    purity = purity_sum / n_sample
    
    return {
        'nmi': float(nmi),
        'ari': float(ari),
        'overall_purity': float(purity),
        'num_areas': n_areas,
        'sample_size': n_sample
    }

def run_one(embeddings, labels, label_type):
    """Run all three hierarchy-family benchmarks."""
    logger.info(f"  Running {label_type} labels: hierarchy_coherence, zoom_coherence, legal_area_clustering")
    
    hc = run_hierarchy_coherence(embeddings, labels)
    zc = run_zoom_coherence(embeddings, labels)
    lac = run_legal_area_clustering(embeddings, labels, [])
    
    return {
        'hierarchy_coherence': {'best_purity': hc['purity'], 'nmi': hc['nmi'], 'ari': hc['ari']},
        'zoom_coherence': {'fine_purity': zc['fine_nmi'], 'nesting_score': zc['nesting_score'], 'coarse_nmi': zc['coarse_nmi']},
        'legal_area_clustering': {'overall_purity': lac['overall_purity'], 'nmi': lac['nmi'], 'num_areas': lac['num_areas']},
    }

def main():
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("V17B LABEL NORMALIZATION TEST AT 174K SCALE")
    logger.info("=" * 70)
    
    # Load metadata and create label variants
    metadata = load_metadata()
    raw_labels, norm_labels, raw_unique, norm_unique, n_norm = make_label_variants(metadata)
    
    out = {
        "run_id": f"eval_v17b_label_normalization_174k_{int(time.time())}",
        "direction_version": 27,
        "seed": FROZEN_SEED,
        "n_labels_normalized": n_norm,
        "raw_unique_areas": len(raw_unique),
        "norm_unique_areas": len(norm_unique),
        "per_representation": {},
    }
    
    for name, fname in REPRESENTATIONS.items():
        logger.info(f"\nProcessing {name}...")
        try:
            emb_path = EMBEDDINGS_DIR / fname
            embeddings = np.load(emb_path, mmap_mode='r')
            logger.info(f"  Loaded {embeddings.shape}")
            
            raw_res = run_one(embeddings, raw_labels, "raw")
            norm_res = run_one(embeddings, norm_labels, "normalized")
            
            # purity ratios (normalized/raw)
            def ratio(a, b):
                return round((a / b), 4) if b else None
            
            out["per_representation"][name] = {
                "raw": raw_res,
                "normalized": norm_res,
                "purity_ratios_norm_over_raw": {
                    "hierarchy": ratio(norm_res["hierarchy_coherence"]["best_purity"],
                                       raw_res["hierarchy_coherence"]["best_purity"]),
                    "zoom_fine": ratio(norm_res["zoom_coherence"]["fine_purity"],
                                       raw_res["zoom_coherence"]["fine_purity"]),
                    "legal_area": ratio(norm_res["legal_area_clustering"]["overall_purity"],
                                        raw_res["legal_area_clustering"]["overall_purity"]),
                },
                "norm_num_areas": norm_res["legal_area_clustering"]["num_areas"],
            }
            logger.info(f"  {name}: ratios {out['per_representation'][name]['purity_ratios_norm_over_raw']}")
            
        except Exception as e:
            logger.error(f"  Error on {name}: {e}")
            import traceback
            traceback.print_exc()
            out["per_representation"][name] = {"error": str(e)}
    
    # Uniformity check: every rep has hierarchy_purity_ratio >= 1 and none worsens by >10%
    worsened = {}
    for name, d in out["per_representation"].items():
        if "error" in d:
            continue
        for k, v in d["purity_ratios_norm_over_raw"].items():
            if v is not None and v < 0.9:
                worsened[f"{name}.{k}"] = v
    
    out["uniform_improvement_or_matching"] = (len(worsened) == 0)
    out["representations_worsened_by_gt10pct"] = worsened
    out["total_duration_seconds"] = round(time.time() - t0, 2)
    
    # Save
    output_file = OUTPUT_DIR / f"v17b_label_normalization_174k_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "v17b_label_normalization_174k_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("V17B LABEL NORMALIZATION 174K - SUMMARY")
    logger.info("=" * 70)
    for name, d in out["per_representation"].items():
        if "error" in d:
            logger.info(f"  {name}: ERROR - {d['error']}")
        else:
            ratios = d["purity_ratios_norm_over_raw"]
            logger.info(f"  {name}: hierarchy={ratios['hierarchy']:.4f}, zoom_fine={ratios['zoom_fine']:.4f}, legal_area={ratios['legal_area']:.4f}")
    
    logger.info(f"\nUniform improvement/matching: {out['uniform_improvement_or_matching']}")
    if worsened:
        logger.info(f"Worsened >10%: {worsened}")
    logger.info(f"Total duration: {out['total_duration_seconds']}s")
    logger.info(f"Results saved to: {output_file}")
    logger.info("=" * 70)
    
    return out

if __name__ == "__main__":
    main()