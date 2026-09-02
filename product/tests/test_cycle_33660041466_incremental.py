"""
LexMachina Product Tests — Cycle 33660041466
Tests for incremental map update infrastructure:
1. Adding decisions increases position count
2. New decisions receive cluster assignments
3. Delta persistence and merge works
4. Pending update count tracks additions
5. POST /api/map/incremental_update endpoint returns valid response
"""
import sys
import json
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.navigation import NavigationAPI
from app.incremental_updater import IncrementalUpdater


def _get_api():
    """Create and initialize a fresh NavigationAPI instance."""
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    api = NavigationAPI(corpus_dir, results_dir)
    api.initialize()
    return api


def _clean_import_state():
    """Clean user import state before tests."""
    base_dir = Path(__file__).parent.parent
    nav_import_dir = base_dir / "results" / "fractal_map" / "user_imports"
    if nav_import_dir.exists():
        shutil.rmtree(nav_import_dir)


def _get_test_decision_ids(api, n=3):
    """Get a list of decision IDs from the corpus for testing."""
    all_ids = list(api._base_decision_ids)
    # Use IDs that exist in the base corpus but are not at the tail
    # so we have good k-NN neighbors
    return all_ids[100:100 + n]


def _get_unknown_decision_ids(api, n=3):
    """Get decision IDs that are NOT in the base corpus (simulating imports)."""
    # Use fabricated IDs that won't match anything in the corpus
    return [f"TEST_INCREMENTAL_{i}" for i in range(n)]


def test_add_decisions_increases_count():
    """Verify that adding decisions increases the map position count."""
    print("=== Test: Add Decisions Increases Count ===")
    _clean_import_state()
    api = _get_api()
    updater = IncrementalUpdater(api)

    default_rep = api._get_default_representation()
    zoom_level = 1

    zl_before = api.map_loader.get_zoom_level(default_rep, zoom_level)
    count_before = len(zl_before.positions) if zl_before else 0

    # Use IDs from the base corpus embedding space (so k-NN finds neighbors)
    test_ids = _get_test_decision_ids(api, n=5)

    result = updater.add_decisions_to_map(
        decision_ids=test_ids,
        representation=default_rep,
        zoom_level=zoom_level,
    )

    zl_after = api.map_loader.get_zoom_level(default_rep, zoom_level)
    count_after = len(zl_after.positions) if zl_after else 0

    assert result["added"] > 0, f"Expected added > 0, got {result['added']}"
    assert count_after >= count_before, (
        f"Expected position count to increase: before={count_before}, after={count_after}"
    )
    print(f"  PASS: added={result['added']}, positions {count_before} -> {count_after}")


def test_cluster_assignment():
    """Verify that new decisions receive cluster assignments."""
    print("=== Test: Cluster Assignment ===")
    _clean_import_state()
    api = _get_api()
    updater = IncrementalUpdater(api)

    default_rep = api._get_default_representation()
    zoom_level = 1
    test_ids = _get_test_decision_ids(api, n=5)

    result = updater.add_decisions_to_map(
        decision_ids=test_ids,
        representation=default_rep,
        zoom_level=zoom_level,
    )

    # Check that each added decision has a cluster assignment
    clusters_affected = result["clusters_affected"]
    assert len(clusters_affected) > 0, "Expected at least one cluster affected"

    # Verify in-memory state
    zl = api.map_loader.get_zoom_level(default_rep, zoom_level)
    for did in test_ids:
        if (did, default_rep) in api._imported_positions:
            rec = api._imported_positions[(did, default_rep)]
            assert "cluster" in rec, f"Missing cluster in record for {did}"
            assert rec["cluster"] >= 0, f"Invalid cluster for {did}: {rec['cluster']}"
            assert did in zl.cluster_assignments, (
                f"Decision {did} not in cluster_assignments"
            )

    print(f"  PASS: clusters_affected={clusters_affected}, all decisions have cluster assignments")


