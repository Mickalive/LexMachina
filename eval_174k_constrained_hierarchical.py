#!/usr/bin/env python3
"""
Constrained Hierarchical Leiden Evaluation at 174k scale for all TF-IDF representations.

Hypothesis: Constrained hierarchical Leiden (min_cluster_size=3) on 174k TF-IDF embeddings
produces zoom refinement (improvement_rate > 0.57) and fine_branch_purity > 0.5
for legally meaningful representations.

Frozen metrics before inspection:
- Sample: 174k decisions (full corpus metadata_174k_full.json, n=173,963)
- Embeddings: 8 TF-IDF representations (128-dim, from committed cache)
- Clustering: Leiden (k=15, seed=42) at resolutions [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
- Constraint: min_cluster_size=3 for coarse clusters in zoom evaluation
- Primary metric: per-transition-average zoom improvement rate (branch purity)
- Secondary metric: fine_branch_purity at resolution 3.0 (hierarchical_v1 protocol)
- Success rule: improvement_rate >= 0.57 AND fine_branch_purity > 0.5

This directly tests the hierarchical_v1 protocol mentioned in factory direction v29.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph

# ============================================================
# FROZEN CONFIGURATION (do not change after seeing results)
# ============================================================
RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3
K = 15
SEED = 42
IMPROVEMENT_RATE_THRESHOLD = 0.57  # from factory direction "57-90%"
FINE_BRANCH_PURITY_THRESHOLD = 0.5  # hierarchical_v1 protocol
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
METADATA_PATH = Path("/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/metadata_174k_eval.json")

# Embedding paths
TFIDF_DIR = Path("/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/tfidf_embeddings")
LEGAL_TFIDF_DIR = Path("/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")

REPRESENTATIONS = {
    "regeste_tfidf": TFIDF_DIR / "regeste_tfidf.npy",
    "full_text_tfidf_light": TFIDF_DIR / "full_text_tfidf_light.npy",
    "regeste_full_text_hybrid_0.5": TFIDF_DIR / "regeste_full_text_hybrid_0.5.npy",
    "regeste_full_text_hybrid_0.7": TFIDF_DIR / "regeste_full_text_hybrid_0.7.npy",
    "cited_decisions_tfidf": LEGAL_TFIDF_DIR / "cited_decisions_tfidf.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.5": LEGAL_TFIDF_DIR / "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.7": LEGAL_TFIDF_DIR / "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    "outcome_tfidf": LEGAL_TFIDF_DIR / "outcome_tfidf.npy",
}

OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# FUNCTIONS
# ============================================================

def leiden_clustering(embeddings, resolution=1.0, k=K, seed=SEED):
    """Run Leiden clustering on embeddings."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    n = len(embeddings)
    k_actual = min(k, n - 1)
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership)


def load_branch_metadata(metadata_path, corpus_dir, n_decisions):
    """Load decision metadata (already has branch from metadata_174k_eval.json)."""
    with open(metadata_path) as f:
        metadata = json.load(f)
    metadata = metadata[:n_decisions]
    # metadata_174k_eval.json already has branch, legal_area, chamber, year, language
    # No need to enrich from corpus
    return metadata


