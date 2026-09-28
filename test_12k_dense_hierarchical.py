#!/usr/bin/env python3
"""
Test hierarchical Leiden on 12k dense embeddings (years 2000-2002)
to confirm scale dependency per factory direction v28.
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


def hierarchical_leiden(embeddings: np.ndarray, 
                        resolutions: List[float] = None,
                        k: int = 15,
                        min_cluster_size: int = 5) -> Dict:
    """Run hierarchical Leiden clustering at multiple resolutions."""
    if resolutions is None:
        resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    
    g = build_knn_graph(embeddings, k=k)
    
    results = {}
    for res in resolutions:
        partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                       weights='weight', resolution_parameter=res)
        labels = np.array(partition.membership)
        
        # Enforce minimum cluster size by merging small clusters
        unique, counts = np.unique(labels, return_counts=True)
        small_clusters = unique[counts < min_cluster_size]
        if len(small_clusters) > 0:
            for sc in small_clusters:
                mask = labels == sc
                if np.any(mask):
                    idx = np.where(mask)[0][0]
                    neighbors = g.neighbors(idx)
                    for n in neighbors:
                        if labels[n] not in small_clusters:
                            labels[mask] = labels[n]
                            break
        
        # Renumber labels consecutively
        unique_labels = np.unique(labels)
        label_map = {old: new for new, old in enumerate(unique_labels)}
        labels = np.array([label_map[l] for l in labels])
        
        results[res] = {
            'labels': labels,
            'n_clusters': len(unique_labels),
            'cluster_sizes': np.bincount(labels).tolist(),
            'modularity': partition.modularity,
            'median_size': np.median(np.bincount(labels)),
            'singleton_fraction': np.sum(np.bincount(labels) == 1) / len(labels)
        }
    
    return results


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


def compute_zoom_coherence(labels_list: List[np.ndarray]) -> Dict:
    """Compute zoom coherence metrics across resolution levels."""
    if len(labels_list) < 2:
        return {'improvement_rate': 0.0, 'nesting_scores': []}
    
    nesting_scores = []
    for i in range(len(labels_list) - 1):
        score = compute_nesting_score(labels_list[i], labels_list[i+1])
        nesting_scores.append(score)
    
    improvements = sum(1 for s in nesting_scores if s > 0.5)
    improvement_rate = improvements / len(nesting_scores) if nesting_scores else 0.0
    
    return {
        'improvement_rate': improvement_rate,
        'nesting_scores': nesting_scores,
        'mean_nesting': np.mean(nesting_scores) if nesting_scores else 0.0,
        'min_nesting': np.min(nesting_scores) if nesting_scores else 0.0
    }


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


def evaluate_zoom_quality(results: Dict, metadata: List[Dict]) -> Dict:
    """Evaluate zoom quality per factory direction v26 rule."""
    resolutions = sorted(results.keys())
    labels_list = [results[r]['labels'] for r in resolutions]
    
    zoom = compute_zoom_coherence(labels_list)
    
    # Check singleton fraction at finest resolution
    finest = results[resolutions[-1]]
    singleton_frac = finest['singleton_fraction']
    median_size = finest['median_size']
    
    # Legal purity at each resolution
    legal_purities = {}
    for field in ['branch', 'legal_area', 'language', 'chamber']:
        purities = []
        for r in resolutions:
            purities.append(compute_legal_purity(results[r]['labels'], metadata, field))
        legal_purities[field] = purities
    
    # Check monotonic improvement in legal purity
    monotonic = {}
    for field, purities in legal_purities.items():
        improvements = sum(1 for i in range(len(purities)-1) if purities[i+1] >= purities[i])
        monotonic[field] = improvements / (len(purities)-1) if len(purities) > 1 else 0
    
    # v26 zoom-quality verdict
    passes_nesting = zoom['min_nesting'] >= 0.99
    passes_improvement = zoom['improvement_rate'] > 0.5
    passes_fragmentation = singleton_frac < 0.99 and median_size > 1
    passes_monotonic = all(m > 0.5 for m in monotonic.values())
    
    verdict = 'PASS' if (passes_nesting and passes_improvement and passes_fragmentation and passes_monotonic) else 'FAIL'
    
    return {
        'verdict': verdict,
        'nesting_scores': zoom['nesting_scores'],
        'improvement_rate': zoom['improvement_rate'],
        'min_nesting': zoom['min_nesting'],
        'singleton_fraction_fine': singleton_frac,
        'median_cluster_size_fine': median_size,
        'passes_nesting': passes_nesting,
        'passes_improvement': passes_improvement,
        'passes_fragmentation': passes_fragmentation,
        'passes_monotonic': passes_monotonic,
        'legal_purities': legal_purities,
        'monotonic_improvement': monotonic,
        'resolutions': resolutions,
        'n_clusters_per_res': [results[r]['n_clusters'] for r in resolutions]
    }


def main():
    # Load 12k embeddings (2000-2002)
    print("Loading 12k dense embeddings (years 2000-2002)...")
    
    embeddings_64 = np.load('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_partial_2000_2002/embeddings_center_projected_64.npy')
    embeddings_768 = np.load('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_partial_2000_2002/embeddings_768.npy')
    embeddings_128 = np.load('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_partial_2000_2002/embeddings_center_projected_128.npy')
    
    print(f"  64-dim: {embeddings_64.shape}")
    print(f"  768-dim: {embeddings_768.shape}")
    print(f"  128-dim: {embeddings_128.shape}")
    
    # Load metadata
    with open('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_partial_2000_2002/metadata.json', 'r') as f:
        metadata = json.load(f)
    print(f"  Metadata: {len(metadata)} entries")
    
    # Test each embedding
    for name, emb in [('center_projected_64', embeddings_64), 
                       ('center_projected_768', embeddings_768),
                       ('center_projected_128', embeddings_128)]:
        print(f"\n{'='*70}")
        print(f"Testing {name} ({emb.shape[0]} decisions, {emb.shape[1]} dim)")
        print(f"{'='*70}")
        
        # Run hierarchical Leiden
        results = hierarchical_leiden(emb, k=15, min_cluster_size=5)
        
        # Print summary
        for res in sorted(results.keys()):
            r = results[res]
            print(f"  Res {res:.2f}: n_clusters={r['n_clusters']}, median_size={r['median_size']:.1f}, "
                  f"singleton_frac={r['singleton_fraction']:.3f}, modularity={r['modularity']:.4f}")
        
        # Evaluate zoom quality
        zoom = evaluate_zoom_quality(results, metadata)
        
        print(f"\n  Zoom Quality Evaluation:")
        print(f"    Verdict: {zoom['verdict']}")
        print(f"    Improvement rate: {zoom['improvement_rate']:.2f}")
        print(f"    Min nesting: {zoom['min_nesting']:.4f}")
        print(f"    Singleton fraction (fine): {zoom['singleton_fraction_fine']:.4f}")
        print(f"    Median cluster size (fine): {zoom['median_cluster_size_fine']:.1f}")
        print(f"    Passes nesting>=0.99: {zoom['passes_nesting']}")
        print(f"    Passes improvement>0.5: {zoom['passes_improvement']}")
        print(f"    Passes fragmentation: {zoom['passes_fragmentation']}")
        print(f"    Passes monotonic: {zoom['passes_monotonic']}")
        print(f"    Legal purities:")
        for field, purities in zoom['legal_purities'].items():
            print(f"      {field}: {[f'{p:.3f}' for p in purities]}")
        print(f"    Monotonic improvement: {zoom['monotonic_improvement']}")


if __name__ == '__main__':
    main()