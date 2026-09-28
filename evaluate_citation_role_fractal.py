#!/usr/bin/env python3
"""
Evaluate citation-role embeddings at 1000-scale with proper fractal-map metrics.
Tests hierarchical Leiden clustering at multiple resolutions and computes zoom coherence.
This addresses the frozen v26 zoom-quality rule: monotonic zoom refinement required.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
import umap
import hdbscan
try:
    import leidenalg
    import igraph as ig
    LEIDEN_AVAILABLE = True
except ImportError:
    LEIDEN_AVAILABLE = False
    print("WARNING: leidenalg not available, using HDBSCAN only")

# Paths
BASE = Path("/tmp/lex_accepted/product/product/results/fractal_map")
ROLES = ["citing_alpha0.3", "following_alpha0.3", "criticizing_alpha0.3"]

# Frozen v26 zoom-quality rule: improvement_rate > 0.5 at fine resolutions
# and NO severe over-fragmentation (singleton_fraction < 0.99 at fine resolutions)

def load_embeddings(role_dir):
    """Load embeddings and metadata for a citation role."""
    emb_path = role_dir / "embeddings.npy"
    meta_path = role_dir / "metadata.json"
    
    embeddings = np.load(emb_path)
    with open(meta_path) as f:
        metadata = json.load(f)
    
    return embeddings, metadata

def run_leiden_clustering(embeddings, resolutions=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]):
    """Run Leiden clustering at multiple resolutions using k-NN graph."""
    if not LEIDEN_AVAILABLE:
        return None
    
    # Build k-NN graph
    n_neighbors = min(30, len(embeddings) - 1)
    nn = NearestNeighbors(n_neighbors=n_neighbors, metric='cosine')
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)
    
    # Build igraph
    edges = []
    weights = []
    for i in range(len(embeddings)):
        for j, dist in zip(indices[i], distances[i]):
            if i < j:  # undirected
                edges.append((i, j))
                weights.append(1.0 - dist)  # similarity as weight
    
    g = ig.Graph(edges=edges, directed=False)
    g.es['weight'] = weights
    
    results = {}
    for res in resolutions:
        partition = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=res, seed=42
        )
        labels = np.array(partition.membership)
        n_clusters = len(set(labels))
        results[res] = {
            'labels': labels,
            'n_clusters': n_clusters,
            'modularity': partition.modularity,
            'cluster_sizes': np.bincount(labels)
        }
    
    return results

def run_hdbscan_clustering(embeddings, min_cluster_sizes=[5, 10, 15, 20, 30, 50]):
    """Run HDBSCAN at multiple min_cluster_size settings."""
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
        n_noise = np.sum(labels == -1)
        results[mcs] = {
            'labels': labels,
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'cluster_sizes': np.bincount(labels[labels >= 0]) if n_clusters > 0 else np.array([]),
            'probabilities': clusterer.probabilities_
        }
    return results

def compute_zoom_coherence(labels_coarse, labels_fine, metadata_path):
    """Compute zoom coherence: does fine resolution refine coarse clusters meaningfully?"""
    # Load decision metadata for branch/legal_area labels
    with open(metadata_path) as f:
        meta = json.load(f)
    
    # We need branch/legal_area labels - try to get from the 174k metadata
    # For now, compute structural zoom coherence (cluster nesting)
    
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
        
        # Coarse purity: how pure is the coarse cluster?
        coarse_purity = max(np.bincount(fine_labels)) / len(fine_labels)
        coarse_purities.append(coarse_purity)
        
        # Fine purity: average purity of fine clusters within this coarse cluster
        fine_counts = np.bincount(fine_labels)
        fine_purity = np.mean(fine_counts / len(fine_labels)) if len(fine_counts) > 0 else 0
        fine_purities.append(fine_purity)
        
        if fine_purity > coarse_purity:
            improvements += 1
        elif fine_purity < coarse_purity:
            deteriorations += 1
        else:
            no_change += 1
    
    if not coarse_purities:
        return {
            'coarse_purity_mean': 0,
            'fine_purity_mean': 0,
            'improvement_rate': 0,
            'improvements': 0,
            'deteriorations': 0,
            'no_change': 0,
            'singleton_fraction': 1.0
        }
    
    # Compute singleton fraction at fine resolution
    unique_fine, counts = np.unique(labels_fine, return_counts=True)
    singleton_fraction = np.sum(counts == 1) / len(labels_fine)
    
    return {
        'coarse_purity_mean': float(np.mean(coarse_purities)),
        'fine_purity_mean': float(np.mean(fine_purities)),
        'improvement_rate': improvements / (improvements + deteriorations + no_change) if (improvements + deteriorations + no_change) > 0 else 0,
        'improvements': improvements,
        'deteriorations': deteriorations,
        'no_change': no_change,
        'singleton_fraction': float(singleton_fraction)
    }

def evaluate_role(role_name):
    """Evaluate a single citation role."""
    print(f"\n{'='*60}")
    print(f"Evaluating {role_name}")
    print(f"{'='*60}")
    
    role_dir = BASE / role_name
    embeddings, metadata = load_embeddings(role_dir)
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Metadata: {metadata}")
    
    results = {
        'role': role_name,
        'n_decisions': len(embeddings),
        'embedding_dim': embeddings.shape[1],
        'metadata': metadata,
        'leiden': None,
        'hdbscan': None,
        'zoom_coherence': {}
    }
    
    # Run Leiden clustering
    if LEIDEN_AVAILABLE:
        print("Running Leiden clustering...")
        leiden_results = run_leiden_clustering(embeddings)
        if leiden_results:
            results['leiden'] = {str(k): {**v, 'labels': v['labels'].tolist(), 'cluster_sizes': v['cluster_sizes'].tolist()} for k, v in leiden_results.items()}
            
            # Compute zoom coherence between adjacent resolutions
            resolutions = sorted([float(k) for k in leiden_results.keys()])
            for i in range(len(resolutions) - 1):
                res_coarse = str(resolutions[i])
                res_fine = str(resolutions[i + 1])
                if res_coarse in leiden_results and res_fine in leiden_results:
                    zc = compute_zoom_coherence(
                        leiden_results[res_coarse]['labels'],
                        leiden_results[res_fine]['labels'],
                        metadata_path=BASE.parent.parent / "evaluation" / "data" / "174k" / "metadata_174k.json"
                    )
                    results['zoom_coherence'][f"{res_coarse}_to_{res_fine}"] = zc
                    print(f"  Zoom {res_coarse} -> {res_fine}: improvement_rate={zc['improvement_rate']:.3f}, singleton_frac={zc['singleton_fraction']:.3f}")
    
    # Run HDBSCAN
    print("Running HDBSCAN clustering...")
    hdbscan_results = run_hdbscan_clustering(embeddings)
    results['hdbscan'] = {str(k): {**v, 'labels': v['labels'].tolist(), 'cluster_sizes': v['cluster_sizes'].tolist()} for k, v in hdbscan_results.items()}
    
    # Check frozen v26 zoom-quality rule
    # Rule: improvement_rate > 0.5 AND singleton_fraction < 0.99 at fine resolutions
    zoom_passes = []
    for key, zc in results['zoom_coherence'].items():
        passes = zc['improvement_rate'] > 0.5 and zc['singleton_fraction'] < 0.99
        zoom_passes.append({
            'comparison': key,
            'passes': passes,
            'improvement_rate': zc['improvement_rate'],
            'singleton_fraction': zc['singleton_fraction']
        })
        print(f"  {key}: passes_v26_rule={passes} (improvement={zc['improvement_rate']:.3f}, singletons={zc['singleton_fraction']:.3f})")
    
    results['v26_zoom_quality'] = {
        'any_pass': any(z['passes'] for z in zoom_passes),
        'details': zoom_passes
    }
    
    return results

def convert_to_serializable(obj):
    """Recursively convert numpy types to Python native types."""
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
    
    # Convert to serializable
    all_results = convert_to_serializable(all_results)
    
    # Save results
    output_path = BASE / "citation_role_fractal_evaluation.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for role, res in all_results.items():
        if 'error' in res:
            print(f"{role}: ERROR - {res['error']}")
        else:
            v26 = res.get('v26_zoom_quality', {})
            print(f"{role}: v26_pass={v26.get('any_pass', False)}")
            for detail in v26.get('details', []):
                print(f"  {detail['comparison']}: imp_rate={detail['improvement_rate']:.3f}, singletons={detail['singleton_fraction']:.3f}, PASS={detail['passes']}")
    
    return all_results

if __name__ == "__main__":
    main()