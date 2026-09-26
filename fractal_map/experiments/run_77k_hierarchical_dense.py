#!/usr/bin/env python3
"""
Fractal Map Lane — 77k Dense Embeddings Hierarchical Clustering Experiment

Tests hierarchical Leiden clustering on 77,169 decisions (years 2000-2012) 
with 768-dim dense embeddings. Evaluates:
- Multi-resolution clustering (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
- Zoom quality: branch purity improvement from coarse to fine
- Nesting score (hierarchical coherence)
- Compressed resolution ladder validity (NESTING_METRIC_DEFECT_v1)
- Scale dependency vs 12k and 1k results

Frozen hypothesis: Hierarchical Leiden on dense embeddings at 77k scale 
produces monotonic zoom refinement (branch purity improvement at each step)
and passes compressed 5-level ladder test.

Frozen metric: Zoom Quality Score (composite: purity_delta, meaningful_split_rate, stability, max_purity)
Success rule: Mean purity_delta > 0 across all transitions AND nesting_score >= 0.99
"""

import json
import numpy as np
import os
import sys
from pathlib import Path
from collections import defaultdict, Counter
import time

# Add project root to path
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

try:
    import igraph as ig
    import leidenalg as la
except ImportError:
    print("Installing igraph and leidenalg...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-igraph", "leidenalg"])
    import igraph as ig
    import leidenalg as la

from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from scipy.spatial.distance import pdist, squareform
from scipy.sparse import csr_matrix


# ============================================================
# CONFIGURATION (FROZEN BEFORE EXPERIMENT)
# ============================================================
FROZEN_CONFIG = {
    "run_id": "fractal_77k_hierarchical_dense_20260926",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "direction_version": 28,
    "lane": "fractal-map",
    "hypothesis": "Hierarchical Leiden on dense embeddings at 77k scale produces monotonic zoom refinement and passes compressed ladder test",
    "frozen_sample": "77,169 BGer decisions (years 2000-2012) with 768-dim center-projected dense embeddings",
    "frozen_metric": "Zoom Quality Score (composite: purity_delta, meaningful_split_rate, stability, max_purity)",
    "success_rule": "Mean purity_delta > 0 across all transitions AND nesting_score >= 0.99",
    "embedding_dir": "/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints",
    "years": list(range(2000, 2013)),
    "resolutions": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
    "compressed_resolutions": [0.25, 0.5, 1.0, 2.0, 3.0],
    "dropped_resolutions": [0.75, 1.5],
    "k_nn_graph": 30,  # k-NN graph for Leiden
    "random_seed": 42,
    "output_dir": "results/fractal_map/77k_hierarchical_dense",
}

# Ensure output directory
os.makedirs(FROZEN_CONFIG["output_dir"], exist_ok=True)

# ============================================================
# DATA LOADING
# ============================================================
def load_embeddings_and_metadata(config):
    """Load and concatenate embeddings and metadata for all years."""
    print(f"Loading embeddings for years {config['years']}...")
    
    all_embeddings = []
    all_metadata = []
    
    for year in config["years"]:
        emb_path = os.path.join(config["embedding_dir"], f"embeddings_{year}.npy")
        meta_path = os.path.join(config["embedding_dir"], f"metadata_{year}.json")
        
        embeddings = np.load(emb_path).astype(np.float32)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
        print(f"  {year}: {len(embeddings)} decisions, shape {embeddings.shape}")
    
    combined_embeddings = np.vstack(all_embeddings)
    print(f"\nTotal: {len(combined_embeddings)} decisions, shape {combined_embeddings.shape}")
    print(f"Metadata entries: {len(all_metadata)}")
    
    return combined_embeddings, all_metadata


# ============================================================
# K-NN GRAPH CONSTRUCTION
# ============================================================
def build_knn_graph(embeddings, k=30, metric='cosine'):
    """Build k-NN graph for Leiden clustering."""
    print(f"Building {k}-NN graph with {metric} distance...")
    n = len(embeddings)
    
    # Use cosine similarity (1 - cosine distance)
    if metric == 'cosine':
        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings_norm = embeddings / norms
        
        # Use sklearn for efficient k-NN
        nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
        nn.fit(embeddings_norm)
        distances, indices = nn.kneighbors(embeddings_norm)
        
        # Remove self-loops (first neighbor)
        indices = indices[:, 1:]
        distances = distances[:, 1:]
        
        # Convert to similarity
        similarities = 1 - distances
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    # Build edge list
    edges = []
    weights = []
    for i in range(n):
        for j, sim in zip(indices[i], similarities[i]):
            edges.append((i, int(j)))
            weights.append(float(sim))
    
    print(f"  Graph: {n} nodes, {len(edges)} edges")
    return edges, weights, n


