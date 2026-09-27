#!/usr/bin/env python3
"""
Test Constrained Hierarchical Leiden on Citation-Role Embeddings at 1k scale
===========================================================================
Tests all 6 citation-role embeddings (citing, following, criticizing, distinguishing, 
overruling, all_weighted) with coarse_res sweep (0.15, 0.2, 0.25, 0.3) 
matching the debiased_citation_blended protocol.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
import argparse
import sys
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path('/home/runner/work/LexMachina/LexMachina')
CITATION_ROLE_DIR = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt')
BASELINE_METADATA = Path('/tmp/lex_accepted/product/results/fractal_map/baseline/metadata.json')
FULL_METADATA = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
OUTPUT_DIR = BASE / 'results/fractal_map/constrained_hierarchical_tests'

MIN_CLUSTER_SIZE = 10
K_NEIGHBORS = 15

COARSE_RES_VALUES = [0.15, 0.2, 0.25, 0.3]
BASE_SUB_RES = 3.0
MAX_SUBCLUSTERS = 20
ADAPTIVE_SUB_RES = True

ROLE_EMBEDDINGS = {
    'citing': 'citation_role_citing_rebuilt.npy',
    'following': 'citation_role_following_rebuilt.npy',
    'criticizing': 'citation_role_criticizing_rebuilt.npy',
    'distinguishing': 'citation_role_distinguishing_rebuilt.npy',
    'overruling': 'citation_role_overruling_rebuilt.npy',
    'all_weighted': 'citation_role_all_weighted_rebuilt.npy',
}


def load_metadata_with_branch():
    """Load baseline 1000 metadata and enrich with branch from full 174k metadata."""
    with open(BASELINE_METADATA) as f:
        baseline = json.load(f)
    with open(FULL_METADATA) as f:
        full = json.load(f)
    
    full_map = {m['decision_id']: m for m in full}
    
    enriched = []
    for m in baseline:
        m2 = m.copy()
        if m['decision_id'] in full_map:
            m2['branch'] = full_map[m['decision_id']].get('branch', 'unknown')
        else:
            m2['branch'] = 'unknown'
        enriched.append(m2)
    
    has_branch = [e for e in enriched if e.get('branch') and e.get('branch') != 'unknown']
    logger.info(f"Enriched metadata: {len(enriched)} total, {len(has_branch)} with branch, {len(enriched)-len(has_branch)} unknown")
    return enriched


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on embeddings."""
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership), partition.modularity


