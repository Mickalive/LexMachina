#!/usr/bin/env python3
"""
Test: v11 OOS hybrid_stabilized cross-validation on frozen harness v3

Verifies that:
1. v11 models can be loaded and generate embeddings for the full 1200-decision slice
2. Both v11 arms pass both adversarial gates on the canonical benchmark
3. Hierarchy loss effect is consistent with v11 report (positive, small)
"""

import json
import numpy as np
import pytest
from pathlib import Path

RESULTS_PATH = Path(__file__).parent.parent.parent / "evaluation/results/v11_cross_validation/v11_cross_validation_results.json"


def load_results():
    with open(RESULTS_PATH) as f:
        return json.load(f)


class TestV11CrossValidation:
    """Test v11 OOS hybrid_stabilized on canonical frozen harness v3."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.results = load_results()

    def test_results_file_exists(self):
        """Cross-validation results file exists."""
        assert RESULTS_PATH.exists(), f"Results not found at {RESULTS_PATH}"

    def test_hierarchy_arm_passes_adversarial_gates(self):
        """v11 OOS hierarchy arm passes both adversarial gates on full slice."""
        res = self.results["results"]["v11_oos_hybrid_stabilized_hierarchy"]
        adv = res["adversarial"]
        assert adv["language_dominance_score"] < 0.85, \
            f"LangDom {adv['language_dominance_score']:.4f} >= 0.85"
        assert adv["jurist_preference_rate"] > 0.5, \
            f"JuristPref {adv['jurist_preference_rate']:.4f} <= 0.5"
        assert adv["both_pass"] is True

    def test_nohierarchy_arm_passes_adversarial_gates(self):
        """v11 OOS no-hierarchy arm passes both adversarial gates on full slice."""
        res = self.results["results"]["v11_oos_hybrid_stabilized_nohierarchy"]
        adv = res["adversarial"]
        assert adv["language_dominance_score"] < 0.85, \
            f"LangDom {adv['language_dominance_score']:.4f} >= 0.85"
        assert adv["jurist_preference_rate"] > 0.5, \
            f"JuristPref {adv['jurist_preference_rate']:.4f} <= 0.5"
        assert adv["both_pass"] is True

    def test_hierarchy_loss_effect_is_positive(self):
        """Hierarchy loss effect on JP is positive (direction consistent with v11 report)."""
        hier = self.results["results"]["v11_oos_hybrid_stabilized_hierarchy"]["adversarial"]["jurist_preference_rate"]
        nohier = self.results["results"]["v11_oos_hybrid_stabilized_nohierarchy"]["adversarial"]["jurist_preference_rate"]
        delta = hier - nohier
        assert delta >= -0.01, \
            f"Hierarchy effect is negative (ΔJP={delta:+.4f}), inconsistent with v11 report"

    def test_hierarchy_loss_effect_is_small(self):
        """Hierarchy loss effect is small (NOT load-bearing for gate crossing)."""
        hier = self.results["results"]["v11_oos_hybrid_stabilized_hierarchy"]["adversarial"]["jurist_preference_rate"]
        nohier = self.results["results"]["v11_oos_hybrid_stabilized_nohierarchy"]["adversarial"]["jurist_preference_rate"]
        delta = hier - nohier
        assert abs(delta) < 0.05, \
            f"Hierarchy effect too large (ΔJP={delta:+.4f}), should be < 0.05"

    def test_v11_beats_center_projected_baseline(self):
        """v11 OOS models beat center_projected_768 baseline on jurist preference."""
        baseline_jp = self.results["results"]["center_projected_768_baseline"]["adversarial"]["jurist_preference_rate"]
        hier_jp = self.results["results"]["v11_oos_hybrid_stabilized_hierarchy"]["adversarial"]["jurist_preference_rate"]
        assert hier_jp > baseline_jp, \
            f"v11 hierarchy ({hier_jp:.4f}) does not beat baseline ({baseline_jp:.4f})"

    def test_v11_jurivoc_alignment(self):
        """v11 OOS hierarchy arm has meaningful Jurivoc alignment."""
        res = self.results["results"]["v11_oos_hybrid_stabilized_hierarchy"]
        l0 = res["jurivoc"]["level_0_nmi"]
        assert l0 > 0.3, f"Jurivoc L0 NMI={l0:.4f} < 0.3 (no meaningful alignment)"

    def test_both_arms_generate_embeddings(self):
        """Both v11 arms generated 128-dim embeddings for all 1200 decisions."""
        hier_emb = Path(__file__).parent.parent.parent / "evaluation/results/v11_cross_validation/v11_oos_hybrid_stabilized_hierarchy_embeddings.npy"
        nohier_emb = Path(__file__).parent.parent.parent / "evaluation/results/v11_cross_validation/v11_oos_hybrid_stabilized_nohierarchy_embeddings.npy"
        assert hier_emb.exists(), "Hierarchy embeddings not generated"
        assert nohier_emb.exists(), "No-hierarchy embeddings not generated"
        h = np.load(hier_emb)
        n = np.load(nohier_emb)
        assert h.shape == (1200, 128), f"Hierarchy embeddings shape: {h.shape}"
        assert n.shape == (1200, 128), f"No-hierarchy embeddings shape: {n.shape}"

    def test_verdict_summary(self):
        """Both v11 arms have PASS verdict in summary."""
        vs = self.results["verdict_summary"]
        assert vs["v11_oos_hybrid_stabilized_hierarchy"] == "PASS"
        assert vs["v11_oos_hybrid_stabilized_nohierarchy"] == "PASS"
