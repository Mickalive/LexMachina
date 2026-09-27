#!/usr/bin/env python3
"""
Test Alternative Hierarchical Clustering Methods on 3-Year Dense Embeddings (2000-2002, ~12.5k decisions).

Bounded question: Can alternative hierarchical clustering methods (HDBSCAN, hierarchical agglomerative,
multilevel Leiden variants) achieve v26 PASS on 3-year dense embeddings with <10% fragmentation,
thereby validating the dense embedding path for 174k scale?

This is discriminating because:
- If YES: we have a method that works for dense embeddings at small scale, likely to work even better at 174k
- If NO: we need legal-distance to produce 174k dense embeddings before we can validate the dense path
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
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import pairwise_distances

# Try to import hdbscan
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    logging.warning("hdbscan not available, will skip HDBSCAN tests")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
EVAL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/metadata_174k_eval.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/alternative_hierarchical_tests/dense_3yr_20260927")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [2000, 2001, 2002]
K = 15
V26_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3

def load_year_embeddings(year):
    """Load embeddings and metadata for a single year."""
    emb_path = DENSE_EMBEDDINGS_DIR / f"embeddings_{year}.npy"
    meta_path = DENSE_EMBEDDINGS_DIR / f"metadata_{year}.json"
    
    if not emb_path.exists() or not meta_path.exists():
        logger.warning(f"Missing files for year {year}")
        return None, None
    
    embeddings = np.load(emb_path)
    with open(meta_path) as f:
        metadata = json.load(f)
    
    logger.info(f"  Year {year}: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dims")
    return embeddings, metadata

def load_all_dense_embeddings():
    """Load and concatenate embeddings for all 3 years."""
    all_embeddings = []
    all_metadata = []
    all_decision_ids = []
    
    for year in YEARS:
        embeddings, metadata = load_year_embeddings(year)
        if embeddings is None:
            continue
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
        all_decision_ids.extend([m['decision_id'] for m in metadata])
    
    if not all_embeddings:
        return None, None, None
    
    combined_embeddings = np.vstack(all_embeddings)
    logger.info(f"Combined embeddings: {combined_embeddings.shape}")
    return combined_embeddings, all_metadata, all_decision_ids

def load_eval_metadata():
    """Load evaluation metadata for branch/legal_area labels."""
    with open(EVAL_METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded eval metadata: {len(metadata)} entries")
    return metadata

def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on k-NN graph."""
    n = len(embeddings)
    k_actual = min(k, n - 1)
    if k_actual < 1:
        return np.full(n, -1), 0.0
    
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership), partition.modularity

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

def compute_zoom_coherence_id_space(metadata, coarse_labels, fine_labels, field='branch', min_cluster_size=3):
    """Compute zoom coherence in decision-ID space (matching v26 evaluation semantics)."""
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
        if len(cmems) < min_cluster_size:
            continue
        cvals = coarse_vals.get(pc, [])
        if not cvals:
            continue
        
        child_clusters = [fc for fc, p in child_to_parent.items()
                          if p == pc and len(fine_vals.get(fc, [])) >= min_cluster_size]
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
    """Evaluate flat resolution zoom coherence using v26 frozen success rule."""
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

def compute_fragmentation(labels):
    """Compute fragmentation metrics."""
    unique, counts = np.unique(labels[labels != -1], return_counts=True)
    return {
        'n_clusters': int(len(unique)),
        'median_size': float(np.median(counts)),
        'singleton_fraction': float(np.mean(counts == 1)),
        'size_distribution': {int(k): int(v) for k, v in zip(unique, counts)}
    }

def run_flat_leiden_at_v26_resolutions(embeddings, metadata):
    """Run flat Leiden at all v26 resolutions."""
    labels_by_res = {}
    for res in V26_RESOLUTIONS:
        labels, mod = leiden_clustering(embeddings, resolution=res, k=K)
        labels_by_res[res] = labels
        n_clusters = len(set(labels[labels != -1]))
        branch_pur = compute_branch_purity(labels, metadata)
        area_pur = compute_legal_area_purity(labels, metadata)
        logger.info(f"    Flat res={res}: {n_clusters} clusters, branch={branch_pur:.4f}, area={area_pur:.4f}")
    return labels_by_res

