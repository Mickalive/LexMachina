"""Minimal cached OpenCaseLaw search client for this team only.

Scope
-----
This is NOT a retrieval adapter rebuild.  It issues exactly the request the
accepted evaluation benchmark already issues -- same endpoint, same parameter
set (``query``, ``limit``, ``offset=0``, ``sort=relevance``, ``fields=full``,
``include_pinpoint=false``) -- and caches the bytes content-addressed under
this team's own directory, so a re-run costs zero network.

Budget discipline
-----------------
Every call is timed and every timing is recorded, because the frozen budget
(per search < 30 s, full live pass < 240 s) is an acceptance gate and a breach
must be disclosed rather than hidden.  Concurrency is capped and the free
public endpoint is never asked for more than ``MAX_CONCURRENCY`` simultaneous
requests, well inside the 5 req/s allowance.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ENDPOINT = "https://mcp.opencaselaw.ch/api/decisions"
CACHE_VERSION = "fqcr-1"
MAX_CONCURRENCY = 5
PER_SEARCH_BUDGET_S = 30.0
FULL_PASS_BUDGET_S = 240.0


@dataclass
class SearchOutcome:
    query: str
    url: str
    status: int
    rows: list[dict]
    n_total: int | None
    latency_seconds: float
    from_cache: bool
    error: str | None = None


@dataclass
class Cache:
    root: Path
    hits: int = 0
    misses: int = 0
    wall_seconds: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)
    #: Every search ever issued for this run's query set, including the ones a
    #: later cached replay does not re-fetch.  The latency budget is an
    #: acceptance gate, so a replay that costs no network must still DISCLOSE
    #: the measured wall time of the original live call.
    disclosed: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.root / digest[:2] / f"{digest}.json"

    def read(self, url: str) -> dict[str, Any] | None:
        path = self._path(url)
        if not path.is_file():
            return None
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if env.get("url") != url or env.get("status") != 200:
            return None
        return env

    def write(self, url: str, body: str, status: int, latency: float) -> None:
        path = self._path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "cache_version": CACHE_VERSION,
            "url": url,
            "status": status,
            "latency_seconds": latency,
            "fetched_at": time.time(),
            "body": body,
        }, ensure_ascii=False), encoding="utf-8")


def build_url(query: str, limit: int = 50) -> str:
    params = {
        "query": query,
        "limit": int(limit),
        "offset": 0,
        "sort": "relevance",
        "fields": "full",
        "include_pinpoint": "false",
    }
    return f"{ENDPOINT}?{urllib.parse.urlencode(params)}"


def _rows_from(body: str) -> tuple[list[dict], int | None]:
    data = json.loads(body)
    results = data.get("results") or []
    rows = []
    for row in results:
        rows.append({
            "decision_id": row.get("decision_id"),
            "canonical_decision_id": row.get("canonical_decision_id")
            or row.get("decision_id"),
            "docket_number": row.get("docket_number"),
            "citation_string_de": row.get("citation_string_de"),
            "citation_string_fr": row.get("citation_string_fr"),
            "citation_string_it": row.get("citation_string_it"),
            "language": row.get("language"),
            "decision_date": row.get("decision_date"),
            "canonical_url": row.get("canonical_url"),
            "court": row.get("court"),
            "text_head": row.get("text_head") or row.get("regeste"),
            "relevance_score": row.get("relevance_score"),
        })
    total = data.get("total")
    return rows, (int(total) if isinstance(total, int) else None)


def search(query: str, cache: Cache, *, limit: int = 50) -> SearchOutcome:
    """One cached search.  Cache hit costs no network and no latency budget."""
    url = build_url(query, limit=limit)
    env = cache.read(url)
    if env is not None:
        cache.hits += 1
        rows, total = _rows_from(str(env.get("body") or "{}"))
        measured = float(env.get("latency_seconds") or 0.0)
        cache.disclosed.append({"query": query, "status": int(env.get("status") or 200),
                                "latency_seconds": round(measured, 3),
                                "from_cache": True, "originally_live": True})
        return SearchOutcome(query, url, 200, rows, total, 0.0, True)

    cache.misses += 1
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read().decode("utf-8")
            status = int(response.status)
        latency = time.monotonic() - started
        if status == 200:
            cache.write(url, body, status, latency)
        rows, total = _rows_from(body)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, OSError) as exc:
        latency = time.monotonic() - started
        cache.calls.append({"query": query, "status": 0, "latency_seconds": round(latency, 3),
                            "error": type(exc).__name__, "from_cache": False})
        return SearchOutcome(query, url, 0, [], None, latency, False, str(exc))

    cache.calls.append({"query": query, "status": status,
                        "latency_seconds": round(latency, 3), "from_cache": False})
    cache.disclosed.append({"query": query, "status": status,
                            "latency_seconds": round(latency, 3),
                            "from_cache": False, "originally_live": True})
    return SearchOutcome(query, url, status, rows, total, latency, False)


def search_many(queries: list[str], cache: Cache, *,
                limit: int = 50, concurrency: int = MAX_CONCURRENCY) -> dict[str, SearchOutcome]:
    """Run searches with a bounded pool; identical queries collapse."""
    unique = list(dict.fromkeys(q for q in queries if q))
    started = time.monotonic()
    out: dict[str, SearchOutcome] = {}
    if unique:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            for outcome in pool.map(lambda q: search(q, cache, limit=limit), unique):
                out[outcome.query] = outcome
    cache.wall_seconds += time.monotonic() - started
    return out


__all__ = [
    "ENDPOINT",
    "Cache",
    "SearchOutcome",
    "build_url",
    "search",
    "search_many",
    "MAX_CONCURRENCY",
    "PER_SEARCH_BUDGET_S",
    "FULL_PASS_BUDGET_S",
]
