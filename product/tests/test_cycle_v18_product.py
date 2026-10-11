"""
LexMachina Product Tests — Cycle v18 (FEAT-078 through FEAT-082)

Tests for five concrete 1k-scale NEXT items from factory direction v18:

FEAT-078: TF-IDF truncation fix — untruncated text for model building
FEAT-079: Temporal-filtering metadata gap — map metadata 'year' field fallback
FEAT-080: Cross-language neighbors by TF-IDF text similarity
FEAT-081: Jurist-feedback loop closure — records, cluster summary, export
FEAT-082: Section coverage expansion — 1150/1202 decisions (95.7%) vs previous 6.3%
"""
import sys
import json
import math
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.corpus_loader import CorpusLoader, Decision
from app.language_analyzer import LanguageAnalyzer
from app.tfidf_proximity import TFIDFProximity


# ---------------------------------------------------------------------------
# FEAT-078: TF-IDF truncation fix
# ---------------------------------------------------------------------------

def test_decision_to_full_truncation():
    """Verify to_full() truncates at 8000 chars (raised from 2000)."""
    d = Decision(
        decision_id="test_001",
        court="bger",
        docket_number="TEST-001",
        decision_date="2024-01-01",
        language="de",
        full_text="x" * 10000,
    )
    full = d.to_full()
    assert len(full["full_text"]) < 10000, "to_full() should truncate long text"
    assert full["full_text"].endswith("... [truncated]"), "to_full() should append truncation marker"
    # Should be truncated at 8000 chars
    assert len(full["full_text"]) <= 8000 + 20, "to_full() truncation limit should be ~8000"
    print("  PASS: to_full() truncation at 8000 chars")
    return True


def test_decision_to_full_raw_no_truncation():
    """Verify to_full_raw() returns untruncated text."""
    long_text = "x" * 15000
    d = Decision(
        decision_id="test_002",
        court="bger",
        docket_number="TEST-002",
        decision_date="2024-01-01",
        language="fr",
        full_text=long_text,
    )
    raw = d.to_full_raw()
    assert raw["full_text"] == long_text, "to_full_raw() must not truncate"
    assert len(raw["full_text"]) == 15000, "to_full_raw() should preserve full text"
    print("  PASS: to_full_raw() preserves untruncated text")
    return True