def compute_zoom_improvement_rate(labels_by_res, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute per-transition-average zoom improvement rate with min_cluster_size constraint."""
    resolutions = sorted(labels_by_res.keys())
    per_transition = {}
    counted_total = 0
    improved_total = 0
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarser_labels = labels_by_res[coarser_res]
        finer_labels = labels_by_res[finer_res]
        improved = 0
        counted = 0
        
        for coarse_id in np.unique(coarser_labels[coarser_labels != -1]):
            coarse_mask = coarser_labels == coarse_id
            coarse_indices = np.where(coarse_mask)[0]
            if len(coarse_indices) < min_cluster_size:
                continue
            coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
            coarse_branches = [b for b in coarse_branches if b and b != 'null']
            if not coarse_branches:
                continue
            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
            
            child_clusters = []
            for fine_id in np.unique(finer_labels[finer_labels != -1]):
                fine_mask = finer_labels == fine_id
                parent_labels = coarser_labels[fine_mask]
                parent_labels_valid = parent_labels[parent_labels != -1]
                if len(parent_labels_valid) > 0 and \
                        Counter(parent_labels_valid.tolist()).most_common(1)[0][0] == coarse_id:
                    child_clusters.append(fine_id)
            
            if not child_clusters:
                continue
            
            child_purities = []
            for child_id in child_clusters:
                child_mask = finer_labels == child_id
                child_indices = np.where(child_mask)[0]
                if len(child_indices) < min_cluster_size:
                    continue
                child_branches = [metadata[i].get('branch') for i in child_indices]
                child_branches = [b for b in child_branches if b and b != 'null']
                if child_branches:
                    child_purities.append(Counter(child_branches).most_common(1)[0][1]
                                          / len(child_branches))
            
            if child_purities:
                mean_child_purity = np.mean(child_purities)
                counted += 1
                improved += 1 if mean_child_purity > coarse_purity else 0
        
        per_transition[f"{coarser_res}_to_{finer_res}"] = {
            'counted_coarse_clusters': counted,
            'improved': improved,
            'transition_rate': (improved / counted if counted else None),
        }
        counted_total += counted
        improved_total += improved
    
    rate = improved_total / counted_total if counted_total else None
    return rate, per_transition, counted_total, improved_total


def compute_fine_branch_purity(labels_fine, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    """Compute fine_branch_purity at the finest resolution (hierarchical_v1 protocol).
    
    fine_branch_purity = weighted average of sub-cluster purity within each coarse cluster
    using the coarse cluster's dominant branch as reference.
    """
    # First get coarse clusters (resolution 0.5)
    # Actually, hierarchical_v1 uses the finest resolution clusters directly
    # and computes purity against branch labels
    fine_labels = labels_fine
    purities = []
    weights = []
    
    for fine_id in np.unique(fine_labels[fine_labels != -1]):
        fine_mask = fine_labels == fine_id
        fine_indices = np.where(fine_mask)[0]
        if len(fine_indices) < min_cluster_size:
            continue
        fine_branches = [metadata[i].get('branch') for i in fine_indices]
        fine_branches = [b for b in fine_branches if b and b != 'null']
        if not fine_branches:
            continue
        dominant_branch = Counter(fine_branches).most_common(1)[0][0]
        branch_purity = Counter(fine_branches).most_common(1)[0][1] / len(fine_branches)
        purities.append(branch_purity)
        weights.append(len(fine_indices))
    
    if not purities:
        return 0.0, 0
    weighted_purity = np.average(purities, weights=weights)
    return weighted_purity, len(purities)


def evaluate_representation(name, embeddings_path, metadata):
    """Evaluate a single representation."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {name}")
    print(f"{'='*60}")
    
    # Load embeddings
    embeddings = np.load(embeddings_path)
    print(f"  Embeddings shape: {embeddings.shape}")
    
    # Run Leiden at all resolutions
    labels_by_res = {}
    for res in RESOLUTIONS:
        print(f"  Running Leiden at resolution {res}...")
        labels = leiden_clustering(embeddings, resolution=res)
        labels_by_res[res] = labels
        n_clusters = len(np.unique(labels))
        print(f"    -> {n_clusters} clusters")
    
    # Compute zoom improvement rate
    print(f"  Computing zoom improvement rate...")
    rate, per_transition, counted, improved = compute_zoom_improvement_rate(labels_by_res, metadata)
    print(f"    Overall rate: {rate:.4f} (counted={counted}, improved={improved})")
    for trans, details in per_transition.items():
        print(f"    {trans}: rate={details['transition_rate']:.4f}, counted={details['counted_coarse_clusters']}")
    
    # Compute fine_branch_purity (hierarchical_v1 protocol)
    print(f"  Computing fine_branch_purity (hierarchical_v1)...")
    fine_purity, n_fine = compute_fine_branch_purity(labels_by_res[3.0], metadata)
    print(f"    fine_branch_purity: {fine_purity:.4f} (n_fine_clusters={n_fine})")
    
    # Determine pass/fail
    zoom_pass = rate is not None and rate >= IMPROVEMENT_RATE_THRESHOLD
    branch_pass = fine_purity > FINE_BRANCH_PURITY_THRESHOLD
    overall_pass = zoom_pass and branch_pass
    
    print(f"    zoom_improvement_rate >= {IMPROVEMENT_RATE_THRESHOLD}: {'PASS' if zoom_pass else 'FAIL'} ({rate:.4f})")
    print(f"    fine_branch_purity > {FINE_BRANCH_PURITY_THRESHOLD}: {'PASS' if branch_pass else 'FAIL'} ({fine_purity:.4f})")
    print(f"    OVERALL: {'PASS' if overall_pass else 'FAIL'}")
    
    return {
        "name": name,
        "embeddings_shape": list(embeddings.shape),
        "n_clusters_per_res": {str(res): len(np.unique(labels_by_res[res])) for res in RESOLUTIONS},
        "zoom_improvement_rate": rate,
        "zoom_per_transition": per_transition,
        "zoom_counted": counted,
        "zoom_improved": improved,
        "fine_branch_purity": fine_purity,
        "n_fine_clusters_evaluated": n_fine,
        "zoom_pass": zoom_pass,
        "branch_pass": branch_pass,
        "overall_pass": overall_pass,
    }


