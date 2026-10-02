#!/usr/bin/env python3
"""
Linear combination weight sweep for center_projected_64 + cited_decisions_tfidf at 22-year scale (2000-2021).
Tests weights from 0.1 to 0.9 to find optimal tradeoff between jurist preference and language dominance.
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
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
TFIDF_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2022))  # 2000-2021 inclusive (22 years)


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
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)}")
    
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
    logger.info(f"  Evaluating: {name}")
    
    # Adversarial benchmarks
    adversarial = run_adversarial_benchmarks_exact(embeddings, metadata)
    
    # Cross-language benchmarks
    cross_language = run_cross_language_benchmarks(embeddings, metadata)
    
    # Jurist usability benchmarks
    jurist_usability = run_jurist_usability_benchmarks(embeddings, metadata)
    
    # Determine verdict based on adversarial gates
    both_pass = (
        adversarial['adversarial_language_dominance']['status'] == 'PASS' and
        adversarial['jurist_pairwise_preference']['status'] == 'PASS'
    )
    
    verdict = 'PASS' if both_pass else 'FAIL'
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'adversarial': adversarial,
        'cross_language': cross_language,
        'jurist_usability': jurist_usability,
        'verdict': verdict,
        'both_adversarial_pass': both_pass,
    }


def weighted_concat(emb1: np.ndarray, emb2: np.ndarray, weight: float) -> np.ndarray:
    """Concatenate with weight scaling: [weight * emb1, (1-weight) * emb2] then L2 normalize."""
    combined = np.hstack([weight * emb1, (1 - weight) * emb2])
    norms = np.linalg.norm(combined, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return combined / norms


def main():
    logger.info("=" * 70)
    logger.info("LINEAR COMBINATION WEIGHT SWEEP AT 22-YEAR SCALE (144k decisions)")
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
    logger.info("Applying language center projection...")
    dense_cp = apply_language_center_projection(dense_emb, subset_metadata)
    
    # Apply PCA to 64 dim
    logger.info("Applying PCA to 64 dimensions...")
    dense_cp_64, explained_var = apply_pca_64(dense_cp)
    logger.info(f"Dense CP 64 shape: {dense_cp_64.shape}, explained var: {explained_var:.4f}")
    
    # Load citation TF-IDF for subset
    logger.info("\n=== Loading citation TF-IDF for 22-year subset ===")
    citation_tfidf = load_tfidf_for_subset("cited_decisions_tfidf.npy", subset_metadata, full_metadata)
    
    # Also load the production default for comparison
    citation_hybrid05 = load_tfidf_for_subset("cited_decisions_tfidf_outcome_hybrid_0.5.npy", subset_metadata, full_metadata)
    
    # Evaluate baselines
    logger.info("\n=== Evaluating Baselines ===")
    result_dense = evaluate_representation_fast("center_projected_64_22year", dense_cp_64, subset_metadata)
    result_citation = evaluate_representation_fast("cited_decisions_tfidf_22year", citation_tfidf, subset_metadata)
    result_citation_hybrid = evaluate_representation_fast("cited_decisions_tfidf_outcome_hybrid_0.5_22year", citation_hybrid05, subset_metadata)
    
    baselines = {
        'center_projected_64': result_dense,
        'cited_decisions_tfidf': result_citation,
        'cited_decisions_tfidf_outcome_hybrid_0.5': result_citation_hybrid,
    }
    
    # Weight sweep
    weights = np.arange(0.1, 1.0, 0.1)  # 0.1 to 0.9
    sweep_results = {}
    
    logger.info(f"\n=== Weight Sweep (cited_decisions_tfidf): {weights} ===")
    
    for weight in weights:
        logger.info(f"\nTesting weight={weight:.1f}...")
        combined = weighted_concat(dense_cp_64, citation_tfidf, weight)
        name = f"linear_weight_{weight:.1f}_22year"
        result = evaluate_representation_fast(name, combined, subset_metadata)
        sweep_results[f"weight_{weight:.1f}"] = result
        
        # Log key metrics
        adv = result['adversarial']
        logger.info(f"  LangDom: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"  JP: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        logger.info(f"  Both pass: {adv['both_pass']}")
    
    # Find best weight by jurist preference among PASSing configs
    passing_results = {w: r for w, r in sweep_results.items() if r['both_adversarial_pass']}
    
    if passing_results:
        best_weight = max(passing_results.items(), key=lambda x: x[1]['adversarial']['jurist_preference_rate'])
        logger.info(f"\n✓ Best PASSING weight: {best_weight[0]} with JP={best_weight[1]['adversarial']['jurist_preference_rate']:.4f}")
    else:
        # Find best by JP even if failing
        best_weight = max(sweep_results.items(), key=lambda x: x[1]['adversarial']['jurist_preference_rate'])
        logger.info(f"\n⚠ No PASSING weights. Best JP: {best_weight[0]} with JP={best_weight[1]['adversarial']['jurist_preference_rate']:.4f}")
    
    # Also test with outcome_hybrid_0.5
    logger.info("\n=== Weight Sweep with outcome_hybrid_0.5 ===")
    sweep_results_hybrid = {}
    
    for weight in weights:
        logger.info(f"Testing weight={weight:.1f} with outcome_hybrid_0.5...")
        combined = weighted_concat(dense_cp_64, citation_hybrid05, weight)
        name = f"linear_hybrid_weight_{weight:.1f}_22year"
        result = evaluate_representation_fast(name, combined, subset_metadata)
        sweep_results_hybrid[f"weight_{weight:.1f}"] = result
        
        adv = result['adversarial']
        logger.info(f"  LangDom: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"  JP: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
    
    passing_hybrid = {w: r for w, r in sweep_results_hybrid.items() if r['both_adversarial_pass']}
    
    if passing_hybrid:
        best_hybrid = max(passing_hybrid.items(), key=lambda x: x[1]['adversarial']['jurist_preference_rate'])
        logger.info(f"\n✓ Best PASSING weight (hybrid): {best_hybrid[0]} with JP={best_hybrid[1]['adversarial']['jurist_preference_rate']:.4f}")
    else:
        best_hybrid = max(sweep_results_hybrid.items(), key=lambda x: x[1]['adversarial']['jurist_preference_rate'])
        logger.info(f"\n⚠ No PASSING weights (hybrid). Best JP: {best_hybrid[0]} with JP={best_hybrid[1]['adversarial']['jurist_preference_rate']:.4f}")
    
    # Save all results
    from datetime import datetime
    combined_results = {
        'baselines': baselines,
        'sweep_cited_decisions_tfidf': sweep_results,
        'sweep_cited_decisions_tfidf_outcome_hybrid_0.5': sweep_results_hybrid,
        'best_weight_cited': best_weight[0] if 'best_weight' in locals() else None,
        'best_weight_hybrid': best_hybrid[0] if 'best_hybrid' in locals() else None,
        'timestamp': datetime.now().isoformat(),
        'n_decisions': len(subset_metadata),
        'year_range': '2000-2021',
    }
    
    output_file = OUTPUT_DIR / f"weight_sweep_22year_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(combined_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "weight_sweep_22year_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(combined_results, f, indent=2, default=str)
    
    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("WEIGHT SWEEP SUMMARY")
    logger.info("=" * 70)
    
    logger.info("\nBaselines:")
    for name, result in baselines.items():
        adv = result['adversarial']
        logger.info(f"  {name}: LangDom={adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']}), JP={adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']}), Both={result['both_adversarial_pass']}")
    
    logger.info("\nWeight sweep (cited_decisions_tfidf):")
    for weight in weights:
        key = f"weight_{weight:.1f}"
        r = sweep_results[key]
        adv = r['adversarial']
        status = "✓" if r['both_adversarial_pass'] else "✗"
        logger.info(f"  {status} w={weight:.1f}: LangDom={adv['language_dominance_score']:.4f}, JP={adv['jurist_preference_rate']:.4f}")
    
    logger.info("\nWeight sweep (cited_decisions_tfidf_outcome_hybrid_0.5):")
    for weight in weights:
        key = f"weight_{weight:.1f}"
        r = sweep_results_hybrid[key]
        adv = r['adversarial']
        status = "✓" if r['both_adversarial_pass'] else "✗"
        logger.info(f"  {status} w={weight:.1f}: LangDom={adv['language_dominance_score']:.4f}, JP={adv['jurist_preference_rate']:.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    return combined_results


if __name__ == "__main__":
    main()