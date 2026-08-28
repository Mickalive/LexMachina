"""
LexMachina Navigation API
Provides the navigation interface for exploring the case-law map.
Connects corpus data with map artifacts for interactive exploration.

Supports multi-view navigation via section-based map modes and
citation graph integration.
"""
import json
import os
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from .corpus_loader import CorpusLoader
from .map_loader import MapLoader
from .section_modes import SectionModeLoader
from .citation_loader import CitationLoader
from .proximity_explainer import ProximityExplainer
from .zoom_coherence_loader import ZoomCoherenceLoader
from .language_analyzer import LanguageAnalyzer
from .tfidf_proximity import TFIDFProximity


class NavigationAPI:
    """
    Main navigation interface for the LexMachina product.
    
    Provides:
    - Cluster exploration at multiple zoom levels
    - Decision inspection with full text
    - Search across the corpus
    - Statistics and metadata
    - Multi-view map modes (section-based projections)
    - Citation graph navigation
    - User corpus import with map position computation
    """

    # Embedding model used by the fractal-map baseline
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    def __init__(self, corpus_dir: str, results_dir: str):
        self.corpus = CorpusLoader(corpus_dir)
        self.map_loader = MapLoader(results_dir, corpus_dir=corpus_dir)
        self.section_modes = SectionModeLoader(
            section_dir=str(Path(results_dir) / "section_scaled"),
            fallback_dir=str(Path(results_dir) / "section_experiment_clean"),
        )
        self.citation_loader = CitationLoader(
            str(Path(results_dir) / "citation_graph" / "citation_graph.json")
        )
        self.proximity_explainer = ProximityExplainer(self.corpus)
        self.zoom_coherence = ZoomCoherenceLoader(results_dir)
        self.language_analyzer = LanguageAnalyzer()
        self.tfidf_proximity = TFIDFProximity()
        self._initialized = False
        self._map_meta_cache: Dict[str, Dict] = {}
        
        # User import map artifacts
        self._base_embeddings: Optional[np.ndarray] = None
        self._base_decision_ids: List[str] = []
        self._embedding_model: Optional[SentenceTransformer] = None
        self._import_positions_file: Optional[Path] = None
        self._imported_positions: Dict[str, Dict] = {}  # decision_id -> {x, y, cluster, zoom_level, representation}

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
        section_count = self.section_modes.load()
        citation_loaded = self.citation_loader.load()
        zoom_coherence_loaded = self.zoom_coherence.load()
        
        # Build TF-IDF model from corpus
        corpus_decisions = self.corpus.get_all_decisions()
        if corpus_decisions:
            self.tfidf_proximity.build_from_corpus(corpus_decisions)

        # Load base embeddings for user import position computation
        self._load_base_embeddings()
        
        # Set up user import positions file
        self._import_positions_file = Path(self.map_loader.results_dir) / "user_imports" / "imported_positions.jsonl"
        self._import_positions_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_imported_positions()

        self._initialized = True

        return {
            "status": "ready",
            "corpus_decisions": corpus_count,
            "maps_loaded": map_count,
            "section_modes_loaded": section_count,
            "citation_graph_loaded": citation_loaded,
            "zoom_coherence_loaded": zoom_coherence_loaded,
            "tfidf_model_built": self.tfidf_proximity._built,
            "representations": self.map_loader.get_available_representations(),
            "languages": self.corpus.languages,
            "branches": self.corpus.branches,
            "user_import_positions": len(self._imported_positions),
        }

    def _load_base_embeddings(self) -> None:
        """Load base corpus embeddings for k-NN search during user imports."""
        try:
            embeddings_path = Path(self.map_loader.results_dir) / "baseline" / "embeddings.npy"
            metadata_path = Path(self.map_loader.results_dir) / "baseline" / "metadata.json"
            
            if embeddings_path.exists() and metadata_path.exists():
                self._base_embeddings = np.load(embeddings_path)
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                self._base_decision_ids = [m["decision_id"] for m in metadata]
                
                # Load embedding model for new imports
                self._embedding_model = SentenceTransformer(self.EMBEDDING_MODEL)
        except Exception as e:
            # Don't fail initialization if embeddings can't be loaded
            self._base_embeddings = None
            self._base_decision_ids = []
            self._embedding_model = None

    def _get_default_representation(self) -> str:
        """Get the default representation (evaluation v2: center_projected is the ONLY 
        representation passing BOTH adversarial language dominance <0.85 AND 
        jurist pairwise preference >0.5)."""
        # Evaluation v2 CRITICAL FINDING: center_projected is the FIRST and ONLY 
        # representation to pass BOTH adversarial language dominance (0.7593 < 0.85) 
        # AND jurist pairwise preference (0.5215 > 0.5). Also passes Jurivoc (4/5) 
        # and zoom coherence (+4.6%). debiased_citation_blended FAILS v2 adversarial 
        # cross-language (language dominance 0.999 = catastrophic).
        # RECOMMENDATION: Product must adopt center_projected as default map mode.
        return "center_projected"

    def _load_imported_positions(self) -> None:
        """Load previously computed import positions from disk."""
        if not self._import_positions_file or not self._import_positions_file.exists():
            return
        
        try:
            with open(self._import_positions_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    did = record.get("decision_id")
                    if did:
                        self._imported_positions[did] = record
        except Exception:
            pass

    def _save_imported_position(self, record: Dict) -> None:
        """Persist an imported decision's map position to disk."""
        if not self._import_positions_file:
            return
        
        try:
            with open(self._import_positions_file, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _compute_import_positions(
        self,
        imported_decisions: List[Dict],
        representation: Optional[str] = None,
        zoom_level: int = 1,
    ) -> List[Dict]:
        if representation is None:
            representation = self._get_default_representation()
        """
        Compute map positions for newly imported decisions using k-NN in embedding space.
        
        For each imported decision:
        1. Compute its embedding using the same model as the base corpus
        2. Find k nearest neighbors in the base corpus embedding space
        3. Assign to the majority cluster of neighbors
        4. Position near the centroid of neighbors with small jitter
        5. Persist the position for future loads
        
        Returns list of position records for the imported decisions.
        """
        if self._base_embeddings is None or len(self._base_embeddings) == 0:
            return []
        if not self._embedding_model:
            return []
        
        # Get base map data for cluster assignments and positions
        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return []
        
        base_positions = zl.positions
        base_cluster_assignments = zl.cluster_assignments
        
        # Prepare texts for imported decisions
        texts = []
        for d in imported_decisions:
            text = d.get("full_text", "")
            if not text:
                text = f"{d.get('title', '')} {d.get('legal_area', '')}"
            texts.append(text)
        
        # Compute embeddings for imported decisions
        try:
            import_embeddings = self._embedding_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        except Exception:
            return []
        
        results = []
        for i, decision in enumerate(imported_decisions):
            did = decision.get("decision_id", "")
            if not did:
                continue
            
            # Skip if already have a persisted position
            if did in self._imported_positions:
                continue
            
            emb = import_embeddings[i]
            
            # Find k nearest neighbors in base embedding space (cosine similarity)
            # Normalize embeddings for cosine similarity
            emb_norm = emb / (np.linalg.norm(emb) + 1e-8)
            base_norms = np.linalg.norm(self._base_embeddings, axis=1, keepdims=True)
            base_norms[base_norms == 0] = 1
            base_normalized = self._base_embeddings / base_norms
            
            # Cosine similarities
            similarities = base_normalized @ emb_norm
            
            # Get top k neighbors
            k = 5
            top_k_indices = np.argpartition(similarities, -k)[-k:]
            top_k_indices = top_k_indices[np.argsort(similarities[top_k_indices])[::-1]]
            
            # Get neighbor info
            neighbor_clusters = []
            neighbor_positions = []
            for idx in top_k_indices:
                neighbor_did = self._base_decision_ids[idx]
                if neighbor_did in base_cluster_assignments:
                    neighbor_clusters.append(base_cluster_assignments[neighbor_did])
                if neighbor_did in base_positions:
                    neighbor_positions.append(base_positions[neighbor_did])
            
            if not neighbor_clusters:
                continue
            
            # Assign to majority cluster
            from collections import Counter
            cluster_counter = Counter(neighbor_clusters)
            assigned_cluster = cluster_counter.most_common(1)[0][0]
            
            # Position: centroid of neighbor positions with small jitter
            if neighbor_positions:
                centroid_x = np.mean([p[0] for p in neighbor_positions])
                centroid_y = np.mean([p[1] for p in neighbor_positions])
                # Add small jitter to avoid exact overlap
                jitter_scale = 0.01
                x = centroid_x + np.random.normal(0, jitter_scale)
                y = centroid_y + np.random.normal(0, jitter_scale)
            else:
                x, y = 0.0, 0.0
            
            # Build position record
            record = {
                "decision_id": did,
                "x": float(x),
                "y": float(y),
                "cluster": int(assigned_cluster),
                "zoom_level": zoom_level,
                "representation": representation,
                "neighbor_count": len(neighbor_clusters),
                "assigned_via": "knn_embedding",
            }
            
            # Persist
            self._imported_positions[did] = record
            self._save_imported_position(record)
            results.append(record)
        
        return results

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
        representation: Optional[str] = None,
        zoom_level: int = 1,
        map_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        if representation is None:
            representation = self._get_default_representation()
        """
        Get map data for rendering at a specific zoom level.
        
        When map_mode is provided (e.g., "sachverhalt", "erwaegungen"), returns
        positions from the section-based projection for the subset of decisions
        that have section data, with background positions from the main map.
        
        Returns positions, cluster assignments, and cluster summaries.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        # If a section mode is requested, return section-based positions
        if map_mode:
            return self._get_section_mode_map(map_mode, zoom_level)

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
                "is_imported": False,
            })

        # Add imported decision positions for this representation and zoom level
        for did, pos_record in self._imported_positions.items():
            if pos_record.get("representation") == representation and pos_record.get("zoom_level") == zoom_level:
                summary = self.corpus.get_summary(did)
                meta = {}
                if not summary:
                    meta = self._get_map_decision_meta(did)
                positions.append({
                    "decision_id": did,
                    "x": pos_record["x"],
                    "y": pos_record["y"],
                    "cluster": pos_record["cluster"],
                    "language": (summary.get("language") if summary else meta.get("language", "unknown")),
                    "branch": (summary.get("branch") if summary else meta.get("branch", "unknown")),
                    "legal_area": (summary.get("legal_area") if summary else meta.get("legal_area", "unknown")),
                    "has_corpus": did in corpus_ids,
                    "is_imported": True,
                })

        return {
            "representation": representation,
            "zoom_level": zoom_level,
            "n_clusters": zl.n_clusters,
            "n_decisions": zl.n_decisions,
            "clusters": cluster_summaries,
            "positions": positions,
            "map_mode": None,
        }

    def _get_section_mode_map(
        self, mode_name: str, zoom_level: int = 1
    ) -> Dict[str, Any]:
        """Get map data for a section-based mode."""
        mode = self.section_modes.get_mode(mode_name)
        if not mode:
            return {"error": f"Section mode '{mode_name}' not available"}

        # Get the base map for cluster info
        zl = self.map_loader.get_zoom_level("concat_center_tfidf", zoom_level)

        # Build cluster summaries from section clustering
        cluster_summaries = []
        resolution = float(zoom_level) if zoom_level > 0 else 0.5
        section_cluster = self.section_modes.get_clustering(mode_name, resolution)
        if section_cluster:
            labels = section_cluster.get("labels", [])
            n_clusters = section_cluster.get("n_clusters", 0)
            # Group decisions by cluster
            cluster_groups = {}
            for idx, label in enumerate(labels):
                if idx < len(mode.decision_ids):
                    did = mode.decision_ids[idx]
                    if label not in cluster_groups:
                        cluster_groups[label] = []
                    cluster_groups[label].append(did)
            for cid, dids in cluster_groups.items():
                sample_decisions = []
                for did in dids[:5]:
                    summary = self.corpus.get_summary(did)
                    if summary:
                        sample_decisions.append(summary)
                # Compute centroid
                xs = [mode.positions[did][0] for did in dids if did in mode.positions]
                ys = [mode.positions[did][1] for did in dids if did in mode.positions]
                centroid_x = sum(xs) / len(xs) if xs else 0
                centroid_y = sum(ys) / len(ys) if ys else 0
                cluster_summaries.append({
                    "cluster_id": cid,
                    "size": len(dids),
                    "centroid_x": centroid_x,
                    "centroid_y": centroid_y,
                    "sample_decisions": sample_decisions,
                })

        # Build position data for section mode decisions
        positions = []
        corpus_ids = set(self.corpus.get_all_ids())
        for did in mode.decision_ids:
            if did not in mode.positions:
                continue
            x, y = mode.positions[did]
            summary = self.corpus.get_summary(did)
            meta = self._get_map_decision_meta(did)
            positions.append({
                "decision_id": did,
                "x": x,
                "y": y,
                "cluster": -1,  # Will be set from section clustering
                "language": (summary.get("language") if summary else meta.get("language", "unknown")),
                "branch": (summary.get("branch") if summary else meta.get("branch", "unknown")),
                "legal_area": (summary.get("legal_area") if summary else meta.get("legal_area", "unknown")),
                "has_corpus": did in corpus_ids,
                "has_section_data": True,
            })

        # Also include background positions from main map for context
        if zl:
            section_ids = set(mode.decision_ids)
            for did, (x, y) in zl.positions.items():
                if did not in section_ids:
                    summary = self.corpus.get_summary(did)
                    meta = self._get_map_decision_meta(did)
                    positions.append({
                        "decision_id": did,
                        "x": x,
                        "y": y,
                        "cluster": -1,
                        "language": (summary.get("language") if summary else meta.get("language", "unknown")),
                        "branch": (summary.get("branch") if summary else meta.get("branch", "unknown")),
                        "legal_area": (summary.get("legal_area") if summary else meta.get("legal_area", "unknown")),
                        "has_corpus": did in corpus_ids,
                        "has_section_data": False,
                    })

        info = self.section_modes.MODE_INFO.get(mode_name, {})
        return {
            "representation": f"section_{mode_name}",
            "zoom_level": zoom_level,
            "n_clusters": len(cluster_summaries),
            "n_decisions": mode.n_decisions,
            "clusters": cluster_summaries,
            "positions": positions,
            "map_mode": {
                "name": mode_name,
                "label": info.get("label", mode_name),
                "description": info.get("description", ""),
                "section_decisions": mode.n_section_decisions,
                "baseline_decisions": mode.n_baseline_decisions,
                "total_positions": len(positions),
            },
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
        """Get full details of a specific decision, including citation connections."""
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

        # Add section mode clusters
        for mode_name in self.section_modes.get_available_modes():
            mode = self.section_modes.get_mode(mode_name["name"])
            if mode and decision_id in mode.positions:
                resolution = 1.0
                section_cluster = self.section_modes.get_clustering(mode_name["name"], resolution)
                if section_cluster:
                    labels = section_cluster.get("labels", [])
                    idx = mode.decision_ids.index(decision_id) if decision_id in mode.decision_ids else -1
                    if 0 <= idx < len(labels):
                        clusters.append({
                            "representation": f"section_{mode_name['name']}",
                            "zoom_level": int(resolution),
                            "cluster_id": labels[idx],
                        })

        decision["map_clusters"] = clusters

        # Add citation connections
        outgoing = self.citation_loader.get_outgoing(decision_id)
        incoming = self.citation_loader.get_incoming(decision_id)
        citation_counts = self.citation_loader.get_citation_count(decision_id)
        decision["citations"] = {
            "outgoing": outgoing,
            "incoming": incoming[:20],  # Limit incoming for response size
            "counts": citation_counts,
        }

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
        representation: Optional[str] = None,
        zoom_level: int = 2,
        n: int = 10,
    ) -> List[Dict]:
        if representation is None:
            representation = self._get_default_representation()
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
        Computes map positions for imported decisions using k-NN in embedding space.
        Returns import statistics.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        result = self.corpus.import_records(records)
        
        # Compute map positions for newly imported decisions
        if result.get("imported", 0) > 0:
            # Get the imported decision records (those with imported_ids)
            imported_ids = result.get("imported_ids", [])
            imported_decisions = []
            for did in imported_ids:
                d = self.corpus.get(did)
                if d:
                    imported_decisions.append(d.to_full())
            
            # Compute positions for the default representation at zoom level 1
            default_rep = self._get_default_representation()
            position_results = self._compute_import_positions(imported_decisions, default_rep, 1)
            result["map_positions_computed"] = len(position_results)
            result["default_representation"] = default_rep
        
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

    def get_map_modes(self) -> List[Dict[str, Any]]:
        """Get available map modes (section-based views)."""
        if not self._initialized:
            return []

        # Base representation modes
        base_modes = [
            {
                "name": rep,
                "label": rep.replace("_", " ").title(),
                "description": f"Standard embedding projection: {rep}",
                "type": "representation",
                "n_decisions": self.map_loader.get_stats(rep).get("n_decisions", 0),
            }
            for rep in self.map_loader.get_available_representations()
        ]

        # Section-based modes
        section_modes = self.section_modes.get_available_modes()

        return base_modes + section_modes

    def get_citations(
        self, decision_id: str, direction: str = "both", limit: int = 50
    ) -> Dict[str, Any]:
        """Get citation connections for a decision.
        
        Args:
            decision_id: The decision to get citations for
            direction: "outgoing", "incoming", or "both"
            limit: Maximum results per direction
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        result = {"decision_id": decision_id}

        if direction in ("outgoing", "both"):
            outgoing_refs = self.citation_loader.get_outgoing(decision_id)[:limit]
            outgoing_decisions = []
            for ref in outgoing_refs:
                # Try to resolve reference to a corpus decision
                summary = self.corpus.get_summary(ref)
                if summary:
                    outgoing_decisions.append(summary)
                else:
                    outgoing_decisions.append({"reference": ref, "in_corpus": False})
            result["outgoing"] = outgoing_decisions

        if direction in ("incoming", "both"):
            incoming_ids = self.citation_loader.get_incoming(decision_id)[:limit]
            incoming_decisions = []
            for did in incoming_ids:
                summary = self.corpus.get_summary(did)
                if summary:
                    incoming_decisions.append(summary)
                else:
                    incoming_decisions.append({"decision_id": did, "in_corpus": False})
            result["incoming"] = incoming_decisions

        result["counts"] = self.citation_loader.get_citation_count(decision_id)
        return result

    def get_proximity_explanation(
        self, decision_id_a: str, decision_id_b: str
    ) -> Dict[str, Any]:
        """Explain why two decisions are spatially close on the map."""
        if not self._initialized:
            return {"error": "Not initialized"}

        # Get distance from map positions (use evaluation-validated default)
        default_rep = self._get_default_representation()
        positions = self.map_loader.get_positions(default_rep)
        pos_a = positions.get(decision_id_a)
        pos_b = positions.get(decision_id_b)

        if pos_a is None or pos_b is None:
            return {"error": "One or both decisions not found on the map"}

        distance = ((pos_a[0] - pos_b[0]) ** 2 + (pos_a[1] - pos_b[1]) ** 2) ** 0.5

        return self.proximity_explainer.explain(
            decision_id_a, decision_id_b, distance
        )

    def get_cluster_coherence(
        self,
        representation: str,
        zoom_level: int,
        cluster_id: int,
    ) -> Dict[str, Any]:
        """Compute coherence summary for a cluster showing attribute distributions."""
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": "Zoom level not found"}

        cluster = zl.clusters.get(cluster_id)
        if not cluster:
            return {"error": "Cluster not found"}

        # Gather metadata for all decisions in the cluster
        languages = []
        branches = []
        legal_areas = []
        for did in cluster.decision_ids:
            summary = self.corpus.get_summary(did)
            if summary:
                languages.append(summary.get("language", "unknown"))
                branches.append(summary.get("branch") or "unknown")
                legal_areas.append(summary.get("legal_area") or "unknown")

        if not languages:
            return {
                "cluster_id": cluster_id,
                "size": cluster.size,
                "language_distribution": {},
                "branch_distribution": {},
                "legal_area_distribution": {},
                "dominant_language": None,
                "dominant_branch": None,
                "purity_score": 0.0,
                "coherence_warning": "No corpus decisions found in cluster",
            }

        lang_counter = Counter(languages)
        branch_counter = Counter(branches)
        legal_counter = Counter(legal_areas)

        dominant_language = lang_counter.most_common(1)[0][0]
        dominant_branch = branch_counter.most_common(1)[0][0]

        # Purity score: fraction of the most common value across all dimensions
        total = len(languages)
        lang_purity = lang_counter.most_common(1)[0][1] / total
        branch_purity = branch_counter.most_common(1)[0][1] / total
        legal_purity = legal_counter.most_common(1)[0][1] / total
        purity_score = (lang_purity + branch_purity + legal_purity) / 3.0

        # Generate coherence warning if dominated by a single attribute
        coherence_warning = None
        if lang_purity > 0.9:
            coherence_warning = f"cluster dominated by single language: {dominant_language}"
        elif branch_purity > 0.9:
            coherence_warning = f"cluster dominated by single branch: {dominant_branch}"
        elif purity_score > 0.85:
            coherence_warning = "cluster highly homogeneous across all attributes"

        return {
            "cluster_id": cluster_id,
            "size": cluster.size,
            "language_distribution": dict(lang_counter),
            "branch_distribution": dict(branch_counter),
            "legal_area_distribution": dict(legal_counter),
            "dominant_language": dominant_language,
            "dominant_branch": dominant_branch,
            "purity_score": round(purity_score, 3),
            "coherence_warning": coherence_warning,
        }

    def get_map_data_with_language_filter(
        self,
        representation: str,
        zoom_level: int,
        languages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get map data with language filtering.

        Returns all positions but marks filtered-out ones with filtered_out: true.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": f"Zoom level {zoom_level} not available for {representation}"}

        filter_set = set(languages) if languages else None

        # Build cluster summaries with decision info
        cluster_summaries = []
        for cid, cluster in zl.clusters.items():
            sample_decisions = []
            for did in cluster.decision_ids[:5]:
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

        # Build position data with filtering flag
        positions = []
        corpus_ids = set(self.corpus.get_all_ids())
        for did, (x, y) in zl.positions.items():
            summary = self.corpus.get_summary(did)
            meta = {}
            if not summary:
                meta = self._get_map_decision_meta(did)
            lang = summary.get("language") if summary else meta.get("language", "unknown")
            filtered_out = filter_set is not None and lang not in filter_set

            positions.append({
                "decision_id": did,
                "x": x,
                "y": y,
                "cluster": zl.cluster_assignments.get(did, -1),
                "language": lang,
                "branch": (summary.get("branch") if summary else meta.get("branch", "unknown")),
                "legal_area": (summary.get("legal_area") if summary else meta.get("legal_area", "unknown")),
                "has_corpus": did in corpus_ids,
                "filtered_out": filtered_out,
            })

        return {
            "representation": representation,
            "zoom_level": zoom_level,
            "n_clusters": zl.n_clusters,
            "n_decisions": zl.n_decisions,
            "clusters": cluster_summaries,
            "positions": positions,
            "language_filter": list(filter_set) if filter_set else None,
            "map_mode": None,
        }

    def get_zoom_coherence_summary(self) -> Dict[str, Any]:
        """Get zoom coherence summary from fractal-map experiment results."""
        if not self._initialized:
            return {"error": "Not initialized"}
        return self.zoom_coherence.get_summary()

    def get_zoom_coherence_flat_baseline(self) -> Dict[str, Any]:
        """Get flat baseline metrics at different resolutions."""
        if not self._initialized:
            return {"error": "Not initialized"}
        return self.zoom_coherence.get_flat_baseline()

    def get_cluster_language_analysis(
        self,
        representation: str,
        zoom_level: int,
        cluster_id: int,
    ) -> Dict[str, Any]:
        """Analyze language dominance for a specific cluster."""
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": "Zoom level not found"}

        cluster = zl.clusters.get(cluster_id)
        if not cluster:
            return {"error": "Cluster not found"}

        # Get decisions in this cluster
        decisions = []
        for did in cluster.decision_ids:
            summary = self.corpus.get_summary(did)
            if summary:
                decisions.append(summary)

        return self.language_analyzer.analyze_cluster_language_dominance(
            decisions, cluster_id
        )

    def get_cross_language_neighbors(
        self,
        decision_id: str,
        n_neighbors: int = 10,
    ) -> Dict[str, Any]:
        """Find cross-language neighbors for a decision."""
        if not self._initialized:
            return {"error": "Not initialized"}

        summary = self.corpus.get_summary(decision_id)
        if not summary:
            return {"error": f"Decision {decision_id} not found"}

        decision_language = summary.get("language", "unknown")
        
        # Get all positions (default to hierarchical_leiden)
        positions = self.map_loader.get_positions("hierarchical_leiden")
        
        # Build corpus summaries dict
        corpus_ids = set(self.corpus.get_all_ids())
        corpus_summaries = {}
        for did in corpus_ids:
            s = self.corpus.get_summary(did)
            if s:
                corpus_summaries[did] = s

        # Find neighbors (same language and cross-language)
        same_lang_neighbors = self.language_analyzer.find_cross_language_neighbors(
            decision_id, decision_language, positions, corpus_summaries,
            n_neighbors=n_neighbors, same_language_only=True
        )
        
        cross_lang_neighbors = self.language_analyzer.find_cross_language_neighbors(
            decision_id, decision_language, positions, corpus_summaries,
            n_neighbors=n_neighbors, same_language_only=False
        )

        return {
            "decision_id": decision_id,
            "decision_language": decision_language,
            "same_language_neighbors": same_lang_neighbors,
            "cross_language_neighbors": [n for n in cross_lang_neighbors if n["is_cross_language"]][:n_neighbors],
            "all_neighbors": cross_lang_neighbors[:n_neighbors],
        }

    def get_temporal_map_data(
        self,
        representation: Optional[str] = None,
        zoom_level: int = 1,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        if representation is None:
            representation = self._get_default_representation()
        """Get map data filtered to decisions within a year range.

        Returns positions with year metadata for each decision, cluster summaries
        computed from the filtered subset, and temporal distribution statistics.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": f"Zoom level {zoom_level} not available for {representation}"}

        corpus_ids = set(self.corpus.get_all_ids())
        year_counts: Dict[int, int] = {}
        filtered_positions = []
        all_positions = []

        for did, (x, y) in zl.positions.items():
            summary = self.corpus.get_summary(did)
            meta = self._get_map_decision_meta(did)
            decision_date = (
                summary.get("decision_date", "") if summary
                else meta.get("decision_date", "")
            )
            year = self._extract_year(decision_date)

            pos_entry = {
                "decision_id": did,
                "x": x,
                "y": y,
                "cluster": zl.cluster_assignments.get(did, -1),
                "language": (summary.get("language") if summary else meta.get("language", "unknown")),
                "branch": (summary.get("branch") if summary else meta.get("branch", "unknown")),
                "legal_area": (summary.get("legal_area") if summary else meta.get("legal_area", "unknown")),
                "has_corpus": did in corpus_ids,
                "year": year,
            }

            all_positions.append(pos_entry)

            # Apply year filter
            if year_start is not None and year is not None and year < year_start:
                continue
            if year_end is not None and year is not None and year > year_end:
                continue

            filtered_positions.append(pos_entry)
            if year is not None:
                year_counts[year] = year_counts.get(year, 0) + 1

        # Build cluster summaries from filtered positions
        cluster_ids_in_filtered = set(p["cluster"] for p in filtered_positions if p["cluster"] >= 0)
        cluster_summaries = []
        for cid in sorted(cluster_ids_in_filtered):
            members = [p for p in filtered_positions if p["cluster"] == cid]
            sample_decisions = []
            for p in members[:5]:
                summary = self.corpus.get_summary(p["decision_id"])
                if summary:
                    sample_decisions.append(summary)
            xs = [p["x"] for p in members]
            ys = [p["y"] for p in members]
            cluster_summaries.append({
                "cluster_id": cid,
                "size": len(members),
                "centroid_x": sum(xs) / len(xs) if xs else 0,
                "centroid_y": sum(ys) / len(ys) if ys else 0,
                "sample_decisions": sample_decisions,
            })

        # Compute temporal stats
        years_sorted = sorted(year_counts.keys())
        temporal_stats = {
            "total_positions": len(all_positions),
            "filtered_positions": len(filtered_positions),
            "year_range": {
                "min": years_sorted[0] if years_sorted else None,
                "max": years_sorted[-1] if years_sorted else None,
            },
            "year_distribution": year_counts,
            "filter_applied": {
                "year_start": year_start,
                "year_end": year_end,
            },
        }

        return {
            "representation": representation,
            "zoom_level": zoom_level,
            "n_clusters": len(cluster_summaries),
            "n_decisions": len(filtered_positions),
            "clusters": cluster_summaries,
            "positions": filtered_positions,
            "temporal_stats": temporal_stats,
            "map_mode": None,
        }

    @staticmethod
    def _extract_year(decision_date: str) -> Optional[int]:
        """Extract a 4-digit year from a decision date string."""
        if not decision_date:
            return None
        # Handle ISO format (YYYY-MM-DD) or plain YYYY
        try:
            year = int(decision_date[:4])
            if 1900 <= year <= 2100:
                return year
        except (ValueError, IndexError):
            pass
        return None

    def get_text_similarity(
        self,
        decision_id_a: str,
        decision_id_b: str,
    ) -> Dict[str, Any]:
        """Get text-based similarity between two decisions using TF-IDF."""
        if not self._initialized:
            return {"error": "Not initialized"}

        corpus_summaries = {}
        for did in self.corpus.get_all_ids():
            s = self.corpus.get_summary(did)
            if s:
                corpus_summaries[did] = s

        return self.tfidf_proximity.get_similarity_explanation(
            decision_id_a, decision_id_b, corpus_summaries
        )

    def export_map_data(
        self,
        representation: Optional[str] = None,
        zoom_level: int = 1,
        format: str = "json",
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        if representation is None:
            representation = self._get_default_representation()
        """Export map data for external use.

        Args:
            representation: Map representation to export
            zoom_level: Zoom level to export
            format: Export format ("json" or "csv")
            include_metadata: Whether to include decision metadata in export

        Returns:
            Export data or error info
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": f"Zoom level {zoom_level} not available for {representation}"}

        # Build export data
        corpus_ids = set(self.corpus.get_all_ids())
        positions = zl.positions
        cluster_assignments = zl.cluster_assignments

        # Collect all data
        export_rows = []
        for did, (x, y) in positions.items():
            summary = self.corpus.get_summary(did)
            meta = {}
            if not summary:
                meta = self._get_map_decision_meta(did)

            row = {
                "decision_id": did,
                "x": round(x, 6),
                "y": round(y, 6),
                "cluster": cluster_assignments.get(did, -1),
                "language": summary.get("language") if summary else meta.get("language", "unknown"),
                "branch": summary.get("branch") if summary else meta.get("branch", "unknown"),
                "legal_area": summary.get("legal_area") if summary else meta.get("legal_area", "unknown"),
                "has_corpus": did in corpus_ids,
            }

            if include_metadata and summary:
                row.update({
                    "docket_number": summary.get("docket_number", ""),
                    "decision_date": summary.get("decision_date", ""),
                    "title": summary.get("title", ""),
                    "chamber": summary.get("chamber", ""),
                    "outcome": summary.get("outcome", ""),
                    "text_length": summary.get("text_length", 0),
                })

            export_rows.append(row)

        # Build cluster summaries
        clusters = []
        for cid, cluster in zl.clusters.items():
            clusters.append({
                "cluster_id": cid,
                "size": cluster.size,
                "centroid_x": round(cluster.centroid_x, 6),
                "centroid_y": round(cluster.centroid_y, 6),
            })

        export_data = {
            "representation": representation,
            "zoom_level": zoom_level,
            "n_clusters": zl.n_clusters,
            "n_decisions": zl.n_decisions,
            "clusters": clusters,
            "positions": export_rows,
        }

        if format == "json":
            return {"format": "json", "data": export_data}
        elif format == "csv":
            # Generate CSV content
            import csv
            import io
            output = io.StringIO()
            if export_rows:
                fieldnames = list(export_rows[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(export_rows)
            return {"format": "csv", "data": output.getvalue()}
        else:
            return {"error": f"Unsupported format: {format}. Use 'json' or 'csv'."}

    def export_cluster_decisions(
        self,
        representation: str,
        zoom_level: int,
        cluster_id: int,
        format: str = "json",
    ) -> Dict[str, Any]:
        """Export all decisions in a specific cluster."""
        if not self._initialized:
            return {"error": "Not initialized"}

        zl = self.map_loader.get_zoom_level(representation, zoom_level)
        if not zl:
            return {"error": f"Zoom level {zoom_level} not available for {representation}"}

        cluster = zl.clusters.get(cluster_id)
        if not cluster:
            return {"error": f"Cluster {cluster_id} not found"}

        corpus_ids = set(self.corpus.get_all_ids())
        export_rows = []

        for did in cluster.decision_ids:
            summary = self.corpus.get_summary(did)
            meta = self._get_map_decision_meta(did) if not summary else {}
            x, y = zl.positions.get(did, (0, 0))

            row = {
                "decision_id": did,
                "x": round(x, 6),
                "y": round(y, 6),
                "cluster": cluster_id,
                "language": summary.get("language") if summary else meta.get("language", "unknown"),
                "branch": summary.get("branch") if summary else meta.get("branch", "unknown"),
                "legal_area": summary.get("legal_area") if summary else meta.get("legal_area", "unknown"),
                "has_corpus": did in corpus_ids,
            }
            if summary:
                row.update({
                    "docket_number": summary.get("docket_number", ""),
                    "decision_date": summary.get("decision_date", ""),
                    "title": summary.get("title", ""),
                    "chamber": summary.get("chamber", ""),
                    "outcome": summary.get("outcome", ""),
                })
            export_rows.append(row)

        if format == "json":
            return {
                "format": "json",
                "data": {
                    "representation": representation,
                    "zoom_level": zoom_level,
                    "cluster_id": cluster_id,
                    "cluster_size": cluster.size,
                    "centroid_x": round(cluster.centroid_x, 6),
                    "centroid_y": round(cluster.centroid_y, 6),
                    "decisions": export_rows,
                }
            }
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            if export_rows:
                fieldnames = list(export_rows[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(export_rows)
            return {"format": "csv", "data": output.getvalue()}
        else:
            return {"error": f"Unsupported format: {format}. Use 'json' or 'csv'."}
