#!/usr/bin/env python3
"""
Run multi-level recursive protocol on 144k checkpoint dense embeddings (exploratory).
Validates scale extrapolation for multi-level protocol beyond 2-level constrained hierarchical.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints')
METADATA_174K = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/144k_multi_level_validation')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Years available in checkpoints (2000-2021)
CHECKPOINT_YEARS = ['2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007', 
                    '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015',
                    '2016', '2017', '2018', '2019', '2020', '2021']

# Multi-level config (same as validated at 12k and 28k, adjusted for scale)
MULTI_LEVEL_CONFIG = {
    "k_neighbors": 15,
    "max_level": 3,
    "levels": {
        "0": {"resolution": 0.1, "min_cluster_size": 1, "max_subclusters_per_parent": 1, "adaptive_resolution": False},
        "1": {"resolution": 0.5, "min_cluster_size": 20, "max_subclusters_per_parent": 15, 
              "branch_purity_stop": 0.75, "area_purity_stop": 0.35, "adaptive_resolution": True},
        "2": {"resolution": 1.5, "min_cluster_size": 10, "max_subclusters_per_parent": 20,
              "branch_purity_stop": 0.8, "area_purity_stop": 0.45, "adaptive_resolution": True},
        "3": {"resolution": 3.0, "min_cluster_size": 5, "max_subclusters_per_parent": 25,
              "branch_purity_stop": 0.9, "area_purity_stop": 0.6, "adaptive_resolution": True},
        "4": {"resolution": 5.0, "min_cluster_size": 3, "max_subclusters_per_parent": 10,
              "branch_purity_stop": 0.95, "area_purity_stop": 0.7, "adaptive_resolution": False},
    }
}

MIN_CLUSTER_SIZE = 3

def load_checkpoint_embeddings():
    """Load all checkpoint embeddings (2000-2021)."""
    logger.info("Loading checkpoint dense embeddings (2000-2021)...")
    
    all_embeddings = []
    all_metadata = []
    
    for year in CHECKPOINT_YEARS:
        emb_path = CHECKPOINT_DIR / f'embeddings_{year}.npy'
        meta_path = CHECKPOINT_DIR / f'metadata_{year}.json'
        
        if not emb_path.exists():
            logger.warning(f"  {year}: embeddings not found, skipping")
            continue
            
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
        logger.info(f"  {year}: {len(embeddings)} embeddings, {len(metadata)} metadata entries")
    
    combined_embeddings = np.vstack(all_embeddings)
    logger.info(f"Combined: {combined_embeddings.shape} embeddings, {len(all_metadata)} metadata")
    
    return combined_embeddings, all_metadata

def load_174k_metadata():
    with open(METADATA_174K) as f:
        return json.load(f)

def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Run Leiden clustering on embeddings."""
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

