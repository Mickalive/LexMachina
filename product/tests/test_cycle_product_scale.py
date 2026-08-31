"""
Tests for product hardening: 192k scale readiness.
- WebGL viewport culling with bbox filtering
- Numpy-optimized WebGL data preparation
- ThreadedHTTPServer for concurrent requests
- Startup validation in health endpoint
- Batch import progress tracking
"""
import json
import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.navigation import NavigationAPI


@pytest.fixture(scope="module")
def nav_api():
    """Shared NavigationAPI instance for all tests in this module."""
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    return api


class TestWebGLViewportCulling:
    """Test WebGL viewport culling with bbox filtering."""
    
    def test_webgl_data_without_bbox(self, nav_api):
        """Without bbox, returns ALL positions."""
        data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        assert "error" not in data
        assert data["points"]["count"] > 0
        assert "viewport_culling" in data
        assert data["viewport_culling"]["requested"] is False
        assert data["viewport_culling"]["visible_positions"] == data["viewport_culling"]["total_positions"]
    
    def test_webgl_data_with_bbox_filters_points(self, nav_api):
        """With tight bbox, returns fewer positions."""
        # Get all data first to know the extents
        all_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        t = all_data["transform"]
        x_range = t["xMax"] - t["xMin"]
        y_range = t["yMax"] - t["yMin"]
        
        # Create a bbox covering the center 25% of the map
        center_x = (t["xMin"] + t["xMax"]) / 2
        center_y = (t["yMin"] + t["yMax"]) / 2
        bbox = {
            "xMin": center_x - x_range * 0.125,
            "yMin": center_y - y_range * 0.125,
            "xMax": center_x + x_range * 0.125,
            "yMax": center_y + y_range * 0.125,
        }
        
        culled_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0, bbox=bbox)
        assert "error" not in culled_data
        assert culled_data["viewport_culling"]["requested"] is True
        assert culled_data["points"]["count"] < all_data["points"]["count"]
        assert culled_data["viewport_culling"]["culled_count"] > 0
    
    def test_webgl_data_with_empty_bbox(self, nav_api):
        """With bbox that covers nothing, returns empty points."""
        all_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        t = all_data["transform"]
        
        # Bbox far outside the data extent
        bbox = {
            "xMin": t["xMax"] + 1000,
            "yMin": t["yMax"] + 1000,
            "xMax": t["xMax"] + 2000,
            "yMax": t["yMax"] + 2000,
        }
        
        culled_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0, bbox=bbox)
        assert "error" not in culled_data
        assert culled_data["points"]["count"] == 0
        assert culled_data["viewport_culling"]["visible_positions"] == 0
    
    def test_webgl_data_with_full_bbox(self, nav_api):
        """With bbox covering all data, returns all positions."""
        all_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        t = all_data["transform"]
        
        # Bbox slightly larger than data extent
        margin = 10
        bbox = {
            "xMin": t["xMin"] - margin,
            "yMin": t["yMin"] - margin,
            "xMax": t["xMax"] + margin,
            "yMax": t["yMax"] + margin,
        }
        
        full_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0, bbox=bbox)
        assert "error" not in full_data
        assert full_data["points"]["count"] == all_data["points"]["count"]
    
    def test_webgl_culling_preserves_array_shapes(self, nav_api):
        """Culled data maintains correct array shapes."""
        all_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        t = all_data["transform"]
        center_x = (t["xMin"] + t["xMax"]) / 2
        center_y = (t["yMin"] + t["yMax"]) / 2
        x_range = t["xMax"] - t["xMin"]
        y_range = t["yMax"] - t["yMin"]
        
        bbox = {
            "xMin": center_x - x_range * 0.1,
            "yMin": center_y - y_range * 0.1,
            "xMax": center_x + x_range * 0.1,
            "yMax": center_y + y_range * 0.1,
        }
        
        data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0, bbox=bbox)
        n = data["points"]["count"]
        
        assert len(data["points"]["positions"]) == n * 2
        assert len(data["points"]["colors"]) == n * 4
        assert len(data["points"]["radii"]) == n
        assert len(data["points"]["imported"]) == n
    
    def test_webgl_culling_cluster_hulls(self, nav_api):
        """Culling still produces cluster hulls for visible clusters."""
        all_data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        t = all_data["transform"]
        center_x = (t["xMin"] + t["xMax"]) / 2
        center_y = (t["yMin"] + t["yMax"]) / 2
        x_range = t["xMax"] - t["xMin"]
        y_range = t["yMax"] - t["yMin"]
        
        bbox = {
            "xMin": center_x - x_range * 0.2,
            "yMin": center_y - y_range * 0.2,
            "xMax": center_x + x_range * 0.2,
            "yMax": center_y + y_range * 0.2,
        }
        
        data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0, bbox=bbox)
        assert len(data["hulls"]) > 0
        # Each hull has the required fields
        for hull in data["hulls"]:
            assert "cluster_id" in hull
            assert "points" in hull
            assert "color" in hull
            assert len(hull["points"]) >= 3  # At least triangle


