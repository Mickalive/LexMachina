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

3. **Fabricated frozen-gate green in fixture mode (audit D1, cycle 39014141628).**
   The BJR fixture branch of ``evaluate()`` emitted the frozen gate name
   ``recall::citation_controlling_authority`` with ``passed=true`` and a
   'not applicable' detail — a pass on a gate that was never evaluated,
   pinned by ``test_bjr_fixture_run_keeps_the_accepted_instrumented_recall_gate``
   and ``test_reality_check.py::test_bjr_frozen_recall_gate_fixture_mode_is_instrumented_skip``.

   Repair: the frozen gate name is absent from fixture output entirely; an
   explicit ``wiring::frozen_recall_gate_not_evaluated`` marker records the
   non-evaluation and the fixture summary carries
   ``frozen_gates_evaluated: []``.  Both tests now pin that contract; the
   frozen gate functions and the live path are byte-untouched.

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


def test_bjr_fixture_run_records_the_frozen_recall_gate_as_not_evaluated():
    """The frozen recall gate must never be reported as passed in fixture mode.

    Repair of audit D1 (cycle 39014141628): fixture mode used to emit the
    frozen gate name ``recall::citation_controlling_authority`` with
    ``passed=true`` and a 'not applicable' detail — a fabricated green on a
    gate that was never evaluated.  The contract now: the frozen gate name is
    absent from fixture output entirely, and an explicit
    ``wiring::frozen_recall_gate_not_evaluated`` marker records the
    non-evaluation.  The frozen gate itself is untouched (live-only).
    """
    gates = {g["gate"]: g for g in evaluate("business-judgment-rule",
                                            _fixture_report())}
    assert "recall::citation_controlling_authority" not in gates, (
        "fixture mode must never emit the frozen gate name, not even as a "
        "'not applicable' pass")
    marker = gates["wiring::frozen_recall_gate_not_evaluated"]
    assert marker["passed"] is True
    assert "not evaluated" in marker["detail"]
    assert "fixture" in marker["detail"]


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


# --------------------------------------------------------------------------- #
# 4. committed-artifact sweep — audit D1-R (rejected cycle 39016943581, round 2)
#
# Round 1 of that repair fixed the CODE path and the 074955Z artifact pair but
# left the earlier 072123Z pair of the same preserved snapshot (f3c47c8)
# carrying `recall::citation_controlling_authority` with `passed=true` under
# `mode=fixture`, while both the resume report and `state/product.json` cited it
# as a clean 4/4 result — and while the repair report asserted "no committed
# artifact carries a fabricated green".  The unit tests above only ever exercised
# freshly *generated* output, so nothing failed on committed residue.
#
# These tests close that gap: they sweep the committed artifact directory itself.
# --------------------------------------------------------------------------- #
FROZEN_GATE_PREFIXES = ("structural", "truth::", "recall::")
REALITY_DIR = ROOT / "results" / "product" / "reality_check"


def _committed_fixture_artifacts() -> list[Path]:
    files = sorted(REALITY_DIR.glob("*fixture*.json"))
    assert files, f"no committed fixture artifacts under {REALITY_DIR}"
    return files


