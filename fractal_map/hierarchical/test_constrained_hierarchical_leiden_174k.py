#!/usr/bin/env python3
"""
Test Constrained Hierarchical Leiden on 174k TF-IDF Embeddings.

Addresses the over-fragmentation problem identified in the 174k zoom quality report:
- Sub_res=3.0 was too aggressive for large coarse clusters
- Median cluster size = 1.0, >99% singletons
- Strict nesting < 1.0 at coarse transitions (0.44-0.61)

This experiment tests:
1. min_cluster_size constraint to prevent over-fragmentation
2. Adaptive sub_resolution per coarse cluster (lower resolution for larger clusters)
3. Different coarse resolutions to find optimal hierarchy depth

Frozen evaluation: v26 success rule (branch/area monotonicity + improvement_rate > 0.5 on ≥2/4 transitions)
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
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_174k")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Modes to test - focus on the best-performing TF-IDF modes from zoom quality report
MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5",  # Best branch purity (0.5525)
    "cited_decisions_tfidf_outcome_hybrid_0.7",  # Similar performance
    "cited_decisions_tfidf",                     # Pure citation signal
]

# Resolution ladder for v26 evaluation (compressed 5-level)
V26_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
K = 15
MIN_CLUSTER_SIZE = 3  # For zoom coherence evaluation


def load_metadata():
    """Load evaluation metadata with branch and legal_area."""
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata: {len(metadata)} entries")
    return metadata


def load_embeddings(mode):
    """Load embeddings for a mode."""
    emb_path = EMBEDDINGS_DIR / f"{mode}.npy"
    if not emb_path.exists():
        logger.warning(f"Embeddings not found: {emb_path}")
        return None
    embeddings = np.load(emb_path)
    logger.info(f"Loaded {mode}: {embeddings.shape}")
    return embeddings


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


def hierarchical_leiden_constrained(embeddings, metadata, coarse_res=0.5, 
                                     min_cluster_size=20, 
                                     sub_res_base=3.0,
                                     adaptive_sub_res=True,
                                     k=15):
    """
    Run constrained hierarchical Leiden:
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at adaptive sub_res within the subset
    3. Enforce min_cluster_size - merge tiny clusters
    4. Assign global labels with guaranteed nesting
    
    adaptive_sub_res: if True, use lower resolution for larger clusters to prevent over-fragmentation
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at adaptive sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_cluster_size:
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
        
        # Adaptive sub-resolution: lower resolution for larger clusters
        if adaptive_sub_res:
            # Heuristic: scale sub_res inversely with cluster size
            # Target ~10-20 sub-clusters per coarse cluster
            target_subclusters = max(5, min(50, cluster_size // 100))
            # Resolution roughly proportional to log(target_subclusters) - calibrate
            sub_res = sub_res_base * (20 / target_subclusters) ** 0.5
            sub_res = max(1.0, min(5.0, sub_res))  # Clamp to reasonable range
        else:
            sub_res = sub_res_base
        
        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): "
                    f"{len(unique_sub)} sub-clusters at sub_res={sub_res:.2f}, modularity={sub_mod:.4f}")
        
        # Post-process: merge sub-clusters smaller than min_cluster_size
        sub_label_to_indices = {sid: indices[sub_labels == sid] for sid in unique_sub}
        
        # Identify clusters to merge
        valid_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) >= min_cluster_size]
        tiny_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) < min_cluster_size]
        
        # Merge tiny clusters into nearest valid cluster (by centroid distance)
        if tiny_sub_labels and valid_sub_labels:
            valid_centroids = {sid: np.mean(subset_embeddings[sub_labels == sid], axis=0) 
                              for sid in valid_sub_labels}
            for tiny_sid in tiny_sub_labels:
                tiny_centroid = np.mean(subset_embeddings[sub_labels == tiny_sid], axis=0)
                # Find nearest valid cluster
                best_sid = min(valid_sub_labels, 
                               key=lambda sid: np.linalg.norm(tiny_centroid - valid_centroids[sid]))
                sub_labels[sub_labels == tiny_sid] = best_sid
            unique_sub = valid_sub_labels
        
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


def compute_strict_nesting(hierarchical_labels, coarse_labels):
    """Compute strict nesting score: fraction of fine clusters whose members share ONE coarse parent."""
    unique_fine = np.unique(hierarchical_labels[hierarchical_labels != -1])
    consistent = 0
    
    for fine_id in unique_fine:
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_valid = parent_labels[parent_labels != -1]
        if len(parent_valid) > 0:
            if len(set(parent_valid.tolist())) == 1:
                consistent += 1
    
    score = consistent / len(unique_fine) if len(unique_fine) > 0 else 0
    return float(score)


