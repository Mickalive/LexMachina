"""
Evaluation v18: Coarse-Label Hierarchy + Multi-Seed Verification tests.

Verifies that the v18 result JSON is well-formed and its key claims are
internally consistent. Also verifies the v17b promotion is properly recorded.

Tests are run against frozen result files (no recomputation).
"""
import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
V18_RESULT = ROOT / "results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json"


class TestV18ResultIntegrity(unittest.TestCase):
    """Verify v18 result file is structurally sound and claims are consistent."""

    @classmethod
    def setUpClass(cls):
        cls.result = None
        if V18_RESULT.exists():
            with open(V18_RESULT) as f:
                cls.result = json.load(f)

    def test_result_file_exists(self):
        self.assertTrue(V18_RESULT.exists(), f"Missing v18 result file: {V18_RESULT}")

    def test_run_id_present(self):
        self.assertIsNotNone(self.result)
        self.assertTrue(self.result["run_id"].startswith("eval_v18_coarse_hierarchy"))

    def test_hypothesis_frozen(self):
        self.assertIsNotNone(self.result)
        self.assertIn("frozen_hypothesis", self.result)
        self.assertIn("frozen_success_rules", self.result)
        self.assertIn("rule_a_coarse_hierarchy", self.result["frozen_success_rules"])
        self.assertIn("rule_b_multi_seed", self.result["frozen_success_rules"])

    def test_part_a_present(self):
        self.assertIsNotNone(self.result)
        self.assertIn("part_a_coarse_hierarchy", self.result)
        self.assertIn("success_a", self.result["part_a_coarse_hierarchy"])

    def test_part_b_present(self):
        self.assertIsNotNone(self.result)
        self.assertIn("part_b_multi_seed_verification", self.result)
        self.assertIn("success_b", self.result["part_b_multi_seed_verification"])

    def test_part_c_scorecard_present(self):
        self.assertIsNotNone(self.result)
        self.assertIn("part_c_scorecard", self.result)
        reps = self.result["part_c_scorecard"]["representations"]
        # Should have all 6 representations
        self.assertEqual(len(reps), 6)

    def test_multi_seed_stability(self):
        """Multi-seed verification should show std < 0.05 for both reps."""
        if not self.result:
            self.skipTest("no v18 result")
        stability = self.result["part_b_multi_seed_verification"]["stability"]
        for rep, metrics in stability.items():
            self.assertLess(metrics["hierarchy_ratio_std"], 0.05,
                            f"{rep} hierarchy std not below 0.05")
            self.assertGreater(metrics["hierarchy_ratio_mean"], 1.10,
                            f"{rep} hierarchy mean not above 1.10")
            self.assertEqual(metrics["n_seeds"], 4)

    def test_seed42_reproduces_v17(self):
        """Seed 42 should match the original v17 finding (hierarchy ratio ~1.20)."""
        if not self.result:
            self.skipTest("no v18 result")
        seed_42 = self.result["part_b_multi_seed_verification"]["seed_results"]["42"]
        cp = seed_42["center_projected_64dim"]
        self.assertAlmostEqual(cp["ratios"]["hierarchy"], 1.2018, delta=0.01)

    def test_branch_level_negative_result(self):
        """Branch-level purity should be below 0.70 (genuine failure captured)."""
        if not self.result:
            self.skipTest("no v18 result")
        part_a = self.result["part_a_coarse_hierarchy"]
        self.assertLess(part_a["branch_purity_center_projected"], 0.70)
        self.assertFalse(part_a["success_a"])

    def test_all_six_reps_covered(self):
        """All 6 representations should have branch-level results."""
        if not self.result:
            self.skipTest("no v18 result")
        part_a = self.result["part_a_coarse_hierarchy"]["results"]
        expected_reps = [
            "center_projected_64dim", "cited_outcome_hybrid_0.5",
            "linear_citation_concat", "linear_hybrid05_concat",
            "linear_citation_w3070", "linear_citation_ridge",
        ]
        for rep in expected_reps:
            self.assertIn(rep, part_a)
            self.assertIn("branch_level", part_a[rep])


class TestV17bPromotionRecorded(unittest.TestCase):
    """Verify the v17b EXPLORATORY -> REPRODUCED promotion is recorded."""

    def test_v17b_tier_in_state(self):
        state_path = ROOT / "state/evaluation.json"
        self.assertTrue(state_path.exists())
        with open(state_path) as f:
            state = json.load(f)
        v17b = state.get("v17b_label_normalization_all_reps_findings", {})
        self.assertEqual(v17b.get("evidence_tier"), "REPRODUCED")
        self.assertTrue(v17b.get("multi_seed_verified", False))
        self.assertGreater(len(v17b.get("multi_seed_details", "")), 20)

    def test_v17_tier_in_state(self):
        state_path = ROOT / "state/evaluation.json"
        with open(state_path) as f:
            state = json.load(f)
        v17 = state.get("v17_label_normalization_findings", {})
        self.assertEqual(v17.get("evidence_tier"), "REPRODUCED")
        self.assertTrue(v17.get("multi_seed_verified", False))


if __name__ == "__main__":
    unittest.main()
