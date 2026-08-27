"""
LexMachina Product Tests — Cycle 33035450227
Tests for scaled section projections, evaluation loader, temporal filtering,
and updated section modes with scaled support.
"""
import sys
import json
import numpy as np
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_DIR = Path(__file__).parent.parent / "results" / "fractal_map"
SCALED_DIR = RESULTS_DIR / "section_scaled"
SECTION_CLEAN_DIR = RESULTS_DIR / "section_experiment_clean"
CORPUS_DIR = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"

SECTION_MODES = [
    "sachverhalt",
    "erwaegungen",
    "dispositiv",
    "full_text",
    "erwaegungen_dispositiv",
    "sachverhalt_erwaegungen_dispositiv",
]


class TestScaledSectionProjections:
    """Tests for the scaled section projection files and metadata."""

    def test_scaled_directory_exists(self):
        """Verify the section_scaled output directory exists."""
        assert SCALED_DIR.exists(), f"Scaled directory not found: {SCALED_DIR}"
        print("  PASS: section_scaled/ directory exists")

    def test_metadata_json_exists(self):
        """Verify metadata.json exists and is valid JSON."""
        meta_path = SCALED_DIR / "metadata.json"
        assert meta_path.exists(), f"metadata.json not found in {SCALED_DIR}"
        with open(meta_path) as f:
            meta = json.load(f)
        assert isinstance(meta, dict), "metadata.json should be a dict"
        print("  PASS: metadata.json exists and is valid JSON")

    def test_metadata_total_decisions(self):
        """Verify metadata reports 1000 total decisions."""
        with open(SCALED_DIR / "metadata.json") as f:
            meta = json.load(f)
        assert meta["total_decisions"] == 1000, (
            f"Expected 1000 total decisions, got {meta['total_decisions']}"
        )
        print("  PASS: total_decisions = 1000")

    def test_metadata_section_covered_decisions(self):
        """Verify metadata reports 63 section-covered decisions."""
        with open(SCALED_DIR / "metadata.json") as f:
            meta = json.load(f)
        assert meta["section_covered_decisions"] == 63, (
            f"Expected 63 section-covered decisions, got {meta['section_covered_decisions']}"
        )
        print("  PASS: section_covered_decisions = 63")

    def test_metadata_section_modes_present(self):
        """Verify all 6 section modes are listed in metadata."""
        with open(SCALED_DIR / "metadata.json") as f:
            meta = json.load(f)
        modes = meta["section_modes"]
        for mode_name in SECTION_MODES:
            assert mode_name in modes, f"Section mode '{mode_name}' missing from metadata"
        assert len(modes) == 6, f"Expected 6 section modes, got {len(modes)}"
        print("  PASS: all 6 section modes present in metadata")

    def test_metadata_coverage_stats(self):
        """Verify per-mode coverage stats (63 section, 937 baseline, 6.3%)."""
        with open(SCALED_DIR / "metadata.json") as f:
            meta = json.load(f)
        for mode_name in SECTION_MODES:
            stats = meta["section_modes"][mode_name]
            assert stats["total_decisions"] == 1000, (
                f"{mode_name}: expected 1000 total, got {stats['total_decisions']}"
            )
            assert stats["section_decisions"] == 63, (
                f"{mode_name}: expected 63 section, got {stats['section_decisions']}"
            )
            assert stats["baseline_fallback"] == 937, (
                f"{mode_name}: expected 937 baseline, got {stats['baseline_fallback']}"
            )
            assert stats["coverage_pct"] == 6.3, (
                f"{mode_name}: expected 6.3% coverage, got {stats['coverage_pct']}"
            )
        print("  PASS: per-mode coverage stats correct (63/937/6.3%)")

    def test_metadata_decision_provenance(self):
        """Verify provenance array has 1000 entries with section/baseline sources."""
        with open(SCALED_DIR / "metadata.json") as f:
            meta = json.load(f)
        prov = meta["decision_provenance"]
        assert len(prov) == 1000, f"Expected 1000 provenance entries, got {len(prov)}"
        sources = {p["source"] for p in prov}
        assert sources == {"section_projection", "baseline"}, (
            f"Unexpected sources: {sources}"
        )
        n_section = sum(1 for p in prov if p["source"] == "section_projection")
        n_baseline = sum(1 for p in prov if p["source"] == "baseline")
        assert n_section == 63, f"Expected 63 section_projection, got {n_section}"
        assert n_baseline == 937, f"Expected 937 baseline, got {n_baseline}"
        print("  PASS: provenance has 1000 entries (63 section + 937 baseline)")

    @pytest.mark.parametrize("mode_name", SECTION_MODES)
    def test_projection_file_exists(self, mode_name):
        """Verify each section mode projection file exists."""
        proj_path = SCALED_DIR / f"projection_{mode_name}.npy"
        assert proj_path.exists(), f"Projection file missing: {proj_path}"
        print(f"  PASS: projection_{mode_name}.npy exists")

    @pytest.mark.parametrize("mode_name", SECTION_MODES)
    def test_projection_shape(self, mode_name):
        """Verify each projection has shape (1000, 2)."""
        proj = np.load(SCALED_DIR / f"projection_{mode_name}.npy")
        assert proj.shape == (1000, 2), (
            f"{mode_name}: expected shape (1000, 2), got {proj.shape}"
        )
        print(f"  PASS: projection_{mode_name}.npy shape = {proj.shape}")

    @pytest.mark.parametrize("mode_name", SECTION_MODES)
    def test_projection_dtype(self, mode_name):
        """Verify projection arrays are numeric (float)."""
        proj = np.load(SCALED_DIR / f"projection_{mode_name}.npy")
        assert np.issubdtype(proj.dtype, np.floating), (
            f"{mode_name}: expected float dtype, got {proj.dtype}"
        )
        print(f"  PASS: projection_{mode_name}.npy dtype = {proj.dtype}")

    def test_baseline_projection_exists(self):
        """Verify the baseline projection was copied to section_scaled."""
        baseline_path = SCALED_DIR / "projection_baseline.npy"
        assert baseline_path.exists(), f"Baseline projection missing: {baseline_path}"
        proj = np.load(baseline_path)
        assert proj.shape == (1000, 2), (
            f"Baseline: expected shape (1000, 2), got {proj.shape}"
        )
        print("  PASS: projection_baseline.npy exists with shape (1000, 2)")

    def test_section_metadata_copy_exists(self):
        """Verify section_metadata.json was copied from section_experiment_clean."""
        sec_meta_path = SCALED_DIR / "section_metadata.json"
        assert sec_meta_path.exists(), f"section_metadata.json missing: {sec_meta_path}"
        with open(sec_meta_path) as f:
            sec_meta = json.load(f)
        assert isinstance(sec_meta, list), "section_metadata.json should be a list"
        assert len(sec_meta) == 63, (
            f"Expected 63 section metadata entries, got {len(sec_meta)}"
        )
        print("  PASS: section_metadata.json has 63 entries")

    def test_projections_not_all_zeros(self):
        """Verify that section-scaled projections differ from zero (are meaningful)."""
        baseline = np.load(SCALED_DIR / "projection_baseline.npy")
        for mode_name in SECTION_MODES:
            proj = np.load(SCALED_DIR / f"projection_{mode_name}.npy")
            # At least some positions should differ from baseline (section decisions)
            diff = np.abs(proj - baseline).sum()
            assert diff > 0, (
                f"{mode_name}: projection is identical to baseline, "
                "expected section decisions to differ"
            )
        print("  PASS: all section projections differ from baseline (section positions blended)")


