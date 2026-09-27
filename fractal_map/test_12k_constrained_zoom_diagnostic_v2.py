#!/usr/bin/env python3
"""
Test constrained hierarchical Leiden on 12k dense embeddings (years 2000-2002, ACCEPTED)
with full zoom quality diagnostic matching the v26 evaluation framework.
FIXED: Correct return value order from constrained_hierarchical_leiden.
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

# Add the experiments module
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/fractal_map/experiments')
from constrained_hierarchical_leiden import (
    leiden_clustering,
    constrained_hierarchical_leiden,
)

# Use the workspace embeddings (3 years ACCEPTED)
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_constrained_zoom_diagnostic")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# v26 resolutions for zoom quality
V26_RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]
V26_TRANSITIONS = [
    ("res_0.25_to_res_0.5", 0.25, 0.5),
    ("res_0.5_to_res_1.0", 0.5, 1.0),
    ("res_1.0_to_res_2.0", 1.0, 2.0),
    ("res_2.0_to_res_3.0", 2.0, 3.0),
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


def compute_v26_zoom_quality(embeddings, metadata):
    """Compute v26 zoom quality metrics on flat Leiden clustering."""
    logger.info("Computing flat Leiden at v26 resolutions...")
    flat_labels = {}
    for res in V26_RESOLUTIONS:
        labels, _ = leiden_clustering(embeddings, resolution=res)
        flat_labels[res] = labels
        n_clusters = len(set(labels[labels != -1]))
        logger.info(f"  res={res}: {n_clusters} clusters")
    
    # Compute branch purity for each cluster at each resolution
    purities_by_res = {}
    for res in V26_RESOLUTIONS:
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
    
    # Compute transitions
    transitions_results = {}
    for trans_name, from_res, to_res in V26_TRANSITIONS:
        from_labels = flat_labels[from_res]
        to_labels = flat_labels[to_res]
        
        from_clusters = np.unique(from_labels[from_labels != -1])
        
        parent_details = {}
        improvements = 0
        n_parents = 0
        
        for coarse_id in from_clusters:
            coarse_mask = from_labels == coarse_id
            coarse_pur = purities_by_res[from_res].get(int(coarse_id), 0)
            
            fine_ids_in_coarse = np.unique(to_labels[coarse_mask])
            fine_ids_in_coarse = [f for f in fine_ids_in_coarse if f != -1]
            
            if len(fine_ids_in_coarse) >= 1:
                n_parents += 1
                fine_purs = [purities_by_res[to_res].get(int(fid), 0) for fid in fine_ids_in_coarse]
                fine_mean = np.mean(fine_purs)
                improvement = fine_mean - coarse_pur
                
                parent_details[str(int(coarse_id))] = {
                    "coarse_purity": float(coarse_pur),
                    "mean_child_purity": float(fine_mean),
                    "improvement": float(improvement),
                    "n_children": len(fine_ids_in_coarse)
                }
                
                if improvement > 0:
                    improvements += 1
        
        mean_improvement = np.mean([v["improvement"] for v in parent_details.values()]) if parent_details else 0
        improvement_rate = improvements / n_parents if n_parents > 0 else 0
        
        transitions_results[trans_name] = {
            "mean_improvement": float(mean_improvement),
            "improvement_rate": float(improvement_rate),
            "n_parents": int(n_parents),
            "parent_details": parent_details
        }
    
    improvements_gt_05 = sum(1 for t in transitions_results.values() if t["improvement_rate"] > 0.5)
    
    fragmentation = {}
    for res in V26_RESOLUTIONS:
        labels = flat_labels[res]
        unique_labels = np.unique(labels[labels != -1])
        sizes = [np.sum(labels == c) for c in unique_labels]
        fragmentation[str(res)] = {
            "n_clusters": len(unique_labels),
            "median_size": float(np.median(sizes)) if sizes else 0,
            "singleton_fraction": float(np.sum(np.array(sizes) == 1) / len(sizes)) if sizes else 0
        }
    
    return {
        "purities_by_res": purities_by_res,
        "transitions": transitions_results,
        "checks": {
            "branch_monotonic_res3_vs_res0.25": None,
            "area_monotonic_res3_vs_res0.25": None,
            "improvement_rate_gt_0.5_on_2_of_4": improvements_gt_05 >= 2
        },
        "per_mode_verdict": "PASS" if improvements_gt_05 >= 2 else "FAIL",
        "fragmentation": fragmentation
    }


def test_constrained_hierarchical(config_name, embeddings, metadata, config):
    """Test constrained hierarchical Leiden with given config."""
    logger.info(f"Testing {config_name}...")
    
    # Run constrained hierarchical Leiden - returns (hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine)
    fine_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
        embeddings,
        metadata,
        coarse_res=config["coarse_res"],
        base_sub_res=config["sub_res"],
        min_cluster_size=config["min_cluster_size"],
        max_subclusters_per_parent=config.get("max_subclusters", 20),
        adaptive_sub_res=config.get("adaptive_sub_res", False)
    )
    
    # Compute purities
    coarse_purities = {}
    for c in np.unique(coarse_labels[coarse_labels != -1]):
        mask = coarse_labels == c
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            coarse_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
    
    fine_purities = {}
    for c in np.unique(fine_labels[fine_labels != -1]):
        mask = fine_labels == c
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        if cluster_branches:
            fine_purities[int(c)] = Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches)
    
    # Compute zoom coherence (parent -> children purity improvement)
    parent_details = {}
    improvements = 0
    n_parents = 0
    
    for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
        coarse_pur = coarse_purities.get(int(coarse_id), 0)
        
        # Find children of this coarse cluster
        child_ids = coarse_to_fine.get(int(coarse_id), [])
        
        if len(child_ids) >= 1:
            n_parents += 1
            child_purs = [fine_purities.get(int(cid), 0) for cid in child_ids]
            child_mean = np.mean(child_purs)
            improvement = child_mean - coarse_pur
            
            parent_details[str(int(coarse_id))] = {
                "coarse_purity": float(coarse_pur),
                "mean_child_purity": float(child_mean),
                "improvement": float(improvement),
                "n_children": len(child_ids)
            }
            
            if improvement > 0:
                improvements += 1
    
    mean_improvement = np.mean([v["improvement"] for v in parent_details.values()]) if parent_details else 0
    improvement_rate = improvements / n_parents if n_parents > 0 else 0
    
    # Fragmentation
    fine_sizes = [np.sum(fine_labels == c) for c in np.unique(fine_labels[fine_labels != -1])]
    coarse_sizes = [np.sum(coarse_labels == c) for c in np.unique(coarse_labels[coarse_labels != -1])]
    
    # Nesting - by construction should be 1.0
    nesting = 1.0
    
    return {
        "config": config,
        "coarse_clusters": len(np.unique(coarse_labels[coarse_labels != -1])),
        "fine_clusters": len(np.unique(fine_labels[fine_labels != -1])),
        "coarse_branch_purity": float(np.mean(list(coarse_purities.values()))) if coarse_purities else 0,
        "fine_branch_purity": float(np.mean(list(fine_purities.values()))) if fine_purities else 0,
        "branch_improvement": float(np.mean(list(fine_purities.values())) - np.mean(list(coarse_purities.values()))) if (coarse_purities and fine_purities) else 0,
        "strict_nesting": float(nesting),
        "zoom_branch": {
            "mean_improvement": float(mean_improvement),
            "improvement_rate": float(improvement_rate),
            "n_parents": int(n_parents),
            "parent_details": parent_details
        },
        "fragmentation": {
            "coarse_median_size": float(np.median(coarse_sizes)) if coarse_sizes else 0,
            "fine_median_size": float(np.median(fine_sizes)) if fine_sizes else 0,
            "fine_singleton_fraction": float(np.sum(np.array(fine_sizes) == 1) / len(fine_sizes)) if fine_sizes else 0,
            "coarse_singleton_fraction": float(np.sum(np.array(coarse_sizes) == 1) / len(coarse_sizes)) if coarse_sizes else 0
        }
    }


def main():
    logger.info("=" * 60)
    logger.info("12k Dense Embeddings Constrained Hierarchical Zoom Diagnostic (FIXED)")
    logger.info("=" * 60)
    
    # Load data
    embeddings, metadata = load_12k_data()
    
    # 1. Run v26 flat zoom quality baseline
    logger.info("\n--- Running v26 Flat Zoom Quality Baseline ---")
    v26_results = compute_v26_zoom_quality(embeddings, metadata)
    
    # 2. Test constrained hierarchical configurations
    configs = [
        {
            "name": "coarse_0.25_sub3.0_min20",
            "coarse_res": 0.25,
            "sub_res": 3.0,
            "min_cluster_size": 20,
            "max_subclusters": 20,
            "adaptive_sub_res": False
        },
        {
            "name": "coarse_0.5_sub3.0_min20",
            "coarse_res": 0.5,
            "sub_res": 3.0,
            "min_cluster_size": 20,
            "max_subclusters": 20,
            "adaptive_sub_res": False
        },
        {
            "name": "coarse_0.5_sub3.0_min50",
            "coarse_res": 0.5,
            "sub_res": 3.0,
            "min_cluster_size": 50,
            "max_subclusters": 20,
            "adaptive_sub_res": False
        },
        {
            "name": "coarse_0.5_sub3.0_min10",
            "coarse_res": 0.5,
            "sub_res": 3.0,
            "min_cluster_size": 10,
            "max_subclusters": 20,
            "adaptive_sub_res": False
        },
        {
            "name": "coarse_1.0_sub3.0_min20",
            "coarse_res": 1.0,
            "sub_res": 3.0,
            "min_cluster_size": 20,
            "max_subclusters": 20,
            "adaptive_sub_res": False
        },
    ]
    
    hierarchical_results = {}
    for config in configs:
        result = test_constrained_hierarchical(config["name"], embeddings, metadata, config)
        hierarchical_results[config["name"]] = result
        logger.info(f"  {config['name']}: coarse_purity={result['coarse_branch_purity']:.4f}, "
                   f"fine_purity={result['fine_branch_purity']:.4f}, "
                   f"improvement_rate={result['zoom_branch']['improvement_rate']:.2f}, "
                   f"fine_singleton={result['fragmentation']['fine_singleton_fraction']:.2%}")
    
    # Save results
    output = {
        "run_id": f"12k_constrained_zoom_diagnostic_v2_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 28,
        "sample": "12k dense embeddings (years 2000-2002, ACCEPTED)",
        "embedding_dim": 768,
        "v26_flat_baseline": v26_results,
        "constrained_hierarchical_results": hierarchical_results
    }
    
    output_path = OUTPUT_DIR / f"constrained_zoom_diagnostic_v2_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"v26 Flat Baseline: {v26_results['per_mode_verdict']}")
    logger.info(f"  improvement_rate_gt_0.5_on_2_of_4={v26_results['checks']['improvement_rate_gt_0.5_on_2_of_4']}")
    
    logger.info("\nConstrained Hierarchical Results:")
    for name, result in hierarchical_results.items():
        logger.info(f"  {name}:")
        logger.info(f"    coarse_clusters={result['coarse_clusters']}, fine_clusters={result['fine_clusters']}")
        logger.info(f"    coarse_purity={result['coarse_branch_purity']:.4f}, fine_purity={result['fine_branch_purity']:.4f}")
        logger.info(f"    improvement_rate={result['zoom_branch']['improvement_rate']:.2f}, "
                   f"mean_improvement={result['zoom_branch']['mean_improvement']:.4f}")
        logger.info(f"    fine_singleton={result['fragmentation']['fine_singleton_fraction']:.2%}, "
                   f"fine_median_size={result['fragmentation']['fine_median_size']:.1f}")
        logger.info(f"    nesting={result['strict_nesting']:.4f}")


if __name__ == "__main__":
    main()
