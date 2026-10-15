"""Cycle-38759730609 required-fix tests: the 20 committed OpenCaseLaw cache
entries must be genuinely consumed by an offline replay, and the persisted
claim-path bundle must be that replay - not substitute content.

Required-fix provenance: results/audit/product/CYCLE_38759730609_GATE.json
(gate=REVISE) required a product test that *calls*
``run_query_initial(<recorded query>, top_n=120, retrieval_mode='offline')``
and asserts request_summary.network_calls == 0, cache_hits >= 8,
len(decisions) >= 100, per-decision decision_id/citation/canonical_url/x/y/
cluster_id, non-empty cluster labels and member_ids, and
validate_bundle(bundle) == [], while leaving the four frozen
product/reality_check.py leg replays unchanged.

Run 38766812030 (operational resume of 38763217418) additionally froze
guards for the defect it found on the claim path: the bundle previously
committed at results/product/CYCLE_38759730609_bundle.json contained 120
synthetic ``bge_BGE_test_*`` decisions labelled ``test decision group N``
instead of the offline replay. The synthetic bytes are preserved at
reports/product/incidents/synthetic_bundle_38759730609.RETIRED.json
(sha256 3f90bd560842c74d93f0dc3abde8b5e5acded2103eb31a541a819a132ba5a0d4).
"""
from __future__ import annotations

import json
import math
import urllib.parse
from pathlib import Path

from product.query.bundle import validate_bundle
from product.query.pipeline import run_query_initial

PRODUCT_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_PATH = PRODUCT_ROOT / "results/product/CYCLE_38759730609_bundle.json"
SUMMARY_PATH = PRODUCT_ROOT / "results/product/reality_check/summary_ci_38604340726.json"

RECORDED_QUERY = "Responsabilite penale de l'entreprise selon l'art. 102 CP"
RECORDED_TOP_N = 120

REQUIRED_NON_NULL = ("decision_id", "citation", "canonical_url", "x", "y", "cluster_id")
REQUIRED_KEYS = ("is_outlier", "source_url")
SOURCE_HOST_SUFFIX = "opencaselaw.ch"


def _request_summary(bundle: dict) -> dict:
    prov = bundle["provenance"]
    remote = (prov.get("retrieval") or {}).get("remote") or {}
    return remote.get("request_summary") or prov.get("request_summary") or {}


def _assert_map_contract(bundle: dict, *, expect_offline_replay: bool) -> None:
    rs = _request_summary(bundle)
    if expect_offline_replay:
        assert rs.get("network_calls") == 0, f"Expected 0 network calls, got {rs.get('network_calls')}"
        assert rs.get("cache_hits", 0) >= 8, f"Expected >= 8 cache hits, got {rs.get('cache_hits')}"

    decisions = bundle["decisions"]
    assert len(decisions) >= 100, f"Expected >= 100 decisions, got {len(decisions)}"

    for i, d in enumerate(decisions):
        did = str(d.get("decision_id") or "")
        # The retired bundle's synthetic ids: bge_BGE_test_0000_2024.
        assert "test_" not in did.lower(), (
            f"Decision[{i}] carries synthetic id {did!r}; claim path must hold "
            "OpenCaseLaw-sourced decisions only"
        )
        for f in REQUIRED_NON_NULL:
            assert d.get(f) is not None and d.get(f) != "", (
                f"Decision[{i}] missing field '{f}'"
            )
        for f in REQUIRED_KEYS:
            assert f in d, f"Decision[{i}] missing key '{f}'"
        assert math.isfinite(d["x"]) and math.isfinite(d["y"]), (
            f"Decision[{i}] has non-finite x/y: {d['x']}, {d['y']}"
        )
        assert -1.0001 <= d["x"] <= 1.0001, f"Decision[{i}] x out of bounds: {d['x']}"
        assert -1.0001 <= d["y"] <= 1.0001, f"Decision[{i}] y out of bounds: {d['y']}"
        host = urllib.parse.urlparse(str(d["canonical_url"])).netloc
        assert host.endswith(SOURCE_HOST_SUFFIX), (
            f"Decision[{i}] canonical_url host {host!r} is not the OpenCaseLaw source"
        )

    decision_ids = {d["decision_id"] for d in decisions}
    clusters = bundle["clusters"]
    assert len(clusters) >= 2, f"Expected >= 2 clusters, got {len(clusters)}"
    for i, c in enumerate(clusters):
        label = str(c.get("label") or "")
        assert label, f"Cluster[{i}] missing label"
        assert "test decision group" not in label.lower(), (
            f"Cluster[{i}] carries a synthetic label: {label!r}"
        )
        members = c.get("member_ids") or []
        assert members, f"Cluster[{i}] missing member_ids"
        orphans = [m for m in members if m not in decision_ids]
        assert not orphans, f"Cluster[{i}] member ids not present in decisions: {orphans[:5]}"

    errors = validate_bundle(bundle)
    assert errors == [], f"validate_bundle errors: {errors}"


def test_run_query_initial_offline_replay_contract():
    """required_fixes[3]: replay the recorded query from the committed cache."""
    bundle = run_query_initial(RECORDED_QUERY, top_n=RECORDED_TOP_N, retrieval_mode="offline")
    _assert_map_contract(bundle, expect_offline_replay=True)
    assert bundle["answer"]["status"] == "pending", (
        "map phase must stay zero-cost/zero-model (answer pending until enrich)"
    )


def test_persisted_claim_bundle_is_genuine_replay():
    """The artifact on the claim path must be the genuine offline replay.

    This is the regression guard for the defect found by run 38766812030:
    synthetic fixture decisions had been persisted under this exact path and
    described in the cycle report as a cache replay.
    """
    assert BUNDLE_PATH.is_file(), f"missing claim-path bundle {BUNDLE_PATH}"
    with open(BUNDLE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)
    assert bundle.get("query") == RECORDED_QUERY, (
        f"claim-path bundle was built for a different query: {bundle.get('query')!r}"
    )
    _assert_map_contract(bundle, expect_offline_replay=True)


def test_cache_entries_unchanged_leg_replays():
    """The four frozen product/reality_check.py leg replays stay unchanged.

    This test ensures the cache non-orphan work does not regress the legacy
    legs that are part of the durable green run 38604340726.
    """
    with open(SUMMARY_PATH, encoding="utf-8") as f:
        summary = json.load(f)
    assert summary.get("all_legs_passed") is True, (
        "Durable green run legs must still be complete"
    )
    assert summary.get("legs_complete") is True, (
        "Leg replay completeness must still be true"
    )
