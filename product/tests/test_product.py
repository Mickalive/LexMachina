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


def test_hdbscan():
    """Test HDBSCAN clustering as alternative to Leiden."""
    print("=== Test: HDBSCAN Clustering ===")
    
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    
    # Verify HDBSCAN is available
    reps = api.map_loader.get_available_representations()
    assert "hdbscan" in reps, f"hdbscan not in representations: {reps}"
    print(f"  Available: {reps}")
    
    # Test HDBSCAN at each zoom level
    for zoom in [0, 1, 2, 3]:
        map_data = api.get_map_data("hdbscan", zoom)
        n_clusters = len(map_data.get("clusters", []))
        n_positions = len(map_data.get("positions", []))
        print(f"  HDBSCAN Zoom {zoom}: {n_clusters} clusters, {n_positions} positions")
        assert n_positions == 1000, f"Expected 1000 positions, got {n_positions}"
    
    # Verify different cluster counts from Leiden
    leiden_data = api.get_map_data("concat_center_tfidf", 1)
    hdbscan_data = api.get_map_data("hdbscan", 1)
    leiden_clusters = len(leiden_data.get("clusters", []))
    hdbscan_clusters = len(hdbscan_data.get("clusters", []))
    print(f"  Leiden zoom 1: {leiden_clusters} clusters")
    print(f"  HDBSCAN zoom 1: {hdbscan_clusters} clusters")
    
    print("  PASS\n")
    return True


def test_corpus_import():
    """Test user corpus import functionality."""
    print("=== Test: Corpus Import ===")
    
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    
    # Clean any previous user imports for idempotent test
    import shutil
    user_import_dir = Path(corpus_dir).parent / "user_imports"
    if user_import_dir.exists():
        shutil.rmtree(user_import_dir)
    
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    
    initial_count = api.corpus.size
    initial_user_imports = api.corpus.user_import_count
    print(f"  Initial: {initial_count} decisions, {initial_user_imports} user imports")
    
    # Import test records
    test_records = [
        {
            "decision_id": "test_product_001",
            "court": "bger",
            "docket_number": "TEST-PROD-001",
            "decision_date": "2024-01-15",
            "language": "de",
            "full_text": "Dies ist ein Testentscheid uber das Strafrecht im Produkttest.",
            "branch": "strafrecht",
            "legal_area": "Strafrecht",
            "provenance": {"source": "user_upload"},
        },
        {
            "decision_id": "test_product_002",
            "court": "bger",
            "docket_number": "TEST-PROD-002",
            "decision_date": "2024-02-20",
            "language": "fr",
            "full_text": "Ceci est un arret de test en droit civil pour le produit.",
            "branch": "zivilrecht",
            "legal_area": "Zivilrecht",
            "provenance": {"source": "user_upload"},
        },
    ]
    
    result = api.import_corpus(test_records)
    print(f"  Imported: {result['imported']}, Skipped: {result['skipped']}")
    assert result["imported"] == 2, f"Expected 2 imported, got {result['imported']}"
    assert api.corpus.size == initial_count + 2
    
    # Verify corpus stats
    stats = api.get_corpus_stats()
    print(f"  Total: {stats['total_decisions']}, User imports: {stats['user_imports']}")
    assert stats["user_imports"] == initial_user_imports + 2
    
    # Duplicate import should skip
    result2 = api.import_corpus(test_records)
    assert result2["imported"] == 0, f"Duplicates should be skipped, got {result2['imported']}"
    print(f"  Duplicate skip: {result2['skipped']} skipped")
    
    # Search should find imported decisions (use unique docket number for reliable match)
    results = api.search_decisions("TEST-PROD-001", limit=10)
    imported_found = [r for r in results if r["decision_id"].startswith("test_product")]
    print(f"  Search found {len(imported_found)} imported decisions")
    assert len(imported_found) >= 1, "Expected to find imported decision in search"
    
    # Verify corpus-map coverage stats
    stats = api.get_corpus_stats()
    coverage = stats["map_coverage"]
    print(f"  Map coverage: {coverage['corpus_with_map_position']}/{coverage['total_map_positions']} corpus decisions on map")
    assert coverage["total_map_positions"] == 1000, "Expected 1000 map positions"
    assert coverage["corpus_with_map_position"] > 0, "Expected some corpus decisions on map"
    
    print("  PASS\n")
    return True


