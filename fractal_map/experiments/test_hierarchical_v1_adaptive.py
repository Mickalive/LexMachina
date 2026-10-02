#!/usr/bin/env python3
"""
Test hierarchical_v1 protocol with ADAPTIVE sub-resolution on TF-IDF embeddings.

The key insight from previous runs: fixed fine_res causes over-fragmentation on large clusters.
Adaptive sub-resolution: lower resolution for larger clusters to prevent over-fragmentation.
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
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_v1_adaptive")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODES = [
    "cited_decisions_tfidf_outcome_hybrid_0.5",
    "cited_decisions_tfidf_outcome_hybrid_0.7",
    "cited_decisions_tfidf",
    "regeste_tfidf",
    "regeste_full_text_hybrid_0.5",
    "regeste_full_text_hybrid_0.7",
    "full_text_tfidf_light",
    "outcome_tfidf",
]

SAMPLE_SIZE = 20000
K = 15
MIN_CLUSTER_SIZE = 20
MAX_SUBCLUSTERS_PER_PARENT = 20

# Test configs with adaptive sub-resolution
TEST_CONFIGS = [
    {
        "name": "adaptive_base2.0_max20",
        "coarse_res": 0.5,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters": 20,
        "adaptive": True,
    },
    {
        "name": "adaptive_base1.5_max20",
        "coarse_res": 0.5,
        "base_sub_res": 1.5,
        "min_cluster_size": 20,
        "max_subclusters": 20,
        "adaptive": True,
    },
    {
        "name": "adaptive_base3.0_max20",
        "coarse_res": 0.5,
        "base_sub_res": 3.0,
        "min_cluster_size": 20,
        "max_subclusters": 20,
        "adaptive": True,
    },
    {
        "name": "adaptive_base2.0_max30",
        "coarse_res": 0.5,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters": 30,
        "adaptive": True,
    },
    {
        "name": "adaptive_base2.0_min10_max20",
        "coarse_res": 0.5,
        "base_sub_res": 2.0,
        "min_cluster_size": 10,
        "max_subclusters": 20,
        "adaptive": True,
    },
    {
        "name": "adaptive_base2.0_min50_max20",
        "coarse_res": 0.5,
        "base_sub_res": 2.0,
        "min_cluster_size": 50,
        "max_subclusters": 20,
        "adaptive": True,
    },
    {
        "name": "coarse0.25_adaptive_base2.0",
        "coarse_res": 0.25,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters": 20,
        "adaptive": True,
    },
    {
        "name": "coarse1.0_adaptive_base2.0",
        "coarse_res": 1.0,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters": 20,
        "adaptive": True,
    },
    # Fixed resolution baselines for comparison
    {
        "name": "fixed_res1.5_min20",
        "coarse_res": 0.5,
        "base_sub_res": 1.5,
        "min_cluster_size": 20,
        "max_subclusters": 20,
        "adaptive": False,
    },
    {
        "name": "fixed_res2.0_min20",
        "coarse_res": 0.5,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters": 20,
        "adaptive": False,
    },
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
    
    total_with_branch = sum(len(v) for v in branch_to_indices.values())
    selected = []
    for branch, indices in branch_to_indices.items():
        n_branch = int(sample_size * len(indices) / total_with_branch)
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
    """
    Hierarchical Leiden with adaptive sub-resolution:
    - Larger clusters get LOWER resolution (fewer sub-clusters)
    - Smaller clusters get HIGHER resolution (more sub-clusters)
    - Enforces max_subclusters_per_parent
    """
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
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0,
                'size': int(cluster_size), 'too_small': True,
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Adaptive sub-resolution
        if adaptive:
            # Target ~10-20 sub-clusters per coarse cluster
            # Scale: <500 docs -> higher res, >2000 docs -> lower res
            if cluster_size < 500:
                sub_res = base_sub_res * 1.5
            elif cluster_size < 2000:
                sub_res = base_sub_res
            else:
                sub_res = base_sub_res * 0.5  # Lower resolution for large clusters
            sub_res = max(0.5, min(5.0, sub_res))
        else:
            sub_res = base_sub_res
        
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k, seed=seed)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        # Post-process: merge tiny clusters
        sub_label_to_indices = {sid: indices[sub_labels == sid] for sid in unique_sub}
        valid_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) >= min_cluster_size]
        tiny_sub_labels = [sid for sid, idxs in sub_label_to_indices.items() if len(idxs) < min_cluster_size]
        
        if tiny_sub_labels and valid_sub_labels:
            valid_centroids = {sid: np.mean(subset_embeddings[sub_labels == sid], axis=0) 
                              for sid in valid_sub_labels}
            for tiny_sid in tiny_sub_labels:
                tiny_centroid = np.mean(subset_embeddings[sub_labels == tiny_sid], axis=0)
                best_sid = min(valid_sub_labels, 
                               key=lambda sid: np.linalg.norm(tiny_centroid - valid_centroids[sid]))
                sub_labels[sub_labels == tiny_sid] = best_sid
            unique_sub = valid_sub_labels
        
        # Enforce max_subclusters by keeping largest
        if len(unique_sub) > max_subclusters:
            sub_sizes = [(sid, (sub_labels == sid).sum()) for sid in unique_sub]
            sub_sizes.sort(key=lambda x: x[1], reverse=True)
            unique_sub = [sid for sid, _ in sub_sizes[:max_subclusters]]
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): {len(unique_sub)} sub-clusters (sub_res={sub_res:.2f})")
        
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False,
                'sub_res_used': sub_res,
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


def compute_zoom_coherence_id_space(metadata, coarse_labels, fine_labels, field='branch'):
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
        child_clusters = [fc for fc, p in child_to_parent.items()
                          if p == pc and len(fine_vals.get(fc, [])) >= MIN_CLUSTER_SIZE]
        if not child_clusters:
            continue
        child_purities = [Counter(fine_vals[fc]).most_common(1)[0][1] / len(fine_vals[fc]) for fc in child_clusters]
        coarse_purity = Counter(cvals).most_common(1)[0][1] / len(cvals)
        improvements.append(float(np.mean(child_purities)) - coarse_purity)
    
    if improvements:
        return {
            'mean_improvement': float(np.mean(improvements)),
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)),
            'n_parents': len(improvements),
        }
    return {'mean_improvement': None, 'improvement_rate': None, 'n_parents': 0}


def compute_fragmentation(labels):
    unique, counts = np.unique(labels[labels != -1], return_counts=True)
    return {
        'n_clusters': int(len(unique)),
        'median_size': float(np.median(counts)),
        'mean_size': float(np.mean(counts)),
        'singleton_fraction': float(np.mean(counts == 1)),
    }


def main():
    logger.info("=== Hierarchical_v1 Adaptive Test on SAMPLED TF-IDF Embeddings ===")
    logger.info(f"Sample size: {SAMPLE_SIZE}")
    
    metadata = load_metadata()
    logger.info(f"Full metadata: {len(metadata)} entries")
    
    all_results = {}
    
    for mode in MODES:
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing mode: {mode}")
        logger.info(f"{'='*70}")
        
        embeddings = load_embeddings(mode)
        if embeddings is None:
            continue
        
        sample_embeddings, sample_metadata = stratified_sample(metadata, embeddings, SAMPLE_SIZE)
        logger.info(f"  Sampled {len(sample_embeddings)} decisions")
        
        mode_results = {}
        
        for config in TEST_CONFIGS:
            logger.info(f"\n  Config: {config['name']} (adaptive={config['adaptive']})")
            
            hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden_adaptive(
                sample_embeddings, sample_metadata,
                coarse_res=config['coarse_res'],
                base_sub_res=config['base_sub_res'],
                min_cluster_size=config['min_cluster_size'],
                max_subclusters=config['max_subclusters'],
                adaptive=config['adaptive'],
                k=K
            )
            
            n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
            n_coarse = len(set(coarse_labels[coarse_labels != -1]))
            
            coarse_branch_purity = compute_branch_purity(coarse_labels, sample_metadata)
            fine_branch_purity = compute_branch_purity(hierarchical_labels, sample_metadata)
            coarse_area_purity = compute_legal_area_purity(coarse_labels, sample_metadata)
            fine_area_purity = compute_legal_area_purity(hierarchical_labels, sample_metadata)
            nesting = compute_strict_nesting(hierarchical_labels, coarse_labels)
            
            zoom_branch = compute_zoom_coherence_id_space(sample_metadata, coarse_labels, hierarchical_labels, 'branch')
            zoom_area = compute_zoom_coherence_id_space(sample_metadata, coarse_labels, hierarchical_labels, 'legal_area')
            
            frag_hierarchical = compute_fragmentation(hierarchical_labels)
            
            hierarchical_v1_pass = (
                nesting >= 0.99 and
                fine_branch_purity > 0.5 and
                zoom_branch['improvement_rate'] is not None and zoom_branch['improvement_rate'] > 0.5 and
                frag_hierarchical['singleton_fraction'] < 0.01
            )
            
            logger.info(f"    Coarse->Fine: {n_coarse} -> {n_fine}")
            logger.info(f"    Branch: {coarse_branch_purity:.4f} -> {fine_branch_purity:.4f} (Δ={fine_branch_purity - coarse_branch_purity:+.4f})")
            logger.info(f"    Area: {coarse_area_purity:.4f} -> {fine_area_purity:.4f} (Δ={fine_area_purity - coarse_area_purity:+.4f})")
            logger.info(f"    Nesting: {nesting:.4f}")
            logger.info(f"    Zoom branch: rate={zoom_branch['improvement_rate']:.4f}, mean_imp={zoom_branch['mean_improvement']:.4f}")
            logger.info(f"    Fragmentation: median={frag_hierarchical['median_size']:.1f}, singletons={frag_hierarchical['singleton_fraction']:.1%}")
            logger.info(f"    hierarchical_v1 PASS: {hierarchical_v1_pass} (branch>0.5={fine_branch_purity>0.5}, zoom>0.5={zoom_branch['improvement_rate']>0.5 if zoom_branch['improvement_rate'] else False}, frag<1%={frag_hierarchical['singleton_fraction']<0.01})")
            
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
                'fragmentation': frag_hierarchical,
                'hierarchical_v1_pass': hierarchical_v1_pass,
            }
        
        all_results[mode] = {
            'mode': mode,
            'n_decisions': SAMPLE_SIZE,
            'configs': mode_results,
        }
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("HIERARCHICAL_V1 ADAPTIVE TEST SUMMARY")
    logger.info("=" * 70)
    
    for mode, result in all_results.items():
        logger.info(f"\n  {mode}:")
        for config_name, config_result in result['configs'].items():
            status = "✓ PASS" if config_result['hierarchical_v1_pass'] else "✗ FAIL"
            logger.info(f"    {config_name}: {status}")
            logger.info(f"      fine_branch_purity={config_result['fine_branch_purity']:.4f}")
            logger.info(f"      zoom_rate={config_result['zoom_branch']['improvement_rate']:.2%}")
            logger.info(f"      nesting={config_result['strict_nesting']:.4f}")
            logger.info(f"      singletons={config_result['fragmentation']['singleton_fraction']:.1%}")
            logger.info(f"      median_size={config_result['fragmentation']['median_size']:.1f}")
    
    # Save
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
        "run_id": f"hierarchical_v1_adaptive_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 29,
        "hypothesis": "Adaptive sub-resolution prevents over-fragmentation while maintaining fine_branch_purity > 0.5",
        "frozen_sample": f"{SAMPLE_SIZE} stratified BGer decisions",
        "frozen_metric": "fine_branch_purity, strict_nesting, zoom_coherence, fragmentation",
        "success_rule": "hierarchical_v1_pass = nesting>=0.99 AND fine_branch_purity>0.5 AND improvement_rate>0.5 AND singleton_fraction<0.01",
        "results": all_results,
    }
    
    output_path = OUTPUT_DIR / "hierarchical_v1_adaptive_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()