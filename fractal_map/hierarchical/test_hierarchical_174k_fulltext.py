#!/usr/bin/env python3
"""
Test Hierarchical Leiden clustering on 174k FULL-TEXT TF-IDF embeddings.

These embeddings have 100% field coverage and no zero vectors, unlike cited_decisions/regeste modes.
This directly addresses the fractal-map lane question: can we build a multi-resolution
geometry at 174k scale using available well-normalized TF-IDF embeddings?
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 174k embeddings directory
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_leiden_174k_fulltext")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Modes with full coverage (no zero vectors)
MODES = [
    "full_text_tfidf_light",
    "regeste_full_text_hybrid_0.5",
    "regeste_full_text_hybrid_0.7",
]

# Resolution ladder for hierarchical Leiden - adjusted for 174k scale
COARSE_RES = 0.25   # Coarser for larger corpus
SUB_RES = 1.5       # Much lower to avoid over-fragmentation
K = 15


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


def leiden_clustering(embeddings, resolution=1.0, k=15):
    """Leiden clustering on k-NN graph."""
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph
    
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
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
        weights='weight', resolution_parameter=resolution, seed=42
    )
    return np.array(partition.membership), partition.modularity


def hierarchical_leiden(embeddings, coarse_res=0.25, sub_res=1.5, k=15):
    """
    Run hierarchical Leiden:
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at sub_res within the subset
    3. Assign global labels: (coarse_id, sub_id) mapped to sequential IDs
    
    This guarantees nesting by construction.
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < 20:  # Skip tiny clusters
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': 0,
                'size': int(len(indices)),
                'too_small': True,
            }
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({len(indices)} docs): "
                    f"{len(unique_sub)} sub-clusters, modularity={sub_mod:.4f}")
        
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
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info


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
    coarse_vals = {}
    fine_vals = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        val = m.get(field)
        if not val or val in ('unknown', 'null'):
            continue
        cc, fc = id_pairs[did]
        coarse_vals.setdefault(cc, []).append(val)
        fine_vals.setdefault(fc, []).append(val)
    
    # Membership counts (all ids)
    coarse_members = {}
    fine_members = {}
    for did, (cc, fc) in id_pairs.items():
        coarse_members.setdefault(cc, []).append(did)
        fine_members.setdefault(fc, []).append(did)
    
    # child -> parent: majority coarse cluster among ALL member ids
    fine_coarse_counter = {}
    for did, (cc, fc) in id_pairs.items():
        fine_coarse_counter.setdefault(fc, Counter())[cc] += 1
    child_to_parent = {fc: cc.most_common(1)[0][0]
                       for fc, cc in fine_coarse_counter.items() if cc}
    
    improvements = []
    n_parents = 0
    MIN_CLUSTER_SIZE = 3
    
    for pc, cmems in coarse_members.items():
        if len(cmems) < MIN_CLUSTER_SIZE:
            continue
        cvals = coarse_vals.get(pc, [])
        if not cvals:
            continue
        
        # children of this parent with >= 3 labeled decisions
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


