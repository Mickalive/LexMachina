#!/usr/bin/env python3
"""
Quick focused test on regeste_tfidf - the only TF-IDF mode that passed hierarchical_v1 at 83k.
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

EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_v1_regeste")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODE = "regeste_tfidf"
SAMPLE_SIZE = 20000
K = 15
MIN_CLUSTER_SIZE = 20
MAX_SUBCLUSTERS = 20

# Best configs from adaptive test
TEST_CONFIGS = [
    {"name": "adaptive_base2.0_max20", "coarse_res": 0.5, "base_sub_res": 2.0, "min_cluster_size": 20, "max_subclusters": 20, "adaptive": True},
    {"name": "adaptive_base1.5_max20", "coarse_res": 0.5, "base_sub_res": 1.5, "min_cluster_size": 20, "max_subclusters": 20, "adaptive": True},
    {"name": "adaptive_base3.0_max20", "coarse_res": 0.5, "base_sub_res": 3.0, "min_cluster_size": 20, "max_subclusters": 20, "adaptive": True},
    {"name": "adaptive_base2.0_max30", "coarse_res": 0.5, "base_sub_res": 2.0, "min_cluster_size": 20, "max_subclusters": 30, "adaptive": True},
    {"name": "adaptive_base2.0_min10", "coarse_res": 0.5, "base_sub_res": 2.0, "min_cluster_size": 10, "max_subclusters": 20, "adaptive": True},
    {"name": "adaptive_base2.0_min50", "coarse_res": 0.5, "base_sub_res": 2.0, "min_cluster_size": 50, "max_subclusters": 20, "adaptive": True},
    {"name": "coarse0.25_adaptive", "coarse_res": 0.25, "base_sub_res": 2.0, "min_cluster_size": 20, "max_subclusters": 20, "adaptive": True},
    {"name": "coarse1.0_adaptive", "coarse_res": 1.0, "base_sub_res": 2.0, "min_cluster_size": 20, "max_subclusters": 20, "adaptive": True},
]


def load_metadata():
    with open(METADATA_PATH) as f:
        return json.load(f)


def load_embeddings(mode):
    emb_path = EMBEDDINGS_DIR / f"{mode}.npy"
    if not emb_path.exists():
        return None
    return np.load(emb_path)


def stratified_sample(metadata, embeddings, sample_size, seed=42):
    np.random.seed(seed)
    branch_to_indices = defaultdict(list)
    for i, m in enumerate(metadata):
        branch = m.get('branch')
        if branch and branch not in ('unknown', 'null', None):
            branch_to_indices[branch].append(i)
    
    total = sum(len(v) for v in branch_to_indices.values())
    selected = []
    for branch, indices in branch_to_indices.items():
        n_branch = int(sample_size * len(indices) / total)
        if n_branch > 0 and n_branch < len(indices):
            selected.extend(np.random.choice(indices, n_branch, replace=False))
        elif n_branch >= len(indices):
            selected.extend(indices)
    
    if len(selected) < sample_size:
        remaining = [i for i in range(len(metadata)) if i not in selected]
        np.random.shuffle(remaining)
        selected.extend(remaining[:sample_size - len(selected)])
    
    selected = np.array(sorted(selected[:sample_size]))
    return embeddings[selected], [metadata[i] for i in selected]


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


def hierarchical_leiden_adaptive(embeddings, metadata, coarse_res=0.5, base_sub_res=2.0,
                                  min_cluster_size=20, max_subclusters=20, adaptive=True, k=15, seed=42):
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k, seed=seed)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_cluster_size:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {'coarse_id': int(coarse_id), 'sub_id': 0, 'size': int(cluster_size), 'too_small': True}
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        if adaptive:
            if cluster_size < 500:
                sub_res = base_sub_res * 1.5
            elif cluster_size < 2000:
                sub_res = base_sub_res
            else:
                sub_res = base_sub_res * 0.5
            sub_res = max(0.5, min(5.0, sub_res))
        else:
            sub_res = base_sub_res
        
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k, seed=seed)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        sub_label_to_indices = {sid: indices[sub_labels == sid] for sid in unique_sub}
        valid_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) >= min_cluster_size]
        tiny_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) < min_cluster_size]
        
        if tiny_sub_labels and valid_sub_labels:
            valid_centroids = {sid: np.mean(subset_embeddings[sub_labels == sid], axis=0) for sid in valid_sub_labels}
            for tiny_sid in tiny_sub_labels:
                tiny_centroid = np.mean(subset_embeddings[sub_labels == tiny_sid], axis=0)
                best_sid = min(valid_sub_labels, key=lambda sid: np.linalg.norm(tiny_centroid - valid_centroids[sid]))
                sub_labels[sub_labels == tiny_sid] = best_sid
            unique_sub = valid_sub_labels
        
        if len(unique_sub) > max_subclusters:
            sub_sizes = [(sid, (sub_labels == sid).sum()) for sid in unique_sub]
            sub_sizes.sort(key=lambda x: x[1], reverse=True)
            unique_sub = [sid for sid, _ in sub_sizes[:max_subclusters]]
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): {len(unique_sub)} sub-clusters (sub_res={sub_res:.2f})")
        
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {'coarse_id': int(coarse_id), 'sub_id': int(sub_id), 'size': int(len(global_indices)), 'too_small': False, 'sub_res_used': sub_res}
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


def compute_branch_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b not in ('unknown', 'null')]
        if cluster_branches:
            purities.append(Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches))
    return float(np.mean(purities)) if purities else 0


def compute_legal_area_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a not in ('unknown', 'null')]
        if cluster_areas:
            purities.append(Counter(cluster_areas).most_common(1)[0][1] / len(cluster_areas))
    return float(np.mean(purities)) if purities else 0


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


def compute_zoom_coherence(metadata, coarse_labels, fine_labels, field='branch'):
    id_pairs = {}
    for i, m in enumerate(metadata):
        id_pairs[m['decision_id']] = (coarse_labels[i], fine_labels[i])
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
    for did, (cc, fc) in id_pairs.items():
        coarse_members[cc].append(did)
    fine_coarse_counter = defaultdict(Counter)
    for did, (cc, fc) in id_pairs.items():
        fine_coarse_counter[fc][cc] += 1
    child_to_parent = {fc: cc.most_common(1)[0][0] for fc, cc in fine_coarse_counter.items() if cc}
    improvements = []
    for pc, cmems in coarse_members.items():
        if len(cmems) < MIN_CLUSTER_SIZE:
            continue
        cvals = coarse_vals.get(pc, [])
        if not cvals:
            continue
        child_clusters = [fc for fc, p in child_to_parent.items() if p == pc and len(fine_vals.get(fc, [])) >= MIN_CLUSTER_SIZE]
        if not child_clusters:
            continue
        child_purities = [Counter(fine_vals[fc]).most_common(1)[0][1] / len(fine_vals[fc]) for fc in child_clusters]
        coarse_purity = Counter(cvals).most_common(1)[0][1] / len(cvals)
        improvements.append(float(np.mean(child_purities)) - coarse_purity)
    if improvements:
        return {'mean_improvement': float(np.mean(improvements)), 'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)), 'n_parents': len(improvements)}
    return {'mean_improvement': None, 'improvement_rate': None, 'n_parents': 0}


def compute_fragmentation(labels):
    unique, counts = np.unique(labels[labels != -1], return_counts=True)
    return {'n_clusters': int(len(unique)), 'median_size': float(np.median(counts)), 'singleton_fraction': float(np.mean(counts == 1))}


def main():
    logger.info(f"=== Focused test: {MODE} on {SAMPLE_SIZE} sample ===")
    metadata = load_metadata()
    embeddings = load_embeddings(MODE)
    if embeddings is None:
        logger.error("Embeddings not found")
        return
    
    sample_embeddings, sample_metadata = stratified_sample(metadata, embeddings, SAMPLE_SIZE)
    logger.info(f"Sampled {len(sample_embeddings)} decisions")
    
    for config in TEST_CONFIGS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Config: {config['name']}")
        
        hierarchical_labels, coarse_labels, _, _ = hierarchical_leiden_adaptive(
            sample_embeddings, sample_metadata, **{k:v for k,v in config.items() if k!='name'}, k=K)
        
        n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse = len(set(coarse_labels[coarse_labels != -1]))
        
        coarse_branch = compute_branch_purity(coarse_labels, sample_metadata)
        fine_branch = compute_branch_purity(hierarchical_labels, sample_metadata)
        coarse_area = compute_legal_area_purity(coarse_labels, sample_metadata)
        fine_area = compute_legal_area_purity(hierarchical_labels, sample_metadata)
        nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
        zoom_branch = compute_zoom_coherence(sample_metadata, coarse_labels, hierarchical_labels, 'branch')
        zoom_area = compute_zoom_coherence(sample_metadata, coarse_labels, hierarchical_labels, 'legal_area')
        frag = compute_fragmentation(hierarchical_labels)
        
        h1_pass = (nesting >= 0.99 and fine_branch > 0.5 and 
                   zoom_branch['improvement_rate'] and zoom_branch['improvement_rate'] > 0.5 and
                   frag['singleton_fraction'] < 0.01)
        
        logger.info(f"  Coarse->Fine: {n_coarse} -> {n_fine}")
        logger.info(f"  Branch: {coarse_branch:.4f} -> {fine_branch:.4f} (Δ={fine_branch-coarse_branch:+.4f})")
        logger.info(f"  Area: {coarse_area:.4f} -> {fine_area:.4f} (Δ={fine_area-coarse_area:+.4f})")
        logger.info(f"  Nesting: {nesting:.4f}")
        logger.info(f"  Zoom branch: rate={zoom_branch['improvement_rate']:.4f}, mean={zoom_branch['mean_improvement']:.4f}")
        logger.info(f"  Fragmentation: median={frag['median_size']:.1f}, singletons={frag['singleton_fraction']:.1%}")
        logger.info(f"  HIERARCHICAL_V1 PASS: {h1_pass}")
        
        if h1_pass:
            logger.info(f"  *** PASS *** fine_branch_purity={fine_branch:.4f} > 0.5!")


if __name__ == "__main__":
    main()