def create_igraph(edges, weights, n):
    """Create igraph Graph from edges and weights."""
    g = ig.Graph()
    g.add_vertices(n)
    g.add_edges(edges)
    g.es['weight'] = weights
    return g


# ============================================================
# HIERARCHICAL LEIDEN CLUSTERING
# ============================================================
def run_leiden_at_resolution(graph, resolution, seed=42):
    """Run Leiden clustering at a specific resolution."""
    partition = la.find_partition(
        graph,
        la.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=resolution,
        seed=seed
    )
    return np.array(partition.membership)


def run_hierarchical_leiden(graph, resolutions, seed=42):
    """Run Leiden at multiple resolutions."""
    print(f"Running Leiden at {len(resolutions)} resolutions...")
    results = {}
    for res in resolutions:
        print(f"  Resolution {res}...")
        start = time.time()
        labels = run_leiden_at_resolution(graph, res, seed)
        elapsed = time.time() - start
        n_clusters = len(np.unique(labels))
        print(f"    -> {n_clusters} clusters in {elapsed:.2f}s")
        results[res] = labels
    return results


# ============================================================
# EVALUATION METRICS
# ============================================================
def compute_purity(labels, metadata, key='branch'):
    """Compute cluster purity for a given metadata key."""
    cluster_to_labels = defaultdict(list)
    for i, label in enumerate(labels):
        if i < len(metadata):
            cluster_to_labels[label].append(metadata[i].get(key))
    
    total = 0
    correct = 0
    for cluster, vals in cluster_to_labels.items():
        if not vals:
            continue
        counter = Counter(v for v in vals if v is not None)
        if not counter:
            continue
        majority = counter.most_common(1)[0][1]
        total += len(vals)
        correct += majority
    
    return correct / total if total > 0 else 0.0


def compute_nmi(labels1, labels2):
    """Compute Normalized Mutual Information between two clusterings."""
    return normalized_mutual_info_score(labels1, labels2, average_method='arithmetic')


def compute_nesting_score(coarse_labels, fine_labels):
    """
    Compute nesting score: fraction of fine clusters that are 
    proper subsets of a single coarse cluster.
    """
    # Map each fine cluster to its coarse cluster(s)
    fine_to_coarse = defaultdict(set)
    for i in range(len(fine_labels)):
        fine_to_coarse[fine_labels[i]].add(coarse_labels[i])
    
    # Count fine clusters that map to exactly one coarse cluster
    nested = sum(1 for coarse_set in fine_to_coarse.values() if len(coarse_set) == 1)
    total = len(fine_to_coarse)
    
    return nested / total if total > 0 else 0.0


def compute_transition_metrics(coarse_labels, fine_labels, metadata, key='branch'):
    """Compute detailed transition metrics between two resolution levels."""
    n_coarse = len(np.unique(coarse_labels))
    n_fine = len(np.unique(fine_labels))
    
    # Coarse cluster purities
    coarse_purities = {}
    for c in np.unique(coarse_labels):
        mask = coarse_labels == c
        coarse_purities[c] = compute_purity(coarse_labels[mask], [metadata[i] for i in np.where(mask)[0]], key)
    
    # Fine cluster purities
    fine_purities = {}
    for f in np.unique(fine_labels):
        mask = fine_labels == f
        fine_purities[f] = compute_purity(fine_labels[mask], [metadata[i] for i in np.where(mask)[0]], key)
    
    # Transition mapping
    coarse_to_fine = defaultdict(set)
    for i in range(len(coarse_labels)):
        coarse_to_fine[coarse_labels[i]].add(fine_labels[i])
    
    # Compute splits
    n_splits = 0
    n_unified = 0
    purity_deltas = []
    meaningful_splits = 0
    
    for c, fine_clusters in coarse_to_fine.items():
        coarse_pur = coarse_purities.get(c, 0)
        if len(fine_clusters) == 1:
            n_unified += 1
            fine_pur = fine_purities.get(list(fine_clusters)[0], 0)
            purity_deltas.append(fine_pur - coarse_pur)
            if fine_pur > coarse_pur + 0.01:  # meaningful improvement threshold
                meaningful_splits += 1
        else:
            n_splits += len(fine_clusters)
            fine_pur_mean = np.mean([fine_purities.get(f, 0) for f in fine_clusters])
            purity_deltas.append(fine_pur_mean - coarse_pur)
            # Check if any fine cluster has meaningful improvement
            for f in fine_clusters:
                if fine_purities.get(f, 0) > coarse_pur + 0.01:
                    meaningful_splits += 1
    
    split_rate = n_splits / n_coarse if n_coarse > 0 else 0
    meaningful_split_rate = meaningful_splits / n_splits if n_splits > 0 else 0
    mean_purity_delta = np.mean(purity_deltas) if purity_deltas else 0
    
    return {
        "n_coarse": n_coarse,
        "n_fine": n_fine,
        "n_splits": n_splits,
        "n_unified": n_unified,
        "split_rate": split_rate,
        "mean_purity_delta": mean_purity_delta,
        "meaningful_split_rate": meaningful_split_rate,
        "coarse_purity_overall": np.mean(list(coarse_purities.values())),
        "fine_purity_overall": np.mean(list(fine_purities.values())),
    }


