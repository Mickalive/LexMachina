#!/usr/bin/env python3
"""
Test Hierarchical Leiden on 174k TF-IDF modes to fix over-fragmentation.

At 1000-scale, hierarchical Leiden achieved:
- Perfect nesting (1.0) by construction
- Branch purity 0.949 (vs flat Leiden 0.912)
- 8 coarse clusters → 98 fine clusters

At 174k scale, flat Leiden with compressed ladder [0.25, 0.5, 1.0, 2.0, 3.0] produces:
- res_2.0: 12,902 clusters (median size 1) - OVER-FRAGMENTED
- res_3.0: 64,131 clusters (median size 1) - OVER-FRAGMENTED

Hypothesis: Hierarchical Leiden (coarse global → fine within parents) will produce
meaningful zoom refinement without over-fragmentation because fine clusters are
constrained within coarse parent clusters.

Test modes (decision-mappable 174k TF-IDF):
1. cited_decisions_tfidf_outcome_hybrid_0.5_174k (production default)
2. regeste_tfidf_174k (regeste only)
3. cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25
4. cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25
"""

import json
import argparse
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
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

# Test modes from census
TEST_MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k",
    "regeste_tfidf_174k",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25",
    "cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25",
]

# Hierarchical Leiden configs to test
HIERARCHICAL_CONFIGS = [
    {"coarse_res": 0.25, "sub_res": 2.0, "name": "coarse_0.25_sub_2.0"},
    {"coarse_res": 0.25, "sub_res": 3.0, "name": "coarse_0.25_sub_3.0"},
    {"coarse_res": 0.5, "sub_res": 2.0, "name": "coarse_0.5_sub_2.0"},
    {"coarse_res": 0.5, "sub_res": 3.0, "name": "coarse_0.5_sub_3.0"},  # Best at 1000-scale
    {"coarse_res": 1.0, "sub_res": 3.0, "name": "coarse_1.0_sub_3.0"},
]

MIN_CLUSTER_SIZE = 3
K = 15


def load_metadata():
    """Load ACCEPTED evaluation metadata."""
    with open(EVAL_META) as f:
        meta = json.load(f)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(meta)}
    return id_to_idx, meta


