#!/usr/bin/env python3
"""
Hierarchical v1 Protocol Evaluation on 12k Dense Embeddings (ACCEPTED)
Tests the hierarchical_v1 protocol (fine_branch_purity > 0.5, nesting >= 0.99, 
improvement_rate > 0.5, singleton_fraction < 0.01) on the ACCEPTED 12k dense 
embeddings from legal-distance (years 2000-2002).

This is productive work while BLOCKED on 174k dense embeddings.
"""

import json
import numpy as np
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_embeddings_and_metadata():
    """Load the 12k dense embeddings and metadata."""
    embeddings_path = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_dense_comprehensive/embeddings_12k_2000_2002.npy")
    metadata_path = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_dense_comprehensive/metadata_12k_2000_2002.json")
    
    embeddings = np.load(embeddings_path)
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    print(f"Loaded embeddings: {embeddings.shape}")
    print(f"Loaded metadata: {len(metadata)} entries")
    return embeddings, metadata

def compute_branch_purity(cluster_labels, branch_labels):
    """Compute branch purity for a clustering."""
    from collections import Counter
    total_correct = 0
    total = 0
    for cluster_id in np.unique(cluster_labels):
        mask = cluster_labels == cluster_id
        cluster_branches = [branch_labels[i] for i in np.where(mask)[0]]
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            total_correct += most_common
            total += len(cluster_branches)
    return total_correct / total if total > 0 else 0.0

def compute_area_purity(cluster_labels, area_labels):
    """Compute legal_area purity for a clustering."""
    from collections import Counter
    total_correct = 0
    total = 0
    for cluster_id in np.unique(cluster_labels):
        mask = cluster_labels == cluster_id
        cluster_areas = [area_labels[i] for i in np.where(mask)[0] if area_labels[i]]
        if cluster_areas:
            most_common = Counter(cluster_areas).most_common(1)[0][1]
            total_correct += most_common
            total += len(cluster_areas)
    return total_correct / total if total > 0 else 0.0

def run_leiden(embeddings, resolution, k=15, seed=42):
    """Run Leiden clustering on embeddings."""
    try:
        import igraph as ig
        import leidenalg as la
    except ImportError:
        print("igraph/leidenalg not available, using sklearn fallback")
        from sklearn.cluster import KMeans
        n_clusters = max(2, int(len(embeddings) * resolution / 10))
        kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
        return kmeans.fit_predict(embeddings)
    
    # Build k-NN graph
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=min(k+1, len(embeddings)), metric='cosine')
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)
    
    # Build igraph
    edges = []
    weights = []
    for i in range(len(embeddings)):
        for j, idx in enumerate(indices[i][1:]):  # Skip self
            edges.append((i, idx))
            weights.append(1.0 - distances[i][j+1])
    
    g = ig.Graph()
    g.add_vertices(len(embeddings))
    g.add_edges(edges)
    g.es['weight'] = weights
    
    # Run Leiden
    partition = la.find_partition(g, la.RBConfigurationVertexPartition, 
                                   weights='weight', resolution_parameter=resolution,
                                   seed=seed)
    return np.array(partition.membership)

def compute_nesting(coarse_labels, fine_labels):
    """Compute nesting score (fraction of fine clusters fully contained in one coarse cluster)."""
    fine_to_coarse = {}
    for i, (c, f) in enumerate(zip(coarse_labels, fine_labels)):
        if f not in fine_to_coarse:
            fine_to_coarse[f] = c
        elif fine_to_coarse[f] != c:
            fine_to_coarse[f] = -1  # Split across coarse clusters
    
    nested = sum(1 for v in fine_to_coarse.values() if v != -1)
    return nested / len(fine_to_coarse) if fine_to_coarse else 0.0

