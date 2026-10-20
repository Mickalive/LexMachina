"""Vendored content_sha256 — the accepted product bundle identity hasher.

Reused verbatim (REUSE-FIRST) from the accepted product mount
product/replay_bundle.py (product/replay_bundle.py::content_sha256). The
harness re-hashes each bundle's content identity before any scoring, exactly
as the accepted preflight does; it never trusts a recorded value.

Only the stdlib hasher is vendored (no product import, no network, no clock).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

TIMING_PATHS = (
    ("provenance", "latency_seconds"),
    ("provenance", "timing", "local_total_s"),
    ("provenance", "timing", "upstream_retrieval_s"),
    ("provenance", "timing", "local_map_s"),
    ("provenance", "retrieval", "remote", "latency_seconds"),
)

CACHE_ROOT_PATHS = (
    ("provenance", "cache_stats", "root"),
    ("provenance", "retrieval", "remote", "cache_stats", "root"),
)

CACHE_ROOT_TOKEN = "<cache-root>"
API_ENDPOINT_PREFIXES = ("/decisions", "/structure", "/citations", "/leading-cases")
ABSOLUTE_PATH_TOKEN = "<absolute-path>"
_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")


def is_absolute_fs_path(value: Any) -> bool:
    if not isinstance(value, str) or len(value) < 2:
        return False
    if value.startswith("//"):
        return False
    return value.startswith("/") or bool(_WINDOWS_ABS_RE.match(value))


def is_machine_path(value: Any) -> bool:
    if not is_absolute_fs_path(value):
        return False
    return not str(value).startswith(API_ENDPOINT_PREFIXES)


def _scrub_machine_paths(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _scrub_machine_paths(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_scrub_machine_paths(v) for v in node]
    if is_machine_path(node):
        return ABSOLUTE_PATH_TOKEN
    return node


def _pop_path(root: dict, path: tuple[str, ...]) -> None:
    node = root
    for key in path[:-1]:
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, dict):
        node.pop(path[-1], None)


def canonical_payload(bundle: dict) -> dict:
    """The exact structure content_sha256 hashes (timings dropped, cache roots
    tokenised, machine paths scrubbed; nothing else touched)."""
    canonical = copy.deepcopy(bundle)
    for path in TIMING_PATHS:
        _pop_path(canonical, path)
    for path in CACHE_ROOT_PATHS:
        node = canonical
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict) and path[-1] in node:
            node[path[-1]] = CACHE_ROOT_TOKEN
    return _scrub_machine_paths(canonical)


def content_sha256(bundle: dict) -> str:
    payload = json.dumps(canonical_payload(bundle), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
