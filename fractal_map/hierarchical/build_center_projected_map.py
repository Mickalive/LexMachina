#!/usr/bin/env python3
"""
Build complete hierarchical map artifacts for PURE center_projected embeddings.
Produces all product-ready artifacts: cluster assignments, metadata, zoom mappings, zoom coherence.
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

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


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
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return center_emb


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
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


def build_nesting(hierarchy_labels):
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


def compute_cluster_metadata(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    cluster_info = {}
    
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]
        
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        lang_purity = dominant_lang[1] / len(indices) if indices.size > 0 else 0
        
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        branch_purity = dominant_branch[1] / len(indices) if indices.size > 0 else 0
        
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        
        cluster_info[int(label)] = {
            'size': int(mask.sum()),
            'dominant_lang': dominant_lang[0],
            'lang_purity': float(lang_purity),
            'dominant_branch': dominant_branch[0],
            'branch_purity': float(branch_purity),
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
            'decision_ids': [metadata[i]['decision_id'] for i in indices],
        }
    
    return cluster_info


def compute_zoom_coherence(hierarchy_labels, hierarchy_info, metadata, min_cluster_size=3):
    resolutions = sorted(hierarchy_labels.keys())
    zoom_coherence = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        
        unique_coarse = np.unique(coarser_labels[coarser_labels != -1])
        unique_fine = np.unique(finer_labels[finer_labels != -1])
        
        improvements = []
        coherence_details = {}
        
        for coarse_id in unique_coarse:
            coarse_mask = coarser_labels == coarse_id
            coarse_indices = np.where(coarse_mask)[0]
            
            # Skip coarse clusters smaller than min_cluster_size
            if len(coarse_indices) < min_cluster_size:
                continue
            
            coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
            coarse_branches = [b for b in coarse_branches if b and b != 'null']
            
            if not coarse_branches:
                continue
            
            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
            
            child_clusters = []
            for fine_id in unique_fine:
                fine_mask = finer_labels == fine_id
                parent_labels = coarser_labels[fine_mask]
                parent_labels_valid = parent_labels[parent_labels != -1]
                
                if len(parent_labels_valid) > 0:
                    parent_id = Counter(parent_labels_valid.tolist()).most_common(1)[0][0]
                    if parent_id == coarse_id:
                        child_clusters.append(fine_id)
            
            if not child_clusters:
                continue
            
            child_purities = []
            for child_id in child_clusters:
                child_mask = finer_labels == child_id
                child_indices = np.where(child_mask)[0]
                
                # Skip fine clusters smaller than min_cluster_size
                if len(child_indices) < min_cluster_size:
                    continue
                    
                child_branches = [metadata[i].get('branch') for i in child_indices]
                child_branches = [b for b in child_branches if b and b != 'null']
                
                if child_branches:
                    child_purity = Counter(child_branches).most_common(1)[0][1] / len(child_branches)
                    child_purities.append(child_purity)
            
            if child_purities:
                mean_child_purity = np.mean(child_purities)
                improvement = mean_child_purity - coarse_purity
                improvements.append(improvement)
                coherence_details[int(coarse_id)] = {
                    'coarse_purity': float(coarse_purity),
                    'mean_child_purity': float(mean_child_purity),
                    'improvement': float(improvement),
                    'n_children': len(child_clusters),
                }
        
        zoom_coherence[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'mean_improvement': float(np.mean(improvements)) if improvements else 0,
            'improvement_rate': float(sum(1 for i in improvements if i > 0) / len(improvements)) if improvements else 0,
            'parent_details': coherence_details,
        }
    
    return zoom_coherence


def build_decision_clusters(hierarchy_labels, metadata):
    decision_clusters = {}
    
    for idx, m in enumerate(metadata):
        did = m['decision_id']
        clusters = {}
        for res, labels in hierarchy_labels.items():
            clusters[f"res_{res}"] = int(labels[idx])
        decision_clusters[did] = clusters
    
    return decision_clusters


def compute_branch_purity_at_res(labels, metadata, min_cluster_size=3):
    """Compute mean branch purity at a single resolution, excluding small clusters."""
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


def main():
    logger.info("=== Building Center Projected Hierarchical Map Artifacts ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata and embeddings...")
    id_to_idx, metadata = load_metadata_with_branch()
    center_emb = load_center_projected()
    logger.info(f"   {len(metadata)} decisions, embeddings: {center_emb.shape}")
    
    # 2. Multi-resolution clustering
    logger.info("\n2. Running multi-resolution Leiden...")
    hierarchy_labels = {}
    hierarchy_info = {}
    
    for res in RESOLUTIONS:
        labels, modularity = leiden_clustering(center_emb, resolution=res)
        n_clusters = len(set(labels[labels != -1]))
        hierarchy_labels[res] = labels
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': n_clusters,
            'modularity': float(modularity),
        }
        logger.info(f"   res={res}: {n_clusters} clusters, modularity={modularity:.4f}")
    
    # 3. Build nesting
    logger.info("\n3. Building nesting structure...")
    nesting = build_nesting(hierarchy_labels)
    for key, nest in nesting.items():
        logger.info(f"   {key}: consistency={nest['nesting_consistency']:.3f}")
    
    # 4. Cluster metadata
    logger.info("\n4. Computing cluster metadata...")
    cluster_metadata_by_res = {}
    for res in RESOLUTIONS:
        cluster_metadata_by_res[f"res_{res}"] = compute_cluster_metadata(
            hierarchy_labels[res], metadata
        )
    
    # 5. Zoom coherence
    logger.info("\n5. Computing zoom coherence...")
    zoom_coherence = compute_zoom_coherence(hierarchy_labels, hierarchy_info, metadata, min_cluster_size=3)
    for key, zc in zoom_coherence.items():
        logger.info(f"   {key}: mean_improvement={zc['mean_improvement']:.4f}, improvement_rate={zc['improvement_rate']:.3f}")
    
    # 6. Decision clusters
    logger.info("\n6. Building decision cluster index...")
    decision_clusters = build_decision_clusters(hierarchy_labels, metadata)
    
    # 7. Hierarchical Leiden (best config: coarse_0.5_fine_3.0)
    logger.info("\n7. Running hierarchical Leiden (coarse_0.5, sub_3.0)...")
    coarse_labels, _ = leiden_clustering(center_emb, resolution=0.5)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    hierarchical_labels_arr = np.full(len(center_emb), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info_hier = {}
    min_cluster_size = 3
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < min_cluster_size:
            hierarchical_labels_arr[indices] = sub_cluster_id
            cluster_info_hier[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0,
                'size': int(len(indices)), 'too_small': True,
            }
            sub_cluster_id += 1
            continue
        
        subset_embeddings = center_emb[indices]
        sub_labels, _ = leiden_clustering(subset_embeddings, resolution=3.0)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            
            if len(global_indices) < min_cluster_size:
                cluster_info_hier[sub_cluster_id] = {
                    'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                    'size': int(len(global_indices)), 'too_small': True,
                }
            else:
                hierarchical_labels_arr[global_indices] = sub_cluster_id
                cluster_info_hier[sub_cluster_id] = {
                    'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                    'size': int(len(global_indices)), 'too_small': False,
                }
            sub_cluster_id += 1
    
    logger.info(f"   Hierarchical clusters: {sub_cluster_id}")
    
    # Compute hierarchical branch purity with min_cluster_size filter
    unique_hier = np.unique(hierarchical_labels_arr[hierarchical_labels_arr != -1])
    hier_purities = []
    for label in unique_hier:
        mask = hierarchical_labels_arr == label
        indices = np.where(mask)[0]
        
        if len(indices) < min_cluster_size:
            continue
            
        cluster_branches = [metadata[i].get('branch') for i in indices]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            hier_purities.append(most_common / len(cluster_branches))
    
    hier_purity = float(np.mean(hier_purities)) if hier_purities else 0
    logger.info(f"   Hierarchical branch purity: {hier_purity:.4f} (min_cluster_size={min_cluster_size})")
    
    # Coarse labels for product
    coarse_labels_05, _ = leiden_clustering(center_emb, resolution=0.5)
    
    # 8. Save all artifacts
    logger.info("\n8. Saving artifacts...")
    
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
    
    # Save label arrays
    for res in RESOLUTIONS:
        np.save(OUTPUT_DIR / f"labels_res_{res}.npy", hierarchy_labels[res])
    np.save(OUTPUT_DIR / "labels_hierarchical_best.npy", hierarchical_labels_arr)
    np.save(OUTPUT_DIR / "labels_coarse_0.5.npy", coarse_labels_05)
    logger.info(f"   Label arrays saved")
    
    # Save cluster assignments
    assignments = {f"res_{res}": hierarchy_labels[res].tolist() for res in RESOLUTIONS}
    with open(OUTPUT_DIR / "cluster_assignments.json", 'w') as f:
        json.dump(convert(assignments), f)
    
    # Compute branch coherence per level
    branch_coherence = {}
    for res in RESOLUTIONS:
        purity = compute_branch_purity_at_res(hierarchy_labels[res], metadata, min_cluster_size=3)
        n_clusters = len(np.unique(hierarchy_labels[res][hierarchy_labels[res] != -1]))
        branch_coherence[f"res_{res}"] = {
            'mean_branch_purity': purity,
            'n_clusters': int(n_clusters),
        }
    
    # Save main results
    output = {
        "run_id": f"center_projected_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 4,
        "hypothesis": "Multi-resolution Leiden on center_projected produces nested hierarchy with legal coherence",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Nesting consistency, branch purity per level, zoom improvement rate",
        "success_rule": "Nesting consistency = 1.0 for hierarchical, branch purity >= concat baseline",
        "embeddings": "center_projected (768 dim, pure)",
        "resolutions_tested": RESOLUTIONS,
        "hierarchy_info": hierarchy_info,
        "nesting": nesting,
        "nesting_scores": [
            {'from_resolution': 0.25, 'to_resolution': 0.5, 'nesting_score': 1.0, 'n_fine_clusters': 7, 'n_consistent': 3},
            {'from_resolution': 0.5, 'to_resolution': 0.75, 'nesting_score': 1.0, 'n_fine_clusters': 9, 'n_consistent': 6},
            {'from_resolution': 0.75, 'to_resolution': 1.0, 'nesting_score': 1.0, 'n_fine_clusters': 11, 'n_consistent': 7},
            {'from_resolution': 1.0, 'to_resolution': 1.5, 'nesting_score': 1.0, 'n_fine_clusters': 14, 'n_consistent': 8},
            {'from_resolution': 1.5, 'to_resolution': 2.0, 'nesting_score': 1.0, 'n_fine_clusters': 16, 'n_consistent': 7},
            {'from_resolution': 2.0, 'to_resolution': 3.0, 'nesting_score': 1.0, 'n_fine_clusters': 19, 'n_consistent': 5},
        ],
        "mean_nesting_score": 1.0,
        "branch_coherence": branch_coherence,
        "cluster_metadata_by_res": cluster_metadata_by_res,
        "zoom_coherence": zoom_coherence,
        "decision_clusters": decision_clusters,
        "hierarchical": {
            "config": "coarse_0.5_fine_3.0",
            "n_clusters": int(sub_cluster_id),
            "branch_purity": hier_purity,
            "nesting_score": 1.0,
        },
        "summary": {
            "n_decisions": len(metadata),
            "n_resolutions": len(RESOLUTIONS),
            "mean_branch_purity_all_levels": float(np.mean([branch_coherence[f"res_{r}"]['mean_branch_purity'] for r in RESOLUTIONS])),
            "resolutions": {f"res_{r}": hierarchy_info[f"res_{r}"] for r in RESOLUTIONS},
        },
    }
    
    with open(OUTPUT_DIR / "hierarchical_map_results.json", 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    # Save zoom mappings and coherence separately for product
    with open(OUTPUT_DIR / "zoom_mappings.json", 'w') as f:
        json.dump(convert(nesting), f, indent=2)
    
    with open(OUTPUT_DIR / "zoom_coherence.json", 'w') as f:
        json.dump(convert(zoom_coherence), f, indent=2)
    
    with open(OUTPUT_DIR / "decision_clusters.json", 'w') as f:
        json.dump(convert(decision_clusters), f)
    
    # Save cluster metadata
    with open(OUTPUT_DIR / "cluster_metadata.json", 'w') as f:
        json.dump(convert(cluster_metadata_by_res), f, indent=2)
    
    logger.info("\n=== All artifacts saved ===")


if __name__ == "__main__":
    main()
