"""
Level-of-Detail (LOD) Manager for LexMachina WebGL Rendering.

Provides efficient LOD computation for 174k+ scale corpora.
Uses scipy.spatial.KDTree for spatial queries and numpy vectorized ops.
No O(n^2) operations on point sets.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from scipy.spatial import KDTree


class LODManager:
    """Manages level-of-detail rendering data for WebGL.

    LOD levels:
      0 — Cluster centroids only (one point per cluster, size = cluster radius)
      1 — Super-cluster centroids (merge nearby clusters)
      2+ — Individual points with optional viewport culling
    """

    # Maximum points per LOD level before auto-selecting a lower level
    DEFAULT_TARGET_POINTS = 5000

    # Merge radius multiplier for super-clusters (relative to data extent)
    SUPER_CLUSTER_RELATIVE_RADIUS = 0.05

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
        else:
            return self._level_2_full(positions, clusters)

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

        Uses KDTree to find clusters within a adaptive radius and merges them.
        Complexity: O(N log N) for tree build + O(N) for radius queries.
        """
        n_total = len(positions)
        n_clusters = len(clusters)

        if n_clusters == 0:
            return self._empty_result(1)

        if n_clusters <= 10:
            # Too few clusters to merge; just use centroids
            return self._level_0_centroids(positions, clusters)

        # Compute adaptive merge radius from data extent
        x_min, x_max = positions[:, 0].min(), positions[:, 0].max()
        y_min, y_max = positions[:, 1].min(), positions[:, 1].max()
        extent = max(x_max - x_min, y_max - y_min, 1.0)
        merge_radius = extent * self.SUPER_CLUSTER_RELATIVE_RADIUS

        # Build KDTree over cluster centroids
        centroids = np.empty((n_clusters, 2), dtype=np.float64)
        sizes = np.empty(n_clusters, dtype=np.float64)
        for i, c in enumerate(clusters):
            centroids[i, 0] = c["centroid_x"]
            centroids[i, 1] = c["centroid_y"]
            sizes[i] = c["size"]

        tree = KDTree(centroids)

        # Merge: greedy union-find style — assign each cluster to its
        # nearest representative that has already been claimed, or become
        # a new representative.
        claimed = np.full(n_clusters, -1, dtype=np.int32)
        rep_idx: List[int] = []
        rep_sizes: List[float] = []

        for i in range(n_clusters):
            if claimed[i] >= 0:
                continue
            # This cluster becomes a new representative
            claimed[i] = i
            rep_idx.append(i)
            rep_sizes.append(float(sizes[i]))

            # Find all clusters within merge_radius of this representative
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

    def _level_2_full(
        self, positions: np.ndarray, clusters: List[Dict]
    ) -> Dict[str, Any]:
        """Level 2+: full detail, all individual points."""
        n = len(positions)
        sizes = np.ones(n, dtype=np.float64)
        return {
            "lod_level": 2,
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
        target_point_count: int = None,
    ) -> Dict[str, Any]:
        """Determine the LOD level needed to render at most target_point_count points.

        Args:
            viewport_bbox: Optional {xMin, yMin, xMax, yMax}. When provided,
                           estimates visible point fraction.
            total_points: Total point count in the dataset.
            target_point_count: Max points to render (default 5000).

        Returns:
            Dict with lod_level, point_count, next_lod_hint.
        """
        if target_point_count is None:
            target_point_count = self.DEFAULT_TARGET_POINTS

        if total_points <= target_point_count:
            return {
                "lod_level": 2,
                "point_count": total_points,
                "next_lod_hint": None,
            }

        # Estimate visible fraction from viewport bbox vs full extent
        if viewport_bbox and total_points > 0:
            # Rough estimate: fraction of area covered
            vp_area = (
                (viewport_bbox["xMax"] - viewport_bbox["xMin"])
                * (viewport_bbox["yMax"] - viewport_bbox["yMin"])
            )
            # We don't have full extent here, so assume worst-case
            # (all points visible) unless bbox is provided
            estimated_visible = total_points
        else:
            estimated_visible = total_points

        if estimated_visible <= target_point_count:
            return {
                "lod_level": 2,
                "point_count": estimated_visible,
                "next_lod_hint": None,
            }

        # Binary-search-like selection: estimate cluster count and
        # super-cluster count to find the right level.
        # Level 0 produces ~sqrt(N) to N/10 points (cluster count).
        # Level 1 produces ~sqrt(N) points (super-cluster count).
        # Level 2 produces N points.
        n_clusters_est = max(1, int(np.sqrt(total_points) * 0.5))
        n_super_est = max(1, int(np.sqrt(n_clusters_est) * 2))

        if n_super_est <= target_point_count:
            return {
                "lod_level": 1,
                "point_count": n_super_est,
                "next_lod_hint": 2,
            }

        if n_clusters_est <= target_point_count:
            return {
                "lod_level": 1,
                "point_count": n_clusters_est,
                "next_lod_hint": 2,
            }

        return {
            "lod_level": 0,
            "point_count": n_clusters_est,
            "next_lod_hint": 1,
        }

    # ------------------------------------------------------------------
    # Viewport culling (KDTree-based)
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
            "lod_level": min(zoom, 2),
            "points": np.empty((0, 2), dtype=np.float64),
            "point_count": 0,
            "cluster_sizes": np.empty(0, dtype=np.float64),
            "next_lod_hint": None,
        }

    def get_lod_info(self) -> Dict[str, Any]:
        """Return static LOD level metadata for the /api/webgl/lod endpoint."""
        return {
            "lod_levels": [0, 1, 2],
            "points_per_level": {
                "0": "cluster_centroids",
                "1": "super_clusters",
                "2": "full_detail",
            },
            "recommended_level": 1,
            "viewport_culling": True,
        }