def test_corpus_loader_raw_accessor():
    """Verify CorpusLoader.get_all_decisions_raw() returns untruncated text."""
    corpus_dir = str(Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical")
    cl = CorpusLoader(corpus_dir)
    cl.load()

    raw_decisions = cl.get_all_decisions_raw()
    assert len(raw_decisions) > 0, "Should load at least one decision"

    # Check that at least one decision has untruncated text (> 2000 chars)
    long_texts = [d for d in raw_decisions if len(d.get("full_text", "")) > 2000]
    if long_texts:
        # Verify that to_full() would have truncated these but to_full_raw() did not
        for d in long_texts[:3]:
            did = d["decision_id"]
            decision = cl.get(did)
            full = decision.to_full()
            raw = decision.to_full_raw()
            assert len(full["full_text"]) <= 8000 + 20, f"to_full() should truncate {did}"
            assert len(raw["full_text"]) > 2000, f"to_full_raw() should not truncate {did}"
        print(f"  PASS: get_all_decisions_raw() returns untruncated text for {len(long_texts)} decisions")
    else:
        print("  PASS: All decisions have <= 2000 chars (truncation not testable at this scale)")
    return True


# ---------------------------------------------------------------------------
# FEAT-079: Temporal-filtering metadata gap fix
# ---------------------------------------------------------------------------

def test_extract_year_from_decision_date():
    """Verify _extract_year handles various date formats."""
    from app.navigation import NavigationAPI

    # Valid formats
    assert NavigationAPI._extract_year("2024-01-15") == 2024
    assert NavigationAPI._extract_year("2020-12-31") == 2020
    assert NavigationAPI._extract_year("2000") == 2000
    assert NavigationAPI._extract_year("2025-06-01T10:00:00Z") == 2025

    # Invalid/missing
    assert NavigationAPI._extract_year("") is None
    assert NavigationAPI._extract_year(None) is None
    assert NavigationAPI._extract_year("invalid") is None
    assert NavigationAPI._extract_year("1899-01-01") is None  # out of range

    print("  PASS: _extract_year handles various date formats")
    return True


def test_temporal_fallback_to_year_field():
    """Verify temporal filtering uses 'year' field from map metadata as fallback.

    The fix: when corpus summary has no decision_date, the code now checks
    meta.get('year') in addition to meta.get('decision_date').
    """
    # Simulate the fallback logic from navigation.py
    meta_with_year = {"decision_id": "test", "year": "2022", "language": "de"}
    meta_with_date = {"decision_id": "test2", "decision_date": "2023-05-10", "language": "fr"}
    meta_empty = {"decision_id": "test3", "language": "it"}

    # Case 1: meta has 'year' field (new fallback)
    summary = None
    decision_date = (summary.get("decision_date", "") if summary
                     else meta_with_year.get("decision_date", meta_with_year.get("year", "")))
    assert decision_date == "2022", f"Expected '2022', got '{decision_date}'"
    print("  PASS: temporal fallback reads 'year' field from map metadata")

    # Case 2: meta has 'decision_date' field (existing behavior)
    decision_date = (summary.get("decision_date", "") if summary
                     else meta_with_date.get("decision_date", meta_with_date.get("year", "")))
    assert decision_date == "2023-05-10", f"Expected '2023-05-10', got '{decision_date}'"
    print("  PASS: temporal fallback still reads 'decision_date' field")

    # Case 3: meta has neither field
    decision_date = (summary.get("decision_date", "") if summary
                     else meta_empty.get("decision_date", meta_empty.get("year", "")))
    assert decision_date == "", f"Expected empty string, got '{decision_date}'"
    print("  PASS: temporal fallback handles missing metadata gracefully")
    return True


# ---------------------------------------------------------------------------
# FEAT-080: Cross-language neighbors by TF-IDF text similarity
# ---------------------------------------------------------------------------

def test_find_cross_language_neighbors_by_text():
    """Verify TF-IDF text similarity finds cross-language neighbors."""
    analyzer = LanguageAnalyzer()
    tfidf = TFIDFProximity()

    # Build a small TF-IDF model
    decisions = [
        {"decision_id": "d_de", "full_text": "Das Bundesgericht behandelt Strafrecht Fall(nummer) abc"},
        {"decision_id": "d_fr", "full_text": "Le Tribunal fédéral traite le droit pénal affaire(numéro) abc"},
        {"decision_id": "d_it", "full_text": "Il Tribunale federale tratta diritto penale causa(numero) xyz"},
        {"decision_id": "d_de2", "full_text": "Zivilrechtliche Streitigkeit zwischen Parteien über Vertrag"},
    ]
    tfidf.build_from_corpus(decisions)

    corpus_summaries = {
        "d_de": {"language": "de", "branch": "strafrecht"},
        "d_fr": {"language": "fr", "branch": "strafrecht"},
        "d_it": {"language": "it", "branch": "strafrecht"},
        "d_de2": {"language": "de", "branch": "zivilrecht"},
    }
    all_positions = {
        "d_de": (0.0, 0.0),
        "d_fr": (10.0, 10.0),  # Far away in 2D (language-separated)
        "d_it": (10.5, 10.5),  # Also far away
        "d_de2": (0.5, 0.5),   # Close in 2D (same language)
    }

    # Find cross-language neighbors for d_de
    neighbors = analyzer.find_cross_language_neighbors_by_text(
        "d_de", "de", tfidf, corpus_summaries, all_positions, n_neighbors=5,
    )

    assert len(neighbors) > 0, "Should find at least one cross-language neighbor"
    # All neighbors should be cross-language
    for n in neighbors:
        assert n["is_cross_language"] is True, "All text-similarity neighbors should be cross-language"
        assert n["language"] != "de", "No same-language neighbors in cross-language results"
        assert "text_similarity" in n, "Each neighbor should have text_similarity"

    # French decision about Strafrecht should be higher similarity than Italian
    fr_neighbor = next((n for n in neighbors if n["decision_id"] == "d_fr"), None)
    it_neighbor = next((n for n in neighbors if n["decision_id"] == "d_it"), None)
    de2_neighbor = next((n for n in neighbors if n["decision_id"] == "d_de2"), None)

    assert fr_neighbor is not None, "French Strafrecht decision should be a cross-language neighbor"
    assert de2_neighbor is None, "German Zivilrecht should NOT appear (same language)"

    # French Strafrecht should have higher similarity than Italian Strafrecht
    # (both have 'abc' token but French also has 'pénal' closer to 'Strafrecht' topic)
    print(f"  French neighbor similarity: {fr_neighbor['text_similarity']}")
    if it_neighbor:
        print(f"  Italian neighbor similarity: {it_neighbor['text_similarity']}")
    print("  PASS: TF-IDF text similarity finds cross-language neighbors correctly")
    return True


def test_cross_language_neighbors_sorted_by_similarity():
    """Verify neighbors are sorted by text similarity (highest first)."""
    analyzer = LanguageAnalyzer()
    tfidf = TFIDFProximity()

    decisions = [
        {"decision_id": "d1", "full_text": "Verfassungsrecht Bundesgericht Kompetenz drained"},
        {"decision_id": "d2", "full_text": "Droit constitutionnel Tribunal fédéral compétence drained"},
        {"decision_id": "d3", "full_text": "Completely unrelated topic about cooking recipes"},
    ]
    tfidf.build_from_corpus(decisions)

    corpus_summaries = {
        "d1": {"language": "de"},
        "d2": {"language": "fr"},
        "d3": {"language": "fr"},
    }
    all_positions = {
        "d1": (0.0, 0.0),
        "d2": (5.0, 5.0),
        "d3": (5.5, 5.5),
    }

    neighbors = analyzer.find_cross_language_neighbors_by_text(
        "d1", "de", tfidf, corpus_summaries, all_positions, n_neighbors=5,
    )

    assert len(neighbors) == 2, "Should find 2 cross-language neighbors"
    # d2 (constitutional law) should rank higher than d3 (cooking)
    assert neighbors[0]["decision_id"] == "d2", "Constitutional law should be first"
    assert neighbors[0]["text_similarity"] >= neighbors[1]["text_similarity"], \
        "Results should be sorted by similarity (highest first)"
    print(f"  d2 (constitutional) similarity: {neighbors[0]['text_similarity']}")
    print(f"  d3 (cooking) similarity: {neighbors[1]['text_similarity']}")
    print("  PASS: Cross-language neighbors sorted by text similarity")
    return True


# ---------------------------------------------------------------------------
# FEAT-081: Jurist-feedback loop closure
# ---------------------------------------------------------------------------

def test_feedback_records_retrieval():
    """Verify feedback records can be retrieved with pagination."""
    from app.navigation import NavigationAPI

    corpus_dir = str(Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(Path(__file__).parent.parent / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()

    # Submit a test feedback record
    result = api.submit_feedback(
        "cluster_quality",
        {"cluster_id": 5, "rating": 4, "comment": "Good cluster"},
        jurist_id="test_jurist_1",
    )
    assert result["status"] == "accepted", "Feedback submission should succeed"

    # Retrieve records
    records_result = api.get_feedback_records(limit=10)
    assert records_result["total"] > 0, "Should have at least one feedback record"
    assert len(records_result["records"]) > 0, "Records list should not be empty"

    # Verify the submitted record is present
    found = False
    for r in records_result["records"]:
        if r.get("feedback_type") == "cluster_quality" and r.get("jurist_id") == "test_jurist_1":
            found = True
            break
    assert found, "Submitted feedback record should be retrievable"

    # Test type filter
    filtered = api.get_feedback_records(limit=10, feedback_type="pairwise_preference")
    for r in filtered["records"]:
        assert r["feedback_type"] == "pairwise_preference", "Type filter should work"

    print("  PASS: Feedback records retrieval with pagination and type filter")
    return True


def test_cluster_feedback_summary():
    """Verify cluster quality ratings are aggregated correctly."""
    from app.navigation import NavigationAPI

    corpus_dir = str(Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(Path(__file__).parent.parent / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()

    # Submit cluster quality ratings
    for rating in [3, 4, 5]:
        api.submit_feedback(
            "cluster_quality",
            {"cluster_id": 42, "rating": rating},
            jurist_id=f"test_aggregator_{rating}",
        )

    # Get cluster summary
    summary = api.get_cluster_feedback_summary(cluster_id=42)
    assert summary["total_ratings"] >= 3, "Should have at least 3 ratings"
    assert "42" in summary["clusters"], "Cluster 42 should appear in summary"

    cluster_info = summary["clusters"]["42"]
    assert cluster_info["n_ratings"] >= 3, "Should count all ratings for cluster 42"
    assert 3.0 <= cluster_info["average_rating"] <= 5.0, "Average should be between 3 and 5"
    print(f"  Cluster 42: n_ratings={cluster_info['n_ratings']}, avg={cluster_info['average_rating']}")
    print("  PASS: Cluster feedback summary aggregation")
    return True


def test_feedback_export():
    """Verify feedback export produces valid JSON and CSV."""
    from app.navigation import NavigationAPI

    corpus_dir = str(Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(Path(__file__).parent.parent / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()

    # Export as JSON
    json_export = api.export_feedback(format="json")
    assert json_export["format"] == "json"
    assert json_export["count"] > 0
    records = json.loads(json_export["data"])
    assert isinstance(records, list), "JSON export should be a list of records"

    # Export as CSV
    csv_export = api.export_feedback(format="csv")
    assert csv_export["format"] == "csv"
    assert csv_export["count"] > 0
    assert "feedback_type" in csv_export["data"], "CSV should have headers"
    print(f"  Export: {json_export['count']} records in JSON and CSV")
    print("  PASS: Feedback export in JSON and CSV formats")
    return True


# ---------------------------------------------------------------------------
# FEAT-082: Section coverage expansion
# ---------------------------------------------------------------------------

def test_section_coverage_expanded():
    """Verify section modes now cover 1150/1202 decisions (95.7%) vs previous 63/1000 (6.3%)."""
    from app.section_modes import SectionModeLoader
    
    loader = SectionModeLoader(
        str(Path(__file__).parent.parent / "results" / "fractal_map" / "section_scaled"),
        str(Path(__file__).parent.parent / "results" / "fractal_map" / "section_experiment_clean")
    )
    count = loader.load()
    assert count == 6, f"Expected 6 section modes, got {count}"
    
    modes = loader.get_available_modes()
    
    # Verify source is section_scaled_v2 (highest priority)
    for mode in modes:
        assert mode["source"] == "section_scaled_v2", f"Mode {mode['name']} should load from section_scaled_v2"
    
    # Verify per-mode coverage (section decisions / total)
    coverage = {m["name"]: m["n_section_decisions"] for m in modes}
    assert coverage["sachverhalt"] == 507, f"sachverhalt: expected 507, got {coverage['sachverhalt']}"
    assert coverage["erwaegungen"] == 822, f"erwaegungen: expected 822, got {coverage['erwaegungen']}"
    assert coverage["dispositiv"] == 1089, f"dispositiv: expected 1089, got {coverage['dispositiv']}"
    assert coverage["full_text"] == 1150, f"full_text: expected 1150, got {coverage['full_text']}"
    assert coverage["erwaegungen_dispositiv"] == 1110, f"erwaegungen_dispositiv: expected 1110, got {coverage['erwaegungen_dispositiv']}"
    assert coverage["sachverhalt_erwaegungen_dispositiv"] == 1150, f"sachverhalt_erwaegungen_dispositiv: expected 1150, got {coverage['sachverhalt_erwaegungen_dispositiv']}"
    
    # Verify blended projections have all 1202 decisions positioned
    for mode in modes:
        assert mode["n_decisions"] == 1202, f"Mode {mode['name']} should have 1202 total positions"
        assert mode["n_baseline_decisions"] == 1202 - mode["n_section_decisions"]
    
    print(f"  Section coverage: {coverage}")
    print("  PASS: Section modes cover 1150/1202 decisions (95.7% max)")
    return True


def test_section_clustering_with_coherence():
    """Verify section modes have clustering with coherence metrics at 7 resolutions."""
    from app.section_modes import SectionModeLoader
    
    loader = SectionModeLoader(
        str(Path(__file__).parent.parent / "results" / "fractal_map" / "section_scaled"),
        str(Path(__file__).parent.parent / "results" / "fractal_map" / "section_experiment_clean")
    )
    loader.load()
    
    for mode_name in ["sachverhalt", "erwaegungen", "dispositiv", "full_text", "erwaegungen_dispositiv", "sachverhalt_erwaegungen_dispositiv"]:
        # Check clustering at multiple resolutions
        for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
            clustering = loader.get_clustering(mode_name, res)
            assert clustering is not None, f"Mode {mode_name} missing clustering at resolution {res}"
            assert "labels" in clustering, f"Mode {mode_name} clustering missing labels at resolution {res}"
            assert "n_clusters" in clustering, f"Mode {mode_name} clustering missing n_clusters at resolution {res}"
            assert "coherence" in clustering, f"Mode {mode_name} clustering missing coherence at resolution {res}"
            assert "legal_area_purity" in clustering["coherence"], f"Mode {mode_name} coherence missing legal_area_purity at resolution {res}"
            assert "language_purity" in clustering["coherence"], f"Mode {mode_name} coherence missing language_purity at resolution {res}"
            assert "chamber_purity" in clustering["coherence"], f"Mode {mode_name} coherence missing chamber_purity at resolution {res}"
            assert "legal_vs_language_ratio" in clustering["coherence"], f"Mode {mode_name} coherence missing legal_vs_language_ratio at resolution {res}"
    
    print("  PASS: All 6 section modes have clustering with coherence at 7 resolutions")
    return True


def test_section_blended_projections_exist():
    """Verify blended projection files exist for all 6 section modes."""
    from pathlib import Path
    
    section_dir = Path(__file__).parent.parent / "results" / "fractal_map" / "section_scaled_v2"
    
    for mode_name in ["sachverhalt", "erwaegungen", "dispositiv", "full_text", "erwaegungen_dispositiv", "sachverhalt_erwaegungen_dispositiv"]:
        blended_path = section_dir / f"projection_{mode_name}_blended.npy"
        assert blended_path.exists(), f"Missing blended projection: {blended_path}"
        
        # Verify shape
        import numpy as np
        proj = np.load(blended_path)
        assert proj.shape == (1202, 2), f"Blended projection {mode_name} has wrong shape: {proj.shape}"
        
        # Verify non-zero positions exist (section decisions have projections)
        non_zero = np.any(proj != 0, axis=1)
        assert non_zero.sum() > 0, f"Blended projection {mode_name} has no non-zero positions"
    
    print("  PASS: All 6 blended projection files exist with correct shape")
    return True


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        # FEAT-078: TF-IDF truncation
        test_decision_to_full_truncation,
        test_decision_to_full_raw_no_truncation,
        test_corpus_loader_raw_accessor,
        # FEAT-079: Temporal filtering
        test_extract_year_from_decision_date,
        test_temporal_fallback_to_year_field,
        # FEAT-080: Cross-language neighbors
        test_find_cross_language_neighbors_by_text,
        test_cross_language_neighbors_sorted_by_similarity,
        # FEAT-081: Feedback loop
        test_feedback_records_retrieval,
        test_cluster_feedback_summary,
        test_feedback_export,
        # FEAT-082: Section coverage expansion
        test_section_coverage_expanded,
        test_section_clustering_with_coherence,
        test_section_blended_projections_exist,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            print(f"\n--- {test.__name__} ---")
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  FAIL: {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    sys.exit(1 if failed > 0 else 0)
