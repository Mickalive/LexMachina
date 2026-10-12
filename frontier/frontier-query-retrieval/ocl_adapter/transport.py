"""Transports: how an adapter request turns into a response.

``OCLClient`` only ever talks to a :class:`Transport`. Three implementations
are provided:

* :class:`HttpTransport`     - real HTTPS via ``urllib`` (stdlib only)
* :class:`CachedTransport`   - read-through/write-through cache + mode policy
* :class:`FixtureTransport`  - recorded responses, for deterministic tests
* :class:`ScriptedTransport` - fails on purpose, for degradation tests
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .cache import FileCache, canonical_params, request_key
from .errors import OCLTransportError

TRANSPORT_CACHE_MISS = "cache_miss"
TRANSPORT_FIXTURE_MISS = "fixture_miss"


@dataclass
class RawResponse:
    path: str
    params: Dict[str, Any]
    url: str
    status: int
    body: str
    fetched_at: float
    from_cache: bool = False
    error: str = ""
    attempts: int = 1

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> Any:
        if not self.body:
            raise OCLTransportError(
                f"empty body (status={self.status}, error={self.error})", url=self.url
            )
        try:
            return json.loads(self.body)
        except ValueError as exc:
            raise OCLTransportError(
                f"non-JSON body (status={self.status}): {exc}", url=self.url
            ) from exc

    def detail(self) -> str:
        try:
            payload = json.loads(self.body)
            if isinstance(payload, dict) and "detail" in payload:
                return str(payload["detail"])
        except ValueError:
            pass
        return self.error or self.body[:200]

    def to_envelope(self) -> dict:
        return {
            "path": self.path,
            "params": canonical_params(self.params),
            "url": self.url,
            "status": self.status,
            "body": self.body,
            "fetched_at": self.fetched_at,
        }


class Transport:
    """Interface: ``get(path, params) -> RawResponse``. Never raises for HTTP."""

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> RawResponse:  # pragma: no cover
        raise NotImplementedError


def build_url(base_url: str, path: str, params: Optional[Dict[str, Any]] = None) -> str:
    base = base_url.rstrip("/")
    url = f"{base}/{path.lstrip('/')}"
    qp = canonical_params(params)
    if qp:
        url = f"{url}?{urllib.parse.urlencode(qp)}"
    return url


class HttpTransport(Transport):
    """Stdlib HTTPS transport with retry + bounded response size."""

    MAX_BYTES = 12_000_000

    def __init__(
        self,
        base_url: str,
        *,
        user_agent: str = "LexMachina-Frontier/1.0",
        timeout: float = 45.0,
        retries: int = 3,
        backoff_seconds: float = 1.5,
        limiter=None,
        time_fn: Callable[[], float] = time.time,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = max(1, int(retries))
        self.backoff_seconds = backoff_seconds
        self.limiter = limiter
        self._time = time_fn
        self._sleep = sleep_fn

    def _fetch(self, url: str) -> tuple[int, str, int]:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read(self.MAX_BYTES)
                return resp.status, raw.decode("utf-8", "replace"), 1
        except urllib.error.HTTPError as exc:
            raw = exc.read() if exc.fp else b""
            return exc.code, raw.decode("utf-8", "replace"), 1

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> RawResponse:
        url = build_url(self.base_url, path, params)
        last_err = ""
        attempts = 0
        for attempt in range(1, self.retries + 1):
            attempts = attempt
            if self.limiter is not None:
                self.limiter.wait()
            try:
                status, body, _ = self._fetch(url)
                # Retry only transient server-side conditions.
                if status in (429, 500, 502, 503, 504) and attempt < self.retries:
                    last_err = f"HTTP {status}"
                    self._sleep(self.backoff_seconds * attempt)
                    continue
                return RawResponse(
                    path=path,
                    params=canonical_params(params),
                    url=url,
                    status=status,
                    body=body,
                    fetched_at=self._time(),
                    attempts=attempt,
                )
            except OCLTransportError as exc:  # defensive; _fetch converts most
                last_err = str(exc)
            except Exception as exc:  # URLError, timeout, DNS, TLS ...
                last_err = f"{type(exc).__name__}: {exc}"
            if attempt < self.retries:
                self._sleep(self.backoff_seconds * attempt)
        raise OCLTransportError(
            f"transport failed after {attempts} attempts: {last_err}", url=url, attempts=attempts
        )


class CachedTransport(Transport):
    """Mode-aware cache wrapper.

    * ``live``    - cache hit short-circuits; miss goes to ``inner`` and is stored
    * ``offline`` - cache hit only; a miss returns ``status=0, error=cache_miss``
    * ``refresh`` - always hits ``inner`` and rewrites the cache
    """

    def __init__(self, inner: Transport, cache: FileCache, mode: str = "live", ttl_seconds: int = 7 * 24 * 3600):
        if mode not in ("live", "offline", "refresh"):
            raise ValueError(f"unknown cache mode {mode!r}")
        self.inner = inner
        self.cache = cache
        self.mode = mode
        self.ttl_seconds = ttl_seconds

    def _fresh(self, entry: dict) -> bool:
        if self.mode == "refresh":
            return False
        if self.mode == "offline":
            # Offline fixtures must stay replayable forever: staleness is
            # irrelevant when the network is deliberately out of the loop.
            return True
        age = time.time() - float(entry.get("fetched_at") or 0)
        return age <= self.ttl_seconds

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> RawResponse:
        key = request_key(path, params)
        entry = self.cache.get(key)
        if entry is not None and self._fresh(entry):
            return RawResponse(
                path=path,
                params=canonical_params(params),
                url=str(entry.get("url", "")),
                status=int(entry.get("status", 200)),
                body=str(entry.get("body", "")),
                fetched_at=float(entry.get("fetched_at") or 0),
                from_cache=True,
            )
        if self.mode == "offline":
            return RawResponse(
                path=path,
                params=canonical_params(params),
                url=build_url(getattr(self.inner, "base_url", ""), path, params),
                status=0,
                body="",
                fetched_at=time.time(),
                from_cache=False,
                error=TRANSPORT_CACHE_MISS,
            )
        resp = self.inner.get(path, params)
        if 200 <= resp.status < 400 and resp.body:
            self.cache.put_response(
                path,
                params,
                status=resp.status,
                body=resp.body,
                url=resp.url,
                fetched_at=resp.fetched_at,
            )
        return resp


class FixtureTransport(Transport):
    """Replays recorded envelopes. ``strict`` raises on unknown keys."""

    def __init__(self, entries: Dict[str, dict], *, base_url: str = "fixture://opencaselaw/api", strict: bool = False):
        self.entries = entries
        self.base_url = base_url.rstrip("/")
        self.strict = strict
        self.seen = []

    @classmethod
    def from_cache_dir(cls, dirpath, **kw) -> "FixtureTransport":
        from .cache import load_fixture_pack  # local import to avoid cycle noise

        # A fixture cache dir is a directory tree of cache envelopes.
        entries: Dict[str, dict] = {}
        root = _as_path(dirpath)
        if root.is_file():
            entries = load_fixture_pack(root)
        else:
            for p in sorted(root.rglob("*.json")):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if isinstance(data, dict) and "path" in data and "body" in data:
                    entries[data.get("key") or p.stem] = data
        return cls(entries, **kw)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> RawResponse:
        key = request_key(path, params)
        self.seen.append(key)
        entry = self.entries.get(key)
        if entry is None:
            if self.strict:
                raise OCLTransportError(
                    f"fixture miss for {path} params={canonical_params(params)}", url=path
                )
            return RawResponse(
                path=path,
                params=canonical_params(params),
                url=build_url(self.base_url, path, params),
                status=0,
                body="",
                fetched_at=time.time(),
                error=TRANSPORT_FIXTURE_MISS,
            )
        return RawResponse(
            path=path,
            params=canonical_params(params),
            url=str(entry.get("url", "")),
            status=int(entry.get("status", 200)),
            body=str(entry.get("body", "")),
            fetched_at=float(entry.get("fetched_at") or 0),
            from_cache=True,
        )


class ScriptedTransport(Transport):
    """Deterministic failure injection for degradation tests.

    ``fail_paths``: path prefixes that always fail with a transport error.
    ``fail_first``: mapping ``path -> n`` meaning the first n calls fail.
    """

    def __init__(self, inner: Transport, *, fail_paths=(), fail_after: Optional[int] = None, error: str = "injected outage"):
        self.inner = inner
        self.fail_paths = tuple(fail_paths)
        self.fail_after = fail_after
        self.error = error
        self.calls = 0

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> RawResponse:
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise OCLTransportError(f"injected outage after {self.fail_after} calls", url=path)
        for prefix in self.fail_paths:
            if path.startswith(prefix):
                raise OCLTransportError(f"injected outage for {path}", url=path)
        return self.inner.get(path, params)


def _as_path(dirpath):
    from pathlib import Path

    return Path(dirpath) if not hasattr(dirpath, "exists") else dirpath
