#!/usr/bin/env python3
"""
Regression test for the anti-noise procedural-passage sensitivity experiment.

Guards two claims against future regression:
1. The ACCEPTED shallow real-boilerplate conclusion reproduces (0.9325 preservation).
2. The anti-noise negative finding is preserved: deep procedural removal does NOT drop
   neighbor preservation more than an equal-volume content-neutral control
   (procedural-specific excess < 0.03). This test exists precisely so a future
   no-control run cannot reintroduce a false "FRAGILE" claim.
"""

import json
from pathlib import Path

RESULTS_PATH = Path("evaluation/results/v3_boilerplate_antinoise/anti_noise_procedural_sensitivity_raw.json")

SHALLOW_EXPECTED = 0.9325
TOLERANCE = 1e-3
FRAGILE_EXCESS_THRESHOLD = 0.03  # frozen in success rule


def load_results() -> dict:
    if not RESULTS_PATH.exists():
        raise FileNotFoundError(f"Raw results not found at {RESULTS_PATH}")
    with open(RESULTS_PATH) as f:
        return json.load(f)


def test_shallow_reproduction():
    """The accepted shallow real-boilerplate conclusion must reproduce."""
    data = load_results()
    shallow = data["tiers"]["shallow_accepted"]["mean_preservation_rate"]
    assert abs(shallow - SHALLOW_EXPECTED) <= TOLERANCE, (
        f"shallow preservation {shallow:.4f} != accepted {SHALLOW_EXPECTED:.4f}"
    )
    print(f"  OK shallow preservation {shallow:.4f} reproduces accepted value")


def test_procedural_specific_excess_below_threshold():
    """Deep procedural removal must NOT exceed equal-volume content control by >=0.03."""
    data = load_results()
    shallow = data["tiers"]["shallow_accepted"]["mean_preservation_rate"]
    # Use the most aggressive tier (deep_target_25)
    deep = data["tiers"]["deep_target_25"]
    proc_rate = deep["mean_preservation_rate"]
    ctrl_rate = deep["control"]["mean_preservation_rate"]
    proc_delta = shallow - proc_rate
    ctrl_delta = shallow - ctrl_rate
    excess = proc_delta - ctrl_delta
    assert excess <= FRAGILE_EXCESS_THRESHOLD, (
        f"procedural-specific excess {excess:.4f} >= {FRAGILE_EXCESS_THRESHOLD}: "
        "would indicate anti-noise leak; negative finding violated"
    )
    assert excess < 0.03, f"excess={excess:.4f}"
    print(f"  OK procedural-specific excess {excess:.4f} < {FRAGILE_EXCESS_THRESHOLD} (robust)")


def test_control_present():
    """Ensure the content-neutral control exists (guard against no-control false FRAGILE)."""
    data = load_results()
    for tier_name in ["deep_target_15", "deep_target_25"]:
        assert "control" in data["tiers"][tier_name], f"{tier_name} missing control"
    assert "control_delta" in data
    print("  OK equal-volume content-neutral control present across aggressive tiers")


def main():
    print("Anti-noise procedural sensitivity regression")
    test_shallow_reproduction()
    test_control_present()
    test_procedural_specific_excess_below_threshold()
    print("\nPASSED: anti-noise negative finding preserved")


if __name__ == "__main__":
    main()
