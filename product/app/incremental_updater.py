"""
LexMachina Incremental Map Update Infrastructure
Enables adding new decisions to existing maps without full recomputation.
Critical for 174k corpus growth - avoids re-clustering the entire dataset.
"""
import hashlib
import json
import os
import time
import threading
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


class IncrementalUpdater:
    """Manages incremental additions of decisions to existing map artifacts.

    New decisions are positioned via k-NN against the base corpus embeddings,
    then persisted as delta files alongside the base map artifacts.
    Deltas can be merged into the base artifacts periodically.
    """

    def __init__(self, nav_api):
        self._nav_api = nav_api
        self._lock = threading.Lock()
        self._pending: Dict[str, List[Dict]] = {}  # rep -> list of pending position records
        self._delta_dir: Optional[Path] = None

    def _ensure_delta_dir(self) -> Path:
        """Return (and lazily create) the delta directory."""
        if self._delta_dir is None:
            self._delta_dir = Path(self._nav_api.map_loader.results_dir) / "user_imports" / "deltas"
            self._delta_dir.mkdir(parents=True, exist_ok=True)
        return self._delta_dir

    def _delta_path(self, representation: str, zoom_level: int) -> Path:
        """Return the delta file path for a given representation and zoom level."""
        safe_rep = representation.replace("/", "_").replace("\\", "_")
        return self._ensure_delta_dir() / f"delta_{safe_rep}_z{zoom_level}.jsonl"

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    def add_decisions_to_map(
        self,
        decision_ids: List[str],
        representation: Optional[str] = None,
        zoom_level: int = 1,
    ) -> Dict[str, Any]:
        """Add new decisions to an existing map's zoom level data.

        Steps:
          a. Compute embeddings for new decisions
          b. Find k-NN in existing map positions
          c. Assign cluster membership via majority vote of neighbors
          d. Compute interpolated 2D positions (centroid of neighbors + jitter)
          e. Update the in-memory ZoomLevel data structures

        Returns summary dict with added count, affected clusters, and
        positions updated.
        """
        if representation is None:
            representation = self._nav_api._get_default_representation()

        nav = self._nav_api
        embedding_model = nav._embedding_model
        base_embeddings = nav._base_embeddings
        base_decision_ids = nav._base_decision_ids

        if embedding_model is None or base_embeddings is None or len(base_embeddings) == 0:
            return {"added": 0, "clusters_affected": [], "positions_updated": 0}

        zl = nav.map_loader.get_zoom_level(representation, zoom_level)
        if zl is None:
            return {"added": 0, "clusters_affected": [], "positions_updated": 0}

        base_positions = zl.positions
        base_cluster_assignments = zl.cluster_assignments

        # Filter out decisions that already have positions
        new_ids = [did for did in decision_ids if (did, representation) not in nav._imported_positions]
        if not new_ids:
            return {"added": 0, "clusters_affected": [], "positions_updated": 0}

        # Gather text for embedding
        texts: List[str] = []
        valid_ids: List[str] = []
        for did in new_ids:
            summary = nav.corpus.get_summary(did)
            text = ""
            if summary:
                text = summary.get("full_text", "") or summary.get("text", "")
                if not text:
                    text = f"{summary.get('title', '')} {summary.get('legal_area', '')}"
            if not text:
                text = did
            texts.append(text)
            valid_ids.append(did)

        if not texts:
            return {"added": 0, "clusters_affected": [], "positions_updated": 0}

        # Compute embeddings
        try:
            embeddings = embedding_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        except Exception:
            return {"added": 0, "clusters_affected": [], "positions_updated": 0}

        # Pre-normalize base embeddings for cosine similarity
        base_norms = np.linalg.norm(base_embeddings, axis=1, keepdims=True)
        base_norms[base_norms == 0] = 1
        base_normalized = base_embeddings / base_norms

        k = 5
        jitter_scale = 0.01
        clusters_affected: set = set()
        added = 0
        new_records: List[Dict] = []

        with self._lock:
            for i, did in enumerate(valid_ids):
                if (did, representation) in nav._imported_positions:
                    continue

                emb = embeddings[i]
                emb_norm = np.linalg.norm(emb)
                if emb_norm == 0:
                    continue
                emb_normalized = emb / emb_norm
                similarities = base_normalized @ emb_normalized

                top_k_indices = np.argpartition(similarities, -k)[-k:]
                top_k_indices = top_k_indices[np.argsort(similarities[top_k_indices])[::-1]]

                neighbor_clusters: List[int] = []
                neighbor_positions: List[tuple] = []
                for idx in top_k_indices:
                    neighbor_did = base_decision_ids[idx]
                    if neighbor_did in base_cluster_assignments:
                        neighbor_clusters.append(base_cluster_assignments[neighbor_did])
                    if neighbor_did in base_positions:
                        neighbor_positions.append(base_positions[neighbor_did])

                if not neighbor_clusters:
                    continue

                cluster_counter = Counter(neighbor_clusters)
                assigned_cluster = cluster_counter.most_common(1)[0][0]

                if neighbor_positions:
                    centroid_x = float(np.mean([p[0] for p in neighbor_positions]))
                    centroid_y = float(np.mean([p[1] for p in neighbor_positions]))
                    seed = int(hashlib.md5(did.encode()).hexdigest()[:8], 16) % (2**31)
                    rng = np.random.RandomState(seed)
                    x = centroid_x + float(rng.normal(0, jitter_scale))
                    y = centroid_y + float(rng.normal(0, jitter_scale))
                else:
                    x, y = 0.0, 0.0

                record = {
                    "decision_id": did,
                    "x": x,
                    "y": y,
                    "cluster": int(assigned_cluster),
                    "zoom_level": zoom_level,
                    "representation": representation,
                    "neighbor_count": len(neighbor_clusters),
                    "assigned_via": "knn_incremental",
                }

                nav._imported_positions[(did, representation)] = record
                new_records.append(record)
                clusters_affected.add(int(assigned_cluster))
                added += 1

            # Update in-memory ZoomLevel structures
            if new_records:
                self._update_zoom_level_in_memory(zl, new_records)

            # Track pending for this representation
            if new_records:
                if representation not in self._pending:
                    self._pending[representation] = []
                self._pending[representation].extend(new_records)

        return {
            "added": added,
            "clusters_affected": sorted(clusters_affected),
            "positions_updated": added,
        }

    def update_cluster_metadata(
        self,
        representation: Optional[str] = None,
        zoom_level: int = 1,
    ) -> Dict[str, Any]:
        """Recompute cluster sizes and centroids after additions.

        Returns summary of updated clusters.
        """
        if representation is None:
            representation = self._nav_api._get_default_representation()

        zl = self._nav_api.map_loader.get_zoom_level(representation, zoom_level)
        if zl is None:
            return {"clusters_updated": 0}

        # Rebuild cluster_info from current assignments
        cluster_members: Dict[int, List[str]] = {}
        for did, cid in zl.cluster_assignments.items():
            cluster_members.setdefault(cid, []).append(did)

        # Add imported decisions that have been added in-memory
        for (key_did, key_rep), rec in self._nav_api._imported_positions.items():
            if key_rep == representation and rec.get("zoom_level") == zoom_level:
                cid = rec.get("cluster", -1)
                if cid >= 0:
                    cluster_members.setdefault(cid, [])
                    if key_did not in cluster_members[cid]:
                        cluster_members[cid].append(key_did)

        updated = 0
        for cid, members in cluster_members.items():
            if cid not in zl.clusters:
                continue
            cluster = zl.clusters[cid]
            cluster.decision_ids = members
            cluster.size = len(members)

            # Recompute centroid
            xs, ys = [], []
            for did in members:
                pos = zl.positions.get(did)
                if pos:
                    xs.append(pos[0])
                    ys.append(pos[1])
                else:
                    # Check imported positions
                    rec = self._nav_api._imported_positions.get((did, representation))
                    if rec:
                        xs.append(rec["x"])
                        ys.append(rec["y"])

            if xs:
                cluster.centroid_x = float(np.mean(xs))
                cluster.centroid_y = float(np.mean(ys))
            updated += 1

        return {"clusters_updated": updated}

    def get_pending_updates(self) -> Dict[str, Any]:
        """Return count of decisions not yet reflected in map data.

        Returns dict with total_pending and by_representation breakdown.
        """
        with self._lock:
            total = sum(len(recs) for recs in self._pending.values())
            by_repr = {rep: len(recs) for rep, recs in self._pending.items()}

        return {
            "total_pending": total,
            "by_representation": by_repr,
        }

    def persist_incremental_update(
        self,
        representation: Optional[str] = None,
        zoom_level: int = 1,
    ) -> Dict[str, Any]:
        """Save updated map data to a delta file alongside base artifacts.

        Does NOT modify existing base artifact files. Writes a JSONL delta.
        """
        if representation is None:
            representation = self._nav_api._get_default_representation()

        with self._lock:
            pending = list(self._pending.get(representation, []))
            # Filter to requested zoom level
            pending = [r for r in pending if r.get("zoom_level") == zoom_level]

        if not pending:
            return {"persisted": 0, "delta_file": None}

        delta_path = self._delta_path(representation, zoom_level)
        try:
            with open(delta_path, "a", encoding="utf-8") as f:
                for record in pending:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            return {"persisted": 0, "error": str(e), "delta_file": str(delta_path)}

        # Clear the persisted pending records
        with self._lock:
            if representation in self._pending:
                remaining = [
                    r for r in self._pending[representation]
                    if r.get("zoom_level") != zoom_level
                ]
                self._pending[representation] = remaining

        # Also persist to the main imported_positions.jsonl
        nav = self._nav_api
        if nav._import_positions_file:
            try:
                nav._import_positions_file.parent.mkdir(parents=True, exist_ok=True)
                with open(nav._import_positions_file, "a", encoding="utf-8") as f:
                    for record in pending:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception:
                pass

        return {"persisted": len(pending), "delta_file": str(delta_path)}

    def merge_deltas(
        self,
        representation: Optional[str] = None,
        zoom_level: int = 1,
    ) -> Dict[str, Any]:
        """Merge pending deltas into the base map artifacts.

        Reads the delta file, applies positions and cluster assignments to
        the in-memory ZoomLevel, then writes a merged snapshot delta. The
        base artifact files are never modified.
        """
        if representation is None:
            representation = self._nav_api._get_default_representation()

        delta_path = self._delta_path(representation, zoom_level)
        if not delta_path.exists():
            return {"merged": 0, "delta_file": str(delta_path)}

        records: List[Dict] = []
        try:
            with open(delta_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    records.append(json.loads(line))
        except Exception as e:
            return {"merged": 0, "error": str(e)}

        if not records:
            return {"merged": 0, "delta_file": str(delta_path)}

        zl = self._nav_api.map_loader.get_zoom_level(representation, zoom_level)
        if zl is None:
            return {"merged": 0, "error": "ZoomLevel not found"}

        merged = 0
        with self._lock:
            for record in records:
                did = record.get("decision_id", "")
                if not did:
                    continue

                # Update in-memory structures
                x = record.get("x", 0.0)
                y = record.get("y", 0.0)
                cid = record.get("cluster", -1)

                zl.positions[did] = (x, y)
                if cid >= 0:
                    zl.cluster_assignments[did] = cid
                    if cid in zl.clusters:
                        if did not in zl.clusters[cid].decision_ids:
                            zl.clusters[cid].decision_ids.append(did)
                        zl.clusters[cid].size = len(zl.clusters[cid].decision_ids)

                # Ensure in imported_positions
                rep = record.get("representation", representation)
                self._nav_api._imported_positions[(did, rep)] = record
                merged += 1

            zl.n_decisions = len(zl.positions)

        # Write merged snapshot (overwrites the delta with merged state)
        merged_path = self._delta_path(representation, zoom_level)
        try:
            with open(merged_path, "w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return {"merged": merged, "delta_file": str(delta_path)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_zoom_level_in_memory(self, zl, records: List[Dict]) -> None:
        """Update ZoomLevel in-memory data structures with new position records."""
        for record in records:
            did = record["decision_id"]
            x = record["x"]
            y = record["y"]
            cid = record.get("cluster", -1)

            zl.positions[did] = (x, y)
            if cid >= 0:
                zl.cluster_assignments[did] = cid
                if cid not in zl.clusters:
                    # Create a minimal cluster entry
                    from app.map_loader import ClusterInfo
                    zl.clusters[cid] = ClusterInfo(
                        cluster_id=cid,
                        zoom_level=zl.level,
                        decision_ids=[],
                        size=0,
                    )
                if did not in zl.clusters[cid].decision_ids:
                    zl.clusters[cid].decision_ids.append(did)
                zl.clusters[cid].size = len(zl.clusters[cid].decision_ids)

        zl.n_decisions = len(zl.positions)
