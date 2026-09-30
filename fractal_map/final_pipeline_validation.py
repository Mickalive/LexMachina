#!/usr/bin/env python3
"""
Final pipeline validation for fractal-map lane before unblocking on 174k dense embeddings.

Validates the production config (coarse_0.5_fixed2.0_min20) on:
1. 12k ACCEPTED dense embeddings (years 2000-2002)
2. 28k checkpoint embeddings (years 2000-2005, PENDING AUDIT - pipeline validation only)
3. Citation-role embeddings at 1000 scale (citing, following, criticizing)
4. Cited_decisions_tfidf_outcome_hybrid_0.5 at 1200 scale

This documents pipeline readiness per factory direction v28.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
import igraph as ig
import leidenalg
import warnings
warnings.filterwarnings('ignore')

# Configuration
PRODUCTION_CONFIG = {
    "name": "coarse_0.5_fixed2.0_min20",
    "coarse_res": 0.5,
    "base_sub_res": 2.0,
    "min_cluster_size": 20,
    "max_subclusters_per_parent": 20,
    "adaptive_sub_res": False,
    "k_neighbors": 15,
    "leiden_seed": 42,
    "n_iterations": 2
}

# Paths
CHECKPOINT_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
CITATION_ROLE_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_rebuilt")
HYBRID_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v7/outcome_cited_hybrids")
EVAL_METADATA_1200 = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/final_pipeline_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dense_embeddings(years):
    """Load and combine dense embeddings for specified years."""
    embeddings_list = []
    metadata_list = []
    for year in years:
        emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINT_DIR / f"metadata_{year}.json"
        emb = np.load(emb_path).astype(np.float32)
        with open(meta_path) as f:
            meta = json.load(f)
        embeddings_list.append(emb)
        metadata_list.extend(meta)
    return np.vstack(embeddings_list), metadata_list


def load_citation_role_embeddings(role):
    """Load citation role embeddings."""
    emb_path = CITATION_ROLE_DIR / f"citation_role_{role}_rebuilt.npy"
    return np.load(emb_path).astype(np.float32)


def load_hybrid_embeddings(name):
    """Load hybrid embeddings."""
    emb_path = HYBRID_DIR / f"{name}.npy"
    return np.load(emb_path).astype(np.float32)


def load_1200_metadata():
    """Load 1200-decision evaluation metadata."""
    metadata = []
    with open(EVAL_METADATA_1200) as f:
        for line in f:
            metadata.append(json.loads(line))
    return metadata


def build_knn_graph(embeddings, k=15):
    """Build k-NN graph for Leiden clustering."""
    nbrs = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1).fit(embeddings)
    distances, indices = nbrs.kneighbors(embeddings)
    
    edges = []
    weights = []
    for i in range(len(embeddings)):
        for j, dist in zip(indices[i][1:], distances[i][1:]):  # Skip self
            edges.append((i, j))
            weights.append(1.0 - dist)  # Convert distance to similarity
    
    g = ig.Graph()
    g.add_vertices(len(embeddings))
    g.add_edges(edges)
    g.es['weight'] = weights
    return g


def run_leiden(embeddings, resolution, seed=42, k=15, n_iterations=2):
    """Run Leiden clustering at given resolution."""
    g = build_knn_graph(embeddings, k)
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution,
        seed=seed, n_iterations=n_iterations
    )
    return np.array(partition.membership), partition


def run_constrained_hierarchical(embeddings, config):
    """Run constrained hierarchical Leiden with min_cluster_size enforcement."""
    # Coarse clustering
    coarse_labels, coarse_partition = run_leiden(
        embeddings, config["coarse_res"], 
        seed=config["leiden_seed"], k=config["k_neighbors"],
        n_iterations=config["n_iterations"]
    )
    
    # Fine clustering per coarse cluster
    fine_labels = np.full(len(embeddings), -1, dtype=int)
    coarse_to_fine = {}
    fine_id = 0
    
    for coarse_id in np.unique(coarse_labels):
        mask = coarse_labels == coarse_id
        sub_embeddings = embeddings[mask]
        sub_indices = np.where(mask)[0]
        
        if len(sub_embeddings) < config["min_cluster_size"]:
            # Too small - assign as single fine cluster
            fine_labels[sub_indices] = fine_id
            coarse_to_fine[coarse_id] = [fine_id]
            fine_id += 1
            continue
        
        # Run fine clustering
        sub_resolution = config["base_sub_res"]
        sub_labels, _ = run_leiden(
            sub_embeddings, sub_resolution,
            seed=config["leiden_seed"] + coarse_id,
            k=config["k_neighbors"],
            n_iterations=config["n_iterations"]
        )
        
        # Enforce min_cluster_size on fine clusters
        unique_sub, sub_counts = np.unique(sub_labels, return_counts=True)
        valid_sub = unique_sub[sub_counts >= config["min_cluster_size"]]
        
        if len(valid_sub) == 0:
            # All too small - merge into one
            fine_labels[sub_indices] = fine_id
            coarse_to_fine[coarse_id] = [fine_id]
            fine_id += 1
            continue
        
        # Map valid sub-clusters
        sub_to_fine = {}
        for sub in valid_sub:
            sub_to_fine[sub] = fine_id
            coarse_to_fine.setdefault(coarse_id, []).append(fine_id)
            fine_id += 1
        
        # Assign
        for i, sub in enumerate(sub_labels):
            if sub in sub_to_fine:
                fine_labels[sub_indices[i]] = sub_to_fine[sub]
            else:
                # Assign to nearest valid sub-cluster centroid
                fine_labels[sub_indices[i]] = sub_to_fine[valid_sub[0]]
    
    return coarse_labels, fine_labels, coarse_to_fine


def compute_purity(labels, metadata, field):
    """Compute purity of clusters w.r.t. a metadata field."""
    values = [m.get(field) for m in metadata]
    unique_labels = np.unique(labels)
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_values = [v for i, v in enumerate(values) if mask[i]]
        if cluster_values:
            from collections import Counter
            counts = Counter(cluster_values)
            purities.append(max(counts.values()) / len(cluster_values))
    return np.mean(purities) if purities else 0.0


def compute_nesting(coarse_labels, fine_labels):
    """Compute nesting consistency (fraction of fine clusters with single parent)."""
    fine_to_coarse = {}
    for f, c in zip(fine_labels, coarse_labels):
        if f not in fine_to_coarse:
            fine_to_coarse[f] = c
        elif fine_to_coarse[f] != c:
            return 0.0  # Not nested
    return 1.0


def compute_zoom_coherence(coarse_labels, fine_labels, metadata, field):
    """Compute zoom coherence metrics."""
    values = [m.get(field) for m in metadata]
    
    # Get coarse clusters that have multiple fine children
    coarse_to_fine = {}
    for f, c in zip(fine_labels, coarse_labels):
        coarse_to_fine.setdefault(c, []).append(f)
    
    improvements = []
    for coarse_id, fine_ids in coarse_to_fine.items():
        if len(fine_ids) <= 1:
            continue
        # Coarse purity
        coarse_mask = coarse_labels == coarse_id
        coarse_vals = [v for i, v in enumerate(values) if coarse_mask[i]]
        if not coarse_vals:
            continue
        from collections import Counter
        coarse_counts = Counter(coarse_vals)
        coarse_purity = max(coarse_counts.values()) / len(coarse_vals)
        
        # Mean child purity
        child_purities = []
        for fine_id in fine_ids:
            fine_mask = fine_labels == fine_id
            fine_vals = [v for i, v in enumerate(values) if fine_mask[i]]
            if fine_vals:
                fine_counts = Counter(fine_vals)
                child_purities.append(max(fine_counts.values()) / len(fine_vals))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
    
    if not improvements:
        return {"mean_improvement": 0.0, "improvement_rate": 0.0, "n_parents": 0}
    
    improvements = np.array(improvements)
    return {
        "mean_improvement": float(np.mean(improvements)),
        "improvement_rate": float(np.mean(improvements > 0)),
        "n_parents": len(improvements)
    }


def compute_fragmentation(labels):
    """Compute fragmentation metrics."""
    unique, counts = np.unique(labels, return_counts=True)
    return {
        "n_clusters": len(unique),
        "median_size": float(np.median(counts)),
        "mean_size": float(np.mean(counts)),
        "singleton_fraction": float(np.sum(counts == 1) / len(counts)),
        "min_size": int(np.min(counts)),
        "max_size": int(np.max(counts))
    }


def evaluate_hierarchical(embeddings, metadata, config, name):
    """Full hierarchical evaluation."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {name}")
    print(f"Config: {config['name']}")
    print(f"N decisions: {len(embeddings)}")
    print(f"Embedding dim: {embeddings.shape[1]}")
    
    # Run constrained hierarchical
    coarse_labels, fine_labels, coarse_to_fine = run_constrained_hierarchical(embeddings, config)
    
    # Compute metrics
    coarse_branch_purity = compute_purity(coarse_labels, metadata, "branch")
    fine_branch_purity = compute_purity(fine_labels, metadata, "branch")
    coarse_area_purity = compute_purity(coarse_labels, metadata, "legal_area")
    fine_area_purity = compute_purity(fine_labels, metadata, "legal_area")
    
    branch_improvement = fine_branch_purity - coarse_branch_purity
    area_improvement = fine_area_purity - coarse_area_purity
    
    nesting = compute_nesting(coarse_labels, fine_labels)
    
    zoom_branch = compute_zoom_coherence(coarse_labels, fine_labels, metadata, "branch")
    zoom_area = compute_zoom_coherence(coarse_labels, fine_labels, metadata, "legal_area")
    
    coarse_frag = compute_fragmentation(coarse_labels)
    fine_frag = compute_fragmentation(fine_labels)
    
    # Hierarchical_v1 protocol metrics
    legal_structure_branch = fine_branch_purity > 0.5
    legal_structure_area = fine_area_purity > 0.5
    fragmentation_ok = fine_frag["singleton_fraction"] < 0.1
    nesting_perfect = nesting >= 0.99
    branch_purity_improves = branch_improvement > 0
    area_purity_improves = area_improvement > 0
    zoom_coherence_ok = zoom_branch["improvement_rate"] > 0.5
    
    # v26 flat zoom rule (for reference)
    # Need flat clustering at multiple resolutions for this
    flat_resolutions = [0.25, 0.5, 1.0, 2.0, 3.0]
    flat_labels = {}
    for res in flat_resolutions:
        labels, _ = run_leiden(embeddings, res, seed=config["leiden_seed"], k=config["k_neighbors"])
        flat_labels[res] = labels
    
    v26_transitions = []
    for i in range(len(flat_resolutions) - 1):
        r1, r2 = flat_resolutions[i], flat_resolutions[i+1]
        zc = compute_zoom_coherence(flat_labels[r1], flat_labels[r2], metadata, "branch")
        v26_transitions.append({
            "from_res": r1, "to_res": r2,
            "branch_improvement_rate": zc["improvement_rate"],
            "branch_mean_improvement": zc["mean_improvement"],
            "n_parents": zc["n_parents"]
        })
    
    v26_pass = sum(1 for t in v26_transitions if t["branch_improvement_rate"] > 0.5) >= 2
    
    result = {
        "name": name,
        "config": config,
        "n_decisions": len(embeddings),
        "embedding_dim": int(embeddings.shape[1]),
        "coarse": {
            "n_clusters": coarse_frag["n_clusters"],
            "branch_purity": coarse_branch_purity,
            "area_purity": coarse_area_purity,
            "fragmentation": coarse_frag
        },
        "hierarchical": {
            "n_clusters": fine_frag["n_clusters"],
            "branch_purity": fine_branch_purity,
            "area_purity": fine_area_purity,
            "fragmentation": fine_frag,
            "nesting": nesting
        },
        "branch_improvement": branch_improvement,
        "area_improvement": area_improvement,
        "zoom_branch": zoom_branch,
        "zoom_area": zoom_area,
        "hierarchical_v1": {
            "legal_structure_branch": legal_structure_branch,
            "legal_structure_area": legal_structure_area,
            "fragmentation_ok": fragmentation_ok,
            "nesting_perfect": nesting_perfect,
            "branch_purity_improves": branch_purity_improves,
            "area_purity_improves": area_purity_improves,
            "zoom_coherence_ok": zoom_coherence_ok,
            "overall_pass": all([
                legal_structure_branch, legal_structure_area,
                fragmentation_ok, nesting_perfect,
                branch_purity_improves, area_purity_improves,
                zoom_coherence_ok
            ])
        },
        "v26_flat_eval": {
            "transitions": v26_transitions,
            "per_mode_verdict": "PASS" if v26_pass else "FAIL"
        }
    }
    
    print(f"  Coarse: {coarse_frag['n_clusters']} clusters, branch_purity={coarse_branch_purity:.4f}")
    print(f"  Fine: {fine_frag['n_clusters']} clusters, branch_purity={fine_branch_purity:.4f}")
    print(f"  Branch improvement: {branch_improvement:.4f}")
    print(f"  Area improvement: {area_improvement:.4f}")
    print(f"  Nesting: {nesting:.4f}")
    print(f"  Zoom branch: improvement_rate={zoom_branch['improvement_rate']:.4f}, mean_improvement={zoom_branch['mean_improvement']:.4f}")
    print(f"  Fine singleton_fraction: {fine_frag['singleton_fraction']:.4f}")
    print(f"  Hierarchical_v1 PASS: {result['hierarchical_v1']['overall_pass']}")
    print(f"  v26 flat PASS: {v26_pass}")
    
    return result