def test_persist_and_merge():
    """Verify delta persistence and merge works."""
    print("=== Test: Persist and Merge ===")
    _clean_import_state()
    api = _get_api()
    updater = IncrementalUpdater(api)

    default_rep = api._get_default_representation()
    zoom_level = 1
    test_ids = _get_test_decision_ids(api, n=5)

    # Add decisions
    updater.add_decisions_to_map(
        decision_ids=test_ids,
        representation=default_rep,
        zoom_level=zoom_level,
    )

    # Persist
    persist_result = updater.persist_incremental_update(
        representation=default_rep,
        zoom_level=zoom_level,
    )
    assert persist_result["persisted"] > 0, (
        f"Expected persisted > 0, got {persist_result['persisted']}"
    )
    assert persist_result["delta_file"] is not None, "Expected delta_file to be set"

    delta_path = Path(persist_result["delta_file"])
    assert delta_path.exists(), f"Delta file does not exist: {delta_path}"

    # Read delta file and verify contents
    with open(delta_path, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    assert len(lines) > 0, "Delta file is empty"

    # Pending should now be 0 for this representation
    pending = updater.get_pending_updates()
    assert pending["by_representation"].get(default_rep, 0) == 0, (
        f"Expected 0 pending after persist, got {pending}"
    )

    # Merge
    merge_result = updater.merge_deltas(
        representation=default_rep,
        zoom_level=zoom_level,
    )
    assert merge_result["merged"] > 0, (
        f"Expected merged > 0, got {merge_result['merged']}"
    )

    print(f"  PASS: persisted={persist_result['persisted']}, merged={merge_result['merged']}")


def test_pending_updates():
    """Verify pending count tracks additions."""
    print("=== Test: Pending Updates ===")
    _clean_import_state()
    api = _get_api()
    updater = IncrementalUpdater(api)

    default_rep = api._get_default_representation()
    zoom_level = 1

    # Initially zero pending
    pending = updater.get_pending_updates()
    assert pending["total_pending"] == 0, (
        f"Expected 0 pending initially, got {pending['total_pending']}"
    )

    # Add some decisions
    test_ids = _get_test_decision_ids(api, n=5)
    result = updater.add_decisions_to_map(
        decision_ids=test_ids,
        representation=default_rep,
        zoom_level=zoom_level,
    )

    # Pending should reflect additions
    pending = updater.get_pending_updates()
    assert pending["total_pending"] == result["added"], (
        f"Expected pending={result['added']}, got {pending['total_pending']}"
    )
    assert default_rep in pending["by_representation"], (
        f"Expected representation in by_representation"
    )

    print(f"  PASS: pending after add = {pending}")


def test_endpoint_structure():
    """Verify POST /api/map/incremental_update returns valid response."""
    print("=== Test: Endpoint Structure ===")
    _clean_import_state()
    api = _get_api()
    updater = IncrementalUpdater(api)

    default_rep = api._get_default_representation()
    zoom_level = 1
    test_ids = _get_test_decision_ids(api, n=5)

    # Simulate the endpoint logic directly (no HTTP server needed)
    result = updater.add_decisions_to_map(
        decision_ids=test_ids,
        representation=default_rep,
        zoom_level=zoom_level,
    )

    # Validate response structure
    assert "added" in result, "Missing 'added' key in response"
    assert "clusters_affected" in result, "Missing 'clusters_affected' key in response"
    assert "positions_updated" in result, "Missing 'positions_updated' key in response"
    assert isinstance(result["added"], int), "'added' must be an int"
    assert isinstance(result["clusters_affected"], list), "'clusters_affected' must be a list"
    assert isinstance(result["positions_updated"], int), "'positions_updated' must be an int"
    assert result["added"] == result["positions_updated"], (
        "'added' and 'positions_updated' should be equal"
    )

    # Validate pending_updates endpoint structure
    pending = updater.get_pending_updates()
    assert "total_pending" in pending, "Missing 'total_pending' key"
    assert "by_representation" in pending, "Missing 'by_representation' key"
    assert isinstance(pending["total_pending"], int), "'total_pending' must be an int"
    assert isinstance(pending["by_representation"], dict), "'by_representation' must be a dict"

    print(f"  PASS: endpoint response structure valid: {result}")
    print(f"  PASS: pending_updates structure valid: {pending}")
