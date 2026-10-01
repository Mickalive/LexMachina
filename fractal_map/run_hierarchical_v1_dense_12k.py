#!/usr/bin/env python3
"""
Run hierarchical_v1 protocol on ACCEPTED dense embeddings (years 2000-2002, ~12k decisions).
Same frozen config as TF-IDF 174k test.
"""

import numpy as np
import json
import os
from collections import Counter, defaultdict
import igraph as ig
import leidenalg as la
from sklearn.neighbors import NearestNeighbors

# Load embeddings and metadata
print("Loading embeddings...")
embeddings = []
dense_meta = []
for year in ['2000', '2001', '2002']:
    emb = np.load(f'/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints/embeddings_{year}.npy')
    with open(f'/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints/metadata_{year}.json') as f:
        meta = json.load(f)
    embeddings.append(emb)
    dense_meta.extend(meta)

embeddings = np.vstack(embeddings)
print(f"Total embeddings: {embeddings.shape}")

# Load 174k metadata for labels
with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json') as f:
    meta_174k = json.load(f)
lookup = {m['decision_id']: m for m in meta_174k}

# Get branch and legal_area labels
branches = []
areas = []
decision_ids = []
for m in dense_meta:
    did = m['decision_id']
    decision_ids.append(did)
    ref = lookup[did]
    branches.append(ref['branch'])
    areas.append(ref['legal_area'])

# Map to integers
branch_to_idx = {b: i for i, b in enumerate(sorted(set(branches)))}
area_to_idx = {a: i for i, a in enumerate(sorted(set(areas)))}
branch_labels = np.array([branch_to_idx[b] for b in branches])
area_labels = np.array([area_to_idx[a] for a in areas])

n_branch = len(branch_to_idx)
n_area = len(area_to_idx)
print(f"Branches: {n_branch} ({sorted(branch_to_idx.keys())})")
print(f"Areas: {n_area}")

# Frozen config
config = {
    "coarse_res": 0.25,
    "base_sub_res": 3.0,
    "min_cluster_size": 10,
    "max_subclusters_per_parent": 20,
    "adaptive_sub_res": True,
    "k_neighbors": 15
}

# Build k-NN graph
print("Building k-NN graph...")
k = config["k_neighbors"]
nbrs = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1).fit(embeddings)
distances, indices = nbrs.kneighbors(embeddings)

# Build igraph
edges = []
weights = []
for i in range(len(embeddings)):
    for j_idx, dist in zip(indices[i][1:], distances[i][1:]):  # Skip self
        edges.append((i, j_idx))
        weights.append(1.0 - dist)  # Convert distance to similarity

g = ig.Graph()
g.add_vertices(len(embeddings))
g.add_edges(edges)
g.es['weight'] = weights
print(f"Graph: {g.vcount()} vertices, {g.ecount()} edges")

# Run coarse Leiden
print("Running coarse Leiden...")
coarse_partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                       resolution_parameter=config["coarse_res"],
                                       weights='weight')
coarse_labels = np.array(coarse_partition.membership)
n_coarse = len(set(coarse_labels))
print(f"Coarse clusters: {n_coarse}")

# Run fine Leiden per coarse cluster (constrained hierarchical)
print("Running constrained hierarchical fine Leiden...")
fine_labels = np.full(len(embeddings), -1, dtype=int)
fine_cluster_id = 0
parent_of_fine = {}

