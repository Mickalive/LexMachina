#!/usr/bin/env python3
"""
Legal Distance Lane v7 - Citation Role Embeddings from Resolved Roles

Builds role-specific embedding matrices (citing, following, distinguishing, 
overruling, criticizing) from the 2,988 resolved role annotations.

Uses the BGE/ATF citation resolution to unlock graph connectivity for 
previously zero-matrix roles (distinguishing, overruling, criticizing).
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
RESOLVED_ROLES_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/citation_id_resolution_bge/citation_roles_resolved.json")
ROLE_GRAPH_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/citation_id_resolution_bge/role_graph.json")
CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/citation_role_embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
EMBEDDING_DIM = 64
SVD_COMPONENTS = 64


def load_resolved_roles() -> List[Dict]:
    """Load resolved role annotations."""
    with open(RESOLVED_ROLES_FILE, 'r') as f:
        roles = json.load(f)
    logger.info(f"Loaded {len(roles)} resolved role annotations")
    return roles


def load_corpus_decision_ids() -> List[str]:
    """Load decision_ids from corpus."""
    decision_ids = []
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            decision_ids.append(d['decision_id'])
    logger.info(f"Loaded {len(decision_ids)} decision IDs")
    return sorted(decision_ids)


def build_role_matrices(roles: List[Dict], decision_ids: List[str], dim: int = EMBEDDING_DIM) -> Dict[str, np.ndarray]:
    """
    Build role-specific embedding matrices from resolved roles.
    
    Approach: Create citation graph adjacency weighted by role, then
    use SVD to get low-dimensional embeddings for each role.
    
    Returns: Dict of role_name -> (n_decisions, dim) embedding matrix
    """
    did_to_idx = {did: i for i, did in enumerate(decision_ids)}
    n = len(decision_ids)
    
    # Role names in priority order
    role_names = ['citing', 'following', 'distinguishing', 'overruling', 'criticizing']
    
    # Build adjacency matrices for each role
    # Matrix[i, j] = weight of role from decision i to decision j
    role_adjacency = {role: np.zeros((n, n), dtype=np.float32) for role in role_names}
    
    for role_anno in roles:
        if not role_anno.get('resolved', False):
            continue
        
        source_did = role_anno.get('source_decision')
        target_did = role_anno.get('resolved_decision_id')
        role_type = role_anno.get('role')
        
        # The roles data doesn't have source_decision directly
        # We need to find which decision this role annotation belongs to
        # Looking at the original roles file structure...
        pass
    
    # Actually, the roles file has 2988 entries but they're not linked to source decisions
    # Let me check the original roles structure more carefully
    
    logger.warning("Role annotations don't have source decision - using target-only approach")
    return {role: np.zeros((n, dim), dtype=np.float32) for role in role_names}


def build_role_embeddings_from_counts(roles: List[Dict], decision_ids: List[str], dim: int = EMBEDDING_DIM) -> Dict[str, np.ndarray]:
    """
    Alternative approach: Use role counts per target decision as features,
    then project to embedding space.
    """
    did_to_idx = {did: i for i, did in enumerate(decision_ids)}
    n = len(decision_ids)
    
    role_names = ['citing', 'following', 'distinguishing', 'overruling', 'criticizing']
    
    # Feature matrix: (n_decisions, 5) - counts of each role type per target
    features = np.zeros((n, len(role_names)), dtype=np.float32)
    
    for role_anno in roles:
        if not role_anno.get('resolved', False):
            continue
        target_did = role_anno.get('resolved_decision_id')
        role_type = role_anno.get('role')
        
        if target_did in did_to_idx and role_type in role_names:
            idx = did_to_idx[target_did]
            role_idx = role_names.index(role_type)
            features[idx, role_idx] += 1
    
    # Normalize features
    row_sums = features.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    features_norm = features / row_sums
    
    # Use SVD to project to higher dimension (or just use as-is if 5 dims)
    # Actually, we can use these as 5-dim features and pad/project
    # But the standard is 64-dim, so let's create embeddings by combining with center_projected
    
    logger.info(f"Role count features shape: {features.shape}")
    logger.info(f"Non-zero targets: {(features.sum(axis=1) > 0).sum()}")
    
    # For each role, create a vector based on whether decision has that role
    role_vectors = {}
    for i, role in enumerate(role_names):
        vec = features[:, i].copy()
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        # Expand to dim using random projection (for now)
        # Better: combine with center_projected or use graph embeddings
        role_vectors[role] = vec
    
    return role_vectors


def create_hybrid_role_embeddings(role_vectors: Dict[str, np.ndarray], 
                                  center_projected: np.ndarray,
                                  dim: int = EMBEDDING_DIM) -> Dict[str, np.ndarray]:
    """
    Create hybrid embeddings combining center_projected with role signals.
    """
    n = center_projected.shape[0]
    hybrids = {}
    
    # Normalize center_projected
    cp_norm = normalize(center_projected, axis=1)
    
    alphas = [0.3, 0.5, 0.7]
    
    for role, rv in role_vectors.items():
        # Expand role vector to matrix (n, 1)
        rv_2d = rv.reshape(-1, 1)
        
        for alpha in alphas:
            # Hybrid: alpha * center_projected + (1-alpha) * role_vector (broadcasted)
            # Since role vector is 1-dim per decision, we need to project it
            # Simple approach: use role vector as weight for center_projected
            hybrid = alpha * cp_norm
            # Add role signal by modulating the embedding
            role_weight = (1 - alpha) * rv_2d
            hybrid = hybrid + role_weight  # Broadcast
            
            # Re-normalize
            hybrid = normalize(hybrid, axis=1)
            hybrids[f"{role}_alpha{alpha:.1f}"] = hybrid
    
    return hybrids


def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v7 - Citation Role Embeddings")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\n1. Loading resolved roles...")
    roles = load_resolved_roles()
    
    logger.info("\n2. Loading corpus decision IDs...")
    decision_ids = load_corpus_decision_ids()
    
    # Load center_projected for hybrid creation
    logger.info("\n3. Loading center_projected embeddings...")
    cp_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
    center_projected = np.load(cp_path)
    logger.info(f"Center projected shape: {center_projected.shape}")
    
    # Align center_projected with our decision_ids (they should match)
    if len(center_projected) != len(decision_ids):
        logger.warning(f"Size mismatch: center_projected={len(center_projected)}, decision_ids={len(decision_ids)}")
    
    # 4. Build role count features
    logger.info("\n4. Building role count features...")
    role_vectors = build_role_embeddings_from_counts(roles, decision_ids)
    
    # Print role vector stats
    for role, vec in role_vectors.items():
        non_zero = (vec != 0).sum()
        logger.info(f"  {role}: {non_zero}/{len(vec)} non-zero, mean={vec.mean():.4f}, std={vec.std():.4f}")
    
    # 5. Create hybrid embeddings
    logger.info("\n5. Creating hybrid role embeddings...")
    hybrids = create_hybrid_role_embeddings(role_vectors, center_projected)
    
    # 6. Evaluate each hybrid against adversarial benchmarks
    logger.info("\n6. Running adversarial evaluation...")
    
    # Import evaluation harness
    import sys
    sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
    from evaluation_v3_harness import (
        GLOBAL_SEED, set_global_seed, evaluate_representation, get_config_hash
    )
    
    set_global_seed(GLOBAL_SEED)
    config_hash = get_config_hash()
    
    # Load metadata
    meta_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
    with open(meta_path, 'r') as f:
        metadata = json.load(f)
    
    # Add branch to metadata
    from evaluation_v3_harness import assign_branch
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    # Evaluate each hybrid
    all_results = {}
    for name, embeddings in hybrids.items():
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
    
    # 7. Save results
    logger.info("\n7. Saving results...")
    with open(OUTPUT_DIR / "role_hybrid_evaluation.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # 8. Summary
    logger.info("\n" + "=" * 70)
    logger.info("ROLE HYBRID EVALUATION SUMMARY")
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
    
    return all_results


if __name__ == "__main__":
    main()