def compute_zoom_coherence(coarse_labels, fine_labels, branch_labels, area_labels):
    """Compute zoom coherence metrics."""
    from collections import defaultdict
    
    # Map coarse cluster -> list of fine clusters
    coarse_to_fine = defaultdict(set)
    for c, f in zip(coarse_labels, fine_labels):
        coarse_to_fine[c].add(f)
    
    parent_details = {}
    improvements = []
    
    for coarse_id, fine_ids in coarse_to_fine.items():
        if len(fine_ids) <= 1:
            continue
        
        # Coarse purity
        coarse_mask = coarse_labels == coarse_id
        coarse_branches = [branch_labels[i] for i in np.where(coarse_mask)[0]]
        from collections import Counter
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches) if coarse_branches else 0
        
        # Mean child purity
        child_purities = []
        for fine_id in fine_ids:
            fine_mask = fine_labels == fine_id
            fine_branches = [branch_labels[i] for i in np.where(fine_mask)[0]]
            if fine_branches:
                child_purity = Counter(fine_branches).most_common(1)[0][1] / len(fine_branches)
                child_purities.append(child_purity)
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvement = mean_child_purity - coarse_purity
            improvements.append(improvement)
            
            parent_details[str(coarse_id)] = {
                "coarse_purity": coarse_purity,
                "mean_child_purity": mean_child_purity,
                "improvement": improvement,
                "n_children": len(fine_ids)
            }
    
    if not improvements:
        return {"mean_improvement": 0, "improvement_rate": 0, "n_parents": 0, "parent_details": {}}
    
    improvement_rate = sum(1 for i in improvements if i > 0) / len(improvements)
    mean_improvement = np.mean(improvements)
    
    return {
        "mean_improvement": float(mean_improvement),
        "improvement_rate": float(improvement_rate),
        "n_parents": len(improvements),
        "parent_details": parent_details
    }

def run_hierarchical_v1_protocol(embeddings, branch_labels, area_labels, config):
    """Run the hierarchical_v1 protocol with given config."""
    coarse_res = config.get("coarse_res", 0.25)
    base_sub_res = config.get("base_sub_res", 3.0)
    min_cluster_size = config.get("min_cluster_size", 20)
    max_subclusters = config.get("max_subclusters", 20)
    adaptive = config.get("adaptive_sub_res", False)
    
    # Coarse clustering
    coarse_labels = run_leiden(embeddings, coarse_res)
    
    # Check coarse cluster sizes
    unique_coarse, coarse_counts = np.unique(coarse_labels, return_counts=True)
    valid_coarse = unique_coarse[coarse_counts >= min_cluster_size]
    
    if len(valid_coarse) == 0:
        return {"error": "No valid coarse clusters"}
    
    # Fine clustering per coarse cluster
    fine_labels = np.full(len(embeddings), -1, dtype=int)
    fine_cluster_id = 0
    
    for c_id in valid_coarse:
        mask = coarse_labels == c_id
        sub_embeddings = embeddings[mask]
        
        if len(sub_embeddings) < min_cluster_size:
            # Assign all to one fine cluster
            fine_labels[mask] = fine_cluster_id
            fine_cluster_id += 1
            continue
        
        if adaptive:
            # Adaptive: resolution proportional to log(cluster_size)
            sub_res = base_sub_res * np.log(len(sub_embeddings) / min_cluster_size + 1)
            sub_res = min(sub_res, base_sub_res * 2)
        else:
            sub_res = base_sub_res
        
        sub_labels = run_leiden(sub_embeddings, sub_res)
        
        # Limit subclusters per parent
        unique_sub, sub_counts = np.unique(sub_labels, return_counts=True)
        if len(unique_sub) > max_subclusters:
            # Keep largest subclusters
            sorted_sub = sorted(zip(unique_sub, sub_counts), key=lambda x: x[1], reverse=True)
            keep_sub = set(s[0] for s in sorted_sub[:max_subclusters])
            new_sub_labels = np.full_like(sub_labels, -1)
            new_id = 0
            for old_id in unique_sub:
                if old_id in keep_sub:
                    new_sub_labels[sub_labels == old_id] = new_id
                    new_id += 1
            # Merge small ones into largest
            if new_id > 0:
                largest = sorted_sub[0][0]
                new_sub_labels[new_sub_labels == -1] = 0
            sub_labels = new_sub_labels
        
        fine_labels[mask] = sub_labels + fine_cluster_id
        fine_cluster_id += len(np.unique(sub_labels))
    
    # Handle unassigned (small coarse clusters)
    unassigned_mask = fine_labels == -1
    if np.any(unassigned_mask):
        fine_labels[unassigned_mask] = fine_cluster_id
        fine_cluster_id += 1
    
    # Compute metrics
    coarse_purity = compute_branch_purity(coarse_labels, branch_labels)
    fine_purity = compute_branch_purity(fine_labels, branch_labels)
    coarse_area_purity = compute_area_purity(coarse_labels, area_labels)
    fine_area_purity = compute_area_purity(fine_labels, area_labels)
    
    nesting = compute_nesting(coarse_labels, fine_labels)
    zoom = compute_zoom_coherence(coarse_labels, fine_labels, branch_labels, area_labels)
    
    # Fragmentation
    unique_fine, fine_counts = np.unique(fine_labels, return_counts=True)
    singleton_fraction = np.sum(fine_counts == 1) / len(fine_counts)
    median_size = np.median(fine_counts)
    
    # Hierarchical v1 pass criteria
    hierarchical_v1_pass = (
        nesting >= 0.99 and
        fine_purity > 0.5 and
        zoom["improvement_rate"] > 0.5 and
        singleton_fraction < 0.01
    )
    
    return {
        "config": config,
        "n_decisions": len(embeddings),
        "coarse_clusters": len(valid_coarse),
        "fine_clusters": fine_cluster_id,
        "coarse_branch_purity": coarse_purity,
        "fine_branch_purity": fine_purity,
        "coarse_area_purity": coarse_area_purity,
        "fine_area_purity": fine_area_purity,
        "branch_improvement": fine_purity - coarse_purity,
        "area_improvement": fine_area_purity - coarse_area_purity,
        "strict_nesting": nesting,
        "zoom_branch": zoom,
        "fragmentation": {
            "n_clusters": fine_cluster_id,
            "median_size": float(median_size),
            "mean_size": float(np.mean(fine_counts)),
            "singleton_fraction": float(singleton_fraction)
        },
        "hierarchical_v1_pass": hierarchical_v1_pass
    }

