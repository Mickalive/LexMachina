"""
Test for scale dependency finding: hierarchical Leiden works at 12k but flat zoom fails.
This validates the core finding from factory direction v28.
"""
import json
import pytest
import numpy as np
from pathlib import Path


class TestScaleDependencyFinding:
    """Validate the scale dependency hypothesis at 12k scale."""

    @classmethod
    @pytest.fixture(scope="class")
    def experiment_results(cls):
        path = Path("results/fractal_map/scale_dependency_12k/experiment_results.json")
        assert path.exists(), f"Experiment results not found at {path}"
        with open(path) as f:
            return json.load(f)

    @classmethod
    @pytest.fixture(scope="class")
    def report(cls):
        path = Path("reports/fractal_map/FRACTAL_MAP_SCALE_DEPENDENCY_ANALYSIS_v28.md")
        assert path.exists(), f"Report not found at {path}"
        return path.read_text()

    def test_hierarchical_leiden_improvement_rate_meets_threshold(self, experiment_results):
        """Hierarchical Leiden should achieve improvement_rate >= 0.75 at 12k."""
        hl = experiment_results["hierarchical_leiden_results"]
        assert hl["improvement_rate"] >= 0.75, \
            f"Hierarchical improvement_rate={hl['improvement_rate']:.3f} < 0.75"
        # Should match factory direction reported 0.80
        assert abs(hl["improvement_rate"] - 0.80) < 0.05, \
            f"Should match factory direction 0.80, got {hl['improvement_rate']:.3f}"

    def test_flat_zoom_collapses_at_intermediate_resolutions(self, experiment_results):
        """Flat zoom should show collapse (improvement_rate < 0.15) at intermediate resolutions."""
        flat = experiment_results["flat_leiden_original_space"]["zoom_monotonicity"]
        # Find the 1.5->2.0 transition
        collapse_transition = next(t for t in flat if t["transition"] == "1.5_to_2.0")
        assert collapse_transition["improvement_rate"] < 0.15, \
            f"Flat zoom collapse not detected: improvement_rate={collapse_transition['improvement_rate']:.3f} >= 0.15"

    def test_umap_worsens_flat_zoom(self, experiment_results):
        """UMAP should not improve flat zoom monotonicity."""
        flat_orig = experiment_results["flat_leiden_original_space"]["zoom_monotonicity"]
        flat_umap = experiment_results["flat_leiden_umap_space"]["zoom_monotonicity"]
        
        # Compare at 1.5->2.0 transition
        orig_collapse = next(t for t in flat_orig if t["transition"] == "1.5_to_2.0")
        umap_collapse = next(t for t in flat_umap if t["transition"] == "1.5_to_2.0")
        
        # UMAP collapse should be worse (lower improvement rate)
        assert umap_collapse["improvement_rate"] <= orig_collapse["improvement_rate"], \
            f"UMAP improved flat zoom unexpectedly: UMAP={umap_collapse['improvement_rate']:.3f} > original={orig_collapse['improvement_rate']:.3f}"

    def test_citation_role_zq_exceeds_baseline(self, experiment_results):
        """Citation-role modes should have ZQ > baseline (outcome_hybrid_0.5=0.2798)."""
        cr = experiment_results["citation_role_1k_results"]
        baseline_zq = cr["outcome_hybrid_0.5"]["ZQ"]
        
        for mode in ["citing_alpha0.3", "following_alpha0.3", "criticizing_alpha0.3"]:
            zq = cr[mode]["ZQ"]
            assert zq > baseline_zq, \
                f"{mode} ZQ={zq:.4f} not > baseline {baseline_zq:.4f}"

    def test_tfidf_174k_modes_fail_zoom_quality(self, experiment_results):
        """TF-IDF 174k modes should all fail zoom quality rule."""
        tfidf = experiment_results["tfidf_174k_results"]
        assert tfidf["modes_passed_zoom_quality"] == 0, \
            f"Expected 0 modes to pass, got {tfidf['modes_passed_zoom_quality']}"
        assert tfidf["modes_tested"] == 4, \
            f"Expected 4 modes tested, got {tfidf['modes_tested']}"

    def test_nesting_metric_defect_enforced(self, experiment_results):
        """NESTING_METRIC_DEFECT_v1 should be enforced."""
        nm = experiment_results["nesting_metric_defect_v1"]
        assert nm["enforced"] is True
        assert "prohibited_claims" in nm
        assert "allowed_claims" in nm
        assert "1000-scale" in nm["allowed_claims"]

    def test_scale_dependency_confirmed(self, experiment_results):
        """Overall scale dependency conclusion should be confirmed."""
        conclusion = experiment_results["conclusion"]
        assert conclusion["scale_dependency_confirmed"] is True
        assert conclusion["hierarchical_works_at_12k"] is True
        assert conclusion["flat_zoom_fails_at_sub_62k"] is True
        assert conclusion["representation_quality_critical"] is True

    def test_report_contains_key_findings(self, report):
        """Report should document all key findings."""
        assert "0.787" in report, "Report should mention hierarchical improvement_rate=0.787"
        assert "0.094" in report, "Report should mention flat zoom collapse at 0.094"
        assert "0.042" in report, "Report should mention UMAP collapse at 0.042"
        assert "0.5401" in report, "Report should mention citing_alpha0.3 ZQ=0.5401"
        assert "0.5280" in report, "Report should mention following_alpha0.3 ZQ=0.5280"
        assert "0.4864" in report, "Report should mention criticizing_alpha0.3 ZQ=0.4864"
        assert "NESTING_METRIC_DEFECT_v1" in report, "Report should mention nesting metric defect"
        assert "scale dependency" in report.lower(), "Report should discuss scale dependency"


class TestHierarchicalLeidenConfiguration:
    """Test that hierarchical Leiden configuration sweep finds optimal params."""

    @classmethod
    @pytest.fixture(scope="class")
    def experiment_results(cls):
        path = Path("results/fractal_map/scale_dependency_12k/experiment_results.json")
        with open(path) as f:
            return json.load(f)

    def test_sweep_finds_best_config(self, experiment_results):
        """Parameter sweep should identify best configuration."""
        sweep = experiment_results["hierarchical_leiden_sweep"]
        assert "best_config" in sweep
        best = sweep["best_config"]
        assert best["improvement_rate"] >= 0.90, \
            f"Best config should have improvement_rate >= 0.90, got {best['improvement_rate']:.3f}"

    def test_factory_direction_config_performs_well(self, experiment_results):
        """Factory direction config (coarse=0.25, fine=3.0) should perform well."""
        sweep = experiment_results["hierarchical_leiden_sweep"]
        fd_config = sweep["factory_direction_config"]
        assert fd_config["improvement_rate"] >= 0.75, \
            f"Factory direction config improvement_rate={fd_config['improvement_rate']:.3f} < 0.75"

    def test_all_configs_have_positive_improvement(self, experiment_results):
        """All tested configs should show positive improvement rate."""
        sweep = experiment_results["hierarchical_leiden_sweep"]
        for config in sweep["all_configs"]:
            assert config["improvement_rate"] > 0.5, \
                f"Config coarse={config['coarse_res']}, fine={config['fine_res']} has low improvement_rate={config['improvement_rate']:.3f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])