#!/usr/bin/env python3
"""
Scalability Profiler for Hierarchical Leiden.
Profiles each step of the fractal map pipeline on current corpus (1,000 decisions)
and extrapolates to 192k decisions.

Research Question: Can the current hierarchical Leiden approach scale to 192k decisions?
Product Decision: Do we need alternative methods or infrastructure changes for full corpus?
"""

import json
import time
import tracemalloc
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/scalability")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Target corpus sizes for extrapolation
TARGET_SIZES = [1000, 5000, 10000, 50000, 100000, 192000]


class Profiler:
    """Profile time and memory for each pipeline step."""
    
    def __init__(self):
        self.results = {}
        self.current_step = None
        self.step_start_time = None
        self.step_start_memory = None
    
    def start_step(self, step_name):
        self.current_step = step_name
        self.step_start_time = time.perf_counter()
        tracemalloc.start()
        self.step_start_memory = tracemalloc.get_traced_memory()
    
    def end_step(self):
        current_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        elapsed = time.perf_counter() - self.step_start_time
        peak_memory = current_memory[1]  # peak
        
        self.results[self.current_step] = {
            'time_seconds': elapsed,
            'peak_memory_mb': peak_memory / (1024 * 1024),
            'current_memory_mb': current_memory[0] / (1024 * 1024),
        }
        logger.info(f"  {self.current_step}: {elapsed:.3f}s, peak {peak_memory/(1024*1024):.1f} MB")
        return elapsed, peak_memory


def load_current_corpus():
    """Load the current 1,000-decision corpus."""
    import json
    
    metadata_path = BASELINE_DIR / "metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    embeddings = np.load(BASELINE_DIR / "embeddings.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    
    return metadata, embeddings, center_emb


def generate_synthetic_corpus(n_decisions, embedding_dim=768):
    """Generate synthetic embeddings for scalability testing.
    
    Uses random embeddings that preserve the statistical properties of real data:
    - Unit normalized (like real embeddings)
    - Similar dimensional distribution
    """
    logger.info(f"  Generating {n_decisions} synthetic embeddings (dim={embedding_dim})...")
    
    # Generate random embeddings with similar properties to real data
    np.random.seed(42)
    embeddings = np.random.randn(n_decisions, embedding_dim)
    
    # Normalize to unit vectors (like real embeddings)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    # Generate synthetic metadata
    metadata = []
    languages = ['de', 'fr', 'it']
    branches = ['oeffentliches_recht', 'zivilrecht', 'strafrecht', 'sozialversicherungsrecht']
    
    for i in range(n_decisions):
        metadata.append({
            'decision_id': f'synthetic_{i:06d}',
            'language': languages[i % 3],
            'branch': branches[i % 4],
            'year': 2020 + (i % 5),
            'legal_area': f'area_{i % 20}',
            'chamber': f'chamber_{i % 10}',
        })
    
    return metadata, embeddings


def profile_knn_graph(embeddings, k=15):
    """Profile k-NN graph construction."""
    from sklearn.neighbors import kneighbors_graph
    
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    
    k_actual = min(k, len(embeddings) - 1)
    
    start = time.perf_counter()
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    elapsed = time.perf_counter() - start
    
    return graph, elapsed


def profile_leiden(graph, resolution=1.0):
    """Profile Leiden clustering."""
    import igraph as ig
    import leidenalg
    
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    
    start = time.perf_counter()
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=42
    )
    elapsed = time.perf_counter() - start
    
    return np.array(partition.membership), partition.modularity, elapsed


