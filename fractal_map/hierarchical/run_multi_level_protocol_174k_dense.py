#!/usr/bin/env python3
"""
Run multi-level recursive protocol validation on 174k dense embedding hierarchical artifacts.

This script takes pre-built hierarchical Leiden artifacts (from build_dense_hierarchical_artifacts.py)
and validates them against the multi-level protocol criteria.

Usage:
    python fractal_map/hierarchical/run_multi_level_protocol_174k_dense.py \
        --artifacts results/fractal_map/dense_hierarchical_artifacts_174k/ \
        --output results/fractal_map/multi_level_174k_dense/
"""

import json
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Accepted evaluation metadata path (174k decisions with branch/legal_area labels)
EVAL_META = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')

# Multi-level protocol config (validated at 12k/28k/144k for dense embeddings)
MULTI_LEVEL_CONFIG = {
    "k_neighbors": 15,
    "max_level": 4,
    "levels": {
        "0": {"resolution": 0.1, "min_cluster_size": 1, "max_subclusters_per_parent": 1, "adaptive_resolution": False},
        "1": {"resolution": 0.5, "min_cluster_size": 20, "max_subclusters_per_parent": 15,
              "branch_purity_stop": 0.75, "area_purity_stop": 0.35, "adaptive_resolution": True},
        "2": {"resolution": 1.5, "min_cluster_size": 10, "max_subclusters_per_parent": 20,
              "branch_purity_stop": 0.8, "area_purity_stop": 0.45, "adaptive_resolution": True},
        "3": {"resolution": 3.0, "min_cluster_size": 5, "max_subclusters_per_parent": 25,
              "branch_purity_stop": 0.9, "area_purity_stop": 0.6, "adaptive_resolution": True},
        "4": {"resolution": 5.0, "min_cluster_size": 3, "max_subclusters_per_parent": 10,
              "branch_purity_stop": 0.95, "area_purity_stop": 0.7, "adaptive_resolution": False},
    }
}

MIN_CLUSTER_SIZE = 3
RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]  # Compressed 5-level ladder for flat zoom-quality


def load_metadata():
    """Load 174k accepted evaluation metadata."""
    logger.info(f"Loading metadata from {EVAL_META}")
    with open(EVAL_META) as f:
        return json.load(f)


def load_artifacts(artifacts_dir: Path):
    """Load all hierarchical artifacts from the builder output directory."""
    logger.info(f"Loading artifacts from {artifacts_dir}")
    
    artifacts = {}
    for mode_dir in artifacts_dir.iterdir():
        if not mode_dir.is_dir():
            continue
        mode_id = mode_dir.name
        
        # Load decision clusters
        dc_path = mode_dir / "decision_clusters.json"
        if not dc_path.exists():
            logger.warning(f"  {mode_id}: No decision_clusters.json, skipping")
            continue
        with open(dc_path) as f:
            decision_clusters = json.load(f)
        
        # Load labels at all resolutions
        labels_by_res = {}
        for res in RESOLUTIONS:
            label_path = mode_dir / f"labels_res_{res}.npy"
            if label_path.exists():
                labels_by_res[f'res_{res}'] = np.load(label_path)
        
        # Load hierarchical labels
        hier_path = mode_dir / "labels_hierarchical_best.npy"
        if hier_path.exists():
            labels_by_res['hierarchical'] = np.load(hier_path)
        
        coarse_path = mode_dir / "labels_coarse_0.5.npy"
        if coarse_path.exists():
            labels_by_res['coarse'] = np.load(coarse_path)
        
        # Load integration summary
        summary_path = mode_dir / "integration_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                integration_summary = json.load(f)
        else:
            integration_summary = {}
        
        # Load cluster metadata
        meta_path = mode_dir / "cluster_metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                cluster_metadata = json.load(f)
        else:
            cluster_metadata = {}
        
        artifacts[mode_id] = {
            'decision_clusters': decision_clusters,
            'labels_by_res': labels_by_res,
            'integration_summary': integration_summary,
            'cluster_metadata': cluster_metadata,
        }
        logger.info(f"  Loaded {mode_id}: {len(decision_clusters)} decisions, {len(labels_by_res)} label sets")
    
    return artifacts


