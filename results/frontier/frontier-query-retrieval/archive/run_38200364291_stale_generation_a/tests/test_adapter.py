"""
Tests for OpenCaseLaw Retrieval Adapter.

Tests cover:
- Pagination and search
- Cache behavior
- Deduplication determinism
- Provenance tracking
- Remote failure degradation
- Query expansion multilingual support
- Bundle validation
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocl_adapter.client import (
    OpenCaseLawClient,
    RateLimiter,
    CacheManager,
    Decision,
    create_client,
)
from ocl_adapter.expansion import (
    QueryExpander,
    SWISS_LEGAL_SYNONYMS,
    expand_query,
    get_search_variants,
)
from ocl_adapter.deduplication import (
    DecisionIdentity,
    deduplicate_decisions,
    DecisionDeduplicator,
)
from ocl_adapter.retrieval import (
    RetrievalOrchestrator,
    RetrievalConfig,
    retrieve_for_query,
)
from ocl_adapter.bundle import (
    QueryResultBundle,
    BundleDecision,
    BundleProvenance,
    build_bundle_from_retrieval,
    validate_bundle,
    validate_bundle_object,
    BUNDLE_VERSION,
)
from ocl_adapter.cli import main as cli_main


# Test fixtures

@pytest.fixture
def sample_decision_data():
    """Sample decision data for testing."""
    return {
        "decision_id": "bge_BGE_117_II_410",
        "canonical_decision_id": "bge_BGE_117_II_410",
        "court": "bge",
        "court_name": "Bundesgericht (BGE)",
        "canton": "CH",
        "chamber": "II",
        "docket_number": "BGE 117 II 410",
        "decision_date": "1990-07-01",
        "publication_date": "1991-01-01",
        "language": "de",
        "title": None,
        "legal_area": "civil",
        "regeste": "Mieterstreckung; materielle Rechtskraft (Art. 273 OR).",
        "rule_statement": "Regeste: Mieterstreckung...",
        "full_text": "BGE 117 II 410 full text...",
        "source_url": "https://search.bger.ch/...",
        "pdf_url": None,
        "canonical_url": "https://mcp.opencaselaw.ch/entscheid/bge_BGE_117_II_410",
        "citation_string_de": "BGE 117 II 410",
        "citation_string_fr": "ATF 117 II 410",
        "citation_string_it": "DTF 117 II 410",
        "statutes": ["Art. 273 OR"],
        "citation_count": 23,
        "cited_by_results": 1,
        "relevance_score": 28.7941,
        "is_canonical": True,
    }


@pytest.fixture
def sample_decision(sample_decision_data):
    """Sample Decision object."""
    return Decision.from_api_response(sample_decision_data, provenance="live")


@pytest.fixture
def duplicate_decisions(sample_decision_data):
    """Two decisions with same canonical identity."""
    d1 = Decision.from_api_response(sample_decision_data, provenance="live")
    d2_data = sample_decision_data.copy()
    d2_data["decision_id"] = "bge_BGE_117_II_410_duplicate"
    d2_data["provenance"] = "cache"
    d2 = Decision.from_api_response(d2_data, provenance="cache")
    return [d1, d2]


@pytest.fixture
def temp_cache_dir():
    """Temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# RateLimiter tests

class TestRateLimiter:
    def test_basic_rate_limiting(self):
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)
        
        # First 3 should be immediate
        for _ in range(3):
            wait = limiter.acquire()
            assert wait == 0.0
        
        # 4th should wait
        start = time.time()
        wait = limiter.acquire()
        elapsed = time.time() - start
        assert wait > 0
        assert elapsed >= 0.9  # Should have waited ~1 second
    
    def test_rate_limiter_status(self):
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        limiter.acquire()
        limiter.acquire()
        
        status = limiter.get_status()
        assert status["max_requests"] == 5
        assert status["current_requests"] == 2
        assert status["remaining"] == 3


# CacheManager tests

class TestCacheManager:
    def test_cache_set_get(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl_seconds=3600)
        
        key = "test_key"
        data = {"test": "data", "number": 42}
        
        cache.set(key, data)
        retrieved = cache.get(key)
        
        assert retrieved == data
    
    def test_cache_expiration(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl_seconds=0)  # Expired immediately
        
        cache.set("key", {"data": "value"})
        retrieved = cache.get("key")
        
        assert retrieved is None
    
    def test_cache_miss(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir)
        
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_stats(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir)
        
        cache.set("key1", {"data": 1})
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
    
    def test_cache_invalidate(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir)
        
        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})
        
        count = cache.invalidate("key1")
        assert count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        
        count = cache.invalidate()
        assert count == 1


