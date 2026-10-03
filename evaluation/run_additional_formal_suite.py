#!/usr/bin/env python3
"""
Evaluation Lane - Additional 174k Formal Suite Evaluations
Runs the formal benchmark suite on representations that have landed from legal-distance
but haven't been evaluated by the evaluation lane's formal suite yet.

Covers:
- 22-year dense embeddings (2000-2021, ~144k decisions): raw_768, center_projected_768/128/64
- 19-year linear_hybrid05_concat (~122k decisions)
- Any other 174k-scale embeddings available
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

# Add paths
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')

from run_174k_formal_suite import (
    evaluate_representation,
    EVALUATION_VERSION,
    GLOBAL_SEED,
    load_evaluation_metadata,
    CHAMBER_TO_BRANCH,
    assign_branch,
    prepare_metadata,
    get_adversarial_subsample,
    run_cross_language_benchmarks,
    run_jurist_usability_benchmarks,
    run_full_corpus_benchmarks_hnsw,
    run_adversarial_benchmarks_exact,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_BASE = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/formal_suite")

# 22-year completed years (2000-2021)
COMPLETED_YEARS_22 = list(range(2000, 2022))

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
        
        if not meta_path.exists() or not emb_path.exists():
            logger.warning(f"Missing files for year {year}: meta={meta_path.exists()}, emb={emb_path.exists()}")
            continue
            
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
        if year not in year_meta:
            continue
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


def language_center_projection(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """
    Project each embedding to remove the component toward its language center.
    This is equivalent to centering each language cluster in embedding space.
    """
    languages = sorted(set(m.get('language', 'unknown') for m in metadata))
    
    # Compute language centers
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f"  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}")
    
    # For each embedding, subtract its language center
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f"Center projected shape: {debiased.shape}")
    logger.info(f"Norm stats: min={np.linalg.norm(debiased, axis=1).min():.6f}, max={np.linalg.norm(debiased, axis=1).max():.6f}, mean={np.linalg.norm(debiased, axis=1).mean():.6f}")
    
    return debiased


def apply_frozen_pca(embeddings: np.ndarray, n_components: int = 64, random_state: int = 42) -> Tuple[np.ndarray, PCA]:
    """Apply PCA fitted on the given embeddings (frozen for this dataset)."""
    logger.info(f"Fitting PCA: {embeddings.shape[1]} -> {n_components} dimensions...")
    pca = PCA(n_components=n_components, random_state=random_state)
    reduced = pca.fit_transform(embeddings)
    reduced = normalize(reduced, norm='l2', axis=1)
    
    explained_var = pca.explained_variance_ratio_.sum()
    logger.info(f"Explained variance ratio (top {n_components}): {explained_var:.4f}")
    
    return reduced, pca


def evaluate_embeddings(name: str, embeddings: np.ndarray, metadata: List[Dict], output_dir: Path) -> Dict[str, Any]:
    """Run formal evaluation on embeddings and save results."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*70}")
    
    result = evaluate_representation(name, embeddings, metadata)
    
    # Save individual result
    from datetime import datetime
    output_file = output_dir / f"{name}_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    # Also save latest
    latest_file = output_dir / f"{name}_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    logger.info(f"Saved result to {output_file}")
    return result


