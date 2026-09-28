#!/usr/bin/env python3
"""
Parameter sweep for constrained hierarchical Leiden on 12k ACCEPTED dense embeddings
(years 2000-2002). Optimizes for 174k extrapolation per factory direction v28.
"""

import numpy as np
import json
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


def constrained_hierarchical_leiden(embeddings: np.ndarray, 
                                     coarse_res: float = 0.25,
                                     fine_res: float = 3.0,
                                     k: int = 15,
                                     min_cluster_size: int = 5,
                                     adaptive_sub_resolution: bool = True,
                                     max_subclusters: int = 50) -> Dict:
    """
    Run CONSTRAINED hierarchical Leiden clustering with configurable parameters.
    Each finer resolution is a refinement of the previous coarser partition.
    """
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    # Coarse level
    partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                   weights='weight', resolution_parameter=coarse_res)
    coarse_labels = np.array(partition.membership)
    
    # Fine level: constrained within coarse clusters
    fine_labels = np.full(n, -1, dtype=int)
    next_label = 0
    
    for coarse_cluster in np.unique(coarse_labels):
        mask = coarse_labels == coarse_cluster
        indices = np.where(mask)[0]
        if len(indices) < 2:
            fine_labels[mask] = next_label
            next_label += 1
            continue
        
        # Induced subgraph
        subg = g.induced_subgraph(indices.tolist())
        
        # Determine sub-resolution
        if adaptive_sub_resolution:
            # Scale sub-resolution by cluster size
            size_factor = min(len(indices) / 100.0, 2.0)
            sub_res = fine_res * size_factor
        else:
            sub_res = fine_res
        
        # Run Leiden on subgraph
        try:
            sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                               weights='weight', resolution_parameter=sub_res)
            sub_labels = np.array(sub_partition.membership)
            
            # Enforce max_subclusters
            unique_sub = np.unique(sub_labels)
            if len(unique_sub) > max_subclusters:
                # Merge smallest clusters
                sub_sizes = np.bincount(sub_labels)
                keep = np.argsort(sub_sizes)[-max_subclusters:]
                merge_map = {u: keep[i] if u not in keep else u for i, u in enumerate(unique_sub)}
                sub_labels = np.array([merge_map[l] for l in sub_labels])
            
            # Map back to global labels
            for j, idx in enumerate(indices):
                fine_labels[idx] = next_label + sub_labels[j]
            next_label += len(np.unique(sub_labels))
        except:
            # Fallback: keep as single cluster
            fine_labels[indices] = next_label
            next_label += 1
    
    # Enforce minimum cluster size on fine labels
    unique, counts = np.unique(fine_labels, return_counts=True)
    small_clusters = unique[counts < min_cluster_size]
    if len(small_clusters) > 0:
        for sc in small_clusters:
            mask = fine_labels == sc
            if np.any(mask):
                idx = np.where(mask)[0][0]
                neighbors = g.neighbors(idx)
                for n_idx in neighbors:
                    if fine_labels[n_idx] not in small_clusters:
                        fine_labels[mask] = fine_labels[n_idx]
                        break
    
    # Renumber labels consecutively
    for labels in [coarse_labels, fine_labels]:
        unique_labels = np.unique(labels)
        label_map = {old: new for new, old in enumerate(unique_labels)}
        labels[:] = [label_map[l] for l in labels]
    
    return {
        'coarse': {
            'labels': coarse_labels,
            'n_clusters': len(np.unique(coarse_labels)),
            'cluster_sizes': np.bincount(coarse_labels).tolist(),
            'median_size': np.median(np.bincount(coarse_labels)),
            'singleton_fraction': np.sum(np.bincount(coarse_labels) == 1) / len(coarse_labels)
        },
        'fine': {
            'labels': fine_labels,
            'n_clusters': len(np.unique(fine_labels)),
            'cluster_sizes': np.bincount(fine_labels).tolist(),
            'median_size': np.median(np.bincount(fine_labels)),
            'singleton_fraction': np.sum(np.bincount(fine_labels) == 1) / len(fine_labels)
        }
    }


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