def constrained_hierarchical_leiden(embeddings, metadata, 
                                    coarse_res=0.25, 
                                    base_sub_res=BASE_SUB_RES,
                                    min_cluster_size=MIN_CLUSTER_SIZE,
                                    max_subclusters_per_parent=MAX_SUBCLUSTERS,
                                    adaptive_sub_res=ADAPTIVE_SUB_RES,
                                    k=K_NEIGHBORS):
    """
    Constrained Hierarchical Leiden:
    - Coarse clustering at coarse_res
    - Fine clustering within each coarse cluster with constraints:
      * Minimum cluster size enforced
      * Adaptive sub-resolution: larger clusters get higher resolution
      * Maximum sub-clusters per parent
    """
    logger.info(f"  Constrained hierarchical Leiden: coarse_res={coarse_res}, base_sub_res={base_sub_res}")
    logger.info(f"  min_cluster_size={min_cluster_size}, max_subclusters={max_subclusters_per_parent}, adaptive={adaptive_sub_res}")
    
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run constrained Leiden
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_cluster_size * 2:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0,
                'size': cluster_size, 'too_small': True,
                'sub_res_used': None
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Determine adaptive sub-resolution based on cluster size
        if adaptive_sub_res:
            if cluster_size < 500:
                sub_res = 1.5
            elif cluster_size < 2000:
                sub_res = 2.0
            else:
                sub_res = base_sub_res
        else:
            sub_res = base_sub_res
        
        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        # Filter out sub-clusters that are too small
        valid_sub = []
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            sub_size = sub_mask.sum()
            if sub_size >= min_cluster_size:
                valid_sub.append(sub_id)
        
        # If too many sub-clusters, keep largest
        if len(valid_sub) > max_subclusters_per_parent:
            logger.warning(f"    Coarse {coarse_id}: {len(valid_sub)} sub-clusters > max {max_subclusters_per_parent}, merging smallest")
            sub_sizes = [(sid, (sub_labels == sid).sum()) for sid in valid_sub]
            sub_sizes.sort(key=lambda x: x[1], reverse=True)
            valid_sub = [sid for sid, _ in sub_sizes[:max_subclusters_per_parent]]
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): {len(valid_sub)} sub-clusters (sub_res={sub_res:.1f}), modularity={sub_mod:.4f}")
        
        # Assign global labels
        for sub_id in valid_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False,
                'sub_res_used': sub_res
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
        
        # Handle documents in filtered-out tiny sub-clusters
        assigned_mask = np.isin(sub_labels, valid_sub)
        unassigned_indices = indices[~assigned_mask]
        if len(unassigned_indices) > 0:
            hierarchical_labels[unassigned_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': -1,
                'size': int(len(unassigned_indices)), 'too_small': False,
                'sub_res_used': sub_res, 'is_remainder': True
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    logger.info(f"  Hierarchical: {len(unique_coarse)} coarse -> {sub_cluster_id} fine clusters")
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


def compute_branch_purity(labels, metadata):
    """Compute branch purity."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'unknown' and b != 'null']
        if cluster_branches:
            purities.append(Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches))
    return float(np.mean(purities)) if purities else 0


def compute_area_purity(labels, metadata):
    """Compute legal_area purity."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a != 'unknown']
        if cluster_areas:
            purities.append(Counter(cluster_areas).most_common(1)[0][1] / len(cluster_areas))
    return float(np.mean(purities)) if purities else 0


def compute_fragmentation(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None, 'size_distribution': {}}
    size_dist = Counter(counts.tolist())
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'mean_size': float(np.mean(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
        'size_distribution': {str(k): int(v) for k, v in sorted(size_dist.items())},
        'max_size': int(np.max(counts)),
        'min_size': int(np.min(counts)),
    }


def compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute zoom coherence for hierarchical Leiden."""
    parent_details = {}
    improvements = []
    
    child_to_parent = {}
    for fine_id in np.unique(hierarchical_labels[hierarchical_labels != -1]):
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_cluster_size:
            continue
        coarse_branches = [metadata[j].get('branch') for j in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
        child_purities = []
        for fc in child_clusters:
            fine_mask = hierarchical_labels == fc
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
                continue
            fine_branches = [metadata[j].get('branch') for j in fine_indices]
            fine_branches = [b for b in fine_branches if b and b != 'unknown' and b != 'null']
            if fine_branches:
                child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_clusters),
            }
    
    return {
        'parent_details': parent_details,
        'overall': {
            'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
            'n_parents': len(parent_details),
        }
    }


def run_single_test(role_name, embeddings, metadata, coarse_res):
    """Run constrained hierarchical Leiden for one role at one coarse_res."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {role_name} at coarse_res={coarse_res}")
    logger.info(f"{'='*60}")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
        embeddings, metadata, coarse_res=coarse_res)
    
    coarse_purity = compute_branch_purity(coarse_labels, metadata)
    hierarchical_purity = compute_branch_purity(hierarchical_labels, metadata)
    coarse_area_purity = compute_area_purity(coarse_labels, metadata)
    hierarchical_area_purity = compute_area_purity(hierarchical_labels, metadata)
    
    frag_hierarchical = compute_fragmentation(hierarchical_labels)
    frag_coarse = compute_fragmentation(coarse_labels)
    
    zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
    
    # v26 assessment criteria
    branch_delta = hierarchical_purity - coarse_purity
    area_delta = hierarchical_area_purity - coarse_area_purity
    improvement_rate = zoom_coherence['overall']['improvement_rate']
    singleton_fraction = frag_hierarchical['singleton_fraction']
    
    v26_pass = (improvement_rate > 0.5 and 
                branch_delta > 0 and 
                area_delta > 0 and 
                singleton_fraction < 0.1)
    
    logger.info(f"  Coarse branch purity: {coarse_purity:.4f}")
    logger.info(f"  Hierarchical branch purity: {hierarchical_purity:.4f}")
    logger.info(f"  Branch delta: {branch_delta:.4f}")
    logger.info(f"  Coarse area purity: {coarse_area_purity:.4f}")
    logger.info(f"  Hierarchical area purity: {hierarchical_area_purity:.4f}")
    logger.info(f"  Area delta: {area_delta:.4f}")
    logger.info(f"  Fragmentation: n={frag_hierarchical['n_clusters']}, median={frag_hierarchical['median_size']}, singletons={singleton_fraction:.4f}")
    logger.info(f"  Zoom coherence: improvement_rate={improvement_rate:.4f}, mean_improvement={zoom_coherence['overall']['mean_improvement']:.4f}, n_parents={zoom_coherence['overall']['n_parents']}")
    logger.info(f"  v26 PASS: {v26_pass}")
    
    return {
        'role': role_name,
        'coarse_res': coarse_res,
        'coarse': {
            'n_clusters': len(set(coarse_labels[coarse_labels != -1])),
            'branch_purity': coarse_purity,
            'area_purity': coarse_area_purity,
            'fragmentation': frag_coarse,
        },
        'hierarchical': {
            'n_clusters': len(set(hierarchical_labels[hierarchical_labels != -1])),
            'branch_purity': hierarchical_purity,
            'area_purity': hierarchical_area_purity,
            'fragmentation': frag_hierarchical,
            'nesting': 1.0,
        },
        'zoom_coherence': zoom_coherence,
        'v26_assessment': {
            'branch_purity_delta': branch_delta,
            'area_purity_delta': area_delta,
            'improvement_rate': improvement_rate,
            'singleton_fraction': singleton_fraction,
            'v26_pass': v26_pass
        },
        'cluster_info': cluster_info,
    }


