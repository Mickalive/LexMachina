"""
LexMachina Navigation API
Provides the navigation interface for exploring the case-law map.
Connects corpus data with map artifacts for interactive exploration.

Supports multi-view navigation via section-based map modes and
citation graph integration.
"""
import json
import os
import time
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
        
        # Server-side caching for expensive computations
        self._cluster_coherence_cache: Dict[str, Dict] = {}
        self._cross_language_cache: Dict[str, Dict] = {}
        self._text_similarity_cache: Dict[str, Dict] = {}
        self._proximity_cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}
        
        # User import map artifacts
        self._base_embeddings: Optional[np.ndarray] = None
        self._base_decision_ids: List[str] = []
        self._embedding_model: Optional[SentenceTransformer] = None
        self._import_positions_file: Optional[Path] = None
        self._imported_positions: Dict[Tuple[str, str], Dict] = {}  # (decision_id, representation) -> {x, y, cluster, zoom_level, representation}

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

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments."""
        return f"{prefix}:{':'.join(str(a) for a in args)}"

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[key]) < self._cache_ttl

    def _set_cache(self, cache_dict: Dict, key: str, value: Dict) -> None:
        """Set cache entry with timestamp."""
        cache_dict[key] = value
        self._cache_timestamps[key] = time.time()

    def _get_cache(self, cache_dict: Dict, key: str) -> Optional[Dict]:
        """Get cache entry if valid."""
        if self._is_cache_valid(key):
            return cache_dict.get(key)
        # Clean up expired entry
        if key in cache_dict:
            del cache_dict[key]
        if key in self._cache_timestamps:
            del self._cache_timestamps[key]
        return None

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
        """Get the default representation for map navigation.
        
        Factory direction v6 (CRITICAL FIX per evaluation v6): 
        center_projected_64dim_hierarchical is the DEFAULT map mode.
        
        Evaluation v6 finding: 768-dim center_projected FAILS jurist pairwise (0.491).
        Evaluation v3 validation: 64-dim frozen PCA center_projected PASSES BOTH 
        adversarial gates (language dominance 0.766 < 0.85, jurist pairwise 0.512 > 0.5).
        
        This representation uses:
        - 64-dim frozen PCA of center_projected embeddings (language-debiased)
        - Hierarchical Leiden clustering (nesting=1.0, purity=0.9718)
        - 2-resolution ladder: zoom 0 (7 coarse) → zoom 1 (108 fine)
        - Coarse purity: 0.9761, Hierarchical purity: 0.9718
        
        The 768-dim center_projected_hierarchical is available as LEGACY mode for comparison.
        """
        return "center_projected_64dim_hierarchical"

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
                    rep = record.get("representation", "")
                    if did:
                        self._imported_positions[(did, rep)] = record
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
            
            # Skip if already have a persisted position for this representation
            if (did, representation) in self._imported_positions:
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
            self._imported_positions[(did, representation)] = record
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
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        if representation is None:
            representation = self._get_default_representation()
        """
        Get map data for rendering at a specific zoom level.
        
        When map_mode is provided (e.g., "sachverhalt", "erwaegungen"), returns
        positions from the section-based projection for the subset of decisions
        that have section data, with background positions from the main map.
        
        Supports pagination via limit/offset for large-scale rendering.
        
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
        for (key_did, key_rep), pos_record in self._imported_positions.items():
            if pos_record.get("representation") == representation and pos_record.get("zoom_level") == zoom_level:
                summary = self.corpus.get_summary(key_did)
                meta = {}
                if not summary:
                    meta = self._get_map_decision_meta(key_did)
                positions.append({
                    "decision_id": key_did,
                    "x": pos_record["x"],
                    "y": pos_record["y"],
                    "cluster": pos_record["cluster"],
                    "language": (summary.get("language") if summary else meta.get("language", "unknown")),
                    "branch": (summary.get("branch") if summary else meta.get("branch", "unknown")),
                    "legal_area": (summary.get("legal_area") if summary else meta.get("legal_area", "unknown")),
                    "has_corpus": key_did in corpus_ids,
                    "is_imported": True,
                })

        # Apply pagination if requested (for large-scale rendering)
        total_positions = len(positions)
        paginated_positions = positions
        pagination = None
        if limit is not None or offset is not None:
            start = offset or 0
            end = start + (limit or total_positions)
            paginated_positions = positions[start:end]
            pagination = {
                "total": total_positions,
                "offset": start,
                "limit": limit or total_positions,
                "returned": len(paginated_positions),
                "has_more": end < total_positions,
            }

        return {
            "representation": representation,
            "zoom_level": zoom_level,
            "n_clusters": zl.n_clusters,
            "n_decisions": zl.n_decisions,
            "clusters": cluster_summaries,
            "positions": paginated_positions,
            "map_mode": None,
            "pagination": pagination,
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
            
            # Compute positions for ALL available representations
            default_rep = self._get_default_representation()
            all_representations = self.map_loader.get_available_representations()
            representations_positioned = []
            total_positions = 0
            
            for rep in all_representations:
                zoom_levels = self.map_loader.get_zoom_levels(rep)
                if not zoom_levels:
                    continue
                first_zl = zoom_levels[0]
                position_results = self._compute_import_positions(imported_decisions, rep, first_zl)
                if position_results:
                    total_positions += len(position_results)
                    representations_positioned.append({
                        "representation": rep,
                        "zoom_level": first_zl,
                        "positions_computed": len(position_results),
                    })
            
            result["map_positions_computed"] = total_positions
            result["representations_positioned"] = representations_positioned
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
        """Get available map modes (section-based views and representations)."""
        if not self._initialized:
            return []

        # Display names for representations
        display_names = {
            "concat_center_tfidf": "Combined Legal + Semantic",
            "baseline": "Semantic Embedding (Baseline)",
            "hdbscan": "HDBSCAN Clustering",
            "hierarchical_leiden": "Multi-Resolution Leiden (Flat)",
            "true_hierarchical_leiden": "True Hierarchical Leiden (127 clusters)",
            "fractal_map_7res": "7-Resolution Fractal Map",
            "debiased_citation_blended": "Citation-Blended (Eval Default)",
            "legal_cited_decisions": "Doctrinal Lineage (Cited TF-IDF)",
            "center_projected": "Language-Debiased (768-dim)",
            "center_projected_hierarchical": "Language-Debiased Hierarchical (768-dim)",
            "center_projected_64dim_hierarchical": "Language-Debiased Hierarchical (64-dim) ★ DEFAULT",
            "hybrid_alpha_0_3": "Hybrid: Citation + Legal (30/70)",
            "hybrid_alpha_0_5": "Hybrid: Citation + Legal (50/50)",
            "legal_issues_outcomes": "Legal Issues & Outcomes",
            "linear_metric_best": "Cross-Lingual Legal (Linear Metric)",
            "mahalanobis_best": "Cross-Lingual Legal (Mahalanobis Metric)",
            "cited_decisions_tfidf": "Doctrinal Lineage (Cited Decisions TF-IDF)",
            "hybrid_cited_decisions_0.3": "Citation-Proximity Blend (α=0.3)",
            "hybrid_cited_decisions_0.5": "Balanced Citation-Legal Blend (α=0.5)",
            "hybrid_cited_decisions_0.7": "Legal-Invariant Blend (α=0.7)",
            "cited_decisions_tfidf_hybrid_cp64_0.3": "Production Hybrid CP64 (α=0.3)",
            "cited_decisions_tfidf_hybrid_cp64_0.5": "Production Hybrid CP64 (α=0.5)",
            "cited_decisions_tfidf_hybrid_cp64_0.7": "BEST Production Hybrid CP64 (α=0.7) ★",
            # NEW: Cited Outcome Hybrids (BEST PRODUCTION/FRACTAL - factory direction v9)
            "cited_outcome_hybrid_0.5": "BEST PRODUCTION: Citation + Outcome (α=0.5) ★ JP=0.799, LangDom=0.491",
            "cited_outcome_hybrid_0.7": "BEST FRACTAL: Citation + Outcome (α=0.7) ★ HierAdv=+0.370",
            # Citation Role Views (ACCEPTED - legal-distance v6)
            "following_alpha0.3": "Citation Role: Following (α=0.3) ★",
            "criticizing_alpha0.3": "Citation Role: Criticizing (α=0.3) ★",
            "citing_alpha0.3": "Citation Role: Overruling (α=0.3) ★",
        }

        # Evidence tier info
        evidence_tiers = {}
        for rep in self.map_loader.get_available_representations():
            m = self.map_loader.get_map(rep)
            if m:
                evidence_tiers[rep] = m.metadata.get("evidence_tier", "UNKNOWN")

        # Base representation modes
        base_modes = [
            {
                "name": rep,
                "label": display_names.get(rep, rep.replace("_", " ").title()),
                "description": self._get_representation_description(rep),
                "type": "representation",
                "evidence_tier": evidence_tiers.get(rep, "UNKNOWN"),
                "n_decisions": self.map_loader.get_stats(rep).get("n_decisions", 0),
                "zoom_levels": len(self.map_loader.get_zoom_levels(rep)),
            }
            for rep in self.map_loader.get_available_representations()
        ]

        # Section-based modes
        section_modes = self.section_modes.get_available_modes()

        return base_modes + section_modes

    def _get_representation_description(self, rep: str) -> str:
        """Get description for a representation."""
        descriptions = {
            "concat_center_tfidf": "Combined language-debiased semantic + TF-IDF on Erwaegungen sections. Baseline best performer.",
            "baseline": "Raw multilingual semantic embeddings (paraphrase-multilingual-mpnet-base-v2).",
            "hdbscan": "Density-based clustering (HDBSCAN) with varying min_cluster_size. Handles noise.",
            "hierarchical_leiden": "Flat multi-resolution Leiden at resolutions 0.25→3.0. Not true hierarchical.",
            "true_hierarchical_leiden": "TRUE hierarchical Leiden: coarse (res=0.5) then fine (res=3.0) within parents. Nesting=1.0, 127 fine clusters in 8 coarse. Branch purity 0.963 > flat Leiden 0.875.",
            "fractal_map_7res": "7-resolution ladder (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0) with legal coherence metrics. Hierarchical Leiden included as level 7.",
            "debiased_citation_blended": "Evaluation default (14/14 PASS). PCA debiasing (n_pca=1) + citation graph embeddings (α=0.7). Citation heritage AUC 0.9102.",
            "legal_cited_decisions": "ACCEPTED legal-distance signal (14/14 PASS). TF-IDF on cited decisions only. Citation heritage AUC 0.9719. Best for citation-proximity.",
            "center_projected": "Language-debiased by removing 1st PCA component. Evaluation v2: ONLY passes BOTH adversarial gates (lang_dom=0.759, pairwise=0.522).",
            "center_projected_hierarchical": "Hierarchical Leiden on pure center_projected. Nesting=1.0, purity=0.9638, 108 fine clusters in 7 coarse. LEGACY: 768-dim.",
            "center_projected_64dim_hierarchical": "DEFAULT map mode. 64-dim frozen PCA of center_projected. Nesting=1.0, purity=0.9718. Evaluation v3: lang_dom=0.766, pairwise=0.512. BOTH gates PASS.",
            "hybrid_alpha_0_3": "Hybrid: 30% center_projected + 70% legal_cited_decisions. EXPLORATORY.",
            "hybrid_alpha_0_5": "Hybrid: 50% center_projected + 50% legal_cited_decisions. EXPLORATORY.",
            "legal_issues_outcomes": "Legal-specific TF-IDF on statutes+cited+outcomes+legal_area. ACCEPTED with warnings (fails 4/14).",
            "linear_metric_best": "ACCEPTED. Linear metric learning on center_projected (epoch 4). JP=0.6847, LangDom=0.680. Improves cross-lingual alignment.",
            "mahalanobis_best": "ACCEPTED. Mahalanobis metric learning on center_projected (epoch 4). JP=0.6781, LangDom=0.684. Learns full metric.",
            "cited_decisions_tfidf": "ACCEPTED. Zero-shot TF-IDF on cited decisions only. JP=0.6889, LangDom=0.612. BEST zero-shot representation.",
            "hybrid_cited_decisions_0.3": "ACCEPTED. 30% center_projected + 70% cited_decisions_tfidf. JP=0.525, LangDom=0.760.",
            "hybrid_cited_decisions_0.5": "ACCEPTED. 50% center_projected + 50% cited_decisions_tfidf. JP=0.611, LangDom=0.706.",
            "hybrid_cited_decisions_0.7": "ACCEPTED. 70% center_projected + 30% cited_decisions_tfidf. JP=0.676, LangDom=0.648.",
            "cited_decisions_tfidf_hybrid_cp64_0.3": "ACCEPTED. 30% center_projected_64dim + 70% cited_decisions_tfidf (PCA-64D). JP=0.535, LangDom=0.748.",
            "cited_decisions_tfidf_hybrid_cp64_0.5": "ACCEPTED. 50% center_projected_64dim + 50% cited_decisions_tfidf (PCA-64D). JP=0.628, LangDom=0.684.",
            "cited_decisions_tfidf_hybrid_cp64_0.7": "ACCEPTED. BEST production hybrid per factory direction. 70% center_projected_64dim + 30% cited_decisions_tfidf (PCA-64D). JP=0.661, LangDom=0.652.",
            # Citation Role Views (ACCEPTED - legal-distance v6)
            "following_alpha0.3": "ACCEPTED. Citation role: Following (precedent extension). Hybrid 30% center_projected_64dim + 70% following signal. JP=0.5485, LangDom=0.7529. Fine purity=0.9672.",
            "criticizing_alpha0.3": "ACCEPTED. Citation role: Criticizing (precedent criticism). Hybrid 30% center_projected_64dim + 70% criticizing signal. JP=0.5485, LangDom=0.7529. Fine purity=0.9672.",
            "citing_alpha0.3": "ACCEPTED. Citation role: Overruling (precedent reversal). Hybrid 30% center_projected_64dim + 70% overruling signal. JP=0.5485, LangDom=0.7529. Fine purity=0.9672.",
            # NEW: Cited Outcome Hybrids (ACCEPTED - factory direction v9)
            "cited_outcome_hybrid_0.5": "ACCEPTED. BEST PRODUCTION hybrid per factory direction v9. 50% cited_decisions_tfidf + 50% outcome signal. JP=0.7990, LangDom=0.4911. Both adversarial gates PASS. LangDom < 0.6 target ACHIEVED.",
            "cited_outcome_hybrid_0.7": "ACCEPTED. BEST FRACTAL hybrid per factory direction v9. 70% cited_decisions_tfidf + 30% outcome signal. HierAdv=+0.3703. Both adversarial gates PASS.",
        }
        return descriptions.get(rep, f"Representation: {rep}")

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
        """Explain why two decisions are spatially close on the map.
        
        Uses server-side caching to avoid recomputing for the same pair.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        # Check cache (order-independent key)
        pair = tuple(sorted([decision_id_a, decision_id_b]))
        cache_key = self._get_cache_key("proximity", pair[0], pair[1])
        cached = self._get_cache(self._proximity_cache, cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached

        # Get distance from map positions (use evaluation-validated default)
        default_rep = self._get_default_representation()
        positions = self.map_loader.get_positions(default_rep)
        pos_a = positions.get(decision_id_a)
        pos_b = positions.get(decision_id_b)

        if pos_a is None or pos_b is None:
            return {"error": "One or both decisions not found on the map"}

        distance = ((pos_a[0] - pos_b[0]) ** 2 + (pos_a[1] - pos_b[1]) ** 2) ** 0.5

        result = self.proximity_explainer.explain(
            decision_id_a, decision_id_b, distance
        )
        
        # Cache the result
        self._set_cache(self._proximity_cache, cache_key, result)
        return result

    def get_cluster_coherence(
        self,
        representation: str,
        zoom_level: int,
        cluster_id: int,
    ) -> Dict[str, Any]:
        """Compute coherence summary for a cluster showing attribute distributions.
        
        Uses server-side caching to avoid recomputing for the same cluster.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        # Check cache
        cache_key = self._get_cache_key("cluster_coherence", representation, zoom_level, cluster_id)
        cached = self._get_cache(self._cluster_coherence_cache, cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached

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
            result = {
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
            self._set_cache(self._cluster_coherence_cache, cache_key, result)
            return result

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

        result = {
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
        
        # Cache the result
        self._set_cache(self._cluster_coherence_cache, cache_key, result)
        return result

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
        """Find cross-language neighbors for a decision.
        
        Uses server-side caching to avoid recomputing for the same decision.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        # Check cache
        cache_key = self._get_cache_key("cross_language", decision_id, n_neighbors)
        cached = self._get_cache(self._cross_language_cache, cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached

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

        result = {
            "decision_id": decision_id,
            "decision_language": decision_language,
            "same_language_neighbors": same_lang_neighbors,
            "cross_language_neighbors": [n for n in cross_lang_neighbors if n["is_cross_language"]][:n_neighbors],
            "all_neighbors": cross_lang_neighbors[:n_neighbors],
        }
        
        # Cache the result
        self._set_cache(self._cross_language_cache, cache_key, result)
        return result

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
        """Get text-based similarity between two decisions using TF-IDF.
        
        Uses server-side caching to avoid recomputing for the same pair.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        # Check cache (order-independent key)
        pair = tuple(sorted([decision_id_a, decision_id_b]))
        cache_key = self._get_cache_key("text_similarity", pair[0], pair[1])
        cached = self._get_cache(self._text_similarity_cache, cache_key)
        if cached is not None:
            cached["cached"] = True
            return cached

        corpus_summaries = {}
        for did in self.corpus.get_all_ids():
            s = self.corpus.get_summary(did)
            if s:
                corpus_summaries[did] = s

        result = self.tfidf_proximity.get_similarity_explanation(
            decision_id_a, decision_id_b, corpus_summaries
        )
        
        # Cache the result
        self._set_cache(self._text_similarity_cache, cache_key, result)
        return result

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

    def submit_feedback(
        self,
        feedback_type: str,
        payload: Dict[str, Any],
        jurist_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit jurist feedback for evaluation purposes.
        
        Args:
            feedback_type: Type of feedback (e.g., "pairwise_preference", "cluster_quality", "map_mode_rating")
            payload: Feedback data specific to the type
            jurist_id: Optional anonymized jurist identifier
            
        Returns:
            Status of feedback submission
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        import time
        from pathlib import Path
        
        # Feedback storage directory
        feedback_dir = Path(self.map_loader.results_dir) / "jurist_feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        feedback_file = feedback_dir / "feedback.jsonl"

        # Build feedback record
        record = {
            "timestamp": time.time(),
            "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "feedback_type": feedback_type,
            "jurist_id": jurist_id or "anonymous",
            "payload": payload,
        }

        # Persist to JSONL
        try:
            with open(feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            return {"error": f"Failed to persist feedback: {e}"}

        return {
            "status": "accepted",
            "feedback_id": f"{feedback_type}_{int(time.time())}",
            "message": "Feedback recorded successfully",
        }

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get statistics about collected jurist feedback."""
        if not self._initialized:
            return {"error": "Not initialized"}

        from pathlib import Path
        feedback_dir = Path(self.map_loader.results_dir) / "jurist_feedback"
        feedback_file = feedback_dir / "feedback.jsonl"

        if not feedback_file.exists():
            return {"total_feedback": 0, "by_type": {}, "by_jurist": {}}

        counts_by_type = Counter()
        counts_by_jurist = Counter()
        total = 0

        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        total += 1
                        counts_by_type[record.get("feedback_type", "unknown")] += 1
                        counts_by_jurist[record.get("jurist_id", "anonymous")] += 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        return {
            "total_feedback": total,
            "by_type": dict(counts_by_type),
            "by_jurist": dict(counts_by_jurist),
        }

    def compare_maps(
        self,
        representation_a: str,
        representation_b: str,
        zoom_level: int = 1,
    ) -> Dict[str, Any]:
        """Compare two map representations side by side.
        
        Returns aligned cluster data showing which decisions move between clusters
        when switching representations, enabling users to understand map mode differences.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        zl_a = self.map_loader.get_zoom_level(representation_a, zoom_level)
        zl_b = self.map_loader.get_zoom_level(representation_b, zoom_level)

        if not zl_a:
            return {"error": f"Zoom level {zoom_level} not available for {representation_a}"}
        if not zl_b:
            return {"error": f"Zoom level {zoom_level} not available for {representation_b}"}

        # Get positions and cluster assignments for both
        pos_a = zl_a.positions
        pos_b = zl_b.positions
        cluster_a = zl_a.cluster_assignments
        cluster_b = zl_b.cluster_assignments

        # Find common decisions
        common_decisions = set(pos_a.keys()) & set(pos_b.keys())

        # Build comparison data for common decisions
        comparison = []
        for did in common_decisions:
            ca = cluster_a.get(did, -1)
            cb = cluster_b.get(did, -1)
            if ca >= 0 and cb >= 0:
                x_a, y_a = pos_a[did]
                x_b, y_b = pos_b[did]
                
                # Get decision summary for metadata
                summary = self.corpus.get_summary(did)
                meta = {}
                if not summary:
                    meta = self._get_map_decision_meta(did)
                
                comparison.append({
                    "decision_id": did,
                    "cluster_a": ca,
                    "cluster_b": cb,
                    "x_a": round(x_a, 6),
                    "y_a": round(y_a, 6),
                    "x_b": round(x_b, 6),
                    "y_b": round(y_b, 6),
                    "displacement": round(((x_a - x_b) ** 2 + (y_a - y_b) ** 2) ** 0.5, 6),
                    "language": summary.get("language") if summary else meta.get("language", "unknown"),
                    "branch": summary.get("branch") if summary else meta.get("branch", "unknown"),
                    "legal_area": summary.get("legal_area") if summary else meta.get("legal_area", "unknown"),
                })

        # Compute aggregate statistics
        total = len(comparison)
        if total == 0:
            return {"error": "No common decisions found between representations"}

        # Cluster transition matrix
        transitions = Counter()
        for c in comparison:
            transitions[(c["cluster_a"], c["cluster_b"])] += 1

        # Average displacement
        avg_displacement = sum(c["displacement"] for c in comparison) / total
        max_displacement = max(c["displacement"] for c in comparison)

        # Decisions that changed clusters
        cluster_changes = sum(1 for c in comparison if c["cluster_a"] != c["cluster_b"])
        stability_rate = 1.0 - (cluster_changes / total) if total > 0 else 0.0

        return {
            "representation_a": representation_a,
            "representation_b": representation_b,
            "zoom_level": zoom_level,
            "n_common_decisions": total,
            "stability_rate": round(stability_rate, 4),
            "avg_displacement": round(avg_displacement, 6),
            "max_displacement": round(max_displacement, 6),
            "cluster_changes": cluster_changes,
            "cluster_transitions": {f"{a}->{b}": count for (a, b), count in transitions.most_common(20)},
            "decisions": comparison,
        }

    def validate_representations(self) -> Dict[str, Any]:
        """Validate all loaded representations and report their status.
        
        Tests each representation by:
        1. Verifying it loads without errors
        2. Checking it has positions at all zoom levels
        3. Verifying cluster assignments are valid
        4. Checking metadata has required fields (evidence_tier, etc.)
        
        Returns a validation report per representation.
        """
        if not self._initialized:
            return {"error": "Not initialized"}
        
        results = {}
        all_reps = self.map_loader.get_available_representations()
        
        for rep in all_reps:
            rep_result = {
                "status": "PASS",
                "zoom_levels": {},
                "issues": [],
                "metadata": {},
            }
            
            try:
                map_state = self.map_loader.get_map(rep)
                if not map_state:
                    rep_result["status"] = "FAIL"
                    rep_result["issues"].append("Map state not loaded")
                    results[rep] = rep_result
                    continue
                
                # Check required metadata fields
                meta = map_state.metadata
                rep_result["metadata"] = {
                    "evidence_tier": meta.get("evidence_tier", "UNKNOWN"),
                    "n_decisions": map_state.n_decisions,
                    "n_zoom_levels": len(map_state.zoom_levels),
                }
                
                if "evidence_tier" not in meta:
                    rep_result["issues"].append("Missing evidence_tier in metadata")
                
                # Test each zoom level
                for zl_level in self.map_loader.get_zoom_levels(rep):
                    zl = self.map_loader.get_zoom_level(rep, zl_level)
                    if not zl:
                        rep_result["status"] = "FAIL"
                        rep_result["issues"].append(f"Zoom level {zl_level} returned None")
                        continue
                    
                    zl_info = {
                        "n_clusters": zl.n_clusters,
                        "n_decisions": zl.n_decisions,
                        "n_positions": len(zl.positions),
                        "has_assignments": len(zl.cluster_assignments) > 0,
                    }
                    
                    # Validate: positions should match decision count
                    if zl.n_decisions > 0 and len(zl.positions) != zl.n_decisions:
                        rep_result["issues"].append(
                            f"Zoom {zl_level}: positions ({len(zl.positions)}) != "
                            f"decisions ({zl.n_decisions})"
                        )
                    
                    # Validate: assignments should cover all positions
                    if len(zl.positions) > 0 and len(zl.cluster_assignments) < len(zl.positions):
                        rep_result["issues"].append(
                            f"Zoom {zl_level}: assignments ({len(zl.cluster_assignments)}) < "
                            f"positions ({len(zl.positions)})"
                        )
                    
                    # Validate: clusters should not be empty
                    if zl.n_clusters == 0 and zl.n_decisions > 0:
                        rep_result["issues"].append(f"Zoom {zl_level}: 0 clusters but {zl.n_decisions} decisions")
                    
                    # Try getting cluster detail
                    try:
                        if zl.clusters:
                            first_cid = list(zl.clusters.keys())[0]
                            detail = self.get_cluster_detail(rep, zl_level, first_cid)
                            if "error" in detail:
                                rep_result["issues"].append(f"Zoom {zl_level}: cluster detail error: {detail['error']}")
                    except Exception as e:
                        rep_result["issues"].append(f"Zoom {zl_level}: cluster detail exception: {e}")
                    
                    rep_result["zoom_levels"][zl_level] = zl_info
                
                if rep_result["issues"]:
                    rep_result["status"] = "WARN"
                
            except Exception as e:
                rep_result["status"] = "FAIL"
                rep_result["issues"].append(f"Exception during validation: {e}")
            
            results[rep] = rep_result
        
        # Summary
        passing = sum(1 for r in results.values() if r["status"] == "PASS")
        warnings = sum(1 for r in results.values() if r["status"] == "WARN")
        failing = sum(1 for r in results.values() if r["status"] == "FAIL")
        
        return {
            "total_representations": len(all_reps),
            "passing": passing,
            "warnings": warnings,
            "failing": failing,
            "representations": results,
        }

    def get_webgl_data(
        self,
        representation: str,
        zoom_level: int,
        map_mode: str = None
    ) -> Dict[str, Any]:
        """Get WebGL-optimized rendering data for a map representation.
        
        Returns flat arrays for positions, colors, radii, imported flags
        suitable for direct upload to GPU buffers.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        if map_mode:
            map_data = self.get_map_data(map_mode=map_mode, zoom_level=zoom_level)
        else:
            map_data = self.get_map_data(representation=representation, zoom_level=zoom_level)

        positions = map_data.get('positions', [])
        clusters = map_data.get('clusters', [])

        # Get imported decision IDs
        imported_ids = set(key[0] for key in self._imported_positions.keys())

        # Color palettes
        LANG_COLORS = {'de': '#4dabf7', 'fr': '#ffd43b', 'it': '#51cf66', 'unknown': '#666'}
        COLORS = [
            '#7c8aff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8',
            '#20c997', '#ff922b', '#4dabf7', '#e599f7', '#69db7c',
            '#fcc419', '#ff8787', '#748ffc', '#63e6be', '#da77f2',
            '#a9e34b', '#ffa94d', '#74c0fc', '#b2f2bb', '#f783ac',
        ]

        # Helper to convert hex to RGBA
        def hex_to_rgba(hex_color: str, alpha: float = 1.0):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b, alpha)

        n_points = len(positions)
        
        # Pre-allocate arrays
        positions_array = []
        colors_array = []
        radii_array = []
        imported_array = []

        # Cluster color map
        cluster_color_map = {}
        for i, cluster in enumerate(clusters):
            cid = cluster['cluster_id']
            color_hex = COLORS[i % len(COLORS)]
            cluster_color_map[cid] = hex_to_rgba(color_hex, 0.8)

        # Fill arrays
        for p in positions:
            # Position (world coordinates)
            positions_array.append(p['x'])
            positions_array.append(p['y'])
            
            # Color (cluster color)
            cid = p.get('cluster', 0)
            r, g, b, a = cluster_color_map.get(cid, (0.5, 0.5, 0.5, 0.8))
            colors_array.extend([r, g, b, a])
            
            # Radius
            is_section = p.get('has_section_data', True)
            radii_array.append(4.0 if is_section else 2.5)
            
            # Imported flag
            imported_array.append(1.0 if p.get('decision_id') in imported_ids else 0.0)

        # Prepare cluster hulls (simplified bounding boxes for now)
        cluster_hulls = []
        cluster_points = {}
        for p in positions:
            cid = p.get('cluster', 0)
            if cid not in cluster_points:
                cluster_points[cid] = []
            cluster_points[cid].append((p['x'], p['y']))

        for i, cluster in enumerate(clusters):
            cid = cluster['cluster_id']
            if cid in cluster_points and len(cluster_points[cid]) >= 3:
                points = cluster_points[cid]
                # Simple bounding box as hull approximation
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                hull = [
                    (min(xs), min(ys)),
                    (max(xs), min(ys)),
                    (max(xs), max(ys)),
                    (min(xs), max(ys)),
                ]
                color_hex = COLORS[i % len(COLORS)]
                r, g, b, a = hex_to_rgba(color_hex, 0.1)
                cluster_hulls.append({
                    'cluster_id': cid,
                    'points': hull,
                    'color': [r, g, b, a]
                })

        # Build transform info
        if positions:
            x_min = min(p['x'] for p in positions)
            x_max = max(p['x'] for p in positions)
            y_min = min(p['y'] for p in positions)
            y_max = max(p['y'] for p in positions)
        else:
            x_min = x_max = y_min = y_max = 0

        return {
            'points': {
                'positions': positions_array,
                'colors': colors_array,
                'radii': radii_array,
                'imported': imported_array,
                'count': n_points
            },
            'clusters': clusters,
            'hulls': cluster_hulls,
            'transform': {
                'xMin': x_min,
                'xMax': x_max,
                'yMin': y_min,
                'yMax': y_max,
                'scale': 1.0,
                'offsetX': 0,
                'offsetY': 0
            }
        }
