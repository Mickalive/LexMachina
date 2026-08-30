"""
LexMachina Product Tests — Cycle 33304668621
Tests for:
1. Multi-representation user import (positions computed for ALL representations)
2. Representation validation endpoint
3. Map data pagination (limit/offset)
4. Server-level proximity caching fix verification
"""
import sys
import json
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.corpus_loader import CorpusLoader
from app.map_loader import MapLoader
from app.navigation import NavigationAPI


def _get_api():
    """Create and initialize a fresh NavigationAPI instance."""
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    return api


def test_multi_representation_import():
    """Test that user import computes positions for ALL available representations.
    
    Previously, import only computed positions for the default representation.
    After the fix, positions are computed for every representation so imported
    decisions appear on the map regardless of which representation is active.
    
    FIX (cycle 33319873420): Clean BOTH user_imports directories BEFORE creating
    the API to avoid stale in-memory corpus and stale persisted import positions
    from prior test runs.
    """
    print("=== Test: Multi-Representation User Import ===")
    
    # Determine paths from base_dir (before API init)
    base_dir = Path(__file__).parent.parent
    
    # Clean corpus user_imports (loaded by CorpusLoader)
    corpus_import_dir = base_dir / "results" / "corpus" / "normalization" / "user_imports"
    if corpus_import_dir.exists():
        shutil.rmtree(corpus_import_dir)
    
    # Clean fractal_map user_imports (persisted by NavigationAPI._save_imported_position)
    nav_import_dir = base_dir / "results" / "fractal_map" / "user_imports"
    if nav_import_dir.exists():
        shutil.rmtree(nav_import_dir)
    
    api = _get_api()
    
    initial_count = api.corpus.size
    initial_imports = api.corpus.user_import_count
    print(f"  Initial: {initial_count} decisions, {initial_imports} user imports")
    
    # Import test records
    test_records = [
        {
            "decision_id": "test_multi_rep_001",
            "court": "bger",
            "docket_number": "TEST-MULTI-REP-001",
            "decision_date": "2024-03-15",
            "language": "de",
            "full_text": "Testentscheid fuer Multi-Repraesentation Import im Strfrecht.",
            "branch": "strafrecht",
            "legal_area": "Strafrecht",
            "provenance": {"source": "test_cycle_33304668621"},
        },
        {
            "decision_id": "test_multi_rep_002",
            "court": "bger",
            "docket_number": "TEST-MULTI-REP-002",
            "decision_date": "2024-04-20",
            "language": "fr",
            "full_text": "Arret de test pour import multi-representation en droit civil.",
            "branch": "zivilrecht",
            "legal_area": "Zivilrecht",
            "provenance": {"source": "test_cycle_33304668621"},
        },
    ]
    
    result = api.import_corpus(test_records)
    print(f"  Imported: {result['imported']}, Skipped: {result['skipped']}")
    assert result["imported"] == 2, f"Expected 2 imported, got {result['imported']}"
    
    # Verify multi-representation positioning
    assert "representations_positioned" in result, "Result missing representations_positioned"
    reps_pos = result["representations_positioned"]
    print(f"  Representations positioned: {len(reps_pos)}")
    assert len(reps_pos) > 1, f"Expected positions in multiple representations, got {len(reps_pos)}"
    
    total_positions = result.get("map_positions_computed", 0)
    print(f"  Total positions computed: {total_positions}")
    assert total_positions >= 2, f"Expected at least 2 positions, got {total_positions}"
    
    # Verify that positions exist for the default representation
    default_rep = result.get("default_representation")
    default_in_list = any(r["representation"] == default_rep for r in reps_pos)
    assert default_in_list, f"Default representation {default_rep} not in positioned list"
    
    # Print details
    for r in reps_pos:
        print(f"    {r['representation']}: {r['positions_computed']} positions at zoom {r['zoom_level']}")
    
    # Verify imported positions are visible in map data for multiple representations
    for rep_info in reps_pos[:3]:  # Check first 3 representations
        rep = rep_info["representation"]
        zl = rep_info["zoom_level"]
        map_data = api.get_map_data(rep, zl)
        imported_on_map = [p for p in map_data["positions"] if p.get("is_imported")]
        print(f"  {rep} zoom {zl}: {len(imported_on_map)} imported positions visible on map")
        assert len(imported_on_map) >= 1, f"Expected at least 1 imported position on map for {rep}"
    
    # Verify duplicate import still skips
    result2 = api.import_corpus(test_records)
    assert result2["imported"] == 0, f"Duplicates should be skipped, got {result2['imported']}"
    print(f"  Duplicate skip: {result2['skipped']} skipped")
    
    # Clean up
    if corpus_import_dir.exists():
        shutil.rmtree(corpus_import_dir)
    if nav_import_dir.exists():
        shutil.rmtree(nav_import_dir)
    
    print("  PASS\n")
    return True


