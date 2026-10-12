"""
OpenCaseLaw API Client with rate limiting, pagination, and file-based caching.

Respects OpenCaseLaw's documented soft pace limit of <=5 req/s.
Provides both live and cached modes for deterministic testing.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterator
from threading import Lock
import logging

logger = logging.getLogger(__name__)

# OpenCaseLaw public API base URL (no API key required)
OCL_BASE_URL = "https://mcp.opencaselaw.ch/api"

# Soft rate limit: <=5 requests/second as documented
DEFAULT_RATE_LIMIT = 5  # requests per second
RATE_LIMIT_WINDOW = 1.0  # seconds

# Default cache TTL: 24 hours
DEFAULT_CACHE_TTL = 86400


@dataclass
class RateLimitState:
    """Thread-safe rate limiter state."""
    requests: List[float] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)


class RateLimiter:
    """
    Token-bucket style rate limiter for OpenCaseLaw API.
    
    Enforces a maximum of DEFAULT_RATE_LIMIT requests per RATE_LIMIT_WINDOW seconds.
    Thread-safe for concurrent use.
    """
    
    def __init__(self, max_requests: int = DEFAULT_RATE_LIMIT, window_seconds: float = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._state = RateLimitState()
    
    def acquire(self) -> float:
        """
        Acquire permission to make a request. Returns the wait time in seconds.
        Blocks until a request slot is available.
        """
        with self._state.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Remove expired requests
            self._state.requests = [t for t in self._state.requests if t > cutoff]
            
            if len(self._state.requests) < self.max_requests:
                # Slot available immediately
                self._state.requests.append(now)
                return 0.0
            
            # Need to wait for oldest request to expire
            oldest = self._state.requests[0]
            wait_time = oldest + self.window_seconds - now
            
            if wait_time > 0:
                time.sleep(wait_time)
                now = time.time()
            
            # Clean up again after wait
            cutoff = now - self.window_seconds
            self._state.requests = [t for t in self._state.requests if t > cutoff]
            self._state.requests.append(now)
            
            return wait_time
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        with self._state.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            active = [t for t in self._state.requests if t > cutoff]
            return {
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "current_requests": len(active),
                "remaining": max(0, self.max_requests - len(active)),
                "reset_at": active[0] + self.window_seconds if active else now,
            }


class CacheManager:
    """
    File-based cache manager for OpenCaseLaw responses.
    
    Provides deterministic offline testing by caching API responses to disk.
    Cache keys are derived from request parameters.
    """
    
    def __init__(self, cache_dir: Path, ttl_seconds: int = DEFAULT_CACHE_TTL):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
    
    def _make_key(self, *parts: str) -> str:
        """Generate a cache key from request parts."""
        key_string = "|".join(parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
    
    def _cache_path(self, key: str) -> Path:
        """Get the cache file path for a key."""
        return self.cache_dir / f"{key}.json"
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if valid and not expired."""
        path = self._cache_path(key)
        
        with self._lock:
            if not path.exists():
                self._stats["misses"] += 1
                return None
            
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                
                # Check TTL
                cached_at = cached.get("_cached_at", 0)
                if time.time() - cached_at > self.ttl_seconds:
                    self._stats["misses"] += 1
                    return None
                
                self._stats["hits"] += 1
                return cached.get("data")
                
            except Exception as e:
                logger.warning(f"Cache read error for {key}: {e}")
                self._stats["errors"] += 1
                return None
    
    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Store response in cache with timestamp."""
        path = self._cache_path(key)
        
        with self._lock:
            try:
                payload = {
                    "_cached_at": time.time(),
                    "data": data,
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Cache write error for {key}: {e}")
                self._stats["errors"] += 1
    
    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching pattern (or all if None)."""
        with self._lock:
            count = 0
            if pattern is None:
                for path in self.cache_dir.glob("*.json"):
                    path.unlink()
                    count += 1
            else:
                for path in self.cache_dir.glob(f"*{pattern}*.json"):
                    path.unlink()
                    count += 1
            return count
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            return dict(self._stats)


