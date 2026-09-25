#!/usr/bin/env python3
"""
Test Hierarchical Leiden on 174k TF-IDF modes with 174k-appropriate parameters.

Key insight from v1: at 174k scale, flat Leiden at res=0.25 gives 22 clusters with
one cluster having 83k docs. Sub-clustering at res=2.0 within 83k docs produces
83k sub-clusters (one per doc).

174k-appropriate approach:
- Use coarser first resolution (0.1, 0.15) to get ~8-12 coarse clusters like 1000-scale
- Use larger min_size (e.g., 500) to skip sub-clustering of tiny clusters
- Use sub_res that produces ~10-20 sub-clusters per parent

Also test: citation-role modes have best zoom quality at 1000-scale (ZQ=0.54 for citing_alpha0.3).
The TF-IDF modes may simply not support fine-grained zoom at 174k due to signal sparsity.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path("/home/runner/work/LexMachina/LexMachina")
MODES_DIR = BASE / "results/fractal_map/legal_distance_modes"
EVAL_META = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = BASE / "results/fractal_map/hierarchical_174k_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Test modes (decision-mappable 174k TF-IDF)
TEST_MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",  # Production default
    "regeste_tfidf_174k",  # Regeste only
]

# 174k-appropriate hierarchical configs
HIERARCHICAL_CONFIGS = [
    {"coarse_res": 0.1, "sub_res": 1.5, "min_size": 500, "name": "coarse_0.1_sub_1.5"},
    {"coarse_res": 0.15, "sub_res": 1.5, "min_size": 500, "name": "coarse_0.15_sub_1.5"},
    {"coarse_res": 0.1, "sub_res": 2.0, "min_size": 500, "name": "coarse_0.1_sub_2.0"},
    {"coarse_res": 0.15, "sub_res": 2.0, "min_size": 500, "name": "coarse_0.15_sub_2.0"},
    {"coarse_res": 0.25, "sub_res": 1.0, "min_size": 1000, "name": "coarse_0.25_sub_1.0_large"},
]

K = 15
MIN_CLUSTER_SIZE = 3


def load_metadata():
    with open(EVAL_META) as f:
        meta = json.load(f)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(meta)}
    return id_to_idx, meta


def load_embedding(mode):
    mode_dir = MODES_DIR / mode
    for emb_file in mode_dir.glob("*.npy"):
        if "labels" not in emb_file.name and "metadata" not in emb_file.name:
            return np.load(emb_file)
    legal_tfidf_dir = BASE / "results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings"
    for emb_file in legal_tfidf_dir.glob("*.npy"):
        if mode.replace("_174k", "").replace("_v25", "") in emb_file.name:
            return np.load(emb_file)
    return None


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
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
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership), float(partition.modularity)


def hierarchical_leiden(embeddings, coarse_res=0.5, sub_res=3.0, k=15, min_size=20):
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"    Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    for cid in unique_coarse:
        mask = coarse_labels == cid
        n = mask.sum()
        logger.info(f"      Cluster {cid}: {n} docs")
    
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < min_size:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0, 'size': int(len(indices)), 'too_small': True}
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"      Coarse {coarse_id} ({len(indices)} docs): "
                    f"{len(unique_sub)} sub-clusters, modularity={sub_mod:.4f}")
        
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False}
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info


def compute_purity(labels, metadata, field='branch', min_cluster_size=MIN_CLUSTER_SIZE):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        vals = [metadata[i].get(field) for i in indices]
        vals = [v for v in vals if v and v not in ('null', 'unknown')]
        if vals:
            purities.append(Counter(vals).most_common(1)[0][1] / len(vals))
    return float(np.mean(purities)) if purities else 0


def compute_zoom_coherence_hierarchical(coarse_labels, fine_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    improvements = []
    n_parents = 0
    parent_details = {}
    
    for coarse_id in unique_coarse:
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_cluster_size:
            continue
        coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b not in ('null', 'unknown')]
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        fine_labels_in_coarse = fine_labels[coarse_indices]
        unique_fine = np.unique(fine_labels_in_coarse[fine_labels_in_coarse != -1])
        
        child_purities = []
        for fine_id in unique_fine:
            fine_mask = fine_labels == fine_id
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
                continue
            fine_branches = [metadata[i].get('branch') for i in fine_indices]
            fine_branches = [b for b in fine_branches if b and b not in ('null', 'unknown')]
            if fine_branches:
                child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            n_parents += 1
            parent_details[int(coarse_id)] = {
                'coarse_purity': round(float(coarse_purity), 4),
                'mean_child_purity': round(float(mean_child_purity), 4),
                'improvement': round(float(mean_child_purity - coarse_purity), 4),
                'n_children': len(child_purities),
            }
    
    return {
        'mean_improvement': round(float(np.mean(improvements)), 4) if improvements else None,
        'improvement_rate': round(float(sum(1 for j in improvements if j > 0) / len(improvements)), 4) if improvements else None,
        'n_parents': n_parents,
        'parent_details': parent_details,
    }


def compute_fragmentation(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
    }


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


def test_mode(mode, metadata):
    logger.info(f"\n=== Testing mode: {mode} ===")
    
    embedding = load_embedding(mode)
    if embedding is None:
        logger.error(f"  Could not load embedding for {mode}")
        return None
    
    logger.info(f"  Embedding shape: {embedding.shape}")
    if embedding.shape[0] > len(metadata):
        embedding = embedding[:len(metadata)]
    elif embedding.shape[0] < len(metadata):
        logger.error(f"  Embedding smaller than metadata")
        return None
    
    branches = {m['branch'] for m in metadata if m.get('branch') and m['branch'] not in ('null', 'unknown')}
    areas = {m['legal_area'] for m in metadata if m.get('legal_area') and m['legal_area'] not in ('null', 'unknown')}
    logger.info(f"  Baseline: branch={1/len(branches):.4f} ({len(branches)} classes), area={1/len(areas):.4f} ({len(areas)} classes)")
    
    results = {'mode': mode, 'embedding_shape': list(embedding.shape), 'configs': {}}
    
    for config in HIERARCHICAL_CONFIGS:
        logger.info(f"\n  Config: {config['name']}")
        
        hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
            embedding, coarse_res=config['coarse_res'], sub_res=config['sub_res'],
            k=K, min_size=config['min_size'])
        
        coarse_branch_pur = compute_purity(coarse_labels, metadata, 'branch')
        coarse_area_pur = compute_purity(coarse_labels, metadata, 'legal_area')
        fine_branch_pur = compute_purity(hierarchical_labels, metadata, 'branch')
        fine_area_pur = compute_purity(hierarchical_labels, metadata, 'legal_area')
        zoom = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
        frag_coarse = compute_fragmentation(coarse_labels)
        frag_fine = compute_fragmentation(hierarchical_labels)
        
        nesting = 1.0
        n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse = len(set(coarse_labels[coarse_labels != -1]))
        
        logger.info(f"    Coarse: {n_coarse} clusters, branch_pur={coarse_branch_pur:.4f}, area_pur={coarse_area_pur:.4f}")
        logger.info(f"    Fine: {n_fine} clusters, branch_pur={fine_branch_pur:.4f}, area_pur={fine_area_pur:.4f}")
        logger.info(f"    Zoom: mean_improvement={zoom['mean_improvement']}, rate={zoom['improvement_rate']}, n_parents={zoom['n_parents']}")
        logger.info(f"    Frag coarse: median={frag_coarse['median_size']}, singleton={frag_coarse['singleton_fraction']}")
        logger.info(f"    Frag fine: median={frag_fine['median_size']}, singleton={frag_fine['singleton_fraction']}")
        
        results['configs'][config['name']] = {
            'config': config,
            'n_coarse_clusters': n_coarse,
            'n_fine_clusters': n_fine,
            'coarse_branch_purity': coarse_branch_pur,
            'fine_branch_purity': fine_branch_pur,
            'coarse_area_purity': coarse_area_pur,
            'fine_area_purity': fine_area_pur,
            'zoom_coherence': zoom,
            'fragmentation_coarse': frag_coarse,
            'fragmentation_fine': frag_fine,
            'nesting': nesting,
        }
    
    # Flat Leiden comparison at same coarse resolutions
    logger.info(f"\n  Flat Leiden comparison:")
    flat_results = {}
    for res in [0.1, 0.15, 0.25, 0.5, 1.0]:
        labels, mod = leiden_clustering(embedding, resolution=res, k=K)
        n_clusters = len(set(labels[labels != -1]))
        branch_pur = compute_purity(labels, metadata, 'branch')
        area_pur = compute_purity(labels, metadata, 'legal_area')
        frag = compute_fragmentation(labels)
        flat_results[f"res_{res}"] = {
            'n_clusters': n_clusters, 'branch_purity': branch_pur, 'area_purity': area_pur,
            'fragmentation': frag, 'modularity': float(mod)}
        logger.info(f"    res={res}: clusters={n_clusters}, branch={branch_pur:.4f}, area={area_pur:.4f}, median={frag['median_size']}, single={frag['singleton_fraction']}")
    
    results['flat_leiden'] = flat_results
    return results


def main():
    logger.info("=" * 70)
    logger.info("HIERARCHICAL LEIDEN TEST ON 174k TF-IDF MODES (v2 - 174k params)")
    logger.info("=" * 70)
    
    id_to_idx, metadata = load_metadata()
    logger.info(f"Metadata: {len(metadata)} entries")
    
    all_results = {
        'run_id': f'hierarchical_leiden_174k_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 27,
        'hypothesis': 'Hierarchical Leiden with 174k-appropriate parameters (coarser first level, larger min_size) can achieve meaningful zoom refinement without over-fragmentation',
        'frozen_sample': f"{len(metadata)} decisions (ACCEPTED evaluation metadata)",
        'frozen_metric': 'Branch/area purity, zoom coherence (improvement rate), fragmentation (median cluster size), nesting',
        'success_rule': 'Fine branch purity > coarse branch purity AND improvement_rate > 0.5 AND fine median cluster size > 5 AND nesting = 1.0',
        'modes_tested': TEST_MODES,
        'results': {}
    }
    
    for mode in TEST_MODES:
        result = test_mode(mode, metadata)
        if result:
            all_results['results'][mode] = result
            output_path = OUTPUT_DIR / f"hierarchical_leiden_174k_{mode}_v2.json"
            with open(output_path, 'w') as f:
                json.dump(convert(result), f, indent=2)
            logger.info(f"  Saved: {output_path}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    
    for mode, result in all_results['results'].items():
        logger.info(f"\n{mode}:")
        best_config = None
        best_score = -1
        
        for config_name, cr in result['configs'].items():
            ir = cr['zoom_coherence']['improvement_rate'] or 0
            median_fine = cr['fragmentation_fine']['median_size'] or 0
            # Score: improvement_rate * log(median_size) - penalizes over-fragmentation
            score = ir * np.log(max(1, median_fine))
            if score > best_score:
                best_score = score
                best_config = config_name
        
        if best_config:
            cr = result['configs'][best_config]
            logger.info(f"  Best config: {best_config} (score={best_score:.3f})")
            logger.info(f"    Coarse: {cr['n_coarse_clusters']} clusters, branch_pur={cr['coarse_branch_purity']:.4f}")
            logger.info(f"    Fine: {cr['n_fine_clusters']} clusters, branch_pur={cr['fine_branch_purity']:.4f}")
            logger.info(f"    Improvement rate: {cr['zoom_coherence']['improvement_rate']}")
            logger.info(f"    Fine median size: {cr['fragmentation_fine']['median_size']}")
            logger.info(f"    Nesting: {cr['nesting']:.4f}")
            
            success = (cr['fine_branch_purity'] > cr['coarse_branch_purity'] and
                      (cr['zoom_coherence']['improvement_rate'] or 0) > 0.5 and
                      (cr['fragmentation_fine']['median_size'] or 0) > 5 and
                      cr['nesting'] == 1.0)
            logger.info(f"    SUCCESS: {success}")
            
            # Compare with best flat Leiden at similar scale
            for res_key, flat in result['flat_leiden'].items():
                if flat['n_clusters'] <= cr['n_fine_clusters'] * 1.5 and flat['n_clusters'] >= cr['n_fine_clusters'] * 0.5:
                    logger.info(f"    Comparable flat {res_key}: branch={flat['branch_purity']:.4f}, clusters={flat['n_clusters']}, median={flat['fragmentation']['median_size']}")
    
    output_path = OUTPUT_DIR / "hierarchical_leiden_174k_v2_all_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(all_results), f, indent=2)
    logger.info(f"\nAll results saved to {output_path}")


if __name__ == "__main__":
    main()