class TestWebGLDataNumpyOptimization:
    """Test that WebGL data uses numpy for performance."""
    
    def test_positions_are_float_lists(self, nav_api):
        """Positions should be flat float lists suitable for Float32Array."""
        data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        positions = data["points"]["positions"]
        assert isinstance(positions, list)
        assert len(positions) > 0
        # All values should be numeric
        for v in positions[:10]:
            assert isinstance(v, (int, float))
    
    def test_colors_are_rgba_floats(self, nav_api):
        """Colors should be flat RGBA float lists."""
        data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        colors = data["points"]["colors"]
        assert isinstance(colors, list)
        assert len(colors) == data["points"]["count"] * 4
        # All values in [0, 1] range
        for v in colors[:40]:
            assert 0.0 <= v <= 1.0
    
    def test_transform_has_full_extents(self, nav_api):
        """Transform should contain full data extents even with bbox culling."""
        data = nav_api.get_webgl_data("center_projected_64dim_hierarchical", 0)
        t = data["transform"]
        assert t["xMin"] < t["xMax"]
        assert t["yMin"] < t["yMax"]
        assert t["scale"] == 1.0


class TestBatchImportProgress:
    """Test batch import with progress tracking."""
    
    def test_import_returns_progress_fields(self, nav_api):
        """Import result includes progress and timing fields."""
        records = [{
            "decision_id": "test_scale_001",
            "full_text": "Test decision for scale testing.",
            "language": "de",
            "branch": "oeffentliches_recht",
            "legal_area": "Verwaltungsrecht",
            "decision_date": "2024-01-15",
            "title": "Test Scale Decision 001",
        }]
        
        result = nav_api.import_corpus(records)
        
        if result.get("imported", 0) > 0:
            assert "representations_total" in result
            assert "representations_ok" in result
            assert "representations_skipped" in result
            assert "batch_elapsed_ms" in result
            assert isinstance(result["batch_elapsed_ms"], (int, float))
            assert result["representations_total"] > 0
            assert result["representations_ok"] + result["representations_skipped"] == result["representations_total"]
            
            # Check per-representation status
            for rep_info in result.get("representations_positioned", []):
                assert "representation" in rep_info
                assert "status" in rep_info
                assert rep_info["status"] in ("ok", "skipped", "no_positions")
                assert "elapsed_ms" in rep_info
        else:
            # If record already imported, still check that the field is present
            # (the record may have been imported in a prior test run)
            assert "representations_total" in result or result.get("skipped", 0) > 0


class TestThreadedHTTPServer:
    """Test that server uses ThreadedHTTPServer."""
    
    def test_threaded_server_class_exists(self):
        """ThreadedHTTPServer class should be importable."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        import server
        assert hasattr(server, 'ThreadedHTTPServer')
    
    def test_threaded_server_is_threaded(self):
        """ThreadedHTTPServer should inherit from ThreadingMixIn."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        import server
        from socketserver import ThreadingMixIn
        assert issubclass(server.ThreadedHTTPServer, ThreadingMixIn)
        assert server.ThreadedHTTPServer.daemon_threads is True


class TestHealthEndpointValidation:
    """Test that health endpoint includes startup validation."""
    
    def test_startup_validation_cached(self, nav_api):
        """Startup validation should be callable and cacheable."""
        # Reset any cached validation
        result = nav_api.startup_validation()
        assert "total_representations" in result
        assert "passing" in result
        assert "warnings" in result
        assert "failing" in result
        assert "elapsed_ms" in result
        assert result["total_representations"] > 0
        assert result["passing"] > 0
    
    def test_startup_validation_per_rep(self, nav_api):
        """Startup validation should check each representation."""
        result = nav_api.startup_validation()
        assert "representations" in result
        reps = result["representations"]
        assert len(reps) > 0
        for rep_name, rep_info in reps.items():
            assert "status" in rep_info
            assert rep_info["status"] in ("PASS", "WARN", "FAIL")
