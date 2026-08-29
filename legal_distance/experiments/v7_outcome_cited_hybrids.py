#!/usr/bin/env python3
"""
Legal Distance Lane v7 - Outcome TF-IDF + Cited Decisions TF-IDF Hybrids

Factory Direction v9 Recommendation:
"New Finding: outcome_tfidf achieves even better cross-lingual alignment (LangDom=0.4458, 
JuristPref=0.8488) but collapses fractal structure. This suggests a hybrid approach 
combining cited_decisions_tfidf (for fractal quality) with outcome_tfidf 
(for cross-lingual alignment) could achieve both LangDom < 0.6 and robust fractal structure."

This experiment:
1. Builds outcome_tfidf from the 1200-decision signals file
2. Creates hybrids with cited_decisions_tfidf (the best zero-shot representation)
3. Evaluates against frozen adversarial harness v3 (seed=42)
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.preprocessing import normalize

# Import frozen benchmark implementations from v3 harness
import sys
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')

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
    load_evaluation_metadata,
    prepare_metadata,
    adversarial_language_dominance,
    simulate_pairwise_preference,
    simulate_cluster_coherence_rating,
    simulate_cross_language_retrieval,
    compute_jurivoc_alignment,
    compute_scale_stability,
    compute_boilerplate_resistance,
    run_fractal_quality_benchmarks,
    run_adversarial_benchmarks,
    evaluate_representation,
    get_config_hash,
    set_global_seed,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_signals_full.jsonl")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
CP_768_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
CP_64_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/outcome_cited_hybrids")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_signals_and_match_metadata() -> Tuple[Dict, List[Dict], List[int]]:
    """Load signals and match with metadata from center_projected_full."""
    # Load signals (1200 decisions)
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")

    # Load full metadata (10802 decisions)
    with open(METADATA_PATH, 'r') as f:
        full_metadata = json.load(f)
    logger.info(f"Loaded full metadata for {len(full_metadata)} decisions")

    # Match signals to metadata by decision_id
    meta_by_id = {m['decision_id']: (i, m) for i, m in enumerate(full_metadata)}
    
    matched_metadata = []
    matched_indices = []
    missing_count = 0
    
    for decision_id, signal in signals.items():
        if decision_id in meta_by_id:
            idx, meta = meta_by_id[decision_id]
            matched_metadata.append(meta)
            matched_indices.append(idx)
        else:
            missing_count += 1
    
    logger.info(f"Matched {len(matched_metadata)} signals to metadata, {missing_count} missing")
    
    # Add branch to metadata
    for meta in matched_metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    return signals, matched_metadata, matched_indices


def build_tfidf_embeddings(texts: List[str], max_features: int = 5000, n_components: int = 128) -> Tuple[np.ndarray, int]:
    """
    Build TF-IDF + TruncatedSVD embeddings from texts.
    Returns (embeddings, actual_n_components).
    """
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    logger.info(f"TF-IDF matrix shape: {tfidf_matrix.shape}, vocab: {len(vectorizer.vocabulary_)}")
    
    actual_n_comp = min(n_components, tfidf_matrix.shape[1] - 1, len(texts) - 1)
    if actual_n_comp <= 1:
        logger.warning(f"Insufficient features for SVD: {actual_n_comp}")
        return np.zeros((len(texts), n_components)), 0
    
    svd = TruncatedSVD(n_components=actual_n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    
    # Normalize
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    logger.info(f"Built TF-IDF embeddings: {reduced.shape}, n_comp={actual_n_comp}")
    return reduced, actual_n_comp


def build_outcome_tfidf(signals: Dict, metadata: List[Dict]) -> Tuple[np.ndarray, List[int]]:
    """
    Build TF-IDF embeddings from outcome field.
    Returns embeddings aligned with metadata order.
    """
    texts = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        did = meta['decision_id']
        sig = signals.get(did, {})
        
        outcome = sig.get('outcome', '')
        if outcome and outcome != 'null':
            texts.append(outcome)
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        logger.warning(f"Only {len(valid_indices)} valid texts for outcome TF-IDF")
        return np.zeros((len(metadata), 128)), valid_indices
    
    # Filter to only valid texts for fitting
    valid_texts = [texts[i] for i in valid_indices]
    
    reduced, n_comp = build_tfidf_embeddings(valid_texts, max_features=5000, n_components=128)
    
    if n_comp == 0:
        return np.zeros((len(metadata), 128)), valid_indices
    
    # Pad to full metadata length
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    logger.info(f"Built outcome_tfidf: {full_emb.shape}, valid={len(valid_indices)}, n_comp={n_comp}")
    return full_emb, valid_indices


def build_cited_decisions_tfidf(signals: Dict, metadata: List[Dict]) -> Tuple[np.ndarray, List[int]]:
    """
    Build TF-IDF embeddings from cited_decisions field.
    Returns embeddings aligned with metadata order.
    """
    texts = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        did = meta['decision_id']
        sig = signals.get(did, {})
        
        cited = sig.get('cited_decisions', [])
        if cited:
            texts.append(" ".join(cited))
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        logger.warning(f"Only {len(valid_indices)} valid texts for cited TF-IDF")
        return np.zeros((len(metadata), 128)), valid_indices
    
    # Filter to only valid texts for fitting
    valid_texts = [texts[i] for i in valid_indices]
    
    reduced, n_comp = build_tfidf_embeddings(valid_texts, max_features=5000, n_components=128)
    
    if n_comp == 0:
        return np.zeros((len(metadata), 128)), valid_indices
    
    # Pad to full metadata length
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    logger.info(f"Built cited_decisions_tfidf: {full_emb.shape}, valid={len(valid_indices)}, n_comp={n_comp}")
    return full_emb, valid_indices


def create_hybrid(emb_a: np.ndarray, emb_b: np.ndarray, alpha: float) -> np.ndarray:
    """
    Create hybrid representation: alpha * emb_a + (1-alpha) * emb_b
    Embeddings may have different dimensions - project to common dimension using PCA.
    """
    # Determine target dimension (use smaller of the two)
    target_dim = min(emb_a.shape[1], emb_b.shape[1])
    
    # Project both to target dimension if needed
    if emb_a.shape[1] != target_dim:
        pca_a = PCA(n_components=target_dim, random_state=42)
        emb_a = pca_a.fit_transform(emb_a)
    if emb_b.shape[1] != target_dim:
        pca_b = PCA(n_components=target_dim, random_state=42)
        emb_b = pca_b.fit_transform(emb_b)
    
    # Normalize both
    norms_a = np.linalg.norm(emb_a, axis=1, keepdims=True)
    norms_a[norms_a == 0] = 1
    emb_a_norm = emb_a / norms_a
    
    norms_b = np.linalg.norm(emb_b, axis=1, keepdims=True)
    norms_b[norms_b == 0] = 1
    emb_b_norm = emb_b / norms_b
    
    hybrid = alpha * emb_a_norm + (1 - alpha) * emb_b_norm
    
    # Re-normalize
    norms = np.linalg.norm(hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    hybrid = hybrid / norms
    
    return hybrid


def main():
    set_global_seed(GLOBAL_SEED)
    
    config_hash = get_config_hash()
    logger.info("=" * 70)
    logger.info(f"Legal Distance Lane v7 - Outcome + Cited Decisions Hybrids")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info("=" * 70)
    
    # 1. Load signals and match metadata
    logger.info("\n1. Loading signals and matching metadata...")
    signals, metadata, matched_indices = load_signals_and_match_metadata()
    
    # 2. Load center_projected baselines
    logger.info("\n2. Loading center_projected baselines...")
    cp_768 = np.load(CP_768_PATH)
    cp_64 = np.load(CP_64_PATH)
    logger.info(f"  center_projected 768-dim: {cp_768.shape}")
    logger.info(f"  center_projected 64-dim: {cp_64.shape}")
    
    # 3. Build outcome_tfidf
    logger.info("\n3. Building outcome_tfidf...")
    outcome_tfidf, outcome_valid = build_outcome_tfidf(signals, metadata)
    
    # 4. Build cited_decisions_tfidf
    logger.info("\n4. Building cited_decisions_tfidf...")
    cited_tfidf, cited_valid = build_cited_decisions_tfidf(signals, metadata)
    
    # 5. Create hybrids
    logger.info("\n5. Creating hybrid representations...")
    hybrids = {}
    
    # Cited + Outcome hybrids (primary experiment from v9 recommendation)
    for alpha in [0.3, 0.5, 0.7]:
        name = f"cited_decisions_tfidf_outcome_hybrid_{alpha:.1f}"
        hybrids[name] = create_hybrid(cited_tfidf, outcome_tfidf, alpha)
        logger.info(f"  Created {name}: {hybrids[name].shape}")
    
    # Also test outcome + center_projected for comparison
    for alpha in [0.3, 0.5, 0.7]:
        name = f"outcome_tfidf_hybrid_cp64_{alpha:.1f}"
        hybrids[name] = create_hybrid(outcome_tfidf, cp_64, alpha)
        logger.info(f"  Created {name}: {hybrids[name].shape}")
    
    # And outcome + center_projected 768
    for alpha in [0.3, 0.5, 0.7]:
        name = f"outcome_tfidf_hybrid_cp768_{alpha:.1f}"
        hybrids[name] = create_hybrid(outcome_tfidf, cp_768, alpha)
        logger.info(f"  Created {name}: {hybrids[name].shape}")
    
    # 6. Define all representations to test
    logger.info("\n6. Preparing representations for evaluation...")
    
    representations = {
        'outcome_tfidf': outcome_tfidf,
        'cited_decisions_tfidf': cited_tfidf,
        **hybrids,
        'center_projected_768': cp_768,
        'center_projected_64dim': cp_64,
    }
    
    # 7. Run evaluations
    logger.info("\n7. Running frozen adversarial evaluations...")
    all_results = {}
    
    for name, embeddings in representations.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating: {name}")
        logger.info(f"Shape: {embeddings.shape}")
        logger.info(f"{'='*60}")
        
        try:
            result = evaluate_representation(name, embeddings, metadata)
            all_results[name] = result
            
            # Save individual result
            output_file = OUTPUT_DIR / f"eval_{name}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            # Log summary
            adv = result['adversarial']
            jurivoc = result['jurivoc_alignment']
            scale = result['scale_stability']
            boiler = result['boilerplate_resistance']
            frac = result['fractal']
            
            logger.info(f"  {name}: verdict={result['verdict']}, "
                       f"lang_dom={adv['language_dominance_score']:.4f} "
                       f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                       f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                       f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
                       f"jurivoc_l0={jurivoc['level_0_nmi']:.4f}, "
                       f"scale_stability={scale.get('mean_neighbor_overlap', 'N/A'):.4f}, "
                       f"boilerplate_resist={boiler['resistance_score']:.4f}, "
                       f"improvement_rate={frac.get('improvement_rate', 0):.2%}")
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {
                'name': name,
                'error': str(e),
                'verdict': 'ERROR'
            }
    
    # 8. Save all results
    output_file = OUTPUT_DIR / "outcome_cited_hybrids_validation_all_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # 9. Summary report
    logger.info("\n" + "=" * 100)
    logger.info("OUTCOME + CITED DECISIONS HYBRIDS ADVERSARIAL VALIDATION SUMMARY")
    logger.info("=" * 100)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED}")
    logger.info("-" * 100)
    logger.info(f"{'Representation':<50} {'Verdict':<7} {'LangDom':>7} {'LD-P':>5} {'Jurist':>7} {'JP-P':>5} {'Both':>5} {'Jurivoc0':>8} {'Scale':>6} {'Boiler':>7} {'ImpRate':>7}")
    logger.info("-" * 100)
    
    # Sort by adversarial pass, then jurist preference, then language dominance
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
            logger.info(f"{name:<50} {'ERROR':<7} {'N/A':>7} {'N/A':>5} {'N/A':>7} {'N/A':>5} {'N/A':>5} {'N/A':>8} {'N/A':>6} {'N/A':>7} {'N/A':>7}")
            continue
        
        adv = res['adversarial']
        jurivoc = res['jurivoc_alignment']
        scale = res['scale_stability']
        boiler = res['boilerplate_resistance']
        frac = res['fractal']
        
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        scale_score = scale.get('mean_neighbor_overlap', 0)
        boiler_score = boiler['resistance_score']
        imp_rate = frac.get('improvement_rate', 0)
        
        logger.info(f"{name:<50} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>5} {jp:>7.4f} {jp_pass:>5} {both:>5} "
                   f"{jurivoc['level_0_nmi']:>8.4f} {scale_score:>6.4f} {boiler_score:>7.4f} {imp_rate:>6.1%}")
    
    # Find best representation (must pass both adversarial gates)
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v and v['both_adversarial_pass']}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['adversarial']['jurist_preference_rate'],
                                                         -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION (passing both adversarial gates): {best[0]}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Jurivoc Level 0 NMI: {best[1]['jurivoc_alignment']['level_0_nmi']:.4f}")
        logger.info(f"   Scale stability: {best[1]['scale_stability'].get('mean_neighbor_overlap', 'N/A')}")
        logger.info(f"   Boilerplate resistance: {best[1]['boilerplate_resistance']['resistance_score']:.4f}")
        logger.info(f"   Fractal n_fine: {best[1]['fractal'].get('n_fine', 'N/A')}")
        logger.info(f"   Fractal improvement_rate: {best[1]['fractal'].get('improvement_rate', 0):.2%}")
    else:
        logger.info("\n⚠️  NO REPRESENTATION PASSES BOTH ADVERSARIAL GATES")
    
    # Reference baselines
    for ref_name in ['center_projected_64dim', 'center_projected_768', 'cited_decisions_tfidf', 'outcome_tfidf']:
        if ref_name in all_results and 'error' not in all_results[ref_name]:
            ref = all_results[ref_name]
            logger.info(f"\n📏 REFERENCE BASELINE ({ref_name}):")
            logger.info(f"   Language dominance: {ref['adversarial']['language_dominance_score']:.4f} ({ref['adversarial']['adversarial_language_dominance']['status']})")
            logger.info(f"   Jurist preference: {ref['adversarial']['jurist_preference_rate']:.4f} ({ref['adversarial']['jurist_pairwise_preference']['status']})")
            logger.info(f"   Both adversarial pass: {ref['both_adversarial_pass']}")
            logger.info(f"   Fractal n_fine: {ref['fractal'].get('n_fine', 'N/A')}")
            logger.info(f"   Fractal improvement_rate: {ref['fractal'].get('improvement_rate', 0):.2%}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 100)
    
    return all_results, config_hash


if __name__ == "__main__":
    main()