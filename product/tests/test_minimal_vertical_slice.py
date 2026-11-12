"""The FAST MVP one-command vertical slice must run end to end, offline.

``product/minimal_vertical_slice.py`` was committed by producer cycle
42756474119 with no test, no artifact and a hard-coded ``retrieval_mode =
"live"``, so its claim (question -> retrieval -> query_result_bundle ->
sourced answer -> counter-authority pass -> visualization adapter) was never
pinned.  Cycle 42771257885 (operational resume of snapshot 42764343815) adds
the ``--mode`` seam (``live`` / ``offline`` / ``fixture``) and pins the slice
here:

* ``mode="offline"`` runs the WHOLE path with an armed socket trap: cache-only
  retrieval, deterministic TF-IDF answer, independent counter-authority pass,
  bundle validation and the frontier ``query_bundle_adapter`` projection;
* every stage of the bundle reports true, the answer's citations are a subset
  of the retrieved decisions, and the visualization block carries the
  clickable-map fields the UI needs;
* the CLI writes a ``--out`` JSON whose ``retrieval_mode`` matches the mode;
* an unknown mode is rejected before any retrieval happens.

No network, no paid inference, no frozen gate, rubric, threshold or serve
verdict is touched by these tests.
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
    """Block every non-loopback connection for the duration of a test."""
    _network_attempts.clear()
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket, "create_connection", _blocked_create_connection)
    yield _network_attempts
    # a slice run must never have tried to leave the machine
    assert _network_attempts == [], f"network attempted: {_network_attempts}"


def _run_offline(top_n: int = 60) -> dict:
    return mvs.run_minimal_slice(
        "Kundigung Mietvertrag Mietrecht",
        top_n=top_n,
        max_cites=6,
        mode="offline",
    )


def test_offline_slice_end_to_end_under_network_trap(network_trap):
    out = _run_offline()

    assert out["retrieval_mode"] == "offline"
    assert out["stages"] == {
        "retrieval": True,
        "map": True,
        "answer": True,
        "counter_authority": True,
    }

    # retrieval -> bundle
    assert 40 <= out["summary"]["n_decisions"] <= 300
    assert out["summary"]["n_clusters"] >= 2

    # sourced answer: citations must be real retrieved decisions
    cited = out["answer"]["cited_decision_ids"]
    assert cited, "answer cited nothing"
    assert out["answer"]["method"] == "extractive_tfidf_v1"
    retrieved = set(out["decision_ids"])
    assert len(retrieved) == out["summary"]["n_decisions"]
    assert set(cited) <= retrieved, "answer cited an unretrieved decision"

    # independent counter-authority pass ran
    assert out["counter_info"]["n_counter_authorities"] >= 1
    assert out["counter_info"]["method"] == "independent_adversarial_tfidf_v1"

    # visualization adapter fields the clickable map consumes
    viz = out["visualization"]
    for field in ("n_decisions", "n_clusters", "n_relations", "n_counter",
                  "n_cited", "n_outliers", "languages", "bounds"):
        assert field in viz, f"visualization missing {field}"
    assert viz["n_decisions"] == out["summary"]["n_decisions"]
    assert "x_min" in viz["bounds"] and "y_min" in viz["bounds"]
    assert network_trap == []  # re-assert after the full run


def test_cli_mode_flag_and_out_file(network_trap, tmp_path):
    out_file = tmp_path / "slice.json"
    rc = mvs.main([
        "Kundigung Mietvertrag Mietrecht",
        "--n", "60",
        "--cites", "6",
        "--mode", "offline",
        "--out", str(out_file),
    ])
    assert rc == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert payload["retrieval_mode"] == "offline"
    assert payload["stages"]["retrieval"] is True
    assert payload["stages"]["counter_authority"] is True
    assert payload["visualization"]["n_decisions"] >= 40
    assert set(payload) >= {"query", "summary", "answer", "counter_info",
                            "visualization", "stages", "retrieval_mode"}


def test_unsupported_mode_rejected_before_retrieval():
    with pytest.raises(ValueError, match="unsupported retrieval mode"):
        mvs.run_minimal_slice("Kundigung Mietvertrag Mietrecht", mode="bogus")
