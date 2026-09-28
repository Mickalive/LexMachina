#!/usr/bin/env python3
"""
Adversarial evaluation of 165k center_projected representations.
Tests: cross-language, jurist usability, scale stability.
"""

# CRITICAL: Insert paths BEFORE any other imports
import sys
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/data')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')
# Override the path that cross_language_benchmarks.py inserts
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')

import json
import numpy as np
from pathlib import Path
from typing import List, Dict
from collections import Counter

from cross_language_benchmarks import (
    cross_language_neighbor_quality,
    zero_shot_cross_language_transfer,
    language_specific_representation_quality,
    adversarial_language_dominance,
)
from jurist_usability import (
    simulate_pairwise_preference,
    simulate_cluster_coherence_rating,
    simulate_zoom_task,
    simulate_cross_language_retrieval,
    prepare_metadata,
)

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def load_165k_embeddings(representation: str = "center_projected_64"):
    """Load 165k embeddings and metadata."""
    if representation == "center_projected_64":
        emb_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/embeddings_center_projected_64.npy")
    elif representation == "center_projected_768":
        emb_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/embeddings_center_projected.npy")
    elif representation == "center_projected_128":
        emb_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/embeddings_center_projected_128.npy")
    elif representation == "raw_768":
        emb_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/embeddings_768.npy")
    else:
        raise ValueError(f"Unknown representation: {representation}")
    
    meta_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/metadata.json")
    
    embeddings = np.load(emb_path)
    with open(meta_path, 'r') as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded {representation}: {embeddings.shape}, metadata: {len(metadata)}")
    return embeddings, metadata


