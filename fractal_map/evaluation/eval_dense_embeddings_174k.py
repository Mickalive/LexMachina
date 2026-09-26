#!/usr/bin/env python3
"""
Evaluation pipeline for dense embeddings at 174k scale.

This script is designed to run when dense embeddings become available from the legal-distance lane.
It supports:
- Year-split embeddings (loaded and combined)
- Full 174k embeddings
- Scalable hierarchical clustering (hierarchical Leiden)
- v26 success rule evaluation

The evidence-backed zoom path is dense embeddings + agglomerative clustering (PASS at 1000-scale),
but agglomerative doesn't scale to 174k. This pipeline uses hierarchical Leiden as the scalable
alternative and evaluates whether it passes the success rule on dense embeddings.
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np

try:
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph
    HAS_LEIDEN = True
except ImportError:
    HAS_LEIDEN = False
    print("WARNING: Leiden not available")

from sklearn.preprocessing import normalize

BASE = Path('/home/runner/work/LexMachina/LexMachina')
EVAL_DIR = BASE / 'results/fractal_map/zoom_quality_174k_eval'
EVAL_META = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')

RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3
K = 15


def load_metadata():
    with open(EVAL_META) as f:
        return json.load(f)


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Multi-resolution Leiden clustering."""
    if not HAS_LEIDEN:
        return None
    n = len(embeddings)
    k_actual = min(k, n - 1)
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership)


def hierarchical_leiden(embeddings, coarse_res=0.25, sub_res=2.0, k=15, seed=42):
    """
    Hierarchical Leiden: coarse global clustering, then fine within each coarse cluster.
    Guarantees nesting=1.0 by construction.
    """
    if not HAS_LEIDEN:
        return None, None
    
    n = len(embeddings)
    k_actual = min(k, n - 1)
    
    # Build kNN graph once
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    # Coarse clustering
    coarse_partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=coarse_res, seed=seed)
    coarse_labels = np.array(coarse_partition.membership)
    
    # Fine clustering within each coarse cluster
    fine_labels = np.full(n, -1, dtype=int)
    fine_cluster_offset = 0
    
    for coarse_id in np.unique(coarse_labels):
        mask = coarse_labels == coarse_id
        sub_indices = np.where(mask)[0]
        if len(sub_indices) < 2:
            fine_labels[sub_indices] = fine_cluster_offset
            fine_cluster_offset += 1
            continue
        
        sub_embeddings = embeddings[sub_indices]
        sub_k = min(k, len(sub_indices) - 1)
        
        # Build subgraph
        sub_graph = kneighbors_graph(sub_embeddings, n_neighbors=sub_k, metric='euclidean',
                                     mode='connectivity', include_self=False)
        sub_graph = sub_graph.maximum(sub_graph.T)
        sub_sources, sub_targets = sub_graph.nonzero()
        sub_weights = sub_graph.data
        sub_edges = list(zip(sub_sources.tolist(), sub_targets.tolist()))
        sg = ig.Graph()
        sg.add_vertices(sub_graph.shape[0])
        sg.add_edges(sub_edges)
        sg.es['weight'] = sub_weights.tolist()
        
        sub_partition = leidenalg.find_partition(
            sg, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=sub_res, seed=seed)
        sub_labels = np.array(sub_partition.membership)
        
        fine_labels[sub_indices] = sub_labels + fine_cluster_offset
        fine_cluster_offset += len(np.unique(sub_labels))
    
    return coarse_labels, fine_labels


def purity_per_res(labels, meta_by_idx, field, min_cluster_size=3):
    """Mean cluster purity per resolution (index space; excludes 'unknown')."""
    purities = []
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        vals = [meta_by_idx[i].get(field) for i in indices]
        vals = [v for v in vals if v and v != 'unknown']
        if vals:
            purities.append(Counter(vals).most_common(1)[0][1] / len(vals))
    return float(np.mean(purities)) if purities else 0.0


