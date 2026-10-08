#!/usr/bin/env python3
"""
Hierarchical validation on available 158k dense embeddings (2000-2023).
Uses constrained hierarchical Leiden with adaptive=False (validated at 12k/28k).
"""
import json
import numpy as np
import os
import sys
from pathlib import Path
from collections import defaultdict

# Add paths
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

# Import clustering libraries
try:
    import leidenalg
    import igraph as ig
    LEIDEN_AVAILABLE = True
    print("Leiden/igraph available")
except ImportError:
    LEIDEN_AVAILABLE = False
    print("Leiden/igraph NOT available")

from sklearn.neighbors import NearestNeighbors

# Path to dense embeddings checkpoints
CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/")

# Years available (2000-2023)
AVAILABLE_YEARS = [str(y) for y in range(2000, 2024)]

def load_embeddings_and_metadata():
    """Load and concatenate all available year embeddings and metadata."""
    all_embeddings = []
    all_metadata = []
    decision_ids = []
    branches = []
    legal_areas = []
    languages = []
    outcomes = []
    chambers = []
    years = []
    
    for year in AVAILABLE_YEARS:
        emb_path = CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINTS_DIR / f"metadata_{year}.json"
        
        if not emb_path.exists() or not meta_path.exists():
            print(f"WARNING: Missing files for {year}")
            continue
            
        embeddings = np.load(emb_path)
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
        
        print(f"Loaded {year}: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dims")
        
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
        decision_ids.extend([m.get('decision_id', f'unknown_{year}_{i}') for i, m in enumerate(metadata)])
        branches.extend([m.get('branch', 'unknown') for m in metadata])
        legal_areas.extend([m.get('legal_area', 'unknown') for m in metadata])
        languages.extend([m.get('language', 'unknown') for m in metadata])
        outcomes.extend([m.get('outcome', 'unknown') for m in metadata])
        chambers.extend([m.get('chamber', 'unknown') for m in metadata])
        years.extend([m.get('year', year) for m in metadata])
    
    all_embeddings = np.vstack(all_embeddings)
    print(f"\nTotal: {all_embeddings.shape[0]} decisions, {all_embeddings.shape[1]} dims")
    
    return all_embeddings, all_metadata, decision_ids, branches, legal_areas, languages, outcomes, chambers, years

def encode_labels(labels):
    """Encode string labels to integers."""
    unique = list(set(labels))
    mapping = {v: i for i, v in enumerate(unique)}
    return np.array([mapping[v] for v in labels])

def build_knn_graph(embeddings, k=15):
    """Build k-NN graph for Leiden clustering."""
    nbrs = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    edges = []
    weights = []
    n = embeddings.shape[0]
    for i in range(n):
        for j_idx, j in enumerate(indices[i][1:], 1):
            w = 1.0 - distances[i][j_idx]
            if w > 0:
                edges.append((i, j))
                weights.append(w)
    
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights
    return g

def constrained_hierarchical_leiden(embeddings, resolutions=[0.25, 0.5, 1.0, 2.0, 3.0], min_cluster_size=20):
    """
    Run constrained hierarchical Leiden clustering with adaptive=False.
    This config validated at 12k and 28k scales.
    """
    if not LEIDEN_AVAILABLE:
        raise RuntimeError("Leiden/igraph required for 158k scale")
    
    print(f"Building k-NN graph for {embeddings.shape[0]} decisions...")
    g = build_knn_graph(embeddings, k=15)
    
    results = {}
    prev_labels = None
    
    for resolution in resolutions:
        print(f"  Running Leiden at resolution {resolution}...")
        partition = leidenalg.find_partition(
            g,
            leidenalg.RBConfigurationVertexPartition,
            resolution_parameter=resolution,
            weights='weight',
            seed=42
        )
        labels = np.array(partition.membership)
        
        # Enforce min_cluster_size by merging small clusters
        unique, counts = np.unique(labels, return_counts=True)
        small_clusters = unique[counts < min_cluster_size]
        
        for sc in small_clusters:
            mask = labels == sc
            if prev_labels is not None:
                parent_labels = prev_labels[mask]
                if len(parent_labels) > 0:
                    parent = np.bincount(parent_labels).argmax()
                    labels[mask] = parent
                else:
                    labels[mask] = -1
            else:
                labels[mask] = -1
        
        # Handle noise (-1)
        if -1 in labels:
            noise_mask = labels == -1
            non_noise_mask = ~noise_mask
            if non_noise_mask.sum() > 0:
                nn = NearestNeighbors(n_neighbors=1, metric='cosine', n_jobs=-1)
                nn.fit(embeddings[non_noise_mask])
                _, indices = nn.kneighbors(embeddings[noise_mask])
                labels[noise_mask] = labels[non_noise_mask][indices.flatten()]
            else:
                labels[noise_mask] = 0
        
        results[resolution] = labels
        prev_labels = labels
        
        # Stats
        unique, counts = np.unique(labels, return_counts=True)
        singleton_rate = (counts == 1).sum() / len(counts)
        print(f"    {len(unique)} clusters, median size {np.median(counts):.1f}, singleton rate {singleton_rate:.3f}")
    
    return results

