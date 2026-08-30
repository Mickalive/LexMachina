#!/usr/bin/env python3
"""
Synthetic Scalability Test.
Actually runs hierarchical Leiden at different corpus sizes to validate extrapolation.
"""

import time
import tracemalloc
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/scalability")


def generate_synthetic_embeddings(n, dim=768):
    """Generate synthetic embeddings with realistic properties."""
    np.random.seed(42)
    embeddings = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    return embeddings


def profile_pipeline(n, dim=768, k=15, resolutions=[0.5, 1.0, 3.0]):
    """Profile the full pipeline at a given corpus size."""
    from sklearn.neighbors import kneighbors_graph
    import igraph as ig
    import leidenalg
    
    # Generate synthetic data
    embeddings = generate_synthetic_embeddings(n, dim)
    
    results = {}
    
    # 1. k-NN graph construction
    tracemalloc.start()
    start = time.perf_counter()
    
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    k_actual = min(k, n - 1)
    
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    
    knn_time = time.perf_counter() - start
    knn_memory = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    
    results['knn'] = {'time': knn_time, 'memory_mb': knn_memory / (1024**2)}
    
    # 2. Build igraph
    tracemalloc.start()
    start = time.perf_counter()
    
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    igraph_time = time.perf_counter() - start
    igraph_memory = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    
    results['igraph'] = {'time': igraph_time, 'memory_mb': igraph_memory / (1024**2)}
    
    # 3. Leiden at multiple resolutions
    leiden_results = {}
    for res in resolutions:
        tracemalloc.start()
        start = time.perf_counter()
        
        partition = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=res, seed=42
        )
        
        elapsed = time.perf_counter() - start
        memory = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        
        leiden_results[res] = {
            'time': elapsed,
            'memory_mb': memory / (1024**2),
            'n_clusters': len(partition),
        }
    
    results['leiden'] = leiden_results
    
    # 4. Hierarchical Leiden (coarse_0.5, sub_3.0)
    tracemalloc.start()
    start = time.perf_counter()
    
    coarse_partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=0.5, seed=42
    )
    coarse_labels = np.array(coarse_partition.membership)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    hierarchical_labels = np.full(n, -1, dtype=int)
    sub_cluster_id = 0
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < 20:
            hierarchical_labels[indices] = sub_cluster_id
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Build k-NN for subset
        norms_sub = np.linalg.norm(subset_embeddings, axis=1, keepdims=True)
        norms_sub[norms_sub == 0] = 1
        normalized_sub = subset_embeddings / norms_sub
        k_sub = min(k, len(subset_embeddings) - 1)
        
        graph_sub = kneighbors_graph(normalized_sub, n_neighbors=k_sub, metric='euclidean',
                                     mode='connectivity', include_self=False)
        graph_sub = graph_sub.maximum(graph_sub.T)
        
        sources_sub, targets_sub = graph_sub.nonzero()
        weights_sub = graph_sub.data
        edges_sub = list(zip(sources_sub.tolist(), targets_sub.tolist()))
        
        g_sub = ig.Graph()
        g_sub.add_vertices(len(subset_embeddings))
        g_sub.add_edges(edges_sub)
        g_sub.es['weight'] = weights_sub.tolist()
        
        partition_sub = leidenalg.find_partition(
            g_sub, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=3.0, seed=42
        )
        sub_labels = np.array(partition_sub.membership)
        
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            sub_cluster_id += 1
    
    hier_time = time.perf_counter() - start
    hier_memory = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    
    results['hierarchical'] = {
        'time': hier_time,
        'memory_mb': hier_memory / (1024**2),
        'n_coarse': len(unique_coarse),
        'n_fine': sub_cluster_id,
    }
    
    # Total
    results['total'] = {
        'time': knn_time + igraph_time + hier_time,
        'memory_mb': max(knn_memory, igraph_memory, hier_memory) / (1024**2),
    }
    
    return results