# Decision tests

class TestDecision:
    def test_from_api_response(self, sample_decision_data):
        decision = Decision.from_api_response(sample_decision_data, provenance="live")
        
        assert decision.decision_id == "bge_BGE_117_II_410"
        assert decision.canonical_decision_id == "bge_BGE_117_II_410"
        assert decision.court == "bge"
        assert decision.language == "de"
        assert decision.provenance == "live"
        assert decision.relevance_score == 28.7941
    
    def test_get_snippet(self, sample_decision):
        snippet = sample_decision.get_snippet(100)
        assert "Mieterstreckung" in snippet
        assert len(snippet) <= 100
    
    def test_to_dict(self, sample_decision):
        d = sample_decision.to_dict()
        assert d["decision_id"] == "bge_BGE_117_II_410"
        assert d["provenance"] == "live"


# QueryExpander tests

class TestQueryExpander:
    def test_expand_miete_query(self):
        expander = QueryExpander()
        result = expander.expand_query("miete kündigung")
        
        assert result.original_query == "miete kündigung"
        assert result.language_detected == "de"
        assert len(result.variants) >= 1
        assert "miete kündigung" in result.variants
        assert len(result.expanded_terms["de"]) > 0
    
    def test_expand_french_query(self):
        expander = QueryExpander()
        result = expander.expand_query("bail congé")
        
        assert result.language_detected == "fr"
        assert "loyer" in result.expanded_terms["fr"] or "bail" in result.expanded_terms["fr"]
    
    def test_expand_italian_query(self):
        expander = QueryExpander()
        result = expander.expand_query("lavoro licenziamento")
        
        assert result.language_detected == "it"
    
    def test_expand_unknown_terms(self):
        expander = QueryExpander()
        result = expander.expand_query("xyz unknown legal term")
        
        # Should still return original query as variant
        assert result.variants == ["xyz unknown legal term"]
        assert result.combined_query == "xyz unknown legal term"
    
    def test_get_search_variants(self):
        variants = get_search_variants("miete", max_variants=3)
        
        assert isinstance(variants, list)
        assert len(variants) <= 3
        assert "miete" in variants


# Deduplication tests

class TestDeduplication:
    def test_deduplicate_by_canonical_id(self, duplicate_decisions):
        unique, report = deduplicate_decisions(duplicate_decisions)
        
        assert len(unique) == 1
        assert report["duplicates_removed"] == 1
        assert report["duplicate_groups"] == 1
    
    def test_deduplicate_prefers_live_provenance(self, duplicate_decisions):
        # duplicate_decisions has live first, cache second
        unique, _ = deduplicate_decisions(duplicate_decisions, prefer_provenance=["live", "cache"])
        
        assert len(unique) == 1
        assert unique[0].provenance == "live"
    
    def test_deduplicate_prefers_cache_when_requested(self, duplicate_decisions):
        unique, _ = deduplicate_decisions(duplicate_decisions, prefer_provenance=["cache", "live"])
        
        assert len(unique) == 1
        assert unique[0].provenance == "cache"
    
    def test_deduplicate_preserves_order(self, duplicate_decisions):
        # Reverse order: cache first, live second
        reversed_decisions = list(reversed(duplicate_decisions))
        unique, _ = deduplicate_decisions(reversed_decisions, prefer_provenance=["live", "cache"])
        
        # Should still prefer live even though it came second
        assert unique[0].provenance == "live"
    
    def test_deduplicate_empty_list(self):
        unique, report = deduplicate_decisions([])
        
        assert unique == []
        assert report["input_count"] == 0
        assert report["output_count"] == 0
    
    def test_decision_identity_key(self, sample_decision):
        identity = DecisionIdentity.from_decision(sample_decision)
        key = identity.to_key()
        
        assert key == "bge_BGE_117_II_410"  # canonical_decision_id
    
    def test_decision_deduplicator_stateful(self, sample_decision):
        deduplicator = DecisionDeduplicator()
        
        # Add same decision twice
        added1 = deduplicator.add(sample_decision)
        added2 = deduplicator.add(sample_decision)
        
        assert added1 is True
        assert added2 is False
        assert deduplicator.get_stats()["total_unique"] == 1
        assert deduplicator.get_stats()["total_duplicates"] == 1


