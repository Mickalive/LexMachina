#!/usr/bin/env python3
"""
Scale Sweep Experiment for TF-IDF Embeddings.

Tests hierarchical Leiden (constrained and unconstrained) at multiple corpus scales
using year-split data to find the fragmentation transition point.

Frozen before observation:
- Corpus: Year-split BGer decisions (2000-2002, 2000-2005, 2000-2010, 2000-2015, 2000-2020, 2000-2026)
- Embeddings: cited_decisions_tfidf, cited_outcome_hybrid_0.5 (production default)
- Structure: Flat Leiden and Constrained Hierarchical Leiden at resolutions [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
- Metric: singleton_fraction, median_cluster_size, improvement_rate, legal purity monotonicity
- Success: Identify scale where fragmentation begins (singleton_fraction > 0.5, median_size <= 1)
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
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
                weight = 1.0 - dist
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


def flat_leiden(embeddings: np.ndarray, resolutions: List[float], k: int = 15, min_cluster_size: int = 5) -> Dict:
    """Run flat (unconstrained) Leiden at multiple resolutions."""
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    results = {}
    for res in resolutions:
        partition = la.find_partition(g, la.RBConfigurationVertexPartition,
                                       weights='weight', resolution_parameter=res)
        labels = np.array(partition.membership)
        
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
        
        # Renumber
        unique_labels = np.unique(labels)
        label_map = {old: new for new, old in enumerate(unique_labels)}
        labels = np.array([label_map[l] for l in labels])
        
        results[res] = {
            'labels': labels,
            'n_clusters': len(unique_labels),
            'cluster_sizes': np.bincount(labels).tolist(),
            'median_size': np.median(np.bincount(labels)),
            'singleton_fraction': np.sum(np.bincount(labels) == 1) / len(labels),
            'modularity': partition.modularity
        }
    
    return results


def constrained_hierarchical_leiden(embeddings: np.ndarray, resolutions: List[float], k: int = 15, min_cluster_size: int = 5) -> Dict:
    """Run constrained hierarchical Leiden (each level refines previous)."""
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    results = {}
    prev_labels = None
    
    for i, res in enumerate(resolutions):
        if i == 0:
            partition = la.find_partition(g, la.RBConfigurationVertexPartition,
                                           weights='weight', resolution_parameter=res)
            labels = np.array(partition.membership)
        else:
            labels = np.full(n, -1, dtype=int)
            next_label = 0
            
            for coarse_cluster in np.unique(prev_labels):
                mask = prev_labels == coarse_cluster
                indices = np.where(mask)[0]
                if len(indices) < 2:
                    labels[mask] = next_label
                    next_label += 1
                    continue
                
                subg = g.induced_subgraph(indices.tolist())
                
                try:
                    sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                                       weights='weight', resolution_parameter=res)
                    sub_labels = np.array(sub_partition.membership)
                    for j, idx in enumerate(indices):
                        labels[idx] = next_label + sub_labels[j]
                    next_label += len(np.unique(sub_labels))
                except:
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
        
        # Renumber
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
    """Fraction of fine clusters that are subsets of coarse clusters."""
    n = len(labels_coarse)
    fine_to_coarse = {}
    for i in range(n):
        fc = labels_fine[i]
        cc = labels_coarse[i]
        if fc not in fine_to_coarse:
            fine_to_coarse[fc] = {}
        fine_to_coarse[fc][cc] = fine_to_coarse[fc].get(cc, 0) + 1
    
    nested = sum(1 for cc_counts in fine_to_coarse.values() if len(cc_counts) == 1)
    return nested / len(fine_to_coarse) if fine_to_coarse else 0.0


def compute_zoom_coherence(results: Dict) -> Dict:
    """Compute zoom coherence metrics."""
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
    valid_mask = [v is not None and v != 'unknown' and v != 'null' for v in values]
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
    """Evaluate zoom quality with full metrics."""
    resolutions = sorted(results.keys())
    labels_list = [results[r]['labels'] for r in resolutions]
    
    zoom = compute_zoom_coherence(results)
    
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
    
    # Monotonic improvement
    monotonic = {}
    for field, purities in legal_purities.items():
        improvements = sum(1 for i in range(len(purities)-1) if purities[i+1] >= purities[i])
        monotonic[field] = improvements / (len(purities)-1) if len(purities) > 1 else 0
    
    return {
        'nesting_scores': zoom['nesting_scores'],
        'improvement_rate': zoom['improvement_rate'],
        'min_nesting': zoom['min_nesting'],
        'perfect_nesting': zoom['perfect_nesting'],
        'singleton_fraction_fine': singleton_frac,
        'median_cluster_size_fine': median_size,
        'legal_purities': legal_purities,
        'monotonic_improvement': monotonic,
        'resolutions': resolutions,
        'n_clusters_per_res': [results[r]['n_clusters'] for r in resolutions],
        'cluster_sizes_per_res': {str(r): results[r]['cluster_sizes'] for r in resolutions}
    }


def load_metadata_for_year_range(year_range: Tuple[int, int]) -> Tuple[List[Dict], List[int]]:
    """Load metadata for a year range from the 174k metadata. Returns (metadata, indices)."""
    with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json', 'r') as f:
        all_metadata = json.load(f)
    
    start_year, end_year = year_range
    filtered = []
    indices = []
    for idx, m in enumerate(all_metadata):
        try:
            year = int(m.get('year', 0))
            if start_year <= year <= end_year:
                filtered.append(m)
                indices.append(idx)
        except (ValueError, TypeError):
            continue
    return filtered, indices


def load_tfidf_embeddings_for_year_range(embedding_name: str, year_range: Tuple[int, int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load TF-IDF embeddings for a year range. Returns (embeddings, metadata)."""
    embeddings_dir = Path('/tmp/lex_accepted/evaluation/evaluation/results/174k/embeddings')
    
    # Load full embeddings
    full_path = embeddings_dir / f'{embedding_name}.npy'
    full_embeddings = np.load(full_path)
    
    # Load metadata and get indices for year range
    metadata, indices = load_metadata_for_year_range(year_range)
    
    return full_embeddings[indices], metadata


