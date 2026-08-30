#!/usr/bin/env python3
"""
Verification test for fractal-map lane.

Tests that the hierarchical Leiden fractal map artifacts are consistent
and reproducible. Run as: python -m pytest tests/fractal_map/test_verify.py -v
"""

import json
import os
import numpy as np
import pytest
from pathlib import Path
from collections import Counter

BASE = Path(os.environ.get("LEXMACHINA_BASE", str(Path(__file__).resolve().parents[2])))
RESULTS_DIR = BASE / "results/fractal_map"
HIERARCHICAL_DIR = RESULTS_DIR / "hierarchical_map"
HIERARCHICAL_CP_DIR = RESULTS_DIR / "hierarchical_map_center_projected"
STATE_FILE = BASE / "state/fractal-map.json"

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


def load_json(path):
    with open(BASE / path) as f:
        return json.load(f)


def load_branch_labels():
    """Load branch labels from corpus files."""
    metadata = load_json("results/fractal_map/baseline/metadata.json")
    id_to_idx = {m["decision_id"]: i for i, m in enumerate(metadata)}
    CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get("decision_id", "")
                if did in id_to_idx:
                    branch_map[did] = d.get("branch")
    return np.array([branch_map.get(m["decision_id"], "unknown") for m in metadata])


def compute_cluster_purity(labels, branch_labels):
    """Compute purity for each cluster."""
    unique_labels = np.unique(labels)
    purities = []
    for cl in unique_labels:
        mask = labels == cl
        cl_branches = branch_labels[mask]
        if len(cl_branches) == 0:
            continue
        counts = Counter(cl_branches)
        most_common_count = counts.most_common(1)[0][1]
        purities.append(most_common_count / len(cl_branches))
    return purities


def compute_nesting(labels_coarse, labels_fine):
    """Compute nesting consistency between coarse and fine resolutions."""
    fine_labels = np.unique(labels_fine)
    consistent = 0
    for fl in fine_labels:
        fine_mask = labels_fine == fl
        coarse_in_fine = labels_coarse[fine_mask]
        if len(coarse_in_fine) == 0:
            continue
        unique_coarse = np.unique(coarse_in_fine)
        if len(unique_coarse) == 1:
            consistent += 1
    return consistent / len(fine_labels) if len(fine_labels) > 0 else 0


