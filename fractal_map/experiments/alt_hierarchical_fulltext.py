#!/usr/bin/env python3
"""
Alternative Hierarchical Clustering Methods for Fractal Map - Full Text TF-IDF
=============================================================================
Tests alternative methods on full_text_tfidf_light embeddings (174k, no zero-norm).
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse
import sys

# Try imports
try:
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph
    HAS_LEIDEN = True
except ImportError:
    HAS_LEIDEN = False

try:
    import hnswlib
    HAS_HNSW = True
except ImportError:
    HAS_HNSW = False

try:
    from sklearn.cluster import AgglomerativeClustering
    HAS_AGGLO = True
except ImportError:
    HAS_AGGLO = False

try:
    import hdbscan
    HAS_HDBSCAN = True
except ImportError:
    HAS_HDBSCAN = False

from sklearn.preprocessing import normalize

BASE = Path('/home/runner/work/LexMachina/LexMachina')
EMBEDDING_PATH = BASE / 'results/fractal_map/hierarchical_map_174k/tfidf_embeddings/full_text_tfidf_light.npy'
METADATA_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
OUTPUT_DIR = BASE / 'results/fractal_map/alternative_hierarchical_tests'

RESOLUTIONS_COMPRESSED = [0.25, 0.5, 1.0, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3

# 4 branch classes, 213 legal_area classes
BRANCH_RANDOM = 0.25
AREA_RANDOM = 1/213


def load_data(sample_size=None, seed=42):
    """Load embeddings and metadata, optionally sample."""
    print(f"Loading embeddings from {EMBEDDING_PATH}")
    embeddings = np.load(EMBEDDING_PATH)
    
    print(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    
    # Align: metadata has 173,963, embeddings has 175,440
    n = min(len(embeddings), len(metadata))
    embeddings = embeddings[:n]
    metadata = metadata[:n]
    
    if sample_size and sample_size < n:
        np.random.seed(seed)
        indices = np.random.choice(n, sample_size, replace=False)
        indices = np.sort(indices)
        embeddings = embeddings[indices]
        metadata = [metadata[i] for i in indices]
        print(f"Sampled {sample_size} decisions (seed={seed})")
    
    # Filter zero-norm embeddings (should be none for full_text_tfidf_light)
    norms = np.linalg.norm(embeddings, axis=1)
    valid_mask = norms > 0
    print(f"Valid embeddings: {valid_mask.sum()}/{len(valid_mask)} ({(1-valid_mask.mean())*100:.1f}% zero-norm)")
    
    embeddings = embeddings[valid_mask]
    metadata = [m for i, m in enumerate(metadata) if valid_mask[i]]
    
    # Normalize
    embeddings = normalize(embeddings, norm='l2')
    
    return embeddings, metadata


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Multi-resolution Leiden clustering (baseline)."""
    if not HAS_LEIDEN:
        return None
    k_actual = min(k, len(embeddings) - 1)
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


def hnsw_hierarchical_clustering(embeddings, n_levels=5, k=15, ef_construction=200):
    """
    HNSW-based hierarchical clustering.
    """
    if not HAS_HNSW:
        return None
    if not HAS_LEIDEN:
        return None
    
    n = len(embeddings)
    dim = embeddings.shape[1]
    
    # Build HNSW index
    index = hnswlib.Index(space='l2', dim=dim)
    index.init_index(max_elements=n, ef_construction=ef_construction, M=16)
    index.add_items(embeddings, np.arange(n))
    
    labels_by_level = {}
    ef_values = [10, 20, 50, 100, 200]
    
    for i, ef in enumerate(ef_values):
        index.set_ef(ef)
        neighbors, distances = index.knn_query(embeddings, k=min(k+1, n))
        edges = []
        weights = []
        for idx in range(n):
            for j in range(1, min(k+1, n)):
                neighbor = neighbors[idx, j]
                if neighbor != idx:
                    edges.append((idx, neighbor))
                    weights.append(1.0 / (1.0 + distances[idx, j]))
        
        g = ig.Graph()
        g.add_vertices(n)
        g.add_edges(edges)
        g.es['weight'] = weights
        resolution = 0.25 * (2 ** i)
        partition = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=resolution, seed=42)
        labels_by_level[RESOLUTIONS_COMPRESSED[i]] = np.array(partition.membership)
    
    return labels_by_level