def test_validate_representations():
    """Test the representation validation endpoint.
    
    Validates all loaded representations and reports their status,
    including zoom-level health checks and metadata verification.
    """
    print("=== Test: Representation Validation ===")
    
    api = _get_api()
    
    # Run validation
    report = api.validate_representations()
    
    assert "total_representations" in report, "Report missing total_representations"
    assert "passing" in report, "Report missing passing count"
    assert "representations" in report, "Report missing representations dict"
    
    total = report["total_representations"]
    passing = report["passing"]
    warnings = report["warnings"]
    failing = report["failing"]
    print(f"  Total: {total}, Passing: {passing}, Warnings: {warnings}, Failing: {failing}")
    
    assert total > 0, "Expected at least one representation"
    assert passing > 0, "Expected at least one passing representation"
    
    # Verify each representation has the expected structure
    for rep_name, rep_data in report["representations"].items():
        assert "status" in rep_data, f"{rep_name} missing status"
        assert "zoom_levels" in rep_data, f"{rep_name} missing zoom_levels"
        assert "issues" in rep_data, f"{rep_name} missing issues"
        assert "metadata" in rep_data, f"{rep_name} missing metadata"
        assert rep_data["status"] in ("PASS", "WARN", "FAIL"), f"{rep_name} invalid status: {rep_data['status']}"
        
        # Check metadata has required fields
        meta = rep_data["metadata"]
        assert "evidence_tier" in meta, f"{rep_name} metadata missing evidence_tier"
        assert "n_decisions" in meta, f"{rep_name} metadata missing n_decisions"
        assert meta["n_decisions"] > 0, f"{rep_name} has 0 decisions"
        
        # Verify zoom levels have expected info
        for zl, zl_info in rep_data["zoom_levels"].items():
            assert "n_clusters" in zl_info, f"{rep_name} zoom {zl} missing n_clusters"
            assert "n_positions" in zl_info, f"{rep_name} zoom {zl} missing n_positions"
        
        status_icon = "✓" if rep_data["status"] == "PASS" else ("⚠" if rep_data["status"] == "WARN" else "✗")
        n_zl = len(rep_data["zoom_levels"])
        n_issues = len(rep_data["issues"])
        evidence = rep_data["metadata"]["evidence_tier"]
        print(f"  {status_icon} {rep_name}: {evidence}, {n_zl} zoom levels, {n_issues} issues")
        
        if rep_data["issues"]:
            for issue in rep_data["issues"]:
                print(f"    Issue: {issue}")
    
    # Verify the default representation passes
    default_rep = api._get_default_representation()
    default_data = report["representations"].get(default_rep)
    assert default_data is not None, f"Default representation {default_rep} not in validation report"
    assert default_data["status"] in ("PASS", "WARN"), f"Default representation failed: {default_data['status']}"
    print(f"  Default ({default_rep}): {default_data['status']}")
    
    print("  PASS\n")
    return True


