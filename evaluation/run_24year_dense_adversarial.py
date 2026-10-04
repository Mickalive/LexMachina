#!/usr/bin/env python3
"""
Evaluation Lane - 24-Year Dense Embeddings Adversarial Evaluation
Runs adversarial benchmarks (language dominance, jurist pairwise preference) 
on 24-year (2000-2023, 158,427 decisions) center_projected dense embeddings.

Uses EXACT k-NN on fixed stratified subsample of valid decisions (HNSW artifact fix).
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
import hashlib

# Add evaluation to path for package imports
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

from evaluation.tests.jurist_usability import (
    simulate_pairwise_preference,
)
from evaluation.tests.cross_language_benchmarks import (
    adversarial_language_dominance,
)

N_CLUSTERS_COHERENCE = 16

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION
# ============================================================
EVALUATION_VERSION = "v34_24year_dense_adversarial"
GLOBAL_SEED = 42
FACTORY_DIRECTION_VERSION = 34

# Adversarial thresholds (FROZEN - do not modify)
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5

# Benchmark parameters (FROZEN)
K_NEIGHBORS_LANG_DOM_FROZEN = 20
K_NEIGHBORS_JURIST_FROZEN = 10
ADVERSARIAL_SUBSAMPLE = 2000  # Fixed stratified subsample for exact k-NN adversarial benchmarks

CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation/24year_dense_adversarial")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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


def assign_branch(chamber: Optional[str]) -> str:
    """Assign legal branch from chamber name. Handles None/empty gracefully."""
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


def set_global_seed(seed: int = GLOBAL_SEED):
    np.random.seed(seed)


def get_config_hash() -> str:
    """Generate hash of frozen configuration for audit trail."""
    config = {
        "version": EVALUATION_VERSION,
        "seed": GLOBAL_SEED,
        "factory_direction": FACTORY_DIRECTION_VERSION,
        "thresholds": {
            "language_dominance": LANGUAGE_DOMINANCE_THRESHOLD,
            "jurist_pairwise": JURIST_PAIRWISE_THRESHOLD,
        },
        "parameters": {
            "k_lang_dom": K_NEIGHBORS_LANG_DOM_FROZEN,
            "k_jurist": K_NEIGHBORS_JURIST_FROZEN,
            "n_clusters": N_CLUSTERS_COHERENCE,
            "adversarial_subsample": ADVERSARIAL_SUBSAMPLE,
        },
        "hnsw_artifact_fix": "exact_knn_on_valid_subset_for_adversarial"
    }
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def load_all_24year_data() -> Tuple[np.ndarray, List[Dict]]:
    """Load and combine all 24 years of embeddings and metadata."""
    logger.info("Loading 24-year dense embeddings (2000-2023)...")
    
    all_embeddings = []
    all_metadata = []
    
    for year in range(2000, 2024):
        emb_path = CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINTS_DIR / f"metadata_{year}.json"
        
        if not emb_path.exists() or not meta_path.exists():
            logger.warning(f"Missing files for {year}: emb={emb_path.exists()}, meta={meta_path.exists()}")
            continue
        
        emb = np.load(emb_path, mmap_mode='r')
        with open(meta_path) as f:
            meta = json.load(f)
        
        # Ensure metadata has branch assigned
        for m in meta:
            if 'branch' not in m or m['branch'] in ('null', None, ''):
                m['branch'] = assign_branch(m.get('chamber'))
            if 'language' not in m:
                m['language'] = m.get('language', 'de')
        
        all_embeddings.append(emb)
        all_metadata.extend(meta)
        logger.info(f"  Loaded {year}: {emb.shape[0]} decisions, shape={emb.shape}")
    
    combined_embeddings = np.vstack(all_embeddings)
    logger.info(f"Combined raw embeddings: {combined_embeddings.shape}")
    logger.info(f"Combined metadata: {len(all_metadata)} decisions")
    
    return combined_embeddings, all_metadata


def create_center_projected(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Create center_projected embeddings by subtracting language centers and L2 normalizing."""
    logger.info("Creating center_projected embeddings (subtract language centers)...")
    
    languages = sorted(set(m.get('language', 'unknown') for m in metadata))
    logger.info(f"Languages: {languages}")
    
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f"  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}")
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f"Center projected shape: {debiased.shape}")
    logger.info(f"Norm stats: min={np.linalg.norm(debiased, axis=1).min():.6f}, max={np.linalg.norm(debiased, axis=1).max():.6f}, mean={np.linalg.norm(debiased, axis=1).mean():.6f}")
    
    return debiased


