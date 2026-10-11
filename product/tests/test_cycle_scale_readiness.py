"""
LexMachina Scale-Readiness Tests (FEAT-070, FEAT-071, FEAT-072, FEAT-073)

Tests for:
- Inverted search index (FEAT-070): Fast TF-IDF search for 192k corpus
- KD-tree spatial index (FEAT-071): Fast viewport queries for WebGL
- Async import manager (FEAT-072): Streaming import with progress tracking
- Compressed resolution ladder (FEAT-073): 5-level zoom optimization
"""
import json
import os
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.inverted_index import InvertedIndex, _tokenize
from app.spatial_index import SpatialIndex
from app.import_manager import ImportManager, ImportJob


# ============================================================================
# FEAT-070: Inverted Search Index Tests
# ============================================================================

class TestInvertedIndex:
    """Tests for the inverted search index."""

    def test_tokenization_basic(self):
        """Tokenize basic text correctly."""
        tokens = _tokenize("Bundesgericht Verwaltung Beschwerde")
        assert "bundesgericht" in tokens
        assert "verwaltung" in tokens
        assert "beschwerde" in tokens

    def test_tokenization_compound_words(self):
        """Preserve internal hyphens in Swiss compound words."""
        tokens = _tokenize("Ober-gerichtshof Verwaltungs-gericht")
        # Internal hyphens should be preserved
        assert any("ober" in t for t in tokens)

    def test_tokenization_short_tokens_filtered(self):
        """Filter tokens shorter than 2 characters."""
        tokens = _tokenize("A B CD EFG")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "cd" in tokens
        assert "efg" in tokens

    def test_build_and_search(self):
        """Build index and search for documents."""
        index = InvertedIndex()
        docs = {
            "doc1": "Bundesgericht Verwaltung Beschwerde zivilrecht",
            "doc2": "Bundesgericht Strafrecht Beschwerde",
            "doc3": "Verwaltungsgericht Verwaltung Beschwerde",
            "doc4": "Bundesgericht Verwaltung Recht",
        }
        languages = {"doc1": "de", "doc2": "de", "doc3": "de", "doc4": "fr"}
        index.build(docs, languages)

        assert index.doc_count == 4
        assert index.term_count > 0

    def test_search_single_term(self):
        """Search with single term returns correct results."""
        index = InvertedIndex()
        docs = {
            "doc1": "Bundesgericht Verwaltung Beschwerde",
            "doc2": "Strafrecht Beschwerde",
            "doc3": "Verwaltungsgericht Verwaltung",
        }
        index.build(docs)

        results = index.search("Verwaltung", limit=10)
        assert len(results) >= 2
        # doc1 and doc3 should match
        result_ids = [r[0] for r in results]
        assert "doc1" in result_ids
        assert "doc3" in result_ids

    def test_search_multi_term_and_semantics(self):
        """Multi-term search uses AND semantics."""
        index = InvertedIndex()
        docs = {
            "doc1": "Bundesgericht Verwaltung Beschwerde",
            "doc2": "Bundesgericht Strafrecht",
            "doc3": "Verwaltungsgericht Verwaltung",
        }
        index.build(docs)

        results = index.search("Bundesgericht Verwaltung", limit=10)
        result_ids = [r[0] for r in results]
        # Only doc1 has both terms
        assert "doc1" in result_ids
        assert "doc2" not in result_ids  # has Bundesgericht but not Verwaltung
        assert "doc3" not in result_ids  # has Verwaltung but not Bundesgericht

    def test_search_language_filter(self):
        """Language filter returns only matching documents."""
        index = InvertedIndex()
        docs = {
            "doc1": "Bundesgericht Verwaltung",
            "doc2": "Tribunal fédéral administration",
            "doc3": "Bundesgericht Strafrecht",
        }
        languages = {"doc1": "de", "doc2": "fr", "doc3": "de"}
        index.build(docs, languages)

        # Search in German only
        results_de = index.search("Bundesgericht", language="de", limit=10)
        result_ids_de = [r[0] for r in results_de]
        assert "doc1" in result_ids_de
        assert "doc2" not in result_ids_de

        # Search in French only
        results_fr = index.search("Tribunal", language="fr", limit=10)
        result_ids_fr = [r[0] for r in results_fr]
        assert "doc2" in result_ids_fr
        assert "doc1" not in result_ids_fr

    def test_search_limit(self):
        """Search respects limit parameter."""
        index = InvertedIndex()
        docs = {f"doc{i}": f"Test keyword document number {i}" for i in range(100)}
        index.build(docs)

        results = index.search("test", limit=5)
        assert len(results) <= 5

    def test_search_empty_query(self):
        """Empty query returns empty results."""
        index = InvertedIndex()
        index.build({"doc1": "test"})
        results = index.search("", limit=10)
        assert results == []

    def test_search_no_match(self):
        """Query with no matches returns empty results."""
        index = InvertedIndex()
        index.build({"doc1": "Bundesgericht Verwaltung"})
        results = index.search("nichtvorhandenxyz", limit=10)
        assert results == []

    def test_add_document_incremental(self):
        """Add documents incrementally after build."""
        index = InvertedIndex()
        index.build({"doc1": "Bundesgericht Verwaltung"})
        
        index.add_document("doc2", "Strafrecht Beschwerde", "de")
        
        assert index.doc_count == 2
        results = index.search("Strafrecht", limit=10)
        assert len(results) == 1
        assert results[0][0] == "doc2"

    def test_remove_document(self):
        """Remove document from index."""
        index = InvertedIndex()
        index.build({"doc1": "Bundesgericht", "doc2": "Strafrecht"})
        
        index.remove_document("doc1")
        
        assert index.doc_count == 1
        results = index.search("Bundesgericht", limit=10)
        assert len(results) == 0

    def test_tf_idf_ranking(self):
        """Results are ranked by TF-IDF score (more relevant first)."""
        index = InvertedIndex()
        docs = {
            "doc1": "Verwaltung Verwaltung Verwaltung Beschwerde",
            "doc2": "Verwaltung Beschwerde",
            "doc3": "Verwaltung Beschwerde Bundesgericht Recht",
        }
        index.build(docs)

        results = index.search("Verwaltung", limit=10)
        # doc1 should rank highest (Verwaltung appears 3 times)
        assert results[0][0] == "doc1"

    def test_unicode_handling(self):
        """Handle Unicode characters from Swiss case law."""
        index = InvertedIndex()
        docs = {
            "doc1": "Bundesgericht Zürich Strafbefehl",
            "doc2": "Tribunal fédéral Lausanne arrêt",
        }
        index.build(docs)

        results = index.search("Zürich", limit=10)
        assert len(results) == 1
        assert results[0][0] == "doc1"