def _fabricated_passes(node) -> list[str]:
    """Frozen gate names reported as *passed* anywhere inside ``node``."""
    found: list[str] = []
    if isinstance(node, dict):
        gate = node.get("gate")
        if (isinstance(gate, str) and node.get("passed") is True
                and gate.startswith(FROZEN_GATE_PREFIXES)):
            found.append(gate)
        for value in node.values():
            found.extend(_fabricated_passes(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_fabricated_passes(value))
    return found


def test_no_committed_fixture_artifact_carries_a_fabricated_frozen_green():
    """Sweep every committed fixture artifact for the D1 fabricated green.

    A fixture artifact must never report a frozen gate (``structural``,
    ``truth::*``, ``recall::*``) as passed: fixture mode evaluates wiring only
    and records the frozen non-evaluation explicitly.  This is the regression
    guard audit D1-R of cycle 39016943581 found missing — it fails on committed
    residue, not only on freshly generated output.
    """
    offenders: dict[str, list[str]] = {}
    for path in _committed_fixture_artifacts():
        payload = json.loads(path.read_text(encoding="utf-8"))
        hits = _fabricated_passes(payload)
        if hits:
            offenders[str(path.relative_to(ROOT))] = sorted(set(hits))
    assert not offenders, (
        "committed fixture artifacts still report a frozen gate as passed: "
        f"{offenders}")


def test_fabricated_green_sweep_is_not_vacuous():
    """Negative control: the sweep predicate must detect a deliberate regress."""
    clean = [{"gate": "wiring::bundle_present", "passed": True, "detail": ""}]
    assert _fabricated_passes(clean) == []
    regressed = clean + [{
        "gate": "recall::citation_controlling_authority",
        "passed": True,
        "detail": "fixture mode: frozen-recall parity not applicable (wiring check only)",
    }]
    assert _fabricated_passes(regressed) == ["recall::citation_controlling_authority"], (
        "the sweep predicate must fire on the exact historical defect shape")
    # a frozen gate honestly reported as FAILED is evidence, never fabrication
    honest_failure = [{"gate": "truth::rent-default", "passed": False,
                       "detail": "missing good-faith branch"}]
    assert _fabricated_passes(honest_failure) == []


def test_corrected_072123_pair_records_the_marker_and_the_frozen_non_evaluation():
    """Audit D1-R's two named artifacts must carry the corrected contract."""
    summary_path = REALITY_DIR / "summary_fixture_20261017T072123Z.json"
    leg_path = REALITY_DIR / "business-judgment-rule_fixture_20261017T072123Z.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    leg = json.loads(leg_path.read_text(encoding="utf-8"))

    for name, payload in ((summary_path.name, summary), (leg_path.name, leg)):
        assert payload["mode"] == "fixture"
        assert _fabricated_passes(payload) == [], name
    # summary: machine-readable non-evaluation, next to live_gates_evaluated
    assert summary["frozen_gates_evaluated"] == []
    assert summary["live_gates_evaluated"] is False
    assert "OFFLINE WIRING EVIDENCE ONLY" in summary["claim_ceiling"]
    # BJR leg: the explicit marker replaced the fabricated entry
    marker = [g for g in leg["gates"]
              if g["gate"] == "wiring::frozen_recall_gate_not_evaluated"]
    assert len(marker) == 1 and marker[0]["passed"] is True
    assert "not evaluated" in marker[0]["detail"]
    bjr_leg = next(l for l in summary["legs"] if l["slug"] == "business-judgment-rule")
    assert [g["gate"] for g in bjr_leg["gates"]][-1] == (
        "wiring::frozen_recall_gate_not_evaluated")
    # the fixture summary count itself must still be honest wiring evidence
    assert all(g["gate"].startswith("wiring::")
               for l in summary["legs"] for g in l["gates"])


def test_every_committed_fixture_summary_declares_frozen_gates_not_evaluated():
    """New fixture summaries must carry ``frozen_gates_evaluated: []``.

    Only summaries produced from the D1 repair onward are held to this (older
    historical summaries predate the key and never claimed it); the corrected
    ``072123Z`` summary is one of them, and every future CLI run already emits
    the key (see ``reality_check.main``).
    """
    required = {
        "summary_fixture_20261017T072123Z.json",
        "summary_fixture_20261017T074955Z.json",
        "summary_fixture_20261017T083008Z.json",
    }
    seen = set()
    for path in _committed_fixture_artifacts():
        if not path.name.startswith("summary_fixture_"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "frozen_gates_evaluated" in payload:
            seen.add(path.name)
            assert payload["frozen_gates_evaluated"] == [], path.name
    missing = required - seen
    assert not missing, f"fixture summaries missing frozen_gates_evaluated: {sorted(missing)}"
