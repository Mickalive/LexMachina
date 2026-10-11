"""Content-addressed file cache.

Keys are SHA-256 over a canonical JSON encoding of ``(path, params)`` so the
same remote request always maps to the same file, in any process, on any host.
Entries are self-describing envelopes, which lets a *directory of cache files*
double as an offline fixture pack (acceptance 7).

Reuses the accepted product lane's file-cache idea
(``product/query/corpus.py`` cached_live_search, ``product/server.py``
ResponseCache) but makes the key canonical and the envelope stable.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

CACHE_VERSION = 1


def canonical_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalise params so key generation is stable across runs."""
    out: Dict[str, Any] = {}
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


def request_key(path: str, params: Optional[Dict[str, Any]] = None) -> str:
    payload = json.dumps(
        {"path": path, "params": canonical_params(params)},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FileCache:
    """JSON envelope store: ``<root>/<key[:2]>/<key>.json``."""

    def __init__(self, root, time_fn: Callable[[], float] = time.time):
        self.root = Path(root)
        self._time = time_fn
        self.hits = 0
        self.misses = 0
        self.writes = 0

    # -- storage ---------------------------------------------------------
    def _path_for(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> Optional[dict]:
        p = self._path_for(key)
        if not p.exists():
            self.misses += 1
            return None
        try:
            entry = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.misses += 1
            return None
        if not isinstance(entry, dict) or entry.get("cache_version") != CACHE_VERSION:
            self.misses += 1
            return None
        self.hits += 1
        return entry

    def set(self, key: str, entry: dict) -> None:
        payload = dict(entry)
        payload["cache_version"] = CACHE_VERSION
        payload.setdefault("key", key)
        p = self._path_for(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(p)
        self.writes += 1

    def put_response(
        self,
        path: str,
        params: Optional[Dict[str, Any]],
        *,
        status: int,
        body: str,
        url: str,
        fetched_at: Optional[float] = None,
    ) -> str:
        key = request_key(path, params)
        self.set(
            key,
            {
                "path": path,
                "params": canonical_params(params),
                "url": url,
                "status": int(status),
                "body": body,
                "fetched_at": self._time() if fetched_at is None else fetched_at,
            },
        )
        return key

    def get_response(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[dict]:
        return self.get(request_key(path, params))

    def keys(self) -> List[str]:
        if not self.root.exists():
            return []
        return sorted(p.stem for p in self.root.rglob("*.json") if p.is_file())

    def stats(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "root": str(self.root),
            "n_keys": len(self.keys()),
        }

    def clear_stats(self) -> None:
        self.hits = self.misses = self.writes = 0


def load_fixture_pack(path) -> Dict[str, dict]:
    """Load a recorded fixture pack (``{key: envelope}``) from JSON.

    A fixture pack is intentionally the same envelope shape as a cache
    entry, so ``results/.../fixtures/cache`` can be used directly as an
    offline ``cache_dir``.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("entries"), dict):
        entries = data["entries"]
    elif isinstance(data, dict):
        entries = {k: v for k, v in data.items() if isinstance(v, dict) and "path" in v}
    else:
        raise ValueError(f"unsupported fixture pack format in {path}")
    for k, v in entries.items():
        v.setdefault("cache_version", CACHE_VERSION)
    return entries
