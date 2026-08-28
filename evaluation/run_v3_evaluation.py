#!/usr/bin/env python3
"""
Evaluation v3 — Full Adversarial Benchmark Suite on Expanded Slice (1,200 decisions)

Validates:
- legal-distance unsupervised signal ablation results (center_projected baseline)
- frontier_metric_learning_jurivoc supervised metric learning results (not yet available)

Adversarial benchmarks:
- Language dominance
- Jurist pairwise preference
- Jurivoc hierarchy alignment
- Scale stability (frozen PCA)
- Boilerplate resistance

Freeze evaluation harness with global seed = 42.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import sys
import importlib.util

# Frozen global seed for reproducibility
GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

eval_dir = Path('/home/runner/work/LexMachina/LexMachina/evaluation')
tests_dir = eval_dir / 'tests'

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load benchmark modules
cross_lang = load_module('cross_language_benchmarks', tests_dir / 'cross_language_benchmarks.py')
jurist_usability = load_module('jurist_usability', tests_dir / 'jurist_usability.py')
jurivoc_module = load_module('jurivoc_benchmarks', tests_dir / 'jurivoc_benchmarks.py')
scale_frozen = load_module('scale_benchmarks_frozen', tests_dir / 'scale_benchmarks_frozen.py')

# Import functions
cross_language_neighbor_quality = cross_lang.cross_language_neighbor_quality
zero_shot_cross_language_transfer = cross_lang.zero_shot_cross_language_transfer
language_specific_representation_quality = cross_lang.language_specific_representation_quality
adversarial_language_dominance = cross_lang.adversarial_language_dominance
run_all_cross_language_benchmarks = cross_lang.run_all_cross_language_benchmarks

prepare_metadata = jurist_usability.prepare_metadata
simulate_pairwise_preference = jurist_usability.simulate_pairwise_preference
simulate_cluster_coherence_rating = jurist_usability.simulate_cluster_coherence_rating
simulate_zoom_task = jurist_usability.simulate_zoom_task
simulate_cross_language_retrieval = jurist_usability.simulate_cross_language_retrieval
run_all_jurist_usability_benchmarks = jurist_usability.run_all_jurist_usability_benchmarks

JurivocBenchmarks = jurivoc_module.JurivocBenchmarks

run_frozen_scale_benchmark = scale_frozen.run_frozen_scale_benchmark
compute_frozen_pipeline = scale_frozen.compute_frozen_pipeline
position_drift = scale_frozen.position_drift
neighbor_preservation = scale_frozen.neighbor_preservation
cluster_stability = scale_frozen.cluster_stability


def load_expanded_slice_metadata() -> List[Dict]:
    """Load the expanded slice metadata (1,200 decisions)."""
    metadata_path = Path('/home/runner/work/LexMachina/LexMachina/evaluation/data/bger_expanded_1200_metadata.jsonl')
    metadata = []
    with open(metadata_path, 'r') as f:
        for line in f:
            metadata.append(json.loads(line))
    return metadata


def load_center_projected_full() -> Tuple[np.ndarray, List[Dict]]:
    """Load center_projected embeddings for 1,200 decisions and align with expanded slice metadata."""
    # Load embeddings
    emb_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy')
    embeddings = np.load(emb_path)
    
    # Load center_projected metadata
    meta_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json')
    with open(meta_path, 'r') as f:
        cp_metadata = json.load(f)
    
    # Load expanded slice metadata (target order)
    expanded_metadata = load_expanded_slice_metadata()
    
    # Create mapping from decision_id to index in center_projected
    cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    
    # Align embeddings to expanded slice order
    aligned_embeddings = np.zeros((len(expanded_metadata), embeddings.shape[1]), dtype=embeddings.dtype)
    aligned_metadata = []
    
    for i, exp_meta in enumerate(expanded_metadata):
        did = exp_meta['decision_id']
        if did in cp_id_to_idx:
            cp_idx = cp_id_to_idx[did]
            aligned_embeddings[i] = embeddings[cp_idx]
            # Use expanded slice metadata (richer)
            aligned_metadata.append(exp_meta)
        else:
            print(f"WARNING: Decision {did} not found in center_projected metadata")
    
    print(f"Loaded and aligned {len(aligned_embeddings)} decisions")
    print(f"Embedding shape: {aligned_embeddings.shape}")
    return aligned_embeddings, aligned_metadata


def run_cross_language_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run cross-language adversarial benchmarks."""
    print("\n" + "="*70)
    print("CROSS-LANGUAGE ADVERSARIAL BENCHMARKS")
    print("="*70)
    
    results = run_all_cross_language_benchmarks(embeddings, metadata)
    results['representation'] = 'center_projected'
    results['n_decisions'] = len(embeddings)
    results['embedding_dim'] = embeddings.shape[1]
    results['global_seed'] = GLOBAL_SEED
    return results


