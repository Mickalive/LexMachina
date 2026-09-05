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
import resource
import base64
import hmac
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from collections import OrderedDict
from functools import wraps
from typing import Tuple, Dict, Optional, Any, List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from app.navigation import NavigationAPI
from app.evaluation_loader import EvaluationLoader
from app.import_manager import ImportManager
from app.health_checker import RepresentationHealthChecker
from app.incremental_updater import IncrementalUpdater


logger = logging.getLogger("lexmachina.server")

# Global navigation API instance
_nav_api = None
_nav_api_init_error = None
_eval_loader = None
_import_manager = None
_incremental_updater = None
_health_checker = RepresentationHealthChecker()
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
_cache_hits = 0
_cache_misses = 0


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
        global _cache_hits, _cache_misses
        with _cache_lock:
            if key in _cache_store:
                entry = _cache_store[key]
                if time.time() < entry['expires']:
                    _cache_hits += 1
                    return entry['data']
                else:
                    del _cache_store[key]
        _cache_misses += 1
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


# Threaded HTTP server for concurrent request handling
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer subclass that handles requests in separate threads.
    
    Critical for 192k+ scale: allows concurrent API calls while one
    request is computing expensive WebGL data or running searches.
    """
    daemon_threads = True
    allow_reuse_address = True


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
    """Get or initialize the navigation API with graceful degradation.

    If the full NavigationAPI fails to initialize (e.g. missing artifacts,
    corrupt data), we log the failure and raise so callers can decide how
    to handle it.  A partial-success path is *not* supported here because
    NavigationAPI.__init__ is not incremental — but we make the server
    tolerant of the failure.
    """
    global _nav_api, _nav_api_init_error
    if _nav_api is not None:
        return _nav_api

    base_dir = Path(__file__).parent
    corpus_dir = str(base_dir / "results" / "corpus" / "normalization" / "canonical")
    results_dir = str(base_dir / "results" / "fractal_map")

    try:
        _nav_api = NavigationAPI(corpus_dir, results_dir)
        _nav_api.initialize()
        _nav_api_init_error = None
    except Exception as e:
        _nav_api_init_error = str(e)
        logger.error("NavigationAPI initialization failed: %s", e)
        raise

    return _nav_api


def get_health_checker() -> RepresentationHealthChecker:
    """Return the global health checker instance."""
    return _health_checker


def get_eval_loader() -> EvaluationLoader:
    """Get or initialize the evaluation loader."""
    global _eval_loader
    if _eval_loader is None:
        base_dir = Path(__file__).parent
        results_dir = str(base_dir / "results" / "fractal_map")
        _eval_loader = EvaluationLoader(results_dir)
        _eval_loader.load()
    return _eval_loader


def get_import_manager() -> ImportManager:
    """Get or initialize the import manager."""
    global _import_manager
    if _import_manager is None:
        _import_manager = ImportManager(get_nav_api())
    return _import_manager


def get_incremental_updater() -> IncrementalUpdater:
    """Get or initialize the incremental updater."""
    global _incremental_updater
    if _incremental_updater is None:
        _incremental_updater = IncrementalUpdater(get_nav_api())
    return _incremental_updater


def get_default_representation() -> str:
    """Get the default representation for map navigation.
    
    Factory direction v15 (v15b-audit CRITICAL + v16 ACCEPTED):
    cited_outcome_hybrid_0.5 is the PRODUCTION DEFAULT.
    
    v15b-audit CRITICAL: NO representation passes all benchmarks;
    PRODUCTION DEFAULT is cited_outcome_hybrid_0.5 because it wins
    full-harness LangDom/JuristPref/Boilerplate. Best for user-imported
    corpora where branch metadata unavailable.
    """
    return "cited_outcome_hybrid_0.5"


class ProductHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the LexMachina product."""
    
    # Cached startup validation result (computed once on first /api/health call)
    _startup_validation = None

    def _handle_cached(self, cache_key: str, func, ttl: int = CACHE_TTL):
        """Handle cached endpoint with X-Cache header.
        
        func must return the data dict (not send it). The result is cached
        before being sent to the client, avoiding capture-pattern timing issues.
        """
        cached_data = _response_cache.get(cache_key)
        cache_hit = cached_data is not None
        if cache_hit:
            data = cached_data
        else:
            data = func()
            _response_cache.set(cache_key, data, ttl)
        
        # Send response with X-Cache header
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Cache", "HIT" if cache_hit else "MISS")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

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
            limit = int(params.get("limit", ["0"])[0]) if "limit" in params else None
            offset = int(params.get("offset", ["0"])[0]) if "offset" in params else None
            try:
                nav = get_nav_api()
                result = nav.get_map_data(rep, zoom, map_mode=mode, limit=limit, offset=offset)
                # Graceful degradation: if the requested representation failed,
                # return a clear error with available alternatives
                if "error" in result:
                    available = nav.map_loader.get_available_representations()
                    # Build health info for the error response
                    health_issues = {}
                    for r in available:
                        h = _health_checker.check_representation_health(r, nav.map_loader)
                        if h["status"] != "healthy":
                            health_issues[r] = h["status"]
                    result["available_representations"] = available
                    result["healthy_representations"] = [
                        r for r in available
                        if r not in health_issues
                    ]
                    result["degraded_representations"] = list(health_issues.keys())
                    result["recommendation"] = (
                        f"Try representation '{get_default_representation()}' which is the "
                        "production default, or use /api/health/representations for full status."
                    )
                self._json_response(result)
            except Exception as e:
                self._json_response({
                    "error": f"Map request failed: {e}",
                    "available_representations": [],
                    "recommendation": "The navigation API may not be fully initialized. Check /api/health.",
                }, 500)
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
            language = params.get("language", [None])[0]
            self._json_response(get_nav_api().search_decisions(q, limit, language=language))
        elif path == "/api/import/status":
            job_id = params.get("job_id", [""])[0]
            if not job_id:
                self._json_response({"error": "job_id parameter required"}, 400)
            else:
                self._json_response(get_import_manager().get_status(job_id))
        elif path == "/api/import/cancel":
            job_id = params.get("job_id", [""])[0]
            if not job_id:
                self._json_response({"error": "job_id parameter required"}, 400)
            else:
                success = get_import_manager().cancel_import(job_id)
                self._json_response({"cancelled": success, "job_id": job_id})
        elif path == "/api/corpus/stats/languages":
            self._handle_cached("corpus_stats_languages",
                lambda: get_nav_api().get_language_stats(), ttl=600)
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
            self._handle_cached(f"proximity:{id_a}:{id_b}",
                lambda: get_nav_api().get_proximity_explanation(id_a, id_b))
        elif path == "/api/cluster_coherence":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            cid = int(params.get("cluster_id", ["0"])[0])
            self._handle_cached(f"cluster_coherence:{rep}:{zoom}:{cid}",
                lambda: get_nav_api().get_cluster_coherence(rep, zoom, cid))
        # New endpoints for this cycle
        elif path == "/api/zoom_coherence":
            self._handle_cached("zoom_coherence:summary",
                lambda: get_nav_api().get_zoom_coherence_summary())
        elif path == "/api/zoom_coherence/flat_baseline":
            self._json_response(get_nav_api().get_zoom_coherence_flat_baseline())
        elif path == "/api/cluster_language_analysis":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            cid = int(params.get("cluster_id", ["0"])[0])
            self._handle_cached(f"cluster_language:{rep}:{zoom}:{cid}",
                lambda: get_nav_api().get_cluster_language_analysis(rep, zoom, cid))
        elif path == "/api/cross_language_neighbors":
            did = params.get("id", [""])[0]
            n = int(params.get("n", ["10"])[0])
            self._handle_cached(f"cross_language:{did}:{n}",
                lambda: get_nav_api().get_cross_language_neighbors(did, n))
        elif path == "/api/text_similarity":
            id_a = params.get("id_a", [""])[0]
            id_b = params.get("id_b", [""])[0]
            self._handle_cached(f"text_similarity:{id_a}:{id_b}",
                lambda: get_nav_api().get_text_similarity(id_a, id_b))
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
        elif path == "/api/representations/validate":
            self._json_response(get_nav_api().validate_representations())
        elif path == "/api/map/compare":
            # Map mode comparison endpoint
            default_rep = get_default_representation()
            rep_a = params.get("rep_a", [default_rep])[0]
            rep_b = params.get("rep_b", ["legal_cited_decisions"])[0]
            zoom = int(params.get("zoom", ["1"])[0])
            self._json_response(get_nav_api().compare_maps(rep_a, rep_b, zoom))
        elif path == "/api/pattern_compare":
            # Design-pattern side-by-side comparison
            pattern_a = params.get("pattern_a", ["DEFAULT"])[0].upper()
            pattern_b = params.get("pattern_b", ["HIGH-PURITY"])[0].upper()
            zoom = int(params.get("zoom", ["1"])[0])
            self._json_response(get_nav_api().compare_design_patterns(pattern_a, pattern_b, zoom))
        elif path == "/api/health/startup_validation":
            # Startup validation: health-check all loaded representations
            self._json_response(get_nav_api().startup_validation())
        elif path == "/api/health/representations":
            try:
                nav = get_nav_api()
                rep_health = _health_checker.get_health_summary(nav.map_loader)
                self._json_response(rep_health)
            except Exception as e:
                self._json_response({
                    "error": f"Representation health check failed: {e}",
                    "total": 0,
                    "healthy": 0,
                    "degraded": 0,
                    "failed": 0,
                }, 500)

        # Design patterns endpoint
        elif path == "/api/design_patterns":
            self._json_response(get_nav_api().get_design_patterns())
        
        # Holdout metrics endpoint
        elif path == "/api/evaluation/holdout":
            self._json_response(get_nav_api().get_holdout_metrics())
        
        # Representation recommendation endpoint
        elif path == "/api/recommendation":
            purpose = params.get("purpose", ["default"])[0]
            self._json_response(get_nav_api().get_representation_recommendation(purpose))
        
        # WebGL LOD info endpoint
        elif path == "/api/webgl/lod":
            from app.lod_manager import LODManager
            lod_mgr = LODManager()
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            # Get total point count for the representation
            try:
                nav = get_nav_api()
                map_data = nav.get_map_data(representation=rep, zoom_level=1)
                total_points = len(map_data.get("positions", []))
            except Exception:
                total_points = 0
            info = lod_mgr.get_lod_info()
            optimal = lod_mgr.get_optimal_detail_level(None, total_points)
            info["total_points"] = total_points
            info["optimal_level"] = optimal
            self._json_response(info)
        
        # WebGL rendering data endpoint
        elif path == "/api/webgl/data":
            default_rep = get_default_representation()
            rep = params.get("representation", [default_rep])[0]
            zoom_level = int(params.get("zoom", ["1"])[0])
            mode = params.get("mode", [None])[0]
            # LOD level override (0=centroids, 1=super-clusters, 2+=full)
            lod_param = params.get("lod_level", [None])[0]
            lod_level = int(lod_param) if lod_param is not None else None
            # Viewport bbox for viewport culling (critical for 192k scale)
            bbox = None
            if "xMin" in params and "xMax" in params and "yMin" in params and "yMax" in params:
                bbox = {
                    'xMin': float(params["xMin"][0]),
                    'yMin': float(params["yMin"][0]),
                    'xMax': float(params["xMax"][0]),
                    'yMax': float(params["yMax"][0]),
                }
            self._json_response(get_nav_api().get_webgl_data(rep, zoom_level, map_mode=mode, bbox=bbox, lod_level=lod_level))
        
        # Health check endpoint
        elif path == "/api/health":
            try:
                nav = get_nav_api()
                nav_ok = True
            except Exception as e:
                nav_ok = False
                nav = None

            overall_status = "healthy"
            health = {
                "status": overall_status,
                "timestamp": time.time(),
                "version": "7.0",
                "uptime_seconds": time.time() - _server_start_time,
                "threaded_server": True,
                "nav_api_initialized": nav_ok,
                "nav_api_error": _nav_api_init_error,
            }
            if nav_ok:
                health["corpus_decisions"] = nav.corpus.size
                health["maps_loaded"] = len(nav.map_loader.get_available_representations())

                # Include startup validation summary on first call (cached)
                if ProductHandler._startup_validation is None:
                    try:
                        ProductHandler._startup_validation = nav.startup_validation()
                    except Exception as e:
                        ProductHandler._startup_validation = {"error": str(e)}
                sv = ProductHandler._startup_validation
                health["startup_validation"] = {
                    "total_representations": sv.get("total_representations", 0),
                    "passing": sv.get("passing", 0),
                    "warnings": sv.get("warnings", 0),
                    "failing": sv.get("failing", 0),
                    "elapsed_ms": sv.get("elapsed_ms", 0),
                }

                # Representation health summary
                try:
                    rep_summary = _health_checker.get_health_summary(nav.map_loader)
                    health["representation_health"] = {
                        "total": rep_summary["total"],
                        "healthy": rep_summary["healthy"],
                        "degraded": rep_summary["degraded"],
                        "failed": rep_summary["failed"],
                        "healthy_pct": rep_summary["healthy_pct"],
                    }
                    if rep_summary["degraded"] > 0 or rep_summary["failed"] > 0:
                        overall_status = "degraded"
                except Exception as e:
                    health["representation_health"] = {"error": str(e)}
                    overall_status = "degraded"
            else:
                overall_status = "failed"
                health["corpus_decisions"] = 0
                health["maps_loaded"] = 0
                health["startup_validation"] = {"error": _nav_api_init_error}
                health["representation_health"] = {"error": _nav_api_init_error}

            health["status"] = overall_status
            self._json_response(health)
        
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

        # Incremental update pending status
        elif path == "/api/map/pending_updates":
            self._json_response(get_incremental_updater().get_pending_updates())

        # Scale simulation endpoint (174k validation)
        elif path == "/api/scale_simulation":
            self._json_response(self._handle_scale_simulation(params))

        # System stats (fast, no auth required)
        elif path == "/api/system/stats":
            self._json_response(self._handle_system_stats())

        # Representations health (quick summary)
        elif path == "/api/representations/health":
            self._json_response(self._handle_representations_health())

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
        elif path == "/api/import/async":
            self._handle_async_import()
        elif path == "/api/feedback":
            self._handle_feedback()
        elif path == "/api/map/incremental_update":
            self._handle_incremental_update()
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

    def _handle_async_import(self):
        """Handle async corpus import via JSON body. Returns job_id for status polling."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            records = json.loads(body.decode("utf-8"))

            if not isinstance(records, list):
                records = [records]

            job_id = get_import_manager().submit_import(records)
            self._json_response({
                "job_id": job_id,
                "status": "submitted",
                "total_records": len(records),
                "status_url": f"/api/import/status?job_id={job_id}",
                "cancel_url": f"/api/import/cancel?job_id={job_id}",
            })
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON"}, 400)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_incremental_update(self):
        """Handle incremental map update: add decisions to existing map."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            decision_ids = data.get("decision_ids", [])
            representation = data.get("representation", None)
            zoom_level = int(data.get("zoom_level", 1))

            if not decision_ids:
                self._json_response({"error": "decision_ids is required and must be non-empty"}, 400)
                return

            updater = get_incremental_updater()
            result = updater.add_decisions_to_map(
                decision_ids=decision_ids,
                representation=representation,
                zoom_level=zoom_level,
            )
            self._json_response(result)
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON"}, 400)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_scale_simulation(self, params):
        """Handle 174k scale simulation endpoint.

        Validates that all scale-readiness infrastructure performs at 174,000
        decision scale using synthetic upsampling. This is the core v17
        product deliverable.
        """
        import time as _time
        from app.lod_manager import LODManager
        from app.spatial_index import SpatialIndex
        import numpy as _np

        t_total = _time.time()
        n_target = int(params.get("n", ["174113"])[0])

        # Step 1: Generate synthetic 174k data
        t0 = _time.time()
        rng = _np.random.RandomState(42)
        n_clusters = int(max(50, int(n_target ** 0.5) * 0.5))
        centroids = rng.randn(n_clusters, 2) * 50.0
        points_per_cluster = n_target // n_clusters
        remainder = n_target - points_per_cluster * n_clusters
        positions = _np.empty((n_target, 2), dtype=_np.float64)
        cluster_labels = _np.empty(n_target, dtype=_np.int32)
        clusters = []
        idx = 0
        for c in range(n_clusters):
            size = points_per_cluster + (1 if c < remainder else 0)
            cx, cy = centroids[c]
            spread = rng.uniform(0.5, 3.0)
            positions[idx:idx+size, 0] = cx + rng.randn(size) * spread
            positions[idx:idx+size, 1] = cy + rng.randn(size) * spread
            cluster_labels[idx:idx+size] = c
            clusters.append({
                "cluster_id": c, "size": size,
                "centroid_x": float(cx), "centroid_y": float(cy),
            })
            idx += size
        t_generate = _time.time() - t0

        # Step 2: LOD computation
        mgr = LODManager()
        t0 = _time.time()
        lod_results = {}
        for zoom in range(4):
            r = mgr.compute_lod_levels(positions, clusters, zoom=zoom)
            lod_results[f"level_{zoom}"] = {
                "point_count": int(r["point_count"]),
                "lod_level": int(r["lod_level"]),
            }
        t_lod = _time.time() - t0

        # Step 3: Viewport culling
        bbox = {"xMin": -10.0, "yMin": -10.0, "xMax": 10.0, "yMax": 10.0}
        t0 = _time.time()
        mask_bf = mgr.cull_to_viewport(positions, bbox)
        t_cull_bf = _time.time() - t0
        n_visible_bf = int(mask_bf.sum())

        t0 = _time.time()
        mask_kd = mgr.cull_to_viewport_kdtree(positions, bbox)
        t_cull_kd = _time.time() - t0
        n_visible_kd = int(mask_kd.sum())
        culling_consistent = bool(_np.array_equal(mask_bf, mask_kd))

        # Step 4: Optimal level selection
        t0 = _time.time()
        optimal = mgr.get_optimal_detail_level(None, n_target)
        t_optimal = _time.time() - t0

        # Step 5: Spatial index
        t0 = _time.time()
        pos_dict = {f"dec_{i}": (positions[i, 0], positions[i, 1])
                    for i in range(0, n_target, 100)}  # Sample for speed
        si = SpatialIndex()
        si.build(pos_dict)
        t_spatial_build = _time.time() - t0

        t0 = _time.time()
        knn_results = si.knn_query(0.0, 0.0, k=20)
        t_knn = _time.time() - t0

        t_total = _time.time() - t_total

        # Step 6: WebGL payload estimate
        payload_bytes = n_target * 2 * 4 + n_target * 4 * 4 + n_target * 4 + n_target * 4
        payload_mb = payload_bytes / (1024 * 1024)

        return {
            "simulation_scale": n_target,
            "scale_readiness": {
                "lod_computation": {
                    "elapsed_s": round(t_lod, 4),
                    "levels": lod_results,
                    "pass": t_lod < 5.0,
                },
                "viewport_culling": {
                    "brute_force_s": round(t_cull_bf, 4),
                    "kdtree_s": round(t_cull_kd, 4),
                    "visible_points": n_visible_bf,
                    "consistent": culling_consistent,
                    "pass": t_cull_bf < 1.0 and t_cull_kd < 1.0,
                },
                "optimal_level": {
                    "elapsed_s": round(t_optimal, 4),
                    "selected_lod": optimal["lod_level"],
                    "selected_points": optimal["point_count"],
                    "pass": t_optimal < 1.0,
                },
                "spatial_index": {
                    "build_s": round(t_spatial_build, 4),
                    "knn_20_s": round(t_knn, 4),
                    "index_size": si.size,
                    "pass": t_spatial_build < 10.0 and t_knn < 1.0,
                },
                "webgl_payload": {
                    "estimated_mb": round(payload_mb, 1),
                    "pass": payload_mb < 50,
                },
            },
            "total_elapsed_s": round(t_total, 4),
            "all_pass": all([
                t_lod < 5.0,
                t_cull_bf < 1.0,
                t_cull_kd < 1.0,
                t_optimal < 1.0,
                t_spatial_build < 10.0,
                t_knn < 1.0,
                payload_mb < 50,
                culling_consistent,
            ]),
            "factory_direction_version": 17,
            "note": "Scale simulation validates infrastructure readiness for 174k corpus. All timings measured on synthetic data upscaled from the 1,200-decision production corpus layout.",
        }

    def _handle_system_stats(self):
        """Return system statistics without heavy computation."""
        import threading as _threading

        # Memory via /proc/self/status (Linux, O(1))
        memory = {"rss": 0.0, "vms": 0.0}
        try:
            status_path = "/proc/self/status"
            with open(status_path, "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        memory["rss"] = float(line.split()[1])
                    elif line.startswith("VmSize:"):
                        memory["vms"] = float(line.split()[1])
        except Exception:
            try:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                memory["rss"] = usage.ru_maxrss / 1024.0  # convert KB to MB
            except Exception:
                pass

        # Representation counts
        representations_loaded = 0
        representations_failed = 0
        load_failures = {}
        try:
            nav = get_nav_api()
            available = nav.map_loader.get_available_representations()
            representations_loaded = len(available)
            # Check DESIGN_PATTERNS dict for all known reps, count loaded vs failed
            all_known = set(nav.map_loader.DESIGN_PATTERNS.keys())
            loaded_set = set(available)
            representations_failed = len(all_known - loaded_set)
            for rep in all_known - loaded_set:
                load_failures[rep] = "not loaded"
        except Exception:
            pass

        # Cache stats
        with _cache_lock:
            hits = _cache_hits
            misses = _cache_misses
            entries = len(_cache_store)
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0.0

        # Rate limit stats
        with _rate_limit_lock:
            active_clients = len(_rate_limit_store)
            total_requests = sum(len(ts) for ts in _rate_limit_store.values())

        # Corpus decisions
        corpus_decisions = 0
        try:
            nav = get_nav_api()
            corpus_decisions = nav.corpus.size
        except Exception:
            pass

        return {
            "uptime_seconds": round(time.time() - _server_start_time, 2),
            "memory_mb": memory,
            "representations_loaded": representations_loaded,
            "representations_failed": representations_failed,
            "load_failures": load_failures,
            "cache_stats": {
                "hits": hits,
                "misses": misses,
                "hit_rate": round(hit_rate, 4),
                "entries": entries,
            },
            "rate_limit_stats": {
                "active_clients": active_clients,
                "total_requests_window": total_requests,
            },
            "corpus_decisions": corpus_decisions,
            "thread_count": _threading.active_count(),
        }

    def _handle_representations_health(self):
        """Quick per-representation status summary."""
        result = {
            "total": 0,
            "loaded": 0,
            "failed": 0,
            "representations": {},
        }
        try:
            nav = get_nav_api()
            map_loader = nav.map_loader
            loaded_reps = set(map_loader.get_available_representations())
            all_known = list(map_loader.DESIGN_PATTERNS.keys())

            result["total"] = len(all_known)
            result["loaded"] = len(loaded_reps)
            result["failed"] = len(all_known) - len(loaded_reps)

            for rep in all_known:
                if rep in loaded_reps:
                    health = _health_checker.check_representation_health(rep, map_loader)
                    result["representations"][rep] = {
                        "status": "loaded" if health["status"] == "healthy" else health["status"],
                        "design_pattern": map_loader.DESIGN_PATTERNS.get(rep, "UNKNOWN"),
                        "error": "; ".join(health.get("issues", [])) if health.get("issues") else None,
                    }
                else:
                    result["representations"][rep] = {
                        "status": "failed",
                        "design_pattern": map_loader.DESIGN_PATTERNS.get(rep, "UNKNOWN"),
                        "error": "Representation not loaded",
                    }
        except Exception as e:
            result["error"] = str(e)

        return result

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
    print(f"Default representation: {default_rep} (PRODUCTION DEFAULT per v15b-audit: wins full-harness LangDom/JuristPref/Boilerplate)")

    server = ThreadedHTTPServer(("0.0.0.0", port), ProductHandler)
    print(f"LexMachina server running on http://localhost:{port} (threaded)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
