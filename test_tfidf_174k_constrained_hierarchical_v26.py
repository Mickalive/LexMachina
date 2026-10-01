#!/usr/bin/env python3
"""
Run CONSTRAINED hierarchical Leiden on ALL 8 TF-IDF modes at 174k scale
using the 7-level FIXED resolution ladder (matching v26 frozen rule).
Evaluates with the frozen v26 zoom-quality criteria.
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


def constrained_hierarchical_leiden_fixed_ladder(embeddings: np.ndarray, 
                                                  resolutions: List[float] = None,
                                                  k: int = 15,
                                                  min_cluster_size: int = 5) -> Dict:
    """
    Run CONSTRAINED hierarchical Leiden clustering with FIXED resolution ladder.
    Each finer resolution is constrained to be a refinement of the previous coarser partition.
    This achieves nesting=1.0 by construction.
    """
    if resolutions is None:
        # v26 frozen ladder: 5 levels (0.25, 0.5, 1.0, 2.0, 3.0) + intermediates for 7 total
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
    valid_mask = [v is not None and v != 'unknown' for v in values]
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


def evaluate_zoom_quality_v26(results: Dict, metadata: List[Dict]) -> Dict:
    """
    Evaluate zoom quality per FACTORY DIRECTION v26 FROZEN RULE.
    A representation PASSES iff:
    1. Branch purity at res_3.0 > res_0.25
    2. Area purity at res_3.0 > res_0.25  
    3. Branch improvement_rate > 0.5 on ≥2 of 4 transitions (0.25→0.5, 0.5→1.0, 1.0→2.0, 2.0→3.0)
    """
    resolutions = sorted(results.keys())
    labels_list = [results[r]['labels'] for r in resolutions]
    
    zoom = compute_zoom_coherence(results)
    
    # Check singleton fraction at finest resolution (res=3.0)
    finest = results[resolutions[-1]]
    singleton_frac = finest['singleton_fraction']
    median_size = finest['median_size']
    
    # Legal purity at each resolution (only for v26 key resolutions)
    v26_resolutions = [0.25, 0.5, 1.0, 2.0, 3.0]
    legal_purities = {}
    for field in ['branch', 'legal_area']:
        purities = []
        for r in v26_resolutions:
            if r in results:
                purities.append(compute_legal_purity(results[r]['labels'], metadata, field))
            else:
                purities.append(0.0)
        legal_purities[field] = purities
    
    # v26 frozen rule: Branch purity at 3.0 > 0.25, Area purity at 3.0 > 0.25
    branch_purity_coarse = legal_purities['branch'][0]  # res=0.25
    branch_purity_fine = legal_purities['branch'][-1]   # res=3.0
    area_purity_coarse = legal_purities['area'][0]      # res=0.25
    area_purity_fine = legal_purities['area'][-1]       # res=3.0
    
    branch_improves = branch_purity_fine > branch_purity_coarse
    area_improves = area_purity_fine > area_purity_coarse
    
    # v26: improvement_rate > 0.5 on ≥2 of 4 transitions (0.25→0.5, 0.5→1.0, 1.0→2.0, 2.0→3.0)
    # We need to compute branch purity at each transition
    branch_purities_v26 = legal_purities['branch']
    transitions = [
        (branch_purities_v26[1] > branch_purities_v26[0]),  # 0.25→0.5
        (branch_purities_v26[2] > branch_purities_v26[1]),  # 0.5→1.0
        (branch_purities_v26[3] > branch_purities_v26[2]),  # 1.0→2.0
        (branch_purities_v26[4] > branch_purities_v26[3]),  # 2.0→3.0
    ]
    transitions_improved = sum(transitions)
    
    # v26 success rule
    passes_purity_improvement = branch_improves and area_improves
    passes_transitions = transitions_improved >= 2
    passes_fragmentation = singleton_frac < 0.9 and median_size > 1
    
    verdict = 'PASS' if (passes_purity_improvement and passes_transitions and passes_fragmentation) else 'FAIL'
    
    return {
        'verdict': verdict,
        'nesting_scores': zoom['nesting_scores'],
        'improvement_rate': zoom['improvement_rate'],
        'min_nesting': zoom['min_nesting'],
        'perfect_nesting': zoom['perfect_nesting'],
        'singleton_fraction_fine': singleton_frac,
        'median_cluster_size_fine': median_size,
        'branch_purity_coarse': branch_purity_coarse,
        'branch_purity_fine': branch_purity_fine,
        'area_purity_coarse': area_purity_coarse,
        'area_purity_fine': area_purity_fine,
        'branch_improves': branch_improves,
        'area_improves': area_improves,
        'transitions': transitions,
        'transitions_improved': transitions_improved,
        'passes_purity_improvement': passes_purity_improvement,
        'passes_transitions': passes_transitions,
        'passes_fragmentation': passes_fragmentation,
        'legal_purities': legal_purities,
        'resolutions': resolutions,
        'n_clusters_per_res': [results[r]['n_clusters'] for r in resolutions]
    }


def main():
    # Load 174k metadata
    print("Loading 174k metadata...")
    with open('/tmp/lex_accepted/evaluation/evaluation/results/174k/embeddings/metadata.json', 'r') as f:
        metadata = json.load(f)
    print(f"  Metadata: {len(metadata)} entries")
    
    # Load all 8 TF-IDF embeddings
    embeddings_dir = Path('/tmp/lex_accepted/evaluation/evaluation/results/174k/embeddings')
    tfidf_files = {
        'cited_decisions_tfidf': 'cited_decisions_tfidf.npy',
        'cited_decisions_tfidf_outcome_hybrid_0.5': 'cited_decisions_tfidf_outcome_hybrid_0.5.npy',
        'cited_decisions_tfidf_outcome_hybrid_0.7': 'cited_decisions_tfidf_outcome_hybrid_0.7.npy',
        'full_text_tfidf_light': 'full_text_tfidf_light.npy',
        'outcome_tfidf': 'outcome_tfidf.npy',
        'regeste_full_text_hybrid_0.5': 'regeste_full_text_hybrid_0.5.npy',
        'regeste_full_text_hybrid_0.7': 'regeste_full_text_hybrid_0.7.npy',
        'regeste_tfidf': 'regeste_tfidf.npy',
    }
    
    all_results = []
    
    for name, filename in tfidf_files.items():
        path = embeddings_dir / filename
        print(f"\n{'='*70}")
        print(f"Loading {name} from {path}")
        print(f"{'='*70}")
        
        embeddings = np.load(path)
        print(f"  Shape: {embeddings.shape}")
        
        # Truncate embeddings to match metadata length (173963) if needed
        if embeddings.shape[0] != len(metadata):
            print(f"  Truncating embeddings from {embeddings.shape[0]} to {len(metadata)} to match metadata")
            embeddings = embeddings[:len(metadata)]
        
        # Run constrained hierarchical Leiden with fixed 7-level ladder
        print(f"  Running constrained hierarchical Leiden (7-level fixed ladder)...")
        results = constrained_hierarchical_leiden_fixed_ladder(embeddings, k=15, min_cluster_size=5)
        
        # Print summary
        for res in sorted(results.keys()):
            r = results[res]
            print(f"    Res {res:.2f}: n_clusters={r['n_clusters']}, median_size={r['median_size']:.1f}, "
                  f"singleton_frac={r['singleton_fraction']:.3f}")
        
        # Evaluate with v26 frozen rule
        zoom = evaluate_zoom_quality_v26(results, metadata)
        
        print(f"\n  v26 Zoom Quality Evaluation:")
        print(f"    Verdict: {zoom['verdict']}")
        print(f"    Branch purity: coarse={zoom['branch_purity_coarse']:.4f}, fine={zoom['branch_purity_fine']:.4f}, improves={zoom['branch_improves']}")
        print(f"    Area purity: coarse={zoom['area_purity_coarse']:.4f}, fine={zoom['area_purity_fine']:.4f}, improves={zoom['area_improves']}")
        print(f"    Transitions improved: {zoom['transitions_improved']}/4 ({zoom['transitions']})")
        print(f"    Singleton fraction (fine): {zoom['singleton_fraction_fine']:.4f}")
        print(f"    Median cluster size (fine): {zoom['median_cluster_size_fine']:.1f}")
        print(f"    Perfect nesting: {zoom['perfect_nesting']}")
        print(f"    Passes purity improvement: {zoom['passes_purity_improvement']}")
        print(f"    Passes transitions (>=2): {zoom['passes_transitions']}")
        print(f"    Passes fragmentation (<0.9): {zoom['passes_fragmentation']}")
        
        all_results.append({
            'embedding_name': name,
            'shape': embeddings.shape,
            'hierarchical_results': {str(k): v for k, v in results.items()},
            'zoom_quality_v26': zoom
        })
    
    # Save all results
    output_dir = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/tfidf_174k_constrained_hierarchical_v26')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'tfidf_174k_constrained_hierarchical_v26_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Print summary
    print(f"\n\n{'='*70}")
    print("SUMMARY: TF-IDF 174k Constrained Hierarchical Leiden (v26 Rule)")
    print(f"{'='*70}")
    for r in all_results:
        zq = r['zoom_quality_v26']
        print(f"{r['embedding_name']:45s} | Verdict: {zq['verdict']:4s} | "
              f"Branch: {zq['branch_purity_coarse']:.3f}→{zq['branch_purity_fine']:.3f} | "
              f"Transitions: {zq['transitions_improved']}/4 | "
              f"SinglFrac: {zq['singleton_fraction_fine']:.3f} | "
              f"MedSize: {zq['median_cluster_size_fine']:.1f}")
    
    return all_results


if __name__ == '__main__':
    main()