#!/usr/bin/env python3
"""
Legal Distance Lane v5 - Benchmark Refinement

Analyzes current benchmarks (v1 14 benchmarks, v2 additions) to identify:
1. Duplicate/redundant benchmarks
2. Non-discriminating benchmarks (all modes pass/fail)
3. Benchmarks with low signal-to-noise
4. Recommends refined benchmark suite for jurist-usefulness proxies
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Load evaluation v2 results
EVAL_V2_RESULTS = Path("/tmp/lex_accepted/evaluation/results/evaluation/v2_alternatives_results.json")
EVAL_V1_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/results/cycle_14_results.json")
SCALE_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/scale_test/scale_test_all_results.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/benchmark_refinement")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path: Path) -> Dict:
    with open(path, 'r') as f:
        return json.load(f)

def analyze_v1_benchmarks():
    """Analyze the 14 v1 benchmarks."""
    v1 = load_json(EVAL_V1_RESULTS)
    
    benchmarks = v1.get('benchmarks', {})
    logger.info("=" * 70)
    logger.info("V1 BENCHMARKS (14 benchmarks) - BASELINE RESULTS")
    logger.info("=" * 70)
    
    for name, result in benchmarks.items():
        status = result.get('status', 'UNKNOWN')
        # Extract key metric
        metrics = {k: v for k, v in result.items() if isinstance(v, (int, float)) and k not in ['status']}
        logger.info(f"  {name}: {status} - {metrics}")
    
    return benchmarks

def analyze_v2_benchmarks():
    """Analyze v2 benchmarks across representations."""
    v2 = load_json(EVAL_V2_RESULTS)
    
    logger.info("\n" + "=" * 70)
    logger.info("V2 BENCHMARKS - ACROSS REPRESENTATIONS")
    logger.info("=" * 70)
    
    # The v2 alternatives tested 5 representations
    reps = v2.get('v2_alternatives', {})
    for rep_name, rep_data in reps.items():
        if rep_name in ['v2_alternatives_overall', 'representations_tested']:
            continue
        logger.info(f"\n  {rep_name}:")
        if 'cross_language' in rep_data:
            cl = rep_data['cross_language']
            logger.info(f"    Language dominance: {cl.get('adversarial_language_dominance', {}).get('mean', 'N/A')}")
            logger.info(f"    Cross-lang neighbor quality: {cl.get('cross_language_neighbor_quality', {})}")
        if 'jurist_usability' in rep_data:
            ju = rep_data['jurist_usability']
            logger.info(f"    Pairwise preference: {ju.get('pairwise_preference', {}).get('legal_neighbor_rate', 'N/A')}")
            logger.info(f"    Cluster coherence: {ju.get('cluster_coherence_rating', {}).get('mean_branch_purity', 'N/A')}")
        if 'jurivoc' in rep_data:
            jv = rep_data['jurivoc']
            logger.info(f"    Jurivoc L2 NMI: {jv.get('l2_recovery_nmi', 'N/A')}")
            logger.info(f"    Passed: {jv.get('passed', 'N/A')}/{jv.get('total', 'N/A')}")
        logger.info(f"    Overall: {rep_data.get('overall_status', 'N/A')}")
    
    return reps

def analyze_scale_benchmarks():
    """Analyze which scale test benchmarks discriminate well."""
    scale = load_json(SCALE_RESULTS)
    
    logger.info("\n" + "=" * 70)
    logger.info("SCALE TEST - BENCHMARK DISCRIMINATION ANALYSIS")
    logger.info("=" * 70)
    
    # Collect metrics across all modes
    mode_metrics = {}
    for mode_name, results in scale.items():
        if 'embedding_shape' in results:
            # Fractal-map metrics
            fm = results
            mode_metrics[mode_name] = {
                'coarse_purity': fm.get('coarse_purity', 0),
                'fine_purity': fm.get('fine_purity', 0),
                'improvement_rate': fm.get('improvement_rate', 0),
                'legal_area_nmi': fm.get('legal_area_nmi', 0),
                'hierarchical_advantage': fm.get('hierarchical_advantage', 0),
                'verdict': fm.get('verdict', 'N/A'),
            }
    
    # Compute variance for each metric (discrimination power)
    metrics = ['coarse_purity', 'fine_purity', 'improvement_rate', 'legal_area_nmi', 'hierarchical_advantage']
    
    logger.info("\nMetric discrimination (std across 15 modes):")
    for metric in metrics:
        values = [m[metric] for m in mode_metrics.values()]
        mean_val = np.mean(values)
        std_val = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)
        logger.info(f"  {metric}: mean={mean_val:.4f}, std={std_val:.4f}, range=[{min_val:.4f}, {max_val:.4f}]")
    
    # Check which modes pass/fail
    passed = sum(1 for m in mode_metrics.values() if m['verdict'] == 'PASS')
    failed = sum(1 for m in mode_metrics.values() if m['verdict'] == 'FAIL')
    partial = sum(1 for m in mode_metrics.values() if m['verdict'] == 'PARTIAL')
    logger.info(f"\nVerdicts: PASS={passed}, FAIL={failed}, PARTIAL={partial}")
    
    return mode_metrics

def identify_redundant_benchmarks():
    """Identify redundant benchmarks across v1, v2, and fractal-map."""
    
    redundancy_analysis = {
        "citation_heritage_vs_citation_proximity": {
            "v1": "citation_heritage (AUC-ROC on shared citations >=1)",
            "v1_also": "citation_proximity (AUC-ROC on shared citations >=1) - SAME METRIC",
            "fractal_map": "citation graph structure captured in hierarchical clustering",
            "verdict": "REDUNDANT - citation_heritage and citation_proximity measure same thing",
            "recommendation": "Keep citation_heritage as primary; remove citation_proximity",
        },
        "citation_graph_neighborhood_vs_citation_heritage": {
            "v1": "citation_graph_neighborhood (AUC-ROC on shared citations >=2)",
            "overlap": "Stronger version of citation_heritage (>=2 vs >=1 shared citations)",
            "verdict": "PARTIALLY REDUNDANT - captures stronger citation signal",
            "recommendation": "Keep as 'strong_citation_heritage' if discriminating; else merge",
        },
        "branch_knn_vs_tf_metadata": {
            "v1": "branch_knn (k-NN classification on branch labels)",
            "v1_also": "tf_metadata_human_indexing (k-NN recall on court metadata)",
            "overlap": "Both measure alignment with human-assigned categories",
            "verdict": "PARTIALLY REDUNDANT - branch_knn uses 4 branches, tf_metadata uses granular legal_area",
            "recommendation": "Keep both but rename: 'branch_classification' and 'legal_area_retrieval'",
        },
        "multilingual_invariance_vs_cross_language_pairs": {
            "v1": "multilingual_invariance (separation metric)",
            "v1_also": "cross_language_pairs (separation metric)",
            "v2": "adversarial_cross_language_transfer (language dominance, zero-shot NMI)",
            "verdict": "REDUNDANT FAMILY - 3 benchmarks measuring cross-language alignment",
            "recommendation": "Consolidate to: 'adversarial_language_dominance' (primary) + 'zero_shot_transfer_NMI'",
        },
        "hierarchy_coherence_vs_zoom_coherence": {
            "v1": "hierarchy_coherence (branch purity + NMI, 4 branches)",
            "fractal_map": "zoom_coherence (improvement rate, hierarchical advantage)",
            "verdict": "COMPLEMENTARY - hierarchy_coherence = branch-level, zoom_coherence = cluster-level",
            "recommendation": "Keep both - they measure different aspects of hierarchical quality",
        },
        "boilerplate_resistance_vs_collapse_check": {
            "v1": "boilerplate_resistance_real_corpus (text-embedding correlation)",
            "v1_also": "collapse_check (pairwise similarity statistics)",
            "verdict": "DIFFERENT - boilerplate = content correlation, collapse = representation degeneracy",
            "recommendation": "Keep both",
        },
        "temporal_stability_vs_scale_benchmark": {
            "v1": "temporal_stability (random-split coherence drift)",
            "v2": "scale_benchmark_frozen_pca (position drift under corpus growth)",
            "verdict": "DIFFERENT - temporal = time splits, scale = corpus size growth",
            "recommendation": "Keep both - both validated as important",
        },
        "legal_area_clustering_vs_jurivoc": {
            "v1": "legal_area_clustering (branch NMI + purity on court legal_area)",
            "v2": "jurivoc_descriptor_integration (descriptor-level NMI/purity, hierarchy alignment)",
            "verdict": "COMPLEMENTARY - legal_area = court metadata, jurivoc = intellectual indexing",
            "recommendation": "Keep both - jurivoc is higher-quality human indexing",
        },
    }
    
    logger.info("\n" + "=" * 70)
    logger.info("BENCHMARK REDUNDANCY ANALYSIS")
    logger.info("=" * 70)
    
    for key, analysis in redundancy_analysis.items():
        logger.info(f"\n  {key}:")
        logger.info(f"    Verdict: {analysis['verdict']}")
        logger.info(f"    Recommendation: {analysis['recommendation']}")
    
    return redundancy_analysis

def propose_refined_benchmark_suite():
    """Propose a refined, non-redundant benchmark suite."""
    
    refined_suite = {
        "tier_1_core": [
            {
                "name": "adversarial_language_dominance",
                "source": "v2",
                "description": "Language dominance score < 0.85 (primary multilingual test)",
                "type": "adversarial",
                "priority": "critical",
            },
            {
                "name": "jurist_pairwise_preference",
                "source": "v2/new",
                "description": "Jurist preference rate > 0.5 for legal neighbors vs baseline",
                "type": "human_evaluation",
                "priority": "critical",
            },
            {
                "name": "jurivoc_l2_descriptor_recovery_nmi",
                "source": "v2",
                "description": "NMI with Jurivoc Level 2 descriptors > 0.4",
                "type": "weak_supervision",
                "priority": "high",
            },
            {
                "name": "zoom_coherence_improvement_rate",
                "source": "fractal_map",
                "description": "Fine cluster purity improvement rate > 50%",
                "type": "structural",
                "priority": "high",
            },
            {
                "name": "citation_heritage_auc",
                "source": "v1",
                "description": "AUC-ROC for shared-citation pairs (>=1) > 0.85",
                "type": "citation_structure",
                "priority": "high",
            },
            {
                "name": "legal_area_classification_accuracy",
                "source": "v1/branch_knn",
                "description": "k-NN classification accuracy on legal_area @5 > 0.8",
                "type": "human_indexing",
                "priority": "high",
            },
            {
                "name": "scale_stability_frozen_pca",
                "source": "v2",
                "description": "Position drift = 0, neighbor preservation = 1.0 under corpus growth",
                "type": "stability",
                "priority": "high",
            },
        ],
        "tier_2_diagnostic": [
            {
                "name": "zero_shot_cross_language_transfer_nmi",
                "source": "v2",
                "description": "Zero-shot cross-language NMI (diagnostic, not gate)",
                "type": "multilingual",
                "priority": "medium",
            },
            {
                "name": "hierarchical_advantage",
                "source": "fractal_map",
                "description": "Hierarchical Leiden fine purity > flat Leiden at same resolution",
                "type": "structural",
                "priority": "medium",
            },
            {
                "name": "boilerplate_resistance_correlation",
                "source": "v1",
                "description": "Text-embedding correlation < 0.3 (low boilerplate influence)",
                "type": "robustness",
                "priority": "medium",
            },
            {
                "name": "collapse_check_mean_similarity",
                "source": "v1",
                "description": "Mean pairwise similarity < 0.15 (no representation collapse)",
                "type": "robustness",
                "priority": "medium",
            },
            {
                "name": "temporal_stability_std",
                "source": "v1",
                "description": "Std of k-NN score across time splits < 0.02",
                "type": "stability",
                "priority": "medium",
            },
            {
                "name": "jurivoc_hierarchy_alignment",
                "source": "v2",
                "description": "Multi-level Jurivoc taxonomy coherence > 0.1 separation",
                "type": "weak_supervision",
                "priority": "medium",
            },
        ],
        "tier_3_exploratory": [
            {
                "name": "cross_language_retrieval_recall",
                "source": "v2",
                "description": "Cross-language legal equivalent retrieval recall@10",
                "type": "multilingual",
                "priority": "low",
            },
            {
                "name": "jurist_cluster_coherence_rating",
                "source": "v2",
                "description": "Human rating of cluster legal coherence",
                "type": "human_evaluation",
                "priority": "low",
            },
            {
                "name": "jurist_zoom_task",
                "source": "v2",
                "description": "Human navigation performance at multiple resolutions",
                "type": "human_evaluation",
                "priority": "low",
            },
        ],
        "removed_redundant": [
            "citation_proximity (duplicate of citation_heritage)",
            "multilingual_invariance (subsumed by adversarial_language_dominance)",
            "cross_language_pairs (subsumed by adversarial_language_dominance)",
            "tf_metadata_human_indexing (subsumed by legal_area_classification + jurivoc)",
        ],
    }
    
    logger.info("\n" + "=" * 70)
    logger.info("PROPOSED REFINED BENCHMARK SUITE")
    logger.info("=" * 70)
    
    for tier, benchmarks in refined_suite.items():
        if tier == "removed_redundant":
            logger.info(f"\n  {tier.upper()}:")
            for b in benchmarks:
                logger.info(f"    - {b}")
        else:
            logger.info(f"\n  {tier.upper()} ({len(benchmarks)} benchmarks):")
            for b in benchmarks:
                logger.info(f"    - {b['name']}: {b['description']} [{b['priority']}]")
    
    return refined_suite

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v5 - Benchmark Refinement")
    logger.info("=" * 70)
    
    analyze_v1_benchmarks()
    analyze_v2_benchmarks()
    analyze_scale_benchmarks()
    redundancy = identify_redundant_benchmarks()
    refined = propose_refined_benchmark_suite()
    
    # Save all analysis
    output = {
        "redundancy_analysis": redundancy,
        "refined_benchmark_suite": refined,
        "summary": {
            "v1_benchmarks": 14,
            "v2_benchmarks_added": 17,
            "fractal_map_benchmarks": 6,
            "total_before_refinement": 37,
            "tier_1_core": 7,
            "tier_2_diagnostic": 6,
            "tier_3_exploratory": 3,
            "removed_redundant": 4,
            "total_after_refinement": 16,
        },
    }
    
    with open(OUTPUT_DIR / "benchmark_refinement_analysis.json", 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    logger.info("\n" + "=" * 70)
    logger.info("BENCHMARK REFINEMENT COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total benchmarks before: 37 (14 v1 + 17 v2 + 6 fractal-map)")
    logger.info(f"Total benchmarks after: 16 (7 core + 6 diagnostic + 3 exploratory)")
    logger.info(f"Removed redundant: 4")
    logger.info(f"Output: {OUTPUT_DIR}/benchmark_refinement_analysis.json")
    
    return output

if __name__ == "__main__":
    main()