def compute_improvement_rate(results: Dict, metadata: List[Dict], field_name: str) -> float:
    """Compute improvement rate: fraction of fine clusters with purity > coarse cluster purity + 0.01."""
    coarse_labels = results['coarse']['labels']
    fine_labels = results['fine']['labels']
    
    # Compute purity for each cluster at both levels
    def cluster_purities(labels, field):
        purities = {}
        values = [m.get(field) for m in metadata]
        valid_mask = [v is not None and v != 'unknown' for v in values]
        if not any(valid_mask):
            return purities
        labels_valid = labels[valid_mask]
        values_valid = [v for v, m in zip(values, valid_mask) if m]
        
        for lbl in np.unique(labels_valid):
            mask = labels_valid == lbl
            cluster_values = [values_valid[i] for i, m in enumerate(mask) if m]
            if not cluster_values:
                continue
            value_counts = {}
            for v in cluster_values:
                value_counts[v] = value_counts.get(v, 0) + 1
            max_count = max(value_counts.values())
            purities[lbl] = max_count / len(cluster_values)
        return purities
    
    coarse_purities = cluster_purities(coarse_labels, field_name)
    fine_purities = cluster_purities(fine_labels, field_name)
    
    # Map fine clusters to coarse clusters
    fine_to_coarse = {}
    for i in range(len(coarse_labels)):
        fc = fine_labels[i]
        cc = coarse_labels[i]
        if fc not in fine_to_coarse:
            fine_to_coarse[fc] = cc
    
    improvements = 0
    total = 0
    for fc, cc in fine_to_coarse.items():
        if fc in fine_purities and cc in coarse_purities:
            total += 1
            if fine_purities[fc] > coarse_purities[cc] + 0.01:
                improvements += 1
    
    return improvements / total if total > 0 else 0.0


def compute_legal_purity(labels: np.ndarray, metadata: List[Dict], field: str) -> float:
    """Compute purity of clusters w.r.t. a legal metadata field."""
    n = len(labels)
    if n == 0:
        return 0.0
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None and v != 'unknown' for v in values]
    if not any(valid_mask):
        return 0.0
    
    labels_valid = labels[valid_mask]
    values_valid = [v for v, m in zip(values, valid_mask) if m]
    
    unique_labels = np.unique(labels_valid)
    total_purity = 0.0
    total_size = 0
    
    for lbl in unique_labels:
        mask = labels_valid == lbl
        cluster_values = [values_valid[i] for i, m in enumerate(mask) if m]
        if not cluster_values:
            continue
        value_counts = {}
        for v in cluster_values:
            value_counts[v] = value_counts.get(v, 0) + 1
        max_count = max(value_counts.values())
        total_purity += max_count
        total_size += len(cluster_values)
    
    return total_purity / total_size if total_size > 0 else 0.0


def evaluate_config(config_name: str, results: Dict, metadata: List[Dict]) -> Dict:
    """Evaluate a constrained hierarchical configuration."""
    coarse_labels = results['coarse']['labels']
    fine_labels = results['fine']['labels']
    
    nesting = compute_nesting_score(coarse_labels, fine_labels)
    branch_impr = compute_improvement_rate(results, metadata, 'branch')
    area_impr = compute_improvement_rate(results, metadata, 'legal_area')
    
    # Overall improvement rate (average of branch and legal_area)
    improvement_rate = (branch_impr + area_impr) / 2
    
    coarse_branch = compute_legal_purity(coarse_labels, metadata, 'branch')
    coarse_area = compute_legal_purity(coarse_labels, metadata, 'legal_area')
    fine_branch = compute_legal_purity(fine_labels, metadata, 'branch')
    fine_area = compute_legal_purity(fine_labels, metadata, 'legal_area')
    
    singleton_frac = results['fine']['singleton_fraction']
    median_size = results['fine']['median_size']
    
    # v26 zoom-quality checks
    passes_nesting = nesting >= 0.99
    passes_improvement = improvement_rate > 0.5
    passes_fragmentation = singleton_frac < 0.99 and median_size > 1
    
    verdict = 'PASS' if (passes_nesting and passes_improvement and passes_fragmentation) else 'FAIL'
    
    return {
        'config': config_name,
        'coarse_clusters': results['coarse']['n_clusters'],
        'fine_clusters': results['fine']['n_clusters'],
        'nesting_score': nesting,
        'branch_improvement_rate': branch_impr,
        'area_improvement_rate': area_impr,
        'improvement_rate': improvement_rate,
        'coarse_branch_purity': coarse_branch,
        'coarse_area_purity': coarse_area,
        'fine_branch_purity': fine_branch,
        'fine_area_purity': fine_area,
        'singleton_fraction': singleton_frac,
        'median_cluster_size': median_size,
        'passes_nesting': passes_nesting,
        'passes_improvement': passes_improvement,
        'passes_fragmentation': passes_fragmentation,
        'verdict': verdict
    }


