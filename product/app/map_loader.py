"""
LexMachina Map Artifact Loader
Loads pre-computed map artifacts from the fractal-map lane.
Supports multi-resolution clustering and zoom navigation.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class ClusterInfo:
    """Information about a cluster at a specific zoom level."""
    cluster_id: int
    zoom_level: int
    decision_ids: List[str]
    size: int
    centroid_x: float = 0.0
    centroid_y: float = 0.0
    legal_area_label: Optional[str] = None
    language_label: Optional[str] = None


@dataclass
class ZoomLevel:
    """A complete zoom level with clusters and positions."""
    level: int
    n_clusters: int
    clusters: Dict[int, ClusterInfo]
    positions: Dict[str, Tuple[float, float]]  # decision_id -> (x, y)
    cluster_assignments: Dict[str, int]  # decision_id -> cluster_id
    n_decisions: int = 0


@dataclass
class MapState:
    """Complete map state for a representation."""
    representation: str
    n_decisions: int
    zoom_levels: Dict[int, ZoomLevel]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MapLoader:
    """Loads and manages map artifacts from the fractal-map lane."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.maps: Dict[str, MapState] = {}
        self._loaded = False

    def load(self) -> int:
        """Load all available map artifacts. Returns count of representations loaded."""
        if self._loaded:
            return len(self.maps)

        # Load the concat_center_tfidf map (best from fractal-map evaluation)
        self._load_concat_center_tfidf()

        # Load baseline for comparison
        self._load_baseline()

        self._loaded = True
        return len(self.maps)

    def _load_concat_center_tfidf(self) -> None:
        """Load the concat_center_tfidf representation (best performer)."""
        baseline_dir = self.results_dir / "baseline"
        zoom_api_dir = self.results_dir / "zoom_api"
        hierarchical_dir = self.results_dir / "hierarchical"

        if not (baseline_dir / "metadata.json").exists():
            return

        # Load metadata (decision list)
        with open(baseline_dir / "metadata.json", "r") as f:
            metadata = json.load(f)

        decision_ids = [m["decision_id"] for m in metadata]
        n_decisions = len(decision_ids)

        # Load 2D projection
        projection = np.load(baseline_dir / "projection_2d.npy")

        # Load zoom API metadata for cluster assignments
        with open(zoom_api_dir / "api_metadata.json", "r") as f:
            api_meta = json.load(f)

        # Load Leiden cluster assignments (actual clustering results)
        leiden_assignments = {}
        leiden_path = hierarchical_dir / "leiden_multi_resolution.json"
        if leiden_path.exists():
            with open(leiden_path, "r") as f:
                leiden_data = json.load(f)
            # Build mapping: decision_index -> decision_id
            index_to_id = {v: k for k, v in api_meta.get("decision_index", {}).items()}
            # Leiden data uses resolution_X.X keys; map each to an integer zoom level
            for leiden_key, leiden_result in leiden_data.items():
                if not leiden_key.startswith("resolution_"):
                    continue
                resolution_val = float(leiden_key.replace("resolution_", ""))
                zoom_level = int(resolution_val)
                labels = leiden_result.get("labels", [])
                assignments = {}
                for idx, label in enumerate(labels):
                    did = index_to_id.get(idx)
                    if did:
                        assignments[did] = label
                # Store with the resolution_X.X key for direct lookup
                leiden_assignments[leiden_key] = assignments
                # Also store with zoom_level int key for fallback matching
                leiden_assignments[str(zoom_level)] = assignments

        # Build zoom levels from the unified evaluation results
        unified_path = self.results_dir / "unified_evaluation" / "unified_results.json"
        if unified_path.exists():
            with open(unified_path, "r") as f:
                unified = json.load(f)

            # Use concat_center_tfidf results
            concat_data = unified.get("concat_center_tfidf", {})
            self._build_zoom_levels(
                representation="concat_center_tfidf",
                decision_ids=decision_ids,
                projection=projection,
                concat_data=concat_data,
                api_meta=api_meta,
                leiden_assignments=leiden_assignments,
            )

    def _load_baseline(self) -> None:
        """Load the baseline representation for comparison."""
        baseline_dir = self.results_dir / "baseline"
        hierarchical_dir = self.results_dir / "hierarchical"

        if not (baseline_dir / "metadata.json").exists():
            return

        with open(baseline_dir / "metadata.json", "r") as f:
            metadata = json.load(f)

        decision_ids = [m["decision_id"] for m in metadata]
        projection = np.load(baseline_dir / "projection_2d.npy")

        # Load Leiden assignments (same clustering applies to all representations)
        leiden_assignments = {}
        leiden_path = hierarchical_dir / "leiden_multi_resolution.json"
        if leiden_path.exists():
            with open(leiden_path, "r") as f:
                leiden_data = json.load(f)
            # Build index->id mapping from baseline metadata
            index_to_id = {i: m["decision_id"] for i, m in enumerate(metadata)}
            for leiden_key, leiden_result in leiden_data.items():
                if not leiden_key.startswith("resolution_"):
                    continue
                resolution_val = float(leiden_key.replace("resolution_", ""))
                zoom_level = int(resolution_val)
                labels = leiden_result.get("labels", [])
                assignments = {}
                for idx, label in enumerate(labels):
                    did = index_to_id.get(idx)
                    if did:
                        assignments[did] = label
                leiden_assignments[leiden_key] = assignments
                leiden_assignments[str(zoom_level)] = assignments

        unified_path = self.results_dir / "unified_evaluation" / "unified_results.json"
        if unified_path.exists():
            with open(unified_path, "r") as f:
                unified = json.load(f)

            baseline_data = unified.get("baseline_1000", {})
            self._build_zoom_levels(
                representation="baseline",
                decision_ids=decision_ids,
                projection=projection,
                concat_data=baseline_data,
                api_meta=None,
                leiden_assignments=leiden_assignments,
            )

    def _build_zoom_levels(
        self,
        representation: str,
        decision_ids: List[str],
        projection: np.ndarray,
        concat_data: Dict,
        api_meta: Optional[Dict],
        leiden_assignments: Optional[Dict[str, Dict[str, int]]] = None,
    ) -> None:
        """Build zoom levels from unified evaluation data.

        Uses actual Leiden cluster assignments when available, falling back
        to spatial grid clustering as a last resort.
        """
        zoom_levels = {}

        # Create position mapping
        positions = {}
        for i, did in enumerate(decision_ids):
            if i < len(projection):
                positions[did] = (float(projection[i, 0]), float(projection[i, 1]))

        # Map resolution values to zoom_api zoom_levels
        # api_meta cluster_counts uses zoom_api level keys ('0','1','2')
        # while unified_results uses resolution_X.X format
        api_zoom_levels = api_meta.get("zoom_levels", []) if api_meta else []

        # Build zoom levels from resolution data
        for res_str, res_data in concat_data.items():
            if not res_str.startswith("resolution_"):
                continue
            resolution = float(res_str.replace("resolution_", ""))
            zoom_level = int(resolution)

            # Try to use Leiden cluster assignments
            cluster_assignments = None
            if leiden_assignments:
                # Direct lookup by resolution key (e.g., "resolution_0.5")
                if res_str in leiden_assignments:
                    cluster_assignments = leiden_assignments[res_str]
                # Fallback: lookup by zoom_level integer
                elif str(zoom_level) in leiden_assignments:
                    cluster_assignments = leiden_assignments[str(zoom_level)]

            if cluster_assignments is None:
                # Last resort: spatial grid clustering
                cluster_assignments = self._assign_clusters_spatial(
                    positions, resolution
                )

            # Build cluster info
            clusters = {}
            for did, cid in cluster_assignments.items():
                if cid not in clusters:
                    clusters[cid] = ClusterInfo(
                        cluster_id=cid,
                        zoom_level=zoom_level,
                        decision_ids=[],
                        size=0,
                    )
                clusters[cid].decision_ids.append(did)
                clusters[cid].size += 1

            # Compute centroids
            for cid, cluster in clusters.items():
                xs = [positions[did][0] for did in cluster.decision_ids if did in positions]
                ys = [positions[did][1] for did in cluster.decision_ids if did in positions]
                if xs and ys:
                    cluster.centroid_x = sum(xs) / len(xs)
                    cluster.centroid_y = sum(ys) / len(ys)

            zoom_levels[zoom_level] = ZoomLevel(
                level=zoom_level,
                n_clusters=len(clusters),
                clusters=clusters,
                positions=positions,
                cluster_assignments=cluster_assignments,
                n_decisions=len(decision_ids),
            )

        self.maps[representation] = MapState(
            representation=representation,
            n_decisions=len(decision_ids),
            zoom_levels=zoom_levels,
            metadata={
                "n_decisions": len(decision_ids),
                "n_zoom_levels": len(zoom_levels),
            },
        )

    def _assign_clusters_spatial(
        self, positions: Dict[str, Tuple[float, float]], resolution: float
    ) -> Dict[str, int]:
        """Simple spatial clustering based on resolution parameter."""
        if not positions:
            return {}

        # Convert to numpy for clustering
        ids = list(positions.keys())
        coords = np.array([positions[did] for did in ids])

        # Simple grid-based clustering (deterministic, fast)
        # Scale grid by resolution
        grid_size = max(1, int(5 / max(0.1, resolution / 3.0)))
        
        # Normalize coordinates
        x_min, x_max = coords[:, 0].min(), coords[:, 0].max()
        y_min, y_max = coords[:, 1].min(), coords[:, 1].max()
        
        x_range = x_max - x_min if x_max > x_min else 1.0
        y_range = y_max - y_min if y_max > y_min else 1.0

        assignments = {}
        for i, did in enumerate(ids):
            gx = int((coords[i, 0] - x_min) / x_range * grid_size)
            gy = int((coords[i, 1] - y_min) / y_range * grid_size)
            # Linearize grid cell to cluster ID
            assignments[did] = gx * (grid_size + 1) + gy

        return assignments

    def get_map(self, representation: str) -> Optional[MapState]:
        """Get a map by representation name."""
        return self.maps.get(representation)

    def get_zoom_level(self, representation: str, level: int) -> Optional[ZoomLevel]:
        """Get a specific zoom level."""
        m = self.get_map(representation)
        return m.zoom_levels.get(level) if m else None

    def get_cluster_decisions(
        self, representation: str, zoom_level: int, cluster_id: int
    ) -> List[str]:
        """Get decision IDs in a specific cluster."""
        zl = self.get_zoom_level(representation, zoom_level)
        if not zl:
            return []
        cluster = zl.clusters.get(cluster_id)
        return cluster.decision_ids if cluster else []

    def get_positions(self, representation: str, filter_ids: Optional[List[str]] = None) -> Dict[str, Tuple[float, float]]:
        """Get 2D positions for all decisions, optionally filtered to a set of IDs."""
        m = self.get_map(representation)
        if not m or not m.zoom_levels:
            return {}
        # Return positions from the first zoom level (they're the same)
        first_zl = next(iter(m.zoom_levels.values()))
        if filter_ids:
            filter_set = set(filter_ids)
            return {did: pos for did, pos in first_zl.positions.items() if did in filter_set}
        return first_zl.positions

    def get_available_representations(self) -> List[str]:
        """List available representation names."""
        return list(self.maps.keys())

    def get_zoom_levels(self, representation: str) -> List[int]:
        """List available zoom levels for a representation."""
        m = self.get_map(representation)
        return sorted(m.zoom_levels.keys()) if m else []

    def get_stats(self, representation: str) -> Dict:
        """Get summary statistics for a representation."""
        m = self.get_map(representation)
        if not m:
            return {}
        return {
            "representation": representation,
            "n_decisions": m.n_decisions,
            "n_zoom_levels": len(m.zoom_levels),
            "zoom_levels": {
                level: {
                    "n_clusters": zl.n_clusters,
                    "avg_cluster_size": zl.n_decisions / max(1, zl.n_clusters),
                }
                for level, zl in m.zoom_levels.items()
            },
        }
