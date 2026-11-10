"""Config-tolerant offline replay over the product OpenCaseLaw cache.

Why this module exists
----------------------
The adapter cache is content-addressed over ``(path, params)``.  For a search
request the params include ``limit``, so a cache recorded by one retrieval
configuration cannot be replayed by another.  That is correct for the *live*
path (a different page size really is a different request), but it made the
product's own committed real-question cache unusable offline: the four frozen
reality questions were recorded with several page sizes (10/12/25/30/...),
while ``run_query_first_page`` / ``run_query_initial`` derive the page size
from the requested ``top_n`` (25 for 100, 37 for 150, ...).  The result was
``RuntimeError: OpenCaseLaw retrieval returned no decisions`` for real,
already-cached Swiss-law questions.

This module is an *offline-only* fallback transport.  It first honours the
exact request key, so canonical fixture replay keeps its historical bytes.  On
a search miss it may serve a cached ``/decisions`` response for the **same
query text and all other request parameters** (offset/sort/fields included),
ignoring only ``limit``.  No
network call, no cross-query substitution and no re-ranking happen here; the
adapter still normalises, dedupes and ranks the returned records exactly as it
does on the live path.

Claim ceiling: this changes *which already-recorded page* an offline replay
reads.  It does not change retrieval semantics, create new evidence, or make a
cache miss look like a live result.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ocl_adapter.cache import FileCache, canonical_params, request_key
from ocl_adapter.transport import TRANSPORT_CACHE_MISS, RawResponse, Transport

SEARCH_PATH = "/decisions"


class QuestionMatchTransport(Transport):
    """Offline transport: exact cache key first, then same-question page match.

    A match requires the same ``path``, the same ``query`` text, the same
    ``language`` and identical values for every other param except ``limit``.
    This means a page recorded at ``limit=12`` can answer a replay that asked
    for ``limit=25`` (the adapter simply receives 12 records and records that
    fact in its search log), but a different question, a different language
    filter, a different offset or a different sort/field selection never
    matches.  Ignoring ``offset`` would replay page 0 as page 1 and is
    therefore forbidden.
    """

    def __init__(self, cache_root: str | Path):
        self.cache = FileCache(cache_root)
        self._index: Optional[Dict[tuple[str, str], list[dict]]] = None
        self.exact_hits = 0
        self.question_matches = 0
        self.misses = 0

    # -- index -----------------------------------------------------------
    def _build_index(self) -> Dict[tuple[str, str], list[dict]]:
        index: Dict[tuple[str, str], list[dict]] = {}
        root = Path(self.cache.root)
        if root.is_dir():
            for path in sorted(root.rglob("*.json")):
                try:
                    entry = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(entry, dict):
                    continue
                if entry.get("cache_version") != 1:
                    continue
                if entry.get("path") != SEARCH_PATH:
                    continue
                params = entry.get("params") or {}
                query = str(params.get("query") or "")
                if not query:
                    continue
                key = (query, str(params.get("language") or ""))
                index.setdefault(key, []).append(entry)
        return index

    # -- matching --------------------------------------------------------
    @staticmethod
    def _compatible(entry: dict, requested: Dict[str, str]) -> bool:
        params = entry.get("params") or {}
        # Same param surface, then same values.  Merely checking the requested
        # names would let an entry that carries an extra filter (e.g. a channel
        # stage) match a request that never asked for it.
        requested_names = {name for name in requested if name != "limit"}
        cached_names = {name for name in params if name != "limit"}
        if requested_names != cached_names:
            return False
        for name in requested_names:
            if str(params.get(name, "")) != str(requested[name]):
                return False
        return True

    def _question_match(self, params: Optional[Dict[str, Any]]) -> Optional[dict]:
        canonical = canonical_params(params)
        query = str(canonical.get("query") or "")
        if not query:
            return None
        if self._index is None:
            self._index = self._build_index()
        entries = self._index.get((query, str(canonical.get("language") or "")), [])
        compatible = [entry for entry in entries if self._compatible(entry, canonical)]
        if not compatible:
            return None
        # Largest recorded page first (maximises recall without inventing
        # records); stable tie-break on the content-addressed key.
        compatible.sort(
            key=lambda entry: (
                -int((entry.get("params") or {}).get("limit") or 0),
                str(entry.get("key") or ""),
            )
        )
        return compatible[0]

    # -- Transport -------------------------------------------------------
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> RawResponse:
        entry = self.cache.get(request_key(path, params))
        if entry is not None:
            self.exact_hits += 1
        elif path == SEARCH_PATH:
            entry = self._question_match(params)
            if entry is not None:
                self.question_matches += 1
        if entry is None:
            self.misses += 1
            return RawResponse(
                path=path,
                params=canonical_params(params),
                url="",
                status=0,
                body="",
                fetched_at=0.0,
                from_cache=False,
                error=TRANSPORT_CACHE_MISS,
            )
        return RawResponse(
            path=path,
            params=canonical_params(params),
            url=str(entry.get("url") or ""),
            status=int(entry.get("status", 200)),
            body=str(entry.get("body") or ""),
            fetched_at=float(entry.get("fetched_at") or 0.0),
            from_cache=True,
        )

    def stats(self) -> dict:
        return {
            "exact_hits": self.exact_hits,
            "question_matches": self.question_matches,
            "misses": self.misses,
            "indexed_search_entries": (
                0 if self._index is None
                else sum(len(v) for v in self._index.values())
            ),
        }


__all__ = ["QuestionMatchTransport", "SEARCH_PATH"]
