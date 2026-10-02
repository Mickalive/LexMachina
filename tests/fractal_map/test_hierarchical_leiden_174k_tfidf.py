#!/usr/bin/env python3
"""
Hierarchical Leiden validation on all 8 TF-IDF representations at 174k scale.
Tests zoom coherence, fine_branch_purity, and hierarchical structure quality.
"""

import json
import numpy as np
import sys
import os
from pathlib import Path
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Add the product module to path
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

# Load metadata
METADATA_PATH = '/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json'
with open(METADATA_PATH, 'r') as f:
    metadata = json.load(f)

# Create lookup by index
decision_ids = [m['decision_id'] for m in metadata]
branches = [m.get('branch', 'unknown') for m in metadata]
legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
languages = [m.get('language', 'unknown') for m in metadata]
outcomes = [m.get('outcome', 'unknown') for m in metadata]
chambers = [m.get('chamber', 'unknown') for m in metadata]

# Representations to test (from product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings)
REPRESENTATIONS = {
    'cited_decisions_tfidf': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.5': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf_outcome_hybrid_0.5.npy',
    'cited_decisions_tfidf_outcome_hybrid_0.7': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf_outcome_hybrid_0.7.npy',
    'full_text_tfidf_light': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/full_text_tfidf_light.npy',
    'outcome_tfidf': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/outcome_tfidf.npy',
    'regeste_full_text_hybrid_0.5': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/regeste_full_text_hybrid_0.5.npy',
    'regeste_full_text_hybrid_0.7': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/regeste_full_text_hybrid_0.7.npy',
    'regeste_tfidf': '/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/regeste_tfidf.npy',
}

# Verify files exist
for name, path in REPRESENTATIONS.items():
    if not os.path.exists(path):
        print(f"WARNING: {name} not found at {path}")
    else:
        print(f"Found: {name} at {path}")

# Import clustering libraries
try:
    import leidenalg
    import igraph as ig
    LEIDEN_AVAILABLE = True
    print("Leiden/igraph available")
except ImportError:
    LEIDEN_AVAILABLE = False
    print("Leiden/igraph NOT available - will use sklearn fallback")

from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import normalized_mutual_info_score
from sklearn.neighbors import NearestNeighbors

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

def encode_labels(labels):
    """Encode string labels to integers."""
    unique = list(set(labels))
    mapping = {v: i for i, v in enumerate(unique)}
    return np.array([mapping[v] for v in labels])

branch_encoded = encode_labels(branches)
legal_area_encoded = encode_labels(legal_areas)
language_encoded = encode_labels(languages)
outcome_encoded = encode_labels(outcomes)

def build_knn_graph(embeddings, k=15):
    """Build k-NN graph for Leiden clustering."""
    nbrs = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    # Build edge list (skip self-loops)
    edges = []
    weights = []
    n = embeddings.shape[0]
    for i in range(n):
        for j_idx, j in enumerate(indices[i][1:], 1):  # skip self
            w = 1.0 - distances[i][j_idx]  # convert distance to similarity
            if w > 0:
                edges.append((i, j))
                weights.append(w)
    
    # Create igraph
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights
    return g

def constrained_hierarchical_leiden(embeddings, resolutions=[0.25, 0.5, 1.0, 2.0, 3.0], min_cluster_size=5):
    """
    Run constrained hierarchical Leiden clustering.
    Enforces min_cluster_size to prevent over-fragmentation.
    Returns cluster labels at each resolution level.
    """
    if not LEIDEN_AVAILABLE:
        # Fallback: Agglomerative clustering with varying n_clusters
        # Estimate n_clusters from resolution parameter
        n = embeddings.shape[0]
        n_clusters_per_res = [max(int(n / (r * 1000)), 10) for r in resolutions]
        results = {}
        for r, n_clust in zip(resolutions, n_clusters_per_res):
            clustering = AgglomerativeClustering(n_clusters=min(n_clust, n//min_cluster_size), 
                                                  metric='cosine', linkage='average')
            labels = clustering.fit_predict(embeddings)
            # Enforce min_cluster_size by merging small clusters
            unique, counts = np.unique(labels, return_counts=True)
            small_clusters = unique[counts < min_cluster_size]
            for sc in small_clusters:
                labels[labels == sc] = -1  # mark as noise
            # Reassign noise to nearest cluster
            if -1 in labels:
                noise_mask = labels == -1
                non_noise_mask = ~noise_mask
                if non_noise_mask.sum() > 0:
                    nn = NearestNeighbors(n_neighbors=1, metric='cosine', n_jobs=-1)
                    nn.fit(embeddings[non_noise_mask])
                    _, indices = nn.kneighbors(embeddings[noise_mask])
                    labels[noise_mask] = labels[non_noise_mask][indices.flatten()]
            results[r] = labels
        return results
    
    # Build k-NN graph once
    g = build_knn_graph(embeddings, k=15)
    
    results = {}
    prev_labels = None
    
    for resolution in resolutions:
        # Run Leiden
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
                # Try to assign to parent cluster from previous resolution
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
    
    return results

def compute_zoom_coherence(labels_coarse, labels_fine, ground_truth):
    """
    Compute zoom coherence: does finer resolution improve purity?
    Returns mean improvement and improvement rate.
    """
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
            # No refinement
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
        'mean_improvement': np.mean(improvements) if improvements else 0,
        'improvement_rate': improved / total if total > 0 else 0,
        'n_parents_tested': total
    }

