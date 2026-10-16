"""Evaluation-lane HTTP client for OpenCaseLaw ``/decisions`` search.

stdlib-only, deliberately independent of the product/frontier retrieval
adapter: the baseline this benchmark measures must be the plain OpenCaseLaw
result set without the query-map/counter-authority machinery under test.

Contract notes:
* soft pace <= 2.5 req/s (charter limit is 5 req/s),
* bounded retries with backoff on transport errors and 5xx,
* ``base_url`` is the frozen spec's endpoint, i.e. the full search path
  (``https://mcp.opencaselaw.ch/api/decisions``), never an API root to which
  ``/decisions`` is appended a second time;
* content-addressed cache envelopes (sha256 of the request URL) written to a
  lane-owned cache directory; pass A is always a live fetch, pass B replays
  strictly offline so ``reproducible::cached_second_pass_identical`` compares
  live bytes against cached bytes.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

CACHE_VERSION = 1


@dataclass
class SearchOutcome:
    query_key: str
    channel: str
    slug: str
    language: str
    query: str
    limit: int
    url: str
    params: dict
    status: int = 0
    attempts: int = 0
    latency_seconds: float | None = None
    error: str | None = None
    raw_sha256: str | None = None
    body: dict | None = None
    from_cache: bool = False
    extra: dict = field(default_factory=dict)


class SearchClient:
    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        cache_dir: Path,
        timeout: float = 30.0,
        retries: int = 3,
        backoff_seconds: float = 1.5,
        max_rps: float = 2.5,
        offline: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("?").rstrip("/")
        self.user_agent = user_agent
        self.cache_dir = Path(cache_dir)
        self.timeout = float(timeout)
        self.retries = max(1, int(retries))
        self.backoff_seconds = float(backoff_seconds)
        self.min_interval = 1.0 / max(0.1, float(max_rps))
        self.offline = bool(offline)
        self._last_request_at = 0.0

    # -- cache ---------------------------------------------------------- #
    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / digest[:2] / f"{digest}.json"

    def _read_cache(self, url: str) -> tuple[bytes, dict] | None:
        path = self._cache_path(url)
        if not path.is_file():
            return None
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if env.get("url") != url or env.get("status") != 200:
            return None
        body = str(env.get("body") or "")
        return body.encode("utf-8"), {"fetched_at": env.get("fetched_at"),
                                      "cache_version": env.get("cache_version")}

    def _write_cache(self, url: str, body: bytes, status: int) -> None:
        path = self._cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        env = {
            "cache_version": CACHE_VERSION,
            "url": url,
            "status": status,
            "fetched_at": time.time(),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "body": body.decode("utf-8", errors="replace"),
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    # -- transport ------------------------------------------------------ #
    def _pace(self) -> None:
        wait = self._last_request_at + self.min_interval - time.time()
        if wait > 0:
            time.sleep(wait)

    def search(self, *, query_key: str, channel: str, slug: str, language: str,
               query: str, limit: int, extra_params: dict | None = None) -> SearchOutcome:
        params = {
            "query": query,
            "limit": int(limit),
            "offset": 0,
            "sort": "relevance",
            "fields": "full",
            "include_pinpoint": "false",
        }
        if extra_params:
            params.update(extra_params)
        # ``base_url`` is the frozen spec's endpoint (the full /decisions path)
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        out = SearchOutcome(query_key=query_key, channel=channel, slug=slug,
                            language=language, query=query, limit=int(limit),
                            url=url, params=params)

        if self.offline:
            cached = self._read_cache(url)
            out.attempts = 1
            if cached is None:
                out.status = 0
                out.error = "cache_miss (offline pass)"
                return out
            body_bytes, meta = cached
            out.from_cache = True
            out.extra["fetched_at"] = meta.get("fetched_at")
            return self._finish(out, body_bytes, status=200)

        deadline_errors: list[str] = []
        for attempt in range(1, self.retries + 1):
            out.attempts = attempt
            self._pace()
            started = time.time()
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": self.user_agent,
                                  "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body_bytes = resp.read()
                    status = int(resp.status)
                self._last_request_at = time.time()
                if 200 <= status < 300:
                    self._write_cache(url, body_bytes, status)
                    out.latency_seconds = round(time.time() - started, 3)
                    return self._finish(out, body_bytes, status)
                deadline_errors.append(f"HTTP {status}")
            except urllib.error.HTTPError as exc:
                self._last_request_at = time.time()
                deadline_errors.append(f"HTTP {exc.code}")
                if exc.code < 500:
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                self._last_request_at = time.time()
                deadline_errors.append(f"{type(exc).__name__}: {exc}")
            out.latency_seconds = round(time.time() - started, 3)
            if attempt < self.retries:
                time.sleep(self.backoff_seconds * attempt)
        out.status = 0
        out.error = "; ".join(deadline_errors) or "unknown transport error"
        return out

    def _finish(self, out: SearchOutcome, body_bytes: bytes, status: int) -> SearchOutcome:
        out.status = status
        out.raw_sha256 = hashlib.sha256(body_bytes).hexdigest()
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            out.status = 0
            out.error = f"non-JSON response: {type(exc).__name__}: {exc}"
            return out
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            out.status = 0
            out.error = "response is not an object with a results list"
            return out
        out.body = payload
        if out.latency_seconds is None and not out.from_cache:
            out.latency_seconds = 0.0
        return out