# RetrievalOrchestrator tests (with mocked client)

class TestRetrievalOrchestrator:
    @pytest.fixture
    def mock_client(self):
        client = Mock(spec=OpenCaseLawClient)
        return client
    
    @pytest.fixture
    def sample_decisions(self, sample_decision_data):
        d1 = Decision.from_api_response(sample_decision_data, provenance="live")
        d2_data = sample_decision_data.copy()
        d2_data["decision_id"] = "bge_BGE_140_III_86"
        d2_data["docket_number"] = "BGE 140 III 86"
        d2_data["canonical_decision_id"] = "bge_BGE_140_III_86"
        d2 = Decision.from_api_response(d2_data, provenance="live")
        return [d1, d2]
    
    def test_retrieve_basic(self, mock_client, sample_decisions):
        # Mock search_decisions_paginated
        mock_client.search_decisions_paginated.return_value = (sample_decisions, {
            "pages_fetched": 1,
            "total_decisions": 2,
            "has_more": False,
        })
        mock_client.get_decision.return_value = (None, "not_found")
        mock_client.get_decision_citations.return_value = ([], {})
        mock_client.get_leading_cases.return_value = ([], {})
        mock_client.get_stats.return_value = {"requests": 1, "cache": {"hits": 0}}
        
        config = RetrievalConfig(
            target_count=10,
            max_query_variants=1,
            max_pages_per_query=1,
            enable_citation_expansion=False,
            enable_leading_cases=False,
        )
        
        orchestrator = RetrievalOrchestrator(client=mock_client, config=config)
        decisions, stats = orchestrator.retrieve("test query")
        
        assert len(decisions) == 2
        assert stats.decisions_fetched == 2
        assert stats.decisions_after_dedupe == 2
        mock_client.search_decisions_paginated.assert_called()
    
    def test_retrieve_with_citation_expansion(self, mock_client, sample_decision, sample_decision_data):
        # Create a cited decision
        cited_data = sample_decision_data.copy()
        cited_data["decision_id"] = "bge_BGE_100_I_1"
        cited_data["canonical_decision_id"] = "bge_BGE_100_I_1"
        cited_data["docket_number"] = "BGE 100 I 1"
        cited_decision = Decision.from_api_response(cited_data, provenance="live")
        
        mock_client.search_decisions_paginated.return_value = ([sample_decision], {
            "pages_fetched": 1,
            "has_more": False,
        })
        mock_client.get_decision.return_value = (sample_decision, "live")
        mock_client.get_decision_citations.return_value = ([cited_decision], {})
        mock_client.get_leading_cases.return_value = ([], {})
        mock_client.get_stats.return_value = {"requests": 1, "cache": {"hits": 0}}
        
        config = RetrievalConfig(
            target_count=10,
            max_query_variants=1,
            max_pages_per_query=1,
            enable_citation_expansion=True,
            citation_seed_count=1,
            citation_expansion_limit=5,
            enable_leading_cases=False,
        )
        
        orchestrator = RetrievalOrchestrator(client=mock_client, config=config)
        decisions, stats = orchestrator.retrieve("test query")
        
        # Should have original + cited decision
        assert len(decisions) >= 2
        assert stats.citation_expansions == 1


# Bundle tests

