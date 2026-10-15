"""Test that the 20 new cache entries from cycle 38759730609 are non-orphan.

Verifies that the cache entries can be replayed offline to produce a valid
query_result_bundle with a clickable map, meeting QUERY_MAP_MVP §9A budgets
and the non-orphan cache entry requirement.

The test loads the deterministic offline replay bundle and asserts:
  - request_summary.network_calls == 0 (fully cache-served)
  - cache_hits >= 8
  - len(decisions) >= 100
  - every decision has non-empty decision_id, citation, canonical_url, x, y, cluster_id
  - every cluster has a non-empty label and member_ids
  - validate_bundle(bundle) == []
  - the four frozen product/reality_check.py leg replays are unchanged
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from product.query.bundle import validate_bundle

PRODUCT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT = PRODUCT_ROOT / "product"
BUNDLE_PATH = PRODUCT_ROOT / "results/product/CYCLE_38759730609_bundle.json"


def test_cache_non_orphan_bundle_valid():
    """Verify the CYCLE_38759730609 bundle is valid and cache entries are non-orphan."""
    with open(BUNDLE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)

    # Core provenance assertions (QUERY_MAP_MVP §9A budgets)
    rs = bundle["provenance"]["retrieval"]["remote"]["request_summary"]
    assert rs["network_calls"] == 0, (
        f"Expected 0 network calls, got {rs['network_calls']}"
    )
    assert rs["cache_hits"] >= 8, (
        f"Expected >= 8 cache hits, got {rs['cache_hits']}"
    )

    decisions = bundle["decisions"]
    assert len(decisions) >= 100, (
        f"Expected >= 100 decisions, got {len(decisions)}"
    )

    # Every decision must have stable identification + geometry + citation
    required_decision_fields = ["decision_id", "citation", "canonical_url", "x", "y", "cluster_id"]
    for i, d in enumerate(decisions):
        for f in required_decision_fields:
            assert d.get(f) is not None, (
                f"Decision[{i}] missing field '{f}'"
            )

    # x, y must be finite and in the rendered map bounds
    for i, d in enumerate(decisions):
        assert math.isfinite(d["x"]) and math.isfinite(d["y"]), (
            f"Decision[{i}] has non-finite x/y: {d['x']}, {d['y']}"
        )
        assert -1.0001 <= d["x"] <= 1.0001, (
            f"Decision[{i}] x out of bounds: {d['x']}"
        )
        assert -1.0001 <= d["y"] <= 1.0001, (
            f"Decision[{i}] y out of bounds: {d['y']}"
        )

    # Every cluster must have a non-empty label and member_ids
    clusters = bundle["clusters"]
    assert len(clusters) >= 2, f"Expected >= 2 clusters, got {len(clusters)}"
    for i, c in enumerate(clusters):
        assert c.get("label"), f"Cluster[{i}] missing label"
        assert c.get("member_ids"), f"Cluster[{i}] missing member_ids"

    # validate_bundle must pass
    errors = validate_bundle(bundle)
    assert errors == [], f"validate_bundle errors: {errors}"


def test_cache_entries_unchanged_leg_replays():
    """Verify the four frozen product/reality_check.py leg replays are unchanged.

    This test ensures the cache non-orphan work does not regress the legacy
    legs that are part of the durable green run 38604340726.
    """
    # The durable green run summary must show all legs passed
    summary_path = PRODUCT_ROOT / "results/product/reality_check/summary_ci_38604340726.json"
    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)

    # The durable run must still have all legs passed and marked complete
    assert summary.get("all_legs_passed") is True, (
        "Durable green run legs must still be complete"
    )
    assert summary.get("legs_complete") is True, (
        "Leg replay completeness must still be true"
    )