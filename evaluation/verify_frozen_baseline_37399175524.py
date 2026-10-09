#!/usr/bin/env python3
"""
Frozen TF-IDF 174k Baseline Verification for GitHub Run 37399175524

Runs the frozen adversarial harness (exact k-NN on stratified subsample n=2000, seed=42)
on the 8 TF-IDF production representations using working directory embeddings.

This verifies the production baseline is still operational and documents
the current metric values for this GitHub run.
"""

import json
import numpy as np
import logging
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from sklearn.neighbors import NearestNeighbors

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION (matches evaluation_v3_harness.py)
# ============================================================
GLOBAL_SEED = 42
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
K_NEIGHBORS_LANG_DOM = 20
K_NEIGHBORS_JURIST = 10
SUBSAMPLE_SIZE = 2000
SUBSAMPLE_SEED = 42

# Paths - WORKING DIRECTORY embeddings and metadata
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/formal_suite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 8 Production TF-IDF representations
TFIDF_REPRESENTATIONS = {
    'regeste_tfidf': EMBEDDINGS_DIR / "regeste_tfidf.npy",
    'full_text_tfidf_light': EMBEDDINGS_DIR / "full_text_tfidf_light.npy",
    'regeste_full_text_hybrid_0.5': EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.5.npy",
    'regeste_full_text_hybrid_0.7': EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.7.npy",
    'cited_decisions_tfidf': EMBEDDINGS_DIR / "cited_decisions_tfidf.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.5': EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.7': EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    'outcome_tfidf': EMBEDDINGS_DIR / "outcome_tfidf.npy",
}

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
    if not chamber:
        return "unknown"
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

