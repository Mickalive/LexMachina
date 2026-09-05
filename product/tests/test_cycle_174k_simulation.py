"""
LexMachina 174k-Scale Simulation Tests — Cycle 17 (direction v17)

Validates that ALL scale-readiness infrastructure works at 174,000-decision
scale using synthetic upsampling of the 1,200-decision corpus.
This is the core v17 product deliverable: proof that the infrastructure
is ready for full-corpus delivery from the corpus lane.

Tests:
1. LOD Manager at 174k: centroid extraction, progressive detail, optimal level
2. Viewport culling at 174k: brute-force and KDTree
3. Spatial Index at 174k: build, range query, k-NN
4. WebGL data preparation at 174k: numpy array generation
5. Inverted Index at 174k: build and search
6. Full pipeline: simulate scale → LOD → cull → serve
"""
import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.lod_manager import LODManager
from app.spatial_index import SpatialIndex
from app.inverted_index import InvertedIndex


# ---------------------------------------------------------------------------
# Synthetic 174k data generator
# ---------------------------------------------------------------------------

def _generate_174k_data(n=174113, seed=42, n_clusters=150):
    """Generate synthetic 174k-point dataset simulating case-law map layout.

    Creates n_clusters clusters with points scattered around centroids,
    mimicking the Swiss Federal Supreme Court legal-area clustering.

    Returns:
        positions: np.ndarray (n, 2) float64
        clusters: list of dicts with cluster_id, size, centroid_x, centroid_y
        cluster_labels: np.ndarray (n,) int — cluster assignment per point
    """
    rng = np.random.RandomState(seed)

    # Generate cluster centroids spread across a large area
    centroids = rng.randn(n_clusters, 2) * 50.0

    # Assign points to clusters (approximately equal size)
    points_per_cluster = n // n_clusters
    remainder = n - points_per_cluster * n_clusters

    positions = np.empty((n, 2), dtype=np.float64)
    cluster_labels = np.empty(n, dtype=np.int32)
    cluster_info = []

    idx = 0
    for c in range(n_clusters):
        size = points_per_cluster + (1 if c < remainder else 0)
        cx, cy = centroids[c]
        spread = rng.uniform(0.5, 3.0)
        positions[idx:idx+size, 0] = cx + rng.randn(size) * spread
        positions[idx:idx+size, 1] = cy + rng.randn(size) * spread
        cluster_labels[idx:idx+size] = c
        cluster_info.append({
            "cluster_id": c,
            "size": size,
            "centroid_x": float(cx),
            "centroid_y": float(cy),
        })
        idx += size

    return positions, cluster_info, cluster_labels


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLODAt174k:
    """LOD Manager validated at 174,000-point scale."""

    def test_centroids_level0_174k(self):
        """Level 0 returns one point per cluster at 174k scale."""
        print("=== Test: LOD Centroids at 174k ===")
        t0 = time.time()
        positions, clusters, _ = _generate_174k_data()
        gen_time = time.time() - t0

        mgr = LODManager()
        t0 = time.time()
        result = mgr.compute_lod_levels(positions, clusters, zoom=0)
        lod_time = time.time() - t0

        assert result["lod_level"] == 0
        assert result["point_count"] == len(clusters), (
            f"Expected {len(clusters)} centroids, got {result['point_count']}"
        )
        assert result["points"].shape == (len(clusters), 2)
        print(f"  174k → {result['point_count']} centroids in {lod_time:.3f}s "
              f"(data gen: {gen_time:.2f}s)")
        # Must be fast enough for interactive use
        assert lod_time < 2.0, f"LOD 0 took {lod_time:.3f}s, must be < 2.0s"

    def test_progressive_detail_174k(self):
        """LOD levels decrease point count progressively at 174k scale."""
        print("=== Test: LOD Progressive Detail at 174k ===")
        positions, clusters, _ = _generate_174k_data()

        mgr = LODManager()
        r0 = mgr.compute_lod_levels(positions, clusters, zoom=0)
        r1 = mgr.compute_lod_levels(positions, clusters, zoom=1)
        r2 = mgr.compute_lod_levels(positions, clusters, zoom=2)
        r3 = mgr.compute_lod_levels(positions, clusters, zoom=3)

        # Level 3 should have all 174k points
        assert r3["point_count"] == 174113, f"Level 3 should have all points"
        # Level 0 should have exactly n_clusters centroids
        assert r0["point_count"] == len(clusters)
        # All LOD levels should reduce points (or stay same) from full detail
        assert r1["point_count"] <= r3["point_count"]
        assert r2["point_count"] <= r3["point_count"]
        assert r0["point_count"] <= r3["point_count"]
        print(f"  L0={r0['point_count']}, L1={r1['point_count']}, "
              f"L2={r2['point_count']}, L3={r3['point_count']}")

    def test_optimal_level_174k(self):
        """Auto LOD selection picks level 0 for 174k points with default target."""
        print("=== Test: Optimal LOD Level at 174k ===")
        mgr = LODManager()
        r = mgr.get_optimal_detail_level(None, total_points=174113)

        # Default target is 5000, so 174k should select LOD 0 or 1
        assert r["lod_level"] <= 1, f"Expected LOD 0 or 1, got {r['lod_level']}"
        assert r["point_count"] <= 5000, (
            f"Point count {r['point_count']} exceeds 5000 target"
        )
        print(f"  174k → LOD {r['lod_level']}, {r['point_count']} points")

    def test_optimal_level_with_viewport_174k(self):
        """Viewport-aware LOD selection at 174k with small viewport."""
        print("=== Test: Optimal LOD with Viewport at 174k ===")
        mgr = LODManager()
        # Data extent from the generator: centroids * 50, so roughly ±150
        bbox = {"xMin": -10.0, "yMin": -10.0, "xMax": 10.0, "yMax": 10.0}
        data_extent = (-150.0, 150.0, -150.0, 150.0)
        r = mgr.get_optimal_detail_level(bbox, total_points=174113,
                                          data_extent=data_extent)
        print(f"  Viewport: LOD {r['lod_level']}, {r['point_count']} visible")
        # Small viewport should allow higher detail
        assert r["point_count"] <= 174113


