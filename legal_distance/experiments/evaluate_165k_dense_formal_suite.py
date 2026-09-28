#!/usr/bin/env python3
"""
Evaluate 165k dense embeddings (center_projected 768/64/128) using the formal suite.
Adapts the 174k formal suite for the 165k dense embeddings (2000-2024).
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
from datetime import datetime

# Add evaluation to path for imports
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
from run_174k_formal_suite import (
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
DENSE_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/metadata.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/dense_165k_formal_suite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Dense representations to evaluate (from the 165k computation)
REPRESENTATIONS = {
    'center_projected_768dim': 'embeddings_center_projected.npy',
    'center_projected_64dim': 'embeddings_center_projected_64.npy',
    'center_projected_128dim': 'embeddings_center_projected_128.npy',
}


def load_dense_embeddings_and_metadata() -> Tuple[Dict[str, np.ndarray], List[Dict]]:
    """Load all dense embeddings and the 165k metadata."""
    logger.info("Loading 165k dense embeddings metadata...")
    with open(FULL_METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Full metadata: {len(metadata)} decisions")
    
    embeddings = {}
    for name, fname in REPRESENTATIONS.items():
        path = DENSE_EMBEDDINGS_DIR / fname
        if path.exists():
            emb = np.load(path)
            logger.info(f"Loaded {name}: {emb.shape}")
            embeddings[name] = emb
        else:
            logger.warning(f"Missing embedding file: {path}")
    
    return embeddings, metadata


def main():
    logger.info("=" * 70)
    logger.info(f"Evaluating 165k Dense Embeddings (2000-2024) - Formal Suite")
    logger.info(f"Using {EVALUATION_VERSION} with HNSW artifact fix")
    logger.info("=" * 70)
    
    # Load embeddings and metadata
    embeddings_dict, metadata = load_dense_embeddings_and_metadata()
    
    if not embeddings_dict:
        logger.error("No embeddings loaded!")
        return
    
    # Verify metadata and embeddings align
    n_meta = len(metadata)
    for name, emb in embeddings_dict.items():
        if emb.shape[0] != n_meta:
            logger.warning(f"Shape mismatch for {name}: embeddings {emb.shape[0]} vs metadata {n_meta}")
            # Trim embeddings to match metadata
            embeddings_dict[name] = emb[:n_meta]
            logger.info(f"  Trimmed to {n_meta}")
    
    # Evaluate each representation
    all_results = {}
    
    for name, embeddings in embeddings_dict.items():
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Evaluating: {name}")
            logger.info(f"Shape: {embeddings.shape}")
            logger.info(f"{'='*60}")
            
            result = evaluate_representation(name, embeddings, metadata)
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
    output_file = OUTPUT_DIR / f"evaluation_165k_dense_formal_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Also save latest symlink
    latest_file = OUTPUT_DIR / "evaluation_165k_dense_formal_suite_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("EVALUATION 165k DENSE FORMAL SUITE - SUMMARY (HNSW ARTIFACT FIXED)")
    logger.info("=" * 100)
    
    logger.info(f"\n{'Representation':<35} {'Verdict':<7} {'LangDom':>7} {'LD-P':>4} {'Jurist':>7} {'JP-P':>4} {'Both':>4} {'Backend':>10}")
    logger.info("-" * 85)
    
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
            logger.info(f"{name:<35} {'ERROR':<7} {'N/A':>7} {'N/A':>4} {'N/A':>7} {'N/A':>4} {'N/A':>4} {'N/A':>10}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        backend = adv.get('backend', 'N/A')
        
        logger.info(f"{name:<35} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>4} {jp:>7.4f} {jp_pass:>4} {both:>4} {backend:>10}")
    
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
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return all_results


if __name__ == "__main__":
    main()