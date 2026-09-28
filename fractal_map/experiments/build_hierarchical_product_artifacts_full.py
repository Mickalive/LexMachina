#!/usr/bin/env python3
"""
Build Product Integration Artifacts for Constrained Hierarchical Leiden (Full)
=============================================================================
Runs constrained hierarchical Leiden AND saves all product artifacts:
- cluster_metadata.json: Legal context per cluster
- zoom_mappings.json: Bidirectional parent-child navigation
- decision_clusters.json: Decision-to-cluster index
- labels_coarse.npy, labels_fine.npy: Cluster assignments
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import logging
import sys
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path('/home/runner/work/LexMachina/LexMachina')
METADATA_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')
EMBEDDING_PATHS = {
    "full_text_tfidf_light": BASE / 'results/fractal_map/hierarchical_map_174k/tfidf_embeddings/full_text_tfidf_light.npy',
    "regeste_tfidf": BASE / 'results/fractal_map/hierarchical_map_174k/tfidf_embeddings/regeste_tfidf.npy',
    "regeste_full_text_hybrid_0.5": BASE / 'results/fractal_map/hierarchical_map_174k/tfidf_embeddings/regeste_full_text_hybrid_0.5.npy',
    "regeste_full_text_hybrid_0.7": BASE / 'results/fractal_map/hierarchical_map_174k/tfidf_embeddings/regeste_full_text_hybrid_0.7.npy',
}
OUTPUT_BASE = BASE / 'results/fractal_map/hierarchical_product_integration'

MODE_IDS = {
    "full_text_tfidf_light": "hierarchical_full_text_tfidf",
    "regeste_tfidf": "hierarchical_regeste_tfidf",
    "regeste_full_text_hybrid_0.5": "hierarchical_regeste_full_text_hybrid_0.5",
    "regeste_full_text_hybrid_0.7": "hierarchical_regeste_full_text_hybrid_0.7",
}

CONFIG = {
    "coarse_res": 0.25,
    "base_sub_res": 3.0,
    "min_cluster_size": 10,
    "max_subclusters_per_parent": 20,
    "adaptive_sub_res": True,
    "k_neighbors": 15,
}

MIN_PURITY_SIZE = 3


def load_data(mode_name):
    """Load embeddings and metadata."""
    emb_path = EMBEDDING_PATHS[mode_name]
    logger.info(f"Loading embeddings from {emb_path}")
    embeddings = np.load(emb_path)
    
    logger.info(f"Loading metadata from {METADATA_PATH}")
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    
    n = min(len(embeddings), len(metadata))
    embeddings = embeddings[:n]
    metadata = metadata[:n]
    
    norms = np.linalg.norm(embeddings, axis=1)
    valid_mask = norms > 0
    logger.info(f"Valid embeddings: {valid_mask.sum()}/{len(valid_mask)} ({(1-valid_mask.mean())*100:.1f}% zero-norm)")
    
    embeddings = embeddings[valid_mask]
    metadata = [m for i, m in enumerate(metadata) if valid_mask[i]]
    
    embeddings = normalize(embeddings, norm='l2')
    
    return embeddings, metadata


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on embeddings."""
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


