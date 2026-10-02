#!/usr/bin/env python3
"""
Evaluation Lane - 19-Year Dense Embeddings Formal Suite
Runs the formal benchmark suite (frozen harness v3 with HNSW artifact fix) 
on 19-year (2000-2018, ~122k decisions) dense embeddings and linear combinations
from legal-distance lane.
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter
from datetime import datetime
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

# Add paths
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

from evaluation.run_174k_formal_suite import (
    evaluate_representation,
    load_evaluation_metadata,
    EVALUATION_VERSION,
    GLOBAL_SEED,
    CHAMBER_TO_BRANCH,
    assign_branch,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
LINEAR_COMB_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/linear_combinations_19year")
TFIDF_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/formal_suite/19year_dense")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS_19 = list(range(2000, 2019))  # 2000-2018 inclusive (19 years)


def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load dense embeddings for specified years and assemble in full metadata order."""
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
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
    
    for m in full_metadata:
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)} (expected {len(target_ids)})")
    
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


def apply_center_projection(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Apply language center projection to embeddings."""
    languages = [m.get('language', 'de') for m in metadata]
    unique_langs = sorted(set(languages))
    centers = {}
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    emb_cp = np.copy(embeddings)
    for i, lang in enumerate(languages):
        if lang in centers:
            emb_cp[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(emb_cp, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_cp = emb_cp / norms
    return emb_cp


def apply_pca(embeddings: np.ndarray, n_components: int) -> np.ndarray:
    """Apply PCA to reduce dimensionality."""
    pca = PCA(n_components=n_components, random_state=GLOBAL_SEED)
    emb_pca = pca.fit_transform(embeddings)
    emb_pca = normalize(emb_pca, norm='l2', axis=1)
    logger.info(f"PCA to {n_components} dim: explained variance = {pca.explained_variance_ratio_.sum():.4f}")
    return emb_pca


def load_citation_tfidf_for_subset(subset_metadata: List[Dict], full_metadata: List[Dict]) -> np.ndarray:
    """Load citation TF-IDF embeddings for the subset decisions."""
    logger.info("Loading citation TF-IDF embeddings for subset...")
    
    cited_tfidf_path = TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf.npy"
    cited_tfidf = np.load(cited_tfidf_path, mmap_mode='r')
    logger.info(f"Full citation TF-IDF shape: {cited_tfidf.shape}")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Extract embeddings for subset
    n_subset = len(subset_metadata)
    tfidf_dim = cited_tfidf.shape[1]
    subset_tfidf = np.zeros((n_subset, tfidf_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_tfidf[i] = cited_tfidf[full_idx]
    
    logger.info(f"Extracted subset citation TF-IDF shape: {subset_tfidf.shape}")
    return subset_tfidf


def load_outcome_hybrid_for_subset(subset_metadata: List[Dict], full_metadata: List[Dict], alpha: float = 0.5) -> np.ndarray:
    """Load cited_decisions_tfidf_outcome_hybrid embeddings for the subset decisions."""
    logger.info(f"Loading cited_decisions_tfidf_outcome_hybrid_{alpha} for subset...")
    
    hybrid_path = TFIDF_EMBEDDINGS_DIR / f"cited_decisions_tfidf_outcome_hybrid_{alpha}.npy"
    hybrid = np.load(hybrid_path, mmap_mode='r')
    logger.info(f"Full hybrid shape: {hybrid.shape}")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Extract embeddings for subset
    n_subset = len(subset_metadata)
    hybrid_dim = hybrid.shape[1]
    subset_hybrid = np.zeros((n_subset, hybrid_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_hybrid[i] = hybrid[full_idx]
    
    logger.info(f"Extracted subset hybrid shape: {subset_hybrid.shape}")
    return subset_hybrid


def create_concat(dense_emb: np.ndarray, citation_emb: np.ndarray, name: str) -> np.ndarray:
    """Concatenate dense and citation embeddings."""
    logger.info(f"Creating {name}: dense {dense_emb.shape} + citation {citation_emb.shape}")
    concat = np.hstack([dense_emb, citation_emb])
    logger.info(f"Concatenated shape: {concat.shape}")
    return concat


def load_19year_metadata() -> List[Dict]:
    """Load 19-year metadata from linear_combinations_19year directory."""
    metadata_path = LINEAR_COMB_DIR / "metadata_19year.json"
    with open(metadata_path) as f:
        metadata = json.load(f)
    logger.info(f"Loaded 19-year metadata: {len(metadata)} decisions")
    return metadata


def main():
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane - 19-Year Dense Embeddings Formal Suite")
    logger.info(f"Years: 2000-2018 ({len(COMPLETED_YEARS_19)} years)")
    logger.info(f"Using formal suite {EVALUATION_VERSION} with HNSW artifact fix")
    logger.info("=" * 70)
    
    # Load full 174k metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load 19-year dense embeddings (768-dim) from checkpoints
    logger.info("\n=== Loading 19-year dense embeddings (768-dim) from checkpoints ===")
    dense_768, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS_19)
    
    # Apply center projection
    logger.info("\n=== Applying language center projection ===")
    dense_cp_768 = apply_center_projection(dense_768, subset_metadata)
    
    # Create PCA versions
    logger.info("\n=== Creating PCA-reduced versions ===")
    dense_cp_128 = apply_pca(dense_cp_768, 128)
    dense_cp_64 = apply_pca(dense_cp_768, 64)
    
    # Load citation embeddings for subset
    logger.info("\n=== Loading citation embeddings for 19-year subset ===")
    citation_tfidf = load_citation_tfidf_for_subset(subset_metadata, full_metadata)
    hybrid_05 = load_outcome_hybrid_for_subset(subset_metadata, full_metadata, 0.5)
    
    # Load pre-computed linear combinations from legal-distance
    logger.info("\n=== Loading pre-computed linear combinations from legal-distance ===")
    linear_hybrid05_concat_path = LINEAR_COMB_DIR / "linear_hybrid05_concat_19year.npy"
    linear_hybrid05_concat = np.load(linear_hybrid05_concat_path)
    logger.info(f"Loaded linear_hybrid05_concat_19year: {linear_hybrid05_concat.shape}")
    
    # Create linear_citation_concat from dense_cp_64 + citation_tfidf
    linear_citation_concat = create_concat(dense_cp_64, citation_tfidf, "linear_citation_concat_19year")
    
    # Define all representations to evaluate
    representations = {
        'center_projected_768dim_19year': dense_cp_768,
        'center_projected_128dim_19year': dense_cp_128,
        'center_projected_64dim_19year': dense_cp_64,
        'linear_citation_concat_19year': linear_citation_concat,
        'linear_hybrid05_concat_19year': linear_hybrid05_concat,
    }
    
    # Also evaluate baselines for comparison
    representations['cited_decisions_tfidf_19year'] = citation_tfidf
    representations['cited_decisions_tfidf_outcome_hybrid_0.5_19year'] = hybrid_05
    
    # Run formal suite evaluation on each
    logger.info("\n" + "=" * 70)
    logger.info("RUNNING FORMAL SUITE EVALUATION")
    logger.info("=" * 70)
    
    all_results = {}
    
    for name, embeddings in representations.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating: {name}")
        logger.info(f"Shape: {embeddings.shape}")
        logger.info(f"{'='*60}")
        
        try:
            result = evaluate_representation(name, embeddings, subset_metadata)
            all_results[name] = result
            
            # Log summary
            if 'error' in result:
                logger.error(f"  {name}: ERROR - {result['error']}")
            else:
                adv = result['adversarial']
                logger.info(f"  {name}: verdict={result['verdict']}, "
                           f"lang_dom={adv['language_dominance_score']:.4f} "
                           f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                           f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                           f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
                           f"backend={adv.get('backend', 'N/A')}, subset={adv.get('subset_size', 'N/A')}")
        
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {
                'name': name,
                'error': str(e),
                'verdict': 'ERROR'
            }
    
    # Save all results
    output_file = OUTPUT_DIR / f"evaluation_19year_dense_formal_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Also save latest symlink
    latest_file = OUTPUT_DIR / "evaluation_19year_dense_formal_suite_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("EVALUATION 19-YEAR DENSE FORMAL SUITE - SUMMARY (HNSW ARTIFACT FIXED)")
    logger.info("=" * 100)
    
    logger.info(f"\n{'Representation':<50} {'Verdict':<7} {'LangDom':>7} {'LD-P':>4} {'Jurist':>7} {'JP-P':>4} {'Both':>4} {'Backend':>10}")
    logger.info("-" * 100)
    
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res['both_adversarial_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<50} {'ERROR':<7} {'N/A':>7} {'N/A':>4} {'N/A':>7} {'N/A':>4} {'N/A':>4} {'N/A':>10}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        backend = adv.get('backend', 'N/A')
        
        logger.info(f"{name:<50} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>4} {jp:>7.4f} {jp_pass:>4} {both:>4} {backend:>10}")
    
    # Find best representation (must pass both adversarial gates)
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Backend: {best[1]['adversarial'].get('backend', 'N/A')}")
        logger.info(f"   Valid subset size: {best[1]['adversarial'].get('subset_size', 'N/A')}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    # Reference: production default at 174k
    prod_default = 'cited_decisions_tfidf_outcome_hybrid_0.5'
    logger.info(f"\n📏 PRODUCTION DEFAULT at 174k ({prod_default}):")
    logger.info(f"   (from evaluation_174k_formal_suite_latest.json)")
    logger.info(f"   Language dominance: ~0.489 (PASS)")
    logger.info(f"   Jurist preference: ~0.727 (PASS)")
    logger.info(f"   Both adversarial pass: True")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return all_results


if __name__ == "__main__":
    main()