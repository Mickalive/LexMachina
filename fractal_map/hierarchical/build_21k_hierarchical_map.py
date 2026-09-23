#!/usr/bin/env python3
"""
Build hierarchical map at 21k scale using compressed 5-level resolution ladder [0.25, 0.5, 1.0, 2.0, 3.0]
for TF-IDF based modes (regeste_tfidf, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7).
"""

import json
import argparse
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Configuration
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_21k/metadata_21k.json")
EMBEDDINGS_BASE = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_21k/tfidf_embeddings")
OUTPUT_BASE = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_21k/legal_distance_modes")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

# Compressed 5-level resolution ladder (validated in compressed_resolution_ladder_all_modes.py)
COMPRESSED_LADDER = [0.25, 0.5, 1.0, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3
K_NEIGHBORS = 15
SEED = 42

MODES = [
    "regeste_tfidf",
    "regeste_full_text_hybrid_0.5",
    "regeste_full_text_hybrid_0.7",
]


def load_metadata():
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    return metadata


def leiden_clustering(embeddings, resolution=1.0, k=K_NEIGHBORS, seed=SEED):
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
    return np.array(partition.membership)


def build_nesting(hierarchy_labels):
    resolutions = sorted(hierarchy_labels.keys())
    nesting = {}
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        child_to_parent = {}
        for fine_id in np.unique(finer_labels[finer_labels != -1]):
            fine_mask = finer_labels == fine_id
            parent_labels = coarser_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                child_to_parent[int(fine_id)] = int(
                    Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
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
            'nesting_consistency': (sum(1 for c, p in child_to_parent.items() if p != -1)
                                    / len(child_to_parent) if child_to_parent else 0),
        }
    return nesting


def compute_cluster_metadata(labels, metadata):
    cluster_info = {}
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        cluster_info[int(label)] = {
            'size': int(mask.sum()),
            'dominant_lang': dominant_lang[0],
            'lang_purity': dominant_lang[1] / len(indices) if indices.size else 0,
            'dominant_branch': dominant_branch[0],
            'branch_purity': dominant_branch[1] / len(indices) if indices.size else 0,
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
            'decision_ids': [metadata[i]['decision_id'] for i in indices],
            'decision_indices': indices.tolist(),
        }
    return cluster_info


def compute_zoom_coherence(hierarchy_labels, metadata, min_cluster_size=3):
    resolutions = sorted(hierarchy_labels.keys())
    zoom_coherence = {}
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        improvements = []
        parent_details = {}
        for coarse_id in np.unique(coarser_labels[coarser_labels != -1]):
            coarse_mask = coarser_labels == coarse_id
            coarse_indices = np.where(coarse_mask)[0]
            if len(coarse_indices) < min_cluster_size:
                continue
            coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
            coarse_branches = [b for b in coarse_branches if b and b != 'null']
            if not coarse_branches:
                continue
            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
            child_clusters = []
            for fine_id in np.unique(finer_labels[finer_labels != -1]):
                fine_mask = finer_labels == fine_id
                parent_labels = coarser_labels[fine_mask]
                parent_labels_valid = parent_labels[parent_labels != -1]
                if len(parent_labels_valid) > 0 and \
                        Counter(parent_labels_valid.tolist()).most_common(1)[0][0] == coarse_id:
                    child_clusters.append(fine_id)
            if not child_clusters:
                continue
            child_purities = []
            for child_id in child_clusters:
                child_mask = finer_labels == child_id
                child_indices = np.where(child_mask)[0]
                if len(child_indices) < min_cluster_size:
                    continue
                child_branches = [metadata[i].get('branch') for i in child_indices]
                child_branches = [b for b in child_branches if b and b != 'null']
                if child_branches:
                    child_purities.append(Counter(child_branches).most_common(1)[0][1]
                                          / len(child_branches))
            if child_purities:
                mean_child_purity = np.mean(child_purities)
                improvements.append(mean_child_purity - coarse_purity)
                parent_details[int(coarse_id)] = {
                    'coarse_purity': float(coarse_purity),
                    'mean_child_purity': float(mean_child_purity),
                    'improvement': float(mean_child_purity - coarse_purity),
                    'n_children': len(child_clusters),
                }
        zoom_coherence[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'mean_improvement': float(np.mean(improvements)) if improvements else 0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0)
                                      / len(improvements)) if improvements else 0,
            'parent_details': parent_details,
        }
    return zoom_coherence


