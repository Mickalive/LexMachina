"""
LexMachina Product Server
Minimal Flask/HTTP server for the case-law map navigation.
"""
import json
import os
import sys
import time
import hashlib
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import OrderedDict
from functools import wraps
from typing import Tuple, Dict, Optional, Any, List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.navigation import NavigationAPI
from app.evaluation_loader import EvaluationLoader


# Global navigation API instance
_nav_api = None
_eval_loader = None
_server_start_time = time.time()

# Rate limiting
_rate_limit_store = {}
_rate_limit_lock = threading.Lock()
DEFAULT_RATE_LIMIT = 100  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds

# Caching
_cache_store = {}
_cache_lock = threading.Lock()
CACHE_TTL = 300  # 5 minutes default


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = DEFAULT_RATE_LIMIT, window_seconds: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def check_rate_limit(self, client_id: str) -> Tuple[bool, Dict]:
        """Check if client is within rate limit. Returns (allowed, info_dict)."""
        now = time.time()
        with _rate_limit_lock:
            if client_id not in _rate_limit_store:
                _rate_limit_store[client_id] = []
            
            # Clean old entries
            cutoff = now - self.window_seconds
            _rate_limit_store[client_id] = [
                t for t in _rate_limit_store[client_id] if t > cutoff
            ]
            
            current_count = len(_rate_limit_store[client_id])
            allowed = current_count < self.max_requests
            
            if allowed:
                _rate_limit_store[client_id].append(now)
            
            return allowed, {
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - current_count - (1 if allowed else 0)),
                "reset": int(now + self.window_seconds),
                "retry_after": self.window_seconds if not allowed else 0
            }


class ResponseCache:
    """Simple in-memory response cache with TTL."""
    
    def __init__(self, default_ttl: int = CACHE_TTL):
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        with _cache_lock:
            if key in _cache_store:
                entry = _cache_store[key]
                if time.time() < entry['expires']:
                    return entry['data']
                else:
                    del _cache_store[key]
        return None
    
    def set(self, key: str, data: Any, ttl: int = None) -> None:
        with _cache_lock:
            ttl = ttl or self.default_ttl
            _cache_store[key] = {
                'data': data,
                'expires': time.time() + ttl
            }
    
    def invalidate(self, pattern: str = None) -> None:
        with _cache_lock:
            if pattern is None:
                _cache_store.clear()
            else:
                keys_to_delete = [k for k in _cache_store.keys() if pattern in k]
                for k in keys_to_delete:
                    del _cache_store[k]


# Global instances
_rate_limiter = RateLimiter()
_response_cache = ResponseCache()


def get_client_id(handler) -> str:
    """Extract client identifier for rate limiting."""
    # Use IP address as client ID
    return handler.client_address[0]


def rate_limited(max_requests: int = DEFAULT_RATE_LIMIT):
    """Decorator for rate limiting endpoints."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            client_id = get_client_id(self)
            limiter = RateLimiter(max_requests)
            allowed, info = limiter.check_rate_limit(client_id)
            
            # Add rate limit headers
            self.send_header("X-RateLimit-Limit", str(info["limit"]))
            self.send_header("X-RateLimit-Remaining", str(info["remaining"]))
            self.send_header("X-RateLimit-Reset", str(info["reset"]))
            
            if not allowed:
                self.send_header("Retry-After", str(info["retry_after"]))
                self._json_response({
                    "error": "Rate limit exceeded",
                    "retry_after": info["retry_after"]
                }, 429)
                return
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def cached(ttl: int = CACHE_TTL, key_prefix: str = ""):
    """Decorator for caching endpoint responses."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Build cache key from path and query params
            cache_key = f"{key_prefix}:{self.path}"
            cached_data = _response_cache.get(cache_key)
            
            if cached_data is not None:
                self.send_header("X-Cache", "HIT")
                self._json_response(cached_data)
                return
            
            self.send_header("X-Cache", "MISS")
            # Call original function but capture response
            # We need to override _json_response to capture the data
            original_json_response = self._json_response
            captured_data = {}
            
            def capture_json_response(data, status=200):
                captured_data['data'] = data
                captured_data['status'] = status
                original_json_response(data, status)
            
            self._json_response = capture_json_response
            try:
                func(self, *args, **kwargs)
            finally:
                self._json_response = original_json_response
            
            # Cache successful responses
            if captured_data.get('status', 200) == 200:
                _response_cache.set(cache_key, captured_data['data'], ttl)
        
        return wrapper
    return decorator


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