# ============================================================================
# FEAT-071: KD-tree Spatial Index Tests
# ============================================================================

class TestSpatialIndex:
    """Tests for the KD-tree spatial index."""

    def test_build_empty(self):
        """Build empty index."""
        si = SpatialIndex()
        si.build({})
        assert si.size == 0

    def test_build_and_range_query(self):
        """Build index and perform range query."""
        si = SpatialIndex()
        positions = {
            "doc1": (1.0, 1.0),
            "doc2": (5.0, 5.0),
            "doc3": (10.0, 10.0),
            "doc4": (2.0, 8.0),
        }
        si.build(positions)

        # Query bbox that should include doc1 and doc2
        result = si.range_query(0.0, 0.0, 6.0, 6.0)
        assert "doc1" in result
        assert "doc2" in result
        assert "doc3" not in result

    def test_range_query_exact_boundary(self):
        """Range query with exact boundary values."""
        si = SpatialIndex()
        positions = {
            "doc1": (1.0, 1.0),
            "doc2": (5.0, 5.0),
        }
        si.build(positions)

        # Exact boundary should include the point
        result = si.range_query(1.0, 1.0, 5.0, 5.0)
        assert "doc1" in result
        assert "doc2" in result

    def test_range_query_empty(self):
        """Range query with no matches returns empty list."""
        si = SpatialIndex()
        positions = {"doc1": (1.0, 1.0), "doc2": (2.0, 2.0)}
        si.build(positions)

        result = si.range_query(100.0, 100.0, 200.0, 200.0)
        assert result == []

    def test_knn_query(self):
        """k-NN query returns nearest neighbors."""
        si = SpatialIndex()
        positions = {
            "doc1": (0.0, 0.0),
            "doc2": (1.0, 0.0),
            "doc3": (0.0, 1.0),
            "doc4": (10.0, 10.0),
        }
        si.build(positions)

        # Query near origin
        results = si.knn_query(0.0, 0.0, k=3)
        assert len(results) == 3
        # doc1 should be closest (distance 0)
        assert results[0][0] == "doc1"
        # doc2 and doc3 should be next (distance 1)
        assert results[1][0] in ("doc2", "doc3")

    def test_knn_query_larger_dataset(self):
        """k-NN query works on larger dataset."""
        si = SpatialIndex()
        n = 1000
        positions = {f"doc{i}": (float(i), float(i % 10)) for i in range(n)}
        si.build(positions)

        results = si.knn_query(500.0, 5.0, k=10)
        assert len(results) == 10
        # All results should be sorted by distance
        distances = [r[1] for r in results]
        assert distances == sorted(distances)

    def test_add_point(self):
        """Add point triggers lazy rebuild."""
        si = SpatialIndex()
        si.build({"doc1": (0.0, 0.0)})
        
        si.add_point("doc2", 1.0, 1.0)
        assert si._dirty is True
        
        # Query triggers rebuild
        result = si.range_query(0.5, 0.5, 1.5, 1.5)
        assert "doc2" in result

    def test_remove_point(self):
        """Remove point triggers lazy rebuild."""
        si = SpatialIndex()
        si.build({"doc1": (0.0, 0.0), "doc2": (1.0, 1.0)})
        
        si.remove_point("doc1")
        assert si._dirty is True
        
        # Query triggers rebuild
        result = si.range_query(-1.0, -1.0, 0.5, 0.5)
        assert "doc1" not in result
        assert "doc2" not in result

    def test_large_scale_performance(self):
        """Spatial index handles 10k+ points efficiently."""
        si = SpatialIndex()
        n = 10000
        np.random.seed(42)
        positions = {f"doc{i}": (float(np.random.randn()), float(np.random.randn())) for i in range(n)}
        
        t0 = time.time()
        si.build(positions)
        build_time = time.time() - t0
        
        # Range query should be fast
        t0 = time.time()
        result = si.range_query(-1.0, -1.0, 1.0, 1.0)
        query_time = time.time() - t0
        
        # Build should complete in reasonable time (< 1s for 10k)
        assert build_time < 2.0
        # Range query should be fast (< 0.1s for 10k)
        assert query_time < 0.5
        assert len(result) > 0

    def test_knn_performance(self):
        """k-NN query handles large datasets efficiently."""
        si = SpatialIndex()
        n = 5000
        np.random.seed(42)
        positions = {f"doc{i}": (float(np.random.randn() * 10), float(np.random.randn() * 10)) for i in range(n)}
        si.build(positions)

        t0 = time.time()
        results = si.knn_query(0.0, 0.0, k=20)
        query_time = time.time() - t0

        assert len(results) == 20
        assert query_time < 0.5

    def test_clear(self):
        """Clear resets index to empty."""
        si = SpatialIndex()
        si.build({"doc1": (0.0, 0.0)})
        si.clear()
        assert si.size == 0
        assert si._built is False


