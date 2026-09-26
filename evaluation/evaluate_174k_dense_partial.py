#!/usr/bin/env python3
"""
Evaluate 174k dense embeddings (partial: years 2000-2015) using the formal suite.
Assembles year-split embeddings in the order of the full 174k metadata.
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter

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
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/dense_partial_2000_2015")
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


def evaluate_dense_partial():
    """Main evaluation function for partial dense embeddings."""
    logger.info("=" * 70)
    logger.info(f"Evaluating 174k Dense Embeddings (Partial: 2000-2015)")
    logger.info(f"Using formal suite {EVALUATION_VERSION} with HNSW artifact fix")
    logger.info("=" * 70)
    
    # Load full metadata
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        full_metadata = json.load(f)
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load and assemble dense embeddings for years 2000-2015
    embeddings, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Run evaluation
    logger.info(f"\nEvaluating representation: multilingual_e5_768dim_partial_2000_2015")
    logger.info(f"Subset size: {len(subset_metadata)} decisions")
    
    result = evaluate_representation(
        "multilingual_e5_768dim_partial_2000_2015",
        embeddings,
        subset_metadata
    )
    
    # Save results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"dense_partial_2000_2015_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "dense_partial_2000_2015_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info(f"Latest symlink: {latest_file}")
    
    # Print summary
    if 'error' not in result:
        adv = result['adversarial']
        logger.info(f"\n{'='*70}")
        logger.info(f"SUMMARY: multilingual_e5_768dim_partial_2000_2015")
        logger.info(f"{'='*70}")
        logger.info(f"Verdict: {result['verdict']}")
        logger.info(f"Language dominance: {adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']})")
        logger.info(f"Jurist preference: {adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        logger.info(f"Both adversarial pass: {adv['both_pass']}")
        logger.info(f"Backend: {adv.get('backend', 'N/A')}")
        logger.info(f"Subset size: {adv.get('subset_size', 'N/A')}")
        
        # Cross-language
        cl = result.get('cross_language', {})
        if cl:
            logger.info(f"\nCross-language:")
            for k, v in cl.items():
                if isinstance(v, dict) and 'status' in v:
                    logger.info(f"  {k}: {v['status']}")
        
        # Full corpus benchmarks
        fc = result.get('full_corpus', {})
        if fc:
            logger.info(f"\nFull-corpus benchmarks (HNSW on subsamples):")
            for k, v in fc.items():
                if isinstance(v, dict) and 'status' in v:
                    logger.info(f"  {k}: {v['status']} (backend={v.get('backend', 'N/A')})")
    else:
        logger.error(f"Evaluation error: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    evaluate_dense_partial()