def compute_zoom_quality_score(transition_metrics, finest_purity):
    """Compute composite zoom quality score."""
    # Components: mean_purity_delta (40%), meaningful_split_rate (30%), 
    # stability (10% - inverse of split_rate variance), finest_purity (20%)
    purity_delta_score = max(0, transition_metrics.get('mean_purity_delta', 0)) * 10  # scale
    split_score = transition_metrics.get('meaningful_split_rate', 0)
    stability_score = 1.0 - min(1.0, transition_metrics.get('split_rate', 0))  # lower split_rate = more stable
    purity_score = finest_purity
    
    composite = (0.4 * purity_delta_score + 
                 0.3 * split_score + 
                 0.1 * stability_score + 
                 0.2 * purity_score)
    return composite


# ============================================================
# MAIN EXPERIMENT
# ============================================================
def main():
    config = FROZEN_CONFIG
    
    # Load data
    embeddings, metadata = load_embeddings_and_metadata(config)
    n_decisions = len(embeddings)
    
    # Extract branch labels for evaluation
    branches = [m.get('branch', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    languages = [m.get('language', 'unknown') for m in metadata]
    
    print(f"\nBranch distribution: {Counter(branches).most_common()}")
    print(f"Legal area count: {len(set(legal_areas))}")
    print(f"Language distribution: {Counter(languages)}")
    
    # Build k-NN graph
    edges, weights, n = build_knn_graph(embeddings, k=config["k_nn_graph"])
    graph = create_igraph(edges, weights, n)
    
    # Run hierarchical Leiden
    all_labels = run_hierarchical_leiden(graph, config["resolutions"], config["random_seed"])
    
    # Save cluster labels
    for res, labels in all_labels.items():
        np.save(os.path.join(config["output_dir"], f"labels_res_{res}.npy"), labels)
    
    # Compute metrics at each resolution
    print("\nComputing resolution metrics...")
    resolution_metrics = {}
    for res in config["resolutions"]:
        labels = all_labels[res]
        n_clusters = len(np.unique(labels))
        branch_purity = compute_purity(labels, metadata, 'branch')
        legal_area_purity = compute_purity(labels, metadata, 'legal_area')
        language_purity = compute_purity(labels, metadata, 'language')
        
        resolution_metrics[res] = {
            "n_clusters": int(n_clusters),
            "branch_purity": float(branch_purity),
            "legal_area_purity": float(legal_area_purity),
            "language_purity": float(language_purity),
        }
        print(f"  res_{res}: {n_clusters} clusters, branch_purity={branch_purity:.4f}, "
              f"legal_area_purity={legal_area_purity:.4f}, language_purity={language_purity:.4f}")
    
    # Compute transitions
    print("\nComputing transition metrics...")
    transitions = {}
    sorted_res = sorted(config["resolutions"])
    for i in range(len(sorted_res) - 1):
        r1, r2 = sorted_res[i], sorted_res[i+1]
        trans_key = f"{r1}->{r2}"
        coarse = all_labels[r1]
        fine = all_labels[r2]
        
        trans = compute_transition_metrics(coarse, fine, metadata, 'branch')
        trans["coarse_resolution"] = r1
        trans["fine_resolution"] = r2
        trans["nesting_score"] = compute_nesting_score(coarse, fine)
        transitions[trans_key] = trans
        
        print(f"  {trans_key}: nesting={trans['nesting_score']:.4f}, "
              f"delta={trans['mean_purity_delta']:.4f}, "
              f"split_rate={trans['split_rate']:.4f}, "
              f"meaningful_split_rate={trans['meaningful_split_rate']:.4f}")
    
    # Overall nesting score (coarsest to finest)
    overall_nesting = compute_nesting_score(all_labels[sorted_res[0]], all_labels[sorted_res[-1]])
    print(f"\nOverall nesting score (res_{sorted_res[0]} -> res_{sorted_res[-1]}): {overall_nesting:.4f}")
    
    # Zoom quality score per transition and overall
    finest_labels = all_labels[sorted_res[-1]]
    finest_purity = compute_purity(finest_labels, metadata, 'branch')
    
    # Compute zoom quality for each transition
    zoom_quality_scores = {}
    for trans_key, trans in transitions.items():
        zq = compute_zoom_quality_score(trans, finest_purity)
        zoom_quality_scores[trans_key] = zq
        print(f"  {trans_key} zoom_quality: {zq:.4f}")
    
    mean_zoom_quality = np.mean(list(zoom_quality_scores.values()))
    print(f"\nMean zoom quality score: {mean_zoom_quality:.4f}")
    
    # Test compressed ladder
    print("\nTesting compressed resolution ladder...")
    compressed_labels = {res: all_labels[res] for res in config["compressed_resolutions"]}
    
    # Full ladder purity deltas
    full_total_delta = 0
    for i in range(len(sorted_res) - 1):
        r1, r2 = sorted_res[i], sorted_res[i+1]
        coarse_pur = resolution_metrics[r1]["branch_purity"]
        fine_pur = resolution_metrics[r2]["branch_purity"]
        full_total_delta += max(0, fine_pur - coarse_pur)
    
    # Compressed ladder purity deltas
    compressed_sorted = sorted(config["compressed_resolutions"])
    compressed_total_delta = 0
    for i in range(len(compressed_sorted) - 1):
        r1, r2 = compressed_sorted[i], compressed_sorted[i+1]
        coarse_pur = resolution_metrics[r1]["branch_purity"]
        fine_pur = resolution_metrics[r2]["branch_purity"]
        compressed_total_delta += max(0, fine_pur - coarse_pur)
    
    delta_retention = (compressed_total_delta / full_total_delta * 100) if full_total_delta > 0 else 100
    
    # Nesting for compressed
    compressed_nesting = compute_nesting_score(
        compressed_labels[compressed_sorted[0]], 
        compressed_labels[compressed_sorted[-1]]
    )
    full_nesting = overall_nesting
    nesting_change = compressed_nesting - full_nesting
    
    print(f"  Full ladder total delta: {full_total_delta:.4f}")
    print(f"  Compressed ladder total delta: {compressed_total_delta:.4f}")
    print(f"  Delta retention: {delta_retention:.2f}%")
    print(f"  Full nesting: {full_nesting:.4f}")
    print(f"  Compressed nesting: {compressed_nesting:.4f}")
    print(f"  Nesting change: {nesting_change:.4f}")
    
    compressed_passes = (delta_retention >= 99.9) and (abs(nesting_change) < 1e-6)
    print(f"  Compressed ladder PASSES: {compressed_passes}")
    
    # Hierarchical coherence (Leiden hierarchy)
    print("\nComputing hierarchical coherence...")
    hierarchical_metrics = {}
    coarse_res = 0.5
    fine_res = 3.0
    coarse_labels = all_labels[coarse_res]
    fine_labels = all_labels[fine_res]
    
    n_coarse = len(np.unique(coarse_labels))
    n_fine = len(np.unique(fine_labels))
    
    coarse_overall_purity = resolution_metrics[coarse_res]["branch_purity"]
    fine_overall_purity = resolution_metrics[fine_res]["branch_purity"]
    
    # Per coarse cluster analysis
    coarse_to_fine = defaultdict(set)
    for i in range(len(coarse_labels)):
        coarse_to_fine[coarse_labels[i]].add(fine_labels[i])
    
    improvements = 0
    deteriorations = 0
    no_change = 0
    per_cluster = {}
    
    for c, fine_clusters in coarse_to_fine.items():
        coarse_mask = coarse_labels == c
        coarse_pur = compute_purity(coarse_labels[coarse_mask], 
                                    [metadata[i] for i in np.where(coarse_mask)[0]], 'branch')
        
        fine_purities = []
        for f in fine_clusters:
            fine_mask = fine_labels == f
            fine_pur = compute_purity(fine_labels[fine_mask], 
                                      [metadata[i] for i in np.where(fine_mask)[0]], 'branch')
            fine_purities.append(fine_pur)
        
        fine_pur_mean = np.mean(fine_purities) if fine_purities else 0
        improvement = fine_pur_mean - coarse_pur
        
        if improvement > 0.01:
            improvements += 1
        elif improvement < -0.01:
            deteriorations += 1
        else:
            no_change += 1
        
        per_cluster[c] = {
            "coarse_size": int(np.sum(coarse_mask)),
            "coarse_purity": float(coarse_pur),
            "n_fine_clusters": len(fine_clusters),
            "fine_purity_mean": float(fine_pur_mean),
            "improvement": float(improvement),
        }
    
    improvement_rate = improvements / n_coarse if n_coarse > 0 else 0
    overall_improvement = fine_overall_purity - coarse_overall_purity
    
    hierarchical_metrics = {
        "coarse_resolution": coarse_res,
        "fine_resolution": fine_res,
        "n_coarse_clusters": int(n_coarse),
        "n_fine_clusters": int(n_fine),
        "coarse_overall_purity": float(coarse_overall_purity),
        "fine_overall_purity": float(fine_overall_purity),
        "overall_improvement": float(overall_improvement),
        "improvement_pct": float(overall_improvement / coarse_overall_purity * 100) if coarse_overall_purity > 0 else 0,
        "total_improvements": improvements,
        "total_deteriorations": deteriorations,
        "total_no_change": no_change,
        "improvement_rate": float(improvement_rate),
        "nesting_score": float(full_nesting),
    }
    
    print(f"  Coarse purity (res={coarse_res}): {coarse_overall_purity:.4f}")
    print(f"  Fine purity (res={fine_res}): {fine_overall_purity:.4f}")
    print(f"  Improvement: {overall_improvement:.4f} ({hierarchical_metrics['improvement_pct']:.2f}%)")
    print(f"  Improvement rate: {improvement_rate:.4f}")
    print(f"  Nesting score: {full_nesting:.4f}")
    
    # Check success rule
    mean_purity_delta = np.mean([t['mean_purity_delta'] for t in transitions.values()])
    success = (mean_purity_delta > 0) and (full_nesting >= 0.99)
    
    print(f"\n{'='*60}")
    print(f"SUCCESS RULE CHECK:")
    print(f"  Mean purity_delta > 0: {mean_purity_delta > 0} (value: {mean_purity_delta:.4f})")
    print(f"  Nesting_score >= 0.99: {full_nesting >= 0.99} (value: {full_nesting:.4f})")
    print(f"  OVERALL SUCCESS: {success}")
    print(f"{'='*60}")
    
    # Prepare results
    results = {
        "run_id": config["run_id"],
        "timestamp": config["timestamp"],
        "direction_version": config["direction_version"],
        "lane": config["lane"],
        "hypothesis": config["hypothesis"],
        "frozen_sample": config["frozen_sample"],
        "frozen_metric": config["frozen_metric"],
        "success_rule": config["success_rule"],
        "n_decisions": int(n_decisions),
        "embedding_dim": int(embeddings.shape[1]),
        "years_covered": config["years"],
        "resolutions_tested": config["resolutions"],
        "resolution_metrics": resolution_metrics,
        "transitions": transitions,
        "zoom_quality_scores": zoom_quality_scores,
        "mean_zoom_quality": float(mean_zoom_quality),
        "finest_purity": float(finest_purity),
        "overall_nesting_score": float(overall_nesting),
        "mean_purity_delta": float(mean_purity_delta),
        "compressed_ladder_test": {
            "full_ladder": config["resolutions"],
            "compressed_ladder": config["compressed_resolutions"],
            "dropped_resolutions": config["dropped_resolutions"],
            "full_total_delta": float(full_total_delta),
            "compressed_total_delta": float(compressed_total_delta),
            "delta_retention_pct": float(delta_retention),
            "full_nesting": float(full_nesting),
            "compressed_nesting": float(compressed_nesting),
            "nesting_change": float(nesting_change),
            "passes": compressed_passes,
        },
        "hierarchical_coherence": hierarchical_metrics,
        "success": success,
        "verdict": "PASS" if success else "FAIL",
    }
    
    # Save results
    output_path = os.path.join(config["output_dir"], "hierarchical_dense_77k_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    
    # Also save labels for downstream use
    for res, labels in all_labels.items():
        np.save(os.path.join(config["output_dir"], f"labels_res_{res}.npy"), labels)
    
    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if results["success"] else 1)