for coarse_id in range(n_coarse):
    mask = (coarse_labels == coarse_id)
    cluster_nodes = np.where(mask)[0]
    cluster_size = len(cluster_nodes)
    
    if cluster_size < config["min_cluster_size"]:
        # Assign all to same fine cluster
        fine_labels[cluster_nodes] = fine_cluster_id
        parent_of_fine[fine_cluster_id] = coarse_id
        fine_cluster_id += 1
        continue
    
    # Subgraph
    subgraph = g.subgraph(cluster_nodes.tolist())
    
    # Adaptive sub-resolution based on cluster size
    if config["adaptive_sub_res"]:
        # Scale resolution: larger clusters get higher resolution (more subclusters)
        size_factor = np.log10(max(cluster_size, 10)) / np.log10(1000)
        sub_res = config["base_sub_res"] * max(0.5, min(2.0, size_factor))
    else:
        sub_res = config["base_sub_res"]
    
    # Run Leiden on subgraph
    try:
        sub_partition = la.find_partition(subgraph, la.RBConfigurationVertexPartition,
                                            resolution_parameter=sub_res,
                                            weights='weight')
        sub_labels = np.array(sub_partition.membership)
        n_sub = len(set(sub_labels))
        
        # Enforce max_subclusters_per_parent
        if n_sub > config["max_subclusters_per_parent"]:
            # Merge smallest clusters
            sub_sizes = Counter(sub_labels)
            # Keep largest max_subclusters_per_parent clusters, merge rest into largest
            sorted_clusters = sorted(sub_sizes.items(), key=lambda x: x[1], reverse=True)
            keep_clusters = set([c for c, _ in sorted_clusters[:config["max_subclusters_per_parent"]]])
            new_sub_labels = np.copy(sub_labels)
            for c in set(sub_labels):
                if c not in keep_clusters:
                    new_sub_labels[sub_labels == c] = sorted_clusters[0][0]
            sub_labels = new_sub_labels
            n_sub = len(set(sub_labels))
        
        # Assign fine labels
        for sub_id in sorted(set(sub_labels)):
            sub_mask = (sub_labels == sub_id)
            fine_labels[cluster_nodes[sub_mask]] = fine_cluster_id
            parent_of_fine[fine_cluster_id] = coarse_id
            fine_cluster_id += 1
    except Exception as e:
        print(f"  Warning: Leiden failed for coarse cluster {coarse_id} (size={cluster_size}): {e}")
        # Fallback: single cluster
        fine_labels[cluster_nodes] = fine_cluster_id
        parent_of_fine[fine_cluster_id] = coarse_id
        fine_cluster_id += 1

n_fine = len(set(fine_labels))
print(f"Fine clusters: {n_fine}")

# Verify nesting
nesting_ok = True
for fine_id, coarse_id in parent_of_fine.items():
    fine_nodes = np.where(fine_labels == fine_id)[0]
    coarse_of_fine = coarse_labels[fine_nodes]
    if not np.all(coarse_of_fine == coarse_id):
        nesting_ok = False
        print(f"Nesting violation: fine {fine_id} spans multiple coarse clusters")
        break

print(f"Nesting: {'PERFECT' if nesting_ok else 'VIOLATED'}")

# Compute fragmentation
fine_sizes = Counter(fine_labels)
singleton_fraction = sum(1 for s in fine_sizes.values() if s == 1) / n_fine
median_size = np.median(list(fine_sizes.values()))
print(f"Fragmentation: singleton_fraction={singleton_fraction:.4f}, median_size={median_size:.1f}")

# Compute purity at coarse and fine levels
def compute_purity(cluster_labels, true_labels):
    """Compute purity: for each cluster, majority class fraction, weighted by cluster size."""
    total = len(true_labels)
    purity_sum = 0
    for cid in set(cluster_labels):
        mask = (cluster_labels == cid)
        cluster_true = true_labels[mask]
        if len(cluster_true) == 0:
            continue
        majority_count = Counter(cluster_true).most_common(1)[0][1]
        purity_sum += majority_count
    return purity_sum / total

coarse_branch_purity = compute_purity(coarse_labels, branch_labels)
fine_branch_purity = compute_purity(fine_labels, branch_labels)
coarse_area_purity = compute_purity(coarse_labels, area_labels)
fine_area_purity = compute_purity(fine_labels, area_labels)

print(f"Coarse branch purity: {coarse_branch_purity:.4f}")
print(f"Fine branch purity: {fine_branch_purity:.4f}")
print(f"Branch purity delta: {fine_branch_purity - coarse_branch_purity:.4f}")
print(f"Coarse area purity: {coarse_area_purity:.4f}")
print(f"Fine area purity: {fine_area_purity:.4f}")
print(f"Area purity delta: {fine_area_purity - coarse_area_purity:.4f}")

# Zoom coherence (improvement rate)
# For each coarse cluster, compute mean child purity and improvement
parent_details = {}
for coarse_id in range(n_coarse):
    children = [fid for fid, pid in parent_of_fine.items() if pid == coarse_id]
    if len(children) <= 1:
        continue
    coarse_mask = (coarse_labels == coarse_id)
    coarse_branch = branch_labels[coarse_mask]
    if len(coarse_branch) == 0:
        continue
    coarse_purity = Counter(coarse_branch).most_common(1)[0][1] / len(coarse_branch)
    
    child_purities = []
    for fid in children:
        fine_mask = (fine_labels == fid)
        fine_branch = branch_labels[fine_mask]
        if len(fine_branch) == 0:
            continue
        child_purity = Counter(fine_branch).most_common(1)[0][1] / len(fine_branch)
        child_purities.append(child_purity)
    
    if child_purities:
        mean_child = np.mean(child_purities)
        improvement = mean_child - coarse_purity
        parent_details[str(coarse_id)] = {
            "coarse_purity": coarse_purity,
            "mean_child_purity": mean_child,
            "improvement": improvement,
            "n_children": len(children)
        }