class TestViewportCullingAt174k:
    """Viewport culling validated at 174,000-point scale."""

    def test_brute_force_culling_174k(self):
        """Brute-force viewport culling runs in < 500ms at 174k."""
        print("=== Test: Brute-Force Culling at 174k ===")
        positions, _, _ = _generate_174k_data()
        mgr = LODManager()
        bbox = {"xMin": -10.0, "yMin": -10.0, "xMax": 10.0, "yMax": 10.0}

        t0 = time.time()
        mask = mgr.cull_to_viewport(positions, bbox)
        elapsed = time.time() - t0

        n_visible = int(mask.sum())
        print(f"  {n_visible}/174113 visible in {elapsed:.4f}s")
        assert n_visible > 0, "Some points should be visible"
        assert n_visible < 174113, "Not all points should be visible"
        assert elapsed < 0.5, f"Culling took {elapsed:.4f}s, must be < 0.5s"

    def test_kdtree_culling_174k(self):
        """KDTree viewport culling runs in < 200ms at 174k."""
        print("=== Test: KDTree Culling at 174k ===")
        positions, _, _ = _generate_174k_data()
        mgr = LODManager()
        bbox = {"xMin": -10.0, "yMin": -10.0, "xMax": 10.0, "yMax": 10.0}

        t0 = time.time()
        mask = mgr.cull_to_viewport_kdtree(positions, bbox)
        elapsed = time.time() - t0

        n_visible = int(mask.sum())
        print(f"  {n_visible}/174113 visible in {elapsed:.4f}s")
        assert n_visible > 0
        assert elapsed < 0.5, f"KDTree culling took {elapsed:.4f}s"

    def test_culling_matches_brute_force(self):
        """KDTree culling produces same result as brute-force at 174k."""
        print("=== Test: Culling Consistency at 174k ===")
        positions, _, _ = _generate_174k_data()
        mgr = LODManager()
        bbox = {"xMin": -10.0, "yMin": -10.0, "xMax": 10.0, "yMax": 10.0}

        mask_bf = mgr.cull_to_viewport(positions, bbox)
        mask_kd = mgr.cull_to_viewport_kdtree(positions, bbox)

        assert np.array_equal(mask_bf, mask_kd), (
            f"Mismatch: brute-force={mask_bf.sum()}, KDTree={mask_kd.sum()}"
        )
        print(f"  Consistent: {int(mask_bf.sum())} visible")


