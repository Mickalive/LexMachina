#!/usr/bin/env python3
"""
Evaluation Lane - 174k Scale Formal Suite (HNSW Artifact Fixed)
Runs the formal benchmark suite at 174k scale on all production representations.
Uses frozen harness v3 thresholds and adversarial benchmarks.

CRITICAL FIX: HNSW artifact confirmed - exact k-NN used for adversarial benchmarks
on valid subset (n≈1200 with known branch); HNSW only for full-corpus scale
benchmarks (citation_heritage, temporal_stability, hierarchy family on subsamples).
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
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

# Add evaluation to path for package imports
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

from evaluation.tests.cross_language_benchmarks import (
    cross_language_neighbor_quality,
    zero_shot_cross_language_transfer,
    language_specific_representation_quality,
    adversarial_language_dominance,
)
from evaluation.tests.jurist_usability import (
    simulate_pairwise_preference,
    simulate_cluster_coherence_rating,
    simulate_zoom_task,
    simulate_cross_language_retrieval,
)
from evaluation.tests.boilerplate_resistance import BoilerplateResistanceTest, BoilerplateConfig
from evaluation.tests.citation_graph_neighborhood import CitationGraphNeighborhoodBenchmark
from evaluation.tests.citation_proximity import CitationProximityBenchmark
from evaluation.tests.hierarchy_coherence import HierarchyCoherenceTest
from evaluation.tests.jurivoc_benchmarks import load_debiased_citation_blended, load_representation
from evaluation.tests.legal_area_clustering import LegalAreaClusteringBenchmark
from evaluation.tests.multilingual_invariance import MultilingualInvarianceTest
from evaluation.tests.neighbor_relevance import NeighborRelevanceTest
from evaluation.tests.scale_benchmarks import position_drift, neighbor_preservation, cluster_stability
from evaluation.tests.stability import CorpusStabilityTest
from evaluation.tests.zoom_coherence import ZoomCoherenceBenchmark

# Use scalable NN infrastructure for full-corpus benchmarks
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
from scalable_nn import (
    ScalableNearestNeighbors,
    build_scalable_nn,
    batched_adversarial_language_dominance,
    batched_jurist_pairwise_preference,
    batched_scale_stability,
    batched_boilerplate_resistance,
    batched_jurivoc_alignment,
    batched_cluster_coherence,
    batched_cross_language_retrieval,
    K_NEIGHBORS_LANG_DOM,
    K_NEIGHBORS_JURIST,
    K_NEIGHBORS_CROSS_LANG,
    EXACT_NN_THRESHOLD,
)

N_CLUSTERS_COHERENCE = 16  # Frozen parameter

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION (from evaluation_v3_harness.py)
# ============================================================
EVALUATION_VERSION = "v3_174k_fixed"
GLOBAL_SEED = 42
FACTORY_DIRECTION_VERSION = 27

# Adversarial thresholds (FROZEN - do not modify)
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
CROSS_LANG_RECALL_THRESHOLD = 0.2
CLUSTER_COHERENCE_THRESHOLD = 0.7

# Benchmark parameters (FROZEN)
K_NEIGHBORS_LANG_DOM_FROZEN = 20
K_NEIGHBORS_JURIST_FROZEN = 10
K_NEIGHBORS_CROSS_LANG_FROZEN = 10
N_CLUSTERS_COHERENCE = 16  # Frozen parameter

# Scale adaptation parameters (FROZEN from protocol_v25_174k_suite.json)
TEMPORAL_STABILITY_SUBSAMPLE = 30000
HIERARCHY_FAMILY_SUBSAMPLE = 15000
ADVERSARIAL_SUBSAMPLE = 2000  # Fixed stratified subsample for exact k-NN adversarial benchmarks
BOILERPLATE_PAIRS = 200

EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/formal_suite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Representations to evaluate (production representations - TF-IDF family)
REPRESENTATIONS = {
    'cited_decisions_tfidf': 'cited_decisions_tfidf.npy',
    'outcome_tfidf': 'outcome_tfidf.npy',
    'regeste_tfidf': 'regeste_tfidf.npy',
    'full_text_tfidf_light': 'full_text_tfidf_light.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.5': 'cited_decisions_tfidf_outcome_hybrid_0.5.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.7': 'cited_decisions_tfidf_outcome_hybrid_0.7.npy',
    'regeste_full_text_hybrid_0.5': 'regeste_full_text_hybrid_0.5.npy',
    'regeste_full_text_hybrid_0.7': 'regeste_full_text_hybrid_0.7.npy',
}

METADATA_PATH = EMBEDDINGS_DIR / "metadata.json"


def set_global_seed(seed: int = GLOBAL_SEED):
    np.random.seed(seed)


def get_config_hash() -> str:
    """Generate hash of frozen configuration for audit trail."""
    import hashlib
    config = {
        "version": EVALUATION_VERSION,
        "seed": GLOBAL_SEED,
        "factory_direction": FACTORY_DIRECTION_VERSION,
        "thresholds": {
            "language_dominance": LANGUAGE_DOMINANCE_THRESHOLD,
            "jurist_pairwise": JURIST_PAIRWISE_THRESHOLD,
            "cross_lang_recall": CROSS_LANG_RECALL_THRESHOLD,
            "cluster_coherence": CLUSTER_COHERENCE_THRESHOLD
        },
        "parameters": {
            "k_lang_dom": K_NEIGHBORS_LANG_DOM_FROZEN,
            "k_jurist": K_NEIGHBORS_JURIST_FROZEN,
            "k_cross_lang": K_NEIGHBORS_CROSS_LANG_FROZEN,
            "n_clusters": N_CLUSTERS_COHERENCE,
            "temporal_stability_subsample": TEMPORAL_STABILITY_SUBSAMPLE,
            "hierarchy_family_subsample": HIERARCHY_FAMILY_SUBSAMPLE,
        },
        "representations": list(REPRESENTATIONS.keys()),
        "hnsw_artifact_fix": "exact_knn_on_valid_subset_for_adversarial"
    }
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


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


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int], np.ndarray]:
    """
    Extract branch, language, chamber from metadata.
    Returns: branches, languages, chambers, valid_indices, valid_mask
    """
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    valid_mask = np.zeros(len(metadata), dtype=bool)
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber if chamber else "")
            valid_indices.append(i)
            valid_mask[i] = True
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices, valid_mask


def load_evaluation_metadata() -> List[Dict]:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Metadata not found at {METADATA_PATH}")
    
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    
    # Ensure branch is assigned (should already be done in metadata)
    for meta in metadata:
        if 'branch' not in meta or meta['branch'] in ('null', None, ''):
            meta['branch'] = assign_branch(meta.get('chamber'))
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    return metadata


def load_embedding(name: str) -> np.ndarray:
    path = EMBEDDINGS_DIR / REPRESENTATIONS[name]
    if not path.exists():
        raise FileNotFoundError(f"Embedding not found: {path}")
    emb = np.load(path, mmap_mode='r')
    logger.info(f"Loaded {name}: {emb.shape}")
    return emb


def get_valid_subset(embeddings: np.ndarray, metadata: List[Dict]) -> Tuple[np.ndarray, List[Dict], np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """
    Get the valid subset (decisions with known branch) for exact k-NN adversarial benchmarks.
    Returns: rep_valid, meta_valid, branches, languages, valid_mask, valid_indices
    """
    branches, languages, chambers, valid_indices, valid_mask = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    return rep_valid, meta_valid, branches, languages, valid_mask, valid_indices


def get_adversarial_subsample(embeddings: np.ndarray, metadata: List[Dict]) -> Tuple[np.ndarray, List[Dict], np.ndarray, np.ndarray]:
    """
    Get a FIXED STRATIFIED SUBSAMPLE of valid decisions for EXACT k-NN adversarial benchmarks.
    This fixes the HNSW artifact by avoiding HNSW on full corpus for adversarial benchmarks.
    
    Uses stratified sampling by branch (seed=42) to ensure representative subsample.
    Returns: rep_sub, meta_sub, branches_sub, languages_sub
    """
    rep_valid, meta_valid, branches, languages, _, _ = get_valid_subset(embeddings, metadata)
    
    n_valid = len(rep_valid)
    if n_valid <= ADVERSARIAL_SUBSAMPLE:
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
    return rep_sub, meta_sub, branches_sub, languages_sub


def run_adversarial_benchmarks_exact(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """
    Run adversarial benchmarks using EXACT k-NN on FIXED STRATIFIED SUBSAMPLE of valid decisions.
    This fixes the HNSW artifact where HNSW on full 174k masked representation differences.
    """
    logger.info("  Running adversarial benchmarks with EXACT k-NN on fixed stratified subsample...")
    
    rep_sub, meta_sub, branches, languages = get_adversarial_subsample(embeddings, metadata)
    
    # 1. Adversarial language dominance - EXACT k-NN
    logger.info("  Running adversarial language dominance (exact k-NN)...")
    lang_dom = adversarial_language_dominance(rep_sub, meta_sub)
    
    # 2. Jurist pairwise preference - EXACT k-NN
    logger.info("  Running jurist pairwise preference (exact k-NN)...")
    jurist_pref = simulate_pairwise_preference(rep_sub, branches, languages)
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
        'backend': 'sklearn_exact',
        'subset_size': len(rep_sub),
        'note': 'EXACT k-NN on fixed stratified subsample (HNSW artifact fix)'
    }


def run_cross_language_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run cross-language benchmarks on adversarial subsample with exact k-NN."""
    logger.info("  Running cross-language benchmarks on adversarial subsample (exact k-NN)...")
    
    rep_sub, meta_sub, branches, languages = get_adversarial_subsample(embeddings, metadata)
    
    results = {}
    
    # 3. Cross-language neighbor quality
    logger.info("  Running cross-language neighbor quality...")
    results['cross_language_neighbor_quality'] = cross_language_neighbor_quality(rep_sub, meta_sub)
    
    # 4. Zero-shot cross-language transfer
    logger.info("  Running zero-shot cross-language transfer...")
    results['zero_shot_cross_language_transfer'] = zero_shot_cross_language_transfer(rep_sub, meta_sub)
    
    # 5. Language-specific representation quality
    logger.info("  Running language-specific representation quality...")
    results['language_specific_representation_quality'] = language_specific_representation_quality(rep_sub, meta_sub)
    
    return results