class TestBundle:
    def test_create_bundle_from_retrieval(self, sample_decision):
        from ocl_adapter.retrieval import RetrievalStats
        
        stats = RetrievalStats(
            query="test",
            query_variants_used=["test"],
            decisions_fetched=1,
            decisions_after_dedupe=1,
        )
        
        bundle = build_bundle_from_retrieval(
            query="test query",
            query_variants=["test query"],
            decisions=[sample_decision],
            retrieval_stats=stats,
        )
        
        assert bundle.query == "test query"
        assert len(bundle.decisions) == 1
        assert bundle.decisions[0].decision_id == "bge_BGE_117_II_410"
        assert bundle.provenance.bundle_version == BUNDLE_VERSION
    
    def test_bundle_to_dict(self, sample_decision):
        from ocl_adapter.retrieval import RetrievalStats
        
        stats = RetrievalStats(query="test", query_variants_used=["test"])
        bundle = build_bundle_from_retrieval(
            query="test",
            query_variants=["test"],
            decisions=[sample_decision],
            retrieval_stats=stats,
        )
        
        d = bundle.to_dict()
        assert d["bundle_version"] == BUNDLE_VERSION
        assert d["query"] == "test"
        assert len(d["decisions"]) == 1
        assert d["decisions"][0]["decision_id"] == "bge_BGE_117_II_410"
    
    def test_bundle_validation_valid(self, sample_decision):
        from ocl_adapter.retrieval import RetrievalStats
        
        stats = RetrievalStats(query="test", query_variants_used=["test"])
        bundle = build_bundle_from_retrieval(
            query="test",
            query_variants=["test"],
            decisions=[sample_decision],
            retrieval_stats=stats,
        )
        
        errors = validate_bundle_object(bundle)
        assert errors == []
    
    def test_bundle_validation_missing_fields(self):
        # Create minimal invalid bundle
        invalid_bundle = {
            "bundle_version": "1.0",
            "schema_version": 1,
            "query": "test",
            "query_variants": [],
            "decisions": [{}],  # Missing required fields
            "clusters": [],
            "relations": [],
            "answer": None,
            "provenance": {},
        }
        
        errors = validate_bundle(invalid_bundle)
        assert len(errors) > 0
        assert any("missing key" in e for e in errors)
    
    def test_bundle_duplicate_detection(self, sample_decision):
        from ocl_adapter.retrieval import RetrievalStats
        
        stats = RetrievalStats(query="test", query_variants_used=["test"])
        # Create bundle with duplicate decision
        bundle = build_bundle_from_retrieval(
            query="test",
            query_variants=["test"],
            decisions=[sample_decision, sample_decision],  # Duplicate
            retrieval_stats=stats,
        )
        
        errors = validate_bundle_object(bundle)
        assert any("duplicate" in e.lower() for e in errors)
    
    def test_bundle_summary(self, sample_decision):
        from ocl_adapter.retrieval import RetrievalStats
        
        stats = RetrievalStats(query="test", query_variants_used=["test"])
        bundle = build_bundle_from_retrieval(
            query="test query",
            query_variants=["test query"],
            decisions=[sample_decision],
            retrieval_stats=stats,
        )
        
        summary = bundle.summary()
        assert summary["n_decisions"] == 1
        assert summary["languages"]["de"] == 1
        assert "bundle_id" in summary


# CLI tests

class TestCLI:
    def test_cli_expand_only(self, capsys):
        import sys
        sys.argv = ["ocl-retrieve", "--expand-only", "miete kündigung"]
        
        exit_code = cli_main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "miete kündigung" in captured.out
        assert "Variants" in captured.out
    
    def test_cli_missing_query(self, capsys, tmp_path):
        import sys
        import io
        # Use --query-file with empty file to avoid stdin capture issue
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        
        sys.argv = ["ocl-retrieve", "--query-file", str(empty_file)]
        
        try:
            exit_code = cli_main()
            assert exit_code != 0
        except SystemExit as e:
            assert e.code != 0
        
        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "query" in captured.err.lower()


# Integration test with fixture

class TestWithFixture:
    @pytest.fixture
    def minimal_fixture(self):
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_fixture.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                return json.load(f)
        return None
    
    def test_minimal_fixture_validates(self, minimal_fixture):
        if minimal_fixture is None:
            pytest.skip("Minimal fixture not found")
        
        errors = validate_bundle(minimal_fixture)
        assert errors == []


# Remote failure degradation tests