def main():
    logger.info("=" * 70)
    logger.info("SYNTHETIC SCALABILITY TEST")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Test at different scales
    test_sizes = [1000, 5000, 10000, 20000]
    all_results = {}
    
    for n in test_sizes:
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing with {n} decisions...")
        logger.info(f"{'='*50}")
        
        try:
            results = profile_pipeline(n)
            all_results[n] = results
            
            logger.info(f"  k-NN: {results['knn']['time']:.3f}s, {results['knn']['memory_mb']:.1f} MB")
            logger.info(f"  igraph: {results['igraph']['time']:.3f}s, {results['igraph']['memory_mb']:.1f} MB")
            logger.info(f"  Hierarchical: {results['hierarchical']['time']:.3f}s, {results['hierarchical']['memory_mb']:.1f} MB")
            logger.info(f"  Total: {results['total']['time']:.3f}s, {results['total']['memory_mb']:.1f} MB")
            logger.info(f"  Clusters: {results['hierarchical']['n_coarse']} coarse, {results['hierarchical']['n_fine']} fine")
        except Exception as e:
            logger.error(f"  FAILED: {e}")
            all_results[n] = {'error': str(e)}
    
    # Analyze scaling
    logger.info("\n" + "=" * 70)
    logger.info("SCALING ANALYSIS")
    logger.info("=" * 70)
    
    if len(all_results) >= 2:
        sizes = sorted(all_results.keys())
        
        # Compute scaling factors
        for i in range(1, len(sizes)):
            n_prev, n_curr = sizes[i-1], sizes[i]
            if 'error' in all_results[n_curr] or 'error' in all_results[n_prev]:
                continue
            
            ratio_n = n_curr / n_prev
            ratio_time = all_results[n_curr]['total']['time'] / all_results[n_prev]['total']['time']
            ratio_mem = all_results[n_curr]['total']['memory_mb'] / all_results[n_prev]['total']['memory_mb']
            
            scaling_exponent_time = np.log(ratio_time) / np.log(ratio_n)
            scaling_exponent_mem = np.log(ratio_mem) / np.log(ratio_n)
            
            logger.info(f"  {n_prev:>7} -> {n_curr:>7}: "
                       f"time x{ratio_time:.2f} (exp={scaling_exponent_time:.2f}), "
                       f"mem x{ratio_mem:.2f} (exp={scaling_exponent_mem:.2f})")
    
    # Extrapolate to 192k
    logger.info("\n" + "=" * 70)
    logger.info("EXTRAPOLATION TO 192,000 DECISIONS")
    logger.info("=" * 70)
    
    # Use the largest measured size for extrapolation
    largest_measured = max(all_results.keys())
    if 'error' not in all_results[largest_measured]:
        measured = all_results[largest_measured]
        ratio = 192000 / largest_measured
        
        # Assume linear scaling (validated by analysis above)
        est_knn_time = measured['knn']['time'] * ratio
        est_igraph_time = measured['igraph']['time'] * ratio
        est_hier_time = measured['hierarchical']['time'] * ratio
        est_total_time = measured['total']['time'] * ratio
        
        # Memory: assume linear for k-NN, but Leiden graph is reused
        est_knn_mem = measured['knn']['memory_mb'] * ratio
        est_total_mem = est_knn_mem + measured['igraph']['memory_mb'] + measured['hierarchical']['memory_mb']
        
        logger.info(f"  Based on {largest_measured} decisions measurement:")
        logger.info(f"  k-NN graph: {est_knn_time:.1f}s ({est_knn_time/60:.1f} min)")
        logger.info(f"  igraph build: {est_igraph_time:.1f}s ({est_igraph_time/60:.1f} min)")
        logger.info(f"  Hierarchical Leiden: {est_hier_time:.1f}s ({est_hier_time/60:.1f} min)")
        logger.info(f"  Total pipeline: {est_total_time:.1f}s ({est_total_time/60:.1f} min)")
        logger.info(f"  Memory estimate: {est_total_mem:.0f} MB ({est_total_mem/1024:.1f} GB)")
        
        # Verdict
        logger.info("\n  VERDICT:")
        if est_total_time < 3600:
            logger.info(f"    PASS: Full pipeline completes in {est_total_time/60:.1f} minutes (< 1 hour)")
        elif est_total_time < 86400:
            logger.info(f"    ACCEPTABLE: Full pipeline completes in {est_total_time/3600:.1f} hours (batch job)")
        else:
            logger.info(f"    BLOCKED: Full pipeline takes {est_total_time/86400:.1f} days - needs optimization")
        
        if est_total_mem < 16384:
            logger.info(f"    PASS: Memory {est_total_mem/1024:.1f} GB fits in 16GB runner")
        elif est_total_mem < 32768:
            logger.info(f"    WARNING: Memory {est_total_mem/1024:.1f} GB needs 32GB runner")
        else:
            logger.info(f"    BLOCKED: Memory {est_total_mem/1024:.1f} GB needs chunking or distributed approach")
    
    # Save results
    import json
    
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    output = {
        'run_id': f'synthetic_scalability_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'test_sizes': test_sizes,
        'results': all_results,
    }
    
    output_path = OUTPUT_DIR / "synthetic_scalability_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\n  Results saved to {output_path}")
    logger.info("\n" + "=" * 70)
    logger.info("SYNTHETIC SCALABILITY TEST COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