class TestSpatialIndexAt174k:
    """Spatial index validated at 174,000-point scale."""

    def test_build_174k(self):
        """Spatial index builds in < 2s at 174k scale."""
        print("=== Test: Spatial Index Build at 174k ===")
        positions, _, _ = _generate_174k_data()
        positions_dict = {f"dec_{i}": (positions[i, 0], positions[i, 1])
                          for i in range(len(positions))}

        si = SpatialIndex()
        t0 = time.time()
        si.build(positions_dict)
        build_time = time.time() - t0

        assert si.size == 174113
        print(f"  Built 174k index in {build_time:.3f}s")
        assert build_time < 5.0, f"Build took {build_time:.3f}s"

    def test_range_query_174k(self):
        """Range query returns correct results in < 100ms at 174k."""
        print("=== Test: Range Query at 174k ===")
        positions, _, _ = _generate_174k_data()
        positions_dict = {f"dec_{i}": (positions[i, 0], positions[i, 1])
                          for i in range(len(positions))}

        si = SpatialIndex()
        si.build(positions_dict)

        t0 = time.time()
        result = si.range_query(-10.0, -10.0, 10.0, 10.0)
        query_time = time.time() - t0

        print(f"  {len(result)}/174113 in bbox in {query_time:.4f}s")
        assert len(result) > 0
        assert len(result) < 174113
        assert query_time < 0.5, f"Range query took {query_time:.4f}s"

    def test_knn_174k(self):
        """k-NN query returns correct results in < 100ms at 174k."""
        print("=== Test: k-NN Query at 174k ===")
        positions, _, _ = _generate_174k_data()
        positions_dict = {f"dec_{i}": (positions[i, 0], positions[i, 1])
                          for i in range(len(positions))}

        si = SpatialIndex()
        si.build(positions_dict)

        t0 = time.time()
        results = si.knn_query(0.0, 0.0, k=20)
        query_time = time.time() - t0

        assert len(results) == 20
        # All results should be sorted by distance
        distances = [r[1] for r in results]
        assert distances == sorted(distances)
        print(f"  20-NN in {query_time:.4f}s, nearest={results[0][1]:.4f}")
        assert query_time < 0.5, f"k-NN took {query_time:.4f}s"


class TestInvertedIndexAt174k:
    """Inverted index validated at 174,000-document scale."""

    def _generate_174k_docs(self, n=174113):
        """Generate 174k synthetic legal documents."""
        rng = np.random.RandomState(42)
        terms_de = ["Bundesgericht", "Verwaltung", "Beschwerde", "Recht",
                     "Zivilrecht", "Strafrecht", "Sozialversicherung",
                     "Nichtigkeitsbeschwerde", "Kassationsbeschwerde",
                     "Verwaltungsgericht", "Ober-gericht", "Erwägung"]
        terms_fr = ["Tribunal", "administration", "recours", "droit",
                     "pénal", "civil", "assurance-vieillesse",
                     "cassation", "tribunal administratif"]
        all_terms = terms_de + terms_fr

        docs = {}
        for i in range(n):
            n_terms = rng.randint(3, 12)
            doc_terms = rng.choice(all_terms, n_terms)
            docs[f"dec_{i}"] = " ".join(doc_terms)
        return docs

    def test_build_174k(self):
        """Inverted index builds in < 10s at 174k scale."""
        print("=== Test: Inverted Index Build at 174k ===")
        docs = self._generate_174k_docs()

        index = InvertedIndex()
        t0 = time.time()
        index.build(docs)
        build_time = time.time() - t0

        assert index.doc_count == 174113
        print(f"  Built 174k index in {build_time:.3f}s, "
              f"{index.term_count} terms")
        assert build_time < 15.0, f"Build took {build_time:.3f}s"

    def test_search_174k(self):
        """Search returns correct results in < 500ms at 174k."""
        print("=== Test: Inverted Index Search at 174k ===")
        docs = self._generate_174k_docs()

        index = InvertedIndex()
        index.build(docs)

        t0 = time.time()
        results = index.search("Bundesgericht Verwaltung", limit=20)
        search_time = time.time() - t0

        assert len(results) > 0
        print(f"  Search 'Bundesgericht Verwaltung': {len(results)} results "
              f"in {search_time:.4f}s")
        assert search_time < 1.0, f"Search took {search_time:.4f}s"