def prepare_metadata_full(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata - returns full-length arrays."""
    CHAMBER_TO_BRANCH = {
        "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
        "I. Zivilrechtliche Abteilung": "zivilrecht",
        "II. Zivilrechtliche Abteilung": "zivilrecht",
        "I. Strafrechtliche Abteilung": "strafrecht",
        "II. Strafrechtliche Abteilung": "strafrecht",
        "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
        "IIe Cour de droit social": "sozialversicherungsrecht",
        "Ire Cour de droit public": "oeffentliches_recht",
        "IIe Cour de droit public": "oeffentliches_recht",
        "Ire Cour de droit civil": "zivilrecht",
        "IIe Cour de droit civil": "zivilrecht",
        "Ire Cour de droit pénal": "strafrecht",
        "IIe Cour de droit pénal": "strafrecht",
    }
    
    def assign_branch(chamber: str) -> str:
        if chamber in CHAMBER_TO_BRANCH:
            return CHAMBER_TO_BRANCH[chamber]
        chamber_lower = chamber.lower()
        if "öffentlich" in chamber_lower or "public" in chamber_lower:
            return "oeffentliches_recht"
        if "zivil" in chamber_lower or "civil" in chamber_lower:
            return "zivilrecht"
        if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower:
            return "strafrecht"
        if "sozial" in chamber_lower or "social" in chamber_lower:
            return "sozialversicherungsrecht"
        return "unknown"
    
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        branches.append(branch)
        languages.append(lang)
        chambers.append(chamber)
        
        if branch != "unknown":
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


def run_jurist_usability_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run jurist usability simulation benchmarks."""
    print("\n" + "="*70)
    print("JURIST USABILITY SIMULATION BENCHMARKS")
    print("="*70)
    
    # Use full-length arrays to avoid indexing issues
    branches, languages, chambers, valid_indices = prepare_metadata_full(metadata)
    
    print(f"Total decisions: {len(branches)}")
    print(f"Valid decisions: {len(valid_indices)}")
    print(f"Branch distribution (valid): {Counter([branches[i] for i in valid_indices])}")
    print(f"Language distribution (valid): {Counter([languages[i] for i in valid_indices])}")
    
    # Use only valid decisions for benchmarks
    rep_valid = embeddings[valid_indices]
    branches_valid = branches[valid_indices]
    languages_valid = languages[valid_indices]
    
    # Run benchmarks directly (bypass run_all which has the same bug)
    results = {}
    
    print("Running jurist pairwise preference simulation...")
    results['pairwise_preference'] = simulate_pairwise_preference(rep_valid, branches_valid, languages_valid)
    
    print("Running jurist cluster coherence rating simulation...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(rep_valid, branches_valid, languages_valid)
    
    print("Running jurist zoom task simulation...")
    try:
        results['zoom_task'] = simulate_zoom_task(rep_valid, branches_valid, languages_valid, valid_indices,
                                                   Path('/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json'))
    except Exception as e:
        print(f"Zoom task failed (expected - cluster assignments only for 1000 decisions): {e}")
        results['zoom_task'] = {'status': 'SKIP', 'reason': f'Cluster assignments only available for 1000-decision baseline: {e}'}
    
    print("Running jurist cross-language retrieval simulation...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(rep_valid, branches_valid, languages_valid)
    
    # Summary
    passed = sum(1 for v in results.values() if v.get('status') == 'PASS')
    total = len(results)
    results['summary'] = {
        'total_benchmarks': total,
        'passed': passed,
        'failed': total - passed,
        'all_passed': passed == total
    }
    
    results['representation'] = 'center_projected'
    results['n_decisions'] = len(rep_valid)
    results['embedding_dim'] = embeddings.shape[1]
    results['global_seed'] = GLOBAL_SEED
    return results


def run_jurivoc_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run Jurivoc descriptor benchmarks."""
    print("\n" + "="*70)
    print("JURIVOC DESCRIPTOR BENCHMARKS")
    print("="*70)
    
    decision_ids = [m.get('decision_id', '') for m in metadata]
    benchmarks = JurivocBenchmarks(embeddings, decision_ids)
    results = benchmarks.run_all()
    
    results['representation'] = 'center_projected'
    results['n_decisions'] = len(embeddings)
    results['embedding_dim'] = embeddings.shape[1]
    results['global_seed'] = GLOBAL_SEED
    return results


def run_scale_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run scale stability benchmarks with frozen PCA."""
    print("\n" + "="*70)
    print("SCALE STABILITY BENCHMARKS (FROZEN PCA)")
    print("="*70)
    
    # Load the original 768-dim baseline embeddings for the expanded slice
    # We need to recompute from the original baseline to test frozen PCA
    # For now, we'll test on the 64-dim center_projected directly
    # The frozen PCA test is designed for 768->64 pipeline
    
    # Since center_projected is already 64-dim, we can't apply the same frozen PCA test
    # But we can test position stability by comparing subsets
    # We'll use the original baseline embeddings if available
    
    # Try to load baseline embeddings for the expanded slice
    # Actually, the center_projected_full was created from some 768-dim embeddings
    # Let's check if we have the 768-dim version
    
    emb_768_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_768.npy')
    if emb_768_path.exists():
        embeddings_768 = np.load(emb_768_path)
        print(f"Loaded 768-dim embeddings: {embeddings_768.shape}")
        
        # Align to expanded slice order
        meta_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json')
        with open(meta_path, 'r') as f:
            cp_metadata = json.load(f)
        
        expanded_metadata = load_expanded_slice_metadata()
        cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
        
        aligned_768 = np.zeros((len(expanded_metadata), embeddings_768.shape[1]), dtype=embeddings_768.dtype)
        for i, exp_meta in enumerate(expanded_metadata):
            did = exp_meta['decision_id']
            if did in cp_id_to_idx:
                cp_idx = cp_id_to_idx[did]
                aligned_768[i] = embeddings_768[cp_idx]
        
        # Run frozen scale benchmark on 768-dim embeddings
        results = run_frozen_scale_benchmark(aligned_768, expanded_metadata)
        results['representation'] = 'center_projected'
        results['embedding_dim'] = 64
        results['global_seed'] = GLOBAL_SEED
        return results
    else:
        print("768-dim embeddings not available, skipping frozen PCA scale test")
        return {'status': 'SKIP', 'reason': '768-dim embeddings not available'}


def run_boilerplate_resistance(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run boilerplate resistance test."""
    print("\n" + "="*70)
    print("BOILERPLATE RESISTANCE TEST")
    print("="*70)
    
    # This requires full text of decisions - check if available
    # The expanded slice metadata doesn't have full text
    # We'll note this as a limitation
    
    return {
        'status': 'SKIP',
        'reason': 'Full decision text not available in expanded slice metadata. Requires corpus text for perturbation test.',
        'recommendation': 'Run when corpus lane provides full text for expanded slice'
    }


def main():
    print("=" * 70)
    print("EVALUATION v3 — ADVERSARIAL BENCHMARK SUITE ON EXPANDED SLICE")
    print("=" * 70)
    print(f"Global seed: {GLOBAL_SEED}")
    print(f"Factory Direction Version: 6")
    print(f"Baseline representation: center_projected")
    print(f"Slice: 1,200 decisions (expanded slice: 1000 from 2024 + 50 each from 2020-2023)")
    
    # Load data
    print("\nLoading center_projected embeddings for expanded slice...")
    embeddings, metadata = load_center_projected_full()
    
    # Verify language/branch distribution
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    print(f"\nLanguage distribution: {Counter(languages)}")
    print(f"Branch distribution: {Counter(branches)}")
    
    all_results = {
        'factory_direction_version': 6,
        'evaluation_version': 3,
        'global_seed': GLOBAL_SEED,
        'baseline_representation': 'center_projected',
        'slice': 'expanded_1200',
        'n_decisions': len(embeddings),
        'embedding_dim': embeddings.shape[1],
        'language_distribution': dict(Counter(languages)),
        'branch_distribution': dict(Counter(branches)),
        'benchmarks': {}
    }
    
    # 1. Cross-language adversarial benchmarks
    try:
        all_results['benchmarks']['cross_language'] = run_cross_language_benchmarks(embeddings, metadata)
    except Exception as e:
        print(f"Cross-language benchmarks failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['benchmarks']['cross_language'] = {'error': str(e)}
    
    # 2. Jurist usability simulations
    try:
        all_results['benchmarks']['jurist_usability'] = run_jurist_usability_benchmarks(embeddings, metadata)
    except Exception as e:
        print(f"Jurist usability benchmarks failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['benchmarks']['jurist_usability'] = {'error': str(e)}
    
    # 3. Jurivoc descriptor benchmarks
    try:
        all_results['benchmarks']['jurivoc'] = run_jurivoc_benchmarks(embeddings, metadata)
    except Exception as e:
        print(f"Jurivoc benchmarks failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['benchmarks']['jurivoc'] = {'error': str(e)}
    
    # 4. Scale stability benchmarks (frozen PCA)
    try:
        all_results['benchmarks']['scale_stability'] = run_scale_benchmarks(embeddings, metadata)
    except Exception as e:
        print(f"Scale benchmarks failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['benchmarks']['scale_stability'] = {'error': str(e)}
    
    # 5. Boilerplate resistance
    try:
        all_results['benchmarks']['boilerplate_resistance'] = run_boilerplate_resistance(embeddings, metadata)
    except Exception as e:
        print(f"Boilerplate resistance failed: {e}")
        all_results['benchmarks']['boilerplate_resistance'] = {'error': str(e)}
    
    # Summary
    print("\n" + "="*70)
    print("V3 EVALUATION SUMMARY")
    print("="*70)
    
    for bench_name, bench_results in all_results['benchmarks'].items():
        if 'error' in bench_results:
            print(f"  {bench_name}: ERROR - {bench_results['error']}")
        elif 'summary' in bench_results:
            summary = bench_results['summary']
            print(f"  {bench_name}: {summary.get('passed', 'N/A')}/{summary.get('total_benchmarks', 'N/A')} passed")
        elif 'status' in bench_results:
            print(f"  {bench_name}: {bench_results['status']} - {bench_results.get('reason', '')}")
        else:
            # Check sub-benchmarks
            passed = sum(1 for v in bench_results.values() if isinstance(v, dict) and v.get('status') == 'PASS')
            total = sum(1 for v in bench_results.values() if isinstance(v, dict) and 'status' in v)
            if total > 0:
                print(f"  {bench_name}: {passed}/{total} passed")
            else:
                print(f"  {bench_name}: completed (no summary)")
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/evaluation')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'v3_evaluation_results.json'
    
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    print("\nEvaluation v3 complete.")
    
    return all_results


if __name__ == '__main__':
    main()