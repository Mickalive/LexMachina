#!/usr/bin/env python3
"""
Test: v12 temporal holdout falsification experiment

Verifies that:
1. Temporal holdout results file exists and is well-formed
2. v12 combination hypothesis REPLICATES on temporal holdout (JP improvement > 0)
3. All combinations pass both adversarial gates on temporal test set
4. Best combination beats center_projected_64dim baseline on temporal test set
5. center_projected_64dim performs normally on temporal test set (JP > 0.5)
6. Temporal degradation is minimal (< 0.10)
7. Config hash is consistent with canonical frozen harness v3
"""

import json
import pytest
from pathlib import Path

RESULTS_PATH = Path(__file__).parent.parent.parent / "results/evaluation/v12_temporal_holdout/v12_temporal_holdout_latest.json"


def load_results():
    with open(RESULTS_PATH) as f:
        return json.load(f)


class TestV12TemporalHoldout:
    """Test v12 temporal holdout on canonical frozen harness v3."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.results = load_results()

    def test_results_file_exists(self):
        """Temporal holdout results file exists."""
        assert RESULTS_PATH.exists(), f"Results not found at {RESULTS_PATH}"

    def test_config_hash_consistent(self):
        """Config hash matches canonical frozen harness v3."""
        assert self.results["config_hash"] == "4323f833fa72366a", \
            f"Config hash mismatch: {self.results['config_hash']}"

    def test_v12_hypothesis_replicates(self):
        """v12 combination hypothesis REPLICATES on temporal holdout: JP improvement > 0."""
        claim = self.results["v12_claim_assessment"]
        assert claim["replicates"] is True, \
            f"v12 hypothesis FALSIFIED on temporal holdout: improvement={claim['temporal_improvement']:+.4f}"

    def test_all_combinations_pass_adversarial_gates(self):
        """All combinations pass both adversarial gates on temporal test set."""
        for name, rep in self.results["results"].items():
            assert rep["both_pass"] is True, \
                f"{name}: both_pass=False (langdom={rep['langdom_score']:.4f}, jurist={rep['jurist_score']:.4f})"

    def test_best_combination_beats_baseline(self):
        """Best combination beats center_projected_64dim on temporal test set."""
        claim = self.results["v12_claim_assessment"]
        assert claim["best_combo_jp"] > claim["best_baseline_jp"], \
            f"Best combo ({claim['best_combo_name']}: {claim['best_combo_jp']:.4f}) " \
            f"does not beat baseline ({claim['best_baseline_name']}: {claim['best_baseline_jp']:.4f})"

    def test_center_projected_normal_on_temporal(self):
        """center_projected_64dim performs normally on temporal test set (JP > 0.5)."""
        cp = self.results["results"]["center_projected_64dim"]
        assert cp["jurist_score"] > 0.5, \
            f"center_projected_64dim JP={cp['jurist_score']:.4f} < 0.5 on temporal test set"

    def test_temporal_degradation_minimal(self):
        """Temporal degradation is minimal (< 0.10)."""
        degradation = self.results["temporal_degradation"]["degradation"]
        assert degradation < 0.10, \
            f"Temporal degradation too large: {degradation:+.4f} (should be < 0.10)"

    def test_temporal_improvement_positive(self):
        """Temporal improvement over baseline is positive and meaningful."""
        claim = self.results["v12_claim_assessment"]
        assert claim["temporal_improvement"] > 0.01, \
            f"Temporal improvement too small: {claim['temporal_improvement']:+.4f} (should be > 0.01)"

    def test_split_is_temporal(self):
        """Split is temporal (train dates < test dates)."""
        split = self.results["split"]
        assert split["train_date_range"][1] <= split["test_date_range"][0], \
            f"Split is not temporal: train ends {split['train_date_range'][1]}, " \
            f"test starts {split['test_date_range'][0]}"

    def test_train_test_sizes_reasonable(self):
        """Train/test sizes are reasonable (80/20 split)."""
        split = self.results["split"]
        assert split["train_size"] == 960, f"Train size: {split['train_size']} (expected 960)"
        assert split["test_size"] == 240, f"Test size: {split['test_size']} (expected 240)"
