"""
KD-tree based spatial index for fast viewport queries on 174k+ point datasets.

Provides O(sqrt(N) + k) range queries and O(sqrt(N) + k log k) k-NN queries,
significantly faster than the brute-force O(N) boolean masking used previously.

Supports optional scipy cKDTree for faster builds (if available), with fallback
to pure-Python implementation. Includes disk persistence for fast startup at
174k scale.
"""
import heapq
import json
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# Try to use scipy's optimized cKDTree if available
try:
    from scipy.spatial import cKDTree as _cKDTree
    _HAS_SCIPY = True
except ImportError:
    _cKDTree = None
    _HAS_SCIPY = False


class _KDNode:
    """Internal KD-tree node."""

    __slots__ = ("point_idx", "split_axis", "left", "right", "bbox")

    def __init__(
        self,
        point_idx: int,
        split_axis: int,
        left: Optional["_KDNode"] = None,
        right: Optional["_KDNode"] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ):
        self.point_idx = point_idx
        self.split_axis = split_axis
        self.left = left
        self.right = right
        self.bbox = bbox


class SpatialIndex:
    """KD-tree spatial index for 2D decision positions.

    Supports fast bounding-box range queries and k-nearest-neighbor queries.
    Uses scipy's cKDTree when available (10-50x faster builds), with fallback
    to pure-Python implementation. Includes disk persistence for fast startup
    at 174k scale.
    """

    def __init__(self, persist_path: Optional[Path] = None):
        self._points: Optional[np.ndarray] = None  # (N, 2) float64
        self._decision_ids: List[str] = []
        self._id_to_idx: Dict[str, int] = {}
        self._tree: Optional[_KDNode] = None
        self._cKDTree: Any = None  # scipy's cKDTree
        self._built: bool = False
        self._dirty: bool = False
        self._deleted_indices: set = set()
        self._pending_adds: List[Tuple[str, float, float]] = []
        self._persist_path = persist_path
        self._use_cKDTree = _HAS_SCIPY

    @property
    def size(self) -> int:
        """Number of active points in the index."""
        return len(self._id_to_idx)

    @property
    def is_built(self) -> bool:
        return self._built and not self._dirty

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[Path] = None) -> bool:
        """Persist spatial index to disk for fast reload."""
        if path is not None:
            path = Path(path)
        else:
            path = self._persist_path
        if not path or self._points is None:
            return False

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Use numpy's savez for efficient binary storage
            np.savez_compressed(
                path.with_suffix(".npz"),
                points=self._points,
                decision_ids=np.array(self._decision_ids, dtype=object),
            )
            # Save id_to_idx as JSON (small)
            with open(path.with_suffix(".json"), "w") as f:
                json.dump(self._id_to_idx, f)
            print(f"[SpatialIndex] Saved {self.size} points to {path}")
            return True
        except Exception as e:
            print(f"[SpatialIndex] Save failed: {e}")
            return False

    @classmethod
    def load(cls, path: Path) -> Optional["SpatialIndex"]:
        """Load spatial index from disk."""
        path = Path(path)
        try:
            npz_path = path.with_suffix(".npz")
            json_path = path.with_suffix(".json")
            if not npz_path.exists() or not json_path.exists():
                return None

            data = np.load(npz_path, allow_pickle=True)
            points = data["points"]
            decision_ids = data["decision_ids"].tolist()

            with open(json_path, "r") as f:
                id_to_idx = json.load(f)

            index = cls(persist_path=path)
            index._points = points
            index._decision_ids = decision_ids
            index._id_to_idx = id_to_idx
            index._deleted_indices = set()
            index._pending_adds = []
            index._dirty = False

            # Build the query structure
            if index._use_cKDTree and points is not None and len(points) > 0:
                index._cKDTree = _cKDTree(points)
            else:
                index._tree = index._build_tree(list(range(len(points))), depth=0)

            index._built = True
            print(f"[SpatialIndex] Loaded {index.size} points from {path}")
            return index
        except Exception as e:
            print(f"[SpatialIndex] Load failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def build(self, positions: Dict[str, Tuple[float, float]]) -> None:
        """Build KD-tree from a decision_id -> (x, y) mapping.

        Replaces any existing data. O(N log N) with scipy, O(N log^2 N) pure Python.
        """
        t0 = time.monotonic()

        n = len(positions)
        if n == 0:
            self._points = np.empty((0, 2), dtype=np.float64)
            self._decision_ids = []
            self._id_to_idx = {}
            self._tree = None
            self._cKDTree = None
            self._built = True
            self._dirty = False
            self._deleted_indices = set()
            self._pending_adds = []
            return

        ids = list(positions.keys())
        pts = np.empty((n, 2), dtype=np.float64)
        for i, did in enumerate(ids):
            x, y = positions[did]
            pts[i, 0] = x
            pts[i, 1] = y

        self._points = pts
        self._decision_ids = ids
        self._id_to_idx = {did: i for i, did in enumerate(ids)}
        self._deleted_indices = set()
        self._pending_adds = []
        self._dirty = False

        if self._use_cKDTree:
            self._cKDTree = _cKDTree(pts)
            self._tree = None
        else:
            self._tree = self._build_tree(list(range(n)), depth=0)
            self._cKDTree = None

        self._built = True

        elapsed = time.monotonic() - t0
        backend = "cKDTree" if self._use_cKDTree else "pure-Python"
        if n >= 10000:
            print(f"[SpatialIndex] Built {backend} for {n} points in {elapsed:.3f}s")

        # Auto-save if persist path is set
        if self._persist_path:
            self.save()

    def _build_tree(self, indices: List[int], depth: int) -> Optional[_KDNode]:
        """Recursively build a median-split KD-tree."""
        if not indices:
            return None

        axis = depth % 2

        # Sort by the split axis and pick median
        indices.sort(key=lambda i: self._points[i, axis])
        median = len(indices) // 2

        node_idx = indices[median]
        left = self._build_tree(indices[:median], depth + 1)
        right = self._build_tree(indices[median + 1 :], depth + 1)

        # Compute bounding box for this subtree
        sub_pts = self._points[indices]
        bbox = (
            float(sub_pts[:, 0].min()),
            float(sub_pts[:, 1].min()),
            float(sub_pts[:, 0].max()),
            float(sub_pts[:, 1].max()),
        )

        return _KDNode(point_idx=node_idx, split_axis=axis, left=left, right=right, bbox=bbox)

    # ------------------------------------------------------------------
    # Incremental updates (lazy rebuild)
    # ------------------------------------------------------------------

    def add_point(self, decision_id: str, x: float, y: float) -> None:
        """Stage a point for addition.  Triggers lazy rebuild on next query."""
        if decision_id in self._id_to_idx:
            return  # already present
        self._pending_adds.append((decision_id, x, y))
        self._dirty = True

    def remove_point(self, decision_id: str) -> None:
        """Mark a point as deleted.  Triggers lazy rebuild on next query."""
        idx = self._id_to_idx.get(decision_id)
        if idx is not None:
            self._deleted_indices.add(idx)
            self._dirty = True

    def _rebuild_if_dirty(self) -> None:
        """Rebuild tree if any mutations are pending."""
        if not self._dirty:
            return
        if self._points is None or len(self._points) == 0 and not self._pending_adds:
            return

        # Collect surviving points + new points
        positions: Dict[str, Tuple[float, float]] = {}
        for i, did in enumerate(self._decision_ids):
            if i not in self._deleted_indices:
                positions[did] = (float(self._points[i, 0]), float(self._points[i, 1]))
        for did, x, y in self._pending_adds:
            positions[did] = (x, y)

        self.build(positions)

    # ------------------------------------------------------------------
    # Range query
    # ------------------------------------------------------------------

    def range_query(
        self, x_min: float, y_min: float, x_max: float, y_max: float
    ) -> List[str]:
        """Return all decision_ids whose points fall inside the bounding box.

        Uses scipy's cKDTree query_ball_point with radius when available,
        otherwise falls back to custom KD-tree range search.
        """
        self._rebuild_if_dirty()

        if self._points is None or len(self._points) == 0:
            return []

        if self._use_cKDTree and self._cKDTree is not None:
            # Use scipy's cKDTree for fast range queries
            # Approximate rectangular query with circular query + filter
            cx = (x_min + x_max) / 2.0
            cy = (y_min + y_max) / 2.0
            radius = max(x_max - cx, y_max - cy)
            indices = self._cKDTree.query_ball_point([cx, cy], radius)
            if not indices:
                return []
            # Filter to exact rectangle
            pts = self._points[indices]
            mask = (
                (pts[:, 0] >= x_min) & (pts[:, 0] <= x_max) &
                (pts[:, 1] >= y_min) & (pts[:, 1] <= y_max)
            )
            return [self._decision_ids[i] for i, m in zip(indices, mask) if m]

        # Fallback to custom KD-tree
        if self._tree is None:
            return []

        result_indices: List[int] = []
        self._range_search(self._tree, x_min, y_min, x_max, y_max, result_indices)
        return [self._decision_ids[i] for i in result_indices]

    def _range_search(
        self,
        node: Optional[_KDNode],
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
        out: List[int],
    ) -> None:
        if node is None:
            return

        # Quick reject: subtree bbox doesn't overlap query bbox
        bx0, by0, bx1, by1 = node.bbox
        if bx1 < x_min or bx0 > x_max or by1 < y_min or by0 > y_max:
            return

        # Check this point
        px, py = self._points[node.point_idx]
        if x_min <= px <= x_max and y_min <= py <= y_max:
            out.append(node.point_idx)

        self._range_search(node.left, x_min, y_min, x_max, y_max, out)
        self._range_search(node.right, x_min, y_min, x_max, y_max, out)

    # ------------------------------------------------------------------
    # k-Nearest-Neighbor query
    # ------------------------------------------------------------------

    def knn_query(self, x: float, y: float, k: int = 10) -> List[Tuple[str, float]]:
        """Return k nearest neighbors as (decision_id, squared_distance) tuples.

        Uses scipy's cKDTree for O(log N) queries when available,
        otherwise falls back to custom KD-tree with max-heap pruning.
        """
        self._rebuild_if_dirty()

        if self._points is None or len(self._points) == 0:
            return []

        k = min(k, len(self._points))

        if self._use_cKDTree and self._cKDTree is not None:
            # Use scipy's optimized cKDTree query
            dists, indices = self._cKDTree.query([x, y], k=k, distance_upper_bound=float('inf'))
            if k == 1:
                dists = [dists]
                indices = [indices]
            results = []
            for dist, idx in zip(dists, indices):
                if idx < len(self._decision_ids):
                    results.append((self._decision_ids[idx], float(dist * dist)))
            return results

        # Fallback to custom KD-tree
        if self._tree is None:
            return []

        # max-heap: store (-dist, idx) so that the largest distance is at the
        # root and can be popped when a closer point is found.
        heap: List[Tuple[float, int]] = []
        self._knn_search(self._tree, x, y, k, heap)

        # Sort by distance (ascending) and return (id, dist)
        results = [(-neg_dist, idx) for neg_dist, idx in heap]
        results.sort(key=lambda t: t[0])
        return [(self._decision_ids[idx], dist) for dist, idx in results]

    def _knn_search(
        self,
        node: Optional[_KDNode],
        qx: float,
        qy: float,
        k: int,
        heap: List[Tuple[float, int]],
    ) -> None:
        if node is None:
            return

        px, py = self._points[node.point_idx]
        dx = px - qx
        dy = py - qy
        dist_sq = dx * dx + dy * dy

        if len(heap) < k:
            heapq.heappush(heap, (-dist_sq, node.point_idx))
        elif dist_sq < -heap[0][0]:
            heapq.heapreplace(heap, (-dist_sq, node.point_idx))

        axis = node.split_axis
        diff = (px - qx) if axis == 0 else (py - qy)

        # Visit the side that contains the query point first
        if diff <= 0:
            near, far = node.left, node.right
        else:
            near, far = node.right, node.left

        self._knn_search(near, qx, qy, k, heap)

        # Prune: only visit far subtree if the splitting plane is closer
        # than the current k-th farthest distance
        if len(heap) < k or diff * diff < -heap[0][0]:
            self._knn_search(far, qx, qy, k, heap)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset the index to empty."""
        self._points = None
        self._decision_ids = []
        self._id_to_idx = {}
        self._tree = None
        self._built = False
        self._dirty = False
        self._deleted_indices = set()
        self._pending_adds = []

    def __len__(self) -> int:
        return self.size

    def __repr__(self) -> str:
        status = "built" if self.is_built else ("dirty" if self._dirty else "empty")
        return f"<SpatialIndex n={self.size} status={status}>"
