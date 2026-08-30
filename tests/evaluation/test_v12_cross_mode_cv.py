#!/usr/bin/env python3
"""
Test: v12 cross-mode combination 5-fold cross-validation on canonical frozen harness v3

Verifies that:
1. v12 cross-mode CV results file exists and is well-formed
2. v12 combination hypothesis REPLICATES (mean JP improvement > 0)
3. All combinations pass both adversarial gates across all folds
4. Best combination (linear_citation_ridge) achieves JP > center_projected_64dim baseline
5. center_projected_64dim performs normally on canonical corpus (JP > 0.5)
6. Config hash is consistent with canonical frozen harness v3
"""

import json
import pytest
from pathlib import Path

RESULTS_PATH = Path(__file__).parent.parent.parent / "results/evaluation/v12_cross_mode_cv/v12_cross_mode_cv_latest.json"
AUDIT_GATE_PATH = Path(__file__).parent.parent.parent / "results/audit/evaluation/CYCLE_33337788256_r1_GATE.json"
REPORT_PATH = Path(__file__).parent.parent.parent / "results/evaluation/v12_cross_mode_cv/REPORT.md"


def load_results():
    with open(RESULTS_PATH) as f:
        return json.load(f)


def load_audit_gate():
    with open(AUDIT_GATE_PATH) as f:
        return json.load(f)


class TestV12CrossModeCV:
    """Test v12 cross-mode combination on canonical frozen harness v3."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.results = load_results()
        self.gate = load_audit_gate()

    def test_results_file_exists(self):
        """v12 cross-mode CV results file exists."""
        assert RESULTS_PATH.exists(), f"Results not found at {RESULTS_PATH}"

    def test_audit_gate_passes(self):
        """Audit gate for v12 repair round 1 is PASS."""
        assert self.gate["gate"] == "PASS", f"Gate status: {self.gate['gate']}"
        assert self.gate["safe_to_integrate"] is True

    def test_config_hash_consistent(self):
        """Config hash matches canonical frozen harness v3."""
        assert self.results["config_hash"] == "4323f833fa72366a", \
            f"Config hash mismatch: {self.results['config_hash']}"

    def test_corpus_is_canonical_1200(self):
        """Results are from the canonical 1200-decision corpus."""
        assert "1200" in self.results["corpus"], \
            f"Corpus is not canonical 1200: {self.results['corpus']}"

    def test_v12_hypothesis_replicates(self):
        """v12 combination hypothesis REPLICATES: mean JP improvement > 0."""
        fold_results = self.results["fold_results"]
        improvements = []
        for fold in fold_results:
            best_baseline_jp = max(
                r["jurist_score"]
                for name, r in fold["results"].items()
                if name in ["center_projected_64dim", "citation_tfidf",
                            "cited_outcome_hybrid_0.5", "cited_outcome_hybrid_0.7"]
            )
            best_combination_jp = max(
                r["jurist_score"]
                for name, r in fold["results"].items()
                if name.startswith("linear_")
            )
            improvements.append(best_combination_jp - best_baseline_jp)
        mean_improvement = sum(improvements) / len(improvements)
        assert mean_improvement > 0, \
            f"v12 hypothesis FALSIFIED: mean ΔJP={mean_improvement:+.4f} (should be > 0)"

    def test_all_folds_pass_adversarial_gates(self):
        """All combinations pass both adversarial gates across all folds."""
        for fold in self.results["fold_results"]:
            for name, rep in fold["results"].items():
                if rep.get("both_pass") is False:
                    pytest.fail(
                        f"Fold {fold['fold']}, {name}: both_pass=False "
                        f"(langdom={rep.get('langdom_score', 'N/A')}, "
                        f"jurist={rep.get('jurist_score', 'N/A')})"
                    )

    def test_best_combination_beats_baseline(self):
        """Best combination (linear_citation_ridge) beats center_projected_64dim on JP."""
        fold_results = self.results["fold_results"]
        ridge_jps = []
        baseline_jps = []
        for fold in fold_results:
            if "linear_citation_ridge" in fold["results"]:
                ridge_jps.append(fold["results"]["linear_citation_ridge"]["jurist_score"])
            if "center_projected_64dim" in fold["results"]:
                baseline_jps.append(fold["results"]["center_projected_64dim"]["jurist_score"])
        if ridge_jps and baseline_jps:
            mean_ridge = sum(ridge_jps) / len(ridge_jps)
            mean_baseline = sum(baseline_jps) / len(baseline_jps)
            assert mean_ridge > mean_baseline, \
                f"linear_citation_ridge ({mean_ridge:.4f}) does not beat baseline ({mean_baseline:.4f})"

    def test_center_projected_normal_on_canonical(self):
        """center_projected_64dim performs normally on canonical corpus (JP > 0.5)."""
        fold_results = self.results["fold_results"]
        cp_jps = []
        for fold in fold_results:
            if "center_projected_64dim" in fold["results"]:
                cp_jps.append(fold["results"]["center_projected_64dim"]["jurist_score"])
        assert len(cp_jps) > 0, "No center_projected_64dim results found"
        mean_cp = sum(cp_jps) / len(cp_jps)
        assert mean_cp > 0.5, \
            f"center_projected_64dim JP={mean_cp:.4f} < 0.5 on canonical corpus (should be > 0.5)"

    def test_five_folds_present(self):
        """Results contain exactly 5 folds."""
        assert len(self.results["fold_results"]) == 5, \
            f"Expected 5 folds, got {len(self.results['fold_results'])}"

    def test_repair_round_documented(self):
        """Repair round 1 is documented in audit gate."""
        assert self.gate["repair_round"] == 1, \
            f"Expected repair_round=1, got {self.gate['repair_round']}"