def main():
    print("="*60)
    print("CONSTRAINED HIERARCHICAL LEIDEN EVALUATION AT 174k")
    print("="*60)
    print(f"Frozen configuration:")
    print(f"  Resolutions: {RESOLUTIONS}")
    print(f"  MIN_CLUSTER_SIZE: {MIN_CLUSTER_SIZE}")
    print(f"  K: {K}, SEED: {SEED}")
    print(f"  IMPROVEMENT_RATE_THRESHOLD: {IMPROVEMENT_RATE_THRESHOLD}")
    print(f"  FINE_BRANCH_PURITY_THRESHOLD: {FINE_BRANCH_PURITY_THRESHOLD}")
    print(f"  Metadata: {METADATA_PATH}")
    
    # Load metadata once
    print("\nLoading metadata...")
    with open(METADATA_PATH) as f:
        metadata_full = json.load(f)
    n_decisions = len(metadata_full)
    print(f"  Total decisions in metadata: {n_decisions}")
    
    # Load branch-enriched metadata
    print("Loading branch-enriched metadata from corpus...")
    metadata = load_branch_metadata(METADATA_PATH, CORPUS_DIR, n_decisions)
    branches_known = sum(1 for m in metadata if m.get('branch') and m.get('branch') != 'null')
    print(f"  Decisions with known branch: {branches_known}/{n_decisions} ({branches_known/n_decisions*100:.1f}%)")
    
    # Evaluate all representations
    results = {
        "run_id": "constrained_hierarchical_leiden_174k_eval",
        "timestamp": "2026-10-02",
        "direction_version": 29,
        "lane": "fractal-map",
        "frozen_config": {
            "resolutions": RESOLUTIONS,
            "min_cluster_size": MIN_CLUSTER_SIZE,
            "k": K,
            "seed": SEED,
            "improvement_rate_threshold": IMPROVEMENT_RATE_THRESHOLD,
            "fine_branch_purity_threshold": FINE_BRANCH_PURITY_THRESHOLD,
        },
        "metadata_stats": {
            "n_decisions": n_decisions,
            "branches_known": branches_known,
            "branch_coverage": branches_known / n_decisions,
        },
        "representations": {}
    }
    
    for name, path in REPRESENTATIONS.items():
        if not path.exists():
            print(f"\nSKIP {name}: file not found at {path}")
            results["representations"][name] = {"error": "file_not_found", "path": str(path)}
            continue
        result = evaluate_representation(name, path, metadata)
        results["representations"][name] = result
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = []
    failed = []
    for name, result in results["representations"].items():
        if "error" in result:
            print(f"  {name}: ERROR - {result['error']}")
            failed.append(name)
        elif result["overall_pass"]:
            print(f"  {name}: PASS (zoom={result['zoom_improvement_rate']:.4f}, branch={result['fine_branch_purity']:.4f})")
            passed.append(name)
        else:
            print(f"  {name}: FAIL (zoom={result['zoom_improvement_rate']:.4f}, branch={result['fine_branch_purity']:.4f})")
            failed.append(name)
    
    results["summary"] = {
        "passed": passed,
        "failed": failed,
        "pass_count": len(passed),
        "fail_count": len(failed),
    }
    
    # Save results
    output_path = OUTPUT_DIR / "constrained_hierarchical_leiden_174k_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\nResults saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    main()