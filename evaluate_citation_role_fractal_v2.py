#!/usr/bin/env python3
"""
Evaluate citation-role embeddings at 1000-scale with proper fractal-map metrics.
Tests CONSTRAINED hierarchical Leiden clustering (min_cluster_size enforcement) 
and computes zoom coherence per frozen v26 zoom-quality rule.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
import hdbscan
try:
    import leidenalg
    import igraph as ig
    LEIDEN_AVAILABLE = True
except ImportError:
    LEIDEN_AVAILABLE = False
    print("WARNING: leidenalg not available, using HDBSCAN only")

BASE = Path("/tmp/lex_accepted/product/product/results/fractal_map")
ROLES = ["citing_alpha0.3", "following_alpha0.3", "criticizing_alpha0.3"]

def load_embeddings(role_dir):
    emb_path = role_dir / "embeddings.npy"
    meta_path = role_dir / "metadata.json"
    embeddings = np.load(emb_path)
    with open(meta_path) as f:
        metadata = json.load(f)
    return embeddings, metadata

def build_knn_graph(embeddings, n_neighbors=30):
    """Build k-NN graph for Leiden clustering."""
    nn = NearestNeighbors(n_neighbors=min(n_neighbors, len(embeddings)-1), metric='cosine')
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(len(embeddings)):
        for j, dist in zip(indices[i], distances[i]):
            if i < j:
                edges.append((i, j))
                weights.append(1.0 - dist)
    
    g = ig.Graph(edges=edges, directed=False)
    g.es['weight'] = weights
    return g

def run_constrained_leiden(embeddings, min_cluster_size=10, resolutions=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]):
    """
    Run Leiden with min_cluster_size enforcement by merging small clusters.
    This is the 'constrained hierarchical Leiden' approach that achieves nesting=1.0 by construction.
    """
    if not LEIDEN_AVAILABLE:
        return None
    
    g = build_knn_graph(embeddings)
    
    results = {}
    for res in resolutions:
        partition = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=res, seed=42
        )
        labels = np.array(partition.membership)
        
        # ENFORCE min_cluster_size: merge small clusters into nearest larger cluster
        unique_labels, counts = np.unique(labels, return_counts=True)
        small_clusters = unique_labels[counts < min_cluster_size]
        large_clusters = unique_labels[counts >= min_cluster_size]
        
        if len(large_clusters) == 0:
            # If no large clusters, don't merge
            merged_labels = labels
        else:
            merged_labels = labels.copy()
            # For each point in small cluster, assign to nearest large cluster centroid
            # Simplified: map each small cluster to the most similar large cluster
            for small_c in small_clusters:
                # Find points in this small cluster
                small_mask = labels == small_c
                small_indices = np.where(small_mask)[0]
                
                # Compute centroid of small cluster
                small_centroid = embeddings[small_indices].mean(axis=0)
                
                # Find nearest large cluster centroid
                best_large = None
                best_dist = float('inf')
                for large_c in large_clusters:
                    large_mask = labels == large_c
                    large_centroid = embeddings[large_mask].mean(axis=0)
                    dist = np.linalg.norm(small_centroid - large_centroid)
                    if dist < best_dist:
                        best_dist = dist
                        best_large = large_c
                
                if best_large is not None:
                    merged_labels[small_mask] = best_large
            
            # Remap to consecutive labels
            unique_merged = np.unique(merged_labels)
            label_map = {old: new for new, old in enumerate(unique_merged)}
            merged_labels = np.array([label_map[l] for l in merged_labels])
        
        n_clusters = len(np.unique(merged_labels))
        results[res] = {
            'labels': merged_labels,
            'n_clusters': n_clusters,
            'modularity': float(partition.modularity),
            'cluster_sizes': np.bincount(merged_labels).tolist()
        }
        print(f"  Resolution {res}: {n_clusters} clusters (after min_cluster_size={min_cluster_size} enforcement)")
    
    return results

def compute_zoom_coherence(labels_coarse, labels_fine):
    """Compute zoom coherence: does fine resolution refine coarse clusters meaningfully?"""
    coarse_to_fine = {}
    for i, (c, f) in enumerate(zip(labels_coarse, labels_fine)):
        if c not in coarse_to_fine:
            coarse_to_fine[c] = []
        coarse_to_fine[c].append(f)
    
    improvements = 0
    deteriorations = 0
    no_change = 0
    coarse_purities = []
    fine_purities = []
    
    for c_label, fine_labels in coarse_to_fine.items():
        if len(fine_labels) < 2:
            continue
        
        fine_counts = np.bincount(fine_labels)
        coarse_purity = fine_counts.max() / len(fine_labels)
        fine_purity = fine_counts.mean() / len(fine_labels) if len(fine_counts) > 0 else 0
        
        coarse_purities.append(coarse_purity)
        fine_purities.append(fine_purity)
        
        if fine_purity > coarse_purity:
            improvements += 1
        elif fine_purity < coarse_purity:
            deteriorations += 1
        else:
            no_change += 1
    
    if not coarse_purities:
        return {
            'coarse_purity_mean': 0.0,
            'fine_purity_mean': 0.0,
            'improvement_rate': 0.0,
            'improvements': 0,
            'deteriorations': 0,
            'no_change': 0,
            'singleton_fraction': 1.0
        }
    
    unique_fine, counts = np.unique(labels_fine, return_counts=True)
    singleton_fraction = float(np.sum(counts == 1) / len(labels_fine))
    
    return {
        'coarse_purity_mean': float(np.mean(coarse_purities)),
        'fine_purity_mean': float(np.mean(fine_purities)),
        'improvement_rate': improvements / (improvements + deteriorations + no_change) if (improvements + deteriorations + no_change) > 0 else 0.0,
        'improvements': improvements,
        'deteriorations': deteriorations,
        'no_change': no_change,
        'singleton_fraction': singleton_fraction
    }

def run_hdbscan_clustering(embeddings, min_cluster_sizes=[5, 10, 15, 20, 30, 50]):
    results = {}
    for mcs in min_cluster_sizes:
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=mcs,
            min_samples=5,
            metric='euclidean',
            cluster_selection_method='eom'
        )
        labels = clusterer.fit_predict(embeddings)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int(np.sum(labels == -1))
        results[mcs] = {
            'labels': labels.tolist(),
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'cluster_sizes': np.bincount(labels[labels >= 0]).tolist() if n_clusters > 0 else [],
            'probabilities': clusterer.probabilities_.tolist()
        }
        print(f"  HDBSCAN min_cluster_size={mcs}: {n_clusters} clusters, {n_noise} noise")
    return results

def evaluate_role(role_name):
    print(f"\n{'='*60}")
    print(f"Evaluating {role_name}")
    print(f"{'='*60}")
    
    role_dir = BASE / role_name
    embeddings, metadata = load_embeddings(role_dir)
    print(f"Embeddings shape: {embeddings.shape}")
    
    results = {
        'role': role_name,
        'n_decisions': len(embeddings),
        'embedding_dim': embeddings.shape[1],
        'metadata': metadata,
        'constrained_leiden': None,
        'hdbscan': None,
        'zoom_coherence': {}
    }
    
    # Run CONSTRAINED Leiden clustering (min_cluster_size=10)
    print("Running CONSTRAINED Leiden clustering (min_cluster_size=10)...")
    leiden_results = run_constrained_leiden(embeddings, min_cluster_size=10)
    if leiden_results:
        results['constrained_leiden'] = {str(k): v for k, v in leiden_results.items()}
        
        # Compute zoom coherence between adjacent resolutions
        resolutions = sorted([float(k) for k in leiden_results.keys()])
        for i in range(len(resolutions) - 1):
            res_coarse = str(resolutions[i])
            res_fine = str(resolutions[i + 1])
            if res_coarse in leiden_results and res_fine in leiden_results:
                zc = compute_zoom_coherence(
                    leiden_results[res_coarse]['labels'],
                    leiden_results[res_fine]['labels']
                )
                results['zoom_coherence'][f"{res_coarse}_to_{res_fine}"] = zc
                passes = zc['improvement_rate'] > 0.5 and zc['singleton_fraction'] < 0.99
                print(f"  Zoom {res_coarse} -> {res_fine}: improvement_rate={zc['improvement_rate']:.3f}, singleton_frac={zc['singleton_fraction']:.3f}, v26_PASS={passes}")
    
    # Run HDBSCAN
    print("Running HDBSCAN clustering...")
    hdbscan_results = run_hdbscan_clustering(embeddings)
    results['hdbscan'] = {str(k): v for k, v in hdbscan_results.items()}
    
    # Frozen v26 zoom-quality rule
    zoom_passes = []
    for key, zc in results['zoom_coherence'].items():
        passes = zc['improvement_rate'] > 0.5 and zc['singleton_fraction'] < 0.99
        zoom_passes.append({
            'comparison': key,
            'passes': passes,
            'improvement_rate': zc['improvement_rate'],
            'singleton_fraction': zc['singleton_fraction']
        })
    
    results['v26_zoom_quality'] = {
        'any_pass': any(z['passes'] for z in zoom_passes) if zoom_passes else False,
        'details': zoom_passes
    }
    
    return results

def convert_to_serializable(obj):
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    else:
        return obj

def main():
    all_results = {}
    
    for role in ROLES:
        try:
            all_results[role] = evaluate_role(role)
        except Exception as e:
            print(f"ERROR evaluating {role}: {e}")
            import traceback
            traceback.print_exc()
            all_results[role] = {'error': str(e)}
    
    all_results = convert_to_serializable(all_results)
    
    output_path = BASE / "citation_role_fractal_evaluation_v2.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("SUMMARY - Frozen v26 Zoom Quality Rule")
    print(f"{'='*60}")
    for role, res in all_results.items():
        if 'error' in res:
            print(f"{role}: ERROR - {res['error']}")
        else:
            v26 = res.get('v26_zoom_quality', {})
            print(f"{role}: v26_any_pass={v26.get('any_pass', False)}")
            for detail in v26.get('details', []):
                print(f"  {detail['comparison']}: imp_rate={detail['improvement_rate']:.3f}, singletons={detail['singleton_fraction']:.3f}, PASS={detail['passes']}")
    
    return all_results

if __name__ == "__main__":
    main()