def main():
    print("="*70)
    print("PARAMETER SWEEP: Constrained Hierarchical Leiden on 12k Dense Embeddings")
    print("Factory Direction v28 | ACCEPTED evidence (years 2000-2002)")
    print("="*70)
    
    # Load embeddings
    embeddings = np.load('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_partial_2000_2002/embeddings_center_projected_64.npy')
    print(f"\nLoaded embeddings: {embeddings.shape}")
    
    # Load metadata
    with open('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_partial_2000_2002/metadata.json', 'r') as f:
        metadata = json.load(f)
    print(f"Loaded metadata: {len(metadata)} entries")
    
    # Parameter grid
    configs = [
        # (coarse_res, fine_res, min_size, adaptive, max_sub, name)
        (0.05, 1.0, 20, False, 20, "coarse_0.05_fixed1.0_min20"),
        (0.05, 2.0, 20, False, 20, "coarse_0.05_fixed2.0_min20"),
        (0.05, 3.0, 20, False, 20, "coarse_0.05_fixed3.0_min20"),
        (0.1, 1.0, 20, False, 20, "coarse_0.1_fixed1.0_min20"),
        (0.1, 2.0, 20, False, 20, "coarse_0.1_fixed2.0_min20"),
        (0.1, 3.0, 20, False, 20, "coarse_0.1_fixed3.0_min20"),
        (0.1, 5.0, 20, False, 20, "coarse_0.1_fixed5.0_min20"),
        (0.25, 1.0, 20, False, 20, "coarse_0.25_fixed1.0_min20"),
        (0.25, 2.0, 20, False, 20, "coarse_0.25_fixed2.0_min20"),  # Previous best
        (0.25, 3.0, 20, False, 20, "coarse_0.25_fixed3.0_min20"),
        (0.25, 5.0, 20, False, 20, "coarse_0.25_fixed5.0_min20"),
        (0.5, 2.0, 20, False, 20, "coarse_0.5_fixed2.0_min20"),    # Reported best
        (0.5, 3.0, 20, False, 20, "coarse_0.5_fixed3.0_min20"),
        (0.5, 5.0, 20, False, 20, "coarse_0.5_fixed5.0_min20"),
        # Test min_cluster_size variations
        (0.5, 2.0, 10, False, 20, "coarse_0.5_fixed2.0_min10"),
        (0.5, 2.0, 50, False, 20, "coarse_0.5_fixed2.0_min50"),
        # Test adaptive sub-resolution (previously deprecated at >=10k)
        (0.25, 3.0, 20, True, 20, "coarse_0.25_adaptive3.0_min20"),
        (0.5, 3.0, 20, True, 20, "coarse_0.5_adaptive3.0_min20"),
        # Test max_subclusters
        (0.5, 2.0, 20, False, 10, "coarse_0.5_fixed2.0_min20_max10"),
        (0.5, 2.0, 20, False, 50, "coarse_0.5_fixed2.0_min20_max50"),
    ]
    
    all_results = []
    
    for coarse_res, fine_res, min_size, adaptive, max_sub, name in configs:
        print(f"\n{'='*70}")
        print(f"Testing: {name}")
        print(f"  coarse_res={coarse_res}, fine_res={fine_res}, min_size={min_size}, adaptive={adaptive}, max_sub={max_sub}")
        print(f"{'='*70}")
        
        try:
            results = constrained_hierarchical_leiden(
                embeddings,
                coarse_res=coarse_res,
                fine_res=fine_res,
                min_cluster_size=min_size,
                adaptive_sub_resolution=adaptive,
                max_subclusters=max_sub
            )
            
            eval_result = evaluate_config(name, results, metadata)
            all_results.append(eval_result)
            
            print(f"  Coarse clusters: {eval_result['coarse_clusters']}")
            print(f"  Fine clusters: {eval_result['fine_clusters']}")
            print(f"  Nesting: {eval_result['nesting_score']:.4f}")
            print(f"  Branch impr: {eval_result['branch_improvement_rate']:.3f}")
            print(f"  Area impr: {eval_result['area_improvement_rate']:.3f}")
            print(f"  Overall impr: {eval_result['improvement_rate']:.3f}")
            print(f"  Singleton frac: {eval_result['singleton_fraction']:.4f}")
            print(f"  Median size: {eval_result['median_cluster_size']:.1f}")
            print(f"  Verdict: {eval_result['verdict']}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            all_results.append({'config': name, 'error': str(e)})
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/parameter_sweep_12k')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'parameter_sweep_12k_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Print summary table
    print(f"\n{'='*70}")
    print("PARAMETER SWEEP SUMMARY")
    print(f"{'='*70}")
    print(f"{'Config':40s} | {'Verdict':6s} | {'Impr':6s} | {'Nest':6s} | {'Singl':6s} | {'MedSz':6s} | {'Coarse':6s} | {'Fine':6s}")
    print(f"{'-'*70}")
    
    passing = []
    for r in all_results:
        if 'error' in r:
            print(f"{r['config']:40s} | ERROR")
            continue
        verdict = r['verdict']
        if verdict == 'PASS':
            passing.append(r)
        print(f"{r['config']:40s} | {verdict:6s} | {r['improvement_rate']:.3f} | {r['nesting_score']:.3f} | {r['singleton_fraction']:.3f} | {r['median_cluster_size']:5.1f} | {r['coarse_clusters']:6d} | {r['fine_clusters']:6d}")
    
    print(f"\nPassing configurations: {len(passing)}/{len(configs)}")
    
    if passing:
        print("\nBest by improvement_rate:")
        for r in sorted(passing, key=lambda x: -x['improvement_rate'])[:5]:
            print(f"  {r['config']}: impr={r['improvement_rate']:.3f}, nesting={r['nesting_score']:.3f}, singleton={r['singleton_fraction']:.3f}")
    
    return all_results


if __name__ == '__main__':
    main()