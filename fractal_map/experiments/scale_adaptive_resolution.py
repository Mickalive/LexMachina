#!/usr/bin/env python3
"""
Scale-Adaptive Resolution Ladder for Fractal Map
=================================================
The fixed resolution ladder [0.25, 0.5, 1.0, 2.0, 3.0] works at ~21k scale
but over-fragments at 174k scale. This experiment tests adaptive resolution
ladders that target specific cluster counts per level regardless of corpus size.

Target: ~5-10 clusters at coarsest, ~50-200 at finest for legal navigation.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse

try:
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph
    HAS_LEIDEN = True
except ImportError:
    HAS_LEIDEN = False

from sklearn.preprocessing import normalize

BASE = Path('/home/runner/work/LexMachina/LexMachina')
EMBEDDING_PATH = BASE / 'results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf.npy'
METADATA_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
OUTPUT_DIR = BASE / 'results/fractal_map/scale_adaptive_tests'

MIN_CLUSTER_SIZE = 3
BRANCH_RANDOM = 0.25
AREA_RANDOM = 1/213


def load_data(sample_size=None, seed=42):
    embeddings = np.load(EMBEDDING_PATH)
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    
    n = min(len(embeddings), len(metadata))
    embeddings = embeddings[:n]
    metadata = metadata[:n]
    
    if sample_size and sample_size < n:
        np.random.seed(seed)
        indices = np.random.choice(n, sample_size, replace=False)
        indices = np.sort(indices)
        embeddings = embeddings[indices]
        metadata = [metadata[i] for i in indices]
    
    norms = np.linalg.norm(embeddings, axis=1)
    valid_mask = norms > 0
    embeddings = embeddings[valid_mask]
    metadata = [m for i, m in enumerate(metadata) if valid_mask[i]]
    embeddings = normalize(embeddings, norm='l2')
    
    return embeddings, metadata


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
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


def find_resolution_for_target_clusters(embeddings, target_clusters, k=15, 
                                         resolution_range=(0.01, 10.0), 
                                         max_iter=20, seed=42):
    """Binary search for resolution that produces target_clusters."""
    n = len(embeddings)
    target_clusters = min(target_clusters, n // MIN_CLUSTER_SIZE)
    if target_clusters < 2:
        return 0.01
    
    low, high = resolution_range
    best_res = low
    best_diff = float('inf')
    
    for _ in range(max_iter):
        mid = (low + high) / 2
        labels = leiden_clustering(embeddings, resolution=mid, k=k, seed=seed)
        n_clusters = len(np.unique(labels[labels != -1]))
        diff = abs(n_clusters - target_clusters)
        
        if diff < best_diff:
            best_diff = diff
            best_res = mid
        
        if n_clusters > target_clusters:
            low = mid
        else:
            high = mid
        
        if high - low < 0.001:
            break
    
    return best_res


def build_scale_adaptive_ladder(embeddings, target_cluster_counts, k=15, seed=42):
    """
    Build a resolution ladder that targets specific cluster counts at each level.
    target_cluster_counts: list of target cluster counts per level (coarsest to finest)
    """
    resolutions = []
    labels_by_res = {}
    
    for i, target in enumerate(target_cluster_counts):
        res = find_resolution_for_target_clusters(embeddings, target, k=k, seed=seed)
        resolutions.append(res)
        labels = leiden_clustering(embeddings, resolution=res, k=k, seed=seed)
        actual_clusters = len(np.unique(labels[labels != -1]))
        labels_by_res[f"level_{i}"] = labels
        print(f"  Level {i}: target={target}, resolution={res:.4f}, actual_clusters={actual_clusters}")
    
    return resolutions, labels_by_res


def compute_purity(labels, metadata, field, min_cluster_size=3):
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
    resolutions = sorted(labels_by_res.keys())
    nesting = {}
    for i in range(len(resolutions) - 1):
        cl = labels_by_res[resolutions[i]]
        fl = labels_by_res[resolutions[i + 1]]
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
        nesting[f"{resolutions[i]}_to_{resolutions[i+1]}"] = round(n_strict / n_valid, 6) if n_valid else None
    return nesting


def compute_fragmentation(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
    }


def evaluate_ladder(ladder_name, labels_by_res, metadata):
    print(f"\n=== Evaluating {ladder_name} ===")
    
    branch_purity = {}
    area_purity = {}
    fragmentation = {}
    
    for level in sorted(labels_by_res.keys()):
        labels = labels_by_res[level]
        branch_purity[level] = compute_purity(labels, metadata, 'branch')
        area_purity[level] = compute_purity(labels, metadata, 'legal_area')
        fragmentation[level] = compute_fragmentation(labels)
        print(f"  {level}: branch_purity={branch_purity[level]:.4f}, "
              f"area_purity={area_purity[level]:.4f}, "
              f"n_clusters={fragmentation[level]['n_clusters']}, "
              f"median_size={fragmentation[level]['median_size']:.1f}, "
              f"singleton_frac={fragmentation[level]['singleton_fraction']:.4f}")
    
    # Zoom coherence
    zoom_branch = {}
    levels = sorted(labels_by_res.keys())
    for i in range(len(levels) - 1):
        zoom_branch[f"{levels[i]}_to_{levels[i+1]}"] = compute_zoom_coherence(
            labels_by_res[levels[i]], labels_by_res[levels[i+1]], metadata, 'branch')
        z = zoom_branch[f"{levels[i]}_to_{levels[i+1]}"]
        print(f"  zoom {levels[i]}->{levels[i+1]}: improvement_rate={z['improvement_rate']:.4f}, "
              f"mean_improvement={z['mean_improvement']:.4f}, n_parents={z['n_parents']}")
    
    # Nesting
    nesting = compute_nesting(labels_by_res)
    mean_nesting = np.mean([v for v in nesting.values() if v is not None])
    print(f"  Mean strict nesting: {mean_nesting:.4f}")
    
    # Checks
    level_list = sorted(labels_by_res.keys())
    b_mono = branch_purity[level_list[-1]] > branch_purity[level_list[0]]
    a_mono = area_purity[level_list[-1]] > area_purity[level_list[0]]
    rates = [v['improvement_rate'] for v in zoom_branch.values()]
    rate_ok = sum(1 for r in rates if r is not None and r > 0.5) >= 2
    mode_pass = b_mono and a_mono and rate_ok
    
    print(f"  Checks: branch_mono={b_mono}, area_mono={a_mono}, rate_ok={rate_ok} ({[f'{r:.3f}' for r in rates]})")
    print(f"  VERDICT: {'PASS' if mode_pass else 'FAIL'}")
    
    return {
        'ladder': ladder_name,
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
    parser = argparse.ArgumentParser(description='Test scale-adaptive resolution ladders')
    parser.add_argument('--sample-size', type=int, default=50000, help='Sample size')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--output', type=Path, help='Output JSON path')
    args = parser.parse_args()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    embeddings, metadata = load_data(sample_size=args.sample_size, seed=args.seed)
    n = len(embeddings)
    print(f"Data: {n} decisions, {embeddings.shape[1]} dims")
    
    # Target cluster counts for different corpus sizes
    # For legal navigation: coarse ~5-10, mid ~20-50, fine ~100-300
    # Scale targets proportionally
    scale_factor = n / 20000  # Reference: 20k decisions
    
    # Fixed ladder (baseline)
    print("\n" + "="*60)
    print("Fixed Resolution Ladder [0.25, 0.5, 1.0, 2.0, 3.0]")
    print("="*60)
    fixed_resolutions = [0.25, 0.5, 1.0, 2.0, 3.0]
    fixed_labels = {}
    for res in fixed_resolutions:
        fixed_labels[f"res_{res}"] = leiden_clustering(embeddings, resolution=res)
    fixed_result = evaluate_ladder('fixed_ladder', fixed_labels, metadata)
    
    # Scale-adaptive ladders
    # Target: 8 coarse, 20 mid, 50 fine, 150 finer, 300 finest (for ~20k)
    base_targets = [8, 20, 50, 150, 300]
    adaptive_targets = [max(3, int(t * scale_factor)) for t in base_targets]
    # Cap at reasonable fractions of N
    adaptive_targets = [min(t, n // 10) for t in adaptive_targets]
    
    print(f"\n" + "="*60)
    print(f"Scale-Adaptive Ladder (targets: {adaptive_targets})")
    print("="*60)
    adaptive_resolutions, adaptive_labels = build_scale_adaptive_ladder(
        embeddings, adaptive_targets)
    adaptive_result = evaluate_ladder('adaptive_ladder', adaptive_labels, metadata)
    
    # More conservative adaptive ladder (fewer fine clusters)
    conservative_targets = [max(3, int(t * scale_factor * 0.5)) for t in base_targets]
    conservative_targets = [min(t, n // 20) for t in conservative_targets]
    
    print(f"\n" + "="*60)
    print(f"Conservative Adaptive Ladder (targets: {conservative_targets})")
    print("="*60)
    conservative_resolutions, conservative_labels = build_scale_adaptive_ladder(
        embeddings, conservative_targets)
    conservative_result = evaluate_ladder('conservative_adaptive', conservative_labels, metadata)
    
    # Very coarse ladder (3 levels)
    coarse_targets = [max(3, int(t * scale_factor * 0.3)) for t in [8, 30, 100]]
    coarse_targets = [min(t, n // 30) for t in coarse_targets]
    
    print(f"\n" + "="*60)
    print(f"Coarse 3-Level Ladder (targets: {coarse_targets})")
    print("="*60)
    coarse_resolutions, coarse_labels = build_scale_adaptive_ladder(
        embeddings, coarse_targets)
    coarse_result = evaluate_ladder('coarse_3level', coarse_labels, metadata)
    
    # Save results
    results = {
        'run_id': f"scale_adaptive_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'sample_size': n,
        'embedding_dim': embeddings.shape[1],
        'baseline': {'branch_random': BRANCH_RANDOM, 'area_random': AREA_RANDOM},
        'fixed_ladder': fixed_result,
        'adaptive_ladder': adaptive_result,
        'conservative_adaptive': conservative_result,
        'coarse_3level': coarse_result,
    }
    
    output_path = args.output or OUTPUT_DIR / f"scale_adaptive_{args.sample_size}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, res in [('fixed', fixed_result), ('adaptive', adaptive_result), 
                       ('conservative', conservative_result), ('coarse3', coarse_result)]:
        print(f"  {name}: {res['verdict']} (nesting={res['mean_nesting']:.4f}, "
              f"branch_fine={res['branch_purity'][sorted(res['branch_purity'].keys())[-1]]:.4f})")


if __name__ == '__main__':
    main()