def load_embedding(mode):
    """Load embedding for a mode."""
    mode_dir = MODES_DIR / mode
    # Find the embedding file
    for emb_file in mode_dir.glob("*.npy"):
        if "embedding" in emb_file.name.lower() or "tfidf" in emb_file.name.lower() or "hybrid" in emb_file.name.lower():
            if "labels" not in emb_file.name and "metadata" not in emb_file.name:
                return np.load(emb_file)
    # Fallback: check hierarchical_map_174k
    legal_tfidf_dir = BASE / "results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings"
    for emb_file in legal_tfidf_dir.glob("*.npy"):
        if mode.replace("_174k", "").replace("_v25", "") in emb_file.name:
            return np.load(emb_file)
    return None


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering."""
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
    """
    Run hierarchical Leiden:
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at sub_res within the subset
    3. Assign global labels
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"    Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < min_size:
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
        
        logger.info(f"      Coarse {coarse_id} ({len(indices)} docs): "
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


def compute_branch_purity(labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute mean branch purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        branches = [metadata[i].get('branch') for i in indices]
        branches = [b for b in branches if b and b != 'null' and b != 'unknown']
        if branches:
            most_common = Counter(branches).most_common(1)[0][1]
            purities.append(most_common / len(branches))
    
    return float(np.mean(purities)) if purities else 0


def compute_area_purity(labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute mean legal_area purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        areas = [metadata[i].get('legal_area') for i in indices]
        areas = [a for a in areas if a and a != 'null' and a != 'unknown']
        if areas:
            most_common = Counter(areas).most_common(1)[0][1]
            purities.append(most_common / len(areas))
    
    return float(np.mean(purities)) if purities else 0


def compute_zoom_coherence_hierarchical(coarse_labels, fine_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute zoom coherence for hierarchical clustering."""
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
        coarse_branches = [b for b in coarse_branches if b and b != 'null' and b != 'unknown']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        # Fine clusters that are children of this coarse cluster
        fine_labels_in_coarse = fine_labels[coarse_indices]
        unique_fine = np.unique(fine_labels_in_coarse[fine_labels_in_coarse != -1])
        
        child_purities = []
        for fine_id in unique_fine:
            fine_mask = fine_labels == fine_id
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
                continue
            fine_branches = [metadata[i].get('branch') for i in fine_indices]
            fine_branches = [b for b in fine_branches if b and b != 'null' and b != 'unknown']
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
    """Compute fragmentation metrics."""
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


def test_mode(mode, metadata, id_to_idx):
    """Test hierarchical Leiden on a single mode."""
    logger.info(f"\n=== Testing mode: {mode} ===")
    
    embedding = load_embedding(mode)
    if embedding is None:
        logger.error(f"  Could not load embedding for {mode}")
        return None
    
    logger.info(f"  Embedding shape: {embedding.shape}")
    
    # Slice to match metadata (173,963 entries)
    if embedding.shape[0] > len(metadata):
        embedding = embedding[:len(metadata)]
    elif embedding.shape[0] < len(metadata):
        logger.error(f"  Embedding smaller than metadata: {embedding.shape[0]} < {len(metadata)}")
        return None
    
    # Baseline random purities
    branches = {m['branch'] for m in metadata if m.get('branch') and m['branch'] not in ('null', 'unknown')}
    areas = {m['legal_area'] for m in metadata if m.get('legal_area') and m['legal_area'] not in ('null', 'unknown')}
    baseline_branch = 1 / len(branches)
    baseline_area = 1 / len(areas)
    logger.info(f"  Baseline: branch={baseline_branch:.4f} ({len(branches)} classes), area={baseline_area:.4f} ({len(areas)} classes)")
    
    results = {
        'mode': mode,
        'embedding_shape': list(embedding.shape),
        'baseline': {'branch': baseline_branch, 'area': baseline_area},
        'configs': {}
    }
    
    for config in HIERARCHICAL_CONFIGS:
        logger.info(f"\n  Config: {config['name']}")
        
        hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
            embedding, 
            coarse_res=config['coarse_res'], 
            sub_res=config['sub_res'],
            k=K
        )
        
        # Metrics
        coarse_branch_purity = compute_branch_purity(coarse_labels, metadata)
        coarse_area_purity = compute_area_purity(coarse_labels, metadata)
        hier_branch_purity = compute_branch_purity(hierarchical_labels, metadata)
        hier_area_purity = compute_area_purity(hierarchical_labels, metadata)
        zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
        frag_coarse = compute_fragmentation(coarse_labels)
        frag_fine = compute_fragmentation(hierarchical_labels)
        
        # Nesting (should be 1.0 by construction)
        nesting = 1.0
        n_fine_clusters = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse_clusters = len(set(coarse_labels[coarse_labels != -1]))
        
        logger.info(f"    Coarse clusters: {n_coarse_clusters}, Fine clusters: {n_fine_clusters}")
        logger.info(f"    Coarse branch purity: {coarse_branch_purity:.4f}, Fine branch purity: {hier_branch_purity:.4f}")
        logger.info(f"    Coarse area purity: {coarse_area_purity:.4f}, Fine area purity: {hier_area_purity:.4f}")
        logger.info(f"    Zoom: mean_improvement={zoom_coherence['mean_improvement']}, improvement_rate={zoom_coherence['improvement_rate']}, n_parents={zoom_coherence['n_parents']}")
        logger.info(f"    Fragmentation coarse: median={frag_coarse['median_size']}, singleton={frag_coarse['singleton_fraction']}")
        logger.info(f"    Fragmentation fine: median={frag_fine['median_size']}, singleton={frag_fine['singleton_fraction']}")
        logger.info(f"    Nesting: {nesting:.4f}")
        
        config_result = {
            'config': config,
            'n_coarse_clusters': n_coarse_clusters,
            'n_fine_clusters': n_fine_clusters,
            'coarse_branch_purity': coarse_branch_purity,
            'fine_branch_purity': hier_branch_purity,
            'coarse_area_purity': coarse_area_purity,
            'fine_area_purity': hier_area_purity,
            'zoom_coherence': zoom_coherence,
            'fragmentation_coarse': frag_coarse,
            'fragmentation_fine': frag_fine,
            'nesting': nesting,
            'cluster_info': cluster_info,
        }
        results['configs'][config['name']] = config_result
    
    # Also run flat Leiden for comparison at same coarse resolution
    logger.info(f"\n  Flat Leiden comparison:")
    flat_results = {}
    for res in [0.25, 0.5, 1.0, 2.0, 3.0]:
        labels, mod = leiden_clustering(embedding, resolution=res, k=K)
        n_clusters = len(set(labels[labels != -1]))
        branch_pur = compute_branch_purity(labels, metadata)
        area_pur = compute_area_purity(labels, metadata)
        frag = compute_fragmentation(labels)
        flat_results[f"res_{res}"] = {
            'n_clusters': n_clusters,
            'branch_purity': branch_pur,
            'area_purity': area_pur,
            'fragmentation': frag,
            'modularity': float(mod),
        }
        logger.info(f"    res={res}: clusters={n_clusters}, branch_pur={branch_pur:.4f}, area_pur={area_pur:.4f}, median={frag['median_size']}, singleton={frag['singleton_fraction']}")
    
    results['flat_leiden'] = flat_results
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Test hierarchical Leiden on 174k TF-IDF modes')
    parser.add_argument('--mode', type=str, default=None, help='Specific mode to test (default: all)')
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("HIERARCHICAL LEIDEN TEST ON 174k TF-IDF MODES")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Direction version: 27")
    
    # Load metadata
    logger.info("\nLoading ACCEPTED evaluation metadata...")
    id_to_idx, metadata = load_metadata()
    logger.info(f"  Metadata entries: {len(metadata)}")
    
    modes_to_test = [args.mode] if args.mode else TEST_MODES
    
    all_results = {
        'run_id': f'hierarchical_leiden_174k_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 27,
        'hypothesis': 'Hierarchical Leiden (coarse global -> fine within parents) fixes over-fragmentation of flat Leiden at 174k scale, providing meaningful zoom refinement with perfect nesting',
        'frozen_sample': f"{len(metadata)} decisions (ACCEPTED evaluation metadata)",
        'frozen_metric': 'Branch purity, area purity, zoom coherence (improvement rate), fragmentation (median cluster size), nesting',
        'success_rule': 'Fine branch purity > coarse branch purity AND improvement_rate > 0.5 AND fine median cluster size > 1 AND nesting = 1.0',
        'modes_tested': modes_to_test,
        'configs_tested': [c['name'] for c in HIERARCHICAL_CONFIGS],
        'results': {}
    }
    
    for mode in modes_to_test:
        result = test_mode(mode, metadata, id_to_idx)
        if result:
            all_results['results'][mode] = result
            
            # Save intermediate
            output_path = OUTPUT_DIR / f"hierarchical_leiden_174k_{mode}.json"
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
        best_improvement = -1
        
        for config_name, config_result in result['configs'].items():
            ir = config_result['zoom_coherence']['improvement_rate'] or 0
            if ir > best_improvement:
                best_improvement = ir
                best_config = config_name
        
        if best_config:
            cr = result['configs'][best_config]
            logger.info(f"  Best config: {best_config}")
            logger.info(f"    Coarse branch purity: {cr['coarse_branch_purity']:.4f}")
            logger.info(f"    Fine branch purity: {cr['fine_branch_purity']:.4f}")
            logger.info(f"    Improvement rate: {cr['zoom_coherence']['improvement_rate']}")
            logger.info(f"    Fine median cluster size: {cr['fragmentation_fine']['median_size']}")
            logger.info(f"    Nesting: {cr['nesting']:.4f}")
            
            # Check success
            success = (cr['fine_branch_purity'] > cr['coarse_branch_purity'] and
                      (cr['zoom_coherence']['improvement_rate'] or 0) > 0.5 and
                      (cr['fragmentation_fine']['median_size'] or 0) > 1 and
                      cr['nesting'] == 1.0)
            logger.info(f"    SUCCESS: {success}")
            
            # Compare with flat Leiden at similar coarse resolution
            coarse_res = result['configs'][best_config]['config']['coarse_res']
            flat_key = f"res_{coarse_res}"
            if flat_key in result['flat_leiden']:
                flat = result['flat_leiden'][flat_key]
                logger.info(f"    Flat Leiden {flat_key}: branch_pur={flat['branch_purity']:.4f}, clusters={flat['n_clusters']}, median={flat['fragmentation']['median_size']}")
    
    # Save all results
    output_path = OUTPUT_DIR / "hierarchical_leiden_174k_all_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(all_results), f, indent=2)
    logger.info(f"\nAll results saved to {output_path}")


if __name__ == "__main__":
    main()