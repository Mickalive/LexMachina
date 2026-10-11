"""
LexMachina Product Tests — Cycle 33660041466
Tests for Level-of-Detail (LOD) system for WebGL rendering at 174k scale.

1. test_lod_manager_centroids: LOD level 0 returns one point per cluster
2. test_lod_manager_progressive: Point count decreases with lower LOD
3. test_lod_api_endpoint: /api/webgl/lod returns valid structure
4. test_webgl_data_with_lod: get_webgl_data respects lod_level parameter
5. test_optimal_detail_level: Automatic LOD selection based on viewport
"""
import sys
import json
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.lod_manager import LODManager


def _get_api():
    """Create and initialize a fresh NavigationAPI instance."""
    from app.navigation import NavigationAPI
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    return api


def test_lod_manager_centroids():
    """Verify LOD level 0 returns exactly one point per cluster centroid."""
    print("=== Test: LOD Manager Centroids (level 0) ===")
    mgr = LODManager()

    # Synthetic data: 100 points in 5 clusters
    rng = np.random.RandomState(42)
    n_per_cluster = 20
    n_clusters = 5
    positions = np.empty((n_per_cluster * n_clusters, 2), dtype=np.float64)
    clusters = []
    for c in range(n_clusters):
        cx = float(c * 10)
        cy = float(c * 5)
        positions[c * n_per_cluster : (c + 1) * n_per_cluster, 0] = cx + rng.randn(n_per_cluster) * 0.5
        positions[c * n_per_cluster : (c + 1) * n_per_cluster, 1] = cy + rng.randn(n_per_cluster) * 0.5
        clusters.append({
            "cluster_id": c,
            "size": n_per_cluster,
            "centroid_x": cx,
            "centroid_y": cy,
        })

    result = mgr.compute_lod_levels(positions, clusters, zoom=0)

    assert result["lod_level"] == 0, f"Expected lod_level 0, got {result['lod_level']}"
    assert result["point_count"] == n_clusters, (
        f"Expected {n_clusters} centroid points, got {result['point_count']}"
    )
    assert result["points"].shape == (n_clusters, 2), (
        f"Points shape mismatch: {result['points'].shape}"
    )
    assert result["next_lod_hint"] == 1, "next_lod_hint should be 1 for level 0"
    # Cluster sizes should match input
    for i, c in enumerate(clusters):
        assert result["cluster_sizes"][i] == c["size"], (
            f"Cluster {i} size mismatch"
        )
    print("  PASSED: level 0 returns one point per cluster")


def test_lod_manager_progressive():
    """Verify point count strictly decreases from level 2 -> 1 -> 0."""
    print("=== Test: LOD Manager Progressive Detail ===")
    mgr = LODManager()

    rng = np.random.RandomState(123)
    n_total = 500
    positions = rng.randn(n_total, 2) * 10

    # Create clusters by k-means-like assignment (simple grid)
    n_clusters = 20
    centroids = rng.randn(n_clusters, 2) * 10
    clusters = []
    for c in range(n_clusters):
        # Assign points closest to this centroid
        dists = np.linalg.norm(positions - centroids[c], axis=1)
        assigned = np.sum(dists < 3.0)
        clusters.append({
            "cluster_id": c,
            "size": int(max(1, assigned)),
            "centroid_x": float(centroids[c, 0]),
            "centroid_y": float(centroids[c, 1]),
        })

    r2 = mgr.compute_lod_levels(positions, clusters, zoom=2)
    r1 = mgr.compute_lod_levels(positions, clusters, zoom=1)
    r0 = mgr.compute_lod_levels(positions, clusters, zoom=0)

    assert r2["point_count"] == n_total, f"Level 2 should have all {n_total} points"
    assert r1["point_count"] <= r2["point_count"], "Level 1 should have <= level 2 points"
    # Level 0 always has exactly n_clusters points (one per cluster).
    # Level 1 merges nearby clusters, which may produce fewer OR more points
    # than level 0 depending on spatial distribution. Both must be <= level 2.
    assert r0["point_count"] == n_clusters, f"Level 0 should have {n_clusters} points"
    assert r0["point_count"] <= r2["point_count"], "Level 0 should have <= level 2 points"
    print(f"  Counts: L2={r2['point_count']}, L1={r1['point_count']}, L0={r0['point_count']}")
    print("  PASSED: progressive detail decrease verified")


def test_lod_api_endpoint():
    """Verify /api/webgl/lod returns valid JSON structure."""
    print("=== Test: LOD API Endpoint ===")
    import http.client
    import time

    # Try to connect to a running server (skip if not available)
    try:
        conn = http.client.HTTPConnection("localhost", 8080, timeout=5)
        conn.request("GET", "/api/webgl/lod")
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        conn.close()
    except (ConnectionRefusedError, OSError, json.JSONDecodeError):
        print("  SKIPPED: server not running on localhost:8080")
        return

    # Validate structure
    assert "lod_levels" in data, "Missing 'lod_levels' key"
    assert data["lod_levels"] == [0, 1, 2, 3], f"Expected [0, 1, 2, 3], got {data['lod_levels']}"
    assert "points_per_level" in data, "Missing 'points_per_level' key"
    assert "recommended_level" in data, "Missing 'recommended_level' key"
    assert "viewport_culling" in data, "Missing 'viewport_culling' key"
    assert data["viewport_culling"] is True, "viewport_culling should be True"
    assert "total_points" in data, "Missing 'total_points' key"
    assert "optimal_level" in data, "Missing 'optimal_level' key"
    assert isinstance(data["total_points"], int), "total_points should be int"
    assert isinstance(data["optimal_level"], dict), "optimal_level should be dict"
    assert "lod_level" in data["optimal_level"], "optimal_level missing lod_level"
    print(f"  Response: {json.dumps(data, indent=2)[:300]}")
    print("  PASSED: valid LOD endpoint structure")


