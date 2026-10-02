#!/usr/bin/env python3
"""
Run constrained hierarchical Leiden on 144k dense embeddings (2000-2021)
using the validated fixed config from 28k checkpoint.

Validated config: coarse_res=0.5, base_sub_res=2.0, min_cluster_size=20, 
max_subclusters=20, adaptive_sub_res=False

This validates the scale extrapolation model predicting hier_impr ~0.67 at 174k.
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors
import warnings
warnings.filterwarnings('ignore')


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


def load_dense_embeddings_and_metadata(embedding_dir: str, years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load embeddings and metadata for specified years."""
    all_embeddings = []
    all_metadata = []
    
    for year in years:
        emb_path = os.path.join(embedding_dir, f'embeddings_{year}.npy')
        meta_path = os.path.join(embedding_dir, f'metadata_{year}.json')
        
        if not os.path.exists(emb_path):
            print(f"  Warning: {emb_path} not found, skipping")
            continue
            
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        # Metadata is a list of dicts
        if isinstance(metadata, list):
            meta_list = metadata
        else:
            meta_list = [metadata]
        
        print(f"  {year}: {embeddings.shape[0]} decisions, {len(meta_list)} metadata entries")
        all_embeddings.append(embeddings)
        all_metadata.extend(meta_list)
    
    combined_embeddings = np.vstack(all_embeddings)
    print(f"\nTotal: {combined_embeddings.shape[0]} decisions, {len(all_metadata)} metadata entries")
    return combined_embeddings, all_metadata


def constrained_hierarchical_leiden(embeddings: np.ndarray,
                                     k: int = 15,
                                     coarse_res: float = 0.5,
                                     base_sub_res: float = 2.0,
                                     min_cluster_size: int = 20,
                                     max_subclusters_per_parent: int = 20,
                                     adaptive_sub_res: bool = False) -> Dict:
    """
    Run constrained hierarchical Leiden with FIXED config (validated at 28k).
    """
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    # Level 1: Coarse clustering (domains)
    partition = la.find_partition(g, la.RBConfigurationVertexPartition,
                                   weights='weight', resolution_parameter=coarse_res)
    coarse_labels = np.array(partition.membership)
    
    # Enforce min cluster size at coarse level
    unique, counts = np.unique(coarse_labels, return_counts=True)
    small_clusters = unique[counts < min_cluster_size]
    if len(small_clusters) > 0:
        for sc in small_clusters:
            mask = coarse_labels == sc
            if np.any(mask):
                idx = np.where(mask)[0][0]
                neighbors = g.neighbors(idx)
                for n_idx in neighbors:
                    if coarse_labels[n_idx] not in small_clusters:
                        coarse_labels[mask] = coarse_labels[n_idx]
                        break
    
    # Renumber
    unique_labels = np.unique(coarse_labels)
    label_map = {old: new for new, old in enumerate(unique_labels)}
    coarse_labels = np.array([label_map[l] for l in coarse_labels])
    n_coarse = len(unique_labels)
    
    # Level 2: Fine clustering (subdomains) - subdivide each coarse cluster
    fine_labels = np.full(n, -1, dtype=int)
    fine_label = 0
    cluster_info = {}
    
    for coarse_cluster in range(n_coarse):
        mask = coarse_labels == coarse_cluster
        indices = np.where(mask)[0]
        
        if len(indices) < min_cluster_size:
            fine_labels[mask] = fine_label
            cluster_info[f'{coarse_cluster}_{fine_label}'] = {
                'coarse_id': coarse_cluster,
                'sub_id': 0,
                'size': len(indices),
                'too_small': True,
                'sub_res_used': base_sub_res,
                'is_remainder': False
            }
            fine_label += 1
            continue
        
        # Induced subgraph
        subg = g.induced_subgraph(indices.tolist())
        
        # Fixed sub-resolution (not adaptive)
        sub_resolution = base_sub_res
        
        try:
            sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                               weights='weight', resolution_parameter=sub_resolution)
            sub_labels = np.array(sub_partition.membership)
            n_subclusters = len(np.unique(sub_labels))
            
            # Cap subclusters per parent
            if n_subclusters > max_subclusters_per_parent:
                sub_unique, sub_counts = np.unique(sub_labels, return_counts=True)
                sorted_idx = np.argsort(sub_counts)[::-1]
                keep = sub_unique[sorted_idx[:max_subclusters_per_parent]]
                for old_label in sub_unique:
                    if old_label not in keep:
                        sub_labels[sub_labels == old_label] = keep[0]
                n_subclusters = max_subclusters_per_parent
            
            if n_subclusters == 1:
                fine_labels[mask] = fine_label
                cluster_info[f'{coarse_cluster}_{fine_label}'] = {
                    'coarse_id': coarse_cluster,
                    'sub_id': 0,
                    'size': len(indices),
                    'too_small': False,
                    'sub_res_used': sub_resolution,
                    'is_remainder': False
                }
                fine_label += 1
            else:
                for j, idx in enumerate(indices):
                    fine_labels[idx] = fine_label + sub_labels[j]
                for sub_id in range(n_subclusters):
                    sub_mask = sub_labels == sub_id
                    size = int(np.sum(sub_mask))
                    cluster_info[f'{coarse_cluster}_{fine_label + sub_id}'] = {
                        'coarse_id': coarse_cluster,
                        'sub_id': sub_id,
                        'size': size,
                        'too_small': False,
                        'sub_res_used': sub_resolution,
                        'is_remainder': False
                    }
                fine_label += n_subclusters
                
        except Exception as e:
            fine_labels[mask] = fine_label
            cluster_info[f'{coarse_cluster}_{fine_label}'] = {
                'coarse_id': coarse_cluster,
                'sub_id': -1,
                'size': len(indices),
                'too_small': False,
                'sub_res_used': sub_resolution,
                'is_remainder': True,
                'error': str(e)
            }
            fine_label += 1
    
    # Renumber fine labels
    unique_fine = np.unique(fine_labels)
    fine_label_map = {old: new for new, old in enumerate(unique_fine)}
    fine_labels = np.array([fine_label_map[l] for l in fine_labels])
    
    return {
        'coarse_labels': coarse_labels,
        'fine_labels': fine_labels,
        'n_coarse': n_coarse,
        'n_fine': len(unique_fine),
        'cluster_info': cluster_info,
        'graph': g
    }


