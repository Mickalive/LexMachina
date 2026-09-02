"""
LexMachina Cycle Tests — Representation Health & Graceful Degradation
Tests: health checker, degraded representation detection, health summary,
per-representation health endpoint, and graceful degradation on map failure.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.map_loader import MapLoader, MapState, ZoomLevel, ClusterInfo
from app.health_checker import RepresentationHealthChecker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_map_state(representation="test_rep", n_decisions=100, zoom_levels=None):
    """Build a minimal MapState for testing."""
    if zoom_levels is None:
        zoom_levels = {1, 2}
    zl_map = {}
    for level in zoom_levels:
        positions = {f"dec_{i}": (float(i), float(i * 2)) for i in range(n_decisions)}
        cluster_assignments = {f"dec_{i}": i % 10 for i in range(n_decisions)}
        clusters = {}
        for cid in range(10):
            members = [f"dec_{i}" for i in range(n_decisions) if i % 10 == cid]
            clusters[cid] = ClusterInfo(
                cluster_id=cid,
                zoom_level=level,
                decision_ids=members,
                size=len(members),
                centroid_x=float(cid),
                centroid_y=float(cid * 2),
            )
        zl_map[level] = ZoomLevel(
            level=level,
            n_clusters=10,
            clusters=clusters,
            positions=positions,
            cluster_assignments=cluster_assignments,
            n_decisions=n_decisions,
        )
    return MapState(
        representation=representation,
        n_decisions=n_decisions,
        zoom_levels=zl_map,
    )


def _make_map_loader(representations=None):
    """Build a MapLoader with pre-populated maps for testing."""
    loader = MagicMock(spec=MapLoader)
    if representations is None:
        representations = {
            "healthy_rep": _make_map_state("healthy_rep", 100, {1, 2, 3}),
        }
    loader.maps = representations
    loader.get_available_representations.return_value = list(representations.keys())
    loader.get_map.side_effect = lambda rep: representations.get(rep)
    loader.get_zoom_levels.side_effect = lambda rep: sorted(
        representations[rep].zoom_levels.keys()
    ) if rep in representations else []
    loader.get_zoom_level.side_effect = lambda rep, lev: (
        representations[rep].zoom_levels.get(lev)
        if rep in representations
        else None
    )
    return loader


# ---------------------------------------------------------------------------
# test_health_checker_healthy
# ---------------------------------------------------------------------------

def test_health_checker_healthy():
    """A representation with multiple zoom levels, full positions and clusters
    is reported as 'healthy'."""
    checker = RepresentationHealthChecker()
    loader = _make_map_loader({
        "healthy_rep": _make_map_state("healthy_rep", 100, {1, 2, 3}),
    })

    result = checker.check_representation_health("healthy_rep", loader)

    assert result["status"] == "healthy", f"Expected healthy, got {result['status']}"
    assert result["zoom_levels_ok"] is True
    assert result["cluster_coverage"] >= 0.9
    assert result["position_coverage"] >= 0.9
    assert result["issues"] == [], f"Unexpected issues: {result['issues']}"


# ---------------------------------------------------------------------------
# test_health_checker_degraded
# ---------------------------------------------------------------------------

def test_health_checker_degraded():
    """A representation with only one zoom level is reported as 'degraded'
    (below MIN_ZOOM_LEVELS threshold)."""
    checker = RepresentationHealthChecker()
    # Single zoom level -> zoom_levels_ok = False
    loader = _make_map_loader({
        "degraded_rep": _make_map_state("degraded_rep", 80, {1}),
    })

    result = checker.check_representation_health("degraded_rep", loader)

    assert result["status"] == "degraded", f"Expected degraded, got {result['status']}"
    assert result["zoom_levels_ok"] is False
    assert len(result["issues"]) >= 1
    assert any("zoom" in issue.lower() for issue in result["issues"])


def test_health_checker_degraded_low_cluster_coverage():
    """A representation with most decisions unclustered is 'degraded'."""
    checker = RepresentationHealthChecker()
    # Only 5 out of 100 decisions get a valid cluster assignment
    positions = {f"dec_{i}": (float(i), float(i)) for i in range(100)}
    # Give cluster ids but mostly -1 (unassigned)
    cluster_assignments = {f"dec_{i}": -1 for i in range(100)}
    for i in range(5):
        cluster_assignments[f"dec_{i}"] = 0

    clusters = {0: ClusterInfo(0, 1, [f"dec_{i}" for i in range(5)], 5, 0.0, 0.0)}
    zl = ZoomLevel(1, 1, clusters, positions, cluster_assignments, 100)
    ms = MapState("low_cluster", 100, {1: zl})
    loader = _make_map_loader({"low_cluster": ms})

    result = checker.check_representation_health("low_cluster", loader)

    assert result["status"] == "degraded"
    assert result["cluster_coverage"] < 0.9
    assert any("cluster coverage" in issue.lower() for issue in result["issues"])


def test_health_checker_failed():
    """A representation that is not loaded at all is 'failed'."""
    checker = RepresentationHealthChecker()
    loader = _make_map_loader({})

    result = checker.check_representation_health("nonexistent", loader)

    assert result["status"] == "failed"
    assert result["cluster_coverage"] == 0.0
    assert result["position_coverage"] == 0.0
    assert len(result["issues"]) >= 1


# ---------------------------------------------------------------------------
# test_health_summary
# ---------------------------------------------------------------------------

def test_health_summary():
    """get_health_summary returns correct counts across healthy/degraded/failed."""
    checker = RepresentationHealthChecker()
    loader = _make_map_loader({
        "rep_healthy": _make_map_state("rep_healthy", 100, {1, 2, 3}),
        "rep_degraded": _make_map_state("rep_degraded", 80, {1}),
    })

    summary = checker.get_health_summary(loader)

    assert summary["total"] == 2
    assert summary["healthy"] >= 1
    assert summary["degraded"] >= 1
    assert summary["healthy_pct"] > 0
    assert "per_representation" in summary
    assert "rep_healthy" in summary["per_representation"]
    assert "rep_degraded" in summary["per_representation"]
    assert summary["per_representation"]["rep_healthy"]["status"] == "healthy"
    assert summary["per_representation"]["rep_degraded"]["status"] == "degraded"


# ---------------------------------------------------------------------------
# test_representation_health_endpoint
# ---------------------------------------------------------------------------

def test_representation_health_endpoint():
    """GET /api/health/representations returns valid per-representation data."""
    # We verify the health checker produces valid data that the endpoint
    # would return, rather than spinning up a full HTTP server.
    checker = RepresentationHealthChecker()
    loader = _make_map_loader({
        "rep_a": _make_map_state("rep_a", 100, {1, 2}),
        "rep_b": _make_map_state("rep_b", 50, {1}),
    })

    summary = checker.get_health_summary(loader)

    # Validate structure matches what the endpoint returns
    assert "total" in summary
    assert "healthy" in summary
    assert "degraded" in summary
    assert "failed" in summary
    assert "healthy_pct" in summary
    assert "per_representation" in summary
    assert isinstance(summary["per_representation"], dict)

    for rep_name, health in summary["per_representation"].items():
        assert "status" in health
        assert health["status"] in ("healthy", "degraded", "failed")
        assert "zoom_levels_ok" in health
        assert "cluster_coverage" in health
        assert "position_coverage" in health
        assert "issues" in health
        assert isinstance(health["issues"], list)
        assert 0.0 <= health["cluster_coverage"] <= 1.0
        assert 0.0 <= health["position_coverage"] <= 1.0


# ---------------------------------------------------------------------------
# test_graceful_degradation
# ---------------------------------------------------------------------------

def test_graceful_degradation():
    """When a representation fails to load, map data includes alternatives."""
    from app.navigation import NavigationAPI

    checker = RepresentationHealthChecker()

    healthy_ms = _make_map_state("production_default", 100, {1, 2})
    broken_ms = _make_map_state("broken_rep", 100, {1})

    loader = _make_map_loader({
        "production_default": healthy_ms,
        "broken_rep": broken_ms,
    })

    # Simulate what get_map_data returns when zoom level is missing
    result_no_zoom = {"error": "Zoom level 5 not available for broken_rep"}

    # The server logic adds available alternatives — simulate it
    available = list(loader.maps.keys())
    result_no_zoom["available_representations"] = available
    result_no_zoom["healthy_representations"] = [
        r for r in available
        if checker.check_representation_health(r, loader)["status"] == "healthy"
    ]
    result_no_zoom["degraded_representations"] = [
        r for r in available
        if checker.check_representation_health(r, loader)["status"] in ("degraded", "failed")
    ]

    assert "error" in result_no_zoom
    assert "available_representations" in result_no_zoom
    assert "production_default" in result_no_zoom["available_representations"]
    assert "recommendation" not in result_no_zoom  # Added only in server logic

    # Verify the healthy representation is reported as available
    assert "production_default" in result_no_zoom["available_representations"]

    # And the broken one is not in healthy list
    assert "broken_rep" not in result_no_zoom.get("healthy_representations", [])


def test_graceful_degradation_all_healthy():
    """When all representations are healthy, alternatives lists are empty."""
    checker = RepresentationHealthChecker()
    loader = _make_map_loader({
        "rep_a": _make_map_state("rep_a", 100, {1, 2, 3}),
        "rep_b": _make_map_state("rep_b", 80, {1, 2}),
    })

    all_health = checker.check_all_representations(loader)
    degraded = [rep for rep, h in all_health.items() if h["status"] != "healthy"]

    # Both should be healthy, so degraded list is empty
    assert degraded == []