class TestEvaluationLoader:
    """Tests for the EvaluationLoader class."""

    def test_loader_instantiation(self):
        """Verify EvaluationLoader can be instantiated."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        assert loader is not None
        print("  PASS: EvaluationLoader instantiated")

    def test_loader_loads_unified_data(self):
        """Verify load() succeeds when unified_results.json exists."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        result = loader.load()
        assert result is True, "load() should return True when unified data found"
        assert loader._unified_data is not None, "Unified data should be loaded"
        print("  PASS: unified evaluation data loaded")

    def test_loader_loads_zoom_coherence(self):
        """Verify zoom_coherence_results.json is loaded."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        loader.load()
        assert loader._zoom_coherence_data is not None, (
            "Zoom coherence data should be loaded"
        )
        print("  PASS: zoom coherence data loaded")

    def test_benchmarks_required_fields(self):
        """Verify get_benchmarks() returns all required fields."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        loader.load()
        benchmarks = loader.get_benchmarks()

        required_fields = [
            "best_representation",
            "zoom_coherence_improvement_rate",
            "best_fine_ratio",
            "flat_baseline_best_ratio",
            "fine_vs_baseline_delta",
            "boilerplate_resistance",
            "language_dominance_warnings",
            "total_representations_evaluated",
            "resolutions_tested",
        ]
        for field in required_fields:
            assert field in benchmarks, f"Missing required field: {field}"
        print("  PASS: all required benchmark fields present")

    def test_best_representation_valid(self):
        """Verify best_representation has name, ratio, and resolution."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        loader.load()
        best = loader.get_benchmarks()["best_representation"]
        assert best["name"] is not None, "Best representation name should not be None"
        assert isinstance(best["ratio"], (int, float)), "Ratio should be numeric"
        assert best["ratio"] > 0, "Best ratio should be > 0"
        assert best["resolution"] is not None, "Resolution should not be None"
        print(f"  PASS: best representation = {best['name']} "
              f"(ratio={best['ratio']:.4f}, res={best['resolution']})")

    def test_zoom_coherence_metrics(self):
        """Verify zoom coherence metrics are sensible."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        loader.load()
        benchmarks = loader.get_benchmarks()
        assert 0 <= benchmarks["zoom_coherence_improvement_rate"] <= 1, (
            f"Improvement rate out of range: {benchmarks['zoom_coherence_improvement_rate']}"
        )
        assert benchmarks["best_fine_ratio"] > 0, "Best fine ratio should be > 0"
        assert benchmarks["flat_baseline_best_ratio"] > 0, (
            "Flat baseline best ratio should be > 0"
        )
        print(f"  PASS: zoom coherence metrics valid "
              f"(improvement_rate={benchmarks['zoom_coherence_improvement_rate']:.3f}, "
              f"fine_ratio={benchmarks['best_fine_ratio']:.3f})")

    def test_resolutions_tested(self):
        """Verify resolutions_tested is a non-empty list."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        loader.load()
        resolutions = loader.get_benchmarks()["resolutions_tested"]
        assert isinstance(resolutions, list), "resolutions_tested should be a list"
        assert len(resolutions) > 0, "resolutions_tested should not be empty"
        print(f"  PASS: resolutions_tested = {resolutions}")

    def test_representation_quality(self):
        """Verify get_representation_quality() returns per-rep metrics."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        loader.load()
        quality = loader.get_representation_quality()
        assert isinstance(quality, dict), "Quality should be a dict"
        assert len(quality) > 0, "Should have at least one representation"
        for rep_name, rep_data in quality.items():
            assert "best_ratio" in rep_data, f"{rep_name} missing best_ratio"
            assert "best_resolution" in rep_data, f"{rep_name} missing best_resolution"
            assert "resolutions" in rep_data, f"{rep_name} missing resolutions"
        print(f"  PASS: representation quality for {len(quality)} representations")

    def test_boilerplate_resistance(self):
        """Verify boilerplate resistance scores are computed."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        loader.load()
        benchmarks = loader.get_benchmarks()
        bp = benchmarks["boilerplate_resistance"]
        assert isinstance(bp, dict), "Boilerplate resistance should be a dict"
        assert len(bp) > 0, "Should have boilerplate resistance for at least one rep"
        print(f"  PASS: boilerplate resistance for {len(bp)} representations")

    def test_not_loaded_returns_error(self):
        """Verify get_benchmarks returns error when not loaded."""
        from app.evaluation_loader import EvaluationLoader
        loader = EvaluationLoader(str(RESULTS_DIR))
        # Do NOT call load()
        result = loader.get_benchmarks()
        assert "error" in result, "Should return error when not loaded"
        print("  PASS: not-loaded state returns error")


class TestTemporalFiltering:
    """Tests for NavigationAPI.get_temporal_map_data()."""

    @pytest.fixture(autouse=True)
    def setup_api(self):
        """Initialize NavigationAPI for temporal tests."""
        from app.navigation import NavigationAPI
        self.api = NavigationAPI(str(CORPUS_DIR), str(RESULTS_DIR))
        self.api.initialize()

    def test_temporal_no_filter(self):
        """Verify get_temporal_map_data without filters returns all positions."""
        data = self.api.get_temporal_map_data("concat_center_tfidf", 1)
        assert "positions" in data, "Missing positions"
        assert "temporal_stats" in data, "Missing temporal_stats"
        assert data["temporal_stats"]["filtered_positions"] > 0, (
            "Should have filtered positions"
        )
        total = data["temporal_stats"]["total_positions"]
        assert total > 0, "Should have total positions"
        print(f"  PASS: no filter -> {total} positions")

    def test_temporal_with_year_range(self):
        """Verify filtering by year range returns subset."""
        data = self.api.get_temporal_map_data(
            "concat_center_tfidf", 1, year_start=2023, year_end=2024
        )
        assert data["temporal_stats"]["filtered_positions"] > 0, (
            "Should have positions in 2023-2024"
        )
        assert data["temporal_stats"]["filter_applied"]["year_start"] == 2023
        assert data["temporal_stats"]["filter_applied"]["year_end"] == 2024
        # All returned positions should be within the range
        for pos in data["positions"]:
            year = pos.get("year")
            if year is not None:
                assert 2023 <= year <= 2024, (
                    f"Position {pos['decision_id']} has year {year} outside 2023-2024"
                )
        print(f"  PASS: 2023-2024 filter -> {data['temporal_stats']['filtered_positions']} positions")

    def test_temporal_year_start_only(self):
        """Verify filtering with only year_start."""
        data = self.api.get_temporal_map_data(
            "concat_center_tfidf", 1, year_start=2024
        )
        for pos in data["positions"]:
            year = pos.get("year")
            if year is not None:
                assert year >= 2024, (
                    f"Position {pos['decision_id']} has year {year} < 2024"
                )
        print(f"  PASS: year_start=2024 -> {data['temporal_stats']['filtered_positions']} positions")

    def test_temporal_year_end_only(self):
        """Verify filtering with only year_end."""
        data = self.api.get_temporal_map_data(
            "concat_center_tfidf", 1, year_end=2022
        )
        for pos in data["positions"]:
            year = pos.get("year")
            if year is not None:
                assert year <= 2022, (
                    f"Position {pos['decision_id']} has year {year} > 2022"
                )
        print(f"  PASS: year_end=2022 -> {data['temporal_stats']['filtered_positions']} positions")

    def test_temporal_narrow_range(self):
        """Verify a narrow year range returns fewer positions."""
        all_data = self.api.get_temporal_map_data("concat_center_tfidf", 1)
        narrow_data = self.api.get_temporal_map_data(
            "concat_center_tfidf", 1, year_start=2024, year_end=2024
        )
        assert narrow_data["temporal_stats"]["filtered_positions"] <= all_data["temporal_stats"]["filtered_positions"], (
            "Narrow range should have <= positions than unfiltered"
        )
        print(f"  PASS: narrow range (2024) -> "
              f"{narrow_data['temporal_stats']['filtered_positions']} <= "
              f"{all_data['temporal_stats']['filtered_positions']} total")

    def test_temporal_year_distribution(self):
        """Verify year_distribution is computed."""
        data = self.api.get_temporal_map_data("concat_center_tfidf", 1)
        yd = data["temporal_stats"]["year_distribution"]
        assert isinstance(yd, dict), "year_distribution should be a dict"
        assert len(yd) > 0, "Should have at least one year"
        total_from_dist = sum(yd.values())
        assert total_from_dist == data["temporal_stats"]["filtered_positions"], (
            "Year distribution sum should equal filtered_positions"
        )
        print(f"  PASS: year distribution = {dict(sorted(yd.items()))}")

    def test_temporal_year_range_stats(self):
        """Verify year_range min/max are computed."""
        data = self.api.get_temporal_map_data("concat_center_tfidf", 1)
        yr = data["temporal_stats"]["year_range"]
        assert yr["min"] is not None, "year_range min should not be None"
        assert yr["max"] is not None, "year_range max should not be None"
        assert yr["min"] <= yr["max"], "min should be <= max"
        print(f"  PASS: year range = {yr['min']}-{yr['max']}")

    def test_temporal_has_year_field(self):
        """Verify each position includes a year field."""
        data = self.api.get_temporal_map_data("concat_center_tfidf", 1)
        for pos in data["positions"]:
            assert "year" in pos, f"Position {pos['decision_id']} missing 'year' field"
        print(f"  PASS: all {len(data['positions'])} positions have 'year' field")

    def test_temporal_clusters_from_filtered(self):
        """Verify clusters are built from the filtered subset."""
        data = self.api.get_temporal_map_data(
            "concat_center_tfidf", 1, year_start=2024, year_end=2024
        )
        assert "clusters" in data, "Missing clusters"
        cluster_ids = {c["cluster_id"] for c in data["clusters"]}
        for pos in data["positions"]:
            cid = pos["cluster"]
            if cid >= 0:
                assert cid in cluster_ids, (
                    f"Position {pos['decision_id']} references cluster {cid} not in summaries"
                )
        print(f"  PASS: {len(data['clusters'])} clusters from filtered subset")

    def test_temporal_empty_range(self):
        """Verify a range with no matching decisions returns empty positions."""
        data = self.api.get_temporal_map_data(
            "concat_center_tfidf", 1, year_start=1900, year_end=1901
        )
        assert data["temporal_stats"]["filtered_positions"] == 0, (
            "No decisions should match 1900-1901"
        )
        assert len(data["positions"]) == 0, "Positions should be empty"
        print("  PASS: empty range (1900-1901) returns 0 positions")


class TestSectionModes:
    """Tests for SectionModeLoader with scaled projection support."""

    @pytest.fixture(autouse=True)
    def setup_loader(self):
        """Initialize SectionModeLoader."""
        from app.section_modes import SectionModeLoader
        self.loader = SectionModeLoader(
            section_dir=str(SCALED_DIR),
            fallback_dir=str(SECTION_CLEAN_DIR),
        )
        self.loader.load()

    def test_modes_loaded(self):
        """Verify at least some section modes loaded."""
        assert len(self.loader.modes) > 0, "Should load at least one section mode"
        print(f"  PASS: {len(self.loader.modes)} section modes loaded")

    def test_all_six_modes_loaded(self):
        """Verify all 6 section modes are loaded."""
        for mode_name in SECTION_MODES:
            assert mode_name in self.loader.modes, (
                f"Section mode '{mode_name}' not loaded"
            )
        print("  PASS: all 6 section modes loaded")

    def test_scaled_detection(self):
        """Verify the loader detects scaled projections (section_scaled/)."""
        assert self.loader._is_scaled is True, (
            "Should detect scaled projections from section_scaled/"
        )
        assert self.loader._source_label == "section_scaled", (
            f"Source label should be 'section_scaled', got '{self.loader._source_label}'"
        )
        print("  PASS: scaled projection detection works")

    def test_total_decisions_1000(self):
        """Verify each mode reports 1000 total decisions."""
        for mode_name, mode in self.loader.modes.items():
            assert mode.n_decisions == 1000, (
                f"{mode_name}: expected 1000 total, got {mode.n_decisions}"
            )
        print("  PASS: all modes report 1000 total decisions")

    def test_section_decision_count(self):
        """Verify each mode reports 63 section decisions."""
        for mode_name, mode in self.loader.modes.items():
            assert mode.n_section_decisions == 63, (
                f"{mode_name}: expected 63 section decisions, got {mode.n_section_decisions}"
            )
        print("  PASS: all modes report 63 section decisions")

    def test_baseline_decision_count(self):
        """Verify each mode reports 937 baseline fallback decisions."""
        for mode_name, mode in self.loader.modes.items():
            assert mode.n_baseline_decisions == 937, (
                f"{mode_name}: expected 937 baseline, got {mode.n_baseline_decisions}"
            )
        print("  PASS: all modes report 937 baseline decisions")

    def test_position_count_per_mode(self):
        """Verify each mode has exactly 1000 positions."""
        for mode_name, mode in self.loader.modes.items():
            assert len(mode.positions) == 1000, (
                f"{mode_name}: expected 1000 positions, got {len(mode.positions)}"
            )
        print("  PASS: all modes have 1000 positions")

    @pytest.mark.parametrize("mode_name", SECTION_MODES)
    def test_mode_label_and_description(self, mode_name):
        """Verify each mode has a label and description."""
        mode = self.loader.get_mode(mode_name)
        assert mode is not None, f"Mode {mode_name} not found"
        assert len(mode.label) > 0, f"{mode_name}: label is empty"
        assert len(mode.description) > 0, f"{mode_name}: description is empty"
        print(f"  PASS: {mode_name} label='{mode.label}'")

    def test_get_available_modes(self):
        """Verify get_available_modes() returns complete metadata."""
        modes = self.loader.get_available_modes()
        assert len(modes) == 6, f"Expected 6 available modes, got {len(modes)}"
        for mode_info in modes:
            assert "name" in mode_info, "Missing 'name'"
            assert "label" in mode_info, "Missing 'label'"
            assert "description" in mode_info, "Missing 'description'"
            assert "n_decisions" in mode_info, "Missing 'n_decisions'"
            assert "n_section_decisions" in mode_info, "Missing 'n_section_decisions'"
            assert "n_baseline_decisions" in mode_info, "Missing 'n_baseline_decisions'"
            assert "coverage" in mode_info, "Missing 'coverage'"
            assert "source" in mode_info, "Missing 'source'"
        print("  PASS: get_available_modes() returns complete metadata for all 6 modes")

    def test_coverage_string(self):
        """Verify coverage string indicates section-specific projections."""
        modes = self.loader.get_available_modes()
        for mode_info in modes:
            coverage = mode_info["coverage"]
            assert "63" in coverage, (
                f"{mode_info['name']}: coverage string should mention 63, got '{coverage}'"
            )
            assert "1000" in coverage, (
                f"{mode_info['name']}: coverage string should mention 1000, got '{coverage}'"
            )
        print("  PASS: coverage strings mention 63 of 1000")

    def test_get_positions(self):
        """Verify get_positions returns dict of (x, y) tuples."""
        for mode_name in SECTION_MODES:
            positions = self.loader.get_positions(mode_name)
            assert isinstance(positions, dict), f"{mode_name}: positions should be dict"
            assert len(positions) == 1000, (
                f"{mode_name}: expected 1000 positions, got {len(positions)}"
            )
            # Spot-check first position
            first_did = list(positions.keys())[0]
            pos = positions[first_did]
            assert isinstance(pos, tuple) and len(pos) == 2, (
                f"{mode_name}: position should be (x, y) tuple"
            )
        print("  PASS: get_positions returns correct data for all modes")

    def test_get_position_details(self):
        """Verify get_position_details includes has_section_data flag."""
        for mode_name in SECTION_MODES:
            details = self.loader.get_position_details(mode_name)
            assert len(details) == 1000, (
                f"{mode_name}: expected 1000 details, got {len(details)}"
            )
            for did, info in details.items():
                assert "has_section_data" in info, (
                    f"{mode_name}/{did}: missing has_section_data"
                )
                assert "x" in info and "y" in info, (
                    f"{mode_name}/{did}: missing x/y coordinates"
                )
        print("  PASS: get_position_details has has_section_data for all positions")

    def test_mode_names_match_modes_list(self):
        """Verify loaded mode names match the SECTION_NAMES constant."""
        from app.section_modes import SectionModeLoader
        loaded = set(self.loader.modes.keys())
        expected = set(SectionModeLoader.SECTION_NAMES)
        assert loaded == expected, (
            f"Mismatch: loaded={loaded}, expected={expected}"
        )
        print("  PASS: loaded modes match SECTION_NAMES constant")

    def test_get_mode_returns_section_mode(self):
        """Verify get_mode returns a SectionMode dataclass."""
        from app.section_modes import SectionMode
        for mode_name in SECTION_MODES:
            mode = self.loader.get_mode(mode_name)
            assert isinstance(mode, SectionMode), (
                f"{mode_name}: expected SectionMode, got {type(mode)}"
            )
        print("  PASS: get_mode returns SectionMode for all modes")

    def test_get_mode_invalid_returns_none(self):
        """Verify get_mode with invalid name returns None."""
        result = self.loader.get_mode("nonexistent_mode")
        assert result is None, "Should return None for invalid mode"
        print("  PASS: invalid mode returns None")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
