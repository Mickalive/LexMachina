#!/usr/bin/env python3
"""
Evaluate center_projected versions on 16-year partial (2000-2015) dense embeddings.
Assembles year-split embeddings in full metadata order, creates center_projected versions,
and runs the formal suite evaluation.
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
from evaluation.run_174k_formal_suite import (
    evaluate_representation,
    load_evaluation_metadata,
    prepare_metadata,
    get_adversarial_subsample,
    run_full_corpus_benchmarks_hnsw,
    run_adversarial_benchmarks_exact,
    run_cross_language_benchmarks,
    run_jurist_usability_benchmarks,
    EVALUATION_VERSION,
    GLOBAL_SEED,
    ADVERSARIAL_SUBSAMPLE,
    TEMPORAL_STABILITY_SUBSAMPLE,
    HIERARCHY_FAMILY_SUBSAMPLE,
    CHAMBER_TO_BRANCH,
    assign_branch,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/center_projected_partial_2000_2015")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2016))  # 2000-2015 inclusive


def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """
    Load dense embeddings for specified years and assemble in full metadata order.
    
    Returns: (embeddings_subset, metadata_subset)
    """
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Collect all decision_ids for the target years
    target_ids = set()
    year_meta = {}
    year_emb = {}
    
    for year in years:
        meta_path = DENSE_CHECKPOINTS_DIR / f"metadata_{year}.json"
        emb_path = DENSE_CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        
        with open(meta_path) as f:
            meta = json.load(f)
        emb = np.load(emb_path)
        
        year_meta[year] = meta
        year_emb[year] = emb
        
        for m in meta:
            target_ids.add(m['decision_id'])
    
    logger.info(f"Total target decisions: {len(target_ids)}")
    
    # Filter full metadata to only target decisions, preserving order
    subset_metadata = []
    subset_indices = []
    
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
            subset_indices.append(i)
    
    logger.info(f"Subset metadata count: {len(subset_metadata)} (expected {len(target_ids)})")
    
    # Now assemble embeddings in the same order as subset_metadata
    # Build a lookup: decision_id -> (year, local_index)
    id_to_year_local = {}
    for year in years:
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
    # Assemble embeddings
    dim = year_emb[years[0]].shape[1]
    embeddings_subset = np.zeros((len(subset_metadata), dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        year, local_idx = id_to_year_local[m['decision_id']]
        embeddings_subset[i] = year_emb[year][local_idx]
    
    logger.info(f"Assembled embeddings shape: {embeddings_subset.shape}")
    
    return embeddings_subset, subset_metadata


def center_project(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Create center_projected embeddings by subtracting language centers."""
    languages = sorted(set(m.get('language', 'de') for m in metadata))
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language', 'de') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language', 'de')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return debiased / norms


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    n_samples, n_features = emb.shape
    if n_features <= target_dim:
        if n_features < target_dim:
            padding = np.zeros((n_samples, target_dim - n_features))
            return np.concatenate([emb, padding], axis=1)
        return emb
    if n_samples < target_dim + 1:
        return emb[:, :target_dim]
    pca = PCA(n_components=target_dim, random_state=GLOBAL_SEED)
    projected = pca.fit_transform(emb)
    return normalize(projected, norm='l2', axis=1)


