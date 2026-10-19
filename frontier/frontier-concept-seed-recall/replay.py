"""Cache-first OpenCaseLaw search for the concept-seeded arm.

REUSE, NOT REBUILD
------------------
The content-addressed key, the canonical parameter encoding and the envelope
shape are **imported from the accepted adapter**
``frontier/frontier-query-retrieval/ocl_adapter/cache.py`` on the accepted
product mount.  ``verify_key_derivation()`` in the regression suite proves the
imported derivation reproduces committed envelope keys byte-for-byte, so a
variant this module mints lands on a cache path the product already honours.

A vendored, byte-identical copy of the two functions is used only when the
accepted mount is absent, and the record then says which derivation ran.

ZERO WRITES OUTSIDE THE TEAM NAMESPACE
--------------------------------------
The accepted product cache is opened READ-ONLY.  Every envelope this module
writes goes to the team's own cache directory under
``results/frontier/frontier-concept-seed-recall/cache/``.

BUDGET
------
Every call is disclosed with its measured wall time.  Cache hits cost no
network and are reported as ``from_cache``.  Live calls are serialised with a
minimum interval and are refused outright once the frozen per-search or
full-pass budget is exhausted; a refusal is a NAMED measurement gap, never a
silent substitution.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ENDPOINT = "https://mcp.opencaselaw.ch/api/decisions"
USER_AGENT = "LexMachina-Frontier-ConceptSeedRecall/1.0 (frontier lane; charter v1)"

#: Verbatim copy of ``ocl_adapter.cache`` (CACHE_VERSION 1).  Used only when the
#: accepted mount is not present; ``key_derivation_source`` records which ran.
CACHE_VERSION = 1


def _vendored_canonical_params(params: dict | None) -> dict:
    out: dict[str, Any] = {}
    for k in sorted(params or {}):
        v = params[k]
        if v is None:
            continue
        if isinstance(v, bool):
            out[k] = "true" if v else "false"
        elif isinstance(v, (list, tuple)):
            out[k] = ",".join(str(x) for x in v)
        else:
            out[k] = str(v)
    return out


def _vendored_request_key(path: str, params: dict | None = None) -> str:
    payload = json.dumps({"path": path, "params": _vendored_canonical_params(params)},
                         sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_accepted_cache_module(product_mount: Path | None):
    """Import the accepted adapter's cache module by file path, or return None."""
    if product_mount is None:
        return None
    target = Path(product_mount) / "frontier" / "frontier-query-retrieval" / "ocl_adapter" / "cache.py"
    if not target.is_file():
        return None
    spec = importlib.util.spec_from_file_location("lex_accepted_ocl_cache", target)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Searcher:
    """Cache-first GET /decisions.  Read-only on the accepted caches."""

    def __init__(self, read_only_cache_dirs: Iterable[Path], write_cache_dir: Path | None,
                 *, product_mount: Path | None = None, allow_live: bool = True,
                 per_search_budget_s: float = 30.0, full_pass_budget_s: float = 240.0,
                 min_interval_s: float = 0.4, timeout_s: float = 30.0,
                 time_fn=time.monotonic, sleep_fn=time.sleep):
        self.read_only_dirs = [Path(d) for d in read_only_cache_dirs if Path(d).is_dir()]
        self.write_cache_dir = Path(write_cache_dir) if write_cache_dir else None
        self.allow_live = allow_live
        self.per_search_budget_s = per_search_budget_s
        self.full_pass_budget_s = full_pass_budget_s
        self.min_interval_s = min_interval_s
        self.timeout_s = timeout_s
        self._time = time_fn
        self._sleep = sleep_fn

        mod = load_accepted_cache_module(product_mount)
        self.key_derivation_source = (
            "accepted lab/product frontier/frontier-query-retrieval/ocl_adapter/cache.py"
            if mod is not None else "vendored byte-identical copy in replay.py"
        )
        self._key_fn = mod.request_key if mod is not None else _vendored_request_key

        self.calls: list[dict] = []
        self.network_calls = 0
        self._live_seconds = 0.0
        self._last_live_end: float | None = None
        self._pass = "default"
        self._pass_start_index = 0
        self._pass_seconds: dict[str, float] = {}
        self._pass_network: dict[str, int] = {}

    # -- key / envelope --------------------------------------------------
    def request_key(self, path: str, params: dict | None) -> str:
        return self._key_fn(path, params)

    def cache_path(self, key: str) -> Path:
        assert self.write_cache_dir is not None
        return self.write_cache_dir / key[:2] / f"{key}.json"

    def _lookup(self, key: str) -> tuple[dict | None, str | None]:
        candidates = [d / key[:2] / f"{key}.json" for d in self.read_only_dirs]
        if self.write_cache_dir is not None:
            candidates.append(self.write_cache_dir / key[:2] / f"{key}.json")
        for p in candidates:
            if p.is_file():
                try:
                    env = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if isinstance(env, dict) and env.get("cache_version") == CACHE_VERSION:
                    return env, str(p)
        return None, None

    def begin_pass(self, name: str) -> None:
        """Start a budgeted pass.  The full-pass budget is per pass, not per run."""
        self._pass = name
        self._pass_start_index = len(self.calls)
        self._pass_seconds.setdefault(name, 0.0)
        self._pass_network.setdefault(name, 0)

    # -- the search ------------------------------------------------------
    @staticmethod
    def search_params(query: str, *, limit: int = 50, offset: int = 0,
                      sort: str = "relevance", fields: str = "full",
                      include_pinpoint: bool = False,
                      language: str | None = None) -> dict:
        """Frozen endpoint parameters.  ``language=None`` means NO language filter.

        The frozen baseline queries carry no ``language`` parameter (see the
        accepted record's own ``url`` fields), so the head-to-head arm must not
        add one: a per-language filter would change more than the query string.
        """
        params = {"query": query, "limit": str(limit), "offset": str(offset),
                  "sort": sort, "fields": fields,
                  "include_pinpoint": "true" if include_pinpoint else "false"}
        if language is not None:
            params["language"] = language
        return params

    @staticmethod
    def build_url(params: dict) -> str:
        qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
        return f"{ENDPOINT}?{qs}"

    def search(self, path: str, params: dict, *, query_key: str,
               allow_live: bool | None = None) -> dict:
        """One search.  Never raises: a transport failure is a measured outcome."""
        key = self.request_key(path, params)
        url = self.build_url(params)
        env, src = self._lookup(key)
        if env is not None:
            return self._record(query_key=query_key, params=params, url=url, key=key,
                                env=env, status=int(env.get("status") or 0),
                                from_cache=True, cache_source=src, latency_s=0.0,
                                live_refused=None)

        live_ok = self.allow_live if allow_live is None else allow_live
        if not live_ok:
            return self._record(query_key=query_key, params=params, url=url, key=key,
                                env=None, status=None, from_cache=False,
                                cache_source=None, latency_s=0.0,
                                live_refused="live retrieval disabled by --offline")
        if self._pass_seconds.get(self._pass, 0.0) >= self.full_pass_budget_s:
            return self._record(query_key=query_key, params=params, url=url, key=key,
                                env=None, status=None, from_cache=False,
                                cache_source=None, latency_s=0.0,
                                live_refused=(f"live budget for pass {self._pass!r} "
                                              f"({self.full_pass_budget_s}s) exhausted"))

        if self._last_live_end is not None:
            gap = self._min_gap_remaining()
            if gap > 0:
                self._sleep(gap)
        started = self._time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = resp.read().decode("utf-8")
                status = int(resp.status)
            err = None
        except Exception as exc:  # noqa: BLE001 - a transport failure is evidence
            body, status, err = "", None, f"{type(exc).__name__}: {exc}"[:200]
        latency = self._time() - started
        self._live_seconds += latency
        self._pass_seconds[self._pass] = self._pass_seconds.get(self._pass, 0.0) + latency
        self._last_live_end = self._time()
        self.network_calls += 1
        self._pass_network[self._pass] = self._pass_network.get(self._pass, 0) + 1

        env = None
        if body:
            env = {"cache_version": CACHE_VERSION, "key": key, "path": path,
                   "params": params, "url": url, "status": status, "body": body,
                   "fetched_at": time.time()}
            if self.write_cache_dir is not None:
                p = self.cache_path(key)
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(env, ensure_ascii=False, sort_keys=True),
                               encoding="utf-8")
                tmp.replace(p)
                src = str(p)
        return self._record(query_key=query_key, params=params, url=url, key=key,
                            env=env, status=status, from_cache=False,
                            cache_source=src, latency_s=latency,
                            live_refused=None, error=err)

    def _min_gap_remaining(self) -> float:
        if self._last_live_end is None:
            return 0.0
        return max(0.0, self.min_interval_s - (self._time() - self._last_live_end))

    def _record(self, *, query_key, params, url, key, env, status, from_cache,
                cache_source, latency_s, live_refused, error=None) -> dict:
        rows: list[dict] = []
        raw = ""
        if env is not None:
            raw = str(env.get("body") or "")
            try:
                payload = json.loads(raw) if raw else {}
            except ValueError:
                payload = {}
            rows = list(payload.get("results") or [])
        rec = {
            "query_key": query_key,
            "query": params.get("query"),
            "search_path": "/decisions",
            "cache_key": key,
            "params": params,
            "url": url,
            "status": status,
            "from_cache": from_cache,
            "cache_source": cache_source,
            "latency_seconds": round(float(latency_s), 3),
            "n_results": len(rows),
            "rows": rows,
            "raw_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw else None,
            "error": error,
            "live_refused": live_refused,
            "over_per_search_budget": bool(
                error is None and latency_s > self.per_search_budget_s),
        }
        self.calls.append({k: v for k, v in rec.items() if k != "rows"})
        return rec

    # -- reporting -------------------------------------------------------
    def budget_report(self) -> dict:
        over = [c["query_key"] for c in self.calls if c.get("over_per_search_budget")]
        per_pass = {}
        for name, secs in sorted(self._pass_seconds.items()):
            calls = [c for c in self.calls
                     if c["query_key"].split("::")[0] == name.split("::")[0]
                     and c["query_key"].startswith(name.split("::")[0] + "::")]
            per_pass[name] = {
                "measured_live_seconds": round(secs, 3),
                "network_calls": self._pass_network.get(name, 0),
                "n_calls": len(calls),
                "n_from_cache": sum(1 for c in calls if c.get("from_cache")),
                "pass_budget_breached": secs > self.full_pass_budget_s,
                "calls_over_per_search_budget": [
                    c["query_key"] for c in calls if c.get("over_per_search_budget")],
            }
        return {
            "budget_scope": "per-search limit applies to EVERY call; the full-pass limit "
                            "applies to EACH PASS separately (amendment "
                            "A2-latency-budget-scope)",
            "per_pass": per_pass,
            "per_search_budget_seconds": self.per_search_budget_s,
            "full_live_pass_budget_seconds": self.full_pass_budget_s,
            "network_calls": self.network_calls,
            "measured_live_seconds": round(self._live_seconds, 3),
            "n_calls": len(self.calls),
            "n_from_cache": sum(1 for c in self.calls if c.get("from_cache")),
            "calls_over_per_search_budget": over,
            "per_search_budget_breached": bool(over),
            "full_pass_budget_breached": any(
                v["pass_budget_breached"] for v in per_pass.values()),
            "any_pass_budget_breached": any(
                v["pass_budget_breached"] for v in per_pass.values()),
            "live_refused_calls": [
                {"query_key": c["query_key"], "reason": c["live_refused"]}
                for c in self.calls if c.get("live_refused")],
            "max_call_latency_seconds": max(
                [c["latency_seconds"] for c in self.calls], default=0.0),
            "key_derivation_source": self.key_derivation_source,
        }


__all__ = ["Searcher", "ENDPOINT", "USER_AGENT", "CACHE_VERSION",
           "load_accepted_cache_module", "_vendored_request_key",
           "_vendored_canonical_params"]


# ``path`` in ``_record`` is a literal; the cache key is the addressable id.
Searcher._record.__doc__ = (Searcher._record.__doc__ or "") + "\n"