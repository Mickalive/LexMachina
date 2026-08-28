#!/usr/bin/env python3
"""
Reproduce center_projected representation and validate on v2 benchmark suite.

center_projected = baseline embeddings with language centers subtracted.
This is the ONLY v2 representation passing BOTH:
- adversarial language dominance < 0.85
- jurist pairwise preference > 0.5

Product decision: If reproduced successfully, center_projected becomes
the default reference representation to beat in legal-distance.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import sys

# Add paths - need to import the benchmark modules directly
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/data')
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map')

from real_corpus import load_real_corpus
from cross_language_benchmarks import (
    cross_language_neighbor_quality,
    zero_shot_cross_language_transfer,
    language_specific_representation_quality,
    adversarial_language_dominance,
    compute_representation as compute_debiased_citation_blended
)
from jurist_usability import (
    simulate_pairwise_preference,
    simulate_cluster_coherence_rating,
    simulate_zoom_task,
    simulate_cross_language_retrieval,
    prepare_metadata,
    create_debiased_citation_blended
)


def load_baseline_embeddings() -> Tuple[np.ndarray, List[Dict]]:
    """Load the baseline 768-dim embeddings and metadata."""
    embeddings_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy')
    metadata_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json')
    
    embeddings = np.load(embeddings_path)
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return embeddings, metadata


def create_center_projected(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """
    Create center_projected representation by subtracting language centers.
    
    For each embedding, subtract the mean embedding of its language cluster.
    This removes the language-specific component from each decision's embedding.
    """
    languages = sorted(set(m['language'] for m in metadata))
    lang_map = {l: i for i, l in enumerate(languages)}
    
    # Compute language centers
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
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
    
    return debiased


def load_corpus_with_branch() -> Tuple[np.ndarray, List[Dict]]:
    """Load corpus with branch metadata using real_corpus loader."""
    decisions, rep_fn, corpus = load_real_corpus(max_decisions=1000)
    
    # Get TF-IDF representation
    embeddings = []
    metadata = []
    for did, d in decisions.items():
        vec = rep_fn(did)
        if vec is not None:
            embeddings.append(vec)
            metadata.append({
                'decision_id': did,
                'language': d.language,
                'branch': d.branch,
                'legal_area': d.legal_area,
                'chamber': d.chamber
            })
    
    embeddings = np.array(embeddings)
    return embeddings, metadata


def compute_debiased_citation_blended_representation(embeddings: np.ndarray) -> np.ndarray:
    """Compute the validated debiased_citation_blended representation (64-dim)."""
    # PCA debiasing (n_pca=1)
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
    
    pca_debias = PCA(n_components=1, random_state=42)
    debias_component = pca_debias.fit_transform(embeddings)
    debiased = embeddings - debias_component @ pca_debias.components_
    
    # Project to 64-dim
    pca_64 = PCA(n_components=64, random_state=42)
    debiased_64 = pca_64.fit_transform(debiased)
    return normalize(debiased_64, norm='l2')


def run_cross_language_benchmarks(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Run all cross-language benchmarks on a representation."""
    print(f"\n{'='*70}")
    print(f"Cross-language benchmarks for {name}")
    print(f"{'='*70}")
    
    results = {}
    
    print("Running cross-language neighbor quality...")
    results['cross_language_neighbor_quality'] = cross_language_neighbor_quality(embeddings, metadata)
    print(f"  cross_lang_same_branch_mean: {results['cross_language_neighbor_quality']['cross_lang_same_branch_mean']:.4f}")
    print(f"  same_lang_same_branch_mean: {results['cross_language_neighbor_quality']['same_lang_same_branch_mean']:.4f}")
    print(f"  invariance_gap: {results['cross_language_neighbor_quality']['invariance_gap']:.4f}")
    
    print("Running zero-shot cross-language transfer...")
    results['zero_shot_transfer'] = zero_shot_cross_language_transfer(embeddings, metadata)
    print(f"  zero_shot_mean_nmi: {results['zero_shot_transfer']['zero_shot_mean_nmi']:.4f}")
    print(f"  in_domain_mean_nmi: {results['zero_shot_transfer']['in_domain_mean_nmi']:.4f}")
    print(f"  transfer_gap: {results['zero_shot_transfer']['transfer_gap']:.4f}")
    print(f"  status: {results['zero_shot_transfer']['status']}")
    
    print("Running language-specific representation quality...")
    results['language_specific_quality'] = language_specific_representation_quality(embeddings, metadata)
    print(f"  mean_nmi: {results['language_specific_quality']['mean_nmi']:.4f}")
    print(f"  std_nmi: {results['language_specific_quality']['std_nmi']:.4f}")
    print(f"  status: {results['language_specific_quality']['status']}")
    
    print("Running adversarial language dominance...")
    results['adversarial_language_dominance'] = adversarial_language_dominance(embeddings, metadata)
    print(f"  mean_language_dominance: {results['adversarial_language_dominance']['mean_language_dominance']:.4f}")
    print(f"  threshold: {results['adversarial_language_dominance']['threshold']}")
    print(f"  status: {results['adversarial_language_dominance']['status']}")
    
    # Summary
    passed = sum(1 for v in results.values() if v.get('status') == 'PASS')
    total = len(results)
    results['summary'] = {
        'total_benchmarks': total,
        'passed': passed,
        'failed': total - passed,
        'all_passed': passed == total
    }
    
    return results


