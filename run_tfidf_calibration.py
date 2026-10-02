#!/usr/bin/env python3
"""
TF-IDF Multi-Level Protocol Threshold Calibration at 174k.

Fixes the two failure modes identified in the multi-level protocol validation:
1. cited_decisions_tfidf: Level 1 branch_purity = 0.39 < 0.5 (only 4 clusters at res=0.5)
   → Increase Level 1 resolution to 0.75-1.0 to produce 10-15 domain clusters
2. regeste modes (4 variants): Level 2 area_purity ≈ 0.13 < 0.15
   → Relax Level 2 area_purity_stop from 0.5→0.35, or increase resolution to 2.0
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CORE GRAPH BUILDING
# ============================================================================

def build_knn_graph(embeddings: np.ndarray, k: int = 15, metric: str = 'cosine') -> ig.Graph:
    """Build k-NN graph from embeddings for Leiden clustering."""
    n = embeddings.shape[0]
    nbrs = NearestNeighbors(n_neighbors=min(k+1, n), metric=metric, n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(n):
        for j, dist in zip(indices[i][1:], distances[i][1:]):  # skip self
            if metric == 'cosine':
                weight = 1.0 - dist  # convert distance to similarity
            else:
                weight = 1.0 / (1.0 + dist)
            if weight > 0:
                edges.append((i, j))
                weights.append(weight)
    
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights
    return g


# ============================================================================
# PURITY COMPUTATION (VALID-ONLY)
# ============================================================================

def compute_cluster_purity_valid_only(cluster_indices: np.ndarray, metadata: List[Dict], field: str) -> float:
    """Compute purity for a single cluster (set of indices), excluding 'unknown'."""
    cluster_metadata = [metadata[i] for i in cluster_indices]
    values = [m.get(field) for m in cluster_metadata]
    valid_values = [v for v in values if v is not None and v != 'unknown' and v != 'null']
    if not valid_values:
        return 1.0  # No valid labels = trivially pure
    value_counts = Counter(valid_values)
    max_count = max(value_counts.values())
    return max_count / len(valid_values)


def compute_legal_purity_valid_only(labels: np.ndarray, metadata: List[Dict], field: str) -> Tuple[float, Dict]:
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


# ============================================================================
# TOP-DOWN HIERARCHICAL CLUSTERING
# ============================================================================

def constrained_leiden_cluster(
    embeddings: np.ndarray,
    indices: np.ndarray,
    g: ig.Graph,
    resolution: float,
    min_cluster_size: int,
    max_subclusters: int,
    adaptive: bool = False
) -> np.ndarray:
    """Run constrained Leiden on a subset of nodes. Returns labels for the subset."""
    if len(indices) < 2:
        return np.zeros(len(indices), dtype=int)
    
    subg = g.induced_subgraph(indices.tolist())
    
    # Adaptive resolution based on cluster size
    if adaptive:
        size_factor = np.log10(max(len(indices), 10)) / np.log10(1000)
        resolution = resolution * max(0.5, min(2.0, size_factor))
    
    try:
        partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                       weights='weight', resolution_parameter=resolution)
        labels = np.array(partition.membership)
        n_clusters = len(np.unique(labels))
        
        # Cap subclusters
        if n_clusters > max_subclusters:
            unique, counts = np.unique(labels, return_counts=True)
            sorted_idx = np.argsort(counts)[::-1]
            keep = unique[sorted_idx[:max_subclusters]]
            for old_label in unique:
                if old_label not in keep:
                    labels[labels == old_label] = keep[0]
            n_clusters = len(np.unique(labels))
        
        # Enforce min_cluster_size by merging small clusters into largest
        unique, counts = np.unique(labels, return_counts=True)
        small = unique[counts < min_cluster_size]
        if len(small) > 0 and len(unique) > 1:
            largest = unique[np.argmax(counts)]
            for s in small:
                labels[labels == s] = largest
        
        # Renumber to 0, 1, 2, ...
        unique = np.unique(labels)
        label_map = {old: new for new, old in enumerate(unique)}
        labels = np.array([label_map[l] for l in labels])
        
        return labels
        
    except Exception:
        return np.zeros(len(indices), dtype=int)


def build_hierarchy_top_down(
    embeddings: np.ndarray,
    metadata: List[Dict],
    config: Dict,
    g: ig.Graph
) -> Dict[int, np.ndarray]:
    """Build full hierarchy top-down. Returns dict mapping level -> global labels array."""
    n = embeddings.shape[0]
    max_level = config['max_level']
    
    # Level 0: Corpus (single cluster)
    level_labels = {0: np.zeros(n, dtype=int)}
    
    # Current level's clusters: list of (global_label, indices)
    current_clusters = [(0, np.arange(n))]
    
    for level in range(1, max_level + 1):
        level_config = config['levels'].get(level, config['levels'][max(config['levels'].keys())])
        resolution = level_config['resolution']
        min_cluster_size = level_config['min_cluster_size']
        max_subclusters = level_config['max_subclusters_per_parent']
        adaptive = level_config.get('adaptive_resolution', False)
        branch_purity_stop = level_config.get('branch_purity_stop', 0.85)
        area_purity_stop = level_config.get('area_purity_stop', 0.5)
        
        # Labels for this level
        labels = np.full(n, -1, dtype=int)
        next_label = 0
        new_clusters = []
        
        for parent_label, indices in current_clusters:
            if len(indices) < 2:
                labels[indices] = next_label
                new_clusters.append((next_label, indices))
                next_label += 1
                continue
            
            # PURITY-AWARE STOPPING CHECK
            branch_purity = compute_cluster_purity_valid_only(indices, metadata, 'branch')
            area_purity = compute_cluster_purity_valid_only(indices, metadata, 'legal_area')
            
            should_stop = (branch_purity > branch_purity_stop and 
                          area_purity > area_purity_stop)
            
            if should_stop:
                # Don't subdivide - keep as single cluster
                labels[indices] = next_label
                new_clusters.append((next_label, indices))
                next_label += 1
                continue
            
            # Subdivide
            local_labels = constrained_leiden_cluster(
                embeddings, indices, g, resolution, min_cluster_size, max_subclusters, adaptive
            )
            
            # Assign global labels
            for local_label in np.unique(local_labels):
                mask = local_labels == local_label
                child_indices = indices[mask]
                labels[child_indices] = next_label
                new_clusters.append((next_label, child_indices))
                next_label += 1
        
        level_labels[level] = labels
        current_clusters = new_clusters
        print(f"  Level {level}: {len(current_clusters)} clusters")
    
    return level_labels


def get_calibration_config(mode: str) -> Dict:
    """Get calibration configuration for a specific TF-IDF mode."""
    # Base config
    base_config = {
        'k_neighbors': 15,
        'max_level': 4,
        'levels': {
            0: {  # Corpus level
                'resolution': 0.1,
                'min_cluster_size': 1,
                'max_subclusters_per_parent': 1,
                'adaptive_resolution': False
            },
            1: {  # Domains (branch-level)
                'resolution': 0.5,
                'min_cluster_size': 20,
                'max_subclusters_per_parent': 15,
                'branch_purity_stop': 0.8,
                'area_purity_stop': 0.4,
                'adaptive_resolution': True
            },
            2: {  # Subdomains (legal_area-level)
                'resolution': 1.5,
                'min_cluster_size': 10,
                'max_subclusters_per_parent': 20,
                'branch_purity_stop': 0.85,
                'area_purity_stop': 0.5,
                'adaptive_resolution': True
            },
            3: {  # Microclusters (fine-grained)
                'resolution': 3.0,
                'min_cluster_size': 5,
                'max_subclusters_per_parent': 25,
                'branch_purity_stop': 0.9,
                'area_purity_stop': 0.6,
                'adaptive_resolution': True
            },
            4: {  # Decisions (finest)
                'resolution': 5.0,
                'min_cluster_size': 3,
                'max_subclusters_per_parent': 10,
                'branch_purity_stop': 0.95,
                'area_purity_stop': 0.7,
                'adaptive_resolution': False
            }
        }
    }
    
    # Mode-specific adjustments
    if mode == 'cited_decisions_tfidf':
        # Fix: Low coarse branch purity (0.39) -> increase resolution to get more clusters
        base_config['levels'][1]['resolution'] = 0.85  # Increased from 0.5
        base_config['levels'][1]['min_cluster_size'] = 15  # Decreased from 20
        base_config['levels'][1]['max_subclusters_per_parent'] = 20
    elif mode.startswith('regeste'):
        # Fix: Level 2 area_purity ~0.13 < 0.15 -> relax area_purity_stop or increase resolution
        base_config['levels'][2]['area_purity_stop'] = 0.35  # Relaxed from 0.5
        base_config['levels'][2]['resolution'] = 2.0  # Increased from 1.5
        base_config['levels'][1]['branch_purity_stop'] = 0.75  # Slightly relaxed
        base_config['levels'][1]['area_purity_stop'] = 0.35
    
    return base_config


# ============================================================================
# EVALUATION
# ============================================================================

def compute_nesting_score(labels_parent: np.ndarray, labels_child: np.ndarray) -> float:
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


def evaluate_multi_level_hierarchy(
    level_labels: Dict[int, np.ndarray],
    metadata: List[Dict],
    max_level: int = 4
) -> Dict:
    """Evaluate multi-level hierarchy with comprehensive metrics."""
    n = len(metadata)
    results = {}
    
    for level in range(max_level + 1):
        if level not in level_labels:
            results[level] = {'error': 'Level not computed'}
            continue
            
        labels = level_labels[level]
        valid = labels >= 0
        if not np.any(valid):
            results[level] = {'error': 'No valid labels'}
            continue
        
        unique, counts = np.unique(labels[valid], return_counts=True)
        n_clusters = len(unique)
        singleton_frac = float(np.sum(counts == 1) / n)
        median_size = float(np.median(counts))
        
        # Legal purity (VALID ONLY)
        branch_purity, _ = compute_legal_purity_valid_only(labels, metadata, 'branch')
        area_purity, _ = compute_legal_purity_valid_only(labels, metadata, 'legal_area')
        
        # Nesting with parent level
        nesting = 1.0 if level == 0 else compute_nesting_score(level_labels[level-1], labels)
        
        results[level] = {
            'n_clusters': n_clusters,
            'singleton_fraction': singleton_frac,
            'median_cluster_size': median_size,
            'branch_purity': float(branch_purity),
            'area_purity': float(area_purity),
            'nesting': float(nesting),
            'size_distribution': {str(int(k)): int(v) for k, v in zip(unique, counts)}
        }
    
    # Cross-level improvements
    improvements = {}
    for level in range(1, max_level + 1):
        if level not in results or level-1 not in results:
            continue
        prev_branch = results[level-1].get('branch_purity', 0)
        curr_branch = results[level].get('branch_purity', 0)
        prev_area = results[level-1].get('area_purity', 0)
        curr_area = results[level].get('area_purity', 0)
        
        improvements[f'level_{level-1}_to_{level}'] = {
            'branch_improvement': curr_branch - prev_branch,
            'area_improvement': curr_area - prev_area,
            'branch_improves': curr_branch > prev_branch,
            'area_improves': curr_area > prev_area
        }
    
    # Overall verdict with FROZEN thresholds from the report
    all_nesting_perfect = all(results[l].get('nesting', 0) >= 0.95 for l in range(1, max_level+1) if l in results)
    all_fragmentation_ok = all(results[l].get('singleton_fraction', 1) < 0.01 for l in range(1, max_level+1) if l in results)
    all_median_ok = all(results[l].get('median_cluster_size', 0) > 3 for l in range(1, max_level+1) if l in results)
    some_subdivision = any(results[l].get('n_clusters', 1) > results[l-1].get('n_clusters', 1) for l in range(1, max_level+1) if l in results and l-1 in results)
    
    # Level-specific purity checks (frozen from the protocol)
    level1_branch_ok = results.get(1, {}).get('branch_purity', 0) > 0.5
    level2_area_ok = results.get(2, {}).get('area_purity', 0) > 0.15
    level3_area_ok = results.get(3, {}).get('area_purity', 0) > 0.2
    
    verdict = 'PASS' if (all_nesting_perfect and all_fragmentation_ok and 
                          all_median_ok and some_subdivision and
                          level1_branch_ok and level2_area_ok and level3_area_ok) else 'FAIL'
    
    return {
        'levels': results,
        'improvements': improvements,
        'checks': {
            'all_nesting_ge_0.95': all_nesting_perfect,
            'all_singleton_lt_0.01': all_fragmentation_ok,
            'all_median_gt_3': all_median_ok,
            'level1_branch_gt_0.5': level1_branch_ok,
            'level2_area_gt_0.15': level2_area_ok,
            'level3_area_gt_0.2': level3_area_ok,
            'some_subdivision': some_subdivision
        },
        'verdict': verdict
    }


# ============================================================================
# MAIN EXPERIMENT RUNNER
# ============================================================================

def run_multi_level_protocol(
    embeddings: np.ndarray,
    metadata: List[Dict],
    config: Dict
) -> Dict:
    """Run the full multi-level recursive purity-aware protocol."""
    
    print(f"\n{'='*70}")
    print(f"MULTI-LEVEL RECURSIVE PURITY-AWARE PROTOCOL")
    print(f"Shape: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dim")
    print(f"Config: max_level={config['max_level']}")
    print(f"{'='*70}")
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    max_level = config.get('max_level', 3)
    
    # Build graph once
    g = build_knn_graph(embeddings, k=config['k_neighbors'])
    print(f"Graph built: {g.vcount()} vertices, {g.ecount()} edges")
    
    # Build hierarchy top-down
    print("\nBuilding hierarchy top-down...")
    level_labels = build_hierarchy_top_down(embeddings, metadata, config, g)
    
    # Evaluate
    print("\nEvaluating multi-level hierarchy...")
    eval_results = evaluate_multi_level_hierarchy(level_labels, metadata, max_level)
    
    print(f"\n  Verdict: {eval_results['verdict']}")
    for level in range(max_level + 1):
        if level in eval_results['levels']:
            l = eval_results['levels'][level]
            print(f"  Level {level}: n_clusters={l['n_clusters']}, "
                  f"branch_purity={l['branch_purity']:.4f}, "
                  f"area_purity={l['area_purity']:.4f}, "
                  f"nesting={l['nesting']:.4f}, "
                  f"singleton={l['singleton_fraction']:.4f}, "
                  f"median_size={l['median_cluster_size']:.1f}")
    
    for key, val in eval_results['checks'].items():
        print(f"  Check {key}: {val}")
    
    return {
        'level_labels': {k: v.tolist() for k, v in level_labels.items()},
        'evaluation': eval_results,
        'config': config
    }


def load_embedding_and_metadata(mode: str) -> Tuple[np.ndarray, List[Dict]]:
    """Load TF-IDF embedding and aligned metadata for a specific mode."""
    # Load embedding
    emb_path = f'/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/{mode}.npy'
    embeddings = np.load(emb_path, mmap_mode='r')
    print(f"  Loaded {mode}: shape={embeddings.shape}")
    
    # Load metadata
    with open('/home/runner/work/LexMachina/LexMachina/results/fractal_map/multi_level_protocol_174k_tfidf/metadata_174k_aligned.json') as f:
        metadata = json.load(f)
    
    # Slice embeddings to match metadata length
    n_meta = len(metadata)
    if embeddings.shape[0] > n_meta:
        embeddings = embeddings[:n_meta]
        print(f"  Sliced embeddings to {n_meta} to match metadata")
    elif embeddings.shape[0] < n_meta:
        metadata = metadata[:embeddings.shape[0]]
        print(f"  Sliced metadata to {embeddings.shape[0]} to match embeddings")
    
    print(f"  Final: {embeddings.shape[0]} decisions, {len(metadata)} metadata entries")
    return embeddings, metadata


def main():
    """Run threshold calibration on all 5 TF-IDF modes at 174k."""
    
    modes = [
        'cited_decisions_tfidf',
        'full_text_tfidf_light',
        'regeste_tfidf',
        'regeste_full_text_hybrid_0.5',
        'regeste_full_text_hybrid_0.7'
    ]
    
    results_summary = {}
    
    for mode in modes:
        print(f"\n{'#'*70}")
        print(f"# CALIBRATION: {mode}")
        print(f"{'#'*70}")
        
        # Load data
        embeddings, metadata = load_embedding_and_metadata(mode)
        
        # Get calibration config
        config = get_calibration_config(mode)
        
        # Run protocol
        result = run_multi_level_protocol(embeddings, metadata, config)
        
        # Save results
        output_dir = Path(f'/home/runner/work/LexMachina/LexMachina/results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/{mode}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / f'multi_level_174k_{mode}_calibrated_results.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\nResults saved to {output_dir / f'multi_level_174k_{mode}_calibrated_results.json'}")
        
        results_summary[mode] = {
            'verdict': result['evaluation']['verdict'],
            'checks': result['evaluation']['checks'],
            'levels_summary': {
                level: {
                    'n_clusters': result['evaluation']['levels'][level]['n_clusters'],
                    'branch_purity': result['evaluation']['levels'][level]['branch_purity'],
                    'area_purity': result['evaluation']['levels'][level]['area_purity'],
                    'nesting': result['evaluation']['levels'][level]['nesting'],
                    'singleton_fraction': result['evaluation']['levels'][level]['singleton_fraction'],
                    'median_cluster_size': result['evaluation']['levels'][level]['median_cluster_size']
                }
                for level in range(config['max_level'] + 1) if level in result['evaluation']['levels']
            }
        }
    
    # Print summary table
    print(f"\n{'='*70}")
    print(f"CALIBRATION SUMMARY - ALL 5 TF-IDF MODES")
    print(f"{'='*70}")
    
    print(f"\n{'Mode':<40} | {'Verdict':<6} | {'L1 Branch':>8} | {'L2 Area':>8} | {'L3 Area':>8} | {'Nesting':>7} | {'Singleton':>9}")
    print(f"{'-'*40}-+-{'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*7}-+-{'-'*9}")
    
    for mode in modes:
        s = results_summary[mode]
        checks = s['checks']
        l1 = s['levels_summary'].get(1, {})
        l2 = s['levels_summary'].get(2, {})
        l3 = s['levels_summary'].get(3, {})
        
        print(f"{mode:<40} | {s['verdict']:<6} | "
              f"{l1.get('branch_purity', 0):>8.4f} | "
              f"{l2.get('area_purity', 0):>8.4f} | "
              f"{l3.get('area_purity', 0):>8.4f} | "
              f"{checks.get('all_nesting_ge_0.95', False):>7} | "
              f"{checks.get('all_singleton_lt_0.01', False):>9}")
    
    # Save summary
    summary_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/multi_level_protocol_174k_tfidf_calibrated')
    with open(summary_dir / 'calibration_summary.json', 'w') as f:
        json.dump(results_summary, f, indent=2, default=str)
    
    print(f"\nSummary saved to {summary_dir / 'calibration_summary.json'}")
    
    # Count PASS
    n_pass = sum(1 for m in modes if results_summary[m]['verdict'] == 'PASS')
    print(f"\nTotal PASS: {n_pass}/{len(modes)}")
    
    return results_summary


if __name__ == '__main__':
    main()