#!/usr/bin/env python3
"""
Test whether v17b label normalization (15-25% purity gain) generalizes 
to dense embeddings subsets (15-year, 19-year).
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
from evaluation.run_15year_dense_formal_suite import (
    load_dense_embeddings_subset,
    apply_center_projection,
    apply_pca,
    load_citation_tfidf_for_subset,
    load_outcome_hybrid_for_subset,
    create_concat,
    COMPLETED_YEARS,
    DENSE_CHECKPOINTS_DIR,
    TFIDF_EMBEDDINGS_DIR,
    FULL_METADATA_PATH,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Years for 19-year evaluation
COMPLETED_YEARS_19 = list(range(2000, 2019))  # 2000-2018 inclusive (19 years)

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_label_normalization")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FROZEN_SEED = 42
N_CLUSTERS = 16  # Match v17b: 16 legal areas for hierarchy


def load_full_metadata():
    """Load full 174k metadata."""
    logger.info(f"Loading full 174k metadata from {FULL_METADATA_PATH}")
    with open(FULL_METADATA_PATH, 'r') as f:
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
    np.random.seed(FROZEN_SEED)
    n_sample = min(15000, len(embeddings))
    sample_indices = np.random.choice(len(embeddings), n_sample, replace=False)
    
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=FROZEN_SEED, n_init=10)
    sample_labels = kmeans.fit_predict(embeddings[sample_indices])
    
    # Assign all points to nearest centroid
    all_labels = kmeans.predict(embeddings)
    
    # Compute purity against legal_area labels
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
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score
    
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


def run_legal_area_clustering(embeddings, labels):
    """Run legal_area clustering benchmark."""
    np.random.seed(FROZEN_SEED)
    n_sample = min(15000, len(embeddings))
    sample_indices = np.random.choice(len(embeddings), n_sample, replace=False)
    sample_emb = embeddings[sample_indices]
    sample_labels = labels[sample_indices]
    
    # Cluster with number of clusters = number of unique legal areas
    n_areas = len(np.unique(sample_labels))
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
    kmeans = KMeans(n_clusters=n_areas, random_state=FROZEN_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(sample_emb)
    
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
    lac = run_legal_area_clustering(embeddings, labels)
    
    return {
        'hierarchy_coherence': {'best_purity': hc['purity'], 'nmi': hc['nmi'], 'ari': hc['ari']},
        'zoom_coherence': {'fine_purity': zc['fine_nmi'], 'nesting_score': zc['nesting_score'], 'coarse_nmi': zc['coarse_nmi']},
        'legal_area_clustering': {'overall_purity': lac['overall_purity'], 'nmi': lac['nmi'], 'num_areas': lac['num_areas']},
    }


def load_dense_subset(years, label):
    """Load dense embeddings for specified years."""
    logger.info(f"\n=== Loading {label} dense embeddings ({years[0]}-{years[-1]}) ===")
    
    full_metadata = load_full_metadata()
    dense_768, subset_metadata = load_dense_embeddings_subset(full_metadata, years)
    
    # Apply center projection
    logger.info("Applying language center projection...")
    dense_cp_768 = apply_center_projection(dense_768, subset_metadata)
    
    # Create PCA versions
    logger.info("Creating PCA-reduced versions...")
    dense_cp_128 = apply_pca(dense_cp_768, 128)
    dense_cp_64 = apply_pca(dense_cp_768, 64)
    
    # Load citation embeddings for subset
    logger.info("Loading citation embeddings for subset...")
    citation_tfidf = load_citation_tfidf_for_subset(subset_metadata, full_metadata)
    hybrid_05 = load_outcome_hybrid_for_subset(subset_metadata, full_metadata, 0.5)
    hybrid_07 = load_outcome_hybrid_for_subset(subset_metadata, full_metadata, 0.7)
    
    # Create linear combinations
    logger.info("Creating linear combinations...")
    linear_citation_concat = create_concat(dense_cp_64, citation_tfidf, f"linear_citation_concat_{label}")
    linear_hybrid05_concat = create_concat(dense_cp_64, hybrid_05, f"linear_hybrid05_concat_{label}")
    linear_hybrid07_concat = create_concat(dense_cp_64, hybrid_07, f"linear_hybrid07_concat_{label}")
    
    representations = {
        f'center_projected_768dim_{label}': dense_cp_768,
        f'center_projected_128dim_{label}': dense_cp_128,
        f'center_projected_64dim_{label}': dense_cp_64,
        f'linear_citation_concat_{label}': linear_citation_concat,
        f'linear_hybrid05_concat_{label}': linear_hybrid05_concat,
        f'linear_hybrid07_concat_{label}': linear_hybrid07_concat,
        f'cited_decisions_tfidf_{label}': citation_tfidf,
        f'cited_decisions_tfidf_outcome_hybrid_0.5_{label}': hybrid_05,
        f'cited_decisions_tfidf_outcome_hybrid_0.7_{label}': hybrid_07,
    }
    
    return representations, subset_metadata


def main():
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("V17B LABEL NORMALIZATION TEST ON DENSE SUBSETS")
    logger.info("=" * 70)
    
    # Load full metadata and create label variants
    full_metadata = load_full_metadata()
    raw_labels_full, norm_labels_full, raw_unique, norm_unique, n_norm = make_label_variants(full_metadata)
    
    # Build raw/norm label arrays aligned with full metadata order
    full_did_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    all_results = {
        "run_id": f"eval_v17b_label_normalization_dense_{int(time.time())}",
        "direction_version": 29,
        "seed": FROZEN_SEED,
        "n_labels_normalized_full": n_norm,
        "raw_unique_areas": len(raw_unique),
        "norm_unique_areas": len(norm_unique),
        "per_subset": {},
    }
    
    for label, years in [("15year", COMPLETED_YEARS), ("19year", COMPLETED_YEARS_19)]:
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING {label.upper()} DENSE EMBEDDINGS")
        logger.info(f"{'='*70}")
        
        reps, subset_metadata = load_dense_subset(years, label)
        
        # Build label arrays aligned with subset metadata
        subset_did_to_idx = {m['decision_id']: i for i, m in enumerate(subset_metadata)}
        subset_raw_labels = []
        subset_norm_labels = []
        for m in subset_metadata:
            full_idx = full_did_to_idx[m['decision_id']]
            subset_raw_labels.append(raw_labels_full[full_idx])
            subset_norm_labels.append(norm_labels_full[full_idx])
        
        subset_raw_labels = np.array(subset_raw_labels)
        subset_norm_labels = np.array(subset_norm_labels)
        
        logger.info(f"Subset size: {len(subset_metadata)} decisions")
        logger.info(f"Raw unique legal_areas in subset: {len(np.unique(subset_raw_labels))}")
        logger.info(f"Normalized unique legal_areas in subset: {len(np.unique(subset_norm_labels))}")
        
        subset_out = {
            "size": len(subset_metadata),
            "raw_unique_areas": int(len(np.unique(subset_raw_labels))),
            "norm_unique_areas": int(len(np.unique(subset_norm_labels))),
            "per_representation": {},
        }
        
        for name, embeddings in reps.items():
            logger.info(f"\nProcessing {name}...")
            try:
                logger.info(f"  Loaded {embeddings.shape}")
                
                raw_res = run_one(embeddings, subset_raw_labels, "raw")
                norm_res = run_one(embeddings, subset_norm_labels, "normalized")
                
                # purity ratios (normalized/raw)
                def ratio(a, b):
                    return round((a / b), 4) if b else None
                
                subset_out["per_representation"][name] = {
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
                logger.info(f"  {name}: ratios {subset_out['per_representation'][name]['purity_ratios_norm_over_raw']}")
                
            except Exception as e:
                logger.error(f"  Error on {name}: {e}")
                import traceback
                traceback.print_exc()
                subset_out["per_representation"][name] = {"error": str(e)}
        
        all_results["per_subset"][label] = subset_out
    
    # Uniformity check across all subsets
    worsened = {}
    for label, subset_data in all_results["per_subset"].items():
        for name, d in subset_data["per_representation"].items():
            if "error" in d:
                continue
            for k, v in d["purity_ratios_norm_over_raw"].items():
                if v is not None and v < 0.9:
                    worsened[f"{label}.{name}.{k}"] = v
    
    all_results["uniform_improvement_or_matching"] = (len(worsened) == 0)
    all_results["representations_worsened_by_gt10pct"] = worsened
    all_results["total_duration_seconds"] = round(time.time() - t0, 2)
    
    # Save
    output_file = OUTPUT_DIR / f"v17b_label_normalization_dense_subsets_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "v17b_label_normalization_dense_subsets_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("V17B LABEL NORMALIZATION DENSE SUBSETS - SUMMARY")
    logger.info("=" * 70)
    for label, subset_data in all_results["per_subset"].items():
        logger.info(f"\n--- {label} ---")
        for name, d in subset_data["per_representation"].items():
            if "error" in d:
                logger.info(f"  {name}: ERROR - {d['error']}")
            else:
                ratios = d["purity_ratios_norm_over_raw"]
                logger.info(f"  {name}: hierarchy={ratios['hierarchy']:.4f}, zoom_fine={ratios['zoom_fine']:.4f}, legal_area={ratios['legal_area']:.4f}")
    
    logger.info(f"\nUniform improvement/matching: {all_results['uniform_improvement_or_matching']}")
    if worsened:
        logger.info(f"Worsened >10%: {worsened}")
    logger.info(f"Total duration: {all_results['total_duration_seconds']}s")
    logger.info(f"Results saved to: {output_file}")
    logger.info("=" * 70)
    
    return all_results


if __name__ == "__main__":
    main()