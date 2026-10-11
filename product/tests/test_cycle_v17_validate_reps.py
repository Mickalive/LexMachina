"""
LexMachina Product Cycle v17 Tests
Validates all 30 representations loaded by the product: structural integrity,
zoom level consistency, cluster size invariants, and design pattern coverage.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.map_loader import MapLoader
from app.navigation import NavigationAPI


def _get_nav():
    """Get an initialized NavigationAPI for testing."""
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    nav = NavigationAPI(corpus_dir, results_dir)
    nav.initialize()
    return nav


# ---------------------------------------------------------------------------
# Representation Count
# ---------------------------------------------------------------------------

class TestRepresentationCount:
    """Verify the expected number of representations load."""

    def test_design_patterns_count(self):
        """DESIGN_PATTERNS covers all 30 representations."""
        assert len(MapLoader.DESIGN_PATTERNS) >= 30

    def test_loaded_representations_count(self):
        """NavigationAPI loads at least 30 representations."""
        nav = _get_nav()
        reps = nav.map_loader.get_available_representations()
        assert len(reps) >= 30, f"Expected >= 30 reps, got {len(reps)}: {reps}"


# ---------------------------------------------------------------------------
# Per-Representation Structural Integrity
# ---------------------------------------------------------------------------

class TestRepresentationStructure:
    """Each loaded representation must have non-empty zoom levels,
    positions, cluster_assignments, and clusters at every zoom level."""

    def _get_reps(self):
        nav = _get_nav()
        return nav, nav.map_loader.get_available_representations()

    def test_each_rep_loads_without_error(self):
        """Every representation is present in map_loader.maps."""
        nav, reps = self._get_reps()
        for rep in reps:
            m = nav.map_loader.get_map(rep)
            assert m is not None, f"Representation '{rep}' returned None from get_map()"

    def test_each_rep_has_at_least_one_zoom_level(self):
        """Every representation has >= 1 zoom level."""
        nav, reps = self._get_reps()
        for rep in reps:
            levels = nav.map_loader.get_zoom_levels(rep)
            assert len(levels) >= 1, f"Representation '{rep}' has {len(levels)} zoom levels"

    def test_positions_nonempty_at_each_zoom(self):
        """At every zoom level, positions dict is non-empty."""
        nav, reps = self._get_reps()
        for rep in reps:
            for zl in nav.map_loader.get_zoom_levels(rep):
                zl_data = nav.map_loader.get_zoom_level(rep, zl)
                assert zl_data is not None, f"{rep} zoom {zl}: get_zoom_level returned None"
                assert len(zl_data.positions) > 0, (
                    f"{rep} zoom {zl}: positions is empty"
                )

    def test_cluster_assignments_nonempty_at_each_zoom(self):
        """At every zoom level, cluster_assignments dict is non-empty."""
        nav, reps = self._get_reps()
        for rep in reps:
            for zl in nav.map_loader.get_zoom_levels(rep):
                zl_data = nav.map_loader.get_zoom_level(rep, zl)
                assert len(zl_data.cluster_assignments) > 0, (
                    f"{rep} zoom {zl}: cluster_assignments is empty"
                )

    def test_clusters_nonempty_at_each_zoom(self):
        """At every zoom level, clusters dict is non-empty."""
        nav, reps = self._get_reps()
        for rep in reps:
            for zl in nav.map_loader.get_zoom_levels(rep):
                zl_data = nav.map_loader.get_zoom_level(rep, zl)
                assert len(zl_data.clusters) > 0, (
                    f"{rep} zoom {zl}: clusters dict is empty"
                )

    def test_n_decisions_matches_positions(self):
        """n_decisions equals len(positions) at every zoom level."""
        nav, reps = self._get_reps()
        for rep in reps:
            for zl in nav.map_loader.get_zoom_levels(rep):
                zl_data = nav.map_loader.get_zoom_level(rep, zl)
                assert zl_data.n_decisions == len(zl_data.positions), (
                    f"{rep} zoom {zl}: n_decisions={zl_data.n_decisions} "
                    f"!= len(positions)={len(zl_data.positions)}"
                )

    def test_cluster_sizes_sum_matches_n_decisions(self):
        """Sum of cluster sizes approx equals n_decisions (within 10%)."""
        nav, reps = self._get_reps()
        for rep in reps:
            for zl in nav.map_loader.get_zoom_levels(rep):
                zl_data = nav.map_loader.get_zoom_level(rep, zl)
                total = sum(c.size for c in zl_data.clusters.values())
                n = zl_data.n_decisions
                if n == 0:
                    continue
                ratio = total / n
                assert 0.9 <= ratio <= 1.1, (
                    f"{rep} zoom {zl}: cluster sizes sum {total} is >10% off "
                    f"n_decisions {n} (ratio={ratio:.3f})"
                )


# ---------------------------------------------------------------------------
# Default Representation
# ---------------------------------------------------------------------------

class TestDefaultRepresentation:
    """The production default representation must be cited_outcome_hybrid_0.5."""

    def test_default_is_cited_outcome_hybrid(self):
        nav = _get_nav()
        default = nav._get_default_representation()
        assert default == "cited_outcome_hybrid_0.5"

    def test_default_is_loaded(self):
        nav = _get_nav()
        default = nav._get_default_representation()
        reps = nav.map_loader.get_available_representations()
        assert default in reps, f"Default '{default}' not in loaded representations"

    def test_default_has_zoom_levels(self):
        nav = _get_nav()
        default = nav._get_default_representation()
        levels = nav.map_loader.get_zoom_levels(default)
        assert len(levels) >= 1

    def test_default_loads_in_get_map_data(self):
        nav = _get_nav()
        data = nav.get_map_data()
        assert "error" not in data, f"get_map_data() returned error: {data.get('error')}"
        assert data["representation"] == "cited_outcome_hybrid_0.5"
        assert len(data["positions"]) > 0


# ---------------------------------------------------------------------------
# COMBINATION_MODE Representation
# ---------------------------------------------------------------------------

class TestCombinationMode:
    """linear_hybrid05_concat loads with 7 zoom levels."""

    def test_combination_mode_loads(self):
        nav = _get_nav()
        reps = nav.map_loader.get_available_representations()
        assert "linear_hybrid05_concat" in reps

    def test_combination_mode_seven_zoom_levels(self):
        nav = _get_nav()
        levels = nav.map_loader.get_zoom_levels("linear_hybrid05_concat")
        assert len(levels) == 7, (
            f"linear_hybrid05_concat expected 7 zoom levels, got {len(levels)}"
        )

    def test_combination_mode_design_pattern(self):
        pattern = MapLoader.DESIGN_PATTERNS.get("linear_hybrid05_concat")
        assert pattern == "COMBINATION", f"Expected COMBINATION, got {pattern}"


# ---------------------------------------------------------------------------
# Design Pattern Coverage
# ---------------------------------------------------------------------------

class TestDesignPatternCoverage:
    """Each design pattern has at least one loaded representation."""

    EXPECTED_PATTERNS = [
        "DEFAULT",
        "LEGACY-DEFAULT",
        "HIGH-PURITY",
        "HIGH-ADVANTAGE",
        "COMBINATION",
        "CITATION-ROLE",
        "LEGACY",
    ]

    def test_all_patterns_have_representations(self):
        """Every expected design pattern has >= 1 representation in DESIGN_PATTERNS."""
        for pattern in self.EXPECTED_PATTERNS:
            matched = [name for name, pat in MapLoader.DESIGN_PATTERNS.items() if pat == pattern]
            assert len(matched) >= 1, f"Pattern '{pattern}' has no representations"

    def test_all_patterns_loaded(self):
        """Every design pattern's representations are present in loaded maps."""
        nav = _get_nav()
        loaded = set(nav.map_loader.get_available_representations())
        for pattern in self.EXPECTED_PATTERNS:
            matched = [name for name, pat in MapLoader.DESIGN_PATTERNS.items() if pat == pattern]
            for rep in matched:
                assert rep in loaded, (
                    f"Representation '{rep}' (pattern={pattern}) not in loaded maps"
                )

    def test_default_pattern_has_two_reps(self):
        """DEFAULT pattern includes both cited_outcome_hybrid variants."""
        default_reps = [
            name for name, pat in MapLoader.DESIGN_PATTERNS.items() if pat == "DEFAULT"
        ]
        assert "cited_outcome_hybrid_0.5" in default_reps
        assert "cited_outcome_hybrid_0.7" in default_reps

    def test_citation_role_pattern_has_three_reps(self):
        """CITATION-ROLE pattern includes following, criticizing, citing."""
        role_reps = [
            name for name, pat in MapLoader.DESIGN_PATTERNS.items() if pat == "CITATION-ROLE"
        ]
        assert "following_alpha0.3" in role_reps
        assert "criticizing_alpha0.3" in role_reps
        assert "citing_alpha0.3" in role_reps

    def test_high_advantage_has_seven_reps(self):
        """HIGH-ADVANTAGE pattern includes 7 representations."""
        ha_reps = [
            name for name, pat in MapLoader.DESIGN_PATTERNS.items() if pat == "HIGH-ADVANTAGE"
        ]
        assert len(ha_reps) == 7, f"Expected 7 HIGH-ADVANTAGE reps, got {len(ha_reps)}: {ha_reps}"


# ---------------------------------------------------------------------------
# Representation Purposes
# ---------------------------------------------------------------------------

class TestRepresentationPurposes:
    """Key representations have correct purpose assignments."""

    def test_production_purpose(self):
        assert MapLoader.REPRESENTATION_PURPOSES.get("cited_outcome_hybrid_0.5") == "production"

    def test_fractal_purpose(self):
        assert MapLoader.REPRESENTATION_PURPOSES.get("cited_outcome_hybrid_0.7") == "fractal_quality"

    def test_legacy_default_purpose(self):
        assert MapLoader.REPRESENTATION_PURPOSES.get("center_projected_64dim_hierarchical") == "legacy_default"

    def test_combination_purpose(self):
        assert MapLoader.REPRESENTATION_PURPOSES.get("linear_hybrid05_concat") == "best_stable_combination"

    def test_citation_purposes(self):
        assert MapLoader.REPRESENTATION_PURPOSES.get("following_alpha0.3") == "following_precedent"
        assert MapLoader.REPRESENTATION_PURPOSES.get("criticizing_alpha0.3") == "identifying_criticism"
        assert MapLoader.REPRESENTATION_PURPOSES.get("citing_alpha0.3") == "citation_network"