def compute_purity(labels, ground_truth):
    """Compute cluster purity against ground truth labels."""
    if len(labels) == 0:
        return 0.0
    unique_clusters = np.unique(labels)
    total_correct = 0
    for c in unique_clusters:
        mask = labels == c
        if mask.sum() == 0:
            continue
        gt_in_cluster = ground_truth[mask]
        if len(gt_in_cluster) == 0:
            continue
        most_common = np.bincount(gt_in_cluster).argmax()
        total_correct += (gt_in_cluster == most_common).sum()
    return total_correct / len(labels)

def compute_zoom_coherence(labels_coarse, labels_fine, ground_truth):
    """Compute zoom coherence: does finer resolution improve purity?"""
    unique_coarse = np.unique(labels_coarse)
    improvements = []
    improved = 0
    total = 0
    
    for c in unique_coarse:
        mask = labels_coarse == c
        if mask.sum() < 2:
            continue
        coarse_purity = compute_purity(labels_coarse[mask], ground_truth[mask])
        
        fine_labels = labels_fine[mask]
        unique_fine = np.unique(fine_labels)
        if len(unique_fine) <= 1:
            improvements.append(0.0)
            total += 1
            continue
        
        child_purities = []
        for f in unique_fine:
            fmask = fine_labels == f
            if fmask.sum() > 0:
                child_purities.append(compute_purity(fine_labels[fmask], ground_truth[mask][fmask]))
        
        mean_child_purity = np.mean(child_purities) if child_purities else 0
        improvement = mean_child_purity - coarse_purity
        improvements.append(improvement)
        if improvement > 0:
            improved += 1
        total += 1
    
    return {
        'mean_improvement': float(np.mean(improvements)) if improvements else 0,
        'improvement_rate': float(improved / total) if total > 0 else 0,
        'n_parents_tested': total
    }

def evaluate_nesting(labels_coarse, labels_fine):
    """Compute nesting consistency between coarse and fine levels."""
    # strict_nesting: fraction of fine clusters that map to exactly one coarse cluster
    unique_fine = np.unique(labels_fine)
    consistent = 0
    for f in unique_fine:
        mask = labels_fine == f
        coarse_parents = np.unique(labels_coarse[mask])
        if len(coarse_parents) == 1:
            consistent += 1
    return float(consistent / len(unique_fine)) if len(unique_fine) > 0 else 0