def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata."""
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices

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

def adversarial_language_dominance(embeddings: np.ndarray, metadata: List[Dict], k: int = K_NEIGHBORS_LANG_DOM) -> Dict:
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    dominance_rates = []
    for i, m in enumerate(metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / k)
    
    mean_dominance = np.mean(dominance_rates)
    
    return {
        'mean_language_dominance': float(mean_dominance),
        'std_language_dominance': float(np.std(dominance_rates)),
        'max_language_dominance': float(np.max(dominance_rates)),
        'k': k,
        'threshold': LANGUAGE_DOMINANCE_THRESHOLD,
        'status': 'PASS' if mean_dominance < LANGUAGE_DOMINANCE_THRESHOLD else 'FAIL',
        'note': 'Lower is better - language should not dominate neighbors'
    }

def simulate_pairwise_preference(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = K_NEIGHBORS_JURIST
) -> Dict:
    n = len(branches)
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        
        has_legal_relevant = False
        has_language_artifact = False
        
        for nb, nl in zip(neighbor_branches, neighbor_langs):
            if nb == branch_i and nl != lang_i:
                has_legal_relevant = True
            if nb != branch_i and nl == lang_i:
                has_language_artifact = True
        
        if has_legal_relevant and has_language_artifact:
            both_count += 1
        elif has_legal_relevant:
            legal_relevant_count += 1
        elif has_language_artifact:
            language_artifact_count += 1
        else:
            neither_count += 1
    
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    language_neighbor_rate = (language_artifact_count + both_count) / total
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    
    return {
        "status": "PASS" if legal_neighbor_rate > JURIST_PAIRWISE_THRESHOLD else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "legal_neighbor_rate": round(legal_neighbor_rate, 4),
        "language_neighbor_rate": round(language_neighbor_rate, 4),
        "jurist_would_succeed_rate": round(jurist_correct / total, 4),
        "jurist_forced_wrong_rate": round(jurist_forced_wrong / total, 4),
        "note": "Simulated jurist prefers legally-relevant neighbors. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k."
    }

def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # 1. Adversarial language dominance
    lang_dom = adversarial_language_dominance(rep_valid, meta_valid)
    
    # 2. Jurist pairwise preference
    jurist_pref = simulate_pairwise_preference(rep_valid, branches, languages)
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }

def get_config_hash() -> str:
    """Generate hash of frozen configuration for audit trail."""
    config = {
        "version": "frozen_adversarial_v3",
        "seed": GLOBAL_SEED,
        "factory_direction": 34,
        "thresholds": {
            "language_dominance": LANGUAGE_DOMINANCE_THRESHOLD,
            "jurist_pairwise": JURIST_PAIRWISE_THRESHOLD
        },
        "parameters": {
            "k_lang_dom": K_NEIGHBORS_LANG_DOM,
            "k_jurist": K_NEIGHBORS_JURIST,
            "subsample_size": SUBSAMPLE_SIZE,
            "subsample_seed": SUBSAMPLE_SEED
        },
        "embedding_file_hashes": {}
    }
    
    # Include embedding file hashes for data integrity
    for name, path in TFIDF_REPRESENTATIONS.items():
        if path.exists():
            try:
                with open(path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                config["embedding_file_hashes"][name] = file_hash
            except Exception:
                config["embedding_file_hashes"][name] = "unreadable"
        else:
            config["embedding_file_hashes"][name] = "missing"
    
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]

def main():
    np.random.seed(GLOBAL_SEED)
    
    config_hash = get_config_hash()
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    
    logger.info("=" * 70)
    logger.info(f"Frozen TF-IDF 174k Baseline Verification - GitHub Run 37399175524")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Subsample: {SUBSAMPLE_SIZE} (exact k-NN)")
    logger.info("=" * 70)
    
    # Load metadata
    logger.info("\n1. Loading 174k evaluation metadata...")
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Verify all embedding files exist
    logger.info("\n2. Verifying embedding files...")
    missing = []
    for name, path in TFIDF_REPRESENTATIONS.items():
        if not path.exists():
            missing.append((name, path))
            logger.error(f"  MISSING: {name} at {path}")
        else:
            logger.info(f"  OK: {name}")
    
    if missing:
        logger.error(f"Missing {len(missing)} embedding files. Cannot proceed.")
        return
    
    # Create stratified subsample (frozen, seed=42)
    logger.info("\n3. Creating stratified subsample (n=2000, seed=42)...")
    subsample_indices = create_stratified_subsample(metadata)
    logger.info(f"Created stratified subsample: {len(subsample_indices)} decisions")
    
    sub_metadata = [metadata[i] for i in subsample_indices]
    
    # Load and evaluate each representation
    logger.info("\n4. Running adversarial evaluations...")
    all_results = {}
    
    for name, path in TFIDF_REPRESENTATIONS.items():
        try:
            logger.info(f"  Loading {name}...")
            embeddings = np.load(path)
            
            # Slice to match metadata length
            if embeddings.shape[0] > len(metadata):
                embeddings = embeddings[:len(metadata)]
                logger.warning(f"  Trimmed embeddings from {embeddings.shape[0]} to {len(metadata)}")
            
            # Subsample
            sub_embeddings = embeddings[subsample_indices]
            
            # Run adversarial benchmarks
            adv_result = run_adversarial_benchmarks(sub_embeddings, sub_metadata)
            result = {
                'name': name,
                'embedding_shape': list(embeddings.shape),
                'subsample_size': len(subsample_indices),
                'adversarial': adv_result,
                'verdict': 'PASS' if adv_result['both_pass'] else 'FAIL',
                'both_adversarial_pass': adv_result['both_pass']
            }
            
            all_results[name] = result
            
            # Log summary
            ld = adv_result['language_dominance_score']
            jp = adv_result['jurist_preference_rate']
            ld_pass = "PASS" if adv_result['adversarial_language_dominance']['status'] == 'PASS' else "FAIL"
            jp_pass = "PASS" if adv_result['jurist_pairwise_preference']['status'] == 'PASS' else "FAIL"
            both = "PASS" if adv_result['both_pass'] else "FAIL"
            
            logger.info(f"  {name}: verdict={both}, lang_dom={ld:.4f} ({ld_pass}), jurist_pref={jp:.4f} ({jp_pass})")
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {
                'name': name,
                'error': str(e),
                'verdict': 'ERROR'
            }
    
    # Save results
    output_file = OUTPUT_DIR / f"evaluation_174k_adversarial_verification_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'run_id': f'verification_37399175524_{timestamp}',
            'github_run': 37399175524,
            'config_hash': config_hash,
            'global_seed': GLOBAL_SEED,
            'subsample_size': SUBSAMPLE_SIZE,
            'subsample_seed': SUBSAMPLE_SEED,
            'metadata_count': len(metadata),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'results': all_results
        }, f, indent=2, default=str)
    
    # Also update latest
    latest_file = OUTPUT_DIR / "evaluation_174k_adversarial_verification_latest.json"
    with open(latest_file, 'w') as f:
        json.dump({
            'run_id': f'verification_37399175524_{timestamp}',
            'github_run': 37399175524,
            'config_hash': config_hash,
            'global_seed': GLOBAL_SEED,
            'subsample_size': SUBSAMPLE_SIZE,
            'subsample_seed': SUBSAMPLE_SEED,
            'metadata_count': len(metadata),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'results': all_results
        }, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 90)
    logger.info("FROZEN TF-IDF 174k ADVERSARIAL VERIFICATION - GITHUB RUN 37399175524")
    logger.info("=" * 90)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED} | Subsample: {SUBSAMPLE_SIZE} (exact k-NN)")
    logger.info(f"Thresholds: LangDom < {LANGUAGE_DOMINANCE_THRESHOLD}, JuristPref > {JURIST_PAIRWISE_THRESHOLD}")
    logger.info("-" * 90)
    logger.info(f"{'Representation':<45} {'Verdict':<7} {'LangDom':>8} {'Jurist':>8} {'Both':>5}")
    logger.info("-" * 90)
    
    # Sort by both_pass, then jurist_pref, then -lang_dom
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res.get('adversarial', {}).get('both_pass', False)
        jurist = res.get('adversarial', {}).get('jurist_preference_rate', 0)
        lang_dom = res.get('adversarial', {}).get('language_dominance_score', 1.0)
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    passed_count = 0
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<45} {'ERROR':<7} {'N/A':>8} {'N/A':>8} {'N/A':>5}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        both = "PASS" if adv['both_pass'] else "FAIL"
        
        if both == "PASS":
            passed_count += 1
        
        logger.info(f"{name:<45} {both:<7} {ld:>8.4f} {jp:>8.4f} {both:>5}")
    
    logger.info("-" * 90)
    logger.info(f"Passed both adversarial gates: {passed_count}/{len(TFIDF_REPRESENTATIONS)}")
    
    # Production default
    prod = 'cited_decisions_tfidf_outcome_hybrid_0.5'
    if prod in all_results and 'error' not in all_results[prod]:
        r = all_results[prod]['adversarial']
        logger.info(f"\nProduction default ({prod}):")
        logger.info(f"  Language dominance: {r['language_dominance_score']:.4f} ({r['adversarial_language_dominance']['status']})")
        logger.info(f"  Jurist preference:  {r['jurist_preference_rate']:.4f} ({r['jurist_pairwise_preference']['status']})")
        logger.info(f"  Both gates PASS:    {r['both_pass']}")
    
    # Compare with frozen baseline (config hash b51701f5a9c11692)
    logger.info(f"\nFrozen baseline reference (config hash b51701f5a9c11692):")
    logger.info(f"  Production default JP: 0.7345, LangDom: 0.4773")
    logger.info(f"  All 8 representations PASS both gates")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return all_results, config_hash

if __name__ == "__main__":
    main()