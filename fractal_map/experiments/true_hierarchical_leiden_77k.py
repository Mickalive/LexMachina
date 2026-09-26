#!/usr/bin/env python3
"""
True Hierarchical Clustering at 77k scale.
Tests hierarchical Leiden: cluster at coarse resolution, then recursively 
sub-cluster within each coarse cluster at finer resolutions.
This produces a genuine hierarchy by construction.
"""

import json
import numpy as np
import os
import sys
import time
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

try:
    import igraph as ig
    import leidenalg as la
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-igraph", "leidenalg"])
    import igraph as ig
    import leidenalg as la

from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score

# Load embeddings and metadata
embedding_dir = "/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints"
years = list(range(2000, 2013))

print("Loading embeddings...")
all_embeddings = []
all_metadata = []

for year in years:
    emb_path = os.path.join(embedding_dir, f"embeddings_{year}.npy")
    meta_path = os.path.join(embedding_dir, f"metadata_{year}.json")
    embeddings = np.load(emb_path).astype(np.float32)
    with open(meta_path) as f:
        metadata = json.load(f)
    all_embeddings.append(embeddings)
    all_metadata.extend(metadata)

embeddings = np.vstack(all_embeddings)
n = len(embeddings)
print(f"Total: {n} decisions")

# Build k-NN graph
k = 30
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
norms[norms == 0] = 1
embeddings_norm = embeddings / norms

nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
nn.fit(embeddings_norm)
distances, indices = nn.kneighbors(embeddings_norm)
indices = indices[:, 1:]
distances = distances[:, 1:]
similarities = 1 - distances

edges = []
weights = []
for i in range(n):
    for j, sim in zip(indices[i], similarities[i]):
        edges.append((i, int(j)))
        weights.append(float(sim))

g = ig.Graph()
g.add_vertices(n)
g.add_edges(edges)
g.es['weight'] = weights

# ============================================================
# TRUE HIERARCHICAL LEIDEN: Coarse -> Fine within clusters
# ============================================================
def hierarchical_leiden(graph, coarse_res=0.5, fine_resolutions=[1.0, 1.5, 2.0, 3.0], seed=42):
    """
    Run Leiden at coarse resolution, then sub-cluster within each coarse cluster
    at progressively finer resolutions.
    Returns: dict of {resolution: global_labels}
    """
    print(f"Running hierarchical Leiden: coarse_res={coarse_res}, fine={fine_resolutions}")
    
    # Step 1: Coarse clustering
    coarse_partition = la.find_partition(
        graph,
        la.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=coarse_res,
        seed=seed
    )
    coarse_labels = np.array(coarse_partition.membership)
    n_coarse = len(np.unique(coarse_labels))
    print(f"  Coarse ({coarse_res}): {n_coarse} clusters")
    
    # Initialize global labels with coarse
    global_labels = {coarse_res: coarse_labels.copy()}
    
    # Step 2: For each fine resolution, sub-cluster within coarse clusters
    for fine_res in fine_resolutions:
        print(f"  Fine ({fine_res}): sub-clustering within {n_coarse} coarse clusters...")
        fine_global = coarse_labels.copy()
        next_cluster_id = n_coarse
        
        for c in range(n_coarse):
            # Get vertices in this coarse cluster
            mask = coarse_labels == c
            vertices = np.where(mask)[0]
            
            if len(vertices) < 2:
                continue
            
            # Create subgraph
            subgraph = graph.subgraph(vertices.tolist())
            
            # Run Leiden on subgraph
            try:
                sub_partition = la.find_partition(
                    subgraph,
                    la.RBConfigurationVertexPartition,
                    weights='weight',
                    resolution_parameter=fine_res,
                    seed=seed
                )
                sub_labels = np.array(sub_partition.membership)
                
                # Remap to global cluster IDs
                for local_idx, global_idx in enumerate(vertices):
                    fine_global[global_idx] = next_cluster_id + sub_labels[local_idx]
                
                next_cluster_id += len(np.unique(sub_labels))
            except Exception as e:
                print(f"    Warning: sub-clustering failed for cluster {c}: {e}")
                # Keep coarse labels for this cluster
                pass
        
        global_labels[fine_res] = fine_global
        n_fine = len(np.unique(fine_global))
        print(f"    -> {n_fine} global clusters")
    
    return global_labels

# Run true hierarchical Leiden
coarse_res = 0.5
fine_resolutions = [1.0, 1.5, 2.0, 3.0]
all_resolutions = [coarse_res] + fine_resolutions

true_hier_labels = hierarchical_leiden(g, coarse_res, fine_resolutions)

# Save
output_dir = "results/fractal_map/77k_true_hierarchical"
os.makedirs(output_dir, exist_ok=True)

for res, labels in true_hier_labels.items():
    np.save(os.path.join(output_dir, f"labels_res_{res}.npy"), labels)

# ============================================================
# EVALUATION
# ============================================================
def compute_purity(labels, metadata, key):
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

def compute_nesting_score(coarse, fine):
    fine_to_coarse = defaultdict(set)
    for i in range(len(fine)):
        fine_to_coarse[fine[i]].add(coarse[i])
    nested = sum(1 for v in fine_to_coarse.values() if len(v) == 1)
    return nested / len(fine_to_coarse) if fine_to_coarse else 0