def run_jurist_usability_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run jurist usability benchmarks on adversarial subsample with exact k-NN."""
    logger.info("  Running jurist usability benchmarks on adversarial subsample (exact k-NN)...")
    
    rep_sub, meta_sub, branches, languages = get_adversarial_subsample(embeddings, metadata)
    
    results = {}
    
    # 6. Cluster coherence rating
    logger.info("  Running cluster coherence rating...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(rep_sub, branches, languages)
    
    # 7. Zoom task (requires hierarchical clusters - skip for now)
    logger.info("  Running zoom task...")
    results['zoom_task'] = {'status': 'SKIP', 'note': 'Requires hierarchical cluster assignments'}
    
    # 8. Cross-language retrieval
    logger.info("  Running cross-language retrieval...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(rep_sub, branches, languages)
    
    return results


def run_full_corpus_benchmarks_hnsw(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """
    Run full-corpus scale benchmarks using HNSW (scalable NN).
    These benchmarks work on subsamples or the full corpus where HNSW is appropriate.
    """
    logger.info("  Running full-corpus scale benchmarks with HNSW...")
    
    # Get branch/language for ALL decisions (including unknown) for full-corpus indexing
    branches_all = np.array([assign_branch(m.get("chamber")) for m in metadata])
    languages_all = np.array([m.get("language", "unknown") for m in metadata])
    valid_mask_full = branches_all != "unknown"
    valid_indices_all = np.where(valid_mask_full)[0]
    
    # Build HNSW index on full corpus (will use HNSW since n > 10000)
    nn_full = build_scalable_nn(embeddings, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG), force_exact=False)
    logger.info(f"  Built {nn_full.backend} index for {embeddings.shape[0]} decisions")
    
    results = {}
    
    # 9. Citation heritage - uses frozen pair pool, needs full corpus NN
    # Note: citation_heritage is run separately via validate_citation_heritage_174k.py
    results['citation_heritage'] = {'status': 'RUN_SEPARATELY', 'note': 'Run via validate_citation_heritage_174k.py on frozen 137k pair pool'}
    
    # 10. Scale stability (temporal) - on 30k subsample with HNSW
    logger.info("  Running scale stability (temporal) on 30k subsample...")
    np.random.seed(GLOBAL_SEED)
    n = embeddings.shape[0]
    temporal_indices = np.random.choice(n, min(TEMPORAL_STABILITY_SUBSAMPLE, n), replace=False)
    temporal_emb = embeddings[temporal_indices]
    temporal_meta = [metadata[i] for i in temporal_indices]
    results['temporal_stability'] = batched_scale_stability(temporal_emb, temporal_meta)
    results['temporal_stability']['backend'] = 'hnsw'
    results['temporal_stability']['subsample_size'] = len(temporal_indices)
    
    # 11. Hierarchy family benchmarks - on 15k subsample stratified by branch
    logger.info("  Running hierarchy family benchmarks on 15k subsample...")
    # Stratified sampling by branch from valid decisions
    if len(valid_indices_all) > HIERARCHY_FAMILY_SUBSAMPLE:
        # Stratify by branch
        branch_labels = branches_all[valid_indices_all]
        unique_branches = np.unique(branch_labels)
        stratified_indices = []
        per_branch = HIERARCHY_FAMILY_SUBSAMPLE // len(unique_branches)
        for branch in unique_branches:
            branch_mask = branch_labels == branch
            branch_indices = valid_indices_all[branch_mask]
            if len(branch_indices) > per_branch:
                np.random.seed(GLOBAL_SEED + hash(branch) % 1000)
                selected = np.random.choice(branch_indices, per_branch, replace=False)
            else:
                selected = branch_indices
            stratified_indices.extend(selected)
        hierarchy_indices = np.array(stratified_indices[:HIERARCHY_FAMILY_SUBSAMPLE])
    else:
        hierarchy_indices = valid_indices_all
    
    hierarchy_emb = embeddings[hierarchy_indices]
    hierarchy_meta = [metadata[i] for i in hierarchy_indices]
    hierarchy_branches = branches_all[hierarchy_indices]
    hierarchy_languages = languages_all[hierarchy_indices]
    
    # Build HNSW for hierarchy subsample
    nn_hierarchy = build_scalable_nn(hierarchy_emb, n_neighbors=max(K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST), force_exact=False)
    
    # Hierarchy coherence
    results['hierarchy_coherence'] = batched_jurivoc_alignment(hierarchy_emb, hierarchy_meta)
    results['hierarchy_coherence']['backend'] = nn_hierarchy.backend
    results['hierarchy_coherence']['subsample_size'] = len(hierarchy_indices)
    
    # Cluster coherence
    results['cluster_coherence'] = batched_cluster_coherence(hierarchy_emb, hierarchy_branches, hierarchy_languages)
    results['cluster_coherence']['backend'] = nn_hierarchy.backend
    
    # Cross-language retrieval
    results['cross_language_retrieval_full'] = batched_cross_language_retrieval(nn_hierarchy, hierarchy_meta, hierarchy_branches, hierarchy_languages)
    results['cross_language_retrieval_full']['backend'] = nn_hierarchy.backend
    
    # 12. Boilerplate resistance - on full corpus (HNSW)
    logger.info("  Running boilerplate resistance on full corpus (HNSW)...")
    results['boilerplate_resistance'] = batched_boilerplate_resistance(nn_full, metadata)
    results['boilerplate_resistance']['backend'] = nn_full.backend
    
    return results


def evaluate_representation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Evaluate a single representation against all benchmarks with HNSW artifact fix."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Ensure metadata and embeddings align
    n_meta = len(metadata)
    if embeddings.shape[0] != n_meta:
        logger.warning(f"Shape mismatch: embeddings {embeddings.shape[0]} vs metadata {n_meta}")
        if embeddings.shape[0] > n_meta:
            embeddings = embeddings[:n_meta]
        else:
            return {'error': 'embedding/metadata length mismatch', 'verdict': 'ERROR'}
    
    # Adversarial benchmarks - EXACT k-NN on valid subset (HNSW ARTIFACT FIX)
    logger.info("Running adversarial benchmarks (EXACT k-NN on valid subset)...")
    adv_results = run_adversarial_benchmarks_exact(embeddings, metadata)
    
    # Cross-language benchmarks - EXACT k-NN on valid subset
    logger.info("Running cross-language benchmarks (EXACT k-NN on valid subset)...")
    cross_lang_results = run_cross_language_benchmarks(embeddings, metadata)
    
    # Jurist usability benchmarks - EXACT k-NN on valid subset
    logger.info("Running jurist usability benchmarks (EXACT k-NN on valid subset)...")
    jurist_results = run_jurist_usability_benchmarks(embeddings, metadata)
    
    # Full-corpus scale benchmarks - HNSW on subsamples
    logger.info("Running full-corpus scale benchmarks (HNSW on subsamples)...")
    full_corpus_results = run_full_corpus_benchmarks_hnsw(embeddings, metadata)
    
    duration = time.time() - start_time
    
    # Overall verdict: MUST pass BOTH adversarial gates
    both_adv_pass = adv_results['both_pass']
    verdict = "PASS" if both_adv_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'cross_language': cross_lang_results,
        'jurist_usability': jurist_results,
        'full_corpus': full_corpus_results,
        'verdict': verdict,
        'both_adversarial_pass': both_adv_pass,
    }


def main():
    set_global_seed(GLOBAL_SEED)
    
    config_hash = get_config_hash()
    
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane - 174k Formal Suite ({EVALUATION_VERSION})")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("HNSW ARTIFACT FIX: exact k-NN on valid subset for adversarial benchmarks")
    logger.info("=" * 70)
    
    # Load metadata
    logger.info("\n1. Loading evaluation metadata...")
    try:
        metadata = load_evaluation_metadata()
        logger.info(f"Loaded metadata for {len(metadata)} decisions")
    except FileNotFoundError as e:
        logger.error(str(e))
        return
    
    # Verify all embedding files exist
    logger.info("\n2. Verifying embedding files...")
    missing = []
    for name, fname in REPRESENTATIONS.items():
        path = EMBEDDINGS_DIR / fname
        if not path.exists():
            missing.append((name, path))
    
    if missing:
        logger.error(f"Missing embedding files: {missing}")
        return
    
    logger.info("All embedding files present.")
    
    # Load and evaluate each representation
    logger.info("\n3. Loading representations and running evaluations...")
    all_results = {}
    
    for name in REPRESENTATIONS.keys():
        try:
            embeddings = load_embedding(name)
            result = evaluate_representation(name, embeddings, metadata)
            all_results[name] = result
            
            # Log summary
            if 'error' in result:
                logger.error(f"  {name}: ERROR - {result['error']}")
            else:
                adv = result['adversarial']
                logger.info(f"  {name}: verdict={result['verdict']}, "
                           f"lang_dom={adv['language_dominance_score']:.4f} "
                           f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                           f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                           f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
                           f"backend={adv.get('backend', 'N/A')}, subset={adv.get('subset_size', 'N/A')}")
        
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {
                'name': name,
                'error': str(e),
                'verdict': 'ERROR'
            }
    
    # Save all results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"evaluation_174k_formal_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Also save latest symlink
    latest_file = OUTPUT_DIR / "evaluation_174k_formal_suite_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("EVALUATION 174k FORMAL SUITE - SUMMARY (HNSW ARTIFACT FIXED)")
    logger.info("=" * 100)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED} | Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("-" * 100)
    
    # Print adversarial results table
    logger.info(f"\n{'Representation':<45} {'Verdict':<7} {'LangDom':>7} {'LD-P':>4} {'Jurist':>7} {'JP-P':>4} {'Both':>4} {'Backend':>10}")
    logger.info("-" * 95)
    
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res['both_adversarial_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<45} {'ERROR':<7} {'N/A':>7} {'N/A':>4} {'N/A':>7} {'N/A':>4} {'N/A':>4} {'N/A':>10}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        backend = adv.get('backend', 'N/A')
        
        logger.info(f"{name:<45} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>4} {jp:>7.4f} {jp_pass:>4} {both:>4} {backend:>10}")
    
    # Find best representation (must pass both adversarial gates)
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Backend: {best[1]['adversarial'].get('backend', 'N/A')}")
        logger.info(f"   Valid subset size: {best[1]['adversarial'].get('subset_size', 'N/A')}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    # Reference baseline (production default)
    prod_default = 'cited_decisions_tfidf_outcome_hybrid_0.5'
    if prod_default in all_results and 'error' not in all_results[prod_default]:
        ref = all_results[prod_default]
        logger.info(f"\n📏 PRODUCTION DEFAULT ({prod_default}):")
        logger.info(f"   Language dominance: {ref['adversarial']['language_dominance_score']:.4f} ({ref['adversarial']['adversarial_language_dominance']['status']})")
        logger.info(f"   Jurist preference: {ref['adversarial']['jurist_preference_rate']:.4f} ({ref['adversarial']['jurist_pairwise_preference']['status']})")
        logger.info(f"   Both adversarial pass: {ref['both_adversarial_pass']}")
        logger.info(f"   Backend: {ref['adversarial'].get('backend', 'N/A')}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return all_results, config_hash


if __name__ == "__main__":
    main()