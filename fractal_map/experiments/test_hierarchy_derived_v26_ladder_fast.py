#!/usr/bin/env python3
"""
Test: Can we derive a v26-compliant 5-level ladder from true hierarchical Leiden structure?

Optimized version: Uses stratified sampling and fixed sub-resolution for speed.
Tests at 10k scale first (matching the 12k partial validation that worked).
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchy_derived_v26_ladder")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Modes to test - focus on best TF-IDF modes from zoom quality report
MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5",  # Best branch purity (0.5525)
    "cited_decisions_tfidf_outcome_hybrid_0.7",  # Similar performance
    "cited_decisions_tfidf",                     # Pure citation signal
]

# v26 compressed 5-level resolution ladder
V26_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
K = 15
MIN_CLUSTER_SIZE = 3  # For zoom coherence evaluation

# Sample size for fast iteration (matching 12k partial validation scale)
SAMPLE_SIZE = 12000
np.random.seed(42)

def load_metadata():
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata: {len(metadata)} entries")
    return metadata

def load_embeddings(mode):
    emb_path = EMBEDDINGS_DIR / f"{mode}.npy"
    if not emb_path.exists():
        logger.warning(f"Embeddings not found: {emb_path}")
        return None
    embeddings = np.load(emb_path)
    logger.info(f"Loaded {mode}: {embeddings.shape}")
    return embeddings

def stratified_sample(metadata, embeddings, sample_size=SAMPLE_SIZE):
    """Create stratified sample by branch to preserve distribution."""
    branch_to_indices = defaultdict(list)
    for i, m in enumerate(metadata):
        branch = m.get('branch', 'unknown')
        branch_to_indices[branch].append(i)
    
    # Calculate sample per branch proportional to population
    total = len(metadata)
    sampled_indices = []
    for branch, indices in branch_to_indices.items():
        n_branch = len(indices)
        n_sample = max(1, int(sample_size * n_branch / total))
        n_sample = min(n_sample, n_branch)
        sampled = np.random.choice(indices, size=n_sample, replace=False)
        sampled_indices.extend(sampled.tolist())
    
    sampled_indices = np.array(sampled_indices)
    # If we got more than sample_size, trim
    if len(sampled_indices) > sample_size:
        sampled_indices = np.random.choice(sampled_indices, size=sample_size, replace=False)
    
    logger.info(f"Stratified sample: {len(sampled_indices)} decisions from {len(branch_to_indices)} branches")
    return sampled_indices

def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on k-NN graph."""
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

