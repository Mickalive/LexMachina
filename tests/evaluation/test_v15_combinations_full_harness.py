#!/usr/bin/env python3
"""
Tests for v15 Combinations Full Adversarial Harness Evaluation
"""

import json
import pytest
from pathlib import Path

RESULTS_DIR = Path("results/evaluation/v15_combinations_full_harness")
LATEST_FILE = RESULTS_DIR / "v15_full_harness_latest.json"


class TestV15CombinationsFullHarness:
    """Test v15 combinations on full 5-benchmark adversarial harness."""

    def test_results_file_exists(self):
        assert LATEST_FILE.exists(), f"Results file not found: {LATEST_FILE}"

    def test_results_parseable(self):
        with open(LATEST_FILE) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_all_representations_present(self):
        with open(LATEST_FILE) as f:
            data = json.load(f)
        expected = [
            'center_projected_64dim',
            'cited_outcome_hybrid_0.5',
            'cited_outcome_hybrid_0.7',
            'linear_citation_concat',
            'linear_hybrid05_concat',
            'linear_citation_w3070',
            'linear_citation_ridge',
        ]
        for exp in expected:
            assert exp in data, f"Missing representation: {exp}"

    def test_all_representations_have_5_benchmarks(self):
        with open(LATEST_FILE) as f:
            data = json.load(f)
        for name, res in data.items():
            assert 'adversarial_language_dominance' in res
            assert 'jurist_pairwise_preference' in res
            assert 'jurivoc_hierarchy_alignment' in res
            assert 'scale_stability_frozen_pca' in res
            assert 'boilerplate_resistance' in res
            assert res['n_total'] == 5

    def test_hybrid_passes_4_of_5(self):
        """cited_outcome_hybrid_0.5 should pass 4/5 benchmarks (fail Jurivoc)."""
        with open(LATEST_FILE) as f:
            data = json.load(f)
        hybrid = data['cited_outcome_hybrid_0.5']
        assert hybrid['n_passed'] == 4
        assert hybrid['adversarial_language_dominance']['status'] == 'PASS'
        assert hybrid['jurist_pairwise_preference']['status'] == 'PASS'
        assert hybrid['jurivoc_hierarchy_alignment']['status'] == 'FAIL'
        assert hybrid['scale_stability_frozen_pca']['status'] == 'PASS'
        assert hybrid['boilerplate_resistance']['status'] == 'PASS'

    def test_combinations_pass_4_of_5_fail_boilerplate(self):
        """All combinations should pass 4/5, failing Boilerplate Resistance."""
        with open(LATEST_FILE) as f:
            data = json.load(f)
        combos = [
            'linear_citation_concat',
            'linear_hybrid05_concat',
            'linear_citation_w3070',
            'linear_citation_ridge',
        ]
        for cn in combos:
            res = data[cn]
            assert res['n_passed'] == 4, f"{cn}: expected 4/5 passed, got {res['n_passed']}"
            assert res['boilerplate_resistance']['status'] == 'FAIL', f"{cn}: expected Boilerplate FAIL"
            # All should pass the other 4
            assert res['adversarial_language_dominance']['status'] == 'PASS'
            assert res['jurist_pairwise_preference']['status'] == 'PASS'
            assert res['jurivoc_hierarchy_alignment']['status'] == 'PASS'
            assert res['scale_stability_frozen_pca']['status'] == 'PASS'

    def test_hybrid_beats_combos_on_2_gates(self):
        """On full-corpus evaluation, hybrid beats combinations on LangDom and JuristPref."""
        with open(LATEST_FILE) as f:
            data = json.load(f)
        hybrid = data['cited_outcome_hybrid_0.5']
        hybrid_ld = hybrid['adversarial_language_dominance']['mean_language_dominance']
        hybrid_jp = hybrid['jurist_pairwise_preference']['jurist_would_succeed_rate']
        
        combos = [
            'linear_citation_concat',
            'linear_hybrid05_concat',
            'linear_citation_w3070',
            'linear_citation_ridge',
        ]
        for cn in combos:
            res = data[cn]
            combo_ld = res['adversarial_language_dominance']['mean_language_dominance']
            combo_jp = res['jurist_pairwise_preference']['jurist_would_succeed_rate']
            # Hybrid should have LOWER langdom (better) and HIGHER jurist (better)
            assert combo_ld > hybrid_ld, f"{cn} LangDom {combo_ld:.4f} not > hybrid {hybrid_ld:.4f}"
            assert combo_jp < hybrid_jp, f"{cn} Jurist {combo_jp:.4f} not < hybrid {hybrid_jp:.4f}"

    def test_combinations_beat_hybrid_on_jurivoc(self):
        """Combinations should beat hybrid on Jurivoc alignment."""
        with open(LATEST_FILE) as f:
            data = json.load(f)
        hybrid_jv = data['cited_outcome_hybrid_0.5']['jurivoc_hierarchy_alignment']['avg_nmi']
        combos = [
            'linear_citation_concat',
            'linear_hybrid05_concat',
            'linear_citation_w3070',
            'linear_citation_ridge',
        ]
        for cn in combos:
            combo_jv = data[cn]['jurivoc_hierarchy_alignment']['avg_nmi']
            assert combo_jv > hybrid_jv, f"{cn} Jurivoc {combo_jv:.4f} not > hybrid {hybrid_jv:.4f}"

    def test_all_pass_scale_stability(self):
        """All representations should pass scale stability (1.0)."""
        with open(LATEST_FILE) as f:
            data = json.load(f)
        for name, res in data.items():
            sc = res['scale_stability_frozen_pca']['mean_cosine_similarity']
            assert sc == 1.0, f"{name} scale stability {sc} != 1.0"
            assert res['scale_stability_frozen_pca']['status'] == 'PASS'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])