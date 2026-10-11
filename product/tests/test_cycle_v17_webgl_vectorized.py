"""
LexMachina Product Cycle v17 — WebGL Vectorized Pipeline Tests

Tests the vectorized WebGL data preparation pipeline against real product data:
- prepare_point_data_vectorized vs prepare_point_data_for_webgl equivalence
- get_webgl_data with default representation, LOD levels, and viewport bbox culling
- End-to-end timing benchmark of the full get_webgl_data pipeline
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np
from app.navigation import NavigationAPI
from app.webgl_renderer import (
    prepare_point_data_vectorized,
    prepare_point_data_for_webgl,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_nav():
    """Get an initialized NavigationAPI for testing."""
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    nav = NavigationAPI(corpus_dir, results_dir)
    nav.initialize()
    return nav


def _sample_positions_for_webgl(nav, representation, zoom_level, max_points=5000):
    """Fetch map data and return a small slice suitable for direct renderer calls."""
    map_data = nav.get_map_data(representation=representation, zoom_level=zoom_level)
    positions = map_data.get("positions", [])
    clusters = map_data.get("clusters", [])

    COLORS = [
        '#7c8aff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8',
        '#20c997', '#ff922b', '#4dabf7', '#e599f7', '#69db7c',
        '#fcc419', '#ff8787', '#748ffc', '#63e6be', '#da77f2',
        '#a9e34b', '#ffa94d', '#74c0fc', '#b2f2bb', '#f783ac',
    ]
    LANG_COLORS = {'de': '#4dabf7', 'fr': '#ffd43b', 'it': '#51cf66', 'unknown': '#666'}
    imported_ids = set()
    transform = {}

    return positions[:max_points], clusters, LANG_COLORS, COLORS, imported_ids, transform


# ---------------------------------------------------------------------------
# Test class: Vectorized data preparation
# ---------------------------------------------------------------------------

class TestVectorizedDataPreparation:
    """Test that prepare_point_data_vectorized produces valid and equivalent output."""

    @pytest.fixture(scope="class")
    def nav(self):
        return _get_nav()

    @pytest.fixture(scope="class")
    def webgl_inputs(self, nav):
        return _sample_positions_for_webgl(
            nav,
            nav._get_default_representation(),
            zoom_level=1,
        )

    def test_vectorized_output_keys(self, webgl_inputs):
        """Vectorized output contains required keys."""
        positions, clusters, lang_colors, colors, imported_ids, transform = webgl_inputs
        result = prepare_point_data_vectorized(
            positions, clusters, lang_colors, colors, imported_ids, transform
        )
        assert "positions" in result
        assert "colors" in result
        assert "radii" in result
        assert "imported" in result
        assert "count" in result

    def test_vectorized_count_matches_input(self, webgl_inputs):
        """Count field matches the number of input positions."""
        positions, clusters, lang_colors, colors, imported_ids, transform = webgl_inputs
        result = prepare_point_data_vectorized(
            positions, clusters, lang_colors, colors, imported_ids, transform
        )
        assert result["count"] == len(positions)

    def test_vectorized_array_lengths(self, webgl_inputs):
        """Flat array lengths are consistent with point count."""
        positions, clusters, lang_colors, colors, imported_ids, transform = webgl_inputs
        n = len(positions)
        result = prepare_point_data_vectorized(
            positions, clusters, lang_colors, colors, imported_ids, transform
        )
        assert len(result["positions"]) == n * 2
        assert len(result["colors"]) == n * 4
        assert len(result["radii"]) == n
        assert len(result["imported"]) == n

    def test_vectorized_empty_input(self):
        """Vectorized path handles empty position list gracefully."""
        result = prepare_point_data_vectorized([], [], {}, [], set(), {})
        assert result["count"] == 0
        assert result["positions"] == []
        assert result["colors"] == []
        assert result["radii"] == []
        assert result["imported"] == []

    def test_vectorized_radii_values(self, webgl_inputs):
        """Radii are 4.0 (section) or 2.5 (no section), matching expected schema."""
        positions, clusters, lang_colors, colors, imported_ids, transform = webgl_inputs
        result = prepare_point_data_vectorized(
            positions, clusters, lang_colors, colors, imported_ids, transform
        )
        for r in result["radii"]:
            assert r in (4.0, 2.5), f"Unexpected radius value: {r}"

    def test_vectorized_imported_flags_zero(self, webgl_inputs):
        """With no imported IDs, all imported flags are 0."""
        positions, clusters, lang_colors, colors, imported_ids, transform = webgl_inputs
        result = prepare_point_data_vectorized(
            positions, clusters, lang_colors, colors, imported_ids, transform
        )
        assert all(v == 0.0 for v in result["imported"])

    def test_vectorized_vs_baseline_equivalence(self, webgl_inputs):
        """Vectorized and baseline produce identical arrays for the same input."""
        positions, clusters, lang_colors, colors, imported_ids, transform = webgl_inputs
        vec = prepare_point_data_vectorized(
            positions, clusters, lang_colors, colors, imported_ids, transform
        )
        base = prepare_point_data_for_webgl(
            positions, clusters, lang_colors, colors, imported_ids, transform
        )
        assert vec["count"] == base["count"]
        np.testing.assert_array_equal(vec["positions"], base["positions"])
        np.testing.assert_array_almost_equal(vec["colors"], base["colors"], decimal=5)
        np.testing.assert_array_equal(vec["radii"], base["radii"])
        np.testing.assert_array_equal(vec["imported"], base["imported"])

    def test_vectorized_equivalence_on_subset(self, nav):
        """Equivalence holds on a random 200-point subset of real data."""
        map_data = nav.get_map_data(
            representation=nav._get_default_representation(),
            zoom_level=1,
        )
        positions = map_data["positions"][:200]
        clusters = map_data["clusters"]
        COLORS = ['#7c8aff', '#ff6b6b']
        imported_ids = set()
        transform = {}

        vec = prepare_point_data_vectorized(
            positions, clusters, {}, COLORS, imported_ids, transform
        )
        base = prepare_point_data_for_webgl(
            positions, clusters, {}, COLORS, imported_ids, transform
        )
        np.testing.assert_array_equal(vec["positions"], base["positions"])
        np.testing.assert_array_equal(vec["radii"], base["radii"])
        np.testing.assert_array_equal(vec["imported"], base["imported"])


# ---------------------------------------------------------------------------
# Test class: WebGL data pipeline (integration)
# ---------------------------------------------------------------------------

class TestWebGLDataPipeline:
    """Integration tests for NavigationAPI.get_webgl_data."""

    @pytest.fixture(scope="class")
    def nav(self):
        return _get_nav()

    def test_default_representation_webgl(self, nav):
        """get_webgl_data succeeds for the default representation."""
        rep = nav._get_default_representation()
        result = nav.get_webgl_data(
            representation=rep,
            zoom_level=1,
        )
        assert "error" not in result, f"Got error: {result.get('error')}"
        assert result["points"]["count"] > 0

    def test_default_representation_webgl_structure(self, nav):
        """get_webgl_data returns expected top-level keys."""
        rep = nav._get_default_representation()
        result = nav.get_webgl_data(representation=rep, zoom_level=1)
        assert "points" in result
        assert "clusters" in result
        assert "hulls" in result
        assert "transform" in result
        pts = result["points"]
        assert "positions" in pts
        assert "colors" in pts
        assert "radii" in pts
        assert "imported" in pts
        assert "decision_ids" in pts
        assert "cluster_ids" in pts
        assert "languages" in pts
        assert "count" in pts

    def test_lod_level_0_centroid_path(self, nav):
        """LOD level 0 returns cluster centroids with reduced point count."""
        rep = nav._get_default_representation()
        full = nav.get_webgl_data(representation=rep, zoom_level=1)
        lod0 = nav.get_webgl_data(representation=rep, zoom_level=1, lod_level=0)
        assert "error" not in lod0, f"Got error: {lod0.get('error')}"
        assert lod0["points"]["count"] > 0
        assert lod0.get("lod_level") == 0
        assert lod0["points"]["count"] <= full["points"]["count"]
        # LOD 0 should have at most as many points as clusters in the full result
        assert lod0["points"]["count"] <= len(full["clusters"]) + 5

    def test_lod_level_1_super_cluster_path(self, nav):
        """LOD level 1 returns super-cluster centroids."""
        rep = nav._get_default_representation()
        full = nav.get_webgl_data(representation=rep, zoom_level=1)
        lod1 = nav.get_webgl_data(representation=rep, zoom_level=1, lod_level=1)
        assert "error" not in lod1, f"Got error: {lod1.get('error')}"
        assert lod1["points"]["count"] > 0
        assert lod1.get("lod_level") == 1
        assert lod1["points"]["count"] <= full["points"]["count"]

    def test_viewport_bbox_culling(self, nav):
        """Viewport bbox culling returns a subset of points."""
        rep = nav._get_default_representation()
        full = nav.get_webgl_data(representation=rep, zoom_level=1)
        transform = full["transform"]
        x_min, x_max = transform["xMin"], transform["xMax"]
        y_min, y_max = transform["yMin"], transform["yMax"]
        # Tight viewport around the center quarter of the data
        mid_x = (x_min + x_max) / 2.0
        mid_y = (y_min + y_max) / 2.0
        x_range = (x_max - x_min) / 4.0
        y_range = (y_max - y_min) / 4.0
        bbox = {
            "xMin": mid_x - x_range,
            "xMax": mid_x + x_range,
            "yMin": mid_y - y_range,
            "yMax": mid_y + y_range,
        }
        culled = nav.get_webgl_data(
            representation=rep, zoom_level=1, bbox=bbox
        )
        assert "error" not in culled, f"Got error: {culled.get('error')}"
        assert culled["points"]["count"] > 0
        # Culling should reduce the point count
        assert culled["points"]["count"] <= full["points"]["count"]
        # Verify viewport_culling metadata
        vc = culled.get("viewport_culling", {})
        assert vc.get("requested") is True
        assert vc.get("visible_positions") == culled["points"]["count"]

    def test_viewport_culling_positions_inside_bbox(self, nav):
        """All returned points have coordinates inside the requested bbox."""
        rep = nav._get_default_representation()
        full = nav.get_webgl_data(representation=rep, zoom_level=1)
        t = full["transform"]
        cx = (t["xMin"] + t["xMax"]) / 2.0
        cy = (t["yMin"] + t["yMax"]) / 2.0
        half = min(t["xMax"] - t["xMin"], t["yMax"] - t["yMin"]) / 4.0
        bbox = {
            "xMin": cx - half, "xMax": cx + half,
            "yMin": cy - half, "yMax": cy + half,
        }
        culled = nav.get_webgl_data(representation=rep, zoom_level=1, bbox=bbox)
        positions_flat = culled["points"]["positions"]
        n = culled["points"]["count"]
        if n > 0:
            xs = np.array(positions_flat[0::2])
            ys = np.array(positions_flat[1::2])
            assert np.all(xs >= bbox["xMin"] - 1e-6)
            assert np.all(xs <= bbox["xMax"] + 1e-6)
            assert np.all(ys >= bbox["yMin"] - 1e-6)
            assert np.all(ys <= bbox["yMax"] + 1e-6)

    def test_lod_decimation_metadata(self, nav):
        """LOD responses include lod_decimation metadata."""
        rep = nav._get_default_representation()
        lod0 = nav.get_webgl_data(representation=rep, zoom_level=1, lod_level=0)
        assert "lod_decimation" in lod0
        assert "applied" in lod0["lod_decimation"]
        assert "original_count" in lod0["lod_decimation"]
        assert "decimated_count" in lod0["lod_decimation"]

    def test_empty_positions_returns_empty(self, nav):
        """get_webgl_data with an empty-result representation returns zero count."""
        result = nav.get_webgl_data(
            representation="__nonexistent_rep__",
            zoom_level=1,
        )
        # Non-existent rep returns error or zero-count; both are acceptable
        if "error" not in result:
            assert result["points"]["count"] == 0


# ---------------------------------------------------------------------------
# Test class: Benchmark
# ---------------------------------------------------------------------------

class TestWebGLBenchmark:
    """Benchmark the full get_webgl_data pipeline on real data."""

    @pytest.fixture(scope="class")
    def nav(self):
        return _get_nav()

    def test_full_pipeline_timing(self, nav):
        """Time get_webgl_data for default representation and report."""
        rep = nav._get_default_representation()

        # Warm up (populates caches)
        nav.get_webgl_data(representation=rep, zoom_level=1)

        # Benchmark: 5 iterations
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            result = nav.get_webgl_data(representation=rep, zoom_level=1)
            t1 = time.perf_counter()
            times.append(t1 - t0)

        avg_ms = sum(times) / len(times) * 1000.0
        min_ms = min(times) * 1000.0
        max_ms = max(times) * 1000.0
        n_points = result["points"]["count"]

        # Sanity: pipeline must produce output
        assert n_points > 0
        # Performance: average must be under 2 seconds for the full pipeline
        assert avg_ms < 2000.0, (
            f"Average get_webgl_data latency {avg_ms:.1f}ms exceeds 2000ms budget "
            f"({n_points} points)"
        )

        # Print benchmark summary (visible in pytest -v output)
        print(
            f"\n  [BENCHMARK] get_webgl_data ({n_points} pts, cached): "
            f"avg={avg_ms:.1f}ms  min={min_ms:.1f}ms  max={max_ms:.1f}ms"
        )

    def test_lod0_timing(self, nav):
        """Time LOD-0 path and report."""
        rep = nav._get_default_representation()
        nav.get_webgl_data(representation=rep, zoom_level=1, lod_level=0)

        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            result = nav.get_webgl_data(representation=rep, zoom_level=1, lod_level=0)
            t1 = time.perf_counter()
            times.append(t1 - t0)

        avg_ms = sum(times) / len(times) * 1000.0
        n_points = result["points"]["count"]
        assert n_points > 0

        print(
            f"\n  [BENCHMARK] LOD-0 ({n_points} pts): avg={avg_ms:.1f}ms"
        )

    def test_viewport_culling_timing(self, nav):
        """Time viewport-culled get_webgl_data and report."""
        rep = nav._get_default_representation()
        full = nav.get_webgl_data(representation=rep, zoom_level=1)
        t = full["transform"]
        cx = (t["xMin"] + t["xMax"]) / 2.0
        cy = (t["yMin"] + t["yMax"]) / 2.0
        half = min(t["xMax"] - t["xMin"], t["yMax"] - t["yMin"]) / 4.0
        bbox = {
            "xMin": cx - half, "xMax": cx + half,
            "yMin": cy - half, "yMax": cy + half,
        }

        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            result = nav.get_webgl_data(
                representation=rep, zoom_level=1, bbox=bbox
            )
            t1 = time.perf_counter()
            times.append(t1 - t0)

        avg_ms = sum(times) / len(times) * 1000.0
        n_points = result["points"]["count"]
        assert n_points > 0

        print(
            f"\n  [BENCHMARK] viewport-culled ({n_points} pts): avg={avg_ms:.1f}ms"
        )

    def test_vectorized_vs_baseline_speedup(self, nav):
        """Measure vectorized vs baseline renderer on the same input."""
        positions, clusters, lang_colors, colors, imported_ids, transform = (
            _sample_positions_for_webgl(
                nav, nav._get_default_representation(), zoom_level=1, max_points=5000
            )
        )

        iters = 3

        t0 = time.perf_counter()
        for _ in range(iters):
            prepare_point_data_for_webgl(
                positions, clusters, lang_colors, colors, imported_ids, transform
            )
        baseline_total = time.perf_counter() - t0

        t0 = time.perf_counter()
        for _ in range(iters):
            prepare_point_data_vectorized(
                positions, clusters, lang_colors, colors, imported_ids, transform
            )
        vectorized_total = time.perf_counter() - t0

        baseline_avg = baseline_total / iters * 1000.0
        vectorized_avg = vectorized_total / iters * 1000.0
        speedup = baseline_avg / vectorized_avg if vectorized_avg > 0 else float("inf")

        print(
            f"\n  [BENCHMARK] baseline={baseline_avg:.1f}ms  "
            f"vectorized={vectorized_avg:.1f}ms  speedup={speedup:.2f}x "
            f"(n={len(positions)})"
        )

        # Vectorized should be no slower than 2x baseline
        assert vectorized_avg <= baseline_avg * 2.0 + 1.0, (
            f"Vectorized ({vectorized_avg:.1f}ms) is >2x slower than baseline "
            f"({baseline_avg:.1f}ms) on {len(positions)} points"
        )
