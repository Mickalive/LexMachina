"""Server smoke tests for frontier-query-map-ui.

Verifies that the prototype server starts and serves all required endpoints.
"""
import json
import sys
import time
import unittest
import threading
from pathlib import Path
from http.client import HTTPConnection

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Add team src to path for imports
TEAM_SRC = REPO_ROOT / "frontier" / "frontier-query-map-ui" / "src"
sys.path.insert(0, str(TEAM_SRC))

from serve import make_server, start_in_thread


class TestServerSmoke(unittest.TestCase):
    """Smoke tests for the prototype HTTP server."""

    @classmethod
    def setUpClass(cls):
        # Start server in background thread
        cls.server, cls.thread = start_in_thread("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        
        # Wait for server to be ready
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _get(self, path):
        """Make GET request and return (status, body_dict)."""
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
        finally:
            conn.close()

    def test_root_returns_html(self):
        """GET / must return 200 with HTML content."""
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.getheader("Content-Type", ""))
            body = resp.read().decode("utf-8")
            self.assertIn("LexMachina", body)
            self.assertIn("query_map", body.lower())
        finally:
            conn.close()

    def test_ui_assets_served(self):
        """GET /ui/* must serve UI assets."""
        # query_map.html
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/ui/query_map.html")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.getheader("Content-Type", ""))
        finally:
            conn.close()
        
        # query_map.css
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/ui/query_map.css")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.getheader("Content-Type", ""))
        finally:
            conn.close()
        
        # query_map_model.js
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/ui/query_map_model.js")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.getheader("Content-Type", ""))
        finally:
            conn.close()
        
        # query_map.js
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/ui/query_map.js")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.getheader("Content-Type", ""))
        finally:
            conn.close()
        
        # canvas2d_renderer.js
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/ui/canvas2d_renderer.js")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.getheader("Content-Type", ""))
        finally:
            conn.close()

    def test_vendor_assets_served(self):
        """GET /vendor/* must serve accepted product static assets."""
        # bundle_adapter.js
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/vendor/bundle_adapter.js")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.getheader("Content-Type", ""))
            body = resp.read().decode("utf-8")
            self.assertIn("adaptBundleForWebGL", body)
        finally:
            conn.close()
        
        # webgl_renderer.js
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/vendor/webgl_renderer.js")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.getheader("Content-Type", ""))
            body = resp.read().decode("utf-8")
            self.assertIn("WebGLRenderer", body)
        finally:
            conn.close()

    def test_data_endpoints(self):
        """GET /data/* must serve fixture data."""
        # visualization.json
        status, data = self._get("/data/visualization.json")
        self.assertEqual(status, 200)
        self.assertIn("decisions", data)
        self.assertIn("clusters", data)
        self.assertIn("relations", data)
        self.assertGreater(data["n_decisions"], 0)
        
        # bundle.json
        status, data = self._get("/data/bundle.json")
        self.assertEqual(status, 200)
        self.assertIn("decisions", data)
        self.assertIn("clusters", data)
        self.assertIn("answer", data)
        self.assertGreater(len(data["decisions"]), 0)
        
        # manifest.json
        status, data = self._get("/data/manifest.json")
        self.assertEqual(status, 200)
        self.assertIn("team_id", data)
        self.assertEqual(data["team_id"], "frontier-query-map-ui")

    def test_api_health(self):
        """GET /api/health must return liveness info."""
        status, data = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("viz_bytes", data)
        self.assertIn("bundle_bytes", data)
        self.assertTrue(data.get("vendor_renderer"))
        self.assertTrue(data.get("vendor_adapter"))

    def test_api_fixture(self):
        """GET /api/fixture must return the bundle."""
        status, data = self._get("/api/fixture")
        self.assertEqual(status, 200)
        self.assertIn("decisions", data)
        self.assertGreater(len(data["decisions"]), 0)

    def test_api_query_run(self):
        """GET /api/query/run must execute shimmed pipeline."""
        # Use GET with query params as implemented
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request("GET", "/api/query/run?q=test&n=10")
            resp = conn.getresponse()
            # May succeed or fail depending on fixture, but should not 500 from import errors
            self.assertNotEqual(resp.status, 500, "Server error - likely import/shim issue")
            
            if resp.status == 200:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                self.assertIn("decisions", data)
            elif resp.status == 400:
                # Empty query or similar - acceptable
                pass
        finally:
            conn.close()

    def test_cors_headers(self):
        """All responses should have CORS headers for test access."""
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/")
            resp = conn.getresponse()
            self.assertEqual(resp.getheader("Access-Control-Allow-Origin"), "*")
        finally:
            conn.close()

    def test_404_for_unknown_paths(self):
        """Unknown paths must return 404 JSON."""
        status, data = self._get("/nonexistent")
        self.assertEqual(status, 404)
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)