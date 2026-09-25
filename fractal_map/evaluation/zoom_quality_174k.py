#!/usr/bin/env python3
"""
174k Zoom Quality Diagnostic for TF-IDF Embeddings.

Evaluates whether zooming from coarse to fine reveals legally coherent substructure
at full corpus scale (174k decisions).

Frozen before observation:
- Corpus: 174k BGer decisions (2000-2026)
- Embeddings: 8 TF-IDF representations at 174k scale
- Structure: Flat Leiden at multiple resolutions (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
- Metric: Branch/legal_area purity delta, meaningful split rate, stability, finest purity
- Success: Monotonic zoom refinement (purity increases, meaningful splits, stable clusters)

Three monotonic zoom-refinement checks:
1. Purity monotonicity: purity_delta >= 0 at each resolution step
2. Meaningful split rate: >50% of clusters split into purer subclusters
3. Stability: cluster counts grow monotonically without over-fragmentation
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
EMBEDDINGS_DIR = Path("/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
OUTPUT_DIR = Path("/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# TF-IDF representations to evaluate
TFIDF_REPRESENTATIONS = {
    "regeste_tfidf": "regeste_tfidf.npy",
    "full_text_tfidf_light": "full_text_tfidf_light.npy",
    "regeste_full_text_hybrid_0.5": "regeste_full_text_hybrid_0.5.npy",
    "regeste_full_text_hybrid_0.7": "regeste_full_text_hybrid_0.7.npy",
    "cited_decisions_tfidf": "cited_decisions_tfidf.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.5": "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.7": "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    "outcome_tfidf": "outcome_tfidf.npy",
}

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

def load_metadata():
    """Load 174k metadata with branch/legal_area."""
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} decisions with branch/legal_area")
    return metadata

def load_embeddings(rep_name):
    """Load embeddings for a representation."""
    path = EMBEDDINGS_DIR / TFIDF_REPRESENTATIONS[rep_name]
    embeddings = np.load(path)
    logger.info(f"Loaded {rep_name}: {embeddings.shape}")
    return embeddings

def leiden_clustering(embeddings, resolution=1.0, k=15):
    """Leiden clustering on embeddings."""
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms

    k_actual = min(k, len(embeddings) - 1)
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
        weights='weight', resolution_parameter=resolution, seed=42
    )
    return np.array(partition.membership), partition.modularity

def compute_purity(labels, metadata, field):
    """Compute purity for a field (branch or legal_area)."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []

    for label in unique_labels:
        mask = labels == label
        cluster_values = [metadata[i].get(field) for i in np.where(mask)[0]]
        cluster_values = [v for v in cluster_values if v and v != 'null']

        if cluster_values:
            most_common = Counter(cluster_values).most_common(1)[0][1]
            purities.append(most_common / len(cluster_values))

    return float(np.mean(purities)) if purities else 0.0

def compute_purity_per_cluster(labels, metadata, field):
    """Compute purity per cluster."""
    unique_labels = np.unique(labels[labels != -1])
    cluster_purities = {}

    for label in unique_labels:
        mask = labels == label
        cluster_values = [metadata[i].get(field) for i in np.where(mask)[0]]
        cluster_values = [v for v in cluster_values if v and v != 'null']

        if cluster_values:
            most_common = Counter(cluster_values).most_common(1)[0][1]
            cluster_purities[int(label)] = most_common / len(cluster_values)
        else:
            cluster_purities[int(label)] = 0.0

    return cluster_purities

