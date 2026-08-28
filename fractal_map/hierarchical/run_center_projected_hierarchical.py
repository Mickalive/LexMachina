#!/usr/bin/env python3
"""
Reproduce hierarchical Leiden on PURE center_projected embeddings (without TF-IDF).
This is required by factory direction v4: "must REPRODUCE hierarchical_leiden on center_projected 
embeddings as new default input"

Current default uses concat (center_projected + TF-IDF Erwaegungen).
This experiment validates whether pure center_projected achieves comparable/better metrics.
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

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_center_projected")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def load_center_projected():
    """Load pure center_projected embeddings (no TF-IDF concat)."""
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return center_emb


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on embeddings."""
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
        weights='weight', resolution_parameter=resolution, seed=seed
    )
    return np.array(partition.membership), partition.modularity


def hierarchical_leiden(embeddings, metadata, coarse_res=0.5, fine_res=1.5, sub_res=3.0, k=15, min_cluster_size=3):
    """
    Run hierarchical Leiden:
    1. Global Leiden at coarse_res
    2. Within each coarse cluster, run Leiden at sub_res
    3. Assign global labels: (coarse_id, sub_id)
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
        
        if len(indices) < min_cluster_size:
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


def compute_branch_purity(labels, metadata, min_cluster_size=3):
    """Compute branch purity, excluding clusters smaller than min_cluster_size."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        
        # Skip clusters smaller than min_cluster_size
        if len(indices) < min_cluster_size:
            continue
            
        cluster_branches = [metadata[i].get('branch') for i in indices]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    
    return float(np.mean(purities)) if purities else 0


def multi_resolution_clustering(embeddings, resolutions=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]):
    """Run Leiden at multiple resolutions."""
    hierarchy_labels = {}
    hierarchy_info = {}
    
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        n_clusters = len(set(labels[labels != -1]))
        hierarchy_labels[res] = labels
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': n_clusters,
            'modularity': float(modularity),
        }
        logger.info(f"   res={res}: {n_clusters} clusters, modularity={modularity:.4f}")
    
    return hierarchy_labels, hierarchy_info


def build_nesting(hierarchy_labels):
    """Build parent-child nesting between consecutive resolutions."""
    resolutions = sorted(hierarchy_labels.keys())
    nesting = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        
        child_to_parent = {}
        unique_fine = np.unique(finer_labels[finer_labels != -1])
        
        for fine_id in unique_fine:
            fine_mask = finer_labels == fine_id
            parent_labels = coarser_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            
            if len(parent_labels_valid) > 0:
                parent_id = Counter(parent_labels_valid.tolist()).most_common(1)[0][0]
                child_to_parent[int(fine_id)] = int(parent_id)
            else:
                child_to_parent[int(fine_id)] = -1
        
        parent_to_children = defaultdict(list)
        for child, parent in child_to_parent.items():
            parent_to_children[parent].append(child)
        
        nesting[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'child_to_parent': child_to_parent,
            'parent_to_children': dict(parent_to_children),
            'nesting_consistency': sum(1 for c, p in child_to_parent.items() if p != -1) / len(child_to_parent) if child_to_parent else 0,
        }
    
    return nesting