def main():
    parser = argparse.ArgumentParser(description='Test Citation-Role Constrained Hierarchical Leiden')
    parser.add_argument('--roles', nargs='+', default=list(ROLE_EMBEDDINGS.keys()), help='Roles to test')
    parser.add_argument('--coarse-res', nargs='+', type=float, default=COARSE_RES_VALUES, help='Coarse resolutions to test')
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR, help='Output directory')
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metadata
    metadata = load_metadata_with_branch()
    n_decisions = len(metadata)
    logger.info(f"Loaded {n_decisions} decisions with enriched metadata")
    
    # Load embeddings
    role_embeddings = {}
    for role in args.roles:
        if role not in ROLE_EMBEDDINGS:
            logger.warning(f"Unknown role: {role}, skipping")
            continue
        emb_path = CITATION_ROLE_DIR / ROLE_EMBEDDINGS[role]
        emb = np.load(emb_path)
        if emb.shape[0] != n_decisions:
            logger.warning(f"  {role}: embedding shape {emb.shape} != metadata {n_decisions}, using min")
            min_n = min(emb.shape[0], n_decisions)
            emb = emb[:min_n]
        else:
            min_n = n_decisions
        # Normalize
        norms = np.linalg.norm(emb, axis=1)
        valid_mask = norms > 0
        logger.info(f"  {role}: {valid_mask.sum()}/{len(valid_mask)} valid embeddings ({(1-valid_mask.mean())*100:.1f}% zero-norm)")
        emb = emb[valid_mask]
        meta_subset = [m for i, m in enumerate(metadata) if valid_mask[i]]
        emb = normalize(emb, norm='l2')
        role_embeddings[role] = (emb, meta_subset)
        logger.info(f"  {role}: final shape {emb.shape}")
    
    # Run tests
    all_results = {
        'run_id': f"citation_role_constrained_hierarchical_1k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'sample_size': n_decisions,
        'config': {
            'coarse_res_values': args.coarse_res,
            'base_sub_res': BASE_SUB_RES,
            'min_cluster_size': MIN_CLUSTER_SIZE,
            'max_subclusters_per_parent': MAX_SUBCLUSTERS,
            'adaptive_sub_res': ADAPTIVE_SUB_RES,
            'roles_tested': args.roles,
        },
        'results': {}
    }
    
    for role in args.roles:
        if role not in role_embeddings:
            continue
        embeddings, meta_subset = role_embeddings[role]
        all_results['results'][role] = {}
        
        for coarse_res in args.coarse_res:
            result = run_single_test(role, embeddings, meta_subset, coarse_res)
            all_results['results'][role][f'coarse_{coarse_res}'] = result
    
    # Save results
    output_path = args.output_dir / f"constrained_hierarchical_citation_roles_1k_coarse_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {output_path}")
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    for role in args.roles:
        if role not in all_results['results']:
            continue
        logger.info(f"\n{role}:")
        for coarse_res in args.coarse_res:
            key = f'coarse_{coarse_res}'
            if key in all_results['results'][role]:
                r = all_results['results'][role][key]
                v26 = r['v26_assessment']
                logger.info(f"  coarse_res={coarse_res}: v26_pass={v26['v26_pass']}, "
                           f"improvement_rate={v26['improvement_rate']:.3f}, "
                           f"branch_delta={v26['branch_purity_delta']:.3f}, "
                           f"area_delta={v26['area_purity_delta']:.3f}, "
                           f"singletons={v26['singleton_fraction']:.3f}")


if __name__ == '__main__':
    main()