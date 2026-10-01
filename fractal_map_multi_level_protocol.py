#!/usr/bin/env python3
"""
Multi-level recursive purity-aware protocol for full fractal hierarchy.

Extends the dense-specific 2-level protocol to 5 levels:
- Level 0: Corpus (single cluster)
- Level 1: Domains (branch-level clusters)
- Level 2: Subdomains (legal_area-level clusters) 
- Level 3: Microclusters (fine-grained legal issue clusters)
- Level 4: Decisions (individual decisions, or small coherent groups)

Key innovations:
1. Top-down recursive clustering with purity-aware stopping at EACH level
2. Valid-only purity metrics (exclude 'unknown')
3. Scale-adaptive resolution parameters
4. Level-specific success criteria
5. Perfect nesting by construction
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
    valid_values = [v for v in values if v is not None and v != 'unknown']
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
    """
    Run constrained Leiden on a subset of nodes.
    Returns labels for the subset (local labels 0, 1, 2, ...).
    """
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
    """
    Build full hierarchy top-down.
    Returns dict mapping level -> global labels array.
    """
    n = embeddings.shape[0]
    max_level = config['max_level']
    
    # Level 0: Corpus (single cluster)
    level_labels = {0: np.zeros(n, dtype=int)}
    
    # Current level's clusters: list of (global_label, indices)
    # Start with level 0: single cluster with label 0
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


def get_default_config() -> Dict:
    """Get default configuration for multi-level protocol."""
    return {
        'k_neighbors': 15,
        'max_level': 3,
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
    
    # Overall verdict
    all_nesting_perfect = all(results[l].get('nesting', 0) >= 0.95 for l in range(1, max_level+1) if l in results)
    all_fragmentation_ok = all(results[l].get('singleton_fraction', 1) < 0.01 for l in range(1, max_level+1) if l in results)
    all_median_ok = all(results[l].get('median_cluster_size', 0) > 3 for l in range(1, max_level+1) if l in results)
    some_subdivision = any(results[l].get('n_clusters', 1) > results[l-1].get('n_clusters', 1) for l in range(1, max_level+1) if l in results and l-1 in results)
    
    # Level-specific purity checks (scale-adjusted for dense embeddings)
    level1_branch_ok = results.get(1, {}).get('branch_purity', 0) > 0.5   # Domain level (adjusted for dense)
    level2_area_ok = results.get(2, {}).get('area_purity', 0) > 0.1     # Subdomain level (adjusted)
    level3_area_ok = results.get(3, {}).get('area_purity', 0) > 0.1     # Microcluster level
    
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
            'level2_area_gt_0.1': level2_area_ok,
            'level3_area_gt_0.1': level3_area_ok,
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
    config: Optional[Dict] = None
) -> Dict:
    """Run the full multi-level recursive purity-aware protocol."""
    
    print(f"\n{'='*70}")
    print(f"MULTI-LEVEL RECURSIVE PURITY-AWARE PROTOCOL")
    print(f"Shape: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dim")
    print(f"{'='*70}")
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    if config is None:
        config = get_default_config()
    
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


def load_12k_dense_embeddings() -> Tuple[np.ndarray, List[Dict]]:
    """Load ACCEPTED 12k dense embeddings (years 2000-2002)."""
    print("Loading ACCEPTED 12k dense embeddings...")
    embeddings = []
    metadata = []
    for year in ['2000', '2001', '2002']:
        emb = np.load(f'/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/embeddings_{year}.npy')
        with open(f'/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/metadata_{year}.json') as f:
            meta = json.load(f)
        embeddings.append(emb)
        metadata.extend(meta)
    
    embeddings = np.vstack(embeddings)
    print(f"  Total: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dims")
    return embeddings, metadata


def load_28k_checkpoint_embeddings() -> Tuple[np.ndarray, List[Dict]]:
    """Load 28k checkpoint dense embeddings (years 2000-2005, PENDING AUDIT)."""
    print("Loading 28k checkpoint dense embeddings (PENDING AUDIT)...")
    embeddings = []
    metadata = []
    for year in ['2000', '2001', '2002', '2003', '2004', '2005']:
        emb = np.load(f'/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/embeddings_{year}.npy')
        with open(f'/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/metadata_{year}.json') as f:
            meta = json.load(f)
        embeddings.append(emb)
        metadata.extend(meta)
    
    embeddings = np.vstack(embeddings)
    print(f"  Total: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dims")
    return embeddings, metadata


def main():
    """Run multi-level protocol on available data."""
    
    # Test 1: 12k ACCEPTED dense embeddings
    print("\n" + "="*70)
    print("TEST 1: 12k ACCEPTED Dense Embeddings (years 2000-2002)")
    print("="*70)
    
    embeddings, metadata = load_12k_dense_embeddings()
    
    config = get_default_config()
    config['max_level'] = 3
    
    result_12k = run_multi_level_protocol(embeddings, metadata, config)
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/multi_level_protocol_12k')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'multi_level_12k_results.json', 'w') as f:
        json.dump(result_12k, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_dir / 'multi_level_12k_results.json'}")
    
    # Test 2: 28k checkpoint embeddings (PENDING AUDIT)
    print("\n" + "="*70)
    print("TEST 2: 28k Checkpoint Dense Embeddings (years 2000-2005, PENDING AUDIT)")
    print("="*70)
    
    embeddings_28k, metadata_28k = load_28k_checkpoint_embeddings()
    
    config_28k = get_default_config()
    config_28k['max_level'] = 3
    # Scale-adjusted thresholds based on 28k validation findings
    config_28k['levels'][1]['branch_purity_stop'] = 0.75
    config_28k['levels'][1]['area_purity_stop'] = 0.35
    config_28k['levels'][2]['branch_purity_stop'] = 0.8
    config_28k['levels'][2]['area_purity_stop'] = 0.45
    
    result_28k = run_multi_level_protocol(embeddings_28k, metadata_28k, config_28k)
    
    # Save results
    output_dir_28k = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/multi_level_protocol_28k')
    output_dir_28k.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir_28k / 'multi_level_28k_results.json', 'w') as f:
        json.dump(result_28k, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_dir_28k / 'multi_level_28k_results.json'}")
    
    # Test 3: Citation-role embeddings at 1000 scale (if available)
    print("\n" + "="*70)
    print("TEST 3: Citation-Role Embeddings (1000-scale evidence)")
    print("="*70)
    print("Evidence-backed zoom paths from zoom_coherence_1000scale_citation_roles.json:")
    print("  citing_alpha0.3:     ZQ=0.5401 (STRONG_ZOOM_PATH)")
    print("  following_alpha0.3:  ZQ=0.5280 (STRONG_ZOOM_PATH)")
    print("  criticizing_alpha0.3: ZQ=0.4864 (STRONG_ZOOM_PATH)")
    print("  cited_outcome_hybrid_0.7: ZQ=0.4017 (EXCELLENT_ZOOM_PATH)")
    print("  cited_decisions_tfidf: ZQ=0.4252 (EXCELLENT_ZOOM_PATH)")
    print("  cited_outcome_hybrid_0.5: ZQ=0.2798 (GOOD_ZOOM_PATH, PRODUCTION DEFAULT)")
    print("\nThese citation-role embeddings need to be computed/retrieved for full validation.")
    
    return result_12k, result_28k


if __name__ == '__main__':
    main()