def compute_legal_purity(labels: np.ndarray, metadata: List[Dict], field: str) -> Tuple[float, Dict]:
    """Compute purity of clusters w.r.t. a legal metadata field."""
    n = len(labels)
    if n == 0:
        return 0.0, {}
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None and v != 'unknown' and v != '' for v in values]
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
        value_counts = {}
        for v in cluster_values:
            value_counts[v] = value_counts.get(v, 0) + 1
        max_count = max(value_counts.values())
        cluster_purity = max_count / len(cluster_values)
        per_cluster[int(lbl)] = {
            'purity': cluster_purity,
            'size': len(cluster_values),
            'dominant_value': max(value_counts, key=value_counts.get),
            'distribution': value_counts
        }
        total_purity += max_count
        total_size += len(cluster_values)
    
    return total_purity / total_size if total_size > 0 else 0.0, per_cluster


def compute_nesting_score(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> float:
    """Compute nesting score: fraction of fine clusters that are subsets of coarse clusters."""
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


def evaluate_hierarchical_v1(results: Dict, metadata: List[Dict]) -> Dict:
    """
    Evaluate using the FROZEN hierarchical_v1 protocol:
    - nesting_score >= 0.99
    - fine_branch_purity > 0.5 (legal_structure_branch)
    - improvement_rate > 0.5 (zoom_coherence)
    - singleton_fraction < 0.01
    """
    coarse_labels = results['coarse_labels']
    fine_labels = results['fine_labels']
    n = len(coarse_labels)
    
    # Nesting
    nesting = compute_nesting_score(coarse_labels, fine_labels)
    
    # Legal purities
    coarse_branch_purity, _ = compute_legal_purity(coarse_labels, metadata, 'branch')
    coarse_area_purity, _ = compute_legal_purity(coarse_labels, metadata, 'legal_area')
    fine_branch_purity, _ = compute_legal_purity(fine_labels, metadata, 'branch')
    fine_area_purity, _ = compute_legal_purity(fine_labels, metadata, 'legal_area')
    
    # Branch purity delta (improvement)
    branch_purity_delta = fine_branch_purity - coarse_branch_purity
    area_purity_delta = fine_area_purity - coarse_area_purity
    
    # Zoom coherence: fraction of coarse clusters where fine children improve purity
    parent_details = {}
    improvements = []
    for coarse_id in np.unique(coarse_labels):
        mask = coarse_labels == coarse_id
        fine_children = fine_labels[mask]
        child_clusters = np.unique(fine_children)
        
        if len(child_clusters) <= 1:
            parent_details[int(coarse_id)] = {
                'coarse_purity': 0,
                'mean_child_purity': 0,
                'improvement': 0,
                'n_children': len(child_clusters)
            }
            continue
        
        # Compute coarse purity for this parent
        parent_metadata = [metadata[i] for i in np.where(mask)[0]]
        coarse_vals = [m.get('branch') for m in parent_metadata]
        coarse_valid = [v for v in coarse_vals if v is not None and v != 'unknown' and v != '']
        if coarse_valid:
            from collections import Counter
            coarse_counts = Counter(coarse_valid)
            coarse_purity = max(coarse_counts.values()) / len(coarse_valid)
        else:
            coarse_purity = 0
        
        # Compute mean child purity
        child_purities = []
        for child_id in child_clusters:
            child_mask = fine_labels == child_id
            child_metadata = [metadata[i] for i in np.where(child_mask)[0]]
            child_vals = [m.get('branch') for m in child_metadata]
            child_valid = [v for v in child_vals if v is not None and v != 'unknown' and v != '']
            if child_valid:
                child_counts = Counter(child_valid)
                child_purity = max(child_counts.values()) / len(child_valid)
                child_purities.append(child_purity)
        
        mean_child_purity = np.mean(child_purities) if child_purities else 0
        improvement = mean_child_purity - coarse_purity
        
        parent_details[int(coarse_id)] = {
            'coarse_purity': coarse_purity,
            'mean_child_purity': mean_child_purity,
            'improvement': improvement,
            'n_children': len(child_clusters)
        }
        improvements.append(improvement)
    
    improvement_rate = np.mean([1 for imp in improvements if imp > 0]) if improvements else 0
    mean_improvement = np.mean(improvements) if improvements else 0
    
    # Fragmentation
    unique_fine, counts_fine = np.unique(fine_labels, return_counts=True)
    singleton_fraction = np.sum(counts_fine == 1) / n
    median_cluster_size = np.median(counts_fine)
    
    # v26 assessment (frozen rule)
    v26_pass = (nesting >= 0.99 and 
                fine_branch_purity > 0.5 and
                improvement_rate > 0.5 and
                singleton_fraction < 0.01)
    
    return {
        'nesting': nesting,
        'coarse_branch_purity': coarse_branch_purity,
        'coarse_area_purity': coarse_area_purity,
        'fine_branch_purity': fine_branch_purity,
        'fine_area_purity': fine_area_purity,
        'branch_purity_delta': branch_purity_delta,
        'area_purity_delta': area_purity_delta,
        'improvement_rate': improvement_rate,
        'mean_improvement': mean_improvement,
        'singleton_fraction': singleton_fraction,
        'median_cluster_size': float(median_cluster_size),
        'n_fine_clusters': len(unique_fine),
        'n_coarse_clusters': len(np.unique(coarse_labels)),
        'parent_details': parent_details,
        'v26_pass': v26_pass,
        'hierarchical_v1_pass': v26_pass  # Same criteria
    }


def main():
    print("="*70)
    print("RUNNING CONSTRAINED HIERARCHICAL LEIDEN ON 144K DENSE EMBEDDINGS")
    print("Years: 2000-2021 (22 years)")
    print("Config: coarse_res=0.5, base_sub_res=2.0, min_cluster_size=20,")
    print("        max_subclusters=20, adaptive_sub_res=False")
    print("="*70)
    
    embedding_dir = '/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints'
    years = list(range(2000, 2022))  # 2000-2021 inclusive
    
    embeddings, metadata = load_dense_embeddings_and_metadata(embedding_dir, years)
    
    print(f"\nRunning constrained hierarchical Leiden...")
    results = constrained_hierarchical_leiden(
        embeddings,
        k=15,
        coarse_res=0.5,
        base_sub_res=2.0,
        min_cluster_size=20,
        max_subclusters_per_parent=20,
        adaptive_sub_res=False
    )
    
    print(f"  Coarse clusters: {results['n_coarse']}")
    print(f"  Fine clusters: {results['n_fine']}")
    
    print(f"\nEvaluating with frozen hierarchical_v1 protocol...")
    eval_results = evaluate_hierarchical_v1(results, metadata)
    
    print(f"\n{'='*70}")
    print("HIERARCHICAL_V1 PROTOCOL RESULTS (144k dense embeddings)")
    print(f"{'='*70}")
    print(f"  Nesting score:           {eval_results['nesting']:.6f} (threshold: >=0.99)")
    print(f"  Coarse branch purity:    {eval_results['coarse_branch_purity']:.4f}")
    print(f"  Fine branch purity:      {eval_results['fine_branch_purity']:.4f} (threshold: >0.5)")
    print(f"  Branch purity delta:     {eval_results['branch_purity_delta']:.4f}")
    print(f"  Coarse area purity:      {eval_results['coarse_area_purity']:.4f}")
    print(f"  Fine area purity:        {eval_results['fine_area_purity']:.4f}")
    print(f"  Area purity delta:       {eval_results['area_purity_delta']:.4f}")
    print(f"  Improvement rate:        {eval_results['improvement_rate']:.4f} (threshold: >0.5)")
    print(f"  Mean improvement:        {eval_results['mean_improvement']:.4f}")
    print(f"  Singleton fraction:      {eval_results['singleton_fraction']:.6f} (threshold: <0.01)")
    print(f"  Median cluster size:     {eval_results['median_cluster_size']:.1f}")
    print(f"  Fine clusters:           {eval_results['n_fine_clusters']}")
    print(f"  Coarse clusters:         {eval_results['n_coarse_clusters']}")
    print(f"  v26 PASS:                {eval_results['v26_pass']}")
    print(f"  hierarchical_v1 PASS:    {eval_results['hierarchical_v1_pass']}")
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/144k_dense_validation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full results
    full_results = {
        'run_id': 'constrained_hierarchical_144k_dense_20261002',
        'timestamp': '2026-10-02',
        'sample_size': int(embeddings.shape[0]),
        'years': years,
        'config': {
            'coarse_res': 0.5,
            'base_sub_res': 2.0,
            'min_cluster_size': 20,
            'max_subclusters_per_parent': 20,
            'adaptive_sub_res': False,
            'k': 15
        },
        'hierarchical_results': {
            'coarse_labels': results['coarse_labels'].tolist(),
            'fine_labels': results['fine_labels'].tolist(),
            'n_coarse': results['n_coarse'],
            'n_fine': results['n_fine'],
            'cluster_info': results['cluster_info']
        },
        'evaluation': eval_results
    }
    
    with open(output_dir / 'constrained_hierarchical_144k_dense_results.json', 'w') as f:
        json.dump(full_results, f, indent=2)
    
    # Save summary
    summary = {
        'run_id': 'constrained_hierarchical_144k_dense_20261002',
        'sample_size': int(embeddings.shape[0]),
        'config': {
            'coarse_res': 0.5,
            'base_sub_res': 2.0,
            'min_cluster_size': 20,
            'max_subclusters_per_parent': 20,
            'adaptive_sub_res': False
        },
        'metrics': {
            'nesting': eval_results['nesting'],
            'coarse_branch_purity': eval_results['coarse_branch_purity'],
            'fine_branch_purity': eval_results['fine_branch_purity'],
            'branch_purity_delta': eval_results['branch_purity_delta'],
            'coarse_area_purity': eval_results['coarse_area_purity'],
            'fine_area_purity': eval_results['fine_area_purity'],
            'area_purity_delta': eval_results['area_purity_delta'],
            'improvement_rate': eval_results['improvement_rate'],
            'mean_improvement': eval_results['mean_improvement'],
            'singleton_fraction': eval_results['singleton_fraction'],
            'median_cluster_size': eval_results['median_cluster_size'],
            'n_fine_clusters': eval_results['n_fine_clusters'],
            'n_coarse_clusters': eval_results['n_coarse_clusters'],
            'v26_pass': eval_results['v26_pass'],
            'hierarchical_v1_pass': eval_results['hierarchical_v1_pass']
        }
    }
    
    with open(output_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to {output_dir}")
    
    # Scale extrapolation comparison
    print(f"\n{'='*70}")
    print("SCALE EXTRAPOLATION VALIDATION")
    print(f"{'='*70}")
    print(f"  28k checkpoint (2000-2005): hier_impr=0.667, singleton=0.0, fine_branch_purity=0.976")
    print(f"  100k checkpoint (2000-2015): hier_impr=0.474, singleton=0.0016, fine_branch_purity=0.986")
    print(f"  144k current (2000-2021):    hier_impr={eval_results['improvement_rate']:.3f}, singleton={eval_results['singleton_fraction']:.4f}, fine_branch_purity={eval_results['fine_branch_purity']:.4f}")
    print(f"  174k predicted:              hier_impr=0.50-0.70, singleton=0.0, fine_branch_purity=0.95-0.97")
    
    return full_results, eval_results


if __name__ == '__main__':
    main()