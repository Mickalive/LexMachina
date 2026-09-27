#!/usr/bin/env python3
"""
Test hierarchical Leiden on 12k dense embeddings (years 2000-2002, ACCEPTED).
Compute zoom quality metrics comparable to the 1k scale zoom_quality_diagnostic.
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

# Add the hierarchical_leiden module
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/fractal_map/hierarchical')
from hierarchical_leiden import (
    leiden_clustering,
    hierarchical_leiden,
    compute_branch_purity,
)

EMBEDDINGS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_dense_hierarchical_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Resolutions for zoom quality (matching zoom_quality_diagnostic)
RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
TRANSITIONS = [
    ("0.25", "0.5"),
    ("0.5", "0.75"),
    ("0.75", "1.0"),
    ("1.0", "1.5"),
    ("1.5", "2.0"),
    ("2.0", "3.0"),
]


def load_12k_data():
    """Load embeddings and metadata for years 2000-2002."""
    years = ["2000", "2001", "2002"]
    all_embeddings = []
    all_metadata = []
    
    for year in years:
        emb_path = EMBEDDINGS_DIR / f"embeddings_{year}.npy"
        meta_path = EMBEDDINGS_DIR / f"metadata_{year}.json"
        
        logger.info(f"Loading {year}...")
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        logger.info(f"  {year}: {embeddings.shape[0]} decisions, {embeddings.shape[1]} dims")
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
    
    combined_embeddings = np.vstack(all_embeddings)
    logger.info(f"Total: {combined_embeddings.shape[0]} decisions, {combined_embeddings.shape[1]} dims")
    
    return combined_embeddings, all_metadata


def compute_zoom_quality(embeddings, metadata, hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine):
    """
    Compute zoom quality metrics matching zoom_quality_diagnostic_results.json.
    """
    # Compute purities per cluster at each resolution
    # First, get flat Leiden labels at all resolutions
    logger.info("Computing flat Leiden at all resolutions...")
    flat_labels = {}
    for res in RESOLUTIONS:
        labels, _ = leiden_clustering(embeddings, resolution=res)
        flat_labels[res] = labels
        n_clusters = len(set(labels[labels != -1]))
        logger.info(f"  res={res}: {n_clusters} clusters")
    
    # Compute branch purity for each cluster at each resolution
    purities_by_res = {}
    for res in RESOLUTIONS:
        labels = flat_labels[res]
        purities = {}
        for cluster_id in np.unique(labels[labels != -1]):
            mask = labels == cluster_id
            cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
            cluster_branches = [b for b in cluster_branches if b and b != 'null']
            if cluster_branches:
                purities[int(cluster_id)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
            else:
                purities[int(cluster_id)] = 0.0
        purities_by_res[res] = purities
    
    # Also compute for hierarchical (coarse and fine)
    coarse_purities = {}
    for c in np.unique(coarse_labels[coarse_labels != -1]):
        mask = coarse_labels == c
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            coarse_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
    
    fine_purities = {}
    for c in np.unique(hierarchical_labels[hierarchical_labels != -1]):
        mask = hierarchical_labels == c
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            fine_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
    
    # Compute transitions (zoom quality metrics)
    transitions_results = []
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    total_splits = 0
    total_meaningful_splits = 0
    purity_deltas = []
    
    for from_res_str, to_res_str in TRANSITIONS:
        from_res = float(from_res_str)
        to_res = float(to_res_str)
        
        from_labels = flat_labels[from_res]
        to_labels = flat_labels[to_res]
        
        # For each coarse cluster at from_res, find sub-clusters at to_res
        n_splits = 0
        n_unified = 0
        n_meaningful = 0
        delta_sum = 0
        
        from_clusters = np.unique(from_labels[from_labels != -1])
        
        for coarse_id in from_clusters:
            coarse_mask = from_labels == coarse_id
            coarse_pur = purities_by_res[from_res].get(int(coarse_id), 0)
            
            # Find fine clusters within this coarse cluster
            fine_ids_in_coarse = np.unique(to_labels[coarse_mask])
            fine_ids_in_coarse = [f for f in fine_ids_in_coarse if f != -1]
            
            if len(fine_ids_in_coarse) == 1:
                # Unified (no split)
                n_unified += 1
                fine_pur = purities_by_res[to_res].get(int(fine_ids_in_coarse[0]), 0)
            elif len(fine_ids_in_coarse) > 1:
                # Split
                n_splits += 1
                fine_purs = [purities_by_res[to_res].get(int(fid), 0) for fid in fine_ids_in_coarse]
                fine_mean = np.mean(fine_purs)
                improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
                deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
                no_change = len(fine_purs) - improvements - deteriorations
                
                total_improvements += improvements
                total_deteriorations += deteriorations
                total_no_change += no_change
                total_splits += 1
                total_meaningful_splits += improvements
                
                delta = fine_mean - coarse_pur
                delta_sum += delta
                purity_deltas.append(delta)
                
                if improvements > 0:
                    n_meaningful += improvements
            else:
                # No clusters (shouldn't happen)
                continue
        
        split_rate = n_splits / len(from_clusters) if len(from_clusters) > 0 else 0
        meaningful_split_rate = n_meaningful / n_splits if n_splits > 0 else 0
        mean_delta = delta_sum / n_splits if n_splits > 0 else 0
        
        transitions_results.append({
            "transition": f"{from_res_str}->{to_res_str}",
            "n_coarse": int(len(from_clusters)),
            "n_splits": int(n_splits),
            "n_unified": int(n_unified),
            "split_rate": float(split_rate),
            "mean_purity_delta": float(mean_delta),
            "meaningful_split_rate": float(meaningful_split_rate),
        })
    
    # Overall metrics
    mean_purity_delta = np.mean(purity_deltas) if purity_deltas else 0
    mean_split_rate = np.mean([t["split_rate"] for t in transitions_results]) if transitions_results else 0
    mean_meaningful_split_rate = np.mean([t["meaningful_split_rate"] for t in transitions_results]) if transitions_results else 0
    
    # Stability score: fraction of transitions with positive delta
    positive_transitions = sum(1 for t in transitions_results if t["mean_purity_delta"] > 0)
    stability_score = positive_transitions / len(transitions_results) if transitions_results else 0
    
    # Finest purity (at res=3.0)
    finest_labels = flat_labels[3.0]
    finest_purity = compute_branch_purity(finest_labels, metadata)
    
    # Zoom quality score (composite)
    zoom_quality_score = (
        0.3 * mean_purity_delta +
        0.2 * mean_split_rate +
        0.3 * mean_meaningful_split_rate +
        0.1 * stability_score +
        0.1 * finest_purity
    )
    
    return {
        "transitions": transitions_results,
        "mean_purity_delta": float(mean_purity_delta),
        "mean_split_rate": float(mean_split_rate),
        "mean_meaningful_split_rate": float(mean_meaningful_split_rate),
        "stability_score": float(stability_score),
        "finest_purity": float(finest_purity),
        "zoom_quality_score": float(zoom_quality_score),
        "cluster_counts": {f"res_{res}": int(len(set(flat_labels[res][flat_labels[res] != -1]))) for res in RESOLUTIONS},
    }


def run_hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0):
    """Run hierarchical Leiden and return results."""
    logger.info(f"Running hierarchical Leiden: coarse_res={coarse_res}, sub_res={sub_res}")
    hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
        embeddings, metadata, coarse_res=coarse_res, sub_res=sub_res
    )
    
    # Build coarse_to_fine mapping
    coarse_to_fine = defaultdict(list)
    for sub_id, info in cluster_info.items():
        if not info.get('too_small', False):
            coarse_to_fine[info['coarse_id']].append(sub_id)
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    logger.info(f"Hierarchical: {n_coarse} coarse, {n_fine} fine clusters")
    
    # Compute purities
    coarse_purity = compute_branch_purity(coarse_labels, metadata)
    hierarchical_purity = compute_branch_purity(hierarchical_labels, metadata)
    
    logger.info(f"Coarse purity: {coarse_purity:.4f}")
    logger.info(f"Hierarchical purity: {hierarchical_purity:.4f}")
    logger.info(f"Improvement: {hierarchical_purity - coarse_purity:.4f}")
    
    return {
        "hierarchical_labels": hierarchical_labels,
        "coarse_labels": coarse_labels,
        "cluster_info": cluster_info,
        "coarse_to_fine": dict(coarse_to_fine),
        "n_fine": n_fine,
        "n_coarse": n_coarse,
        "coarse_purity": float(coarse_purity),
        "hierarchical_purity": float(hierarchical_purity),
        "improvement": float(hierarchical_purity - coarse_purity),
        "nesting_score": 1.0,  # By construction
    }


def main():
    logger.info("=== 12k Dense Embeddings Hierarchical Leiden Test ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Load data
    embeddings, metadata = load_12k_data()
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    # Run hierarchical Leiden with validated config
    hier_results = run_hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0)
    
    # Compute zoom quality metrics
    logger.info("\nComputing zoom quality metrics...")
    zoom_quality = compute_zoom_quality(
        embeddings, metadata,
        hier_results["hierarchical_labels"],
        hier_results["coarse_labels"],
        hier_results["cluster_info"],
        hier_results["coarse_to_fine"]
    )
    
    # Save results
    output = {
        "run_id": f"12k_dense_hierarchical_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 28,
        "sample": "12k dense embeddings (years 2000-2002, ACCEPTED)",
        "embedding_dim": int(embeddings.shape[1]),
        "hierarchical_config": {"coarse_res": 0.5, "sub_res": 3.0},
        "hierarchical_results": {
            "n_coarse": hier_results["n_coarse"],
            "n_fine": hier_results["n_fine"],
            "coarse_purity": hier_results["coarse_purity"],
            "hierarchical_purity": hier_results["hierarchical_purity"],
            "improvement": hier_results["improvement"],
            "nesting_score": 1.0,
        },
        "zoom_quality": zoom_quality,
        "verdict": "PASS" if zoom_quality["zoom_quality_score"] > 0.3 else "FAIL",
    }
    
    output_path = OUTPUT_DIR / "hierarchical_leiden_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Save labels
    np.save(OUTPUT_DIR / "labels_hierarchical.npy", hier_results["hierarchical_labels"].astype(np.int32))
    np.save(OUTPUT_DIR / "labels_coarse.npy", hier_results["coarse_labels"].astype(np.int32))
    
    logger.info(f"\n{'='*60}")
    logger.info("ZOOM QUALITY SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Zoom Quality Score: {zoom_quality['zoom_quality_score']:.4f}")
    logger.info(f"  Mean Purity Delta: {zoom_quality['mean_purity_delta']:.4f}")
    logger.info(f"  Mean Split Rate: {zoom_quality['mean_split_rate']:.4f}")
    logger.info(f"  Mean Meaningful Split Rate: {zoom_quality['mean_meaningful_split_rate']:.4f}")
    logger.info(f"  Stability Score: {zoom_quality['stability_score']:.4f}")
    logger.info(f"  Finest Purity: {zoom_quality['finest_purity']:.4f}")
    logger.info(f"Cluster counts: {zoom_quality['cluster_counts']}")
    logger.info(f"Verdict: {output['verdict']}")
    logger.info(f"Results saved to {output_path}")
    
    return output


if __name__ == "__main__":
    main()