def evaluate_22year_dense():
    """Evaluate 22-year dense embeddings (2000-2021)."""
    logger.info("=" * 70)
    logger.info(f"Evaluating 22-Year Dense Embeddings (2000-2021)")
    logger.info("=" * 70)
    
    output_dir = OUTPUT_BASE / "22year_dense"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load and assemble dense embeddings for years 2000-2021
    embeddings_768, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS_22)
    
    # Step 1: Apply language-center projection
    logger.info("\n=== Step 1: Language-Center Projection ===")
    embeddings_center_projected = language_center_projection(embeddings_768, subset_metadata)
    
    # Step 2: Apply frozen PCA to get 64-dim version
    logger.info("\n=== Step 2: Frozen PCA (768 -> 64 dim) ===")
    embeddings_64, pca_64 = apply_frozen_pca(embeddings_center_projected, n_components=64, random_state=42)
    
    # Step 3: Apply frozen PCA to get 128-dim version
    logger.info("\n=== Step 3: Frozen PCA (768 -> 128 dim) ===")
    embeddings_128, pca_128 = apply_frozen_pca(embeddings_center_projected, n_components=128, random_state=42)
    
    # Step 4: Evaluate center_projected (768-dim)
    logger.info("\n=== Step 4: Evaluate center_projected 768-dim ===")
    result_768 = evaluate_embeddings("center_projected_768dim_22year", embeddings_center_projected, subset_metadata, output_dir)
    
    # Step 5: Evaluate center_projected 64-dim
    logger.info("\n=== Step 5: Evaluate center_projected 64-dim ===")
    result_64 = evaluate_embeddings("center_projected_64dim_22year", embeddings_64, subset_metadata, output_dir)
    
    # Step 6: Evaluate center_projected 128-dim
    logger.info("\n=== Step 6: Evaluate center_projected 128-dim ===")
    result_128 = evaluate_embeddings("center_projected_128dim_22year", embeddings_128, subset_metadata, output_dir)
    
    # Step 7: Evaluate raw 768-dim for comparison
    logger.info("\n=== Step 7: Evaluate raw 768-dim (baseline) ===")
    result_raw = evaluate_embeddings("multilingual_e5_768dim_22year", embeddings_768, subset_metadata, output_dir)
    
    # Save combined results
    combined = {
        'raw_768dim': result_raw,
        'center_projected_768dim': result_768,
        'center_projected_64dim': result_64,
        'center_projected_128dim': result_128,
    }
    combined_file = output_dir / "combined_results.json"
    with open(combined_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    logger.info(f"\nCombined results saved to: {combined_file}")
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY - 22-Year Dense Embeddings Evaluation")
    logger.info("=" * 70)
    
    for name, result in [
        ("Raw 768-dim", result_raw),
        ("Center Projected 768-dim", result_768),
        ("Center Projected 64-dim", result_64),
        ("Center Projected 128-dim", result_128),
    ]:
        if 'error' not in result:
            adv = result['adversarial']
            logger.info(f"\n{name}:")
            logger.info(f"  Verdict: {result['verdict']}")
            logger.info(f"  Language dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
            logger.info(f"  Jurist preference: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
            logger.info(f"  Both adversarial pass: {adv['both_pass']}")
        else:
            logger.info(f"\n{name}: ERROR - {result.get('error')}")
    
    return combined


def evaluate_19year_linear_hybrid():
    """Evaluate 19-year linear_hybrid05_concat."""
    logger.info("=" * 70)
    logger.info(f"Evaluating 19-Year Linear Hybrid (122k decisions)")
    logger.info("=" * 70)
    
    output_dir = OUTPUT_BASE / "19year_linear_hybrid"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metadata
    metadata_path = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/linear_combinations_19year/metadata_19year.json")
    with open(metadata_path) as f:
        metadata = json.load(f)
    logger.info(f"Metadata: {len(metadata)} decisions")
    
    # Load embedding
    emb_path = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_hybrid05_concat_19year.npy")
    embeddings = np.load(emb_path)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    
    # Evaluate
    result = evaluate_embeddings("linear_hybrid05_concat_19year", embeddings, metadata, output_dir)
    
    # Print summary
    if 'error' not in result:
        adv = result['adversarial']
        logger.info(f"\n19-year Linear Hybrid:")
        logger.info(f"  Verdict: {result['verdict']}")
        logger.info(f"  Language dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"  Jurist preference: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        logger.info(f"  Both adversarial pass: {adv['both_pass']}")
    
    return result


def main():
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane - Additional 174k Formal Suite ({EVALUATION_VERSION})")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info("=" * 70)
    
    all_results = {}
    
    # 1. Evaluate 22-year dense embeddings
    try:
        results_22yr = evaluate_22year_dense()
        all_results['22year_dense'] = results_22yr
    except Exception as e:
        logger.error(f"Failed to evaluate 22-year dense: {e}")
        import traceback
        traceback.print_exc()
        all_results['22year_dense'] = {'error': str(e)}
    
    # 2. Evaluate 19-year linear hybrid
    try:
        result_19yr = evaluate_19year_linear_hybrid()
        all_results['19year_linear_hybrid'] = result_19yr
    except Exception as e:
        logger.error(f"Failed to evaluate 19-year linear hybrid: {e}")
        import traceback
        traceback.print_exc()
        all_results['19year_linear_hybrid'] = {'error': str(e)}
    
    # Save overall combined results
    from datetime import datetime
    overall_file = OUTPUT_BASE / f"additional_formal_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(overall_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info(f"\nOverall results saved to: {overall_file}")
    
    return all_results


if __name__ == "__main__":
    main()