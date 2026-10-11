"""
LexMachina Product Tests — Cycle 33032746334
Tests for proximity explanations, cluster coherence, and language-aware features.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.corpus_loader import CorpusLoader
from app.map_loader import MapLoader
from app.navigation import NavigationAPI
from app.proximity_explainer import ProximityExplainer, FEATURE_WEIGHTS


def test_proximity_explainer_basic():
    """Test proximity explanation between two known decisions."""
    print("=== Test: Proximity Explainer (basic) ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    corpus = CorpusLoader(str(corpus_dir))
    corpus.load()
    
    explainer = ProximityExplainer(corpus)
    
    # Find two decisions in the same branch
    same_branch = None
    ids = list(corpus.decisions.keys())
    for i, id_a in enumerate(ids):
        for id_b in ids[i+1:i+50]:
            a = corpus.get(id_a)
            b = corpus.get(id_b)
            if a and b and a.branch == b.branch and a.language == b.language:
                same_branch = (id_a, id_b)
                break
        if same_branch:
            break
    
    assert same_branch, "Could not find two decisions in same branch"
    id_a, id_b = same_branch
    
    result = explainer.explain(id_a, id_b, distance=0.5)
    
    assert "proximity_score" in result, "Missing proximity_score"
    assert "feature_contributions" in result, "Missing feature_contributions"
    assert "warnings" in result, "Missing warnings"
    assert "summary" in result, "Missing summary"
    assert 0 <= result["proximity_score"] <= 1, f"Score out of range: {result['proximity_score']}"
    assert len(result["feature_contributions"]) == 6, f"Expected 6 features, got {len(result['feature_contributions'])}"
    
    # Same branch + language should have decent proximity
    assert result["proximity_score"] > 0.2, f"Expected >0.2 proximity for same branch, got {result['proximity_score']}"
    
    print(f"  {id_a} <-> {id_b}")
    print(f"  Proximity score: {result['proximity_score']:.3f}")
    print(f"  Matching features: {sum(1 for f in result['feature_contributions'] if f['match'])}/6")
    print(f"  Warnings: {len(result['warnings'])}")
    print(f"  Summary: {result['summary'][:100]}")
    
    print("  PASS\n")
    return True


def test_proximity_explainer_cross_branch():
    """Test proximity explanation between decisions in different branches."""
    print("=== Test: Proximity Explainer (cross-branch) ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    corpus = CorpusLoader(str(corpus_dir))
    corpus.load()
    
    explainer = ProximityExplainer(corpus)
    
    # Find two decisions in different branches
    diff_branch = None
    ids = list(corpus.decisions.keys())
    for i, id_a in enumerate(ids):
        for id_b in ids[i+1:i+100]:
            a = corpus.get(id_a)
            b = corpus.get(id_b)
            if a and b and a.branch != b.branch:
                diff_branch = (id_a, id_b)
                break
        if diff_branch:
            break
    
    assert diff_branch, "Could not find two decisions in different branches"
    id_a, id_b = diff_branch
    
    result = explainer.explain(id_a, id_b, distance=2.0)
    
    # Cross-branch should have warnings or lower proximity
    branch_feature = next(f for f in result["feature_contributions"] if f["feature"] == "branch")
    assert not branch_feature["match"], "Branch should not match for cross-branch pair"
    
    print(f"  {id_a} <-> {id_b}")
    print(f"  Proximity score: {result['proximity_score']:.3f}")
    print(f"  Branch match: {branch_feature['match']}")
    print(f"  Warnings: {result['warnings']}")
    
    print("  PASS\n")
    return True


def test_proximity_explainer_language_warning():
    """Test that language-dominated proximity triggers warnings."""
    print("=== Test: Proximity Explainer (language warning) ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    corpus = CorpusLoader(str(corpus_dir))
    corpus.load()
    
    explainer = ProximityExplainer(corpus)
    
    # Find two decisions with same language but different branch
    same_lang_diff_branch = None
    ids = list(corpus.decisions.keys())
    for i, id_a in enumerate(ids):
        for id_b in ids[i+1:i+100]:
            a = corpus.get(id_a)
            b = corpus.get(id_b)
            if a and b and a.language == b.language and a.branch != b.branch:
                same_lang_diff_branch = (id_a, id_b)
                break
        if same_lang_diff_branch:
            break
    
    assert same_lang_diff_branch, "Could not find same-language different-branch pair"
    id_a, id_b = same_lang_diff_branch
    
    result = explainer.explain(id_a, id_b, distance=1.0)
    
    # Should have language as significant contributor
    lang_feature = next(f for f in result["feature_contributions"] if f["feature"] == "language")
    assert lang_feature["match"], "Language should match"
    
    # Should NOT have branch matching
    branch_feature = next(f for f in result["feature_contributions"] if f["feature"] == "branch")
    assert not branch_feature["match"], "Branch should not match"
    
    print(f"  {id_a} ({corpus.get(id_a).branch}) <-> {id_b} ({corpus.get(id_b).branch})")
    print(f"  Language: {corpus.get(id_a).language}")
    print(f"  Proximity score: {result['proximity_score']:.3f}")
    print(f"  Warnings: {result['warnings']}")
    print(f"  Suggested views: {result['suggested_views']}")
    
    print("  PASS\n")
    return True


def test_proximity_explainer_missing_decision():
    """Test graceful handling of missing decision IDs."""
    print("=== Test: Proximity Explainer (missing decision) ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    corpus = CorpusLoader(str(corpus_dir))
    corpus.load()
    
    explainer = ProximityExplainer(corpus)
    
    result = explainer.explain("nonexistent_decision_a", "nonexistent_decision_b")
    
    assert result["proximity_score"] == 0.0, "Score should be 0 for missing decisions"
    assert len(result["warnings"]) > 0, "Should have warnings for missing decisions"
    assert result["summary"].startswith("Error:"), "Summary should indicate error"
    
    print(f"  Warnings: {result['warnings']}")
    print(f"  Summary: {result['summary']}")
    
    print("  PASS\n")
    return True


def test_proximity_feature_weights():
    """Test that feature weights are correctly configured."""
    print("=== Test: Proximity Feature Weights ===")
    
    # Verify weights sum to 1.0
    total = sum(FEATURE_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights should sum to 1.0, got {total}"
    
    # Verify language is intentionally downweighted
    assert FEATURE_WEIGHTS["language"] < FEATURE_WEIGHTS["branch"], \
        "Language should be weighted less than branch"
    assert FEATURE_WEIGHTS["language"] < FEATURE_WEIGHTS["legal_area"], \
        "Language should be weighted less than legal_area"
    
    print(f"  Feature weights: {FEATURE_WEIGHTS}")
    print(f"  Total: {total}")
    print(f"  Language < Branch: {FEATURE_WEIGHTS['language'] < FEATURE_WEIGHTS['branch']}")
    print(f"  Language < Legal_area: {FEATURE_WEIGHTS['language'] < FEATURE_WEIGHTS['legal_area']}")
    
    print("  PASS\n")
    return True


def test_cluster_coherence():
    """Test cluster coherence analysis."""
    print("=== Test: Cluster Coherence ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Get cluster coherence for first cluster at zoom 1
    coherence = api.get_cluster_coherence("concat_center_tfidf", 1, 0)
    
    assert "cluster_id" in coherence, "Missing cluster_id"
    assert "language_distribution" in coherence, "Missing language_distribution"
    assert "branch_distribution" in coherence, "Missing branch_distribution"
    assert "purity_score" in coherence, "Missing purity_score"
    assert 0 <= coherence["purity_score"] <= 1, f"Purity out of range: {coherence['purity_score']}"
    
    print(f"  Cluster {coherence['cluster_id']}: {coherence['size']} decisions")
    print(f"  Language distribution: {coherence['language_distribution']}")
    print(f"  Branch distribution: {coherence['branch_distribution']}")
    print(f"  Dominant language: {coherence['dominant_language']}")
    print(f"  Dominant branch: {coherence['dominant_branch']}")
    print(f"  Purity score: {coherence['purity_score']:.3f}")
    print(f"  Coherence warning: {coherence['coherence_warning']}")
    
    print("  PASS\n")
    return True


def test_cluster_coherence_all_clusters():
    """Test coherence for multiple clusters."""
    print("=== Test: Cluster Coherence (all clusters) ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Get map data to find all cluster IDs
    map_data = api.get_map_data("concat_center_tfidf", 1)
    cluster_ids = [c["cluster_id"] for c in map_data["clusters"]]
    
    print(f"  Testing {len(cluster_ids)} clusters at zoom 1")
    
    for cid in cluster_ids:
        coherence = api.get_cluster_coherence("concat_center_tfidf", 1, cid)
        assert "purity_score" in coherence, f"Cluster {cid} missing purity_score"
        print(f"    Cluster {cid}: {coherence['size']} decisions, purity={coherence['purity_score']:.3f}, "
              f"warning={coherence['coherence_warning'] or 'none'}")
    
    print("  PASS\n")
    return True


def test_proximity_api_endpoint():
    """Test the proximity API endpoint through NavigationAPI."""
    print("=== Test: Proximity API Endpoint ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Get two decisions from the map
    positions = api.map_loader.get_positions("concat_center_tfidf")
    ids = list(positions.keys())[:2]
    
    result = api.get_proximity_explanation(ids[0], ids[1])
    
    assert "proximity_score" in result, "Missing proximity_score"
    assert "feature_contributions" in result, "Missing feature_contributions"
    assert len(result["feature_contributions"]) == 6, f"Expected 6 features, got {len(result['feature_contributions'])}"
    
    print(f"  {ids[0]} <-> {ids[1]}")
    print(f"  Proximity score: {result['proximity_score']:.3f}")
    print(f"  Features: {len(result['feature_contributions'])}")
    print(f"  Warnings: {len(result['warnings'])}")
    
    # Test with missing decision
    result_missing = api.get_proximity_explanation("nonexistent", ids[0])
    assert "error" in result_missing, "Should return error for missing decision"
    
    print("  PASS\n")
    return True


def test_language_filter():
    """Test language-aware map data filtering."""
    print("=== Test: Language Filter ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Get unfiltered data
    all_data = api.get_map_data("concat_center_tfidf", 1)
    total = len(all_data["positions"])
    
    # Get filtered data (German only)
    filtered = api.get_map_data_with_language_filter("concat_center_tfidf", 1, ["de"])
    visible = [p for p in filtered["positions"] if not p.get("filtered_out", False)]
    hidden = [p for p in filtered["positions"] if p.get("filtered_out", False)]
    
    print(f"  Total positions: {total}")
    print(f"  Visible (de): {len(visible)}")
    print(f"  Hidden: {len(hidden)}")
    assert len(visible) > 0, "Should have some German decisions"
    assert len(hidden) > 0, "Should have some hidden decisions"
    assert len(visible) + len(hidden) == total, "Visible + hidden should equal total"
    
    # All visible should be German
    for p in visible:
        assert p["language"] == "de", f"Visible position should be German: {p['language']}"
    
    # All hidden should NOT be German
    for p in hidden:
        assert p["language"] != "de", f"Hidden position should not be German: {p['language']}"
    
    print("  PASS\n")
    return True


if __name__ == "__main__":
    results = []
    results.append(("Proximity Explainer (basic)", test_proximity_explainer_basic()))
    results.append(("Proximity Explainer (cross-branch)", test_proximity_explainer_cross_branch()))
    results.append(("Proximity Explainer (language warning)", test_proximity_explainer_language_warning()))
    results.append(("Proximity Explainer (missing)", test_proximity_explainer_missing_decision()))
    results.append(("Proximity Feature Weights", test_proximity_feature_weights()))
    results.append(("Cluster Coherence", test_cluster_coherence()))
    results.append(("Cluster Coherence (all)", test_cluster_coherence_all_clusters()))
    results.append(("Proximity API Endpoint", test_proximity_api_endpoint()))
    results.append(("Language Filter", test_language_filter()))
    
    print("=" * 50)
    print("RESULTS:")
    for name, passed in results:
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    
    all_passed = all(p for _, p in results)
    print(f"\nOverall: {'ALL PASS' if all_passed else 'SOME FAILED'}")
    sys.exit(0 if all_passed else 1)