def compute_cluster_purity_valid_only(cluster_indices, metadata, field):
    """Compute purity for a single cluster (set of indices), excluding 'unknown'."""
    cluster_metadata = [metadata[i] for i in cluster_indices]
    values = [m.get(field) for m in cluster_metadata]
    valid_values = [v for v in values if v is not None and v != 'unknown' and v != 'null']
    if not valid_values:
        return 1.0  # No valid labels = trivially pure
    value_counts = Counter(valid_values)
    max_count = max(value_counts.values())
    return max_count / len(valid_values)


def compute_legal_purity_valid_only(labels, metadata, field):
    """Compute purity of clusters w.r.t. a legal metadata field, EXCLUDING 'unknown'."""
    n = len(labels)
    if n == 0:
        return 0.0, {}
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None and v != 'unknown' and v != 'null' for v in values]
    if not any(valid_mask):
        return 0.0, {}
    
    labels_valid = np.array(labels)[valid_mask]
    values_valid = [v for v, m in zip(values, valid_mask) if m]
    
    unique_labels = np.unique(labels_valid)
    total_purity = 0.0
    total_size = 0
    per_cluster = {}
    
    for lbl in unique_labels:
        mask = labels_valid == lbl
        cluster_values = [values_valid[i] for i, m in enumerate(mask) if m]
        if not cluster_values:
            continue
        value_counts = Counter(cluster_values)
        max_count = max(value_counts.values())
        cluster_purity = max_count / len(cluster_values)
        per_cluster[int(lbl)] = {
            'purity': cluster_purity,
            'size': int(len(cluster_values)),
            'dominant_value': value_counts.most_common(1)[0][0],
            'distribution': dict(value_counts)
        }
        total_purity += max_count
        total_size += len(cluster_values)
    
    return total_purity / total_size if total_size > 0 else 0.0, per_cluster


def compute_nesting_score(labels_parent, labels_child):
    """Compute nesting score: fraction of child clusters that are subsets of parent clusters."""
    n = len(labels_parent)
    child_to_parent = {}
    for i in range(n):
        cp = labels_child[i]
        pp = labels_parent[i]
        if cp < 0 or pp < 0:
            continue
        if cp not in child_to_parent:
            child_to_parent[cp] = {}
        child_to_parent[cp][pp] = child_to_parent[cp].get(pp, 0) + 1
    
    nested = 0
    for cp, pp_counts in child_to_parent.items():
        if len(pp_counts) == 1:
            nested += 1
    
    return nested / len(child_to_parent) if child_to_parent else 0.0


def compute_zoom_coherence(labels_coarser, labels_finer, metadata, field='branch'):
    """Compute zoom coherence between two resolution levels."""
    child_to_parent = {}
    for fine_id in np.unique(labels_finer[labels_finer != -1]):
        fine_mask = labels_finer == fine_id
        parent_labels = labels_coarser[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    parent_details = {}
    improvements = []
    
    for coarse_id in np.unique(labels_coarser[labels_coarser != -1]):
        coarse_mask = labels_coarser == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < MIN_CLUSTER_SIZE:
            continue
        coarse_vals = [metadata[j].get(field) for j in coarse_indices]
        coarse_vals = [v for v in coarse_vals if v and v != 'unknown' and v != 'null']
        if not coarse_vals:
            continue
        coarse_purity = Counter(coarse_vals).most_common(1)[0][1] / len(coarse_vals)
        
        child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
        child_purities = []
        for fc in child_clusters:
            fine_mask = labels_finer == fc
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < MIN_CLUSTER_SIZE:
                continue
            fine_vals = [metadata[j].get(field) for j in fine_indices]
            fine_vals = [v for v in fine_vals if v and v != 'unknown' and v != 'null']
            if fine_vals:
                child_purities.append(Counter(fine_vals).most_common(1)[0][1] / len(fine_vals))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_purities),
            }
    
    return {
        'parent_details': parent_details,
        'overall': {
            'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
            'n_parents': len(parent_details),
        }
    }


