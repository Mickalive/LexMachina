#!/usr/bin/env python3
"""
Evaluation Lane - 174k Scale Formal Suite
Runs the formal benchmark suite at 174k scale on all production representations.
Uses frozen harness v3 thresholds and adversarial benchmarks.
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FROZEN CONFIGURATION (from evaluation_v3_harness.py)
# ============================================================
EVALUATION_VERSION = "v3_174k"
GLOBAL_SEED = 42
FACTORY_DIRECTION_VERSION = 27

# Adversarial thresholds (FROZEN - do not modify)
LANGUAGE_DOMINANCE_THRESHOLD = 0.85
JURIST_PAIRWISE_THRESHOLD = 0.5
CROSS_LANG_RECALL_THRESHOLD = 0.2
CLUSTER_COHERENCE_THRESHOLD = 0.7

# Benchmark parameters (FROZEN)
K_NEIGHBORS_LANG_DOM = 20
K_NEIGHBORS_JURIST = 10
K_NEIGHBORS_CROSS_LANG = 10
N_CLUSTERS_COHERENCE = 16

EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/formal_suite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Representations to evaluate (production representations)
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
            "k_lang_dom": K_NEIGHBORS_LANG_DOM,
            "k_jurist": K_NEIGHBORS_JURIST,
            "k_cross_lang": K_NEIGHBORS_CROSS_LANG,
            "n_clusters": N_CLUSTERS_COHERENCE
        },
        "representations": list(REPRESENTATIONS.keys()),
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
    """Extract branch, language, chamber from metadata (from frozen harness v3)."""
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


def load_evaluation_metadata() -> List[Dict]:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Metadata not found at {METADATA_PATH}")
    
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    
    # Ensure branch is assigned (should already be done)
    for meta in metadata:
        if 'branch' not in meta or meta['branch'] in ('null', None, ''):
            meta['branch'] = assign_branch(meta.get('chamber', ''))
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


def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run the two critical adversarial benchmarks."""
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # 1. Adversarial language dominance
    logger.info("  Running adversarial language dominance...")
    lang_dom = adversarial_language_dominance(rep_valid, meta_valid)
    
    # 2. Jurist pairwise preference
    logger.info("  Running jurist pairwise preference...")
    jurist_pref = simulate_pairwise_preference(rep_valid, branches, languages)
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }


