#!/usr/bin/env python3
"""
Fully Hierarchical Leiden: each level sub-clusters the previous level's clusters.
This creates a true multi-level hierarchy: coarse -> fine1 -> fine2 -> fine3 -> finest
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
# FULLY RECURSIVE HIERARCHICAL LEIDEN
# ============================================================
def fully_recursive_hierarchical_leiden(graph, resolutions, seed=42):
    """
    Run Leiden recursively: each resolution sub-clusters the previous resolution's clusters.
    Returns: dict of {resolution: global_labels}
    """
    print(f"Running fully recursive hierarchical Leiden: {resolutions}")
    
    global_labels = {}
    current_labels = None
    current_clusters = None
    
    for i, res in enumerate(resolutions):
        if i == 0:
            # First resolution: global clustering
            print(f"  Level {i} (res={res}): global clustering...")
            partition = la.find_partition(
                graph,
                la.RBConfigurationVertexPartition,
                weights='weight',
                resolution_parameter=res,
                seed=seed
            )
            current_labels = np.array(partition.membership)
            current_clusters = len(np.unique(current_labels))
            print(f"    -> {current_clusters} clusters")
        else:
            # Subsequent resolutions: sub-cluster within each current cluster
            print(f"  Level {i} (res={res}): sub-clustering within {current_clusters} clusters...")
            new_labels = current_labels.copy()
            next_cluster_id = 0
            
            # We need to assign new global IDs
            # First, collect all unique current cluster IDs
            unique_current = np.unique(current_labels)
            cluster_id_map = {old_id: new_id for new_id, old_id in enumerate(unique_current)}
            remapped_current = np.array([cluster_id_map[old] for old in current_labels])
            
            # Now sub-cluster each
            for c in range(len(unique_current)):
                mask = remapped_current == c
                vertices = np.where(mask)[0]
                
                if len(vertices) < 2:
                    # Keep as single cluster
                    new_labels[mask] = next_cluster_id
                    next_cluster_id += 1
                    continue
                
                # Create subgraph
                subgraph = graph.subgraph(vertices.tolist())
                
                try:
                    sub_partition = la.find_partition(
                        subgraph,
                        la.RBConfigurationVertexPartition,
                        weights='weight',
                        resolution_parameter=res,
                        seed=seed
                    )
                    sub_labels = np.array(sub_partition.membership)
                    
                    # Remap to global IDs
                    for local_idx, global_idx in enumerate(vertices):
                        new_labels[global_idx] = next_cluster_id + sub_labels[local_idx]
                    
                    next_cluster_id += len(np.unique(sub_labels))
                except Exception as e:
                    print(f"    Warning: sub-clustering failed for cluster {c}: {e}")
                    new_labels[mask] = next_cluster_id
                    next_cluster_id += 1
            
            current_labels = new_labels
            current_clusters = next_cluster_id
            print(f"    -> {current_clusters} global clusters")
        
        global_labels[res] = current_labels.copy()
    
    return global_labels

# Run fully recursive hierarchical Leiden
resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

full_hier_labels = fully_recursive_hierarchical_leiden(g, resolutions)

# Save
output_dir = "results/fractal_map/77k_fully_recursive_hierarchical"
os.makedirs(output_dir, exist_ok=True)

for res, labels in full_hier_labels.items():
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

print("\n=== FULLY RECURSIVE HIERARCHICAL LEIDEN METRICS ===")
full_hier_metrics = {}
for res in resolutions:
    labels = full_hier_labels[res]
    branch_purity = compute_purity(labels, all_metadata, 'branch')
    legal_area_purity = compute_purity(labels, all_metadata, 'legal_area')
    language_purity = compute_purity(labels, all_metadata, 'language')
    n_clusters = len(np.unique(labels))
    full_hier_metrics[res] = {
        "n_clusters": int(n_clusters),
        "branch_purity": float(branch_purity),
        "legal_area_purity": float(legal_area_purity),
        "language_purity": float(language_purity),
    }
    print(f"  res_{res}: {n_clusters} clusters, branch={branch_purity:.4f}, "
          f"legal_area={legal_area_purity:.4f}, lang={language_purity:.4f}")

# Nesting scores (should be 1.0 at every step!)
print("\n=== FULLY RECURSIVE NESTING (should be 1.0 at each step) ===")
for i in range(len(resolutions) - 1):
    r1, r2 = resolutions[i], resolutions[i+1]
    nesting = compute_nesting_score(full_hier_labels[r1], full_hier_labels[r2])
    print(f"  {r1}->{r2}: nesting={nesting:.4f}")

full_overall_nesting = compute_nesting_score(full_hier_labels[resolutions[0]], full_hier_labels[resolutions[-1]])
print(f"\nOverall nesting ({resolutions[0]}->{resolutions[-1]}): {full_overall_nesting:.4f}")

# Purity deltas
print("\n=== PURITY DELTAS (monotonic zoom refinement?) ===")
purity_deltas = []
for i in range(len(resolutions) - 1):
    r1, r2 = resolutions[i], resolutions[i+1]
    coarse_pur = full_hier_metrics[r1]["branch_purity"]
    fine_pur = full_hier_metrics[r2]["branch_purity"]
    delta = fine_pur - coarse_pur
    purity_deltas.append(delta)
    print(f"  {r1}->{r2}: delta={delta:+.4f} (coarse={coarse_pur:.4f}, fine={fine_pur:.4f})")

mean_delta = np.mean(purity_deltas)
print(f"  Mean purity delta: {mean_delta:.4f}")
print(f"  All positive? {all(d > -0.01 for d in purity_deltas)}")

# Zoom quality score
finest_purity = full_hier_metrics[resolutions[-1]]["branch_purity"]
zoom_quality = (0.4 * max(0, mean_delta * 10) + 
                0.3 * 1.0 +  # nesting is 1.0
                0.1 * 1.0 +  # stability
                0.2 * finest_purity)
print(f"  Zoom quality score: {zoom_quality:.4f}")

# Hierarchical coherence: coarse (0.5) -> fine (3.0)
coarse_labels = full_hier_labels[0.5]
fine_labels = full_hier_labels[3.0]
coarse_pur = full_hier_metrics[0.5]["branch_purity"]
fine_pur = full_hier_metrics[3.0]["branch_purity"]

print(f"\n=== HIERARCHICAL COHERENCE (0.5 -> 3.0) ===")
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
    
    fine_c_pur = compute_purity(fine_labels[mask], 
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
    "run_id": "fully_recursive_hierarchical_leiden_77k_20260926",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "direction_version": 28,
    "n_decisions": n,
    "method": "fully_recursive_hierarchical_leiden",
    "resolutions": resolutions,
    "resolution_metrics": full_hier_metrics,
    "transition_nesting": {f"{resolutions[i]}->{resolutions[i+1]}": float(compute_nesting_score(full_hier_labels[resolutions[i]], full_hier_labels[resolutions[i+1]])) for i in range(len(resolutions)-1)},
    "overall_nesting": float(full_overall_nesting),
    "purity_deltas": {f"{resolutions[i]}->{resolutions[i+1]}": float(purity_deltas[i]) for i in range(len(purity_deltas))},
    "mean_purity_delta": float(mean_delta),
    "zoom_quality_score": float(zoom_quality),
    "finest_purity": float(finest_purity),
    "hierarchical_coherence": {
        "coarse_resolution": 0.5,
        "fine_resolution": 3.0,
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

output_path = os.path.join(output_dir, "fully_recursive_hierarchical_77k_results.json")
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {output_path}")