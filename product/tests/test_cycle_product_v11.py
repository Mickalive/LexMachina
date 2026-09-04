"""
LexMachina Product Cycle v11 Tests
Tests: design pattern comparison, startup validation, compound language search,
split view infrastructure, and language statistics.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.map_loader import MapLoader
from app.navigation import NavigationAPI


# ---------------------------------------------------------------------------
# Design Pattern Comparison (compare_design_patterns)
# ---------------------------------------------------------------------------

def _get_nav():
    """Get a initialized NavigationAPI for testing."""
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    nav = NavigationAPI(corpus_dir, results_dir)
    nav.initialize()
    return nav


def test_compare_design_patterns_basic():
    """compare_design_patterns returns valid comparison for two patterns."""
    nav = _get_nav()
    result = nav.compare_design_patterns("HIGH-ADVANTAGE", "HIGH-PURITY", zoom_level=1)
    assert "error" not in result, f"Got error: {result.get('error')}"
    assert result["pattern_a"] == "HIGH-ADVANTAGE"
    assert result["pattern_b"] == "HIGH-PURITY"
    assert "representation_a" in result
    assert "representation_b" in result
    assert "name" in result["representation_a"]
    assert "name" in result["representation_b"]


def test_compare_design_patterns_same_pattern():
    """compare_design_patterns with same pattern returns self-comparison."""
    nav = _get_nav()
    result = nav.compare_design_patterns("DEFAULT", "DEFAULT", zoom_level=1)
    assert "error" not in result, f"Got error: {result.get('error')}"
    # Same pattern = same representation = same clusters for all decisions
    stability = result["stability"]["stability_percentage"]
    assert stability == 100.0, f"Same pattern should have 100% stability, got {stability}"


def test_compare_design_patterns_includes_holdout_metrics():
    """Comparison includes holdout JP scores for each pattern."""
    nav = _get_nav()
    result = nav.compare_design_patterns("HIGH-ADVANTAGE", "CITATION-ROLE", zoom_level=1)
    assert "error" not in result
    # Each representation should have holdout info
    assert "representation_a" in result
    assert "representation_b" in result
    assert "holdout_jp" in result["representation_a"]
    assert "holdout_jp" in result["representation_b"]


def test_compare_design_patterns_decision_list():
    """Comparison includes per-decision cluster assignments."""
    nav = _get_nav()
    result = nav.compare_design_patterns("HIGH-ADVANTAGE", "HIGH-PURITY", zoom_level=1)
    assert "error" not in result
    assert "decisions" in result
    assert isinstance(result["decisions"], list)
    if len(result["decisions"]) > 0:
        d = result["decisions"][0]
        assert "decision_id" in d
        assert "cluster_a" in d
        assert "cluster_b" in d


def test_compare_design_patterns_stability():
    """Stability rate is a float between 0 and 100."""
    nav = _get_nav()
    result = nav.compare_design_patterns("HIGH-ADVANTAGE", "HIGH-PURITY", zoom_level=1)
    assert "error" not in result
    stability = result["stability"]["stability_percentage"]
    assert 0.0 <= stability <= 100.0, f"Stability {stability} out of range"


def test_compare_design_patterns_invalid_pattern():
    """Invalid pattern name returns error."""
    nav = _get_nav()
    result = nav.compare_design_patterns("NONEXISTENT", "DEFAULT", zoom_level=1)
    assert "error" in result


# ---------------------------------------------------------------------------
# Startup Validation
# ---------------------------------------------------------------------------

def test_startup_validation_returns_all_reps():
    """startup_validation checks all loaded representations."""
    nav = _get_nav()
    result = nav.startup_validation()
    assert "representations" in result
    assert len(result["representations"]) > 0


def test_startup_validation_per_rep_status():
    """Each representation has a status field (PASS/WARN/FAIL)."""
    nav = _get_nav()
    result = nav.startup_validation()
    for rep_name, rep_info in result["representations"].items():
        assert "status" in rep_info, f"{rep_name} missing status"
        assert rep_info["status"] in ("PASS", "WARN", "FAIL"), f"{rep_name} invalid status: {rep_info['status']}"


def test_startup_validation_default_representation_passes():
    """The PRODUCTION DEFAULT representation (cited_outcome_hybrid_0.5) passes validation per v15b-audit."""
    nav = _get_nav()
    result = nav.startup_validation()
    default = "cited_outcome_hybrid_0.5"
    assert default in result["representations"], f"Default {default} not in validation results"
    assert result["representations"][default]["status"] == "PASS"


def test_startup_validation_timing():
    """startup_validation includes elapsed timing info."""
    nav = _get_nav()
    result = nav.startup_validation()
    assert "elapsed_ms" in result
    assert result["elapsed_ms"] >= 0


def test_startup_validation_totals():
    """startup_validation includes aggregate totals."""
    nav = _get_nav()
    result = nav.startup_validation()
    assert "passing" in result
    assert "warnings" in result
    assert "failing" in result
    assert result["passing"] + result["warnings"] + result["failing"] == len(result["representations"])


# ---------------------------------------------------------------------------
# Compound Language Search
# ---------------------------------------------------------------------------

def test_search_with_language_filter():
    """search_decisions with language='de' returns only German decisions."""
    nav = _get_nav()
    results = nav.search_decisions("recht", limit=20, language="de")
    for r in results:
        assert r.get("language") == "de", f"Expected de, got {r.get('language')}"


def test_search_with_compound_language():
    """search_decisions with language='de,fr' returns German and French."""
    nav = _get_nav()
    results = nav.search_decisions("Bundesgericht", limit=600, language="de,fr")
    languages = set(r.get("language") for r in results)
    assert "de" in languages, "Expected German results"
    assert "fr" in languages, "Expected French results"
    assert languages <= {"de", "fr"}, f"Unexpected languages: {languages}"


def test_search_without_language_returns_all():
    """search_decisions without language filter does not restrict to one language."""
    nav = _get_nav()
    # Use language-neutral term that matches across de/fr/it in the corpus
    results = nav.search_decisions("Bundesgericht", limit=600, language=None)
    languages = set(r.get("language") for r in results)
    assert len(languages) > 1, f"Expected multiple languages, got {languages}"


def test_search_language_invalid():
    """search_decisions with invalid language returns empty or all."""
    nav = _get_nav()
    results = nav.search_decisions("recht", limit=10, language="zz")
    # Should return no results for non-existent language
    for r in results:
        assert r.get("language") == "zz"


# ---------------------------------------------------------------------------
# Language Statistics
# ---------------------------------------------------------------------------

def test_language_stats_structure():
    """get_language_stats returns per-language counts."""
    nav = _get_nav()
    stats = nav.get_language_stats()
    assert "per_language" in stats
    assert isinstance(stats["per_language"], dict)
    # Should have at least de, fr, it
    for lang in ["de", "fr", "it"]:
        assert lang in stats["per_language"], f"Language {lang} missing from stats"
        assert stats["per_language"][lang] > 0


def test_language_stats_branch():
    """get_language_stats includes per-language-branch counts."""
    nav = _get_nav()
    stats = nav.get_language_stats()
    assert "per_language_branch" in stats
    assert isinstance(stats["per_language_branch"], dict)
    # Should have entries like "de:oeffentliches_recht"
    de_branch_keys = [k for k in stats["per_language_branch"] if k.startswith("de:")]
    assert len(de_branch_keys) > 0, "No de:* branch entries found"


def test_language_stats_year_distribution():
    """get_language_stats includes year distribution per language."""
    nav = _get_nav()
    stats = nav.get_language_stats()
    assert "year_distribution" in stats
    assert isinstance(stats["year_distribution"], dict)
    # Should have year entries
    assert len(stats["year_distribution"]) > 0


# ---------------------------------------------------------------------------
# MapLoader design pattern metadata
# ---------------------------------------------------------------------------

def test_design_patterns_count():
    """DESIGN_PATTERNS covers all 29 representations."""
    assert len(MapLoader.DESIGN_PATTERNS) >= 29


def test_representation_purposes():
    """REPRESENTATION_PURPOSES maps key representations to purposes (v15b-audit)."""
    purposes = MapLoader.REPRESENTATION_PURPOSES
    assert "cited_outcome_hybrid_0.5" in purposes
    assert purposes["cited_outcome_hybrid_0.5"] == "production"  # v15b-audit: PRODUCTION DEFAULT
    assert "center_projected_64dim_hierarchical" in purposes
    assert purposes["center_projected_64dim_hierarchical"] == "legacy_default"