def test_hdbscan_hierarchical(embeddings, metadata, min_cluster_size=20, min_samples=5):
    """Test HDBSCAN hierarchical clustering."""
    if not HDBSCAN_AVAILABLE:
        return None
    
    logger.info(f"  Testing HDBSCAN (min_cluster_size={min_cluster_size}, min_samples={min_samples})...")
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',
        cluster_selection_method='eom',
        gen_min_span_tree=True
    )
    
    labels = clusterer.fit_predict(embeddings)
    
    # HDBSCAN returns -1 for noise points
    n_clusters = len(set(labels[labels != -1]))
    n_noise = np.sum(labels == -1)
    
    branch_pur = compute_branch_purity(labels, metadata)
    area_pur = compute_legal_area_purity(labels, metadata)
    frag = compute_fragmentation(labels)
    
    logger.info(f"    HDBSCAN: {n_clusters} clusters, {n_noise} noise ({n_noise/len(labels):.1%}), "
                f"branch={branch_pur:.4f}, area={area_pur:.4f}, singletons={frag['singleton_fraction']:.1%}")
    
    return {
        'method': 'hdbscan',
        'params': {'min_cluster_size': min_cluster_size, 'min_samples': min_samples},
        'labels': labels,
        'n_clusters': n_clusters,
        'n_noise': int(n_noise),
        'branch_purity': branch_pur,
        'area_purity': area_pur,
        'fragmentation': frag,
    }

def test_hierarchical_agglomerative(embeddings, metadata, n_clusters_list, linkage='ward'):
    """Test Hierarchical Agglomerative Clustering at multiple cluster counts."""
    results = {}
    
    # For Ward linkage, need to use euclidean distance
    # For other linkages, can use precomputed distances
    if linkage == 'ward':
        metric = 'euclidean'
        dist_matrix = None
    else:
        metric = 'precomputed'
        logger.info(f"    Computing pairwise distances for {linkage} linkage...")
        dist_matrix = pairwise_distances(embeddings, metric='euclidean')
    
    for n_clusters in n_clusters_list:
        logger.info(f"  Testing Agglomerative ({linkage}, n_clusters={n_clusters})...")
        
        if linkage == 'ward':
            clusterer = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage, metric=metric)
            labels = clusterer.fit_predict(embeddings)
        else:
            clusterer = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage, metric=metric)
            labels = clusterer.fit_predict(dist_matrix)
        
        branch_pur = compute_branch_purity(labels, metadata)
        area_pur = compute_legal_area_purity(labels, metadata)
        frag = compute_fragmentation(labels)
        
        logger.info(f"    Agglomerative ({linkage}, n={n_clusters}): branch={branch_pur:.4f}, "
                    f"area={area_pur:.4f}, singletons={frag['singleton_fraction']:.1%}")
        
        results[f'agglomerative_{linkage}_n{n_clusters}'] = {
            'method': 'agglomerative',
            'linkage': linkage,
            'n_clusters_target': n_clusters,
            'labels': labels,
            'branch_purity': branch_pur,
            'area_purity': area_pur,
            'fragmentation': frag,
        }
    
    return results