def run_cross_language_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run cross-language benchmarks."""
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    results = {}
    
    # 3. Cross-language neighbor quality
    logger.info("  Running cross-language neighbor quality...")
    results['cross_language_neighbor_quality'] = cross_language_neighbor_quality(rep_valid, meta_valid)
    
    # 4. Zero-shot cross-language transfer
    logger.info("  Running zero-shot cross-language transfer...")
    results['zero_shot_cross_language_transfer'] = zero_shot_cross_language_transfer(rep_valid, meta_valid)
    
    # 5. Language-specific representation quality
    logger.info("  Running language-specific representation quality...")
    results['language_specific_representation_quality'] = language_specific_representation_quality(rep_valid, meta_valid)
    
    return results


def run_jurist_usability_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run jurist usability benchmarks."""
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    results = {}
    
    # 6. Cluster coherence rating
    logger.info("  Running cluster coherence rating...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(rep_valid, branches, languages)
    
    # 7. Zoom task (requires hierarchical clusters - skip for now)
    logger.info("  Running zoom task...")
    results['zoom_task'] = {'status': 'SKIP', 'note': 'Requires hierarchical cluster assignments'}
    
    # 8. Cross-language retrieval
    logger.info("  Running cross-language retrieval...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(rep_valid, branches, languages)
    
    return results


def run_class_based_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run class-based benchmarks from test modules."""
    results = {}
    
    # 9. Boilerplate resistance
    logger.info("  Running boilerplate resistance...")
    try:
        config = BoilerplateConfig(
            boilerplate_threshold=0.1,
            min_decisions_per_area=10,
            sample_size=5000,  # Use sample for speed
            random_seed=GLOBAL_SEED
        )
        test = BoilerplateResistanceTest(config)
        # Create mock decisions with text content
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'language': m.get('language', 'de'),
                'legal_area': m.get('legal_area', 'unknown'),
                'chamber': m.get('chamber', ''),
                'text': '',  # We don't have full text in metadata
                'erwaegungen_text': '',
                'dispositiv_text': '',
            })
        result = test.run(decisions, embeddings)
        results['boilerplate_resistance'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Boilerplate resistance failed: {e}")
        import traceback
        traceback.print_exc()
        results['boilerplate_resistance'] = {'error': str(e)}
    
    # 10. Citation graph neighborhood
    logger.info("  Running citation graph neighborhood...")
    try:
        test = CitationGraphNeighborhoodBenchmark()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'cited_decisions': [],  # Not in metadata
            })
        result = test.run(decisions, embeddings)
        results['citation_graph_neighborhood'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Citation graph neighborhood failed: {e}")
        results['citation_graph_neighborhood'] = {'error': str(e)}
    
    # 11. Citation proximity
    logger.info("  Running citation proximity...")
    try:
        test = CitationProximityBenchmark()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'cited_decisions': [],
            })
        result = test.run(decisions, embeddings)
        results['citation_proximity'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Citation proximity failed: {e}")
        results['citation_proximity'] = {'error': str(e)}
    
    # 12. Hierarchy coherence
    logger.info("  Running hierarchy coherence...")
    try:
        test = HierarchyCoherenceTest()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'legal_area': m.get('legal_area', 'unknown'),
                'branch': m.get('branch', 'unknown'),
            })
        result = test.run(decisions, embeddings)
        results['hierarchy_coherence'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Hierarchy coherence failed: {e}")
        results['hierarchy_coherence'] = {'error': str(e)}
    
    # 13. Legal area clustering
    logger.info("  Running legal area clustering...")
    try:
        test = LegalAreaClusteringBenchmark()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'legal_area': m.get('legal_area', 'unknown'),
            })
        result = test.run(decisions, embeddings)
        results['legal_area_clustering'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Legal area clustering failed: {e}")
        results['legal_area_clustering'] = {'error': str(e)}
    
    # 14. Multilingual invariance
    logger.info("  Running multilingual invariance...")
    try:
        test = MultilingualInvarianceTest()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'language': m.get('language', 'de'),
                'legal_area': m.get('legal_area', 'unknown'),
            })
        result = test.run(decisions, embeddings)
        results['multilingual_invariance'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Multilingual invariance failed: {e}")
        results['multilingual_invariance'] = {'error': str(e)}
    
    # 15. Neighbor relevance
    logger.info("  Running neighbor relevance...")
    try:
        test = NeighborRelevanceTest()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'legal_area': m.get('legal_area', 'unknown'),
                'branch': m.get('branch', 'unknown'),
            })
        result = test.run(decisions, embeddings)
        results['neighbor_relevance'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Neighbor relevance failed: {e}")
        results['neighbor_relevance'] = {'error': str(e)}
    
    # 16. Scale benchmarks
    logger.info("  Running scale benchmarks...")
    try:
        # Scale benchmarks require comparing small vs large corpus
        # For now, use the full corpus and compare with a subsample
        n = embeddings.shape[0]
        sample_size = min(10000, n)
        indices = np.random.choice(n, sample_size, replace=False)
        small_emb = embeddings[indices]
        results['scale_benchmarks'] = {
            'position_drift': float(position_drift(small_emb, embeddings)),
            'neighbor_preservation': float(neighbor_preservation(small_emb, embeddings)),
            'cluster_stability': float(cluster_stability(small_emb, embeddings)),
        }
    except Exception as e:
        logger.warning(f"  Scale benchmarks failed: {e}")
        results['scale_benchmarks'] = {'error': str(e)}
    
    # 17. Stability test
    logger.info("  Running stability test...")
    try:
        test = CorpusStabilityTest()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'year': m.get('year', 'unknown'),
            })
        result = test.run(decisions, embeddings)
        results['stability'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Stability test failed: {e}")
        results['stability'] = {'error': str(e)}
    
    # 18. Zoom coherence test
    logger.info("  Running zoom coherence...")
    try:
        test = ZoomCoherenceBenchmark()
        decisions = []
        for m in metadata:
            decisions.append({
                'decision_id': m['decision_id'],
                'legal_area': m.get('legal_area', 'unknown'),
                'branch': m.get('branch', 'unknown'),
            })
        result = test.run(decisions, embeddings)
        results['zoom_coherence'] = {
            'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
            'metrics': result.metrics,
            'details': result.details
        }
    except Exception as e:
        logger.warning(f"  Zoom coherence failed: {e}")
        results['zoom_coherence'] = {'error': str(e)}
    
    return results


def evaluate_representation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Evaluate a single representation against all benchmarks."""
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
    
    # Adversarial benchmarks
    logger.info("Running adversarial benchmarks...")
    adv_results = run_adversarial_benchmarks(embeddings, metadata)
    
    # Cross-language benchmarks
    logger.info("Running cross-language benchmarks...")
    cross_lang_results = run_cross_language_benchmarks(embeddings, metadata)
    
    # Jurist usability benchmarks
    logger.info("Running jurist usability benchmarks...")
    jurist_results = run_jurist_usability_benchmarks(embeddings, metadata)
    
    # Class-based benchmarks
    logger.info("Running class-based benchmarks...")
    class_results = run_class_based_benchmarks(embeddings, metadata)
    
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
        'class_based': class_results,
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
                           f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'})")
        
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
    logger.info("EVALUATION 174k FORMAL SUITE - SUMMARY")
    logger.info("=" * 100)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED} | Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("-" * 100)
    
    # Print adversarial results table
    logger.info(f"\n{'Representation':<45} {'Verdict':<7} {'LangDom':>7} {'LD-P':>4} {'Jurist':>7} {'JP-P':>4} {'Both':>4}")
    logger.info("-" * 85)
    
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
            logger.info(f"{name:<45} {'ERROR':<7} {'N/A':>7} {'N/A':>4} {'N/A':>7} {'N/A':>4} {'N/A':>4}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        logger.info(f"{name:<45} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>4} {jp:>7.4f} {jp_pass:>4} {both:>4}")
    
    # Find best representation (must pass both adversarial gates)
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                          -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
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
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return all_results, config_hash


if __name__ == "__main__":
    main()