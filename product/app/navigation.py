"""
LexMachina Navigation API
Provides the navigation interface for exploring the case-law map.
Connects corpus data with map artifacts for interactive exploration.
"""
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from .corpus_loader import CorpusLoader
from .map_loader import MapLoader


class NavigationAPI:
    """
    Main navigation interface for the LexMachina product.
    
    Provides:
    - Cluster exploration at multiple zoom levels
    - Decision inspection with full text
    - Search across the corpus
    - Statistics and metadata
    """

    def __init__(self, corpus_dir: str, results_dir: str):
        self.corpus = CorpusLoader(corpus_dir)
        self.map_loader = MapLoader(results_dir)
        self._initialized = False
        self._map_meta_cache: Dict[str, Dict] = {}

    def _get_map_decision_meta(self, decision_id: str) -> Dict:
        """Get metadata for a map decision not in the corpus (from baseline metadata)."""
        if not self._map_meta_cache:
            import json as _json
            meta_path = Path(self.map_loader.results_dir) / "baseline" / "metadata.json"
            if meta_path.exists():
                with open(meta_path, "r") as f:
                    meta_list = _json.load(f)
                for m in meta_list:
                    self._map_meta_cache[m["decision_id"]] = m
        return self._map_meta_cache.get(decision_id, {})

    def initialize(self) -> Dict[str, Any]:
        """Load all data and return initialization status."""
        corpus_count = self.corpus.load()
        map_count = self.map_loader.load()

        self._initialized = True

        return {
            "status": "ready",
            "corpus_decisions": corpus_count,
            "maps_loaded": map_count,
            "representations": self.map_loader.get_available_representations(),
            "languages": self.corpus.languages,
            "branches": self.corpus.branches,
        }

    def get_overview(self) -> Dict[str, Any]:
        """Get high-level overview of the map."""
        if not self._initialized:
            return {"error": "Not initialized"}

        reps = self.map_loader.get_available_representations()
        stats = {}
        for rep in reps:
            stats[rep] = self.map_loader.get_stats(rep)

        return {
            "total_decisions": self.corpus.size,
            "representations": reps,
            "stats": stats,
            "languages": self.corpus.languages,
            "branches": self.corpus.branches,
        }

    def get_map_data(
        self,
        representation: str = "concat_center_tfidf",
        zoom_level: int = 1,
    ) -> Dict[str, Any]:
        """
        Get map data for rendering at a specific zoom level.
        
        Returns positions, cluster assignments, and cluster summaries.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": f"Zoom level {zoom_level} not available for {representation}"}

        # Build cluster summaries with decision info
        cluster_summaries = []
        for cid, cluster in zl.clusters.items():
            # Get sample decisions from this cluster
            sample_decisions = []
            for did in cluster.decision_ids[:5]:  # Max 5 samples
                summary = self.corpus.get_summary(did)
                if summary:
                    sample_decisions.append(summary)

            cluster_summaries.append({
                "cluster_id": cid,
                "size": cluster.size,
                "centroid_x": cluster.centroid_x,
                "centroid_y": cluster.centroid_y,
                "sample_decisions": sample_decisions,
            })

        # Build position data for ALL map decisions (show full map, enrich from corpus when available)
        positions = []
        corpus_ids = set(self.corpus.get_all_ids())
        for did, (x, y) in zl.positions.items():
            summary = self.corpus.get_summary(did)
            meta = {}
            # Extract basic metadata from map metadata if not in corpus
            if not summary:
                # Try to get metadata from the map metadata file
                meta = self._get_map_decision_meta(did)
            positions.append({
                "decision_id": did,
                "x": x,
                "y": y,
                "cluster": zl.cluster_assignments.get(did, -1),
                "language": (summary.get("language") if summary else meta.get("language", "unknown")),
                "branch": (summary.get("branch") if summary else meta.get("branch", "unknown")),
                "legal_area": (summary.get("legal_area") if summary else meta.get("legal_area", "unknown")),
                "has_corpus": did in corpus_ids,
            })

        return {
            "representation": representation,
            "zoom_level": zoom_level,
            "n_clusters": zl.n_clusters,
            "n_decisions": zl.n_decisions,
            "clusters": cluster_summaries,
            "positions": positions,
        }

    def get_cluster_detail(
        self,
        representation: str,
        zoom_level: int,
        cluster_id: int,
    ) -> Dict[str, Any]:
        """Get detailed information about a specific cluster."""
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": "Zoom level not found"}

        cluster = zl.clusters.get(cluster_id)
        if not cluster:
            return {"error": "Cluster not found"}

        # Get all decisions in this cluster
        decisions = []
        for did in cluster.decision_ids:
            summary = self.corpus.get_summary(did)
            if summary:
                decisions.append(summary)

        return {
            "cluster_id": cluster_id,
            "zoom_level": zoom_level,
            "size": cluster.size,
            "centroid_x": cluster.centroid_x,
            "centroid_y": cluster.centroid_y,
            "decisions": decisions,
        }

    def get_decision(self, decision_id: str) -> Dict[str, Any]:
        """Get full details of a specific decision."""
        if not self._initialized:
            return {"error": "Not initialized"}

        decision = self.corpus.get_full(decision_id)
        if not decision:
            return {"error": f"Decision {decision_id} not found"}

        # Find which clusters this decision belongs to
        clusters = []
        for rep in self.map_loader.get_available_representations():
            for zl_level in self.map_loader.get_zoom_levels(rep):
                zl = self.map_loader.get_zoom_level(rep, zl_level)
                if decision_id in zl.cluster_assignments:
                    clusters.append({
                        "representation": rep,
                        "zoom_level": zl_level,
                        "cluster_id": zl.cluster_assignments[decision_id],
                    })

        decision["map_clusters"] = clusters
        return decision

    def search_decisions(self, query: str, limit: int = 20) -> List[Dict]:
        """Search decisions by text content."""
        if not self._initialized:
            return []
        return self.corpus.search(query, limit)

    def get_zoom_levels(self, representation: str) -> List[Dict]:
        """Get available zoom levels for a representation."""
        if not self._initialized:
            return []

        levels = self.map_loader.get_zoom_levels(representation)
        result = []
        for level in levels:
            zl = self.map_loader.get_zoom_level(representation, level)
            if zl:
                result.append({
                    "level": level,
                    "n_clusters": zl.n_clusters,
                    "n_decisions": zl.n_decisions,
                })
        return result

    def get_neighbors(
        self,
        decision_id: str,
        representation: str = "concat_center_tfidf",
        zoom_level: int = 2,
        n: int = 10,
    ) -> List[Dict]:
        """Get nearest neighbors of a decision based on spatial proximity."""
        if not self._initialized:
            return []

        positions = self.map_loader.get_positions(representation)
        if decision_id not in positions:
            return []

        target_pos = positions[decision_id]
        corpus_ids = set(self.corpus.get_all_ids())
        
        # Compute distances to all other decisions (only those in corpus)
        distances = []
        for did, pos in positions.items():
            if did == decision_id or did not in corpus_ids:
                continue
            dist = ((pos[0] - target_pos[0]) ** 2 + (pos[1] - target_pos[1]) ** 2) ** 0.5
            distances.append((did, dist))

        # Sort by distance and return top n
        distances.sort(key=lambda x: x[1])
        
        neighbors = []
        for did, dist in distances[:n]:
            summary = self.corpus.get_summary(did)
            if summary:
                summary["distance"] = round(dist, 4)
                neighbors.append(summary)

        return neighbors

    def import_corpus(self, records: List[Dict]) -> Dict[str, Any]:
        """Import user corpus records into the navigation index.

        Accepts a list of JSONL-style decision records. Validates the schema,
        persists to a user-import directory, and reloads the corpus index.
        Returns import statistics.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        result = self.corpus.import_records(records)
        return result

    def get_corpus_stats(self) -> Dict[str, Any]:
        """Get corpus statistics including user-imported records."""
        if not self._initialized:
            return {"error": "Not initialized"}

        # Compute corpus-map coverage
        corpus_ids = set(self.corpus.get_all_ids())
        map_positions = self.map_loader.get_positions("concat_center_tfidf")
        map_ids = set(map_positions.keys())
        mapped_count = len(corpus_ids & map_ids)

        return {
            "total_decisions": self.corpus.size,
            "languages": self.corpus.languages,
            "branches": self.corpus.branches,
            "user_imports": self.corpus.user_import_count,
            "map_coverage": {
                "corpus_with_map_position": mapped_count,
                "corpus_without_map_position": len(corpus_ids - map_ids),
                "map_positions_without_corpus": len(map_ids - corpus_ids),
                "total_map_positions": len(map_ids),
            },
        }