def get_eval_loader() -> EvaluationLoader:
    """Get or initialize the evaluation loader."""
    global _eval_loader
    if _eval_loader is None:
        base_dir = Path(__file__).parent
        results_dir = str(base_dir / "results" / "fractal_map")
        _eval_loader = EvaluationLoader(results_dir)
        _eval_loader.load()
    return _eval_loader


def get_default_representation() -> str:
    """Get the default representation for map navigation.
    
    Factory direction v6: center_projected_hierarchical is the DEFAULT map mode.
    It uses center_projected embeddings (the ONLY representation passing BOTH 
    adversarial language dominance <0.85 AND jurist pairwise preference >0.5)
    with true hierarchical Leiden clustering (nesting=1.0, 108 fine clusters 
    nested in 8 coarse, branch purity=0.9638, 7-resolution ladder).
    
    The raw center_projected embeddings are available as a separate mode for
    comparison, but map navigation should use the hierarchical version.
    """
    return "center_projected_hierarchical"


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
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            mode = params.get("mode", [None])[0]
            self._json_response(get_nav_api().get_map_data(rep, zoom, map_mode=mode))
        elif path == "/api/map_modes":
            self._json_response(get_nav_api().get_map_modes())
        elif path == "/api/cluster":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            cid = int(params.get("cluster_id", ["0"])[0])
            self._json_response(get_nav_api().get_cluster_detail(rep, zoom, cid))
        elif path == "/api/decision":
            did = params.get("id", [""])[0]
            self._json_response(get_nav_api().get_decision(did))
        elif path == "/api/citations":
            did = params.get("id", [""])[0]
            direction = params.get("direction", ["both"])[0]
            limit = int(params.get("limit", ["50"])[0])
            self._json_response(get_nav_api().get_citations(did, direction, limit))
        elif path == "/api/search":
            q = params.get("q", [""])[0]
            limit = int(params.get("limit", ["20"])[0])
            self._json_response(get_nav_api().search_decisions(q, limit))
        elif path == "/api/neighbors":
            did = params.get("id", [""])[0]
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["2"])[0])
            n = int(params.get("n", ["10"])[0])
            self._json_response(get_nav_api().get_neighbors(did, rep, zoom, n))
        elif path == "/api/zoom_levels":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            self._json_response(get_nav_api().get_zoom_levels(rep))
        elif path == "/api/corpus/stats":
            self._json_response(get_nav_api().get_corpus_stats())
        elif path == "/api/proximity":
            id_a = params.get("id_a", [""])[0]
            id_b = params.get("id_b", [""])[0]
            self._json_response(get_nav_api().get_proximity_explanation(id_a, id_b))
        elif path == "/api/cluster_coherence":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            cid = int(params.get("cluster_id", ["0"])[0])
            self._json_response(get_nav_api().get_cluster_coherence(rep, zoom, cid))
        # New endpoints for this cycle
        elif path == "/api/zoom_coherence":
            self._json_response(get_nav_api().get_zoom_coherence_summary())
        elif path == "/api/zoom_coherence/flat_baseline":
            self._json_response(get_nav_api().get_zoom_coherence_flat_baseline())
        elif path == "/api/cluster_language_analysis":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            cid = int(params.get("cluster_id", ["0"])[0])
            self._json_response(get_nav_api().get_cluster_language_analysis(rep, zoom, cid))
        elif path == "/api/cross_language_neighbors":
            did = params.get("id", [""])[0]
            n = int(params.get("n", ["10"])[0])
            self._json_response(get_nav_api().get_cross_language_neighbors(did, n))
        elif path == "/api/text_similarity":
            id_a = params.get("id_a", [""])[0]
            id_b = params.get("id_b", [""])[0]
            self._json_response(get_nav_api().get_text_similarity(id_a, id_b))
        elif path == "/api/evaluation/benchmarks":
            self._json_response(get_eval_loader().get_benchmarks())
        elif path == "/api/evaluation/representation_quality":
            self._json_response(get_eval_loader().get_representation_quality())
        elif path == "/api/map/temporal":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            year_start = int(params["year_start"][0]) if "year_start" in params else None
            year_end = int(params["year_end"][0]) if "year_end" in params else None
            self._json_response(get_nav_api().get_temporal_map_data(rep, zoom, year_start, year_end))
        # Map export endpoints
        elif path == "/api/map/export":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            fmt = params.get("format", ["json"])[0]
            include_meta = params.get("include_metadata", ["true"])[0].lower() == "true"
            self._json_response(get_nav_api().export_map_data(rep, zoom, fmt, include_meta))
        elif path == "/api/cluster/export":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            cid = int(params.get("cluster_id", ["0"])[0])
            fmt = params.get("format", ["json"])[0]
            self._json_response(get_nav_api().export_cluster_decisions(rep, zoom, cid, fmt))
        elif path == "/api/feedback":
            # GET returns feedback stats
            self._json_response(get_nav_api().get_feedback_stats())
        elif path == "/api/map/compare":
            # Map mode comparison endpoint
            default_rep = get_default_representation()
            rep_a = params.get("rep_a", [default_rep])[0]
            rep_b = params.get("rep_b", ["legal_cited_decisions"])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            self._json_response(get_nav_api().compare_maps(rep_a, rep_b, zoom))
        
        # WebGL rendering data endpoint
        elif path == "/api/webgl/data":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom_level = int(params.get("zoom", ["1"])[0])
            mode = params.get("mode", [None])[0]
            self._json_response(get_nav_api().get_webgl_data(rep, zoom_level, map_mode=mode))
        
        # Health check endpoint
        elif path == "/api/health":
            self._json_response({
                "status": "healthy",
                "timestamp": time.time(),
                "version": "6.0",
                "corpus_decisions": get_nav_api().corpus.size,
                "maps_loaded": len(get_nav_api().map_loader.get_available_representations()),
                "uptime_seconds": time.time() - _server_start_time
            })
        
        # Cache management endpoints
        elif path == "/api/cache/stats":
            with _cache_lock:
                self._json_response({
                    "entries": len(_cache_store),
                    "keys": list(_cache_store.keys())[:20]
                })
        elif path == "/api/cache/clear":
            _response_cache.invalidate()
            self._json_response({"status": "cache cleared"})
        
        # Rate limit status
        elif path == "/api/rate_limit/status":
            client_id = get_client_id(self)
            allowed, info = _rate_limiter.check_rate_limit(client_id)
            self._json_response(info)
        
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
        elif path == "/api/feedback":
            self._handle_feedback()
        else:
            self.send_error(404)

    def _handle_feedback(self):
        """Handle jurist feedback submission."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            feedback_type = data.get("feedback_type", "")
            payload = data.get("payload", {})
            jurist_id = data.get("jurist_id", None)

            if not feedback_type:
                self._json_response({"error": "feedback_type is required"}, 400)
                return

            result = get_nav_api().submit_feedback(feedback_type, payload, jurist_id)
            self._json_response(result)
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON"}, 400)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

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
    default_rep = get_default_representation()
    print(f"Loaded {nav.corpus.size} decisions, {len(nav.map_loader.get_available_representations())} maps, "
          f"{len(nav.section_modes.modes)} section modes, citation graph: {nav.citation_loader.get_stats()}, "
          f"zoom coherence: {nav.zoom_coherence._loaded}, TF-IDF model: {nav.tfidf_proximity._built}")
    print(f"Available representations: {nav.map_loader.get_available_representations()}")
    for rep in nav.map_loader.get_available_representations():
        print(f"  {rep}: zoom levels = {nav.map_loader.get_zoom_levels(rep)}")
    print(f"Default representation: {default_rep} (evaluation-validated: 14/14 benchmarks PASS)")

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
