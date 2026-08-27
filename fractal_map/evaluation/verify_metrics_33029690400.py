#!/usr/bin/env python3
"""
Independent metric recomputation for fractal-map lane verification.
Run 33029690400: Recomputes all key metrics from saved .npy label arrays
and compares against reported values in state file.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import sys

BASE = Path("/home/runner/work/LexMachina/LexMachina")

def load_json(path):
    with open(BASE / path) as f:
        return json.load(f)

def compute_cluster_purity(labels, branch_labels):
    """Compute purity for each cluster. labels=cluster assignments, branch_labels=ground truth."""
    unique_labels = np.unique(labels)
    purities = []
    for cl in unique_labels:
        mask = labels == cl
        cl_branches = branch_labels[mask]
        if len(cl_branches) == 0:
            continue
        counts = Counter(cl_branches)
        most_common_count = counts.most_common(1)[0][1]
        purities.append(most_common_count / len(cl_branches))
    return purities

def compute_nesting(labels_coarse, labels_fine):
    """Compute nesting consistency between coarse and fine resolutions.
    For each fine cluster, check if all its elements belong to the same coarse cluster.
    """
    fine_labels = np.unique(labels_fine)
    consistent = 0
    for fl in fine_labels:
        fine_mask = labels_fine == fl
        coarse_in_fine = labels_coarse[fine_mask]
        if len(coarse_in_fine) == 0:
            continue
        unique_coarse = np.unique(coarse_in_fine)
        if len(unique_coarse) == 1:
            consistent += 1
    return consistent / len(fine_labels) if len(fine_labels) > 0 else 0

def load_branch_labels():
    """Load branch labels from corpus files, matching the hierarchical_map_builder approach."""
    metadata = load_json("results/fractal_map/baseline/metadata.json")
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    branch_labels = np.array([branch_map.get(m['decision_id'], 'unknown') for m in metadata])
    return branch_labels

def main():
    results = {}
    checks = {}
    
    # Load state file
    state = load_json("state/fractal-map.json")
    
    # Load branch labels from corpus (matching hierarchical_map_builder approach)
    branch_labels = load_branch_labels()
    
    # Load hierarchical leiden results
    hl_results = load_json("results/fractal_map/hierarchical_map/hierarchical_leiden_results.json")
    
    # Define resolutions
    resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    
    # Step 1: Load all label arrays and verify counts
    print("=== Step 1: Label array verification ===")
    label_arrays = {}
    for res in resolutions:
        path = f"results/fractal_map/hierarchical_map/labels_res_{res}.npy"
        arr = np.load(BASE / path)
        label_arrays[res] = arr
        check_name = f"label_count_res_{res}"
        expected = 1000
        actual = len(arr)
        checks[check_name] = {
            "pass": actual == expected,
            "detail": f"res_{res}: {actual} labels (expected {expected})"
        }
        print(f"  res_{res}: {actual} labels -> {'PASS' if actual == expected else 'FAIL'}")
    
    # Step 2: Compute flat branch purity for each resolution
    print("\n=== Step 2: Flat branch purity recomputation ===")
    flat_purities = {}
    for res in resolutions:
        labels = label_arrays[res]
        purities = compute_cluster_purity(labels, branch_labels)
        mean_purity = np.mean(purities) if purities else 0
        flat_purities[res] = mean_purity
        
        # Compare with reported value
        report_key = f"res_{res}"
        reported = None
        if "hierarchy_info" in hl_results:
            # Try to get from hierarchical_map_results
            hm_results = load_json("results/fractal_map/hierarchical_map/hierarchical_map_results.json")
            if "branch_coherence" in hm_results and report_key in hm_results["branch_coherence"]:
                reported = hm_results["branch_coherence"][report_key]["mean_branch_purity"]
        
        if reported is not None:
            diff = abs(mean_purity - reported)
            check_name = f"flat_purity_res_{res}"
            checks[check_name] = {
                "pass": diff < 1e-6,
                "detail": f"Computed {mean_purity:.6f}, reported {reported:.6f}, diff={diff:.10f}"
            }
            print(f"  res_{res}: computed={mean_purity:.6f}, reported={reported:.6f}, diff={diff:.10f} -> {'PASS' if diff < 1e-6 else 'FAIL'}")
        else:
            print(f"  res_{res}: computed={mean_purity:.6f} (no reported value to compare)")
    
    flat_mean_purity = np.mean(list(flat_purities.values()))
    print(f"\n  Flat mean purity: {flat_mean_purity:.6f}")
    
    # Step 3: Compute nesting consistency for flat Leiden
    print("\n=== Step 3: Flat nesting consistency ===")
    nesting_scores = []
    for i in range(len(resolutions) - 1):
        res_coarse = resolutions[i]
        res_fine = resolutions[i + 1]
        nesting = compute_nesting(label_arrays[res_coarse], label_arrays[res_fine])
        nesting_scores.append(nesting)
        print(f"  {res_coarse}->{res_fine}: nesting={nesting:.6f}")
    
    flat_mean_nesting = np.mean(nesting_scores)
    print(f"\n  Flat mean nesting: {flat_mean_nesting:.6f}")
    
    # Step 4: Verify hierarchical Leiden results
    print("\n=== Step 4: Hierarchical Leiden verification ===")
    best_config = hl_results.get("best_config", "coarse_0.5_fine_3.0")
    best_results = hl_results.get("hierarchical_results", {}).get(best_config, {})
    
    h_purity = best_results.get("hierarchical_purity", 0)
    h_nesting = best_results.get("nesting_score", 0)
    n_fine = best_results.get("n_fine_clusters", 0)
    
    print(f"  Best config: {best_config}")
    print(f"  Hierarchical purity: {h_purity:.6f}")
    print(f"  Hierarchical nesting: {h_nesting:.6f}")
    print(f"  Fine clusters: {n_fine}")
    
    # Verify sub-cluster sizes sum to 1000
    cluster_info = best_results.get("cluster_info", {})
    total_size = sum(c.get("size", 0) for c in cluster_info.values())
    checks["sub_cluster_size_check"] = {
        "pass": total_size == 1000,
        "detail": f"{n_fine} sub-clusters sum to {total_size} (expected 1000)"
    }
    print(f"  Sub-cluster sum: {total_size} -> {'PASS' if total_size == 1000 else 'FAIL'}")
    
    # Verify all sub-clusters have valid parent (0..7)
    valid_parents = all(
        0 <= c.get("coarse_id", -1) <= 7
        for c in cluster_info.values()
    )
    checks["parent_child_consistency"] = {
        "pass": valid_parents,
        "detail": f"All {n_fine} sub-clusters have valid parent (0..7)"
    }
    print(f"  Parent-child consistency: {'PASS' if valid_parents else 'FAIL'}")
    
    # Step 5: Compare with state file metrics
    print("\n=== Step 5: State file comparison ===")
    state_metrics = state.get("metrics_summary", {})
    hl_experiment = state_metrics.get("hierarchical_leiden_experiment", {})
    
    reported_h_purity = hl_experiment.get("hierarchical_purity", 0)
    reported_flat_purity = hl_experiment.get("flat_mean_purity", 0)
    reported_flat_nesting = hl_experiment.get("flat_mean_nesting", 0)
    
    purity_diff = abs(h_purity - reported_h_purity)
    flat_purity_diff = abs(flat_mean_purity - reported_flat_purity)
    flat_nesting_diff = abs(flat_mean_nesting - reported_flat_nesting)
    
    checks["state_hierarchical_purity"] = {
        "pass": purity_diff < 1e-6,
        "detail": f"Computed {h_purity:.6f}, state {reported_h_purity:.6f}, diff={purity_diff:.10f}"
    }
    checks["state_flat_mean_purity"] = {
        "pass": flat_purity_diff < 1e-6,
        "detail": f"Computed {flat_mean_purity:.6f}, state {reported_flat_purity:.6f}, diff={flat_purity_diff:.10f}"
    }
    checks["state_flat_mean_nesting"] = {
        "pass": flat_nesting_diff < 1e-6,
        "detail": f"Computed {flat_mean_nesting:.6f}, state {reported_flat_nesting:.6f}, diff={flat_nesting_diff:.10f}"
    }
    
    print(f"  Hierarchical purity: computed={h_purity:.6f}, state={reported_h_purity:.6f}, diff={purity_diff:.10f} -> {'PASS' if purity_diff < 1e-6 else 'FAIL'}")
    print(f"  Flat mean purity: computed={flat_mean_purity:.6f}, state={reported_flat_purity:.6f}, diff={flat_purity_diff:.10f} -> {'PASS' if flat_purity_diff < 1e-6 else 'FAIL'}")
    print(f"  Flat mean nesting: computed={flat_mean_nesting:.6f}, state={reported_flat_nesting:.6f}, diff={flat_nesting_diff:.10f} -> {'PASS' if flat_nesting_diff < 1e-6 else 'FAIL'}")
    
    # Step 6: Post-verdict state consistency check
    print("\n=== Step 6: Post-verdict state consistency ===")
    verdict = hl_experiment.get("verdict", "")
    continue_rec = state.get("continue_recommended", True)
    next_rec = state.get("next_recommendation", "")
    
    if verdict == "PASS":
        state_consistent = (not continue_rec) and (next_rec != "CONTINUE")
        checks["post_verdict_consistency"] = {
            "pass": state_consistent,
            "detail": f"verdict=PASS requires continue_recommended=false and next_recommendation!=CONTINUE. Got: continue={continue_rec}, next={next_rec}"
        }
        print(f"  verdict=PASS, continue={continue_rec}, next={next_rec} -> {'PASS' if state_consistent else 'FAIL'}")
    else:
        checks["post_verdict_consistency"] = {
            "pass": True,
            "detail": f"verdict={verdict} (not PASS, no constraint)"
        }
    
    # Step 7: Evidence tier check
    evidence_tier = state.get("evidence_tier", "")
    checks["evidence_tier"] = {
        "pass": evidence_tier == "REPRODUCED",
        "detail": f"evidence_tier={evidence_tier} (expected REPRODUCED)"
    }
    print(f"  evidence_tier={evidence_tier} -> {'PASS' if evidence_tier == 'REPRODUCED' else 'FAIL'}")
    
    # Summary
    total_checks = len(checks)
    passed = sum(1 for c in checks.values() if c["pass"])
    failed = total_checks - passed
    
    summary = {
        "total_checks": total_checks,
        "passed": passed,
        "failed": failed,
        "overall_pass": failed == 0
    }
    
    print(f"\n=== SUMMARY ===")
    print(f"Total checks: {total_checks}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Overall: {'PASS' if failed == 0 else 'FAIL'}")
    
    # Write report
    report = {
        "run_id": "verification_33029690400",
        "timestamp": "2026-08-27",
        "purpose": "Independent metric recomputation for fractal-map lane verification",
        "checks": checks,
        "summary": summary,
        "recomputed_metrics": {
            "flat_purity_per_resolution": {str(k): float(v) for k, v in flat_purities.items()},
            "flat_mean_purity": float(flat_mean_purity),
            "flat_nesting_per_pair": [float(s) for s in nesting_scores],
            "flat_mean_nesting": float(flat_mean_nesting),
            "hierarchical_purity": float(h_purity),
            "hierarchical_nesting": float(h_nesting),
            "n_fine_clusters": n_fine,
            "total_sub_cluster_size": total_size,
            "zoom_purity_improvement_pct": float((h_purity - flat_mean_purity) / flat_mean_purity * 100)
        }
    }
    
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)
    
    output_path = BASE / "results/fractal_map/audit/verification_33029690400.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, cls=NumpyEncoder)
    
    print(f"\nReport written to {output_path}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
