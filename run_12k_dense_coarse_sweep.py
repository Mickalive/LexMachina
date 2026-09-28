#!/usr/bin/env python3
"""
Run constrained hierarchical Leiden on 12k dense embeddings with coarse resolution sweep.
Tests hypothesis: lower coarse_res (0.15, 0.2) improves improvement_rate for dense embeddings
(based on 1k debiased results: 0.15->66.7%, 0.2->75%, 0.25->50%)
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
from sklearn.preprocessing import normalize
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path('/home/runner/work/LexMachina/LexMachina')
EMBEDDING_PATH = BASE / 'results/fractal_map/12k_dense_comprehensive/embeddings_12k_2000_2002.npy'
METADATA_PATH = BASE / 'results/fractal_map/12k_dense_comprehensive/metadata_12k_2000_2002.json'
OUTPUT_DIR = BASE / 'results/fractal_map/12k_dense_comprehensive/coarse_sweep'

MIN_CLUSTER_SIZE = 3
K_NEIGHBORS = 15

def load_data():
    logger.info(f"Loading embeddings from {EMBEDDING_PATH}")
    embeddings = np.load(EMBEDDING_PATH)
    
    logger.info(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    
    n = min(len(embeddings), len(metadata))
    embeddings = embeddings[:n]
    metadata = metadata[:n]
    
    norms = np.linalg.norm(embeddings, axis=1)
    valid_mask = norms > 0
    logger.info(f"Valid embeddings: {valid_mask.sum()}/{len(valid_mask)} ({(1-valid_mask.mean())*100:.1f}% zero-norm)")
    
    embeddings = embeddings[valid_mask]
    metadata = [m for i, m in enumerate(metadata) if valid_mask[i]]
    
    embeddings = normalize(embeddings, norm='l2')
    
    return embeddings, metadata

def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
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
                                    base_sub_res=3.0,
                                    min_cluster_size=MIN_CLUSTER_SIZE,
                                    max_subclusters_per_parent=20,
                                    adaptive_sub_res=False,  # Fixed sub_res as per best 12k config
                                    k=15):
    logger.info(f"Running constrained hierarchical Leiden: coarse_res={coarse_res}, base_sub_res={base_sub_res}")
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
        
        # Fixed sub-resolution (best config from 12k test)
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
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
    }

def compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
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

def convert(obj):
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    return obj

def run_experiment(coarse_res, base_sub_res, min_cluster_size, max_subclusters_per_parent, adaptive_sub_res):
    embeddings, metadata = load_data()
    logger.info(f"Final data: {len(embeddings)} decisions, {embeddings.shape[1]} dims")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
        embeddings, metadata,
        coarse_res=coarse_res,
        base_sub_res=base_sub_res,
        min_cluster_size=min_cluster_size,
        max_subclusters_per_parent=max_subclusters_per_parent,
        adaptive_sub_res=adaptive_sub_res,
        k=K_NEIGHBORS
    )
    
    coarse_purity = compute_branch_purity(coarse_labels, metadata)
    hierarchical_purity = compute_branch_purity(hierarchical_labels, metadata)
    coarse_area_purity = compute_area_purity(coarse_labels, metadata)
    hierarchical_area_purity = compute_area_purity(hierarchical_labels, metadata)
    
    frag_hierarchical = compute_fragmentation(hierarchical_labels)
    frag_coarse = compute_fragmentation(coarse_labels)
    
    zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
    
    logger.info(f"\n=== Results for coarse_res={coarse_res} ===")
    logger.info(f"Coarse clusters: {len(set(coarse_labels[coarse_labels != -1]))}")
    logger.info(f"Hierarchical fine clusters: {len(set(hierarchical_labels[hierarchical_labels != -1]))}")
    logger.info(f"Coarse branch purity: {coarse_purity:.4f}")
    logger.info(f"Hierarchical branch purity: {hierarchical_purity:.4f}")
    logger.info(f"Branch purity delta: {hierarchical_purity - coarse_purity:.4f}")
    logger.info(f"Coarse area purity: {coarse_area_purity:.4f}")
    logger.info(f"Hierarchical area purity: {hierarchical_area_purity:.4f}")
    logger.info(f"Area purity delta: {hierarchical_area_purity - coarse_area_purity:.4f}")
    logger.info(f"Hierarchical fragmentation: {frag_hierarchical}")
    logger.info(f"Zoom coherence: improvement_rate={zoom_coherence['overall']['improvement_rate']:.4f}, "
                f"mean_improvement={zoom_coherence['overall']['mean_improvement']:.4f}, "
                f"n_parents={zoom_coherence['overall']['n_parents']}")
    
    output = {
        'run_id': f"constrained_hierarchical_12k_dense_coarse{coarse_res}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'sample_size': len(embeddings),
        'embedding_type': 'dense_paraphrase_multilingual_mpnet_base_v2_768dim',
        'years': [2000, 2001, 2002],
        'config': {
            'coarse_res': coarse_res,
            'base_sub_res': base_sub_res,
            'min_cluster_size': min_cluster_size,
            'max_subclusters_per_parent': max_subclusters_per_parent,
            'adaptive_sub_res': adaptive_sub_res,
        },
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
            'branch_purity_delta': hierarchical_purity - coarse_purity,
            'area_purity_delta': hierarchical_area_purity - coarse_area_purity,
            'nesting': 1.0,
        },
        'zoom_coherence': zoom_coherence,
        'v26_checks': {
            'branch_monotonic': hierarchical_purity > coarse_purity,
            'area_monotonic': hierarchical_area_purity > coarse_area_purity,
            'improvement_rate_gt_0.5': zoom_coherence['overall']['improvement_rate'] > 0.5,
            'zero_fragmentation': frag_hierarchical['singleton_fraction'] < 0.01,
        }
    }
    
    return output

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Best config from 12k test: fixed sub_res=2.0, min_cluster_size=20, max_subclusters=20
    # Sweep coarse_res: 0.15, 0.2, 0.25 (0.15 and 0.2 worked best at 1k for debiased)
    configs = [
        {'coarse_res': 0.15, 'base_sub_res': 2.0, 'min_cluster_size': 20, 'max_subclusters': 20, 'adaptive': False},
        {'coarse_res': 0.2,  'base_sub_res': 2.0, 'min_cluster_size': 20, 'max_subclusters': 20, 'adaptive': False},
        {'coarse_res': 0.25, 'base_sub_res': 2.0, 'min_cluster_size': 20, 'max_subclusters': 20, 'adaptive': False},
    ]
    
    all_results = []
    for cfg in configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing config: coarse_res={cfg['coarse_res']}, sub_res={cfg['base_sub_res']}, min_size={cfg['min_cluster_size']}, max_sub={cfg['max_subclusters']}")
        logger.info(f"{'='*60}")
        
        result = run_experiment(
            coarse_res=cfg['coarse_res'],
            base_sub_res=cfg['base_sub_res'],
            min_cluster_size=cfg['min_cluster_size'],
            max_subclusters_per_parent=cfg['max_subclusters'],
            adaptive_sub_res=cfg['adaptive']
        )
        
        all_results.append(result)
        
        # Save individual result
        output_path = OUTPUT_DIR / f"12k_dense_coarse{str(cfg['coarse_res']).replace('.', 'p')}_fixed2.0_min20_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, 'w') as f:
            json.dump(convert(result), f, indent=2)
        logger.info(f"Saved to {output_path}")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY: Coarse Resolution Sweep on 12k Dense Embeddings")
    logger.info(f"{'='*60}")
    for r in all_results:
        c = r['config']['coarse_res']
        bp_delta = r['hierarchical']['branch_purity_delta']
        ap_delta = r['hierarchical']['area_purity_delta']
        imp_rate = r['zoom_coherence']['overall']['improvement_rate']
        singleton = r['hierarchical']['fragmentation']['singleton_fraction']
        v26 = 'PASS' if (r['v26_checks']['branch_monotonic'] and r['v26_checks']['area_monotonic'] and r['v26_checks']['improvement_rate_gt_0.5'] and r['v26_checks']['zero_fragmentation']) else 'FAIL'
        logger.info(f"  coarse_res={c}: branch_delta={bp_delta:.4f}, area_delta={ap_delta:.4f}, imp_rate={imp_rate:.4f}, singletons={singleton:.4f}, v26={v26}")
    
    # Save combined results
    combined_path = OUTPUT_DIR / f"12k_dense_coarse_sweep_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(combined_path, 'w') as f:
        json.dump(convert(all_results), f, indent=2)
    logger.info(f"\nCombined results saved to {combined_path}")

if __name__ == '__main__':
    main()
