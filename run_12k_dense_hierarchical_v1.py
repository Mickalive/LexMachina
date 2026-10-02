#!/usr/bin/env python3
"""
Run hierarchical_v1 protocol on 12k ACCEPTED dense embeddings (years 2000-2002).
Produces comparable metrics to TF-IDF 174k results and 28k checkpoint validation.
"""

import json
import numpy as np
import pickle
from pathlib import Path
from collections import Counter, defaultdict
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors
import time
import sys

# ─── Paths ──────────────────────────────────────────────────────────────
EMBEDDINGS_PATH = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_dense_comprehensive/embeddings_12k_2000_2002.npy")
METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_dense_comprehensive/metadata_12k_2000_2002.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_dense_hierarchical_v1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Frozen hierarchical_v1 spec ───────────────────────────────────────
FROZEN_CONFIG = {
    "coarse_res": 0.25,
    "base_sub_res": 3.0,
    "min_cluster_size": 10,
    "max_subclusters_per_parent": 20,
    "adaptive_sub_res": True,
    "k_neighbors": 15
}

# Also test dense-optimized configs from 28k validation
DENSE_CONFIGS = {
    "frozen_tfidf": FROZEN_CONFIG,
    "dense_fixed2.0_min20": {
        "coarse_res": 0.5,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": False,
        "k_neighbors": 15
    },
    "dense_fixed3.0_min20": {
        "coarse_res": 0.5,
        "base_sub_res": 3.0,
        "min_cluster_size": 20,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": False,
        "k_neighbors": 15
    },
    "dense_fixed2.0_min20_coarse0.25": {
        "coarse_res": 0.25,
        "base_sub_res": 2.0,
        "min_cluster_size": 20,
        "max_subclusters_per_parent": 20,
        "adaptive_sub_res": False,
        "k_neighbors": 15
    }
}

# ─── Load data ──────────────────────────────────────────────────────────
print("Loading embeddings and metadata...", flush=True)
embeddings = np.load(EMBEDDINGS_PATH)
with open(METADATA_PATH) as f:
    metadata = json.load(f)

n_decisions = len(metadata)
print(f"Loaded {n_decisions} decisions, embedding dim: {embeddings.shape[1]}", flush=True)

# Extract labels
branches = [m["branch"] for m in metadata]
legal_areas = [m["legal_area"] for m in metadata]
languages = [m["language"] for m in metadata]

# Compute random baselines
branch_counter = Counter(branches)
area_counter = Counter(legal_areas)
n_branch_classes = len(branch_counter)
n_area_classes = len(area_counter)
random_branch_baseline = 1.0 / n_branch_classes
random_area_baseline = 1.0 / n_area_classes
print(f"Branch classes: {n_branch_classes}, random baseline: {random_branch_baseline:.4f}")
print(f"Area classes: {n_area_classes}, random baseline: {random_area_baseline:.4f}")

# ─── Helper functions ───────────────────────────────────────────────────
def run_leiden(embeddings, resolution, k_neighbors=15):
    """Run Leiden clustering on embeddings using k-NN graph."""
    n = len(embeddings)
    nn = NearestNeighbors(n_neighbors=min(k_neighbors + 1, n), metric="cosine")
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(n):
        for j_idx in range(1, len(indices[i])):  # Skip self
            j = indices[i][j_idx]
            if i < j:  # Undirected
                w = 1.0 - distances[i][j_idx]
                if w > 0:
                    edges.append((i, j))
                    weights.append(w)
    
    if not edges:
        return np.zeros(n, dtype=int)
    
    g = ig.Graph(edges=edges, directed=False)
    g.es["weight"] = weights
    
    partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                   weights="weight", resolution_parameter=resolution)
    labels = np.array(partition.membership)
    return labels

