#!/usr/bin/env python3
"""
Test constrained hierarchical Leiden on ACCEPTED 1k citation-role embeddings.
Goal: Test if constrained approach reduces over-fragmentation at fine resolutions
while preserving the strong zoom quality (ZQ=0.54/0.53/0.49) observed at 1k scale.
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


def constrained_hierarchical_leiden(embeddings: np.ndarray, 
                                     coarse_res: float = 0.25,
                                     fine_res: float = 3.0,
                                     k: int = 15,
                                     min_cluster_size: int = 5,
                                     adaptive_sub_resolution: bool = False,
                                     max_subclusters: int = 50) -> Dict:
    """
    Run CONSTRAINED hierarchical Leiden clustering.
    Each finer resolution is a refinement of the previous coarser partition.
    """
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    # Coarse level
    partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                   weights='weight', resolution_parameter=coarse_res)
    coarse_labels = np.array(partition.membership)
    
    # Fine level: constrained within coarse clusters
    fine_labels = np.full(n, -1, dtype=int)
    next_label = 0
    
    for coarse_cluster in np.unique(coarse_labels):
        mask = coarse_labels == coarse_cluster
        indices = np.where(mask)[0]
        if len(indices) < 2:
            fine_labels[mask] = next_label
            next_label += 1
            continue
        
        # Induced subgraph
        subg = g.induced_subgraph(indices.tolist())
        
        # Determine sub-resolution
        if adaptive_sub_resolution:
            size_factor = min(len(indices) / 100.0, 2.0)
            sub_res = fine_res * size_factor
        else:
            sub_res = fine_res
        
        # Run Leiden on subgraph
        try:
            sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                               weights='weight', resolution_parameter=sub_res)
            sub_labels = np.array(sub_partition.membership)
            
            # Enforce max_subclusters
            unique_sub = np.unique(sub_labels)
            if len(unique_sub) > max_subclusters:
                sub_sizes = np.bincount(sub_labels)
                keep = np.argsort(sub_sizes)[-max_subclusters:]
                merge_map = {u: keep[i] if u not in keep else u for i, u in enumerate(unique_sub)}
                sub_labels = np.array([merge_map[l] for l in sub_labels])
            
            # Map back to global labels
            for j, idx in enumerate(indices):
                fine_labels[idx] = next_label + sub_labels[j]
            next_label += len(np.unique(sub_labels))
        except:
            fine_labels[indices] = next_label
            next_label += 1
    
    # Enforce minimum cluster size on fine labels
    unique, counts = np.unique(fine_labels, return_counts=True)
    small_clusters = unique[counts < min_cluster_size]
    if len(small_clusters) > 0:
        for sc in small_clusters:
            mask = fine_labels == sc
            if np.any(mask):
                idx = np.where(mask)[0][0]
                neighbors = g.neighbors(idx)
                for n_idx in neighbors:
                    if fine_labels[n_idx] not in small_clusters:
                        fine_labels[mask] = fine_labels[n_idx]
                        break
    
    # Renumber labels consecutively
    for labels in [coarse_labels, fine_labels]:
        unique_labels = np.unique(labels)
        label_map = {old: new for new, old in enumerate(unique_labels)}
        labels[:] = [label_map[l] for l in labels]
    
    return {
        'coarse': {
            'labels': coarse_labels,
            'n_clusters': len(np.unique(coarse_labels)),
            'cluster_sizes': np.bincount(coarse_labels).tolist(),
            'median_size': np.median(np.bincount(coarse_labels)),
            'singleton_fraction': np.sum(np.bincount(coarse_labels) == 1) / len(coarse_labels)
        },
        'fine': {
            'labels': fine_labels,
            'n_clusters': len(np.unique(fine_labels)),
            'cluster_sizes': np.bincount(fine_labels).tolist(),
            'median_size': np.median(np.bincount(fine_labels)),
            'singleton_fraction': np.sum(np.bincount(fine_labels) == 1) / len(fine_labels)
        }
    }


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


def compute_zoom_quality_score(coarse_labels: np.ndarray, fine_labels: np.ndarray, metadata: List[Dict]) -> Dict:
    """Compute Zoom Quality (ZQ) = improvement_rate * fine_purity * hierarchical_advantage per v8."""
    # Improvement rate: fraction of fine clusters with purity > coarse purity + 0.01
    def cluster_purities(labels, field):
        purities = {}
        values = [m.get(field) for m in metadata]
        valid_mask = [v is not None for v in values]
        if not any(valid_mask):
            return purities
        labels_valid = labels[valid_mask]
        values_valid = [v for v, m in zip(values, valid_mask) if m]
        for lbl in np.unique(labels_valid):
            mask = labels_valid == lbl
            cluster_values = [values_valid[i] for i, m in enumerate(mask) if m]
            if not cluster_values:
                continue
            value_counts = {}
            for v in cluster_values:
                value_counts[v] = value_counts.get(v, 0) + 1
            max_count = max(value_counts.values())
            purities[lbl] = max_count / len(cluster_values)
        return purities
    
    # Use branch for purity (most decisions have branch)
    coarse_purities = cluster_purities(coarse_labels, 'branch')
    fine_purities = cluster_purities(fine_labels, 'branch')
    
    fine_to_coarse = {}
    for i in range(len(coarse_labels)):
        fc = fine_labels[i]
        cc = coarse_labels[i]
        if fc not in fine_to_coarse:
            fine_to_coarse[fc] = cc
    
    improvements = 0
    total = 0
    for fc, cc in fine_to_coarse.items():
        if fc in fine_purities and cc in coarse_purities:
            total += 1
            if fine_purities[fc] > coarse_purities[cc] + 0.01:
                improvements += 1
    improvement_rate = improvements / total if total > 0 else 0.0
    
    # Fine purity (mean purity at fine level)
    fine_purity = np.mean(list(fine_purities.values())) if fine_purities else 0.0
    coarse_purity = np.mean(list(coarse_purities.values())) if coarse_purities else 0.0
    
    # Hierarchical advantage: fine_purity - coarse_purity
    hierarchical_advantage = fine_purity - coarse_purity
    
    # Zoom Quality Score
    zoom_quality = improvement_rate * fine_purity * (1 + hierarchical_advantage)
    
    return {
        'zoom_quality': zoom_quality,
        'improvement_rate': improvement_rate,
        'fine_purity': fine_purity,
        'coarse_purity': coarse_purity,
        'hierarchical_advantage': hierarchical_advantage
    }


def load_citation_role_metadata(n_decisions: int) -> List[Dict]:
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
                'branch': s.get('branch', 'strafrecht'),
                'legal_area': s.get('legal_area', 'Strafprozess'),
                'chamber': s.get('chamber', 'II. Strafrechtliche Abteilung')
            })
        else:
            metadata.append({'decision_id': sd, 'language': 'de', 'branch': 'unknown', 'legal_area': 'unknown', 'chamber': 'unknown'})
    while len(metadata) < n_decisions:
        metadata.append({'decision_id': f'pad_{len(metadata)}', 'language': 'de', 'branch': 'unknown', 'legal_area': 'unknown', 'chamber': 'unknown'})
    return metadata[:n_decisions]


def run_constrained_test(role: str, embeddings: np.ndarray, metadata: List[Dict], 
                         coarse_res: float, fine_res: float, min_size: int) -> Dict:
    """Run constrained hierarchical Leiden on a citation role embedding."""
    results = constrained_hierarchical_leiden(
        embeddings,
        coarse_res=coarse_res,
        fine_res=fine_res,
        min_cluster_size=min_size,
        adaptive_sub_resolution=False,
        max_subclusters=50
    )
    
    coarse_labels = results['coarse']['labels']
    fine_labels = results['fine']['labels']
    
    nesting = compute_nesting_score(coarse_labels, fine_labels)
    zq = compute_zoom_quality_score(coarse_labels, fine_labels, metadata)
    
    return {
        'role': role,
        'config': f'coarse_{coarse_res}_fixed{fine_res}_min{min_size}',
        'coarse_clusters': results['coarse']['n_clusters'],
        'fine_clusters': results['fine']['n_clusters'],
        'nesting_score': nesting,
        'zoom_quality': zq['zoom_quality'],
        'improvement_rate': zq['improvement_rate'],
        'fine_purity': zq['fine_purity'],
        'coarse_purity': zq['coarse_purity'],
        'hierarchical_advantage': zq['hierarchical_advantage'],
        'singleton_fraction': results['fine']['singleton_fraction'],
        'median_cluster_size': results['fine']['median_size'],
        'coarse_cluster_sizes': results['coarse']['cluster_sizes'],
        'fine_cluster_sizes': results['fine']['cluster_sizes']
    }


def main():
    print("="*70)
    print("CONSTRAINED HIERARCHICAL LEIDEN ON CITATION-ROLE EMBEDDINGS (1k)")
    print("Factory Direction v28 | ACCEPTED evidence (citation roles v6)")
    print("="*70)
    
    roles = ['citing', 'following', 'criticizing', 'all_weighted']
    
    # Test configurations - sweep coarse_res and fine_res
    configs = [
        (0.05, 1.0, 5),
        (0.05, 2.0, 5),
        (0.05, 3.0, 5),
        (0.1, 1.0, 5),
        (0.1, 2.0, 5),
        (0.1, 3.0, 5),
        (0.25, 1.0, 5),
        (0.25, 2.0, 5),
        (0.25, 3.0, 5),
        (0.5, 1.0, 5),
        (0.5, 2.0, 5),
        (0.5, 3.0, 5),
    ]
    
    all_results = []
    
    for role in roles:
        print(f"\n{'='*70}")
        print(f"Testing role: {role}")
        print(f"{'='*70}")
        
        embeddings = np.load(f'/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_fixed/citation_role_{role}_fixed.npy')
        print(f"  Embeddings shape: {embeddings.shape}")
        
        metadata = load_citation_role_metadata(embeddings.shape[0])
        
        for coarse_res, fine_res, min_size in configs:
            try:
                result = run_constrained_test(role, embeddings, metadata, coarse_res, fine_res, min_size)
                all_results.append(result)
                
                print(f"  {result['config']:30s} | Coarse: {result['coarse_clusters']:3d} | Fine: {result['fine_clusters']:3d} | "
                      f"Nesting: {result['nesting_score']:.3f} | ZQ: {result['zoom_quality']:.4f} | "
                      f"ImpRate: {result['improvement_rate']:.3f} | Singleton: {result['singleton_fraction']:.3f} | MedSz: {result['median_cluster_size']:.1f}")
            except Exception as e:
                print(f"  {coarse_res}_{fine_res}_{min_size} ERROR: {e}")
                all_results.append({'role': role, 'config': f'coarse_{coarse_res}_fixed{fine_res}_min{min_size}', 'error': str(e)})
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/citation_role_constrained')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'citation_role_constrained_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Print summary by role
    print(f"\n{'='*70}")
    print("SUMMARY BY ROLE")
    print(f"{'='*70}")
    
    for role in roles:
        role_results = [r for r in all_results if r.get('role') == role and 'error' not in r]
        if not role_results:
            continue
        
        print(f"\n{role.upper()}:")
        # Best by zoom_quality
        best_zq = max(role_results, key=lambda x: x['zoom_quality'])
        # Best by improvement_rate with nesting >= 0.99
        best_impr = max([r for r in role_results if r['nesting_score'] >= 0.99], 
                       key=lambda x: x['improvement_rate'], default=None)
        
        print(f"  Best ZQ: {best_zq['config']} | ZQ={best_zq['zoom_quality']:.4f} | "
              f"Impr={best_zq['improvement_rate']:.3f} | Nesting={best_zq['nesting_score']:.3f} | "
              f"Singleton={best_zq['singleton_fraction']:.3f} | MedSz={best_zq['median_cluster_size']:.1f}")
        if best_impr:
            print(f"  Best Impr (nesting>=0.99): {best_impr['config']} | ZQ={best_impr['zoom_quality']:.4f} | "
                  f"Impr={best_impr['improvement_rate']:.3f} | Nesting={best_impr['nesting_score']:.3f} | "
                  f"Singleton={best_impr['singleton_fraction']:.3f} | MedSz={best_impr['median_cluster_size']:.1f}")
    
    return all_results


if __name__ == '__main__':
    main()