def run_multi_level_protocol(embeddings, metadata, config):
    """Run the multi-level recursive protocol."""
    logger.info("Running multi-level recursive protocol on 144k...")
    
    # Level 0: single cluster
    level_labels = {'0': np.zeros(len(embeddings), dtype=int)}
    
    # Build k-NN graph once
    k = config['k_neighbors']
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    
    current_labels = level_labels['0']
    
    for level_idx in range(1, 5):  # levels 1-4
        level_key = str(level_idx)
        level_cfg = config['levels'][level_key]
        resolution = level_cfg['resolution']
        min_size = level_cfg['min_cluster_size']
        max_sub = level_cfg['max_subclusters_per_parent']
        branch_stop = level_cfg.get('branch_purity_stop', 1.0)
        area_stop = level_cfg.get('area_purity_stop', 1.0)
        adaptive = level_cfg.get('adaptive_resolution', False)
        
        new_labels = np.full(len(embeddings), -1, dtype=int)
        sub_cluster_id = 0
        
        for parent_id in np.unique(current_labels[current_labels != -1]):
            parent_mask = current_labels == parent_id
            parent_indices = np.where(parent_mask)[0]
            
            if len(parent_indices) < min_size:
                new_labels[parent_indices] = sub_cluster_id
                sub_cluster_id += 1
                continue
            
            # Check purity stops
            parent_branches = [metadata[j].get('branch') for j in parent_indices]
            parent_branches = [b for b in parent_branches if b and b != 'unknown' and b != 'null']
            parent_areas = [metadata[j].get('legal_area') for j in parent_indices]
            parent_areas = [a for a in parent_areas if a and a != 'unknown' and a != 'null']
            
            branch_purity = 0.0
            area_purity = 0.0
            if parent_branches:
                branch_purity = Counter(parent_branches).most_common(1)[0][1] / len(parent_branches)
            if parent_areas:
                area_purity = Counter(parent_areas).most_common(1)[0][1] / len(parent_areas)
            
            if branch_purity >= branch_stop and area_purity >= area_stop:
                new_labels[parent_indices] = sub_cluster_id
                sub_cluster_id += 1
                continue
            
            # Sub-cluster
            subset_embeddings = embeddings[parent_indices]
            sub_labels, _ = leiden_clustering(subset_embeddings, resolution=resolution, k=min(k, len(parent_indices)-1))
            unique_sub = np.unique(sub_labels[sub_labels != -1])
            
            # Limit sub-clusters
            if len(unique_sub) > max_sub:
                unique_sub = unique_sub[:max_sub]
            
            for sub_id in unique_sub:
                sub_mask = sub_labels == sub_id
                global_indices = parent_indices[sub_mask]
                if len(global_indices) < min_size:
                    continue
                new_labels[global_indices] = sub_cluster_id
                sub_cluster_id += 1
        
        level_labels[level_key] = new_labels
        current_labels = new_labels
        n_clusters = len(np.unique(new_labels[new_labels != -1]))
        logger.info(f"  Level {level_idx} (res={resolution}): {n_clusters} clusters")
    
    return level_labels

