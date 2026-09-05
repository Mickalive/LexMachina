"""Tests for cycle 33974964520: graceful degradation, system stats, representations health.

FEAT-078: MapLoader graceful degradation (load_selected, get_load_report, failure handling)
FEAT-079: /api/system/stats endpoint
FEAT-080: /api/representations/health endpoint
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from app.map_loader import MapLoader
from app.health_checker import RepresentationHealthChecker


# ---------------------------------------------------------------------------
# FEAT-078: MapLoader graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """MapLoader should tolerate individual representation load failures."""

    def test_repr_methods_table_complete(self):
        """_REPR_METHODS should have exactly 30 entries."""
        ml = MapLoader(Path("results/fractal_map"))
        assert len(ml._REPR_METHODS) == 30

    def test_load_failures_initially_empty(self):
        ml = MapLoader(Path("results/fractal_map"))
        assert ml._load_failures == {}

    def test_load_all_succeeds(self):
        """All 30 representations should load without failure."""
        ml = MapLoader(Path("results/fractal_map"))
        count = ml.load()
        report = ml.get_load_report()
        assert count == 30
        assert report["loaded"] == 30
        assert report["failed"] == 0
        assert report["failures"] == {}

    def test_get_available_representations(self):
        ml = MapLoader(Path("results/fractal_map"))
        ml.load()
        avail = ml.get_available_representations()
        assert len(avail) == 30

    def test_load_report_has_required_keys(self):
        ml = MapLoader(Path("results/fractal_map"))
        ml.load()
        report = ml.get_load_report()
        assert "loaded" in report
        assert "failed" in report
        assert "failures" in report
        assert "total" in report

    def test_load_report_total_matches(self):
        ml = MapLoader(Path("results/fractal_map"))
        ml.load()
        report = ml.get_load_report()
        assert report["total"] == report["loaded"] + report["failed"]

    def test_load_selected_single(self):
        """load_selected should load only named representations."""
        ml = MapLoader(Path("results/fractal_map"))
        ml.load_selected(["baseline"])
        assert "baseline" in ml.maps
        assert len(ml.maps) == 1
        assert len(ml.get_available_representations()) == 1

    def test_load_selected_multiple(self):
        ml = MapLoader(Path("results/fractal_map"))
        ml.load_selected(["baseline", "linear_hybrid05_concat"])
        assert len(ml.maps) == 2
        assert "baseline" in ml.maps
        assert "linear_hybrid05_concat" in ml.maps

    def test_load_selected_unknown_repr(self):
        """Unknown representation name should be recorded as failure, not crash."""
        ml = MapLoader(Path("results/fractal_map"))
        ml.load_selected(["nonexistent_representation_xyz"])
        report = ml.get_load_report()
        assert report["failed"] == 1
        assert "nonexistent_representation_xyz" in report["failures"]

    def test_load_selected_idempotent(self):
        """Loading same representation twice should be a no-op."""
        ml = MapLoader(Path("results/fractal_map"))
        ml.load_selected(["baseline"])
        count1 = len(ml.maps)
        ml.load_selected(["baseline"])
        count2 = len(ml.maps)
        assert count1 == count2 == 1

    def test_load_returns_cached_on_second_call(self):
        """Second call to load() should return cached count."""
        ml = MapLoader(Path("results/fractal_map"))
        count1 = ml.load()
        count2 = ml.load()
        assert count1 == count2 == 30

    def test_available_excludes_failures(self):
        """get_available_representations should not include failed loads."""
        ml = MapLoader(Path("results/fractal_map"))
        ml.load_selected(["nonexistent_xyz", "baseline"])
        avail = ml.get_available_representations()
        assert "nonexistent_xyz" not in avail
        assert "baseline" in avail


# ---------------------------------------------------------------------------
# FEAT-079+080: Server endpoints (unit test the handler methods directly)
# ---------------------------------------------------------------------------

class TestServerEndpoints:
    """Test new server endpoints via handler method invocation."""

    def test_handle_system_stats_structure(self):
        """_handle_system_stats should return expected keys."""
        from server import ProductHandler
        # Create a minimal mock handler
        handler = object.__new__(ProductHandler)
        result = handler._handle_system_stats()
        assert "uptime_seconds" in result
        assert "memory_mb" in result
        assert "representations_loaded" in result
        assert "representations_failed" in result
        assert "cache_stats" in result
        assert "rate_limit_stats" in result
        assert "corpus_decisions" in result
        assert "thread_count" in result

    def test_handle_system_stats_memory_format(self):
        """Memory should have rss and vms keys."""
        from server import ProductHandler
        handler = object.__new__(ProductHandler)
        result = handler._handle_system_stats()
        assert "rss" in result["memory_mb"]
        assert "vms" in result["memory_mb"]

    def test_handle_system_stats_representations(self):
        """Should report loaded representations correctly."""
        from server import ProductHandler
        handler = object.__new__(ProductHandler)
        result = handler._handle_system_stats()
        # All 30 should be loaded when server starts
        assert result["representations_loaded"] == 30
        assert result["representations_failed"] == 0

    def test_handle_system_stats_cache_format(self):
        from server import ProductHandler
        handler = object.__new__(ProductHandler)
        result = handler._handle_system_stats()
        cs = result["cache_stats"]
        assert "hits" in cs
        assert "misses" in cs
        assert "hit_rate" in cs
        assert "entries" in cs

    def test_handle_representations_health_structure(self):
        """_handle_representations_health should return expected keys."""
        from server import ProductHandler
        handler = object.__new__(ProductHandler)
        result = handler._handle_representations_health()
        assert "total" in result
        assert "loaded" in result
        assert "failed" in result
        assert "representations" in result

    def test_handle_representations_health_all_loaded(self):
        """All 30 representations should be reported as loaded/healthy."""
        from server import ProductHandler
        handler = object.__new__(ProductHandler)
        result = handler._handle_representations_health()
        assert result["total"] == 30
        assert result["loaded"] == 30
        assert result["failed"] == 0

    def test_handle_representations_health_per_rep(self):
        """Each representation should have status and design_pattern."""
        from server import ProductHandler
        handler = object.__new__(ProductHandler)
        result = handler._handle_representations_health()
        for rep_name, rep_info in result["representations"].items():
            assert "status" in rep_info, f"{rep_name} missing status"
            assert "design_pattern" in rep_info, f"{rep_name} missing design_pattern"
            assert rep_info["status"] in ("loaded", "healthy", "degraded", "failed")

    def test_handle_representations_health_known_reps_present(self):
        """Key representations should be present in the health report."""
        from server import ProductHandler
        handler = object.__new__(ProductHandler)
        result = handler._handle_representations_health()
        key_reps = [
            "center_projected_64dim_hierarchical",
            "cited_outcome_hybrid_0.5",
            "linear_hybrid05_concat",
            "following_alpha0.3",
            "baseline",
        ]
        for rep in key_reps:
            assert rep in result["representations"], f"{rep} missing from health report"


# ---------------------------------------------------------------------------
# Integration: graceful degradation + server endpoints coherence
# ---------------------------------------------------------------------------

class TestGracefulDegradationIntegration:
    """Verify that graceful degradation integrates with NavigationAPI."""

    def test_nav_api_loads_all(self):
        """NavigationAPI should load all 30 representations."""
        from app.navigation import NavigationAPI
        nav = NavigationAPI(
            results_dir=Path("results/fractal_map"),
            corpus_dir=Path("results/corpus/normalization/canonical"),
        )
        nav.map_loader.load()
        report = nav.map_loader.get_load_report()
        assert report["loaded"] == 30
        assert report["failed"] == 0

    def test_nav_api_get_load_report(self):
        from app.navigation import NavigationAPI
        nav = NavigationAPI(
            results_dir=Path("results/fractal_map"),
            corpus_dir=Path("results/corpus/normalization/canonical"),
        )
        nav.map_loader.load()
        report = nav.map_loader.get_load_report()
        assert report["total"] == 30