def compute_purity(labels, true_labels):
    """Compute purity: for each cluster, fraction of majority class."""
    cluster_to_true = defaultdict(list)
    for i, label in enumerate(labels):
        cluster_to_true[label].append(true_labels[i])
    
    total_correct = 0
    total = 0
    purities = []
    for cluster, true_list in cluster_to_true.items():
        if not true_list:
            continue
        counter = Counter(true_list)
        majority = counter.most_common(1)[0][1]
        purities.append(majority / len(true_list))
        total_correct += majority
        total += len(true_list)
    
    return np.mean(purities) if purities else 0.0, total_correct / total if total else 0.0

def compute_zoom_coherence(coarse_labels, fine_labels, true_labels):
    """Compute zoom coherence metrics for coarse->fine transition."""
    parent_details = {}
    n_parents = len(np.unique(coarse_labels))
    
    for parent in np.unique(coarse_labels):
        parent_mask = (coarse_labels == parent)
        parent_true = [true_labels[i] for i in np.where(parent_mask)[0]]
        if not parent_true:
            continue
        parent_counter = Counter(parent_true)
        coarse_purity = parent_counter.most_common(1)[0][1] / len(parent_true)
        
        # Children
        child_labels = fine_labels[parent_mask]
        child_improvements = []
        for child in np.unique(child_labels):
            child_mask = (child_labels == child)
            child_true = [parent_true[i] for i in np.where(child_mask)[0]]
            if not child_true:
                continue
            child_counter = Counter(child_true)
            child_purity = child_counter.most_common(1)[0][1] / len(child_true)
            child_improvements.append(child_purity - coarse_purity)
        
        if child_improvements:
            parent_details[str(parent)] = {
                "coarse_purity": coarse_purity,
                "mean_child_purity": np.mean([coarse_purity + imp for imp in child_improvements]),
                "improvement": np.mean(child_improvements),
                "n_children": len(child_improvements)
            }
    
    improvements = [d["improvement"] for d in parent_details.values()]
    improvement_rate = np.mean([1 for imp in improvements if imp > 0]) if improvements else 0.0
    mean_improvement = np.mean(improvements) if improvements else 0.0
    
    return {
        "parent_details": parent_details,
        "overall": {
            "mean_improvement": mean_improvement,
            "improvement_rate": improvement_rate,
            "n_parents": len(parent_details)
        }
    }

def compute_nesting(coarse_labels, fine_labels):
    """Compute strict nesting consistency (each fine cluster maps to exactly one coarse cluster)."""
    n_fine = len(np.unique(fine_labels))
    n_consistent = 0
    
    for fine in np.unique(fine_labels):
        fine_mask = (fine_labels == fine)
        parent_labels = coarse_labels[fine_mask]
        unique_parents = np.unique(parent_labels)
        if len(unique_parents) == 1:
            n_consistent += 1
    
    return n_consistent / n_fine if n_fine else 1.0

def compute_fragmentation(labels):
    """Compute fragmentation metrics."""
    unique, counts = np.unique(labels, return_counts=True)
    median_size = np.median(counts)
    singleton_fraction = np.sum(counts == 1) / len(counts)
    return {
        "n_clusters": len(unique),
        "median_size": float(median_size),
        "mean_size": float(np.mean(counts)),
        "singleton_fraction": float(singleton_fraction),
        "max_size": int(np.max(counts)),
        "min_size": int(np.min(counts))
    }