def evaluate_representation(name, embeddings_path):
    """Evaluate a single representation with hierarchical Leiden."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {name}")
    print(f"{'='*60}")
    
    # Load embeddings
    embeddings = np.load(embeddings_path)
    print(f"Shape: {embeddings.shape}")
    n = embeddings.shape[0]
    
    # Run constrained hierarchical Leiden
    resolutions = [0.25, 0.5, 1.0, 2.0, 3.0]
    min_cluster_size = max(5, n // 50000)  # Adaptive min cluster size
    print(f"Min cluster size: {min_cluster_size}")
    
    cluster_results = constrained_hierarchical_leiden(embeddings, resolutions, min_cluster_size)
    
    # Compute metrics at each resolution
    results = {
        'name': name,
        'n_decisions': n,
        'embedding_dim': embeddings.shape[1],
        'resolutions': resolutions,
        'min_cluster_size': min_cluster_size,
        'cluster_stats': {},
        'zoom_coherence': {},
        'fine_branch_purity': None,
        'hierarchy_nmi': {}
    }
    
    # Cluster stats at each resolution
    for r in resolutions:
        labels = cluster_results[r]
        unique, counts = np.unique(labels, return_counts=True)
        results['cluster_stats'][str(r)] = {
            'n_clusters': len(unique),
            'cluster_sizes': counts.tolist(),
            'median_size': float(np.median(counts)),
            'mean_size': float(np.mean(counts)),
            'max_size': int(np.max(counts)),
            'min_size': int(np.min(counts)),
            'singleton_rate': float((counts == 1).sum() / len(counts))
        }
        print(f"  Resolution {r}: {len(unique)} clusters, median size {np.median(counts):.1f}, singleton rate {(counts==1).sum()/len(counts):.3f}")
    
    # Zoom coherence (branch purity)
    for i in range(len(resolutions) - 1):
        r_coarse = resolutions[i]
        r_fine = resolutions[i + 1]
        key = f"{r_coarse}_to_{r_fine}"
        zc = compute_zoom_coherence(cluster_results[r_coarse], cluster_results[r_fine], branch_encoded)
        results['zoom_coherence'][key] = zc
        print(f"  Zoom {key}: mean_impr={zc['mean_improvement']:.4f}, impr_rate={zc['improvement_rate']:.3f}")
    
    # Fine branch purity (at finest resolution)
    finest_labels = cluster_results[resolutions[-1]]
    fine_branch_purity = compute_purity(finest_labels, branch_encoded)
    results['fine_branch_purity'] = float(fine_branch_purity)
    print(f"  Fine branch purity: {fine_branch_purity:.4f}")
    
    # Hierarchy NMI (normalized mutual information between levels)
    for i in range(len(resolutions) - 1):
        r_coarse = resolutions[i]
        r_fine = resolutions[i + 1]
        nmi = normalized_mutual_info_score(cluster_results[r_coarse], cluster_results[r_fine])
        results['hierarchy_nmi'][f"{r_coarse}_to_{r_fine}"] = float(nmi)
        print(f"  NMI {r_coarse}->{r_fine}: {nmi:.4f}")
    
    # Also compute legal_area purity at finest level
    fine_legal_area_purity = compute_purity(finest_labels, legal_area_encoded)
    results['fine_legal_area_purity'] = float(fine_legal_area_purity)
    print(f"  Fine legal_area purity: {fine_legal_area_purity:.4f}")
    
    # Language purity at finest level
    fine_language_purity = compute_purity(finest_labels, language_encoded)
    results['fine_language_purity'] = float(fine_language_purity)
    print(f"  Fine language purity: {fine_language_purity:.4f}")
    
    return results, cluster_results

# Run evaluation on all representations
all_results = {}
all_cluster_labels = {}

for name, path in REPRESENTATIONS.items():
    if os.path.exists(path):
        try:
            results, labels = evaluate_representation(name, path)
            all_results[name] = results
            all_cluster_labels[name] = labels
        except Exception as e:
            print(f"ERROR evaluating {name}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"SKIPPING {name}: file not found")

# Save results
output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map')
output_dir.mkdir(parents=True, exist_ok=True)

with open(output_dir / 'hierarchical_leiden_174k_tfidf_all_modes.json', 'w') as f:
    # Convert numpy types to native Python
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
    
    json.dump(convert(all_results), f, indent=2)

print(f"\n\nResults saved to {output_dir / 'hierarchical_leiden_174k_tfidf_all_modes.json'}")

# Summary table
print("\n" + "="*80)
print("SUMMARY: Hierarchical Leiden on 8 TF-IDF Representations at 174k")
print("="*80)
print(f"{'Representation':<45} {'Fine Branch Purity':>18} {'Fine LegalArea':>15} {'Improvement Rate (avg)':>22}")
print("-"*100)
for name, res in all_results.items():
    avg_impr_rate = np.mean([zc['improvement_rate'] for zc in res['zoom_coherence'].values()])
    print(f"{name:<45} {res['fine_branch_purity']:>18.4f} {res['fine_legal_area_purity']:>15.4f} {avg_impr_rate:>22.3f}")

# Hierarchical_v1 protocol check
print("\n" + "="*80)
print("HIERARCHICAL_V1 PROTOCOL CHECK (fine_branch_purity > 0.5)")
print("="*80)
for name, res in all_results.items():
    status = "PASS" if res['fine_branch_purity'] > 0.5 else "FAIL"
    print(f"  {name:<45} fine_branch_purity={res['fine_branch_purity']:.4f} -> {status}")

print("\nDone!")