def compute_branch_purity(labels, metadata):
    """Compute mean branch purity per cluster."""
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
    """Compute mean legal_area purity per cluster."""
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
    """
    Compute zoom coherence in decision-ID space (matching v26 evaluation semantics).
    """
    id_pairs = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        id_pairs[did] = (coarse_labels[i], fine_labels[i])
    
    # Labeled values per cluster
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
    
    # Membership counts (all ids)
    coarse_members = defaultdict(list)
    fine_members = defaultdict(list)
    for did, (cc, fc) in id_pairs.items():
        coarse_members[cc].append(did)
        fine_members[fc].append(did)
    
    # child -> parent: majority coarse cluster among ALL member ids
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
        
        # children of this parent with >= MIN_CLUSTER_SIZE labeled decisions
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
    """
    Evaluate flat resolution zoom coherence using v26 frozen success rule.
    Returns per-transition metrics and overall PASS/FAIL.
    """
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
    
    # v26 success rule: branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on ≥2/4 transitions
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
    logger.info("=== Constrained Hierarchical Leiden on 174k TF-IDF Embeddings ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load metadata
    logger.info("\n1. Loading metadata...")
    metadata = load_metadata()
    n_meta = len(metadata)
    
    # 2. Test each mode with different constraint configurations
    all_results = {}
    
    # Constraint configurations to test
    constraint_configs = [
        {
            'name': 'coarse_0.25_adaptive_min20',
            'coarse_res': 0.25,
            'min_cluster_size': 20,
            'sub_res_base': 3.0,
            'adaptive_sub_res': True,
        },
        {
            'name': 'coarse_0.5_adaptive_min20',
            'coarse_res': 0.5,
            'min_cluster_size': 20,
            'sub_res_base': 3.0,
            'adaptive_sub_res': True,
        },
        {
            'name': 'coarse_0.5_adaptive_min50',
            'coarse_res': 0.5,
            'min_cluster_size': 50,
            'sub_res_base': 3.0,
            'adaptive_sub_res': True,
        },
        {
            'name': 'coarse_1.0_adaptive_min20',
            'coarse_res': 1.0,
            'min_cluster_size': 20,
            'sub_res_base': 3.0,
            'adaptive_sub_res': True,
        },
        {
            'name': 'coarse_0.5_fixed3.0_min20',
            'coarse_res': 0.5,
            'min_cluster_size': 20,
            'sub_res_base': 3.0,
            'adaptive_sub_res': False,
        },
        {
            'name': 'coarse_0.5_fixed2.0_min20',
            'coarse_res': 0.5,
            'min_cluster_size': 20,
            'sub_res_base': 2.0,
            'adaptive_sub_res': False,
        },
    ]
    
    for mode in MODES:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing mode: {mode}")
        logger.info(f"{'='*60}")
        
        embeddings = load_embeddings(mode)
        if embeddings is None:
            continue
        
        # Truncate to metadata length if needed
        if len(embeddings) > n_meta:
            embeddings = embeddings[:n_meta]
            logger.info(f"   Truncated embeddings to {n_meta}")
        elif len(embeddings) < n_meta:
            logger.warning(f"   Embeddings ({len(embeddings)}) < metadata ({n_meta}), skipping")
            continue
        
        mode_results = {}
        
        for config in constraint_configs:
            logger.info(f"\n  Config: {config['name']}")
            
            hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden_constrained(
                embeddings, metadata,
                coarse_res=config['coarse_res'],
                min_cluster_size=config['min_cluster_size'],
                sub_res_base=config['sub_res_base'],
                adaptive_sub_res=config['adaptive_sub_res'],
                k=K
            )
            
            n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
            n_coarse = len(set(coarse_labels[coarse_labels != -1]))
            
            # Compute metrics
            coarse_branch_purity = compute_branch_purity(coarse_labels, metadata)
            fine_branch_purity = compute_branch_purity(hierarchical_labels, metadata)
            coarse_area_purity = compute_legal_area_purity(coarse_labels, metadata)
            fine_area_purity = compute_legal_area_purity(hierarchical_labels, metadata)
            nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
            
            # Zoom coherence in ID space (matching v26 semantics)
            zoom_branch = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'branch')
            zoom_area = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'legal_area')
            
            # Fragmentation
            fine_unique, fine_counts = np.unique(hierarchical_labels[hierarchical_labels != -1], return_counts=True)
            coarse_unique, coarse_counts = np.unique(coarse_labels[coarse_labels != -1], return_counts=True)
            
            logger.info(f"    Coarse clusters: {n_coarse}, median size: {np.median(coarse_counts):.1f}")
            logger.info(f"    Fine clusters: {n_fine}, median size: {np.median(fine_counts):.1f}")
            logger.info(f"    Branch purity: coarse={coarse_branch_purity:.4f}, fine={fine_branch_purity:.4f}")
            logger.info(f"    Area purity: coarse={coarse_area_purity:.4f}, fine={fine_area_purity:.4f}")
            logger.info(f"    Strict nesting: {nesting:.4f}")
            logger.info(f"    Zoom branch: mean_imp={zoom_branch['mean_improvement']:.4f}, rate={zoom_branch['improvement_rate']:.4f}")
            logger.info(f"    Fragmentation: fine singletons={np.mean(fine_counts == 1):.1%}")
            
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
            }
        
        # 3. Also run flat Leiden at v26 resolutions for comparison
        logger.info(f"\n  Running flat Leiden at v26 resolutions for comparison...")
        flat_labels = {}
        for res in V26_RESOLUTIONS:
            labels, mod = leiden_clustering(embeddings, resolution=res, k=K)
            flat_labels[res] = labels
            n_clusters = len(set(labels[labels != -1]))
            branch_pur = compute_branch_purity(labels, metadata)
            area_pur = compute_legal_area_purity(labels, metadata)
            logger.info(f"    Flat res={res}: {n_clusters} clusters, branch={branch_pur:.4f}, area={area_pur:.4f}")
        
        # Evaluate flat zoom with v26 rule
        flat_zoom_eval = evaluate_v26_flat_zoom(flat_labels, metadata)
        
        all_results[mode] = {
            'mode': mode,
            'n_decisions': n_meta,
            'constraint_configs': mode_results,
            'flat_v26': flat_zoom_eval,
            'flat_labels_summary': {f"res_{r}": {
                'n_clusters': len(set(flat_labels[r][flat_labels[r] != -1])),
                'branch_purity': compute_branch_purity(flat_labels[r], metadata),
                'area_purity': compute_legal_area_purity(flat_labels[r], metadata),
            } for r in V26_RESOLUTIONS},
        }
    
    # 4. Summary
    logger.info("\n" + "=" * 70)
    logger.info("CONSTRAINED HIERARCHICAL LEIDEN 174k SUMMARY")
    logger.info("=" * 70)
    
    for mode, result in all_results.items():
        logger.info(f"\n  {mode}:")
        logger.info(f"    Flat v26: PASS={result['flat_v26']['passes_v26']}, "
                    f"branch_mono={result['flat_v26']['branch_monotonic']}, "
                    f"area_mono={result['flat_v26']['area_monotonic']}, "
                    f"rate>0.5={result['flat_v26']['branch_improvement_rate_gt_0.5_count']}/4")
        
        for config_name, config_result in result['constraint_configs'].items():
            logger.info(f"\n    {config_name}:")
            logger.info(f"      Coarse->Fine: {config_result['coarse_clusters']} -> {config_result['fine_clusters']}")
            logger.info(f"      Branch: {config_result['coarse_branch_purity']:.4f} -> {config_result['fine_branch_purity']:.4f} (Δ={config_result['branch_improvement']:+.4f})")
            logger.info(f"      Area: {config_result['coarse_area_purity']:.4f} -> {config_result['fine_area_purity']:.4f} (Δ={config_result['area_improvement']:+.4f})")
            logger.info(f"      Nesting: {config_result['strict_nesting']:.4f}")
            logger.info(f"      Zoom branch rate: {config_result['zoom_branch']['improvement_rate']:.2%}")
            logger.info(f"      Fragmentation: fine median={config_result['fragmentation']['fine_median_size']:.1f}, singletons={config_result['fragmentation']['fine_singleton_fraction']:.1%}")
    
    # 5. Save results
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
        "run_id": f"constrained_hierarchical_leiden_174k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 27,
        "hypothesis": "Constrained hierarchical Leiden (min_cluster_size + adaptive sub_resolution) on 174k TF-IDF embeddings reduces over-fragmentation while maintaining nesting and improving zoom refinement",
        "frozen_sample": f"{n_meta} BGer decisions (2000-2026)",
        "frozen_metric": "Strict nesting, branch/area purity, zoom coherence (v26 semantics), fragmentation",
        "success_rule": "Strict nesting >= 0.99 AND branch/area purity improvement AND zoom improvement_rate > 0.5 AND fine_singleton_fraction < 0.1",
        "v26_flat_zoom_rule": "Branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on ≥2/4 transitions",
        "results": all_results,
    }
    
    output_path = OUTPUT_DIR / "constrained_hierarchical_leiden_174k_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Constrained Hierarchical Leiden 174k experiment complete ===")


if __name__ == "__main__":
    main()