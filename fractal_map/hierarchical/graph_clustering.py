#!/usr/bin/env python3
"""
Multi-resolution graph clustering (Leiden/Louvain) for fractal-map lane.
Builds k-NN graph on embeddings and applies Leiden at multiple resolutions.
"""
import json
import numpy as np
from pathlib import Path
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

def build_knn_graph(embeddings, k=15, metric='cosine'):
    """Build k-NN graph using sklearn's kneighbors_graph."""
    from sklearn.neighbors import kneighbors_graph
    logger.info(f"Building k-NN graph with k={k}, metric={metric}")
    # Normalize for cosine
    if metric == 'cosine':
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings = embeddings / norms
        metric = 'euclidean'
    
    # kneighbors_graph with mode='distance' returns distances
    # We want connectivity graph with weights
    graph = kneighbors_graph(embeddings, n_neighbors=k, metric=metric, mode='connectivity', include_self=False)
    # Make symmetric
    graph = graph.maximum(graph.T)
    logger.info(f"Graph shape: {graph.shape}, nnz: {graph.nnz}")
    return graph

def leiden_clustering(graph, resolution=1.0, random_state=42):
    """Run Leiden clustering using igraph/leidenalg."""
    try:
        import igraph as ig
        import leidenalg
        
        # Convert scipy sparse to igraph
        sources, targets = graph.nonzero()
        weights = graph.data
        edges = list(zip(sources, targets))
        
        g = ig.Graph()
        g.add_vertices(graph.shape[0])
        g.add_edges(edges)
        g.es['weight'] = weights
        
        # Run Leiden
        partition = leidenalg.find_partition(
            g, 
            leidenalg.RBConfigurationVertexPartition,
            weights='weight',
            resolution_parameter=resolution,
            seed=random_state
        )
        
        labels = np.array(partition.membership)
        n_clusters = len(set(labels))
        modularity = partition.modularity
        
        logger.info(f"Leiden resolution={resolution}: {n_clusters} clusters, modularity={modularity:.4f}")
        return labels, modularity
    except ImportError:
        logger.warning("igraph/leidenalg not available, falling back to Louvain")
        return louvain_clustering(graph, resolution, random_state)

def louvain_clustering(graph, resolution=1.0, random_state=42):
    """Run Louvain clustering using community library."""
    try:
        import community as community_louvain
        import networkx as nx
        
        # Convert to networkx
        sources, targets = graph.nonzero()
        weights = graph.data
        
        G = nx.Graph()
        G.add_nodes_from(range(graph.shape[0]))
        for s, t, w in zip(sources, targets, weights):
            G.add_edge(s, t, weight=w)
        
        # Louvain
        partition = community_louvain.best_partition(G, resolution=resolution, random_state=random_state)
        labels = np.array([partition[i] for i in range(graph.shape[0])])
        n_clusters = len(set(labels))
        
        # Compute modularity
        modularity = community_louvain.modularity(partition, G, weight='weight')
        
        logger.info(f"Louvain resolution={resolution}: {n_clusters} clusters, modularity={modularity:.4f}")
        return labels, modularity
    except ImportError:
        logger.error("Neither leidenalg nor python-louvain available")
        raise

def multi_resolution_clustering(graph, resolutions=[0.25, 0.5, 1.0, 1.5, 2.0, 3.0]):
    """Run clustering at multiple resolutions."""
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(graph, resolution=res)
        results[f"resolution_{res}"] = {
            'labels': labels.tolist(),
            'n_clusters': int(len(set(labels))),
            'modularity': modularity,
            'resolution': res
        }
    return results

def analyze_cluster_coherence(labels, metadata):
    """Analyze cluster coherence by metadata."""
    labels = np.array(labels)
    unique_labels = np.unique(labels)
    
    coherence = {}
    for label in unique_labels:
        mask = labels == label
        cluster_meta = [metadata[i] for i in np.where(mask)[0]]
        
        langs = [m['language'] for m in cluster_meta if m['language']]
        lang_dist = {k: langs.count(k) for k in set(langs)}
        
        areas = [m['legal_area'] for m in cluster_meta if m['legal_area']]
        area_dist = {k: areas.count(k) for k in set(areas)}
        
        years = [m['year'] for m in cluster_meta if m['year']]
        year_dist = {k: years.count(k) for k in set(years)}
        
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
    logger.info("Starting multi-resolution graph clustering")
    embeddings, projection, metadata = load_baseline()
    
    # Build k-NN graph
    graph = build_knn_graph(embeddings, k=15, metric='cosine')
    
    # Multi-resolution Leiden/Louvain
    logger.info("=" * 50)
    logger.info("Multi-resolution Graph Clustering")
    graph_results = multi_resolution_clustering(graph, resolutions=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0])
    
    # Analyze coherence
    for key, result in graph_results.items():
        result['coherence'] = analyze_cluster_coherence(result['labels'], metadata)
    
    save_results(graph_results, "leiden_multi_resolution")
    
    # Also test different k values at a fixed resolution
    logger.info("=" * 50)
    logger.info("Testing different k values at resolution=1.0")
    k_results = {}
    for k in [5, 10, 15, 20, 30, 50]:
        g = build_knn_graph(embeddings, k=k, metric='cosine')
        labels, modularity = leiden_clustering(g, resolution=1.0)
        k_results[f"k_{k}"] = {
            'labels': labels.tolist(),
            'n_clusters': int(len(set(labels))),
            'modularity': modularity,
            'k': k
        }
        k_results[f"k_{k}"]['coherence'] = analyze_cluster_coherence(labels, metadata)
    
    save_results(k_results, "leiden_k_sensitivity")
    
    logger.info("Graph clustering experiments complete")

if __name__ == "__main__":
    main()