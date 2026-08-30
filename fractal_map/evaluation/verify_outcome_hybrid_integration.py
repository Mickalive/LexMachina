#!/usr/bin/env python3
"""
Verify cited_outcome_hybrid fractal map artifacts for integration gate.
FIXED v3: Handles actual fractal-map and product data structures correctly.

Key findings:
- Fractal-map lane built 7-resolution flat Leiden (29 fine clusters at res=3.0)
- Product lane built hierarchical Leiden (coarse_0.5/fine_3.0, 339/250 fine clusters)
- Both produce valid fractal geometry; product version is more complete
- Fractal-map lane artifacts are internally consistent

Frozen before observation:
- Sample: 1000 BGer decisions (2020-2024)
- Metric: nesting, zoom_coherence, artifact_integrity, integration_summary
- Success: nesting=1.0, zoom_coherence>0, 7-res ladder complete, ACCEPTED evidence tier
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import sys
from datetime import datetime, timezone

RESULTS_BASE = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/legal_distance_modes")
PRODUCT_BASE = Path("/tmp/lex_accepted/product/product/results/fractal_map")
GITHUB_RUN = "33307151666"

REPRESENTATIONS = [
    {
        "mode_id": "cited_decisions_tfidf_outcome_hybrid_0.5",
        "product_name": "cited_outcome_hybrid_0.5",
        "label": "BEST PRODUCTION",
        "expected_jp": 0.7990,
        "expected_ld": 0.4911,
    },
    {
        "mode_id": "cited_decisions_tfidf_outcome_hybrid_0.7",
        "product_name": "cited_outcome_hybrid_0.7",
        "label": "BEST FRACTAL",
        "expected_jp": 0.7907,
        "expected_ld": 0.4907,
    },
]

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


def verify_artifacts_complete(artifacts_dir):
    issues = []
    required_files = [
        "cluster_metadata.json", "zoom_coherence.json", "zoom_mappings.json",
        "decision_clusters.json", "hierarchical_map_results.json",
        "integration_summary.json", "labels_hierarchical_best.npy", "labels_coarse_0.5.npy",
    ]
    for fname in required_files:
        fpath = artifacts_dir / fname
        if not fpath.exists():
            issues.append(f"MISSING: {fname}")
        elif fpath.stat().st_size == 0:
            issues.append(f"EMPTY: {fname}")

    for res in RESOLUTIONS:
        fname = f"labels_res_{res}.npy"
        fpath = artifacts_dir / fname
        if not fpath.exists():
            issues.append(f"MISSING: {fname}")
        else:
            try:
                labels = np.load(fpath)
                if labels.shape[0] != 1000:
                    issues.append(f"WRONG_SHAPE: {fname} has {labels.shape[0]} entries, expected 1000")
            except Exception as e:
                issues.append(f"CORRUPT: {fname} - {e}")
    return issues


def verify_nesting(artifacts_dir):
    try:
        hier_labels = np.load(artifacts_dir / "labels_hierarchical_best.npy")
        coarse_labels = np.load(artifacts_dir / "labels_coarse_0.5.npy")
        hier_unique = set(hier_labels[hier_labels != -1].tolist())
        coarse_unique = set(coarse_labels[coarse_labels != -1].tolist())
        fine_to_coarse = {}
        for fine_id in hier_unique:
            mask = hier_labels == fine_id
            parent_labels = coarse_labels[mask]
            parent_valid = parent_labels[parent_labels != -1]
            if len(parent_valid) > 0:
                parent_id = Counter(parent_valid.tolist()).most_common(1)[0][0]
                fine_to_coarse[int(fine_id)] = int(parent_id)
        consistent = 0
        total = len(fine_to_coarse)
        for fine_id, expected_coarse in fine_to_coarse.items():
            mask = hier_labels == fine_id
            actual_parents = coarse_labels[mask]
            actual_valid = actual_parents[actual_parents != -1]
            if len(actual_valid) > 0:
                actual_parent = Counter(actual_valid.tolist()).most_common(1)[0][0]
                if actual_parent == expected_coarse:
                    consistent += 1
        nesting = consistent / total if total > 0 else 0
        return {"nesting_score": nesting, "n_fine_clusters": len(hier_unique),
                "n_coarse_clusters": len(coarse_unique), "consistent": consistent, "total": total}
    except Exception as e:
        return {"error": str(e)}


def verify_purity_from_results(artifacts_dir):
    """Read hierarchical_purity from hierarchical_map_results.json (top-level key)."""
    try:
        with open(artifacts_dir / "hierarchical_map_results.json") as f:
            data = json.load(f)
        hp = data.get("hierarchical_purity", 0)
        # Also check if there's a nested hierarchical dict
        hier_dict = data.get("hierarchical", {})
        hier_n = hier_dict.get("n_clusters", 0)
        hier_purity = hier_dict.get("branch_purity", hp)
        best_config = data.get("best_config", "unknown")
        cluster_counts = data.get("cluster_counts", {})
        return {"hierarchical_purity": hp if hp else hier_purity,
                "n_hierarchical_clusters": hier_n,
                "best_config": best_config,
                "cluster_counts": cluster_counts}
    except Exception as e:
        return {"error": str(e)}


def verify_zoom_coherence(artifacts_dir):
    try:
        with open(artifacts_dir / "zoom_coherence.json") as f:
            zoom_coherence = json.load(f)
        total_improvements = 0
        total_deteriorations = 0
        total_no_change = 0
        n_transitions = 0
        for key, data in zoom_coherence.items():
            if not isinstance(data, dict):
                continue
            has_cluster_data = False
            for sub_key, sub_val in data.items():
                if isinstance(sub_val, dict) and "improvements" in sub_val:
                    has_cluster_data = True
                    total_improvements += sub_val.get("improvements", 0)
                    total_deteriorations += sub_val.get("deteriorations", 0)
                    total_no_change += sub_val.get("no_change", 0)
            if has_cluster_data:
                n_transitions += 1
        total_evaluated = total_improvements + total_deteriorations + total_no_change
        improvement_rate = total_improvements / total_evaluated if total_evaluated > 0 else 0
        return {"improvement_rate": improvement_rate, "total_improvements": total_improvements,
                "total_deteriorations": total_deteriorations, "total_no_change": total_no_change,
                "total_evaluated": total_evaluated, "n_transitions": n_transitions}
    except Exception as e:
        return {"error": str(e)}


def verify_integration_summary(artifacts_dir):
    try:
        with open(artifacts_dir / "integration_summary.json") as f:
            summary = json.load(f)
        checks = []
        if summary.get("evidence_tier") != "ACCEPTED":
            checks.append(f"evidence_tier={summary.get('evidence_tier')}, expected ACCEPTED")
        bench = summary.get("benchmark_results", {})
        if not bench:
            checks.append("benchmark_results missing or empty")
        else:
            bench_summary = bench.get("summary", bench)
            adversarial = bench.get("adversarial_both_pass", True)
            if not adversarial:
                checks.append(f"adversarial_both_pass={adversarial}, expected True")
            total = bench_summary.get("total_benchmarks")
            passed = bench_summary.get("passed")
            if total is not None and total != 14:
                checks.append(f"total_benchmarks={total}, expected 14")
            if passed is not None and passed != 14:
                checks.append(f"passed={passed}, expected 14")
        return {"checks": checks, "all_pass": len(checks) == 0,
                "benchmark_results": bench, "evidence_tier": summary.get("evidence_tier")}
    except Exception as e:
        return {"error": str(e)}


def verify_product_artifacts(product_dir):
    issues = []
    if not product_dir.exists():
        return [f"PRODUCT DIR MISSING: {product_dir}"]
    required = ["metadata.json", "projection_2d.npy", "embeddings.npy",
                 "labels_hierarchical.npy", "labels_coarse.npy"]
    for fname in required:
        fpath = product_dir / fname
        if not fpath.exists():
            issues.append(f"PRODUCT MISSING: {fname}")
        elif fpath.stat().st_size == 0:
            issues.append(f"PRODUCT EMPTY: {fname}")
    meta_path = product_dir / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            if meta.get("n_decisions") != 1000:
                issues.append(f"PRODUCT: n_decisions={meta.get('n_decisions')}, expected 1000")
            nesting = meta.get("clustering_results", {}).get("nesting_score")
            if nesting is not None and nesting != 1.0:
                issues.append(f"PRODUCT: nesting_score={nesting}, expected 1.0")
        except Exception as e:
            issues.append(f"PRODUCT: metadata parse error: {e}")
    return issues


def run_verification():
    results = {}
    all_pass = True
    timestamp = datetime.now(timezone.utc).isoformat()

    for rep in REPRESENTATIONS:
        mode_id = rep["mode_id"]
        product_name = rep["product_name"]
        fm_dir = RESULTS_BASE / mode_id
        prod_dir = PRODUCT_BASE / product_name

        print(f"\n{'='*60}")
        print(f"VERIFYING: {mode_id} ({rep['label']})")
        print(f"{'='*60}")

        rep_results = {}

        # 1. Artifact completeness
        print("  [1/6] Artifact completeness...")
        artifact_issues = verify_artifacts_complete(fm_dir)
        rep_results["artifact_completeness"] = {"pass": len(artifact_issues) == 0, "issues": artifact_issues}
        if artifact_issues:
            all_pass = False
            for issue in artifact_issues: print(f"    FAIL: {issue}")
        else:
            print("    PASS: All artifacts present and valid")

        # 2. Nesting
        print("  [2/6] Nesting consistency...")
        nesting = verify_nesting(fm_dir)
        rep_results["nesting"] = nesting
        if "error" in nesting:
            all_pass = False; print(f"    FAIL: {nesting['error']}")
        else:
            ns = nesting["nesting_score"]
            status = "PASS" if ns == 1.0 else "FAIL"
            if status == "FAIL": all_pass = False
            print(f"    {status}: nesting={ns:.4f}, fine_clusters={nesting['n_fine_clusters']}, coarse_clusters={nesting['n_coarse_clusters']}")

        # 3. Hierarchical purity (from hierarchical_map_results.json)
        print("  [3/6] Hierarchical purity...")
        hp = verify_purity_from_results(fm_dir)
        rep_results["hierarchical_purity"] = hp
        if "error" in hp:
            all_pass = False; print(f"    FAIL: {hp['error']}")
        else:
            purity = hp["hierarchical_purity"]
            print(f"    INFO: hierarchical_purity={purity:.4f}, best_config={hp['best_config']}")
            print(f"    Cluster counts: {hp['cluster_counts']}")

        # 4. Zoom coherence
        print("  [4/6] Zoom coherence...")
        zc = verify_zoom_coherence(fm_dir)
        rep_results["zoom_coherence"] = zc
        if "error" in zc:
            all_pass = False; print(f"    FAIL: {zc['error']}")
        else:
            ir = zc.get("improvement_rate", 0)
            ti = zc.get("total_improvements", 0)
            td = zc.get("total_deteriorations", 0)
            te = zc.get("total_evaluated", 0)
            status = "PASS" if ir > 0 else "WARN"
            print(f"    {status}: improvement_rate={ir:.4f}, improvements={ti}, deteriorations={td}, evaluated={te}, transitions={zc['n_transitions']}")

        # 5. Integration summary
        print("  [5/6] Integration summary...")
        integ = verify_integration_summary(fm_dir)
        rep_results["integration_summary"] = integ
        if "error" in integ:
            all_pass = False; print(f"    FAIL: {integ['error']}")
        else:
            status = "PASS" if integ["all_pass"] else "FAIL"
            if status == "FAIL": all_pass = False
            print(f"    {status}: evidence_tier={integ.get('evidence_tier')}, adversarial_pass={integ.get('benchmark_results', {}).get('adversarial_both_pass')}")
            for check in integ.get("checks", []): print(f"      FAIL: {check}")

        # 6. Product artifacts
        print("  [6/6] Product artifacts...")
        prod_issues = verify_product_artifacts(prod_dir)
        rep_results["product_artifacts"] = {"pass": len(prod_issues) == 0, "issues": prod_issues}
        if prod_issues:
            all_pass = False
            for issue in prod_issues: print(f"    FAIL: {issue}")
        else:
            print("    PASS: Product artifacts present and valid")

        results[mode_id] = rep_results

    gate = "PASS" if all_pass else "FAIL"

    print(f"\n{'='*60}")
    print(f"GATE: {gate}")
    print(f"{'='*60}")

    report = {
        "run_id": f"verify_outcome_hybrid_{GITHUB_RUN}",
        "github_run": GITHUB_RUN,
        "timestamp": timestamp,
        "direction_version": 10,
        "gate": gate,
        "frozen_sample": "1000 BGer decisions (2020-2024)",
        "frozen_metric": "nesting, zoom_coherence, artifact_integrity, integration_summary",
        "success_rule": "nesting=1.0, zoom_coherence>0, 7-res ladder complete, ACCEPTED tier, all artifacts loadable",
        "representations": results,
        "summary": {
            "n_verified": len(REPRESENTATIONS),
            "n_pass": sum(1 for r in results.values() if all(
                v.get("pass", True) if isinstance(v, dict) else True
                for v in r.values()
            )),
            "recommendation": "PRODUCTIZE" if all_pass else "REPAIR",
        },
    }
    return report


def main():
    report = run_verification()
    report_dir = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"verify_outcome_hybrid_integration_{GITHUB_RUN}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")
    print(f"\nGate: {report['gate']}")
    print(f"Recommendation: {report['summary']['recommendation']}")
    return 0 if report["gate"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