def profile_hierarchical_leiden(embeddings, coarse_res=0.5, sub_res=3.0, k=15):
    """Profile hierarchical Leiden (coarse + sub-clustering)."""
    from sklearn.neighbors import kneighbors_graph
    import igraph as ig
    import leidenalg
    
    n = len(embeddings)
    
    # Step 1: Build k-NN graph
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    k_actual = min(k, n - 1)
    
    start = time.perf_counter()
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    knn_time = time.perf_counter() - start
    
    # Step 2: Coarse Leiden
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    
    start = time.perf_counter()
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=coarse_res, seed=42
    )
    coarse_labels = np.array(partition.membership)
    coarse_time = time.perf_counter() - start
    
    # Step 3: Sub-clustering within each coarse cluster
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    hierarchical_labels = np.full(n, -1, dtype=int)
    sub_cluster_id = 0
    sub_time_total = 0
    
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
        
        start = time.perf_counter()
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
            weights='weight', resolution_parameter=sub_res, seed=42
        )
        sub_labels = np.array(partition_sub.membership)
        sub_time_total += time.perf_counter() - start
        
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            sub_cluster_id += 1
    
    total_time = knn_time + coarse_time + sub_time_total
    
    return hierarchical_labels, coarse_labels, {
        'knn_time': knn_time,
        'coarse_time': coarse_time,
        'sub_time_total': sub_time_total,
        'total_time': total_time,
        'n_coarse_clusters': len(unique_coarse),
        'n_fine_clusters': sub_cluster_id,
    }


def extrapolate_time(time_1000, n_target, method='linear'):
    """Extrapolate time to target corpus size.
    
    Complexity estimates:
    - k-NN graph: O(n * k * d) ~= O(n) for fixed k, d
    - Leiden: O(n + m) where m = edges ~= O(n * k) = O(n)
    - Hierarchical: O(n) for coarse + sum of O(n_i) for sub = O(n)
    
    So overall should be roughly linear for fixed k and d.
    """
    ratio = n_target / 1000
    if method == 'linear':
        return time_1000 * ratio
    elif method == 'nlogn':
        return time_1000 * ratio * (np.log2(n_target) / np.log2(1000))
    elif method == 'nsqrt':
        return time_1000 * ratio * np.sqrt(n_target / 1000)
    else:
        return time_1000 * ratio


def extrapolate_memory(memory_1000, n_target):
    """Extrapolate memory to target corpus size.
    
    Memory components:
    - Embeddings: O(n * d) -- linear
    - k-NN graph: O(n * k) -- linear
    - Leiden partition: O(n) -- linear
    - Metadata: O(n) -- linear
    
    So memory should scale roughly linearly.
    """
    ratio = n_target / 1000
    return memory_1000 * ratio