def test_constrained_hierarchical_leiden_tuned(embeddings, metadata):
    """Test constrained hierarchical Leiden with more aggressive parameters for small scale."""
    logger.info("  Testing constrained hierarchical Leiden with tuned parameters...")
    
    # More aggressive configs for small scale
    configs = [
        {'name': 'coarse_0.15_min10_adaptive', 'coarse_res': 0.15, 'min_cluster_size': 10, 'sub_res_base': 2.0, 'adaptive': True},
        {'name': 'coarse_0.15_min20_adaptive', 'coarse_res': 0.15, 'min_cluster_size': 20, 'sub_res_base': 2.0, 'adaptive': True},
        {'name': 'coarse_0.2_min10_adaptive', 'coarse_res': 0.2, 'min_cluster_size': 10, 'sub_res_base': 2.5, 'adaptive': True},
        {'name': 'coarse_0.2_min20_adaptive', 'coarse_res': 0.2, 'min_cluster_size': 20, 'sub_res_base': 2.5, 'adaptive': True},
        {'name': 'coarse_0.25_min10_adaptive', 'coarse_res': 0.25, 'min_cluster_size': 10, 'sub_res_base': 3.0, 'adaptive': True},
        {'name': 'coarse_0.25_min20_adaptive', 'coarse_res': 0.25, 'min_cluster_size': 20, 'sub_res_base': 3.0, 'adaptive': True},
        {'name': 'coarse_0.15_min50_fixed2', 'coarse_res': 0.15, 'min_cluster_size': 50, 'sub_res_base': 2.0, 'adaptive': False},
        {'name': 'coarse_0.2_min50_fixed2', 'coarse_res': 0.2, 'min_cluster_size': 50, 'sub_res_base': 2.0, 'adaptive': False},
        {'name': 'coarse_0.25_min50_fixed2', 'coarse_res': 0.25, 'min_cluster_size': 50, 'sub_res_base': 2.0, 'adaptive': False},
    ]
    
    results = {}
    
    for config in configs:
        logger.info(f"    Config: {config['name']}")
        
        # Step 1: Global coarse clustering
        coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=config['coarse_res'], k=K)
        unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
        
        # Step 2: Within each coarse cluster, run Leiden at adaptive sub_res
        hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
        sub_cluster_id = 0
        coarse_to_fine = defaultdict(list)
        
        for coarse_id in unique_coarse:
            mask = coarse_labels == coarse_id
            indices = np.where(mask)[0]
            cluster_size = len(indices)
            
            if cluster_size < config['min_cluster_size']:
                hierarchical_labels[indices] = sub_cluster_id
                coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
                sub_cluster_id += 1
                continue
            
            subset_embeddings = embeddings[indices]
            
            # Adaptive sub-resolution
            if config['adaptive']:
                target_subclusters = max(3, min(30, cluster_size // 50))
                sub_res = config['sub_res_base'] * (15 / target_subclusters) ** 0.5
                sub_res = max(1.0, min(4.0, sub_res))
            else:
                sub_res = config['sub_res_base']
            
            sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=K)
            unique_sub = np.unique(sub_labels[sub_labels != -1])
            
            # Post-process: merge sub-clusters smaller than min_cluster_size
            sub_label_to_indices = {sid: indices[sub_labels == sid] for sid in unique_sub}
            valid_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) >= config['min_cluster_size']]
            tiny_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) < config['min_cluster_size']]
            
            if tiny_sub_labels and valid_sub_labels:
                valid_centroids = {sid: np.mean(subset_embeddings[sub_labels == sid], axis=0) 
                                  for sid in valid_sub_labels}
                for tiny_sid in tiny_sub_labels:
                    tiny_centroid = np.mean(subset_embeddings[sub_labels == tiny_sid], axis=0)
                    best_sid = min(valid_sub_labels, 
                                   key=lambda sid: np.linalg.norm(tiny_centroid - valid_centroids[sid]))
                    sub_labels[sub_labels == tiny_sid] = best_sid
                unique_sub = valid_sub_labels
            
            for sub_id in unique_sub:
                sub_mask = sub_labels == sub_id
                global_indices = indices[sub_mask]
                hierarchical_labels[global_indices] = sub_cluster_id
                coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
                sub_cluster_id += 1
        
        # Evaluate
        coarse_branch = compute_branch_purity(coarse_labels, metadata)
        fine_branch = compute_branch_purity(hierarchical_labels, metadata)
        coarse_area = compute_legal_area_purity(coarse_labels, metadata)
        fine_area = compute_legal_area_purity(hierarchical_labels, metadata)
        
        zoom_branch = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'branch')
        zoom_area = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'legal_area')
        
        coarse_frag = compute_fragmentation(coarse_labels)
        fine_frag = compute_fragmentation(hierarchical_labels)
        
        # Nesting
        unique_fine = np.unique(hierarchical_labels[hierarchical_labels != -1])
        consistent = 0
        for fine_id in unique_fine:
            fine_mask = hierarchical_labels == fine_id
            parent_labels = coarse_labels[fine_mask]
            parent_valid = parent_labels[parent_labels != -1]
            if len(parent_valid) > 0 and len(set(parent_valid.tolist())) == 1:
                consistent += 1
        nesting = consistent / len(unique_fine) if len(unique_fine) > 0 else 0
        
        logger.info(f"      Coarse: {coarse_frag['n_clusters']} clusters, branch={coarse_branch:.4f}")
        logger.info(f"      Fine: {fine_frag['n_clusters']} clusters, branch={fine_branch:.4f}, "
                    f"Δ={fine_branch - coarse_branch:+.4f}, nesting={nesting:.4f}")
        logger.info(f"      Zoom branch: rate={zoom_branch['improvement_rate']:.2%}")
        logger.info(f"      Fragmentation: fine median={fine_frag['median_size']:.1f}, singletons={fine_frag['singleton_fraction']:.1%}")
        
        results[config['name']] = {
            'config': config,
            'coarse_clusters': coarse_frag['n_clusters'],
            'fine_clusters': fine_frag['n_clusters'],
            'coarse_branch_purity': coarse_branch,
            'fine_branch_purity': fine_branch,
            'coarse_area_purity': coarse_area,
            'fine_area_purity': fine_area,
            'branch_improvement': fine_branch - coarse_branch,
            'area_improvement': fine_area - coarse_area,
            'strict_nesting': nesting,
            'zoom_branch': zoom_branch,
            'zoom_area': zoom_area,
            'fragmentation': {
                'coarse': coarse_frag,
                'fine': fine_frag,
            },
        }
    
    return results

