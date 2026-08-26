#!/usr/bin/env python3
"""
Local UMAP experiments for zoom-conditioned neighborhoods.
Tests the fractal requirement: zoom should reveal more specific structure.
"""
import json
import numpy as np
from pathlib import Path
import umap
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_baseline():
    embeddings = np.load(BASELINE_DIR / "embeddings.npy")
    projection = np.load(BASELINE_DIR / "projection_2d.npy")
    with open(BASELINE_DIR / "metadata.json", 'r') as f:
        metadata = json.load(f)
    return embeddings, projection, metadata

def local_umap(embeddings, center_idx, n_neighbors_local=50, n_components=2, 
               n_neighbors_umap=15, min_dist=0.1, metric='cosine', random_state=42):
    """Compute local UMAP around a center point."""
    # Find k nearest neighbors of center
    from sklearn.neighbors import NearestNeighbors
    if metric == 'cosine':
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = embeddings / norms
        nn = NearestNeighbors(n_neighbors=n_neighbors_local, metric='cosine')
        nn.fit(normalized)
        distances, indices = nn.kneighbors(normalized[center_idx:center_idx+1])
    else:
        nn = NearestNeighbors(n_neighbors=n_neighbors_local, metric=metric)
        nn.fit(embeddings)
        distances, indices = nn.kneighbors(embeddings[center_idx:center_idx+1])
    
    local_indices = indices[0]
    local_embeddings = embeddings[local_indices]
    
    # Compute UMAP on local neighborhood
    reducer = umap.UMAP(
        n_neighbors=min(n_neighbors_umap, len(local_indices)-1),
        min_dist=min_dist,
        n_components=n_components,
        metric=metric,
        random_state=random_state
    )
    local_projection = reducer.fit_transform(local_embeddings)
    
    return local_projection, local_indices, reducer

def multi_scale_umap(embeddings, n_neighbors_list=[5, 10, 15, 30, 50, 100]):
    """Compute UMAP at multiple neighborhood scales (global)."""
    results = {}
    for n_nbrs in n_neighbors_list:
        logger.info(f"Global UMAP with n_neighbors={n_nbrs}")
        reducer = umap.UMAP(
            n_neighbors=n_nbrs,
            min_dist=0.1,
            n_components=2,
            metric='cosine',
            random_state=42
        )
        projection = reducer.fit_transform(embeddings)
        results[f"n_neighbors_{n_nbrs}"] = {
            'projection': projection.tolist(),
            'n_neighbors': n_nbrs
        }
    return results

def zoom_into_cluster(embeddings, cluster_labels, cluster_id, n_neighbors_umap=15):
    """Zoom into a specific cluster and compute local UMAP."""
    cluster_mask = np.array(cluster_labels) == cluster_id
    cluster_indices = np.where(cluster_mask)[0]
    cluster_embeddings = embeddings[cluster_mask]
    
    if len(cluster_embeddings) < 10:
        logger.warning(f"Cluster {cluster_id} too small ({len(cluster_embeddings)} points)")
        return None
    
    logger.info(f"Zooming into cluster {cluster_id} with {len(cluster_embeddings)} points")
    reducer = umap.UMAP(
        n_neighbors=min(n_neighbors_umap, len(cluster_embeddings)-1),
        min_dist=0.1,
        n_components=2,
        metric='cosine',
        random_state=42
    )
    local_projection = reducer.fit_transform(cluster_embeddings)
    
    return {
        'cluster_id': cluster_id,
        'size': len(cluster_embeddings),
        'projection': local_projection.tolist(),
        'global_indices': cluster_indices.tolist()
    }

def hierarchical_umap(embeddings, cluster_hierarchy):
    """Compute UMAP at each level of a cluster hierarchy."""
    results = {}
    for level_name, labels in cluster_hierarchy.items():
        unique_labels = np.unique(labels)
        level_results = {}
        for label in unique_labels:
            if label == -1:  # Skip noise
                continue
            zoom_result = zoom_into_cluster(embeddings, labels, label)
            if zoom_result:
                level_results[f"cluster_{label}"] = zoom_result
        results[level_name] = level_results
    return results

def save_results(results, name):
    output_path = OUTPUT_DIR / f"{name}.json"
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
    with open(output_path, 'w') as f:
        json.dump(convert(results), f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {name} to {output_path}")

def main():
    logger.info("Starting local/zoom UMAP experiments")
    embeddings, global_projection, metadata = load_baseline()
    
    # 1. Multi-scale global UMAP
    logger.info("=" * 50)
    logger.info("Multi-scale Global UMAP")
    multiscale_results = multi_scale_umap(embeddings)
    save_results(multiscale_results, "multiscale_global_umap")
    
    # 2. Load Leiden clustering results for hierarchical zoom
    with open(OUTPUT_DIR / "leiden_multi_resolution.json", 'r') as f:
        leiden_results = json.load(f)
    
    # Build cluster hierarchy from Leiden results
    cluster_hierarchy = {}
    for key, result in leiden_results.items():
        cluster_hierarchy[key] = result['labels']
    
    # 3. Hierarchical zoom UMAP
    logger.info("=" * 50)
    logger.info("Hierarchical Zoom UMAP")
    hierarchical_results = hierarchical_umap(embeddings, cluster_hierarchy)
    save_results(hierarchical_results, "hierarchical_zoom_umap")
    
    # 4. Local UMAP around specific points (sample)
    logger.info("=" * 50)
    logger.info("Local UMAP around sample points")
    local_results = {}
    # Sample diverse points: one from each language
    lang_indices = {'de': [], 'fr': [], 'it': []}
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in lang_indices and len(lang_indices[lang]) < 3:
            lang_indices[lang].append(i)
    
    for lang, indices in lang_indices.items():
        for idx in indices:
            local_proj, local_indices, _ = local_umap(embeddings, idx, n_neighbors_local=50)
            local_results[f"local_{lang}_{idx}"] = {
                'center_idx': idx,
                'language': lang,
                'projection': local_proj.tolist(),
                'neighbor_indices': local_indices.tolist()
            }
    
    save_results(local_results, "local_umap_samples")
    
    logger.info("Local/zoom UMAP experiments complete")

if __name__ == "__main__":
    main()