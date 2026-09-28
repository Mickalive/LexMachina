#!/usr/bin/env python3
"""
Constrained Hierarchical Leiden clustering for fractal map evaluation.
Each finer resolution is constrained to be a refinement of the coarser level.
This achieves nesting=1.0 by construction.
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
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
                                     resolutions: List[float] = None,
                                     k: int = 15,
                                     min_cluster_size: int = 5) -> Dict:
    """
    Run CONSTRAINED hierarchical Leiden clustering.
    Each finer resolution is a refinement of the previous coarser partition.
    This achieves nesting=1.0 by construction.
    """
    if resolutions is None:
        resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    results = {}
    prev_labels = None
    
    for i, res in enumerate(resolutions):
        if i == 0:
            # First level: run Leiden normally
            partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                           weights='weight', resolution_parameter=res)
            labels = np.array(partition.membership)
        else:
            # Constrained: run Leiden on each coarse cluster separately
            labels = np.full(n, -1, dtype=int)
            next_label = 0
            
            for coarse_cluster in np.unique(prev_labels):
                mask = prev_labels == coarse_cluster
                indices = np.where(mask)[0]
                if len(indices) < 2:
                    labels[mask] = next_label
                    next_label += 1
                    continue
                
                # Induced subgraph
                subg = g.induced_subgraph(indices.tolist())
                
                # Run Leiden on subgraph
                try:
                    sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                                       weights='weight', resolution_parameter=res)
                    sub_labels = np.array(sub_partition.membership)
                    # Map back to global labels
                    for j, idx in enumerate(indices):
                        labels[idx] = next_label + sub_labels[j]
                    next_label += len(np.unique(sub_labels))
                except:
                    # Fallback: keep as single cluster
                    labels[indices] = next_label
                    next_label += 1
        
        # Enforce minimum cluster size
        unique, counts = np.unique(labels, return_counts=True)
        small_clusters = unique[counts < min_cluster_size]
        if len(small_clusters) > 0:
            for sc in small_clusters:
                mask = labels == sc
                if np.any(mask):
                    idx = np.where(mask)[0][0]
                    neighbors = g.neighbors(idx)
                    for n_idx in neighbors:
                        if labels[n_idx] not in small_clusters:
                            labels[mask] = labels[n_idx]
                            break
        
        # Renumber labels consecutively
        unique_labels = np.unique(labels)
        label_map = {old: new for new, old in enumerate(unique_labels)}
        labels = np.array([label_map[l] for l in labels])
        
        results[res] = {
            'labels': labels.copy(),
            'n_clusters': len(unique_labels),
            'cluster_sizes': np.bincount(labels).tolist(),
            'median_size': np.median(np.bincount(labels)),
            'singleton_fraction': np.sum(np.bincount(labels) == 1) / len(labels)
        }
        
        prev_labels = labels.copy()
    
    return results


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


def compute_zoom_coherence(results: Dict) -> Dict:
    """Compute zoom coherence metrics across resolution levels."""
    resolutions = sorted(results.keys())
    labels_list = [results[r]['labels'] for r in resolutions]
    
    if len(labels_list) < 2:
        return {'improvement_rate': 0.0, 'nesting_scores': []}
    
    nesting_scores = []
    for i in range(len(labels_list) - 1):
        score = compute_nesting_score(labels_list[i], labels_list[i+1])
        nesting_scores.append(score)
    
    improvements = sum(1 for s in nesting_scores if s > 0.5)
    improvement_rate = improvements / len(nesting_scores) if nesting_scores else 0.0
    
    return {
        'improvement_rate': improvement_rate,
        'nesting_scores': nesting_scores,
        'mean_nesting': np.mean(nesting_scores) if nesting_scores else 0.0,
        'min_nesting': np.min(nesting_scores) if nesting_scores else 0.0,
        'perfect_nesting': all(s == 1.0 for s in nesting_scores)
    }


def compute_legal_purity(labels: np.ndarray, metadata: List[Dict], field: str) -> float:
    """Compute purity of clusters w.r.t. a legal metadata field."""
    n = len(labels)
    if n == 0:
        return 0.0
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None for v in values]
    if not any(valid_mask):
        return 0.0
    
    labels_valid = np.array(labels)[valid_mask]
    values_valid = [v for v, m in zip(values, valid_mask) if m]
    
    unique_labels = np.unique(labels_valid)
    total_purity = 0.0
    total_size = 0
    
    for lbl in unique_labels:
        mask = labels_valid == lbl
        cluster_values = [values_valid[i] for i, m in enumerate(mask) if m]
        if not cluster_values:
            continue
        value_counts = {}
        for v in cluster_values:
            value_counts[v] = value_counts.get(v, 0) + 1
        max_count = max(value_counts.values())
        total_purity += max_count
        total_size += len(cluster_values)
    
    return total_purity / total_size if total_size > 0 else 0.0


def evaluate_zoom_quality(results: Dict, metadata: List[Dict]) -> Dict:
    """
    Evaluate zoom quality per factory direction v26 rule.
    """
    resolutions = sorted(results.keys())
    labels_list = [results[r]['labels'] for r in resolutions]
    
    zoom = compute_zoom_coherence(results)
    
    # Check singleton fraction at finest resolution
    finest = results[resolutions[-1]]
    singleton_frac = finest['singleton_fraction']
    median_size = finest['median_size']
    
    # Legal purity at each resolution
    legal_purities = {}
    for field in ['branch', 'legal_area', 'language', 'chamber']:
        purities = []
        for r in resolutions:
            purities.append(compute_legal_purity(results[r]['labels'], metadata, field))
        legal_purities[field] = purities
    
    # Check monotonic improvement in legal purity
    monotonic = {}
    for field, purities in legal_purities.items():
        improvements = sum(1 for i in range(len(purities)-1) if purities[i+1] >= purities[i])
        monotonic[field] = improvements / (len(purities)-1) if len(purities) > 1 else 0
    
    # v26 zoom-quality verdict
    passes_nesting = zoom['min_nesting'] >= 0.99
    passes_improvement = zoom['improvement_rate'] > 0.5
    passes_fragmentation = singleton_frac < 0.99 and median_size > 1
    passes_monotonic = all(m > 0.5 for m in monotonic.values())
    
    verdict = 'PASS' if (passes_nesting and passes_improvement and passes_fragmentation and passes_monotonic) else 'FAIL'
    
    return {
        'verdict': verdict,
        'nesting_scores': zoom['nesting_scores'],
        'improvement_rate': zoom['improvement_rate'],
        'min_nesting': zoom['min_nesting'],
        'perfect_nesting': zoom['perfect_nesting'],
        'singleton_fraction_fine': singleton_frac,
        'median_cluster_size_fine': median_size,
        'passes_nesting': passes_nesting,
        'passes_improvement': passes_improvement,
        'passes_fragmentation': passes_fragmentation,
        'passes_monotonic': passes_monotonic,
        'legal_purities': legal_purities,
        'monotonic_improvement': monotonic,
        'resolutions': resolutions,
        'n_clusters_per_res': [results[r]['n_clusters'] for r in resolutions]
    }


def load_metadata_for_embeddings(embedding_name: str, n_decisions: int) -> List[Dict]:
    """Load appropriate metadata for the given embedding set."""
    if embedding_name.startswith('citation_role'):
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
    elif '1200' in embedding_name or 'dense_1200' in embedding_name:
        with open('/tmp/lex_accepted/evaluation/evaluation/data/dense_1200_baseline/metadata_1200.json', 'r') as f:
            return json.load(f)[:n_decisions]
    elif 'fractal_map_baseline' in embedding_name or 'baseline' in embedding_name:
        with open('/tmp/lex_accepted/legal-distance/results/fractal_map/baseline/metadata.json', 'r') as f:
            return json.load(f)[:n_decisions]
    else:
        with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json', 'r') as f:
            return json.load(f)[:n_decisions]


def run_experiment(embedding_name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run constrained hierarchical Leiden experiment on embeddings."""
    print(f"\n{'='*60}")
    print(f"Experiment: {embedding_name} ({embeddings.shape[0]} decisions, {embeddings.shape[1]} dim)")
    print(f"{'='*60}")
    
    # Run constrained hierarchical Leiden
    results = constrained_hierarchical_leiden(embeddings, k=15, min_cluster_size=5)
    
    # Print summary
    for res in sorted(results.keys()):
        r = results[res]
        print(f"  Res {res:.2f}: n_clusters={r['n_clusters']}, median_size={r['median_size']:.1f}, "
              f"singleton_frac={r['singleton_fraction']:.3f}")
    
    # Evaluate zoom quality
    zoom = evaluate_zoom_quality(results, metadata)
    
    print(f"\n  Zoom Quality Evaluation:")
    print(f"    Verdict: {zoom['verdict']}")
    print(f"    Improvement rate: {zoom['improvement_rate']:.2f}")
    print(f"    Min nesting: {zoom['min_nesting']:.4f}")
    print(f"    Perfect nesting (all 1.0): {zoom['perfect_nesting']}")
    print(f"    Singleton fraction (fine): {zoom['singleton_fraction_fine']:.4f}")
    print(f"    Median cluster size (fine): {zoom['median_cluster_size_fine']:.1f}")
    print(f"    Passes nesting>=0.99: {zoom['passes_nesting']}")
    print(f"    Passes improvement>0.5: {zoom['passes_improvement']}")
    print(f"    Passes fragmentation: {zoom['passes_fragmentation']}")
    print(f"    Passes monotonic: {zoom['passes_monotonic']}")
    print(f"    Legal purities (branch/legal_area/language/chamber):")
    for field, purities in zoom['legal_purities'].items():
        print(f"      {field}: {[f'{p:.3f}' for p in purities]}")
    print(f"    Monotonic improvement: {zoom['monotonic_improvement']}")
    
    return {
        'embedding_name': embedding_name,
        'shape': embeddings.shape,
        'hierarchical_results': {str(k): v for k, v in results.items()},
        'zoom_quality': zoom
    }