def main():
    print("=" * 80)
    print("HIERARCHICAL V1 PROTOCOL EVALUATION ON 12K DENSE EMBEDDINGS (ACCEPTED)")
    print("=" * 80)
    
    embeddings, metadata = load_embeddings_and_metadata()
    
    # Extract branch and area labels
    branch_labels = [m.get("branch", "unknown") for m in metadata]
    area_labels = [m.get("legal_area", "") for m in metadata]
    
    print(f"\nBranch distribution:")
    from collections import Counter
    branch_dist = Counter(branch_labels)
    for b, c in branch_dist.most_common():
        print(f"  {b}: {c}")
    
    print(f"\nLegal area coverage: {sum(1 for a in area_labels if a)} / {len(area_labels)}")
    
    # Test configurations
    configs = [
        # adaptive=False configs (v28 showed this crosses 50% threshold)
        {"name": "adaptive_false_base3.0", "coarse_res": 0.25, "base_sub_res": 3.0, "min_cluster_size": 5, "max_subclusters": 20, "adaptive_sub_res": False},
        {"name": "adaptive_false_base2.5", "coarse_res": 0.25, "base_sub_res": 2.5, "min_cluster_size": 5, "max_subclusters": 20, "adaptive_sub_res": False},
        {"name": "adaptive_false_base2.0", "coarse_res": 0.25, "base_sub_res": 2.0, "min_cluster_size": 5, "max_subclusters": 20, "adaptive_sub_res": False},
        {"name": "adaptive_false_base1.5", "coarse_res": 0.25, "base_sub_res": 1.5, "min_cluster_size": 5, "max_subclusters": 20, "adaptive_sub_res": False},
        {"name": "adaptive_false_base1.0", "coarse_res": 0.25, "base_sub_res": 1.0, "min_cluster_size": 5, "max_subclusters": 20, "adaptive_sub_res": False},
        
        # adaptive=True configs (for comparison)
        {"name": "adaptive_true_base3.0", "coarse_res": 0.25, "base_sub_res": 3.0, "min_cluster_size": 20, "max_subclusters": 20, "adaptive_sub_res": True},
        {"name": "adaptive_true_base2.0", "coarse_res": 0.25, "base_sub_res": 2.0, "min_cluster_size": 20, "max_subclusters": 20, "adaptive_sub_res": True},
        {"name": "adaptive_true_base1.5", "coarse_res": 0.25, "base_sub_res": 1.5, "min_cluster_size": 20, "max_subclusters": 20, "adaptive_sub_res": True},
        
        # Different coarse resolutions
        {"name": "adaptive_false_coarse0.5_base3.0", "coarse_res": 0.5, "base_sub_res": 3.0, "min_cluster_size": 5, "max_subclusters": 20, "adaptive_sub_res": False},
        {"name": "adaptive_false_coarse0.5_base2.0", "coarse_res": 0.5, "base_sub_res": 2.0, "min_cluster_size": 5, "max_subclusters": 20, "adaptive_sub_res": False},
    ]
    
    results = {}
    for config in configs:
        print(f"\n--- Testing {config['name']} ---")
        result = run_hierarchical_v1_protocol(embeddings, branch_labels, area_labels, config)
        results[config['name']] = result
        
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            continue
        
        print(f"  Coarse clusters: {result['coarse_clusters']}")
        print(f"  Fine clusters: {result['fine_clusters']}")
        print(f"  Coarse branch purity: {result['coarse_branch_purity']:.4f}")
        print(f"  Fine branch purity: {result['fine_branch_purity']:.4f}")
        print(f"  Coarse area purity: {result['coarse_area_purity']:.4f}")
        print(f"  Fine area purity: {result['fine_area_purity']:.4f}")
        print(f"  Branch improvement: {result['branch_improvement']:.4f}")
        print(f"  Nesting: {result['strict_nesting']:.4f}")
        print(f"  Zoom improvement_rate: {result['zoom_branch']['improvement_rate']:.4f}")
        print(f"  Zoom mean_improvement: {result['zoom_branch']['mean_improvement']:.4f}")
        print(f"  Singleton fraction: {result['fragmentation']['singleton_fraction']:.4f}")
        print(f"  Median cluster size: {result['fragmentation']['median_size']:.1f}")
        print(f"  HIERARCHICAL_V1_PASS: {result['hierarchical_v1_pass']}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY: HIERARCHICAL_V1 PASS STATUS")
    print("=" * 80)
    for name, result in results.items():
        if "error" not in result:
            pass_status = "PASS" if result['hierarchical_v1_pass'] else "FAIL"
            print(f"  {name:40s} {pass_status}  (fine_purity={result['fine_branch_purity']:.3f}, "
                  f"impr_rate={result['zoom_branch']['improvement_rate']:.3f}, "
                  f"nesting={result['strict_nesting']:.3f}, "
                  f"singletons={result['fragmentation']['singleton_fraction']:.3f})")
    
    # Find best config
    best = None
    best_score = -1
    for name, result in results.items():
        if "error" not in result and result['hierarchical_v1_pass']:
            score = result['fine_branch_purity'] + result['zoom_branch']['improvement_rate']
            if score > best_score:
                best_score = score
                best = name
    
    if best:
        print(f"\nBEST PASSING CONFIG: {best}")
    else:
        print(f"\nNO CONFIG PASSES HIERARCHICAL_V1 PROTOCOL")
        # Show closest
        for name, result in results.items():
            if "error" not in result:
                gaps = []
                if result['strict_nesting'] < 0.99: gaps.append(f"nesting={result['strict_nesting']:.3f}")
                if result['fine_branch_purity'] <= 0.5: gaps.append(f"fine_purity={result['fine_branch_purity']:.3f}")
                if result['zoom_branch']['improvement_rate'] <= 0.5: gaps.append(f"impr_rate={result['zoom_branch']['improvement_rate']:.3f}")
                if result['fragmentation']['singleton_fraction'] >= 0.01: gaps.append(f"singletons={result['fragmentation']['singleton_fraction']:.3f}")
                print(f"  {name:40s} gaps: {', '.join(gaps)}")
    
    # Save results
    output = {
        "run_id": f"hierarchical_v1_12k_dense_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "direction_version": 29,
        "sample": "12k dense embeddings (years 2000,2001,2002, ACCEPTED)",
        "embedding_dim": 768,
        "hypothesis": "Adaptive=False constrained hierarchical Leiden achieves hierarchical_v1 PASS at 12k scale",
        "frozen_metric": "fine_branch_purity > 0.5, nesting >= 0.99, improvement_rate > 0.5, singleton_fraction < 0.01",
        "success_rule": "hierarchical_v1_pass = all four criteria met",
        "results": results,
        "best_config": best
    }
    
    output_path = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_hierarchical_v1_protocol_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    return output

if __name__ == "__main__":
    main()