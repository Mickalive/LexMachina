#!/usr/bin/env python3
"""
Run Constrained Hierarchical Leiden on dense embeddings for years 2000-2015 (~99k decisions)
with multiple coarse_res values to test v26 pass viability.
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
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints')
OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_tests')
METADATA_174K_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')

TARGET_YEARS = list(range(2000, 2016))  # 2000-2015 inclusive (16 years)
COARSE_RES_VALUES = [0.15, 0.2, 0.25, 0.3]
MIN_CLUSTER_SIZE = 10
K_NEIGHBORS = 15

def load_dense_embeddings(years):
    """Load and concatenate dense embeddings and metadata for specified years."""
    all_embeddings = []
    all_metadata = []
    total_decisions = 0
    
    for year in years:
        emb_path = CHECKPOINT_DIR / f'embeddings_{year}.npy'
        meta_path = CHECKPOINT_DIR / f'metadata_{year}.json'
        
        if not emb_path.exists():
            logger.warning(f"Embeddings not found for year {year}: {emb_path}")
            continue
        if not meta_path.exists():
            logger.warning(f"Metadata not found for year {year}: {meta_path}")
            continue
            
        logger.info(f"Loading year {year}...")
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
        total_decisions += len(embeddings)
        logger.info(f"  Year {year}: {len(embeddings)} embeddings, {len(metadata)} metadata")
    
    if not all_embeddings:
        raise ValueError("No embeddings loaded!")
    
    embeddings = np.vstack(all_embeddings)
    logger.info(f"Total loaded: {len(embeddings)} embeddings, {len(all_metadata)} metadata, dim={embeddings.shape[1]}")
    
    # Normalize
    embeddings = normalize(embeddings, norm='l2')
    
    return embeddings, all_metadata, total_decisions


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
                                    base_sub_res=3.0,
                                    min_cluster_size=MIN_CLUSTER_SIZE,
                                    max_subclusters_per_parent=20,
                                    adaptive_sub_res=True,
                                    k=K_NEIGHBORS):
    """
    Constrained Hierarchical Leiden:
    - Coarse clustering at coarse_res
    - Fine clustering within each coarse cluster with constraints
    """
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
        cluster_areas = [a for a in cluster_areas if a and a != 'unknown' and a != 'null']
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


def run_for_coarse_res(embeddings, metadata, coarse_res):
    """Run constrained hierarchical Leiden for a specific coarse_res."""
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTING coarse_res={coarse_res}")
    logger.info(f"{'='*60}")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
        embeddings, metadata,
        coarse_res=coarse_res,
        base_sub_res=3.0,
        min_cluster_size=MIN_CLUSTER_SIZE,
        max_subclusters_per_parent=20,
        adaptive_sub_res=True,
        k=K_NEIGHBORS
    )
    
    # Compute metrics
    coarse_purity = compute_branch_purity(coarse_labels, metadata)
    hierarchical_purity = compute_branch_purity(hierarchical_labels, metadata)
    coarse_area_purity = compute_area_purity(coarse_labels, metadata)
    hierarchical_area_purity = compute_area_purity(hierarchical_labels, metadata)
    
    frag_hierarchical = compute_fragmentation(hierarchical_labels)
    frag_coarse = compute_fragmentation(coarse_labels)
    
    zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
    
    logger.info(f"Coarse clusters: {len(set(coarse_labels[coarse_labels != -1]))}")
    logger.info(f"Hierarchical fine clusters: {len(set(hierarchical_labels[hierarchical_labels != -1]))}")
    logger.info(f"Coarse branch purity: {coarse_purity:.4f}")
    logger.info(f"Hierarchical branch purity: {hierarchical_purity:.4f}")
    logger.info(f"Branch purity delta: {hierarchical_purity - coarse_purity:+.4f}")
    logger.info(f"Coarse area purity: {coarse_area_purity:.4f}")
    logger.info(f"Hierarchical area purity: {hierarchical_area_purity:.4f}")
    logger.info(f"Area purity delta: {hierarchical_area_purity - coarse_area_purity:+.4f}")
    logger.info(f"Hierarchical fragmentation: {frag_hierarchical}")
    logger.info(f"Zoom coherence: improvement_rate={zoom_coherence['overall']['improvement_rate']:.4f}, "
                f"mean_improvement={zoom_coherence['overall']['mean_improvement']:.4f}, "
                f"n_parents={zoom_coherence['overall']['n_parents']}")
    
    # v26 Zoom Quality Rule Assessment
    improvement_rate = zoom_coherence['overall']['improvement_rate']
    branch_delta = hierarchical_purity - coarse_purity
    area_delta = hierarchical_area_purity - coarse_area_purity
    singleton_frac = frag_hierarchical['singleton_fraction']
    
    v26_pass = (
        branch_delta > 0 and
        area_delta > 0 and
        improvement_rate > 0.5 and
        singleton_frac < 0.01  # Less than 1% singletons
    )
    
    logger.info(f"\n=== v26 Zoom Quality Rule Assessment (coarse_res={coarse_res}) ===")
    logger.info(f"Branch purity improvement: {branch_delta:+.4f} {'PASS' if branch_delta > 0 else 'FAIL'}")
    logger.info(f"Area purity improvement: {area_delta:+.4f} {'PASS' if area_delta > 0 else 'FAIL'}")
    logger.info(f"Branch improvement_rate > 0.5: {improvement_rate:.4f} {'PASS' if improvement_rate > 0.5 else 'FAIL'}")
    logger.info(f"Fragmentation (singleton_fraction < 0.01): {singleton_frac:.4f} {'PASS' if singleton_frac < 0.01 else 'FAIL'}")
    logger.info(f"OVERALL v26 PASS: {v26_pass}")
    
    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output = {
        'run_id': f"constrained_hierarchical_dense_2000_2015_coarse{coarse_res}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'sample_size': len(embeddings),
        'years': TARGET_YEARS,
        'config': {
            'coarse_res': coarse_res,
            'base_sub_res': 3.0,
            'min_cluster_size': MIN_CLUSTER_SIZE,
            'max_subclusters_per_parent': 20,
            'adaptive_sub_res': True,
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
            'nesting': 1.0,
        },
        'zoom_coherence': zoom_coherence,
        'v26_assessment': {
            'branch_purity_delta': branch_delta,
            'area_purity_delta': area_delta,
            'improvement_rate': improvement_rate,
            'singleton_fraction': singleton_frac,
            'v26_pass': v26_pass,
        },
        'cluster_info': cluster_info,
    }
    
    output_path = OUTPUT_DIR / f"constrained_hierarchical_dense_2000_2015_coarse{coarse_res}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Results saved to {output_path}")
    
    return output_path, v26_pass, output


def main():
    logger.info(f"Starting constrained hierarchical Leiden coarse_res sweep on dense embeddings for years {TARGET_YEARS}")
    
    # Load dense embeddings once
    embeddings, metadata, total_decisions = load_dense_embeddings(TARGET_YEARS)
    logger.info(f"Final data: {len(embeddings)} decisions, {embeddings.shape[1]} dims")
    
    # Check branch distribution
    branches = [m.get('branch', 'unknown') for m in metadata]
    logger.info(f"Branch distribution: {Counter(branches)}")
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    logger.info(f"Legal area distribution (top 15): {Counter(legal_areas).most_common(15)}")
    
    results = {}
    for coarse_res in COARSE_RES_VALUES:
        output_path, v26_pass, output = run_for_coarse_res(embeddings, metadata, coarse_res)
        results[coarse_res] = {
            'output_path': str(output_path),
            'v26_pass': v26_pass,
            'improvement_rate': output['v26_assessment']['improvement_rate'],
            'branch_delta': output['v26_assessment']['branch_purity_delta'],
            'area_delta': output['v26_assessment']['area_purity_delta'],
            'singleton_fraction': output['v26_assessment']['singleton_fraction'],
            'coarse_purity': output['coarse']['branch_purity'],
            'hierarchical_purity': output['hierarchical']['branch_purity'],
            'coarse_area_purity': output['coarse']['area_purity'],
            'hierarchical_area_purity': output['hierarchical']['area_purity'],
            'n_coarse_clusters': output['coarse']['n_clusters'],
            'n_hierarchical_clusters': output['hierarchical']['n_clusters'],
        }
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY: coarse_res sweep results")
    logger.info(f"{'='*60}")
    for cr, r in results.items():
        logger.info(f"coarse_res={cr}: v26_pass={r['v26_pass']}, improvement_rate={r['improvement_rate']:.4f}, "
                    f"branch_delta={r['branch_delta']:+.4f}, area_delta={r['area_delta']:+.4f}, "
                    f"singleton_frac={r['singleton_fraction']:.4f}, "
                    f"coarse_clusters={r['n_coarse_clusters']}, fine_clusters={r['n_hierarchical_clusters']}")
    
    # Save summary
    summary_path = OUTPUT_DIR / f"dense_99k_coarse_sweep_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'target_years': TARGET_YEARS,
            'sample_size': len(embeddings),
            'coarse_res_values': COARSE_RES_VALUES,
            'results': results
        }, f, indent=2, default=str)
    logger.info(f"Summary saved to {summary_path}")
    
    return results


if __name__ == '__main__':
    main()