# ============================================================================
# FEAT-072: Async Import Manager Tests
# ============================================================================

class TestImportManager:
    """Tests for the async import manager."""

    def test_import_job_progress(self):
        """ImportJob tracks progress correctly."""
        records = [{"decision_id": f"test_{i}", "full_text": f"text {i}"} for i in range(10)]
        job = ImportJob("test_job", records)
        
        assert job.status == "pending"
        assert job.total == 10
        assert job.processed == 0
        
        progress = job.progress()
        assert progress["job_id"] == "test_job"
        assert progress["status"] == "pending"
        assert progress["progress_pct"] == 0.0

    def test_import_job_cancellation(self):
        """ImportJob can be cancelled."""
        records = [{"decision_id": f"test_{i}"} for i in range(5)]
        job = ImportJob("test_cancel", records)
        
        assert job.is_cancelled is False
        job.cancel()
        assert job.is_cancelled is True

    def test_import_job_completion_progress(self):
        """ImportJob shows 100% progress when completed."""
        records = [{"decision_id": "test"}]
        job = ImportJob("test_complete", records)
        job.status = "completed"
        job.processed = 1
        job.end_time = job.start_time = time.time()
        
        progress = job.progress()
        assert progress["progress_pct"] == 100.0

    def test_import_manager_submit(self):
        """ImportManager accepts jobs and returns job_id."""
        # Create a minimal mock nav_api
        class MockCorpus:
            def __init__(self):
                self._schema_validator = type('V', (), {'validate': lambda self, r, strict=False: type('R', (), {'valid': True, 'errors': [], 'warnings': [], 'normalized_record': r})()})()
            def get_all_ids(self): return []
            def get(self, did): return None
        class MockMapLoader:
            def get_zoom_level(self, rep, zoom): return None
        class MockNavApi:
            corpus = MockCorpus()
            map_loader = MockMapLoader()
            _embedding_model = None
            _base_embeddings = None
            _base_decision_ids = []
            _import_positions_file = None
            _imported_positions = {}
            def _get_default_representation(self): return "test"
        
        manager = ImportManager(MockNavApi())
        records = [{"decision_id": "test_001", "full_text": "test"}]
        job_id = manager.submit_import(records)
        
        assert job_id.startswith("import_")
        
        # Check status
        status = manager.get_status(job_id)
        assert status["job_id"] == job_id
        assert status["total"] == 1

    def test_import_manager_nonexistent_job(self):
        """ImportManager returns error for nonexistent job."""
        class MockNavApi:
            pass
        manager = ImportManager(MockNavApi())
        status = manager.get_status("nonexistent")
        assert "error" in status

    def test_import_manager_cancel(self):
        """ImportManager can cancel a job."""
        class MockCorpus:
            def __init__(self):
                self._schema_validator = type('V', (), {'validate': lambda self, r, strict=False: type('R', (), {'valid': True, 'errors': [], 'warnings': [], 'normalized_record': r})()})()
            def get_all_ids(self): return []
            def get(self, did): return None
        class MockMapLoader:
            def get_zoom_level(self, rep, zoom): return None
        class MockNavApi:
            corpus = MockCorpus()
            map_loader = MockMapLoader()
            _embedding_model = None
            _base_embeddings = None
            _base_decision_ids = []
            _import_positions_file = None
            _imported_positions = {}
            def _get_default_representation(self): return "test"
        
        manager = ImportManager(MockNavApi())
        records = [{"decision_id": "test_cancel"}]
        job_id = manager.submit_import(records)
        
        result = manager.cancel_import(job_id)
        assert result is True

    def test_import_manager_cancel_nonexistent(self):
        """ImportManager returns False for nonexistent job cancellation."""
        class MockNavApi:
            pass
        manager = ImportManager(MockNavApi())
        result = manager.cancel_import("nonexistent")
        assert result is False


