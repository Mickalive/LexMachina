#!/usr/bin/env python3
"""
Evaluate citation-role embeddings (768-dim, 1200 decisions) with v26 zoom-quality rule.
Uses CONSTRAINED Leiden clustering (min_cluster_size=10) and computes zoom coherence.
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.neighbors import NearestNeighbors
import igraph as ig
import leidenalg as la
import warnings
warnings.filterwarnings('ignore')

# Paths
CITATION_ROLES_DIR = Path("/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/")
METADATA_174K = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl")
OUTPUT_DIR = Path("results/fractal_map/citation_roles_v26_768_20260930")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CITATION_ROLE_FILES = [
    "citing_alpha0.3.npy", "citing_alpha0.5.npy", "citing_alpha0.7.npy",
    "following_alpha0.3.npy", "following_alpha0.5.npy", "following_alpha0.7.npy",
    "criticizing_alpha0.3.npy", "criticizing_alpha0.5.npy", "criticizing_alpha0.7.npy",
    "distinguishing_alpha0.3.npy", "distinguishing_alpha0.5.npy", "distinguishing_alpha0.7.npy",
    "overruling_alpha0.3.npy", "overruling_alpha0.5.npy", "overruling_alpha0.7.npy",
]

RESOLUTIONS = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
MIN_CLUSTER_SIZE = 10
K_NEIGHBORS = 30
SEED = 42

def load_metadata(n_decisions=1200):
    metadata = []
    with open(METADATA_174K, 'r') as f:
        for i, line in enumerate(f):
            if i >= n_decisions:
                break
            metadata.append(json.loads(line.strip()))
    return metadata

def build_knn_graph(embeddings, k=K_NEIGHBORS):
    """Build k-NN graph for Leiden clustering using cosine distance."""
    nbrs = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine', algorithm='brute')
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(len(embeddings)):
        for j_idx in range(1, min(k+1, len(embeddings))):  # skip self
            if j_idx >= len(indices[i]):
                break
            j = indices[i, j_idx]
            w = 1.0 - distances[i, j_idx]
            if w > 0:
                edges.append((i, j))
                weights.append(w)
    
    g = ig.Graph()
    g.add_vertices(len(embeddings))
    g.add_edges(edges)
    g.es['weight'] = weights
    return g

def enforce_min_cluster_size(labels, embeddings, min_size):
    """Merge clusters smaller than min_size into nearest larger cluster by centroid distance."""
    unique, counts = np.unique(labels, return_counts=True)
    small_clusters = unique[counts < min_size]
    large_clusters = unique[counts >= min_size]
    
    if len(small_clusters) == 0 or len(large_clusters) == 0:
        return labels
    
    new_labels = labels.copy()
    
    for small_c in small_clusters:
        small_mask = (labels == small_c)
        small_centroid = embeddings[small_mask].mean(axis=0)
        
        best_dist = float('inf')
        best_large = large_clusters[0]
        for large_c in large_clusters:
            large_mask = (labels == large_c)
            large_centroid = embeddings[large_mask].mean(axis=0)
            dist = np.linalg.norm(small_centroid - large_centroid)
            if dist < best_dist:
                best_dist = dist
                best_large = large_c
        
        new_labels[small_mask] = best_large
    
    # Renumber to consecutive
    unique_new = np.unique(new_labels)
    label_map = {old: new for new, old in enumerate(unique_new)}
    return np.array([label_map[l] for l in new_labels])

def run_constrained_leiden(embeddings, min_cluster_size=MIN_CLUSTER_SIZE, resolutions=RESOLUTIONS):
    """Run constrained Leiden clustering at multiple resolutions."""
    g = build_knn_graph(embeddings)
    
    results = {}
    for res in resolutions:
        partition = la.find_partition(
            g, la.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=res, seed=SEED, n_iterations=-1
        )
        labels = np.array(partition.membership)
        
        # Enforce min_cluster_size
        merged_labels = enforce_min_cluster_size(labels, embeddings, min_cluster_size)
        
        n_clusters = len(np.unique(merged_labels))
        results[res] = {
            'labels': merged_labels,
            'n_clusters': n_clusters,
            'modularity': float(partition.modularity),
            'cluster_sizes': np.bincount(merged_labels).tolist()
        }
        print(f"  Resolution {res}: {n_clusters} clusters (after min_cluster_size={min_cluster_size})")
    
    return results

def compute_zoom_coherence(labels_coarse, labels_fine):
    """Compute zoom coherence: does fine resolution refine coarse clusters meaningfully?"""
    coarse_to_fine = {}
    for c, f in zip(labels_coarse, labels_fine):
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

def evaluate_role(name, embeddings, metadata):
    """Evaluate a single citation-role embedding."""
    print(f"\n{'='*60}")
    print(f"Evaluating {name}")
    print(f"{'='*60}")
    print(f"Embeddings shape: {embeddings.shape}")
    
    results = {
        'role': name,
        'n_decisions': len(embeddings),
        'embedding_dim': embeddings.shape[1],
        'constrained_leiden': None,
        'zoom_coherence': {},
        'v26_zoom_quality': None
    }
    
    # Run CONSTRAINED Leiden clustering
    print(f"Running CONSTRAINED Leiden clustering (min_cluster_size={MIN_CLUSTER_SIZE})...")
    leiden_results = run_constrained_leiden(embeddings, min_cluster_size=MIN_CLUSTER_SIZE)
    results['constrained_leiden'] = {str(k): v for k, v in leiden_results.items()}
    
# Compute zoom coherence between adjacent resolutions
    for i in range(len(RESOLUTIONS) - 1):
        res_coarse = RESOLUTIONS[i]
        res_fine = RESOLUTIONS[i + 1]
        if res_coarse in leiden_results and res_fine in leiden_results:
            zc = compute_zoom_coherence(
                leiden_results[res_coarse]['labels'],
                leiden_results[res_fine]['labels']
            )
            results['zoom_coherence'][f"{res_coarse}_to_{res_fine}"] = zc
            passes = zc['improvement_rate'] > 0.5 and zc['singleton_fraction'] < 0.99
            print(f"  Zoom {res_coarse} -> {res_fine}: improvement_rate={zc['improvement_rate']:.3f}, "
                  f"singleton_frac={zc['singleton_fraction']:.3f}, v26_PASS={passes}")
    
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

def main():
    print("=" * 80)
    print("V26 ZOOM QUALITY EVALUATION - CITATION-ROLE EMBEDDINGS (768-dim, 1200 decisions)")
    print("=" * 80)
    print(f"Min cluster size: {MIN_CLUSTER_SIZE}")
    print(f"K neighbors: {K_NEIGHBORS}")
    print(f"Resolutions: {RESOLUTIONS}")
    print(f"v26 rule: improvement_rate > 0.5 AND singleton_fraction < 0.99")
    print()
    
    # Load metadata
    print("Loading metadata...")
    metadata = load_metadata(1200)
    print(f"Loaded {len(metadata)} decisions")
    
    all_results = {}
    
    for fname in CITATION_ROLE_FILES:
        role_name = fname.replace('.npy', '')
        emb_path = CITATION_ROLES_DIR / fname
        
        if not emb_path.exists():
            print(f"\nWARNING: {emb_path} not found, skipping")
            continue
        
        embeddings = np.load(emb_path)
        
        try:
            all_results[role_name] = evaluate_role(role_name, embeddings, metadata)
        except Exception as e:
            print(f"ERROR evaluating {role_name}: {e}")
            import traceback
            traceback.print_exc()
            all_results[role_name] = {'error': str(e)}
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"citation_roles_v26_768_{timestamp}.json"
    
    # Convert numpy types for JSON serialization
    def convert(obj):
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        else:
            return obj
    
    all_results = convert(all_results)
    
    with open(output_file, 'w') as f:
        json.dump({
            "run_id": f"citation_roles_v26_768_{timestamp}",
            "timestamp": datetime.now().isoformat(),
            "direction_version": 29,
            "hypothesis": "Citation-role embeddings at 1200 scale (768-dim) achieve v26 zoom-quality PASS, confirming evidence-backed zoom path from 1000-scale",
            "frozen_sample": "1200 BGer decisions from 174k corpus (first 1200 by date order)",
            "frozen_metric": "Zoom coherence: improvement_rate > 0.5 AND singleton_fraction < 0.99",
            "methodology": "Constrained Leiden (min_cluster_size=10) at resolutions [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]",
            "results": all_results
        }, f, indent=2)
    
    print(f"\n\nResults saved to: {output_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - Frozen v26 Zoom Quality Rule")
    print("=" * 80)
    
    for role, res in all_results.items():
        if 'error' in res:
            print(f"{role}: ERROR - {res['error']}")
        else:
            v26 = res.get('v26_zoom_quality', {})
            any_pass = v26.get('any_pass', False)
            print(f"{role}: v26_any_pass={any_pass}")
            for detail in v26.get('details', []):
                print(f"  {detail['comparison']}: imp_rate={detail['improvement_rate']:.3f}, "
                      f"singletons={detail['singleton_fraction']:.3f}, PASS={detail['passes']}")
    
    return all_results

if __name__ == "__main__":
    main()