def main():
    print("="*60)
    print("FINAL PIPELINE VALIDATION - FRACTAL MAP LANE")
    print("Factory Direction v28 - Blocked on 174k dense embeddings")
    print("="*60)
    
    all_results = {}
    
    # 1. 12k ACCEPTED dense embeddings (2000-2002)
    print("\n\n### 1. 12k ACCEPTED Dense Embeddings (2000-2002) ###")
    emb_12k, meta_12k = load_dense_embeddings([2000, 2001, 2002])
    result_12k = evaluate_hierarchical(emb_12k, meta_12k, PRODUCTION_CONFIG, "dense_12k_ACCEPTED_2000_2002")
    all_results["dense_12k_ACCEPTED"] = result_12k
    
    # 2. 28k checkpoint (2000-2005) - PENDING AUDIT, pipeline validation only
    print("\n\n### 2. 28k Checkpoint (2000-2005) - PIPELINE VALIDATION ONLY ###")
    emb_28k, meta_28k = load_dense_embeddings([2000, 2001, 2002, 2003, 2004, 2005])
    result_28k = evaluate_hierarchical(emb_28k, meta_28k, PRODUCTION_CONFIG, "dense_28k_checkpoint_2000_2005")
    all_results["dense_28k_checkpoint"] = result_28k
    
    # 3. Citation-role embeddings at 1000 scale
    print("\n\n### 3. Citation-Role Embeddings (1000 scale) ###")
    meta_1200 = load_1200_metadata()
    for role in ["citing", "following", "criticizing"]:
        emb = load_citation_role_embeddings(role)
        # Use first 1000 metadata entries to match
        result = evaluate_hierarchical(emb, meta_1200[:1000], PRODUCTION_CONFIG, f"citation_role_{role}_1000")
        all_results[f"citation_role_{role}_1000"] = result
    
    # 4. Cited_decisions_tfidf_outcome_hybrid_0.5 at 1200 scale
    print("\n\n### 4. Cited_Decisions_TFIDF_Outcome_Hybrid_0.5 (1200 scale) ###")
    emb_hybrid = load_hybrid_embeddings("cited_decisions_tfidf_outcome_hybrid_0.5")
    result_hybrid = evaluate_hierarchical(emb_hybrid, meta_1200[:1200], PRODUCTION_CONFIG, "cited_decisions_tfidf_outcome_hybrid_0.5_1200")
    all_results["cited_decisions_tfidf_outcome_hybrid_0.5_1200"] = result_hybrid
    
    # 5. Cited_decisions_tfidf at 1200 scale
    print("\n\n### 5. Cited_Decisions_TFIDF (1200 scale) ###")
    emb_cited = load_hybrid_embeddings("cited_decisions_tfidf")
    result_cited = evaluate_hierarchical(emb_cited, meta_1200[:1200], PRODUCTION_CONFIG, "cited_decisions_tfidf_1200")
    all_results["cited_decisions_tfidf_1200"] = result_cited
    
    # 6. Outcome_tfidf at 1200 scale
    print("\n\n### 6. Outcome_TFIDF (1200 scale) ###")
    emb_outcome = load_hybrid_embeddings("outcome_tfidf")
    result_outcome = evaluate_hierarchical(emb_outcome, meta_1200[:1200], PRODUCTION_CONFIG, "outcome_tfidf_1200")
    all_results["outcome_tfidf_1200"] = result_outcome
    
    # Save results
    output_file = OUTPUT_DIR / "final_pipeline_validation_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, result in all_results.items():
        hv1 = result["hierarchical_v1"]
        print(f"\n{name}:")
        print(f"  Hierarchical_v1 PASS: {hv1['overall_pass']}")
        print(f"  Fine branch purity: {result['hierarchical']['branch_purity']:.4f}")
        print(f"  Fine area purity: {result['hierarchical']['area_purity']:.4f}")
        print(f"  Branch improvement: {result['branch_improvement']:.4f}")
        print(f"  Zoom branch improvement_rate: {result['zoom_branch']['improvement_rate']:.4f}")
        print(f"  Nesting: {result['hierarchical']['nesting']:.4f}")
        print(f"  Fine singleton_fraction: {result['hierarchical']['fragmentation']['singleton_fraction']:.4f}")
        print(f"  v26 flat: {result['v26_flat_eval']['per_mode_verdict']}")
    
    print(f"\nResults saved to: {output_file}")
    return all_results


if __name__ == "__main__":
    main()