def create_pca_projection(embeddings: np.ndarray, n_components: int) -> np.ndarray:
    """Create PCA projection of embeddings."""
    logger.info(f"Creating PCA {n_components}dim projection...")
    pca = PCA(n_components=n_components, random_state=42)
    projected = pca.fit_transform(embeddings)
    projected = normalize(projected, norm='l2', axis=1)
    logger.info(f"  Explained variance ratio ({n_components} components): {pca.explained_variance_ratio_.sum():.4f}")
    return projected


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, List[int], np.ndarray]:
    """Extract branch, language from metadata. Returns arrays and valid indices."""
    branches = []
    languages = []
    valid_indices = []
    valid_mask = np.zeros(len(metadata), dtype=bool)
    
    for i, meta in enumerate(metadata):
        branch = meta.get('branch', 'unknown')
        lang = meta.get('language', 'unknown')
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            valid_indices.append(i)
            valid_mask[i] = True
    
    return np.array(branches), np.array(languages), valid_indices, valid_mask


def get_adversarial_subsample(embeddings: np.ndarray, metadata: List[Dict]) -> Tuple[np.ndarray, List[Dict], np.ndarray, np.ndarray]:
    """
    Get a FIXED STRATIFIED SUBSAMPLE of valid decisions for EXACT k-NN adversarial benchmarks.
    Uses stratified sampling by branch (seed=42) to ensure representative subsample.
    """
    branches, languages, valid_indices, _ = prepare_metadata(metadata)
    
    if len(valid_indices) == 0:
        raise ValueError("No valid decisions with known branch found")
    
    # Get valid subset embeddings and metadata
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    n_valid = len(rep_valid)
    if n_valid <= ADVERSARIAL_SUBSAMPLE:
        logger.info(f"  Valid subset ({n_valid}) <= subsample size, using all")
        return rep_valid, meta_valid, branches, languages
    
    # Stratified sampling by branch
    np.random.seed(GLOBAL_SEED)
    unique_branches = np.unique(branches)
    per_branch = ADVERSARIAL_SUBSAMPLE // len(unique_branches)
    subsample_indices = []
    
    for branch in unique_branches:
        branch_mask = branches == branch
        branch_indices = np.where(branch_mask)[0]
        if len(branch_indices) > per_branch:
            selected = np.random.choice(branch_indices, per_branch, replace=False)
        else:
            selected = branch_indices
        subsample_indices.extend(selected)
    
    subsample_indices = np.array(subsample_indices[:ADVERSARIAL_SUBSAMPLE])
    np.random.shuffle(subsample_indices)
    
    rep_sub = rep_valid[subsample_indices]
    meta_sub = [meta_valid[i] for i in subsample_indices]
    branches_sub = branches[subsample_indices]
    languages_sub = languages[subsample_indices]
    
    logger.info(f"  Adversarial subsample: {len(rep_sub)} decisions (stratified by branch from {n_valid} valid)")
    logger.info(f"  Branch distribution: {Counter(branches_sub)}")
    logger.info(f"  Language distribution: {Counter(languages_sub)}")
    
    return rep_sub, meta_sub, branches_sub, languages_sub


