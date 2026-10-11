"""
Level-of-Detail (LOD) Manager for LexMachina WebGL Rendering.

Provides efficient LOD computation for 174k+ scale corpora.
Uses scipy.spatial.KDTree for spatial queries and numpy vectorized ops.
No O(n^2) operations on point sets.

Supports:
- Multiple LOD levels (0-3) for smooth transitions
- Optimized super-cluster merging (DBSCAN-based when available)
- GPU frustum culling plane computation
- Progressive loading metadata
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from scipy.spatial import KDTree

# Try to use scipy's DBSCAN for better super-cluster merging
try:
    from sklearn.cluster import DBSCAN
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


class LODManager:
    """Manages level-of-detail rendering data for WebGL.

    LOD levels:
      0 — Cluster centroids only (one point per cluster, size = cluster radius)
      1 — Super-cluster centroids (merge nearby clusters via DBSCAN)
      2 — Downsampled points (grid-based decimation)
      3+ — Individual points with optional viewport culling
    """

    # Maximum points per LOD level before auto-selecting a lower level
    DEFAULT_TARGET_POINTS = 5000

    # Merge radius multiplier for super-clusters (relative to data extent)
    SUPER_CLUSTER_RELATIVE_RADIUS = 0.05

    # Grid-based decimation factors for level 2
    LEVEL_2_GRID_FACTOR = 4  # sqrt of decimation factor

    def compute_lod_levels(
        self,
        positions: np.ndarray,
        clusters: List[Dict],
        zoom: int,
    ) -> Dict[str, Any]:
        """Compute LOD-decimated point data for the given zoom level.

        Args:
            positions: (N, 2) float64 array of (x, y) world coordinates.
            clusters: List of cluster dicts with 'cluster_id', 'size',
                      'centroid_x', 'centroid_y'.
            zoom: Current zoom level (0, 1, 2, ...).

        Returns:
            Dict with keys:
              lod_level: int — the LOD level used.
              points: np.ndarray (M, 2) — decimated positions.
              point_count: int — M.
              cluster_sizes: np.ndarray (M,) — size per output point.
              next_lod_hint: int or None — suggested next-lod value.
        """
        n_total = len(positions)
        if n_total == 0:
            return self._empty_result(zoom)

        if zoom <= 0:
            return self._level_0_centroids(positions, clusters)
        elif zoom == 1:
            return self._level_1_super_clusters(positions, clusters)
        elif zoom == 2:
            # Backward compatibility: for small datasets (< 5000 points),
            # level 2 returns full detail. For larger datasets, returns
            # grid-downsampled points.
            if n_total <= self.DEFAULT_TARGET_POINTS:
                return self._level_3_full(positions, clusters)
            return self._level_2_downsampled(positions, clusters)
        else:
            return self._level_3_full(positions, clusters)

    # ------------------------------------------------------------------
    # LOD level implementations
    # ------------------------------------------------------------------

    def _level_0_centroids(
        self, positions: np.ndarray, clusters: List[Dict]
    ) -> Dict[str, Any]:
        """Level 0: one point per cluster centroid, radius = cluster size."""
        n_clusters = len(clusters)
        if n_clusters == 0:
            return self._empty_result(0)

        centroids = np.empty((n_clusters, 2), dtype=np.float64)
        sizes = np.empty(n_clusters, dtype=np.float64)
        for i, c in enumerate(clusters):
            centroids[i, 0] = c["centroid_x"]
            centroids[i, 1] = c["centroid_y"]
            sizes[i] = c["size"]

        return {
            "lod_level": 0,
            "points": centroids,
            "point_count": n_clusters,
            "cluster_sizes": sizes,
            "next_lod_hint": 1,
        }

    def _level_1_super_clusters(
        self, positions: np.ndarray, clusters: List[Dict]
    ) -> Dict[str, Any]:
        """Level 1: merge nearby clusters into super-clusters.

        Uses DBSCAN (if sklearn available) or KDTree-based greedy merging
        to create super-clusters. DBSCAN provides better global optimization
        than the greedy approach.
        """
        n_total = len(positions)
        n_clusters = len(clusters)

        if n_clusters == 0:
            return self._empty_result(1)

        if n_clusters <= 10:
            # Too few clusters to merge; just use centroids
            return self._level_0_centroids(positions, clusters)

        # Build centroids array
        centroids = np.empty((n_clusters, 2), dtype=np.float64)
        sizes = np.empty(n_clusters, dtype=np.float64)
        for i, c in enumerate(clusters):
            centroids[i, 0] = c["centroid_x"]
            centroids[i, 1] = c["centroid_y"]
            sizes[i] = c["size"]

        if _HAS_SKLEARN:
            # Use DBSCAN for density-based super-clustering
            # eps = merge radius relative to data extent
            x_min, x_max = positions[:, 0].min(), positions[:, 0].max()
            y_min, y_max = positions[:, 1].min(), positions[:, 1].max()
            extent = max(x_max - x_min, y_max - y_min, 1.0)
            eps = extent * self.SUPER_CLUSTER_RELATIVE_RADIUS

            dbscan = DBSCAN(eps=eps, min_samples=1, metric='euclidean')
            labels = dbscan.fit_predict(centroids)

            # Compute super-cluster centroids and sizes
            unique_labels = np.unique(labels)
            n_super = len(unique_labels)
            super_centroids = np.empty((n_super, 2), dtype=np.float64)
            super_sizes = np.empty(n_super, dtype=np.float64)

            for i, label in enumerate(unique_labels):
                mask = labels == label
                super_centroids[i] = centroids[mask].mean(axis=0)
                super_sizes[i] = sizes[mask].sum()

            return {
                "lod_level": 1,
                "points": super_centroids,
                "point_count": n_super,
                "cluster_sizes": super_sizes,
                "next_lod_hint": 2,
            }
        else:
            # Fallback to KDTree-based greedy merging
            return self._level_1_super_clusters_kdtree(positions, clusters)

    def _level_1_super_clusters_kdtree(
        self, positions: np.ndarray, clusters: List[Dict]
    ) -> Dict[str, Any]:
        """Legacy KDTree-based greedy super-cluster merging."""
        n_clusters = len(clusters)
        if n_clusters <= 10:
            return self._level_0_centroids(positions, clusters)

        x_min, x_max = positions[:, 0].min(), positions[:, 0].max()
        y_min, y_max = positions[:, 1].min(), positions[:, 1].max()
        extent = max(x_max - x_min, y_max - y_min, 1.0)
        merge_radius = extent * self.SUPER_CLUSTER_RELATIVE_RADIUS

        centroids = np.empty((n_clusters, 2), dtype=np.float64)
        sizes = np.empty(n_clusters, dtype=np.float64)
        for i, c in enumerate(clusters):
            centroids[i, 0] = c["centroid_x"]
            centroids[i, 1] = c["centroid_y"]
            sizes[i] = c["size"]

        tree = KDTree(centroids)
        claimed = np.full(n_clusters, -1, dtype=np.int32)
        rep_idx: List[int] = []
        rep_sizes: List[float] = []

        for i in range(n_clusters):
            if claimed[i] >= 0:
                continue
            claimed[i] = i
            rep_idx.append(i)
            rep_sizes.append(float(sizes[i]))

            neighbors = tree.query_ball_point(centroids[i], merge_radius)
            for j in neighbors:
                if j == i or claimed[j] >= 0:
                    continue
                claimed[j] = i
                rep_sizes[-1] += float(sizes[j])

        n_reps = len(rep_idx)
        super_centroids = centroids[rep_idx]
        super_sizes = np.array(rep_sizes, dtype=np.float64)

        return {
            "lod_level": 1,
            "points": super_centroids,
            "point_count": n_reps,
            "cluster_sizes": super_sizes,
            "next_lod_hint": 2,
        }

    def _level_2_downsampled(
        self, positions: np.ndarray, clusters: List[Dict]
    ) -> Dict[str, Any]:
        """Level 2: grid-based downsampling of individual points.

        Uses a spatial grid to decimate points while preserving spatial
        distribution. Each grid cell keeps one representative point.
        """
        n_total = len(positions)
        if n_total == 0:
            return self._empty_result(2)

        # Target: reduce to ~1/16 of original points (grid_factor^2)
        grid_factor = self.LEVEL_2_GRID_FACTOR
        x_min, x_max = positions[:, 0].min(), positions[:, 0].max()
        y_min, y_max = positions[:, 1].min(), positions[:, 1].max()
        x_range = x_max - x_min if x_max > x_min else 1.0
        y_range = y_max - y_min if y_max > y_min else 1.0

        # Compute grid cell for each point
        grid_x = np.floor((positions[:, 0] - x_min) / x_range * grid_factor).astype(int)
        grid_y = np.floor((positions[:, 1] - y_min) / y_range * grid_factor).astype(int)
        grid_keys = grid_x * 100000 + grid_y

        # Keep first point in each grid cell
        _, unique_indices = np.unique(grid_keys, return_index=True)

        downsampled = positions[unique_indices]
        # For cluster sizes, we'd need to map back - use uniform for now
        sizes = np.ones(len(unique_indices), dtype=np.float64)

        return {
            "lod_level": 2,
            "points": downsampled,
            "point_count": len(unique_indices),
            "cluster_sizes": sizes,
            "next_lod_hint": 3,
        }

    def _level_3_full(
        self, positions: np.ndarray, clusters: List[Dict]
    ) -> Dict[str, Any]:
        """Level 3+: full detail, all individual points."""
        n = len(positions)
        sizes = np.ones(n, dtype=np.float64)
        return {
            "lod_level": 3,
            "points": positions,
            "point_count": n,
            "cluster_sizes": sizes,
            "next_lod_hint": None,
        }

    # ------------------------------------------------------------------
    # Optimal detail level selection
    # ------------------------------------------------------------------

    def get_optimal_detail_level(
        self,
        viewport_bbox: Optional[Dict[str, float]],
        total_points: int,
        data_extent: Optional[Tuple[float, float, float, float]] = None,
        target_point_count: int = None,
    ) -> Dict[str, Any]:
        """Determine the LOD level needed to render at most target_point_count points.

        Args:
            viewport_bbox: Optional {xMin, yMin, xMax, yMax}. When provided,
                           estimates visible point fraction.
            total_points: Total point count in the dataset.
            data_extent: Optional (x_min, x_max, y_min, y_max) of full data extent.
                         If provided with viewport_bbox, enables accurate visible
                           fraction estimation.
            target_point_count: Max points to render (default 5000).

        Returns:
            Dict with lod_level, point_count, next_lod_hint.
        """
        if target_point_count is None:
            target_point_count = self.DEFAULT_TARGET_POINTS

        # Backward compatibility: for small datasets, use LOD 2 (full detail)
        # This maintains API compatibility with existing tests and clients.
        if total_points <= target_point_count:
            return {
                "lod_level": 2,
                "point_count": total_points,
                "next_lod_hint": None,
            }

        # Estimate visible fraction from viewport bbox vs full extent
        estimated_visible = total_points
        if viewport_bbox and data_extent and total_points > 0:
            x_min, x_max, y_min, y_max = data_extent
            full_area = max(x_max - x_min, 1.0) * max(y_max - y_min, 1.0)
            vp_area = (
                (viewport_bbox["xMax"] - viewport_bbox["xMin"])
                * (viewport_bbox["yMax"] - viewport_bbox["yMin"])
            )
            if full_area > 0:
                visible_fraction = min(1.0, vp_area / full_area)
                estimated_visible = int(total_points * visible_fraction)

        if estimated_visible <= target_point_count:
            return {
                "lod_level": 2,
                "point_count": estimated_visible,
                "next_lod_hint": 3,
            }

        # Estimate point counts per LOD level
        # Level 0: ~sqrt(N) clusters (typically 5-50)
        # Level 1: ~N^0.25 super-clusters (typically 20-200)
        # Level 2: ~N/16 grid-downsampled points
        # Level 3: N points
        n_clusters_est = max(1, int(np.sqrt(total_points) * 0.5))
        n_super_est = max(1, int(np.sqrt(n_clusters_est) * 2))
        n_grid_est = max(1, total_points // (self.LEVEL_2_GRID_FACTOR ** 2))

        if n_grid_est <= target_point_count:
            return {
                "lod_level": 2,
                "point_count": n_grid_est,
                "next_lod_hint": 3,
            }

        if n_super_est <= target_point_count:
            return {
                "lod_level": 1,
                "point_count": n_super_est,
                "next_lod_hint": 2,
            }

        if n_clusters_est <= target_point_count:
            return {
                "lod_level": 0,
                "point_count": n_clusters_est,
                "next_lod_hint": 1,
            }

        return {
            "lod_level": 0,
            "point_count": n_clusters_est,
            "next_lod_hint": 1,
        }

    # ------------------------------------------------------------------
    # GPU Frustum Culling Support
    # ------------------------------------------------------------------

    def compute_frustum_planes(
        self,
        viewport_bbox: Dict[str, float],
        canvas_width: int,
        canvas_height: int,
    ) -> List[Tuple[float, float, float, float]]:
        """Compute frustum planes for GPU-side culling.

        Returns 4 planes (left, right, bottom, top) in normalized device
        coordinates as (a, b, c, d) where ax + by + cz + d = 0.
        For 2D orthographic projection, z=0, so planes are just 2D lines.

        The client can use these planes in the vertex shader for early
        culling of points outside the viewport.
        """
        x_min = viewport_bbox["xMin"]
        x_max = viewport_bbox["xMax"]
        y_min = viewport_bbox["yMin"]
        y_max = viewport_bbox["yMax"]

        # Convert world coordinates to NDC (-1 to 1)
        # This matches the WebGL vertex shader transform:
        # clipSpace = (position / resolution) * 2.0 - 1.0
        x_min_ndc = (x_min / canvas_width) * 2.0 - 1.0
        x_max_ndc = (x_max / canvas_width) * 2.0 - 1.0
        y_min_ndc = (y_min / canvas_height) * 2.0 - 1.0
        y_max_ndc = (y_max / canvas_height) * 2.0 - 1.0

        # Frustum planes: x >= x_min, x <= x_max, y >= y_min, y <= y_max
        # In form: a*x + b*y + c*z + d >= 0
        planes = [
            (1.0, 0.0, 0.0, -x_min_ndc),   # left: x - x_min >= 0
            (-1.0, 0.0, 0.0, x_max_ndc),   # right: -x + x_max >= 0
            (0.0, 1.0, 0.0, -y_min_ndc),   # bottom: y - y_min >= 0
            (0.0, -1.0, 0.0, y_max_ndc),   # top: -y + y_max >= 0
        ]
        return planes

    # ------------------------------------------------------------------
    # Viewport culling (KDTree-based) - BACKWARD COMPATIBLE
    # ------------------------------------------------------------------

    def cull_to_viewport(
        self,
        points: np.ndarray,
        bbox: Dict[str, float],
    ) -> np.ndarray:
        """Return boolean mask of points inside the viewport bounding box.

        Uses numpy vectorized ops — O(N).
        """
        x_min, x_max = bbox["xMin"], bbox["xMax"]
        y_min, y_max = bbox["yMin"], bbox["yMax"]
        mask = (
            (points[:, 0] >= x_min)
            & (points[:, 0] <= x_max)
            & (points[:, 1] >= y_min)
            & (points[:, 1] <= y_max)
        )
        return mask

    def cull_to_viewport_kdtree(
        self,
        points: np.ndarray,
        bbox: Dict[str, float],
    ) -> np.ndarray:
        """Viewport culling using KDTree range query.

        Faster than brute-force for large point sets when the viewport
        is a small fraction of the total extent.
        """
        n = len(points)
        if n < 1000:
            return self.cull_to_viewport(points, bbox)

        tree = KDTree(points)
        # query_ball_point with a bounding box requires querying with
        # a rectangle. KDTree in scipy only supports point+radius.
        # We approximate: use the diagonal of the bbox as radius,
        # centered at bbox center, then refine with numpy.
        cx = (bbox["xMin"] + bbox["xMax"]) / 2.0
        cy = (bbox["yMin"] + bbox["yMax"]) / 2.0
        half_diag = np.sqrt(
            (bbox["xMax"] - bbox["xMin"]) ** 2
            + (bbox["yMax"] - bbox["yMin"]) ** 2
        ) / 2.0

        candidates = tree.query_ball_point([cx, cy], half_diag)
        if not candidates:
            return np.zeros(n, dtype=bool)

        candidate_idx = np.array(candidates, dtype=np.int64)
        # Refine with exact bounds
        pts = points[candidate_idx]
        in_box = (
            (pts[:, 0] >= bbox["xMin"])
            & (pts[:, 0] <= bbox["xMax"])
            & (pts[:, 1] >= bbox["yMin"])
            & (pts[:, 1] <= bbox["yMax"])
        )
        mask = np.zeros(n, dtype=bool)
        mask[candidate_idx[in_box]] = True
        return mask

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_result(self, zoom: int) -> Dict[str, Any]:
        return {
            "lod_level": min(zoom, 3),
            "points": np.empty((0, 2), dtype=np.float64),
            "point_count": 0,
            "cluster_sizes": np.empty(0, dtype=np.float64),
            "next_lod_hint": None,
        }

    def get_lod_info(self) -> Dict[str, Any]:
        """Return static LOD level metadata for the /api/webgl/lod endpoint."""
        return {
            "lod_levels": [0, 1, 2, 3],
            "points_per_level": {
                "0": "cluster_centroids",
                "1": "super_clusters",
                "2": "grid_downsampled",
                "3": "full_detail",
            },
            "recommended_level": 1,
            "viewport_culling": True,
            "frustum_culling": True,
            "gpu_frustum_planes": True,
        }
