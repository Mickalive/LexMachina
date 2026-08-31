"""
Tests for v16 Full Benchmark Suite results.
Verifies that v15 combinations pass the formal benchmark suite.
"""
import json
import pytest
from pathlib import Path

RESULTS_PATH = Path("results/evaluation/v16_full_benchmark_suite/v16_full_benchmark_latest.json")


class TestV16FullBenchmarkSuite:
    """Tests for v16 full benchmark suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        if RESULTS_PATH.exists():
            with open(RESULTS_PATH) as f:
                self.results = json.load(f)
        else:
            self.results = None

    def test_results_file_exists(self):
        assert RESULTS_PATH.exists(), f"Results file not found: {RESULTS_PATH}"

    def test_results_parseable(self):
        assert self.results is not None
        assert 'results' in self.results
        assert 'config_hash' in self.results

    def test_config_hash_consistent(self):
        assert self.results['config_hash'] == "4323f833fa72366a"

    def test_all_representations_present(self):
        expected = [
            'center_projected_64dim', 'cited_outcome_hybrid_0.5',
            'linear_citation_concat', 'linear_hybrid05_concat',
            'linear_citation_w3070', 'linear_citation_ridge'
        ]
        for name in expected:
            assert name in self.results['results'], f"Missing representation: {name}"

    def test_all_representations_have_benchmarks(self):
        for name, data in self.results['results'].items():
            assert 'benchmarks' in data, f"{name} missing benchmarks"
            assert len(data['benchmarks']) >= 10, f"{name} has only {len(data['benchmarks'])} benchmarks"

    def test_baseline_passes_7_of_12(self):
        baseline = self.results['results']['center_projected_64dim']
        assert baseline['n_passed'] >= 7, f"Baseline only passed {baseline['n_passed']}/12"

    def test_combinations_match_baseline(self):
        baseline = self.results['results']['center_projected_64dim']
        for name in ['linear_citation_concat', 'linear_hybrid05_concat', 'linear_citation_ridge']:
            combo = self.results['results'][name]
            assert combo['n_passed'] >= baseline['n_passed'] - 1, \
                f"{name} ({combo['n_passed']}) below baseline ({baseline['n_passed']})"

    def test_universal_passes(self):
        """All representations pass branch_knn, adversarial_falsification, multilingual, collapse, temporal."""
        universal = ['branch_knn', 'adversarial_falsification', 'multilingual_invariance',
                     'cross_language_pairs', 'collapse_check', 'temporal_stability']
        for name, data in self.results['results'].items():
            for bm in data['benchmarks']:
                if bm.get('benchmark_id') in universal:
                    assert bm['status'] == 'PASS', \
                        f"{name} FAILS {bm['benchmark_id']}: {bm.get('metrics', {})}"

    def test_all_fail_boilerplate(self):
        """All representations fail boilerplate resistance (known systemic limitation)."""
        for name, data in self.results['results'].items():
            for bm in data['benchmarks']:
                if bm.get('benchmark_id') == 'boilerplate_resistance_real_corpus':
                    assert bm['status'] == 'FAIL', \
                        f"{name} unexpectedly PASSSED boilerplate resistance"

    def test_citation_heritage_skipped(self):
        """citation_heritage should be SKIPPED (no internal citations in 1200 corpus)."""
        for name, data in self.results['results'].items():
            for bm in data['benchmarks']:
                if bm.get('benchmark_id') == 'citation_heritage':
                    assert bm['status'] == 'SKIP', \
                        f"{name} citation_heritage unexpected status: {bm['status']}"

    def test_hybrid_fails_tf_metadata(self):
        """cited_outcome_hybrid_0.5 should FAIL tf_metadata_human_indexing."""
        hybrid = self.results['results']['cited_outcome_hybrid_0.5']
        for bm in hybrid['benchmarks']:
            if bm.get('benchmark_id') == 'tf_metadata_human_indexing':
                assert bm['status'] == 'FAIL', \
                    f"hybrid_0.5 unexpectedly PASSSED tf_metadata"

    def test_linear_hybrid05_passes_tf_metadata(self):
        """linear_hybrid05_concat should PASS tf_metadata_human_indexing."""
        combo = self.results['results']['linear_hybrid05_concat']
        for bm in combo['benchmarks']:
            if bm.get('benchmark_id') == 'tf_metadata_human_indexing':
                assert bm['status'] == 'PASS', \
                    f"linear_hybrid05_concat FAILS tf_metadata: {bm.get('metrics', {})}"

    def test_no_dimensional_collapse(self):
        """All representations should pass collapse check."""
        for name, data in self.results['results'].items():
            for bm in data['benchmarks']:
                if bm.get('benchmark_id') == 'collapse_check':
                    assert bm['status'] == 'PASS', \
                        f"{name} DIMENSIONAL COLLAPSE: {bm.get('metrics', {})}"
