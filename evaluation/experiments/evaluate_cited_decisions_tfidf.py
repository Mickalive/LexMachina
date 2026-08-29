#!/usr/bin/env python3
"""
Evaluation Lane - Evaluate cited_decisions_tfidf against frozen v3 harness

This is a new candidate representation from legal-distance hybrids_adversarial_test
that passed both adversarial gates (LangDom=0.6086, JP=0.6889) with meaningful
hierarchical structure. Needs validation against the full v3 benchmark suite.

Factory Direction v6: Evaluation lane must validate new representations on expanded
slice (1,200 decisions) using adversarial benchmarks.
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans
import sys

# Frozen v3 harness imports
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
from evaluation_v3_harness import (
    GLOBAL_SEED, EVALUATION_VERSION, FACTORY_DIRECTION_VERSION,
    LANGUAGE_DOMINANCE_THRESHOLD, JURIST_PAIRWISE_THRESHOLD,
    CROSS_LANG_RECALL_THRESHOLD, CLUSTER_COHERENCE_THRESHOLD,
    K_NEIGHBORS_LANG_DOM, K_NEIGHBORS_JURIST, K_NEIGHBORS_CROSS_LANG,
    N_CLUSTERS_COHERENCE, CHAMBER_TO_BRANCH, assign_branch,
    load_evaluation_metadata, prepare_metadata,
    adversarial_language_dominance, simulate_pairwise_preference,
    simulate_cluster_coherence_rating, simulate_cross_language_retrieval,
    compute_jurivoc_alignment, compute_scale_stability,
    compute_boilerplate_resistance, run_fractal_quality_benchmarks,
    get_config_hash
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
SIGNALS_FILE = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/legal_signals_full.jsonl")
CENTER_PROJECTED_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v3_cited_decisions")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CITED_DECISIONS_EMBEDDINGS_PATH = OUTPUT_DIR / "cited_decisions_tfidf_1200.npy"

def load_signals() -> Dict[str, Any]:
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")
    return signals

def load_center_projected_metadata() -> List[Dict]:
    metadata_path = CENTER_PROJECTED_DIR / 'metadata.json'
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    logger.info(f"Loaded center_projected metadata: {len(metadata)} decisions")
    return metadata

def build_cited_decisions_tfidf(signals: Dict[str, Any], metadata: List[Dict]) -> Tuple[np.ndarray, List[int]]:
    """Build TF-IDF embeddings from cited decisions."""
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        cited = sig.get('cited_decisions', [])
        if cited:
            texts.append(" ".join(cited))
            valid_indices.append(i)
        else:
            texts.append("")
    
    valid_texts = [texts[i] for i in valid_indices]
    logger.info(f"cited_decisions_tfidf: {len(valid_indices)} valid decisions with citations")
    
    if len(valid_indices) < 100:
        logger.warning(f"Only {len(valid_indices)} valid texts for TF-IDF")
        return np.zeros((len(metadata), 128)), valid_indices
    
    vectorizer = TfidfVectorizer(
        max_features=5000,
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
    )
    
    tfidf_matrix = vectorizer.fit_transform(valid_texts)
    
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=GLOBAL_SEED)
    reduced = svd.fit_transform(tfidf_matrix)
    
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    logger.info(f"cited_decisions_tfidf embeddings: {len(valid_indices)} valid, {n_comp} dims")
    return full_emb, valid_indices

def run_full_v3_evaluation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run the complete frozen v3 evaluation suite on a representation."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating {name} against frozen v3 harness")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Adversarial benchmarks
    logger.info("Running adversarial benchmarks...")
    adv_results = {
        'adversarial_language_dominance': adversarial_language_dominance(embeddings, metadata),
        'jurist_pairwise_preference': None,  # Will fill after prepare_metadata
    }
    
    # Prepare metadata for pairwise preference
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    adv_results['jurist_pairwise_preference'] = simulate_pairwise_preference(rep_valid, branches, languages)
    adv_results['both_pass'] = (adv_results['adversarial_language_dominance']['status'] == 'PASS' and 
                                 adv_results['jurist_pairwise_preference']['status'] == 'PASS')
    adv_results['language_dominance_score'] = adv_results['adversarial_language_dominance']['mean_language_dominance']
    adv_results['jurist_preference_rate'] = adv_results['jurist_pairwise_preference']['jurist_would_succeed_rate']
    
    # Jurivoc hierarchy alignment
    logger.info("Running Jurivoc hierarchy alignment...")
    jurivoc_results = compute_jurivoc_alignment(embeddings, metadata)
    
    # Scale stability
    logger.info("Running scale stability...")
    scale_results = compute_scale_stability(embeddings, metadata)
    
    # Boilerplate resistance
    logger.info("Running boilerplate resistance...")
    boilerplate_results = compute_boilerplate_resistance(embeddings, metadata)
    
    # Fractal quality benchmarks
    logger.info("Running fractal quality benchmarks...")
    fractal_results = run_fractal_quality_benchmarks(embeddings, metadata)
    
    duration = time.time() - start_time
    
    both_adv_pass = adv_results['both_pass']
    verdict = "PASS" if both_adv_pass else "FAIL"
    
    result = {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'jurivoc_alignment': jurivoc_results,
        'scale_stability': scale_results,
        'boilerplate_resistance': boilerplate_results,
        'fractal': fractal_results,
        'verdict': verdict,
        'both_adversarial_pass': both_adv_pass,
    }
    
    return result

def main():
    np.random.seed(GLOBAL_SEED)
    
    config_hash = get_config_hash()
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane - cited_decisions_tfidf Validation")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Factory direction: v{FACTORY_DIRECTION_VERSION}")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\n1. Loading legal signals and metadata...")
    signals = load_signals()
    metadata = load_center_projected_metadata()
    
    # Build cited_decisions_tfidf embeddings
    logger.info("\n2. Building cited_decisions_tfidf embeddings...")
    embeddings, valid_indices = build_cited_decisions_tfidf(signals, metadata)
    
    # Save embeddings
    np.save(CITED_DECISIONS_EMBEDDINGS_PATH, embeddings)
    logger.info(f"Saved embeddings to {CITED_DECISIONS_EMBEDDINGS_PATH}")
    
    # Run full v3 evaluation
    logger.info("\n3. Running full v3 evaluation suite...")
    result = run_full_v3_evaluation("cited_decisions_tfidf", embeddings, metadata)
    
    # Save results
    output_file = OUTPUT_DIR / "cited_decisions_tfidf_v3_evaluation.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    # Load baseline for comparison
    baseline_file = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v3/evaluation_v3_results.json")
    baseline_results = {}
    if baseline_file.exists():
        with open(baseline_file, 'r') as f:
            baseline_results = json.load(f)
    
    # Print summary
    logger.info("\n" + "=" * 90)
    logger.info("CITED_DECISIONS_TFIDF - FROZEN V3 HARNESS EVALUATION SUMMARY")
    logger.info("=" * 90)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED}")
    logger.info("-" * 90)
    
    adv = result['adversarial']
    jurivoc = result['jurivoc_alignment']
    scale = result['scale_stability']
    boiler = result['boilerplate_resistance']
    frac = result['fractal']
    
    ld = adv['language_dominance_score']
    jp = adv['jurist_preference_rate']
    ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
    jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
    both = "✓" if adv['both_pass'] else "✗"
    
    scale_score = scale.get('mean_neighbor_overlap', 0)
    boiler_score = boiler['resistance_score']
    imp_rate = frac.get('improvement_rate', 0)
    
    logger.info(f"{'Representation':<30} {'Verdict':<7} {'LangDom':>7} {'LD-P':>5} {'Jurist':>7} {'JP-P':>5} {'Both':>5} {'Jurivoc0':>8} {'Scale':>6} {'Boiler':>7} {'ImpRate':>7}")
    logger.info("-" * 90)
    logger.info(f"{'cited_decisions_tfidf':<30} {result['verdict']:<7} {ld:>7.4f} {ld_pass:>5} {jp:>7.4f} {jp_pass:>5} {both:>5} "
               f"{jurivoc['level_0_nmi']:>8.4f} {scale_score:>6.4f} {boiler_score:>7.4f} {imp_rate:>6.1%}")
    
    # Compare with baseline if available
    if 'center_projected_64dim' in baseline_results:
        ref = baseline_results['center_projected_64dim']
        logger.info(f"\n📏 DELTA vs center_projected_64dim (production baseline):")
        logger.info(f"   Language dominance: {ld - ref['adversarial']['language_dominance_score']:+.4f}")
        logger.info(f"   Jurist preference: {jp - ref['adversarial']['jurist_preference_rate']:+.4f}")
        logger.info(f"   Jurivoc L0 NMI: {jurivoc['level_0_nmi'] - ref['jurivoc_alignment']['level_0_nmi']:+.4f}")
        logger.info(f"   Cross-language retrieval: {frac['cross_language_retrieval']['mean_cross_language_recall_at_k'] - ref['fractal']['cross_language_retrieval']['mean_cross_language_recall_at_k']:+.4f}")
        logger.info(f"   Fractal improvement rate: {imp_rate - ref['fractal']['improvement_rate']:+.1%}")
    
    # Compare with best breakthrough (linear_metric_epoch4)
    if 'linear_metric_epoch4' in baseline_results:
        best = baseline_results['linear_metric_epoch4']
        logger.info(f"\n📏 DELTA vs linear_metric_epoch4 (best breakthrough):")
        logger.info(f"   Language dominance: {ld - best['adversarial']['language_dominance_score']:+.4f}")
        logger.info(f"   Jurist preference: {jp - best['adversarial']['jurist_preference_rate']:+.4f}")
        logger.info(f"   Jurivoc L0 NMI: {jurivoc['level_0_nmi'] - best['jurivoc_alignment']['level_0_nmi']:+.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return result, config_hash

if __name__ == "__main__":
    main()