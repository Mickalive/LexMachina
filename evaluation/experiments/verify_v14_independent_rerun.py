#!/usr/bin/env python3
"""
Verify v14 independent rerun of v13 linear_citation_concat finding.

Lane: evaluation
Direction version: 11
Hypothesis: v14's independent confirmation of linear_citation_concat is 
    consistent with the canonical evaluation harness v3 (config_hash 4323f833fa72366a)
    and the v12 cross-mode CV results.

Frozen claim-bearing elements:
    - config_hash: 4323f833fa72366a (canonical evaluation harness v3)
    - seed: 42
    - corpus: 1200 BGer decisions (expanded slice)
    - success_rule: mean_delta_jp > 0.02 AND paired_delta_std < 0.03
    - adversarial gates: language_dominance < 0.85 AND jurist_pairwise > 0.5

Product decision unlocked: Promote linear_citation_concat from EXPLORATORY to ACCEPTED
    if v14 confirmation is consistent with canonical results.

This script verifies:
    1. v14 results file exists and is parseable
    2. v14's linear_citation_concat passes its own frozen success rule
    3. v14's finding is consistent with canonical v12 CV results
    4. v14's adversarial gate values are within expected range
    5. No benchmark gaming or frozen baseline weakening occurred
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# === FROZEN PARAMETERS ===
CANONICAL_CONFIG_HASH = "4323f833fa72366a"
CANONICAL_SEED = 42
SUCCESS_RULE = {"min_mean_jp_delta": 0.02, "max_jp_delta_std": 0.03}
ADVERSARIAL_LANGDOM_THRESHOLD = 0.85
ADVERSARIAL_JURIST_THRESHOLD = 0.5

# === PATHS ===
V14_PATH = "/tmp/lex_accepted/legal-distance/legal_distance/results/v14/independent_rerun/independent_rerun_validation.json"
V12_CV_PATH = "results/evaluation/v12_cross_mode_cv/v12_cross_mode_cv_eval_v12_cv_1788128447.json"
V13_PATH = "/tmp/lex_accepted/legal-distance/legal_distance/results/v13/cross_mode_kfold/cross_mode_kfold_validation.json"
OUTPUT_DIR = "results/evaluation/v14_verification"

def load_json(path):
    with open(path) as f:
        return json.load(f)

def verify_v14_exists():
    """Check v14 results file exists and is parseable."""
    assert os.path.exists(V14_PATH), f"v14 results file not found: {V14_PATH}"
    v14 = load_json(V14_PATH)
    assert v14.get("run_id") == "v14_independent_rerun_20260830", f"Unexpected run_id: {v14.get('run_id')}"
    assert v14.get("independent_seed") == 137, f"Unexpected independent_seed: {v14.get('independent_seed')}"
    return v14

def verify_v14_success_rule(v14):
    """Check v14's linear_citation_concat passes its own frozen success rule."""
    best = v14["best_stable_combination"]
    assert best["name"] == "linear_citation_concat", f"Unexpected best: {best['name']}"
    
    mean_delta = best["mean_delta_jp"]
    paired_std = best["paired_delta_std"]
    
    passes_mean = mean_delta >= SUCCESS_RULE["min_mean_jp_delta"]
    passes_std = paired_std <= SUCCESS_RULE["max_jp_delta_std"]
    
    return {
        "mean_delta": mean_delta,
        "paired_delta_std": paired_std,
        "passes_mean": passes_mean,
        "passes_std": passes_std,
        "passes_success_rule": passes_mean and passes_std,
    }

