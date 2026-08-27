"""
LexMachina Product Smoke Tests
Verifies end-to-end navigation utility.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.corpus_loader import CorpusLoader
from app.map_loader import MapLoader
from app.navigation import NavigationAPI


def test_corpus_loader():
    """Test corpus loading and basic operations."""
    print("=== Test: Corpus Loader ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    loader = CorpusLoader(str(corpus_dir))
    count = loader.load()
    
    assert count > 0, f"Expected >0 decisions, got {count}"
    print(f"  Loaded {count} decisions")
    
    # Check languages
    langs = loader.languages
    print(f"  Languages: {langs}")
    assert "de" in langs, "Expected German decisions"
    
    # Check branches
    branches = loader.branches
    print(f"  Branches: {branches}")
    
    # Get a decision
    ids = loader.get_all_ids()
    assert len(ids) > 0, "Expected at least one decision ID"
    
    first_id = ids[0]
    decision = loader.get(first_id)
    assert decision is not None, f"Decision {first_id} not found"
    print(f"  First decision: {first_id} ({decision.language}, {decision.branch})")
    
    # Test summary
    summary = loader.get_summary(first_id)
    assert "decision_id" in summary, "Summary missing decision_id"
    assert "language" in summary, "Summary missing language"
    
    # Test search
    results = loader.search("Recht", limit=5)
    print(f"  Search 'Recht': {len(results)} results")
    
    print("  PASS\n")
    return True


def test_map_loader():
    """Test map artifact loading."""
    print("=== Test: Map Loader ===")
    
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    loader = MapLoader(str(results_dir))
    count = loader.load()
    
    assert count > 0, f"Expected >0 maps, got {count}"
    print(f"  Loaded {count} maps")
    
    # Check available representations
    reps = loader.get_available_representations()
    print(f"  Representations: {reps}")
    assert "concat_center_tfidf" in reps, "Expected concat_center_tfidf"
    
    # Check zoom levels
    for rep in reps:
        levels = loader.get_zoom_levels(rep)
        print(f"  {rep} zoom levels: {levels}")
        assert len(levels) > 0, f"No zoom levels for {rep}"
    
    # Check stats
    stats = loader.get_stats("concat_center_tfidf")
    print(f"  concat_center_tfidf stats: {stats['n_decisions']} decisions, {stats['n_zoom_levels']} zoom levels")
    
    # Check positions
    positions = loader.get_positions("concat_center_tfidf")
    print(f"  Positions: {len(positions)} decisions with 2D coordinates")
    assert len(positions) > 0, "No positions found"
    
    print("  PASS\n")
    return True


def test_navigation_api():
    """Test the navigation API end-to-end."""
    print("=== Test: Navigation API ===")
    
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    
    api = NavigationAPI(corpus_dir, results_dir)
    status = api.initialize()
    
    assert status["status"] == "ready", f"API not ready: {status}"
    print(f"  Initialized: {status['corpus_decisions']} decisions, {status['maps_loaded']} maps")
    
    # Test overview
    overview = api.get_overview()
    assert "total_decisions" in overview, "Overview missing total_decisions"
    print(f"  Overview: {overview['total_decisions']} decisions")
    
    # Test map data
    map_data = api.get_map_data("concat_center_tfidf", 1)
    assert "positions" in map_data, "Map data missing positions"
    assert "clusters" in map_data, "Map data missing clusters"
    print(f"  Map data: {len(map_data['positions'])} positions, {len(map_data['clusters'])} clusters")
    
    # Test cluster detail
    if map_data["clusters"]:
        cid = map_data["clusters"][0]["cluster_id"]
        detail = api.get_cluster_detail("concat_center_tfidf", 1, cid)
        assert "decisions" in detail, "Cluster detail missing decisions"
        print(f"  Cluster {cid}: {detail['size']} decisions")
    
    # Test decision detail
    if map_data["positions"]:
        did = map_data["positions"][0]["decision_id"]
        decision = api.get_decision(did)
        assert "decision_id" in decision, "Decision missing decision_id"
        print(f"  Decision: {did}")
    
    # Test neighbors
    if map_data["positions"]:
        did = map_data["positions"][0]["decision_id"]
        neighbors = api.get_neighbors(did, "concat_center_tfidf", 2, 5)
        print(f"  Neighbors of {did}: {len(neighbors)} found")
    
    # Test search
    results = api.search_decisions("Beschwerde", limit=5)
    print(f"  Search: {len(results)} results")
    
    # Test zoom levels
    levels = api.get_zoom_levels("concat_center_tfidf")
    print(f"  Zoom levels: {levels}")
    
    print("  PASS\n")
    return True


def test_end_to_end():
    """Test complete end-to-end navigation flow."""
    print("=== Test: End-to-End Navigation ===")
    
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    
    # Flow: Overview → Map → Cluster → Decision → Neighbors
    overview = api.get_overview()
    print(f"  1. Overview: {overview['total_decisions']} decisions")
    
    # Get map at each zoom level
    for zoom in [0, 1, 2]:
        map_data = api.get_map_data("concat_center_tfidf", zoom)
        n_clusters = len(map_data.get("clusters", []))
        n_positions = len(map_data.get("positions", []))
        print(f"  2. Zoom {zoom}: {n_clusters} clusters, {n_positions} positions")
        
        # Pick a cluster and inspect it
        if map_data.get("clusters"):
            cluster = map_data["clusters"][0]
            detail = api.get_cluster_detail("concat_center_tfidf", zoom, cluster["cluster_id"])
            if detail.get("decisions"):
                did = detail["decisions"][0]["decision_id"]
                decision = api.get_decision(did)
                print(f"  3. Decision: {did} ({decision.get('language', '?')})")
                
                # Get neighbors
                neighbors = api.get_neighbors(did, "concat_center_tfidf", zoom, 5)
                print(f"  4. Neighbors: {len(neighbors)}")
    
    print("  PASS\n")
    return True


if __name__ == "__main__":
    results = []
    results.append(("Corpus Loader", test_corpus_loader()))
    results.append(("Map Loader", test_map_loader()))
    results.append(("Navigation API", test_navigation_api()))
    results.append(("End-to-End", test_end_to_end()))
    
    print("=" * 50)
    print("RESULTS:")
    for name, passed in results:
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    
    all_passed = all(p for _, p in results)
    print(f"\nOverall: {'ALL PASS' if all_passed else 'SOME FAILED'}")
    sys.exit(0 if all_passed else 1)
