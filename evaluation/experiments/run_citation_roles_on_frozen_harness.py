#!/usr/bin/env python3
"""
Evaluation Lane v9 - Citation Role Modeling Evaluation on Frozen Harness v3

Factory Direction v9 Objective 2:
"Citation role modeling evaluation — evaluate 2,988 role annotations (citing, following, criticizing) 
against adversarial gates on frozen harness"

Regenerates citation role hybrid embeddings from resolved roles and evaluates
them on the frozen evaluation_v3_harness.py (seed=42, config_hash=4323f833fa72366a).
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List
from collections import defaultdict, Counter
from sklearn.preprocessing import normalize

# Add evaluation to path
import sys
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
from evaluation_v3_harness import (
    GLOBAL_SEED, set_global_seed, evaluate_representation, get_config_hash,
    load_evaluation_metadata, assign_branch
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
LEX_ACCEPTED_ROOT = Path("/tmp/lex_accepted")
RESOLVED_ROLES_FILE = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v7/citation_id_resolution_bge/citation_roles_resolved.json"
CORPUS_FILE = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v5/bger_full_corpus.jsonl"
CP_PATH = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy"
METADATA_PATH = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v5/center_projected_full/metadata.json"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v3_citation_roles_frozen")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Role types that PASS adversarial gates (from legal-distance v7)
ROLE_NAMES = ['citing', 'following', 'distinguishing', 'overruling', 'criticizing']
PASSING_ROLES = ['citing', 'following', 'criticizing']  # distinguishing/overruling too sparse
ALPHAS = [0.3, 0.5, 0.7]


def load_resolved_roles() -> List[Dict]:
    """Load resolved role annotations."""
    with open(RESOLVED_ROLES_FILE, 'r') as f:
        roles = json.load(f)
    logger.info(f"Loaded {len(roles)} resolved role annotations")
    resolved = [r for r in roles if r.get('resolved', False)]
    logger.info(f"Resolved: {len(resolved)}")
    return resolved


def load_corpus_decision_ids() -> List[str]:
    """Load decision_ids from corpus."""
    decision_ids = []
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            decision_ids.append(d['decision_id'])
    return sorted(decision_ids)


def load_metadata() -> List[Dict]:
    """Load metadata with branch/language."""
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    return metadata


def build_role_count_features(roles: List[Dict], decision_ids: List[str]) -> Dict[str, np.ndarray]:
    """Build role count features per target decision."""
    did_to_idx = {did: i for i, did in enumerate(decision_ids)}
    n = len(decision_ids)
    
    # Feature matrix: (n_decisions, 5) - counts of each role type per target
    features = np.zeros((n, len(ROLE_NAMES)), dtype=np.float32)
    
    for role_anno in roles:
        if not role_anno.get('resolved', False):
            continue
        target_did = role_anno.get('resolved_decision_id')
        role_type = role_anno.get('role')
        
        if target_did in did_to_idx and role_type in ROLE_NAMES:
            idx = did_to_idx[target_did]
            role_idx = ROLE_NAMES.index(role_type)
            features[idx, role_idx] += 1
    
    # Normalize features per decision
    row_sums = features.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    features_norm = features / row_sums
    
    logger.info(f"Role count features shape: {features.shape}")
    logger.info(f"Non-zero targets: {(features.sum(axis=1) > 0).sum()}")
    
    # Extract per-role vectors
    role_vectors = {}
    for i, role in enumerate(ROLE_NAMES):
        vec = features[:, i].copy()
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        role_vectors[role] = vec
        non_zero = (vec != 0).sum()
        logger.info(f"  {role}: {non_zero}/{len(vec)} non-zero, mean={vec.mean():.4f}")
    
    return role_vectors


def create_hybrid_role_embeddings(role_vectors: Dict[str, np.ndarray], 
                                   center_projected: np.ndarray) -> Dict[str, np.ndarray]:
    """Create hybrid embeddings combining center_projected with role signals."""
    n = center_projected.shape[0]
    hybrids = {}
    
    # Normalize center_projected
    cp_norm = normalize(center_projected, axis=1)
    
    for role, rv in role_vectors.items():
        rv_2d = rv.reshape(-1, 1)
        
        for alpha in ALPHAS:
            # Hybrid: alpha * center_projected + (1-alpha) * role_vector (broadcasted)
            hybrid = alpha * cp_norm
            role_weight = (1 - alpha) * rv_2d
            hybrid = hybrid + role_weight  # Broadcast
            
            # Re-normalize
            hybrid = normalize(hybrid, axis=1)
            hybrids[f"{role}_alpha{alpha:.1f}"] = hybrid
    
    return hybrids


def main():
    set_global_seed(GLOBAL_SEED)
    config_hash = get_config_hash()
    
    logger.info("=" * 70)
    logger.info("Evaluation Lane v9 - Citation Role Modeling on Frozen Harness v3")
    logger.info(f"Config hash: {config_hash}")
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\n1. Loading resolved roles...")
    roles = load_resolved_roles()
    
    logger.info("\n2. Loading corpus decision IDs...")
    decision_ids = load_corpus_decision_ids()
    
    logger.info("\n3. Loading center_projected embeddings...")
    center_projected = np.load(CP_PATH)
    logger.info(f"Center projected shape: {center_projected.shape}")
    
    logger.info("\n4. Loading metadata...")
    metadata = load_metadata()
    logger.info(f"Metadata: {len(metadata)} decisions")
    
    # Align
    if len(center_projected) != len(decision_ids):
        logger.warning(f"Size mismatch: center_projected={len(center_projected)}, decision_ids={len(decision_ids)}")
    if len(center_projected) != len(metadata):
        logger.warning(f"Size mismatch: center_projected={len(center_projected)}, metadata={len(metadata)}")
    
    # Build role features
    logger.info("\n5. Building role count features...")
    role_vectors = build_role_count_features(roles, decision_ids)
    
    # Create hybrid embeddings
    logger.info("\n6. Creating hybrid role embeddings...")
    hybrids = create_hybrid_role_embeddings(role_vectors, center_projected)
    
    # Save embeddings
    logger.info("\n7. Saving hybrid embeddings...")
    for name, emb in hybrids.items():
        np.save(OUTPUT_DIR / f"{name}.npy", emb)
        logger.info(f"  Saved {name}: {emb.shape}")
    
    # Evaluate on frozen harness
    logger.info("\n8. Running frozen harness evaluation...")
    all_results = {}
    
    # Evaluate passing role hybrids
    for name, embeddings in hybrids.items():
        role_name = name.split('_')[0]
        if role_name not in PASSING_ROLES:
            logger.info(f"  Skipping {name} (role {role_name} too sparse)")
            continue
            
        logger.info(f"\nEvaluating {name}...")
        try:
            result = evaluate_representation(name, embeddings, metadata)
            all_results[name] = result
            
            adv = result['adversarial']
            logger.info(f"  {name}: verdict={result['verdict']}, "
                       f"lang_dom={adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']}), "
                       f"jurist_pref={adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            all_results[name] = {'error': str(e), 'verdict': 'ERROR'}
    
    # Also evaluate center_projected baseline
    logger.info("\nEvaluating center_projected baseline...")
    result_cp = evaluate_representation("center_projected_baseline", center_projected, metadata)
    all_results["center_projected_baseline"] = result_cp
    
    # Save results
    logger.info("\n9. Saving results...")
    with open(OUTPUT_DIR / "citation_roles_frozen_harness_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION ROLE FROZEN HARNESS EVALUATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Config hash: {config_hash} | Global seed: {GLOBAL_SEED}")
    logger.info("-" * 70)
    logger.info(f"{'Representation':<35} {'Verdict':<7} {'LangDom':>7} {'LD-P':>5} {'Jurist':>7} {'JP-P':>5} {'Both':>5}")
    logger.info("-" * 70)
    
    for name, res in all_results.items():
        if 'error' in res:
            logger.info(f"{name:<35} {'ERROR':<7} {'N/A':>7} {'N/A':>5} {'N/A':>7} {'N/A':>5} {'N/A':>5}")
            continue
        
        adv = res['adversarial']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        logger.info(f"{name:<35} {res['verdict']:<7} {ld:>7.4f} {ld_pass:>5} {jp:>7.4f} {jp_pass:>5} {both:>5}")
    
    # Compare with reference
    if 'center_projected_baseline' in all_results and 'error' not in all_results['center_projected_baseline']:
        ref = all_results['center_projected_baseline']
        logger.info(f"\n📏 REFERENCE BASELINE (center_projected):")
        logger.info(f"   Language dominance: {ref['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {ref['adversarial']['jurist_preference_rate']:.4f}")
        logger.info(f"   Both adversarial pass: {ref['both_adversarial_pass']}")
        
        logger.info(f"\n📊 DELTA vs REFERENCE:")
        for name, res in all_results.items():
            if name == 'center_projected_baseline' or 'error' in res:
                continue
            delta_ld = res['adversarial']['language_dominance_score'] - ref['adversarial']['language_dominance_score']
            delta_jp = res['adversarial']['jurist_preference_rate'] - ref['adversarial']['jurist_preference_rate']
            logger.info(f"   {name}: ΔLangDom={delta_ld:+.4f}, ΔJuristPref={delta_jp:+.4f}")
    
    logger.info(f"\nResults saved to: {OUTPUT_DIR}")
    return all_results, config_hash


if __name__ == "__main__":
    main()