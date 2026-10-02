#!/usr/bin/env python3
"""
Threshold Calibration for Multi-Level Protocol at 174k TF-IDF.

This script calibrates the multi-level recursive purity-aware protocol thresholds
to achieve full protocol PASS on all 5 TF-IDF modes.

Calibration targets based on cycle_20261002_multi_level_tfidf_174k_report.md:
1. cited_decisions_tfidf: Level 1 branch_purity=0.39 < 0.5 (only 4 coarse clusters)
   → Increase Level 1 resolution from 0.5 to 0.75/1.0 to get 10-15 domain clusters
2. regeste modes (4 variants): Level 2 area_purity≈0.13 < 0.15
   → Relax Level 2 area_purity_stop from 0.5 to 0.4 (lowers effective threshold to ~0.12)

Protocol config (from report):
- Level 0: res=0.1, min_size=1, branch_stop=NA, area_stop=NA (corpus level)
- Level 1: res=0.5, min_size=20, branch_stop=0.8, area_stop=0.4 (domains)
- Level 2: res=1.5, min_size=10, branch_stop=0.85, area_stop=0.5 (subdomains)
- Level 3: res=3.0, min_size=5, branch_stop=0.9, area_stop=0.6 (microclusters)
- Level 4: res=5.0, min_size=3, branch_stop=0.95, area_stop=0.7 (decisions)

Threshold checks (protocol):
- Level 1 branch_purity > 0.5
- Level 2 area_purity > 0.15
- Level 3 area_purity > 0.2
- Some subdivision at each level
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone
import sys
import warnings
warnings.filterwarnings('ignore')

import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/multi_level_calibration_174k_tfidf")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Modes to test
MODES = [
    "cited_decisions_tfidf",
    "full_text_tfidf_light",
    "regeste_full_text_hybrid_0.5",
    "regeste_full_text_hybrid_0.7",
    "regeste_tfidf",
]

K = 15


def load_metadata():
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata: {len(metadata)} decisions")
    return metadata


def load_embeddings(mode):
    emb_path = EMBEDDINGS_DIR / f"{mode}.npy"
    embeddings = np.load(emb_path)
    logger.info(f"  Loaded {mode}: {embeddings.shape}")
    return embeddings


def build_knn_graph(embeddings: np.ndarray, k: int = 15, metric: str = 'cosine') -> ig.Graph:
    n = embeddings.shape[0]
    nbrs = NearestNeighbors(n_neighbors=min(k+1, n), metric=metric, n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    indices = indices[:, 1:]
    distances = distances[:, 1:]
    
    if metric == 'cosine':
        weights = 1.0 - distances
    else:
        weights = 1.0 / (1.0 + distances)
    
    edges = []
    edge_weights = []
    for i in range(n):
        for j, w in zip(indices[i], weights[i]):
            if w > 0:
                edges.append((i, int(j)))
                edge_weights.append(float(w))
    
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = edge_weights
    return g


def compute_cluster_purity(cluster_indices: np.ndarray, metadata: list, field: str) -> float:
    cluster_metadata = [metadata[i] for i in cluster_indices]
    values = [m.get(field) for m in cluster_metadata]
    valid_values = [v for v in values if v is not None and v != 'unknown']
    if not valid_values:
        return 1.0
    value_counts = Counter(valid_values)
    max_count = max(value_counts.values())
    return max_count / len(valid_values)


def compute_legal_purity_valid_only(labels: np.ndarray, metadata: list, field: str) -> tuple:
    n = len(labels)
    if n == 0:
        return 0.0, {}
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None and v != 'unknown' for v in values]
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


def compute_nesting_score(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> float:
    n = len(labels_coarse)
    fine_to_coarse = {}
    for i in range(n):
        fc = labels_fine[i]
        cc = labels_coarse[i]
        if fc not in fine_to_coarse:
            fine_to_coarse[fc] = {}
        fine_to_coarse[fc][cc] = fine_to_coarse[fc].get(cc, 0) + 1
    
    nested = 0
    for fc, cc_counts in fine_to_coarse.items():
        if len(cc_counts) == 1:
            nested += 1
    
    return nested / len(fine_to_coarse) if fine_to_coarse else 0.0


def purity_aware_constrained_leiden_recursive(embeddings: np.ndarray,
                                               metadata: list,
                                               level_configs: list,
                                               k: int = 15) -> tuple:
    """
    Run recursive purity-aware constrained Leiden at multiple levels.
    
    level_configs: list of dicts with keys:
        - resolution: Leiden resolution parameter
        - min_cluster_size: minimum cluster size
        - branch_purity_stop: stop subdividing if branch purity > this
        - area_purity_stop: stop subdividing if area purity > this
        - max_subclusters_per_parent: max subclusters per parent cluster
    """
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    level_labels = {}
    level_coarse_labels = {}  # Labels at each level (for nesting computation)
    stop_info_all = {}
    
    for level_idx, config in enumerate(level_configs):
        res = config['resolution']
        min_size = config['min_cluster_size']
        branch_stop = config.get('branch_purity_stop', 1.0)
        area_stop = config.get('area_purity_stop', 1.0)
        max_sub = config.get('max_subclusters_per_parent', 20)
        
        logger.info(f"  Level {level_idx}: res={res}, min_size={min_size}, branch_stop={branch_stop}, area_stop={area_stop}, max_sub={max_sub}")
        
        if level_idx == 0:
            # Level 0: Global clustering
            partition = la.find_partition(
                g, la.RBConfigurationVertexPartition,
                weights='weight', resolution_parameter=res, seed=42
            )
            current_labels = np.array(partition.membership)
            
            # Enforce min_cluster_size
            unique, counts = np.unique(current_labels, return_counts=True)
            small_clusters = unique[counts < min_size]
            if len(small_clusters) > 0:
                for sc in small_clusters:
                    mask = current_labels == sc
                    if np.any(mask):
                        idx = np.where(mask)[0][0]
                        neighbors = g.neighbors(idx)
                        for n_idx in neighbors:
                            if current_labels[n_idx] not in small_clusters:
                                current_labels[mask] = current_labels[n_idx]
                                break
            
            # Renumber
            unique_labels = np.unique(current_labels)
            label_map = {old: new for new, old in enumerate(unique_labels)}
            current_labels = np.array([label_map[l] for l in current_labels])
            
            level_labels[level_idx] = current_labels.copy()
            level_coarse_labels[level_idx] = current_labels.copy()
            
            logger.info(f"    Level {level_idx}: {len(unique_labels)} clusters")
            
        else:
            # Subsequent levels: sub-cluster within each parent cluster with purity-aware stopping
            new_labels = np.full(n, -1, dtype=int)
            next_label = 0
            stop_info = {
                'level': level_idx,
                'subdivided': [],
                'not_subdivided': [],
                'branch_purity_stop': branch_stop,
                'area_purity_stop': area_stop
            }
            
            prev_labels = level_coarse_labels[level_idx - 1]
            unique_parents = np.unique(prev_labels[prev_labels != -1])
            
            for parent_id in unique_parents:
                mask = prev_labels == parent_id
                indices = np.where(mask)[0]
                
                if len(indices) < min_size * 2:  # Too small to meaningfully sub-cluster
                    new_labels[indices] = next_label
                    stop_info['not_subdivided'].append({
                        'parent_cluster': int(parent_id),
                        'size': int(len(indices)),
                        'reason': 'too_small'
                    })
                    next_label += 1
                    continue
                
                # PURITY-AWARE STOPPING CHECK
                branch_purity = compute_cluster_purity(indices, metadata, 'branch')
                area_purity = compute_cluster_purity(indices, metadata, 'legal_area')
                
                should_stop = branch_purity > branch_stop and area_purity > area_stop
                
                if should_stop:
                    new_labels[indices] = next_label
                    stop_info['not_subdivided'].append({
                        'parent_cluster': int(parent_id),
                        'size': int(len(indices)),
                        'branch_purity': float(branch_purity),
                        'area_purity': float(area_purity),
                        'reason': 'purity_stop'
                    })
                    next_label += 1
                    continue
                
                # Subdivide
                subg = g.induced_subgraph(indices.tolist())
                try:
                    sub_partition = la.find_partition(
                        subg, la.RBConfigurationVertexPartition,
                        weights='weight', resolution_parameter=res
                    )
                    sub_labels = np.array(sub_partition.membership)
                    n_sub = len(np.unique(sub_labels))
                    
                    if n_sub > max_sub:
                        sub_unique, sub_counts = np.unique(sub_labels, return_counts=True)
                        sorted_idx = np.argsort(sub_counts)[::-1]
                        keep = sub_unique[sorted_idx[:max_sub]]
                        for old_label in sub_unique:
                            if old_label not in keep:
                                sub_labels[sub_labels == old_label] = keep[0]
                        n_sub = len(np.unique(sub_labels))
                    
                    for j, idx in enumerate(indices):
                        new_labels[idx] = next_label + sub_labels[j]
                    
                    stop_info['subdivided'].append({
                        'parent_cluster': int(parent_id),
                        'size': int(len(indices)),
                        'branch_purity': float(branch_purity),
                        'area_purity': float(area_purity),
                        'n_subclusters': int(n_sub),
                        'reason': 'subdivided'
                    })
                    next_label += n_sub
                except Exception as e:
                    logger.warning(f"    Sub-clustering failed for cluster {parent_id}: {e}")
                    new_labels[indices] = next_label
                    stop_info['not_subdivided'].append({
                        'parent_cluster': int(parent_id),
                        'size': int(len(indices)),
                        'branch_purity': float(branch_purity),
                        'area_purity': float(area_purity),
                        'reason': 'error'
                    })
                    next_label += 1
            
            # Enforce min_cluster_size on fine level (preserve nesting)
            unique, counts = np.unique(new_labels, return_counts=True)
            small_clusters = unique[counts < min_size]
            if len(small_clusters) > 0:
                for sc in small_clusters:
                    mask = new_labels == sc
                    if np.any(mask):
                        idx = np.where(mask)[0][0]
                        parent_cluster = prev_labels[idx]
                        neighbors = g.neighbors(idx)
                        for n_idx in neighbors:
                            if prev_labels[n_idx] == parent_cluster and new_labels[n_idx] not in small_clusters:
                                new_labels[mask] = new_labels[n_idx]
                                break
            
            # Renumber
            unique_labels = np.unique(new_labels)
            label_map = {old: new for new, old in enumerate(unique_labels)}
            new_labels = np.array([label_map[l] for l in new_labels])
            
            level_labels[level_idx] = new_labels
            level_coarse_labels[level_idx] = new_labels
            stop_info_all[level_idx] = stop_info
            
            logger.info(f"    Level {level_idx}: {len(unique_labels)} global clusters, "
                       f"subdivided={len(stop_info['subdivided'])}, "
                       f"not_subdivided={len(stop_info['not_subdivided'])}")
    
    return level_labels, level_coarse_labels, stop_info_all


def evaluate_multi_level_hierarchy(level_labels: dict, metadata: list) -> dict:
    """Evaluate the multi-level hierarchy against protocol checks."""
    n = len(metadata)
    levels = sorted(level_labels.keys())
    
    # Compute purities at each level
    branch_purities = {}
    area_purities = {}
    n_clusters = {}
    singleton_fractions = {}
    median_sizes = {}
    
    for level in levels:
        labels = level_labels[level]
        unique, counts = np.unique(labels[labels != -1], return_counts=True)
        
        branch_pur, _ = compute_legal_purity_valid_only(labels, metadata, 'branch')
        area_pur, _ = compute_legal_purity_valid_only(labels, metadata, 'legal_area')
        
        branch_purities[level] = float(branch_pur)
        area_purities[level] = float(area_pur)
        n_clusters[level] = int(len(unique))
        singleton_fractions[level] = float(np.sum(counts == 1) / n)
        median_sizes[level] = float(np.median(counts))
    
    # Compute nesting scores between consecutive levels
    nesting_scores = {}
    for i in range(len(levels) - 1):
        coarse_level = levels[i]
        fine_level = levels[i + 1]
        nesting = compute_nesting_score(level_labels[coarse_level], level_labels[fine_level])
        nesting_scores[f"{coarse_level}->{fine_level}"] = float(nesting)
    
    # Compute purity improvements
    branch_improvements = {}
    area_improvements = {}
    for i in range(len(levels) - 1):
        coarse_level = levels[i]
        fine_level = levels[i + 1]
        branch_improvements[f"{coarse_level}->{fine_level}"] = branch_purities[fine_level] - branch_purities[coarse_level]
        area_improvements[f"{coarse_level}->{fine_level}"] = area_purities[fine_level] - area_purities[coarse_level]
    
    # Protocol threshold checks
    checks = {}
    
    # Structural checks (all level transitions)
    checks['all_nesting_ge_0.95'] = all(v >= 0.95 for v in nesting_scores.values())
    checks['all_singleton_lt_0.01'] = all(v < 0.01 for v in singleton_fractions.values())
    checks['all_median_gt_3'] = all(v > 3 for v in median_sizes.values())
    checks['monotonic_branch_improvement'] = all(v > 0 for v in branch_improvements.values())
    checks['monotonic_area_improvement'] = all(v > 0 for v in area_improvements.values())
    
    # Threshold checks (specific levels)
    # Level 1 branch_purity > 0.5
    checks['level1_branch_gt_0.5'] = branch_purities.get(1, 0) > 0.5
    # Level 2 area_purity > 0.15
    checks['level2_area_gt_0.15'] = area_purities.get(2, 0) > 0.15
    # Level 3 area_purity > 0.2
    checks['level3_area_gt_0.2'] = area_purities.get(3, 0) > 0.2
    # Some subdivision at each level
    checks['some_subdivision'] = all(n_clusters.get(l, 0) > n_clusters.get(l-1, 0) for l in levels[1:])
    
    all_checks_pass = all(checks.values())
    
    return {
        'branch_purities': branch_purities,
        'area_purities': area_purities,
        'n_clusters': n_clusters,
        'singleton_fractions': singleton_fractions,
        'median_sizes': median_sizes,
        'nesting_scores': nesting_scores,
        'branch_improvements': branch_improvements,
        'area_improvements': area_improvements,
        'checks': checks,
        'verdict': 'PASS' if all_checks_pass else 'FAIL'
    }


def run_calibration_experiment(mode: str, level_configs: list, experiment_name: str, metadata: list):
    """Run a single calibration experiment."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Experiment: {experiment_name}")
    logger.info(f"Mode: {mode}")
    logger.info(f"{'='*70}")
    
    embeddings = load_embeddings(mode)
    n_meta = len(metadata)
    if len(embeddings) > n_meta:
        embeddings = embeddings[:n_meta]
        logger.info(f"  Truncated embeddings to {n_meta}")
    elif len(embeddings) < n_meta:
        logger.warning(f"  Embeddings ({len(embeddings)}) < metadata ({n_meta}), skipping")
        return None
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    # Run multi-level protocol
    level_labels, level_coarse_labels, stop_info_all = purity_aware_constrained_leiden_recursive(
        embeddings, metadata, level_configs, k=K
    )
    
    # Evaluate
    eval_results = evaluate_multi_level_hierarchy(level_labels, metadata)
    
    # Log results
    logger.info(f"  Verdict: {eval_results['verdict']}")
    for level in sorted(level_labels.keys()):
        logger.info(f"    Level {level}: {eval_results['n_clusters'][level]} clusters, "
                   f"branch={eval_results['branch_purities'][level]:.4f}, "
                   f"area={eval_results['area_purities'][level]:.4f}, "
                   f"singleton={eval_results['singleton_fractions'][level]:.4f}, "
                   f"median_size={eval_results['median_sizes'][level]:.1f}")
    
    for trans, nest in eval_results['nesting_scores'].items():
        logger.info(f"    Nesting {trans}: {nest:.4f}")
    
    for trans, imp in eval_results['branch_improvements'].items():
        logger.info(f"    Branch improvement {trans}: {imp:+.4f}")
    
    for trans, imp in eval_results['area_improvements'].items():
        logger.info(f"    Area improvement {trans}: {imp:+.4f}")
    
    for check, passed in eval_results['checks'].items():
        logger.info(f"    Check {check}: {'PASS' if passed else 'FAIL'}")
    
    return {
        'experiment': experiment_name,
        'mode': mode,
        'level_configs': level_configs,
        'level_labels': {str(k): v.tolist() for k, v in level_labels.items()},
        'evaluation': eval_results,
        'stop_info': stop_info_all
    }


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