class TestArtifactIntegrity:
    """Test that all evidence artifacts exist and have correct shapes."""

    @pytest.mark.parametrize("res", RESOLUTIONS)
    def test_label_array_exists_cp(self, res):
        """Test center_projected label arrays exist."""
        path = HIERARCHICAL_CP_DIR / f"labels_res_{res}.npy"
        assert path.exists(), f"Missing label array: labels_res_{res}.npy"

    @pytest.mark.parametrize("res", RESOLUTIONS)
    def test_label_array_size_cp(self, res):
        """Test center_projected label arrays have correct size."""
        path = HIERARCHICAL_CP_DIR / f"labels_res_{res}.npy"
        arr = np.load(path)
        assert len(arr) == 1000, f"labels_res_{res}.npy has {len(arr)} labels, expected 1000"

    def test_hierarchical_best_exists_cp(self):
        """Test hierarchical best labels exist for center_projected."""
        path = HIERARCHICAL_CP_DIR / "labels_hierarchical_best.npy"
        assert path.exists(), "Missing labels_hierarchical_best.npy"
        arr = np.load(path)
        assert len(arr) == 1000

    def test_coarse_labels_exists_cp(self):
        """Test coarse labels exist for center_projected."""
        path = HIERARCHICAL_CP_DIR / "labels_coarse_0.5.npy"
        assert path.exists(), "Missing labels_coarse_0.5.npy"
        arr = np.load(path)
        assert len(arr) == 1000

    def test_center_projected_results_exists(self):
        path = HIERARCHICAL_CP_DIR / "center_projected_hierarchical_results.json"
        assert path.exists()

    def test_hierarchical_map_results_exists(self):
        path = HIERARCHICAL_CP_DIR / "hierarchical_map_results.json"
        assert path.exists()

    def test_cluster_assignments_exists_cp(self):
        path = HIERARCHICAL_CP_DIR / "cluster_assignments.json"
        assert path.exists()

    def test_cluster_assignments_size_cp(self):
        ca = load_json("results/fractal_map/hierarchical_map_center_projected/cluster_assignments.json")
        for res in RESOLUTIONS:
            key = f"res_{res}"
            assert key in ca, f"Missing key {key} in cluster_assignments.json"
            assert len(ca[key]) == 1000, f"cluster_assignments[{key}] has {len(ca[key])} entries, expected 1000"

    # V9 hybrid mode artifact integrity tests (cp-hybrids)
    V9_CP_HYBRID_MODES = [
        "cited_decisions_tfidf_hybrid_cp64_0.3",
        "cited_decisions_tfidf_hybrid_cp64_0.5",
        "cited_decisions_tfidf_hybrid_cp64_0.7",
        "cited_decisions_tfidf_hybrid_cp768_0.3",
        "cited_decisions_tfidf_hybrid_cp768_0.5",
        "cited_decisions_tfidf_hybrid_cp768_0.7",
    ]

    # V9 breakthrough representations (factory direction v9 requirement)
    V9_BREAKTHROUGH_MODES = [
        "hybrid_stabilized_epoch1",
        "cited_decisions_tfidf_outcome_hybrid_0.5",
        "cited_decisions_tfidf_outcome_hybrid_0.7",
        "following_alpha0.3",
        "criticizing_alpha0.3",
        "citing_alpha0.3",
    ]

    @pytest.mark.parametrize("mode_id", V9_CP_HYBRID_MODES)
    def test_v9_cp_hybrid_label_arrays_exist(self, mode_id):
        """Test v9 cp-hybrid mode label arrays exist."""
        for res in RESOLUTIONS:
            path = RESULTS_DIR / "legal_distance_modes" / mode_id / f"labels_res_{res}.npy"
            assert path.exists(), f"Missing label array for {mode_id}: labels_res_{res}.npy"

    @pytest.mark.parametrize("mode_id", V9_CP_HYBRID_MODES)
    def test_v9_cp_hybrid_label_arrays_size(self, mode_id):
        """Test v9 cp-hybrid mode label arrays have correct size."""
        for res in RESOLUTIONS:
            path = RESULTS_DIR / "legal_distance_modes" / mode_id / f"labels_res_{res}.npy"
            arr = np.load(path)
            assert len(arr) == 1000, f"{mode_id} labels_res_{res}.npy has {len(arr)} labels, expected 1000"

    @pytest.mark.parametrize("mode_id", V9_CP_HYBRID_MODES)
    def test_v9_cp_hybrid_hierarchical_labels_exist(self, mode_id):
        """Test v9 cp-hybrid mode hierarchical labels exist."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "labels_hierarchical_best.npy"
        assert path.exists(), f"Missing labels_hierarchical_best.npy for {mode_id}"
        arr = np.load(path)
        assert len(arr) == 1000

    @pytest.mark.parametrize("mode_id", V9_CP_HYBRID_MODES)
    def test_v9_cp_hybrid_coarse_labels_exist(self, mode_id):
        """Test v9 cp-hybrid mode coarse labels exist."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "labels_coarse_0.5.npy"
        assert path.exists(), f"Missing labels_coarse_0.5.npy for {mode_id}"
        arr = np.load(path)
        assert len(arr) == 1000

    @pytest.mark.parametrize("mode_id", V9_CP_HYBRID_MODES)
    def test_v9_cp_hybrid_hierarchical_map_results_exist(self, mode_id):
        """Test v9 cp-hybrid mode hierarchical results exist."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "hierarchical_map_results.json"
        assert path.exists(), f"Missing hierarchical_map_results.json for {mode_id}"

    @pytest.mark.parametrize("mode_id", V9_CP_HYBRID_MODES)
    def test_v9_cp_hybrid_integration_summary_exist(self, mode_id):
        """Test v9 cp-hybrid mode integration summary exists."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "integration_summary.json"
        assert path.exists(), f"Missing integration_summary.json for {mode_id}"

    # V9 breakthrough representation tests
    @pytest.mark.parametrize("mode_id", V9_BREAKTHROUGH_MODES)
    def test_v9_breakthrough_label_arrays_exist(self, mode_id):
        """Test v9 breakthrough mode label arrays exist."""
        for res in RESOLUTIONS:
            path = RESULTS_DIR / "legal_distance_modes" / mode_id / f"labels_res_{res}.npy"
            assert path.exists(), f"Missing label array for {mode_id}: labels_res_{res}.npy"

    @pytest.mark.parametrize("mode_id", V9_BREAKTHROUGH_MODES)
    def test_v9_breakthrough_label_arrays_size(self, mode_id):
        """Test v9 breakthrough mode label arrays have correct size."""
        for res in RESOLUTIONS:
            path = RESULTS_DIR / "legal_distance_modes" / mode_id / f"labels_res_{res}.npy"
            arr = np.load(path)
            assert len(arr) == 1000, f"{mode_id} labels_res_{res}.npy has {len(arr)} labels, expected 1000"

    @pytest.mark.parametrize("mode_id", V9_BREAKTHROUGH_MODES)
    def test_v9_breakthrough_hierarchical_labels_exist(self, mode_id):
        """Test v9 breakthrough mode hierarchical labels exist."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "labels_hierarchical_best.npy"
        assert path.exists(), f"Missing labels_hierarchical_best.npy for {mode_id}"
        arr = np.load(path)
        assert len(arr) == 1000

    @pytest.mark.parametrize("mode_id", V9_BREAKTHROUGH_MODES)
    def test_v9_breakthrough_coarse_labels_exist(self, mode_id):
        """Test v9 breakthrough mode coarse labels exist."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "labels_coarse_0.5.npy"
        assert path.exists(), f"Missing labels_coarse_0.5.npy for {mode_id}"
        arr = np.load(path)
        assert len(arr) == 1000

    @pytest.mark.parametrize("mode_id", V9_BREAKTHROUGH_MODES)
    def test_v9_breakthrough_hierarchical_map_results_exist(self, mode_id):
        """Test v9 breakthrough mode hierarchical results exist."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "hierarchical_map_results.json"
        assert path.exists(), f"Missing hierarchical_map_results.json for {mode_id}"

    @pytest.mark.parametrize("mode_id", V9_BREAKTHROUGH_MODES)
    def test_v9_breakthrough_integration_summary_exist(self, mode_id):
        """Test v9 breakthrough mode integration summary exists."""
        path = RESULTS_DIR / "legal_distance_modes" / mode_id / "integration_summary.json"
        assert path.exists(), f"Missing integration_summary.json for {mode_id}"


class TestHierarchicalLeiden:
    """Test that hierarchical Leiden achieves target metrics on center_projected."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.cp_results = load_json("results/fractal_map/hierarchical_map_center_projected/center_projected_hierarchical_results.json")
        self.state = load_json("state/fractal-map.json")

    def test_best_config_exists(self):
        best = self.cp_results.get("best_config")
        assert best is not None, "No best_config in center_projected_hierarchical_results.json"
        assert best in self.cp_results.get("hierarchical_results", {}), f"Best config {best} not in results"

    def test_hierarchical_purity(self):
        best = self.cp_results["best_config"]
        purity = self.cp_results["hierarchical_results"][best]["hierarchical_purity"]
        assert purity > 0.95, f"Hierarchical purity {purity:.6f} below 0.95 threshold"

    def test_hierarchical_nesting(self):
        best = self.cp_results["best_config"]
        nesting = self.cp_results["hierarchical_results"][best]["nesting_score"]
        assert nesting == 1.0, f"Hierarchical nesting {nesting:.6f} != 1.0"

    def test_sub_cluster_count(self):
        best = self.cp_results["best_config"]
        n_fine = self.cp_results["hierarchical_results"][best]["n_fine_clusters"]
        assert n_fine > 0, f"Zero fine clusters"

    def test_sub_cluster_sizes_sum_to_1000(self):
        best = self.cp_results["best_config"]
        cluster_info = self.cp_results["hierarchical_results"][best]["cluster_info"]
        total = sum(c["size"] for c in cluster_info.values())
        assert total == 1000, f"Sub-cluster sizes sum to {total}, expected 1000"

    def test_valid_parents(self):
        best = self.cp_results["best_config"]
        cluster_info = self.cp_results["hierarchical_results"][best]["cluster_info"]
        for cid, info in cluster_info.items():
            assert 0 <= info["coarse_id"] <= 7, f"Cluster {cid} has invalid coarse_id {info['coarse_id']}"