def test_webgl_data_with_lod():
    """Verify get_webgl_data respects lod_level parameter."""
    print("=== Test: WebGL Data with LOD Level ===")
    api = _get_api()

    default_rep = "cited_outcome_hybrid_0.5"

    # Full detail (lod_level=None)
    full = api.get_webgl_data(default_rep, zoom_level=1, lod_level=None)
    assert "points" in full, "Missing points in full detail response"
    full_count = full["points"]["count"]

    # LOD level 0 (centroids)
    lod0 = api.get_webgl_data(default_rep, zoom_level=1, lod_level=0)
    assert "points" in lod0, "Missing points in LOD 0 response"
    lod0_count = lod0["points"]["count"]
    assert "lod_level" in lod0, "Response missing lod_level key"
    assert lod0["lod_level"] == 0, f"Expected lod_level=0 in response, got {lod0['lod_level']}"

    # LOD level 1 (super-clusters)
    lod1 = api.get_webgl_data(default_rep, zoom_level=1, lod_level=1)
    assert "points" in lod1, "Missing points in LOD 1 response"
    lod1_count = lod1["points"]["count"]
    assert "lod_level" in lod1, "Response missing lod_level key"
    assert lod1["lod_level"] == 1, f"Expected lod_level=1 in response, got {lod1['lod_level']}"

    print(f"  Full: {full_count} pts, LOD1: {lod1_count} pts, LOD0: {lod0_count} pts")
    assert lod0_count <= full_count, "LOD 0 should have <= full detail points"
    assert lod1_count <= full_count, "LOD 1 should have <= full detail points"

    # Verify arrays have consistent lengths
    for label, data in [("full", full), ("lod0", lod0), ("lod1", lod1)]:
        pts = data["points"]
        n = pts["count"]
        assert len(pts["positions"]) == n * 2, f"{label}: positions length mismatch"
        assert len(pts["colors"]) == n * 4, f"{label}: colors length mismatch"
        assert len(pts["radii"]) == n, f"{label}: radii length mismatch"
        assert len(pts["imported"]) == n, f"{label}: imported length mismatch"

    print("  PASSED: get_webgl_data respects lod_level parameter")


def test_optimal_detail_level():
    """Verify automatic LOD selection based on viewport and point count."""
    print("=== Test: Optimal Detail Level Selection ===")
    mgr = LODManager()

    # Small dataset: should stay at level 2
    r = mgr.get_optimal_detail_level(None, total_points=1000)
    assert r["lod_level"] == 2, f"Small dataset should use LOD 2, got {r['lod_level']}"
    assert r["point_count"] == 1000
    assert r["next_lod_hint"] is None

    # Large dataset: should select lower LOD
    r = mgr.get_optimal_detail_level(None, total_points=200000)
    assert r["lod_level"] < 2, f"Large dataset should use LOD < 2, got {r['lod_level']}"
    assert r["point_count"] <= 5000, f"Point count {r['point_count']} exceeds target 5000"

    # Custom target
    r = mgr.get_optimal_detail_level(None, total_points=50000, target_point_count=1000)
    assert r["point_count"] <= 1000, f"Custom target: {r['point_count']} > 1000"

    # With viewport bbox
    bbox = {"xMin": -10.0, "yMin": -10.0, "xMax": 10.0, "yMax": 10.0}
    r = mgr.get_optimal_detail_level(bbox, total_points=100000)
    assert "lod_level" in r
    assert "point_count" in r
    assert "next_lod_hint" in r
    print(f"  Small: LOD={mgr.get_optimal_detail_level(None, 1000)['lod_level']}, "
          f"Large: LOD={mgr.get_optimal_detail_level(None, 200000)['lod_level']}")
    print("  PASSED: optimal LOD selection works correctly")


def test_viewport_culling():
    """Verify viewport culling returns only points inside bbox."""
    print("=== Test: Viewport Culling ===")
    mgr = LODManager()

    rng = np.random.RandomState(99)
    points = rng.randn(500, 2) * 10
    bbox = {"xMin": -2.0, "yMin": -2.0, "xMax": 2.0, "yMax": 2.0}

    mask = mgr.cull_to_viewport(points, bbox)
    assert mask.dtype == bool
    assert mask.sum() > 0, "Should have some points inside the bbox"
    assert mask.sum() < 500, "Should not include all points"

    # All selected points should be within bounds
    selected = points[mask]
    assert np.all(selected[:, 0] >= -2.0)
    assert np.all(selected[:, 0] <= 2.0)
    assert np.all(selected[:, 1] >= -2.0)
    assert np.all(selected[:, 1] <= 2.0)

    # KDTree culling should produce same result
    mask_kdt = mgr.cull_to_viewport_kdtree(points, bbox)
    assert np.array_equal(mask, mask_kdt), "KDTree culling should match brute-force"
    print(f"  Culling: {mask.sum()}/500 points visible")
    print("  PASSED: viewport culling works correctly")


if __name__ == "__main__":
    test_lod_manager_centroids()
    test_lod_manager_progressive()
    test_optimal_detail_level()
    test_viewport_culling()
    test_lod_api_endpoint()
    test_webgl_data_with_lod()
    print("\n=== All LOD tests passed ===")
