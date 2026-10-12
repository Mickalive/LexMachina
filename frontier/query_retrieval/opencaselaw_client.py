"""
OpenCaseLaw API Client
Production-ready client with rate limiting, caching, and error handling.
"""
import json
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from urllib.parse import urlencode, urljoin
from collections import OrderedDict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    max_requests_per_second: float = 5.0
    max_concurrent: int = 3
    burst_allowance: int = 10


@dataclass
class CacheConfig:
    """Cache configuration."""
    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour default
    max_entries: int = 10000
    cache_dir: Optional[Path] = None


class TokenBucketRateLimiter:
    """Token bucket rate limiter for OpenCaseLaw API (max 5 req/s)."""
    
    def __init__(self, rate: float = 5.0, burst: int = 10):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, blocking until available. Returns wait time."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Need to wait
            needed = tokens - self.tokens
            wait_time = needed / self.rate
            self.tokens = 0
            return wait_time


class ResponseCache:
    """Persistent response cache with TTL and LRU eviction."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._memory_cache: OrderedDict[str, tuple] = OrderedDict()  # key -> (data, expires_at)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        
        if config.cache_dir:
            config.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _make_key(self, method: str, url: str, params: Optional[Dict] = None, 
                  json_body: Optional[Dict] = None) -> str:
        """Generate cache key from request."""
        parts = [method, url]
        if params:
            parts.append(urlencode(sorted(params.items())))
        if json_body:
            parts.append(json.dumps(json_body, sort_keys=True))
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]
    
    def get(self, method: str, url: str, params: Optional[Dict] = None,
            json_body: Optional[Dict] = None) -> Optional[Any]:
        """Get cached response if valid."""
        if not self.config.enabled:
            return None
            
        key = self._make_key(method, url, params, json_body)
        
        with self._lock:
            if key in self._memory_cache:
                data, expires_at = self._memory_cache[key]
                if time.time() < expires_at:
                    self._hits += 1
                    # Move to end (LRU)
                    self._memory_cache.move_to_end(key)
                    return data
                else:
                    del self._memory_cache[key]
            
            self._misses += 1
            return None
    
    def set(self, method: str, url: str, data: Any, params: Optional[Dict] = None,
            json_body: Optional[Dict] = None, ttl: Optional[int] = None) -> None:
        """Cache response."""
        if not self.config.enabled:
            return
            
        key = self._make_key(method, url, params, json_body)
        ttl = ttl or self.config.ttl_seconds
        expires_at = time.time() + ttl
        
        with self._lock:
            # Evict if at capacity
            if len(self._memory_cache) >= self.config.max_entries:
                self._memory_cache.popitem(last=False)
            
            self._memory_cache[key] = (data, expires_at)
    
    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self._memory_cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "entries": len(self._memory_cache),
            }


class OpenCaseLawClient:
    """
    Production-ready OpenCaseLaw API client.
    
    Features:
    - Rate limiting (5 req/s soft limit)
    - Response caching with TTL
    - Automatic retry with exponential backoff
    - Request/response logging
    - Offline mode with cached fixtures
    """
    
    BASE_URL = "https://mcp.opencaselaw.ch/api/"
    
    def __init__(
        self,
        rate_limit: Optional[RateLimitConfig] = None,
        cache_config: Optional[CacheConfig] = None,
        timeout: float = 30.0,
        offline_mode: bool = False,
        fixture_dir: Optional[Path] = None,
    ):
        self.rate_limit = rate_limit or RateLimitConfig()
        self.cache_config = cache_config or CacheConfig()
        self.timeout = timeout
        self.offline_mode = offline_mode
        self.fixture_dir = fixture_dir or Path("/tmp/lexmachina_fixtures")
        
        # Rate limiter
        self._rate_limiter = TokenBucketRateLimiter(
            rate=self.rate_limit.max_requests_per_second,
            burst=self.rate_limit.burst_allowance
        )
        
        # Cache
        self._cache = ResponseCache(self.cache_config)
        
        # Session with retry strategy
        self._session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        
        # Semaphore for concurrent request limiting
        self._semaphore = threading.Semaphore(self.rate_limit.max_concurrent)
        
        # Stats
        self._request_count = 0
        self._error_count = 0
        self._lock = threading.Lock()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP request with rate limiting, caching, and error handling."""
        url = urljoin(self.BASE_URL, endpoint.lstrip("/"))
        
        # Check cache first
        if use_cache and method == "GET":
            cached = self._cache.get(method, url, params, json_body)
            if cached is not None:
                logger.debug(f"Cache HIT: {method} {url}")
                return cached
        
        # Offline mode - try to load from fixtures
        if self.offline_mode:
            fixture = self._load_fixture(method, endpoint, params, json_body)
            if fixture is not None:
                return fixture
            raise RuntimeError(f"Offline mode: no fixture for {method} {endpoint}")
        
        # Rate limit
        wait_time = self._rate_limiter.acquire()
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        # Execute request with concurrency control
        with self._semaphore:
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    timeout=self.timeout,
                    headers={"Accept": "application/json", "User-Agent": "LexMachina/1.0"}
                )
                response.raise_for_status()
                data = response.json()
                
                # Cache successful GET responses
                if use_cache and method == "GET":
                    self._cache.set(method, url, data, params, json_body, cache_ttl)
                
                with self._lock:
                    self._request_count += 1
                
                logger.debug(f"Request OK: {method} {url} -> {len(str(data))} chars")
                return data
                
            except requests.exceptions.RequestException as e:
                with self._lock:
                    self._error_count += 1
                logger.error(f"Request failed: {method} {url} - {e}")
                raise
    
    def _load_fixture(self, method: str, endpoint: str, params: Optional[Dict],
                      json_body: Optional[Dict]) -> Optional[Dict]:
        """Load response from fixture file."""
        # First try exact match
        key = self._cache._make_key(method, endpoint, params, json_body)
        fixture_path = self.fixture_dir / f"{key}.json"
        if fixture_path.exists():
            with open(fixture_path, "r") as f:
                return json.load(f)
        
        # For search endpoints in offline mode, try to find a fixture with same query/language
        # but different pagination params
        if method == "GET" and endpoint == "/decisions" and params and "q" in params:
            # Include language and other filters but exclude pagination
            base_params = {k: v for k, v in params.items() if k not in ("offset", "limit")}
            base_key = self._cache._make_key(method, endpoint, base_params, json_body)
            base_fixture_path = self.fixture_dir / f"{base_key}.json"
            if base_fixture_path.exists():
                with open(base_fixture_path, "r") as f:
                    data = json.load(f)
                    # Apply pagination to the fixture data
                    offset = params.get("offset", 0)
                    limit = params.get("limit", 50)
                    if "results" in data:
                        data = dict(data)  # Copy to avoid modifying cached fixture
                        data["results"] = data["results"][offset:offset + limit]
                        data["offset"] = offset
                        data["limit"] = limit
                        data["returned"] = len(data["results"])
                        data["has_more"] = offset + limit < data.get("total", 0)
                        if data["has_more"]:
                            data["next_offset"] = offset + limit
                    return data
        
        return None
    
    def save_fixture(self, method: str, endpoint: str, data: Dict,
                     params: Optional[Dict] = None, json_body: Optional[Dict] = None) -> None:
        """Save response as fixture for offline testing."""
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        key = self._cache._make_key(method, endpoint, params, json_body)
        fixture_path = self.fixture_dir / f"{key}.json"
        with open(fixture_path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ===== Search endpoints =====
    
    def search_decisions(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        language: Optional[str] = None,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        legal_area: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Search decisions via OpenCaseLaw.
        
        Args:
            query: Search query string
            limit: Max results per page (max 100)
            offset: Pagination offset
            language: Filter by language (de, fr, it)
            court: Filter by court code
            date_from: Filter decisions from date (YYYY-MM-DD)
            date_to: Filter decisions to date (YYYY-MM-DD)
            legal_area: Filter by legal area
            use_cache: Whether to use cache
        
        Returns:
            Dict with keys: total, total_is_lower_bound, returned, results, limit, offset, has_more, next_offset, result_set_id
        """
        params = {"q": query, "limit": min(limit, 100), "offset": offset}
        if language:
            params["language"] = language
        if court:
            params["court"] = court
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if legal_area:
            params["legal_area"] = legal_area
        
        return self._request("GET", "/decisions", params=params, use_cache=use_cache)
    
    def search_decisions_paginated(
        self,
        query: str,
        target_count: int = 100,
        language: Optional[str] = None,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        legal_area: Optional[str] = None,
        use_cache: bool = True,
        max_pages: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search decisions with automatic pagination to reach target_count.
        
        Returns:
            List of decision result dicts (merged across pages)
        """
        all_results = []
        offset = 0
        page_size = 50
        pages_fetched = 0
        
        while len(all_results) < target_count and pages_fetched < max_pages:
            remaining = target_count - len(all_results)
            current_limit = min(page_size, remaining)
            
            response = self.search_decisions(
                query=query,
                limit=current_limit,
                offset=offset,
                language=language,
                court=court,
                date_from=date_from,
                date_to=date_to,
                legal_area=legal_area,
                use_cache=use_cache,
            )
            
            results = response.get("results", [])
            if not results:
                break
            
            all_results.extend(results)
            pages_fetched += 1
            
            if not response.get("has_more", False):
                break
            
            offset = response.get("next_offset", offset + len(results))
        
        return all_results[:target_count]
    
    def lookup_case_number(
        self,
        case_number: str,
        limit: int = 8,
        exact: bool = False,
    ) -> Dict[str, Any]:
        """Instant case number lookup."""
        params = {"q": case_number, "limit": limit, "exact": str(exact).lower()}
        return self._request("GET", "/lookup", params=params)
    
    # ===== Decision detail endpoints =====
    
    def get_decision(self, decision_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get full decision by ID."""
        return self._request("GET", f"/decisions/{decision_id}", use_cache=use_cache)
    
    def get_decision_structure(self, decision_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get decision structure (regeste, sachverhalt, erwaegungen paragraphs)."""
        return self._request("GET", f"/structure/{decision_id}", use_cache=use_cache)
    
    def get_erwaegung(self, decision_id: str, e_number: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get full text of a specific Erwägung paragraph."""
        return self._request("GET", f"/erwaegung/{decision_id}/{e_number}", use_cache=use_cache)
    
    def get_regeste(self, decision_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get the official Regeste (court-formulated legal summary)."""
        return self._request("GET", f"/regeste/{decision_id}", use_cache=use_cache)
    
    def get_citations(
        self,
        decision_id: str,
        direction: str = "both",
        limit: int = 50,
        offset: int = 0,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get citation graph for a decision.
        
        Args:
            decision_id: Decision ID
            direction: "outgoing", "incoming", or "both"
            limit: Max results per direction
            offset: Pagination offset
            use_cache: Whether to use cache
        
        Returns:
            Dict with outgoing/incoming citation lists and totals
        """
        params = {"direction": direction, "limit": limit, "offset": offset}
        return self._request("GET", f"/citations/{decision_id}", params=params, use_cache=use_cache)
    
    def get_appeal_chain(self, decision_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get appeal chain (procedural history) for a decision."""
        return self._request("GET", f"/appeal-chain/{decision_id}", use_cache=use_cache)
    
    def get_integrity(self, decision_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get integrity/checksum info for a decision."""
        return self._request("GET", f"/integrity/{decision_id}", use_cache=use_cache)
    
    def get_relevant_erwaegung(self, decision_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get relevant Erwägung paragraphs for a decision."""
        return self._request("GET", f"/relevant-erwaegung/{decision_id}", use_cache=use_cache)
    
    # ===== Export endpoints =====
    
    def export_decision(self, decision_id: str, format: str = "json") -> Dict[str, Any]:
        """Export decision in various formats."""
        if format == "json":
            return self.get_decision(decision_id)
        endpoint = f"/decisions/{decision_id}/export.{format}"
        return self._request("GET", endpoint, use_cache=False)
    
    # ===== Stats =====
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        with self._lock:
            return {
                "request_count": self._request_count,
                "error_count": self._error_count,
                "cache": self._cache.stats(),
                "rate_limiter_tokens": self._rate_limiter.tokens,
            }
    
    def clear_cache(self) -> None:
        """Clear response cache."""
        self._cache.clear()


# Convenience function for quick setup
def create_client(
    offline: bool = False,
    cache_ttl: int = 3600,
    rate_limit: float = 5.0,
) -> OpenCaseLawClient:
    """Create a configured OpenCaseLaw client."""
    return OpenCaseLawClient(
        rate_limit=RateLimitConfig(max_requests_per_second=rate_limit),
        cache_config=CacheConfig(enabled=True, ttl_seconds=cache_ttl),
        offline_mode=offline,
    )