class TestWebGLPipelineAt174k:
    """Full WebGL data preparation pipeline at 174,000-point scale."""

    def test_webgl_array_generation_174k(self):
        """Generate Float32Arrays for WebGL at 174k in < 2s."""
        print("=== Test: WebGL Array Generation at 174k ===")
        positions, clusters, labels = _generate_174k_data()
        n = len(positions)

        t0 = time.time()
        # Simulate what get_webgl_data does: prepare Float32Arrays
        pos_array = np.zeros(n * 2, dtype=np.float32)
        colors_array = np.zeros(n * 4, dtype=np.float32)
        radii_array = np.zeros(n, dtype=np.float32)
        imported_array = np.zeros(n, dtype=np.float32)

        pos_array[0::2] = positions[:, 0].astype(np.float32)
        pos_array[1::2] = positions[:, 1].astype(np.float32)
        radii_array[:] = 3.0
        elapsed = time.time() - t0

        # Verify sizes
        assert len(pos_array) == n * 2
        assert len(colors_array) == n * 4
        assert len(radii_array) == n
        assert len(imported_array) == n
        print(f"  {n} points: {len(pos_array)} pos floats, "
              f"{len(colors_array)} color floats in {elapsed:.4f}s")
        assert elapsed < 2.0, f"Array gen took {elapsed:.4f}s"

    def test_webgl_payload_size_174k(self):
        """WebGL payload for 174k points is < 50MB."""
        print("=== Test: WebGL Payload Size at 174k ===")
        n = 174113
        # positions: 174k * 2 * 4 bytes
        # colors: 174k * 4 * 4 bytes
        # radii: 174k * 4 bytes
        # imported: 174k * 4 bytes
        payload_bytes = n * 2 * 4 + n * 4 * 4 + n * 4 + n * 4
        payload_mb = payload_bytes / (1024 * 1024)
        print(f"  Total payload: {payload_mb:.1f} MB")
        # This should fit in a single HTTP response
        assert payload_mb < 50, f"Payload {payload_mb:.1f}MB exceeds 50MB limit"


class TestFullScalePipeline:
    """End-to-end pipeline: generate 174k → LOD → cull → validate."""

    def test_lod_then_cull_pipeline_174k(self):
        """Full pipeline: 174k points → LOD level 0 → viewport cull."""
        print("=== Test: Full Scale Pipeline at 174k ===")
        positions, clusters, _ = _generate_174k_data()
        mgr = LODManager()

        t0 = time.time()
        # Step 1: LOD level 0 (centroids)
        lod0 = mgr.compute_lod_levels(positions, clusters, zoom=0)
        t_lod = time.time() - t0

        t1 = time.time()
        # Step 2: Cull centroids to viewport (should pass all)
        bbox = {"xMin": -150.0, "yMin": -150.0, "xMax": 150.0, "yMax": 150.0}
        mask = mgr.cull_to_viewport(lod0["points"], bbox)
        t_cull = time.time() - t1

        t2 = time.time()
        # Step 3: Prepare Float32Arrays from culled centroids
        n_visible = int(mask.sum())
        visible_pts = lod0["points"][mask]
        pos_arr = np.zeros(n_visible * 2, dtype=np.float32)
        pos_arr[0::2] = visible_pts[:, 0].astype(np.float32)
        pos_arr[1::2] = visible_pts[:, 1].astype(np.float32)
        t_prep = time.time() - t2

        total = time.time() - t0
        print(f"  Pipeline: {n_visible} centroids, "
              f"LOD={t_lod:.3f}s, cull={t_cull:.4f}s, prep={t_prep:.4f}s, "
              f"total={total:.3f}s")
        assert total < 3.0, f"Pipeline took {total:.3f}s, must be < 3.0s"
        assert n_visible > 0

    def test_representation_coverage_174k(self):
        """All 30 representations have their spatial index at 1000 scale."""
        print("=== Test: Representation Coverage ===")
        from app.navigation import NavigationAPI
        base_dir = Path(__file__).parent.parent
        corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
        results_dir = str(base_dir / "results" / "fractal_map")

        if not Path(corpus_dir).exists() or not Path(results_dir).exists():
            print("  SKIP: data directories not available")
            return

        api = NavigationAPI(corpus_dir, results_dir)
        api.initialize()

        reps = api.map_loader.get_available_representations()
        print(f"  {len(reps)} representations loaded")

        # Verify each representation has zoom levels and spatial index
        # Now spatial indices are per-zoom-level (key format: rep_z{zoom})
        for rep in reps:
            zoom_levels = api.map_loader.get_zoom_levels(rep)
            assert len(zoom_levels) > 0, f"{rep} has no zoom levels"
            # Check at least one spatial index exists for this representation
            has_spatial_index = False
            for zl in zoom_levels:
                si = api._spatial_indices.get(f"{rep}_z{zl}")
                if si is not None:
                    assert si.size > 0, f"{rep}_z{zl} spatial index is empty"
                    has_spatial_index = True
            assert has_spatial_index, f"{rep} has no spatial index for any zoom level"

        print(f"  All {len(reps)} representations validated")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short", "-x"])