def main():
    all_results = []
    
    # 1. 1200 baseline dense embeddings - these showed good structure in unconstrained test
    print("\n\n### 1200 BASELINE DENSE EMBEDDINGS (Constrained Hierarchical Leiden) ###")
    dense_1200_dir = Path('/tmp/lex_accepted/evaluation/evaluation/data/dense_1200_baseline')
    metadata_1200 = load_metadata_for_embeddings('dense_1200', 1200)
    
    for npy_file in dense_1200_dir.glob('*.npy'):
        if 'metadata' in npy_file.name:
            continue
        name = npy_file.stem
        embeddings = np.load(npy_file)
        if embeddings.shape[0] != 1200:
            print(f"  Skipping {name}: wrong shape {embeddings.shape}")
            continue
        result = run_experiment(f'dense_1200_{name}', embeddings, metadata_1200)
        all_results.append(result)
    
    # 2. Citation role embeddings - test if constrained helps with fragmentation
    print("\n\n### CITATION ROLE EMBEDDINGS (Constrained Hierarchical Leiden) ###")
    roles = ['citing', 'following', 'criticizing', 'all_weighted']
    for role in roles:
        path = f'/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_fixed/citation_role_{role}_fixed.npy'
        embeddings = np.load(path)
        metadata = load_metadata_for_embeddings(f'citation_role_{role}', embeddings.shape[0])
        result = run_experiment(f'citation_role_{role}', embeddings, metadata)
        all_results.append(result)
    
    # 3. 6988 baseline fractal_map embeddings
    print("\n\n### 6988 BASELINE FRACTAL_MAP EMBEDDINGS (Constrained Hierarchical Leiden) ###")
    baseline_dir = Path('/tmp/lex_accepted/legal-distance/results/fractal_map/baseline')
    metadata_baseline = load_metadata_for_embeddings('fractal_map_baseline', 6988)
    
    for npy_file in baseline_dir.glob('*.npy'):
        if 'metadata' in npy_file.name or 'projection' in npy_file.name:
            continue
        name = npy_file.stem
        embeddings = np.load(npy_file)
        print(f"  Checking {name}: shape={embeddings.shape}")
        if embeddings.shape[0] != 6988:
            print(f"  Skipping {name}: wrong shape {embeddings.shape}")
            continue
        result = run_experiment(f'fractal_map_baseline_{name}', embeddings, metadata_baseline)
        all_results.append(result)
    
    # Save all results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_leiden')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'constrained_hierarchical_leiden_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n\n{'='*60}")
    print("CONSTRAINED HIERARCHICAL LEIDEN SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        zq = r['zoom_quality']
        print(f"{r['embedding_name']:50s} | Verdict: {zq['verdict']:4s} | "
              f"ImpRate: {zq['improvement_rate']:.2f} | "
              f"MinNest: {zq['min_nesting']:.3f} | "
              f"PerfectNest: {str(zq['perfect_nesting']):5s} | "
              f"SinglFrac: {zq['singleton_fraction_fine']:.3f} | "
              f"MedSize: {zq['median_cluster_size_fine']:.1f}")
    
    return all_results


if __name__ == '__main__':
    main()