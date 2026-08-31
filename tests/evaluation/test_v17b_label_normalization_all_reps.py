"""
Tests for v17b: normalization improves hierarchy-family purity across ALL
representations (uniformity check). Confirms the v16 hierarchy-family FAIL was a
shared, representation-agnostic label artifact and does NOT distort the relative
product ranking.
"""
import json
import pytest
from pathlib import Path

RESULTS_PATH = Path("results/evaluation/v17b_label_normalization_all_reps/"
                    "v17b_label_normalization_all_reps_latest.json")

REPS = [
    'center_projected_64dim', 'cited_outcome_hybrid_0.5',
    'linear_citation_concat', 'linear_hybrid05_concat',
    'linear_citation_w3070', 'linear_citation_ridge',
]


class TestV17bUniformNormalizationImprovement:
    @pytest.fixture(autouse=True)
    def _load(self):
        assert RESULTS_PATH.exists(), f"Missing {RESULTS_PATH}"
        with open(RESULTS_PATH) as f:
            self.results = json.load(f)

    def test_all_reps_present(self):
        for name in REPS:
            assert name in self.results['per_representation'], f"missing {name}"

    def test_raw_reproduces_v16(self):
        """linear_hybrid05_concat raw hierarchy best_purity ~ v16 0.3084."""
        d = self.results['per_representation']['linear_hybrid05_concat']
        assert d['raw']['hierarchy_coherence']['best_purity'] == pytest.approx(0.3084, abs=1e-3)

    def test_every_rep_improves_or_matches(self):
        assert self.results['uniform_improvement_or_matching'] is True
        assert self.results['representations_worsened_by_gt10pct'] == {}

    def test_each_rep_hierarchy_improves(self):
        for name in REPS:
            r = self.results['per_representation'][name]['purity_ratios_norm_over_raw']
            assert r['hierarchy'] >= 1.0, f"{name} hierarchy did not improve"

    def test_product_default_hybrid_improves_materially(self):
        """linear_hybrid05_concat (product default combo) should improve most or near-most."""
        d = self.results['per_representation']['linear_hybrid05_concat']
        r = d['purity_ratios_norm_over_raw']
        # we observed hierarchy ratio ~1.24, the strongest
        assert r['hierarchy'] >= 1.20, f"linear_hybrid05_concat hier ratio {r['hierarchy']} < 1.20"

    def test_num_areas_uniform(self):
        areas = {self.results['per_representation'][n]['norm_num_areas'] for n in REPS}
        assert areas == {54}, f"expected uniform 54 normalized areas, got {areas}"
