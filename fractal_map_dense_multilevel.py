#!/usr/bin/env python3
"""
Dense-specific MULTI-LEVEL fractal hierarchy protocol.

Extends the 2-level PASSING protocol to full fractal hierarchy:
- Level 0: Corpus (1 cluster)
- Level 1: Domains (~4-8 clusters, branch level)
- Level 2: Subdomains (~20-50 clusters, legal_area level)  
- Level 3: Microclusters (~100-200 clusters)
- Level 4: Decisions (leaf level)

Each level uses purity-aware stopping based on valid-only purity.
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors
from collections import Counter
import warnings
warnings.filterwarnings('ignore')


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
            'purity': cluster_purity, 'size': int(len(cluster_values)),
            'dominant_value': value_counts.most_common(1)[0][0],
            'distribution': dict(value_counts)
        }
        total_purity += max_count
        total_size += len(cluster_values)
    return total_purity / total_size if total_size > 0 else 0.0, per_cluster


def compute_cluster_purity(cluster_indices: np.ndarray, metadata: List[Dict], field: str) -> float:
    cluster_metadata = [metadata[i] for i in cluster_indices]
    values = [m.get(field) for m in cluster_metadata]
    valid_values = [v for v in values if v is not None and v != 'unknown']
    if not valid_values:
        return 1.0
    value_counts = Counter(valid_values)
    max_count = max(value_counts.values())
    return max_count / len(valid_values)


def purity_aware_constrained_leiden_level(embeddings: np.ndarray,
                                           metadata: List[Dict],
                                           parent_labels: np.ndarray,
                                           k: int = 15,
                                           resolution: float = 1.0,
                                           min_cluster_size: int = 10,
                                           max_subclusters_per_parent: int = 20,
                                           stop_thresholds: Dict = None) -> Tuple[np.ndarray, Dict]:
    """
    Run one level of constrained Leiden with purity-aware stopping.
    """
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    if parent_labels is None:
        # Level 0: single cluster
        labels = np.zeros(n, dtype=int)
        stop_info = {'level': 0, 'not_subdivided': [], 'subdivided': []}
        return labels, g, stop_info
    
    labels = np.full(n, -1, dtype=int)
    next_label = 0
    stop_info = {'level': 'unknown', 'not_subdivided': [], 'subdivided': []}
    
    for parent_cluster in np.unique(parent_labels):
        mask = parent_labels == parent_cluster
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            labels[mask] = next_label
            stop_info['not_subdivided'].append({
                'parent_cluster': int(parent_cluster), 'size': int(len(indices)),
                'reason': 'too_small'
            })
            next_label += 1
            continue
        
        # Purity-aware stopping
        should_stop = False
        stop_reason = ''
        if stop_thresholds:
            branch_purity = compute_cluster_purity(indices, metadata, 'branch')
            area_purity = compute_cluster_purity(indices, metadata, 'legal_area')
            
            branch_thresh = stop_thresholds.get('branch', 0.9)
            area_thresh = stop_thresholds.get('area', 0.7)
            
            if branch_purity > branch_thresh and area_purity > area_thresh:
                should_stop = True
                stop_reason = f'purity_stop (branch={branch_purity:.3f}, area={area_purity:.3f})'
        
        if should_stop:
            labels[mask] = next_label
            stop_info['not_subdivided'].append({
                'parent_cluster': int(parent_cluster), 'size': int(len(indices)),
                'branch_purity': float(branch_purity), 'area_purity': float(area_purity),
                'reason': stop_reason
            })
            next_label += 1
            continue
        
        # Subdivide
        subg = g.induced_subgraph(indices.tolist())
        try:
            sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                               weights='weight', resolution_parameter=resolution)
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
                labels[idx] = next_label + sub_labels[j]
            
            branch_purity = compute_cluster_purity(indices, metadata, 'branch')
            area_purity = compute_cluster_purity(indices, metadata, 'legal_area')
            
            stop_info['subdivided'].append({
                'parent_cluster': int(parent_cluster), 'size': int(len(indices)),
                'branch_purity': float(branch_purity), 'area_purity': float(area_purity),
                'n_subclusters': int(n_sub), 'reason': 'subdivided'
            })
            next_label += n_sub
        except Exception as e:
            labels[mask] = next_label
            stop_info['not_subdivided'].append({
                'parent_cluster': int(parent_cluster), 'size': int(len(indices)),
                'reason': f'error: {e}'
            })
            next_label += 1
    
    # Renumber
    unique_labels = np.unique(labels)
    label_map = {old: new for new, old in enumerate(unique_labels)}
    labels = np.array([label_map[l] for l in labels])
    
    return labels, g, stop_info


def build_multi_level_hierarchy(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """
    Build full multi-level fractal hierarchy with purity-aware stopping.
    """
    n = embeddings.shape[0]
    hierarchy = {}
    stop_infos = {}
    
    # Level 0: Corpus
    level0_labels = np.zeros(n, dtype=int)
    hierarchy['level_0_corpus'] = {
        'labels': level0_labels, 'n_clusters': 1,
        'parent': None, 'children': []
    }
    
    # Level 1: Domains (branch level) - coarse resolution, strict stopping
    level1_labels, g, stop1 = purity_aware_constrained_leiden_level(
        embeddings, metadata, level0_labels,
        k=15, resolution=0.3, min_cluster_size=10,
        max_subclusters_per_parent=8,  # Expect ~4-8 branches
        stop_thresholds={'branch': 0.8, 'area': 0.4}  # Stop if already pure
    )
    stop1['level'] = 1
    stop_infos['level_1_domains'] = stop1
    hierarchy['level_1_domains'] = {
        'labels': level1_labels, 'n_clusters': int(len(np.unique(level1_labels))),
        'parent': 'level_0_corpus', 'children': {}
    }
    
    # Level 2: Subdomains (legal_area level)
    level2_labels, _, stop2 = purity_aware_constrained_leiden_level(
        embeddings, metadata, level1_labels,
        k=15, resolution=1.0, min_cluster_size=10,
        max_subclusters_per_parent=10,
        stop_thresholds={'branch': 0.9, 'area': 0.5}
    )
    stop2['level'] = 2
    stop_infos['level_2_subdomains'] = stop2
    hierarchy['level_2_subdomains'] = {
        'labels': level2_labels, 'n_clusters': int(len(np.unique(level2_labels))),
        'parent': 'level_1_domains', 'children': {}
    }
    
    # Level 3: Microclusters
    level3_labels, _, stop3 = purity_aware_constrained_leiden_level(
        embeddings, metadata, level2_labels,
        k=15, resolution=2.0, min_cluster_size=5,
        max_subclusters_per_parent=8,
        stop_thresholds={'branch': 0.95, 'area': 0.7}
    )
    stop3['level'] = 3
    stop_infos['level_3_microclusters'] = stop3
    hierarchy['level_3_microclusters'] = {
        'labels': level3_labels, 'n_clusters': int(len(np.unique(level3_labels))),
        'parent': 'level_2_subdomains', 'children': {}
    }
    
    # Level 4: Decisions (leaf - each decision in its own cluster or small groups)
    # For decisions level, we don't cluster - we just use the microcluster assignment
    # or we can do a final fine-grained clustering
    level4_labels, _, stop4 = purity_aware_constrained_leiden_level(
        embeddings, metadata, level3_labels,
        k=15, resolution=3.0, min_cluster_size=3,
        max_subclusters_per_parent=5,
        stop_thresholds={'branch': 0.98, 'area': 0.8}
    )
    stop4['level'] = 4
    stop_infos['level_4_decisions'] = stop4
    hierarchy['level_4_decisions'] = {
        'labels': level4_labels, 'n_clusters': int(len(np.unique(level4_labels))),
        'parent': 'level_3_microclusters', 'children': {}
    }
    
    return hierarchy, g, stop_infos


def compute_nesting_score(labels_coarse: np.ndarray, labels_fine: np.ndarray) -> float:
    n = len(labels_coarse)
    fine_to_coarse = {}
    for i in range(n):
        fc = labels_fine[i]
        cc = labels_coarse[i]
        if fc not in fine_to_coarse:
            fine_to_coarse[fc] = {}
        fine_to_coarse[fc][cc] = fine_to_coarse[fc].get(cc, 0) + 1
    nested = sum(1 for fc, cc_counts in fine_to_coarse.items() if len(cc_counts) == 1)
    return nested / len(fine_to_coarse) if fine_to_coarse else 0.0


def evaluate_multi_level_hierarchy(hierarchy: Dict, metadata: List[Dict], g: ig.Graph, 
                                    stop_infos: Dict) -> Dict:
    """Evaluate full multi-level hierarchy."""
    n = len(metadata)
    
    level_names = ['level_0_corpus', 'level_1_domains', 'level_2_subdomains', 
                   'level_3_microclusters', 'level_4_decisions']
    
    # Verify all levels exist
    for ln in level_names:
        if ln not in hierarchy:
            return {'verdict': 'FAIL', 'error': f'Missing level {ln}'}
    
    # Nesting between adjacent levels
    nesting_scores = []
    for i in range(len(level_names) - 1):
        coarse_labels = hierarchy[level_names[i]]['labels']
        fine_labels = hierarchy[level_names[i+1]]['labels']
        nesting = compute_nesting_score(coarse_labels, fine_labels)
        nesting_scores.append(nesting)
    
    # Legal purity at each level (VALID ONLY)
    legal_purities = {}
    for field in ['branch', 'legal_area']:
        purities = {}
        for ln in level_names:
            labels = hierarchy[ln]['labels']
            wp, pc = compute_legal_purity_valid_only(labels, metadata, field)
            purities[ln] = {'weighted_purity': wp, 'per_cluster': pc}
        legal_purities[field] = purities
    
    # Fragmentation at each level
    fragmentation = {}
    for ln in level_names:
        labels = hierarchy[ln]['labels']
        unique, counts = np.unique(labels, return_counts=True)
        singleton_frac = float(np.sum(counts == 1) / n)
        median_size = float(np.median(counts))
        fragmentation[ln] = {
            'singleton_fraction': singleton_frac,
            'median_size': median_size,
            'n_clusters': int(len(unique))
        }
    
    # Semantic coherence for each transition
    coherence_scores = []
    for i in range(len(level_names) - 1):
        parent_ln = level_names[i]
        child_ln = level_names[i+1]
        parent_labels = hierarchy[parent_ln]['labels']
        child_labels = hierarchy[child_ln]['labels']
        
        level_coherence = []
        for parent in np.unique(parent_labels):
            mask = parent_labels == parent
            if np.sum(mask) < 2:
                continue
            children = child_labels[mask]
            child_clusters = np.unique(children)
            if len(child_clusters) <= 1:
                level_coherence.append(1.0)
                continue
            child_areas = []
            for child in child_clusters:
                child_mask = child_labels == child
                valid = [m.get('legal_area') for i, m in enumerate(metadata) if child_mask[i] and m.get('legal_area') != 'unknown']
                if valid:
                    area_counts = Counter(valid)
                    dominant = area_counts.most_common(1)[0][0]
                    child_areas.append(dominant)
            if len(child_areas) > 1:
                level_coherence.append(len(set(child_areas)) / len(child_areas))
            else:
                level_coherence.append(0.0)
        coherence_scores.append(float(np.mean(level_coherence)) if level_coherence else 0.0)
    
    # Overall assessment
    all_nesting_ok = all(s >= 0.95 for s in nesting_scores)
    all_fragmentation_ok = all(f['singleton_fraction'] < 0.01 for f in fragmentation.values())
    all_median_ok = all(f['median_size'] > 3 for f in fragmentation.values() if f['n_clusters'] > 1)
    
    domain_branch = legal_purities['branch']['level_1_domains']['weighted_purity']
    subdomain_area = legal_purities['legal_area']['level_2_subdomains']['weighted_purity']
    microcluster_area = legal_purities['legal_area']['level_3_microclusters']['weighted_purity']
    
    avg_coherence = float(np.mean(coherence_scores)) if coherence_scores else 0.0
    
    # Multi-level success criteria
    verdict = 'PASS' if (all_nesting_ok and all_fragmentation_ok and all_median_ok and
                          domain_branch > 0.8 and subdomain_area > 0.35 and 
                          microcluster_area > 0.4 and avg_coherence > 0.3) else 'FAIL'
    
    return {
        'verdict': verdict,
        'nesting_scores': [float(s) for s in nesting_scores],
        'all_nesting_ok': all_nesting_ok,
        'domain_branch_purity': float(domain_branch),
        'subdomain_area_purity': float(subdomain_area),
        'microcluster_area_purity': float(microcluster_area),
        'fragmentation': fragmentation,
        'all_fragmentation_ok': all_fragmentation_ok,
        'all_median_ok': all_median_ok,
        'coherence_scores': coherence_scores,
        'avg_coherence': avg_coherence,
        'legal_purities': legal_purities,
        'level_names': level_names,
        'checks': {
            'all_nesting_ge_0.95': all_nesting_ok,
            'all_frag_lt_0.01': all_fragmentation_ok,
            'all_median_gt_3': all_median_ok,
            'domain_branch_gt_0.8': domain_branch > 0.8,
            'subdomain_area_gt_0.35': subdomain_area > 0.35,
            'microcluster_area_gt_0.4': microcluster_area > 0.4,
            'avg_coherence_gt_0.3': avg_coherence > 0.3
        }
    }


def load_dense_metadata(n_decisions: int) -> List[Dict]:
    with open('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_embeddings_2000_2002/metadata_2000_2002.json', 'r') as f:
        return json.load(f)[:n_decisions]


def main():
    print("Loading ACCEPTED 12k dense embeddings (years 2000-2002)...")
    embeddings = np.load('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_embeddings_2000_2002/embeddings_2000_2002.npy')
    metadata = load_dense_metadata(embeddings.shape[0])
    print(f"  Shape: {embeddings.shape}, Metadata: {len(metadata)}")
    
    hierarchy, g, stop_infos = build_multi_level_hierarchy(embeddings, metadata)
    eval_results = evaluate_multi_level_hierarchy(hierarchy, metadata, g, stop_infos)
    
    print(f"\n{'='*70}")
    print("MULTI-LEVEL DENSE-SPECIFIC FRACTAL HIERARCHY")
    print(f"{'='*70}")
    print(f"Verdict: {eval_results['verdict']}")
    print(f"\nHierarchy structure:")
    for ln in eval_results['level_names']:
        h = hierarchy[ln]
        frag = eval_results['fragmentation'][ln]
        print(f"  {ln}: {h['n_clusters']} clusters, singleton_frac={frag['singleton_fraction']:.4f}, median={frag['median_size']:.1f}")
    
    print(f"\nNesting scores (adjacent levels):")
    for i, score in enumerate(eval_results['nesting_scores']):
        print(f"  {eval_results['level_names'][i]} → {eval_results['level_names'][i+1]}: {score:.4f}")
    
    print(f"\nLegal purities (VALID ONLY):")
    for field in ['branch', 'legal_area']:
        print(f"  {field}:")
        for ln in eval_results['level_names']:
            wp = eval_results['legal_purities'][field][ln]['weighted_purity']
            print(f"    {ln}: {wp:.4f}")
    
    print(f"\nCoherence scores (transitions):")
    for i, score in enumerate(eval_results['coherence_scores']):
        print(f"  {eval_results['level_names'][i]} → {eval_results['level_names'][i+1]}: {score:.4f}")
    print(f"  Average: {eval_results['avg_coherence']:.4f}")
    
    print(f"\nChecks:")
    for check, passed in eval_results['checks'].items():
        print(f"  {check}: {passed}")
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/dense_multilevel_protocol')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert hierarchy for JSON
    serializable_hierarchy = {}
    for k, v in hierarchy.items():
        serializable_hierarchy[k] = {
            'labels': v['labels'].tolist(),
            'n_clusters': v['n_clusters'],
            'parent': v['parent']
        }
    
    results = {
        'hierarchy': serializable_hierarchy,
        'stop_infos': stop_infos,
        'evaluation': eval_results
    }
    
    with open(output_dir / 'dense_multilevel_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return results


if __name__ == '__main__':
    main()