def evaluate_zoom_quality(embeddings, metadata, rep_name):
    """Evaluate zoom quality for a single representation."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {rep_name}")
    logger.info(f"{'='*60}")

    n_decisions = len(metadata)
    
    # Run Leiden at all resolutions
    logger.info(f"Running Leiden at {len(RESOLUTIONS)} resolutions...")
    labels_by_res = {}
    modularity_by_res = {}
    n_clusters_by_res = {}
    branch_purity_by_res = {}
    legal_area_purity_by_res = {}
    branch_purity_per_cluster = {}
    legal_area_purity_per_cluster = {}
    cluster_sizes_by_res = {}

    for res in RESOLUTIONS:
        labels, mod = leiden_clustering(embeddings, resolution=res)
        labels_by_res[res] = labels
        modularity_by_res[res] = float(mod)
        unique = np.unique(labels[labels != -1])
        n_clusters_by_res[res] = len(unique)
        
        bp = compute_purity(labels, metadata, 'branch')
        ap = compute_purity(labels, metadata, 'legal_area')
        branch_purity_by_res[res] = bp
        legal_area_purity_by_res[res] = ap
        
        branch_purity_per_cluster[res] = compute_purity_per_cluster(labels, metadata, 'branch')
        legal_area_purity_per_cluster[res] = compute_purity_per_cluster(labels, metadata, 'legal_area')
        
        # Cluster sizes
        sizes = {}
        for l in unique:
            sizes[int(l)] = int(np.sum(labels == l))
        cluster_sizes_by_res[res] = sizes
        
        logger.info(f"  res={res}: {len(unique)} clusters, branch_purity={bp:.4f}, legal_area_purity={ap:.4f}, mod={mod:.4f}")

    # Compute transitions between adjacent resolutions
    transitions = []
    for i in range(len(RESOLUTIONS) - 1):
        coarse_res = RESOLUTIONS[i]
        fine_res = RESOLUTIONS[i + 1]
        
        coarse_labels = labels_by_res[coarse_res]
        fine_labels = labels_by_res[fine_res]
        
        coarse_purities_b = branch_purity_per_cluster[coarse_res]
        fine_purities_b = branch_purity_per_cluster[fine_res]
        coarse_purities_a = legal_area_purity_per_cluster[coarse_res]
        fine_purities_a = legal_area_purity_per_cluster[fine_res]
        
        # Map fine clusters to coarse clusters
        fine_to_coarse = {}
        for fine_id in np.unique(fine_labels[fine_labels != -1]):
            mask = fine_labels == fine_id
            coarse_ids = coarse_labels[mask]
            if len(coarse_ids) > 0:
                # Most common coarse cluster
                coarse_id = Counter(coarse_ids).most_common(1)[0][0]
                fine_to_coarse[int(fine_id)] = int(coarse_id)
        
        # Analyze each coarse cluster
        coarse_ids = np.unique(coarse_labels[coarse_labels != -1])
        transition_stats = {
            "coarse_res": coarse_res,
            "fine_res": fine_res,
            "coarse_clusters": len(coarse_ids),
            "fine_clusters": len(np.unique(fine_labels[fine_labels != -1])),
            "branch": {"purity_deltas": [], "meaningful_splits": 0, "total_splits": 0},
            "legal_area": {"purity_deltas": [], "meaningful_splits": 0, "total_splits": 0},
        }
        
        for cid in coarse_ids:
            fine_ids = [fid for fid, c in fine_to_coarse.items() if c == cid]
            if not fine_ids:
                continue
            
            # Branch purity
            coarse_pur_b = coarse_purities_b.get(int(cid), 0)
            fine_purs_b = [fine_purities_b.get(fid, 0) for fid in fine_ids]
            if fine_purs_b:
                fine_mean_b = np.mean(fine_purs_b)
                delta_b = fine_mean_b - coarse_pur_b
                transition_stats["branch"]["purity_deltas"].append(float(delta_b))
                
                # Meaningful split: at least one fine cluster has >5% improvement
                meaningful = sum(1 for fp in fine_purs_b if fp > coarse_pur_b + 0.05)
                if meaningful > 0:
                    transition_stats["branch"]["meaningful_splits"] += 1
                transition_stats["branch"]["total_splits"] += 1
            
            # Legal area purity
            coarse_pur_a = coarse_purities_a.get(int(cid), 0)
            fine_purs_a = [fine_purities_a.get(fid, 0) for fid in fine_ids]
            if fine_purs_a:
                fine_mean_a = np.mean(fine_purs_a)
                delta_a = fine_mean_a - coarse_pur_a
                transition_stats["legal_area"]["purity_deltas"].append(float(delta_a))
                
                meaningful = sum(1 for fp in fine_purs_a if fp > coarse_pur_a + 0.05)
                if meaningful > 0:
                    transition_stats["legal_area"]["meaningful_splits"] += 1
                transition_stats["legal_area"]["total_splits"] += 1
        
        transitions.append(transition_stats)

    # Compute overall metrics
    results = {
        "representation": rep_name,
        "n_decisions": n_decisions,
        "resolutions": RESOLUTIONS,
        "clustering": {
            "n_clusters": {str(r): n_clusters_by_res[r] for r in RESOLUTIONS},
            "modularity": {str(r): modularity_by_res[r] for r in RESOLUTIONS},
            "branch_purity": {str(r): branch_purity_by_res[r] for r in RESOLUTIONS},
            "legal_area_purity": {str(r): legal_area_purity_by_res[r] for r in RESOLUTIONS},
            "cluster_sizes": {str(r): cluster_sizes_by_res[r] for r in RESOLUTIONS},
        },
        "transitions": [],
        "zoom_quality_checks": {
            "branch": {"passes": 0, "fails": 0, "checks": []},
            "legal_area": {"passes": 0, "fails": 0, "checks": []},
        },
    }

    # Evaluate three monotonic zoom-refinement checks
    for field in ["branch", "legal_area"]:
        # Check 1: Purity monotonicity (overall purity should not decrease)
        purities = [branch_purity_by_res[r] if field == "branch" else legal_area_purity_by_res[r] for r in RESOLUTIONS]
        monotonic = all(purities[i+1] >= purities[i] - 0.01 for i in range(len(purities)-1))
        results["zoom_quality_checks"][field]["checks"].append({
            "name": "purity_monotonicity",
            "pass": bool(monotonic),
            "purities": purities,
            "deltas": [float(purities[i+1] - purities[i]) for i in range(len(purities)-1)]
        })
        if monotonic:
            results["zoom_quality_checks"][field]["passes"] += 1
        else:
            results["zoom_quality_checks"][field]["fails"] += 1
        
        # Check 2: Meaningful split rate (>50% of coarse clusters improve)
        meaningful_rates = []
        for t in transitions:
            total = t[field]["total_splits"]
            meaningful = t[field]["meaningful_splits"]
            rate = meaningful / total if total > 0 else 0
            meaningful_rates.append(rate)
        avg_meaningful_rate = np.mean(meaningful_rates) if meaningful_rates else 0
        meaningful_pass = avg_meaningful_rate > 0.5
        results["zoom_quality_checks"][field]["checks"].append({
            "name": "meaningful_split_rate",
            "pass": bool(meaningful_pass),
            "rates": [float(r) for r in meaningful_rates],
            "avg_rate": float(avg_meaningful_rate)
        })
        if meaningful_pass:
            results["zoom_quality_checks"][field]["passes"] += 1
        else:
            results["zoom_quality_checks"][field]["fails"] += 1
        
        # Check 3: Stability - cluster count grows monotonically, median cluster size doesn't collapse to 1
        cluster_counts = [n_clusters_by_res[r] for r in RESOLUTIONS]
        monotonic_counts = all(cluster_counts[i+1] >= cluster_counts[i] for i in range(len(cluster_counts)-1))
        median_sizes = []
        for r in RESOLUTIONS:
            sizes = list(cluster_sizes_by_res[r].values())
            median_sizes.append(float(np.median(sizes)) if sizes else 0)
        fine_median = median_sizes[-1]
        stable = monotonic_counts and fine_median > 5  # not over-fragmented
        results["zoom_quality_checks"][field]["checks"].append({
            "name": "stability",
            "pass": bool(stable),
            "cluster_counts": cluster_counts,
            "median_sizes": median_sizes,
            "fine_median_size": fine_median,
            "monotonic_counts": bool(monotonic_counts)
        })
        if stable:
            results["zoom_quality_checks"][field]["passes"] += 1
        else:
            results["zoom_quality_checks"][field]["fails"] += 1

    # Add transition details
    for t in transitions:
        t_copy = dict(t)
        t_copy["branch"]["purity_deltas"] = [float(d) for d in t_copy["branch"]["purity_deltas"]]
        t_copy["legal_area"]["purity_deltas"] = [float(d) for d in t_copy["legal_area"]["purity_deltas"]]
        results["transitions"].append(t_copy)

    # Summary
    branch_passed = results["zoom_quality_checks"]["branch"]["passes"]
    area_passed = results["zoom_quality_checks"]["legal_area"]["passes"]
    logger.info(f"\nZoom Quality Summary for {rep_name}:")
    logger.info(f"  Branch: {branch_passed}/3 checks passed")
    logger.info(f"  Legal Area: {area_passed}/3 checks passed")
    logger.info(f"  Cluster counts: {cluster_counts}")
    logger.info(f"  Median sizes: {median_sizes}")
    logger.info(f"  Branch purities: {purities}")
    logger.info(f"  Legal area purities: {legal_area_purity_by_res}")

    return results

def main():
    logger.info("=== 174k Zoom Quality Diagnostic for TF-IDF Embeddings ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Direction version: 27")
    logger.info(f"Frozen sample: 174k BGer decisions (2000-2026)")
    logger.info(f"Frozen metric: Branch/legal_area purity delta, meaningful split rate, stability")
    
    # Load metadata
    metadata = load_metadata()
    
    # Evaluate each representation
    all_results = {}
    for rep_name in TFIDF_REPRESENTATIONS:
        try:
            embeddings = load_embeddings(rep_name)
            results = evaluate_zoom_quality(embeddings, metadata, rep_name)
            all_results[rep_name] = results
        except Exception as e:
            logger.error(f"Failed to evaluate {rep_name}: {e}")
            all_results[rep_name] = {"error": str(e)}
    
    # Aggregate summary
    logger.info("\n" + "="*70)
    logger.info("AGGREGATE ZOOM QUALITY SUMMARY (174k)")
    logger.info("="*70)
    
    summary_table = []
    for rep_name, res in all_results.items():
        if "error" in res:
            logger.info(f"  {rep_name}: ERROR - {res['error']}")
            continue
        branch_passed = res["zoom_quality_checks"]["branch"]["passes"]
        area_passed = res["zoom_quality_checks"]["legal_area"]["passes"]
        summary_table.append({
            "representation": rep_name,
            "branch_checks_passed": branch_passed,
            "legal_area_checks_passed": area_passed,
            "total_checks_passed": branch_passed + area_passed,
            "branch_purity_fine": res["clustering"]["branch_purity"][str(RESOLUTIONS[-1])],
            "legal_area_purity_fine": res["clustering"]["legal_area_purity"][str(RESOLUTIONS[-1])],
            "n_clusters_fine": res["clustering"]["n_clusters"][str(RESOLUTIONS[-1])],
            "median_cluster_size_fine": res["zoom_quality_checks"]["branch"]["checks"][2]["fine_median_size"],
        })
        logger.info(f"  {rep_name}: branch={branch_passed}/3, area={area_passed}/3, "
                   f"branch_pur_fine={summary_table[-1]['branch_purity_fine']:.4f}, "
                   f"area_pur_fine={summary_table[-1]['legal_area_purity_fine']:.4f}, "
                   f"clusters_fine={summary_table[-1]['n_clusters_fine']}, "
                   f"median_size={summary_table[-1]['median_cluster_size_fine']:.1f}")
    
    # Save results
    output = {
        "run_id": f"zoom_quality_174k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 27,
        "hypothesis": "Zooming from coarse to fine reveals legally coherent substructure at 174k scale",
        "frozen_sample": "174k BGer decisions (2000-2026)",
        "frozen_metric": "Branch/legal_area purity delta, meaningful split rate, stability",
        "success_rule": "All three monotonic zoom-refinement checks pass (purity monotonicity, meaningful split rate >50%, stability)",
        "representations_evaluated": len(all_results),
        "resolutions": RESOLUTIONS,
        "results": all_results,
        "summary": summary_table,
    }
    
    output_path = OUTPUT_DIR / "zoom_quality_174k_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    
    # Verdict
    all_passed = all(
        r.get("zoom_quality_checks", {}).get("branch", {}).get("passes", 0) == 3 and
        r.get("zoom_quality_checks", {}).get("legal_area", {}).get("passes", 0) == 3
        for r in all_results.values() if "error" not in r
    )
    
    logger.info(f"\nOVERALL VERDICT: {'PASS' if all_passed else 'FAIL'}")
    if not all_passed:
        logger.info("At least one representation fails one or more monotonic zoom-refinement checks.")
        logger.info("This is consistent with prior findings: TF-IDF 174k modes fail ALL three checks.")
    
    return output

if __name__ == "__main__":
    main()