def evaluate_cross_language(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Evaluate cross-language benchmarks."""
    logger.info("=" * 70)
    logger.info("V2 CROSS-LANGUAGE BENCHMARKS")
    logger.info("=" * 70)
    
    results = {}
    
    logger.info("Running cross-language neighbor quality...")
    results['cross_language_neighbor_quality'] = cross_language_neighbor_quality(embeddings, metadata)
    logger.info(f"  cross_lang_same_branch_mean: {results['cross_language_neighbor_quality']['cross_lang_same_branch_mean']:.4f}")
    logger.info(f"  same_lang_same_branch_mean: {results['cross_language_neighbor_quality']['same_lang_same_branch_mean']:.4f}")
    logger.info(f"  invariance_gap: {results['cross_language_neighbor_quality']['invariance_gap']:.4f}")
    
    logger.info("Running zero-shot cross-language transfer...")
    results['zero_shot_transfer'] = zero_shot_cross_language_transfer(embeddings, metadata)
    logger.info(f"  zero_shot_mean_nmi: {results['zero_shot_transfer']['zero_shot_mean_nmi']:.4f}")
    logger.info(f"  in_domain_mean_nmi: {results['zero_shot_transfer']['in_domain_mean_nmi']:.4f}")
    logger.info(f"  transfer_gap: {results['zero_shot_transfer']['transfer_gap']:.4f}")
    logger.info(f"  status: {results['zero_shot_transfer']['status']}")
    
    logger.info("Running language-specific representation quality...")
    results['language_specific_quality'] = language_specific_representation_quality(embeddings, metadata)
    logger.info(f"  mean_nmi: {results['language_specific_quality']['mean_nmi']:.4f}")
    logger.info(f"  std_nmi: {results['language_specific_quality']['std_nmi']:.4f}")
    logger.info(f"  status: {results['language_specific_quality']['status']}")
    
    logger.info("Running adversarial language dominance...")
    results['adversarial_language_dominance'] = adversarial_language_dominance(embeddings, metadata)
    logger.info(f"  mean_language_dominance: {results['adversarial_language_dominance']['mean_language_dominance']:.4f}")
    logger.info(f"  threshold: {results['adversarial_language_dominance']['threshold']}")
    logger.info(f"  status: {results['adversarial_language_dominance']['status']}")
    
    passed = sum(1 for v in results.values() if v.get('status') == 'PASS')
    total = len(results)
    results['summary'] = {'total_benchmarks': total, 'passed': passed, 'failed': total - passed, 'all_passed': passed == total}
    
    return results


def evaluate_jurist_usability(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Evaluate jurist usability benchmarks."""
    logger.info("=" * 70)
    logger.info("V2 JURIST USABILITY BENCHMARKS")
    logger.info("=" * 70)
    
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    
    logger.info(f"Valid decisions for jurist eval: {len(rep_valid)} / {len(embeddings)}")
    
    results = {}
    
    logger.info("Running jurist pairwise preference simulation...")
    results['pairwise_preference'] = simulate_pairwise_preference(rep_valid, branches, languages)
    logger.info(f"  legal_neighbor_rate: {results['pairwise_preference']['legal_neighbor_rate']:.4f}")
    logger.info(f"  jurist_would_succeed_rate: {results['pairwise_preference']['jurist_would_succeed_rate']:.4f}")
    logger.info(f"  status: {results['pairwise_preference']['status']}")
    
    logger.info("Running jurist cluster coherence rating simulation...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(rep_valid, branches, languages)
    logger.info(f"  mean_branch_purity: {results['cluster_coherence_rating']['mean_branch_purity']:.4f}")
    logger.info(f"  mean_language_purity: {results['cluster_coherence_rating']['mean_language_purity']:.4f}")
    logger.info(f"  status: {results['cluster_coherence_rating']['status']}")
    
    logger.info("Running jurist zoom task simulation...")
    results['zoom_task'] = simulate_zoom_task(rep_valid, branches, languages, valid_indices,
                                               Path('/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json'))
    logger.info(f"  coarse_purity: {results['zoom_task'].get('coarse_purity', 'N/A')}")
    logger.info(f"  fine_purity: {results['zoom_task'].get('fine_purity', 'N/A')}")
    logger.info(f"  status: {results['zoom_task'].get('status', 'N/A')}")
    
    logger.info("Running jurist cross-language retrieval simulation...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(rep_valid, branches, languages)
    logger.info(f"  mean_cross_language_recall_at_k: {results['cross_language_retrieval']['mean_cross_language_recall_at_k']:.4f}")
    logger.info(f"  status: {results['cross_language_retrieval']['status']}")
    
    passed = sum(1 for v in results.values() if v.get('status') == 'PASS')
    total = len(results)
    results['summary'] = {'total_benchmarks': total, 'passed': passed, 'failed': total - passed, 'all_passed': passed == total}
    
    return results


# Add scale_benchmarks_frozen path
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')

def evaluate_scale_stability(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Evaluate scale stability via subsampling."""
    logger.info("=" * 70)
    logger.info("V2 SCALE STABILITY BENCHMARKS (SUBSAMPLING)")
    logger.info("=" * 70)
    
    from scale_benchmarks_frozen import position_drift, neighbor_preservation, cluster_stability
    
    np.random.seed(42)
    indices = np.arange(len(embeddings))
    np.random.shuffle(indices)
    
    sizes = [200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
    sizes = [s for s in sizes if s < len(embeddings)]
    results = {'growth_steps': []}
    
    prev_rep = None
    prev_size = 0
    
    for size in sizes:
        subset_indices = indices[:size]
        subset_emb = embeddings[subset_indices]
        
        step_result = {'corpus_size': size, 'representation_shape': list(subset_emb.shape)}
        
        if prev_rep is not None:
            common_indices = list(range(prev_size))
            step_result['vs_prev_position_drift'] = position_drift(prev_rep, subset_emb, common_indices)
            step_result['vs_prev_neighbor_preservation_k10'] = neighbor_preservation(prev_rep, subset_emb, common_indices, k=10)
            step_result['vs_prev_cluster_stability_k10'] = cluster_stability(prev_rep, subset_emb, common_indices, n_clusters=10)
        
        results['growth_steps'].append(step_result)
        prev_rep = subset_emb
        prev_size = size
    
    # Summary
    logger.info("  Growth steps:")
    for step in results['growth_steps']:
        if 'vs_prev_position_drift' in step:
            drift = step['vs_prev_position_drift']['mean_cosine_similarity']
            neighbor = step['vs_prev_neighbor_preservation_k10']['mean_preservation_rate']
            cluster = step['vs_prev_cluster_stability_k10']['nmi']
            logger.info(f"    Size {step['corpus_size']}: position_drift={drift:.6f}, neighbor_pres={neighbor:.4f}, cluster_nmi={cluster:.4f}")
    
    return results


def evaluate_representation(name: str, representation: str):
    """Evaluate a single representation."""
    logger.info(f"\n{'='*70}")
    logger.info(f"EVALUATING {name} ({representation})")
    logger.info(f"{'='*70}")
    
    embeddings, metadata = load_165k_embeddings(representation)
    
    # Run evaluations
    cl_results = evaluate_cross_language(embeddings, metadata)
    jurist_results = evaluate_jurist_usability(embeddings, metadata)
    scale_results = evaluate_scale_stability(embeddings, metadata)
    
    # Critical tests
    center_dom = cl_results['adversarial_language_dominance']['mean_language_dominance']
    center_pref = jurist_results['pairwise_preference']['jurist_would_succeed_rate']
    
    logger.info(f"\nCRITICAL ADVERSARIAL TESTS for {name}:")
    logger.info(f"  Adversarial Language Dominance (< 0.85): {center_dom:.4f} {'PASS' if center_dom < 0.85 else 'FAIL'}")
    logger.info(f"  Jurist Pairwise Preference (> 0.5): {center_pref:.4f} {'PASS' if center_pref > 0.5 else 'FAIL'}")
    
    both_pass = (center_dom < 0.85) and (center_pref > 0.5)
    logger.info(f"  BOTH PASS: {'YES' if both_pass else 'NO'}")
    
    return {
        'representation': name,
        'cross_language': cl_results,
        'jurist_usability': jurist_results,
        'scale_stability': scale_results,
        'critical_tests': {
            'adversarial_language_dominance': float(center_dom),
            'jurist_pairwise_preference': float(center_pref),
            'both_pass': both_pass,
        }
    }


def main():
    logger.info("=" * 70)
    logger.info("ADVERSARIAL EVALUATION OF 165K DENSE EMBEDDINGS")
    logger.info("=" * 70)
    
    representations = [
        ("center_projected_64", "center_projected_64"),
        ("center_projected_768", "center_projected_768"),
        ("center_projected_128", "center_projected_128"),
        ("raw_768", "raw_768"),
    ]
    
    all_results = {}
    
    for name, rep_key in representations:
        try:
            all_results[name] = evaluate_representation(name, rep_key)
        except Exception as e:
            logger.error(f"Failed to evaluate {name}: {e}")
            all_results[name] = {'error': str(e)}
    
    # Summary comparison
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY COMPARISON")
    logger.info("=" * 70)
    
    for name, res in all_results.items():
        if 'error' in res:
            logger.info(f"  {name}: ERROR - {res['error']}")
            continue
        ct = res['critical_tests']
        logger.info(f"  {name}: LangDom={ct['adversarial_language_dominance']:.4f} ({'PASS' if ct['adversarial_language_dominance'] < 0.85 else 'FAIL'}), "
                   f"JuristPref={ct['jurist_pairwise_preference']:.4f} ({'PASS' if ct['jurist_pairwise_preference'] > 0.5 else 'FAIL'}), "
                   f"BOTH={'YES' if ct['both_pass'] else 'NO'}")
    
    # Save results
    output_dir = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    with open(output_dir / 'adversarial_evaluation_165k.json', 'w') as f:
        json.dump(convert(all_results), f, indent=2)
    
    logger.info(f"\nResults saved to {output_dir / 'adversarial_evaluation_165k.json'}")
    
    return all_results


if __name__ == "__main__":
    main()