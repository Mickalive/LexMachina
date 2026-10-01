#!/usr/bin/env python3
"""
Run dense-specific 2-level protocol on 28k checkpoint dense embeddings (years 2000-2005).
This validates scale stability of the dense protocol before 174k extrapolation.
PENDING AUDIT data - results are for pipeline validation only, not ACCEPTED evidence.
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# Reuse functions from fractal_map_dense_protocol_2level.py
def build_knn_graph(embeddings: np.ndarray, k: int = 15, metric: str = 'cosine') -> ig.Graph:
    n = embeddings.shape[0]
    nbrs = NearestNeighbors(n_neighbors=min(k+1, n), metric=metric, n_jobs=-1)
    nbrs.fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(n):
        for j, dist in zip(indices[i][1:], distances[i][1:]):
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


def compute_cluster_purity(cluster_indices: np.ndarray, metadata: List[Dict], field: str) -> float:
    cluster_metadata = [metadata[i] for i in cluster_indices]
    values = [m.get(field) for m in cluster_metadata]
    valid_values = [v for v in values if v is not None and v != 'unknown']
    if not valid_values:
        return 1.0
    value_counts = Counter(valid_values)
    max_count = max(value_counts.values())
    return max_count / len(valid_values)


def compute_legal_purity_valid_only(labels: np.ndarray, metadata: List[Dict], field: str) -> Tuple[float, Dict]:
    n = len(labels)
    if n == 0:
        return 0.0, {}
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None and v != 'unknown' for v in values]
    if not any(valid_mask):
        return 0.0, {}
    
    labels_valid = np.array(labels)[valid_mask]
    values_valid = [v for v, m in zip(values, valid_mask) if m]
    
    unique_labels = np.unique(labels_valid)
    total_purity = 0.0
    total_size = 0
    per_cluster = {}
    
    for lbl in unique_labels:
        mask = labels_valid == lbl
        cluster_values = [values_valid[i] for i, m in enumerate(mask) if m]
        if not cluster_values:
            continue
        value_counts = Counter(cluster_values)
        max_count = max(value_counts.values())
        cluster_purity = max_count / len(cluster_values)
        per_cluster[int(lbl)] = {
            'purity': cluster_purity,
            'size': int(len(cluster_values)),
            'dominant_value': value_counts.most_common(1)[0][0],
            'distribution': dict(value_counts)
        }
        total_purity += max_count
        total_size += len(cluster_values)
    
    return total_purity / total_size if total_size > 0 else 0.0, per_cluster


def purity_aware_constrained_leiden_2level(embeddings: np.ndarray,
                                            metadata: List[Dict],
                                            k: int = 15,
                                            coarse_res: float = 0.25,
                                            fine_res: float = 3.0,
                                            min_cluster_size: int = 10,
                                            max_subclusters_per_parent: int = 20,
                                            branch_purity_stop: float = 0.85,
                                            area_purity_stop: float = 0.5) -> Tuple[np.ndarray, np.ndarray, ig.Graph, Dict]:
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    # Coarse level
    partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                   weights='weight', resolution_parameter=coarse_res)
    coarse_labels = np.array(partition.membership)
    
    # Enforce min_cluster_size
    unique, counts = np.unique(coarse_labels, return_counts=True)
    small_clusters = unique[counts < min_cluster_size]
    if len(small_clusters) > 0:
        for sc in small_clusters:
            mask = coarse_labels == sc
            if np.any(mask):
                idx = np.where(mask)[0][0]
                neighbors = g.neighbors(idx)
                for n_idx in neighbors:
                    if coarse_labels[n_idx] not in small_clusters:
                        coarse_labels[mask] = coarse_labels[n_idx]
                        break
    
    # Renumber
    unique_labels = np.unique(coarse_labels)
    label_map = {old: new for new, old in enumerate(unique_labels)}
    coarse_labels = np.array([label_map[l] for l in coarse_labels])
    
    # Fine level with purity-aware stopping
    fine_labels = np.full(n, -1, dtype=int)
    next_label = 0
    stop_info = {
        'subdivided': [],
        'not_subdivided': [],
        'branch_purity_stop': branch_purity_stop,
        'area_purity_stop': area_purity_stop
    }
    
    for coarse_cluster in np.unique(coarse_labels):
        mask = coarse_labels == coarse_cluster
        indices = np.where(mask)[0]
        if len(indices) < 2:
            fine_labels[mask] = next_label
            stop_info['not_subdivided'].append({
                'coarse_cluster': int(coarse_cluster),
                'size': int(len(indices)),
                'reason': 'too_small'
            })
            next_label += 1
            continue
        
        # PURITY-AWARE STOPPING CHECK
        branch_purity = compute_cluster_purity(indices, metadata, 'branch')
        area_purity = compute_cluster_purity(indices, metadata, 'legal_area')
        
        should_stop = branch_purity > branch_purity_stop and area_purity > area_purity_stop
        
        if should_stop:
            fine_labels[mask] = next_label
            stop_info['not_subdivided'].append({
                'coarse_cluster': int(coarse_cluster),
                'size': int(len(indices)),
                'branch_purity': float(branch_purity),
                'area_purity': float(area_purity),
                'reason': 'purity_stop'
            })
            next_label += 1
            continue
        
        # Subdivide
        subg = g.induced_subgraph(indices.tolist())
        try:
            sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                               weights='weight', resolution_parameter=fine_res)
            sub_labels = np.array(sub_partition.membership)
            n_sub = len(np.unique(sub_labels))
            
            if n_sub > max_subclusters_per_parent:
                sub_unique, sub_counts = np.unique(sub_labels, return_counts=True)
                sorted_idx = np.argsort(sub_counts)[::-1]
                keep = sub_unique[sorted_idx[:max_subclusters_per_parent]]
                for old_label in sub_unique:
                    if old_label not in keep:
                        sub_labels[sub_labels == old_label] = keep[0]
                n_sub = len(np.unique(sub_labels))
            
            for j, idx in enumerate(indices):
                fine_labels[idx] = next_label + sub_labels[j]
            
            stop_info['subdivided'].append({
                'coarse_cluster': int(coarse_cluster),
                'size': int(len(indices)),
                'branch_purity': float(branch_purity),
                'area_purity': float(area_purity),
                'n_subclusters': int(n_sub),
                'reason': 'subdivided'
            })
            next_label += n_sub
        except:
            fine_labels[indices] = next_label
            stop_info['not_subdivided'].append({
                'coarse_cluster': int(coarse_cluster),
                'size': int(len(indices)),
                'branch_purity': float(branch_purity),
                'area_purity': float(area_purity),
                'reason': 'error'
            })
            next_label += 1
    
    # Enforce min_cluster_size on fine (preserve nesting)
    unique, counts = np.unique(fine_labels, return_counts=True)
    small_clusters = unique[counts < min_cluster_size]
    if len(small_clusters) > 0:
        for sc in small_clusters:
            mask = fine_labels == sc
            if np.any(mask):
                idx = np.where(mask)[0][0]
                coarse_cluster = coarse_labels[idx]
                neighbors = g.neighbors(idx)
                for n_idx in neighbors:
                    if coarse_labels[n_idx] == coarse_cluster and fine_labels[n_idx] not in small_clusters:
                        fine_labels[mask] = fine_labels[n_idx]
                        break
    
    # Renumber
    unique_labels = np.unique(fine_labels)
    label_map = {old: new for new, old in enumerate(unique_labels)}
    fine_labels = np.array([label_map[l] for l in fine_labels])
    
    return coarse_labels, fine_labels, g, stop_info


def compute_nesting_score(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> float:
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


def evaluate_2level_hierarchy(coarse_labels: np.ndarray, fine_labels: np.ndarray, 
                               metadata: List[Dict], g: ig.Graph, stop_info: Dict) -> Dict:
    n = len(metadata)
    
    # Nesting
    nesting = compute_nesting_score(coarse_labels, fine_labels)
    
    # Fragmentation
    unique, counts = np.unique(fine_labels, return_counts=True)
    singleton_frac = float(np.sum(counts == 1) / n)
    median_size = float(np.median(counts))
    
    # Legal purity (VALID ONLY)
    coarse_branch_purity, coarse_branch_detail = compute_legal_purity_valid_only(coarse_labels, metadata, 'branch')
    coarse_area_purity, coarse_area_detail = compute_legal_purity_valid_only(coarse_labels, metadata, 'legal_area')
    fine_branch_purity, fine_branch_detail = compute_legal_purity_valid_only(fine_labels, metadata, 'branch')
    fine_area_purity, fine_area_detail = compute_legal_purity_valid_only(fine_labels, metadata, 'legal_area')
    
    # Purity improvement
    branch_improvement = fine_branch_purity - coarse_branch_purity
    area_improvement = fine_area_purity - coarse_area_purity
    
    # Semantic coherence
    coherence_scores = []
    for item in stop_info['subdivided']:
        coarse_cluster = item['coarse_cluster']
        mask = coarse_labels == coarse_cluster
        if np.sum(mask) < 2:
            continue
        children = fine_labels[mask]
        child_clusters = np.unique(children)
        if len(child_clusters) <= 1:
            continue
        
        child_areas = []
        for child in child_clusters:
            child_mask = fine_labels == child
            valid = [m.get('legal_area') for i, m in enumerate(metadata) if child_mask[i] and m.get('legal_area') != 'unknown']
            if valid:
                area_counts = Counter(valid)
                dominant = area_counts.most_common(1)[0][0]
                child_areas.append(dominant)
        
        if len(child_areas) > 1:
            coherence_scores.append(len(set(child_areas)) / len(child_areas))
        else:
            coherence_scores.append(0.0)
    
    avg_coherence = float(np.mean(coherence_scores)) if coherence_scores else 0.0
    
    # DENSE-SPECIFIC SUCCESS CRITERIA
    passes_nesting = nesting >= 0.95
    passes_fragmentation = singleton_frac < 0.01 and median_size > 5
    passes_coarse_branch = coarse_branch_purity > 0.8
    passes_fine_area = fine_area_purity > 0.4
    passes_area_improvement = area_improvement > 0.05
    passes_coherence = avg_coherence > 0.3
    some_subdivision = len(stop_info['subdivided']) > 0
    
    verdict = 'PASS' if (passes_nesting and passes_fragmentation and passes_coarse_branch and 
                         passes_fine_area and passes_area_improvement and passes_coherence and some_subdivision) else 'FAIL'
    
    return {
        'verdict': verdict,
        'nesting': float(nesting),
        'passes_nesting': passes_nesting,
        'singleton_fraction': singleton_frac,
        'median_cluster_size': median_size,
        'passes_fragmentation': passes_fragmentation,
        'coarse_branch_purity': float(coarse_branch_purity),
        'coarse_area_purity': float(coarse_area_purity),
        'fine_branch_purity': float(fine_branch_purity),
        'fine_area_purity': float(fine_area_purity),
        'branch_improvement': float(branch_improvement),
        'area_improvement': float(area_improvement),
        'passes_coarse_branch': passes_coarse_branch,
        'passes_fine_area': passes_fine_area,
        'passes_area_improvement': passes_area_improvement,
        'avg_coherence': avg_coherence,
        'passes_coherence': passes_coherence,
        'some_subdivision': some_subdivision,
        'n_coarse_clusters': int(len(np.unique(coarse_labels))),
        'n_fine_clusters': int(len(np.unique(fine_labels))),
        'stop_info': stop_info,
        'checks': {
            'nesting_ge_0.95': passes_nesting,
            'singleton_lt_0.01': singleton_frac < 0.01,
            'median_size_gt_5': median_size > 5,
            'coarse_branch_gt_0.8': passes_coarse_branch,
            'fine_area_gt_0.4': passes_fine_area,
            'area_improvement_gt_0.05': passes_area_improvement,
            'coherence_gt_0.3': passes_coherence,
            'some_subdivision': some_subdivision
        }
    }


def load_checkpoint_data(years):
    """Load embeddings and metadata for given years from checkpoints."""
    CHECKPOINT_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
    all_embeddings = []
    all_metadata = []
    
    for year in years:
        emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINT_DIR / f"metadata_{year}.json"
        
        print(f"Loading {year}...")
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        print(f"  {year}: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dims")
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
    
    combined_embeddings = np.vstack(all_embeddings)
    print(f"Total: {combined_embeddings.shape[0]} decisions, {combined_embeddings.shape[1]} dims")
    
    return combined_embeddings, all_metadata


def main():
    print("=" * 70)
    print("28k Checkpoint Dense Embeddings - Dense-Specific 2-Level Protocol Validation")
    print("PENDING AUDIT - Pipeline validation only, not ACCEPTED evidence")
    print("=" * 70)
    
    # Load data for years 2000-2005 (~28k decisions)
    years = ["2000", "2001", "2002", "2003", "2004", "2005"]
    embeddings, metadata = load_checkpoint_data(years)
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    # Test with different purity stop thresholds (same as 12k validation)
    results = {}
    for branch_thresh, area_thresh in [(0.8, 0.4), (0.85, 0.5), (0.9, 0.6)]:
        print(f"\n\n### Testing branch_stop={branch_thresh}, area_stop={area_thresh} ###")
        coarse_labels, fine_labels, g, stop_info = purity_aware_constrained_leiden_2level(
            embeddings, metadata,
            k=15,
            coarse_res=0.25,
            fine_res=3.0,
            min_cluster_size=10,
            max_subclusters_per_parent=20,
            branch_purity_stop=branch_thresh,
            area_purity_stop=area_thresh
        )
        
        eval_results = evaluate_2level_hierarchy(coarse_labels, fine_labels, metadata, g, stop_info)
        results[f'dense_protocol_branch_{branch_thresh}_area_{area_thresh}'] = {
            'coarse_labels': coarse_labels.tolist(),
            'fine_labels': fine_labels.tolist(),
            'stop_info': stop_info,
            'evaluation': eval_results
        }
        
        print(f"  Verdict: {eval_results['verdict']}")
        print(f"  Nesting: {eval_results['nesting']:.4f}")
        print(f"  Singleton: {eval_results['singleton_fraction']:.4f}")
        print(f"  Median size: {eval_results['median_cluster_size']:.1f}")
        print(f"  Coarse branch: {eval_results['coarse_branch_purity']:.4f}")
        print(f"  Fine area: {eval_results['fine_area_purity']:.4f}")
        print(f"  Area improvement: {eval_results['area_improvement']:.4f}")
        print(f"  Coherence: {eval_results['avg_coherence']:.4f}")
        print(f"  Subdivided: {len(stop_info['subdivided'])}, Not subdivided: {len(stop_info['not_subdivided'])}")
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/28k_dense_protocol_validation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"28k_dense_protocol_validation_{os.environ.get('RUN_ID', 'manual')}.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\nResults saved to {output_path}")
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY: 28k Dense Protocol Validation")
    print(f"{'='*70}")
    for name, result in results.items():
        ev = result['evaluation']
        print(f"{name:45s} | Verdict: {ev['verdict']:4s} | "
              f"Nest: {ev['nesting']:.3f} | "
              f"Singl: {ev['singleton_fraction']:.4f} | "
              f"MedSz: {ev['median_cluster_size']:.1f} | "
              f"CoBranch: {ev['coarse_branch_purity']:.3f} | "
              f"FiArea: {ev['fine_area_purity']:.3f} | "
              f"ArImpr: {ev['area_improvement']:.3f} | "
              f"Coh: {ev['avg_coherence']:.3f} | "
              f"SubDiv: {ev['some_subdivision']}")
    
    return results


if __name__ == '__main__':
    main()