def evaluate_center_projected_16year():
    """Main evaluation function for center_projected on 16-year partial."""
    logger.info("=" * 70)
    logger.info(f"Evaluating Center_Projected on 174k Dense Embeddings (Partial: 2000-2015)")
    logger.info(f"Using formal suite {EVALUATION_VERSION} with HNSW artifact fix")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load and assemble dense embeddings for years 2000-2015
    embeddings_raw, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Create center_projected version
    logger.info("Creating center_projected version...")
    embeddings_cp = center_project(embeddings_raw, subset_metadata)
    
    # Create 64-dim and 128-dim versions
    logger.info("Creating 64-dim version...")
    embeddings_cp_64 = project_to_dim(embeddings_cp, 64)
    
    logger.info("Creating 128-dim version...")
    embeddings_cp_128 = project_to_dim(embeddings_cp, 128)
    
    # Evaluate all versions
    representations = {
        'center_projected_768dim_partial_2000_2015': embeddings_cp,
        'center_projected_64dim_partial_2000_2015': embeddings_cp_64,
        'center_projected_128dim_partial_2000_2015': embeddings_cp_128,
    }
    
    all_results = {}
    
    for name, emb in representations.items():
        logger.info(f"\nEvaluating representation: {name}")
        logger.info(f"Subset size: {len(subset_metadata)} decisions")
        
        result = evaluate_representation(name, emb, subset_metadata)
        all_results[name] = result
        
        # Save individual result
        from datetime import datetime
        output_file = OUTPUT_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Print summary
        if 'error' not in result:
            adv = result['adversarial']
            logger.info(f"\n{'='*70}")
            logger.info(f"SUMMARY: {name}")
            logger.info(f"{'='*70}")
            logger.info(f"Verdict: {result['verdict']}")
            logger.info(f"Language dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
            logger.info(f"Jurist preference: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
            logger.info(f"Both adversarial pass: {adv['both_pass']}")
            logger.info(f"Backend: {adv.get('backend', 'N/A')}")
            logger.info(f"Subset size: {adv.get('subset_size', 'N/A')}")
    
    # Save combined results
    from datetime import datetime
    combined_file = OUTPUT_DIR / f"center_projected_16year_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "center_projected_16year_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\nCombined results saved to: {combined_file}")
    logger.info(f"Latest symlink: {latest_file}")
    
    # Overall summary
    logger.info("\n" + "=" * 80)
    logger.info("CENTER_PROJECTED 16-YEAR PARTIAL EVALUATION SUMMARY (Years 2000-2015)")
    logger.info("=" * 80)
    
    for name, result in all_results.items():
        if 'error' in result:
            logger.info(f"\n{name}: ERROR - {result['error']}")
            continue
            
        adv = result['adversarial']
        cross = result.get('cross_language', {})
        jurist = result.get('jurist_usability', {})
        full = result.get('full_corpus', {})
        
        logger.info(f"\n--- {name} ---")
        logger.info(f"Verdict: {result['verdict']}")
        logger.info(f"Both adversarial pass: {result['both_adversarial_pass']}")
        logger.info(f"  Language Dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"  Jurist Pairwise: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        
        if cross:
            cl_nq = cross.get('cross_language_neighbor_quality', {})
            zscl = cross.get('zero_shot_cross_language_transfer', {})
            lsrq = cross.get('language_specific_representation_quality', {})
            logger.info(f"  Cross-Lang Neighbor Quality: gap={cl_nq.get('invariance_gap', 'N/A'):.4f} ({cl_nq.get('status', 'N/A')})")
            logger.info(f"  Zero-Shot Transfer: gap={zscl.get('transfer_gap', 'N/A'):.4f} ({zscl.get('status', 'N/A')})")
            logger.info(f"  Lang-Specific Quality: mean_nmi={lsrq.get('mean_nmi', 'N/A'):.4f} ({lsrq.get('status', 'N/A')})")
        
        if jurist:
            cc = jurist.get('cluster_coherence_rating', {})
            clr = jurist.get('cross_language_retrieval', {})
            logger.info(f"  Cluster Coherence: branch_purity={cc.get('mean_branch_purity', 'N/A'):.4f} ({cc.get('status', 'N/A')})")
            logger.info(f"  Cross-Lang Retrieval: recall={clr.get('mean_cross_language_recall_at_k', 'N/A'):.4f} ({clr.get('status', 'N/A')})")
        
        if full:
            jv = full.get('hierarchy_coherence', {}) or full.get('jurivoc_alignment', {})
            ts = full.get('temporal_stability', {}) or full.get('scale_stability', {})
            bp = full.get('boilerplate_resistance', {})
            logger.info(f"  Hierarchy Level 0 NMI: {jv.get('level_0_nmi', 'N/A'):.4f}")
            logger.info(f"  Hierarchy Level 1 NMI: {jv.get('level_1_nmi', 'N/A'):.4f}")
            logger.info(f"  Nesting Score: {jv.get('nesting_score', 'N/A'):.4f}")
            logger.info(f"  Scale Stability: {ts.get('mean_neighbor_overlap', 'N/A'):.4f}")
            logger.info(f"  Boilerplate Resistance: {bp.get('resistance_score', 'N/A'):.4f}")
    
    # Find best representation
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    logger.info("=" * 80)
    
    return all_results


if __name__ == "__main__":
    evaluate_center_projected_16year()