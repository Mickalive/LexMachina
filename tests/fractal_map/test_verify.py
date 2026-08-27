#!/usr/bin/env python3
"""
Verification test for fractal-map lane.

Tests that the hierarchical Leiden fractal map artifacts are consistent
and reproducible. Run as: python -m pytest tests/fractal_map/test_verify.py -v
"""

import json
import numpy as np
import pytest
from pathlib import Path
from collections import Counter

BASE = Path("/home/runner/work/LexMachina/LexMachina")
RESULTS_DIR = BASE / "results/fractal_map"
HIERARCHICAL_DIR = RESULTS_DIR / "hierarchical_map"
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
    def test_label_array_exists(self, res):
        path = HIERARCHICAL_DIR / f"labels_res_{res}.npy"
        assert path.exists(), f"Missing label array: labels_res_{res}.npy"

    @pytest.mark.parametrize("res", RESOLUTIONS)
    def test_label_array_size(self, res):
        path = HIERARCHICAL_DIR / f"labels_res_{res}.npy"
        arr = np.load(path)
        assert len(arr) == 1000, f"labels_res_{res}.npy has {len(arr)} labels, expected 1000"

    def test_hierarchical_leiden_results_exists(self):
        path = HIERARCHICAL_DIR / "hierarchical_leiden_results.json"
        assert path.exists()

    def test_cluster_assignments_exists(self):
        path = HIERARCHICAL_DIR / "cluster_assignments.json"
        assert path.exists()

    def test_cluster_assignments_size(self):
        ca = load_json("results/fractal_map/hierarchical_map/cluster_assignments.json")
        for res in RESOLUTIONS:
            key = f"res_{res}"
            assert key in ca, f"Missing key {key} in cluster_assignments.json"
            assert len(ca[key]) == 1000, f"cluster_assignments[{key}] has {len(ca[key])} entries, expected 1000"


class TestHierarchicalLeiden:
    """Test that hierarchical Leiden achieves target metrics."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.hl_results = load_json("results/fractal_map/hierarchical_map/hierarchical_leiden_results.json")
        self.state = load_json("state/fractal-map.json")

    def test_best_config_exists(self):
        best = self.hl_results.get("best_config")
        assert best is not None, "No best_config in hierarchical_leiden_results.json"
        assert best in self.hl_results.get("hierarchical_results", {}), f"Best config {best} not in results"

    def test_hierarchical_purity(self):
        best = self.hl_results["best_config"]
        purity = self.hl_results["hierarchical_results"][best]["hierarchical_purity"]
        assert purity > 0.95, f"Hierarchical purity {purity:.6f} below 0.95 threshold"

    def test_hierarchical_nesting(self):
        best = self.hl_results["best_config"]
        nesting = self.hl_results["hierarchical_results"][best]["nesting_score"]
        assert nesting == 1.0, f"Hierarchical nesting {nesting:.6f} != 1.0"

    def test_sub_cluster_count(self):
        best = self.hl_results["best_config"]
        n_fine = self.hl_results["hierarchical_results"][best]["n_fine_clusters"]
        assert n_fine > 0, f"Zero fine clusters"

    def test_sub_cluster_sizes_sum_to_1000(self):
        best = self.hl_results["best_config"]
        cluster_info = self.hl_results["hierarchical_results"][best]["cluster_info"]
        total = sum(c["size"] for c in cluster_info.values())
        assert total == 1000, f"Sub-cluster sizes sum to {total}, expected 1000"

    def test_valid_parents(self):
        best = self.hl_results["best_config"]
        cluster_info = self.hl_results["hierarchical_results"][best]["cluster_info"]
        for cid, info in cluster_info.items():
            assert 0 <= info["coarse_id"] <= 7, f"Cluster {cid} has invalid coarse_id {info['coarse_id']}"


class TestMetricConsistency:
    """Test that state file metrics match recomputed values."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.state = load_json("state/fractal-map.json")
        self.hl_results = load_json("results/fractal_map/hierarchical_map/hierarchical_leiden_results.json")

    def test_state_evidence_tier(self):
        assert self.state["evidence_tier"] == "REPRODUCED"

    def test_state_cycle_status(self):
        assert self.state["cycle_status"] == "COMPLETED"

    def test_state_continue_recommended_false(self):
        assert self.state["continue_recommended"] is False

    def test_state_recommendation_productize(self):
        assert self.state["next_recommendation"] == "PRODUCTIZE"

    def test_state_verdict_pass(self):
        verdict = self.state["metrics_summary"]["hierarchical_leiden_experiment"]["verdict"]
        assert verdict == "PASS"

    def test_state_hierarchical_purity_matches(self):
        state_purity = self.state["metrics_summary"]["hierarchical_leiden_experiment"]["hierarchical_purity"]
        best = self.hl_results["best_config"]
        recomputed = self.hl_results["hierarchical_results"][best]["hierarchical_purity"]
        assert abs(state_purity - recomputed) < 1e-6, f"State {state_purity} != recomputed {recomputed}"

    def test_zoom_improvement_positive(self):
        improvement = self.state["metrics_summary"]["hierarchical_leiden_experiment"]["purity_improvement_pct"]
        assert improvement > 0, f"Zoom improvement {improvement}% is not positive"