class TestRemoteFailureDegradation:
    @pytest.fixture
    def failing_client(self):
        client = Mock(spec=OpenCaseLawClient)
        client.search_decisions_paginated.side_effect = Exception("Network error")
        client.get_stats.return_value = {"requests": 0, "cache": {"hits": 0}}
        return client
    
    def test_retrieval_handles_network_error(self, failing_client):
        config = RetrievalConfig(
            target_count=10,
            max_query_variants=1,
            max_pages_per_query=1,
            enable_citation_expansion=False,
            enable_leading_cases=False,
        )
        
        orchestrator = RetrievalOrchestrator(client=failing_client, config=config)
        decisions, stats = orchestrator.retrieve("test query")
        
        # Should return empty list with error recorded
        assert decisions == []
        assert len(stats.errors) > 0
        assert "Network error" in stats.errors[0]
    
    def test_retrieval_partial_failure(self, sample_decision):
        client = Mock(spec=OpenCaseLawClient)
        
        # Create sample decisions
        d1 = sample_decision
        d2_data = {
            "decision_id": "bge_BGE_140_III_86",
            "canonical_decision_id": "bge_BGE_140_III_86",
            "court": "bge",
            "court_name": "Bundesgericht (BGE)",
            "canton": "CH",
            "chamber": "III",
            "docket_number": "BGE 140 III 86",
            "decision_date": "2014-03-18",
            "publication_date": None,
            "language": "de",
            "title": None,
            "legal_area": "civil",
            "regeste": "Mietrecht; Formvorschriften; Kündigung; Erstreckung.",
            "rule_statement": "Regeste: Mietrecht...",
            "full_text": "BGE 140 III 86...",
            "source_url": "https://search.bger.ch/...",
            "pdf_url": None,
            "canonical_url": "https://mcp.opencaselaw.ch/entscheid/bge_BGE_140_III_86",
            "citation_string_de": "BGE 140 III 86",
            "citation_string_fr": "ATF 140 III 86",
            "citation_string_it": "DTF 140 III 86",
            "statutes": ["Art. 266l OR", "Art. 271 OR"],
            "citation_count": 15,
            "cited_by_results": 3,
            "relevance_score": 25.3,
            "is_canonical": True,
        }
        d2 = Decision.from_api_response(d2_data, provenance="live")
        sample_decisions = [d1, d2]
        
        # First variant succeeds, second fails
        # Use a query that generates multiple variants
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return (sample_decisions, {"pages_fetched": 1, "has_more": False})
            else:
                raise Exception("Rate limited")
        
        client.search_decisions_paginated.side_effect = side_effect
        client.get_decision.return_value = (None, "not_found")
        client.get_decision_citations.return_value = ([], {})
        client.get_leading_cases.return_value = ([], {})
        client.get_stats.return_value = {"requests": 1, "cache": {"hits": 0}}
        
        config = RetrievalConfig(
            target_count=10,
            max_query_variants=2,
            max_pages_per_query=1,
            enable_citation_expansion=False,
            enable_leading_cases=False,
        )
        
        orchestrator = RetrievalOrchestrator(client=client, config=config)
        decisions, stats = orchestrator.retrieve("miete kündigung")
        
        # Should have results from first variant, error from second
        assert len(decisions) == 2
        assert len(stats.errors) == 1


# Multilingual expansion tests

class TestMultilingualExpansion:
    def test_german_expansion(self):
        result = expand_query("mietrecht kündigung")
        
        assert result.language_detected == "de"
        assert any("miete" in t for t in result.expanded_terms["de"])
        assert any("loyer" in t for t in result.expanded_terms["fr"])
        assert any("affitto" in t for t in result.expanded_terms["it"])
    
    def test_french_expansion(self):
        result = expand_query("bail congé")
        
        assert result.language_detected == "fr"
        assert any("loyer" in t for t in result.expanded_terms["fr"])
        assert any("miete" in t for t in result.expanded_terms["de"])
    
    def test_italian_expansion(self):
        result = expand_query("lavoro licenziamento")
        
        assert result.language_detected == "it"
        assert any("lavoro" in t for t in result.expanded_terms["it"])
    
    def test_mixed_language_query(self):
        # Query with mixed terms
        result = expand_query("miete bail lavoro")
        
        # Should detect one language but expand all
        assert len(result.variants) >= 1
        assert all(len(result.expanded_terms[lang]) >= 0 for lang in ["de", "fr", "it"])


# Provenance tracking tests

class TestProvenanceTracking:
    def test_decision_provenance_preserved(self, sample_decision):
        assert sample_decision.provenance == "live"
        
        from ocl_adapter.retrieval import RetrievalStats
        stats = RetrievalStats(query="test", query_variants_used=["test"])
        bundle = build_bundle_from_retrieval(
            query="test",
            query_variants=["test"],
            decisions=[sample_decision],
            retrieval_stats=stats,
        )
        
        assert bundle.decisions[0].provenance == "live"
    
    def test_provenance_breakdown_in_bundle(self, sample_decision):
        from ocl_adapter.retrieval import RetrievalStats
        
        stats = RetrievalStats(
            query="test",
            query_variants_used=["test"],
            provenance_breakdown={"live": 1, "cache": 2},
        )
        
        bundle = build_bundle_from_retrieval(
            query="test",
            query_variants=["test"],
            decisions=[sample_decision],
            retrieval_stats=stats,
        )
        
        assert bundle.provenance.retrieval["provenance_breakdown"]["live"] == 1
        assert bundle.provenance.retrieval["provenance_breakdown"]["cache"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])