def test_map_pagination():
    """Test map data pagination with limit/offset.
    
    For large-scale rendering (192k corpus), the API must support
    pagination to avoid returning all positions at once.
    """
    print("=== Test: Map Data Pagination ===")
    
    api = _get_api()
    
    # Get full map data (no pagination)
    full_data = api.get_map_data("center_projected_64dim_hierarchical", 0)
    total_positions = len(full_data["positions"])
    print(f"  Full map: {total_positions} positions")
    assert total_positions > 0, "Expected positions"
    assert full_data.get("pagination") is None, "Full request should have no pagination info"
    
    # Get paginated data: first 100 positions
    page1 = api.get_map_data("center_projected_64dim_hierarchical", 0, limit=100)
    assert len(page1["positions"]) == 100, f"Expected 100 positions, got {len(page1['positions'])}"
    assert page1["pagination"] is not None, "Paginated request should have pagination info"
    assert page1["pagination"]["total"] == total_positions, "Pagination total should match full count"
    assert page1["pagination"]["offset"] == 0
    assert page1["pagination"]["limit"] == 100
    assert page1["pagination"]["returned"] == 100
    assert page1["pagination"]["has_more"] == True, "Should have more data"
    print(f"  Page 1: {len(page1['positions'])} positions, has_more={page1['pagination']['has_more']}")
    
    # Get second page
    page2 = api.get_map_data("center_projected_64dim_hierarchical", 0, limit=100, offset=100)
    assert len(page2["positions"]) == 100, f"Expected 100 positions, got {len(page2['positions'])}"
    assert page2["pagination"]["offset"] == 100
    print(f"  Page 2: {len(page2['positions'])} positions")
    
    # Ensure pages don't overlap
    page1_ids = {p["decision_id"] for p in page1["positions"]}
    page2_ids = {p["decision_id"] for p in page2["positions"]}
    overlap = page1_ids & page2_ids
    assert len(overlap) == 0, f"Pages overlap: {len(overlap)} shared decisions"
    print(f"  No overlap between pages: ✓")
    
    # Get last page (may have fewer items)
    last_offset = total_positions - 50
    last_page = api.get_map_data("center_projected_64dim_hierarchical", 0, limit=100, offset=last_offset)
    expected_last = total_positions - last_offset
    assert len(last_page["positions"]) == expected_last, f"Expected {expected_last} positions on last page"
    assert last_page["pagination"]["has_more"] == False, "Last page should not have more data"
    print(f"  Last page: {len(last_page['positions'])} positions, has_more={last_page['pagination']['has_more']}")
    
    # Verify clusters are always returned in full (no pagination on clusters)
    assert len(page1["clusters"]) == len(full_data["clusters"]), "Clusters should not be paginated"
    print(f"  Clusters: {len(page1['clusters'])} (consistent across pages) ✓")
    
    # Verify offset beyond total returns empty
    empty_page = api.get_map_data("center_projected_64dim_hierarchical", 0, limit=100, offset=9999)
    assert len(empty_page["positions"]) == 0, "Offset beyond total should return empty"
    assert empty_page["pagination"]["has_more"] == False
    print(f"  Empty page: {len(empty_page['positions'])} positions ✓")
    
    print("  PASS\n")
    return True


def test_proximity_caching():
    """Verify the proximity explanation endpoint returns consistent results.
    
    The caching fix in server.py ensures that repeated calls to
    /api/proximity return the same data. This test verifies the
    navigation-level caching works correctly.
    """
    print("=== Test: Proximity Caching ===")
    
    api = _get_api()
    
    # Find two decisions that exist
    ids = api.corpus.get_all_ids()
    assert len(ids) >= 2, "Need at least 2 decisions"
    id_a, id_b = ids[0], ids[1]
    
    # First call
    result1 = api.get_proximity_explanation(id_a, id_b)
    assert "proximity_score" in result1, "Result missing proximity_score"
    assert "feature_contributions" in result1, "Result missing feature_contributions"
    assert result1.get("cached", False) == False, "First call should not be cached"
    print(f"  First call: proximity_score={result1['proximity_score']}, cached=False")
    
    # Second call (should hit cache)
    result2 = api.get_proximity_explanation(id_a, id_b)
    assert result2.get("cached", False) == True, "Second call should be cached"
    assert result2["proximity_score"] == result1["proximity_score"], "Cached result should match"
    print(f"  Second call: proximity_score={result2['proximity_score']}, cached=True")
    
    # Reverse order should also hit cache (order-independent)
    result3 = api.get_proximity_explanation(id_b, id_a)
    assert result3.get("cached", False) == True, "Reverse call should also be cached"
    print(f"  Reverse call: cached={result3.get('cached', False)} ✓")
    
    print("  PASS\n")
    return True


if __name__ == "__main__":
    tests = [
        test_multi_representation_import,
        test_validate_representations,
        test_map_pagination,
        test_proximity_caching,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  FAIL: {test.__name__}\n")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test.__name__}: {e}\n")
    
    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    sys.exit(1 if failed > 0 else 0)
