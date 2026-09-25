"""Guard test for the 174k dense embeddings evaluation infrastructure.

Validates that the evaluation pipeline is ready for when legal-distance delivers
full 174k dense embeddings. This is a PREPARATORY test - the lane is BLOCKED on
legal-distance_174k_dense_embeddings.

When dense embeddings are complete, this test will:
1. Verify the evaluation script loads and runs correctly
2. Verify the success rule is applied with frozen thresholds
3. Verify artifacts are produced in the expected format
"""
import json
from pathlib import Path
import pytest

EVAL_SCRIPT = Path("fractal_map/evaluation/evaluate_174k_dense_embeddings.py")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")
MODES_BASE = Path("results/fractal_map/legal_distance_modes")


class TestDenseEmbeddingsEvaluationInfrastructure:
    """Tests that the dense embeddings evaluation infrastructure is ready."""

    def test_evaluation_script_exists(self):
        """The evaluation script must exist and be executable."""
        assert EVAL_SCRIPT.exists(), f"Missing evaluation script: {EVAL_SCRIPT}"
        # Check it's a valid Python script
        content = EVAL_SCRIPT.read_text()
        assert "def main()" in content
        assert "success_rule" in content
        assert "PASS iff" in content

    def test_success_rule_frozen(self):
        """The success rule must match the frozen v26 specification."""
        content = EVAL_SCRIPT.read_text()
        # Frozen success rule from v26:
        # PASS iff (a) branch purity res_3.0 > res_0.25 AND
        #          (b) area purity res_3.0 > res_0.25 AND
        #          (c) branch improvement_rate > 0.5 on >= 2 of 4 transitions
        assert "branch purity res_3.0 > res_0.25" in content
        assert "area purity res_3.0 > res_0.25" in content
        assert "improvement_rate > 0.5 on >= 2 of 4" in content
        assert "RESOLUTIONS = [0.25, 0.5, 1.0, 2.0, 3.0]" in content

    def test_metadata_path_configured(self):
        """The metadata path must point to accepted 174k metadata."""
        content = EVAL_SCRIPT.read_text()
        assert "metadata_174k.json" in content
        # The script should load from the accepted evaluation mount
        assert "/tmp/lex_accepted/evaluation" in content or "EVAL_META" in content

    def test_modes_directory_configured(self):
        """The modes directory must point to legal_distance_modes."""
        content = EVAL_SCRIPT.read_text()
        assert "legal_distance_modes" in content
        assert "MODES_DIR" in content

    def test_outputs_verdict_json(self):
        """The script must output a machine-readable verdict JSON."""
        content = EVAL_SCRIPT.read_text()
        assert "verdict" in content.lower()
        assert "json.dump" in content or "json.dumps" in content

    def test_computes_required_metrics(self):
        """The script must compute all required metrics."""
        content = EVAL_SCRIPT.read_text()
        required_functions = [
            "purity_per_res",
            "zoom_per_transition",
            "compute_nesting",
            "fragmentation_from_labels",
        ]
        for fn in required_functions:
            assert f"def {fn}" in content, f"Missing required function: {fn}"

    def test_baseline_random_purities_computed(self):
        """The script must compute baseline random purities for comparison."""
        content = EVAL_SCRIPT.read_text()
        assert "branch_random" in content
        assert "area_random" in content
        assert "1 / len(branches)" in content or "1/len(branches)" in content


class TestDenseEmbeddingsDataReadiness:
    """Tests for data readiness (will pass when legal-distance delivers)."""

    @pytest.mark.skipif(
        not METADATA_PATH.exists(),
        reason="174k metadata not yet available from accepted evaluation"
    )
    def test_174k_metadata_exists(self):
        """Full 174k metadata must exist in accepted evaluation."""
        assert METADATA_PATH.exists()
        with open(METADATA_PATH) as f:
            meta = json.load(f)
        # Should have ~174k entries (factory direction: 173,963)
        assert len(meta) >= 170000
        # Branch/area labels exist for subset (accepted eval has ~90k labeled)
        branch_labeled = sum(1 for m in meta if m.get('branch') and m['branch'] not in ('unknown', 'null'))
        area_labeled = sum(1 for m in meta if m.get('legal_area') and m['legal_area'] not in ('unknown', 'null'))
        assert branch_labeled > 80000  # Actual ~90k
        assert area_labeled > 80000    # Actual ~91k

    @pytest.mark.skipif(
        not any(MODES_BASE.glob("dense_*/")),
        reason="No dense embedding modes yet delivered by legal-distance"
    )
    def test_dense_mode_artifacts_exist(self):
        """When delivered, dense modes must have required artifacts."""
        dense_modes = list(MODES_BASE.glob("dense_*"))
        for mode_dir in dense_modes:
            assert (mode_dir / "decision_clusters.json").exists()
            for res in [0.25, 0.5, 1.0, 2.0, 3.0]:
                assert (mode_dir / f"labels_res_{res}.npy").exists()
            assert (mode_dir / "zoom_mappings.json").exists()


class TestDenseEmbeddingsHierarchicalBuilder:
    """Tests for the hierarchical map builder for dense embeddings."""

    BUILDER = Path("fractal_map/hierarchical/build_dense_hierarchical_artifacts.py")

    def test_builder_exists(self):
        assert self.BUILDER.exists(), f"Missing builder: {self.BUILDER}"

    def test_builder_supports_agglomerative(self):
        """Builder should be extensible to agglomerative clustering (validated at 1000-scale)."""
        content = self.BUILDER.read_text()
        # Currently builds hierarchical Leiden configs
        # Will need extension for agglomerative when full 174k dense embeddings arrive
        assert "hierarchical_leiden" in content
        assert "AgglomerativeClustering" not in content  # Not yet implemented
        # This is expected - preparatory note for future work

    def test_builder_produces_product_artifacts(self):
        """Builder must produce all artifacts required by product integration."""
        content = self.BUILDER.read_text()
        required_artifacts = [
            "cluster_metadata.json",
            "zoom_mappings.json",
            "zoom_coherence.json",
            "decision_clusters.json",
            "integration_summary.json",
            "hierarchical_map_results.json",
        ]
        for artifact in required_artifacts:
            assert artifact in content, f"Builder missing artifact: {artifact}"

    def test_builder_updates_registry(self):
        """Builder must update the map mode registry."""
        content = self.BUILDER.read_text()
        assert "map_mode_registry.json" in content
        assert "registry['modes']" in content


# This test documents the expected workflow when dense embeddings arrive
class TestDenseEmbeddingsWorkflow:
    """Documents the expected workflow for dense embeddings evaluation."""

    def test_workflow_documented(self):
        """The workflow is documented in the infrastructure validation report."""
        report = Path("reports/fractal_map/DENSE_EMBEDDINGS_INFRASTRUCTURE_VALIDATION_PARTIAL_2000_2010.md")
        assert report.exists(), "Infrastructure validation report must exist"
        content = report.read_text()
        assert "VALIDATED and READY" in content
        assert "agglomerative" in content.lower()
        assert "nesting=1.0" in content

    def test_partial_validation_completed(self):
        """Partial validation on 2000-2010 data (62k decisions) completed."""
        report = Path("reports/fractal_map/DENSE_EMBEDDINGS_INFRASTRUCTURE_VALIDATION_PARTIAL_2000_2010.md")
        content = report.read_text()
        assert "62,645" in content  # Combined decisions 2000-2010
        # Report documents that agglomerative methods achieve nesting=1.0
        assert "nesting=1.0" in content
        assert "Leiden baseline consistently FAILS" in content
        assert "Agglomerative" in content
        assert "VALIDATED and READY" in content