def main():
    logger.info("=== Multi-Level Protocol Threshold Calibration at 174k TF-IDF ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    metadata = load_metadata()
    
    # Base configuration from the report
    base_config = [
        {'level': 0, 'resolution': 0.1, 'min_cluster_size': 1, 'branch_purity_stop': 1.0, 'area_purity_stop': 1.0, 'max_subclusters_per_parent': 1},
        {'level': 1, 'resolution': 0.5, 'min_cluster_size': 20, 'branch_purity_stop': 0.8, 'area_purity_stop': 0.4, 'max_subclusters_per_parent': 15},
        {'level': 2, 'resolution': 1.5, 'min_cluster_size': 10, 'branch_purity_stop': 0.85, 'area_purity_stop': 0.5, 'max_subclusters_per_parent': 20},
        {'level': 3, 'resolution': 3.0, 'min_cluster_size': 5, 'branch_purity_stop': 0.9, 'area_purity_stop': 0.6, 'max_subclusters_per_parent': 25},
        {'level': 4, 'resolution': 5.0, 'min_cluster_size': 3, 'branch_purity_stop': 0.95, 'area_purity_stop': 0.7, 'max_subclusters_per_parent': 10},
    ]
    
    # Calibration experiments to run
    experiments = []
    
    # Experiment 1: cited_decisions_tfidf - increase Level 1 resolution
    for res in [0.75, 1.0, 1.25]:
        config = [c.copy() for c in base_config]
        config[1]['resolution'] = res
        experiments.append({
            'name': f'cited_decisions_level1_res_{res}',
            'mode': 'cited_decisions_tfidf',
            'config': config
        })
    
    # Experiment 2: cited_decisions_tfidf - decrease Level 1 min_cluster_size
    for min_size in [10, 5]:
        config = [c.copy() for c in base_config]
        config[1]['min_cluster_size'] = min_size
        experiments.append({
            'name': f'cited_decisions_level1_minsize_{min_size}',
            'mode': 'cited_decisions_tfidf',
            'config': config
        })
    
    # Experiment 3: regeste modes - relax Level 2 area_purity_stop
    for area_stop in [0.4, 0.35, 0.3]:
        config = [c.copy() for c in base_config]
        config[2]['area_purity_stop'] = area_stop
        for mode in ['regeste_tfidf', 'regeste_full_text_hybrid_0.5', 'regeste_full_text_hybrid_0.7', 'full_text_tfidf_light']:
            experiments.append({
                'name': f'{mode}_level2_area_stop_{area_stop}',
                'mode': mode,
                'config': config
            })
    
    # Experiment 4: regeste modes - increase Level 2 resolution
    for res in [2.0, 2.5]:
        config = [c.copy() for c in base_config]
        config[2]['resolution'] = res
        for mode in ['regeste_tfidf', 'regeste_full_text_hybrid_0.5', 'regeste_full_text_hybrid_0.7', 'full_text_tfidf_light']:
            experiments.append({
                'name': f'{mode}_level2_res_{res}',
                'mode': mode,
                'config': config
            })
    
    # Experiment 5: Combined - cited_decisions Level 1 res + regeste Level 2 area_stop
    for cited_res in [0.75, 1.0]:
        for regeste_area_stop in [0.4, 0.35]:
            config = [c.copy() for c in base_config]
            config[1]['resolution'] = cited_res
            config[2]['area_purity_stop'] = regeste_area_stop
            
            # Test on all modes
            for mode in MODES:
                experiments.append({
                    'name': f'{mode}_cited_res_{cited_res}_regeste_area_{regeste_area_stop}',
                    'mode': mode,
                    'config': config
                })
    
    logger.info(f"Total experiments to run: {len(experiments)}")
    
    # Run experiments
    all_results = {}
    for exp in experiments:
        try:
            result = run_calibration_experiment(
                exp['mode'], exp['config'], exp['name'], metadata
            )
            if result:
                all_results[exp['name']] = result
        except Exception as e:
            logger.error(f"Experiment {exp['name']} failed: {e}", exc_info=True)
    
    # Save results
    output = {
        'run_id': f'multi_level_calibration_174k_tfidf_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 29,
        'hypothesis': 'Threshold calibration of multi-level recursive purity-aware protocol can achieve full PASS on all 5 TF-IDF modes at 174k scale',
        'base_config': base_config,
        'frozen_sample': f'{len(metadata)} BGer decisions (metadata_174k.json)',
        'frozen_metrics': 'Nesting >= 0.95, Singleton < 0.01, Median > 3, Monotonic purity, Level 1 branch > 0.5, Level 2 area > 0.15, Level 3 area > 0.2',
        'success_rule': 'PASS iff ALL structural checks pass AND ALL threshold checks pass',
        'results': all_results
    }
    
    output_path = OUTPUT_DIR / f"calibration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Calibration complete. Results saved to {output_path}")
    logger.info(f"Total experiments run: {len(all_results)}")
    
    # Summary
    logger.info("\n=== SUMMARY ===")
    for exp_name, result in all_results.items():
        ev = result['evaluation']
        checks_passed = sum(1 for v in ev['checks'].values() if v)
        total_checks = len(ev['checks'])
        logger.info(f"  {exp_name}: {ev['verdict']} ({checks_passed}/{total_checks} checks)")
        if ev['verdict'] == 'PASS':
            logger.info(f"    *** FULL PASS! ***")


if __name__ == "__main__":
    main()