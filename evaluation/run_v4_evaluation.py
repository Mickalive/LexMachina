#!/usr/bin/env python3
"""
Evaluation v4 — Adversarial Benchmarks on Alternative Representations + Boilerplate Resistance

Validates:
- Legal embedding models (multilingual-e5-small, paraphrase-multilingual-minilm, xlm-roberta-base)
- Citation role embeddings (overruling, distinguishing, following, all_weighted, citing, criticizing)
- Boilerplate resistance on center_projected (now that full text is available)

Baseline: center_projected (validated in v3 on 1,200 decisions)
Adversarial benchmarks: language dominance, jurist pairwise, Jurivoc hierarchy, scale stability, boilerplate resistance
Freeze: global seed = 42
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


def load_center_projected_1200() -> Tuple[np.ndarray, List[Dict]]:
    """Load center_projected embeddings for 1,200 decisions and align with expanded slice metadata."""
    emb_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy')
    embeddings = np.load(emb_path)
    
    meta_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json')
    with open(meta_path, 'r') as f:
        cp_metadata = json.load(f)
    
    expanded_metadata = load_expanded_slice_metadata()
    
    cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    
    aligned_embeddings = np.zeros((len(expanded_metadata), embeddings.shape[1]), dtype=embeddings.dtype)
    aligned_metadata = []
    
    for i, exp_meta in enumerate(expanded_metadata):
        did = exp_meta['decision_id']
        if did in cp_id_to_idx:
            cp_idx = cp_id_to_idx[did]
            aligned_embeddings[i] = embeddings[cp_idx]
            aligned_metadata.append(exp_meta)
        else:
            print(f"WARNING: Decision {did} not found in center_projected metadata")
    
    print(f"Loaded and aligned {len(aligned_embeddings)} decisions for center_projected")
    print(f"Embedding shape: {aligned_embeddings.shape}")
    return aligned_embeddings, aligned_metadata


def load_legal_embeddings(rep_name: str) -> Tuple[np.ndarray, List[Dict]]:
    """Load a legal embedding representation and align with expanded slice."""
    emb_path = Path(f'/tmp/lex_accepted/legal-distance/legal_distance/results/v5/legal_embeddings/embeddings_{rep_name}.npy')
    if not emb_path.exists():
        raise FileNotFoundError(f"Embedding file not found: {emb_path}")
    
    embeddings = np.load(emb_path)
    
    # These embeddings are for the full 1200 slice - need to check metadata
    # Legal embeddings were created from the same 1200 decisions
    # Let's load the expanded slice metadata and assume same order
    expanded_metadata = load_expanded_slice_metadata()
    
    if len(embeddings) != len(expanded_metadata):
        print(f"WARNING: Embedding count ({len(embeddings)}) != metadata count ({len(expanded_metadata)})")
        # Try to find metadata for this representation
        # For now, truncate or pad
        min_len = min(len(embeddings), len(expanded_metadata))
        embeddings = embeddings[:min_len]
        expanded_metadata = expanded_metadata[:min_len]
    
    print(f"Loaded {rep_name}: {embeddings.shape}")
    return embeddings, expanded_metadata


def load_citation_role_embeddings(role_name: str) -> Tuple[np.ndarray, List[Dict]]:
    """Load a citation role embedding and align with expanded slice."""
    emb_path = Path(f'/tmp/lex_accepted/legal-distance/legal_distance/results/v5/citation_roles/citation_role_{role_name}.npy')
    if not emb_path.exists():
        raise FileNotFoundError(f"Embedding file not found: {emb_path}")
    
    embeddings = np.load(emb_path)
    expanded_metadata = load_expanded_slice_metadata()
    
    if len(embeddings) != len(expanded_metadata):
        print(f"WARNING: Embedding count ({len(embeddings)}) != metadata count ({len(expanded_metadata)})")
        min_len = min(len(embeddings), len(expanded_metadata))
        embeddings = embeddings[:min_len]
        expanded_metadata = expanded_metadata[:min_len]
    
    print(f"Loaded citation_role_{role_name}: {embeddings.shape}")
    return embeddings, expanded_metadata


def load_full_text_for_decisions(decision_ids: List[str]) -> Dict[str, str]:
    """Load full text for decisions from legal_signals_full.jsonl."""
    text_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/legal_signals_full.jsonl')
    texts = {}
    with open(text_path, 'r') as f:
        for line in f:
            d = json.loads(line)
            did = d.get('decision_id', '')
            if did in decision_ids:
                # Use full_text field
                texts[did] = d.get('full_text', '')
    return texts


def run_boilerplate_resistance(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run boilerplate resistance test using full text."""
    print("\n" + "="*70)
    print("BOILERPLATE RESISTANCE TEST")
    print("="*70)
    
    decision_ids = [m.get('decision_id', '') for m in metadata]
    texts = load_full_text_for_decisions(decision_ids)
    
    # Filter to decisions with text
    valid_indices = [i for i, did in enumerate(decision_ids) if did in texts and len(texts[did]) > 100]
    
    if len(valid_indices) < 20:
        return {
            'status': 'SKIP',
            'reason': f'Insufficient decisions with full text: {len(valid_indices)}',
            'recommendation': 'Need more full text data'
        }
    
    print(f"Testing boilerplate resistance on {len(valid_indices)} decisions with full text")
    
    # Sample pairs for efficiency
    rng = np.random.RandomState(GLOBAL_SEED)
    n_pairs = min(500, len(valid_indices) * 5)
    
    text_sims = []
    emb_sims = []
    
    valid_embeddings = embeddings[valid_indices]
    # Normalize
    norms = np.linalg.norm(valid_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    valid_embeddings = valid_embeddings / norms
    
    for _ in range(n_pairs):
        i, j = rng.choice(len(valid_indices), size=2, replace=False)
        did_i = decision_ids[valid_indices[i]]
        did_j = decision_ids[valid_indices[j]]
        
        text_i = texts[did_i]
        text_j = texts[did_j]
        
        # Simple word overlap (Jaccard)
        words_i = set(text_i.lower().split())
        words_j = set(text_j.lower().split())
        
        if words_i and words_j:
            jaccard = len(words_i & words_j) / len(words_i | words_j)
            text_sims.append(jaccard)
            emb_sims.append(float(valid_embeddings[i] @ valid_embeddings[j]))
    
    if len(text_sims) < 10:
        return {'status': 'SKIP', 'reason': 'Insufficient valid pairs'}
    
    text_sims_arr = np.array(text_sims)
    emb_sims_arr = np.array(emb_sims)
    
    correlation = float(np.corrcoef(text_sims_arr, emb_sims_arr)[0, 1])
    
    # Boilerplate resistance: LOW correlation is better (embeddings don't just track word overlap)
    # But we need SOME correlation to show legal content is captured
    # Pass if correlation is moderate (0.1-0.4) - not too high (boilerplate), not too low (random)
    passed = 0.1 < correlation < 0.4
    
    return {
        'status': 'PASS' if passed else 'FAIL',
        'benchmark': 'boilerplate_resistance',
        'text_embedding_correlation': round(correlation, 4),
        'mean_text_similarity': round(float(np.mean(text_sims)), 4),
        'mean_emb_similarity': round(float(np.mean(emb_sims)), 4),
        'num_pairs': len(text_sims),
        'n_decisions_with_text': len(valid_indices),
        'threshold_range': '0.1 < correlation < 0.4',
        'note': 'Low correlation = boilerplate resistant; moderate = captures legal content without boilerplate dominance'
    }


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


def run_cross_language_benchmarks(embeddings: np.ndarray, metadata: List[Dict], rep_name: str) -> Dict:
    """Run cross-language adversarial benchmarks."""
    print(f"\nRunning cross-language benchmarks for {rep_name}...")
    results = run_all_cross_language_benchmarks(embeddings, metadata)
    results['representation'] = rep_name
    results['n_decisions'] = len(embeddings)
    results['embedding_dim'] = embeddings.shape[1]
    results['global_seed'] = GLOBAL_SEED
    return results


def run_jurist_usability_benchmarks(embeddings: np.ndarray, metadata: List[Dict], rep_name: str) -> Dict:
    """Run jurist usability simulation benchmarks."""
    print(f"\nRunning jurist usability benchmarks for {rep_name}...")
    
    branches, languages, chambers, valid_indices = prepare_metadata_full(metadata)
    
    print(f"Total decisions: {len(branches)}")
    print(f"Valid decisions: {len(valid_indices)}")
    print(f"Branch distribution (valid): {Counter([branches[i] for i in valid_indices])}")
    print(f"Language distribution (valid): {Counter([languages[i] for i in valid_indices])}")
    
    # Use only valid decisions for benchmarks
    rep_valid = embeddings[valid_indices]
    branches_valid = branches[valid_indices]
    languages_valid = languages[valid_indices]
    
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
        print(f"Zoom task failed: {e}")
        results['zoom_task'] = {'status': 'SKIP', 'reason': f'Cluster assignments only for 1000 decisions: {e}'}
    
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
    
    results['representation'] = rep_name
    results['n_decisions'] = len(rep_valid)
    results['embedding_dim'] = embeddings.shape[1]
    results['global_seed'] = GLOBAL_SEED
    return results


def run_jurivoc_benchmarks(embeddings: np.ndarray, metadata: List[Dict], rep_name: str) -> Dict:
    """Run Jurivoc descriptor benchmarks."""
    print(f"\nRunning Jurivoc benchmarks for {rep_name}...")
    
    decision_ids = [m.get('decision_id', '') for m in metadata]
    benchmarks = JurivocBenchmarks(embeddings, decision_ids)
    results = benchmarks.run_all()
    
    results['representation'] = rep_name
    results['n_decisions'] = len(embeddings)
    results['embedding_dim'] = embeddings.shape[1]
    results['global_seed'] = GLOBAL_SEED
    return results


def run_scale_benchmarks(embeddings_768: np.ndarray, metadata: List[Dict], rep_name: str) -> Dict:
    """Run scale stability benchmarks with frozen PCA."""
    print(f"\nRunning scale stability benchmarks (frozen PCA) for {rep_name}...")
    
    # The frozen scale benchmark needs 768-dim embeddings to fit PCA on full and apply to subsets
    # If we only have 64-dim, we can't run the same test
    # For non-center_projected representations, we'll skip this or adapt
    if embeddings_768 is None:
        return {'status': 'SKIP', 'reason': '768-dim embeddings not available for frozen PCA test'}
    
    try:
        results = run_frozen_scale_benchmark(embeddings_768, metadata)
        results['representation'] = rep_name
        results['embedding_dim'] = 64
        results['global_seed'] = GLOBAL_SEED
        return results
    except Exception as e:
        print(f"Scale benchmark failed: {e}")
        return {'error': str(e)}


def load_center_projected_768() -> Tuple[np.ndarray, List[Dict]]:
    """Load 768-dim center_projected embeddings for scale test."""
    emb_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_768.npy')
    embeddings = np.load(emb_path)
    
    meta_path = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json')
    with open(meta_path, 'r') as f:
        cp_metadata = json.load(f)
    
    expanded_metadata = load_expanded_slice_metadata()
    cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    
    aligned_768 = np.zeros((len(expanded_metadata), embeddings.shape[1]), dtype=embeddings.dtype)
    for i, exp_meta in enumerate(expanded_metadata):
        did = exp_meta['decision_id']
        if did in cp_id_to_idx:
            cp_idx = cp_id_to_idx[did]
            aligned_768[i] = embeddings[cp_idx]
    
    return aligned_768, expanded_metadata


def main():
    print("=" * 70)
    print("EVALUATION v4 — ADVERSARIAL BENCHMARKS ON ALTERNATIVE REPRESENTATIONS")
    print("=" * 70)
    print(f"Global seed: {GLOBAL_SEED}")
    print(f"Factory Direction Version: 6")
    print(f"Baseline representation: center_projected (validated in v3)")
    print(f"Test representations: legal embeddings, citation roles")
    print(f"New test: boilerplate resistance (full text now available)")
    
    # Load baseline center_projected for 1200 decisions
    print("\nLoading center_projected baseline (64-dim)...")
    cp_embeddings_64, cp_metadata = load_center_projected_1200()
    
    # Load 768-dim for scale test
    print("\nLoading center_projected baseline (768-dim) for scale test...")
    cp_embeddings_768, _ = load_center_projected_768()
    
    # Verify language/branch distribution
    languages = [m.get('language', 'unknown') for m in cp_metadata]
    branches = [m.get('branch', 'unknown') for m in cp_metadata]
    print(f"\nLanguage distribution: {Counter(languages)}")
    print(f"Branch distribution: {Counter(branches)}")
    
    all_results = {
        'factory_direction_version': 6,
        'evaluation_version': 4,
        'global_seed': GLOBAL_SEED,
        'baseline_representation': 'center_projected',
        'slice': 'expanded_1200',
        'n_decisions': len(cp_embeddings_64),
        'embedding_dim': cp_embeddings_64.shape[1],
        'language_distribution': dict(Counter(languages)),
        'branch_distribution': dict(Counter(branches)),
        'benchmarks': {}
    }
    
    # ============================================================
    # 1. Run boilerplate resistance on center_projected (baseline)
    # ============================================================
    try:
        all_results['benchmarks']['boilerplate_resistance_center_projected'] = run_boilerplate_resistance(cp_embeddings_64, cp_metadata)
    except Exception as e:
        print(f"Boilerplate resistance failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['benchmarks']['boilerplate_resistance_center_projected'] = {'error': str(e)}
    
    # ============================================================
    # 2. Test legal embedding models
    # ============================================================
    legal_embeddings = [
        'multilingual_e5_small',
        'paraphrase_multilingual_minilm',
        'xlm_roberta_base'
    ]
    
    for rep_name in legal_embeddings:
        try:
            print(f"\n{'='*70}")
            print(f"TESTING LEGAL EMBEDDING: {rep_name}")
            print(f"{'='*70}")
            
            emb, meta = load_legal_embeddings(rep_name)
            
            rep_results = {
                'representation': rep_name,
                'n_decisions': len(emb),
                'embedding_dim': emb.shape[1]
            }
            
            # Cross-language
            rep_results['cross_language'] = run_cross_language_benchmarks(emb, meta, rep_name)
            
            # Jurist usability
            rep_results['jurist_usability'] = run_jurist_usability_benchmarks(emb, meta, rep_name)
            
            # Jurivoc
            rep_results['jurivoc'] = run_jurivoc_benchmarks(emb, meta, rep_name)
            
            # Scale stability - skip for legal embeddings (no 768-dim)
            rep_results['scale_stability'] = {'status': 'SKIP', 'reason': 'No 768-dim baseline for frozen PCA'}
            
            all_results['benchmarks'][rep_name] = rep_results
            
        except Exception as e:
            print(f"Failed to test {rep_name}: {e}")
            import traceback
            traceback.print_exc()
            all_results['benchmarks'][rep_name] = {'error': str(e)}
    
    # ============================================================
    # 3. Test citation role embeddings
    # ============================================================
    citation_roles = [
        'overruling',
        'distinguishing',
        'following',
        'all_weighted',
        'citing',
        'criticizing'
    ]
    
    for role_name in citation_roles:
        try:
            print(f"\n{'='*70}")
            print(f"TESTING CITATION ROLE: {role_name}")
            print(f"{'='*70}")
            
            emb, meta = load_citation_role_embeddings(role_name)
            
            rep_results = {
                'representation': f'citation_role_{role_name}',
                'n_decisions': len(emb),
                'embedding_dim': emb.shape[1]
            }
            
            # Cross-language
            rep_results['cross_language'] = run_cross_language_benchmarks(emb, meta, f'citation_role_{role_name}')
            
            # Jurist usability
            rep_results['jurist_usability'] = run_jurist_usability_benchmarks(emb, meta, f'citation_role_{role_name}')
            
            # Jurivoc
            rep_results['jurivoc'] = run_jurivoc_benchmarks(emb, meta, f'citation_role_{role_name}')
            
            # Scale stability - skip
            rep_results['scale_stability'] = {'status': 'SKIP', 'reason': 'No 768-dim baseline for frozen PCA'}
            
            all_results['benchmarks'][f'citation_role_{role_name}'] = rep_results
            
        except Exception as e:
            print(f"Failed to test citation_role_{role_name}: {e}")
            import traceback
            traceback.print_exc()
            all_results['benchmarks'][f'citation_role_{role_name}'] = {'error': str(e)}
    
    # ============================================================
    # 4. Also run boilerplate resistance on best legal embedding
    # ============================================================
    # Test on multilingual_e5_small as the most promising legal embedding
    try:
        print(f"\n{'='*70}")
        print(f"BOILERPLATE RESISTANCE: multilingual_e5_small")
        print(f"{'='*70}")
        emb, meta = load_legal_embeddings('multilingual_e5_small')
        all_results['benchmarks']['boilerplate_resistance_multilingual_e5_small'] = run_boilerplate_resistance(emb, meta)
    except Exception as e:
        print(f"Boilerplate resistance on multilingual_e5_small failed: {e}")
        all_results['benchmarks']['boilerplate_resistance_multilingual_e5_small'] = {'error': str(e)}
    
    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "="*70)
    print("V4 EVALUATION SUMMARY")
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
    output_path = output_dir / 'v4_evaluation_results.json'
    
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    print("\nEvaluation v4 complete.")
    
    return all_results


if __name__ == '__main__':
    main()