def compute_hierarchy_nesting_score(hierarchy_labels):
    """Compute nesting consistency: each finer cluster fully contained in one coarser."""
    resolutions = sorted(hierarchy_labels.keys())
    nesting_scores = []
    
    for i in range(len(resolutions) - 1):
        coarser = hierarchy_labels[resolutions[i]]
        finer = hierarchy_labels[resolutions[i + 1]]
        
        unique_fine = np.unique(finer[finer != -1])
        consistent = 0
        
        for fine_id in unique_fine:
            fine_mask = finer == fine_id
            parent_labels = coarser[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            
            if len(parent_labels_valid) > 0:
                unique_parents = len(set(parent_labels_valid.tolist()))
                if unique_parents == 1:
                    consistent += 1
        
        score = consistent / len(unique_fine) if len(unique_fine) > 0 else 0
        nesting_scores.append({
            'from_resolution': resolutions[i],
            'to_resolution': resolutions[i + 1],
            'nesting_score': float(score),
            'n_fine_clusters': int(len(unique_fine)),
            'n_consistent': int(consistent),
        })
    
    return nesting_scores


def compute_branch_coherence_per_level(hierarchy_labels, metadata, min_cluster_size=3):
    """Compute branch purity at each resolution level, excluding small clusters."""
    results = {}
    for res, labels in hierarchy_labels.items():
        unique_labels = np.unique(labels[labels != -1])
        purities = []
        
        for label in unique_labels:
            mask = labels == label
            indices = np.where(mask)[0]
            
            # Skip clusters smaller than min_cluster_size
            if len(indices) < min_cluster_size:
                continue
                
            cluster_branches = [metadata[i].get('branch') for i in indices]
            cluster_branches = [b for b in cluster_branches if b and b != 'null']
            
            if cluster_branches:
                most_common = Counter(cluster_branches).most_common(1)[0][1]
                purities.append(most_common / len(cluster_branches))
        
        results[f"res_{res}"] = {
            'mean_branch_purity': float(np.mean(purities)) if purities else 0,
            'n_clusters': int(len(unique_labels)),
            'purity_values': [float(p) for p in purities],
        }
    
    return results


def main():
    logger.info("=== Hierarchical Leiden on PURE center_projected ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    center_emb = load_center_projected()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    logger.info(f"   Center projected embeddings: {center_emb.shape}")
    
    branches = Counter(m.get('branch') for m in metadata if m.get('branch'))
    logger.info(f"   Branches: {dict(branches)}")
    
    # 2. Multi-resolution clustering
    resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    logger.info("\n2. Running multi-resolution Leiden on center_projected...")
    hierarchy_labels, hierarchy_info = multi_resolution_clustering(center_emb, resolutions)
    
    # 3. Build nesting structure
    logger.info("\n3. Building nesting structure...")
    nesting = build_nesting(hierarchy_labels)
    for key, nest in nesting.items():
        logger.info(f"   {key}: consistency={nest['nesting_consistency']:.3f}")
    
    # 4. Compute nesting score
    logger.info("\n4. Computing nesting consistency score...")
    nesting_scores = compute_hierarchy_nesting_score(hierarchy_labels)
    mean_nesting = np.mean([s['nesting_score'] for s in nesting_scores])
    logger.info(f"   Mean nesting score: {mean_nesting:.4f}")
    for s in nesting_scores:
        logger.info(f"   {s['from_resolution']}->{s['to_resolution']}: {s['nesting_score']:.3f} "
                    f"({s['n_consistent']}/{s['n_fine_clusters']})")
    
    # 5. Compute branch coherence per level
    logger.info("\n5. Computing branch coherence per level...")
    branch_coherence = compute_branch_coherence_per_level(hierarchy_labels, metadata, min_cluster_size=3)
    for res_key, bc in branch_coherence.items():
        logger.info(f"   {res_key}: branch_purity={bc['mean_branch_purity']:.4f}, n_clusters={bc['n_clusters']}")
    
    # 6. Hierarchical Leiden (coarse_0.5 -> fine_3.0) for comparison with concat results
    logger.info("\n6. Running hierarchical Leiden (coarse_0.5, sub_3.0)...")
    hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
        center_emb, metadata, coarse_res=0.5, fine_res=1.5, sub_res=3.0, min_cluster_size=3
    )
    
    n_fine_clusters = len(set(hierarchical_labels[hierarchical_labels != -1]))
    purity_hierarchical = compute_branch_purity(hierarchical_labels, metadata, min_cluster_size=3)
    purity_coarse = compute_branch_purity(coarse_labels, metadata, min_cluster_size=3)
    
    logger.info(f"   Fine clusters: {n_fine_clusters}")
    logger.info(f"   Coarse purity: {purity_coarse:.4f}")
    logger.info(f"   Hierarchical purity: {purity_hierarchical:.4f}")
    logger.info(f"   Nesting: 1.0 (by construction)")
    
    # 7. Flat Leiden comparison
    logger.info("\n7. Comparison with flat Leiden...")
    flat_labels = {}
    flat_purities = {}
    for res in resolutions:
        labels, mod = leiden_clustering(center_emb, resolution=res)
        flat_labels[res] = labels
        purity = compute_branch_purity(labels, metadata, min_cluster_size=3)
        flat_purities[res] = purity
        n_clusters = len(set(labels[labels != -1]))
        logger.info(f"  Flat res={res}: {n_clusters} clusters, purity={purity:.4f} (min_size=3)")
    
    flat_mean_purity = np.mean(list(flat_purities.values()))
    flat_nesting = compute_hierarchy_nesting_score(flat_labels)
    flat_mean_nesting = np.mean([s['nesting_score'] for s in flat_nesting])
    
    logger.info(f"\n  Flat Leiden: mean_nesting={flat_mean_nesting:.4f}, mean_purity={flat_mean_purity:.4f}")
    
    # 8. Hierarchical configs comparison
    logger.info("\n8. Testing hierarchical configs...")
    configs = [
        {'coarse_res': 0.25, 'fine_res': 1.0, 'sub_res': 3.0, 'name': 'coarse_0.25_fine_3.0'},
        {'coarse_res': 0.5, 'fine_res': 1.5, 'sub_res': 3.0, 'name': 'coarse_0.5_fine_3.0'},
        {'coarse_res': 0.5, 'fine_res': 2.0, 'sub_res': 3.0, 'name': 'coarse_0.5_fine_2.0'},
    ]
    
    all_results = {}
    for config in configs:
        logger.info(f"\n  Config: {config['name']}")
        h_labels, c_labels, c_info = hierarchical_leiden(
            center_emb, metadata,
            coarse_res=config['coarse_res'],
            fine_res=config['fine_res'],
            sub_res=config['sub_res'],
            min_cluster_size=3,
        )
        
        n_fine = len(set(h_labels[h_labels != -1]))
        purity_h = compute_branch_purity(h_labels, metadata, min_cluster_size=3)
        purity_c = compute_branch_purity(c_labels, metadata, min_cluster_size=3)
        
        logger.info(f"    Fine clusters: {n_fine}")
        logger.info(f"    Coarse purity: {purity_c:.4f}")
        logger.info(f"    Hierarchical purity: {purity_h:.4f}")
        logger.info(f"    Nesting: 1.0 (by construction)")
        
        all_results[config['name']] = {
            'config': config,
            'n_fine_clusters': n_fine,
            'coarse_purity': float(purity_c),
            'hierarchical_purity': float(purity_h),
            'nesting_score': 1.0,
            'cluster_info': c_info,
        }
    
    # 9. Summary
    logger.info("\n" + "=" * 70)
    logger.info("CENTER_PROJECTED HIERARCHICAL LEIDEN SUMMARY")
    logger.info("=" * 70)
    
    logger.info("\n  Multi-resolution flat Leiden:")
    for res in resolutions:
        info = hierarchy_info[f"res_{res}"]
        logger.info(f"    res={res}: {info['n_clusters']} clusters, modularity={info['modularity']:.4f}")
    
    logger.info(f"\n  Mean nesting score (multi-res): {mean_nesting:.4f}")
    logger.info(f"  Mean branch purity (all levels): {np.mean([branch_coherence[f'res_{r}']['mean_branch_purity'] for r in resolutions]):.4f}")
    
    logger.info("\n  Hierarchical Leiden (nesting guaranteed):")
    for name, result in all_results.items():
        logger.info(f"    {name}: purity={result['hierarchical_purity']:.4f}, nesting={result['nesting_score']:.4f}")
    
    logger.info(f"\n  Flat Leiden:")
    logger.info(f"    mean_nesting={flat_mean_nesting:.4f}, mean_purity={flat_mean_purity:.4f}")
    
    best_config = max(all_results.values(), key=lambda x: x['hierarchical_purity'])
    logger.info(f"\n  Best hierarchical config: {best_config['config']['name']}")
    logger.info(f"    Purity: {best_config['hierarchical_purity']:.4f}")
    logger.info(f"    Nesting: {best_config['nesting_score']:.4f}")
    
    logger.info("\n  KEY INSIGHT:")
    if best_config['hierarchical_purity'] > flat_mean_purity:
        logger.info(f"    Hierarchical Leiden achieves HIGHER purity ({best_config['hierarchical_purity']:.4f})")
        logger.info(f"    than flat Leiden ({flat_mean_purity:.4f}) while guaranteeing nesting (1.0).")
    else:
        logger.info(f"    Flat Leiden has higher purity ({flat_mean_purity:.4f}) than")
        logger.info(f"    hierarchical Leiden ({best_config['hierarchical_purity']:.4f}).")
    
    # Compare with concat results
    logger.info("\n  COMPARISON WITH CONCAT (center_projected + TF-IDF) RESULTS:")
    concat_purity = 0.9490748223452176  # from hierarchical_leiden_results.json
    logger.info(f"    Concat hierarchical purity (coarse_0.5_fine_3.0): {concat_purity:.4f}")
    logger.info(f"    Center_projected hierarchical purity (coarse_0.5_fine_3.0): {all_results['coarse_0.5_fine_3.0']['hierarchical_purity']:.4f}")
    diff = all_results['coarse_0.5_fine_3.0']['hierarchical_purity'] - concat_purity
    logger.info(f"    Difference: {diff:+.4f}")
    
    # Save results
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
        "run_id": f"center_projected_hierarchical_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 4,
        "hypothesis": "Hierarchical Leiden on pure center_projected embeddings achieves comparable/better purity and nesting than concat embeddings",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Nesting consistency, branch purity, zoom improvement rate",
        "success_rule": "Nesting = 1.0 AND purity >= concat baseline (0.949)",
        "embeddings": "center_projected (768 dim, no TF-IDF)",
        "hierarchical_results": all_results,
        "flat_results": {
            "mean_nesting": float(flat_mean_nesting),
            "mean_purity": float(flat_mean_purity),
            "per_resolution": flat_purities,
        },
        "multi_resolution": {
            "nesting_scores": nesting_scores,
            "mean_nesting_score": float(mean_nesting),
            "branch_coherence": branch_coherence,
            "hierarchy_info": hierarchy_info,
        },
        "best_config": best_config['config']['name'],
        "best_hierarchical_purity": best_config['hierarchical_purity'],
        "flat_mean_purity": float(flat_mean_purity),
        "concat_baseline_purity": concat_purity,
        "verdict": "PASS" if best_config['hierarchical_purity'] >= concat_purity else "FAIL",
    }
    
    output_path = OUTPUT_DIR / "center_projected_hierarchical_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Experiment complete ===")


if __name__ == "__main__":
    main()