def hierarchical_leiden_fixed_subres(embeddings, metadata, 
                                    coarse_res=0.5, 
                                    sub_res=2.0,
                                    min_coarse_size=50,
                                    k=15):
    """
    Run hierarchical Leiden with FIXED sub-resolution (no binary search).
    Much faster, and we can test multiple sub_res values.
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at fixed sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_coarse_size:
            # Too small to sub-cluster
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': 0,
                'size': int(cluster_size),
                'too_small': True,
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Run Leiden within subset at fixed sub_res
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): "
                    f"{len(unique_sub)} sub-clusters at sub_res={sub_res:.2f}, modularity={sub_mod:.4f}")
        
        # Assign global labels
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': int(sub_id),
                'size': int(len(global_indices)),
                'too_small': False,
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine

def compute_branch_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'unknown' and b != 'null']
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    return float(np.mean(purities)) if purities else 0

def compute_legal_area_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a != 'unknown' and a != 'null']
        if cluster_areas:
            most_common = Counter(cluster_areas).most_common(1)[0][1]
            purities.append(most_common / len(cluster_areas))
    return float(np.mean(purities)) if purities else 0

def compute_zoom_coherence_id_space(metadata, coarse_labels, fine_labels, field='branch'):
    id_pairs = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        id_pairs[did] = (coarse_labels[i], fine_labels[i])
    
    coarse_vals = defaultdict(list)
    fine_vals = defaultdict(list)
    for i, m in enumerate(metadata):
        did = m['decision_id']
        val = m.get(field)
        if not val or val in ('unknown', 'null'):
            continue
        cc, fc = id_pairs[did]
        coarse_vals[cc].append(val)
        fine_vals[fc].append(val)
    
    coarse_members = defaultdict(list)
    fine_members = defaultdict(list)
    for did, (cc, fc) in id_pairs.items():
        coarse_members[cc].append(did)
        fine_members[fc].append(did)
    
    fine_coarse_counter = defaultdict(Counter)
    for did, (cc, fc) in id_pairs.items():
        fine_coarse_counter[fc][cc] += 1
    child_to_parent = {fc: cc.most_common(1)[0][0]
                       for fc, cc in fine_coarse_counter.items() if cc}
    
    improvements = []
    n_parents = 0
    
    for pc, cmems in coarse_members.items():
        if len(cmems) < MIN_CLUSTER_SIZE:
            continue
        cvals = coarse_vals.get(pc, [])
        if not cvals:
            continue
        
        child_clusters = [fc for fc, p in child_to_parent.items()
                          if p == pc and len(fine_vals.get(fc, [])) >= MIN_CLUSTER_SIZE]
        if not child_clusters:
            continue
        
        child_purities = []
        for fc in child_clusters:
            fvals = fine_vals[fc]
            child_purities.append(Counter(fvals).most_common(1)[0][1] / len(fvals))
        
        coarse_purity = Counter(cvals).most_common(1)[0][1] / len(cvals)
        mean_child = float(np.mean(child_purities))
        improvements.append(mean_child - coarse_purity)
        n_parents += 1
    
    if improvements:
        mean_improvement = float(np.mean(improvements))
        improvement_rate = float(sum(1 for j in improvements if j > 0) / len(improvements))
    else:
        mean_improvement = None
        improvement_rate = None
    
    return {
        'mean_improvement': mean_improvement,
        'improvement_rate': improvement_rate,
        'n_parents': n_parents,
    }

def evaluate_v26_flat_zoom(labels_by_res, metadata):
    transitions = []
    for i in range(len(V26_RESOLUTIONS) - 1):
        coarse_res = V26_RESOLUTIONS[i]
        fine_res = V26_RESOLUTIONS[i + 1]
        
        zoom_branch = compute_zoom_coherence_id_space(metadata, 
                                                       labels_by_res[coarse_res], 
                                                       labels_by_res[fine_res], 
                                                       'branch')
        zoom_area = compute_zoom_coherence_id_space(metadata, 
                                                     labels_by_res[coarse_res], 
                                                     labels_by_res[fine_res], 
                                                     'legal_area')
        
        transitions.append({
            'from_res': coarse_res,
            'to_res': fine_res,
            'branch_improvement_rate': zoom_branch['improvement_rate'],
            'branch_mean_improvement': zoom_branch['mean_improvement'],
            'area_improvement_rate': zoom_area['improvement_rate'],
            'area_mean_improvement': zoom_area['mean_improvement'],
            'n_parents': zoom_branch['n_parents'],
        })
    
    branch_mono = (compute_branch_purity(labels_by_res[V26_RESOLUTIONS[-1]], metadata) > 
                   compute_branch_purity(labels_by_res[V26_RESOLUTIONS[0]], metadata))
    area_mono = (compute_legal_area_purity(labels_by_res[V26_RESOLUTIONS[-1]], metadata) > 
                 compute_legal_area_purity(labels_by_res[V26_RESOLUTIONS[0]], metadata))
    rate_gt_half = sum(1 for t in transitions if t['branch_improvement_rate'] and t['branch_improvement_rate'] > 0.5)
    
    passes = branch_mono and area_mono and (rate_gt_half >= 2)
    
    return {
        'transitions': transitions,
        'branch_monotonic': branch_mono,
        'area_monotonic': area_mono,
        'branch_improvement_rate_gt_0.5_count': rate_gt_half,
        'passes_v26': passes,
    }

def main():
    logger.info("=== Hierarchy-Derived v26 Ladder Experiment (Optimized, 12k sample) ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    metadata_full = load_metadata()
    n_meta_full = len(metadata_full)
    
    all_results = {}
    
    for mode in MODES:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing mode: {mode}")
        logger.info(f"{'='*60}")
        
        embeddings_full = load_embeddings(mode)
        if embeddings_full is None:
            continue
        
        if len(embeddings_full) > n_meta_full:
            embeddings_full = embeddings_full[:n_meta_full]
        
        # Create stratified sample
        sample_indices = stratified_sample(metadata_full, embeddings_full, SAMPLE_SIZE)
        sample_indices.sort()
        
        metadata = [metadata_full[i] for i in sample_indices]
        embeddings = embeddings_full[sample_indices]
        
        logger.info(f"Sample size: {len(metadata)}")
        
        mode_results = {}
        
        # Test different coarse resolutions and sub_resolutions
        configs = [
            {'name': 'coarse_0.25_sub1.5', 'coarse_res': 0.25, 'sub_res': 1.5, 'min_coarse_size': 20},
            {'name': 'coarse_0.25_sub2.0', 'coarse_res': 0.25, 'sub_res': 2.0, 'min_coarse_size': 20},
            {'name': 'coarse_0.25_sub2.5', 'coarse_res': 0.25, 'sub_res': 2.5, 'min_coarse_size': 20},
            {'name': 'coarse_0.5_sub1.5', 'coarse_res': 0.5, 'sub_res': 1.5, 'min_coarse_size': 20},
            {'name': 'coarse_0.5_sub2.0', 'coarse_res': 0.5, 'sub_res': 2.0, 'min_coarse_size': 20},
            {'name': 'coarse_0.5_sub2.5', 'coarse_res': 0.5, 'sub_res': 2.5, 'min_coarse_size': 20},
            {'name': 'coarse_1.0_sub1.5', 'coarse_res': 1.0, 'sub_res': 1.5, 'min_coarse_size': 20},
            {'name': 'coarse_1.0_sub2.0', 'coarse_res': 1.0, 'sub_res': 2.0, 'min_coarse_size': 20},
        ]
        
        for config in configs:
            logger.info(f"\n  Config: {config['name']}")
            
            hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden_fixed_subres(
                embeddings, metadata,
                coarse_res=config['coarse_res'],
                sub_res=config['sub_res'],
                min_coarse_size=config['min_coarse_size'],
                k=K
            )
            
            n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
            n_coarse = len(set(coarse_labels[coarse_labels != -1]))
            
            # Also run flat Leiden at v26 resolutions for comparison
            flat_labels = {}
            for res in V26_RESOLUTIONS:
                labels, mod = leiden_clustering(embeddings, resolution=res, k=K)
                flat_labels[res] = labels
            
            # Evaluate flat Leiden at v26 resolutions (baseline)
            flat_v26 = evaluate_v26_flat_zoom(flat_labels, metadata)
            
            # Evaluate the TRUE hierarchical structure as a 2-level zoom
            zoom_branch = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'branch')
            zoom_area = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'legal_area')
            
            # Hierarchy purity metrics
            coarse_branch_purity = compute_branch_purity(coarse_labels, metadata)
            fine_branch_purity = compute_branch_purity(hierarchical_labels, metadata)
            coarse_area_purity = compute_legal_area_purity(coarse_labels, metadata)
            fine_area_purity = compute_legal_area_purity(hierarchical_labels, metadata)
            
            # Strict nesting
            unique_fine = np.unique(hierarchical_labels[hierarchical_labels != -1])
            consistent = 0
            for fine_id in unique_fine:
                fine_mask = hierarchical_labels == fine_id
                parent_labels = coarse_labels[fine_mask]
                parent_valid = parent_labels[parent_labels != -1]
                if len(parent_valid) > 0 and len(set(parent_valid.tolist())) == 1:
                    consistent += 1
            nesting = consistent / len(unique_fine) if len(unique_fine) > 0 else 0
            
            # Fragmentation
            fine_unique, fine_counts = np.unique(hierarchical_labels[hierarchical_labels != -1], return_counts=True)
            coarse_unique, coarse_counts = np.unique(coarse_labels[coarse_labels != -1], return_counts=True)
            
            logger.info(f"    Coarse clusters: {n_coarse}, median size: {np.median(coarse_counts):.1f}")
            logger.info(f"    Fine clusters: {n_fine}, median size: {np.median(fine_counts):.1f}")
            logger.info(f"    Branch purity: coarse={coarse_branch_purity:.4f}, fine={fine_branch_purity:.4f}")
            logger.info(f"    Area purity: coarse={coarse_area_purity:.4f}, fine={fine_area_purity:.4f}")
            logger.info(f"    Strict nesting: {nesting:.4f}")
            logger.info(f"    Zoom branch: mean_imp={zoom_branch['mean_improvement']:.4f}, rate={zoom_branch['improvement_rate']:.4f}")
            logger.info(f"    Zoom area: mean_imp={zoom_area['mean_improvement']:.4f}, rate={zoom_area['improvement_rate']:.4f}")
            logger.info(f"    Fragmentation: fine singletons={np.mean(fine_counts == 1):.1%}")
            logger.info(f"    Flat v26: PASS={flat_v26['passes_v26']}, rate>0.5={flat_v26['branch_improvement_rate_gt_0.5_count']}/4")
            
            mode_results[config['name']] = {
                'config': config,
                'coarse_clusters': int(n_coarse),
                'fine_clusters': int(n_fine),
                'coarse_branch_purity': coarse_branch_purity,
                'fine_branch_purity': fine_branch_purity,
                'coarse_area_purity': coarse_area_purity,
                'fine_area_purity': fine_area_purity,
                'branch_improvement': fine_branch_purity - coarse_branch_purity,
                'area_improvement': fine_area_purity - coarse_area_purity,
                'strict_nesting': nesting,
                'zoom_branch': zoom_branch,
                'zoom_area': zoom_area,
                'fragmentation': {
                    'coarse_median_size': float(np.median(coarse_counts)),
                    'fine_median_size': float(np.median(fine_counts)),
                    'fine_singleton_fraction': float(np.mean(fine_counts == 1)),
                    'coarse_singleton_fraction': float(np.mean(coarse_counts == 1)),
                },
                'flat_v26_baseline': flat_v26,
            }
        
        all_results[mode] = {
            'mode': mode,
            'n_decisions': len(metadata),
            'configs': mode_results,
        }
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("HIERARCHY-DERIVED v26 LADDER SUMMARY (12k sample)")
    logger.info("=" * 70)
    
    for mode, result in all_results.items():
        logger.info(f"\n  {mode}:")
        for config_name, config_result in result['configs'].items():
            logger.info(f"\n    {config_name}:")
            logger.info(f"      Coarse->Fine: {config_result['coarse_clusters']} -> {config_result['fine_clusters']}")
            logger.info(f"      Branch: {config_result['coarse_branch_purity']:.4f} -> {config_result['fine_branch_purity']:.4f} (Δ={config_result['branch_improvement']:+.4f})")
            logger.info(f"      Area: {config_result['coarse_area_purity']:.4f} -> {config_result['fine_area_purity']:.4f} (Δ={config_result['area_improvement']:+.4f})")
            logger.info(f"      Nesting: {config_result['strict_nesting']:.4f}")
            logger.info(f"      Zoom branch rate: {config_result['zoom_branch']['improvement_rate']:.2%}")
            logger.info(f"      Fragmentation: fine median={config_result['fragmentation']['fine_median_size']:.1f}, singletons={config_result['fragmentation']['fine_singleton_fraction']:.1%}")
            logger.info(f"      Flat v26 baseline: PASS={config_result['flat_v26_baseline']['passes_v26']}, rate>0.5={config_result['flat_v26_baseline']['branch_improvement_rate_gt_0.5_count']}/4")
    
    # Save results
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
    
    output = {
        "run_id": f"hierarchy_derived_v26_ladder_12k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 28,
        "hypothesis": "True hierarchical Leiden structure (controlled fine clusters via fixed sub_res) on 12k sample shows higher purity improvement than flat Leiden, testing if hierarchical zoom coherence is fundamentally better at this scale",
        "frozen_sample": f"{SAMPLE_SIZE} BGer decisions (stratified sample from 2000-2026)",
        "frozen_metric": "Strict nesting, branch/area purity, zoom coherence (v26 semantics), fragmentation",
        "v26_flat_zoom_rule": "Branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on ≥2/4 transitions",
        "note": "12k sample matches the partial validation scale (years 2000-2002) where hierarchical Leiden pipeline worked (improvement_rate=0.80, zero fragmentation)",
        "results": all_results,
    }
    
    output_path = OUTPUT_DIR / "hierarchy_derived_v26_ladder_12k_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Experiment complete ===")

if __name__ == "__main__":
    main()