def compute_zoom_coherence(labels_coarse, labels_fine, meta_by_idx, field='branch', min_cluster_size=3):
    """Compute zoom coherence metrics between two resolution levels."""
    improvements = []
    n_parents = 0
    parent_details = {}
    
    # Build child->parent mapping (majority parent among ALL members)
    child_to_parent = {}
    for fine_id in np.unique(labels_fine[labels_fine != -1]):
        fine_mask = labels_fine == fine_id
        parent_labels = labels_coarse[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(
                Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    # For each coarse cluster, compute purity and child purities
    for coarse_id in np.unique(labels_coarse[labels_coarse != -1]):
        coarse_mask = labels_coarse == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_cluster_size:
            continue
        coarse_vals = [meta_by_idx[i].get(field) for i in coarse_indices]
        coarse_vals = [v for v in coarse_vals if v and v != 'unknown']
        if not coarse_vals:
            continue
        coarse_purity = Counter(coarse_vals).most_common(1)[0][1] / len(coarse_vals)
        
        # Find child clusters
        child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
        child_purities = []
        for fc in child_clusters:
            fine_mask = labels_fine == fc
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
                continue
            fine_vals = [meta_by_idx[i].get(field) for i in fine_indices]
            fine_vals = [v for v in fine_vals if v and v != 'unknown']
            if fine_vals:
                child_purities.append(Counter(fine_vals).most_common(1)[0][1] / len(fine_vals))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': round(float(coarse_purity), 4),
                'mean_child_purity': round(float(mean_child_purity), 4),
                'improvement': round(float(mean_child_purity - coarse_purity), 4),
                'n_children': len(child_clusters),
            }
            n_parents += 1
    
    return {
        'mean_improvement': round(float(np.mean(improvements)), 4) if improvements else None,
        'improvement_rate': round(float(sum(1 for j in improvements if j > 0) / len(improvements)), 4)
                            if improvements else None,
        'n_parents': n_parents,
        'parent_details': parent_details,
    }


def compute_nesting(labels_coarse, labels_fine):
    """Strict nesting: fraction of fine clusters whose members share ONE unique coarse parent."""
    n_strict = 0
    n_valid = 0
    for fid in np.unique(labels_fine[labels_fine != -1]):
        members = labels_coarse[labels_fine == fid]
        members = members[members != -1]
        if len(members) == 0:
            continue
        n_valid += 1
        if len(set(members.tolist())) == 1:
            n_strict += 1
    return round(n_strict / n_valid, 6) if n_valid else None


def fragmentation(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
    }


def evaluate_hierarchical(embeddings, metadata, config_name, coarse_res=0.25, sub_res=2.0):
    """Evaluate a hierarchical Leiden configuration."""
    print(f"\n=== Evaluating {config_name}: coarse_res={coarse_res}, sub_res={sub_res} ===")
    
    # Align embeddings with metadata
    n = min(len(embeddings), len(metadata))
    embeddings = embeddings[:n]
    metadata = metadata[:n]
    
    # Filter zero-norm embeddings
    norms = np.linalg.norm(embeddings, axis=1)
    valid_mask = norms > 0
    embeddings = embeddings[valid_mask]
    metadata = [m for i, m in enumerate(metadata) if valid_mask[i]]
    
    # Normalize
    embeddings = normalize(embeddings, norm='l2')
    
    print(f"  Valid embeddings: {len(embeddings)}, dim: {embeddings.shape[1]}")
    
    # Hierarchical Leiden
    coarse_labels, fine_labels = hierarchical_leiden(embeddings, coarse_res=coarse_res, sub_res=sub_res)
    if coarse_labels is None:
        return {'error': 'Leiden not available'}
    
    # Build labels_by_res for the compressed ladder
    # We need labels at 0.25, 0.5, 1.0, 2.0, 3.0
    # For hierarchical Leiden, we have coarse and fine. We can run flat Leiden at intermediate resolutions.
    labels_by_res = {
        'res_0.25': coarse_labels,
        'res_3.0': fine_labels,
    }
    
    # Run flat Leiden at intermediate resolutions
    for res in [0.5, 1.0, 2.0]:
        labels_by_res[f'res_{res}'] = leiden_clustering(embeddings, resolution=res)
    
    # Evaluate
    branch_purity = {}
    area_purity = {}
    fragmentation_metrics = {}
    
    for res in RESOLUTIONS:
        labels = labels_by_res[f'res_{res}']
        branch_purity[f'res_{res}'] = purity_per_res(labels, metadata, 'branch')
        area_purity[f'res_{res}'] = purity_per_res(labels, metadata, 'legal_area')
        fragmentation_metrics[f'res_{res}'] = fragmentation(labels)
        print(f"  res_{res}: branch={branch_purity[f'res_{res}']:.4f}, area={area_purity[f'res_{res}']:.4f}, "
              f"n_clusters={fragmentation_metrics[f'res_{res}']['n_clusters']}, "
              f"median={fragmentation_metrics[f'res_{res}']['median_size']:.1f}, "
              f"singleton={fragmentation_metrics[f'res_{res}']['singleton_fraction']:.4f}")
    
    # Zoom coherence
    zoom_branch = {}
    for i in range(len(RESOLUTIONS) - 1):
        coarser, finer = RESOLUTIONS[i], RESOLUTIONS[i + 1]
        zoom_branch[f'res_{coarser}_to_res_{finer}'] = compute_zoom_coherence(
            labels_by_res[f'res_{coarser}'], labels_by_res[f'res_{finer}'], metadata, 'branch')
        print(f"  zoom {coarser}->{finer}: rate={zoom_branch[f'res_{coarser}_to_res_{finer}']['improvement_rate']}, "
              f"improvement={zoom_branch[f'res_{coarser}_to_res_{finer}']['mean_improvement']}, "
              f"parents={zoom_branch[f'res_{coarser}_to_res_{finer}']['n_parents']}")
    
    # Nesting (using the hierarchical labels for coarse->fine, flat for others)
    nesting = {}
    # coarse (0.25) -> 0.5 (flat)
    nesting['res_0.25_to_res_0.5'] = compute_nesting(labels_by_res['res_0.25'], labels_by_res['res_0.5'])
    # 0.5 -> 1.0 (flat)
    nesting['res_0.5_to_res_1.0'] = compute_nesting(labels_by_res['res_0.5'], labels_by_res['res_1.0'])
    # 1.0 -> 2.0 (flat)
    nesting['res_1.0_to_res_2.0'] = compute_nesting(labels_by_res['res_1.0'], labels_by_res['res_2.0'])
    # 2.0 -> fine (hierarchical 3.0)
    nesting['res_2.0_to_res_3.0'] = compute_nesting(labels_by_res['res_2.0'], labels_by_res['res_3.0'])
    
    mean_nesting = np.mean([v for v in nesting.values() if v is not None])
    print(f"  Mean strict nesting: {mean_nesting:.4f}")
    
    # Per-mode checks (v25 success rule)
    b_mono = branch_purity['res_3.0'] > branch_purity['res_0.25']
    a_mono = area_purity['res_3.0'] > area_purity['res_0.25']
    rates = [v['improvement_rate'] for v in zoom_branch.values()]
    rate_ok = sum(1 for r in rates if r is not None and r > 0.5) >= 2
    mode_pass = b_mono and a_mono and rate_ok
    
    print(f"  Checks: branch_mono={b_mono}, area_mono={a_mono}, rate_ok={rate_ok} ({[f'{r:.3f}' if r else None for r in rates]})")
    print(f"  VERDICT: {'PASS' if mode_pass else 'FAIL'}")
    
    return {
        'config': config_name,
        'coarse_res': coarse_res,
        'sub_res': sub_res,
        'branch_purity': branch_purity,
        'area_purity': area_purity,
        'zoom_branch': zoom_branch,
        'nesting': nesting,
        'mean_nesting': mean_nesting,
        'fragmentation': fragmentation_metrics,
        'checks': {
            'branch_monotonic': b_mono,
            'area_monotonic': a_mono,
            'improvement_rate_gt_0.5_on_2_of_4': rate_ok,
        },
        'verdict': 'PASS' if mode_pass else 'FAIL',
        'n_decisions': len(embeddings),
        'embedding_dim': embeddings.shape[1],
    }


def main():
    parser = argparse.ArgumentParser(description='Evaluate dense embeddings at 174k scale')
    parser.add_argument('--embedding-path', type=Path, required=True, help='Path to dense embeddings .npy file')
    parser.add_argument('--config-name', type=str, default='dense_embeddings_174k', help='Config name for output')
    parser.add_argument('--coarse-res', type=float, default=0.25, help='Coarse resolution for hierarchical Leiden')
    parser.add_argument('--sub-res', type=float, default=2.0, help='Sub resolution for hierarchical Leiden')
    parser.add_argument('--output', type=Path, help='Output JSON path')
    args = parser.parse_args()
    
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load metadata
    metadata = load_metadata()
    print(f"Loaded metadata: {len(metadata)} entries")
    
    # Load embeddings
    print(f"Loading embeddings from {args.embedding_path}")
    embeddings = np.load(args.embedding_path)
    print(f"Embeddings shape: {embeddings.shape}")
    
    # Evaluate
    result = evaluate_hierarchical(embeddings, metadata, args.config_name, args.coarse_res, args.sub_res)
    
    # Save results
    output_path = args.output or EVAL_DIR / f'{args.config_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    result['timestamp'] = datetime.now(timezone.utc).isoformat()
    result['embedding_path'] = str(args.embedding_path)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")
    
    return result


if __name__ == '__main__':
    main()