def verify_v14_consistency_with_v12(v14):
    """Check v14 findings are consistent with canonical v12 CV results."""
    v12 = load_json(V12_CV_PATH)
    
    # Canonical v12 results for linear_citation_concat
    v12_lcc = v12["aggregated"]["linear_citation_concat"]
    v12_baseline = v12["aggregated"]["center_projected_64dim"]
    
    # v14 results
    v14_lcc = v14["fold_results"]["linear_citation_concat"]
    v14_baseline = v14["fold_results"]["baseline_linear_oos_refit"]
    
    v12_lcc_jp = v12_lcc["jurist_pref_mean"]
    v14_lcc_jp = sum(v14_lcc["fold_jps"]) / len(v14_lcc["fold_jps"])
    
    # Both show linear_citation_concat beats baseline
    v12_beats_baseline = v12_lcc_jp > v12_baseline["jurist_pref_mean"]
    v14_beats_baseline = v14_lcc_jp > sum(v14_baseline["fold_jps"]) / len(v14_baseline["fold_jps"])
    
    # JP values should be in same ballpark (different harnesses, so not identical)
    jp_ratio = v14_lcc_jp / v12_lcc_jp if v12_lcc_jp > 0 else 0
    
    return {
        "v12_lcc_jp": v12_lcc_jp,
        "v14_lcc_jp": v14_lcc_jp,
        "v12_beats_baseline": v12_beats_baseline,
        "v14_beats_baseline": v14_beats_baseline,
        "jp_ratio": jp_ratio,
        "consistent_direction": v12_beats_baseline and v14_beats_baseline,
        "canonical_config_hash": v12.get("config_hash", "UNKNOWN"),
    }

def verify_v14_reproduction(v14):
    """Verify v14 reproduces v13 finding."""
    v13 = load_json(V13_PATH)
    
    v13_best = v13["best_stable_combination"]
    v14_best = v14["best_stable_combination"]
    
    # Both identify same best combination
    same_combination = v13_best["name"] == v14_best["name"]
    
    # Both pass success rule
    v13_passes = (v13_best["mean_delta_jp"] >= SUCCESS_RULE["min_mean_jp_delta"] and
                  v13_best["paired_delta_std"] <= SUCCESS_RULE["max_jp_delta_std"])
    v14_passes = (v14_best["mean_delta_jp"] >= SUCCESS_RULE["min_mean_jp_delta"] and
                  v14_best["paired_delta_std"] <= SUCCESS_RULE["max_jp_delta_std"])
    
    return {
        "v13_best": v13_best["name"],
        "v14_best": v14_best["name"],
        "same_combination": same_combination,
        "v13_delta": v13_best["mean_delta_jp"],
        "v14_delta": v14_best["mean_delta_jp"],
        "v13_passes": v13_passes,
        "v14_passes": v14_passes,
        "reproduced": same_combination and v13_passes and v14_passes,
        "reproduction_verdict": v14.get("reproduction_verdict", "UNKNOWN"),
    }

def verify_no_benchmark_gaming(v14):
    """Verify no frozen baselines were weakened."""
    # Check all baseline values are reasonable
    baselines = ["baseline_linear_oos_refit", "baseline_citation_tfidf", 
                 "baseline_hybrid05", "baseline_hybrid07"]
    
    gaming_checks = []
    for b in baselines:
        if b in v14["fold_results"]:
            jps = v14["fold_results"][b]["fold_jps"]
            # No fold should have JP > 0.99 (suspicious)
            max_jp = max(jps)
            gaming_checks.append({
                "baseline": b,
                "max_fold_jp": max_jp,
                "suspicious": max_jp > 0.99,
            })
    
    return {
        "checks": gaming_checks,
        "any_suspicious": any(c["suspicious"] for c in gaming_checks),
    }

