#!/usr/bin/env python3
"""
Compare Hierarchical vs Flat Leiden clustering at 77k scale.
Tests whether hierarchical clustering provides genuine zoom refinement
over flat independent clustering at each resolution.
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

# Load the hierarchical results
hierarchical_results_path = "results/fractal_map/77k_hierarchical_dense/hierarchical_dense_77k_results.json"
with open(hierarchical_results_path) as f:
    hier_results = json.load(f)

# Load embeddings and metadata for flat clustering
embedding_dir = "/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints"
years = list(range(2000, 2013))

print("Loading embeddings for flat baseline...")
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

# Run flat Leiden at each resolution
resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
flat_labels = {}

print("\nRunning flat Leiden at each resolution...")
for res in resolutions:
    partition = la.find_partition(
        g,
        la.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=res,
        seed=42
    )
    labels = np.array(partition.membership)
    flat_labels[res] = labels
    n_clusters = len(np.unique(labels))
    print(f"  res_{res}: {n_clusters} clusters")

# Save flat labels
output_dir = "results/fractal_map/77k_hierarchical_dense"
os.makedirs(output_dir, exist_ok=True)
for res, labels in flat_labels.items():
    np.save(os.path.join(output_dir, f"flat_labels_res_{res}.npy"), labels)

# Load hierarchical labels
hier_labels = {}
for res in resolutions:
    hier_labels[res] = np.load(os.path.join(output_dir, f"labels_res_{res}.npy"))

# Compute metrics
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

print("\n=== FLAT BASELINE METRICS ===")
flat_metrics = {}
for res in resolutions:
    labels = flat_labels[res]
    branch_purity = compute_purity(labels, all_metadata, 'branch')
    legal_area_purity = compute_purity(labels, all_metadata, 'legal_area')
    language_purity = compute_purity(labels, all_metadata, 'language')
    n_clusters = len(np.unique(labels))
    flat_metrics[res] = {
        "n_clusters": int(n_clusters),
        "branch_purity": float(branch_purity),
        "legal_area_purity": float(legal_area_purity),
        "language_purity": float(language_purity),
    }
    print(f"  res_{res}: {n_clusters} clusters, branch={branch_purity:.4f}, "
          f"legal_area={legal_area_purity:.4f}, lang={language_purity:.4f}")

print("\n=== HIERARCHICAL METRICS (from previous run) ===")
hier_metrics = {}
for res in resolutions:
    labels = hier_labels[res]
    branch_purity = compute_purity(labels, all_metadata, 'branch')
    legal_area_purity = compute_purity(labels, all_metadata, 'legal_area')
    language_purity = compute_purity(labels, all_metadata, 'language')
    n_clusters = len(np.unique(labels))
    hier_metrics[res] = {
        "n_clusters": int(n_clusters),
        "branch_purity": float(branch_purity),
        "legal_area_purity": float(legal_area_purity),
        "language_purity": float(language_purity),
    }
    print(f"  res_{res}: {n_clusters} clusters, branch={branch_purity:.4f}, "
          f"legal_area={legal_area_purity:.4f}, lang={language_purity:.4f}")

# Compare: does hierarchical have advantage?
print("\n=== HIERARCHICAL ADVANTAGE ===")
advantages = {}
for res in resolutions:
    hier_bp = hier_metrics[res]["branch_purity"]
    flat_bp = flat_metrics[res]["branch_purity"]
    adv = hier_bp - flat_bp
    advantages[res] = adv
    print(f"  res_{res}: hierarchical={hier_bp:.4f}, flat={flat_bp:.4f}, advantage={adv:+.4f}")

# NMI between hierarchical and flat at same resolution
print("\n=== NMI BETWEEN HIERARCHICAL AND FLAT AT SAME RESOLUTION ===")
for res in resolutions:
    nmi = normalized_mutual_info_score(hier_labels[res], flat_labels[res])
    print(f"  res_{res}: NMI={nmi:.4f}")

# Check nesting in flat baseline (should be lower)
print("\n=== FLAT BASELINE NESTING (should be low) ===")
def compute_nesting_score(coarse, fine):
    fine_to_coarse = defaultdict(set)
    for i in range(len(fine)):
        fine_to_coarse[fine[i]].add(coarse[i])
    nested = sum(1 for v in fine_to_coarse.values() if len(v) == 1)
    return nested / len(fine_to_coarse) if fine_to_coarse else 0

for i in range(len(resolutions) - 1):
    r1, r2 = resolutions[i], resolutions[i+1]
    nesting = compute_nesting_score(flat_labels[r1], flat_labels[r2])
    print(f"  {r1}->{r2}: nesting={nesting:.4f}")

# Overall flat nesting
flat_overall_nesting = compute_nesting_score(flat_labels[0.25], flat_labels[3.0])
hier_overall_nesting = compute_nesting_score(hier_labels[0.25], hier_labels[3.0])
print(f"\nOverall flat nesting (0.25->3.0): {flat_overall_nesting:.4f}")
print(f"Overall hierarchical nesting (0.25->3.0): {hier_overall_nesting:.4f}")

# Save comparison
comparison = {
    "run_id": "flat_vs_hierarchical_77k_20260926",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "n_decisions": n,
    "flat_metrics": flat_metrics,
    "hierarchical_metrics": hier_metrics,
    "branch_purity_advantage": advantages,
    "nmi_hierarchical_vs_flat": {f"res_{res}": float(normalized_mutual_info_score(hier_labels[res], flat_labels[res])) for res in resolutions},
    "flat_transition_nesting": {f"{resolutions[i]}->{resolutions[i+1]}": float(compute_nesting_score(flat_labels[resolutions[i]], flat_labels[resolutions[i+1]])) for i in range(len(resolutions)-1)},
    "flat_overall_nesting": float(flat_overall_nesting),
    "hierarchical_overall_nesting": float(hier_overall_nesting),
    "hierarchical_advantage_over_flat": float(hier_overall_nesting - flat_overall_nesting),
}

output_path = os.path.join(output_dir, "hierarchical_vs_flat_comparison.json")
with open(output_path, 'w') as f:
    json.dump(comparison, f, indent=2)

print(f"\nComparison saved to: {output_path}")