def build_decision_clusters(hierarchy_labels, metadata):
    decision_clusters = {}
    for idx, m in enumerate(metadata):
        did = m['decision_id']
        decision_clusters[did] = {f"res_{res}": int(hierarchy_labels[res][idx])
                                  for res in hierarchy_labels}
    return decision_clusters


def compute_branch_purity(labels, metadata, min_cluster_size=3):
    purities = []
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        branches = [metadata[i].get('branch') for i in indices]
        branches = [b for b in branches if b and b != 'null']
        if branches:
            purities.append(Counter(branches).most_common(1)[0][1] / len(branches))
    return float(np.mean(purities)) if purities else 0


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


def build_mode(mode_id):
    logger.info(f"\n{'='*70}")
    logger.info(f"Building hierarchical map for: {mode_id}")
    logger.info(f"{'='*70}")
    
    # Load embeddings
    emb_path = EMBEDDINGS_BASE / f"{mode_id}.npy"
    if not emb_path.exists():
        logger.error(f"Embedding not found: {emb_path}")
        return None
    
    embeddings = np.load(emb_path)
    logger.info(f"Loaded embeddings: {embeddings.shape}")
    
    # Load metadata
    metadata = load_metadata()
    
    if embeddings.shape[0] != len(metadata):
        logger.error(f"Embedding count {embeddings.shape[0]} != metadata count {len(metadata)}")
        return None
    
    # Multi-resolution Leiden
    hierarchy_labels = {}
    hierarchy_info = {}
    for res in COMPRESSED_LADDER:
        labels = leiden_clustering(embeddings, resolution=res)
        n_clusters = len(set(labels[labels != -1]))
        hierarchy_labels[res] = labels
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': int(n_clusters),
        }
        logger.info(f"  res={res}: {n_clusters} clusters")
    
    # Nesting
    nesting = build_nesting(hierarchy_labels)
    for key, nest in nesting.items():
        logger.info(f"  {key}: consistency={nest['nesting_consistency']:.3f}")
    
    # Cluster metadata
    cluster_metadata_by_res = {}
    for res in COMPRESSED_LADDER:
        cluster_metadata_by_res[f"res_{res}"] = compute_cluster_metadata(
            hierarchy_labels[res], metadata)
    
    # Zoom coherence
    zoom_coherence = compute_zoom_coherence(hierarchy_labels, metadata,
                                            min_cluster_size=MIN_CLUSTER_SIZE)
    for key, zc in zoom_coherence.items():
        logger.info(f"  {key}: mean_improvement={zc['mean_improvement']:.4f}, improvement_rate={zc['improvement_rate']:.3f}")
    
    # Decision clusters
    decision_clusters = build_decision_clusters(hierarchy_labels, metadata)
    
    # Hierarchical best = finest resolution (legal-distance rule)
    hierarchical_labels = hierarchy_labels[COMPRESSED_LADDER[-1]]
    coarse_labels = hierarchy_labels[0.5]
    hier_purity = compute_branch_purity(hierarchical_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE)
    coarse_purity = compute_branch_purity(coarse_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE)
    
    branch_coherence = {}
    for res in COMPRESSED_LADDER:
        branch_coherence[f"res_{res}"] = {
            'mean_branch_purity': compute_branch_purity(hierarchy_labels[res], metadata, min_cluster_size=MIN_CLUSTER_SIZE),
            'n_clusters': int(len(np.unique(hierarchy_labels[res][hierarchy_labels[res] != -1]))),
        }
    
    # Output directory
    mode_output_dir = OUTPUT_BASE / mode_id
    mode_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save label arrays
    for res in COMPRESSED_LADDER:
        np.save(mode_output_dir / f"labels_res_{res}.npy", hierarchy_labels[res])
    np.save(mode_output_dir / "labels_hierarchical_best.npy", hierarchical_labels)
    np.save(mode_output_dir / "labels_coarse_0.5.npy", coarse_labels)
    
    # Save results
    output = {
        "run_id": f"hierarchical_21k_{mode_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 25,
        "mode_id": mode_id,
        "hypothesis": "Multi-resolution Leiden on TF-IDF legal-text embeddings produces nested hierarchy at 21k scale",
        "frozen_sample": f"{len(metadata)} decisions from local JSONL corpus (subset of 174k)",
        "frozen_metric": "Nesting consistency, branch purity per level, zoom improvement rate, provenance purity",
        "embeddings_source": str(emb_path),
        "corpus_size": len(metadata),
        "resolutions_tested": COMPRESSED_LADDER,
        "hierarchy_info": hierarchy_info,
        "nesting": nesting,
        "mean_nesting_score": float(np.mean([n['nesting_consistency'] for n in nesting.values()])),
        "branch_coherence": branch_coherence,
        "zoom_coherence": zoom_coherence,
        "hierarchical": {
            "config": "fine_3.0 (legal-distance rule: hierarchical_best := finest resolution)",
            "n_clusters": int(len(set(hierarchical_labels[hierarchical_labels != -1]))),
            "branch_purity": hier_purity,
            "coarse_0.5_purity": coarse_purity,
        },
        "summary": {
            "n_decisions": len(metadata),
            "n_resolutions": len(COMPRESSED_LADDER),
            "mean_branch_purity_all_levels": float(np.mean(
                [branch_coherence[f"res_{r}"]['mean_branch_purity'] for r in COMPRESSED_LADDER])),
        },
    }
    
    with open(mode_output_dir / "hierarchical_map_results.json", 'w') as f:
        json.dump(convert(output), f, indent=2)
    with open(mode_output_dir / "zoom_mappings.json", 'w') as f:
        json.dump(convert(nesting), f, indent=2)
    with open(mode_output_dir / "zoom_coherence.json", 'w') as f:
        json.dump(convert(zoom_coherence), f, indent=2)
    with open(mode_output_dir / "decision_clusters.json", 'w') as f:
        json.dump(convert(decision_clusters), f)
    with open(mode_output_dir / "cluster_metadata.json", 'w') as f:
        json.dump(convert(cluster_metadata_by_res), f, indent=2)
    
    logger.info(f"\nArtifacts saved to {mode_output_dir}")
    
    # Print summary
    print(json.dumps({
        "mode_id": mode_id,
        "corpus_size": len(metadata),
        "n_fine_clusters": int(len(set(hierarchical_labels[hierarchical_labels != -1]))),
        "mean_nesting_score": float(np.mean([n['nesting_consistency'] for n in nesting.values()])),
        "mean_branch_purity_all_levels": float(np.mean(
            [branch_coherence[f"res_{r}"]['mean_branch_purity'] for r in COMPRESSED_LADDER])),
        "output_dir": str(mode_output_dir),
    }, indent=2))
    
    return output


def main():
    logger.info("=== Building 21k Hierarchical Maps (Compressed 5-Level Ladder) ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Modes: {MODES}")
    logger.info(f"Resolution ladder: {COMPRESSED_LADDER}")
    
    results = {}
    for mode_id in MODES:
        try:
            result = build_mode(mode_id)
            if result:
                results[mode_id] = result
        except Exception as e:
            logger.error(f"Failed to build {mode_id}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    for mode_id, result in results.items():
        logger.info(f"{mode_id}:")
        logger.info(f"  Fine clusters: {result['hierarchical']['n_clusters']}")
        logger.info(f"  Mean nesting: {result['mean_nesting_score']:.4f}")
        logger.info(f"  Mean branch purity: {result['summary']['mean_branch_purity_all_levels']:.4f}")
        logger.info(f"  Hierarchical purity: {result['hierarchical']['branch_purity']:.4f}")
    
    logger.info("\n=== 21k hierarchical map build complete ===")


if __name__ == "__main__":
    main()