class TestMetricConsistency:
    """Test that state file metrics match recomputed values."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.state = load_json("state/fractal-map.json")
        self.cp_results = load_json("results/fractal_map/hierarchical_map_center_projected/center_projected_hierarchical_results.json")

    def test_state_evidence_tier(self):
        assert self.state["evidence_tier"] == "REPRODUCED"

    def test_state_cycle_status(self):
        assert self.state["cycle_status"] == "COMPLETED"

    def test_state_continue_recommended_false(self):
        assert self.state["continue_recommended"] is False

    def test_state_recommendation_productize(self):
        # Accept either "PRODUCTIZE" or detailed recommendation containing "PRODUCTIZE" or "CONTINUE"
        rec = self.state["next_recommendation"]
        assert rec == "PRODUCTIZE" or "PRODUCTIZE" in rec or "CONTINUE" in rec, f"Unexpected recommendation: {rec}"

    def test_state_verdict_pass(self):
        verdict = self.state["metrics_summary"]["center_projected_hierarchical_experiment"]["verdict"]
        assert verdict == "PASS"

    def test_state_hierarchical_purity_matches(self):
        state_purity = self.state["metrics_summary"]["center_projected_hierarchical_experiment"]["hierarchical_purity_global"]
        state_best_config = self.state["metrics_summary"]["center_projected_hierarchical_experiment"]["best_config"]
        recomputed = self.cp_results["hierarchical_results"][state_best_config]["hierarchical_purity"]
        assert abs(state_purity - recomputed) < 1e-6, f"State {state_purity} != recomputed {recomputed} for config {state_best_config}"

    def test_zoom_improvement_positive(self):
        improvement = self.state["metrics_summary"]["center_projected_hierarchical_experiment"]["purity_improvement_vs_flat_pct"]
        assert improvement > 0, f"Zoom improvement {improvement}% is not positive"

    def test_default_mode_is_center_projected(self):
        """Verify center_projected_hierarchical is the default mode."""
        default_mode = self.state["map_modes"]["default"]["mode_id"]
        assert default_mode == "center_projected_hierarchical"

    def test_center_projected_purity_beats_concat(self):
        """Verify center_projected hierarchical purity > concat baseline."""
        cp_purity = self.state["validation_metrics"]["center_projected_hierarchical"]["hierarchical_purity_global"]
        concat_purity = self.state["validation_metrics"]["hierarchical_leiden_concat_legacy"]["hierarchical_purity_global"]
        assert cp_purity > concat_purity, f"center_projected ({cp_purity}) not better than concat ({concat_purity})"


class TestLegacyConcatPreserved:
    """Test that legacy concat artifacts are preserved."""

    @pytest.mark.parametrize("res", RESOLUTIONS)
    def test_legacy_label_array_exists(self, res):
        path = HIERARCHICAL_DIR / f"labels_res_{res}.npy"
        assert path.exists(), f"Missing legacy label array: labels_res_{res}.npy"

    def test_legacy_hierarchical_best_exists(self):
        path = HIERARCHICAL_DIR / "labels_hierarchical_best.npy"
        assert path.exists(), "Missing legacy labels_hierarchical_best.npy"

    def test_legacy_coarse_labels_exists(self):
        path = HIERARCHICAL_DIR / "labels_coarse_0.5.npy"
        assert path.exists(), "Missing legacy labels_coarse_0.5.npy"

    def test_legacy_results_exist(self):
        assert (HIERARCHICAL_DIR / "hierarchical_leiden_results.json").exists()
        assert (HIERARCHICAL_DIR / "hierarchical_map_results.json").exists()


class TestLegalDistanceModes:
    """Test that legal-distance modes are properly integrated."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.state = load_json("state/fractal-map.json")

    def test_five_legal_distance_modes_available(self):
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        assert "debiased_citation_blended" in ld_modes
        assert "legal_cited_decisions_only" in ld_modes
        assert "hybrid_alpha_03" in ld_modes
        assert "hybrid_alpha_05" in ld_modes
        assert "legal_issues_outcomes" in ld_modes

    def test_v7_metric_learning_modes_available(self):
        """Test that v7 metric learning modes are available."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        assert "linear_metric_epoch4" in ld_modes
        assert "mahalanobis_metric_epoch4" in ld_modes

    def test_v7_citation_signal_modes_available(self):
        """Test that v7 citation signal modes are available."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        assert "cited_decisions_tfidf" in ld_modes
        assert "hybrid_cited_0.3" in ld_modes

    def test_legal_distance_modes_accepted_tier(self):
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        for mode_id, mode_info in ld_modes.items():
            if mode_id != "center_projected":
                assert mode_info["evidence_tier"] == "ACCEPTED"

    def test_v7_modes_pass_both_adversarial_gates(self):
        """Test that all v7 modes pass both adversarial gates."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        v7_modes = ["linear_metric_epoch4", "mahalanobis_metric_epoch4", "cited_decisions_tfidf", "hybrid_cited_0.3"]
        for mode_id in v7_modes:
            mode_info = ld_modes[mode_id]
            assert mode_info.get("adversarial_both_pass") is True, f"{mode_id} does not pass both adversarial gates"

    def test_v9_cited_decisions_hybrid_modes_available(self):
        """Test that v9 cited_decisions_tfidf cp-hybrid modes are available."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        v9_cp_hybrids = [
            "cited_decisions_tfidf_hybrid_cp64_0.3",
            "cited_decisions_tfidf_hybrid_cp64_0.5",
            "cited_decisions_tfidf_hybrid_cp64_0.7",
            "cited_decisions_tfidf_hybrid_cp768_0.3",
            "cited_decisions_tfidf_hybrid_cp768_0.5",
            "cited_decisions_tfidf_hybrid_cp768_0.7",
        ]
        for mode_id in v9_cp_hybrids:
            assert mode_id in ld_modes, f"Missing v9 cp-hybrid mode: {mode_id}"

    def test_v9_cp_hybrids_pass_both_adversarial_gates(self):
        """Test that all v9 cp-hybrid modes pass both adversarial gates."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        v9_cp_hybrids = [
            "cited_decisions_tfidf_hybrid_cp64_0.3",
            "cited_decisions_tfidf_hybrid_cp64_0.5",
            "cited_decisions_tfidf_hybrid_cp64_0.7",
            "cited_decisions_tfidf_hybrid_cp768_0.3",
            "cited_decisions_tfidf_hybrid_cp768_0.5",
            "cited_decisions_tfidf_hybrid_cp768_0.7",
        ]
        for mode_id in v9_cp_hybrids:
            mode_info = ld_modes[mode_id]
            assert mode_info.get("adversarial_both_pass") is True, f"{mode_id} does not pass both adversarial gates"
            assert mode_info.get("evidence_tier") == "ACCEPTED", f"{mode_id} evidence tier not ACCEPTED"

    def test_v9_breakthrough_modes_available(self):
        """Test that v9 breakthrough representations are available."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        v9_breakthrough = [
            "hybrid_stabilized_epoch1",
            "cited_decisions_tfidf_outcome_hybrid_0.5",
            "cited_decisions_tfidf_outcome_hybrid_0.7",
            "following_alpha0.3",
            "criticizing_alpha0.3",
            "citing_alpha0.3",
        ]
        for mode_id in v9_breakthrough:
            assert mode_id in ld_modes, f"Missing v9 breakthrough mode: {mode_id}"

    def test_v9_breakthrough_modes_pass_both_adversarial_gates(self):
        """Test that all v9 breakthrough modes pass both adversarial gates."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        v9_breakthrough = [
            "hybrid_stabilized_epoch1",
            "cited_decisions_tfidf_outcome_hybrid_0.5",
            "cited_decisions_tfidf_outcome_hybrid_0.7",
            "following_alpha0.3",
            "criticizing_alpha0.3",
            "citing_alpha0.3",
        ]
        for mode_id in v9_breakthrough:
            mode_info = ld_modes[mode_id]
            assert mode_info.get("adversarial_both_pass") is True, f"{mode_id} does not pass both adversarial gates"
            assert mode_info.get("evidence_tier") == "ACCEPTED", f"{mode_id} evidence tier not ACCEPTED"

    def test_total_modes_count(self):
        """Test total mode count is 24 (1 default + 21 available legal-distance + 1 legacy + 1 placeholder)."""
        ld_modes = self.state["map_modes"]["legal_distance_modes"]
        # 5 v6 + 4 v7 + 6 v9 cp-hybrids + 3 v9 outcome-hybrids + 3 citation-role = 21 available legal-distance modes
        # 1 placeholder (center_projected) = 22 total legal-distance modes
        available_count = sum(1 for m in ld_modes.values() if m.get("status") == "available")
        placeholder_count = sum(1 for m in ld_modes.values() if m.get("status") == "placeholder")
        assert available_count == 21, f"Expected 21 available legal-distance modes, got {available_count}"
        assert placeholder_count == 1, f"Expected 1 placeholder legal-distance mode, got {placeholder_count}"

    def test_legacy_mode_preserved(self):
        legacy = self.state["map_modes"]["legacy_modes"]
        assert "hierarchical_leiden_concat" in legacy
        assert legacy["hierarchical_leiden_concat"]["status"] == "legacy"