# ─── Run hierarchical clustering ────────────────────────────────────────
def run_hierarchical(config_name, config):
    print(f"\n{'='*60}")
    print(f"Running config: {config_name}")
    print(f"Config: {json.dumps(config, indent=2)}", flush=True)
    
    coarse_res = config["coarse_res"]
    base_sub_res = config["base_sub_res"]
    min_cluster_size = config["min_cluster_size"]
    max_subclusters = config["max_subclusters_per_parent"]
    adaptive = config["adaptive_sub_res"]
    k_neighbors = config["k_neighbors"]
    
    # Coarse clustering
    print("  Coarse clustering...", flush=True)
    coarse_labels = run_leiden(embeddings, coarse_res, k_neighbors)
    coarse_unique = np.unique(coarse_labels)
    print(f"  Coarse clusters: {len(coarse_unique)}", flush=True)
    
    # Fine clustering within each coarse cluster
    fine_labels = np.full(n_decisions, -1, dtype=int)
    fine_cluster_id = 0
    
    for parent in coarse_unique:
        parent_mask = (coarse_labels == parent)
        parent_indices = np.where(parent_mask)[0]
        parent_size = len(parent_indices)
        
        if parent_size < min_cluster_size:
            # Assign all to single fine cluster
            fine_labels[parent_indices] = fine_cluster_id
            fine_cluster_id += 1
            continue
        
        if adaptive:
            # Adaptive sub-resolution: increase until we get good split or hit max
            sub_res = base_sub_res
            best_labels = None
            best_n_clusters = 1
            
            for attempt in range(5):
                sub_labels = run_leiden(embeddings[parent_indices], sub_res, k_neighbors)
                n_sub = len(np.unique(sub_labels))
                
                # Check min_cluster_size constraint
                sub_unique, sub_counts = np.unique(sub_labels, return_counts=True)
                min_size = np.min(sub_counts)
                
                if min_size >= min_cluster_size and n_sub > 1:
                    best_labels = sub_labels
                    best_n_clusters = n_sub
                    break
                elif n_sub > best_n_clusters:
                    best_labels = sub_labels
                    best_n_clusters = n_sub
                
                sub_res *= 1.5  # Increase resolution
                
                if best_n_clusters >= max_subclusters:
                    break
            
            if best_labels is None or best_n_clusters <= 1:
                # No valid split found
                fine_labels[parent_indices] = fine_cluster_id
                fine_cluster_id += 1
            else:
                # Map to global fine cluster IDs
                for sub in np.unique(best_labels):
                    sub_mask = (best_labels == sub)
                    if np.sum(sub_mask) >= min_cluster_size:
                        fine_labels[parent_indices[sub_mask]] = fine_cluster_id
                        fine_cluster_id += 1
                    else:
                        # Too small, merge into first valid cluster
                        first_valid = np.unique(best_labels)[0]
                        fine_labels[parent_indices[sub_mask]] = fine_cluster_id - (1 if best_n_clusters > 1 else 0)
        else:
            # Fixed sub-resolution
            sub_labels = run_leiden(embeddings[parent_indices], base_sub_res, k_neighbors)
            n_sub = len(np.unique(sub_labels))
            
            if n_sub <= 1:
                fine_labels[parent_indices] = fine_cluster_id
                fine_cluster_id += 1
            else:
                for sub in np.unique(sub_labels):
                    sub_mask = (sub_labels == sub)
                    if np.sum(sub_mask) >= min_cluster_size:
                        fine_labels[parent_indices[sub_mask]] = fine_cluster_id
                        fine_cluster_id += 1
                    else:
                        # Merge small clusters
                        fine_labels[parent_indices[sub_mask]] = fine_cluster_id - 1 if fine_cluster_id > 0 else 0
    
    # Remove unassigned (-1)
    unassigned = np.sum(fine_labels == -1)
    if unassigned > 0:
        print(f"  Warning: {unassigned} unassigned, assigning to cluster 0")
        fine_labels[fine_labels == -1] = 0
    
    # ─── Compute metrics ─────────────────────────────────────────────
    # Branch purity
    coarse_branch_purity, _ = compute_purity(coarse_labels, branches)
    fine_branch_purity, _ = compute_purity(fine_labels, branches)
    
    # Area purity
    coarse_area_purity, _ = compute_purity(coarse_labels, legal_areas)
    fine_area_purity, _ = compute_purity(fine_labels, legal_areas)
    
    # Nesting
    nesting = compute_nesting(coarse_labels, fine_labels)
    
    # Zoom coherence
    zoom_branch = compute_zoom_coherence(coarse_labels, fine_labels, branches)
    zoom_area = compute_zoom_coherence(coarse_labels, fine_labels, legal_areas)
    
    # Fragmentation
    coarse_frag = compute_fragmentation(coarse_labels)
    fine_frag = compute_fragmentation(fine_labels)
    
    # Checks
    fragmentation_ok = fine_frag["singleton_fraction"] < 0.01
    nesting_perfect = nesting >= 0.99
    branch_purity_improves = fine_branch_purity > coarse_branch_purity
    area_purity_improves = fine_area_purity > coarse_area_purity
    zoom_coherence_ok = zoom_branch["overall"]["improvement_rate"] > 0.5
    legal_structure_branch = fine_branch_purity > 2 * random_branch_baseline
    legal_structure_area = fine_area_purity > 2 * random_area_baseline
    
    hierarchical_v1_pass = (fragmentation_ok and nesting_perfect and 
                           branch_purity_improves and area_purity_improves and
                           zoom_coherence_ok and legal_structure_branch and legal_structure_area)
    
    # Convert numpy types to Python types for JSON serialization
    def convert(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    result = convert({
        "mode": "dense_12k_2000_2002",
        "config": config,
        "n_decisions": n_decisions,
        "coarse": {
            "n_clusters": coarse_frag["n_clusters"],
            "branch_purity": coarse_branch_purity,
            "area_purity": coarse_area_purity,
            "fragmentation": coarse_frag
        },
        "hierarchical_fine": {
            "n_clusters": fine_frag["n_clusters"],
            "branch_purity": fine_branch_purity,
            "area_purity": fine_area_purity,
            "fragmentation": fine_frag
        },
        "nesting": nesting,
        "zoom_coherence": {
            "branch": zoom_branch,
            "area": zoom_area
        },
        "checks": {
            "fragmentation_ok": fragmentation_ok,
            "nesting_perfect": nesting_perfect,
            "branch_purity_improves": branch_purity_improves,
            "area_purity_improves": area_purity_improves,
            "zoom_coherence_ok": zoom_coherence_ok,
            "legal_structure_branch": legal_structure_branch,
            "legal_structure_area": legal_structure_area
        },
        "hierarchical_v1_pass": hierarchical_v1_pass,
        "per_mode_verdict": "PASS" if hierarchical_v1_pass else "FAIL"
    })
    
    print(f"  Coarse clusters: {coarse_frag['n_clusters']}, branch_purity: {coarse_branch_purity:.4f}")
    print(f"  Fine clusters: {fine_frag['n_clusters']}, branch_purity: {fine_branch_purity:.4f}")
    print(f"  Nesting: {nesting:.4f}")
    print(f"  Branch improvement: {fine_branch_purity - coarse_branch_purity:.4f}")
    print(f"  Zoom improvement_rate: {zoom_branch['overall']['improvement_rate']:.4f}")
    print(f"  Singleton fraction: {fine_frag['singleton_fraction']:.4f}")
    print(f"  hierarchical_v1_pass: {hierarchical_v1_pass}")
    
    return result

# ─── Main ───────────────────────────────────────────────────────────────
all_results = {}
for config_name, config in DENSE_CONFIGS.items():
    result = run_hierarchical(config_name, config)
    all_results[config_name] = result

# Save results
output_path = OUTPUT_DIR / "hierarchical_v1_12k_dense_results.json"
with open(output_path, "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\n{'='*60}")
print(f"Results saved to {output_path}")

# Summary
print("\nSUMMARY:")
for name, res in all_results.items():
    verdict = res["per_mode_verdict"]
    fb = res["hierarchical_fine"]["branch_purity"]
    zoom = res["zoom_coherence"]["branch"]["overall"]["improvement_rate"]
    frag = res["hierarchical_fine"]["fragmentation"]["singleton_fraction"]
    print(f"  {name}: {verdict} | fine_branch_purity={fb:.4f} | improvement_rate={zoom:.4f} | singleton_fraction={frag:.4f}")

# Best config
best = max(all_results.items(), key=lambda x: (x[1]["hierarchical_v1_pass"], x[1]["hierarchical_fine"]["branch_purity"]))
print(f"\nBest config: {best[0]} (PASS={best[1]['hierarchical_v1_pass']}, fine_branch_purity={best[1]['hierarchical_fine']['branch_purity']:.4f})")