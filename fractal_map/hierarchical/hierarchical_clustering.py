#!/usr/bin/env python3
"""
Hierarchical clustering experiments for fractal-map lane.
Tests multiple hierarchical clustering approaches on the baseline embeddings.
"""
import json
import numpy as np
from pathlib import Path
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
import hdbscan
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_baseline():
    """Load baseline embeddings and metadata."""
    embeddings = np.load(BASELINE_DIR / "embeddings.npy")
    projection = np.load(BASELINE_DIR / "projection_2d.npy")
    with open(BASELINE_DIR / "metadata.json", 'r') as f:
        metadata = json.load(f)
    logger.info(f"Loaded embeddings: {embeddings.shape}, projection: {projection.shape}")
    return embeddings, projection, metadata

def hierarchical_agglomerative(embeddings, n_clusters_list=[10, 20, 50, 100], linkage='ward'):
    """Test agglomerative clustering at multiple resolutions."""
    results = {}
    for n_clusters in n_clusters_list:
        logger.info(f"Agglomerative clustering: n_clusters={n_clusters}, linkage={linkage}")
        # For cosine metric, use average linkage; ward requires euclidean
        if linkage == 'ward':
            clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
        else:
            clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage, metric='cosine')
        labels = clustering.fit_predict(embeddings)
        
        # Compute silhouette score
        sil = silhouette_score(embeddings, labels, metric='cosine')
        logger.info(f"  Silhouette score (cosine): {sil:.4f}")
        
        # Cluster sizes
        unique, counts = np.unique(labels, return_counts=True)
        cluster_sizes = dict(zip(unique.tolist(), counts.tolist()))
        
        results[n_clusters] = {
            'labels': labels.tolist(),
            'silhouette_cosine': sil,
            'cluster_sizes': cluster_sizes,
            'n_clusters': n_clusters,
            'linkage': linkage
        }
    return results

def hdbscan_clustering(embeddings, min_cluster_size=5, min_samples=None, cluster_selection_epsilon=0.0):
    """HDBSCAN for density-based hierarchical clustering.
    Normalize embeddings for cosine similarity via Euclidean distance.
    """
    logger.info(f"HDBSCAN: min_cluster_size={min_cluster_size}, min_samples={min_samples}")
    # Normalize embeddings for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized_embeddings = embeddings / norms
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon,
        metric='euclidean',  # Use euclidean on normalized = cosine
        cluster_selection_method='eom',  # Excess of Mass
        prediction_data=True
    )
    labels = clusterer.fit_predict(normalized_embeddings)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = np.sum(labels == -1)
    logger.info(f"  Clusters found: {n_clusters}, Noise points: {n_noise}")
    
    # Get hierarchy
    condensed_tree = clusterer.condensed_tree_
    
    # Compute silhouette (excluding noise) - use normalized embeddings
    mask = labels != -1
    if np.sum(mask) > 1:
        sil = silhouette_score(normalized_embeddings[mask], labels[mask], metric='euclidean')
        logger.info(f"  Silhouette score (euclidean on normalized, excl noise): {sil:.4f}")
    else:
        sil = None
    
    unique, counts = np.unique(labels[labels != -1], return_counts=True)
    cluster_sizes = dict(zip(unique.tolist(), counts.tolist()))
    
    return {
        'labels': labels.tolist(),
        'n_clusters': n_clusters,
        'n_noise': int(n_noise),
        'silhouette_cosine': sil,
        'cluster_sizes': cluster_sizes,
        'probabilities': clusterer.probabilities_.tolist(),
        'outlier_scores': clusterer.outlier_scores_.tolist()
    }

def multi_resolution_hdbscan(embeddings):
    """Run HDBSCAN at multiple min_cluster_size values for multi-resolution."""
    results = {}
    for min_size in [5, 10, 20, 30, 50]:
        result = hdbscan_clustering(embeddings, min_cluster_size=min_size)
        results[f"min_cluster_size_{min_size}"] = result
    return results

def analyze_cluster_coherence(labels, metadata, embeddings):
    """Analyze cluster coherence by metadata (language, legal_area, year)."""
    labels = np.array(labels)
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels != -1]  # Exclude noise
    
    coherence = {}
    for label in unique_labels:
        mask = labels == label
        cluster_meta = [metadata[i] for i in np.where(mask)[0]]
        
        # Language distribution
        langs = [m['language'] for m in cluster_meta if m['language']]
        lang_dist = {k: langs.count(k) for k in set(langs)}
        
        # Legal area distribution
        areas = [m['legal_area'] for m in cluster_meta if m['legal_area']]
        area_dist = {k: areas.count(k) for k in set(areas)}
        
        # Year distribution
        years = [m['year'] for m in cluster_meta if m['year']]
        year_dist = {k: years.count(k) for k in set(years)}
        
        # Chamber distribution
        chambers = [m['chamber'] for m in cluster_meta if m['chamber']]
        chamber_dist = {k: chambers.count(k) for k in set(chambers)}
        
        coherence[int(label)] = {
            'size': int(np.sum(mask)),
            'language_dist': lang_dist,
            'legal_area_dist': area_dist,
            'year_dist': year_dist,
            'chamber_dist': chamber_dist,
            'dominant_language': max(lang_dist, key=lang_dist.get) if lang_dist else None,
            'dominant_area': max(area_dist, key=area_dist.get) if area_dist else None,
        }
    return coherence

def save_results(results, name):
    """Save clustering results."""
    output_path = OUTPUT_DIR / f"{name}.json"
    # Convert numpy types to native Python
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
    logger.info("Starting hierarchical clustering experiments")
    embeddings, projection, metadata = load_baseline()
    
    # 1. Agglomerative clustering at multiple resolutions
    logger.info("=" * 50)
    logger.info("Agglomerative Clustering (multiple resolutions)")
    agg_results = hierarchical_agglomerative(embeddings, n_clusters_list=[10, 20, 50, 100, 200], linkage='average')
    save_results(agg_results, "agglomerative_multi_resolution")
    
    # Analyze coherence for each resolution
    for n_clusters, result in agg_results.items():
        coherence = analyze_cluster_coherence(result['labels'], metadata, embeddings)
        result['coherence'] = coherence
    save_results(agg_results, "agglomerative_multi_resolution_with_coherence")
    
    # 2. HDBSCAN at multiple resolutions
    logger.info("=" * 50)
    logger.info("HDBSCAN Multi-resolution")
    hdbscan_results = multi_resolution_hdbscan(embeddings)
    save_results(hdbscan_results, "hdbscan_multi_resolution")
    
    # Analyze coherence for HDBSCAN
    for key, result in hdbscan_results.items():
        coherence = analyze_cluster_coherence(result['labels'], metadata, embeddings)
        result['coherence'] = coherence
    save_results(hdbscan_results, "hdbscan_multi_resolution_with_coherence")
    
    # 3. Single best HDBSCAN (min_cluster_size=10) for detailed analysis
    logger.info("=" * 50)
    logger.info("Detailed HDBSCAN analysis (min_cluster_size=10)")
    best_hdbscan = hdbscan_clustering(embeddings, min_cluster_size=10)
    best_hdbscan['coherence'] = analyze_cluster_coherence(best_hdbscan['labels'], metadata, embeddings)
    save_results(best_hdbscan, "hdbscan_detailed")
    
    logger.info("Hierarchical clustering experiments complete")

if __name__ == "__main__":
    main()