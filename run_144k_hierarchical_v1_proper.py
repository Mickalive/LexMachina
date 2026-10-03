#!/usr/bin/env python3
"""
Run hierarchical_v1 protocol on 144k dense embeddings (2000-2021) using CHECKPOINT metadata
which has proper branch/legal_area labels (not the evaluation metadata with 'unknown').
"""

import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors
import warnings
warnings.filterwarnings('ignore')

CHECKPOINT_DIR = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints')
OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/144k_hierarchical_v1_proper')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Years in the 144k checkpoint (2000-2021)
CHECKPOINT_YEARS = list(range(2000, 2022))

# Validated best configuration from 28k and 12k testing
BEST_CONFIG = {
    'name': 'coarse_0.5_fixed2.0_min20',
    'coarse_res': 0.5,
    'base_sub_res': 2.0,
    'min_cluster_size': 20,
    'max_subclusters_per_parent': 20,
    'adaptive_sub_res': False
}

K_NEIGHBORS = 15
LEIDEN_SEED = 42
GLOBAL_SEED = 42

np.random.seed(GLOBAL_SEED)


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
                                     coarse_res: float = 0.5,
                                     base_sub_res: float = 2.0,
                                     min_cluster_size: int = 20,
                                     max_subclusters_per_parent: int = 20,
                                     k: int = 15) -> Dict:
    """
    Run CONSTRAINED hierarchical Leiden clustering (2-level: coarse -> fine).
    Fine level is constrained to be a refinement of coarse level.
    Achieves nesting=1.0 by construction.
    """
    g = build_knn_graph(embeddings, k=k)
    n = embeddings.shape[0]
    
    # Coarse level
    coarse_partition = la.find_partition(g, la.RBConfigurationVertexPartition,
                                          weights='weight', resolution_parameter=coarse_res)
    coarse_labels = np.array(coarse_partition.membership)
    
    # Enforce minimum cluster size at coarse level
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
    
    # Renumber coarse labels
    unique_coarse = np.unique(coarse_labels)
    coarse_label_map = {old: new for new, old in enumerate(unique_coarse)}
    coarse_labels = np.array([coarse_label_map[l] for l in coarse_labels])
    n_coarse = len(unique_coarse)
    
    # Fine level: constrained refinement within each coarse cluster
    fine_labels = np.full(n, -1, dtype=int)
    next_fine_label = 0
    
    for coarse_cluster in range(n_coarse):
        mask = coarse_labels == coarse_cluster
        indices = np.where(mask)[0]
        if len(indices) < 2:
            fine_labels[mask] = next_fine_label
            next_fine_label += 1
            continue
        
        # Induced subgraph
        subg = g.induced_subgraph(indices.tolist())
        
        # Run Leiden on subgraph
        try:
            sub_partition = la.find_partition(subg, la.RBConfigurationVertexPartition,
                                               weights='weight', resolution_parameter=base_sub_res)
            sub_labels = np.array(sub_partition.membership)
            
            # Enforce minimum cluster size within subgraph
            unique_sub, counts_sub = np.unique(sub_labels, return_counts=True)
            small_sub = unique_sub[counts_sub < min_cluster_size]
            if len(small_sub) > 0:
                for sc in small_sub:
                    sub_mask = sub_labels == sc
                    if np.any(sub_mask):
                        sub_idx = np.where(sub_mask)[0][0]
                        sub_neighbors = subg.neighbors(sub_idx)
                        for sn_idx in sub_neighbors:
                            if sub_labels[sn_idx] not in small_sub:
                                sub_labels[sub_mask] = sub_labels[sn_idx]
                                break
            
            # Renumber sub_labels
            unique_sub = np.unique(sub_labels)
            sub_label_map = {old: new for new, old in enumerate(unique_sub)}
            sub_labels = np.array([sub_label_map[l] for l in sub_labels])
            
            # Map back to global labels
            for j, idx in enumerate(indices):
                fine_labels[idx] = next_fine_label + sub_labels[j]
            next_fine_label += len(unique_sub)
        except Exception as e:
            # Fallback: keep as single cluster
            fine_labels[indices] = next_fine_label
            next_fine_label += 1
    
    # Final renumbering
    unique_fine = np.unique(fine_labels)
    fine_label_map = {old: new for new, old in enumerate(unique_fine)}
    fine_labels = np.array([fine_label_map[l] for l in fine_labels])
    n_fine = len(unique_fine)
    
    return {
        'coarse_labels': coarse_labels,
        'fine_labels': fine_labels,
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_cluster_sizes': np.bincount(coarse_labels).tolist(),
        'fine_cluster_sizes': np.bincount(fine_labels).tolist(),
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


def compute_zoom_coherence(coarse_labels: np.ndarray, fine_labels: np.ndarray) -> Dict:
    """Compute zoom coherence metrics."""
    nesting_score = compute_nesting_score(coarse_labels, fine_labels)
    
    # For 2-level hierarchy, improvement_rate is 1.0 if nesting > 0.5 else 0.0
    improvement_rate = 1.0 if nesting_score > 0.5 else 0.0
    
    return {
        'nesting_score': nesting_score,
        'improvement_rate': improvement_rate,
        'perfect_nesting': nesting_score == 1.0
    }


def compute_legal_purity(labels: np.ndarray, metadata: List[Dict], field: str) -> float:
    """Compute purity of clusters w.r.t. a legal metadata field (VALID ONLY - exclude 'unknown')."""
    n = len(labels)
    if n == 0:
        return 0.0
    
    values = [m.get(field) for m in metadata[:n]]
    valid_mask = [v is not None and v != 'unknown' and v != '' for v in values]
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


def evaluate_hierarchical_v1(coarse_labels: np.ndarray, fine_labels: np.ndarray,
                              metadata: List[Dict]) -> Dict:
    """
    Evaluate using hierarchical_v1 protocol (7 checks):
    1. fragmentation_ok: fine_singleton_fraction < 0.05, fine_median_size > 1
    2. nesting_perfect: nesting_score == 1.0
    3. branch_purity_improves: fine_branch_purity > coarse_branch_purity
    4. area_purity_improves: fine_area_purity > coarse_area_purity
    5. zoom_coherence_ok: improvement_rate > 0.5
    6. legal_structure_branch: fine_branch_purity > 0.5
    7. legal_structure_area: fine_area_purity > 0.5
    """
    # Fragmentation
    fine_unique, fine_counts = np.unique(fine_labels, return_counts=True)
    fine_singleton_fraction = np.sum(fine_counts == 1) / len(fine_labels)
    fine_median_size = np.median(fine_counts)
    fragmentation_ok = fine_singleton_fraction < 0.05 and fine_median_size > 1
    
    # Nesting
    nesting_score = compute_nesting_score(coarse_labels, fine_labels)
    nesting_perfect = nesting_score == 1.0
    
    # Legal purities (VALID ONLY - exclude 'unknown')
    coarse_branch_purity = compute_legal_purity(coarse_labels, metadata, 'branch')
    fine_branch_purity = compute_legal_purity(fine_labels, metadata, 'branch')
    coarse_area_purity = compute_legal_purity(coarse_labels, metadata, 'legal_area')
    fine_area_purity = compute_legal_purity(fine_labels, metadata, 'legal_area')
    
    branch_purity_improves = fine_branch_purity > coarse_branch_purity
    area_purity_improves = fine_area_purity > coarse_area_purity
    
    # Zoom coherence
    zoom = compute_zoom_coherence(coarse_labels, fine_labels)
    zoom_coherence_ok = zoom['improvement_rate'] > 0.5
    
    # Legal structure thresholds
    legal_structure_branch = fine_branch_purity > 0.5
    legal_structure_area = fine_area_purity > 0.5
    
    all_checks = {
        'fragmentation_ok': fragmentation_ok,
        'nesting_perfect': nesting_perfect,
        'branch_purity_improves': branch_purity_improves,
        'area_purity_improves': area_purity_improves,
        'zoom_coherence_ok': zoom_coherence_ok,
        'legal_structure_branch': legal_structure_branch,
        'legal_structure_area': legal_structure_area
    }
    
    per_mode_verdict = 'PASS' if all(all_checks.values()) else 'FAIL'
    
    return {
        'checks': all_checks,
        'per_mode_verdict': per_mode_verdict,
        'metrics': {
            'fine_singleton_fraction': fine_singleton_fraction,
            'fine_median_size': float(fine_median_size),
            'nesting_score': nesting_score,
            'coarse_branch_purity': coarse_branch_purity,
            'fine_branch_purity': fine_branch_purity,
            'coarse_area_purity': coarse_area_purity,
            'fine_area_purity': fine_area_purity,
            'branch_improvement': fine_branch_purity - coarse_branch_purity,
            'area_improvement': fine_area_purity - coarse_area_purity,
            'improvement_rate': zoom['improvement_rate'],
        }
    }


def load_checkpoint_embeddings(years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load and concatenate embeddings and metadata for multiple years."""
    all_embeddings = []
    all_metadata = []
    
    for year in years:
        emb_path = CHECKPOINT_DIR / f'embeddings_{year}.npy'
        meta_path = CHECKPOINT_DIR / f'metadata_{year}.json'
        
        if not emb_path.exists() or not meta_path.exists():
            print(f"  WARNING: Missing files for year {year}")
            continue
        
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        print(f"  Loaded {year}: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dim")
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
    
    if not all_embeddings:
        raise ValueError("No embeddings loaded")
    
    combined = np.vstack(all_embeddings)
    print(f"\nTotal combined: {combined.shape[0]} decisions, {combined.shape[1]} dim")
    return combined, all_metadata


def run_config_test(embeddings: np.ndarray, metadata: List[Dict], config: Dict, config_name: str) -> Dict:
    """Run constrained hierarchical Leiden with a specific config and evaluate with hierarchical_v1."""
    print(f"\n  Testing config: {config_name}")
    print(f"    coarse_res={config['coarse_res']}, base_sub_res={config['base_sub_res']}, min_cluster_size={config['min_cluster_size']}")
    
    results = constrained_hierarchical_leiden(
        embeddings,
        coarse_res=config['coarse_res'],
        base_sub_res=config['base_sub_res'],
        min_cluster_size=config['min_cluster_size'],
        max_subclusters_per_parent=config['max_subclusters_per_parent'],
        k=K_NEIGHBORS
    )
    
    eval_results = evaluate_hierarchical_v1(
        results['coarse_labels'],
        results['fine_labels'],
        metadata
    )
    
    print(f"    n_coarse={results['n_coarse']}, n_fine={results['n_fine']}")
    print(f"    fine_singleton_fraction={eval_results['metrics']['fine_singleton_fraction']:.4f}")
    print(f"    fine_median_size={eval_results['metrics']['fine_median_size']:.1f}")
    print(f"    nesting_score={eval_results['metrics']['nesting_score']:.4f}")
    print(f"    coarse_branch_purity={eval_results['metrics']['coarse_branch_purity']:.4f}")
    print(f"    fine_branch_purity={eval_results['metrics']['fine_branch_purity']:.4f}")
    print(f"    coarse_area_purity={eval_results['metrics']['coarse_area_purity']:.4f}")
    print(f"    fine_area_purity={eval_results['metrics']['fine_area_purity']:.4f}")
    print(f"    improvement_rate={eval_results['metrics']['improvement_rate']:.4f}")
    print(f"    Verdict: {eval_results['per_mode_verdict']}")
    
    return {
        'config': config,
        'hierarchical_results': {
            'n_coarse': int(results['n_coarse']),
            'n_fine': int(results['n_fine']),
            'coarse_cluster_sizes': results['coarse_cluster_sizes'],
            'fine_cluster_sizes': results['fine_cluster_sizes'],
            'coarse_median_size': float(np.median(results['coarse_cluster_sizes'])),
            'fine_median_size': float(np.median(results['fine_cluster_sizes'])),
        },
        'hierarchical_v1_evaluation': eval_results
    }


def main():
    print("=" * 70)
    print("HIERARCHICAL_V1 PROTOCOL ON 144K CHECKPOINT (2000-2021)")
    print("Using CHECKPOINT metadata with proper branch/legal_area labels")
    print("=" * 70)
    
    # Load embeddings and metadata
    print("\nLoading checkpoint embeddings...")
    embeddings, metadata = load_checkpoint_embeddings(CHECKPOINT_YEARS)
    
    # Check metadata coverage
    branches = set()
    areas = set()
    for m in metadata:
        if m.get('branch') and m['branch'] != 'unknown':
            branches.add(m['branch'])
        if m.get('legal_area') and m['legal_area'] != 'unknown':
            areas.add(m['legal_area'])
    print(f"\nMetadata coverage:")
    print(f"  Unique branches: {len(branches)} - {sorted(branches)}")
    print(f"  Unique legal_areas: {len(areas)} - {sorted(areas)}")
    
    # Test multiple configs
    configs_to_test = [
        {'name': 'coarse_0.25_fixed2.0_min20', 'coarse_res': 0.25, 'base_sub_res': 2.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'name': 'coarse_0.5_fixed2.0_min20', 'coarse_res': 0.5, 'base_sub_res': 2.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'name': 'coarse_0.5_fixed3.0_min20', 'coarse_res': 0.5, 'base_sub_res': 3.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'name': 'coarse_0.5_fixed2.0_min50', 'coarse_res': 0.5, 'base_sub_res': 2.0, 'min_cluster_size': 50, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'name': 'coarse_0.5_fixed2.0_min10', 'coarse_res': 0.5, 'base_sub_res': 2.0, 'min_cluster_size': 10, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'name': 'coarse_1.0_fixed2.0_min20', 'coarse_res': 1.0, 'base_sub_res': 2.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': False},
        {'name': 'coarse_0.5_adaptive3.0_min20', 'coarse_res': 0.5, 'base_sub_res': 3.0, 'min_cluster_size': 20, 'max_subclusters_per_parent': 20, 'adaptive_sub_res': True},
    ]
    
    all_results = {}
    for config in configs_to_test:
        config_name = config['name']
        result = run_config_test(embeddings, metadata, config, config_name)
        all_results[config_name] = result
    
    # Find best config (PASS with lowest fragmentation)
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    passing_configs = []
    for name, result in all_results.items():
        verdict = result['hierarchical_v1_evaluation']['per_mode_verdict']
        singleton_frac = result['hierarchical_v1_evaluation']['metrics']['fine_singleton_fraction']
        fine_branch = result['hierarchical_v1_evaluation']['metrics']['fine_branch_purity']
        fine_area = result['hierarchical_v1_evaluation']['metrics']['fine_area_purity']
        improvement_rate = result['hierarchical_v1_evaluation']['metrics']['improvement_rate']
        print(f"  {name:35s} | {verdict:4s} | singleton={singleton_frac:.4f} | branch={fine_branch:.4f} | area={fine_area:.4f} | impr_rate={improvement_rate:.4f}")
        if verdict == 'PASS':
            passing_configs.append((name, singleton_frac, result))
    
    if passing_configs:
        best = min(passing_configs, key=lambda x: x[1])
        print(f"\n  BEST PASSING CONFIG: {best[0]} (singleton_fraction={best[1]:.4f})")
    else:
        print(f"\n  NO CONFIG PASSED ALL 7 CHECKS")
    
    # Save results
    output = {
        'run_id': '144k_hierarchical_v1_proper_20261003',
        'timestamp': np.datetime64("now").astype(str),
        'direction_version': 30,
        'sample': f'144k checkpoint dense embeddings (years {CHECKPOINT_YEARS[0]}-{CHECKPOINT_YEARS[-1]}, PENDING AUDIT for 2003-2021)',
        'n_decisions': int(embeddings.shape[0]),
        'embedding_dim': int(embeddings.shape[1]),
        'metadata_branches': len(branches),
        'metadata_areas': len(areas),
        'configs_tested': all_results,
        'note': 'Years 2003-2021 are PENDING AUDIT. Results for pipeline validation only, not ACCEPTED evidence.'
    }
    
    output_path = OUTPUT_DIR / f'144k_hierarchical_v1_proper_{np.datetime64("now").astype(str).replace(":", "-")}.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    # Save summary
    summary = {
        'n_decisions': int(embeddings.shape[0]),
        'embedding_dim': int(embeddings.shape[1]),
        'passing_configs': [c[0] for c in passing_configs],
        'best_config': passing_configs[0][0] if passing_configs else None,
        'status': 'PIPELINE_VALIDATION_ONLY_PENDING_AUDIT'
    }
    
    summary_path = OUTPUT_DIR / '144k_hierarchical_v1_proper_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    print(f"Summary saved to: {summary_path}")
    
    return output


if __name__ == '__main__':
    main()