#!/usr/bin/env python3
"""
Test: Product Integration Verification v11

Verifies that the product integration verification protocol correctly:
1. Identifies all product map_representations
2. Cross-references against accepted evaluation metrics
3. Flags BEST production hybrids (cited_outcome_hybrid_0.5/0.7) as NOT in product
4. All 3 regression tests PASS (frozen harness, cross-lingual, boilerplate)

Frozen harness v3: seed=42, config_hash=4323f833fa72366a
"""

import json
import sys
from pathlib import Path

WORKSPACE = Path("/home/runner/work/LexMachina/LexMachina")
RESULTS_PATH = WORKSPACE / "results" / "evaluation" / "product_integration_verification_v11.json"

def test_product_integration_verification_results_exist():
    """Verify the verification results file was produced."""
    assert RESULTS_PATH.exists(), f"Verification results not found: {RESULTS_PATH}"
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    assert "run_id" in results, "Missing run_id in results"
    assert "adversarial_gate_results" in results, "Missing adversarial_gate_results"
    print(f"✅ Verification results exist: {RESULTS_PATH}")

def test_best_production_hybrids_identified():
    """Verify that BEST production hybrids are flagged as NOT in product."""
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    
    gate_results = results["adversarial_gate_results"]
    
    # cited_decisions_tfidf_outcome_hybrid_0.5 should PASS adversarial gates
    assert "cited_decisions_tfidf_outcome_hybrid_0.5" in gate_results
    hybrid_05 = gate_results["cited_decisions_tfidf_outcome_hybrid_0.5"]
    assert hybrid_05["verdict"] == "PASS", f"hybrid_0.5 should PASS, got {hybrid_05['verdict']}"
    assert hybrid_05["jurist_pairwise"]["value"] > 0.7, f"hybrid_0.5 JP should be >0.7, got {hybrid_05['jurist_pairwise']['value']}"
    
    # cited_decisions_tfidf_outcome_hybrid_0.7 should PASS adversarial gates
    assert "cited_decisions_tfidf_outcome_hybrid_0.7" in gate_results
    hybrid_07 = gate_results["cited_decisions_tfidf_outcome_hybrid_0.7"]
    assert hybrid_07["verdict"] == "PASS", f"hybrid_0.7 should PASS, got {hybrid_07['verdict']}"
    assert hybrid_07["jurist_pairwise"]["value"] > 0.7, f"hybrid_0.7 JP should be >0.7, got {hybrid_07['jurist_pairwise']['value']}"
    
    # Both should be in gaps as NOT in product
    gaps = results["gaps"]
    assert "cited_decisions_tfidf_outcome_hybrid_0.5" in gaps["in_eval_not_product"], \
        "hybrid_0.5 should be flagged as evaluated but not in product"
    assert "cited_decisions_tfidf_outcome_hybrid_0.7" in gaps["in_eval_not_product"], \
        "hybrid_0.7 should be flagged as evaluated but not in product"
    
    print(f"✅ BEST production hybrids correctly identified: JP={hybrid_05['jurist_pairwise']['value']:.4f}, {hybrid_07['jurist_pairwise']['value']:.4f}")

def test_adversarial_gate_summary():
    """Verify adversarial gate summary matches expected counts."""
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    
    summary = results["summary"]
    assert summary["total_evaluated"] == 24, f"Expected 24 evaluated, got {summary['total_evaluated']}"
    assert summary["pass_count"] == 20, f"Expected 20 PASS, got {summary['pass_count']}"
    assert summary["fail_count"] == 4, f"Expected 4 FAIL, got {summary['fail_count']}"
    
    print(f"✅ Adversarial gate summary: {summary['pass_count']}/{summary['total_evaluated']} PASS ({summary['pass_rate']})")

def test_all_3_regression_tests_pass():
    """Verify all 3 regression tests PASS."""
    import subprocess
    
    tests = [
        "tests/evaluation/test_frozen_harness_v3_reproducibility.py",
        "tests/evaluation/test_cross_lingual_alignment_v10.py",
        "tests/evaluation/test_boilerplate_resistance_real.py",
    ]
    
    for test in tests:
        result = subprocess.run(
            ["python", "-m", "pytest", test, "-v", "--tb=short"],
            capture_output=True, text=True, cwd=str(WORKSPACE)
        )
        assert result.returncode == 0, f"Regression test FAILED: {test}\n{result.stdout}\n{result.stderr}"
    
    print(f"✅ All 3 regression tests PASS")

def test_known_failures_correctly_excluded():
    """Verify known FAIL representations are correctly identified."""
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    
    gate_results = results["adversarial_gate_results"]
    
    known_failures = ["center_projected_768", "cited_decisions_tfidf_procrustes", 
                      "cited_decisions_tfidf_cca", "criticizing_alpha0.7"]
    
    for name in known_failures:
        assert name in gate_results, f"Known failure {name} not in gate_results"
        assert gate_results[name]["verdict"] == "FAIL", f"{name} should FAIL, got {gate_results[name]['verdict']}"
    
    print(f"✅ Known failures correctly identified: {known_failures}")

if __name__ == "__main__":
    tests = [
        test_product_integration_verification_results_exist,
        test_best_production_hybrids_identified,
        test_adversarial_gate_summary,
        test_all_3_regression_tests_pass,
        test_known_failures_correctly_excluded,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    
    sys.exit(0 if failed == 0 else 1)