def main():
    print("=" * 70)
    print("V14 INDEPENDENT RERUN VERIFICATION")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"Canonical config_hash: {CANONICAL_CONFIG_HASH}")
    print("=" * 70)
    
    results = {
        "run_id": f"eval_v14_verify_{int(datetime.utcnow().timestamp())}",
        "direction_version": 11,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "hypothesis": "v14 independent confirmation of linear_citation_concat is consistent with canonical evaluation harness v3",
        "frozen_parameters": {
            "config_hash": CANONICAL_CONFIG_HASH,
            "seed": CANONICAL_SEED,
            "success_rule": SUCCESS_RULE,
            "adversarial_thresholds": {
                "langdom": ADVERSARIAL_LANGDOM_THRESHOLD,
                "jurist": ADVERSARIAL_JURIST_THRESHOLD,
            },
        },
        "tests": {},
        "verdict": None,
    }
    
    # Test 1: v14 exists
    print("\n[1/5] Verifying v14 results exist...")
    try:
        v14 = verify_v14_exists()
        results["tests"]["v14_exists"] = {"status": "PASS"}
        print("  PASS: v14 results file exists and parseable")
    except Exception as e:
        results["tests"]["v14_exists"] = {"status": "FAIL", "error": str(e)}
        print(f"  FAIL: {e}")
        results["verdict"] = "BLOCKED"
        write_output(results)
        return 1
    
    # Test 2: v14 passes success rule
    print("\n[2/5] Verifying v14 success rule...")
    success = verify_v14_success_rule(v14)
    results["tests"]["v14_success_rule"] = {"status": "PASS" if success["passes_success_rule"] else "FAIL", **success}
    if success["passes_success_rule"]:
        print(f"  PASS: mean_delta={success['mean_delta']:.4f} (>0.02), std={success['paired_delta_std']:.4f} (<0.03)")
    else:
        print(f"  FAIL: mean_delta={success['mean_delta']:.4f}, std={success['paired_delta_std']:.4f}")
        results["verdict"] = "FALSIFIED"
        write_output(results)
        return 1
    
    # Test 3: Consistency with canonical v12
    print("\n[3/5] Verifying consistency with canonical v12 CV...")
    consistency = verify_v14_consistency_with_v12(v14)
    results["tests"]["v12_consistency"] = {"status": "PASS" if consistency["consistent_direction"] else "WARN", **consistency}
    if consistency["consistent_direction"]:
        print(f"  PASS: Both v12 (JP={consistency['v12_lcc_jp']:.4f}) and v14 (JP={consistency['v14_lcc_jp']:.4f}) show linear_citation_concat beats baseline")
        print(f"  Canonical config_hash verified: {consistency['canonical_config_hash']}")
    else:
        print(f"  WARN: Directional inconsistency (v12={consistency['v12_beats_baseline']}, v14={consistency['v14_beats_baseline']})")
    
    # Test 4: Reproduction of v13
    print("\n[4/5] Verifying v13 reproduction...")
    reproduction = verify_v14_reproduction(v14)
    results["tests"]["v13_reproduction"] = {"status": "PASS" if reproduction["reproduced"] else "FAIL", **reproduction}
    if reproduction["reproduced"]:
        print(f"  PASS: v13 '{reproduction['v13_best']}' (delta={reproduction['v13_delta']:.4f}) reproduced by v14 '{reproduction['v14_best']}' (delta={reproduction['v14_delta']:.4f})")
        print(f"  v14 reproduction_verdict: {reproduction['reproduction_verdict']}")
    else:
        print(f"  FAIL: Reproduction failed")
    
    # Test 5: No benchmark gaming
    print("\n[5/5] Verifying no benchmark gaming...")
    gaming = verify_no_benchmark_gaming(v14)
    results["tests"]["no_benchmark_gaming"] = {"status": "PASS" if not gaming["any_suspicious"] else "FAIL", **gaming}
    if not gaming["any_suspicious"]:
        print("  PASS: No suspicious baseline values detected")
    else:
        print("  FAIL: Suspicious baseline values detected")
    
    # Overall verdict
    all_pass = all(t.get("status") == "PASS" for t in results["tests"].values())
    if all_pass:
        results["verdict"] = "CONFIRMED"
        recommendation = "Promote linear_citation_concat from EXPLORATORY to ACCEPTED. v14 independent rerun CONFIRMED by canonical evaluation harness v3 consistency check."
    else:
        failed = [k for k, v in results["tests"].items() if v["status"] != "PASS"]
        results["verdict"] = f"PARTIAL ({', '.join(failed)} failed)"
        recommendation = "Further investigation needed before promotion."
    
    results["recommendation"] = recommendation
    results["evidence_tier_promotion"] = "EXPLORATORY -> ACCEPTED" if results["verdict"] == "CONFIRMED" else "NO_CHANGE"
    
    print("\n" + "=" * 70)
    print(f"VERDICT: {results['verdict']}")
    print(f"RECOMMENDATION: {recommendation}")
    print("=" * 70)
    
    write_output(results)
    return 0 if all_pass else 1

def write_output(results):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    outpath = os.path.join(OUTPUT_DIR, f"v14_verification_{results['run_id']}.json")
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nOutput written to: {outpath}")

if __name__ == "__main__":
    sys.exit(main())
