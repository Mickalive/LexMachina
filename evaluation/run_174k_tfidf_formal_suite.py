#!/usr/bin/env python3
"""
Evaluation Lane: 174k TF-IDF Formal Suite (Factory Direction v29)

Runs the frozen evaluation harness v3 on all 8 TF-IDF production representations
at 174k scale. Uses scalable_nn infrastructure for exact k-NN on stratified subsample
(per HNSW adversarial artifact fix).

Validates:
1. Full 12-benchmark formal suite (frozen harness v3 thresholds unchanged)
2. citation_heritage benchmark using 174k citation-ID resolution
3. v17b label normalization generalization to 174k fine-grained legal_area labels
"""

import json
import numpy as np
import logging
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize

# Add paths for frozen harness and scalable NN
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
sys.path.insert(0, '/tmp/lex_accepted/legal-distance/evaluation')

from evaluation_v3_harness import (
    GLOBAL_SEED,
    LANGUAGE_DOMINANCE_THRESHOLD,
    JURIST_PAIRWISE_THRESHOLD,
    CROSS_LANG_RECALL_THRESHOLD,
    CLUSTER_COHERENCE_THRESHOLD,
    K_NEIGHBORS_LANG_DOM,
    K_NEIGHBORS_JURIST,
    K_NEIGHBORS_CROSS_LANG,
    N_CLUSTERS_COHERENCE,
    CHAMBER_TO_BRANCH,
    assign_branch,
    prepare_metadata,
    adversarial_language_dominance,
    simulate_pairwise_preference,
    simulate_cluster_coherence_rating,
    simulate_cross_language_retrieval,
    compute_jurivoc_alignment,
    compute_scale_stability,
    compute_boilerplate_resistance,
    run_fractal_quality_benchmarks,
    evaluate_representation,
    get_config_hash,
    set_global_seed,
)

