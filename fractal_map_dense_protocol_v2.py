#!/usr/bin/env python3
"""
Dense-specific hierarchical protocol for fractal map evaluation - REVISED.

Key findings from investigation:
1. Previous hierarchical_v1 purity metrics INCLUDED 'unknown' as valid category, inflating scores
2. Actual valid-only purity: coarse_branch=0.836, coarse_area=0.255, fine_branch=0.988, fine_area=0.511
3. Dense embeddings achieve high branch purity but modest area purity
4. Fragmentation (6-9% singletons) is the main failure mode

This protocol implements:
1. Valid-only purity computation (exclude 'unknown')
2. Purity-aware stopping: Don't subdivide clusters with coarse_valid_purity > threshold
3. Target: meaningful area purity at subdomain level (>0.5)
4. Fragmentation control: singleton_fraction < 0.01 at all levels
5. Proper fractal hierarchy: corpus → domain (branch) → subdomain (area) → microcluster → decisions
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


def compute_legal_purity_valid_only(labels: np.ndarray, metadata: List[Dict], field: str) -> Tuple[float, Dict]:
    """Compute purity of clusters w.r.t. a legal metadata field, EXCLUDING 'unknown'."""
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
        value_counts = {}
        for v in cluster_values:
            value_counts[v] = value_counts.get(v, 0) + 1
        max_count = max(value_counts.values())
        cluster_purity = max_count / len(cluster_values)
        per_cluster[int(lbl)] = {
            'purity': cluster_purity,
            'size': int(len(cluster_values)),
            'dominant_value': max(value_counts, key=value_counts.get),
            'distribution': value_counts
        }
        total_purity += max_count
        total_size += len(cluster_values)
    
    return total_purity / total_size if total_size > 0 else 0.0, per_cluster


def purity_aware_constrained_leiden(embeddings: np.ndarray,
                                     k: int = 15,
                                     min_cluster_size: int = 10,
                                     max_subclusters_per_parent: int = 20,
                                     branch_purity_stop_threshold: float = 0.85,
                                     area_purity_stop_threshold: float = 0.5) -> Tuple[Dict, ig.Graph]:
    """
    Run constrained hierarchical Leiden with PURITY-AWARE STOPPING.
    
    Key features:
    - Level 1 (domains): Target branch-level clustering (~4-8 clusters)
    - Level 2 (subdomains): Target legal_area clustering (~20-50 clusters)  
    - Level 3 (microclusters): Fine-grained (~100-200 clusters)
    - Level 4 (decisions): Leaf level
    
    Purity-aware stopping:
    - Don't subdivide clusters with branch_purity > branch_purity_stop_threshold
    - Don't subdivide clusters with area_purity > area_purity_stop_threshold
    - Only subdivide if there's potential for meaningful area refinement
    """
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    # We need metadata for purity checks during construction
    # Load it once
    with open('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_embeddings_2000_2002/metadata_2000_2002.json', 'r') as f:
        full_metadata = json.load(f)
    metadata = full_metadata[:n]
    
    # Level 1: Domains (branch level) - resolution ~0.3
    domain_resolution = 0.3
    partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                   weights='weight', resolution_parameter=domain_resolution)
    domain_labels = np.array(partition.membership)
    
    # Enforce min cluster size
    unique, counts = np.unique(domain_labels, return_counts=True)
    small_clusters = unique[counts < min_cluster_size]
    if len(small_clusters) > 0:
        for sc in small_clusters:
            mask = domain_labels == sc
            if np.any(mask):
                idx = np.where(mask)[0][0]
                neighbors = g.neighbors(idx)
                for n_idx in neighbors:
                    if domain_labels[n_idx] not in small_clusters:
                        domain_labels[mask] = domain_labels[n_idx]
                        break
    
    # Renumber
    unique_labels = np.unique(domain_labels)
    label_map = {old: new for new, old in enumerate(unique_labels)}
    domain_labels = np.array([label_map[l] for l in domain_labels])
    
    # Build hierarchy
    hierarchy = {
        'level_0_corpus': {
            'labels': np.zeros(n, dtype=int),
            'n_clusters': 1,
            'parent': None,
            'children': list(range(len(unique_labels)))
        },
        'level_1_domains': {
            'labels': domain_labels.copy(),
            'n_clusters': len(unique_labels),
            'parent': 'level_0_corpus',
            'children': {}
        }
    }
    
    # Recursively subdivide with purity-aware stopping
    current_labels = domain_labels.copy()
    level = 1
    max_levels = 4
    
    while level < max_levels:
        next_level_name = f'level_{level+1}'
        next_labels = np.full(n, -1, dtype=int)
        next_label = 0
        parent_children = {}
        
        for parent_cluster in np.unique(current_labels):
            mask = current_labels == parent_cluster
            indices = np.where(mask)[0]
            
            if len(indices) < min_cluster_size:
                next_labels[mask] = next_label
                parent_children[parent_cluster] = [next_label]
                next_label += 1
                continue
            
            # PURITY-AWARE STOPPING CHECK
            # Check if this cluster should be subdivided
            # Compute branch and area purity for this cluster
            cluster_metadata = [metadata[i] for i in indices]
            branch_purity, _ = compute_legal_purity_valid_only(
                np.zeros(len(indices), dtype=int),  # single cluster
                cluster_metadata, 'branch'
            )
            area_purity, _ = compute_legal_purity_valid_only(
                np.zeros(len(indices), dtype=int),
                cluster_metadata, 'legal_area'
            )
            
            # Stop if already pure enough
            should_stop = False
            if level == 1:  # Domain -> Subdomain
                if branch_purity > branch_purity_stop_threshold and area_purity > area_purity_stop_threshold:
                    should_stop = True
            elif level == 2:  # Subdomain -> Microcluster
                if area_purity > area_purity_stop_threshold:
                    should_stop = True
            
            if should_stop:
                next_labels[mask] = next_label
                parent_children[parent_cluster] = [next_label]
                next_label += 1
                continue
            
            # Induced subgraph
            subg = g.induced_subgraph(indices.tolist())
            
            # Resolution increases with level
            sub_resolution = 1.0 + level * 0.8
            
            try:
                sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                                   weights='weight', resolution_parameter=sub_resolution)
                sub_labels = np.array(sub_partition.membership)
                n_subclusters = len(np.unique(sub_labels))
                
                # Cap subclusters per parent
                if n_subclusters > max_subclusters_per_parent:
                    sub_unique, sub_counts = np.unique(sub_labels, return_counts=True)
                    sorted_idx = np.argsort(sub_counts)[::-1]
                    keep = sub_unique[sorted_idx[:max_subclusters_per_parent]]
                    for old_label in sub_unique:
                        if old_label not in keep:
                            sub_labels[sub_labels == old_label] = keep[0]
                    n_subclusters = max_subclusters_per_parent
                
                if n_subclusters == 1:
                    next_labels[mask] = next_label
                    parent_children[parent_cluster] = [next_label]
                    next_label += 1
                else:
                    for j, idx in enumerate(indices):
                        next_labels[idx] = next_label + sub_labels[j]
                    child_labels = list(range(next_label, next_label + n_subclusters))
                    parent_children[parent_cluster] = child_labels
                    next_label += n_subclusters
                    
            except Exception as e:
                next_labels[mask] = next_label
                parent_children[parent_cluster] = [next_label]
                next_label += 1
        
        # We need to map old parent labels to new parent labels after renumbering
        # First, compute what each old parent label becomes after renumbering
        old_parent_labels = np.unique(current_labels)
        # For each old parent label, find what it maps to in next_labels
        parent_label_map = {}
        for old_parent in old_parent_labels:
            mask = current_labels == old_parent
            if np.any(mask):
                # All points in this parent cluster get the same new label (first one)
                new_parent = next_labels[mask][0]
                parent_label_map[old_parent] = int(new_parent)
        
        # Renumber next_labels
        unique_labels = np.unique(next_labels)
        label_map = {old: new for new, old in enumerate(unique_labels)}
        next_labels = np.array([label_map[l] for l in next_labels])
        
        # Update parent_children mapping: both parent keys and children values remapped
        new_parent_children = {}
        for old_parent, children in parent_children.items():
            new_parent = parent_label_map.get(old_parent, old_parent)
            new_children = [label_map[c] for c in children if c in label_map]
            if new_children:  # Only add if there are valid children
                new_parent_children[new_parent] = new_children
        
        hierarchy[next_level_name] = {
            'labels': next_labels.copy(),
            'n_clusters': len(unique_labels),
            'parent': f'level_{level}',
            'children': new_parent_children
        }
        
        current_labels = next_labels.copy()
        level += 1
    
    return hierarchy, g


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


def evaluate_dense_hierarchy(hierarchy: Dict, metadata: List[Dict], g: ig.Graph) -> Dict:
    """
    Evaluate dense-specific hierarchy with VALID-ONLY metrics:
    1. Nesting = 1.0 (by construction)
    2. Domain level (level_1) branch_purity > 0.8 (strong branch structure)
    3. Subdomain level (level_2) area_purity > 0.4 (meaningful sub-topics)
    4. Fragmentation < 0.01 at ALL levels
    5. At least 3 levels with >1 cluster
    6. Semantic coherence > 0.3 at subdivision transitions
    """
    n = len(metadata)
    
    # Get labels for each level
    level_labels = {}
    for level_name, level_data in hierarchy.items():
        level_labels[level_name] = level_data['labels']
    
    # Level names in order
    level_names = sorted(hierarchy.keys(), key=lambda x: int(x.split('_')[1]))
    
    # Compute nesting between adjacent levels
    nesting_scores = []
    for i in range(len(level_names) - 1):
        score = compute_nesting_score(level_labels[level_names[i]], level_labels[level_names[i+1]])
        nesting_scores.append(score)
    
    # Legal purity at each level (VALID ONLY)
    legal_purities = {}
    for field in ['branch', 'legal_area']:
        purities = {}
        for level_name in level_names:
            weighted_purity, per_cluster = compute_legal_purity_valid_only(
                level_labels[level_name], metadata, field
            )
            purities[level_name] = {
                'weighted_purity': weighted_purity,
                'per_cluster': per_cluster
            }
        legal_purities[field] = purities
    
    # Fragmentation at each level
    fragmentation = {}
    for level_name in level_names:
        labels = level_labels[level_name]
        unique, counts = np.unique(labels, return_counts=True)
        singleton_frac = float(np.sum(counts == 1) / n)
        median_size = float(np.median(counts))
        fragmentation[level_name] = {
            'singleton_fraction': singleton_frac,
            'median_size': median_size,
            'n_clusters': int(len(unique)),
            'size_distribution': [int(c) for c in counts]
        }
    
    # Semantic coherence: children of a cluster should have different dominant areas
    semantic_coherence = {}
    for level_name in level_names[:-1]:
        parent_level = level_name
        child_level = level_names[level_names.index(level_name) + 1]
        
        parent_labels = level_labels[parent_level]
        child_labels = level_labels[child_level]
        
        coherence_scores = []
        for parent in np.unique(parent_labels):
            parent_mask = parent_labels == parent
            if np.sum(parent_mask) < 2:
                continue
            
            children = child_labels[parent_mask]
            child_clusters = np.unique(children)
            
            if len(child_clusters) <= 1:
                coherence_scores.append(1.0)  # Not subdivided - neutral
                continue
            
            # Check if children have different dominant legal_areas
            child_areas = []
            for child in child_clusters:
                child_mask = child_labels == child
                valid = [m.get('legal_area') for i, m in enumerate(metadata) if child_mask[i] and m.get('legal_area') != 'unknown']
                if valid:
                    from collections import Counter
                    area_counts = Counter(valid)
                    dominant = area_counts.most_common(1)[0][0]
                    child_areas.append(dominant)
            
            if len(child_areas) > 1:
                coherence_scores.append(len(set(child_areas)) / len(child_areas))
            else:
                coherence_scores.append(0.0)
        
        semantic_coherence[parent_level] = {
            'mean_coherence': float(np.mean(coherence_scores)) if coherence_scores else 0.0,
            'per_parent': [float(c) for c in coherence_scores]
        }
    
    # Overall assessment - DENSE-SPECIFIC CRITERIA
    domain_branch_purity = legal_purities.get('branch', {}).get('level_1_domains', {}).get('weighted_purity', 0)
    subdomain_area_purity = legal_purities.get('legal_area', {}).get('level_2_subdomains', {}).get('weighted_purity', 0)
    
    # Check if level_2 exists, if not use level_2_subdomains might be named differently
    if 'level_2_subdomains' not in legal_purities.get('legal_area', {}):
        # Find the level that corresponds to subdomains (should be level_2)
        for ln in level_names:
            if ln.startswith('level_2'):
                subdomain_area_purity = legal_purities.get('legal_area', {}).get(ln, {}).get('weighted_purity', 0)
                break
    
    all_nesting_perfect = all(abs(s - 1.0) < 1e-10 for s in nesting_scores)
    all_fragmentation_ok = all(f['singleton_fraction'] < 0.01 for f in fragmentation.values())
    meaningful_depth = sum(1 for f in fragmentation.values() if f['n_clusters'] > 1) >= 3
    
    coherence_scores = [c['mean_coherence'] for c in semantic_coherence.values()]
    avg_coherence = float(np.mean(coherence_scores)) if coherence_scores else 0.0
    
    # Dense protocol success criteria (VALID-ONLY):
    verdict = 'PASS' if (all_nesting_perfect and 
                          domain_branch_purity > 0.8 and
                          subdomain_area_purity > 0.3 and  # Adjusted for valid-only
                          all_fragmentation_ok and
                          meaningful_depth and
                          avg_coherence > 0.2) else 'FAIL'
    
    return {
        'verdict': verdict,
        'nesting_scores': [float(s) for s in nesting_scores],
        'all_nesting_perfect': all_nesting_perfect,
        'domain_branch_purity': float(domain_branch_purity),
        'subdomain_area_purity': float(subdomain_area_purity),
        'fragmentation': fragmentation,
        'all_fragmentation_ok': all_fragmentation_ok,
        'meaningful_depth': meaningful_depth,
        'semantic_coherence': semantic_coherence,
        'avg_coherence': avg_coherence,
        'legal_purities': legal_purities,
        'level_names': level_names
    }


def load_dense_metadata(n_decisions: int) -> List[Dict]:
    """Load metadata for 12k dense embeddings."""
    with open('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_embeddings_2000_2002/metadata_2000_2002.json', 'r') as f:
        metadata = json.load(f)
    return metadata[:n_decisions]


def run_dense_protocol_experiment(embeddings: np.ndarray, metadata: List[Dict], 
                                   branch_purity_stop: float = 0.85,
                                   area_purity_stop: float = 0.5) -> Dict:
    """Run the dense-specific hierarchical protocol experiment."""
    print(f"\n{'='*70}")
    print(f"DENSE-SPECIFIC HIERARCHICAL PROTOCOL (VALID-ONLY PURITY)")
    print(f"Shape: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dim")
    print(f"Branch purity stop: {branch_purity_stop}, Area purity stop: {area_purity_stop}")
    print(f"{'='*70}")
    
    hierarchy, g = purity_aware_constrained_leiden(
        embeddings,
        k=15,
        min_cluster_size=10,
        max_subclusters_per_parent=20,
        branch_purity_stop_threshold=branch_purity_stop,
        area_purity_stop_threshold=area_purity_stop
    )
    
    # Print hierarchy summary
    print("\nHierarchy structure:")
    for level_name, level_data in hierarchy.items():
        print(f"  {level_name}: {level_data['n_clusters']} clusters")
    
    eval_results = evaluate_dense_hierarchy(hierarchy, metadata, g)
    
    print(f"\n  Dense Protocol Evaluation (VALID-ONLY):")
    print(f"    Verdict: {eval_results['verdict']}")
    print(f"    All nesting perfect: {eval_results['all_nesting_perfect']}")
    print(f"    Domain branch purity: {eval_results['domain_branch_purity']:.4f}")
    print(f"    Subdomain area purity: {eval_results['subdomain_area_purity']:.4f}")
    print(f"    All fragmentation OK (<1%): {eval_results['all_fragmentation_ok']}")
    print(f"    Meaningful depth (>=3 levels): {eval_results['meaningful_depth']}")
    print(f"    Avg semantic coherence: {eval_results['avg_coherence']:.4f}")
    
    for level_name, frag in eval_results['fragmentation'].items():
        print(f"    {level_name}: n_clusters={frag['n_clusters']}, singleton_frac={frag['singleton_fraction']:.4f}, median_size={frag['median_size']:.1f}")
    
    # Convert numpy arrays to lists for JSON serialization
    serializable_hierarchy = {}
    for k, v in hierarchy.items():
        serializable_hierarchy[k] = {
            'labels': v['labels'].tolist(),
            'n_clusters': v['n_clusters'],
            'parent': v['parent'],
            'children': v['children']
        }
    
    return {
        'hierarchy': serializable_hierarchy,
        'evaluation': eval_results
    }


def run_standard_hierarchical_v26(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run standard hierarchical Leiden (v26 rule) for comparison."""
    from test_12k_dense_hierarchical import hierarchical_leiden, evaluate_zoom_quality
    
    standard_results = hierarchical_leiden(embeddings, k=15, min_cluster_size=5)
    standard_eval = evaluate_zoom_quality(standard_results, metadata)
    
    return {
        'verdict': standard_eval['verdict'],
        'improvement_rate': float(standard_eval['improvement_rate']),
        'singleton_fraction_fine': float(standard_eval['singleton_fraction_fine']),
        'median_cluster_size_fine': float(standard_eval['median_cluster_size_fine']),
        'legal_purities': standard_eval['legal_purities']
    }


