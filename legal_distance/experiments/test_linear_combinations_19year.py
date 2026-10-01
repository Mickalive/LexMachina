#!/usr/bin/env python3
"""
Test linear_citation_concat and linear_hybrid05_concat at 19-year scale (2000-2018, ~122k decisions).
Combines 19-year center_projected dense embeddings with corresponding citation TF-IDF.
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
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/linear_combinations_19year")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2019))  # 2000-2018 inclusive (19 years)


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


def apply_language_center_projection(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Apply language center projection and L2 normalize."""
    languages = [m.get('language', 'de') for m in metadata]
    unique_langs = sorted(set(languages))
    centers = {}
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, lang in enumerate(languages):
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    return debiased


def apply_pca_64(embeddings: np.ndarray) -> Tuple[np.ndarray, float]:
    """Apply PCA to 64 dimensions and L2 normalize."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
    
    pca = PCA(n_components=64, random_state=GLOBAL_SEED)
    embeddings_64 = pca.fit_transform(embeddings)
    embeddings_64 = normalize(embeddings_64, norm='l2', axis=1)
    explained_var = pca.explained_variance_ratio_.sum()
    
    return embeddings_64, explained_var


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
    logger.info("TESTING LINEAR COMBINATIONS AT 19-YEAR SCALE (2000-2018) - FAST MODE")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load 19-year dense embeddings
    logger.info("\n=== Loading 19-year dense embeddings ===")
    dense_emb, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Apply language center projection to dense embeddings
    logger.info("Applying language center projection to dense embeddings...")
    dense_cp = apply_language_center_projection(dense_emb, subset_metadata)
    logger.info(f"Center-projected dense shape: {dense_cp.shape}")
    
    # Apply PCA to 64 dim
    logger.info("Applying PCA to 64 dimensions...")
    dense_cp_64, explained_var = apply_pca_64(dense_cp)
    logger.info(f"Dense CP 64 shape: {dense_cp_64.shape}, explained var: {explained_var:.4f}")
    
    # Load citation TF-IDF for subset
    logger.info("\n=== Loading citation TF-IDF for 19-year subset ===")
    citation_tfidf = load_tfidf_for_subset("cited_decisions_tfidf.npy", subset_metadata, full_metadata)
    citation_tfidf_hybrid05 = load_tfidf_for_subset("cited_decisions_tfidf_outcome_hybrid_0.5.npy", subset_metadata, full_metadata)
    
    # Create linear_citation_concat (64 + 128 = 192 dim)
    logger.info("\n=== Creating linear_citation_concat ===")
    linear_citation_concat = np.hstack([dense_cp_64, citation_tfidf])
    logger.info(f"Concatenated shape: {linear_citation_concat.shape}")
    
    # Create linear_hybrid05_concat (64 + 128 = 192 dim)
    logger.info("\n=== Creating linear_hybrid05_concat ===")
    linear_hybrid05_concat = np.hstack([dense_cp_64, citation_tfidf_hybrid05])
    logger.info(f"Concatenated shape: {linear_hybrid05_concat.shape}")
    
    # Evaluate center_projected 64 alone for comparison
    logger.info("\n=== Evaluating center_projected_64 (baseline) ===")
    result_dense = evaluate_representation_fast("center_projected_64_19year", dense_cp_64, subset_metadata)
    
    # Evaluate citation TF-IDF alone for comparison
    logger.info("\n=== Evaluating cited_decisions_tfidf (baseline) ===")
    result_citation = evaluate_representation_fast("cited_decisions_tfidf_19year", citation_tfidf, subset_metadata)
    
    # Evaluate citation TF-IDF outcome_hybrid_0.5 alone for comparison
    logger.info("\n=== Evaluating cited_decisions_tfidf_outcome_hybrid_0.5 (baseline) ===")
    result_citation_hybrid = evaluate_representation_fast("cited_decisions_tfidf_outcome_hybrid_0.5_19year", citation_tfidf_hybrid05, subset_metadata)
    
    # Evaluate linear_citation_concat
    logger.info("\n=== Evaluating linear_citation_concat ===")
    result_concat = evaluate_representation_fast("linear_citation_concat_19year", linear_citation_concat, subset_metadata)
    
    # Evaluate linear_hybrid05_concat
    logger.info("\n=== Evaluating linear_hybrid05_concat ===")
    result_hybrid_concat = evaluate_representation_fast("linear_hybrid05_concat_19year", linear_hybrid05_concat, subset_metadata)
    
    # Save results
    from datetime import datetime
    combined = {
        'center_projected_64_19year': result_dense,
        'cited_decisions_tfidf_19year': result_citation,
        'cited_decisions_tfidf_outcome_hybrid_0.5_19year': result_citation_hybrid,
        'linear_citation_concat_19year': result_concat,
        'linear_hybrid05_concat_19year': result_hybrid_concat,
    }
    
    output_file = OUTPUT_DIR / f"linear_combinations_19year_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "linear_combinations_19year_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY - LINEAR COMBINATIONS 19-YEAR EVALUATION (FAST)")
    logger.info("=" * 70)
    
    for name, result in [
        ("center_projected_64_19year", result_dense),
        ("cited_decisions_tfidf_19year", result_citation),
        ("cited_decisions_tfidf_outcome_hybrid_0.5_19year", result_citation_hybrid),
        ("linear_citation_concat_19year", result_concat),
        ("linear_hybrid05_concat_19year", result_hybrid_concat),
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
    
    # Check if linear combinations improve over baselines
    if all('error' not in r for r in [result_concat, result_hybrid_concat, result_dense, result_citation, result_citation_hybrid]):
        concat_jp = result_concat['adversarial']['jurist_preference_rate']
        hybrid_concat_jp = result_hybrid_concat['adversarial']['jurist_preference_rate']
        dense_jp = result_dense['adversarial']['jurist_preference_rate']
        citation_jp = result_citation['adversarial']['jurist_preference_rate']
        citation_hybrid_jp = result_citation_hybrid['adversarial']['jurist_preference_rate']
        best_baseline = max(dense_jp, citation_jp, citation_hybrid_jp)
        
        logger.info(f"\nIMPROVEMENT ANALYSIS:")
        logger.info(f"  Best baseline JP: {best_baseline:.4f}")
        logger.info(f"  linear_citation_concat JP: {concat_jp:.4f} (delta: {concat_jp - best_baseline:+.4f})")
        logger.info(f"  linear_hybrid05_concat JP: {hybrid_concat_jp:.4f} (delta: {hybrid_concat_jp - best_baseline:+.4f})")
        
        if concat_jp > best_baseline:
            logger.info(f"  ✓ linear_citation_concat IMPROVES over best baseline")
        else:
            logger.info(f"  ✗ linear_citation_concat does NOT improve over best baseline")
            
        if hybrid_concat_jp > best_baseline:
            logger.info(f"  ✓ linear_hybrid05_concat IMPROVES over best baseline")
        else:
            logger.info(f"  ✗ linear_hybrid05_concat does NOT improve over best baseline")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return combined


if __name__ == "__main__":
    main()