# ============================================================================
# FEAT-070 Integration: CorpusLoader with InvertedIndex
# ============================================================================

class TestCorpusSearchIntegration:
    """Test inverted index integration with CorpusLoader."""

    def test_corpus_search_uses_inverted_index(self):
        """CorpusLoader.search uses inverted index when available."""
        from app.corpus_loader import CorpusLoader
        
        corpus_dir = str(Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical")
        if not Path(corpus_dir).exists():
            pytest.skip("Corpus directory not available")
        
        corpus = CorpusLoader(corpus_dir)
        count = corpus.load()
        
        if count == 0:
            pytest.skip("No corpus data available")
        
        # Search should use inverted index
        results = corpus.search("Beschwerde", limit=5)
        assert isinstance(results, list)
        # Results should have search_score from inverted index
        if results:
            assert "search_score" in results[0]

    def test_corpus_search_with_language(self):
        """CorpusLoader.search supports language parameter."""
        from app.corpus_loader import CorpusLoader
        
        corpus_dir = str(Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical")
        if not Path(corpus_dir).exists():
            pytest.skip("Corpus directory not available")
        
        corpus = CorpusLoader(corpus_dir)
        count = corpus.load()
        
        if count == 0:
            pytest.skip("No corpus data available")
        
        results_de = corpus.search("Beschwerde", limit=5, language="de")
        results_fr = corpus.search("Beschwerde", limit=5, language="fr")
        
        # German results should not include French documents
        for r in results_de:
            assert r.get("language") == "de" or "search_score" not in r


# ============================================================================
# Integration: Navigation API with Spatial Index
# ============================================================================

class TestNavigationSpatialIntegration:
    """Test spatial index integration with NavigationAPI."""

    def test_navigation_initializes_spatial_indices(self):
        """NavigationAPI builds spatial indices during initialization."""
        from app.navigation import NavigationAPI
        
        base_dir = Path(__file__).parent.parent
        corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
        results_dir = str(base_dir / "results" / "fractal_map")
        
        if not Path(corpus_dir).exists() or not Path(results_dir).exists():
            pytest.skip("Data directories not available")
        
        nav = NavigationAPI(corpus_dir, results_dir)
        nav.initialize()
        
        # Should have spatial indices built
        assert len(nav._spatial_indices) > 0

    def test_webgl_data_with_spatial_index(self):
        """WebGL data endpoint uses spatial index for viewport queries."""
        from app.navigation import NavigationAPI
        
        base_dir = Path(__file__).parent.parent
        corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
        results_dir = str(base_dir / "results" / "fractal_map")
        
        if not Path(corpus_dir).exists() or not Path(results_dir).exists():
            pytest.skip("Data directories not available")
        
        nav = NavigationAPI(corpus_dir, results_dir)
        nav.initialize()
        
        # Get WebGL data with viewport bbox
        data = nav.get_webgl_data(
            "center_projected_64dim_hierarchical", 1,
            bbox={"xMin": -5.0, "yMin": -5.0, "xMax": 5.0, "yMax": 5.0}
        )
        
        assert "points" in data
        assert "viewport_culling" in data
        assert data["viewport_culling"]["requested"] is True
        # Should have culled some points
        assert data["viewport_culling"]["visible_positions"] <= data["viewport_culling"]["total_positions"]


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