def run_adversarial_evaluation(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict[str, Any]:
    """Run adversarial benchmarks using EXACT k-NN on FIXED STRATIFIED SUBSAMPLE."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Get adversarial subsample
    logger.info("Creating fixed stratified subsample for exact k-NN...")
    rep_sub, meta_sub, branches, languages = get_adversarial_subsample(embeddings, metadata)
    
    # 1. Adversarial language dominance - EXACT k-NN
    logger.info("Running adversarial language dominance (exact k-NN)...")
    lang_dom = adversarial_language_dominance(rep_sub, meta_sub)
    
    # 2. Jurist pairwise preference - EXACT k-NN
    logger.info("Running jurist pairwise preference (exact k-NN)...")
    jurist_pref = simulate_pairwise_preference(rep_sub, branches, languages)
    
    duration = time.time() - start_time
    
    both_pass = (lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS')
    verdict = "PASS" if both_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': {
            'adversarial_language_dominance': lang_dom,
            'jurist_pairwise_preference': jurist_pref,
            'both_pass': both_pass,
            'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
            'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
            'backend': 'sklearn_exact',
            'subset_size': len(rep_sub),
            'note': 'EXACT k-NN on fixed stratified subsample (HNSW artifact fix)'
        },
        'verdict': verdict,
        'both_adversarial_pass': both_pass,
    }


def main():
    set_global_seed(GLOBAL_SEED)
    
    config_hash = get_config_hash()
    
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane - 24-Year Dense Adversarial Evaluation ({EVALUATION_VERSION})")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("HNSW ARTIFACT FIX: exact k-NN on valid subset for adversarial benchmarks")
    logger.info("=" * 70)
    
    # Load all 24-year data (raw 768-dim embeddings)
    logger.info("\n1. Loading 24-year dense embeddings and metadata...")
    try:
        raw_embeddings, metadata = load_all_24year_data()
        logger.info(f"Loaded {raw_embeddings.shape[0]} decisions, {raw_embeddings.shape[1]} dimensions")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Create center_projected 768-dim
    logger.info("\n2. Creating center_projected 768-dim embeddings...")
    cp768 = create_center_projected(raw_embeddings, metadata)
    
    # Create center_projected 64-dim via PCA
    logger.info("\n3. Creating center_projected 64-dim via PCA...")
    cp64 = create_pca_projection(cp768, 64)
    
    # Create center_projected 128-dim via PCA
    logger.info("\n4. Creating center_projected 128-dim via PCA...")
    cp128 = create_pca_projection(cp768, 128)
    
    # Run evaluation on all three
    results = {}
    
    for name, emb in [
        ("center_projected_768dim_24year", cp768),
        ("center_projected_64dim_24year", cp64),
        ("center_projected_128dim_24year", cp128),
    ]:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running adversarial evaluation for {name}...")
        logger.info(f"{'='*60}")
        results[name] = run_adversarial_evaluation(emb, metadata, name)
    
    # Save combined results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"evaluation_24year_dense_adversarial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Also save latest symlink
    latest_file = OUTPUT_DIR / "evaluation_24year_dense_adversarial_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 90)
    logger.info("24-YEAR DENSE ADVERSARIAL EVALUATION - SUMMARY (ALL PROJECTIONS)")
    logger.info("=" * 90)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED}")
    logger.info("-" * 90)
    
    logger.info(f"\n{'Representation':<40} {'Verdict':<7} {'LangDom':>7} {'LD-P':>4} {'Jurist':>7} {'JP-P':>4} {'Both':>4} {'Subset':>6}")
    logger.info("-" * 85)
    
    for name, result in results.items():
        adv = result['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        logger.info(f"{name:<40} {result['verdict']:<7} {ld:>7.4f} {ld_pass:>4} {jp:>7.4f} {jp_pass:>4} {both:>4} {adv['subset_size']:>6}")
    
    # Detailed results for each
    for name, result in results.items():
        adv = result['adversarial']
        logger.info(f"\n📊 {name}:")
        logger.info(f"   Language Dominance: {adv['language_dominance_score']:.4f} (threshold: {LANGUAGE_DOMINANCE_THRESHOLD}, status: {adv['adversarial_language_dominance']['status']})")
        logger.info(f"   Jurist Preference:  {adv['jurist_preference_rate']:.4f} (threshold: {JURIST_PAIRWISE_THRESHOLD}, status: {adv['jurist_pairwise_preference']['status']})")
        logger.info(f"   Both Gates Pass:    {adv['both_pass']}")
        logger.info(f"   Subset Size:        {adv['subset_size']} decisions")
        logger.info(f"   Duration:           {result['duration_seconds']:.1f}s")
    
    # Compare with previous 22-year results
    logger.info(f"\n📈 COMPARISON WITH 22-YEAR RESULTS:")
    logger.info(f"   22-year center_projected_768dim:  LangDom=0.842, JP=0.3975 (FAIL)")
    logger.info(f"   22-year center_projected_128dim:  LangDom=0.838, JP=0.4080 (FAIL)")
    logger.info(f"   22-year center_projected_64dim:   LangDom=0.832, JP=0.4265 (FAIL)")
    logger.info(f"   24-year center_projected_768dim:  LangDom={results['center_projected_768dim_24year']['adversarial']['language_dominance_score']:.4f}, JP={results['center_projected_768dim_24year']['adversarial']['jurist_preference_rate']:.4f} ({results['center_projected_768dim_24year']['verdict']})")
    logger.info(f"   24-year center_projected_128dim:  LangDom={results['center_projected_128dim_24year']['adversarial']['language_dominance_score']:.4f}, JP={results['center_projected_128dim_24year']['adversarial']['jurist_preference_rate']:.4f} ({results['center_projected_128dim_24year']['verdict']})")
    logger.info(f"   24-year center_projected_64dim:   LangDom={results['center_projected_64dim_24year']['adversarial']['language_dominance_score']:.4f}, JP={results['center_projected_64dim_24year']['adversarial']['jurist_preference_rate']:.4f} ({results['center_projected_64dim_24year']['verdict']})")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return results, config_hash


if __name__ == "__main__":
    main()