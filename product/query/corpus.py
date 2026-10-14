"""Compatibility facade over the accepted OpenCaseLaw retrieval adapter.

New product code should use :mod:`query.pipeline`.  This module remains for
older callers, but it deliberately keeps live and fixture modes separate.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_ROOT = REPO_ROOT / "frontier" / "frontier-query-retrieval"
if ADAPTER_ROOT.is_dir() and str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

from ocl_adapter import AdapterConfig, build_candidate_bundle  # noqa: E402
from ocl_adapter.fixtures import replay_fixtures  # noqa: E402


def _to_legacy(c: dict) -> dict:
    return {
        "decision_id": c.get("decision_id", ""),
        "court": c.get("court") or "?",
        "language": c.get("language") or "?",
        "decision_date": c.get("decision_date") or "",
        "docket_number": c.get("docket_number") or "",
        "full_text": c.get("full_text") or c.get("regeste") or c.get("snippet") or "",
        "canonical_url": c.get("canonical_url") or "",
        "provenance": c.get("provenance") or "",
    }


def load_fixture_decisions() -> list[dict]:
    """Replay the frozen OpenCaseLaw envelopes. Explicit test/offline path only."""
    bundle = replay_fixtures(hydrate_top=2)
    return [_to_legacy(c) for c in bundle.get("candidates", [])]


def ocl_live_search(query: str, limit: int = 150, timeout: int = 45) -> tuple[list[dict], str]:
    """Live search through the accepted adapter and verified mcp.opencaselaw.ch API."""
    target = max(1, min(300, int(limit)))
    # Product-owned cache root: a live run must never create files in another
    # lane's directory (Enforce lane write scope failed run 38575541439 that
    # way).  Same content-addressed format, product path only.
    from .cache_path import product_cache_dir

    cfg = AdapterConfig(
        mode="live",
        cache_dir=str(product_cache_dir()),
        target=target,
        max_candidates=target,
        timeout=float(timeout),
        stop_when_target_met=True,
    )
    bundle = build_candidate_bundle(query, config=cfg)
    return (
        [_to_legacy(c) for c in bundle.get("candidates", [])],
        "live:https://mcp.opencaselaw.ch/api",
    )


def cached_live_search(query: str, limit: int = 150, ttl_seconds: int = 86400) -> tuple[list[dict], str, bool]:
    """Compatibility signature. The accepted adapter owns its content-addressed cache."""
    rows, provenance = ocl_live_search(query, limit=limit)
    return rows, provenance, False


def get_query_corpus(query: str, limit: int = 150, *, fixture: bool = False) -> tuple[list[dict], dict]:
    """Return one source mode only. Live results are never padded with fixtures."""
    if fixture:
        rows = load_fixture_decisions()[:limit]
        return rows, {"mode": "fixture", "n_total": len(rows), "fixture_only": True}

    rows, provenance = ocl_live_search(query, limit=limit)
    return rows, {
        "mode": "live",
        "n_total": len(rows),
        "live_provenance": provenance,
        "fixture_only": False,
    }


__all__ = [
    "load_fixture_decisions",
    "ocl_live_search",
    "cached_live_search",
    "get_query_corpus",
]