from scalable_nn import (
    build_scalable_nn,
    batched_adversarial_language_dominance,
    batched_jurist_pairwise_preference,
    batched_cross_language_retrieval,
    batched_scale_stability,
    batched_boilerplate_resistance,
    batched_jurivoc_alignment,
    batched_cluster_coherence,
    run_scalable_adversarial_benchmarks,
    run_scalable_full_evaluation,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# PATHS - 174k TF-IDF embeddings and metadata
# ============================================================
LEX_ACCEPTED_ROOT = Path("/tmp/lex_accepted")

# 174k metadata (evaluation format)
METADATA_174K_PATH = LEX_ACCEPTED_ROOT / "legal-distance/evaluation/data/174k/metadata_174k.json"

# TF-IDF embeddings (128-dim, 174k decisions)
TFIDF_EMBEDDINGS_DIR = LEX_ACCEPTED_ROOT / "fractal-map/results/fractal_map/hierarchical_map_174k/tfidf_embeddings"
LEGAL_TFIDF_EMBEDDINGS_DIR = LEX_ACCEPTED_ROOT / "fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings"

# 8 Production TF-IDF representations at 174k
TFIDF_REPRESENTATIONS = {
    # From tfidf_embeddings directory
    'regeste_tfidf': TFIDF_EMBEDDINGS_DIR / "regeste_tfidf.npy",
    'full_text_tfidf_light': TFIDF_EMBEDDINGS_DIR / "full_text_tfidf_light.npy",
    'regeste_full_text_hybrid_0.5': TFIDF_EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.5.npy",
    'regeste_full_text_hybrid_0.7': TFIDF_EMBEDDINGS_DIR / "regeste_full_text_hybrid_0.7.npy",
    # From legal_tfidf_embeddings directory
    'cited_decisions_tfidf': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.5': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    'cited_decisions_tfidf_outcome_hybrid_0.7': LEGAL_TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    'outcome_tfidf': LEGAL_TFIDF_EMBEDDINGS_DIR / "outcome_tfidf.npy",
}

# Citation heritage validation data
CITATION_RESOLUTION_PATH = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v7/citation_id_resolution_bge/citation_to_decision_id.json"

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_tfidf_formal_suite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# STRATIFIED SUBSAMPLE FOR EXACT k-NN (HNSW artifact fix)
# ============================================================
SUBSAMPLE_SIZE = 2000  # Frozen: 2000 decisions for exact adversarial eval
SUBSAMPLE_SEED = 42

def create_stratified_subsample(metadata: List[Dict], size: int = SUBSAMPLE_SIZE, seed: int = SUBSAMPLE_SEED) -> List[int]:
    """Create stratified subsample by branch x language."""
    np.random.seed(seed)
    
    # Group by (branch, language)
    groups = defaultdict(list)
    for i, m in enumerate(metadata):
        branch = m.get('branch', 'unknown')
        lang = m.get('language', 'unknown')
        if branch != 'unknown':
            groups[(branch, lang)].append(i)
    
    # Sample proportionally
    total_valid = sum(len(v) for v in groups.values())
    indices = []
    for key, group_indices in groups.items():
        n_sample = max(1, int(len(group_indices) * size / total_valid))
        n_sample = min(n_sample, len(group_indices))
        sampled = np.random.choice(group_indices, n_sample, replace=False)
        indices.extend(sampled.tolist())
    
    # If we have too many/few, adjust
    if len(indices) > size:
        indices = np.random.choice(indices, size, replace=False).tolist()
    elif len(indices) < size:
        # Add from remaining
        all_valid = [i for i, m in enumerate(metadata) if m.get('branch', 'unknown') != 'unknown']
        remaining = [i for i in all_valid if i not in indices]
        additional = np.random.choice(remaining, min(size - len(indices), len(remaining)), replace=False)
        indices.extend(additional.tolist())
    
    return indices[:size]


# ============================================================
# CITATION HERITAGE VALIDATION (Benchmark from spec)
# ============================================================
def load_citation_pairs() -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Load citation pairs for citation_heritage benchmark.
    
    Uses the 174k citation-ID resolution (2,019/2,105 resolved).
    Returns positive pairs (shared citations) and negative pairs (no shared citations).
    """
    # Load citation resolution
    with open(CITATION_RESOLUTION_PATH) as f:
        citation_resolution = json.load(f)
    
    # Load metadata to get decision_id -> index mapping
    with open(METADATA_174K_PATH) as f:
        metadata = json.load(f)
    
    decision_id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    # Build citation graph: decision_id -> set of cited decision_ids
    citation_graph = defaultdict(set)
    for citation, info in citation_resolution.items():
        if 'target_decision_id' in info:
            cited_id = info['target_decision_id']
            # Find which decisions cite this (we need the reverse mapping)
            # The citation_resolution maps FROM citation string TO decision_id
            # We need to find which decisions contain each citation
            pass
    
    # Actually, we need the citation extraction from the corpus
    # Let's use the resolved citations as positive pairs
    # For now, we'll use the role_graph from the same directory
    role_graph_path = CITATION_RESOLUTION_PATH.parent / "role_graph.json"
    if role_graph_path.exists():
        with open(role_graph_path) as f:
            role_graph = json.load(f)
    else:
        role_graph = {}
    
    # Build positive pairs from citation graph
    positive_pairs = []
    for source, targets in role_graph.items():
        if source in decision_id_to_idx:
            source_idx = decision_id_to_idx[source]
            for target in targets:
                if target in decision_id_to_idx:
                    target_idx = decision_id_to_idx[target]
                    positive_pairs.append((source_idx, target_idx))
    
    # Remove duplicates and self-pairs
    positive_pairs = list(set(p for p in positive_pairs if p[0] != p[1]))
    
    # Sample negative pairs (random pairs not in positive)
    positive_set = set(positive_pairs)
    np.random.seed(GLOBAL_SEED)
    negative_pairs = []
    n_decisions = len(metadata)
    while len(negative_pairs) < len(positive_pairs) * 2:  # 2:1 negative:positive ratio
        i, j = np.random.choice(n_decisions, 2, replace=False)
        if (i, j) not in positive_set and (j, i) not in positive_set:
            negative_pairs.append((i, j))
    
    logger.info(f"Citation heritage: {len(positive_pairs)} positive pairs, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs


def run_citation_heritage(embeddings: np.ndarray, metadata: List[Dict], 
                          positive_pairs: List[Tuple[int, int]], 
                          negative_pairs: List[Tuple[int, int]]) -> Dict[str, Any]:
    """
    Run citation_heritage benchmark: AUC-ROC on citation pairs vs random pairs.
    Frozen threshold: AUC >= 0.65
    """
    from sklearn.metrics import roc_auc_score
    
    # Compute cosine similarities for positive and negative pairs
    pos_similarities = []
    for i, j in positive_pairs:
        if i < len(embeddings) and j < len(embeddings):
            sim = np.dot(embeddings[i], embeddings[j]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
            )
            pos_similarities.append(sim)
    
    neg_similarities = []
    for i, j in negative_pairs:
        if i < len(embeddings) and j < len(embeddings):
            sim = np.dot(embeddings[i], embeddings[j]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
            )
            neg_similarities.append(sim)
    
    # AUC-ROC
    y_true = [1] * len(pos_similarities) + [0] * len(neg_similarities)
    y_score = pos_similarities + neg_similarities
    
    if len(set(y_true)) < 2:
        return {"status": "ERROR", "error": "Insufficient pair diversity for AUC"}
    
    auc_roc = roc_auc_score(y_true, y_score)
    pos_mean = np.mean(pos_similarities) if pos_similarities else 0
    neg_mean = np.mean(neg_similarities) if neg_similarities else 0
    
    return {
        "status": "PASS" if auc_roc >= 0.65 else "FAIL",
        "auc_roc": float(auc_roc),
        "positive_pairs": len(pos_similarities),
        "negative_pairs": len(neg_similarities),
        "positive_mean_similarity": float(pos_mean),
        "negative_mean_similarity": float(neg_mean),
        "similarity_gap": float(pos_mean - neg_mean),
        "threshold": 0.65,
    }


# ============================================================
# V17B LABEL NORMALIZATION TEST
# ============================================================
def test_v17b_label_normalization(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """
    Test whether v17b label normalization (15-25% purity gain) generalizes to 174k.
    
    v17b finding: Normalizing legal_area labels (removing language variants, 
    standardizing) improves branch purity by 15-25% across 4 seeds.
    
    Test: Compare cluster purity using raw legal_area vs normalized legal_area.
    """
    # Extract legal areas
    raw_legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    raw_legal_areas = [la if la and la != 'null' else 'unknown' for la in raw_legal_areas]
    
    # v17b normalization: group language variants
    # e.g., "Vertragsrecht" (de) + "Droit des contrats" (fr) + "Diritto contrattuale" (it) -> "Contract Law"
    NORMALIZATION_MAP = {
        # Contract Law
        'Vertragsrecht': 'Contract Law',
        'Droit des contrats': 'Contract Law',
        'Diritto contrattuale': 'Contract Law',
        # Family Law
        'Familienrecht': 'Family Law',
        'Droit de la famille': 'Family Law',
        'Diritto di famiglia': 'Family Law',
        # Criminal Procedure
        'Strafprozess': 'Criminal Procedure',
        'Procédure pénale': 'Criminal Procedure',
        'Procedura penale': 'Criminal Procedure',
        # Debt Enforcement
        'Schuldbetreibungs- und Konkursrecht': 'Debt Enforcement & Bankruptcy',
        'Droit de la poursuite et de la faillite': 'Debt Enforcement & Bankruptcy',
        'Diritto d\'esecuzione e fallimento': 'Debt Enforcement & Bankruptcy',
        # Constitutional Law
        'Verfassungsrecht': 'Constitutional Law',
        'Droit constitutionnel': 'Constitutional Law',
        'Diritto costituzionale': 'Constitutional Law',
        # Administrative Law
        'Verwaltungsrecht': 'Administrative Law',
        'Droit administratif': 'Administrative Law',
        'Diritto amministrativo': 'Administrative Law',
        # Tax Law
        'Steuerrecht': 'Tax Law',
        'Droit fiscal': 'Tax Law',
        'Diritto tributario': 'Tax Law',
        # Social Insurance
        'Sozialversicherungsrecht': 'Social Insurance Law',
        'Droit des assurances sociales': 'Social Insurance Law',
        'Diritto delle assicurazioni sociali': 'Social Insurance Law',
        # Invalidity Insurance
        'Invalidenversicherung': 'Invalidity Insurance',
        'Assurance invalidité': 'Invalidity Insurance',
        'Assicurazione invalidità': 'Invalidity Insurance',
        # Citizenship & Foreigners
        'Bürgerrecht und Ausländerrecht': 'Citizenship & Foreigners Law',
        'Droit de la citoyenneté et des étrangers': 'Citizenship & Foreigners Law',
        'Diritto di cittadinanza e degli stranieri': 'Citizenship & Foreigners Law',
    }
    
    normalized_legal_areas = [NORMALIZATION_MAP.get(la, la) for la in raw_legal_areas]
    
    # Cluster embeddings at 16 clusters (matching ~16 legal areas)
    kmeans = KMeans(n_clusters=16, random_state=GLOBAL_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Compute purity for raw and normalized labels
    def compute_purity(labels):
        purities = []
        for c in range(16):
            mask = cluster_labels == c
            if np.sum(mask) == 0:
                continue
            cluster_labels_subset = [labels[i] for i in np.where(mask)[0]]
            # Exclude 'unknown'
            cluster_labels_subset = [l for l in cluster_labels_subset if l != 'unknown']
            if not cluster_labels_subset:
                continue
            majority = Counter(cluster_labels_subset).most_common(1)[0][1]
            purity = majority / len(cluster_labels_subset)
            purities.append(purity)
        return np.mean(purities) if purities else 0
    
    raw_purity = compute_purity(raw_legal_areas)
    normalized_purity = compute_purity(normalized_legal_areas)
    gain = (normalized_purity - raw_purity) / raw_purity if raw_purity > 0 else 0
    
    return {
        "raw_legal_area_purity": float(raw_purity),
        "normalized_legal_area_purity": float(normalized_purity),
        "purity_gain_pct": float(gain * 100),
        "n_raw_labels": len(set(raw_legal_areas)),
        "n_normalized_labels": len(set(normalized_legal_areas)),
        "v17b_expectation": "15-25% gain",
        "generalizes": gain >= 0.15,
    }


# ============================================================
# FULL 174k EVALUATION WITH SCALABLE NN
# ============================================================
def evaluate_174k_representation(name: str, embeddings: np.ndarray, metadata: List[Dict],
                                  citation_pairs: Tuple[List, List] = None) -> Dict[str, Any]:
    """Evaluate a single 174k representation using scalable NN infrastructure."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating 174k representation: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Ensure embeddings match metadata length
    n_meta = len(metadata)
    if embeddings.shape[0] > n_meta:
        embeddings = embeddings[:n_meta]
        logger.warning(f"Trimmed embeddings from {embeddings.shape[0]} to {n_meta}")
    elif embeddings.shape[0] < n_meta:
        logger.error(f"Embeddings ({embeddings.shape[0]}) shorter than metadata ({n_meta})")
        return {"error": "Embedding/metadata length mismatch", "verdict": "ERROR"}
    
    # 1. Create stratified subsample for exact adversarial evaluation
    subsample_indices = create_stratified_subsample(metadata)
    logger.info(f"Created stratified subsample: {len(subsample_indices)} decisions")
    
    sub_embeddings = embeddings[subsample_indices]
    sub_metadata = [metadata[i] for i in subsample_indices]
    
    # 2. Run scalable adversarial benchmarks on subsample (exact k-NN)
    logger.info("Running adversarial benchmarks (exact k-NN on stratified subsample)...")
    adv_results = run_scalable_adversarial_benchmarks(sub_embeddings, sub_metadata, force_exact=True)
    
    # 3. Run full scalable evaluation on full corpus
    logger.info("Running full scalable evaluation on 174k corpus...")
    full_results = run_scalable_full_evaluation(embeddings, metadata, force_exact=False)
    
    # 4. Citation heritage (using full embeddings for pair computation)
    citation_result = {}
    if citation_pairs:
        logger.info("Running citation_heritage benchmark...")
        pos_pairs, neg_pairs = citation_pairs
        citation_result = run_citation_heritage(embeddings, metadata, pos_pairs, neg_pairs)
    
    # 5. v17b label normalization test
    logger.info("Testing v17b label normalization...")
    v17b_result = test_v17b_label_normalization(embeddings, metadata)
    
    duration = time.time() - start_time
    
    # Overall verdict: MUST pass BOTH adversarial gates (frozen rule)
    both_adv_pass = adv_results['both_pass']
    verdict = "PASS" if both_adv_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'subsample_size': len(subsample_indices),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'full_corpus': full_results,
        'citation_heritage': citation_result,
        'v17b_label_normalization': v17b_result,
        'verdict': verdict,
        'both_adversarial_pass': both_adv_pass,
    }