def main():
    print("="*60)
    print("Hierarchical Validation: 158k Dense Embeddings (2000-2023)")
    print("="*60)
    
    # Load data
    embeddings, metadata, decision_ids, branches, legal_areas, languages, outcomes, chambers, years = load_embeddings_and_metadata()
    
    # Encode ground truth labels
    branch_encoded = encode_labels(branches)
    legal_area_encoded = encode_labels(legal_areas)
    language_encoded = encode_labels(languages)
    outcome_encoded = encode_labels(outcomes)
    chamber_encoded = encode_labels(chambers)
    
    # Run constrained hierarchical Leiden
    resolutions = [0.25, 0.5, 1.0, 2.0, 3.0]
    min_cluster_size = 20  # As validated at 28k scale
    
    cluster_results = constrained_hierarchical_leiden(embeddings, resolutions, min_cluster_size)
    
    # Compute metrics
    results = {
        'run_id': 'dense_158k_hierarchical_validation_20261008',
        'timestamp': '2026-10-08T04:49:00Z',
        'direction_version': 35,
        'hypothesis': "Constrained hierarchical Leiden (adaptive=False, min_cluster_size=20) achieves improvement_rate > 0.5 at 158k scale with zero fragmentation, as predicted by scale-stable model",
        'frozen_sample': f"{embeddings.shape[0]} decisions (years 2000-2023, legal-distance ACCEPTED checkpoints)",
        'embedding_shape': list(embeddings.shape),
        'resolutions': resolutions,
        'min_cluster_size': min_cluster_size,
        'adaptive_sub_res': False,
        'cluster_stats': {},
        'zoom_coherence': {},
        'nesting': {},
        'fine_branch_purity': None,
        'fine_legal_area_purity': None,
        'fine_language_purity': None
    }
    
    # Cluster stats at each resolution
    for r in resolutions:
        labels = cluster_results[r]
        unique, counts = np.unique(labels, return_counts=True)
        results['cluster_stats'][str(r)] = {
            'n_clusters': int(len(unique)),
            'median_size': float(np.median(counts)),
            'mean_size': float(np.mean(counts)),
            'max_size': int(np.max(counts)),
            'min_size': int(np.min(counts)),
            'singleton_rate': float((counts == 1).sum() / len(counts))
        }
        print(f"\nResolution {r}: {len(unique)} clusters, median {np.median(counts):.1f}, singleton rate {(counts==1).sum()/len(counts):.3f}")
    
    # Zoom coherence (branch purity)
    for i in range(len(resolutions) - 1):
        r_coarse = resolutions[i]
        r_fine = resolutions[i + 1]
        key = f"{r_coarse}_to_{r_fine}"
        zc = compute_zoom_coherence(cluster_results[r_coarse], cluster_results[r_fine], branch_encoded)
        results['zoom_coherence'][key] = zc
        print(f"Zoom {key}: mean_impr={zc['mean_improvement']:.4f}, impr_rate={zc['improvement_rate']:.3f}, n_parents={zc['n_parents_tested']}")
    
    # Nesting
    for i in range(len(resolutions) - 1):
        r_coarse = resolutions[i]
        r_fine = resolutions[i + 1]
        nesting = evaluate_nesting(cluster_results[r_coarse], cluster_results[r_fine])
        results['nesting'][f"{r_coarse}_to_{r_fine}"] = nesting
        print(f"Nesting {r_coarse}->{r_fine}: {nesting:.4f}")
    
    # Fine-level purities
    finest_labels = cluster_results[resolutions[-1]]
    results['fine_branch_purity'] = float(compute_purity(finest_labels, branch_encoded))
    results['fine_legal_area_purity'] = float(compute_purity(finest_labels, legal_area_encoded))
    results['fine_language_purity'] = float(compute_purity(finest_labels, language_encoded))
    print(f"\nFine branch purity: {results['fine_branch_purity']:.4f}")
    print(f"Fine legal_area purity: {results['fine_legal_area_purity']:.4f}")
    print(f"Fine language purity: {results['fine_language_purity']:.4f}")
    
    # Coarse-level purities
    coarsest_labels = cluster_results[resolutions[0]]
    results['coarse_branch_purity'] = float(compute_purity(coarsest_labels, branch_encoded))
    results['coarse_legal_area_purity'] = float(compute_purity(coarsest_labels, legal_area_encoded))
    results['coarse_language_purity'] = float(compute_purity(coarsest_labels, language_encoded))
    print(f"Coarse branch purity: {results['coarse_branch_purity']:.4f}")
    print(f"Coarse legal_area purity: {results['coarse_legal_area_purity']:.4f}")
    print(f"Coarse language purity: {results['coarse_language_purity']:.4f}")
    
    # Overall assessment
    avg_improvement_rate = np.mean([zc['improvement_rate'] for zc in results['zoom_coherence'].values()])
    all_nesting_1 = all(v == 1.0 for v in results['nesting'].values())
    fine_singleton_rate = results['cluster_stats'][str(resolutions[-1])]['singleton_rate']
    coarse_singleton_rate = results['cluster_stats'][str(resolutions[0])]['singleton_rate']
    
    results['summary'] = {
        'avg_improvement_rate': float(avg_improvement_rate),
        'passes_50pct_threshold': avg_improvement_rate > 0.5,
        'perfect_nesting': all_nesting_1,
        'coarse_singleton_rate': coarse_singleton_rate,
        'fine_singleton_rate': fine_singleton_rate,
        'hierarchical_branch_purity': results['fine_branch_purity'],
        'hierarchical_branch_purity_delta': results['fine_branch_purity'] - results['coarse_branch_purity'],
        'validation_verdict': 'PASS' if (avg_improvement_rate > 0.5 and all_nesting_1 and fine_singleton_rate < 0.1) else 'FAIL'
    }
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Avg improvement rate: {avg_improvement_rate:.4f} ({'PASS' if avg_improvement_rate > 0.5 else 'FAIL'} > 0.5)")
    print(f"Perfect nesting: {all_nesting_1}")
    print(f"Coarse singleton rate: {coarse_singleton_rate:.4f}")
    print(f"Fine singleton rate: {fine_singleton_rate:.4f}")
    print(f"Fine branch purity: {results['fine_branch_purity']:.4f}")
    print(f"Branch purity delta: {results['fine_branch_purity'] - results['coarse_branch_purity']:.4f}")
    print(f"Validation verdict: {results['summary']['validation_verdict']}")
    
    # Save results
    output_dir = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/dense_158k_hierarchical_validation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert numpy types
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    with open(output_dir / 'dense_158k_hierarchical_validation.json', 'w') as f:
        json.dump(convert(results), f, indent=2)
    
    print(f"\nResults saved to {output_dir / 'dense_158k_hierarchical_validation.json'}")
    
    return results

if __name__ == "__main__":
    main()
