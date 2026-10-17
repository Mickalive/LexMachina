"""Fixture replay + offline wiring gates (product cycle 39011220761).

Two negatives preserved as evidence, each pinned here as a repair:

1. **Dead fixture retrieval for the frozen legs.** ``--mode fixture`` raised
   ``RuntimeError: OpenCaseLaw retrieval returned no decisions`` for every
   reality leg (``results/product/reality_check/summary_fixture_20261016T165553Z.json``
   and ``..._20261017T055734Z.json``), because the canonical Frontier fixture
   scenario only ever recorded the single frozen query
   "Kündigung Mietvertrag Mietrecht". The leg envelopes *do* exist — in the
   product-owned live cache — but the replay used a differently-shaped config
   against a different directory and therefore missed.

   Repair: ``product.query.pipeline.replay_fixture_query`` replays offline
   against the canonical scenario first (unchanged historical behaviour) and
   then against the product cache with the exact live config shape.

2. **Un-passable fixture gates.** Once retrieval worked, fixture mode failed
   forever on a live-only assertion (``adversarial method:
   fixture_adversarial_v2``), so the offline check could never distinguish a
   broken pipeline from an inherently unsatisfiable gate.

   Repair: ``evaluate()`` emits ``wiring::*`` gates in fixture mode. The frozen
   ``structural_gates`` / ``truth_gates`` / ``frozen_recall_gate`` functions are
   byte-untouched, are never evaluated in fixture mode, and are never reported
   as passed there; live mode is unchanged.

Everything here is deterministic and network-free.
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
        sys.path.insert(0, _p)

from query import run_query_initial  # noqa: E402
from query import pipeline as pl  # noqa: E402
from query.progressive import run_query_first_page  # noqa: E402
from reality_check import LEGS, evaluate, fixture_wiring_gates  # noqa: E402

FROZEN_FIXTURE_QUERY = "Kündigung Mietvertrag Mietrecht"


# --------------------------------------------------------------------------- #
# 1. offline replay for the frozen reality legs
# --------------------------------------------------------------------------- #
def _no_network(*_a, **_k):  # pragma: no cover - exercised by every test here
    raise AssertionError("fixture mode attempted network access")


def test_leg_question_replays_from_the_product_cache_without_network(monkeypatch):
    """A frozen leg question must replay offline from recorded live envelopes.

    ``socket.connect`` is booby-trapped: any network attempt fails the test,
    so a green result proves the replay is cache-only.
    """
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    bundle = run_query_initial(LEGS["rent-default"], top_n=100,
                               retrieval_mode="fixture")
    assert len(bundle["decisions"]) >= 40, "fixture replay returned too few rows"
    assert bundle["provenance"]["fixture_mode"] is True
    replay = bundle["provenance"]["product_fixture_replay"]
    assert replay["source"] == "product_query_cache_live_config_replay"
    assert replay["network"] == "none"
    assert replay["n_candidates"] >= len(bundle["decisions"]), (
        "replay provenance must describe a pool at least as large as the served slice")
    # the map every decision needs to be clickable
    for d in bundle["decisions"]:
        assert isinstance(d.get("x"), (int, float))
        assert isinstance(d.get("y"), (int, float))
        assert d.get("cluster_id") is not None
        assert d.get("canonical_url"), f"missing source link: {d.get('decision_id')}"


def test_first_page_replay_works_for_a_leg_question_without_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    bundle = run_query_first_page(LEGS["business-judgment-rule"], top_n=100,
                                  retrieval_mode="fixture")
    assert len(bundle["decisions"]) > 0
    assert bundle["provenance"]["fixture_mode"] is True


def test_canonical_frozen_query_still_replays_from_the_frontier_scenario(monkeypatch):
    """Ordering guard: the historical source is tried first, so every
    pre-existing fixture test keeps the exact behaviour it had before."""
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    bundle = run_query_initial(FROZEN_FIXTURE_QUERY, top_n=100,
                               retrieval_mode="fixture")
    assert len(bundle["decisions"]) > 0
    assert (bundle["provenance"]["product_fixture_replay"]["source"]
            == "canonical_frontier_fixture_scenario")


def test_replay_fabricates_nothing_when_both_caches_are_empty(monkeypatch, tmp_path):
    """Non-vacuity control: with empty caches the replay must come back empty
    (the caller then raises), not invent decisions."""
    empty = tmp_path / "empty_cache"
    empty.mkdir()
    real_fixture_config = pl.fixture_config

    def _empty_config(**kw):
        kw.setdefault("mode", "offline")
        kw["cache_dir"] = str(empty)
        return real_fixture_config(**kw)

    monkeypatch.setattr(pl, "fixture_config", _empty_config)
    monkeypatch.setattr(pl, "_retrieval_config",
                        lambda top_n, mode="offline": _empty_config())
    out = pl.replay_fixture_query(LEGS["rent-default"], top_n=100, hydrate_top=0)
    assert (out.get("candidates") or []) == []
    assert out["provenance"]["product_fixture_replay"]["n_candidates"] == 0


# --------------------------------------------------------------------------- #
# 2. fixture wiring gates vs the frozen live gates
# --------------------------------------------------------------------------- #
def _fixture_report(mode: str = "fixture", decisions=None) -> dict:
    ids = [f"bge_{n}" for n in range(45)] if decisions is None else None
    rows = decisions if decisions is not None else [
        {"decision_id": i, "x": 1.0, "y": 2.0, "cluster_id": 0,
         "rank": n, "counter_status": "none"} for n, i in enumerate(ids)
    ]
    cited = rows[0]["decision_id"]
    return {
        "mode": mode,
        "validation_errors": [],
        "total_seconds": 3.0,
        "bundle": {
            "decisions": rows,
            "answer": {
                "status": "ready",
                "method": "fixture_answer_v1",
                "prose": f"Fixture grounded answer [{cited}]",
                "cited_decision_ids": [cited],
            },
            "provenance": {"generative_audit": {
                "provider_error": None,
                "adversarial": {"method": "fixture_adversarial_v2",
                                "model": "fixture", "error": None},
            }},
        },
    }


def test_fixture_mode_emits_only_wiring_gates_plus_instrumented_recall():
    gates = evaluate("rent-default", _fixture_report())
    names = [g["gate"] for g in gates]
    assert names, "no gates emitted"
    assert all(n.startswith("wiring::") for n in names), names
    # the frozen gates must be absent, not silently passed
    assert "structural" not in names
    assert not any(n.startswith("truth::") for n in names)
    assert all(g["passed"] for g in gates), gates


def test_bjr_fixture_run_keeps_the_accepted_instrumented_recall_gate():
    gates = {g["gate"]: g for g in evaluate("business-judgment-rule",
                                            _fixture_report())}
    recall = gates["recall::citation_controlling_authority"]
    assert recall["passed"]
    assert "fixture" in recall["detail"]


def test_live_mode_gate_names_are_untouched():
    """The durable workflow's gate set must be exactly what it always was."""
    gates = evaluate("rent-default", _fixture_report(mode="live"))
    assert [g["gate"] for g in gates] == ["structural", "truth::rent-default"]