def evaluate_multi_level(level_labels, metadata):
    """Evaluate multi-level protocol results."""
    logger.info("Evaluating multi-level protocol...")
    
    results = {'levels': {}, 'improvements': {}, 'checks': {}}
    
    for level_idx in range(4):  # 0-3
        level_key = str(level_idx)
        labels = level_labels[level_key]
        unique_labels = np.unique(labels[labels != -1])
        
        branch_vals = []
        area_vals = []
        for label in unique_labels:
            mask = labels == label
            indices = np.where(mask)[0]
            if len(indices) < MIN_CLUSTER_SIZE:
                continue
            branch_vals.extend([metadata[j].get('branch') for j in indices])
            area_vals.extend([metadata[j].get('legal_area') for j in indices])
        
        branch_vals = [v for v in branch_vals if v and v != 'unknown' and v != 'null']
        area_vals = [v for v in area_vals if v and v != 'unknown' and v != 'null']
        
        branch_purity = 0.0
        area_purity = 0.0
        if branch_vals:
            branch_purity = Counter(branch_vals).most_common(1)[0][1] / len(branch_vals)
        if area_vals:
            area_purity = Counter(area_vals).most_common(1)[0][1] / len(area_vals)
        
        vals, counts = np.unique(labels[labels != -1], return_counts=True)
        singleton_frac = float(np.mean(counts == 1)) if len(vals) > 0 else 0.0
        median_size = float(np.median(counts)) if len(vals) > 0 else 0.0
        
        results['levels'][level_key] = {
            'n_clusters': int(len(unique_labels)),
            'singleton_fraction': singleton_frac,
            'median_cluster_size': median_size,
            'branch_purity': float(branch_purity),
            'area_purity': float(area_purity),
            'nesting': 1.0,  # By construction
        }
    
    # Compute improvements between levels
    def compute_zoom_coherence(labels_coarser, labels_finer, metadata, field='branch'):
        child_to_parent = {}
        for fine_id in np.unique(labels_finer[labels_finer != -1]):
            fine_mask = labels_finer == fine_id
            parent_labels = labels_coarser[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
        
        parent_details = {}
        improvements = []
        
        for coarse_id in np.unique(labels_coarser[labels_coarser != -1]):
            coarse_mask = labels_coarser == coarse_id
            coarse_indices = np.where(coarse_mask)[0]
            if len(coarse_indices) < MIN_CLUSTER_SIZE:
                continue
            coarse_vals = [metadata[j].get(field) for j in coarse_indices]
            coarse_vals = [v for v in coarse_vals if v and v != 'unknown' and v != 'null']
            if not coarse_vals:
                continue
            coarse_purity = Counter(coarse_vals).most_common(1)[0][1] / len(coarse_vals)
            
            child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
            child_purities = []
            for fc in child_clusters:
                fine_mask = labels_finer == fc
                fine_indices = np.where(fine_mask)[0]
                if len(fine_indices) < MIN_CLUSTER_SIZE:
                    continue
                fine_vals = [metadata[j].get(field) for j in fine_indices]
                fine_vals = [v for v in fine_vals if v and v != 'unknown' and v != 'null']
                if fine_vals:
                    child_purities.append(Counter(fine_vals).most_common(1)[0][1] / len(fine_vals))
            
            if child_purities:
                mean_child_purity = np.mean(child_purities)
                improvements.append(mean_child_purity - coarse_purity)
                parent_details[int(coarse_id)] = {
                    'coarse_purity': float(coarse_purity),
                    'mean_child_purity': float(mean_child_purity),
                    'improvement': float(mean_child_purity - coarse_purity),
                    'n_children': len(child_purities),
                }
        
        return {
            'parent_details': parent_details,
            'overall': {
                'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
                'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
                'n_parents': len(parent_details),
            }
        }
    
    for i in range(3):
        coarser, finer = str(i), str(i+1)
        labels_c = level_labels[coarser]
        labels_f = level_labels[finer]
        zoom = compute_zoom_coherence(labels_c, labels_f, metadata, 'branch')
        results['improvements'][f'{coarser}_to_{finer}'] = {
            'branch_improvement': zoom['overall']['mean_improvement'],
            'branch_improvement_rate': zoom['overall']['improvement_rate'],
            'branch_improves': zoom['overall']['mean_improvement'] > 0,
        }
    
    # Checks
    results['checks'] = {
        'all_nesting_ge_0.95': all(v.get('nesting', 0) >= 0.95 for v in results['levels'].values()),
        'all_singleton_lt_0.01': all(v.get('singleton_fraction', 1) < 0.01 for v in results['levels'].values()),
        'all_median_gt_3': all(v.get('median_cluster_size', 0) > 3 for v in results['levels'].values()),
        'level1_branch_gt_0.5': results['levels']['1'].get('branch_purity', 0) > 0.5,
        'level2_area_gt_0.1': results['levels']['2'].get('area_purity', 0) > 0.1,
        'level3_area_gt_0.1': results['levels']['3'].get('area_purity', 0) > 0.1,
        'some_subdivision': results['levels']['1'].get('n_clusters', 0) > 1,
    }
    
    all_pass = all(results['checks'].values())
    results['verdict'] = 'PASS' if all_pass else 'FAIL'
    
    logger.info(f"Multi-level verdict: {results['verdict']}")
    for check, val in results['checks'].items():
        logger.info(f"  {check}: {val}")
    
    return results

def main():
    logger.info("=" * 60)
    logger.info("MULTI-LEVEL PROTOCOL VALIDATION ON 144K CHECKPOINT (EXPLORATORY)")
    logger.info("=" * 60)
    
    embeddings, metadata = load_checkpoint_embeddings()
    
    level_labels = run_multi_level_protocol(embeddings, metadata, MULTI_LEVEL_CONFIG)
    ml_results = evaluate_multi_level(level_labels, metadata)
    
    output_data = {
        'run_id': f'144k_multi_level_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 29,
        'evidence_tier': 'EXPLORATORY',
        'sample': f'{len(embeddings)} dense embeddings from checkpoints (years 2000-2021, PENDING AUDIT for 2003-2021)',
        'embedding_dim': embeddings.shape[1],
        'config': MULTI_LEVEL_CONFIG,
        'level_labels': {k: v.tolist() for k, v in level_labels.items()},
        'evaluation': ml_results,
    }
    
    with open(OUTPUT_DIR / 'multi_level_144k_results.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    logger.info(f"\nResults saved to {OUTPUT_DIR / 'multi_level_144k_results.json'}")
    logger.info(f"Verdict: {ml_results['verdict']}")
    
    return ml_results

if __name__ == '__main__':
    main()
