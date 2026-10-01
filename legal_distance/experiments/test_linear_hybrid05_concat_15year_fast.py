#!/usr/bin/env python3
"""
Test linear_hybrid05_concat at 15-year scale (2000-2014, ~91k decisions).
FAST VERSION: Only runs adversarial and cross-language benchmarks (no full-corpus scale benchmarks).
Combines 15-year center_projected_64 dense embeddings with cited_decisions_tfidf_outcome_hybrid_0.5.
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
    run_adversarial_benchmarks_exact,
    run_cross_language_benchmarks,
    run_jurist_usability_benchmarks,
    GLOBAL_SEED,
    ADVERSARIAL_SUBSAMPLE,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
TFIDF_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_15year")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2015))  # 2000-2014 inclusive (15 years)


def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load dense embeddings for specified years and assemble in full metadata order."""
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
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
    
    subset_metadata = []
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)} (expected {len(target_ids)})")
    
    id_to_year_local = {}
    for year in years:
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
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
    
    tfidf_path = TFIDF_EMBEDDINGS_DIR / tfidf_filename
    tfidf = np.load(tfidf_path, mmap_mode='r')
    logger.info(f"Full TF-IDF shape: {tfidf.shape}")
    
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    n_subset = len(subset_metadata)
    tfidf_dim = tfidf.shape[1]
    subset_tfidf = np.zeros((n_subset, tfidf_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_tfidf[i] = tfidf[full_idx]
    
    logger.info(f"Extracted subset TF-IDF shape: {subset_tfidf.shape}")
    return subset_tfidf


def evaluate_representation_fast(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run fast evaluation (adversarial + cross-language + jurist usability only)."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Evaluating (fast): {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*70}")
    
    # Adversarial benchmarks
    logger.info("Running adversarial benchmarks (EXACT k-NN on valid subset)...")
    adversarial = run_adversarial_benchmarks_exact(embeddings, metadata)
    
    # Cross-language benchmarks
    logger.info("Running cross-language benchmarks (EXACT k-NN on valid subset)...")
    cross_language = run_cross_language_benchmarks(embeddings, metadata)
    
    # Jurist usability benchmarks
    logger.info("Running jurist usability benchmarks (EXACT k-NN on valid subset)...")
    jurist_usability = run_jurist_usability_benchmarks(embeddings, metadata)
    
    # Determine verdict based on adversarial gates
    both_pass = (
        adversarial['adversarial_language_dominance']['status'] == 'PASS' and
        adversarial['jurist_pairwise_preference']['status'] == 'PASS'
    )
    
    verdict = 'PASS' if both_pass else 'FAIL'
    
    result = {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'adversarial': adversarial,
        'cross_language': cross_language,
        'jurist_usability': jurist_usability,
        'full_corpus': {
            'citation_heritage': {'status': 'SKIP_FAST', 'note': 'Fast mode: skipped'},
            'temporal_stability': {'status': 'SKIP_FAST', 'note': 'Fast mode: skipped'},
            'hierarchy_coherence': {'status': 'SKIP_FAST', 'note': 'Fast mode: skipped'},
            'cluster_coherence': {'status': 'SKIP_FAST', 'note': 'Fast mode: skipped'},
            'cross_language_retrieval_full': {'status': 'SKIP_FAST', 'note': 'Fast mode: skipped'},
            'boilerplate_resistance': {'status': 'SKIP_FAST', 'note': 'Fast mode: skipped'},
        },
        'verdict': verdict,
        'both_adversarial_pass': both_pass,
    }
    
    return result


def main():
    logger.info("=" * 70)
    logger.info("TESTING LINEAR_HYBRID05_CONCAT AT 15-YEAR SCALE (2000-2014) - FAST MODE")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load 15-year dense embeddings
    logger.info("\n=== Loading 15-year dense embeddings ===")
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
    logger.info("\n=== Loading citation TF-IDF outcome_hybrid_0.5 for 15-year subset ===")
    citation_tfidf = load_tfidf_for_subset("cited_decisions_tfidf_outcome_hybrid_0.5.npy", subset_metadata, full_metadata)
    
    # Create linear_hybrid05_concat (64 + 128 = 192 dim)
    logger.info("\n=== Creating linear_hybrid05_concat ===")
    linear_hybrid05_concat = np.hstack([dense_cp_64, citation_tfidf])
    logger.info(f"Concatenated shape: {linear_hybrid05_concat.shape}")
    
    # Evaluate center_projected 64 alone for comparison
    logger.info("\n=== Evaluating center_projected_64 (baseline) ===")
    result_dense = evaluate_representation_fast("center_projected_64_15year", dense_cp_64, subset_metadata)
    
    # Evaluate citation TF-IDF outcome_hybrid_0.5 alone for comparison
    logger.info("\n=== Evaluating cited_decisions_tfidf_outcome_hybrid_0.5 (baseline) ===")
    result_citation = evaluate_representation_fast("cited_decisions_tfidf_outcome_hybrid_0.5_15year", citation_tfidf, subset_metadata)
    
    # Evaluate linear_hybrid05_concat
    logger.info("\n=== Evaluating linear_hybrid05_concat ===")
    result_concat = evaluate_representation_fast("linear_hybrid05_concat_15year", linear_hybrid05_concat, subset_metadata)
    
    # Save results
    from datetime import datetime
    combined = {
        'center_projected_64_15year': result_dense,
        'cited_decisions_tfidf_outcome_hybrid_0.5_15year': result_citation,
        'linear_hybrid05_concat_15year': result_concat,
    }
    
    output_file = OUTPUT_DIR / f"linear_hybrid05_concat_15year_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "linear_hybrid05_concat_15year_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY - LINEAR_HYBRID05_CONCAT 15-YEAR EVALUATION (FAST)")
    logger.info("=" * 70)
    
    for name, result in [
        ("center_projected_64_15year", result_dense),
        ("cited_decisions_tfidf_outcome_hybrid_0.5_15year", result_citation),
        ("linear_hybrid05_concat_15year", result_concat),
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
    if 'error' not in result_concat and 'error' not in result_dense and 'error' not in result_citation:
        concat_jp = result_concat['adversarial']['jurist_preference_rate']
        dense_jp = result_dense['adversarial']['jurist_preference_rate']
        citation_jp = result_citation['adversarial']['jurist_preference_rate']
        best_baseline = max(dense_jp, citation_jp)
        
        logger.info(f"\nIMPROVEMENT ANALYSIS:")
        logger.info(f"  Best baseline JP: {best_baseline:.4f}")
        logger.info(f"  Concat JP: {concat_jp:.4f}")
        logger.info(f"  Delta: {concat_jp - best_baseline:+.4f}")
        
        if concat_jp > best_baseline:
            logger.info(f"  ✓ linear_hybrid05_concat IMPROVES over best baseline")
        else:
            logger.info(f"  ✗ linear_hybrid05_concat does NOT improve over best baseline")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return combined


if __name__ == "__main__":
    main()