def agglomerative_hierarchical_clustering(embeddings, linkage='ward', n_clusters_list=None):
    """Agglomerative clustering at multiple cluster counts."""
    if not HAS_AGGLO:
        return None
    
    if n_clusters_list is None:
        n = len(embeddings)
        n_clusters_list = [max(3, n // 50000), max(3, n // 20000), max(3, n // 5000), 
                          max(3, n // 1000), max(3, n // 500)]
        n_clusters_list = [min(c, n//3) for c in n_clusters_list]
    
    labels_by_res = {}
    for i, n_clusters in enumerate(n_clusters_list):
        if n_clusters >= len(embeddings):
            continue
        clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage, metric='euclidean')
        labels = clustering.fit_predict(embeddings)
        labels_by_res[RESOLUTIONS_COMPRESSED[i]] = labels
    
    return labels_by_res


def hdbscan_hierarchical_clustering(embeddings, min_cluster_size_list=None):
    """HDBSCAN at multiple min_cluster_size for multi-resolution."""
    if not HAS_HDBSCAN:
        return None
    
    if min_cluster_size_list is None:
        n = len(embeddings)
        min_cluster_size_list = [max(5, n // 50000), max(5, n // 20000), max(5, n // 5000), 
                                max(5, n // 1000), max(5, n // 500)]
        min_cluster_size_list = [min(c, n//3) for c in min_cluster_size_list]
    
    # Normalize for cosine similarity via Euclidean
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized_embeddings = embeddings / norms
    
    labels_by_res = {}
    for i, min_size in enumerate(min_cluster_size_list):
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_size,
            min_samples=None,
            cluster_selection_epsilon=0.0,
            metric='euclidean',
            cluster_selection_method='eom',
        )
        labels = clusterer.fit_predict(normalized_embeddings)
        labels_by_res[RESOLUTIONS_COMPRESSED[i]] = labels
    
    return labels_by_res


def compute_purity(labels, metadata, field, min_cluster_size=3):
    """Compute mean cluster purity for a metadata field."""
    purities = []
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        vals = [metadata[i].get(field) for i in indices]
        vals = [v for v in vals if v and v != 'unknown']
        if vals:
            purities.append(Counter(vals).most_common(1)[0][1] / len(vals))
    return float(np.mean(purities)) if purities else 0.0


def compute_zoom_coherence(labels_coarse, labels_fine, metadata, field='branch', min_cluster_size=3):
    """Compute zoom coherence metrics between two resolution levels."""
    improvements = []
    n_parents = 0
    parent_details = {}
    
    child_to_parent = {}
    for fine_id in np.unique(labels_fine[labels_fine != -1]):
        fine_mask = labels_fine == fine_id
        parent_labels = labels_coarse[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(
                Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    for coarse_id in np.unique(labels_coarse[labels_coarse != -1]):
        coarse_mask = labels_coarse == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_cluster_size:
            continue
        coarse_vals = [metadata[i].get(field) for i in coarse_indices]
        coarse_vals = [v for v in coarse_vals if v and v != 'unknown']
        if not coarse_vals:
            continue
        coarse_purity = Counter(coarse_vals).most_common(1)[0][1] / len(coarse_vals)
        
        child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
        child_purities = []
        for fc in child_clusters:
            fine_mask = labels_fine == fc
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
                continue
            fine_vals = [metadata[i].get(field) for i in fine_indices]
            fine_vals = [v for v in fine_vals if v and v != 'unknown']
            if fine_vals:
                child_purities.append(Counter(fine_vals).most_common(1)[0][1] / len(fine_vals))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_clusters),
            }
            n_parents += 1
    
    return {
        'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
        'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
        'n_parents': n_parents,
        'parent_details': parent_details,
    }


def compute_nesting(labels_by_res):
    """Compute strict nesting consistency across resolutions."""
    resolutions = sorted(labels_by_res.keys())
    nesting = {}
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        cl = labels_by_res[coarser_res]
        fl = labels_by_res[finer_res]
        n_strict = 0
        n_valid = 0
        for fid in np.unique(fl[fl != -1]):
            members = cl[fl == fid]
            members = members[members != -1]
            if len(members) == 0:
                continue
            n_valid += 1
            if len(set(members.tolist())) == 1:
                n_strict += 1
        nesting[f"{coarser_res}_to_{finer_res}"] = round(n_strict / n_valid, 6) if n_valid else None
    return nesting


def compute_fragmentation(labels):
    """Compute cluster fragmentation metrics."""
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
    }


def evaluate_method(method_name, labels_by_res, metadata):
    """Evaluate a hierarchical clustering method using zoom-quality metrics."""
    print(f"\n=== Evaluating {method_name} ===")
    
    branch_purity = {}
    area_purity = {}
    fragmentation = {}
    
    for res in sorted(labels_by_res.keys()):
        labels = labels_by_res[res]
        branch_purity[f"res_{res}"] = compute_purity(labels, metadata, 'branch')
        area_purity[f"res_{res}"] = compute_purity(labels, metadata, 'legal_area')
        fragmentation[f"res_{res}"] = compute_fragmentation(labels)
        print(f"  res_{res}: branch_purity={branch_purity[f'res_{res}']:.4f}, "
              f"area_purity={area_purity[f'res_{res}']:.4f}, "
              f"n_clusters={fragmentation[f'res_{res}']['n_clusters']}, "
              f"median_size={fragmentation[f'res_{res}']['median_size']:.1f}, "
              f"singleton_frac={fragmentation[f'res_{res}']['singleton_fraction']:.4f}")
    
    zoom_branch = {}
    resolutions = sorted(labels_by_res.keys())
    for i in range(len(resolutions) - 1):
        coarser, finer = resolutions[i], resolutions[i + 1]
        zoom_branch[f"res_{coarser}_to_res_{finer}"] = compute_zoom_coherence(
            labels_by_res[coarser], labels_by_res[finer], metadata, 'branch')
        print(f"  zoom {coarser}->{finer}: improvement_rate={zoom_branch[f'res_{coarser}_to_res_{finer}']['improvement_rate']:.4f}, "
              f"mean_improvement={zoom_branch[f'res_{coarser}_to_res_{finer}']['mean_improvement']:.4f}, "
              f"n_parents={zoom_branch[f'res_{coarser}_to_res_{finer}']['n_parents']}")
    
    nesting = compute_nesting(labels_by_res)
    mean_nesting = np.mean([v for v in nesting.values() if v is not None])
    print(f"  Mean strict nesting: {mean_nesting:.4f}")
    
    res_list = sorted(labels_by_res.keys())
    b_mono = branch_purity[f"res_{res_list[-1]}"] > branch_purity[f"res_{res_list[0]}"]
    a_mono = area_purity[f"res_{res_list[-1]}"] > area_purity[f"res_{res_list[0]}"]
    rates = [v['improvement_rate'] for v in zoom_branch.values()]
    rate_ok = sum(1 for r in rates if r is not None and r > 0.5) >= 2
    mode_pass = b_mono and a_mono and rate_ok
    
    print(f"  Checks: branch_mono={b_mono}, area_mono={a_mono}, rate_ok={rate_ok} ({[f'{r:.3f}' for r in rates]})")
    print(f"  VERDICT: {'PASS' if mode_pass else 'FAIL'}")
    
    return {
        'method': method_name,
        'branch_purity': branch_purity,
        'area_purity': area_purity,
        'zoom_branch': zoom_branch,
        'nesting': nesting,
        'mean_nesting': mean_nesting,
        'fragmentation': fragmentation,
        'checks': {
            'branch_monotonic': b_mono,
            'area_monotonic': a_mono,
            'improvement_rate_gt_0.5_on_2_of_4': rate_ok,
        },
        'verdict': 'PASS' if mode_pass else 'FAIL',
    }


def main():
    parser = argparse.ArgumentParser(description='Test alternative hierarchical clustering methods on full_text_tfidf')
    parser.add_argument('--sample-size', type=int, default=20000, help='Sample size for testing (None for full)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--methods', nargs='+', 
                        default=['leiden', 'hnsw', 'agglom_ward', 'agglom_average', 'hdbscan'],
                        help='Methods to test')
    parser.add_argument('--output', type=Path, help='Output JSON path')
    args = parser.parse_args()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    embeddings, metadata = load_data(sample_size=args.sample_size, seed=args.seed)
    print(f"Final data: {len(embeddings)} decisions, {embeddings.shape[1]} dims")
    
    meta_by_idx = metadata
    
    results = {
        'run_id': f"alt_hierarchical_fulltext_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'sample_size': len(embeddings),
        'embedding_dim': embeddings.shape[1],
        'embedding_type': 'full_text_tfidf_light',
        'baseline': {'branch_random': BRANCH_RANDOM, 'area_random': AREA_RANDOM},
        'methods': {}
    }
    
    # Test each method
    if 'leiden' in args.methods and HAS_LEIDEN:
        print("\n" + "="*60)
        print("Testing Multi-Resolution Leiden (Baseline)")
        print("="*60)
        labels_by_res = {}
        for res in RESOLUTIONS_COMPRESSED:
            labels = leiden_clustering(embeddings, resolution=res)
            labels_by_res[res] = labels
        results['methods']['leiden'] = evaluate_method('leiden', labels_by_res, meta_by_idx)
    
    if 'hnsw' in args.methods and HAS_HNSW and HAS_LEIDEN:
        print("\n" + "="*60)
        print("Testing HNSW-based Hierarchical Clustering")
        print("="*60)
        labels_by_res = hnsw_hierarchical_clustering(embeddings)
        if labels_by_res:
            results['methods']['hnsw'] = evaluate_method('hnsw', labels_by_res, meta_by_idx)
        else:
            print("  HNSW clustering failed or not available")
    
    if any(m.startswith('agglom') for m in args.methods) and HAS_AGGLO:
        for linkage in ['ward', 'average', 'complete']:
            method_key = f'agglom_{linkage}'
            if method_key in args.methods:
                print("\n" + "="*60)
                print(f"Testing Agglomerative Clustering ({linkage} linkage)")
                print("="*60)
                labels_by_res = agglomerative_hierarchical_clustering(embeddings, linkage=linkage)
                if labels_by_res:
                    results['methods'][method_key] = evaluate_method(method_key, labels_by_res, meta_by_idx)
                else:
                    print(f"  Agglomerative ({linkage}) failed or not available")
    
    if 'hdbscan' in args.methods and HAS_HDBSCAN:
        print("\n" + "="*60)
        print("Testing HDBSCAN Multi-resolution")
        print("="*60)
        labels_by_res = hdbscan_hierarchical_clustering(embeddings)
        if labels_by_res:
            results['methods']['hdbscan'] = evaluate_method('hdbscan', labels_by_res, meta_by_idx)
        else:
            print("  HDBSCAN failed or not available")
    
    # Save results
    output_path = args.output or OUTPUT_DIR / f"alt_hierarchical_fulltext_{len(embeddings)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for method, res in results['methods'].items():
        res_list = sorted(res['branch_purity'].keys())
        fine_key = res_list[-1]
        print(f"  {method}: {res['verdict']} (nesting={res['mean_nesting']:.4f}, "
              f"branch_purity_fine={res['branch_purity'][fine_key]:.4f})")


if __name__ == '__main__':
    main()