def run_jurist_usability_benchmarks(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Run all jurist usability benchmarks on a representation."""
    print(f"\n{'='*70}")
    print(f"Jurist usability benchmarks for {name}")
    print(f"{'='*70}")
    
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    
    results = {}
    
    print("Running jurist pairwise preference simulation...")
    results['pairwise_preference'] = simulate_pairwise_preference(rep_valid, branches, languages)
    print(f"  legal_neighbor_rate: {results['pairwise_preference']['legal_neighbor_rate']:.4f}")
    print(f"  jurist_would_succeed_rate: {results['pairwise_preference']['jurist_would_succeed_rate']:.4f}")
    print(f"  status: {results['pairwise_preference']['status']}")
    
    print("Running jurist cluster coherence rating simulation...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(rep_valid, branches, languages)
    print(f"  mean_branch_purity: {results['cluster_coherence_rating']['mean_branch_purity']:.4f}")
    print(f"  mean_language_purity: {results['cluster_coherence_rating']['mean_language_purity']:.4f}")
    print(f"  status: {results['cluster_coherence_rating']['status']}")
    
    print("Running jurist zoom task simulation...")
    results['zoom_task'] = simulate_zoom_task(rep_valid, branches, languages, valid_indices,
                                               Path('/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json'))
    print(f"  coarse_purity: {results['zoom_task'].get('coarse_purity', 'N/A')}")
    print(f"  fine_purity: {results['zoom_task'].get('fine_purity', 'N/A')}")
    print(f"  status: {results['zoom_task'].get('status', 'N/A')}")
    
    print("Running jurist cross-language retrieval simulation...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(rep_valid, branches, languages)
    print(f"  mean_cross_language_recall_at_k: {results['cross_language_retrieval']['mean_cross_language_recall_at_k']:.4f}")
    print(f"  status: {results['cross_language_retrieval']['status']}")
    
    # Summary
    passed = sum(1 for v in results.values() if v.get('status') == 'PASS')
    total = len(results)
    results['summary'] = {
        'total_benchmarks': total,
        'passed': passed,
        'failed': total - passed,
        'all_passed': passed == total
    }
    
    return results


def main():
    print("=" * 70)
    print("REPRODUCE center_projected AND VALIDATE ON V2 BENCHMARK SUITE")
    print("=" * 70)
    
    # Load baseline embeddings and metadata
    print("\n1. Loading baseline embeddings (1000 decisions, 768-dim)...")
    baseline_embeddings, baseline_metadata = load_baseline_embeddings()
    print(f"   Shape: {baseline_embeddings.shape}")
    
    # Create center_projected
    print("\n2. Creating center_projected representation...")
    center_projected = create_center_projected(baseline_embeddings, baseline_metadata)
    print(f"   Shape: {center_projected.shape}")
    
    # Save center_projected
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected')
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / 'embeddings_center_projected.npy', center_projected)
    with open(output_dir / 'metadata.json', 'w') as f:
        json.dump(baseline_metadata, f, indent=2)
    print(f"   Saved to {output_dir}")
    
    # Load corpus for benchmarks (using real_corpus loader which has branch metadata)
    print("\n3. Loading corpus with branch metadata for benchmarks...")
    corpus_embeddings, corpus_metadata = load_corpus_with_branch()
    print(f"   Corpus embeddings shape: {corpus_embeddings.shape}")
    
    # Create center_projected on corpus embeddings
    print("\n4. Creating center_projected on corpus embeddings...")
    corpus_center_projected = create_center_projected(corpus_embeddings, corpus_metadata)
    print(f"   Shape: {corpus_center_projected.shape}")
    
    # Also create debiased_citation_blended for comparison
    print("\n5. Creating debiased_citation_blended baseline for comparison...")
    debiased_citation_blended = compute_debiased_citation_blended_representation(corpus_embeddings)
    print(f"   Shape: {debiased_citation_blended.shape}")
    
    # Run cross-language benchmarks
    print("\n" + "="*70)
    print("CROSS-LANGUAGE BENCHMARKS")
    print("="*70)
    
    print("\n--- center_projected ---")
    center_cross_lang = run_cross_language_benchmarks(corpus_center_projected, corpus_metadata, "center_projected")
    
    print("\n--- debiased_citation_blended (baseline) ---")
    baseline_cross_lang = run_cross_language_benchmarks(debiased_citation_blended, corpus_metadata, "debiased_citation_blended")
    
    # Run jurist usability benchmarks
    print("\n" + "="*70)
    print("JURIST USABILITY BENCHMARKS")
    print("="*70)
    
    print("\n--- center_projected ---")
    center_jurist = run_jurist_usability_benchmarks(center_projected, baseline_metadata, "center_projected")
    
    print("\n--- debiased_citation_blended (baseline) ---")
    baseline_jurist = run_jurist_usability_benchmarks(debiased_citation_blended, baseline_metadata, "debiased_citation_blended")
    
    # Summary comparison
    print("\n" + "="*70)
    print("SUMMARY COMPARISON")
    print("="*70)
    
    # Adversarial language dominance
    print("\nAdversarial Language Dominance (threshold < 0.85, lower is better):")
    center_dom = center_cross_lang['adversarial_language_dominance']['mean_language_dominance']
    baseline_dom = baseline_cross_lang['adversarial_language_dominance']['mean_language_dominance']
    print(f"  center_projected: {center_dom:.4f} {'✅ PASS' if center_dom < 0.85 else '❌ FAIL'}")
    print(f"  debiased_citation_blended: {baseline_dom:.4f} {'✅ PASS' if baseline_dom < 0.85 else '❌ FAIL'}")
    
    # Jurist pairwise preference
    print("\nJurist Pairwise Preference (threshold > 0.5, higher is better):")
    center_pref = center_jurist['pairwise_preference']['jurist_would_succeed_rate']
    baseline_pref = baseline_jurist['pairwise_preference']['jurist_would_succeed_rate']
    print(f"  center_projected: {center_pref:.4f} {'✅ PASS' if center_pref > 0.5 else '❌ FAIL'}")
    print(f"  debiased_citation_blended: {baseline_pref:.4f} {'✅ PASS' if baseline_pref > 0.5 else '❌ FAIL'}")
    
    # Overall verdict
    print("\n" + "="*70)
    print("OVERALL VERDICT")
    print("="*70)
    
    center_both_pass = (center_dom < 0.85) and (center_pref > 0.5)
    baseline_both_pass = (baseline_dom < 0.85) and (baseline_pref > 0.5)
    
    print(f"center_projected passes BOTH adversarial tests: {'✅ YES' if center_both_pass else '❌ NO'}")
    print(f"debiased_citation_blended passes BOTH adversarial tests: {'✅ YES' if baseline_both_pass else '❌ NO'}")
    
    if center_both_pass and not baseline_both_pass:
        print("\n✅ REPRODUCTION SUCCESSFUL: center_projected is the ONLY representation passing both adversarial tests")
    elif center_both_pass and baseline_both_pass:
        print("\n⚠️  Both pass - center_projected is not uniquely superior")
    else:
        print("\n❌ REPRODUCTION FAILED: center_projected does not pass both tests")
    
    # Save all results
    all_results = {
        'center_projected': {
            'cross_language': center_cross_lang,
            'jurist_usability': center_jurist,
        },
        'debiased_citation_blended': {
            'cross_language': baseline_cross_lang,
            'jurist_usability': baseline_jurist,
        },
        'verdict': {
            'center_projected_passes_both': center_both_pass,
            'baseline_passes_both': baseline_both_pass,
            'reproduction_successful': center_both_pass and not baseline_both_pass,
        }
    }
    
    with open(output_dir / 'v2_benchmark_results.json', 'w') as f:
        # Convert numpy types to Python types
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
        
        json.dump(convert(all_results), f, indent=2)
    
    print(f"\nResults saved to {output_dir / 'v2_benchmark_results.json'}")
    
    return all_results


if __name__ == "__main__":
    main()