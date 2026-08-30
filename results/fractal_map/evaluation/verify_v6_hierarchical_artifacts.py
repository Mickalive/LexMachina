#!/usr/bin/env python3
"""
Independent verification of v6 hierarchical artifact completion.

Recomputes labels_hierarchical_best and labels_coarse_0.5 from the original
labels_res_*.npy files and checks they match the generated artifacts.
Also verifies hierarchical_map_results.json contains valid metrics.

PROVENANCE RULE: For legal-distance modes, hierarchical_best := labels_res_3.0.
"""

import json
import numpy as np
from pathlib import Path

BASE = Path("/home/runner/work/LexMachina/LexMachina")
RESULTS_DIR = BASE / "results/fractal_map/legal_distance_modes"

INCOMPLETE_MODES = [
    "debiased_citation_blended",
    "hybrid_alpha_03",
    "hybrid_alpha_05",
    "legal_cited_decisions_only",
    "legal_issues_outcomes",
]


def verify_mode(mode_id):
    """Verify the generated artifacts are consistent with source data."""
    mode_dir = RESULTS_DIR / mode_id
    issues = []

    # 1. Verify labels_hierarchical_best == labels_res_3.0
    hier_best = np.load(mode_dir / "labels_hierarchical_best.npy")
    res_3 = np.load(mode_dir / "labels_res_3.0.npy")
    if not np.array_equal(hier_best, res_3):
        issues.append("labels_hierarchical_best != labels_res_3.0")
    if len(hier_best) != 1000:
        issues.append(f"labels_hierarchical_best has {len(hier_best)} entries, expected 1000")

    # 2. Verify labels_coarse_0.5 == labels_res_0.5
    coarse = np.load(mode_dir / "labels_coarse_0.5.npy")
    res_05 = np.load(mode_dir / "labels_res_0.5.npy")
    if not np.array_equal(coarse, res_05):
        issues.append("labels_coarse_0.5 != labels_res_0.5")
    if len(coarse) != 1000:
        issues.append(f"labels_coarse_0.5 has {len(coarse)} entries, expected 1000")

    # 3. Verify hierarchical_map_results.json
    with open(mode_dir / "hierarchical_map_results.json") as f:
        data = json.load(f)

    if data["corpus_size"] != 1000:
        issues.append(f"corpus_size {data['corpus_size']} != 1000")
    if data["mean_nesting_score"] != 1.0:
        issues.append(f"mean_nesting_score {data['mean_nesting_score']} != 1.0")
    if data["direction_version"] != 10:
        issues.append(f"direction_version {data['direction_version']} != 10")

    # 4. Verify hierarchical.n_clusters matches actual unique labels
    n_clusters_json = data["hierarchical"]["n_clusters"]
    n_clusters_actual = len(set(hier_best[hier_best != -1]))
    if n_clusters_json != n_clusters_actual:
        issues.append(f"hierarchical.n_clusters {n_clusters_json} != actual {n_clusters_actual}")

    # 5. Verify all 7 resolutions present in hierarchy_info
    for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        key = f"res_{res}"
        if key not in data["hierarchy_info"]:
            issues.append(f"Missing hierarchy_info key: {key}")

    # 6. Verify 6 nesting transitions
    if len(data["nesting"]) != 6:
        issues.append(f"nesting has {len(data['nesting'])} transitions, expected 6")

    # 7. Verify 6 zoom_coherence transitions
    if len(data["zoom_coherence"]) != 6:
        issues.append(f"zoom_coherence has {len(data['zoom_coherence'])} transitions, expected 6")

    return {
        "mode_id": mode_id,
        "verified": len(issues) == 0,
        "issues": issues,
        "n_fine_clusters": n_clusters_actual,
        "nesting_score": data["mean_nesting_score"],
        "hier_purity": data["hierarchical"]["branch_purity"],
        "coarse_purity": data["hierarchical"]["coarse_0.5_purity"],
    }


def main():
    results = []
    all_pass = True
    for mode_id in INCOMPLETE_MODES:
        r = verify_mode(mode_id)
        results.append(r)
        status = "PASS" if r["verified"] else "FAIL"
        print(f"{status} {mode_id}: fine={r['n_fine_clusters']}, "
              f"nesting={r['nesting_score']:.4f}, "
              f"hier_purity={r['hier_purity']:.4f}, "
              f"coarse_purity={r['coarse_purity']:.4f}")
        if not r["verified"]:
            all_pass = False
            for issue in r["issues"]:
                print(f"  ISSUE: {issue}")

    output = {
        "run_id": "v6_hierarchical_artifact_verification",
        "modes_verified": len(results),
        "all_pass": all_pass,
        "results": results,
    }

    out_path = BASE / "results/fractal_map/evaluation/v6_hierarchical_artifact_verification.json"
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'ALL PASS' if all_pass else 'SOME FAILED'}: {len(results)} modes verified")
    print(f"Results written to {out_path}")


if __name__ == "__main__":
    main()