def test_wiring_gates_fail_when_retrieval_replayed_nothing():
    """Negative control: the wiring gate that caught the original defect."""
    report = _fixture_report(decisions=[
        {"decision_id": "bge_1", "x": 0.0, "y": 0.0, "cluster_id": 0,
         "rank": 1, "counter_status": "none"},
    ] * 3)
    gates = {g["gate"]: g for g in fixture_wiring_gates(report)}
    assert not gates["wiring::retrieval_replayed"]["passed"]
    assert "40" in gates["wiring::retrieval_replayed"]["detail"]


def test_wiring_gates_fail_on_a_row_without_map_coordinates():
    rows = [
        {"decision_id": f"bge_{n}", "x": 1.0 if n else None, "y": 2.0,
         "cluster_id": 0 if n else None, "rank": n + 1, "counter_status": "none"}
        for n in range(45)
    ]
    gates = {g["gate"]: g for g in fixture_wiring_gates(_fixture_report(decisions=rows))}
    assert not gates["wiring::map_coordinates"]["passed"]


def test_wiring_gates_fail_when_the_adversarial_pass_is_missing():
    report = _fixture_report()
    report["bundle"]["provenance"]["generative_audit"]["adversarial"] = {
        "method": "", "error": "provider exploded"}
    gates = {g["gate"]: g for g in fixture_wiring_gates(report)}
    assert not gates["wiring::adversarial_recorded"]["passed"]


def test_wiring_gates_report_one_located_failure_when_retrieval_died():
    """A fatal retrieval error must not be buried under derived failures."""
    report = {"mode": "fixture",
              "fatal_error": "RuntimeError: OpenCaseLaw retrieval returned no decisions"}
    gates = fixture_wiring_gates(report)
    assert len(gates) == 1
    assert gates[0]["gate"] == "wiring::bundle_present"
    assert not gates[0]["passed"]


# --------------------------------------------------------------------------- #
# 3. end-to-end offline CLI: the pre-existing red is now a wiring pass
# --------------------------------------------------------------------------- #
def test_fixture_cli_leg_passes_offline_and_declares_live_gates_not_evaluated(tmp_path, capsys):
    from reality_check import main

    rc = main(["--slug", "rent-default", "--mode", "fixture", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0, out
    summaries = sorted(tmp_path.glob("summary_fixture_*.json"))
    assert summaries, "no fixture summary written"
    summary = json.loads(summaries[-1].read_text(encoding="utf-8"))
    assert summary["mode"] == "fixture"
    assert summary["live_gates_evaluated"] is False
    assert "OFFLINE WIRING EVIDENCE ONLY" in summary["claim_ceiling"]
    gates = [g["gate"] for leg in summary["legs"] for g in leg["gates"]]
    assert gates and all(g.startswith("wiring::") for g in gates), gates