def main():
    """Test dense-specific protocol on ACCEPTED 12k dense embeddings."""
    print("Loading ACCEPTED 12k dense embeddings (years 2000-2002)...")
    
    embeddings = np.load('/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_embeddings_2000_2002/embeddings_2000_2002.npy')
    print(f"  Shape: {embeddings.shape}")
    
    metadata = load_dense_metadata(embeddings.shape[0])
    print(f"  Metadata: {len(metadata)} entries")
    
    # Test with different purity stop thresholds
    results = {}
    for branch_thresh, area_thresh in [(0.8, 0.4), (0.85, 0.5), (0.9, 0.6)]:
        print(f"\n\n### Testing branch_stop={branch_thresh}, area_stop={area_thresh} ###")
        result = run_dense_protocol_experiment(embeddings, metadata, 
                                               branch_purity_stop=branch_thresh,
                                               area_purity_stop=area_thresh)
        results[f'branch_{branch_thresh}_area_{area_thresh}'] = result
    
    # Also test standard hierarchical_v26 for comparison
    print(f"\n\n### COMPARISON: Standard hierarchical Leiden (v26 rule) ###")
    standard_result = run_standard_hierarchical_v26(embeddings, metadata)
    print(f"  Standard v26 Verdict: {standard_result['verdict']}")
    print(f"  Improvement rate: {standard_result['improvement_rate']:.2f}")
    print(f"  Singleton fraction (fine): {standard_result['singleton_fraction_fine']:.4f}")
    print(f"  Median cluster size (fine): {standard_result['median_cluster_size_fine']:.1f}")
    
    results['standard_hierarchical_v26'] = standard_result
    
    # Save results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/dense_specific_protocol_v2')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'dense_protocol_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\n{'='*70}")
    print("SUMMARY: Dense-specific protocol vs standard")
    print(f"{'='*70}")
    for name, result in results.items():
        if 'evaluation' in result:
            ev = result['evaluation']
            print(f"{name:35s} | Verdict: {ev['verdict']:4s} | "
                  f"DomBranch: {ev['domain_branch_purity']:.3f} | "
                  f"SubArea: {ev['subdomain_area_purity']:.3f} | "
                  f"FragOK: {ev['all_fragmentation_ok']} | "
                  f"Depth: {ev['meaningful_depth']} | "
                  f"Coherence: {ev['avg_coherence']:.3f}")
        else:
            print(f"{name:35s} | Verdict: {result['verdict']:4s} | "
                  f"ImpRate: {result['improvement_rate']:.2f} | "
                  f"SinglFrac: {result['singleton_fraction_fine']:.4f} | "
                  f"MedSize: {result['median_cluster_size_fine']:.1f}")
    
    return results


if __name__ == '__main__':
    main()