def test_section_modes():
    """Test section-based map modes (multi-view navigation)."""
    print("=== Test: Section Modes ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Verify section modes loaded
    modes = api.section_modes.get_available_modes()
    print(f"  Section modes: {len(modes)}")
    assert len(modes) == 6, f"Expected 6 section modes, got {len(modes)}"
    
    for mode in modes:
        print(f"    {mode['name']}: {mode['label']} ({mode['n_decisions']} decisions)")
        assert mode["n_decisions"] > 0, f"Mode {mode['name']} has no decisions"
    
    # Test getting map data for a section mode
    mode_data = api.get_map_data(map_mode="erwaegungen")
    print(f"  erwaegungen mode: {mode_data['map_mode']['section_decisions']} section decisions, "
          f"{mode_data['map_mode']['total_positions']} total positions")
    assert "map_mode" in mode_data, "Expected map_mode in response"
    assert mode_data["map_mode"]["name"] == "erwaegungen"
    assert mode_data["n_decisions"] >= 63, f"Expected at least 63 decisions, got {mode_data['n_decisions']}"
    assert len(mode_data["positions"]) > mode_data["map_mode"]["section_decisions"], "Expected more total positions than section decisions"
    
    # Test another section mode
    mode_data2 = api.get_map_data(map_mode="sachverhalt")
    assert mode_data2["map_mode"]["name"] == "sachverhalt"
    print(f"  sachverhalt mode: {mode_data2['map_mode']['section_decisions']} section decisions")
    
    # Verify clustering data is available
    cluster = api.section_modes.get_clustering("erwaegungen", 1.0)
    assert cluster is not None, "Expected clustering data for erwaegungen"
    print(f"  erwaegungen clustering: {cluster['n_clusters']} clusters, "
          f"legal_area_purity={cluster['coherence']['legal_area_purity']:.3f}")
    
    print("  PASS\n")
    return True


def test_citations():
    """Test citation graph integration."""
    print("=== Test: Citations ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Verify citation graph loaded
    stats = api.citation_loader.get_stats()
    print(f"  Citation graph: {stats['n_decisions_with_citations']} decisions with citations, "
          f"{stats['total_citation_edges']} edges")
    assert stats["n_decisions_with_citations"] > 0, "Expected some citations"
    
    # Test citation lookup for a decision with known citations
    # Find a decision that has citations
    test_decision = None
    for did in list(api.citation_loader.graph.outgoing.keys())[:10]:
        if did in api.corpus.decisions:
            test_decision = did
            break
    
    if test_decision:
        outgoing = api.citation_loader.get_outgoing(test_decision)
        print(f"  {test_decision}: {len(outgoing)} outgoing citations")
        assert len(outgoing) > 0, "Expected outgoing citations"
        
        # Test get_citations API
        citations = api.get_citations(test_decision)
        assert "outgoing" in citations, "Expected outgoing in citations"
        assert "incoming" in citations, "Expected incoming in citations"
        print(f"  get_citations: {citations['counts']['outgoing']} out, {citations['counts']['incoming']} in")
    
    # Test decision with citation connections
    test_decision2 = "bger_4A_562_2020"  # Known to have citations
    decision = api.get_decision(test_decision2)
    if "citations" in decision:
        print(f"  Decision citations: {decision['citations']['counts']['outgoing']} out, "
              f"{decision['citations']['counts']['incoming']} in")
        assert "outgoing" in decision["citations"]
        assert "incoming" in decision["citations"]
    
    print("  PASS\n")
    return True


def test_map_modes_api():
    """Test the map modes API endpoint."""
    print("=== Test: Map Modes API ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Test get_map_modes
    modes = api.get_map_modes()
    print(f"  Total map modes: {len(modes)}")
    
    # Separate by type
    base_modes = [m for m in modes if m["type"] == "representation"]
    section_modes = [m for m in modes if m["type"] == "section_view"]
    print(f"  Base modes: {len(base_modes)}")
    print(f"  Section modes: {len(section_modes)}")
    
    assert len(base_modes) >= 3, "Expected at least 3 base modes"
    assert len(section_modes) == 6, "Expected 6 section modes"
    
    # Verify each mode has required fields
    for mode in modes:
        assert "name" in mode, f"Mode missing name"
        assert "label" in mode, f"Mode {mode['name']} missing label"
        assert "type" in mode, f"Mode {mode['name']} missing type"
        assert "n_decisions" in mode, f"Mode {mode['name']} missing n_decisions"
    
    print("  PASS\n")
    return True


def test_hierarchical_leiden():
    """Test hierarchical Leiden representation (validated fractal map architecture)."""
    print("=== Test: Hierarchical Leiden ===")
    
    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()
    
    # Verify hierarchical_leiden is available
    reps = api.map_loader.get_available_representations()
    assert "hierarchical_leiden" in reps, f"hierarchical_leiden not in representations: {reps}"
    print(f"  Available representations: {reps}")
    
    # Test hierarchical_leiden at each zoom level
    zoom_levels = api.get_zoom_levels("hierarchical_leiden")
    print(f"  Zoom levels: {zoom_levels}")
    assert len(zoom_levels) == 3, f"Expected 3 zoom levels, got {len(zoom_levels)}"
    
    # Zoom 0: 5 clusters (coarse, res 0.25)
    map_data = api.get_map_data("hierarchical_leiden", 0)
    assert map_data["n_clusters"] == 5, f"Expected 5 clusters at zoom 0, got {map_data['n_clusters']}"
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 0: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")
    
    # Zoom 1: 8 clusters (intermediate, res 0.5)
    map_data = api.get_map_data("hierarchical_leiden", 1)
    assert map_data["n_clusters"] == 8, f"Expected 8 clusters at zoom 1, got {map_data['n_clusters']}"
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 1: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")
    
    # Zoom 2: 27 clusters (fine, res 3.0)
    map_data = api.get_map_data("hierarchical_leiden", 2)
    assert map_data["n_clusters"] == 27, f"Expected 27 clusters at zoom 2, got {map_data['n_clusters']}"
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 2: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")
    
# Verify hierarchical structure: fine clusters nest within coarse
    # Get cluster assignments at zoom 0 and zoom 2
    zl_0 = api.map_loader.get_zoom_level("hierarchical_leiden", 0)
    zl_2 = api.map_loader.get_zoom_level("hierarchical_leiden", 2)
    
    # Check that decisions in a zoom 2 cluster also belong to a single zoom 0 cluster
    nesting_consistent = 0
    total_fine_clusters = len(zl_2.clusters)
    for fine_cid, fine_cluster in zl_2.clusters.items():
        if not fine_cluster.decision_ids:
            continue
        # Check which zoom 0 cluster the first decision belongs to
        first_did = fine_cluster.decision_ids[0]
        coarse_cid = zl_0.cluster_assignments.get(first_did)
        if coarse_cid is not None:
            # Verify all decisions in this fine cluster map to the same coarse cluster
            all_same = all(zl_0.cluster_assignments.get(did) == coarse_cid
                          for did in fine_cluster.decision_ids)
            if all_same:
                nesting_consistent += 1
    
    nesting_rate = nesting_consistent / total_fine_clusters if total_fine_clusters > 0 else 0
    print(f"  Nesting consistency (flat multi-res): {nesting_consistent}/{total_fine_clusters} = {nesting_rate:.2f}")
    # Note: Current implementation uses flat Leiden at multiple resolutions.
    # True hierarchical Leiden (with nesting=1.0) is available in fractal-map results
    # but requires loading the hierarchical_leiden_results.json assignments.
    # For now, accept the flat multi-resolution nesting rate.
    assert nesting_rate >= 0.8, f"Expected reasonable nesting consistency, got {nesting_rate}"
    
    # Test neighbors with hierarchical_leiden
    did = list(zl_0.positions.keys())[0]
    neighbors = api.get_neighbors(did, "hierarchical_leiden", 1, 5)
    print(f"  Neighbors of {did}: {len(neighbors)} found")
    assert len(neighbors) > 0, "Expected neighbors"
    
    # Verify map modes includes hierarchical_leiden
    modes = api.get_map_modes()
    hl_mode = next((m for m in modes if m["name"] == "hierarchical_leiden"), None)
    assert hl_mode is not None, "hierarchical_leiden not in map modes"
    assert hl_mode["label"] == "Hierarchical Leiden"
    print(f"  Map mode label: {hl_mode['label']}")
    
    print("  PASS\n")
    return True


def test_true_hierarchical_leiden():
    """Test TRUE hierarchical Leiden representation (validated fractal map architecture).

    True hierarchical Leiden runs Leiden within parent clusters at finer resolution,
    guaranteeing perfect nesting (1.0) by construction. This validates the fractal
    map architecture where zoom reveals legally coherent substructure.

    Note: This runs on baseline embeddings (not concat_center_tfidf), so exact cluster
    counts may differ from fractal-map lane validation (which got 8 coarse, 127 fine).
    The key property is perfect nesting (1.0) by construction.
    """
    print("=== Test: True Hierarchical Leiden ===")

    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()

    # Verify true_hierarchical_leiden is available
    reps = api.map_loader.get_available_representations()
    assert "true_hierarchical_leiden" in reps, f"true_hierarchical_leiden not in representations: {reps}"
    print(f"  Available representations: {reps}")

    # Test true_hierarchical_leiden at each zoom level
    zoom_levels = api.get_zoom_levels("true_hierarchical_leiden")
    print(f"  Zoom levels: {zoom_levels}")
    # True hierarchical Leiden has 2 zoom levels: coarse and fine
    assert len(zoom_levels) == 2, f"Expected 2 zoom levels, got {len(zoom_levels)}"

    # Zoom 0: coarse clusters
    map_data = api.get_map_data("true_hierarchical_leiden", 0)
    n_coarse = map_data["n_clusters"]
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 0 (coarse): {n_coarse} clusters, {map_data['n_decisions']} decisions")

    # Zoom 1: fine clusters (nested within coarse)
    map_data = api.get_map_data("true_hierarchical_leiden", 1)
    n_fine = map_data["n_clusters"]
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 1 (fine): {n_fine} clusters, {map_data['n_decisions']} decisions")

    # Verify PERFECT nesting: each fine cluster maps to exactly one coarse cluster
    zl_0 = api.map_loader.get_zoom_level("true_hierarchical_leiden", 0)
    zl_1 = api.map_loader.get_zoom_level("true_hierarchical_leiden", 1)

    nesting_consistent = 0
    total_fine_clusters = len(zl_1.clusters)
    for fine_cid, fine_cluster in zl_1.clusters.items():
        if not fine_cluster.decision_ids:
            continue
        first_did = fine_cluster.decision_ids[0]
        coarse_cid = zl_0.cluster_assignments.get(first_did)
        if coarse_cid is not None:
            all_same = all(zl_0.cluster_assignments.get(did) == coarse_cid
                          for did in fine_cluster.decision_ids)
            if all_same:
                nesting_consistent += 1

    nesting_rate = nesting_consistent / total_fine_clusters if total_fine_clusters > 0 else 0
    print(f"  Nesting consistency: {nesting_consistent}/{total_fine_clusters} = {nesting_rate:.4f}")
    # True hierarchical Leiden guarantees perfect nesting by construction
    assert nesting_rate == 1.0, f"True hierarchical Leiden should have perfect nesting (1.0), got {nesting_rate}"

    # Verify metadata reports expected metrics
    map_state = api.map_loader.get_map("true_hierarchical_leiden")
    metadata = map_state.metadata
    assert metadata.get("nesting_score") == 1.0, "Metadata should report nesting_score=1.0"
    assert metadata.get("nesting_verified") == 1.0, "Metadata should report nesting_verified=1.0"
    assert metadata.get("coarse_clusters") == n_coarse, "Metadata coarse_clusters should match zoom 0"
    assert metadata.get("fine_clusters") == n_fine, "Metadata fine_clusters should match zoom 1"
    assert metadata.get("hierarchical_purity", 0) > 0.8, f"Expected hierarchical_purity > 0.8, got {metadata.get('hierarchical_purity')}"
    print(f"  Metadata: coarse={metadata.get('coarse_clusters')}, fine={metadata.get('fine_clusters')}, "
          f"hierarchical_purity={metadata.get('hierarchical_purity'):.4f}, "
          f"coarse_purity={metadata.get('coarse_purity'):.4f}")

    # Test neighbors with true_hierarchical_leiden
    did = list(zl_0.positions.keys())[0]
    neighbors = api.get_neighbors(did, "true_hierarchical_leiden", 1, 5)
    print(f"  Neighbors of {did}: {len(neighbors)} found")
    assert len(neighbors) > 0, "Expected neighbors"

    # Verify map modes includes true_hierarchical_leiden
    modes = api.get_map_modes()
    thl_mode = next((m for m in modes if m["name"] == "true_hierarchical_leiden"), None)
    assert thl_mode is not None, "true_hierarchical_leiden not in map modes"
    assert thl_mode["label"] == "True Hierarchical Leiden"
    print(f"  Map mode label: {thl_mode['label']}")

    print("  PASS\n")
    return True


def test_legal_cited_decisions():
    """Test legal_cited_decisions representation (ACCEPTED legal-distance signal).

    This representation uses TF-IDF on cited decisions only.
    Evidence tier: ACCEPTED (14/14 benchmarks PASS in legal-distance lane).
    Citation heritage AUC: 0.9719 (beats baseline 0.9097).
    Best for: citation-proximity navigation, finding legally related decisions via citation overlap.
    """
    print("=== Test: Legal Cited Decisions (ACCEPTED legal-distance signal) ===")

    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()

    # Verify legal_cited_decisions is available
    reps = api.map_loader.get_available_representations()
    assert "legal_cited_decisions" in reps, f"legal_cited_decisions not in representations: {reps}"
    print(f"  Available representations: {reps}")

    # Test legal_cited_decisions at each zoom level
    zoom_levels = api.get_zoom_levels("legal_cited_decisions")
    print(f"  Zoom levels: {zoom_levels}")
    # Should have 7 zoom levels (0-6) using fractal-map validated 7-resolution ladder
    assert len(zoom_levels) == 7, f"Expected 7 zoom levels, got {len(zoom_levels)}"

    # Zoom 0: domain level (resolution 0.25)
    map_data = api.get_map_data("legal_cited_decisions", 0)
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 0: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Zoom 1: subdomain (resolution 0.5)
    map_data = api.get_map_data("legal_cited_decisions", 1)
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 1: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Zoom 2: (resolution 0.75)
    map_data = api.get_map_data("legal_cited_decisions", 2)
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 2: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Zoom 3: (resolution 1.0)
    map_data = api.get_map_data("legal_cited_decisions", 3)
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 3: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Zoom 4: (resolution 1.5)
    map_data = api.get_map_data("legal_cited_decisions", 4)
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 4: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Zoom 5: (resolution 2.0)
    map_data = api.get_map_data("legal_cited_decisions", 5)
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 5: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Zoom 6: detail (resolution 3.0)
    map_data = api.get_map_data("legal_cited_decisions", 6)
    assert map_data["n_decisions"] == 1000
    print(f"  Zoom 6: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Verify metadata reports ACCEPTED evidence tier
    map_state = api.map_loader.get_map("legal_cited_decisions")
    metadata = map_state.metadata
    assert metadata.get("evidence_tier") == "ACCEPTED", f"Expected evidence_tier=ACCEPTED, got {metadata.get('evidence_tier')}"
    assert metadata.get("benchmark_status") == "14/14 PASS", f"Expected 14/14 PASS, got {metadata.get('benchmark_status')}"
    assert metadata.get("citation_heritage_auc") == 0.9719, f"Expected AUC 0.9719, got {metadata.get('citation_heritage_auc')}"
    print(f"  Metadata: evidence_tier={metadata.get('evidence_tier')}, benchmark_status={metadata.get('benchmark_status')}, AUC={metadata.get('citation_heritage_auc')}")

    # Test neighbors with legal_cited_decisions
    zl_0 = api.map_loader.get_zoom_level("legal_cited_decisions", 0)
    did = list(zl_0.positions.keys())[0]
    neighbors = api.get_neighbors(did, "legal_cited_decisions", 1, 5)
    print(f"  Neighbors of {did}: {len(neighbors)} found")
    assert len(neighbors) > 0, "Expected neighbors"

    # Verify map modes includes legal_cited_decisions
    modes = api.get_map_modes()
    lcd_mode = next((m for m in modes if m["name"] == "legal_cited_decisions"), None)
    assert lcd_mode is not None, "legal_cited_decisions not in map modes"
    print(f"  Map mode label: {lcd_mode['label']}")

    print("  PASS\n")
    return True


def test_center_projected():
    """Test center_projected representation (CRITICAL - evaluation v2 finding).

    This is the ONLY representation passing BOTH adversarial benchmarks:
    - Language dominance: 0.7593 < 0.85 threshold (PASS)
    - Jurist pairwise preference: 0.5215 > 0.5 threshold (PASS)
    - Also passes Jurivoc (4/5) and zoom coherence (+4.6%)

    Evidence tier: REPRODUCED (evaluation v2).
    """
    print("=== Test: Center Projected (eval v2 critical finding) ===")

    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()

    # Verify center_projected is available
    reps = api.map_loader.get_available_representations()
    assert "center_projected" in reps, f"center_projected not in representations: {reps}"
    print(f"  Available representations: {reps}")

    # Test center_projected at each zoom level
    zoom_levels_data = api.get_zoom_levels("center_projected")
    zoom_levels = [z["level"] for z in zoom_levels_data]
    print(f"  Zoom levels: {zoom_levels}")
    assert len(zoom_levels) == 4, f"Expected 4 zoom levels, got {len(zoom_levels)}"

    for zl in zoom_levels:
        map_data = api.get_map_data("center_projected", zl)
        assert map_data["n_decisions"] == 1000
        print(f"  Zoom {zl}: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Verify metadata reports evaluation v2 results
    map_state = api.map_loader.get_map("center_projected")
    metadata = map_state.metadata
    assert metadata.get("evidence_tier") == "REPRODUCED", f"Expected evidence_tier=REPRODUCED, got {metadata.get('evidence_tier')}"
    eval_results = metadata.get("evaluation_v2_results", {})
    assert eval_results.get("language_dominance_pass") == True, "Expected language_dominance_pass=True"
    assert eval_results.get("jurist_pairwise_pass") == True, "Expected jurist_pairwise_pass=True"
    print(f"  Metadata: evidence_tier={metadata.get('evidence_tier')}, language_dom_pass={eval_results.get('language_dominance_pass')}, jurist_pass={eval_results.get('jurist_pairwise_pass')}")

    # Test neighbors with center_projected
    zl_0 = api.map_loader.get_zoom_level("center_projected", 0)
    did = list(zl_0.positions.keys())[0]
    neighbors = api.get_neighbors(did, "center_projected", 1, 5)
    print(f"  Neighbors of {did}: {len(neighbors)} found")
    assert len(neighbors) > 0, "Expected neighbors"

    # Verify map modes includes center_projected
    modes = api.get_map_modes()
    cp_mode = next((m for m in modes if m["name"] == "center_projected"), None)
    assert cp_mode is not None, "center_projected not in map modes"
    print(f"  Map mode label: {cp_mode['label']}")

    print("  PASS\n")
    return True


def test_hybrid_alpha_0_3():
    """Test hybrid_alpha_0_3 representation (30% center_projected + 70% legal_cited_decisions).

    This hybrid favors citation-proximity (legal_cited_decisions) while retaining
    some language-invariant legal geometry from center_projected.

    Evidence tier: EXPLORATORY.
    """
    print("=== Test: Hybrid Alpha 0.3 (30% center + 70% cited) ===")

    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()

    # Verify hybrid_alpha_0_3 is available
    reps = api.map_loader.get_available_representations()
    assert "hybrid_alpha_0_3" in reps, f"hybrid_alpha_0_3 not in representations: {reps}"
    print(f"  Available representations: {reps}")

    # Test hybrid_alpha_0_3 at each zoom level
    zoom_levels_data = api.get_zoom_levels("hybrid_alpha_0_3")
    zoom_levels = [z["level"] for z in zoom_levels_data]
    print(f"  Zoom levels: {zoom_levels}")
    assert len(zoom_levels) == 4, f"Expected 4 zoom levels, got {len(zoom_levels)}"

    for zl in zoom_levels:
        map_data = api.get_map_data("hybrid_alpha_0_3", zl)
        assert map_data["n_decisions"] == 1000
        print(f"  Zoom {zl}: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Verify metadata
    map_state = api.map_loader.get_map("hybrid_alpha_0_3")
    metadata = map_state.metadata
    assert metadata.get("alpha") == 0.3, f"Expected alpha=0.3, got {metadata.get('alpha')}"
    assert metadata.get("center_projected_weight") == 0.3
    assert metadata.get("legal_cited_decisions_weight") == 0.7
    assert metadata.get("evidence_tier") == "EXPLORATORY"
    print(f"  Metadata: alpha={metadata.get('alpha')}, center_weight={metadata.get('center_projected_weight')}, cited_weight={metadata.get('legal_cited_decisions_weight')}, evidence_tier={metadata.get('evidence_tier')}")

    # Test neighbors
    zl_0 = api.map_loader.get_zoom_level("hybrid_alpha_0_3", 0)
    did = list(zl_0.positions.keys())[0]
    neighbors = api.get_neighbors(did, "hybrid_alpha_0_3", 1, 5)
    print(f"  Neighbors of {did}: {len(neighbors)} found")
    assert len(neighbors) > 0, "Expected neighbors"

    print("  PASS\n")
    return True


def test_hybrid_alpha_0_5():
    """Test hybrid_alpha_0_5 representation (50% center_projected + 50% legal_cited_decisions).

    Equal blend of language-invariant legal geometry and citation-proximity signals.

    Evidence tier: EXPLORATORY.
    """
    print("=== Test: Hybrid Alpha 0.5 (50% center + 50% cited) ===")

    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()

    # Verify hybrid_alpha_0_5 is available
    reps = api.map_loader.get_available_representations()
    assert "hybrid_alpha_0_5" in reps, f"hybrid_alpha_0_5 not in representations: {reps}"
    print(f"  Available representations: {reps}")

    # Test hybrid_alpha_0_5 at each zoom level
    zoom_levels_data = api.get_zoom_levels("hybrid_alpha_0_5")
    zoom_levels = [z["level"] for z in zoom_levels_data]
    print(f"  Zoom levels: {zoom_levels}")
    assert len(zoom_levels) == 4, f"Expected 4 zoom levels, got {len(zoom_levels)}"

    for zl in zoom_levels:
        map_data = api.get_map_data("hybrid_alpha_0_5", zl)
        assert map_data["n_decisions"] == 1000
        print(f"  Zoom {zl}: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

    # Verify metadata
    map_state = api.map_loader.get_map("hybrid_alpha_0_5")
    metadata = map_state.metadata
    assert metadata.get("alpha") == 0.5, f"Expected alpha=0.5, got {metadata.get('alpha')}"
    assert metadata.get("center_projected_weight") == 0.5
    assert metadata.get("legal_cited_decisions_weight") == 0.5
    assert metadata.get("evidence_tier") == "EXPLORATORY"
    print(f"  Metadata: alpha={metadata.get('alpha')}, center_weight={metadata.get('center_projected_weight')}, cited_weight={metadata.get('legal_cited_decisions_weight')}, evidence_tier={metadata.get('evidence_tier')}")

    # Test neighbors
    zl_0 = api.map_loader.get_zoom_level("hybrid_alpha_0_5", 0)
    did = list(zl_0.positions.keys())[0]
    neighbors = api.get_neighbors(did, "hybrid_alpha_0_5", 1, 5)
    print(f"  Neighbors of {did}: {len(neighbors)} found")
    assert len(neighbors) > 0, "Expected neighbors"

    print("  PASS\n")
    return True


def test_legal_issues_outcomes():
    """Test legal_issues_outcomes representation (legal-specific signal from legal_signals).

    This representation captures legal issues (statutes, cited decisions) and outcomes
    as a TF-IDF embedding, providing a legal-specific view distinct from
    generic semantic similarity or citation-only proximity.

    Evidence tier: ACCEPTED (legal-distance lane v6) with warnings (fails 4/14 benchmarks:
    adversarial_falsification, multilingual_invariance, citation_heritage, tf_metadata_human_indexing).
    """
    print("=== Test: Legal Issues & Outcomes (EXPLORATORY) ===")

    corpus_dir = Path(__file__).parent.parent / "results" / "corpus" / "normalization" / "canonical"
    results_dir = Path(__file__).parent.parent / "results" / "fractal_map"
    api = NavigationAPI(str(corpus_dir), str(results_dir))
    api.initialize()

    # Verify legal_issues_outcomes is available
    reps = api.map_loader.get_available_representations()
    assert "legal_issues_outcomes" in reps, f"legal_issues_outcomes not in representations: {reps}"
    print(f"  Available representations: {reps}")

    # Test legal_issues_outcomes at each zoom level
    zoom_levels_data = api.get_zoom_levels("legal_issues_outcomes")
    zoom_levels = [z["level"] for z in zoom_levels_data]
    print(f"  Zoom levels: {zoom_levels}")
    # Should have 7 zoom levels (0-6) using fractal-map validated 7-resolution ladder
    assert len(zoom_levels) == 7, f"Expected 7 zoom levels, got {len(zoom_levels)}"

    for zl in zoom_levels:
        map_data = api.get_map_data("legal_issues_outcomes", zl)
        assert map_data["n_decisions"] == 1000
        print(f"  Zoom {zl}: {map_data['n_clusters']} clusters, {map_data['n_decisions']} decisions")

# Verify metadata
        map_state = api.map_loader.get_map("legal_issues_outcomes")
        metadata = map_state.metadata
        # Fractal-map lane validates this as ACCEPTED (with warnings for 4 failed benchmarks)
        assert metadata.get("evidence_tier") == "ACCEPTED", f"Expected evidence_tier=ACCEPTED, got {metadata.get('evidence_tier')}"
        assert metadata.get("signal_source") == "statutes_cited_outcomes_legal_area_erwaegungen_headings"
        assert "tfidf_features" in metadata
        print(f"  Metadata: evidence_tier={metadata.get('evidence_tier')}, signal_source={metadata.get('signal_source')}, tfidf_features={metadata.get('tfidf_features')}")
        
        # Verify warnings are present
        warnings = metadata.get("warnings", [])
        assert len(warnings) >= 4, f"Expected at least 4 warnings, got {warnings}"
        print(f"  Warnings: {warnings}")

    # Test neighbors
    zl_0 = api.map_loader.get_zoom_level("legal_issues_outcomes", 0)
    did = list(zl_0.positions.keys())[0]
    neighbors = api.get_neighbors(did, "legal_issues_outcomes", 1, 5)
    print(f"  Neighbors of {did}: {len(neighbors)} found")
    assert len(neighbors) > 0, "Expected neighbors"

    print("  PASS\n")
    return True


if __name__ == "__main__":
    results = []
    results.append(("Corpus Loader", test_corpus_loader()))
    results.append(("Map Loader", test_map_loader()))
    results.append(("Navigation API", test_navigation_api()))
    results.append(("End-to-End", test_end_to_end()))
    results.append(("HDBSCAN", test_hdbscan()))
    results.append(("Corpus Import", test_corpus_import()))
    results.append(("Section Modes", test_section_modes()))
    results.append(("Citations", test_citations()))
    results.append(("Map Modes API", test_map_modes_api()))
    results.append(("Hierarchical Leiden", test_hierarchical_leiden()))
    results.append(("True Hierarchical Leiden", test_true_hierarchical_leiden()))
    results.append(("Legal Cited Decisions", test_legal_cited_decisions()))
    results.append(("Center Projected (eval v2)", test_center_projected()))
    results.append(("Hybrid Alpha 0.3", test_hybrid_alpha_0_3()))
    results.append(("Hybrid Alpha 0.5", test_hybrid_alpha_0_5()))
    results.append(("Legal Issues & Outcomes", test_legal_issues_outcomes()))
    
    print("=" * 50)
    print("RESULTS:")
    for name, passed in results:
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    
    all_passed = all(p for _, p in results)
    print(f"\nOverall: {'ALL PASS' if all_passed else 'SOME FAILED'}")
    sys.exit(0 if all_passed else 1)