improvements = [d["improvement"] for d in parent_details.values()]
improvement_rate = sum(1 for imp in improvements if imp > 0) / len(improvements) if improvements else 0
mean_improvement = np.mean(improvements) if improvements else 0

print(f"Zoom coherence: mean_improvement={mean_improvement:.4f}, improvement_rate={improvement_rate:.4f}")

# Random baselines
branch_random = 1.0 / n_branch
area_random = 1.0 / n_area
print(f"Random branch baseline: {branch_random:.4f}")
print(f"Random area baseline: {area_random:.4f}")

# Legal structure checks
legal_structure_branch = fine_branch_purity > 2 * branch_random
legal_structure_area = fine_area_purity > 2 * area_random
print(f"Legal structure branch: {legal_structure_branch} (fine={fine_branch_purity:.4f} > 2*{branch_random:.4f}={2*branch_random:.4f})")
print(f"Legal structure area: {legal_structure_area} (fine={fine_area_purity:.4f} > 2*{area_random:.4f}={2*area_random:.4f})")

# Fragmentation check
fragmentation_ok = singleton_fraction < 0.01

# Nesting check
nesting_perfect = nesting_ok

# Branch/area purity improvement checks
branch_purity_improves = fine_branch_purity > coarse_branch_purity
area_purity_improves = fine_area_purity > coarse_area_purity

# Zoom coherence check
zoom_coherence_ok = improvement_rate > 0.5

# Per-mode verdict
checks = {
    "fragmentation_ok": fragmentation_ok,
    "nesting_perfect": nesting_perfect,
    "branch_purity_improves": branch_purity_improves,
    "area_purity_improves": area_purity_improves,
    "zoom_coherence_ok": zoom_coherence_ok,
    "legal_structure_branch": legal_structure_branch,
    "legal_structure_area": legal_structure_area
}

per_mode_verdict = "PASS" if all(checks.values()) else "FAIL"

print(f"\n=== CHECKS ===")
for k, v in checks.items():
    print(f"  {k}: {v}")
print(f"Per-mode verdict: {per_mode_verdict}")

# Save results
results = {
    "mode": "dense_embeddings_12k_accepted",
    "config": config,
    "sample_size": len(embeddings),
    "coarse": {
        "n_clusters": n_coarse,
        "branch_purity": coarse_branch_purity,
        "area_purity": coarse_area_purity
    },
    "hierarchical_fine": {
        "n_clusters": n_fine,
        "branch_purity": fine_branch_purity,
        "area_purity": fine_area_purity,
        "fragmentation": {
            "singleton_fraction": singleton_fraction,
            "median_size": float(median_size),
            "size_distribution": {str(k): v for k, v in fine_sizes.items()}
        }
    },
    "nesting": 1.0 if nesting_ok else 0.0,
    "zoom_coherence": {
        "parent_details": parent_details,
        "overall": {
            "mean_improvement": float(mean_improvement),
            "improvement_rate": float(improvement_rate),
            "n_parents": len(parent_details)
        }
    },
    "checks": checks,
    "per_mode_verdict": per_mode_verdict,
    "baselines": {
        "branch_random": branch_random,
        "area_random": area_random,
        "n_branch_classes": n_branch,
        "n_area_classes": n_area
    }
}

output_path = "/home/runner/work/LexMachina/LexMachina/results/fractal_map/dense_12k_hierarchical_v1/dense_12k_hierarchical_v1_results.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to {output_path}")
print(f"PER_MODE_VERDICT: {per_mode_verdict}")

# Also save a summary for comparison
summary = {
    "mode": "dense_embeddings_12k_accepted",
    "sample_size": len(embeddings),
    "coarse_branch_purity": coarse_branch_purity,
    "fine_branch_purity": fine_branch_purity,
    "branch_purity_delta": fine_branch_purity - coarse_branch_purity,
    "fine_area_purity": fine_area_purity,
    "area_purity_delta": fine_area_purity - coarse_area_purity,
    "singleton_fraction": singleton_fraction,
    "median_cluster_size": float(median_size),
    "nesting": 1.0 if nesting_ok else 0.0,
    "improvement_rate": improvement_rate,
    "mean_improvement": mean_improvement,
    "legal_structure_branch": legal_structure_branch,
    "legal_structure_area": legal_structure_area,
    "per_mode_verdict": per_mode_verdict
}
print(f"\nSUMMARY: {json.dumps(summary, indent=2)}")