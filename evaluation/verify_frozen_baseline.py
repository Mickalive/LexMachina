#!/usr/bin/env python3
"""
Quick verification of the frozen TF-IDF 174k baseline.
Runs only the adversarial benchmarks (exact k-NN on 2000-stratified subsample).
"""

import json
import numpy as np
import logging
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize

# Add paths for frozen harness
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')

from evaluation_v3_harness import (
    GLOBAL_SEED,
    LANGUAGE_DOMINANCE_THRESHOLD,
    JURIST_PAIRWISE_THRESHOLD,
    K_NEIGHBORS_LANG_DOM,
    K_NEIGHBORS_JURIST,
    CHAMBER_TO_BRANCH,
    assign_branch,
    prepare_metadata,
    adversarial_language_dominance,
    simulate_pairwise_preference,
    get_config_hash,
    set_global_seed,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# PATHS - 174k TF-IDF embeddings and metadata
# ============================================================
LEX_ACCEPTED_ROOT = Path("/tmp/lex_accepted")

METADATA_174K_PATH = LEX_ACCEPTED_ROOT / "legal-distance/evaluation/data/174k/metadata_174k.json"

TFIDF_EMBEDDINGS_DIR = LEX_ACCEPTED_ROOT / "fractal-map/results/fractal_map/hierarchical_map_174k/tfidf_embeddings"
LEGAL_TFIDF_EMBEDDINGS_DIR = LEX_ACCEPTED_ROOT / "fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings"

TFIDF_REPRESENTATIONS = {
    'regeste_tfidf': TFIDF_EMBEDDINGS_DIR / "regeste_tfidf.npy",
    'full_text_tfidf_light': TFIDF_EMBEDDINGS_DIR / "full_text_tfidf_light.npy",
    'regeste_full_text_hybrid_0.5': TFIDF_EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.5.npy",
    'regeste_full_text_hybrid_0.7': TFIDF_EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.7.npy",
    'cited_decisions_tfidf': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.5': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.7': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    'outcome_tfidf': LEGAL_TFIDF_EMBEDDINGS_DIR / "outcome_tfidf.npy",
}

SUBSAMPLE_SIZE = 2000
SUBSAMPLE_SEED = 42

def create_stratified_subsample(metadata: List[Dict], size: int = SUBSAMPLE_SIZE, seed: int = SUBSAMPLE_SEED) -> List[int]:
    """Create stratified subsample by branch x language.
    
    FIXED: Groups are now sorted by (branch, language) key to ensure deterministic
    subsampling regardless of metadata JSON ordering. This fixes the non-determinism
    introduced when control plane mount updated metadata_174k.json at 2026-10-08T23:40.
    """
    np.random.seed(seed)
    
    groups = defaultdict(list)
    for i, m in enumerate(metadata):
        branch = m.get('branch', 'unknown')
        lang = m.get('language', 'unknown')
        if branch != 'unknown':
            groups[(branch, lang)].append(i)
    
    total_valid = sum(len(v) for v in groups.values())
    indices = []
    # FIX: Sort groups by (branch, language) key for deterministic iteration order
    for key in sorted(groups.keys()):
        group_indices = groups[key]
        n_sample = max(1, int(len(group_indices) * size / total_valid))
        n_sample = min(n_sample, len(group_indices))
        sampled = np.random.choice(group_indices, n_sample, replace=False)
        indices.extend(sampled.tolist())
    
    if len(indices) > size:
        indices = np.random.choice(indices, size, replace=False).tolist()
    elif len(indices) < size:
        all_valid = [i for i, m in enumerate(metadata) if m.get('branch', 'unknown') != 'unknown']
        remaining = [i for i in all_valid if i not in indices]
        additional = np.random.choice(remaining, min(size - len(indices), len(remaining)), replace=False)
        indices.extend(additional.tolist())
    
    return indices[:size]

def run_adversarial_verification(embeddings: np.ndarray, metadata: List[Dict], subsample_idx: List[int]) -> Dict[str, Any]:
    """Run exact k-NN adversarial benchmarks on subsample."""
    sub_embeddings = embeddings[subsample_idx]
    sub_metadata = [metadata[i] for i in subsample_idx]
    
    # Language dominance
    lang_dom_result = adversarial_language_dominance(sub_embeddings, sub_metadata)
    
    # Jurist pairwise preference - need branch and language arrays
    branches = np.array([m.get('branch', 'unknown') for m in sub_metadata])
    languages = np.array([m.get('language', 'unknown') for m in sub_metadata])
    jurist_result = simulate_pairwise_preference(sub_embeddings, branches, languages)
    
    both_pass = (lang_dom_result['status'] == 'PASS' and 
                 jurist_result['status'] == 'PASS')
    
    verdict = 'PASS' if both_pass else 'FAIL'
    
    return {
        'adversarial_language_dominance': lang_dom_result,
        'jurist_pairwise_preference': jurist_result,
        'both_pass': both_pass,
        'language_dominance_score': lang_dom_result['mean_language_dominance'],
        'jurist_preference_rate': jurist_result['jurist_would_succeed_rate'],
        'verdict': verdict
    }

def main():
    set_global_seed(GLOBAL_SEED)
    config_hash = get_config_hash()
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Subsample size: {SUBSAMPLE_SIZE}")
    
    # Load metadata
    logger.info("Loading 174k metadata...")
    with open(METADATA_174K_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Create stratified subsample
    logger.info("Creating stratified subsample...")
    subsample_idx = create_stratified_subsample(metadata)
    logger.info(f"Subsample size: {len(subsample_idx)}")
    
    # Verify all embedding files exist
    logger.info("Verifying embedding files...")
    missing = []
    for name, path in TFIDF_REPRESENTATIONS.items():
        if not path.exists():
            missing.append((name, path))
            logger.error(f"  MISSING: {name} at {path}")
        else:
            logger.info(f"  OK: {name}")
    
    if missing:
        logger.error(f"Missing {len(missing)} embedding files.")
        return
    
    # Evaluate each representation
    logger.info("\nRunning adversarial verification on all 8 representations...")
    all_results = {}
    
    for name, path in TFIDF_REPRESENTATIONS.items():
        logger.info(f"  Loading {name}...")
        embeddings = np.load(path)
        
        # Trim to metadata length
        if len(embeddings) > len(metadata):
            embeddings = embeddings[:len(metadata)]
        
        logger.info(f"  Loaded {name}: {embeddings.shape}")
        
        result = run_adversarial_verification(embeddings, metadata, subsample_idx)
        all_results[name] = result
        
        adv = result
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        logger.info(f"  {name}: verdict={adv['verdict']}, "
                   f"lang_dom={ld:.4f} ({ld_pass}), "
                   f"jurist_pref={jp:.4f} ({jp_pass}), "
                   f"both={both}")
    
    # Summary
    logger.info("\n" + "=" * 90)
    logger.info("FROZEN BASELINE VERIFICATION - ADVERSARIAL GATES")
    logger.info("=" * 90)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED} | Subsample: {SUBSAMPLE_SIZE}")
    logger.info("-" * 90)
    logger.info(f"{'Representation':<45} {'Verdict':<7} {'LangDom':>7} {'LD-Pass':>7} {'Jurist':>7} {'JP-Pass':>7} {'Both':>5}")
    logger.info("-" * 90)
    
    def sort_key(item):
        name, res = item
        both = res.get('both_pass', False)
        jurist = res.get('jurist_preference_rate', 0)
        lang_dom = res.get('language_dominance_score', 1.0)
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    passed_count = 0
    for name, res in sorted_results:
        ld = res['language_dominance_score']
        jp = res['jurist_preference_rate']
        ld_pass = "✓" if res['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if res['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if res['both_pass'] else "✗"
        
        if both == "✓":
            passed_count += 1
        
        logger.info(f"{name:<45} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>7} {jp:>7.4f} {jp_pass:>7} {both:>5}")
    
    logger.info("-" * 90)
    logger.info(f"Passed both adversarial gates: {passed_count}/{len(TFIDF_REPRESENTATIONS)}")
    logger.info("=" * 90)
    
    # Save results
    OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_tfidf_formal_suite")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = OUTPUT_DIR / f"verification_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "verification_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    return all_results, config_hash

if __name__ == "__main__":
    main()