def test_multilevel_leiden(embeddings, metadata):
    """Test igraph's built-in multilevel clustering (hierarchical by construction)."""
    logger.info("  Testing igraph multilevel clustering...")
    
    # Build k-NN graph
    n = len(embeddings)
    k_actual = min(K, n - 1)
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    # Multilevel clustering
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=1.0, seed=42, n_iterations=-1)
    
    # Get hierarchical structure from multilevel
    # Note: igraph's multilevel returns a single partition, not full hierarchy
    # We can run at multiple resolutions to simulate hierarchy
    results = {}
    
    for res in V26_RESOLUTIONS:
        part = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=res, seed=42)
        labels = np.array(part.membership)
        
        branch_pur = compute_branch_purity(labels, metadata)
        area_pur = compute_legal_area_purity(labels, metadata)
        frag = compute_fragmentation(labels)
        
        logger.info(f"    Multilevel res={res}: {frag['n_clusters']} clusters, "
                    f"branch={branch_pur:.4f}, area={area_pur:.4f}, singletons={frag['singleton_fraction']:.1%}")
        
        results[f'multilevel_res_{res}'] = {
            'method': 'multilevel_leiden',
            'resolution': res,
            'labels': labels,
            'branch_purity': branch_pur,
            'area_purity': area_pur,
            'fragmentation': frag,
        }
    
    return results

