"""Offline mode must replay the four real frozen Swiss-law questions.

Regression pinned by cycle 42794322956 (operational resume of the persisted
snapshot of run 42793313084): ``minimal_vertical_slice.py --mode offline``
raised ``OpenCaseLaw retrieval returned no decisions`` for the frozen reality
questions because their committed OpenCaseLaw pages were recorded at page
sizes a ``top_n``-derived request never reproduces.  The tolerant question-match
transport now serves the same question text at a different ``limit`` with no
network call, and ``--bundle-out`` preserves the full query_result_bundle the
clickable map consumes.

These tests run under an armed non-loopback socket trap.  They assert wiring
only: no frozen recall/truth bar and no legal or usability claim.
"""
from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

import minimal_vertical_slice as mvs  # noqa: E402
from query.bundle import validate_bundle  # noqa: E402
from reality_check import LEGS  # noqa: E402

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_ORIG_CONNECT = socket.socket.connect
_network_attempts: list[str] = []


def _guarded_connect(self, address):  # pragma: no cover - trap machinery
    host = address[0] if isinstance(address, (tuple, list)) else str(address)
    if host not in _LOOPBACK:
        _network_attempts.append(str(host))
        raise OSError(f"NETWORK TRAPPED: blocked connect to {host}")
    return _ORIG_CONNECT(self, address)


def _blocked_create_connection(address, *args, **kwargs):  # pragma: no cover
    _network_attempts.append(str(address))
    raise OSError(f"NETWORK TRAPPED: blocked create_connection {address}")


@pytest.fixture
def network_trap(monkeypatch):
    _network_attempts.clear()
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket, "create_connection", _blocked_create_connection)
    yield _network_attempts
    assert _network_attempts == [], f"network attempted: {_network_attempts}"


@pytest.mark.parametrize("slug", ["rent-default", "petty-theft-dismissal"])
def test_frozen_question_replays_offline_with_full_bundle(network_trap, slug):
    question = LEGS[slug]
    out, bundle = mvs.run_minimal_slice(
        question, top_n=150, max_cites=8, mode="offline", with_bundle=True,
    )

    assert out["retrieval_mode"] == "offline"
    assert out["stages"] == {
        "retrieval": True,
        "map": True,
        "answer": True,
        "counter_authority": True,
    }
    # The whole point of the fix: a real cached question reaches the MVP map
    # band instead of failing with "no decisions".
    assert 100 <= out["summary"]["n_decisions"] <= 300
    assert out["summary"]["n_clusters"] >= 2

    rows = bundle.get("decisions") or []
    assert len(rows) == out["summary"]["n_decisions"]
    assert validate_bundle(bundle) == []
    for row in rows:
        assert isinstance(row.get("x"), (int, float))
        assert isinstance(row.get("y"), (int, float))
        assert row.get("cluster_id") is not None
        assert row.get("canonical_url") or row.get("source_url")

    cited = set((bundle.get("answer") or {}).get("cited_decision_ids") or [])
    assert cited
    assert cited <= {row["decision_id"] for row in rows}
    assert out["counter_info"]["n_counter_authorities"] >= 1

    replay = (bundle.get("provenance") or {}).get("product_offline_replay") or {}
    assert replay.get("source") == "product_query_cache_question_match_replay"
    assert replay.get("network") == "none"
    assert (replay.get("question_match") or {}).get("question_matches", 0) > 0
    assert network_trap == []


def test_cli_bundle_out_writes_full_query_result_bundle(network_trap, tmp_path):
    summary_file = tmp_path / "summary.json"
    bundle_file = tmp_path / "bundle.json"
    rc = mvs.main([
        LEGS["business-judgment-rule"],
        "--n", "150",
        "--mode", "offline",
        "--out", str(summary_file),
        "--bundle-out", str(bundle_file),
    ])
    assert rc == 0

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
    assert summary["retrieval_mode"] == "offline"
    assert summary["visualization"]["n_decisions"] >= 100
    assert len(bundle.get("decisions") or []) >= 100
    assert bundle.get("answer", {}).get("cited_decision_ids")
    assert validate_bundle(bundle) == []
    assert network_trap == []