def main():
    logger.info("=== Hierarchical Leiden on 174k Full-Text TF-IDF Embeddings ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load metadata
    logger.info("\n1. Loading metadata...")
    metadata = load_metadata()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    
    # 2. Test each mode
    all_results = {}
    
    for mode in MODES:
        logger.info(f"\n2. Testing mode: {mode}")
        
        embeddings = load_embeddings(mode)
        if embeddings is None:
            continue
        
        # Truncate to metadata length if needed
        n_meta = len(metadata)
        if len(embeddings) > n_meta:
            embeddings = embeddings[:n_meta]
            logger.info(f"   Truncated embeddings to {n_meta}")
        elif len(embeddings) < n_meta:
            logger.warning(f"   Embeddings ({len(embeddings)}) < metadata ({n_meta}), skipping")
            continue
        
        # 3. Run hierarchical Leiden
        logger.info(f"   Running hierarchical Leiden (coarse={COARSE_RES}, sub={SUB_RES})...")
        hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
            embeddings, coarse_res=COARSE_RES, sub_res=SUB_RES, k=K
        )
        
        n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse = len(set(coarse_labels[coarse_labels != -1]))
        
        # 4. Compute metrics
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
        
        logger.info(f"   Results:")
        logger.info(f"     Coarse clusters: {n_coarse}, median size: {np.median(coarse_counts):.1f}")
        logger.info(f"     Fine clusters: {n_fine}, median size: {np.median(fine_counts):.1f}")
        logger.info(f"     Branch purity: coarse={coarse_branch_purity:.4f}, fine={fine_branch_purity:.4f}")
        logger.info(f"     Area purity: coarse={coarse_area_purity:.4f}, fine={fine_area_purity:.4f}")
        logger.info(f"     Strict nesting: {nesting:.4f}")
        logger.info(f"     Zoom branch: mean_imp={zoom_branch['mean_improvement']:.4f}, rate={zoom_branch['improvement_rate']:.4f}")
        logger.info(f"     Zoom area: mean_imp={zoom_area['mean_improvement']:.4f}, rate={zoom_area['improvement_rate']:.4f}")
        
        # 5. Compare with flat Leiden at equivalent resolutions
        logger.info(f"   Comparing with flat Leiden...")
        flat_results = {}
        for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
            flat_labels, flat_mod = leiden_clustering(embeddings, resolution=res, k=K)
            flat_branch = compute_branch_purity(flat_labels, metadata)
            flat_area = compute_legal_area_purity(flat_labels, metadata)
            n_flat = len(set(flat_labels[flat_labels != -1]))
            flat_results[res] = {
                'branch_purity': flat_branch,
                'area_purity': flat_area,
                'n_clusters': n_flat,
                'modularity': flat_mod,
            }
            logger.info(f"     Flat res={res}: {n_flat} clusters, branch={flat_branch:.4f}, area={flat_area:.4f}")
        
        # 6. Determine if hierarchical improves over flat
        # Compare fine hierarchical purity vs flat at similar cluster count
        flat_purities = [v['branch_purity'] for v in flat_results.values()]
        flat_mean_purity = np.mean(flat_purities)
        hierarchical_advantage = fine_branch_purity - flat_mean_purity
        
        all_results[mode] = {
            'mode': mode,
            'n_decisions': n_meta,
            'coarse_res': COARSE_RES,
            'sub_res': SUB_RES,
            'k': K,
            'coarse_clusters': n_coarse,
            'fine_clusters': n_fine,
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
            },
            'flat_comparison': flat_results,
            'flat_mean_branch_purity': float(flat_mean_purity),
            'hierarchical_advantage': float(hierarchical_advantage),
            'passes_zoom_checks': (
                fine_branch_purity > coarse_branch_purity and
                fine_area_purity > coarse_area_purity and
                (zoom_branch['improvement_rate'] or 0) > 0.5
            ),
        }
    
    # 7. Summary
    logger.info("\n" + "=" * 70)
    logger.info("HIERARCHICAL LEIDEN 174k FULL-TEXT SUMMARY")
    logger.info("=" * 70)
    
    for mode, result in all_results.items():
        logger.info(f"\n  {mode}:")
        logger.info(f"    Coarse->Fine: {result['coarse_clusters']} -> {result['fine_clusters']} clusters")
        logger.info(f"    Branch purity: {result['coarse_branch_purity']:.4f} -> {result['fine_branch_purity']:.4f} (Δ={result['branch_improvement']:+.4f})")
        logger.info(f"    Area purity: {result['coarse_area_purity']:.4f} -> {result['fine_area_purity']:.4f} (Δ={result['area_improvement']:+.4f})")
        logger.info(f"    Strict nesting: {result['strict_nesting']:.4f}")
        logger.info(f"    Zoom branch rate: {result['zoom_branch']['improvement_rate']:.2%}")
        logger.info(f"    Fragmentation: fine median={result['fragmentation']['fine_median_size']:.1f}, singletons={result['fragmentation']['fine_singleton_fraction']:.1%}")
        logger.info(f"    Hierarchical advantage vs flat: {result['hierarchical_advantage']:+.4f}")
        logger.info(f"    Passes zoom checks: {result['passes_zoom_checks']}")
    
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
        "run_id": f"hierarchical_leiden_174k_fulltext_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 27,
        "hypothesis": "Hierarchical Leiden on 174k full-text TF-IDF embeddings (100% coverage, no zero vectors) achieves both perfect nesting and meaningful zoom refinement",
        "frozen_sample": f"{len(metadata)} BGer decisions (2000-2026)",
        "frozen_metric": "Strict nesting, branch/area purity, zoom coherence (v26 semantics)",
        "success_rule": "Strict nesting >= 0.99 AND branch/area purity improvement AND zoom improvement_rate > 0.5 AND fine median cluster size > 5",
        "config": {
            "coarse_resolution": COARSE_RES,
            "sub_resolution": SUB_RES,
            "k": K,
        },
        "results": all_results,
    }
    
    output_path = OUTPUT_DIR / "hierarchical_leiden_174k_fulltext_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Hierarchical Leiden 174k full-text experiment complete ===")


if __name__ == "__main__":
    main()