def main():
    logger.info("=== Alternative Hierarchical Clustering on 3-Year Dense Embeddings (2000-2002) ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load dense embeddings
    logger.info("\n1. Loading dense embeddings (2000-2002)...")
    embeddings, dense_metadata, dense_decision_ids = load_all_dense_embeddings()
    if embeddings is None:
        logger.error("No embeddings loaded!")
        return
    
    n_dense = len(embeddings)
    logger.info(f"Total dense decisions: {n_dense}")
    
    # 2. Load evaluation metadata for labels
    logger.info("\n2. Loading evaluation metadata...")
    eval_metadata = load_eval_metadata()
    
    eval_by_id = {m['decision_id']: i for i, m in enumerate(eval_metadata)}
    
    matched_indices = []
    matched_metadata = []
    for i, did in enumerate(dense_decision_ids):
        if did in eval_by_id:
            matched_indices.append(i)
            matched_metadata.append(eval_metadata[eval_by_id[did]])
    
    logger.info(f"Matched {len(matched_indices)}/{n_dense} decisions to eval metadata")
    
    if len(matched_indices) < 1000:
        logger.error("Too few matched decisions!")
        return
    
    embeddings = embeddings[matched_indices]
    metadata = matched_metadata
    n_matched = len(embeddings)
    
    # Check label coverage
    branch_count = sum(1 for m in metadata if m.get('branch') and m.get('branch') not in ('null', 'unknown', None))
    area_count = sum(1 for m in metadata if m.get('legal_area') and m.get('legal_area') not in ('null', 'unknown', None))
    logger.info(f"Branch coverage: {branch_count}/{n_matched} = {branch_count/n_matched:.2%}")
    logger.info(f"Area coverage: {area_count}/{n_matched} = {area_count/n_matched:.2%}")
    
    all_results = {}
    
    # 3. Run flat Leiden at v26 resolutions for baseline
    logger.info("\n3. Running flat Leiden at v26 resolutions (baseline)...")
    flat_labels = run_flat_leiden_at_v26_resolutions(embeddings, metadata)
    flat_v26_eval = evaluate_v26_flat_zoom(flat_labels, metadata)
    all_results['flat_leiden_v26'] = {
        'method': 'flat_leiden',
        'v26_eval': flat_v26_eval,
        'labels_by_res': {str(k): v.tolist() for k, v in flat_labels.items()},
    }
    logger.info(f"  Flat v26: PASS={flat_v26_eval['passes_v26']}, "
                f"branch_mono={flat_v26_eval['branch_monotonic']}, "
                f"area_mono={flat_v26_eval['area_monotonic']}, "
                f"rate>0.5={flat_v26_eval['branch_improvement_rate_gt_0.5_count']}/4")
    
    # 4. Test constrained hierarchical Leiden with tuned parameters
    logger.info("\n4. Testing constrained hierarchical Leiden (tuned for small scale)...")
    constrained_results = test_constrained_hierarchical_leiden_tuned(embeddings, metadata)
    all_results['constrained_hierarchical_leiden_tuned'] = constrained_results
    
    # 5. Test HDBSCAN
    if HDBSCAN_AVAILABLE:
        logger.info("\n5. Testing HDBSCAN hierarchical clustering...")
        for min_cluster_size in [10, 20, 30, 50]:
            for min_samples in [5, 10, 20]:
                result = test_hdbscan_hierarchical(embeddings, metadata, min_cluster_size, min_samples)
                if result:
                    all_results[f'hdbscan_min{min_cluster_size}_samp{min_samples}'] = result
    else:
        logger.info("\n5. HDBSCAN not available, skipping...")
    
    # 6. Test Hierarchical Agglomerative Clustering
    logger.info("\n6. Testing Hierarchical Agglomerative Clustering...")
    n_clusters_list = [20, 30, 40, 50, 60, 80, 100]
    for linkage in ['ward', 'average', 'complete']:
        agg_results = test_hierarchical_agglomerative(embeddings, metadata, n_clusters_list, linkage)
        all_results.update(agg_results)
    
    # 7. Test multilevel Leiden
    logger.info("\n7. Testing multilevel Leiden...")
    multilevel_results = test_multilevel_leiden(embeddings, metadata)
    all_results['multilevel_leiden'] = multilevel_results
    
    # 8. Summary
    logger.info("\n" + "=" * 80)
    logger.info("ALTERNATIVE HIERARCHICAL CLUSTERING 3-YR DENSE SUMMARY")
    logger.info("=" * 80)
    
    logger.info(f"\n  Baseline flat Leiden v26: PASS={flat_v26_eval['passes_v26']}, "
                f"rate>0.5={flat_v26_eval['branch_improvement_rate_gt_0.5_count']}/4")
    
    # Find best results by different criteria
    best_v26 = None
    best_frag = None
    best_branch_delta = None
    
    for name, result in all_results.items():
        if name == 'flat_leiden_v26':
            continue
            
        # Check if it has v26 eval (constrained hierarchical)
        if 'zoom_branch' in result:
            zoom_rate = result['zoom_branch']['improvement_rate'] or 0
            frag = result['fragmentation']['fine']['singleton_fraction']
            branch_delta = result['branch_improvement']
            
            logger.info(f"\n  {name}:")
            logger.info(f"    Branch Δ: {branch_delta:+.4f}, Zoom rate: {zoom_rate:.2%}, "
                        f"Fine singletons: {frag:.1%}, Nesting: {result['strict_nesting']:.4f}")
            
            if zoom_rate > 0.5 and frag < 0.1 and result['strict_nesting'] >= 0.99:
                if best_v26 is None or zoom_rate > best_v26[1]:
                    best_v26 = (name, zoom_rate, frag, branch_delta)
            
            if frag < 0.1:
                if best_frag is None or frag < best_frag[1]:
                    best_frag = (name, frag, zoom_rate, branch_delta)
            
            if branch_delta > 0:
                if best_branch_delta is None or branch_delta > best_branch_delta[1]:
                    best_branch_delta = (name, branch_delta, zoom_rate, frag)
        
        elif 'fragmentation' in result:
            frag = result['fragmentation']['singleton_fraction']
            branch_pur = result['branch_purity']
            logger.info(f"\n  {name}: branch={branch_pur:.4f}, singletons={frag:.1%}")
            
            if frag < 0.1:
                if best_frag is None or frag < best_frag[1]:
                    best_frag = (name, frag, None, branch_pur)
    
    logger.info("\n" + "=" * 80)
    logger.info("BEST RESULTS")
    logger.info("=" * 80)
    
    if best_v26:
        logger.info(f"\n  BEST v26 candidate: {best_v26[0]}")
        logger.info(f"    Zoom rate: {best_v26[1]:.2%}, Fragmentation: {best_v26[2]:.1%}, Branch Δ: {best_v26[3]:+.4f}")
    else:
        logger.info("\n  NO METHOD ACHIEVES v26 PASS with <10% fragmentation and nesting >= 0.99")
    
    if best_frag:
        logger.info(f"\n  LOWEST FRAGMENTATION: {best_frag[0]}")
        logger.info(f"    Fragmentation: {best_frag[1]:.1%}")
    
    if best_branch_delta:
        logger.info(f"\n  HIGHEST BRANCH IMPROVEMENT: {best_branch_delta[0]}")
        logger.info(f"    Branch Δ: {best_branch_delta[1]:+.4f}")
    
    # 9. Save results
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
        "run_id": f"alternative_hierarchical_dense_3yr_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 28,
        "hypothesis": "Alternative hierarchical clustering methods (HDBSCAN, agglomerative, multilevel Leiden, tuned constrained Leiden) on 3-year dense embeddings (2000-2002, ~12.5k decisions) can achieve v26 PASS with <10% fragmentation, validating the dense embedding path for 174k scale",
        "frozen_sample": f"{n_matched} BGer decisions from years 2000-2002 (matched to eval metadata)",
        "frozen_metric": "v26 flat zoom rule (branch/area monotonic + improvement_rate > 0.5 on >=2/4 transitions), fragmentation, strict nesting",
        "success_rule": "v26 PASS AND fine_singleton_fraction < 0.1 AND strict_nesting >= 0.99",
        "flat_baseline": flat_v26_eval,
        "results": all_results,
    }
    
    output_path = OUTPUT_DIR / "alternative_hierarchical_dense_3yr_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Alternative Hierarchical Clustering 3-year Dense experiment complete ===")

if __name__ == "__main__":
    main()