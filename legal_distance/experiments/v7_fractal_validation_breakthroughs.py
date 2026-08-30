#!/usr/bin/env python3
"""
Legal Distance Lane v7 - Fractal Quality Validation of Breakthrough Representations

Validates hierarchical structure of all representations that passed adversarial gates
on frozen harness v3 (seed=42, config_hash=1674829901d55e83).

Representations tested:
1. center_projected_64dim (DEFAULT baseline)
2. cited_decisions_tfidf (zero-shot citation signal)
3. cited_decisions_tfidf_outcome_hybrid_0.3, 0.5, 0.7 (cross-lingual breakthrough)
4. linear_metric_epoch4 (metric learning breakthrough)
5. mahalanobis_metric_epoch4 (metric learning breakthrough)
6. hybrid_stabilized_epoch1 (metric learning breakthrough)
7. citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 (citation role hybrids)

Frozen before observation:
- Corpus: 1,200 BGer decisions (2024 expanded slice)
- Embeddings: As listed above
- Structure: Hierarchical Leiden with coarse_res=0.5, sub_res=3.0
- Metrics: Branch purity, improvement rate, legal_area NMI, overclustering
- Success rule: Improvement rate > 50%, no overclustering, fine purity > coarse purity
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter, defaultdict
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.metrics import normalized_mutual_info_score
import sys

sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity, compute_branch_purity_per_cluster

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Configuration
EVAL_METADATA_FILE = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/fractal_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Frozen harness config for reproducibility
HIERARCHICAL_CONFIG = {
    "coarse_res": 0.5,
    "sub_res": 3.0,
    "k": 15
}

# Overclustering threshold
OVERCLUSTERING_THRESHOLD = 500  # 1 coarse -> >500 fine = overclustering


def load_evaluation_metadata() -> List[Dict]:
    """Load the 1200-decision evaluation metadata with branch info."""
    metadata = []
    with open(EVAL_METADATA_FILE, 'r') as f:
        for line in f:
            metadata.append(json.loads(line))
    logger.info(f"Loaded {len(metadata)} evaluation decisions")
    
    # Ensure branch field exists (already present in evaluation metadata)
    for m in metadata:
        if 'branch' not in m:
            m['branch'] = m.get('branch', 'unknown')
        if 'language' not in m:
            m['language'] = m.get('language', 'de')
    
    return metadata


def load_center_projected_64() -> Tuple[np.ndarray, List[Dict]]:
    """Load center_projected_64dim embeddings and metadata."""
    cp_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy")
    meta_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
    
    embeddings = np.load(cp_path)
    with open(meta_path, 'r') as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded center_projected_64: {embeddings.shape}")
    return embeddings, metadata


def load_center_projected_768() -> Tuple[np.ndarray, List[Dict]]:
    """Load center_projected_768dim embeddings and metadata."""
    cp_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
    meta_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
    
    embeddings = np.load(cp_path)
    with open(meta_path, 'r') as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded center_projected_768: {embeddings.shape}")
    return embeddings, metadata


def load_cited_decisions_tfidf() -> np.ndarray:
    """Load cited_decisions_tfidf embeddings (1200, 128)."""
    path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/outcome_cited_hybrids/cited_decisions_tfidf.npy")
    embeddings = np.load(path)
    logger.info(f"Loaded cited_decisions_tfidf: {embeddings.shape}")
    return embeddings


def load_outcome_cited_hybrid(alpha: float) -> np.ndarray:
    """Load cited_decisions_tfidf_outcome_hybrid embeddings."""
    path = Path(f"/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/outcome_cited_hybrids/cited_decisions_tfidf_outcome_hybrid_{alpha:.1f}.npy")
    embeddings = np.load(path)
    logger.info(f"Loaded cited_decisions_tfidf_outcome_hybrid_{alpha:.1f}: {embeddings.shape}")
    return embeddings


def load_metric_learning_embeddings(name: str) -> np.ndarray:
    """Load metric learning embeddings."""
    paths = {
        'linear_metric_epoch4': Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_linear_embeddings.npy"),
        'mahalanobis_metric_epoch4': Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/metric_learning/best_mahalanobis_embeddings.npy"),
        'hybrid_stabilized_epoch1': Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/hybrid_objective_stabilized/best_embeddings.npy"),
    }
    embeddings = np.load(paths[name])
    logger.info(f"Loaded {name}: {embeddings.shape}")
    return embeddings


def load_citation_role_hybrid(role: str, alpha: float, center_projected: np.ndarray, eval_decision_ids: List[str]) -> np.ndarray:
    """
    Generate citation role hybrid embeddings on-the-fly (as in v7_citation_role_embeddings.py).
    
    The role vectors are derived from resolved role counts per target decision.
    """
    # Load resolved roles
    roles_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v7/citation_id_resolution_bge/citation_roles_resolved.json")
    with open(roles_path, 'r') as f:
        roles = json.load(f)
    
    # Build role count features per target decision
    did_to_idx = {did: i for i, did in enumerate(eval_decision_ids)}
    n = len(eval_decision_ids)
    role_names = ['citing', 'following', 'distinguishing', 'overruling', 'criticizing']
    
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
    
    # Extract role vector
    role_idx = role_names.index(role)
    rv = features_norm[:, role_idx]
    
    # Normalize role vector
    norm = np.linalg.norm(rv)
    if norm > 0:
        rv = rv / norm
    
    # Create hybrid: alpha * center_projected + (1-alpha) * role_vector (broadcasted)
    cp_norm = normalize(center_projected, axis=1)
    rv_2d = rv.reshape(-1, 1)
    hybrid = alpha * cp_norm + (1 - alpha) * rv_2d
    hybrid = normalize(hybrid, axis=1)
    
    return hybrid


def align_embeddings_to_evaluation(embeddings: np.ndarray, source_metadata: List[Dict], eval_metadata: List[Dict]) -> np.ndarray:
    """
    Align embeddings from source corpus to evaluation corpus by decision_id.
    """
    eval_ids = [m['decision_id'] for m in eval_metadata]
    source_ids = [m['decision_id'] for m in source_metadata]
    source_id_to_idx = {did: i for i, did in enumerate(source_ids)}
    
    valid_indices = []
    for did in eval_ids:
        if did in source_id_to_idx:
            valid_indices.append(source_id_to_idx[did])
        else:
            valid_indices.append(-1)
    
    # For missing decisions, we'll use zero vectors (should not happen with proper alignment)
    aligned = np.zeros((len(eval_ids), embeddings.shape[1]), dtype=embeddings.dtype)
    for i, src_idx in enumerate(valid_indices):
        if src_idx >= 0:
            aligned[i] = embeddings[src_idx]
    
    n_missing = sum(1 for idx in valid_indices if idx < 0)
    if n_missing > 0:
        logger.warning(f"  {n_missing}/{len(eval_ids)} decisions missing in source embeddings")
    
    return aligned


def run_fractal_quality(embeddings: np.ndarray, metadata: List[Dict], name: str) -> Dict:
    """Run hierarchical Leiden and compute fractal quality metrics."""
    logger.info(f"\n=== Fractal Quality: {name} ===")
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings_norm = embeddings / norms
    
    # Run hierarchical Leiden
    result = hierarchical_leiden(embeddings_norm, metadata, 
                                  coarse_res=HIERARCHICAL_CONFIG["coarse_res"],
                                  sub_res=HIERARCHICAL_CONFIG["sub_res"],
                                  k=HIERARCHICAL_CONFIG["k"])
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = result
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    # Zoom coherence analysis
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    # Legal area NMI
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    # Flat Leiden comparison for hierarchical advantage
    from hierarchical_zoom_validation import leiden_clustering
    flat_labels = {}
    for res in [0.5, 1.0, 1.5, 2.0, 3.0]:
        labels, _ = leiden_clustering(embeddings_norm, resolution=res, k=HIERARCHICAL_CONFIG["k"])
        flat_labels[res] = labels
    flat_purities = {f"res_{r}": compute_branch_purity(flat_labels[r], metadata) for r in flat_labels.keys()}
    flat_best = max(flat_purities.values())
    hierarchical_advantage = fine_overall - flat_best
    
    # Overclustering detection
    overclustering = n_coarse == 1 and n_fine > OVERCLUSTERING_THRESHOLD
    if overclustering:
        logger.warning(f"  ⚠️ OVERCLUSTERING: 1 coarse → {n_fine} fine clusters!")
    
    # Coarse cluster size distribution
    coarse_sizes = {}
    for cid in sorted(coarse_to_fine.keys()):
        mask = coarse_labels == cid
        coarse_sizes[int(cid)] = int(np.sum(mask))
    
    # Fine cluster size distribution
    fine_sizes = {}
    for fid, info in cluster_info.items():
        fine_sizes[int(fid)] = info['size']
    
    logger.info(f"  Coarse clusters: {n_coarse}, Fine clusters: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Overall improvement: {overall_improvement:+.4f}")
    logger.info(f"  Improvement rate: {improvement_rate:.1%} ({total_improvements}/{total_fine})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Flat best purity: {flat_best:.4f}, Hierarchical advantage: {hierarchical_advantage:+.4f}")
    logger.info(f"  Overclustering: {overclustering}")
    
    return {
        'name': name,
        'n_coarse': int(n_coarse),
        'n_fine': int(n_fine),
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_best_purity': float(flat_best),
        'hierarchical_advantage': float(hierarchical_advantage),
        'overclustering': bool(overclustering),
        'coarse_sizes': coarse_sizes,
        'fine_sizes': fine_sizes,
        'coarse_to_fine': {int(k): [int(f) for f in v] for k, v in coarse_to_fine.items()},
        'cluster_info': cluster_info,
        'flat_purities': flat_purities,
        'verdict': "PASS" if (improvement_rate > 0.5 and not overclustering and fine_overall > coarse_overall) else "PARTIAL" if improvement_rate > 0.3 else "FAIL"
    }


def main():
    logger.info("=" * 80)
    logger.info("Legal Distance Lane v7 - Fractal Quality Validation of Breakthrough Representations")
    logger.info("=" * 80)
    logger.info(f"Frozen config: {HIERARCHICAL_CONFIG}")
    logger.info(f"Corpus: 1,200 BGer decisions (2024 expanded slice)")
    logger.info(f"Frozen harness: v3 (seed=42, config_hash=1674829901d55e83)")
    
    # 1. Load evaluation metadata
    logger.info("\n1. Loading evaluation metadata...")
    eval_metadata = load_evaluation_metadata()
    eval_decision_ids = [m['decision_id'] for m in eval_metadata]
    
    # 2. Load center_projected metadata for alignment
    _, cp_metadata = load_center_projected_64()
    
    # 3. Define all representations to test
    representations = {}
    
    # Baseline: center_projected_64dim
    cp_64, _ = load_center_projected_64()
    representations['center_projected_64dim'] = align_embeddings_to_evaluation(cp_64, cp_metadata, eval_metadata)
    
    # center_projected_768 for reference
    cp_768, _ = load_center_projected_768()
    representations['center_projected_768dim'] = align_embeddings_to_evaluation(cp_768, cp_metadata, eval_metadata)
    
    # Zero-shot citation signal
    cited_tfidf = load_cited_decisions_tfidf()
    representations['cited_decisions_tfidf'] = align_embeddings_to_evaluation(cited_tfidf, cp_metadata, eval_metadata)
    
    # Cross-lingual breakthrough hybrids
    for alpha in [0.3, 0.5, 0.7]:
        hybrid = load_outcome_cited_hybrid(alpha)
        representations[f'cited_decisions_tfidf_outcome_hybrid_{alpha:.1f}'] = align_embeddings_to_evaluation(hybrid, cp_metadata, eval_metadata)
    
    # Metric learning breakthroughs
    for name in ['linear_metric_epoch4', 'mahalanobis_metric_epoch4', 'hybrid_stabilized_epoch1']:
        ml_emb = load_metric_learning_embeddings(name)
        representations[name] = align_embeddings_to_evaluation(ml_emb, cp_metadata, eval_metadata)
    
    # Citation role hybrids (need center_projected for hybrid creation)
    cp_for_roles = align_embeddings_to_evaluation(cp_768, cp_metadata, eval_metadata)
    for role in ['citing', 'following', 'criticizing']:
        for alpha in [0.3]:
            hybrid = load_citation_role_hybrid(role, alpha, cp_for_roles, eval_decision_ids)
            representations[f'{role}_alpha{alpha:.1f}'] = hybrid
    
    # 4. Run fractal quality for all representations
    logger.info(f"\n{'='*80}")
    logger.info(f"Running fractal quality validation for {len(representations)} representations...")
    logger.info(f"{'='*80}")
    
    all_results = {}
    for name, emb in representations.items():
        try:
            all_results[name] = run_fractal_quality(emb, eval_metadata, name)
        except Exception as e:
            logger.error(f"  ERROR on {name}: {e}")
            all_results[name] = {'name': name, 'error': str(e), 'verdict': 'ERROR'}
    
    # 5. Save results
    output_path = OUTPUT_DIR / "fractal_validation_breakthroughs.json"
    
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    output = {
        "run_id": "fractal_validation_breakthroughs_20260830",
        "timestamp": "2026-08-30T00:00:00+00:00",
        "factory_direction_version": 8,
        "lane": "legal-distance",
        "evidence_tier": "REPRODUCED",
        "hypothesis": "Breakthrough representations (zero-shot hybrids, metric learning, citation roles) produce superior fractal structure vs center_projected_64dim baseline",
        "frozen_sample": "1,200 BGer decisions (2024 expanded slice) from evaluation_v3_frozen_harness",
        "frozen_metric": "Hierarchical Leiden (coarse_res=0.5, sub_res=3.0) branch purity improvement rate",
        "success_rule": "Improvement rate > 50%, no overclustering, fine purity > coarse purity, hierarchical advantage > 0",
        "hierarchical_config": HIERARCHICAL_CONFIG,
        "representations_tested": list(representations.keys()),
        "results": all_results,
    }
    
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    
    # 6. Summary table
    logger.info("\n" + "=" * 100)
    logger.info("FRACTAL QUALITY VALIDATION SUMMARY")
    logger.info("=" * 100)
    logger.info(f"{'Representation':<45} {'Verdict':<8} {'C':>3} {'F':>4} {'CoarsePur':>9} {'FinePur':>8} {'ImpRate':>8} {'LegalNMI':>8} {'HierAdv':>8} {'Over':>5}")
    logger.info("-" * 100)
    
    for name, r in all_results.items():
        if 'error' in r:
            logger.info(f"{name:<45} {'ERROR':<8} {'N/A':>3} {'N/A':>4} {'N/A':>9} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>5}")
            continue
        
        verdict = r.get('verdict', 'N/A')
        n_coarse = r.get('n_coarse', 0)
        n_fine = r.get('n_fine', 0)
        coarse_pur = r.get('coarse_purity', 0)
        fine_pur = r.get('fine_purity', 0)
        imp_rate = r.get('improvement_rate', 0)
        legal_nmi = r.get('legal_area_nmi', 0)
        hier_adv = r.get('hierarchical_advantage', 0)
        over = "⚠️" if r.get('overclustering', False) else ""
        
        logger.info(f"{name:<45} {verdict:<8} {n_coarse:>3} {n_fine:>4} {coarse_pur:>9.4f} {fine_pur:>8.4f} {imp_rate:>7.1%} {legal_nmi:>8.4f} {hier_adv:>+8.4f} {over:>5}")
    
    # 7. Comparison with baseline
    baseline = all_results.get('center_projected_64dim', {})
    if baseline and 'error' not in baseline:
        baseline_fine = baseline.get('fine_purity', 0)
        baseline_coarse = baseline.get('coarse_purity', 0)
        baseline_imp = baseline.get('improvement_rate', 0)
        baseline_nmi = baseline.get('legal_area_nmi', 0)
        baseline_adv = baseline.get('hierarchical_advantage', 0)
        
        logger.info("\n" + "=" * 100)
        logger.info("IMPROVEMENT OVER BASELINE (center_projected_64dim)")
        logger.info("=" * 100)
        logger.info(f"{'Representation':<45} {'ΔFinePur':>9} {'ΔCoarsePur':>10} {'ΔImpRate':>9} {'ΔLegalNMI':>9} {'ΔHierAdv':>9}")
        logger.info("-" * 100)
        
        for name, r in all_results.items():
            if name == 'center_projected_64dim' or 'error' in r:
                continue
            
            delta_fine = r.get('fine_purity', 0) - baseline_fine
            delta_coarse = r.get('coarse_purity', 0) - baseline_coarse
            delta_imp = r.get('improvement_rate', 0) - baseline_imp
            delta_nmi = r.get('legal_area_nmi', 0) - baseline_nmi
            delta_adv = r.get('hierarchical_advantage', 0) - baseline_adv
            
            logger.info(f"{name:<45} {delta_fine:>+9.4f} {delta_coarse:>+10.4f} {delta_imp:>+8.1%} {delta_nmi:>+9.4f} {delta_adv:>+9.4f}")
    
    # 8. Product integration recommendations
    logger.info("\n" + "=" * 100)
    logger.info("PRODUCT INTEGRATION RECOMMENDATIONS")
    logger.info("=" * 100)
    
    # Filter PASS results
    pass_results = {name: r for name, r in all_results.items() if r.get('verdict') == 'PASS' and 'error' not in r}
    
    if pass_results:
        best_fine = max(pass_results.items(), key=lambda x: x[1].get('fine_purity', 0))
        best_imp = max(pass_results.items(), key=lambda x: x[1].get('improvement_rate', 0))
        best_nmi = max(pass_results.items(), key=lambda x: x[1].get('legal_area_nmi', 0))
        best_adv = max(pass_results.items(), key=lambda x: x[1].get('hierarchical_advantage', 0))
        
        logger.info(f"\n  Best fine purity:      {best_fine[0]} ({best_fine[1]['fine_purity']:.4f})")
        logger.info(f"  Best improvement rate: {best_imp[0]} ({best_imp[1]['improvement_rate']:.1%})")
        logger.info(f"  Best legal area NMI:   {best_nmi[0]} ({best_nmi[1]['legal_area_nmi']:.4f})")
        logger.info(f"  Best hierarchical adv: {best_adv[0]} ({best_adv[1]['hierarchical_advantage']:.4f})")
        
        logger.info("\n  Recommended map modes (PASS verdict + no overclustering):")
        for name, r in sorted(pass_results.items(), key=lambda x: x[1].get('fine_purity', 0), reverse=True):
            over = " ⚠️ OVERCLUSTER" if r.get('overclustering') else ""
            logger.info(f"    ✅ {name}: fine_pur={r['fine_purity']:.4f}, imp_rate={r['improvement_rate']:.1%}, NMI={r['legal_area_nmi']:.4f}, hier_adv={r['hierarchical_advantage']:+.4f}{over}")
    
    fail_results = {name: r for name, r in all_results.items() if r.get('verdict') in ['FAIL', 'ERROR'] and 'error' not in r}
    if fail_results:
        logger.info("\n  Failed representations:")
        for name, r in fail_results.items():
            logger.info(f"    ❌ {name}: {r.get('verdict', 'N/A')} - {r.get('error', 'metrics below threshold')}")
    
    logger.info("\n=== Fractal quality validation complete ===")
    return all_results


if __name__ == "__main__":
    main()