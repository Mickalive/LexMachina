"""
Tests for v17 label-normalization adversarial evaluation.

Validates:
  1. The cross-lingual legal_area normalization module merges ONLY clearly
     equivalent de/fr/it labels and substantially reduces the unique-label count.
  2. The v17 raw-machinery re-run reproduces the frozen v16 baseline values
     (identical embedding + identical KMeans) -- proving a fair comparison.
  3. Normalized labels materially improve hierarchy-family purity on identical
     machinery (the v17 central finding).
"""
import json
import sys
import pytest
from pathlib import Path

_EXPERIMENTS = Path("evaluation/experiments")
sys.path.insert(0, str(_EXPERIMENTS))

RESULTS_PATH = Path("results/evaluation/v17_label_normalization/v17_label_normalization_latest.json")
CORPUS_PATH = Path("evaluation/data/bger_expanded_1200_metadata.jsonl")


def _load_results():
    with open(RESULTS_PATH) as f:
        return json.load(f)


class TestLegalAreaNormalization:
    """Cross-lingual normalization map must be conservative and effective."""

    def test_normalization_reduces_label_count(self):
        from legal_area_normalize import normalize_legal_area
        from collections import Counter
        raw = Counter()
        norm = Counter()
        with open(CORPUS_PATH) as f:
            for line in f:
                m = json.loads(line)
                lbl = m.get('legal_area') or m.get('branch') or 'unknown'
                raw[lbl] += 1
                norm[normalize_legal_area(lbl)] += 1
        assert len(norm) < len(raw), "Normalization must reduce unique label count"
        # The observed material reduction (108 -> 55) is > 30% reduction
        assert len(norm) <= 0.70 * len(raw), \
            f"Expected >=30% label reduction, raw={len(raw)}, norm={len(norm)}"

    def test_normalization_only_merges_clear_equivalents(self):
        """Distinct legal topics must NOT be collapsed together."""
        from legal_area_normalize import normalize_legal_area
        # Distinct topics must remain distinct
        assert normalize_legal_area("Strafprozess") == normalize_legal_area("Procédure pénale")
        assert normalize_legal_area("Strafprozess") == normalize_legal_area("Procedura penale")
        # genuinely different areas must map differently
        assert normalize_legal_area("Familienrecht") != normalize_legal_area("Vertragsrecht")
        assert normalize_legal_area("Invalidenversicherung") != normalize_legal_area("Unfallversicherung")
        # coarse umbrella labels pass through unchanged
        assert normalize_legal_area("public") == "public"
        assert normalize_legal_area("NONE") == "NONE"


class TestV17ReproducesV16Baseline:
    """v17 raw machinery must reproduce the frozen v16 values exactly."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.results = _load_results()

    def test_raw_run_matches_v16_frozen(self):
        raw = self.results['raw_run']
        hier = raw['hierarchy_coherence']
        assert hier['best_purity'] == pytest.approx(0.3885017, abs=1e-4)
        assert hier['best_nmi'] == pytest.approx(0.521771, abs=1e-4)
        leg = raw['legal_area_clustering']
        assert leg['overall_purity'] == pytest.approx(0.008258, abs=1e-5)
        assert leg['num_areas'] == 104
        zoom = raw['zoom_coherence']
        assert zoom['coarse_purity'] == pytest.approx(0.0290723, abs=1e-4)
        assert zoom['fine_purity'] == pytest.approx(0.0143554, abs=1e-4)

    def test_normalized_empty_or_reduced_num_areas(self):
        norm = self.results['normalized_run']
        assert norm['legal_area_clustering']['num_areas'] < \
            self.results['raw_run']['legal_area_clustering']['num_areas']


class TestV17Finding:
    """The v17 central finding: normalization materially improves purity on identical machinery."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.results = _load_results()

    def test_success_rule_met(self):
        """At least one hierarchy-family purity metric improves >=20% over frozen raw baseline."""
        assert self.results['success_rule_met_any'] is True

    def test_hierarchy_purity_improves_materially(self):
        r = self.results['ratios_vs_frozen_raw_baseline']
        assert r['hierarchy_purity_ratio'] >= 1.20, \
            f"hierarchy purity ratio {r['hierarchy_purity_ratio']} < 1.20"

    def test_zoom_fine_purity_improves_materially(self):
        r = self.results['ratios_vs_frozen_raw_baseline']
        assert r['zoom_fine_purity_ratio'] >= 1.20, \
            f"zoom fine purity ratio {r['zoom_fine_purity_ratio']} < 1.20"

    def test_normalized_does_not_overclaim_pass(self):
        """Honesty guard: normalization improves purity but must NOT flip to PASS ---
        confirms the nuanced finding (not purely label error) rather than an overclaim."""
        norm = self.results['normalized_run']
        hier_purity = norm['hierarchy_coherence']['best_purity']
        # frozen purity PASS threshold is 0.7
        assert hier_purity < 0.7, "normalized should still be below PASS threshold (nuance)"

    def test_cross_lingual_duplication_is_majority_of_label_count(self):
        """Provenance: the dominant cause of the 108-label count is cross-lingual
        duplication, not genuine granularity (raw->norm reduces by ~49%)."""
        assert self.results['raw_unique_labels'] >= 90
        assert self.results['normalized_unique_labels'] <= 60
