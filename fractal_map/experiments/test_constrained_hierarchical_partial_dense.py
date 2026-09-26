#!/usr/bin/env python3
"""
Test Constrained Hierarchical Leiden on PARTIAL Dense Embeddings (years 2000-2002, ~12k).
Exploratory validation of adaptive resolution approach on dense embeddings before 174k arrival.

This does NOT claim 174k results - explicitly partial scale validation.
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
CHECKPOINT_DIR = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints')
META_174K_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_partial_dense')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AVAILABLE_YEARS = ['2000', '2001', '2002']

# Resolution ladder for v26 evaluation (compressed 5-level)
V26_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
K = 15
MIN_CLUSTER_SIZE = 3  # For zoom coherence evaluation


def load_partial_embeddings_and_metadata():
    """Load and concatenate available year embeddings and metadata."""
    all_embeddings = []
    all_metadata = []
    
    for year in AVAILABLE_YEARS:
        emb_path = CHECKPOINT_DIR / f'embeddings_{year}.npy'
        meta_path = CHECKPOINT_DIR / f'metadata_{year}.json'
        
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        logger.info(f'Loaded {year}: embeddings {embeddings.shape}, metadata {len(metadata)}')
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
    
    # Concatenate
    all_embeddings = np.vstack(all_embeddings)
    logger.info(f'Total partial embeddings: {all_embeddings.shape}, metadata: {len(all_metadata)}')
    
    return all_embeddings, all_metadata


def compute_center_projected(embeddings, metadata):
    """Compute language-debiased center_projected embeddings on partial data."""
    languages = sorted(set(m['language'] for m in metadata))
    logger.info(f'Languages in partial data: {languages}')
    
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f'  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}')
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f'Center projected shape: {debiased.shape}')
    norms = np.linalg.norm(debiased, axis=1)
    logger.info(f'Norm stats: min={norms.min():.6f}, max={norms.max():.6f}, mean={norms.mean():.6f}')
    
    return debiased


def load_full_metadata():
    """Load full 174k metadata for evaluation (we'll only use matching IDs)."""
    with open(META_174K_PATH) as f:
        metadata = json.load(f)
    logger.info(f'Loaded full metadata: {len(metadata)} entries')
    return metadata


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
    
    logger.info(f'  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}')
    
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
        
        logger.info(f'    Coarse {coarse_id} ({cluster_size} docs): '
                    f'{len(unique_sub)} sub-clusters at sub_res={sub_res:.2f}, modularity={sub_mod:.4f}')
        
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


def fragmentation_from_labels(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': float(np.mean(counts == 1)),
    }


def main():
    logger.info("=== Constrained Hierarchical Leiden on Partial Dense Embeddings (12k) ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Scale: ~12k decisions (years 2000-2002) - NOT 174k")
    
    # 1. Load partial embeddings and metadata
    logger.info("\n1. Loading partial embeddings...")
    embeddings, partial_metadata = load_partial_embeddings_and_metadata()
    
    # 2. Compute center_projected on partial data
    logger.info("\n2. Computing center_projected (language-debiased)...")
    center_projected = compute_center_projected(embeddings, partial_metadata)
    
    # 3. Load full metadata for evaluation (we'll match by decision_id)
    logger.info("\n3. Loading full metadata for evaluation...")
    full_metadata = load_full_metadata()
    full_meta_by_id = {m['decision_id']: m for m in full_metadata}
    
    # Filter full metadata to only include decisions in our partial set
    partial_ids = set(m['decision_id'] for m in partial_metadata)
    eval_metadata = [m for m in full_metadata if m['decision_id'] in partial_ids]
    logger.info(f'  Evaluation metadata: {len(eval_metadata)} decisions (matched from partial)')
    
    # 4. Test different constraint configurations
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
    
    all_results = {}
    
    for config in constraint_configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Config: {config['name']}")
        logger.info(f"{'='*60}")
        
        hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden_constrained(
            center_projected, eval_metadata,
            coarse_res=config['coarse_res'],
            min_cluster_size=config['min_cluster_size'],
            sub_res_base=config['sub_res_base'],
            adaptive_sub_res=config['adaptive_sub_res'],
            k=K
        )
        
        n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse = len(set(coarse_labels[coarse_labels != -1]))
        
        # Compute metrics
        coarse_branch_purity = compute_branch_purity(coarse_labels, eval_metadata)
        fine_branch_purity = compute_branch_purity(hierarchical_labels, eval_metadata)
        coarse_area_purity = compute_legal_area_purity(coarse_labels, eval_metadata)
        fine_area_purity = compute_legal_area_purity(hierarchical_labels, eval_metadata)
        nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
        
        # Zoom coherence in ID space (matching v26 semantics)
        zoom_branch = compute_zoom_coherence_id_space(eval_metadata, coarse_labels, hierarchical_labels, 'branch')
        zoom_area = compute_zoom_coherence_id_space(eval_metadata, coarse_labels, hierarchical_labels, 'legal_area')
        
        # Fragmentation
        fine_unique, fine_counts = np.unique(hierarchical_labels[hierarchical_labels != -1], return_counts=True)
        coarse_unique, coarse_counts = np.unique(coarse_labels[coarse_labels != -1], return_counts=True)
        
        logger.info(f'  Coarse clusters: {n_coarse}, median size: {np.median(coarse_counts):.1f}')
        logger.info(f'  Fine clusters: {n_fine}, median size: {np.median(fine_counts):.1f}')
        logger.info(f'  Branch purity: coarse={coarse_branch_purity:.4f}, fine={fine_branch_purity:.4f}')
        logger.info(f'  Area purity: coarse={coarse_area_purity:.4f}, fine={fine_area_purity:.4f}')
        logger.info(f'  Strict nesting: {nesting:.4f}')
        logger.info(f'  Zoom branch: mean_imp={zoom_branch["mean_improvement"]:.4f}, rate={zoom_branch["improvement_rate"]:.4f}')
        logger.info(f'  Fragmentation: fine singletons={np.mean(fine_counts == 1):.1%}')
        
        all_results[config['name']] = {
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
    
    # 5. Also run flat Leiden at v26 resolutions for comparison
    logger.info(f"\n{'='*60}")
    logger.info(f"Flat Leiden at v26 resolutions for comparison")
    logger.info(f"{'='*60}")
    
    flat_labels = {}
    for res in V26_RESOLUTIONS:
        labels, mod = leiden_clustering(center_projected, resolution=res, k=K)
        flat_labels[res] = labels
        n_clusters = len(set(labels[labels != -1]))
        branch_pur = compute_branch_purity(labels, eval_metadata)
        area_pur = compute_legal_area_purity(labels, eval_metadata)
        logger.info(f'  Flat res={res}: {n_clusters} clusters, branch={branch_pur:.4f}, area={area_pur:.4f}')
    
    # Evaluate flat zoom with v26 rule
    flat_zoom_eval = evaluate_v26_flat_zoom(flat_labels, eval_metadata)
    logger.info(f'  Flat v26: PASS={flat_zoom_eval["passes_v26"]}, '
                f'branch_mono={flat_zoom_eval["branch_monotonic"]}, '
                f'area_mono={flat_zoom_eval["area_monotonic"]}, '
                f'rate>0.5={flat_zoom_eval["branch_improvement_rate_gt_0.5_count"]}/4')
    
    # 6. Also test the validated hierarchical config (coarse=0.25, sub=3.0) from partial validation
    logger.info(f"\n{'='*60}")
    logger.info(f"Validated hierarchical config (coarse=0.25, sub=3.0) - from 12k partial validation")
    logger.info(f"{'='*60}")
    
    val_hierarchical_labels, val_coarse_labels, val_cluster_info, val_coarse_to_fine = hierarchical_leiden_constrained(
        center_projected, eval_metadata,
        coarse_res=0.25,
        min_cluster_size=20,  # Using same min_cluster_size as constrained
        sub_res_base=3.0,
        adaptive_sub_res=False,  # Fixed sub_res as in original validation
        k=K
    )
    
    val_n_fine = len(set(val_hierarchical_labels[val_hierarchical_labels != -1]))
    val_n_coarse = len(set(val_coarse_labels[val_coarse_labels != -1]))
    val_coarse_branch = compute_branch_purity(val_coarse_labels, eval_metadata)
    val_fine_branch = compute_branch_purity(val_hierarchical_labels, eval_metadata)
    val_coarse_area = compute_legal_area_purity(val_coarse_labels, eval_metadata)
    val_fine_area = compute_legal_area_purity(val_hierarchical_labels, eval_metadata)
    val_nesting = compute_strict_nesting(val_hierarchical_labels, val_coarse_labels)
    val_zoom_branch = compute_zoom_coherence_id_space(eval_metadata, val_coarse_labels, val_hierarchical_labels, 'branch')
    val_zoom_area = compute_zoom_coherence_id_space(eval_metadata, val_coarse_labels, val_hierarchical_labels, 'legal_area')
    val_fine_counts = np.unique(val_hierarchical_labels[val_hierarchical_labels != -1], return_counts=True)[1]
    val_coarse_counts = np.unique(val_coarse_labels[val_coarse_labels != -1], return_counts=True)[1]
    
    logger.info(f'  Coarse clusters: {val_n_coarse}, median size: {np.median(val_coarse_counts):.1f}')
    logger.info(f'  Fine clusters: {val_n_fine}, median size: {np.median(val_fine_counts):.1f}')
    logger.info(f'  Branch purity: coarse={val_coarse_branch:.4f}, fine={val_fine_branch:.4f}')
    logger.info(f'  Area purity: coarse={val_coarse_area:.4f}, fine={val_fine_area:.4f}')
    logger.info(f'  Strict nesting: {val_nesting:.4f}')
    logger.info(f'  Zoom branch: mean_imp={val_zoom_branch["mean_improvement"]:.4f}, rate={val_zoom_branch["improvement_rate"]:.4f}')
    logger.info(f'  Fragmentation: fine singletons={np.mean(val_fine_counts == 1):.1%}')
    
    all_results['validated_coarse_0.25_sub_3.0'] = {
        'config': {'coarse_res': 0.25, 'min_cluster_size': 20, 'sub_res_base': 3.0, 'adaptive_sub_res': False},
        'coarse_clusters': int(val_n_coarse),
        'fine_clusters': int(val_n_fine),
        'coarse_branch_purity': val_coarse_branch,
        'fine_branch_purity': val_fine_branch,
        'coarse_area_purity': val_coarse_area,
        'fine_area_purity': val_fine_area,
        'branch_improvement': val_fine_branch - val_coarse_branch,
        'area_improvement': val_fine_area - val_coarse_area,
        'strict_nesting': val_nesting,
        'zoom_branch': val_zoom_branch,
        'zoom_area': val_zoom_area,
        'fragmentation': {
            'coarse_median_size': float(np.median(val_coarse_counts)),
            'fine_median_size': float(np.median(val_fine_counts)),
            'fine_singleton_fraction': float(np.mean(val_fine_counts == 1)),
            'coarse_singleton_fraction': float(np.mean(val_coarse_counts == 1)),
        },
    }
    
    # 7. Summary
    logger.info("\n" + "=" * 70)
    logger.info("CONSTRAINED HIERARCHICAL LEIDEN PARTIAL DENSE (12k) SUMMARY")
    logger.info("=" * 70)
    
    logger.info(f"\n  Flat v26: PASS={flat_zoom_eval['passes_v26']}, "
                f"branch_mono={flat_zoom_eval['branch_monotonic']}, "
                f"area_mono={flat_zoom_eval['area_monotonic']}, "
                f"rate>0.5={flat_zoom_eval['branch_improvement_rate_gt_0.5_count']}/4")
    
    for config_name, config_result in all_results.items():
        logger.info(f"\n  {config_name}:")
        logger.info(f"    Coarse->Fine: {config_result['coarse_clusters']} -> {config_result['fine_clusters']}")
        logger.info(f"    Branch: {config_result['coarse_branch_purity']:.4f} -> {config_result['fine_branch_purity']:.4f} (Δ={config_result['branch_improvement']:+.4f})")
        logger.info(f"    Area: {config_result['coarse_area_purity']:.4f} -> {config_result['fine_area_purity']:.4f} (Δ={config_result['area_improvement']:+.4f})")
        logger.info(f"    Nesting: {config_result['strict_nesting']:.4f}")
        logger.info(f"    Zoom branch rate: {config_result['zoom_branch']['improvement_rate']:.2%}")
        logger.info(f"    Fragmentation: fine median={config_result['fragmentation']['fine_median_size']:.1f}, singletons={config_result['fragmentation']['fine_singleton_fraction']:.1%}")
    
    # 8. Save results
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
        "run_id": f"constrained_hierarchical_partial_dense_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 27,
        "hypothesis": "Constrained hierarchical Leiden (min_cluster_size + adaptive sub_resolution) on 12k center_projected dense embeddings maintains high purity/nesting while controlling fragmentation",
        "frozen_sample": f"{len(eval_metadata)} BGer decisions (years 2000-2002)",
        "frozen_metric": "Strict nesting, branch/area purity, zoom coherence (v26 semantics), fragmentation",
        "success_rule": "Strict nesting >= 0.99 AND branch/area purity improvement AND zoom improvement_rate > 0.5 AND fine_singleton_fraction < 0.1",
        "v26_flat_zoom_rule": "Branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on ≥2/4 transitions",
        "scale_note": "PARTIAL SCALE VALIDATION - years 2000-2002 only (~12k decisions). NOT 174k evaluation.",
        "results": all_results,
        "flat_v26": flat_zoom_eval,
        "flat_labels_summary": {f"res_{r}": {
            'n_clusters': len(set(flat_labels[r][flat_labels[r] != -1])),
            'branch_purity': compute_branch_purity(flat_labels[r], eval_metadata),
            'area_purity': compute_legal_area_purity(flat_labels[r], eval_metadata),
        } for r in V26_RESOLUTIONS},
    }
    
    output_path = OUTPUT_DIR / "constrained_hierarchical_partial_dense_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Constrained Hierarchical Leiden Partial Dense experiment complete ===")
    logger.info("NOTE: This is PARTIAL scale validation (~12k). Full 174k awaits legal-distance year-split completion.")


if __name__ == "__main__":
    main()