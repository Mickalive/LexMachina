#!/usr/bin/env python3
"""
Build 174k-scale hierarchical Leiden fractal map artifacts for dense embeddings.
=================================================================================

This pipeline consumes year-split dense embeddings from legal-distance and builds
hierarchical Leiden maps at full corpus scale (174k decisions).

Key design decisions based on accepted evidence:
- Embedding: center_projected_64dim (language-debiased, validated sweet spot at 62k)
- Method: Hierarchical Leiden (coarse res=0.25, sub_res=3.0) - PASSED v26 success rule at 62k
- Resolution ladder: Compressed 5-level [0.25, 0.5, 1.0, 2.0, 3.0] - 100% purity delta retention
- Local UMAP: Zoom-conditioned neighborhoods within each coarse cluster
- Artifacts: Compatible with ProductMapLoader API

Evidence-backed path (from state/fractal_map.json):
- center_projected_64dim + hierarchical Leiden (coarse=0.25, sub=3.0): FIRST PASS of v26 success rule at 62k scale
- Branch PASS, Area PASS, Rate PASS (2/4 > 0.5), frag 1.7%
- Pipeline ready for full 174k delivery

Usage:
    python build_174k_dense_hierarchical.py --embedding-dir /path/to/dense/embeddings --output-dir results/fractal_map/legal_distance_modes/center_projected_64dim_hierarchical_174k
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
import argparse
import sys
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
from sklearn.preprocessing import normalize
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False
    logging.warning("UMAP not available - local zoom neighborhoods will be skipped")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Configuration
RESOLUTIONS_FULL = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
RESOLUTIONS_COMPRESSED = [0.25, 0.5, 1.0, 2.0, 3.0]  # Validated 5-level ladder
DEFAULT_COARSE_RES = 0.25
DEFAULT_SUB_RES = 3.0
MIN_CLUSTER_SIZE = 3
K_NEIGHBORS = 15
UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST = 0.1
UMAP_MAX_CLUSTER_SIZE = 5000  # Subsample large clusters for UMAP


def load_metadata_174k(metadata_path: Path):
    """Load 174k metadata with branch/legal_area."""
    logger.info(f"Loading metadata from {metadata_path}")
    with open(metadata_path) as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} decisions")
    return metadata


def load_year_split_embeddings(embedding_dir: Path, pattern: str = "center_projected_64dim_*.npy"):
    """
    Load and concatenate year-split dense embeddings.
    
    Expected structure: embedding_dir/center_projected_64dim_2000.npy, _2001.npy, etc.
    """
    files = sorted(embedding_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No embedding files found matching {pattern} in {embedding_dir}")
    
    logger.info(f"Found {len(files)} year-split embedding files")
    embeddings_list = []
    total_decisions = 0
    
    for f in files:
        emb = np.load(f)
        embeddings_list.append(emb)
        total_decisions += len(emb)
        logger.info(f"  {f.name}: {emb.shape}")
    
    embeddings = np.vstack(embeddings_list)
    logger.info(f"Concatenated embeddings: {embeddings.shape} ({total_decisions} decisions)")
    return embeddings


def load_dense_embeddings_174k(embedding_path: Path):
    """Load single-file 174k dense embeddings."""
    logger.info(f"Loading embeddings from {embedding_path}")
    embeddings = np.load(embedding_path)
    logger.info(f"Loaded embeddings: {embeddings.shape}")
    return embeddings


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


def hierarchical_leiden(embeddings, metadata, coarse_res=0.25, sub_res=3.0, k=15):
    """
    Hierarchical Leiden: coarse clustering, then fine clustering within each coarse cluster.
    Guarantees perfect nesting (nesting=1.0) by construction.
    """
    logger.info(f"Running hierarchical Leiden: coarse_res={coarse_res}, sub_res={sub_res}")
    
    # Coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Fine clustering within each coarse cluster
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < 20:
            # Too small to sub-cluster
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0, 
                'size': int(len(indices)), 'too_small': True}
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
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
                'size': int(len(global_indices)), 'too_small': False}
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    logger.info(f"  Hierarchical: {len(unique_coarse)} coarse -> {sub_cluster_id} fine clusters")
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


def compute_cluster_metadata(labels, metadata):
    """Compute cluster metadata (purity, dominant labels, etc.)."""
    unique_labels = np.unique(labels[labels != -1])
    cluster_info = {}
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]
        
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        lang_purity = dominant_lang[1] / len(indices) if len(indices) > 0 else 0
        
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        branch_purity = dominant_branch[1] / len(indices) if len(indices) > 0 else 0
        
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
            'decision_indices': indices.tolist(),
        }
    return cluster_info


def build_zoom_mappings(labels_by_res):
    """Build bidirectional zoom mappings between consecutive resolutions."""
    resolutions = sorted(labels_by_res.keys())
    zoom_mappings = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarse_labels = labels_by_res[coarser_res]
        fine_labels = labels_by_res[finer_res]
        
        parent_to_children = defaultdict(list)
        child_to_parent = {}
        
        for fine_id in np.unique(fine_labels[fine_labels != -1]):
            fine_mask = fine_labels == fine_id
            parent_labels = coarse_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                parent = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
                child_to_parent[int(fine_id)] = parent
                parent_to_children[parent].append(int(fine_id))
        
        zoom_mappings[f"{coarser_res}_to_{finer_res}"] = {
            'parent_to_children': {str(k): v for k, v in parent_to_children.items()},
            'child_to_parent': {str(k): v for k, v in child_to_parent.items()},
        }
    
    return zoom_mappings


def build_zoom_coherence(labels_by_res, metadata):
    """Build zoom coherence metrics between consecutive resolutions."""
    resolutions = sorted(labels_by_res.keys())
    zoom_coherence = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarse_labels = labels_by_res[coarser_res]
        fine_labels = labels_by_res[finer_res]
        
        child_to_parent = {}
        for fine_id in np.unique(fine_labels[fine_labels != -1]):
            fine_mask = fine_labels == fine_id
            parent_labels = coarse_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                child_to_parent[int(fine_id)] = int(
                    Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
        
        parent_details = {}
        improvements = []
        
        for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
            coarse_mask = coarse_labels == coarse_id
            coarse_indices = np.where(coarse_mask)[0]
            if len(coarse_indices) < MIN_CLUSTER_SIZE:
                continue
            coarse_branches = [metadata[j].get('branch') for j in coarse_indices]
            coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
            if not coarse_branches:
                continue
            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
            
            child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
            child_purities = []
            for fc in child_clusters:
                fine_mask = fine_labels == fc
                fine_indices = np.where(fine_mask)[0]
                if len(fine_indices) < MIN_CLUSTER_SIZE:
                    continue
                fine_branches = [metadata[j].get('branch') for j in fine_indices]
                fine_branches = [b for b in fine_branches if b and b != 'unknown' and b != 'null']
                if fine_branches:
                    child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
            
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
            'parent_details': parent_details,
            'overall': {
                'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
                'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
                'n_parents': len(parent_details),
            }
        }
    
    # Add hierarchical zoom coherence
    return zoom_coherence


def compute_local_umap_neighborhoods(embeddings, coarse_labels, output_dir: Path):
    """
    Compute local UMAP embeddings within each coarse cluster for zoom-conditioned neighborhoods.
    Creates a 'local map' for each cluster for fine-grained interactive navigation.
    """
    if not HAS_UMAP:
        logger.warning("UMAP not available, skipping local neighborhood computation")
        return {}
    
    logger.info("Computing local UMAP zoom-conditioned neighborhoods...")
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    local_embeddings = {}
    local_metadata = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        cluster_embeddings = embeddings[mask]
        cluster_indices = np.where(mask)[0]
        
        if len(cluster_embeddings) < 10:
            continue
        
        # Subsample if too large
        if len(cluster_embeddings) > UMAP_MAX_CLUSTER_SIZE:
            idx = np.random.choice(len(cluster_embeddings), UMAP_MAX_CLUSTER_SIZE, replace=False)
            cluster_embeddings = cluster_embeddings[idx]
            cluster_indices = cluster_indices[idx]
        
        try:
            reducer = umap.UMAP(
                n_neighbors=min(UMAP_N_NEIGHBORS, len(cluster_embeddings)-1),
                min_dist=UMAP_MIN_DIST, 
                n_components=2, 
                random_state=42,
                metric='euclidean'
            )
            local_emb = reducer.fit_transform(cluster_embeddings)
            local_embeddings[int(coarse_id)] = local_emb.astype(np.float32)
            local_metadata[int(coarse_id)] = {
                'global_indices': cluster_indices.tolist(),
                'n_points': len(cluster_indices),
                'subsampled': len(cluster_indices) > UMAP_MAX_CLUSTER_SIZE
            }
            logger.info(f"  Coarse cluster {coarse_id}: {len(cluster_embeddings)} points -> 2D UMAP")
        except Exception as e:
            logger.warning(f"  UMAP failed for coarse cluster {coarse_id}: {e}")
    
    # Save local UMAP embeddings
    umap_dir = output_dir / "local_umap"
    umap_dir.mkdir(parents=True, exist_ok=True)
    
    for coarse_id, emb in local_embeddings.items():
        np.save(umap_dir / f"coarse_{coarse_id}_umap.npy", emb)
    
    with open(umap_dir / "local_umap_metadata.json", 'w') as f:
        json.dump(local_metadata, f, indent=2)
    
    logger.info(f"Local UMAP saved to {umap_dir} ({len(local_embeddings)} clusters)")
    return local_metadata


def build_artifacts_174k(config, metadata, embeddings, output_dir: Path):
    """Build all artifacts for a 174k hierarchical Leiden config."""
    mode_id = config['mode_id']
    coarse_res = config.get('coarse_res', DEFAULT_COARSE_RES)
    sub_res = config.get('sub_res', DEFAULT_SUB_RES)
    
    logger.info(f"\n=== Building 174k artifacts for {mode_id} ===")
    logger.info(f"Embeddings: {embeddings.shape}")
    logger.info(f"Config: coarse_res={coarse_res}, sub_res={sub_res}")
    
    # Run flat Leiden at all resolutions (for zoom navigation)
    logger.info("Running flat Leiden at all resolutions...")
    labels_by_res = {}
    for res in RESOLUTIONS_FULL:
        labels, mod = leiden_clustering(embeddings, resolution=res, k=K_NEIGHBORS)
        labels_by_res[res] = labels
        n_clusters = len(np.unique(labels[labels != -1]))
        logger.info(f"  Flat res={res}: {n_clusters} clusters, modularity={mod:.4f}")
    
    # Run hierarchical Leiden (validated config)
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=coarse_res, sub_res=sub_res, k=K_NEIGHBORS)
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    logger.info(f"  Hierarchical: {n_coarse} coarse -> {n_fine} fine clusters")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save flat resolution labels
    for res in RESOLUTIONS_FULL:
        np.save(output_dir / f"labels_res_{res}.npy", labels_by_res[res].astype(np.int32))
    
    # Save hierarchical labels
    np.save(output_dir / f"labels_coarse_{coarse_res}.npy", coarse_labels.astype(np.int32))
    # Also save as labels_coarse_0.5.npy for ProductMapLoader compatibility
    np.save(output_dir / "labels_coarse_0.5.npy", coarse_labels.astype(np.int32))
    np.save(output_dir / "labels_hierarchical_best.npy", hierarchical_labels.astype(np.int32))
    
    # Build cluster metadata for flat resolutions
    cluster_metadata = {}
    for res in RESOLUTIONS_FULL:
        cluster_metadata[f"res_{res}"] = compute_cluster_metadata(labels_by_res[res], metadata)
    
    # Hierarchical metadata
    cluster_metadata['hierarchical'] = compute_cluster_metadata(hierarchical_labels, metadata)
    cluster_metadata['coarse'] = compute_cluster_metadata(coarse_labels, metadata)
    
    with open(output_dir / "cluster_metadata.json", 'w') as f:
        json.dump(cluster_metadata, f, indent=2)
    
    # Build decision clusters (for fast decision-to-cluster lookup)
    logger.info("Building decision clusters...")
    decision_clusters = {}
    for i, m in enumerate(metadata):
        decision_clusters[m['decision_id']] = {}
        for res in RESOLUTIONS_FULL:
            decision_clusters[m['decision_id']][f"res_{res}"] = int(labels_by_res[res][i])
        decision_clusters[m['decision_id']]["hierarchical"] = int(hierarchical_labels[i])
        decision_clusters[m['decision_id']][f"coarse_{coarse_res}"] = int(coarse_labels[i])
    
    with open(output_dir / "decision_clusters.json", 'w') as f:
        json.dump(decision_clusters, f, indent=2)
    
    # Build zoom mappings
    zoom_mappings = build_zoom_mappings(labels_by_res)
    
    # Add hierarchical zoom mappings
    child_to_parent = {}
    for fine_id in np.unique(hierarchical_labels[hierarchical_labels != -1]):
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    parent_to_children = defaultdict(list)
    for child, parent in child_to_parent.items():
        parent_to_children[parent].append(child)
    
    zoom_mappings[f"hierarchical_coarse_{coarse_res}_to_fine"] = {
        'parent_to_children': {str(k): v for k, v in parent_to_children.items()},
        'child_to_parent': {str(k): v for k, v in child_to_parent.items()},
    }
    
    with open(output_dir / "zoom_mappings.json", 'w') as f:
        json.dump(zoom_mappings, f, indent=2)
    
    # Build zoom coherence
    zoom_coherence = build_zoom_coherence(labels_by_res, metadata)
    
    # Add hierarchical zoom coherence
    parent_details = {}
    improvements = []
    for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < MIN_CLUSTER_SIZE:
            continue
        coarse_branches = [metadata[j].get('branch') for j in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        fine_labels_in_coarse = hierarchical_labels[coarse_indices]
        unique_fine = np.unique(fine_labels_in_coarse[fine_labels_in_coarse != -1])
        child_purities = []
        for fine_id in unique_fine:
            fine_mask = hierarchical_labels == fine_id
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < MIN_CLUSTER_SIZE:
                continue
            fine_branches = [metadata[j].get('branch') for j in fine_indices]
            fine_branches = [b for b in fine_branches if b and b != 'unknown' and b != 'null']
            if fine_branches:
                child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_purities),
            }
    
    zoom_coherence[f"hierarchical_coarse_{coarse_res}_to_fine"] = {
        'parent_details': parent_details,
        'overall': {
            'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
            'n_parents': len(parent_details),
        }
    }
    
    with open(output_dir / "zoom_coherence.json", 'w') as f:
        json.dump(zoom_coherence, f, indent=2)
    
    # Compute local UMAP neighborhoods (zoom-conditioned)
    local_umap_metadata = compute_local_umap_neighborhoods(embeddings, coarse_labels, output_dir)
    
    # Build integration summary
    integration_summary = {
        'mode_id': mode_id,
        'description': config.get('description', ''),
        'embedding_type': config.get('embedding_type', 'center_projected_64dim'),
        'hierarchical_config': {'coarse_res': coarse_res, 'sub_res': sub_res},
        'n_decisions': len(metadata),
        'n_coarse_clusters': n_coarse,
        'n_fine_clusters': n_fine,
        'nesting': 1.0,  # Guaranteed by hierarchical Leiden construction
        'resolutions': RESOLUTIONS_FULL,
        'compressed_resolutions': RESOLUTIONS_COMPRESSED,
        'artifacts': {
            'cluster_metadata': f'legal_distance_modes/{mode_id}/cluster_metadata.json',
            'zoom_mappings': f'legal_distance_modes/{mode_id}/zoom_mappings.json',
            'zoom_coherence': f'legal_distance_modes/{mode_id}/zoom_coherence.json',
            'decision_clusters': f'legal_distance_modes/{mode_id}/decision_clusters.json',
            'local_umap': f'legal_distance_modes/{mode_id}/local_umap/',
        },
        'local_umap': local_umap_metadata,
        'evidence_tier': 'ACCEPTED',  # Based on 62k validation
        'validation_note': 'Hierarchical Leiden config (coarse=0.25, sub=3.0) validated at 62k scale (2000-2010) - PASS v26 success rule',
    }
    
    with open(output_dir / "integration_summary.json", 'w') as f:
        json.dump(integration_summary, f, indent=2)
    
    # Build hierarchical map results (for compatibility with existing loaders)
    hierarchical_map_results = {
        'mode_id': mode_id,
        'description': config.get('description', ''),
        'n_decisions': len(metadata),
        'resolutions': RESOLUTIONS_FULL,
        'n_resolutions': len(RESOLUTIONS_FULL),
        'cluster_counts': {f"res_{res}": len(np.unique(labels_by_res[res][labels_by_res[res] != -1])) for res in RESOLUTIONS_FULL},
        'cluster_metadata': cluster_metadata,
        'hierarchical_config': {'coarse_res': coarse_res, 'sub_res': sub_res},
        'n_coarse_clusters': n_coarse,
        'n_fine_clusters': n_fine,
    }
    
    with open(output_dir / "hierarchical_map_results.json", 'w') as f:
        json.dump(hierarchical_map_results, f, indent=2)
    
    logger.info(f"Artifacts saved to {output_dir}")
    return output_dir, integration_summary


def register_mode_in_registry(mode_id: str, integration_summary: dict, registry_path: Path, output_dir: Path):
    """Register the new mode in the map_mode_registry.py."""
    logger.info(f"Registering mode {mode_id} in registry...")
    
    # Load existing registry
    with open(registry_path) as f:
        registry_content = f.read()
    
    # Parse the MAP_MODES dict (simplified - we'll append to the file)
    # Better approach: generate the mode spec and update registry
    
    # For now, generate a spec that can be added
    mode_spec = {
        'mode_id': mode_id,
        'name': mode_id.replace('_', ' ').title(),
        'description': integration_summary['description'],
        'mode_type': 'hierarchical_leiden',
        'status': 'available',
        'is_default': False,
        'resolution_ladder': RESOLUTIONS_FULL,
        'artifacts': integration_summary['artifacts'],
        'metadata': {
            'n_decisions': integration_summary['n_decisions'],
            'n_coarse_clusters': integration_summary['n_coarse_clusters'],
            'n_fine_clusters': integration_summary['n_fine_clusters'],
            'nesting_score': 1.0,
            'hierarchical_config': integration_summary['hierarchical_config'],
            'evidence_tier': 'ACCEPTED',
            'validation_note': integration_summary['validation_note'],
        },
        'legal_distance_config': {
            'type': 'dense_embedding_hierarchical_leiden',
            'config': integration_summary['hierarchical_config']
        },
    }
    
    spec_path = output_dir / "map_mode_spec.json"
    with open(spec_path, 'w') as f:
        json.dump(mode_spec, f, indent=2)
    
    logger.info(f"Mode spec saved to {spec_path} (manual registry update needed)")
    return mode_spec


def main():
    parser = argparse.ArgumentParser(description='Build 174k hierarchical Leiden artifacts for dense embeddings')
    parser.add_argument('--metadata', type=Path, required=True, help='Path to 174k metadata JSON')
    parser.add_argument('--embedding-dir', type=Path, help='Directory with year-split embeddings (center_projected_64dim_YYYY.npy)')
    parser.add_argument('--embedding-file', type=Path, help='Single 174k embedding file (alternative to --embedding-dir)')
    parser.add_argument('--output-dir', type=Path, required=True, help='Output directory for artifacts')
    parser.add_argument('--mode-id', type=str, default='center_projected_64dim_hierarchical_174k', help='Mode ID')
    parser.add_argument('--coarse-res', type=float, default=DEFAULT_COARSE_RES, help='Coarse resolution')
    parser.add_argument('--sub-res', type=float, default=DEFAULT_SUB_RES, help='Sub-resolution')
    parser.add_argument('--description', type=str, 
                        default='Hierarchical Leiden on center_projected_64dim (language-debiased dense embeddings). coarse=0.25, sub=3.0 validated at 62k scale - PASS v26 success rule.',
                        help='Mode description')
    parser.add_argument('--registry', type=Path, default=Path('fractal_map/hierarchical/map_mode_registry.py'), help='Registry path')
    parser.add_argument('--skip-umap', action='store_true', help='Skip local UMAP computation')
    args = parser.parse_args()
    
    logger.info('=== Building 174k Dense Hierarchical Leiden Artifacts ===')
    logger.info(f'Timestamp: {datetime.now(timezone.utc).isoformat()}')
    logger.info(f'Mode ID: {args.mode_id}')
    logger.info(f'Output: {args.output_dir}')
    
    # Load metadata
    metadata = load_metadata_174k(args.metadata)
    
    # Load embeddings
    if args.embedding_dir:
        embeddings = load_year_split_embeddings(args.embedding_dir)
    elif args.embedding_file:
        embeddings = load_dense_embeddings_174k(args.embedding_file)
    else:
        raise ValueError("Either --embedding-dir or --embedding-file required")
    
    # Align embeddings with metadata
    n = min(len(embeddings), len(metadata))
    if len(embeddings) != len(metadata):
        logger.warning(f"Embedding count ({len(embeddings)}) != metadata count ({len(metadata)}), using min: {n}")
    embeddings = embeddings[:n]
    metadata = metadata[:n]
    
    # Normalize embeddings
    embeddings = normalize(embeddings, norm='l2')
    
    # Config
    config = {
        'mode_id': args.mode_id,
        'description': args.description,
        'embedding_type': 'center_projected_64dim',
        'coarse_res': args.coarse_res,
        'sub_res': args.sub_res,
    }
    
    # Build artifacts
    output_dir, integration_summary = build_artifacts_174k(config, metadata, embeddings, args.output_dir)
    
    # Register in registry (generate spec)
    register_mode_in_registry(args.mode_id, integration_summary, args.registry, output_dir)
    
    logger.info('\n=== Build complete ===')
    logger.info(f'Mode: {args.mode_id}')
    logger.info(f'Artifacts: {output_dir}')
    logger.info(f'Decisions: {integration_summary["n_decisions"]}')
    logger.info(f'Coarse clusters: {integration_summary["n_coarse_clusters"]}')
    logger.info(f'Fine clusters: {integration_summary["n_fine_clusters"]}')
    logger.info(f'Nesting: 1.0 (guaranteed by hierarchical Leiden)')
    logger.info(f'Local UMAP clusters: {len(integration_summary.get("local_umap", {}))}')


if __name__ == '__main__':
    main()