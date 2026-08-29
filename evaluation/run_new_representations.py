#!/usr/bin/env python3
"""
Evaluate new representations from legal-distance v6 against frozen harness v3.
This extends the canonical v3 evaluation with:
- Citation role embeddings (following, citing, all_weighted + alpha blends)
- multilingual-e5-small pretrained embeddings
"""

import json
import numpy as np
import logging
import sys
import os
from pathlib import Path

# Add evaluation directory to path for importing harness functions
sys.path.insert(0, str(Path(__file__).parent))

from evaluation_v3_harness import (
    GLOBAL_SEED, LANGUAGE_DOMINANCE_THRESHOLD, JURIST_PAIRWISE_THRESHOLD,
    CROSS_LANG_RECALL_THRESHOLD, CLUSTER_COHERENCE_THRESHOLD,
    K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG,
    N_CLUSTERS_COHERENCE, LEX_ACCEPTED_ROOT, REPO_ROOT,
    load_evaluation_metadata, prepare_metadata, assign_branch,
    adversarial_language_dominance, simulate_pairwise_preference,
    compute_jurivoc_alignment, compute_scale_stability,
    compute_boilerplate_resistance, run_fractal_quality_benchmarks,
    evaluate_representation
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def load_metadata_1000():
    """Load first 1000 decisions from the 1200-decision metadata."""
    metadata = load_evaluation_metadata()
    return metadata[:1000]

def evaluate_new_representation(name: str, embeddings: np.ndarray, metadata: list) -> dict:
    """Evaluate a single new representation using frozen harness benchmarks."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating NEW representation: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    # Ensure embeddings match metadata length
    if embeddings.shape[0] != len(metadata):
        logger.warning(f"Embedding count ({embeddings.shape[0]}) != metadata count ({len(metadata)})")
        min_len = min(embeddings.shape[0], len(metadata))
        embeddings = embeddings[:min_len]
        metadata = metadata[:min_len]
        logger.info(f"Truncated to {min_len}")
    
    result = evaluate_representation(name, embeddings, metadata)
    return result

def main():
    # Set global seed for reproducibility
    np.random.seed(GLOBAL_SEED)
    
    logger.info("=" * 70)
    logger.info("Evaluation Lane - New Representations from legal-distance v6")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info("=" * 70)
    
    # Load metadata (1000 decisions to match new embeddings)
    logger.info("\n1. Loading evaluation metadata (1000 decisions)...")
    metadata = load_metadata_1000()
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Define new representations to evaluate
    new_representations = {
        # Citation role embeddings (from citation_roles_rebuilt)
        'citation_following': '/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_following_rebuilt.npy',
        'citation_citing': '/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_citing_rebuilt.npy',
        'citation_all_weighted': '/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt/citation_role_all_weighted_rebuilt.npy',
        
        # Alpha blends with center_projected_64 (need to load center_projected_64 and blend)
        # These will be computed below
        
        # multilingual-e5-small pretrained
        'multilingual_e5_small_pretrained': '/tmp/lex_accepted/legal-distance/legal_distance/results/v6/finetune_multilingual_e5/embeddings_multilingual_e5_small_pretrained.npy',
    }
    
    # Load center_projected_64 for alpha blending
    cp64_path = Path(os.environ.get("LEX_ACCEPTED_ROOT", "/tmp/lex_accepted")) / "legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy"
    if cp64_path.exists():
        cp64_embeddings = np.load(cp64_path)
        # Truncate to 1000 if needed
        if cp64_embeddings.shape[0] > 1000:
            cp64_embeddings = cp64_embeddings[:1000]
        logger.info(f"Loaded center_projected_64 for blending: {cp64_embeddings.shape}")
    else:
        logger.error(f"center_projected_64 not found at {cp64_path}")
        cp64_embeddings = None
    
    all_results = {}
    
    # Evaluate each base representation
    for name, path in new_representations.items():
        path = Path(path)
        if not path.exists():
            logger.warning(f"  {name}: NOT FOUND at {path}")
            all_results[name] = {'error': f'File not found: {path}', 'verdict': 'ERROR'}
            continue
        
        try:
            embeddings = np.load(path)
            # Convert float64 to float32 for consistency
            if embeddings.dtype == np.float64:
                embeddings = embeddings.astype(np.float32)
            logger.info(f"  Loaded {name}: {embeddings.shape}, dtype={embeddings.dtype}")
            
            result = evaluate_new_representation(name, embeddings, metadata)
            all_results[name] = result
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'name': name, 'error': str(e), 'verdict': 'ERROR'}
    
    # Evaluate alpha blends (if center_projected_64 available)
    if cp64_embeddings is not None:
        alpha_blends = [
            ('citation_following_alpha0.3', 'citation_following', 0.3),
            ('citation_following_alpha0.5', 'citation_following', 0.5),
            ('citation_following_alpha0.7', 'citation_following', 0.7),
            ('citation_citing_alpha0.3', 'citation_citing', 0.3),
            ('citation_citing_alpha0.5', 'citation_citing', 0.5),
            ('citation_citing_alpha0.7', 'citation_citing', 0.7),
            ('citation_all_weighted_alpha0.3', 'citation_all_weighted', 0.3),
            ('citation_all_weighted_alpha0.5', 'citation_all_weighted', 0.5),
            ('citation_all_weighted_alpha0.7', 'citation_all_weighted', 0.7),
        ]
        
        for blend_name, base_name, alpha in alpha_blends:
            if base_name in all_results and 'error' not in all_results[base_name]:
                # Get base embeddings
                base_path = new_representations[base_name]
                base_embeddings = np.load(base_path)
                if base_embeddings.dtype == np.float64:
                    base_embeddings = base_embeddings.astype(np.float32)
                if base_embeddings.shape[0] > 1000:
                    base_embeddings = base_embeddings[:1000]
                
                # Alpha blend: (1-alpha) * cp64 + alpha * citation
                blended = (1 - alpha) * cp64_embeddings + alpha * base_embeddings
                # Normalize
                from sklearn.preprocessing import normalize
                blended = normalize(blended, norm='l2', axis=1)
                
                result = evaluate_new_representation(blend_name, blended, metadata)
                all_results[blend_name] = result
            else:
                logger.warning(f"  Skipping {blend_name}: base {base_name} not available")
    
    # Load existing canonical v3 results
    canonical_path = REPO_ROOT / "evaluation/results/v3/evaluation_v3_results.json"
    with open(canonical_path) as f:
        canonical_results = json.load(f)
    
    # Merge new results into canonical
    for name, result in all_results.items():
        if 'error' not in result:
            canonical_results[name] = result
            logger.info(f"Added {name} to canonical results: verdict={result['verdict']}")
        else:
            logger.warning(f"Skipping {name} due to error: {result.get('error')}")
    
    # Save updated canonical results
    with open(canonical_path, 'w') as f:
        json.dump(canonical_results, f, indent=2, default=str)
    
    logger.info(f"\nUpdated canonical results saved to: {canonical_path}")
    logger.info(f"Total representations in canonical: {len(canonical_results)}")
    
    # Print summary
    logger.info("\n" + "=" * 90)
    logger.info("NEW REPRESENTATIONS SUMMARY")
    logger.info("=" * 90)
    logger.info(f"{'Representation':<40} {'Verdict':<7} {'LangDom':>7} {'LD-P':>5} {'Jurist':>7} {'JP-P':>5} {'Both':>5}")
    logger.info("-" * 90)
    
    for name, res in all_results.items():
        if 'error' in res:
            logger.info(f"{name:<40} {'ERROR':<7}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        logger.info(f"{name:<40} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>5} {jp:>7.4f} {jp_pass:>5} {both:>5}")
    
    return all_results

if __name__ == "__main__":
    main()