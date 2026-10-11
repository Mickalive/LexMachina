"""
LexMachina Product HTTP API Integration Tests
Verifies HTTP endpoint response formats match frontend expectations.
These tests catch breaking API changes that navigation API layer tests miss.
"""
import sys
import json
import threading
import time
from pathlib import Path
from http.server import HTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import run_server, ProductHandler, ThreadedHTTPServer, get_nav_api
import server as server_module


class HTTPIntegrationTest:
    """HTTP integration test harness using the real server."""
    
    def __init__(self, port=18080):
        self.port = port
        self.server = None
        self.server_thread = None
        self.base_url = f"http://localhost:{port}"
    
    def start(self):
        """Start the server in a background thread."""
        # Reset global nav_api to force fresh initialization for this test
        server_module._nav_api = None
        server_module._nav_api_init_error = None
        
        self.server = ThreadedHTTPServer(("0.0.0.0", self.port), ProductHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        
        # Wait for server to be ready
        for _ in range(50):
            try:
                with urlopen(f"{self.base_url}/api/health", timeout=1) as resp:
                    if resp.status == 200:
                        break
            except:
                time.sleep(0.1)
        else:
            raise RuntimeError("Server failed to start")
    
    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.server_thread:
            self.server_thread.join(timeout=2)
        # Reset global for next test
        server_module._nav_api = None
        server_module._nav_api_init_error = None
    
    def get(self, path):
        """Make a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))


def test_http_search_response_format():
    """Test /api/search returns wrapped format with 'results' key."""
    print("=== Test: HTTP /api/search Response Format ===")
    
    test = HTTPIntegrationTest(18080)
    test.start()
    
    try:
        # Test basic search
        resp = test.get("/api/search?q=Beschwerde&limit=5")
        
        # Assert wrapped response format
        assert "results" in resp, f"Response missing 'results' key: {resp.keys()}"
        assert isinstance(resp["results"], list), f"'results' should be list, got {type(resp['results'])}"
        assert "query" in resp, f"Response missing 'query' key"
        assert "limit" in resp, f"Response missing 'limit' key"
        
        print(f"  Response keys: {list(resp.keys())}")
        print(f"  Results count: {len(resp['results'])}")
        print(f"  Query: {resp['query']}")
        print(f"  Limit: {resp['limit']}")
        
        # Verify results structure if any
        if resp["results"]:
            first = resp["results"][0]
            assert "decision_id" in first, "Result missing decision_id"
            assert "language" in first, "Result missing language"
            print(f"  First result: {first['decision_id']} ({first['language']})")
        
        # Test with language filter
        resp_lang = test.get("/api/search?q=Recht&limit=3&language=de")
        assert "results" in resp_lang
        assert resp_lang["query"] == "Recht"
        assert resp_lang["limit"] == 3
        
        # Test empty query returns empty results
        resp_empty = test.get("/api/search?q=nonexistentqueryxyz123&limit=5")
        assert "results" in resp_empty
        assert isinstance(resp_empty["results"], list)
        
        print("  PASS\n")
        return True
        
    finally:
        test.stop()


def test_http_neighbors_response_format():
    """Test /api/neighbors returns wrapped format with 'neighbors' key."""
    print("=== Test: HTTP /api/neighbors Response Format ===")
    
    test = HTTPIntegrationTest(18081)
    test.start()
    
    try:
        # Debug: check health endpoint first
        health = test.get("/api/health")
        print(f"  Health: {health}")
        
        # Debug: check available representations
        modes = test.get("/api/map_modes")
        print(f"  Map modes response: {modes}")
        reps = [m["name"] for m in modes if m.get("type") == "representation"]
        print(f"  Available representations: {reps}")
        
        # Use default representation (what the server initializes with - production default)
        map_data = test.get("/api/map?zoom=1")
        
        # If error, try the production default explicitly
        if "positions" not in map_data or len(map_data.get("positions", [])) == 0:
            print(f"  Default map failed: {map_data}")
            map_data = test.get("/api/map?representation=cited_outcome_hybrid_0.5_174k&zoom=1")
        
        assert "positions" in map_data, f"Map data missing positions: {map_data.keys()}"
        assert len(map_data["positions"]) > 0, "No positions in map data"
        
        decision_id = map_data["positions"][0]["decision_id"]
        print(f"  Testing with decision: {decision_id}")
        
        # Test neighbors endpoint with the same representation
        rep = map_data.get("representation", "cited_outcome_hybrid_0.5_174k")
        resp = test.get(f"/api/neighbors?id={decision_id}&representation={rep}&zoom=1&n=5")
        
        # Assert wrapped response format
        assert "neighbors" in resp, f"Response missing 'neighbors' key: {resp.keys()}"
        assert isinstance(resp["neighbors"], list), f"'neighbors' should be list, got {type(resp['neighbors'])}"
        assert "decision_id" in resp, f"Response missing 'decision_id' key"
        assert "representation" in resp, f"Response missing 'representation' key"
        assert "zoom" in resp, f"Response missing 'zoom' key"
        
        print(f"  Response keys: {list(resp.keys())}")
        print(f"  Neighbors count: {len(resp['neighbors'])}")
        print(f"  Decision ID: {resp['decision_id']}")
        print(f"  Representation: {resp['representation']}")
        print(f"  Zoom: {resp['zoom']}")
        
        # Verify neighbors structure if any
        if resp["neighbors"]:
            first = resp["neighbors"][0]
            assert "decision_id" in first, "Neighbor missing decision_id"
            assert "distance" in first, "Neighbor missing distance"
            assert "language" in first, "Neighbor missing language"
            print(f"  First neighbor: {first['decision_id']} (dist={first['distance']})")
        
        # Test with default representation (no explicit representation param)
        resp_default = test.get(f"/api/neighbors?id={decision_id}&n=3")
        assert "neighbors" in resp_default
        assert "decision_id" in resp_default
        
        # Test invalid decision ID
        resp_invalid = test.get("/api/neighbors?id=nonexistent&n=5")
        assert "neighbors" in resp_invalid
        assert isinstance(resp_invalid["neighbors"], list)
        # Should return empty list for invalid ID
        
        print("  PASS\n")
        return True
        
    finally:
        test.stop()


def test_http_search_backward_compatibility():
    """Test that navigation API layer (search_decisions) still returns List[Dict]."""
    print("=== Test: Navigation API search_decisions Backward Compatibility ===")
    
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    
    api = get_nav_api()
    api.initialize()
    
    # Test direct navigation API call (bypasses HTTP layer)
    results = api.search_decisions("Beschwerde", limit=5)
    
    assert isinstance(results, list), f"search_decisions should return list, got {type(results)}"
    if results:
        assert isinstance(results[0], dict), "Results should be list of dicts"
        assert "decision_id" in results[0]
        assert "language" in results[0]
    
    print(f"  Direct API returns: {type(results)} with {len(results)} items")
    print("  PASS\n")
    return True


def test_http_neighbors_backward_compatibility():
    """Test that navigation API layer (get_neighbors) still returns List[Dict]."""
    print("=== Test: Navigation API get_neighbors Backward Compatibility ===")
    
    base_dir = Path(__file__).parent.parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")
    
    api = get_nav_api()
    api.initialize()
    
    # Get a decision ID
    map_data = api.get_map_data("concat_center_tfidf", 1)
    decision_id = map_data["positions"][0]["decision_id"]
    
    # Test direct navigation API call (bypasses HTTP layer)
    neighbors = api.get_neighbors(decision_id, "concat_center_tfidf", 1, 5)
    
    assert isinstance(neighbors, list), f"get_neighbors should return list, got {type(neighbors)}"
    if neighbors:
        assert isinstance(neighbors[0], dict), "Neighbors should be list of dicts"
        assert "decision_id" in neighbors[0]
        assert "distance" in neighbors[0]
    
    print(f"  Direct API returns: {type(neighbors)} with {len(neighbors)} items")
    print("  PASS\n")
    return True


def run_all_tests():
    """Run all HTTP integration tests."""
    tests = [
        test_http_search_response_format,
        test_http_neighbors_response_format,
        test_http_search_backward_compatibility,
        test_http_neighbors_backward_compatibility,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}\n")
            failed += 1
    
    print(f"=== HTTP Integration Tests: {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)