"""
LexMachina Product Cycle v10 Tests
Tests: design patterns, holdout metrics, representation recommendations,
Navigation API new endpoints, and representation metadata.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.map_loader import MapLoader
from app.evaluation_loader import EvaluationLoader
from app.navigation import NavigationAPI


# ---------------------------------------------------------------------------
# Design patterns in MapLoader
# ---------------------------------------------------------------------------

def test_design_patterns_all_five_exist():
    """All 5 design pattern labels exist in MapLoader.DESIGN_PATTERNS."""
    expected = {"DEFAULT", "HIGH-PURITY", "HIGH-ADVANTAGE", "CITATION-ROLE", "LEGACY"}
    actual = set(MapLoader.DESIGN_PATTERNS.values())
    assert expected == actual, f"Missing patterns: {expected - actual}"


def test_design_patterns_default_representation():
    """DEFAULT pattern maps to center_projected_64dim_hierarchical."""
    pattern = MapLoader.DESIGN_PATTERNS["center_projected_64dim_hierarchical"]
    assert pattern == "DEFAULT"


def test_design_patterns_high_purity_representations():
    """HIGH-PURITY pattern includes the expected metric-learning representations."""
    hp_reps = [k for k, v in MapLoader.DESIGN_PATTERNS.items() if v == "HIGH-PURITY"]
    assert "linear_metric_best" in hp_reps
    assert "mahalanobis_best" in hp_reps
    assert "hybrid_stabilized_best" in hp_reps


def test_design_patterns_high_advantage_representations():
    """HIGH-ADVANTAGE pattern includes citation/outcome hybrids."""
    ha_reps = [k for k, v in MapLoader.DESIGN_PATTERNS.items() if v == "HIGH-ADVANTAGE"]
    assert "cited_decisions_tfidf" in ha_reps
    assert "cited_outcome_hybrid_0.5" in ha_reps
    assert "cited_outcome_hybrid_0.7" in ha_reps


def test_design_patterns_citation_role_representations():
    """CITATION-ROLE pattern includes the three role views."""
    cr_reps = [k for k, v in MapLoader.DESIGN_PATTERNS.items() if v == "CITATION-ROLE"]
    assert "following_alpha0.3" in cr_reps
    assert "criticizing_alpha0.3" in cr_reps
    assert "citing_alpha0.3" in cr_reps


def test_design_patterns_legacy_representations():
    """LEGACY pattern includes legacy representations."""
    leg_reps = [k for k, v in MapLoader.DESIGN_PATTERNS.items() if v == "LEGACY"]
    assert "baseline" in leg_reps
    assert "hdbscan" in leg_reps
    assert "concat_center_tfidf" in leg_reps


def _make_map_loader_stub():
    """Create a minimal MapLoader stub with only the class attrs needed for pattern queries."""
    stub = object.__new__(MapLoader)
    stub.DESIGN_PATTERNS = MapLoader.DESIGN_PATTERNS
    return stub


def test_get_representations_by_pattern_default():
    """get_representations_by_pattern returns correct list for DEFAULT."""
    stub = _make_map_loader_stub()
    reps = stub.get_representations_by_pattern("DEFAULT")
    assert "center_projected_64dim_hierarchical" in reps


def test_get_representations_by_pattern_high_purity():
    """get_representations_by_pattern returns sorted list for HIGH-PURITY."""
    stub = _make_map_loader_stub()
    reps = stub.get_representations_by_pattern("HIGH-PURITY")
    assert isinstance(reps, list)
    assert len(reps) >= 3
    assert reps == sorted(reps)


def test_get_representations_by_pattern_all_patterns():
    """Each design pattern yields at least one representation."""
    stub = _make_map_loader_stub()
    for pattern in {"DEFAULT", "HIGH-PURITY", "HIGH-ADVANTAGE", "CITATION-ROLE", "LEGACY"}:
        reps = stub.get_representations_by_pattern(pattern)
        assert len(reps) > 0, f"Pattern {pattern} has no representations"


# ---------------------------------------------------------------------------
# Representation purposes
# ---------------------------------------------------------------------------

def test_representation_purposes_covers_key_reps():
    """REPRESENTATION_PURPOSES maps key representations to valid purpose strings."""
    purposes = MapLoader.REPRESENTATION_PURPOSES
    assert purposes["center_projected_64dim_hierarchical"] == "production"
    assert purposes["linear_metric_best"] == "citation_independent"
    assert purposes["cited_outcome_hybrid_0.5"] == "cross_lingual"
    assert purposes["cited_outcome_hybrid_0.7"] == "fractal_quality"


# ---------------------------------------------------------------------------
# Holdout metrics in EvaluationLoader
# ---------------------------------------------------------------------------

def test_holdout_metrics_keys():
    """HOLDOUT_METRICS contains all expected representation keys."""
    keys = set(EvaluationLoader.HOLDOUT_METRICS.keys())
    assert "linear_metric_epoch4" in keys
    assert "mahalanobis_metric_epoch4" in keys
    assert "hybrid_stabilized_epoch1" in keys
    assert "cited_decisions_tfidf" in keys
    assert "cited_outcome_hybrid_0.5" in keys
    assert "cited_outcome_hybrid_0.7" in keys
    assert "center_projected_64dim_hierarchical" in keys
    assert "following_alpha0.3" in keys
    assert "criticizing_alpha0.3" in keys
    assert "citing_alpha0.3" in keys


def test_holdout_metrics_have_jp_scores():
    """Each holdout metric entry contains a jp_score (float or None)."""
    for name, metrics in EvaluationLoader.HOLDOUT_METRICS.items():
        assert "jp_score" in metrics, f"{name} missing jp_score"
        jp = metrics["jp_score"]
        if jp is not None:
            assert isinstance(jp, float), f"{name} jp_score not float: {type(jp)}"


def test_holdout_metrics_have_language_dominance():
    """Each holdout metric entry contains language_dominance."""
    for name, metrics in EvaluationLoader.HOLDOUT_METRICS.items():
        assert "language_dominance" in metrics, f"{name} missing language_dominance"


def test_holdout_metrics_have_design_pattern():
    """Each holdout metric entry includes its design_pattern."""
    for name, metrics in EvaluationLoader.HOLDOUT_METRICS.items():
        assert "design_pattern" in metrics, f"{name} missing design_pattern"
        assert metrics["design_pattern"] in {
            "DEFAULT", "HIGH-PURITY", "HIGH-ADVANTAGE", "CITATION-ROLE", "LEGACY"
        }


def test_holdout_linear_metric_best_jp():
    """linear_metric_epoch4 holdout JP is 0.6050."""
    m = EvaluationLoader.HOLDOUT_METRICS["linear_metric_epoch4"]
    assert m["jp_score"] == 0.6050
    assert m["language_dominance"] == 0.5795


def test_holdout_cited_outcome_hybrid_best():
    """cited_outcome_hybrid_0.5 has highest JP among holdout metrics."""
    jp = EvaluationLoader.HOLDOUT_METRICS["cited_outcome_hybrid_0.5"]["jp_score"]
    for name, metrics in EvaluationLoader.HOLDOUT_METRICS.items():
        if metrics["jp_score"] is not None and name != "cited_outcome_hybrid_0.5":
            assert jp >= metrics["jp_score"], (
                f"cited_outcome_hybrid_0.5 JP {jp} should be >= {name} JP {metrics['jp_score']}"
            )


def test_holdout_metrics_loader_returns_same():
    """EvaluationLoader.get_holdout_metrics() returns the class constant."""
    loader = EvaluationLoader(str(Path(__file__).parent.parent / "results" / "fractal_map"))
    result = loader.get_holdout_metrics()
    assert result is EvaluationLoader.HOLDOUT_METRICS


# ---------------------------------------------------------------------------
# Design patterns in EvaluationLoader
# ---------------------------------------------------------------------------

def test_eval_design_patterns_keys():
    """EvaluationLoader.DESIGN_PATTERNS contains all 5 pattern keys."""
    dp = EvaluationLoader.DESIGN_PATTERNS
    assert "DEFAULT" in dp
    assert "HIGH-PURITY" in dp
    assert "HIGH-ADVANTAGE" in dp
    assert "CITATION-ROLE" in dp
    # LEGACY is intentionally absent from EvaluationLoader.DESIGN_PATTERNS


def test_eval_design_patterns_default_has_representations():
    """DEFAULT pattern lists center_projected_64dim_hierarchical."""
    reps = EvaluationLoader.DESIGN_PATTERNS["DEFAULT"]["representations"]
    assert "center_projected_64dim_hierarchical" in reps


def test_eval_design_patterns_high_purity_strengths():
    """HIGH-PURITY pattern lists citation-independent retrieval as a strength."""
    strengths = EvaluationLoader.DESIGN_PATTERNS["HIGH-PURITY"]["strengths"]
    assert any("citation-independent" in s.lower() for s in strengths)


def test_eval_design_patterns_high_advantage_representations():
    """HIGH-ADVANTAGE lists the cited outcome hybrids."""
    reps = EvaluationLoader.DESIGN_PATTERNS["HIGH-ADVANTAGE"]["representations"]
    assert "cited_outcome_hybrid_0.5" in reps
    assert "cited_outcome_hybrid_0.7" in reps


def test_eval_design_patterns_loader_returns_same():
    """EvaluationLoader.get_design_patterns() returns the class constant."""
    loader = EvaluationLoader(str(Path(__file__).parent.parent / "results" / "fractal_map"))
    result = loader.get_design_patterns()
    assert result is EvaluationLoader.DESIGN_PATTERNS


# ---------------------------------------------------------------------------
# Representation recommendations
# ---------------------------------------------------------------------------

def test_recommendations_all_purposes():
    """EvaluationLoader.RECOMMENDATIONS covers all 5 purposes."""
    recs = EvaluationLoader.RECOMMENDATIONS
    for purpose in ("production", "citation_independent", "cross_lingual", "fractal_quality", "default"):
        assert purpose in recs, f"Missing purpose: {purpose}"


def test_recommendations_production_is_default():
    """Production and default purposes recommend the same representation."""
    prod = EvaluationLoader.RECOMMENDATIONS["production"]
    default = EvaluationLoader.RECOMMENDATIONS["default"]
    assert prod["representation"] == default["representation"]
    assert prod["pattern"] == default["pattern"]


def test_recommendations_have_required_fields():
    """Each recommendation has representation, pattern, and rationale."""
    for purpose, rec in EvaluationLoader.RECOMMENDATIONS.items():
        assert "representation" in rec, f"{purpose} missing representation"
        assert "pattern" in rec, f"{purpose} missing pattern"
        assert "rationale" in rec, f"{purpose} missing rationale"


def test_recommendations_citation_independent_uses_high_purity():
    """citation_independent recommendation uses a HIGH-PURITY representation."""
    rec = EvaluationLoader.RECOMMENDATIONS["citation_independent"]
    assert rec["pattern"] == "HIGH-PURITY"
    # The representation name may differ between DESIGN_PATTERNS and HOLDOUT_METRICS
    # (linear_metric_epoch4 vs linear_metric_best); verify the pattern is correct.
    rep = rec["representation"]
    assert rep in EvaluationLoader.HOLDOUT_METRICS or rep in MapLoader.DESIGN_PATTERNS


def test_recommendations_cross_lingual_uses_high_advantage():
    """cross_lingual recommendation uses a HIGH-ADVANTAGE representation."""
    rec = EvaluationLoader.RECOMMENDATIONS["cross_lingual"]
    assert rec["pattern"] == "HIGH-ADVANTAGE"
    rep = rec["representation"]
    assert MapLoader.DESIGN_PATTERNS.get(rep) == "HIGH-ADVANTAGE"


def test_recommendations_fractal_quality_uses_high_advantage():
    """fractal_quality recommendation uses a HIGH-ADVANTAGE representation."""
    rec = EvaluationLoader.RECOMMENDATIONS["fractal_quality"]
    assert rec["pattern"] == "HIGH-ADVANTAGE"
    rep = rec["representation"]
    assert MapLoader.DESIGN_PATTERNS.get(rep) == "HIGH-ADVANTAGE"


def test_get_representation_recommendation_valid():
    """get_representation_recommendation returns valid recommendation for each purpose."""
    loader = EvaluationLoader(str(Path(__file__).parent.parent / "results" / "fractal_map"))
    for purpose in ("production", "citation_independent", "cross_lingual", "fractal_quality", "default"):
        rec = loader.get_representation_recommendation(purpose)
        assert "representation" in rec, f"Missing representation for {purpose}"
        assert "pattern" in rec, f"Missing pattern for {purpose}"


def test_get_representation_recommendation_invalid_purpose():
    """get_representation_recommendation returns error for unknown purpose."""
    loader = EvaluationLoader(str(Path(__file__).parent.parent / "results" / "fractal_map"))
    rec = loader.get_representation_recommendation("nonexistent_purpose")
    assert "error" in rec


# ---------------------------------------------------------------------------
# Navigation API new endpoints
# ---------------------------------------------------------------------------

def _init_nav():
    """Initialize NavigationAPI with test paths."""
    base = Path(__file__).parent.parent
    corpus_dir = str(base / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    return api


def test_nav_get_design_patterns():
    """NavigationAPI.get_design_patterns returns all 5 patterns with representations."""
    api = _init_nav()
    patterns = api.get_design_patterns()
    assert isinstance(patterns, dict)
    for name in ("DEFAULT", "HIGH-PURITY", "HIGH-ADVANTAGE", "CITATION-ROLE", "LEGACY"):
        assert name in patterns, f"Missing pattern: {name}"
        assert "representations" in patterns[name], f"{name} missing representations"
        assert "description" in patterns[name], f"{name} missing description"
        assert len(patterns[name]["representations"]) > 0, f"{name} has no representations"


def test_nav_get_design_patterns_default_has_correct_rep():
    """NavigationAPI design patterns DEFAULT contains center_projected_64dim_hierarchical."""
    api = _init_nav()
    patterns = api.get_design_patterns()
    default_reps = patterns["DEFAULT"]["representations"]
    assert "center_projected_64dim_hierarchical" in default_reps


def test_nav_get_holdout_metrics():
    """NavigationAPI.get_holdout_metrics returns holdout metrics dict."""
    api = _init_nav()
    metrics = api.get_holdout_metrics()
    assert isinstance(metrics, dict)
    assert "linear_metric_epoch4" in metrics
    assert "jp_score" in metrics["linear_metric_epoch4"]
    assert "language_dominance" in metrics["linear_metric_epoch4"]


def test_nav_get_holdout_metrics_all_entries():
    """NavigationAPI holdout metrics includes all expected representations."""
    api = _init_nav()
    metrics = api.get_holdout_metrics()
    expected_keys = {
        "linear_metric_epoch4", "mahalanobis_metric_epoch4", "hybrid_stabilized_epoch1",
        "cited_decisions_tfidf", "cited_outcome_hybrid_0.5", "cited_outcome_hybrid_0.7",
        "center_projected_64dim_hierarchical", "following_alpha0.3", "criticizing_alpha0.3",
        "citing_alpha0.3",
    }
    assert expected_keys == set(metrics.keys())


def test_nav_get_representation_recommendation_production():
    """NavigationAPI recommendation for production returns DEFAULT pattern."""
    api = _init_nav()
    rec = api.get_representation_recommendation("production")
    assert rec["pattern"] == "DEFAULT"
    assert rec["representation"] == "center_projected_64dim_hierarchical"


def test_nav_get_representation_recommendation_cross_lingual():
    """NavigationAPI recommendation for cross_lingual returns HIGH-ADVANTAGE."""
    api = _init_nav()
    rec = api.get_representation_recommendation("cross_lingual")
    assert rec["pattern"] == "HIGH-ADVANTAGE"


def test_nav_get_representation_recommendation_default():
    """NavigationAPI recommendation for default returns DEFAULT pattern."""
    api = _init_nav()
    rec = api.get_representation_recommendation("default")
    assert rec["pattern"] == "DEFAULT"
    assert rec["representation"] == "center_projected_64dim_hierarchical"


def test_nav_get_representation_recommendation_invalid():
    """NavigationAPI recommendation for invalid purpose returns error."""
    api = _init_nav()
    rec = api.get_representation_recommendation("bogus")
    assert "error" in rec


# ---------------------------------------------------------------------------
# Representation metadata (design_pattern, purpose, evidence_tier)
# ---------------------------------------------------------------------------

def test_map_loader_metadata_has_design_pattern():
    """MapLoader.DESIGN_PATTERNS assigns a pattern to every representation."""
    for rep_name, pattern in MapLoader.DESIGN_PATTERNS.items():
        assert pattern in {"DEFAULT", "HIGH-PURITY", "HIGH-ADVANTAGE", "CITATION-ROLE", "LEGACY"}, (
            f"{rep_name} has unexpected pattern: {pattern}"
        )


def test_map_loader_metadata_has_purpose():
    """MapLoader.REPRESENTATION_PURPOSES assigns a purpose to key representations."""
    for rep_name, purpose in MapLoader.REPRESENTATION_PURPOSES.items():
        assert isinstance(purpose, str) and len(purpose) > 0, (
            f"{rep_name} has empty purpose"
        )


def test_eval_loader_recommendations_metadata_consistent():
    """Recommendation patterns match DESIGN_PATTERNS classification."""
    for purpose, rec in EvaluationLoader.RECOMMENDATIONS.items():
        rep = rec["representation"]
        pattern = rec["pattern"]
        actual_pattern = MapLoader.DESIGN_PATTERNS.get(rep)
        if actual_pattern is not None:
            assert actual_pattern == pattern, (
                f"{purpose}: recommendation pattern {pattern} != DESIGN_PATTERNS {actual_pattern} for {rep}"
            )


def test_holdout_metrics_pattern_matches_design_patterns():
    """Holdout metric design_pattern entries match MapLoader.DESIGN_PATTERNS."""
    for rep_name, metrics in EvaluationLoader.HOLDOUT_METRICS.items():
        hp_pattern = metrics.get("design_pattern")
        if hp_pattern:
            actual = MapLoader.DESIGN_PATTERNS.get(rep_name)
            # Some holdout entries reference patterns not directly in DESIGN_PATTERNS (e.g. names differ)
            if actual is not None:
                assert actual == hp_pattern, (
                    f"{rep_name}: holdout pattern {hp_pattern} != DESIGN_PATTERNS {actual}"
                )