def run_scale_sweep():
    """Run scale sweep experiment."""
    
    # Define year ranges for scale sweep
    year_ranges = [
        (2000, 2002),   # ~19k (3 years) - ACCEPTED dense years
        (2000, 2005),   # ~35k (6 years)
        (2000, 2010),   # ~62k (11 years) - factory direction mentions "sub-62k scale"
        (2000, 2015),   # ~95k (16 years)
        (2000, 2020),   # ~130k (21 years)
        (2000, 2026),   # 174k (27 years) - full
    ]
    
    # Embeddings to test
    embeddings_to_test = [
        'cited_decisions_tfidf',
        'cited_decisions_tfidf_outcome_hybrid_0.5',  # production default
    ]
    
    resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    
    all_results = []
    
    for year_range in year_ranges:
        start, end = year_range
        print(f"\n{'='*70}")
        print(f"SCALE: {start}-{end} (years)")
        print(f"{'='*70}")
        
        metadata, indices = load_metadata_for_year_range(year_range)
        n_decisions = len(metadata)
        print(f"  Decisions: {n_decisions}")
        
        if n_decisions < 100:
            print(f"  Skipping: too few decisions")
            continue
        
        for emb_name in embeddings_to_test:
            print(f"\n  Testing {emb_name}...")
            
            try:
                embeddings, metadata = load_tfidf_embeddings_for_year_range(emb_name, year_range)
                print(f"  Embeddings shape: {embeddings.shape}")
            except Exception as e:
                print(f"  Error loading embeddings: {e}")
                continue
            
            # Run flat Leiden
            print(f"  Running flat Leiden...")
            flat_results = flat_leiden(embeddings, resolutions, k=15, min_cluster_size=5)
            flat_zoom = evaluate_zoom_quality(flat_results, metadata)
            
            # Run constrained hierarchical Leiden
            print(f"  Running constrained hierarchical Leiden...")
            hier_results = constrained_hierarchical_leiden(embeddings, resolutions, k=15, min_cluster_size=5)
            hier_zoom = evaluate_zoom_quality(hier_results, metadata)
            
            # Print summary
            print(f"\n  FLAT LEIDEN:")
            for res in resolutions:
                r = flat_results[res]
                print(f"    Res {res:.2f}: n_clusters={r['n_clusters']}, median={r['median_size']:.1f}, singleton={r['singleton_fraction']:.3f}")
            print(f"    Improvement rate: {flat_zoom['improvement_rate']:.2f}")
            print(f"    Min nesting: {flat_zoom['min_nesting']:.3f}")
            print(f"    Singleton (fine): {flat_zoom['singleton_fraction_fine']:.3f}")
            print(f"    Median size (fine): {flat_zoom['median_cluster_size_fine']:.1f}")
            for field, purities in flat_zoom['legal_purities'].items():
                print(f"    {field} purity: {[f'{p:.3f}' for p in purities]}")
            
            print(f"\n  CONSTRAINED HIERARCHICAL LEIDEN:")
            for res in resolutions:
                r = hier_results[res]
                print(f"    Res {res:.2f}: n_clusters={r['n_clusters']}, median={r['median_size']:.1f}, singleton={r['singleton_fraction']:.3f}")
            print(f"    Improvement rate: {hier_zoom['improvement_rate']:.2f}")
            print(f"    Min nesting: {hier_zoom['min_nesting']:.3f}")
            print(f"    Perfect nesting: {hier_zoom['perfect_nesting']}")
            print(f"    Singleton (fine): {hier_zoom['singleton_fraction_fine']:.3f}")
            print(f"    Median size (fine): {hier_zoom['median_cluster_size_fine']:.1f}")
            for field, purities in hier_zoom['legal_purities'].items():
                print(f"    {field} purity: {[f'{p:.3f}' for p in purities]}")
            
            all_results.append({
                'year_range': year_range,
                'n_decisions': n_decisions,
                'embedding_name': emb_name,
                'flat': {
                    'results': {str(k): v for k, v in flat_results.items()},
                    'zoom_quality': flat_zoom
                },
                'constrained_hierarchical': {
                    'results': {str(k): v for k, v in hier_results.items()},
                    'zoom_quality': hier_zoom
                }
            })
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/scale_sweep_tfidf')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'scale_sweep_tfidf_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Print summary table
    print(f"\n\n{'='*70}")
    print("SCALE SWEEP SUMMARY")
    print(f"{'='*70}")
    
    for r in all_results:
        yr = r['year_range']
        n = r['n_decisions']
        emb = r['embedding_name']
        flat = r['flat']['zoom_quality']
        hier = r['constrained_hierarchical']['zoom_quality']
        
        print(f"\n{emb} @ {yr[0]}-{yr[1]} ({n} decisions):")
        print(f"  FLAT:       ImpRate={flat['improvement_rate']:.2f}, MinNest={flat['min_nesting']:.3f}, Singl={flat['singleton_fraction_fine']:.3f}, MedSize={flat['median_cluster_size_fine']:.1f}")
        print(f"  HIER:       ImpRate={hier['improvement_rate']:.2f}, MinNest={hier['min_nesting']:.3f}, Perfect={hier['perfect_nesting']}, Singl={hier['singleton_fraction_fine']:.3f}, MedSize={hier['median_cluster_size_fine']:.1f}")
        print(f"  Branch purities FLAT:  {[f'{p:.3f}' for p in flat['legal_purities']['branch']]}")
        print(f"  Branch purities HIER:  {[f'{p:.3f}' for p in hier['legal_purities']['branch']]}")
    
    return all_results


if __name__ == '__main__':
    run_scale_sweep()