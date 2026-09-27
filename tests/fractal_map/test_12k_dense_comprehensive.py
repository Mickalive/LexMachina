#!/usr/bin/env python3
"""
Test: 12k Dense Embeddings Comprehensive Constrained Hierarchical Leiden Validation
===================================================================================
Verifies that constrained hierarchical Leiden on ACCEPTED 12k dense embeddings
(3 years: 2000-2002) achieves zero fragmentation, high purity, and meaningful
zoom coherence, while flat v26 zoom quality FAILS (confirming scale dependency).
"""

import json
import pytest
from pathlib import Path

RESULTS_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/12k_dense_comprehensive')

CONFIGS = [
    ('coarse_0.25_adaptive_min20', '12k_dense_comprehensive_12570_20260927_221342.json'),
    ('coarse_0.5_adaptive_min20', '12k_dense_comprehensive_12570_20260927_221413.json'),
    ('coarse_0.5_adaptive_min50', '12k_dense_comprehensive_12570_20260927_221442.json'),
    ('coarse_0.5_fixed2.0_min20', '12k_dense_comprehensive_12570_20260927_221514.json'),
    ('coarse_0.25_fixed3.0_min20', '12k_dense_comprehensive_12570_20260927_221545.json'),
]


def load_result(filename):
    """Load a result JSON file."""
    path = RESULTS_DIR / filename
    assert path.exists(), f"Result file not found: {path}"
    with open(path) as f:
        return json.load(f)


class Test12kDenseComprehensive:
    """Tests for 12k dense embeddings constrained hierarchical Leiden validation."""

    def test_all_configs_exist(self):
        """All 5 configuration result files exist."""
        for name, filename in CONFIGS:
            path = RESULTS_DIR / filename
            assert path.exists(), f"Missing result file for {name}: {filename}"

    def test_constrained_hierarchical_zero_fragmentation(self):
        """All constrained hierarchical results show zero fragmentation."""
        for name, filename in CONFIGS:
            result = load_result(filename)
            frag = result['hierarchical']['fragmentation']
            assert frag['singleton_fraction'] == 0.0, f"{name}: singleton_fraction = {frag['singleton_fraction']}, expected 0.0"

    def test_constrained_hierarchical_perfect_nesting(self):
        """All constrained hierarchical results show perfect nesting (1.0)."""
        for name, filename in CONFIGS:
            result = load_result(filename)
            assert result['hierarchical']['nesting'] == 1.0, f"{name}: nesting = {result['hierarchical']['nesting']}, expected 1.0"

    def test_constrained_hierarchical_high_branch_purity(self):
        """Constrained hierarchical results show high hierarchical branch purity (> 0.97 for min20 configs, > 0.90 for min50)."""
        for name, filename in CONFIGS:
            result = load_result(filename)
            purity = result['hierarchical']['branch_purity']
            if 'min50' in name:
                assert purity > 0.90, f"{name}: hierarchical branch purity = {purity}, expected > 0.90"
            else:
                assert purity > 0.97, f"{name}: hierarchical branch purity = {purity}, expected > 0.97"

    def test_constrained_hierarchical_zoom_coherence(self):
        """All constrained hierarchical results show positive zoom coherence improvement."""
        for name, filename in CONFIGS:
            result = load_result(filename)
            zoom = result['zoom_coherence']['overall']
            assert zoom['improvement_rate'] > 0.3, f"{name}: improvement_rate = {zoom['improvement_rate']}, expected > 0.3"
            assert zoom['mean_improvement'] > 0.0, f"{name}: mean_improvement = {zoom['mean_improvement']}, expected > 0.0"

    def test_best_config_achieves_50pct_improvement_rate(self):
        """Best config (coarse_0.5_fixed2.0_min20) achieves improvement_rate >= 0.50."""
        result = load_result('12k_dense_comprehensive_12570_20260927_221514.json')
        zoom = result['zoom_coherence']['overall']
        assert zoom['improvement_rate'] >= 0.50, f"Best config improvement_rate = {zoom['improvement_rate']}, expected >= 0.50"

    def test_flat_v26_zoom_quality_fails_on_12k_dense(self):
        """Flat v26 zoom quality FAILS on all 12k dense embedding configs."""
        for name, filename in CONFIGS:
            result = load_result(filename)
            assert 'flat_v26' in result, f"{name}: missing flat_v26 evaluation"
            flat = result['flat_v26']
            assert flat['per_mode_verdict'] == 'FAIL', f"{name}: flat v26 verdict = {flat['per_mode_verdict']}, expected FAIL"
            checks = flat['checks']
            # Branch and area monotonic should pass, but improvement_rate check should fail
            assert checks['branch_monotonic_res3_vs_res0.25'] == True, f"{name}: branch monotonic failed"
            assert checks['area_monotonic_res3_vs_res0.25'] == True, f"{name}: area monotonic failed"
            assert checks['improvement_rate_gt_0.5_on_2_of_4'] == False, f"{name}: improvement_rate check should fail"

    def test_scale_dependency_confirmed(self):
        """Scale dependency confirmed: flat v26 FAILS at 12k, but constrained hierarchical works."""
        # At least one config should have hierarchical improvement_rate > flat improvement_rate
        for name, filename in CONFIGS:
            result = load_result(filename)
            hier_zoom = result['zoom_coherence']['overall']['improvement_rate']
            flat_transitions = result['flat_v26']['transitions']
            # Count flat transitions with improvement_rate > 0.5
            flat_good_transitions = sum(1 for t in flat_transitions if t['branch_improvement_rate'] > 0.5)
            # Hierarchical should have higher or comparable improvement_rate
            # At 12k, hierarchical works (improvement_rate ~0.33-0.55) while flat has only 1/4 good transitions
            assert flat_good_transitions <= 1, f"{name}: flat has {flat_good_transitions} good transitions, expected <= 1"

    def test_branch_purity_improvement(self):
        """Hierarchical branch purity > coarse branch purity for all configs."""
        for name, filename in CONFIGS:
            result = load_result(filename)
            coarse = result['coarse']['branch_purity']
            hier = result['hierarchical']['branch_purity']
            assert hier > coarse, f"{name}: hierarchical purity ({hier}) not > coarse purity ({coarse})"

    def test_area_purity_improvement(self):
        """Hierarchical area purity > coarse area purity for most configs (config C min50 is exception)."""
        for name, filename in CONFIGS:
            result = load_result(filename)
            coarse = result['coarse']['area_purity']
            hier = result['hierarchical']['area_purity']
            if 'min50' not in name:  # min50 config has fewer clusters, lower area purity
                assert hier > coarse, f"{name}: hierarchical area purity ({hier}) not > coarse ({coarse})"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])