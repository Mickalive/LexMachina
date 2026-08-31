#!/usr/bin/env python3
"""Tests for v15 combination vs hybrid evaluation."""

import json
import os
import pytest
from pathlib import Path

RESULTS_DIR = Path("results/evaluation/v15_combination_vs_hybrid")


class TestV15FullSlice:
    """Test v15 full-slice head-to-head evaluation."""

    def test_results_file_exists(self):
        latest = RESULTS_DIR / "v15_combination_vs_hybrid_latest.json"
        assert latest.exists(), f"v15 results not found: {latest}"

    def test_results_parseable(self):
        latest = RESULTS_DIR / "v15_combination_vs_hybrid_latest.json"
        with open(latest) as f:
            data = json.load(f)
        assert data['frozen_before_observation'] is True
        assert data['config_hash'] == "4323f833fa72366a"

    def test_hybrid_reigns_supreme(self):
        """v15 full-slice: hybrid dominates all combinations."""
        latest = RESULTS_DIR / "v15_combination_vs_hybrid_latest.json"
        with open(latest) as f:
            data = json.load(f)
        assert data['verdict'] == "HYBRID_REMAINS_DOMINANT"
        assert len(data['combinations_beating_hybrid']) == 0

    def test_all_representations_pass_adversarial(self):
        """All representations should pass both adversarial gates on full slice."""
        latest = RESULTS_DIR / "v15_combination_vs_hybrid_latest.json"
        with open(latest) as f:
            data = json.load(f)
        for r in data['results']:
            assert r['both_pass'] is True, f"{r['name']} fails adversarial gates"

    def test_best_hybrid_is_hybrid05(self):
        """Best zero-shot hybrid should be cited_outcome_hybrid_0.5."""
        latest = RESULTS_DIR / "v15_combination_vs_hybrid_latest.json"
        with open(latest) as f:
            data = json.load(f)
        assert data['best_zero_shot_hybrid']['name'] == 'cited_outcome_hybrid_0.5'
        assert data['best_zero_shot_hybrid']['jurist_pref'] > 0.5


class TestV15BCrossValidation:
    """Test v15b 5-fold CV evaluation."""

    def test_cv_results_file_exists(self):
        latest = RESULTS_DIR / "v15b_cv_latest.json"
        assert latest.exists(), f"v15b CV results not found: {latest}"

    def test_cv_results_parseable(self):
        latest = RESULTS_DIR / "v15b_cv_latest.json"
        with open(latest) as f:
            data = json.load(f)
        assert data['frozen_before_observation'] is True
        assert data['n_folds'] == 5

    def test_cv_combinations_beat_hybrid(self):
        """In 5-fold CV, combinations should beat the zero-shot hybrid."""
        latest = RESULTS_DIR / "v15b_cv_latest.json"
        with open(latest) as f:
            data = json.load(f)
        assert data['verdict'] == "COMBINATION_BEATS_HYBRID"
        assert len(data['combinations_beating_hybrid']) > 0

    def test_cv_linear_hybrid05_is_best_stable(self):
        """linear_hybrid05_concat should be the best stable combination (lowest std)."""
        latest = RESULTS_DIR / "v15b_cv_latest.json"
        with open(latest) as f:
            data = json.load(f)
        agg = data['aggregated']
        # linear_hybrid05_concat should have std < 0.03
        assert agg['linear_hybrid05_concat']['jp_std'] < 0.03, \
            f"linear_hybrid05_concat std too high: {agg['linear_hybrid05_concat']['jp_std']}"
        # And should beat the hybrid by > 0.02
        hybrid_jp = agg['cited_outcome_hybrid_0.5']['jp_mean']
        combo_jp = agg['linear_hybrid05_concat']['jp_mean']
        assert combo_jp - hybrid_jp > 0.02, \
            f"linear_hybrid05_concat doesn't beat hybrid: {combo_jp:.4f} vs {hybrid_jp:.4f}"

    def test_cv_all_combinations_beat_hybrid(self):
        """All combinations should beat the hybrid in CV."""
        latest = RESULTS_DIR / "v15b_cv_latest.json"
        with open(latest) as f:
            data = json.load(f)
        agg = data['aggregated']
        hybrid_jp = agg['cited_outcome_hybrid_0.5']['jp_mean']
        for name in data['combinations_beating_hybrid']:
            assert agg[name]['jp_mean'] - hybrid_jp > 0.02, \
                f"{name} doesn't beat hybrid: {agg[name]['jp_mean']:.4f} vs {hybrid_jp:.4f}"

    def test_cv_center_projected_baseline(self):
        """center_projected_64dim should be around JP=0.80 in CV."""
        latest = RESULTS_DIR / "v15b_cv_latest.json"
        with open(latest) as f:
            data = json.load(f)
        cp_jp = data['aggregated']['center_projected_64dim']['jp_mean']
        assert 0.75 < cp_jp < 0.85, f"center_projected_64dim JP out of range: {cp_jp}"

    def test_cv_all_representations_pass_adversarial(self):
        """All representations should pass adversarial gates in CV."""
        latest = RESULTS_DIR / "v15b_cv_latest.json"
        with open(latest) as f:
            data = json.load(f)
        for name, agg in data['aggregated'].items():
            assert agg['adv_pass_rate'] == 1.0, f"{name} fails adversarial gates in some folds"
