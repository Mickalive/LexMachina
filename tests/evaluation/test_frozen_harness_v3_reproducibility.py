#!/usr/bin/env python3
"""
Regression test for frozen evaluation harness v3 reproducibility.

This test verifies that the frozen evaluation harness v3 (seed=42) produces
consistent results for the baseline representations. It should PASS if results
match the accepted baseline within tolerance.

Accepted baseline (GitHub run 33283750508, config_hash=4323f833fa72366a):
- center_projected_64dim: PASS, lang_dom=0.7664, jurist_pref=0.5121
- center_projected_768: FAIL, lang_dom=0.7738, jurist_pref=0.4912
- linear_metric_epoch4: PASS, lang_dom=0.6805, jurist_pref=0.6847
- mahalanobis_metric_epoch4: PASS, lang_dom=0.6843, jurist_pref=0.6781
- hybrid_stabilized_epoch1: PASS, lang_dom=0.6704, jurist_pref=0.6656
- hybrid_v2_epoch3: PASS, lang_dom=0.7115, jurist_pref=0.5988
"""

import json
import numpy as np
from pathlib import Path

# Tolerance for floating-point comparison
TOLERANCE = 1e-3

# Accepted baseline results (from state/evaluation.json validation_metrics)
ACCEPTED_BASELINE = {
    "center_projected_768": {
        "verdict": "FAIL",
        "adversarial_language_dominance": 0.7737698081734778,
        "jurist_pairwise_preference": 0.4912,
        "both_adversarial_pass": False,
    },
    "center_projected_64dim": {
        "verdict": "PASS",
        "adversarial_language_dominance": 0.7663886572143453,
        "jurist_pairwise_preference": 0.5121,
        "both_adversarial_pass": True,
    },
    "linear_metric_epoch4": {
        "verdict": "PASS",
        "adversarial_language_dominance": 0.6805254378648874,
        "jurist_pairwise_preference": 0.6847,
        "both_adversarial_pass": True,
    },
    "mahalanobis_metric_epoch4": {
        "verdict": "PASS",
        "adversarial_language_dominance": 0.684278565471226,
        "jurist_pairwise_preference": 0.6781,
        "both_adversarial_pass": True,
    },
    "hybrid_stabilized_epoch1": {
        "verdict": "PASS",
        "adversarial_language_dominance": 0.6704336947456214,
        "jurist_pairwise_preference": 0.6656,
        "both_adversarial_pass": True,
    },
    "hybrid_v2_epoch3": {
        "verdict": "PASS",
        "adversarial_language_dominance": 0.7114678899082568,
        "jurist_pairwise_preference": 0.5988,
        "both_adversarial_pass": True,
    },
}


def load_current_results() -> dict:
    """Load current evaluation v3 results."""
    results_path = Path("evaluation/results/v3/evaluation_v3_results.json")
    if not results_path.exists():
        raise FileNotFoundError(f"Results not found at {results_path}")
    
    with open(results_path) as f:
        return json.load(f)


def compare_results(name: str, current: dict, accepted: dict) -> list:
    """Compare current results with accepted baseline. Return list of discrepancies."""
    errors = []
    
    if 'error' in current:
        errors.append(f"{name}: ERROR in current results - {current.get('error')}")
        return errors
    
    # Compare verdict
    if current.get('verdict') != accepted['verdict']:
        errors.append(f"{name}: verdict mismatch - current={current.get('verdict')}, accepted={accepted['verdict']}")
    
    # Compare adversarial language dominance
    curr_ld = current.get('adversarial', {}).get('language_dominance_score', 0)
    acc_ld = accepted['adversarial_language_dominance']
    if abs(curr_ld - acc_ld) > TOLERANCE:
        errors.append(f"{name}: lang_dom mismatch - current={curr_ld:.6f}, accepted={acc_ld:.6f}, diff={abs(curr_ld - acc_ld):.6f}")
    
    # Compare jurist pairwise preference
    curr_jp = current.get('adversarial', {}).get('jurist_preference_rate', 0)
    acc_jp = accepted['jurist_pairwise_preference']
    if abs(curr_jp - acc_jp) > TOLERANCE:
        errors.append(f"{name}: jurist_pref mismatch - current={curr_jp:.6f}, accepted={acc_jp:.6f}, diff={abs(curr_jp - acc_jp):.6f}")
    
    # Compare both_adversarial_pass
    curr_both = current.get('both_adversarial_pass', False)
    acc_both = accepted['both_adversarial_pass']
    if curr_both != acc_both:
        errors.append(f"{name}: both_adversarial_pass mismatch - current={curr_both}, accepted={acc_both}")
    
    return errors


def test_frozen_harness_reproducibility():
    """Main test function."""
    print("Loading current evaluation v3 results...")
    current_results = load_current_results()
    
    all_errors = []
    
    for name, accepted in ACCEPTED_BASELINE.items():
        if name not in current_results:
            all_errors.append(f"{name}: MISSING from current results")
            continue
        
        current = current_results[name]
        errors = compare_results(name, current, accepted)
        all_errors.extend(errors)
        
        if not errors:
            print(f"  ✓ {name}: REPRODUCED")
        else:
            for e in errors:
                print(f"  ✗ {e}")
    
    # Summary
    print(f"\n{'='*60}")
    if all_errors:
        print(f"FAILED: {len(all_errors)} discrepancy(ies) found")
        for e in all_errors:
            print(f"  - {e}")
        return False
    else:
        print(f"PASSED: All {len(ACCEPTED_BASELINE)} representations REPRODUCED within tolerance {TOLERANCE}")
        return True


if __name__ == "__main__":
    success = test_frozen_harness_reproducibility()
    exit(0 if success else 1)