def constrained_hierarchical_leiden(embeddings, metadata,
                                    coarse_res=0.25,
                                    base_sub_res=3.0,
                                    min_cluster_size=10,
                                    max_subclusters_per_parent=20,
                                    adaptive_sub_res=True,
                                    k=15):
    """Constrained Hierarchical Leiden with full label persistence."""
    logger.info(f"Running constrained hierarchical Leiden: coarse_res={coarse_res}, base_sub_res={base_sub_res}")
    
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run constrained Leiden
    fine_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_cluster_size * 2:
            fine_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0,
                'size': cluster_size, 'too_small': True,
                'sub_res_used': None
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        if adaptive_sub_res:
            if cluster_size < 500:
                sub_res = 1.5
            elif cluster_size < 2000:
                sub_res = 2.0
            else:
                sub_res = base_sub_res
        else:
            sub_res = base_sub_res
        
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        valid_sub = []
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            sub_size = sub_mask.sum()
            if sub_size >= min_cluster_size:
                valid_sub.append(sub_id)
        
        if len(valid_sub) > max_subclusters_per_parent:
            logger.warning(f"    Coarse {coarse_id}: {len(valid_sub)} sub-clusters > max {max_subclusters_per_parent}, merging smallest")
            sub_sizes = [(sid, (sub_labels == sid).sum()) for sid in valid_sub]
            sub_sizes.sort(key=lambda x: x[1], reverse=True)
            valid_sub = [sid for sid, _ in sub_sizes[:max_subclusters_per_parent]]
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): {len(valid_sub)} sub-clusters (sub_res={sub_res:.1f}), modularity={sub_mod:.4f}")
        
        for sub_id in valid_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            fine_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False,
                'sub_res_used': sub_res
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
        
        assigned_mask = np.isin(sub_labels, valid_sub)
        unassigned_indices = indices[~assigned_mask]
        if len(unassigned_indices) > 0:
            fine_labels[unassigned_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': -1,
                'size': int(len(unassigned_indices)), 'too_small': False,
                'sub_res_used': sub_res, 'is_remainder': True
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    logger.info(f"  Hierarchical: {len(unique_coarse)} coarse -> {sub_cluster_id} fine clusters")
    return coarse_labels, fine_labels, cluster_info, coarse_to_fine


def compute_cluster_metadata(labels, metadata, cluster_ids, level_name):
    """Compute legal context metadata for each cluster."""
    cluster_meta = {}
    for cid in cluster_ids:
        mask = labels == cid
        indices = np.where(mask)[0]
        if len(indices) == 0:
            continue
        
        branches = [metadata[i].get('branch') for i in indices]
        areas = [metadata[i].get('legal_area') for i in indices]
        chambers = [metadata[i].get('chamber') for i in indices]
        languages = [metadata[i].get('language') for i in indices]
        decision_ids = [metadata[i].get('decision_id') for i in indices]
        years = [metadata[i].get('year') for i in indices]
        
        branches = [b for b in branches if b and b != 'unknown' and b != 'null']
        areas = [a for a in areas if a and a != 'unknown' and a != 'null']
        chambers = [c for c in chambers if c and c != 'unknown' and c != 'null']
        languages = [l for l in languages if l and l != 'unknown' and l != 'null']
        years = [y for y in years if y is not None]
        
        cluster_meta[str(cid)] = {
            'cluster_id': int(cid),
            'level': level_name,
            'size': int(len(indices)),
            'dominant_branch': Counter(branches).most_common(1)[0][0] if branches else None,
            'branch_purity': round(Counter(branches).most_common(1)[0][1] / len(branches), 4) if branches else None,
            'branch_distribution': dict(Counter(branches)),
            'dominant_area': Counter(areas).most_common(1)[0][0] if areas else None,
            'area_purity': round(Counter(areas).most_common(1)[0][1] / len(areas), 4) if areas else None,
            'area_distribution': dict(Counter(areas)),
            'dominant_chamber': Counter(chambers).most_common(1)[0][0] if chambers else None,
            'chamber_distribution': dict(Counter(chambers)),
            'dominant_language': Counter(languages).most_common(1)[0][0] if languages else None,
            'language_distribution': dict(Counter(languages)),
            'year_range': [min(years), max(years)] if years else None,
            'decision_ids_sample': decision_ids[:100],
        }
    return cluster_meta


def build_zoom_mappings(coarse_labels, fine_labels):
    """Build bidirectional parent-child zoom mappings."""
    child_to_parent = {}
    parent_to_children = defaultdict(list)
    
    for fid in np.unique(fine_labels[fine_labels != -1]):
        mask = fine_labels == fid
        parent_vals = coarse_labels[mask]
        parent_vals = parent_vals[parent_vals != -1]
        if len(parent_vals) > 0:
            parent = int(Counter(parent_vals.tolist()).most_common(1)[0][0])
            child_to_parent[str(fid)] = parent
            parent_to_children[str(parent)].append(int(fid))
    
    return {
        'child_to_parent': child_to_parent,
        'parent_to_children': {k: v for k, v in parent_to_children.items()},
    }


def build_decision_clusters(metadata, coarse_labels, fine_labels):
    """Build decision_id -> {coarse, fine} mapping."""
    decision_clusters = {}
    for i, m in enumerate(metadata):
        did = m.get('decision_id')
        if did:
            decision_clusters[did] = {
                'coarse': int(coarse_labels[i]) if coarse_labels[i] != -1 else None,
                'fine': int(fine_labels[i]) if fine_labels[i] != -1 else None,
            }
    return decision_clusters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=list(EMBEDDING_PATHS.keys()))
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    
    mode_name = args.mode
    mode_id = MODE_IDS[mode_name]
    
    logger.info(f"Building product artifacts for {mode_name} -> {mode_id}")
    
    # Load data
    embeddings, metadata = load_data(mode_name)
    n_docs = len(embeddings)
    
    # Run constrained hierarchical Leiden
    coarse_labels, fine_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
        embeddings, metadata,
        coarse_res=CONFIG['coarse_res'],
        base_sub_res=CONFIG['base_sub_res'],
        min_cluster_size=CONFIG['min_cluster_size'],
        max_subclusters_per_parent=CONFIG['max_subclusters_per_parent'],
        adaptive_sub_res=CONFIG['adaptive_sub_res'],
        k=CONFIG['k_neighbors']
    )
    
    # Compute cluster metadata
    coarse_ids = np.unique(coarse_labels[coarse_labels != -1])
    fine_ids = np.unique(fine_labels[fine_labels != -1])
    
    coarse_meta = compute_cluster_metadata(coarse_labels, metadata, coarse_ids, 'coarse')
    fine_meta = compute_cluster_metadata(fine_labels, metadata, fine_ids, 'fine')
    
    # Merge metadata
    all_cluster_meta = {**coarse_meta, **fine_meta}
    
    # Build zoom mappings
    zoom_mappings = build_zoom_mappings(coarse_labels, fine_labels)
    
    # Build decision clusters
    decision_clusters = build_decision_clusters(metadata, coarse_labels, fine_labels)
    
    # Compute zoom coherence for storage
    def compute_zoom_coherence(coarse_labels, fine_labels, metadata, field='branch'):
        child_to_parent = {}
        for fid in np.unique(fine_labels[fine_labels != -1]):
            mask = fine_labels == fid
            parent_vals = coarse_labels[mask]
            parent_vals = parent_vals[parent_vals != -1]
            if len(parent_vals) > 0:
                child_to_parent[int(fid)] = int(Counter(parent_vals.tolist()).most_common(1)[0][0])
        
        improvements = []
        parent_details = {}
        for cid in np.unique(coarse_labels[coarse_labels != -1]):
            mask = coarse_labels == cid
            indices = np.where(mask)[0]
            if len(indices) < MIN_PURITY_SIZE:
                continue
            cvals = [metadata[i].get(field) for i in indices]
            cvals = [v for v in cvals if v and v != 'unknown' and v != 'null']
            if not cvals:
                continue
            coarse_purity = Counter(cvals).most_common(1)[0][1] / len(cvals)
            
            child_clusters = [fc for fc, pc in child_to_parent.items() if pc == cid]
            child_purities = []
            for fc in child_clusters:
                fmask = fine_labels == fc
                findices = np.where(fmask)[0]
                if len(findices) < MIN_PURITY_SIZE:
                    continue
                fvals = [metadata[i].get(field) for i in findices]
                fvals = [v for v in fvals if v and v != 'unknown' and v != 'null']
                if fvals:
                    child_purities.append(Counter(fvals).most_common(1)[0][1] / len(fvals))
            
            if child_purities:
                mean_child = float(np.mean(child_purities))
                improvements.append(mean_child - coarse_purity)
                parent_details[int(cid)] = {
                    'coarse_purity': round(float(coarse_purity), 4),
                    'mean_child_purity': round(mean_child, 4),
                    'improvement': round(mean_child - coarse_purity, 4),
                    'n_children': len(child_clusters),
                }
        
        return {
            'parent_details': parent_details,
            'overall': {
                'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
                'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
                'n_parents': len(parent_details),
            }
        }
    
    zoom_coherence_branch = compute_zoom_coherence(coarse_labels, fine_labels, metadata, 'branch')
    zoom_coherence_area = compute_zoom_coherence(coarse_labels, fine_labels, metadata, 'legal_area')
    
    # Output directory
    output_dir = OUTPUT_BASE / mode_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save artifacts
    logger.info(f"Saving artifacts to {output_dir}")
    
    # 1. Labels
    np.save(output_dir / 'labels_coarse.npy', coarse_labels)
    np.save(output_dir / 'labels_fine.npy', fine_labels)
    
    # 2. Cluster metadata
    with open(output_dir / 'cluster_metadata.json', 'w') as f:
        json.dump(all_cluster_meta, f, indent=2, default=str)
    
    # 3. Zoom mappings
    with open(output_dir / 'zoom_mappings.json', 'w') as f:
        json.dump(zoom_mappings, f, indent=2, default=str)
    
    # 4. Decision clusters
    with open(output_dir / 'decision_clusters.json', 'w') as f:
        json.dump(decision_clusters, f, indent=2, default=str)
    
    # 5. Zoom coherence
    with open(output_dir / 'zoom_coherence.json', 'w') as f:
        json.dump({
            'branch': zoom_coherence_branch,
            'area': zoom_coherence_area,
        }, f, indent=2, default=str)
    
    # 6. Summary
    summary = {
        'mode_id': mode_id,
        'source_mode': mode_name,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'config': CONFIG,
        'sample_size': n_docs,
        'coarse': {
            'n_clusters': len(coarse_ids),
            'branch_purity': coarse_meta[str(coarse_ids[0])]['branch_purity'] if len(coarse_ids) > 0 else None,
        },
        'fine': {
            'n_clusters': len(fine_ids),
            'branch_purity': fine_meta[str(fine_ids[0])]['branch_purity'] if len(fine_ids) > 0 else None,
        },
        'nesting': 1.0,
        'artifacts': [
            'labels_coarse.npy',
            'labels_fine.npy',
            'cluster_metadata.json',
            'zoom_mappings.json',
            'decision_clusters.json',
            'zoom_coherence.json',
        ],
    }
    
    with open(output_dir / 'product_integration_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"All artifacts saved to {output_dir}")
    logger.info(f"  Coarse clusters: {len(coarse_ids)}")
    logger.info(f"  Fine clusters: {len(fine_ids)}")
    logger.info(f"  Nesting: 1.0 (guaranteed)")
    logger.info(f"  Branch zoom coherence: {zoom_coherence_branch['overall']['improvement_rate']:.4f}")


if __name__ == '__main__':
    main()