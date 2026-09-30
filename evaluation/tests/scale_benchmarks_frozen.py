#!/usr/bin/env python3
"""
Scale benchmarks with frozen PCA components.
Tests representation stability when PCA is fit on full corpus and applied to subsets.
This simulates the production scenario where we compute PCA once on full corpus
and then apply it to incremental updates.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans


def load_baseline_embeddings() -> Tuple[np.ndarray, List[Dict]]:
    """Load the baseline 768-dim embeddings and metadata for 1000 decisions."""
    embeddings_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy')
    metadata_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json')
    
    embeddings = np.load(embeddings_path)
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return embeddings, metadata


def compute_frozen_pipeline(embeddings: np.ndarray, 
                            pca_debias: PCA, 
                            pca_64: PCA) -> np.ndarray:
    """Apply frozen PCA pipeline to embeddings."""
    # PCA debiasing
    debias_component = pca_debias.transform(embeddings)
    debiased = embeddings - debias_component @ pca_debias.components_
    
    # Project to 64-dim
    debiased_64 = pca_64.transform(debiased)
    debiased_64 = normalize(debiased_64, norm='l2')
    
    return debiased_64


def position_drift(embeddings_small: np.ndarray, embeddings_large: np.ndarray, 
                   common_indices: List[int]) -> Dict:
    """Measure position drift of common decisions."""
    old_positions = embeddings_small[common_indices]
    new_positions = embeddings_large[:len(common_indices)]
    
    sims = np.sum(old_positions * new_positions, axis=1)
    
    return {
        'mean_cosine_similarity': float(np.mean(sims)),
        'std_cosine_similarity': float(np.std(sims)),
        'min_cosine_similarity': float(np.min(sims)),
        'pct_below_0.9': float(np.mean(sims < 0.9) * 100),
        'pct_below_0.8': float(np.mean(sims < 0.8) * 100),
        'pct_below_0.5': float(np.mean(sims < 0.5) * 100)
    }


def neighbor_preservation(embeddings_small: np.ndarray, embeddings_large: np.ndarray,
                          common_indices: List[int], k: int = 10) -> Dict:
    """Measure neighbor preservation."""
    n_common = len(common_indices)
    
    nn_small = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn_small.fit(embeddings_small)
    _, indices_small = nn_small.kneighbors(embeddings_small[common_indices])
    neighbors_small = indices_small[:, 1:]
    
    nn_large = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn_large.fit(embeddings_large)
    _, indices_large = nn_large.kneighbors(embeddings_large[:n_common])
    neighbors_large = indices_large[:, 1:]
    
    preservation_rates = []
    for i in range(n_common):
        set_small = set(neighbors_small[i])
        set_large = set(neighbors_large[i])
        preserved = len(set_small & set_large) / k
        preservation_rates.append(preserved)
    
    return {
        'mean_preservation_rate': float(np.mean(preservation_rates)),
        'std_preservation_rate': float(np.std(preservation_rates)),
        'min_preservation_rate': float(np.min(preservation_rates)),
        'pct_above_0.5': float(np.mean(np.array(preservation_rates) > 0.5) * 100),
        'pct_above_0.8': float(np.mean(np.array(preservation_rates) > 0.8) * 100)
    }


def cluster_stability(embeddings_small: np.ndarray, embeddings_large: np.ndarray,
                      common_indices: List[int], n_clusters: int = 10) -> Dict:
    """Measure cluster assignment stability."""
    n_common = len(common_indices)
    
    kmeans_small = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels_small = kmeans_small.fit_predict(embeddings_small[common_indices])
    
    kmeans_large = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels_large = kmeans_large.fit_predict(embeddings_large[:n_common])
    
    nmi = normalized_mutual_info_score(labels_small, labels_large)
    ari = adjusted_rand_score(labels_small, labels_large)
    
    return {
        'nmi': float(nmi),
        'ari': float(ari),
        'n_clusters': n_clusters
    }


def run_frozen_scale_benchmark(embeddings: np.ndarray, metadata: List[Dict], 
                               sizes: List[int] = None) -> Dict:
    """
    Run scale benchmark with FROZEN PCA components (fit on full corpus).
    """
    if sizes is None:
        sizes = [200, 400, 600, 800, 1000]
    
    # Shuffle with fixed seed
    np.random.seed(42)
    indices = np.arange(len(embeddings))
    np.random.shuffle(indices)
    
    # FIT PCA ON FULL CORPUS (this is the key - frozen components)
    full_embeddings = embeddings[indices]
    
    # Fit debias PCA on full corpus
    pca_debias = PCA(n_components=1, random_state=42)
    pca_debias.fit(full_embeddings)
    
    # Compute debiased full embeddings
    debias_comp_full = pca_debias.transform(full_embeddings)
    debiased_full = full_embeddings - debias_comp_full @ pca_debias.components_
    
    # Fit 64-dim PCA on full debiased
    pca_64 = PCA(n_components=64, random_state=42)
    pca_64.fit(debiased_full)
    
    print(f"Frozen PCA components fitted on full corpus ({len(full_embeddings)} decisions)")
    print(f"  Debias PCA explained variance: {pca_debias.explained_variance_ratio_[0]:.4f}")
    print(f"  64-dim PCA cumulative variance: {np.sum(pca_64.explained_variance_ratio_):.4f}")
    
    # Compute full representation (reference)
    full_representation = compute_frozen_pipeline(full_embeddings, pca_debias, pca_64)
    
    results = {
        'corpus_sizes': sizes,
        'max_size': len(embeddings),
        'method': 'frozen_pca_fit_on_full',
        'growth_steps': []
    }
    
    for size in sizes:
        if size > len(embeddings):
            continue
            
        subset_indices = indices[:size]
        subset_embeddings = embeddings[subset_indices]
        
        # Apply FROZEN pipeline
        representation = compute_frozen_pipeline(subset_embeddings, pca_debias, pca_64)
        
        step_result = {
            'corpus_size': size,
            'representation_shape': representation.shape
        }
        
        # Compare to full representation for the common decisions
        common_indices = list(range(size))
        step_result['vs_full_position_drift'] = position_drift(
            representation, full_representation, common_indices)
        step_result['vs_full_neighbor_preservation_k10'] = neighbor_preservation(
            representation, full_representation, common_indices, k=10)
        step_result['vs_full_cluster_stability_k10'] = cluster_stability(
            representation, full_representation, common_indices, n_clusters=10)
        
        results['growth_steps'].append(step_result)
    
    return results


def run_recomputed_scale_benchmark(embeddings: np.ndarray, metadata: List[Dict], 
                                   sizes: List[int] = None) -> Dict:
    """
    Run scale benchmark with RECOMPUTED PCA (current behavior - fit on each subset).
    This is the baseline to compare against frozen PCA.
    """
    if sizes is None:
        sizes = [200, 400, 600, 800, 1000]
    
    np.random.seed(42)
    indices = np.arange(len(embeddings))
    np.random.shuffle(indices)
    
    results = {
        'corpus_sizes': sizes,
        'max_size': len(embeddings),
        'method': 'recomputed_pca_per_subset',
        'growth_steps': []
    }
    
    prev_representation = None
    prev_size = 0
    
    for size in sizes:
        if size > len(embeddings):
            continue
            
        subset_indices = indices[:size]
        subset_embeddings = embeddings[subset_indices]
        
        # Recompute PCA on this subset
        representation = compute_representation(subset_embeddings)
        
        step_result = {
            'corpus_size': size,
            'representation_shape': representation.shape
        }
        
        if prev_representation is not None:
            common_indices = list(range(prev_size))
            step_result['vs_prev_position_drift'] = position_drift(
                prev_representation, representation, common_indices)
            step_result['vs_prev_neighbor_preservation_k10'] = neighbor_preservation(
                prev_representation, representation, common_indices, k=10)
            step_result['vs_prev_cluster_stability_k10'] = cluster_stability(
                prev_representation, representation, common_indices, n_clusters=10)
        
        results['growth_steps'].append(step_result)
        prev_representation = representation
        prev_size = size
    
    return results


def compute_representation(embeddings_subset: np.ndarray) -> np.ndarray:
    """Recompute debiased_citation_blended from scratch on subset."""
    pca_debias = PCA(n_components=1, random_state=42)
    debias_component = pca_debias.fit_transform(embeddings_subset)
    debiased = embeddings_subset - debias_component @ pca_debias.components_
    
    pca_64 = PCA(n_components=64, random_state=42)
    debiased_64 = pca_64.fit_transform(debiased)
    return normalize(debiased_64, norm='l2')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/scale_benchmark_frozen_results.json')
    parser.add_argument('--sizes', nargs='+', type=int, default=[200, 400, 600, 800, 1000])
    args = parser.parse_args()
    
    print("Loading baseline embeddings...")
    embeddings, metadata = load_baseline_embeddings()
    print(f"Loaded {len(embeddings)} decisions, {embeddings.shape[1]} dimensions")
    
    print("\n=== FROZEN PCA (production mode) ===")
    frozen_results = run_frozen_scale_benchmark(embeddings, metadata, args.sizes)
    
    print("\n=== RECOMPUTED PCA (current dev mode) ===")
    recomputed_results = run_recomputed_scale_benchmark(embeddings, metadata, args.sizes)
    
    # Compare
    combined = {
        'frozen_pca': frozen_results,
        'recomputed_pca': recomputed_results,
        'comparison': {}
    }
    
    print("\n=== COMPARISON AT 1000 DECISIONS ===")
    for step_f, step_r in zip(frozen_results['growth_steps'], recomputed_results['growth_steps']):
        size = step_f['corpus_size']
        if 'vs_full_position_drift' in step_f and 'vs_prev_position_drift' in step_r:
            frozen_drift = step_f['vs_full_position_drift']['mean_cosine_similarity']
            recomputed_drift = step_r['vs_prev_position_drift']['mean_cosine_similarity']
            combined['comparison'][f'size_{size}'] = {
                'frozen_vs_full_mean_sim': frozen_drift,
                'recomputed_vs_prev_mean_sim': recomputed_drift,
                'frozen_better_by': frozen_drift - recomputed_drift
            }
            print(f"  Size {size}: Frozen vs Full = {frozen_drift:.4f}, Recomputed vs Prev = {recomputed_drift:.4f}, Diff = {frozen_drift - recomputed_drift:.4f}")
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(combined, f, indent=2)
    
    print(f"\nResults saved to {output_path}")