"""
LexMachina Product Server
Minimal Flask/HTTP server for the case-law map navigation.
"""
import json
import os
import sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.navigation import NavigationAPI


# Global navigation API instance
_nav_api = None


def get_nav_api() -> NavigationAPI:
    """Get or initialize the navigation API."""
    global _nav_api
    if _nav_api is None:
        base_dir = Path(__file__).parent
        corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
        results_dir = str(base_dir / "results" / "fractal_map")
        _nav_api = NavigationAPI(corpus_dir, results_dir)
        _nav_api.initialize()
    return _nav_api


class ProductHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the LexMachina product."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API routes
        if path == "/api/overview":
            self._json_response(get_nav_api().get_overview())
        elif path == "/api/map":
            rep = params.get("representation", ["concat_center_tfidf"])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            self._json_response(get_nav_api().get_map_data(rep, zoom))
        elif path == "/api/cluster":
            rep = params.get("representation", ["concat_center_tfidf"])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            cid = int(params.get("cluster_id", ["0"])[0])
            self._json_response(get_nav_api().get_cluster_detail(rep, zoom, cid))
        elif path == "/api/decision":
            did = params.get("id", [""])[0]
            self._json_response(get_nav_api().get_decision(did))
        elif path == "/api/search":
            q = params.get("q", [""])[0]
            limit = int(params.get("limit", ["20"])[0])
            self._json_response(get_nav_api().search_decisions(q, limit))
        elif path == "/api/neighbors":
            did = params.get("id", [""])[0]
            rep = params.get("representation", ["concat_center_tfidf"])[0]
            zoom = int(params.get("zoom", ["2"])[0])
            n = int(params.get("n", ["10"])[0])
            self._json_response(get_nav_api().get_neighbors(did, rep, zoom, n))
        elif path == "/api/zoom_levels":
            rep = params.get("representation", ["concat_center_tfidf"])[0]
            self._json_response(get_nav_api().get_zoom_levels(rep))
        elif path == "/api/corpus/stats":
            self._json_response(get_nav_api().get_corpus_stats())
        # Static files
        elif path == "/" or path == "/index.html":
            self._serve_file("static/index.html", "text/html")
        elif path.endswith(".js"):
            self._serve_file(f"static{path}", "application/javascript")
        elif path.endswith(".css"):
            self._serve_file(f"static{path}", "text/css")
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/import":
            self._handle_import()
        else:
            self.send_error(404)

    def _handle_import(self):
        """Handle corpus import via multipart form upload or JSON body."""
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            self._handle_multipart_import(content_type)
        elif "application/json" in content_type:
            self._handle_json_import()
        else:
            self._json_response({"error": "Expected Content-Type: multipart/form-data or application/json"}, 400)

    def _handle_json_import(self):
        """Import corpus from JSON body (array of decision records)."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            records = json.loads(body.decode("utf-8"))

            if not isinstance(records, list):
                records = [records]

            result = get_nav_api().import_corpus(records)
            self._json_response(result)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_multipart_import(self, content_type):
        """Import corpus from multipart file upload."""
        try:
            # Parse boundary
            boundary = content_type.split("boundary=")[1].strip()
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            # Simple multipart parser for file uploads
            parts = body.split(f"--{boundary}".encode())
            records = []

            for part in parts:
                if b"filename=" in part:
                    # Extract file content
                    header_end = part.find(b"\r\n\r\n")
                    if header_end == -1:
                        continue
                    file_content = part[header_end + 4:]
                    # Remove trailing boundary marker
                    if file_content.endswith(b"\r\n"):
                        file_content = file_content[:-2]
                    if file_content.endswith(b"--"):
                        file_content = file_content[:-2]

                    # Parse JSONL
                    for line in file_content.decode("utf-8").split("\n"):
                        line = line.strip()
                        if line:
                            try:
                                records.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            if not records:
                self._json_response({"error": "No valid records found in upload"}, 400)
                return

            result = get_nav_api().import_corpus(records)
            self._json_response(result)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _json_response(self, data, status=200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _serve_file(self, filepath, content_type):
        """Serve a static file."""
        base_dir = Path(__file__).parent
        full_path = base_dir / filepath
        if full_path.exists():
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            with open(full_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        """Suppress default logging for cleaner output."""
        pass


def run_server(port=8080):
    """Start the product server."""
    print(f"Initializing LexMachina navigation...")
    nav = get_nav_api()
    print(f"Loaded {nav.corpus.size} decisions, {len(nav.map_loader.get_available_representations())} maps")

    server = HTTPServer(("0.0.0.0", port), ProductHandler)
    print(f"LexMachina server running on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