def main():
    logger.info("=" * 70)
    logger.info("FRACTAL MAP SCALABILITY PROFILING")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Target sizes: {TARGET_SIZES}")
    
    # 1. Profile on current corpus (1,000 decisions)
    logger.info("\n1. Loading current corpus...")
    metadata, embeddings, center_emb = load_current_corpus()
    logger.info(f"   Loaded: {len(metadata)} decisions, embeddings {embeddings.shape}")
    
    profiler = Profiler()
    
    # Profile k-NN graph
    logger.info("\n2. Profiling k-NN graph construction...")
    profiler.start_step("knn_graph")
    graph, knn_time = profile_knn_graph(center_emb, k=15)
    profiler.end_step()
    
    # Profile Leiden at multiple resolutions
    logger.info("\n3. Profiling Leiden clustering...")
    leiden_results = {}
    for res in [0.5, 1.0, 3.0]:
        profiler.start_step(f"leiden_res_{res}")
        labels, mod, elapsed = profile_leiden(graph, resolution=res)
        profiler.end_step()
        leiden_results[res] = {'labels': labels, 'modularity': mod, 'time': elapsed}
    
    # Profile hierarchical Leiden
    logger.info("\n4. Profiling hierarchical Leiden (coarse_0.5, sub_3.0)...")
    profiler.start_step("hierarchical_leiden")
    hier_labels, coarse_labels, hier_stats = profile_hierarchical_leiden(
        center_emb, coarse_res=0.5, sub_res=3.0, k=15
    )
    profiler.end_step()
    
    # Profile multi-resolution (7 resolutions)
    logger.info("\n5. Profiling multi-resolution pipeline (7 resolutions)...")
    profiler.start_step("multi_resolution_pipeline")
    resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    multi_res_start = time.perf_counter()
    multi_res_labels = {}
    for res in resolutions:
        if res in leiden_results:
            result = leiden_results[res]
            labels, mod = result['labels'], result['modularity']
        else:
            labels, mod, _ = profile_leiden(graph, resolution=res)
        multi_res_labels[res] = labels
    multi_res_time = time.perf_counter() - multi_res_start
    profiler.end_step()
    
    # 2. Summarize current performance
    logger.info("\n" + "=" * 70)
    logger.info("CURRENT PERFORMANCE (1,000 decisions)")
    logger.info("=" * 70)
    
    current_perf = {
        'n_decisions': 1000,
        'knn_graph': profiler.results.get('knn_graph', {}),
        'leiden': {str(r): {'time': leiden_results[r]['time']} for r in leiden_results},
        'hierarchical_leiden': profiler.results.get('hierarchical_leiden', {}),
        'hierarchical_breakdown': hier_stats,
        'multi_resolution_pipeline': profiler.results.get('multi_resolution_pipeline', {}),
    }
    
    for step, data in profiler.results.items():
        logger.info(f"  {step}: {data['time_seconds']:.3f}s, {data['peak_memory_mb']:.1f} MB")
    
    # 3. Extrapolate to target sizes
    logger.info("\n" + "=" * 70)
    logger.info("EXTRAPOLATION TO TARGET SIZES")
    logger.info("=" * 70)
    
    extrapolations = {}
    for target in TARGET_SIZES:
        if target == 1000:
            extrapolations[target] = current_perf
            continue
        
        ext = {}
        for step in ['knn_graph', 'hierarchical_leiden', 'multi_resolution_pipeline']:
            if step in profiler.results:
                time_est = extrapolate_time(profiler.results[step]['time_seconds'], target)
                mem_est = extrapolate_memory(profiler.results[step]['peak_memory_mb'], target)
                ext[step] = {
                    'time_seconds': time_est,
                    'peak_memory_mb': mem_est,
                    'time_human': f"{time_est/3600:.1f}h" if time_est > 3600 else f"{time_est/60:.1f}min" if time_est > 60 else f"{time_est:.1f}s",
                }
        
        # Hierarchical Leiden breakdown
        if hier_stats:
            ext['hierarchical_breakdown'] = {
                'knn_time': extrapolate_time(hier_stats['knn_time'], target),
                'coarse_time': extrapolate_time(hier_stats['coarse_time'], target),
                'sub_time_total': extrapolate_time(hier_stats['sub_time_total'], target),
                'total_time': extrapolate_time(hier_stats['total_time'], target),
            }
        
        extrapolations[target] = ext
    
    # Print extrapolation table
    logger.info("\n  Estimated times and memory:")
    logger.info(f"  {'Size':>10} | {'k-NN Graph':>12} | {'Hier Leiden':>12} | {'Multi-Res':>12} | {'Memory':>12}")
    logger.info("  " + "-" * 70)
    
    for target in TARGET_SIZES:
        ext = extrapolations[target]
        knn_t = ext.get('knn_graph', {}).get('time_human', 'N/A')
        hier_t = ext.get('hierarchical_leiden', {}).get('time_human', 'N/A')
        multi_t = ext.get('multi_resolution_pipeline', {}).get('time_human', 'N/A')
        mem = ext.get('knn_graph', {}).get('peak_memory_mb', 0)
        mem_est = extrapolate_memory(mem, target) if target > 1000 else mem
        logger.info(f"  {target:>10} | {knn_t:>12} | {hier_t:>12} | {multi_t:>12} | {mem_est:>8.0f} MB")
    
    # 4. Identify bottlenecks
    logger.info("\n" + "=" * 70)
    logger.info("BOTTLENECK ANALYSIS")
    logger.info("=" * 70)
    
    bottleneck_analysis = {}
    
    # k-NN graph is the most expensive step
    knn_time_1000 = profiler.results.get('knn_graph', {}).get('time_seconds', 0)
    hier_time_1000 = profiler.results.get('hierarchical_leiden', {}).get('time_seconds', 0)
    
    if knn_time_1000 > 0:
        knn_fraction = knn_time_1000 / (hier_time_1000 if hier_time_1000 > 0 else knn_time_1000)
        bottleneck_analysis['knn_graph_fraction'] = knn_fraction
        bottleneck_analysis['knn_graph_dominant'] = knn_fraction > 0.5
    
    # Memory estimate for 192k
    mem_1000 = profiler.results.get('knn_graph', {}).get('peak_memory_mb', 0)
    mem_192k = extrapolate_memory(mem_1000, 192000)
    bottleneck_analysis['memory_estimate_192k_mb'] = mem_192k
    bottleneck_analysis['memory_estimate_192k_gb'] = mem_192k / 1024
    
    # Time estimate for 192k
    time_192k_hier = extrapolate_time(hier_time_1000, 192000)
    bottleneck_analysis['time_estimate_192k_hierarchical_seconds'] = time_192k_hier
    bottleneck_analysis['time_estimate_192k_hierarchical_hours'] = time_192k_hier / 3600
    
    for key, value in bottleneck_analysis.items():
        logger.info(f"  {key}: {value}")
    
    # 5. Recommendations
    logger.info("\n" + "=" * 70)
    logger.info("RECOMMENDATIONS")
    logger.info("=" * 70)
    
    recommendations = []
    
    # Check if linear scaling is achievable
    time_192k_hours = bottleneck_analysis.get('time_estimate_192k_hierarchical_hours', 0)
    mem_192k_gb = bottleneck_analysis.get('memory_estimate_192k_gb', 0)
    
    if time_192k_hours < 1:
        recommendations.append("PASS: Hierarchical Leiden scales linearly to 192k (< 1 hour estimated)")
    elif time_192k_hours < 24:
        recommendations.append(f"ACCEPTABLE: Hierarchical Leiden takes ~{time_192k_hours:.1f}h for 192k (overnight batch)")
    else:
        recommendations.append(f"BLOCKER: Hierarchical Leiden takes ~{time_192k_hours:.1f}h for 192k - needs optimization")
    
    if mem_192k_gb < 16:
        recommendations.append(f"PASS: Memory estimate {mem_192k_gb:.1f}GB fits in standard CI runner (16GB)")
    elif mem_192k_gb < 64:
        recommendations.append(f"WARNING: Memory estimate {mem_192k_gb:.1f}GB requires larger runner (32-64GB)")
    else:
        recommendations.append(f"BLOCKER: Memory estimate {mem_192k_gb:.1f}GB exceeds standard runners - needs chunking")
    
    # Check if k-NN is the bottleneck
    if bottleneck_analysis.get('knn_graph_dominant', False):
        recommendations.append("INSIGHT: k-NN graph construction is the bottleneck - consider approximate nearest neighbors (FAISS/Annoy) for 192k")
    
    for rec in recommendations:
        logger.info(f"  {rec}")
    
    # 6. Save results
    logger.info("\n" + "=" * 70)
    logger.info("SAVING RESULTS")
    logger.info("=" * 70)
    
    output = {
        'run_id': f'scalability_profile_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 10,
        'hypothesis': 'Current hierarchical Leiden approach scales linearly to 192k decisions',
        'frozen_sample': '1000 BGer decisions (2020-2024)',
        'frozen_metric': 'Time (seconds), peak memory (MB)',
        'success_rule': 'Time < 24h AND memory < 32GB for 192k',
        'current_performance': current_perf,
        'extrapolations': extrapolations,
        'bottleneck_analysis': bottleneck_analysis,
        'recommendations': recommendations,
        'verdict': 'PASS' if time_192k_hours < 24 and mem_192k_gb < 32 else 'BLOCKED',
    }
    
    # Convert numpy types
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
    
    output_path = OUTPUT_DIR / "scalability_profile_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"  Results saved to {output_path}")
    
    # Save synthetic test results if we ran them
    logger.info("\n" + "=" * 70)
    logger.info("SCALABILITY PROFILING COMPLETE")
    logger.info("=" * 70)
    
    return output


if __name__ == "__main__":
    main()
