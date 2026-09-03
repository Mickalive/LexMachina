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
from typing import Dict, List, Optional, Set, Tuple, Any
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
from .spatial_index import SpatialIndex
from .lod_manager import LODManager


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
        self._webgl_cache: Dict[str, Dict] = {}  # WebGL data cache
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}
        
        # Spatial index for fast viewport queries (KD-tree)
        self._spatial_indices: Dict[str, SpatialIndex] = {}  # representation -> SpatialIndex
        self.lod_manager = LODManager()
        
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

        # Build spatial indices for fast viewport queries
        self._build_spatial_indices()

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

    def _build_spatial_indices(self) -> None:
        """Build KD-tree spatial indices for fast viewport queries.
        
        Builds one SpatialIndex per representation for the default zoom level.
        This enables O(sqrt(N) + k) viewport culling instead of O(N) brute-force.
        Tries to load from persisted artifacts for fast startup at 174k scale.
        """
        import time as _time
        t0 = _time.time()
        count = 0
        loaded_from_disk = 0
        
        persist_dir = Path(self.map_loader.results_dir) / "spatial_indices"
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        for rep in self.map_loader.get_available_representations():
            zl = self.map_loader.get_zoom_level(rep, 1)  # Default zoom level
            if zl and zl.positions:
                persist_path = persist_dir / f"spatial_{rep.replace('/', '_')}"
                
                # Try to load from disk first
                si = SpatialIndex.load(persist_path)
                if si is None:
                    # Build and persist
                    si = SpatialIndex(persist_path=persist_path)
                    si.build(zl.positions)
                else:
                    loaded_from_disk += 1
                
                self._spatial_indices[rep] = si
                count += 1
        
        elapsed = _time.time() - t0
        if count > 0:
            print(f"[SpatialIndex] Built/loaded {count} spatial indices ({loaded_from_disk} from disk) in {elapsed:.3f}s")

    def _get_spatial_index(self, representation: str) -> Optional[SpatialIndex]:
        """Get or build spatial index for a representation."""
        if representation in self._spatial_indices:
            return self._spatial_indices[representation]
        
        # Build on demand if not pre-built
        zl = self.map_loader.get_zoom_level(representation, 1)
        if zl and zl.positions:
            persist_dir = Path(self.map_loader.results_dir) / "spatial_indices"
            persist_path = persist_dir / f"spatial_{representation.replace('/', '_')}"
            
            si = SpatialIndex.load(persist_path)
            if si is None:
                si = SpatialIndex(persist_path=persist_path)
                si.build(zl.positions)
            
            self._spatial_indices[representation] = si
            return si
        return None

    def _get_default_representation(self) -> str:
        """Get the default representation for map navigation.
        
        Factory direction v15 (v15b-audit CRITICAL + v16 ACCEPTED):
        cited_outcome_hybrid_0.5 is the PRODUCTION DEFAULT.
        
        v15b-audit CRITICAL: NO representation passes all benchmarks;
        PRODUCTION DEFAULT is cited_outcome_hybrid_0.5 because it wins
        full-harness LangDom/JuristPref/Boilerplate. Hypothesis: SVD
        information leakage may favor hybrid in production deployment.
        Best for user-imported corpora where branch metadata unavailable.
        
        This representation uses:
        - 50% cited_decisions_tfidf + 50% outcome signal
        - JP=0.799 (train), LangDom=0.491, both adversarial gates PASS
        - ACCEPTED evidence tier, production-viable
        
        center_projected_64dim_hierarchical available as LEGACY mode for comparison.
        linear_hybrid05_concat (JP=0.838, best stable combination) available as
        COMBINATION mode for doctrinal/Jurivoc exploration.
        """
        return "cited_outcome_hybrid_0.5"

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

    def search_decisions(
        self, query: str, limit: int = 20, language: Optional[str] = None
    ) -> List[Dict]:
        """Search decisions by text content with optional language filtering.

        Args:
            query: Text search query
            limit: Maximum results
            language: Optional language filter. Supports:
                - Single language: "de", "fr", "it"
                - Compound (AND): "de,fr" (German AND French results)
                - None: all languages
        """
        if not self._initialized:
            return []

        results = self.corpus.search(query, limit)

        if language is None:
            return results

        # Parse compound language (e.g. "de,fr" or "de+fr" or "de fr")
        # Accept comma, plus, or space as separators
        target_langs: set = set()
        for part in language.replace("+", ",").replace(" ", ",").split(","):
            lang = part.strip()
            if lang:
                target_langs.add(lang)
        if not target_langs:
            return results

        return [r for r in results if r.get("language") in target_langs]

    def get_language_stats(self) -> Dict[str, Any]:
        """Get language statistics including per-language counts,
        per-language-branch counts, and language distribution per year."""
        if not self._initialized:
            return {"error": "Not initialized"}

        lang_counts: Dict[str, int] = {}
        lang_branch_counts: Dict[str, int] = {}
        lang_year_counts: Dict[str, Dict[int, int]] = {}

        for d in self.corpus.decisions.values():
            lang = d.language
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

            branch = d.branch or "unknown"
            key = f"{lang}:{branch}"
            lang_branch_counts[key] = lang_branch_counts.get(key, 0) + 1

            year = self._extract_year(d.decision_date)
            if year is not None:
                if lang not in lang_year_counts:
                    lang_year_counts[lang] = {}
                lang_year_counts[lang][year] = lang_year_counts[lang].get(year, 0) + 1

        # Convert year dicts to {year: count} sorted
        year_distributions: Dict[str, Dict[int, int]] = {}
        for lang, yd in lang_year_counts.items():
            year_distributions[lang] = dict(sorted(yd.items()))

        return {
            "total": self.corpus.size,
            "per_language": lang_counts,
            "per_language_branch": lang_branch_counts,
            "year_distribution": year_distributions,
        }

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
        
        For batch imports (192k+ scale): processes representations incrementally
        with progress tracking. Returns import statistics including per-representation
        timing and success status.
        
        Returns import statistics.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        result = self.corpus.import_records(records)
        
        # Compute map positions for newly imported decisions
        if result.get("imported", 0) > 0:
            imported_ids = result.get("imported_ids", [])
            imported_decisions = []
            for did in imported_ids:
                d = self.corpus.get(did)
                if d:
                    imported_decisions.append(d.to_full())
            
            # Compute positions for ALL available representations with progress
            default_rep = self._get_default_representation()
            all_representations = self.map_loader.get_available_representations()
            representations_positioned = []
            total_positions = 0
            batch_start_time = time.time()
            
            for rep_idx, rep in enumerate(all_representations):
                rep_start = time.time()
                zoom_levels = self.map_loader.get_zoom_levels(rep)
                if not zoom_levels:
                    representations_positioned.append({
                        "representation": rep,
                        "status": "skipped",
                        "reason": "no_zoom_levels",
                    })
                    continue
                first_zl = zoom_levels[0]
                position_results = self._compute_import_positions(imported_decisions, rep, first_zl)
                rep_elapsed = time.time() - rep_start
                
                if position_results:
                    total_positions += len(position_results)
                    representations_positioned.append({
                        "representation": rep,
                        "zoom_level": first_zl,
                        "positions_computed": len(position_results),
                        "elapsed_ms": round(rep_elapsed * 1000, 1),
                        "status": "ok",
                    })
                else:
                    representations_positioned.append({
                        "representation": rep,
                        "zoom_level": first_zl,
                        "positions_computed": 0,
                        "elapsed_ms": round(rep_elapsed * 1000, 1),
                        "status": "no_positions",
                        "reason": "no_embeddings_or_model",
                    })
            
            result["map_positions_computed"] = total_positions
            result["representations_positioned"] = representations_positioned
            result["representations_total"] = len(all_representations)
            result["representations_ok"] = sum(1 for r in representations_positioned if r.get("status") == "ok")
            result["representations_skipped"] = sum(1 for r in representations_positioned if r.get("status") in ("skipped", "no_positions"))
            result["batch_elapsed_ms"] = round((time.time() - batch_start_time) * 1000, 1)
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
            "center_projected_64dim_hierarchical": "Language-Debiased Hierarchical (64-dim) ★ LEGACY DEFAULT",
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
                "design_pattern": self.map_loader.get_representation_metadata(rep).get("design_pattern"),
                "purpose": self.map_loader.get_representation_metadata(rep).get("purpose"),
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
            "center_projected_64dim_hierarchical": "LEGACY DEFAULT. 64-dim frozen PCA of center_projected. Nesting=1.0, purity=0.9718. Eval v3: lang_dom=0.766, pairwise=0.512. BOTH gates PASS. Replaced by cited_outcome_hybrid_0.5 per v15b-audit.",
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
            "cited_outcome_hybrid_0.5": "PRODUCTION DEFAULT per v15b-audit CRITICAL. Wins full-harness LangDom/JuristPref/Boilerplate. 50% cited_decisions_tfidf + 50% outcome signal. JP=0.7990, LangDom=0.4911. Both adversarial gates PASS. Best for user-imported corpora.",
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
        map_mode: str = None,
        bbox: Optional[Dict[str, float]] = None,
        import_ids: Optional[Set[str]] = None,
        lod_level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get WebGL-optimized rendering data for a map representation.
        
        Returns flat arrays for positions, colors, radii, imported flags
        suitable for direct upload to GPU buffers.
        
        For 174k+ scale: uses numpy vectorized ops, server-side caching,
        optional viewport bbox filtering, and LOD decimation to minimize
        data transfer.
        
        Args:
            representation: Map representation name
            zoom_level: Zoom level
            map_mode: Optional section mode override
            bbox: Optional viewport bounding box {xMin, yMin, xMax, yMax}.
                  When provided, only points inside the bbox are returned,
                  dramatically reducing payload for large corpora.
            lod_level: Optional LOD level override.
                       0 = cluster centroids only.
                       1 = super-cluster centroids.
                       None or 2 = full detail (current behavior).
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        # Check cache for non-viewport requests (viewport requests are dynamic)
        cache_key = None
        if bbox is None:
            mode_key = map_mode or representation
            lod_key = lod_level if lod_level is not None else 2
            cache_key = self._get_cache_key("webgl", mode_key, zoom_level, lod_key)
            cached = self._get_cache(self._webgl_cache, cache_key)
            if cached is not None:
                cached["cached"] = True
                return cached

        if map_mode:
            map_data = self.get_map_data(map_mode=map_mode, zoom_level=zoom_level)
        else:
            map_data = self.get_map_data(representation=representation, zoom_level=zoom_level)

        positions = map_data.get('positions', [])
        clusters = map_data.get('clusters', [])

        if not positions:
            return {
                'points': {'positions': [], 'colors': [], 'radii': [], 'imported': [], 'decision_ids': [], 'cluster_ids': [], 'languages': [], 'count': 0},
                'clusters': clusters,
                'hulls': [],
                'transform': {'xMin': 0, 'xMax': 0, 'yMin': 0, 'yMax': 0, 'scale': 1.0, 'offsetX': 0, 'offsetY': 0}
            }

        # Get imported decision IDs (caller override takes precedence)
        if import_ids is not None:
            imported_ids = import_ids
        else:
            imported_ids = set(key[0] for key in self._imported_positions.keys())

        # Color palette (pre-computed as RGBA floats for vectorized lookup)
        COLORS = [
            '#7c8aff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8',
            '#20c997', '#ff922b', '#4dabf7', '#e599f7', '#69db7c',
            '#fcc419', '#ff8787', '#748ffc', '#63e6be', '#da77f2',
            '#a9e34b', '#ffa94d', '#74c0fc', '#b2f2bb', '#f783ac',
        ]

        def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
            h = hex_color.lstrip('#')
            if len(h) == 3:
                h = ''.join([c*2 for c in h])
            return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)

        # Build cluster -> color RGBA map
        cluster_color_rgba = {}
        for i, cluster in enumerate(clusters):
            cid = cluster['cluster_id']
            r, g, b = hex_to_rgb(COLORS[i % len(COLORS)])
            cluster_color_rgba[cid] = (r, g, b, 0.8)

        # --- Build numpy arrays for all positions ---
        n_total = len(positions)

        # Build cluster id index map
        cluster_id_to_idx = {c['cluster_id']: i for i, c in enumerate(clusters)}
        default_rgba = (0.5, 0.5, 0.5, 0.8)

        languages = []
        # Vectorized extraction from positions list-of-dicts (174k-optimized)
        if n_total > 0:
            xs = np.array([p['x'] for p in positions], dtype=np.float64)
            ys = np.array([p['y'] for p in positions], dtype=np.float64)
            decision_ids = [p.get('decision_id', '') for p in positions]
            cluster_ids = np.array([p.get('cluster', 0) for p in positions], dtype=np.int32)
            has_section = np.array([p.get('has_section_data', True) for p in positions], dtype=bool)
            languages = [p.get('language', 'unknown') for p in positions]
        else:
            xs = np.empty(0, dtype=np.float64)
            ys = np.empty(0, dtype=np.float64)
            decision_ids = []
            cluster_ids = np.empty(0, dtype=np.int32)
            has_section = np.empty(0, dtype=bool)
            languages = []

        # --- LOD level override via LODManager ---
        effective_lod = lod_level
        if effective_lod is not None and effective_lod < 2 and n_total > 0:
            positions_arr = np.column_stack((xs, ys))
            lod_result = self.lod_manager.compute_lod_levels(
                positions_arr, clusters, effective_lod
            )
            lod_points = lod_result["points"]
            lod_n = lod_result["point_count"]
            lod_sizes = lod_result["cluster_sizes"]

            # Viewport culling on LOD-decimated points
            if bbox and lod_n > 0:
                culled_mask = self.lod_manager.cull_to_viewport(lod_points, bbox)
                lod_points = lod_points[culled_mask]
                lod_sizes = lod_sizes[culled_mask]
                lod_n = int(lod_points.shape[0])

            # Build flat arrays for WebGL
            positions_array = np.empty(lod_n * 2, dtype=np.float32)
            if lod_n > 0:
                positions_array[0::2] = lod_points[:, 0]
                positions_array[1::2] = lod_points[:, 1]

            # Cluster color for each centroid/super-centroid
            colors_array = np.empty(lod_n * 4, dtype=np.float32)
            radii_array = np.empty(lod_n, dtype=np.float32)
            imported_array = np.zeros(lod_n, dtype=np.float32)

            # Build decision_ids, cluster_ids, and languages for LOD points
            lod_decision_ids = []
            lod_cluster_ids = np.zeros(lod_n, dtype=np.int32)
            lod_languages = []

            imported_set = imported_ids

            # --- Vectorized LOD color assignment (174k-optimized) ---
            # Build centroids array from clusters for vectorized distance computation
            n_cl = len(clusters)
            cl_centroids = np.empty((n_cl, 2), dtype=np.float64)
            cl_cids = np.empty(n_cl, dtype=np.int32)
            for idx_c, cl in enumerate(clusters):
                cl_centroids[idx_c, 0] = cl["centroid_x"]
                cl_centroids[idx_c, 1] = cl["centroid_y"]
                cl_cids[idx_c] = cl["cluster_id"]

            if lod_n > 0 and n_cl > 0:
                # Compute distances from each LOD point to each cluster centroid: (lod_n, n_cl)
                # Using broadcasting: (lod_n, 1, 2) - (1, n_cl, 2) -> (lod_n, n_cl, 2) -> sum -> (lod_n, n_cl)
                diffs = lod_points[:, np.newaxis, :] - cl_centroids[np.newaxis, :, :]
                dists_sq = np.sum(diffs * diffs, axis=2)  # (lod_n, n_cl)
                nearest_idx = np.argmin(dists_sq, axis=1)  # (lod_n,)
                lod_cluster_ids = cl_cids[nearest_idx]

                # Vectorized RGBA lookup
                LOD_COLOR_PALETTE = np.empty((len(COLORS), 4), dtype=np.float32)
                for ci, hex_c in enumerate(COLORS):
                    r, g, b = hex_to_rgb(hex_c)
                    LOD_COLOR_PALETTE[ci] = [r, g, b, 0.8]
                cid_to_color = {}
                for idx_c, cl in enumerate(clusters):
                    cid_to_color[cl["cluster_id"]] = idx_c % len(COLORS)
                color_indices_lod = np.array([cid_to_color.get(int(c), 0) for c in lod_cluster_ids], dtype=np.int32)
                colors_array = LOD_COLOR_PALETTE[color_indices_lod].ravel()

                # Vectorized radius computation
                radii_array = np.clip(np.sqrt(lod_sizes) * 2, 3.0, 20.0).astype(np.float32)
            else:
                lod_cluster_ids = np.zeros(lod_n, dtype=np.int32)
                radii_array = np.full(lod_n, 5.0, dtype=np.float32)

            # Build decision_ids and languages for LOD points
            lod_decision_ids = [f"lod_cluster_{int(lod_cluster_ids[j])}_{j}" for j in range(lod_n)]
            lod_languages = ['unknown'] * lod_n

            n_culled = lod_n
            n_total_pre_lod = n_total
            n_after_lod = lod_n
            cluster_hulls = []
            visible_cluster_ids = set()

            # Build transform from full data extents
            transform = {
                "xMin": float(xs.min()),
                "xMax": float(xs.max()),
                "yMin": float(ys.min()),
                "yMax": float(ys.max()),
                "scale": 1.0,
                "offsetX": 0,
                "offsetY": 0,
            }

            result = {
                "points": {
                    "positions": positions_array.tolist(),
                    "colors": colors_array.tolist(),
                    "radii": radii_array.tolist(),
                    "imported": imported_array.tolist(),
                    "decision_ids": lod_decision_ids,
                    "cluster_ids": lod_cluster_ids.tolist(),
                    "languages": lod_languages,
                    "count": n_culled,
                },
                "clusters": clusters,
                "hulls": cluster_hulls,
                "transform": transform,
                "lod_decimation": {
                    "applied": True,
                    "original_count": n_total_pre_lod,
                    "decimated_count": n_after_lod,
                    "zoom_level": zoom_level,
                },
                "viewport_culling": {
                    "requested": bbox is not None,
                    "total_positions": n_total_pre_lod,
                    "visible_positions": n_culled,
                    "culled_count": n_total_pre_lod - n_culled,
                    "visible_clusters": len(clusters),
                },
                "lod_level": effective_lod,
            }

            # Cache non-viewport requests
            if cache_key is not None:
                self._set_cache(self._webgl_cache, cache_key, result)

            return result

        # --- LOD: Level-of-detail point decimation for 174k+ scale ---
        n_total_pre_lod = n_total
        LOD_LIMITS = {0: 15000, 1: 30000}
        lod_limit = LOD_LIMITS.get(zoom_level)
        if lod_limit and n_total > lod_limit:
            grid_size = max(1, int(np.sqrt(n_total / lod_limit)))
            x_min_range, x_max_range = xs.min(), xs.max()
            y_min_range, y_max_range = ys.min(), ys.max()
            x_range = x_max_range - x_min_range if x_max_range > x_min_range else 1.0
            y_range = y_max_range - y_min_range if y_max_range > y_min_range else 1.0

            grid_x = ((xs - x_min_range) / x_range * grid_size).astype(int)
            grid_y = ((ys - y_min_range) / y_range * grid_size).astype(int)
            grid_keys = grid_x * 100000 + grid_y

            _, unique_indices = np.unique(grid_keys, return_index=True)
            lod_mask = np.zeros(n_total, dtype=bool)
            lod_mask[unique_indices] = True
            n_after_lod = int(lod_mask.sum())
        else:
            lod_mask = np.ones(n_total, dtype=bool)
            n_after_lod = n_total

        # Apply LOD mask, then viewport culling
        xs = xs[lod_mask]
        ys = ys[lod_mask]
        cluster_ids = cluster_ids[lod_mask]
        has_section = has_section[lod_mask]
        # Vectorized: extract decision_ids and languages using boolean mask
        decision_ids_np = np.array(decision_ids)
        decision_ids = decision_ids_np[lod_mask].tolist()
        n_total = len(xs)

        # --- Viewport culling using KD-tree spatial index ---
        culled_mask = np.ones(n_total, dtype=bool)
        visible_cluster_ids = set()
        
        spatial_index = self._spatial_indices.get(representation)
        # Only use spatial index for zoom level 1 (where it was built from).
        # For other zoom levels, fall back to brute-force to correctly handle
        # imported positions which are not in the spatial index.
        use_spatial_index = (spatial_index is not None and 
                            zoom_level == 1 and
                            bbox and 'xMin' in bbox and 'xMax' in bbox and 'yMin' in bbox and 'yMax' in bbox)
        if use_spatial_index:
            # Use KD-tree for fast viewport query (O(sqrt(N) + k) vs O(N))
            visible_ids = spatial_index.range_query(
                bbox['xMin'], bbox['yMin'], bbox['xMax'], bbox['yMax']
            )
            visible_set = set(visible_ids)
            # Vectorized set membership: convert visible_set to numpy array and use np.isin
            visible_arr = np.array(list(visible_set))
            decision_ids_arr = np.array(decision_ids)
            visible_mask_1d = np.isin(decision_ids_arr, visible_arr)
            culled_mask = visible_mask_1d
        elif bbox and 'xMin' in bbox and 'xMax' in bbox and 'yMin' in bbox and 'yMax' in bbox:
            # Fallback: brute-force numpy boolean mask (handles imported positions correctly)
            x_min_v = bbox['xMin']
            x_max_v = bbox['xMax']
            y_min_v = bbox['yMin']
            y_max_v = bbox['yMax']
            culled_mask = (xs >= x_min_v) & (xs <= x_max_v) & (ys >= y_min_v) & (ys <= y_max_v)

        n_culled = int(culled_mask.sum())

        # If viewport culling removed too many points, we need cluster hulls
        # for clusters that have ANY visible point (for context)
        visible_cluster_ids = set(cluster_ids[culled_mask].tolist()) if n_culled < n_total else set()

        # Apply mask
        xs_v = xs[culled_mask]
        ys_v = ys[culled_mask]
        cluster_ids_v = cluster_ids[culled_mask]
        has_section_v = has_section[culled_mask]
        # Vectorized extraction of decision_ids and languages via boolean mask
        decision_ids_v_arr = np.array(decision_ids)
        decision_ids_v = decision_ids_v_arr[culled_mask].tolist()
        languages_v = np.array(languages)[culled_mask].tolist()

        # --- Vectorized color + radius assembly ---
        positions_array = np.empty(n_culled * 2, dtype=np.float32)
        positions_array[0::2] = xs_v
        positions_array[1::2] = ys_v

        colors_array = np.empty(n_culled * 4, dtype=np.float32)
        radii_array = np.empty(n_culled, dtype=np.float32)
        imported_array = np.zeros(n_culled, dtype=np.float32)

        imported_set = imported_ids  # already a set

        # --- Vectorized color + radius assembly (174k-optimized) ---
        # Build cluster-id-to-color-index mapping for vectorized lookup
        cid_to_color_idx = np.full(int(cluster_ids_v.max()) + 1 if n_culled > 0 else 0, -1, dtype=np.int32)
        for idx_c, cl in enumerate(clusters):
            cid_val = cl['cluster_id']
            if cid_val < len(cid_to_color_idx):
                cid_to_color_idx[cid_val] = idx_c % len(COLORS)

        # Vectorized RGBA lookup via index array
        default_color_idx = 0  # fallback index
        safe_cids = np.clip(cluster_ids_v, 0, len(cid_to_color_idx) - 1) if n_culled > 0 else np.array([], dtype=np.int32)
        color_indices = cid_to_color_idx[safe_cids] if n_culled > 0 else np.array([], dtype=np.int32)
        color_indices[color_indices < 0] = default_color_idx

        # Pre-compute COLOR_PALETTE as (N_COLORS, 4) float32 array
        COLOR_PALETTE = np.empty((len(COLORS), 4), dtype=np.float32)
        for ci, hex_c in enumerate(COLORS):
            r, g, b = hex_to_rgb(hex_c)
            COLOR_PALETTE[ci] = [r, g, b, 0.8]

        if n_culled > 0:
            colors_array = COLOR_PALETTE[color_indices].ravel()
        # radii: vectorized
        radii_array = np.where(has_section_v, 4.0, 2.5).astype(np.float32)
        # imported: vectorized set membership
        if imported_set:
            imported_id_arr = np.array(list(imported_set))
            # Build a set-check via broadcast for small sets, or vectorized for large
            decision_ids_v_arr = np.array(decision_ids_v)
            if len(imported_set) < 5000:
                imported_array = np.isin(decision_ids_v_arr, imported_id_arr).astype(np.float32)
            else:
                imported_set_for_np = set(imported_id_arr.tolist())
                imported_array = np.array([1.0 if did in imported_set_for_np else 0.0 for did in decision_ids_v], dtype=np.float32)

        # --- Cluster hulls (bounding boxes) ---
        cluster_hulls = []
        # Group culled positions by cluster
        if n_culled > 0:
            unique_clusters = np.unique(cluster_ids_v)
            for cid in unique_clusters:
                mask_c = cluster_ids_v == cid
                cx = xs_v[mask_c]
                cy = ys_v[mask_c]
                if len(cx) >= 3:
                    color_rgba = cluster_color_rgba.get(int(cid), default_rgba)
                    cluster_hulls.append({
                        'cluster_id': int(cid),
                        'points': [
                            [float(cx.min()), float(cy.min())],
                            [float(cx.max()), float(cy.min())],
                            [float(cx.max()), float(cy.max())],
                            [float(cx.min()), float(cy.max())],
                        ],
                        'color': list(color_rgba[:3]) + [0.1]
                    })

        # For clusters that are NOT visible but have nearby points,
        # add their bounding box hulls as "context hulls" (faded)
        if visible_cluster_ids and clusters:
            all_cluster_bboxes = {}
            for i, cluster in enumerate(clusters):
                cid = cluster['cluster_id']
                if cid not in visible_cluster_ids:
                    # Check if this cluster's centroid is near the viewport
                    if bbox and 'xMin' in bbox:
                        cx = cluster.get('centroid_x', 0)
                        cy = cluster.get('centroid_y', 0)
                        margin = max(bbox['xMax'] - bbox['xMin'], bbox['yMax'] - bbox['yMin']) * 0.1
                        if (bbox['xMin'] - margin <= cx <= bbox['xMax'] + margin and
                            bbox['yMin'] - margin <= cy <= bbox['yMax'] + margin):
                            # Find this cluster's positions in the full (unculled) data
                            c_mask = cluster_ids == cid
                            if c_mask.sum() >= 3:
                                color_rgba = cluster_color_rgba.get(cid, default_rgba)
                                cluster_hulls.append({
                                    'cluster_id': cid,
                                    'points': [
                                        [float(xs[c_mask].min()), float(ys[c_mask].min())],
                                        [float(xs[c_mask].max()), float(ys[c_mask].min())],
                                        [float(xs[c_mask].max()), float(ys[c_mask].max())],
                                        [float(xs[c_mask].min()), float(ys[c_mask].max())],
                                    ],
                                    'color': list(color_rgba[:3]) + [0.04],
                                    'context_only': True
                                })

        # Build transform from full data extents (not culled)
        transform = {
            'xMin': float(xs.min()),
            'xMax': float(xs.max()),
            'yMin': float(ys.min()),
            'yMax': float(ys.max()),
            'scale': 1.0,
            'offsetX': 0,
            'offsetY': 0
        }

        result = {
            'points': {
                'positions': positions_array.tolist(),
                'colors': colors_array.tolist(),
                'radii': radii_array.tolist(),
                'imported': imported_array.tolist(),
                'decision_ids': decision_ids_v,
                'cluster_ids': cluster_ids_v.tolist(),
                'languages': languages_v,
                'count': n_culled
            },
            'clusters': clusters,
            'hulls': cluster_hulls,
            'transform': transform,
            'lod_decimation': {
                'applied': zoom_level in LOD_LIMITS and n_after_lod < n_total_pre_lod,
                'original_count': n_total_pre_lod,
                'decimated_count': n_after_lod,
                'zoom_level': zoom_level,
            },
            'viewport_culling': {
                'requested': bbox is not None,
                'total_positions': n_total,
                'visible_positions': n_culled,
                'culled_count': n_total - n_culled,
                'visible_clusters': len(visible_cluster_ids) if visible_cluster_ids else len(clusters),
            },
            'lod_level': lod_level,
        }

        # Cache non-viewport requests
        if cache_key is not None:
            self._set_cache(self._webgl_cache, cache_key, result)

        return result

    def get_design_patterns(self) -> Dict[str, Any]:
        """Return design pattern classification for all representations.
        
        Design patterns group representations by their strengths:
        - DEFAULT: Production default (passes both adversarial gates)
        - LEGACY-DEFAULT: Previous production default (center_projected_64dim_hierarchical)
        - HIGH-PURITY: Metric learning (best citation-independent retrieval)
        - HIGH-ADVANTAGE: Citation/outcome (best cross-lingual alignment)
        - COMBINATION: Best stable combination (linear_hybrid05_concat)
        - CITATION-ROLE: Role-specific views (following, criticizing, citing)
        - LEGACY: Earlier representations (available but not primary)
        """
        patterns = self.map_loader.get_representations_by_pattern
        return {
            "DEFAULT": {
                "description": "Production default — passes both adversarial gates (language dominance < 0.85, jurist pairwise > 0.5)",
                "representations": patterns("DEFAULT"),
                "strength": "Systematic, balanced, production-ready",
                "use_when": "General purpose, first-time users, production deployment"
            },
            "LEGACY-DEFAULT": {
                "description": "Previous production default (factory direction v6) — 64-dim frozen PCA center_projected with hierarchical Leiden. Nesting=1.0, purity=0.9718. Replaced by cited_outcome_hybrid_0.5 per v15b-audit.",
                "representations": patterns("LEGACY-DEFAULT"),
                "strength": "High cluster purity, validated hierarchical structure",
                "use_when": "Comparing with previous default, doctrinal/Jurivoc exploration with known metadata"
            },
            "HIGH-PURITY": {
                "description": "Metric learning representations — best for citation-independent retrieval (35% vs 14% for citation signals)",
                "representations": patterns("HIGH-PURITY"),
                "strength": "Citation-independent legal proximity, high cluster purity",
                "use_when": "Exploring legal proximity without citation bias, finding semantically similar cases"
            },
            "HIGH-ADVANTAGE": {
                "description": "Citation/outcome representations — best for cross-lingual alignment and fractal quality",
                "representations": patterns("HIGH-ADVANTAGE"),
                "strength": "Cross-lingual navigation, hierarchical structure, citation-proximity",
                "use_when": "Cross-language exploration, finding precedent chains, fractal zoom navigation"
            },
            "COMBINATION": {
                "description": "Best stable combination (v15b ACCEPTED) — 256D concat of linear_metric_best (128D) + cited_outcome_hybrid_0.5 (128D). JP=0.838, std=0.027. Beats zero-shot hybrids on CV.",
                "representations": patterns("COMBINATION"),
                "strength": "Best stable combination across benchmarks, doctrinal/Jurivoc exploration",
                "use_when": "Doctrinal exploration, Jurivoc hierarchy recovery, research comparison"
            },
            "CITATION-ROLE": {
                "description": "Role-specific citation views — see how decisions follow, criticize, or cite each other",
                "representations": patterns("CITATION-ROLE"),
                "strength": "Citation role differentiation",
                "use_when": "Analyzing precedent relationships, finding divergent rulings"
            },
            "LEGACY": {
                "description": "Earlier representations — available for comparison but superseded by newer patterns",
                "representations": patterns("LEGACY"),
                "strength": "Historical comparison",
                "use_when": "Comparing with earlier approaches, research reproducibility"
            }
        }

    def get_holdout_metrics(self) -> Dict[str, Any]:
        """Return holdout-validated metrics from legal-distance v9.
        
        These are true out-of-sample metrics, not training metrics.
        Use these for comparing representation quality.
        """
        from .evaluation_loader import EvaluationLoader
        eval_loader = EvaluationLoader(str(self.map_loader.results_dir))
        eval_loader.load()
        return eval_loader.get_holdout_metrics()

    def get_representation_recommendation(self, purpose: str = "default") -> Dict[str, Any]:
        """Get recommended representation for a specific purpose.
        
        Factory direction v15 (v15b-audit CRITICAL):
        - "production": PRODUCTION DEFAULT (cited_outcome_hybrid_0.5) — wins full-harness
        - "citation_independent": Best for citation-independent retrieval (linear_metric_best)
        - "cross_lingual": Best for cross-language navigation (cited_outcome_hybrid_0.5)
        - "fractal_quality": Best hierarchical structure (cited_outcome_hybrid_0.7)
        - "default": Same as production
        - "best_stable_combination": linear_hybrid05_concat (JP=0.838, std=0.027)
        """
        from .evaluation_loader import EvaluationLoader
        eval_loader = EvaluationLoader(str(self.map_loader.results_dir))
        eval_loader.load()
        return eval_loader.get_representation_recommendation(purpose)

    # ── Design-Pattern Side-by-Side Comparison ──────────────────────────

    _HOLDOUT_TO_MAP_REP: Dict[str, str] = {
        "linear_metric_epoch4": "linear_metric_best",
        "mahalanobis_metric_epoch4": "mahalanobis_best",
        "hybrid_stabilized_epoch1": "hybrid_stabilized_best",
    }

    def _select_best_representation(self, pattern: str) -> Optional[str]:
        """Select the best representation for *pattern* by holdout JP score.

        Falls back to the first loaded representation matching the pattern
        when no holdout metrics are available.
        """
        from .evaluation_loader import EvaluationLoader

        eval_loader = EvaluationLoader(str(self.map_loader.results_dir))
        eval_loader.load()
        holdout = eval_loader.get_holdout_metrics()

        loaded_reps = set(self.map_loader.get_available_representations())

        candidates = []
        for rep_key, metrics in holdout.items():
            if metrics.get("design_pattern") != pattern:
                continue
            jp = metrics.get("jp_score")
            # Map holdout key to actual loaded representation name
            actual_rep = self._HOLDOUT_TO_MAP_REP.get(rep_key, rep_key)
            if actual_rep not in loaded_reps:
                continue
            candidates.append((jp if jp is not None else -1.0, actual_rep))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

        # Fallback: first loaded rep that belongs to this pattern
        for rep in loaded_reps:
            pat = self.map_loader.DESIGN_PATTERNS.get(rep)
            if pat == pattern:
                return rep
        return None

    def compare_design_patterns(
        self,
        pattern_a: str,
        pattern_b: str,
        zoom_level: int = 1,
    ) -> Dict[str, Any]:
        """Side-by-side comparison of two design patterns.

        For each pattern selects the best representation (by holdout JP),
        then returns per-decision cluster membership in both representations
        plus stability metrics.
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        VALID_PATTERNS = {"DEFAULT", "HIGH-PURITY", "HIGH-ADVANTAGE", "CITATION-ROLE", "COMBINATION"}
        if pattern_a not in VALID_PATTERNS:
            return {"error": f"Invalid pattern_a '{pattern_a}'. Valid: {sorted(VALID_PATTERNS)}"}
        if pattern_b not in VALID_PATTERNS:
            return {"error": f"Invalid pattern_b '{pattern_b}'. Valid: {sorted(VALID_PATTERNS)}"}

        rep_a = self._select_best_representation(pattern_a)
        rep_b = self._select_best_representation(pattern_b)

        if not rep_a:
            return {"error": f"No loaded representation found for pattern '{pattern_a}'"}
        if not rep_b:
            return {"error": f"No loaded representation found for pattern '{pattern_b}'"}

        zl_a = self.map_loader.get_zoom_level(rep_a, zoom_level)
        zl_b = self.map_loader.get_zoom_level(rep_b, zoom_level)

        if not zl_a:
            return {"error": f"Zoom level {zoom_level} not available for {rep_a}"}
        if not zl_b:
            return {"error": f"Zoom level {zoom_level} not available for {rep_b}"}

        # Gather holdout metadata for each representation
        from .evaluation_loader import EvaluationLoader
        eval_loader = EvaluationLoader(str(self.map_loader.results_dir))
        eval_loader.load()
        holdout = eval_loader.get_holdout_metrics()

        def _holdout_for(rep: str) -> Dict[str, Any]:
            # Reverse-map loaded rep name back to holdout key
            rev = {v: k for k, v in self._HOLDOUT_TO_MAP_REP.items()}
            key = rev.get(rep, rep)
            return holdout.get(key, {})

        meta_a = _holdout_for(rep_a)
        meta_b = _holdout_for(rep_b)

        # Common decisions
        common = set(zl_a.positions.keys()) & set(zl_b.positions.keys())

        decisions = []
        same_cluster_count = 0
        for did in common:
            ca = zl_a.cluster_assignments.get(did, -1)
            cb = zl_b.cluster_assignments.get(did, -1)
            same = ca == cb and ca >= 0
            if same:
                same_cluster_count += 1
            decisions.append({
                "decision_id": did,
                "cluster_a": ca,
                "cluster_b": cb,
                "same_cluster": same,
            })

        total = len(decisions)
        stability_pct = round(same_cluster_count / total * 100, 2) if total else 0.0

        # Highlight decisions that move
        movers = [d for d in decisions if not d["same_cluster"]]

        return {
            "pattern_a": pattern_a,
            "pattern_b": pattern_b,
            "zoom_level": zoom_level,
            "representation_a": {
                "name": rep_a,
                "holdout_jp": meta_a.get("jp_score"),
                "language_dominance": meta_a.get("language_dominance"),
                "cluster_count": zl_a.n_clusters,
                "positions_count": len(zl_a.positions),
            },
            "representation_b": {
                "name": rep_b,
                "holdout_jp": meta_b.get("jp_score"),
                "language_dominance": meta_b.get("language_dominance"),
                "cluster_count": zl_b.n_clusters,
                "positions_count": len(zl_b.positions),
            },
            "stability": {
                "total_common_decisions": total,
                "same_cluster_count": same_cluster_count,
                "stability_percentage": stability_pct,
                "movers_count": len(movers),
            },
            "decisions": decisions,
            "movers": movers,
        }

    # ── Startup Validation ──────────────────────────────────────────────

    def startup_validation(self) -> Dict[str, Any]:
        """Validate all loaded representations at startup.

        Checks:
        - Zoom levels exist for each representation
        - Positions are non-empty at each zoom level
        - Clusters are non-empty at each zoom level

        Returns per-representation PASS/WARN/FAIL with issue list and timing.
        """
        import time as _time

        if not self._initialized:
            return {"error": "Not initialized"}

        t0 = _time.time()
        all_reps = self.map_loader.get_available_representations()
        results: Dict[str, Dict[str, Any]] = {}

        for rep in all_reps:
            rep_start = _time.time()
            issues: List[str] = []
            status = "PASS"

            map_state = self.map_loader.get_map(rep)
            if not map_state:
                results[rep] = {
                    "status": "FAIL",
                    "issues": ["Map state not loaded"],
                    "elapsed_ms": round((_time.time() - rep_start) * 1000, 1),
                }
                continue

            zoom_levels = self.map_loader.get_zoom_levels(rep)
            if not zoom_levels:
                status = "WARN"
                issues.append("No zoom levels found")

            for zl_level in zoom_levels:
                zl = self.map_loader.get_zoom_level(rep, zl_level)
                if not zl:
                    status = "FAIL"
                    issues.append(f"Zoom level {zl_level} returned None")
                    continue

                if len(zl.positions) == 0:
                    status = "WARN" if status == "PASS" else status
                    issues.append(f"Zoom {zl_level}: positions is empty")

                if zl.n_clusters == 0:
                    status = "WARN" if status == "PASS" else status
                    issues.append(f"Zoom {zl_level}: clusters is empty (0 clusters)")

            results[rep] = {
                "status": status,
                "issues": issues,
                "zoom_levels_checked": zoom_levels,
                "elapsed_ms": round((_time.time() - rep_start) * 1000, 1),
            }

        elapsed_total = round((_time.time() - t0) * 1000, 1)
        passing = sum(1 for r in results.values() if r["status"] == "PASS")
        warnings = sum(1 for r in results.values() if r["status"] == "WARN")
        failing = sum(1 for r in results.values() if r["status"] == "FAIL")

        return {
            "total_representations": len(all_reps),
            "passing": passing,
            "warnings": warnings,
            "failing": failing,
            "representations": results,
            "elapsed_ms": elapsed_total,
        }
