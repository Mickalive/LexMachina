#!/usr/bin/env python3
"""
Evaluation v2 Alternative Representations Test

Tests the language_debiasing representations (PCA2, PCA3, center_projected)
from the product branch against v2 adversarial benchmarks:
- Cross-language transfer stability
- Jurist usability simulation
- Jurivoc descriptor integration
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
import sys
import importlib.util

# Load modules directly by file path to avoid package import issues
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

eval_dir = Path('/home/runner/work/LexMachina/LexMachina/evaluation')
tests_dir = eval_dir / 'tests'

cross_lang = load_module('cross_language_benchmarks', tests_dir / 'cross_language_benchmarks.py')
jurist_usability = load_module('jurist_usability', tests_dir / 'jurist_usability.py')
jurivoc_module = load_module('jurivoc_benchmarks', tests_dir / 'jurivoc_benchmarks.py')

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


def load_baseline_metadata() -> List[Dict]:
    """Load the baseline metadata with branch/language info."""
    metadata_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json')
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    return metadata[:1000]  # First 1000 decisions match embeddings


def load_language_debiasing_embeddings() -> Dict[str, np.ndarray]:
    """Load all language_debiasing embeddings."""
    base_path = Path('/tmp/lex_accepted/product/product/results/fractal_map/language_debiasing')
    embeddings = {}
    
    for name in ['embeddings_pca2.npy', 'embeddings_pca3.npy', 'embeddings_center_projected.npy']:
        path = base_path / name
        if path.exists():
            key = name.replace('embeddings_', '').replace('.npy', '')
            embeddings[key] = np.load(path)
            print(f"Loaded {key}: {embeddings[key].shape}")
    
    return embeddings


def load_citation_blended_embeddings() -> np.ndarray:
    """Load the debiased_citation_blended representation for comparison."""
    path = Path('/tmp/lex_accepted/product/product/results/fractal_map/citation_graph/embeddings_blended.npy')
    return np.load(path)


def load_baseline_embeddings() -> np.ndarray:
    """Load baseline TF-IDF embeddings."""
    path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy')
    return np.load(path)


def run_cross_language_on_embeddings(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Run cross-language benchmarks on given embeddings."""
    print(f"\n{'='*70}")
    print(f"Cross-language benchmarks: {name}")
    print(f"{'='*70}")
    
    # Use only first 1000 to match metadata
    emb = embeddings[:1000]
    meta = metadata[:1000]
    
    results = run_all_cross_language_benchmarks(emb, meta)
    results['representation'] = name
    return results


def run_jurist_usability_on_embeddings(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Run jurist usability benchmarks on given embeddings."""
    print(f"\n{'='*70}")
    print(f"Jurist usability benchmarks: {name}")
    print(f"{'='*70}")
    
    emb = embeddings[:1000]
    meta = metadata[:1000]
    
    branches, languages, chambers, valid_indices = prepare_metadata(meta)
    rep_valid = emb[valid_indices]
    
    print(f"Valid decisions: {len(valid_indices)}")
    print(f"Branch distribution: {Counter(branches)}")
    print(f"Language distribution: {Counter(languages)}")
    
    # Need cluster assignments for zoom task
    cluster_assignments_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json')
    
    results = run_all_jurist_usability_benchmarks(rep_valid, branches, languages, valid_indices)
    results['representation'] = name
    return results


def run_jurivoc_on_embeddings(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Run Jurivoc benchmarks on given embeddings."""
    print(f"\n{'='*70}")
    print(f"Jurivoc benchmarks: {name}")
    print(f"{'='*70}")
    
    emb = embeddings[:1000]
    meta = metadata[:1000]
    
    decision_ids = [m.get('decision_id', '') for m in meta]
    
    try:
        benchmarks = JurivocBenchmarks(emb, decision_ids)
        results = benchmarks.run_all()
        results['representation'] = name
        return results
    except Exception as e:
        print(f"Jurivoc benchmarks failed for {name}: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'representation': name}


def main():
    print("=" * 70)
    print("EVALUATION v2: TESTING ALTERNATIVE REPRESENTATIONS")
    print("=" * 70)
    
    # Load metadata
    print("Loading baseline metadata...")
    metadata = load_baseline_metadata()
    print(f"Loaded {len(metadata)} decisions metadata")
    
    # Load language_debiasing embeddings
    print("\nLoading language_debiasing embeddings...")
    lang_debias_embeddings = load_language_debiasing_embeddings()
    
    # Load citation_blended for comparison
    print("Loading citation_blended embeddings...")
    citation_blended = load_citation_blended_embeddings()
    print(f"citation_blended shape: {citation_blended.shape}")
    
    # Load baseline for comparison
    print("Loading baseline embeddings...")
    baseline = load_baseline_embeddings()
    print(f"baseline shape: {baseline.shape}")
    
    # Test representations
    representations = {
        'pca2': lang_debias_embeddings.get('pca2'),
        'pca3': lang_debias_embeddings.get('pca3'),
        'center_projected': lang_debias_embeddings.get('center_projected'),
        'citation_blended': citation_blended,
        'baseline': baseline,
    }
    
    all_results = {
        'cross_language': {},
        'jurist_usability': {},
        'jurivoc': {}
    }
    
    for name, emb in representations.items():
        if emb is None:
            print(f"\nSkipping {name} - not available")
            continue
            
        print(f"\n\n{'#'*70}")
        print(f"# TESTING REPRESENTATION: {name}")
        print(f"# Shape: {emb.shape}")
        print(f"{'#'*70}")
        
        # Cross-language benchmarks
        try:
            cl_results = run_cross_language_on_embeddings(emb, metadata, name)
            all_results['cross_language'][name] = cl_results
        except Exception as e:
            print(f"Cross-language benchmarks failed for {name}: {e}")
            all_results['cross_language'][name] = {'error': str(e)}
        
        # Jurist usability benchmarks
        try:
            ju_results = run_jurist_usability_on_embeddings(emb, metadata, name)
            all_results['jurist_usability'][name] = ju_results
        except Exception as e:
            print(f"Jurist usability benchmarks failed for {name}: {e}")
            all_results['jurist_usability'][name] = {'error': str(e)}
        
        # Jurivoc benchmarks (run separately via subprocess)
        try:
            jv_results = run_jurivoc_on_embeddings(emb, metadata, name)
            all_results['jurivoc'][name] = jv_results
        except Exception as e:
            print(f"Jurivoc benchmarks failed for {name}: {e}")
            all_results['jurivoc'][name] = {'error': str(e)}
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/evaluation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / 'v2_alternatives_results.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n\n{'='*70}")
    print(f"ALL RESULTS SAVED TO: {output_path}")
    print(f"{'='*70}")
    
    # Print summary
    print("\nSUMMARY:")
    for category, reps in all_results.items():
        print(f"\n{category}:")
        for name, results in reps.items():
            if 'error' in results:
                print(f"  {name}: ERROR - {results['error']}")
            elif 'summary' in results:
                print(f"  {name}: {results['summary']['passed']}/{results['summary']['total_benchmarks']} passed")
            elif 'subprocess_output' in results:
                print(f"  {name}: subprocess completed")
            else:
                print(f"  {name}: completed (see full output)")
    
    return all_results


if __name__ == '__main__':
    main()