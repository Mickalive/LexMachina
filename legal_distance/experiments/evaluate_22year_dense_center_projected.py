#!/usr/bin/env python3
"""
Evaluate 174k dense embeddings (22 years: 2000-2021, ~144k decisions) with center_projected debiasing.
1. Apply language-center projection to remove language bias
2. Apply frozen PCA (fitted on this data with seed=42) to get 64-dim and 128-dim versions
3. Run formal evaluation suite on all versions
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

sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
from run_174k_formal_suite import (
    evaluate_representation,
    EVALUATION_VERSION,
    GLOBAL_SEED,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2022))  # 2000-2021 inclusive (22 years)


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


def save_pca_model(pca: PCA, output_path: Path, name: str):
    """Save PCA model info for reproducibility."""
    pca_info = {
        'name': name,
        'n_components': pca.n_components_,
        'original_dim': pca.n_features_in_,
        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
        'explained_variance_ratio_sum': float(pca.explained_variance_ratio_.sum()),
        'random_state': 42,
        'mean': pca.mean_.tolist(),
        'components_shape': pca.components_.shape,
    }
    with open(output_path, 'w') as f:
        json.dump(pca_info, f, indent=2)
    logger.info(f"Saved PCA model to {output_path}")


def evaluate_embeddings(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run formal evaluation on embeddings."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*70}")
    
    result = evaluate_representation(name, embeddings, metadata)
    
    # Save individual result
    from datetime import datetime
    output_file = OUTPUT_DIR / f"{name}_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    return result


def main():
    logger.info("=" * 70)
    logger.info(f"Evaluating 174k Dense Embeddings with Center Projection (22 years: 2000-2021)")
    logger.info(f"Using formal suite {EVALUATION_VERSION}")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load and assemble dense embeddings for years 2000-2021
    embeddings_768, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Step 1: Apply language-center projection
    logger.info("\n=== Step 1: Language-Center Projection ===")
    embeddings_center_projected = language_center_projection(embeddings_768, subset_metadata)
    
    # Step 2: Apply frozen PCA to get 64-dim version
    logger.info("\n=== Step 2: Frozen PCA (768 -> 64 dim) ===")
    embeddings_64, pca_64 = apply_frozen_pca(embeddings_center_projected, n_components=64, random_state=42)
    save_pca_model(pca_64, OUTPUT_DIR / "pca_model_22year_64.json", "center_projected_64dim_22year")
    
    # Step 3: Apply frozen PCA to get 128-dim version
    logger.info("\n=== Step 3: Frozen PCA (768 -> 128 dim) ===")
    embeddings_128, pca_128 = apply_frozen_pca(embeddings_center_projected, n_components=128, random_state=42)
    save_pca_model(pca_128, OUTPUT_DIR / "pca_model_22year_128.json", "center_projected_128dim_22year")
    
    # Step 4: Evaluate center_projected (768-dim)
    logger.info("\n=== Step 4: Evaluate center_projected 768-dim ===")
    result_768 = evaluate_embeddings("center_projected_768dim_22year", embeddings_center_projected, subset_metadata)
    
    # Step 5: Evaluate center_projected 64-dim
    logger.info("\n=== Step 5: Evaluate center_projected 64-dim ===")
    result_64 = evaluate_embeddings("center_projected_64dim_22year", embeddings_64, subset_metadata)
    
    # Step 6: Evaluate center_projected 128-dim
    logger.info("\n=== Step 6: Evaluate center_projected 128-dim ===")
    result_128 = evaluate_embeddings("center_projected_128dim_22year", embeddings_128, subset_metadata)
    
    # Step 7: Evaluate raw 768-dim for comparison
    logger.info("\n=== Step 7: Evaluate raw 768-dim (baseline) ===")
    result_raw = evaluate_embeddings("multilingual_e5_768dim_22year", embeddings_768, subset_metadata)
    
    # Summary
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
    
    # Save combined results
    combined = {
        'raw_768dim': result_raw,
        'center_projected_768dim': result_768,
        'center_projected_64dim': result_64,
        'center_projected_128dim': result_128,
    }
    combined_file = OUTPUT_DIR / "combined_results.json"
    with open(combined_file, 'w') as f:
        json.dump(combined, f, indent=2, default=str)
    logger.info(f"\nCombined results saved to: {combined_file}")
    
    return combined


if __name__ == "__main__":
    main()