print("\n=== TRUE HIERARCHICAL LEIDEN METRICS ===")
true_hier_metrics = {}
for res in all_resolutions:
    labels = true_hier_labels[res]
    branch_purity = compute_purity(labels, all_metadata, 'branch')
    legal_area_purity = compute_purity(labels, all_metadata, 'legal_area')
    language_purity = compute_purity(labels, all_metadata, 'language')
    n_clusters = len(np.unique(labels))
    true_hier_metrics[res] = {
        "n_clusters": int(n_clusters),
        "branch_purity": float(branch_purity),
        "legal_area_purity": float(legal_area_purity),
        "language_purity": float(language_purity),
    }
    print(f"  res_{res}: {n_clusters} clusters, branch={branch_purity:.4f}, "
          f"legal_area={legal_area_purity:.4f}, lang={language_purity:.4f}")

# Nesting scores (should be 1.0 by construction!)
print("\n=== TRUE HIERARCHICAL NESTING (should be 1.0) ===")
for i in range(len(all_resolutions) - 1):
    r1, r2 = all_resolutions[i], all_resolutions[i+1]
    nesting = compute_nesting_score(true_hier_labels[r1], true_hier_labels[r2])
    print(f"  {r1}->{r2}: nesting={nesting:.4f}")

true_overall_nesting = compute_nesting_score(true_hier_labels[coarse_res], true_hier_labels[fine_resolutions[-1]])
print(f"\nOverall nesting (coarse->{fine_resolutions[-1]}): {true_overall_nesting:.4f}")

# Purity deltas
print("\n=== PURITY DELTAS (zoom refinement) ===")
for i in range(len(all_resolutions) - 1):
    r1, r2 = all_resolutions[i], all_resolutions[i+1]
    coarse_pur = true_hier_metrics[r1]["branch_purity"]
    fine_pur = true_hier_metrics[r2]["branch_purity"]
    delta = fine_pur - coarse_pur
    print(f"  {r1}->{r2}: delta={delta:+.4f} (coarse={coarse_pur:.4f}, fine={fine_pur:.4f})")

# Compare with flat/non-hierarchical
print("\n=== COMPARISON WITH NON-HIERARCHICAL ===")
# Load non-hierarchical results
non_hier_dir = "results/fractal_map/77k_hierarchical_dense"
for res in all_resolutions:
    non_hier_labels = np.load(os.path.join(non_hier_dir, f"labels_res_{res}.npy"))
    nmi = normalized_mutual_info_score(true_hier_labels[res], non_hier_labels)
    print(f"  res_{res}: NMI={nmi:.4f}")

# Hierarchical coherence: coarse (0.5) -> fine (3.0)
coarse_labels = true_hier_labels[coarse_res]
fine_labels = true_hier_labels[fine_resolutions[-1]]

coarse_pur = true_hier_metrics[coarse_res]["branch_purity"]
fine_pur = true_hier_metrics[fine_resolutions[-1]]["branch_purity"]

print(f"\n=== HIERARCHICAL COHERENCE (coarse={coarse_res} -> fine={fine_resolutions[-1]}) ===")
print(f"  Coarse purity: {coarse_pur:.4f}")
print(f"  Fine purity: {fine_pur:.4f}")
print(f"  Improvement: {fine_pur - coarse_pur:.4f} ({(fine_pur - coarse_pur)/coarse_pur*100:.2f}%)")

# Per coarse cluster analysis
n_coarse = len(np.unique(coarse_labels))
improvements = 0
deteriorations = 0
no_change = 0

for c in range(n_coarse):
    mask = coarse_labels == c
    if np.sum(mask) < 2:
        continue
    coarse_c_pur = compute_purity(coarse_labels[mask], 
                                   [all_metadata[i] for i in np.where(mask)[0]], 'branch')
    
    fine_mask = fine_labels[mask]
    fine_c_pur = compute_purity(fine_mask, 
                                 [all_metadata[i] for i in np.where(mask)[0]], 'branch')
    
    improvement = fine_c_pur - coarse_c_pur
    if improvement > 0.01:
        improvements += 1
    elif improvement < -0.01:
        deteriorations += 1
    else:
        no_change += 1

print(f"  Clusters improving: {improvements}")
print(f"  Clusters deteriorating: {deteriorations}")
print(f"  Clusters no change: {no_change}")
print(f"  Improvement rate: {improvements/n_coarse:.4f}")

# Save results
results = {
    "run_id": "true_hierarchical_leiden_77k_20260926",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "direction_version": 28,
    "n_decisions": n,
    "method": "true_hierarchical_leiden",
    "coarse_resolution": coarse_res,
    "fine_resolutions": fine_resolutions,
    "resolution_metrics": true_hier_metrics,
    "transition_nesting": {f"{all_resolutions[i]}->{all_resolutions[i+1]}": float(compute_nesting_score(true_hier_labels[all_resolutions[i]], true_hier_labels[all_resolutions[i+1]])) for i in range(len(all_resolutions)-1)},
    "overall_nesting": float(true_overall_nesting),
    "hierarchical_coherence": {
        "coarse_resolution": coarse_res,
        "fine_resolution": fine_resolutions[-1],
        "n_coarse_clusters": int(n_coarse),
        "n_fine_clusters": int(len(np.unique(fine_labels))),
        "coarse_overall_purity": float(coarse_pur),
        "fine_overall_purity": float(fine_pur),
        "overall_improvement": float(fine_pur - coarse_pur),
        "improvement_pct": float((fine_pur - coarse_pur) / coarse_pur * 100),
        "total_improvements": improvements,
        "total_deteriorations": deteriorations,
        "total_no_change": no_change,
        "improvement_rate": float(improvements / n_coarse),
    },
}

output_path = os.path.join(output_dir, "true_hierarchical_leiden_77k_results.json")
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {output_path}")