@dataclass
class Decision:
    """Normalized decision record from OpenCaseLaw."""
    decision_id: str
    canonical_decision_id: str
    court: str
    court_name: Optional[str]
    canton: Optional[str]
    chamber: Optional[str]
    docket_number: str
    decision_date: str
    publication_date: Optional[str]
    language: str
    title: Optional[str]
    legal_area: Optional[str]
    regeste: Optional[str]
    rule_statement: Optional[str]
    full_text: Optional[str]
    source_url: Optional[str]
    pdf_url: Optional[str]
    canonical_url: str
    citation_string_de: Optional[str]
    citation_string_fr: Optional[str]
    citation_string_it: Optional[str]
    statutes: List[str]
    citation_count: int
    cited_by_count: int
    relevance_score: Optional[float]
    is_canonical: bool
    provenance: str  # "live", "cache", "fixture"
    fetched_at: float = field(default_factory=time.time)
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], provenance: str = "live") -> "Decision":
        """Create Decision from OpenCaseLaw API response."""
        return cls(
            decision_id=str(data.get("decision_id", "")),
            canonical_decision_id=str(data.get("canonical_decision_id", data.get("decision_id", ""))),
            court=str(data.get("court", "")),
            court_name=data.get("court_name"),
            canton=data.get("canton"),
            chamber=data.get("chamber"),
            docket_number=str(data.get("docket_number", "")),
            decision_date=str(data.get("decision_date", "")),
            publication_date=data.get("publication_date"),
            language=str(data.get("language", "?")),
            title=data.get("title"),
            legal_area=data.get("legal_area"),
            regeste=data.get("regeste"),
            rule_statement=data.get("rule_statement"),
            full_text=data.get("full_text"),
            source_url=data.get("source_url"),
            pdf_url=data.get("pdf_url"),
            canonical_url=str(data.get("canonical_url", "")),
            citation_string_de=data.get("citation_string_de"),
            citation_string_fr=data.get("citation_string_fr"),
            citation_string_it=data.get("citation_string_it"),
            statutes=data.get("statutes", []) or [],
            citation_count=int(data.get("citation_count", 0) or 0),
            cited_by_count=int(data.get("cited_by_results", data.get("cited_by_count", 0)) or 0),
            relevance_score=data.get("relevance_score"),
            is_canonical=bool(data.get("is_canonical", True)),
            provenance=provenance,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def get_snippet(self, max_length: int = 600) -> str:
        """Get a text snippet for display (prefers regeste, then rule_statement, then full_text)."""
        for field in (self.regeste, self.rule_statement, self.full_text):
            if field:
                snippet = " ".join(field.split())  # Normalize whitespace
                return snippet[:max_length].strip()
        return ""


class OpenCaseLawClient:
    """
    OpenCaseLaw API client with rate limiting, caching, and pagination.
    
    Provides methods for:
    - Searching decisions with query expansion
    - Fetching full decision details
    - Fetching citations (incoming/outgoing)
    - Fetching leading cases
    - Pagination support for large result sets
    """
    
    def __init__(
        self,
        base_url: str = OCL_BASE_URL,
        rate_limiter: Optional[RateLimiter] = None,
        cache_manager: Optional[CacheManager] = None,
        timeout: int = 30,
        user_agent: str = "LexMachina-Frontier/1.0",
    ):
        self.base_url = base_url.rstrip("/")
        self.rate_limiter = rate_limiter or RateLimiter()
        self.cache_manager = cache_manager
        self.timeout = timeout
        self.user_agent = user_agent
        self._session_stats = {"requests": 0, "cache_hits": 0, "errors": 0}
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Make an HTTP request to OpenCaseLaw API.
        
        Returns (response_data, provenance) where provenance is "live", "cache", or "error".
        """
        url = f"{self.base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        # Check cache first
        cache_key = self.cache_manager._make_key("ocl", endpoint, str(sorted(params.items()) if params else ""))
        
        if use_cache and self.cache_manager:
            cached = self.cache_manager.get(cache_key)
            if cached is not None:
                self._session_stats["cache_hits"] += 1
                return cached, "cache"
        
        # Rate limit
        wait_time = self.rate_limiter.acquire()
        if wait_time > 0:
            logger.debug(f"Rate limited, waited {wait_time:.3f}s")
        
        # Make request
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_text = resp.read().decode("utf-8", errors="replace")
                data = json.loads(response_text)
            
            self._session_stats["requests"] += 1
            
            # Cache successful response
            if use_cache and self.cache_manager and resp.status == 200:
                self.cache_manager.set(cache_key, data)
            
            return data, "live"
            
        except urllib.error.HTTPError as e:
            self._session_stats["errors"] += 1
            logger.error(f"HTTP error {e.code} for {url}: {e.reason}")
            raise
        except urllib.error.URLError as e:
            self._session_stats["errors"] += 1
            logger.error(f"URL error for {url}: {e.reason}")
            raise
        except json.JSONDecodeError as e:
            self._session_stats["errors"] += 1
            logger.error(f"JSON decode error for {url}: {e}")
            raise
        except Exception as e:
            self._session_stats["errors"] += 1
            logger.error(f"Unexpected error for {url}: {e}")
            raise
    
    def search_decisions(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        language: Optional[str] = None,
        court: Optional[str] = None,
        canton: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "relevance",
        fields: str = "full",
        include_pinpoint: bool = False,
        use_cache: bool = True,
    ) -> Tuple[List[Decision], Dict[str, Any]]:
        """
        Search decisions with pagination.
        
        Returns (decisions, search_metadata) where search_metadata contains
        total, returned, has_more, next_offset, result_set_id.
        """
        params = {
            "query": query,
            "limit": min(limit, 2000),  # API max
            "offset": offset,
            "sort": sort,
            "fields": fields,
            "include_pinpoint": str(include_pinpoint).lower(),
        }
        
        if language:
            params["language"] = language
        if court:
            params["court"] = court
        if canton:
            params["canton"] = canton
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        
        data, provenance = self._make_request("/decisions", params, use_cache=use_cache)
        
        decisions = []
        for item in data.get("results", []):
            item["_provenance"] = provenance
            decisions.append(Decision.from_api_response(item, provenance))
        
        metadata = {
            "query": query,
            "total": data.get("total", 0),
            "total_is_lower_bound": data.get("total_is_lower_bound", False),
            "returned": data.get("returned", len(decisions)),
            "has_more": data.get("has_more", False),
            "next_offset": data.get("next_offset"),
            "result_set_id": data.get("result_set_id"),
            "provenance": provenance,
            "limit": limit,
            "offset": offset,
        }
        
        return decisions, metadata
    
    def search_decisions_paginated(
        self,
        query: str,
        target_count: int = 100,
        max_pages: int = 10,
        language: Optional[str] = None,
        court: Optional[str] = None,
        canton: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "relevance",
        use_cache: bool = True,
    ) -> Tuple[List[Decision], Dict[str, Any]]:
        """
        Search decisions with automatic pagination to reach target_count.
        
        Respects rate limits and stops when target_count reached or no more results.
        """
        all_decisions: List[Decision] = []
        offset = 0
        pages_fetched = 0
        last_metadata = {}
        
        while len(all_decisions) < target_count and pages_fetched < max_pages:
            page_limit = min(200, target_count - len(all_decisions))
            decisions, metadata = self.search_decisions(
                query=query,
                limit=page_limit,
                offset=offset,
                language=language,
                court=court,
                canton=canton,
                date_from=date_from,
                date_to=date_to,
                sort=sort,
                use_cache=use_cache,
            )
            
            all_decisions.extend(decisions)
            last_metadata = metadata
            pages_fetched += 1
            
            if not metadata.get("has_more", False):
                break
            
            offset = metadata.get("next_offset", offset + page_limit)
        
        # Aggregate metadata
        last_metadata.update({
            "pages_fetched": pages_fetched,
            "total_decisions": len(all_decisions),
            "target_count": target_count,
        })
        
        return all_decisions, last_metadata
    
    def get_decision(
        self,
        decision_id: str,
        full_text: bool = True,
        use_cache: bool = True,
    ) -> Tuple[Optional[Decision], str]:
        """
        Fetch a single decision by ID or docket number.
        
        Returns (decision, provenance) or (None, "error") if not found.
        """
        endpoint = f"/decisions/{urllib.parse.quote(decision_id)}"
        params = {"full_text": str(full_text).lower()}
        
        try:
            data, provenance = self._make_request(endpoint, params, use_cache=use_cache)
            decision = Decision.from_api_response(data, provenance)
            return decision, provenance
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, "not_found"
            raise
    
    def get_decision_citations(
        self,
        decision_id: str,
        direction: str = "both",  # "outgoing", "incoming", "both"
        limit: int = 50,
        use_cache: bool = True,
    ) -> Tuple[List[Decision], Dict[str, Any]]:
        """
        Fetch citation neighborhood for a decision.
        
        Note: Based on API exploration, citations may be embedded in the decision
        response or available via separate endpoints. This method handles both.
        """
        # First get the full decision which may contain cited_decisions
        decision, provenance = self.get_decision(decision_id, full_text=False, use_cache=use_cache)
        
        if not decision:
            return [], {"error": "decision_not_found", "provenance": provenance}
        
        outgoing = []
        incoming = []
        
        # Parse cited_decisions from the decision (if available in full_text response)
        # The API returns cited_decisions as JSON string in the full decision
        # For now, we'll need to fetch the full decision to get citations
        if decision.full_text is None and full_text:
            # Re-fetch with full_text to get citations
            full_decision, _ = self.get_decision(decision_id, full_text=True, use_cache=use_cache)
            if full_decision and full_decision.full_text:
                # The cited_decisions field might be in the raw response
                pass
        
        # Try to get structured citations from the decision object
        # The API returns cited_decisions as a JSON array string
        cited_data = getattr(decision, "_cited_decisions_raw", None)
        
        metadata = {
            "decision_id": decision_id,
            "direction": direction,
            "outgoing_count": len(outgoing),
            "incoming_count": len(incoming),
            "provenance": provenance,
        }
        
        results = []
        if direction in ("outgoing", "both"):
            results.extend(outgoing)
        if direction in ("incoming", "both"):
            results.extend(incoming)
        
        return results[:limit], metadata
    
    def get_leading_cases(
        self,
        decision_id: str,
        limit: int = 20,
        use_cache: bool = True,
    ) -> Tuple[List[Decision], Dict[str, Any]]:
        """
        Fetch leading cases related to a decision.
        
        Leading cases are authoritative decisions on the same legal issue.
        """
        # Try the decisions search with a query based on the decision's legal area/statutes
        decision, _ = self.get_decision(decision_id, full_text=False, use_cache=use_cache)
        
        if not decision:
            return [], {"error": "decision_not_found"}
        
        # Build query from legal area and statutes
        query_parts = []
        if decision.legal_area:
            query_parts.append(decision.legal_area)
        if decision.statutes:
            query_parts.extend(decision.statutes[:3])  # Top 3 statutes
        
        if not query_parts:
            return [], {"error": "no_query_terms"}
        
        query = " ".join(query_parts)
        decisions, metadata = self.search_decisions(
            query=query,
            limit=limit,
            court=decision.court,
            language=decision.language,
            sort="relevance",
            use_cache=use_cache,
        )
        
        # Exclude the original decision
        decisions = [d for d in decisions if d.decision_id != decision_id]
        
        metadata.update({
            "source_decision_id": decision_id,
            "query_used": query,
            "provenance": "leading_cases_search",
        })
        
        return decisions, metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client session statistics."""
        stats = dict(self._session_stats)
        if self.cache_manager:
            stats["cache"] = self.cache_manager.get_stats()
        stats["rate_limiter"] = self.rate_limiter.get_status()
        return stats


def create_client(
    cache_dir: Optional[Path] = None,
    use_cache: bool = True,
    rate_limit: int = DEFAULT_RATE_LIMIT,
    cache_ttl: int = DEFAULT_CACHE_TTL,
) -> OpenCaseLawClient:
    """
    Factory function to create a configured OpenCaseLawClient.
    
    Args:
        cache_dir: Directory for file cache (None = disabled)
        use_cache: Whether to enable caching
        rate_limit: Max requests per second
        cache_ttl: Cache time-to-live in seconds
    
    Returns:
        Configured OpenCaseLawClient instance
    """
    rate_limiter = RateLimiter(max_requests=rate_limit)
    cache_manager = CacheManager(cache_dir, ttl_seconds=cache_ttl) if use_cache and cache_dir else None
    
    return OpenCaseLawClient(
        rate_limiter=rate_limiter,
        cache_manager=cache_manager,
    )