"""
LexMachina Product Tests - Cycle 33033658714
Tests for zoom coherence, language analysis, and TF-IDF proximity features.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.navigation import NavigationAPI
from app.zoom_coherence_loader import ZoomCoherenceLoader
from app.language_analyzer import LanguageAnalyzer
from app.tfidf_proximity import TFIDFProximity


def test_zoom_coherence_loader():
    """Test zoom coherence data loading and summary."""
    print("=== Test: Zoom Coherence Loader ===")
    
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    loader = ZoomCoherenceLoader(str(results_dir))
    loaded = loader.load()
    
    assert loaded, "Zoom coherence data should load"
    print(f"  Loaded: {loaded}")
    
    # Get summary
    summary = loader.get_summary()
    assert "overall_improvement_rate" in summary, "Summary should have improvement rate"
    assert summary["overall_improvement_rate"] > 0, "Improvement rate should be positive"
    assert summary["total_deteriorations"] == 0, "Should have zero deteriorations"
    print(f"  Improvement rate: {summary['overall_improvement_rate']:.1%}")
    print(f"  Total improvements: {summary['total_improvements']}")
    print(f"  Total deteriorations: {summary['total_deteriorations']}")
    print(f"  Best zoom ratio: {summary['best_zoom_ratio']:.3f}")
    print(f"  Flat baseline best ratio: {summary['flat_baseline_best_ratio']:.3f}")
    
    # Get flat baseline
    baseline = loader.get_flat_baseline()
    assert "resolution_1.0" in baseline, "Baseline should have resolution 1.0"
    print(f"  Flat baseline at res 1.0: ratio={baseline['resolution_1.0']['ratio']:.3f}")
    
    # Get cluster improvements
    improvements = loader.get_cluster_improvements(0.25)
    assert "improvements" in improvements, "Should have improvements list"
    assert len(improvements["improvements"]) > 0, "Should have some improvements"
    print(f"  Improvements at coarse res 0.25: {len(improvements['improvements'])}")
    
    print("  PASS")
    return True


def test_language_analyzer():
    """Test language dominance analysis and cross-language neighbors."""
    print("=== Test: Language Analyzer ===")
    
    analyzer = LanguageAnalyzer()
    
    # Test cluster language analysis
    cluster_decisions = [
        {"language": "de", "branch": "strafrecht"},
        {"language": "de", "branch": "strafrecht"},
        {"language": "de", "branch": "zivilrecht"},
        {"language": "fr", "branch": "strafrecht"},
    ]
    
    result = analyzer.analyze_cluster_language_dominance(cluster_decisions, 0)
    assert result["cluster_id"] == 0, "Should have correct cluster ID"
    assert result["n_decisions"] == 4, "Should count 4 decisions"
    assert result["dominant_language"] == "de", "German should be dominant"
    assert result["language_dominance"] == 0.75, "Dominance should be 0.75"
    assert result["warning"] is not None, "Should have warning for 75% dominance"
    print(f"  Cluster 0: dominant={result['dominant_language']}, dominance={result['language_dominance']}")
    print(f"  Warning: {result['warning']}")
    
    # Test empty cluster
    empty_result = analyzer.analyze_cluster_language_dominance([], 1)
    assert empty_result["n_decisions"] == 0, "Empty cluster should have 0 decisions"
    print(f"  Empty cluster: {empty_result['warning']}")
    
    # Test cross-language neighbors
    positions = {
        "doc1": (0.0, 0.0),
        "doc2": (0.1, 0.1),  # Same language, close
        "doc3": (0.2, 0.2),  # Different language, close
        "doc4": (1.0, 1.0),  # Same language, far
    }
    summaries = {
        "doc1": {"language": "de", "branch": "strafrecht"},
        "doc2": {"language": "de", "branch": "zivilrecht"},
        "doc3": {"language": "fr", "branch": "strafrecht"},
        "doc4": {"language": "de", "branch": "oeffentliches_recht"},
    }
    
    neighbors = analyzer.find_cross_language_neighbors(
        "doc1", "de", positions, summaries, n_neighbors=3
    )
    assert len(neighbors) == 3, "Should find 3 neighbors"
    assert neighbors[0]["decision_id"] == "doc2", "Closest should be doc2"
    assert neighbors[0]["is_cross_language"] == False, "doc2 is same language"
    assert neighbors[1]["is_cross_language"] == True, "doc3 is cross-language"
    print(f"  Cross-language neighbors: {len(neighbors)} found")
    print(f"  Closest: {neighbors[0]['decision_id']} (cross-lang={neighbors[0]['is_cross_language']})")
    
    # Test language filter recommendations
    recommendations = analyzer.get_language_filter_recommendations(cluster_decisions, 0)
    assert len(recommendations["recommendations"]) > 0, "Should have recommendations"
    print(f"  Filter recommendations: {len(recommendations['recommendations'])}")
    
    print("  PASS")
    return True


def test_tfidf_proximity():
    """Test TF-IDF proximity calculation."""
    print("=== Test: TF-IDF Proximity ===")
    
    proximity = TFIDFProximity()
    
    # Build from sample documents
    decisions = [
        {"decision_id": "doc1", "full_text": "This is a legal document about criminal law and procedure."},
        {"decision_id": "doc2", "full_text": "This is a legal document about criminal law and procedure."},
        {"decision_id": "doc3", "full_text": "This is a civil law document about contracts and obligations."},
    ]
    
    proximity.build_from_corpus(decisions)
    assert proximity._built, "Model should be built"
    assert len(proximity._vocab) > 0, "Should have vocabulary"
    print(f"  Vocab size: {len(proximity._vocab)}")
    print(f"  Documents: {len(proximity._tfidf_vectors)}")
    
    # Test similarity
    sim_same = proximity.cosine_similarity("doc1", "doc2")
    sim_diff = proximity.cosine_similarity("doc1", "doc3")
    assert sim_same > sim_diff, "Same-topic documents should be more similar"
    print(f"  Similarity (same topic): {sim_same:.4f}")
    print(f"  Similarity (different topic): {sim_diff:.4f}")
    
    # Test explanation
    summaries = {
        "doc1": {"decision_id": "doc1", "language": "en"},
        "doc2": {"decision_id": "doc2", "language": "en"},
    }
    explanation = proximity.get_similarity_explanation("doc1", "doc2", summaries)
    assert "text_similarity" in explanation, "Explanation should have similarity"
    assert "top_shared_terms" in explanation, "Explanation should have shared terms"
    print(f"  Explanation similarity: {explanation['text_similarity']:.4f}")
    print(f"  Shared terms: {explanation['n_shared_terms']}")
    
    print("  PASS")
    return True


def test_navigation_new_endpoints():
    """Test new navigation API endpoints."""
    print("=== Test: Navigation New Endpoints ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    nav = NavigationAPI(str(corpus_dir), str(results_dir))
    nav.initialize()
    
    # Test zoom coherence summary
    zoom_summary = nav.get_zoom_coherence_summary()
    assert "overall_improvement_rate" in zoom_summary, "Zoom summary should have improvement rate"
    print(f"  Zoom coherence: {zoom_summary['overall_improvement_rate']:.1%} improvement rate")
    
    # Test zoom coherence flat baseline
    flat_baseline = nav.get_zoom_coherence_flat_baseline()
    assert "resolution_1.0" in flat_baseline, "Flat baseline should have resolution 1.0"
    print(f"  Flat baseline res 1.0: ratio={flat_baseline['resolution_1.0']['ratio']:.3f}")
    
    # Test cluster language analysis
    lang_analysis = nav.get_cluster_language_analysis("concat_center_tfidf", 1, 0)
    assert "language_dominance" in lang_analysis, "Language analysis should have dominance score"
    print(f"  Cluster 0 language dominance: {lang_analysis['language_dominance']:.3f}")
    
    # Test cross-language neighbors
    cross_lang = nav.get_cross_language_neighbors("bger_7B_832_2024", 5)
    assert "same_language_neighbors" in cross_lang, "Should have same-language neighbors"
    assert "cross_language_neighbors" in cross_lang, "Should have cross-language neighbors"
    print(f"  Same-lang neighbors: {len(cross_lang['same_language_neighbors'])}")
    print(f"  Cross-lang neighbors: {len(cross_lang['cross_language_neighbors'])}")
    
    # Test text similarity
    text_sim = nav.get_text_similarity("bger_7B_832_2024", "bger_7B_545_2023")
    assert "text_similarity" in text_sim, "Text similarity should have score"
    assert text_sim["text_similarity"] > 0, "Similar documents should have positive similarity"
    print(f"  Text similarity: {text_sim['text_similarity']:.4f}")
    print(f"  Shared terms: {text_sim['n_shared_terms']}")
    
    print("  PASS")
    return True


if __name__ == "__main__":
    tests = [
        test_zoom_coherence_loader,
        test_language_analyzer,
        test_tfidf_proximity,
        test_navigation_new_endpoints,
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_func in tests:
        try:
            print(f'\nRunning {test_func.__name__}...')
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_func.__name__, str(e)))
            print(f'  FAILED: {e}')
    
    print(f'\n=== Test Results ===')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    if errors:
        print('Errors:')
        for name, error in errors:
            print(f'  {name}: {error}')