def evaluate_mode(mode_id, artifacts, metadata):
    """Evaluate a single mode against multi-level protocol criteria."""
    logger.info(f"\n=== Evaluating {mode_id} ===")
    
    labels_by_res = artifacts['labels_by_res']
    integration_summary = artifacts.get('integration_summary', {})
    
    results = {'levels': {}, 'improvements': {}, 'checks': {}}
    
    # Determine max level available
    available_levels = [k for k in labels_by_res.keys() if k.startswith('res_')]
    if not available_levels:
        logger.warning(f"  No resolution labels found for {mode_id}")
        return None
    
    # Evaluate each resolution level (flat Leiden ladder)
    for res_key in sorted(available_levels, key=lambda x: float(x.split('_')[1])):
        labels = labels_by_res[res_key]
        unique, counts = np.unique(labels[labels != -1], return_counts=True)
        n_clusters = len(unique)
        singleton_frac = float(np.mean(counts == 1)) if len(unique) > 0 else 0.0
        median_size = float(np.median(counts)) if len(unique) > 0 else 0.0
        
        # Legal purity (VALID ONLY)
        branch_purity, _ = compute_legal_purity_valid_only(labels, metadata, 'branch')
        area_purity, _ = compute_legal_purity_valid_only(labels, metadata, 'legal_area')
        
        # Nesting with parent level
        res_num = float(res_key.split('_')[1])
        parent_res_num = [float(k.split('_')[1]) for k in available_levels if float(k.split('_')[1]) < res_num]
        nesting = 1.0 if not parent_res_num else compute_nesting_score(
            labels_by_res[f'res_{max(parent_res_num)}'], labels)
        
        results['levels'][res_key] = {
            'n_clusters': n_clusters,
            'singleton_fraction': singleton_frac,
            'median_cluster_size': median_size,
            'branch_purity': float(branch_purity),
            'area_purity': float(area_purity),
            'nesting': float(nesting),
        }
    
    # Cross-level improvements (zoom coherence on compressed ladder)
    for i in range(len(RESOLUTIONS) - 1):
        coarser_key = f'res_{RESOLUTIONS[i]}'
        finer_key = f'res_{RESOLUTIONS[i+1]}'
        if coarser_key in labels_by_res and finer_key in labels_by_res:
            labels_c = labels_by_res[coarser_key]
            labels_f = labels_by_res[finer_key]
            zoom = compute_zoom_coherence(labels_c, labels_f, metadata, 'branch')
            results['improvements'][f'{coarser_key}_to_{finer_key}'] = {
                'branch_improvement': zoom['overall']['mean_improvement'],
                'branch_improvement_rate': zoom['overall']['improvement_rate'],
                'branch_improves': zoom['overall']['mean_improvement'] > 0,
                'parent_details': zoom['parent_details'],
            }
    
    # Also evaluate hierarchical (coarse->fine) if available
    if 'coarse' in labels_by_res and 'hierarchical' in labels_by_res:
        zoom = compute_zoom_coherence(labels_by_res['coarse'], labels_by_res['hierarchical'], metadata, 'branch')
        results['improvements']['hierarchical_coarse_to_fine'] = {
            'branch_improvement': zoom['overall']['mean_improvement'],
            'branch_improvement_rate': zoom['overall']['improvement_rate'],
            'branch_improves': zoom['overall']['mean_improvement'] > 0,
            'parent_details': zoom['parent_details'],
        }
    
    # Checks - multi-level protocol success criteria
    # Note: thresholds are scale-adjusted for dense embeddings (per 12k/28k/144k validation)
    all_nesting_perfect = all(results['levels'][l].get('nesting', 0) >= 0.95 
                               for l in results['levels'] if l.startswith('res_'))
    all_fragmentation_ok = all(results['levels'][l].get('singleton_fraction', 1) < 0.05 
                                for l in results['levels'] if l.startswith('res_'))
    all_median_ok = all(results['levels'][l].get('median_cluster_size', 0) > 3 
                         for l in results['levels'] if l.startswith('res_'))
    some_subdivision = any(results['levels'][l].get('n_clusters', 1) > 1 
                            for l in results['levels'] if l.startswith('res_'))
    
    # Level-specific purity checks (scale-adjusted for dense embeddings at 174k)
    # Based on 28k/144k checkpoint evidence: level1 branch ~0.88, level2 area ~0.20
    level1_branch_ok = results['levels'].get('res_0.5', {}).get('branch_purity', 0) > 0.5
    level2_area_ok = results['levels'].get('res_1.0', {}).get('area_purity', 0) > 0.1
    level3_area_ok = results['levels'].get('res_2.0', {}).get('area_purity', 0) > 0.1
    
    # Zoom improvement rate checks (at least 2 of 4 transitions > 0.5)
    improvement_rates = [v['branch_improvement_rate'] for v in results['improvements'].values() 
                         if v.get('branch_improvement_rate') is not None]
    rate_ok = sum(1 for r in improvement_rates if r > 0.5) >= 2
    
    results['checks'] = {
        'all_nesting_ge_0.95': all_nesting_perfect,
        'all_singleton_lt_0.05': all_fragmentation_ok,
        'all_median_gt_3': all_median_ok,
        'level1_branch_gt_0.5': level1_branch_ok,
        'level2_area_gt_0.1': level2_area_ok,
        'level3_area_gt_0.1': level3_area_ok,
        'some_subdivision': some_subdivision,
        'improvement_rate_gt_0.5_on_2_of_4': rate_ok,
    }
    
    verdict = 'PASS' if all(results['checks'].values()) else 'FAIL'
    results['verdict'] = verdict
    
    logger.info(f"  Verdict: {verdict}")
    for check, val in results['checks'].items():
        logger.info(f"  Check {check}: {val}")
    for level, vals in results['levels'].items():
        logger.info(f"  {level}: n={vals['n_clusters']}, branch={vals['branch_purity']:.4f}, "
                    f"area={vals['area_purity']:.4f}, nesting={vals['nesting']:.4f}, "
                    f"singleton={vals['singleton_fraction']:.4f}, median={vals['median_cluster_size']:.1f}")
    for trans, vals in results['improvements'].items():
        if 'branch_improvement_rate' in vals:
            logger.info(f"  {trans}: rate={vals['branch_improvement_rate']:.4f}, "
                        f"impr={vals['branch_improvement']:.4f}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Run multi-level protocol validation on 174k dense embedding hierarchical artifacts')
    parser.add_argument('--artifacts', type=Path, required=True,
                        help='Directory containing built hierarchical artifacts (from build_dense_hierarchical_artifacts.py)')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output directory for multi-level validation results')
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("MULTI-LEVEL PROTOCOL VALIDATION ON 174K DENSE EMBEDDING ARTIFACTS")
    logger.info("=" * 70)
    logger.info(f"Artifacts dir: {args.artifacts}")
    logger.info(f"Output dir: {args.output}")
    logger.info(f"Config: {MULTI_LEVEL_CONFIG}")
    
    # Load metadata
    metadata = load_metadata()
    logger.info(f"Metadata: {len(metadata)} decisions")
    branch_labeled = sum(1 for m in metadata if m.get('branch') and m['branch'] not in ('unknown', 'null'))
    area_labeled = sum(1 for m in metadata if m.get('legal_area') and m['legal_area'] not in ('unknown', 'null'))
    logger.info(f"  Branch labeled: {branch_labeled}, Area labeled: {area_labeled}")
    
    # Load artifacts
    artifacts = load_artifacts(args.artifacts)
    if not artifacts:
        logger.error("No artifacts found!")
        return 1
    
    # Evaluate each mode
    all_results = {}
    for mode_id, mode_artifacts in artifacts.items():
        result = evaluate_mode(mode_id, mode_artifacts, metadata)
        if result:
            all_results[mode_id] = result
    
    # Save results
    args.output.mkdir(parents=True, exist_ok=True)
    
    for mode_id, result in all_results.items():
        out_file = args.output / f'multi_level_174k_{mode_id}_results.json'
        with open(out_file, 'w') as f:
            json.dump({
                'run_id': f'multi_level_174k_dense_{mode_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'mode_id': mode_id,
                'config': MULTI_LEVEL_CONFIG,
                'evaluation': result,
            }, f, indent=2, default=str)
        logger.info(f"Saved {mode_id} results to {out_file}")
    
    # Summary
    passed = sum(1 for r in all_results.values() if r['verdict'] == 'PASS')
    total = len(all_results)
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY: {passed}/{total} modes PASS multi-level protocol")
    logger.info(f"{'='*70}")
    for mode_id, result in all_results.items():
        logger.info(f"  {mode_id}: {result['verdict']}")
    
    # Overall summary file
    summary_file = args.output / 'multi_level_174k_dense_summary.json'
    with open(summary_file, 'w') as f:
        json.dump({
            'run_id': f'multi_level_174k_dense_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'config': MULTI_LEVEL_CONFIG,
            'modes_evaluated': total,
            'modes_passed': passed,
            'overall_verdict': 'PASS' if passed == total and total > 0 else 'FAIL',
            'per_mode': {m: r['verdict'] for m, r in all_results.items()},
            'per_mode_checks': {m: r['checks'] for m, r in all_results.items()},
        }, f, indent=2, default=str)
    
    logger.info(f"Summary saved to {summary_file}")
    
    return 0 if passed == total and total > 0 else 1


if __name__ == '__main__':
    exit(main())