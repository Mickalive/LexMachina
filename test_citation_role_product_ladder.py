#!/usr/bin/env python3
"""
Test citation-role embeddings with the product's resolution ladder
to validate the ZQ scores mentioned in factory direction v28.
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


def build_knn_graph(embeddings: np.ndarray, k: int = 30, metric: str = 'cosine') -> ig.Graph:
    """Build k-NN graph from embeddings for Leiden clustering."""
    n = embeddings.shape[0]
    nbrs = NearestNeighbors(n_neighbors=min(k+1, n), metric=metric, n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(n):
        for j, dist in zip(indices[i], distances[i]):
            if i < j:  # undirected
                if metric == 'cosine':
                    weight = 1.0 - dist
                else:
                    weight = 1.0 / (1.0 + dist)
                if weight > 0:
                    edges.append((i, j))
                    weights.append(weight)
    
    g = ig.Graph(edges=edges, directed=False)
    g.es['weight'] = weights
    return g


def run_leiden_at_resolutions(embeddings: np.ndarray, 
                               resolutions: List[float],
                               k: int = 30,
                               min_cluster_size: int = 1) -> Dict:
    """Run Leiden clustering at specific resolutions (product ladder)."""
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    results = {}
    for res in resolutions:
        partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                       weights='weight', resolution_parameter=res, seed=42)
        labels = np.array(partition.membership)
        
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


def compute_zoom_coherence_v2(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> Dict:
    """Compute zoom coherence per product's method (per-coarse-cluster)."""
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
            'no_change': 0
        }
    
    return {
        'coarse_purity_mean': float(np.mean(coarse_purities)),
        'fine_purity_mean': float(np.mean(fine_purities)),
        'improvement_rate': improvements / (improvements + deteriorations + no_change) if (improvements + deteriorations + no_change) > 0 else 0.0,
        'improvements': improvements,
        'deteriorations': deteriorations,
        'no_change': no_change
    }


def load_metadata_for_citation_role(role: str, n_decisions: int) -> List[Dict]:
    """Load metadata for citation role embeddings."""
    with open('/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_fixed/citation_roles_fixed_sample.json', 'r') as f:
        sample = json.load(f)
    
    seen = set()
    source_decisions = []
    for s in sample:
        sd = s['source_decision']
        if sd not in seen:
            seen.add(sd)
            source_decisions.append(sd)
            if len(source_decisions) >= n_decisions:
                break
    
    metadata = []
    for sd in source_decisions:
        s = next((x for x in sample if x['source_decision'] == sd), None)
        if s:
            metadata.append({
                'decision_id': s['source_decision'],
                'language': s.get('language', 'de'),
                'branch': 'strafrecht',
                'legal_area': 'Strafprozess',
                'chamber': 'II. Strafrechtliche Abteilung'
            })
        else:
            metadata.append({'decision_id': sd, 'language': 'de', 'branch': 'unknown', 'legal_area': 'unknown', 'chamber': 'unknown'})
    
    while len(metadata) < n_decisions:
        metadata.append({'decision_id': f'pad_{len(metadata)}', 'language': 'de', 'branch': 'unknown', 'legal_area': 'unknown', 'chamber': 'unknown'})
    
    return metadata[:n_decisions]


def main():
    # Product resolution ladder
    product_resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    
    # Citation roles
    roles = ['citing', 'following', 'criticizing', 'all_weighted']
    
    print(f"Testing citation-role embeddings with product resolution ladder: {product_resolutions}")
    print(f"k=30, min_cluster_size=1 (product settings)")
    
    all_results = {}
    
    for role in roles:
        print(f"\n{'='*70}")
        print(f"Testing citation_role_{role}")
        print(f"{'='*70}")
        
        path = f'/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_fixed/citation_role_{role}_fixed.npy'
        embeddings = np.load(path)
        print(f"Embeddings shape: {embeddings.shape}")
        
        metadata = load_metadata_for_citation_role(role, embeddings.shape[0])
        
        # Run Leiden at product resolutions
        results = run_leiden_at_resolutions(embeddings, product_resolutions, k=30, min_cluster_size=1)
        
        # Print resolution ladder
        print(f"\nResolution ladder:")
        for res in product_resolutions:
            r = results[res]
            print(f"  Res {res}: n_clusters={r['n_clusters']}, median_size={r['median_size']:.1f}, singleton_frac={r['singleton_fraction']:.3f}")
        
        # Compute zoom coherence between adjacent resolutions
        zoom_results = {}
        for i in range(len(product_resolutions) - 1):
            res_coarse = product_resolutions[i]
            res_fine = product_resolutions[i + 1]
            zc = compute_zoom_coherence_v2(
                results[res_coarse]['labels'],
                results[res_fine]['labels']
            )
            zoom_results[f"{res_coarse}_to_{res_fine}"] = zc
            print(f"  Zoom {res_coarse} -> {res_fine}: coarse_purity={zc['coarse_purity_mean']:.4f}, "
                  f"fine_purity={zc['fine_purity_mean']:.4f}, "
                  f"improvement_rate={zc['improvement_rate']:.3f}, "
                  f"improvements={zc['improvements']}, deteriorations={zc['deteriorations']}, no_change={zc['no_change']}")
        
        # Overall ZQ score (mean improvement rate across transitions)
        imp_rates = [zc['improvement_rate'] for zc in zoom_results.values()]
        zq_score = np.mean(imp_rates) if imp_rates else 0.0
        print(f"\n  Overall ZQ (mean improvement_rate): {zq_score:.4f}")
        
        all_results[role] = {
            'shape': embeddings.shape,
            'resolution_ladder': {str(res): results[res]['n_clusters'] for res in product_resolutions},
            'zoom_coherence': zoom_results,
            'zq_score': float(zq_score)
        }
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY - Citation Role ZQ Scores (Product Resolution Ladder)")
    print(f"{'='*70}")
    for role, res in all_results.items():
        print(f"  {role}: ZQ={res['zq_score']:.4f} | Ladder: {res['resolution_ladder']}")
    
    # Factory direction v28 claims: citing_alpha0.3 ZQ=0.5401, following 0.5280, criticizing 0.4864
    print(f"\n  Factory direction v28 claims:")
    print(f"    citing_alpha0.3 ZQ=0.5401")
    print(f"    following_alpha0.3 ZQ=0.5280")
    print(f"    criticizing_alpha0.3 ZQ=0.4864")
    
    return all_results


if __name__ == '__main__':
    main()