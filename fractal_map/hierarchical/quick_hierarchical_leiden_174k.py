#!/usr/bin/env python3
"""
Quick Hierarchical Leiden test on 174k TF-IDF embeddings (single mode, no flat comparison).
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_leiden_174k")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODE = "cited_decisions_tfidf_outcome_hybrid_0.5"
COARSE_RES = 0.5
SUB_RES = 1.5  # Lower to avoid over-fragmentation
K = 15


def load_metadata():
    with open(METADATA_PATH) as f:
        return json.load(f)


def load_embeddings(mode):
    emb_path = EMBEDDINGS_DIR / f"{mode}.npy"
    embeddings = np.load(emb_path)
    return embeddings


def leiden_clustering(embeddings, resolution=1.0, k=15):
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


def hierarchical_leiden(embeddings, coarse_res=0.5, sub_res=1.5, k=15):
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < 20:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0, 'size': int(len(indices)), 'too_small': True
            }
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({len(indices)} docs): {len(unique_sub)} sub-clusters, modularity={sub_mod:.4f}")
        
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False
            }
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info


def compute_strict_nesting(hierarchical_labels, coarse_labels):
    unique_fine = np.unique(hierarchical_labels[hierarchical_labels != -1])
    consistent = 0
    for fine_id in unique_fine:
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_valid = parent_labels[parent_labels != -1]
        if len(parent_valid) > 0 and len(set(parent_valid.tolist())) == 1:
            consistent += 1
    return float(consistent / len(unique_fine)) if len(unique_fine) > 0 else 0


def compute_branch_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b not in ('unknown', 'null')]
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
        cluster_areas = [a for a in cluster_areas if a and a not in ('unknown', 'null')]
        if cluster_areas:
            most_common = Counter(cluster_areas).most_common(1)[0][1]
            purities.append(most_common / len(cluster_areas))
    return float(np.mean(purities)) if purities else 0


def compute_zoom_coherence_id_space(metadata, coarse_labels, fine_labels, field='branch'):
    id_pairs = {}
    for i, m in enumerate(metadata):
        did = m['decision_id']
        id_pairs[did] = (coarse_labels[i], fine_labels[i])
    
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
    
    coarse_members = {}
    fine_members = {}
    for did, (cc, fc) in id_pairs.items():
        coarse_members.setdefault(cc, []).append(did)
        fine_members.setdefault(fc, []).append(did)
    
    fine_coarse_counter = {}
    for did, (cc, fc) in id_pairs.items():
        fine_coarse_counter.setdefault(fc, Counter())[cc] += 1
    child_to_parent = {fc: cc.most_common(1)[0][0] for fc, cc in fine_coarse_counter.items() if cc}
    
    improvements = []
    n_parents = 0
    MIN_CLUSTER_SIZE = 3
    
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
        return {
            'mean_improvement': float(np.mean(improvements)),
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)),
            'n_parents': n_parents,
        }
    return {'mean_improvement': None, 'improvement_rate': None, 'n_parents': 0}


def main():
    logger.info(f"=== Quick Hierarchical Leiden: {MODE} ===")
    
    metadata = load_metadata()
    n_meta = len(metadata)
    
    embeddings = load_embeddings(MODE)
    if len(embeddings) > n_meta:
        embeddings = embeddings[:n_meta]
    
    logger.info(f"Embeddings: {embeddings.shape}")
    
    hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
        embeddings, coarse_res=COARSE_RES, sub_res=SUB_RES, k=K
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_branch = compute_branch_purity(coarse_labels, metadata)
    fine_branch = compute_branch_purity(hierarchical_labels, metadata)
    coarse_area = compute_legal_area_purity(coarse_labels, metadata)
    fine_area = compute_legal_area_purity(hierarchical_labels, metadata)
    nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
    
    zoom_branch = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'branch')
    zoom_area = compute_zoom_coherence_id_space(metadata, coarse_labels, hierarchical_labels, 'legal_area')
    
    fine_unique, fine_counts = np.unique(hierarchical_labels[hierarchical_labels != -1], return_counts=True)
    coarse_unique, coarse_counts = np.unique(coarse_labels[coarse_labels != -1], return_counts=True)
    
    logger.info(f"\nResults:")
    logger.info(f"  Coarse: {n_coarse} clusters, median size {np.median(coarse_counts):.1f}")
    logger.info(f"  Fine: {n_fine} clusters, median size {np.median(fine_counts):.1f}")
    logger.info(f"  Branch purity: {coarse_branch:.4f} -> {fine_branch:.4f} (Δ={fine_branch-coarse_branch:+.4f})")
    logger.info(f"  Area purity: {coarse_area:.4f} -> {fine_area:.4f} (Δ={fine_area-coarse_area:+.4f})")
    logger.info(f"  Strict nesting: {nesting:.4f}")
    logger.info(f"  Zoom branch: imp={zoom_branch['mean_improvement']:.4f}, rate={zoom_branch['improvement_rate']:.2%}")
    logger.info(f"  Zoom area: imp={zoom_area['mean_improvement']:.4f}, rate={zoom_area['improvement_rate']:.2%}")
    logger.info(f"  Singletons: {np.mean(fine_counts == 1):.1%}")
    
    # Check v26 success rule
    branch_mono = fine_branch > coarse_branch
    area_mono = fine_area > coarse_area
    rate_ok = (zoom_branch['improvement_rate'] or 0) > 0.5
    passes = branch_mono and area_mono and rate_ok
    
    logger.info(f"\nv26 Success Rule Checks:")
    logger.info(f"  Branch monotonic: {branch_mono}")
    logger.info(f"  Area monotonic: {area_mono}")
    logger.info(f"  Improvement rate > 0.5: {rate_ok}")
    logger.info(f"  MODE PASSES: {passes}")
    
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)): return obj.item()
        elif isinstance(obj, np.ndarray): return obj.tolist()
        elif isinstance(obj, dict): return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list): return [convert(v) for v in obj]
        return obj
    
    output = {
        "run_id": f"hierarchical_leiden_174k_{MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 27,
        "mode": MODE,
        "config": {"coarse_res": COARSE_RES, "sub_res": SUB_RES, "k": K},
        "coarse_clusters": n_coarse,
        "fine_clusters": n_fine,
        "coarse_branch_purity": coarse_branch,
        "fine_branch_purity": fine_branch,
        "coarse_area_purity": coarse_area,
        "fine_area_purity": fine_area,
        "branch_improvement": fine_branch - coarse_branch,
        "area_improvement": fine_area - coarse_area,
        "strict_nesting": nesting,
        "zoom_branch": zoom_branch,
        "zoom_area": zoom_area,
        "fragmentation": {
            "coarse_median_size": float(np.median(coarse_counts)),
            "fine_median_size": float(np.median(fine_counts)),
            "fine_singleton_fraction": float(np.mean(fine_counts == 1)),
        },
        "v26_checks": {
            "branch_monotonic": branch_mono,
            "area_monotonic": area_mono,
            "improvement_rate_gt_0.5": rate_ok,
            "passes": passes,
        },
    }
    
    output_path = OUTPUT_DIR / f"hierarchical_leiden_174k_{MODE}_sub1.5.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()