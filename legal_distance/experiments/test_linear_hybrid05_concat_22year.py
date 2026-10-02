#!/usr/bin/env python3
"""
Test linear_hybrid05_concat at 22-year scale (2000-2021, ~144k decisions).
Combines 22-year center_projected_64 dense embeddings with cited_decisions_tfidf_outcome_hybrid_0.5.
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

from run_174k_formal_suite import (
    evaluate_representation,
    GLOBAL_SEED,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
TFIDF_EMBEDDINGS_DIR = Path("/tmp/lex_accepted/evaluation/evaluation/results/174k/embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_22year")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2022))  # 2000-2021 inclusive (22 years)


def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load dense embeddings for specified years and assemble in full metadata order."""
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
    
    logger.info(f"Total target decisions from checkpoints: {len(target_ids)}")
    
    # Filter full metadata to only target decisions, preserving order
    subset_metadata = []
    subset_indices = []
    
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
            subset_indices.append(i)
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)} (expected {len(target_ids)})")
    
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
    
    logger.info(f"Assembled dense embeddings shape: {embeddings_subset.shape}")
    
    return embeddings_subset, subset_metadata


def load_tfidf_for_subset(tfidf_filename: str, subset_metadata: List[Dict], full_metadata: List[Dict]) -> np.ndarray:
    """Load TF-IDF embeddings for the subset decisions."""
    logger.info(f"Loading {tfidf_filename} for subset...")
    
    # Load full TF-IDF
    tfidf_path = TFIDF_EMBEDDINGS_DIR / tfidf_filename
    tfidf = np.load(tfidf_path, mmap_mode='r')
    logger.info(f"Full TF-IDF shape: {tfidf.shape}")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Extract embeddings for subset
    n_subset = len(subset_metadata)
    tfidf_dim = tfidf.shape[1]
    subset_tfidf = np.zeros((n_subset, tfidf_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_tfidf[i] = tfidf[full_idx]
    
    logger.info(f"Extracted subset TF-IDF shape: {subset_tfidf.shape}")
    return subset_tfidf


def create_linear_hybrid05_concat(dense_emb: np.ndarray, citation_emb: np.ndarray) -> np.ndarray:
    """Concatenate dense and citation embeddings (equal weight concat)."""
    logger.info(f"Concatenating: dense {dense_emb.shape} + citation {citation_emb.shape}")
    concat = np.hstack([dense_emb, citation_emb])
    logger.info(f"Concatenated shape: {concat.shape}")
    return concat


def main():
    logger.info("=" * 70)
    logger.info("TESTING LINEAR_HYBRID05_CONCAT AT 22-YEAR SCALE (2000-2021)")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load 22-year dense embeddings
    logger.info("\n=== Loading 22-year dense embeddings ===")
    dense_emb, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Apply language center projection to dense embeddings
    logger.info("Applying language center projection to dense embeddings...")
    languages = [m.get('language', 'de') for m in subset_metadata]
    unique_langs = sorted(set(languages))
    centers = {}
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) > 0:
            centers[lang] = dense_emb[mask].mean(axis=0)
    
    dense_cp = np.copy(dense_emb)
    for i, lang in enumerate(languages):
        if lang in centers:
            dense_cp[i] = dense_emb[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(dense_cp, axis=1, keepdims=True)
    norms[norms == 0] = 1
    dense_cp = dense_cp / norms
    logger.info(f"Center-projected dense shape: {dense_cp.shape}")
    
    # Apply PCA to 64 dim
    logger.info("Applying PCA to 64 dimensions...")
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
    pca = PCA(n_components=64, random_state=GLOBAL_SEED)
    dense_cp_64 = pca.fit_transform(dense_cp)
    dense_cp_64 = normalize(dense_cp_64, norm='l2', axis=1)
    logger.info(f"Dense CP 64 shape: {dense_cp_64.shape}, explained var: {pca.explained_variance_ratio_.sum():.4f}")
    
    # Load citation TF-IDF outcome_hybrid_0.5 for subset
    logger.info("\n=== Loading citation TF-IDF outcome_hybrid_0.5 for 22-year subset ===")
    citation_tfidf = load_tfidf_for_subset("cited_decisions_tfidf_outcome_hybrid_0.5.npy", subset_metadata, full_metadata)
    
    # Also load cited_decisions_tfidf for linear_citation_concat comparison
    logger.info("Loading cited_decisions_tfidf for linear_citation_concat comparison...")
    citation_tfidf_raw = load_tfidf_for_subset("cited_decisions_tfidf.npy", subset_metadata, full_metadata)
    
    # Create linear_citation_concat (64 + 128 = 192 dim)
    logger.info("\n=== Creating linear_citation_concat ===")
    linear_citation_concat = create_linear_hybrid05_concat(dense_cp_64, citation_tfidf_raw)
    
    # Create linear_hybrid05_concat (64 + 128 = 192 dim)
    logger.info("\n=== Creating linear_hybrid05_concat ===")
    linear_hybrid05_concat = create_linear_hybrid05_concat(dense_cp_64, citation_tfidf)
    
    # Also test center_projected 64 alone for comparison
    logger.info("\n=== Evaluating center_projected_64 (baseline) ===")
    result_dense = evaluate_representation("center_projected_64_22year", dense_cp_64, subset_metadata)
    
    # Evaluate citation TF-IDF outcome_hybrid_0.5 alone for comparison
    logger.info("\n=== Evaluating cited_decisions_tfidf_outcome_hybrid_0.5 (baseline) ===")
    result_citation_hybrid = evaluate_representation("cited_decisions_tfidf_outcome_hybrid_0.5_22year", citation_tfidf, subset_metadata)
    
    # Evaluate cited_decisions_tfidf alone for comparison
    logger.info("\n=== Evaluating cited_decisions_tfidf (baseline) ===")
    result_citation_raw = evaluate_representation("cited_decisions_tfidf_22year", citation_tfidf_raw, subset_metadata)
    
    # Evaluate linear_citation_concat
    logger.info("\n=== Evaluating linear_citation_concat ===")
    result_linear_citation = evaluate_representation("linear_citation_concat_22year", linear_citation_concat, subset_metadata)
    
    # Evaluate linear_hybrid05_concat
    logger.info("\n=== Evaluating linear_hybrid05_concat ===")
    result_concat = evaluate_representation("linear_hybrid05_concat_22year", linear_hybrid05_concat, subset_metadata)
    
    # Save results
    from datetime import datetime
    combined = {
        'center_projected_64_22year': result_dense,
        'cited_decisions_tfidf_22year': result_citation_raw,
        'cited_decisions_tfidf_outcome_hybrid_0.5_22year': result_citation_hybrid,
        'linear_citation_concat_22year': result_linear_citation,
        'linear_hybrid05_concat_22year': result_concat,
    }
    
    output_file = OUTPUT_DIR / f"linear_hybrid05_concat_22year_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "linear_hybrid05_concat_22year_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY - LINEAR_HYBRID05_CONCAT 22-YEAR EVALUATION")
    logger.info("=" * 70)
    
    for name, result in [
        ("center_projected_64_22year", result_dense),
        ("cited_decisions_tfidf_22year", result_citation_raw),
        ("cited_decisions_tfidf_outcome_hybrid_0.5_22year", result_citation_hybrid),
        ("linear_citation_concat_22year", result_linear_citation),
        ("linear_hybrid05_concat_22year", result_concat),
    ]:
        if 'error' not in result:
            adv = result['adversarial']
            logger.info(f"\n{name}:")
            logger.info(f"  Verdict: {result['verdict']}")
            logger.info(f"  Language dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
            logger.info(f"  Jurist preference: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
            logger.info(f"  Both adversarial pass: {adv['both_pass']}")
            logger.info(f"  Embedding dim: {result['embedding_shape'][1]}")
        else:
            logger.info(f"\n{name}: ERROR - {result.get('error')}")
    
    # Check if linear_hybrid05_concat improves over baselines
    if 'error' not in result_concat and 'error' not in result_dense and 'error' not in result_citation_hybrid:
        concat_jp = result_concat['adversarial']['jurist_preference_rate']
        dense_jp = result_dense['adversarial']['jurist_preference_rate']
        citation_jp = result_citation_hybrid['adversarial']['jurist_preference_rate']
        best_baseline = max(dense_jp, citation_jp)
        
        logger.info(f"\nIMPROVEMENT ANALYSIS:")
        logger.info(f"  Best baseline JP: {best_baseline:.4f}")
        logger.info(f"  Concat JP: {concat_jp:.4f}")
        logger.info(f"  Delta: {concat_jp - best_baseline:+.4f}")
        
        if concat_jp > best_baseline:
            logger.info(f"  ✓ linear_hybrid05_concat IMPROVES over best baseline")
        else:
            logger.info(f"  ✗ linear_hybrid05_concat does NOT improve over best baseline")
    
    # Scale dependency analysis
    logger.info(f"\nSCALE DEPENDENCY (from previous runs):")
    logger.info(f"  3-year (19k): center_projected JP=0.39-0.42, linear_hybrid05_concat not tested")
    logger.info(f"  15-year (92k): center_projected JP=0.288, linear_hybrid05_concat JP=0.473 (FAIL)")
    logger.info(f"  19-year (122k): center_projected JP=0.3685, linear_hybrid05_concat JP=0.5395 (PASS)")
    logger.info(f"  22-year (144k): center_projected JP=?, linear_hybrid05_concat JP=? (this run)")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return combined


if __name__ == "__main__":
    main()