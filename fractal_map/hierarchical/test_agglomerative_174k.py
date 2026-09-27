#!/usr/bin/env python3
"""
Test Agglomerative Hierarchical Clustering on 174k TF-IDF Embeddings.

Agglomerative Ward/Average/Complete PASS v26 frozen rule at 1k scale (nesting=1.0 by construction).
This experiment tests whether they scale to 174k and provide better zoom quality
than constrained hierarchical Leiden.

Frozen evaluation: v26 success rule (branch/area monotonicity + improvement_rate > 0.5 on ≥2/4 transitions)
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone
from sklearn.cluster import AgglomerativeClustering
from sklearn.neighbors import kneighbors_graph
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/alternative_hierarchical_tests")
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

# Agglomerative linkage methods to test
LINKAGE_METHODS = ['ward', 'average', 'complete']


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


def agglomerative_clustering(embeddings, n_clusters, linkage='ward'):
    """Agglomerative clustering with specified linkage."""
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        linkage=linkage,
        metric='euclidean'
    )
    labels = clustering.fit_predict(embeddings)
    return labels


def get_n_clusters_for_resolution(embeddings, resolution, k=15, reference_labels=None):
    """
    Estimate number of clusters for a given Leiden resolution by running Leiden once.
    We'll use this to match agglomerative cluster counts to Leiden resolutions.
    """
    from sklearn.neighbors import kneighbors_graph
    import igraph as ig
    import leidenalg
    
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
        weights='weight', resolution_parameter=resolution, seed=42)
    return len(set(partition.membership))


def hierarchical_agglomerative(embeddings, n_coarse_clusters, linkage='ward'):
    """
    Run agglomerative clustering at two levels:
    1. Coarse level: n_coarse_clusters
    2. Fine level: n_fine_clusters (higher number)
    
    Returns both label sets with guaranteed nesting (agglom is hierarchical by construction).
    """
    # Coarse clustering
    coarse_labels = agglomerative_clustering(embeddings, n_coarse_clusters, linkage)
    
    # For fine clustering, we run agglomerative with more clusters
    # The hierarchy is implicit in the linkage tree, but sklearn doesn't expose it easily.
    # We'll run separate agglomerative at different cluster counts.
    # For true nesting, we'd need to use the linkage tree, but for now we approximate
    # by running at different n_clusters.
    
    return coarse_labels


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
    logger.info("=== Agglomerative Hierarchical Clustering on 174k TF-IDF Embeddings ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load metadata
    logger.info("\n1. Loading metadata...")
    metadata = load_metadata()
    n_meta = len(metadata)
    
    # 2. First, run Leiden at v26 resolutions to get reference cluster counts
    logger.info("\n2. Getting reference cluster counts from Leiden at v26 resolutions...")
    import igraph as ig
    import leidenalg
    
    # Load one mode to get reference counts
    test_embeddings = load_embeddings(MODES[0])
    if test_embeddings is None:
        logger.error("Failed to load test embeddings")
        return
    if len(test_embeddings) > n_meta:
        test_embeddings = test_embeddings[:n_meta]
    
    leiden_n_clusters = {}
    for res in V26_RESOLUTIONS:
        k_actual = min(K, len(test_embeddings) - 1)
        graph = kneighbors_graph(test_embeddings, n_neighbors=k_actual, metric='euclidean',
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
            weights='weight', resolution_parameter=res, seed=42)
        leiden_n_clusters[res] = len(set(partition.membership))
        logger.info(f"  Leiden res={res}: {leiden_n_clusters[res]} clusters")
    
    # 3. Test each mode with agglomerative clustering
    all_results = {}
    
    for mode in MODES:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing mode: {mode}")
        logger.info(f"{'='*60}")
        
        embeddings = load_embeddings(mode)
        if embeddings is None:
            continue
        
        if len(embeddings) > n_meta:
            embeddings = embeddings[:n_meta]
            logger.info(f"   Truncated embeddings to {n_meta}")
        elif len(embeddings) < n_meta:
            logger.warning(f"   Embeddings ({len(embeddings)}) < metadata ({n_meta}), skipping")
            continue
        
        mode_results = {}
        
        # Test each linkage method
        for linkage in LINKAGE_METHODS:
            logger.info(f"\n  Linkage: {linkage}")
            
            linkage_results = {}
            
            # Run at each v26 resolution cluster count
            labels_by_res = {}
            for res in V26_RESOLUTIONS:
                n_clusters = leiden_n_clusters[res]
                logger.info(f"    Running agglomerative {linkage} with n_clusters={n_clusters}...")
                
                try:
                    labels = agglomerative_clustering(embeddings, n_clusters, linkage)
                    labels_by_res[res] = labels
                    
                    n_found = len(set(labels[labels != -1]))
                    branch_pur = compute_branch_purity(labels, metadata)
                    area_pur = compute_legal_area_purity(labels, metadata)
                    logger.info(f"      Clusters: {n_found}, branch={branch_pur:.4f}, area={area_pur:.4f}")
                except Exception as e:
                    logger.error(f"      Failed: {e}")
                    labels_by_res[res] = None
            
            # Evaluate with v26 rule
            if all(v is not None for v in labels_by_res.values()):
                flat_zoom_eval = evaluate_v26_flat_zoom(labels_by_res, metadata)
                logger.info(f"    v26 Flat Zoom: PASS={flat_zoom_eval['passes_v26']}, "
                           f"branch_mono={flat_zoom_eval['branch_monotonic']}, "
                           f"area_mono={flat_zoom_eval['area_monotonic']}, "
                           f"rate>0.5={flat_zoom_eval['branch_improvement_rate_gt_0.5_count']}/4")
                
                linkage_results['flat_v26'] = flat_zoom_eval
                linkage_results['labels_summary'] = {f"res_{r}": {
                    'n_clusters': len(set(labels_by_res[r][labels_by_res[r] != -1])),
                    'branch_purity': compute_branch_purity(labels_by_res[r], metadata),
                    'area_purity': compute_legal_area_purity(labels_by_res[r], metadata),
                } for r in V26_RESOLUTIONS}
            else:
                linkage_results['flat_v26'] = {'passes_v26': False, 'error': 'Some resolutions failed'}
            
            mode_results[linkage] = linkage_results
        
        # Also run Leiden at v26 resolutions for direct comparison
        logger.info(f"\n  Running Leiden at v26 resolutions for comparison...")
        flat_labels = {}
        for res in V26_RESOLUTIONS:
            k_actual = min(K, len(embeddings) - 1)
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
                weights='weight', resolution_parameter=res, seed=42)
            flat_labels[res] = np.array(partition.membership)
            n_clusters = len(set(flat_labels[res][flat_labels[res] != -1]))
            branch_pur = compute_branch_purity(flat_labels[res], metadata)
            area_pur = compute_legal_area_purity(flat_labels[res], metadata)
            logger.info(f"    Flat res={res}: {n_clusters} clusters, branch={branch_pur:.4f}, area={area_pur:.4f}")
        
        leiden_flat_zoom = evaluate_v26_flat_zoom(flat_labels, metadata)
        logger.info(f"    Leiden v26: PASS={leiden_flat_zoom['passes_v26']}, "
                   f"rate>0.5={leiden_flat_zoom['branch_improvement_rate_gt_0.5_count']}/4")
        
        all_results[mode] = {
            'mode': mode,
            'n_decisions': n_meta,
            'linkage_methods': mode_results,
            'leiden_flat_v26': leiden_flat_zoom,
            'leiden_n_clusters': leiden_n_clusters,
        }
    
    # 4. Summary
    logger.info("\n" + "=" * 70)
    logger.info("AGGLOMERATIVE HIERARCHICAL CLUSTERING 174k SUMMARY")
    logger.info("=" * 70)
    
    for mode, result in all_results.items():
        logger.info(f"\n  {mode}:")
        logger.info(f"    Leiden v26: PASS={result['leiden_flat_v26']['passes_v26']}, "
                    f"rate>0.5={result['leiden_flat_v26']['branch_improvement_rate_gt_0.5_count']}/4")
        
        for linkage, link_result in result['linkage_methods'].items():
            if 'flat_v26' in link_result and 'passes_v26' in link_result['flat_v26']:
                logger.info(f"    {linkage.capitalize()}: PASS={link_result['flat_v26']['passes_v26']}, "
                           f"rate>0.5={link_result['flat_v26']['branch_improvement_rate_gt_0.5_count']}/4")
            else:
                logger.info(f"    {linkage.capitalize()}: FAILED/ERROR")
    
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
        "run_id": f"agglomerative_174k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 28,
        "hypothesis": "Agglomerative hierarchical clustering (Ward/Average/Complete) on 174k TF-IDF embeddings achieves v26 PASS with nesting=1.0 by construction, providing an alternative to constrained hierarchical Leiden",
        "frozen_sample": f"{n_meta} BGer decisions (2000-2026)",
        "frozen_metric": "Branch/area purity, zoom coherence (v26 semantics), nesting",
        "success_rule": "v26 frozen rule: branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on ≥2/4 transitions",
        "results": all_results,
    }
    
    output_path = OUTPUT_DIR / f"agglomerative_174k_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Agglomerative 174k experiment complete ===")


if __name__ == "__main__":
    main()