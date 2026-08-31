#!/usr/bin/env python3
"""
Tests for v14 independent rerun verification (evaluation cycle 33354034841).

These tests verify that the v14 independent rerun from the legal-distance lane
CONFIRMS the v13 linear_citation_concat finding, and that this confirmation is
consistent with the canonical evaluation harness v3 results.

Frozen: config_hash=4323f833fa72366a, seed=42, corpus=1200 BGer decisions
"""

import json
import os
import pytest
from pathlib import Path

# === PATHS ===
V14_PATH = "/tmp/lex_accepted/legal-distance/legal_distance/results/v14/independent_rerun/independent_rerun_validation.json"
V13_PATH = "/tmp/lex_accepted/legal-distance/legal_distance/results/v13/cross_mode_kfold/cross_mode_kfold_validation.json"
V12_CV_PATH = "results/evaluation/v12_cross_mode_cv/v12_cross_mode_cv_eval_v12_cv_1788128447.json"
VERIFICATION_DIR = "results/evaluation/v14_verification"

# === FROZEN SUCCESS RULE ===
SUCCESS_RULE = {"min_mean_jp_delta": 0.02, "max_jp_delta_std": 0.03}


def _load_json(path):
    with open(path) as f:
        return json.load(f)


class TestV14IndependentRerunVerification:
    """Tests for v14 independent rerun verification."""

    def test_v14_results_file_exists(self):
        """v14 results file exists and is parseable."""
        assert os.path.exists(V14_PATH), f"v14 results not found: {V14_PATH}"
        v14 = _load_json(V14_PATH)
        assert v14["run_id"] == "v14_independent_rerun_20260830"
        assert v14["independent_seed"] == 137

    def test_v13_results_file_exists(self):
        """v13 results file exists for comparison."""
        assert os.path.exists(V13_PATH), f"v13 results not found: {V13_PATH}"
        v13 = _load_json(V13_PATH)
        assert v13["run_id"] == "v13_cross_mode_kfold_20260830"

    def test_v14_linear_citation_concat_passes_success_rule(self):
        """v14 linear_citation_concat passes the frozen success rule."""
        v14 = _load_json(V14_PATH)
        best = v14["best_stable_combination"]
        assert best["name"] == "linear_citation_concat"
        assert best["mean_delta_jp"] >= SUCCESS_RULE["min_mean_jp_delta"], \
            f"mean_delta {best['mean_delta_jp']:.4f} < {SUCCESS_RULE['min_mean_jp_delta']}"
        assert best["paired_delta_std"] <= SUCCESS_RULE["max_jp_delta_std"], \
            f"paired_std {best['paired_delta_std']:.4f} > {SUCCESS_RULE['max_jp_delta_std']}"

    def test_v14_reproduction_verdict_confirmed(self):
        """v14 reproduction verdict is CONFIRMED."""
        v14 = _load_json(V14_PATH)
        assert v14["reproduction_verdict"] == "CONFIRMED"

    def test_v14_same_best_as_v13(self):
        """v14 and v13 identify the same best combination."""
        v13 = _load_json(V13_PATH)
        v14 = _load_json(V14_PATH)
        assert v13["best_stable_combination"]["name"] == v14["best_stable_combination"]["name"]

    def test_v13_also_passes_success_rule(self):
        """v13 also passes the frozen success rule (both must pass)."""
        v13 = _load_json(V13_PATH)
        best = v13["best_stable_combination"]
        assert best["mean_delta_jp"] >= SUCCESS_RULE["min_mean_jp_delta"]
        assert best["paired_delta_std"] <= SUCCESS_RULE["max_jp_delta_std"]

    def test_v14_consistent_with_canonical_v12(self):
        """v14 finding is consistent with canonical v12 CV results."""
        v12 = _load_json(V12_CV_PATH)
        v14 = _load_json(V14_PATH)
        
        # Canonical v12: linear_citation_concat beats baseline
        v12_lcc_jp = v12["aggregated"]["linear_citation_concat"]["jurist_pref_mean"]
        v12_baseline_jp = v12["aggregated"]["center_projected_64dim"]["jurist_pref_mean"]
        v12_beats = v12_lcc_jp > v12_baseline_jp
        
        # v14: linear_citation_concat beats baseline
        v14_lcc_jp = sum(v14["fold_results"]["linear_citation_concat"]["fold_jps"]) / 5
        v14_baseline_jp = sum(v14["fold_results"]["baseline_linear_oos_refit"]["fold_jps"]) / 5
        v14_beats = v14_lcc_jp > v14_baseline_jp
        
        # Both must show same direction
        assert v12_beats and v14_beats, \
            f"Directional inconsistency: v12={v12_beats}, v14={v14_beats}"

    def test_v12_canonical_config_hash(self):
        """Canonical v12 uses the frozen evaluation harness config hash."""
        v12 = _load_json(V12_CV_PATH)
        assert v12["config_hash"] == "4323f833fa72366a", \
            f"Unexpected config_hash: {v12['config_hash']}"

    def test_v14_no_benchmark_gaming(self):
        """No suspicious baseline values in v14 results."""
        v14 = _load_json(V14_PATH)
        for name, folds_data in v14["fold_results"].items():
            max_jp = max(folds_data["fold_jps"])
            assert max_jp <= 0.99, f"Suspicious JP {max_jp:.4f} in {name}"

    def test_v14_verification_output_exists(self):
        """Verification output was written."""
        assert os.path.isdir(VERIFICATION_DIR), f"Output dir missing: {VERIFICATION_DIR}"
        files = list(Path(VERIFICATION_DIR).glob("v14_verification_*.json"))
        assert len(files) >= 1, "No verification output files found"

    def test_v14_tradeoff_status_partially_broken(self):
        """Tradeoff status is PARTIALLY_BROKEN (expected from v14)."""
        v14 = _load_json(V14_PATH)
        assert v14["tradeoff_status"] == "PARTIALLY_BROKEN"

    def test_v14_all_combinations_in_fold_results(self):
        """All expected combination names are present in v14 fold_results."""
        v14 = _load_json(V14_PATH)
        expected = [
            "baseline_linear_oos_refit", "baseline_citation_tfidf",
            "baseline_hybrid05", "baseline_hybrid07",
            "linear_citation_concat", "linear_hybrid05_concat",
            "linear_citation_ridge", "linear_citation_pca128",
        ]
        for name in expected:
            assert name in v14["fold_results"], f"Missing combination: {name}"