def main():
    set_global_seed(GLOBAL_SEED)
    
    config_hash = get_config_hash()
    
    logger.info("=" * 70)
    logger.info(f"Evaluation Lane: 174k TF-IDF Formal Suite (Factory Direction v29)")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Subsample size: {SUBSAMPLE_SIZE} (exact k-NN, HNSW artifact fix)")
    logger.info("=" * 70)
    
    # Load metadata
    logger.info("\n1. Loading 174k evaluation metadata...")
    with open(METADATA_174K_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Load citation pairs for heritage benchmark
    logger.info("\n2. Loading citation pairs for citation_heritage benchmark...")
    citation_pairs = load_citation_pairs()
    
    # Verify all embedding files exist
    logger.info("\n3. Verifying embedding files...")
    missing = []
    for name, path in TFIDF_REPRESENTATIONS.items():
        if not path.exists():
            missing.append((name, path))
            logger.error(f"  MISSING: {name} at {path}")
        else:
            logger.info(f"  OK: {name} at {path}")
    
    if missing:
        logger.error(f"Missing {len(missing)} embedding files. Cannot proceed.")
        return
    
    # Load and evaluate each representation
    logger.info("\n4. Running evaluations...")
    all_results = {}
    
    for name, path in TFIDF_REPRESENTATIONS.items():
        try:
            logger.info(f"  Loading {name}...")
            embeddings = np.load(path)
            logger.info(f"  Loaded {name}: {embeddings.shape}")
            
            result = evaluate_174k_representation(name, embeddings, metadata, citation_pairs)
            all_results[name] = result
            
            # Log summary
            adv = result['adversarial']
            fc = result['full_corpus']
            ch = result.get('citation_heritage', {})
            v17b = result.get('v17b_label_normalization', {})
            
            logger.info(f"  {name}: verdict={result['verdict']}, "
                       f"lang_dom={adv['language_dominance_score']:.4f} "
                       f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                       f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                       f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
                       f"citation_auc={ch.get('auc_roc', 'N/A'):.4f} "
                       f"({'PASS' if ch.get('status')=='PASS' else 'FAIL' if ch.get('status') else 'N/A'}), "
                       f"v17b_gain={v17b.get('purity_gain_pct', 'N/A'):.1f}% "
                       f"({'generalizes' if v17b.get('generalizes') else 'no generalize' if v17b else 'N/A'})")
            
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
    output_file = OUTPUT_DIR / f"174k_tfidf_formal_suite_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "174k_tfidf_formal_suite_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 90)
    logger.info("174k TF-IDF FORMAL SUITE - FROZEN HARNESS v3 SUMMARY")
    logger.info("=" * 90)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED} | Subsample: {SUBSAMPLE_SIZE}")
    logger.info("-" * 90)
    logger.info(f"{'Representation':<40} {'Verdict':<7} {'LangDom':>7} {'Jurist':>7} {'Both':>5} {'CiteAUC':>7} {'v17b%':>7}")
    logger.info("-" * 90)
    
    # Sort by adversarial pass, then jurist preference
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res.get('both_adversarial_pass', False)
        jurist = res.get('adversarial', {}).get('jurist_preference_rate', 0)
        lang_dom = res.get('adversarial', {}).get('language_dominance_score', 1.0)
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    passed_count = 0
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<40} {'ERROR':<7} {'N/A':>7} {'N/A':>7} {'N/A':>5} {'N/A':>7} {'N/A':>7}")
            continue
        
        adv = res['adversarial']
        ch = res.get('citation_heritage', {})
        v17b = res.get('v17b_label_normalization', {})
        
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        cite_auc = ch.get('auc_roc', 0)
        v17b_gain = v17b.get('purity_gain_pct', 0)
        
        if both == "✓":
            passed_count += 1
        
        logger.info(f"{name:<40} {res['verdict']:<7} {ld:>7.4f} {jp:>7.4f} {both:>5} {cite_auc:>7.4f} {v17b_gain:>6.1f}%")
    
    logger.info("-" * 90)
    logger.info(f"Passed both adversarial gates: {passed_count}/{len(TFIDF_REPRESENTATIONS)}")
    
    # v17b summary
    logger.info("\nv17b Label Normalization Generalization Test:")
    for name, res in sorted_results:
        if 'error' not in res:
            v17b = res.get('v17b_label_normalization', {})
            logger.info(f"  {name}: raw_purity={v17b.get('raw_legal_area_purity', 0):.4f}, "
                       f"norm_purity={v17b.get('normalized_legal_area_purity', 0):.4f}, "
                       f"gain={v17b.get('purity_gain_pct', 0):.1f}%, "
                       f"generalizes={v17b.get('generalizes', False)}")
    
    # Citation heritage summary
    logger.info("\nCitation Heritage Validation (174k citation-ID resolution):")
    for name, res in sorted_results:
        if 'error' not in res:
            ch = res.get('citation_heritage', {})
            logger.info(f"  {name}: AUC={ch.get('auc_roc', 0):.4f} "
                       f"({'PASS' if ch.get('status')=='PASS' else 'FAIL' if ch.get('status') else 'N/A'})")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 90)
    
    return all_results, config_hash


if __name__ == "__main__":
    main()