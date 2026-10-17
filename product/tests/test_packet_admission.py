"""Factory direction v50 product obligation (1): the two ACCEPTED frozen-bar
verdicts are a machine-readable input of packet admission.

The property under test is negative and therefore easy to state and easy to
violate: while counter-label support is below the frozen bar ``4457e971...`` or
geometry below ``a7452748...``, NO packet, owner card, disclosure or state field
may carry ``ready_for_owner_session=true`` or ``human_gate_ready=true``.

Every test here has a non-vacuity control, because a gate that cannot fail is
indistinguishable from a gate that is not wired up.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PRODUCT_ROOT.parent))
sys.path.insert(0, str(PRODUCT_ROOT))

from product.packet_admission import (  # noqa: E402
    DO_NOT_SERVE,
    FORBIDDEN_CLAIM_PATTERNS,
    GEOMETRY_RULES_SHA256,
    LABEL_RULES_SHA256,
    enforce_owner_session,
    evaluate_bars,
    find_forbidden_claims,
    is_admissible,
    packet_admission,
)


def _verdict(**overrides):
    """A minimal accepted verdict whose halves FAIL both frozen bars."""
    base = {
        "team_id": "frontier-served-packet-falsification",
        "team_run_id": "38880639079",
        "accept_commit": "464c45f7e4bf741b6a67adbef35dc587d8cfa21f",
        "covers_this_packet": True,
        "label_half": {"verdict": "LABEL_UNSOUND", "n_scored": 65,
                       "n_supported": 5, "support_rate": 0.076923},
        "geometry_half": {"verdict": "FAIL", "n_bundles": 3, "n_bundles_pass": 0,
                          "pass_counts": {"de": 6, "fr": 5, "it": 5},
                          "french_largest_share": 0.7696},
        "serve_recommendation": f"{DO_NOT_SERVE} this packet unchanged.",
    }
    base.update(overrides)
    return base


def _write(tmp_path: Path, verdict: dict) -> Path:
    p = tmp_path / "verdict.json"
    p.write_text(json.dumps(verdict), encoding="utf-8")
    return p


def test_committed_accepted_verdict_freezes_admission_closed():
    """The real accepted artifact must keep the packet closed, today."""
    d = packet_admission()
    assert d["verdict_team"] == "frontier-served-packet-falsification"
    assert d["verdict_accept_commit"] == "464c45f7e4bf741b6a67adbef35dc587d8cfa21f"
    assert d["verdict_covers_this_packet"] is True
    assert d["admissible"] is False
    assert d["ready_for_owner_session"] is False
    assert d["human_gate_ready"] is False
    assert DO_NOT_SERVE in d["serve_recommendation"]
    assert "accepted_do_not_serve_order" in d["blocked_by"]


def test_both_frozen_bars_are_reported_from_the_accepted_numbers():
    """Bars are reported with their frozen digests and never silently moved."""
    bars = packet_admission()["bars"]
    assert bars["available"] is True
    assert bars["label"]["rules_sha256"] == LABEL_RULES_SHA256
    assert bars["geometry"]["rules_sha256"] == GEOMETRY_RULES_SHA256
    # The accepted recomputation, not a re-derived one.
    assert (bars["label"]["n_scored"], bars["label"]["n_supported"]) == (65, 5)
    assert bars["label"]["meets_absolute_bar"] is False
    assert bars["geometry"]["pass_counts"] == {
        "de-kapitalverletzung": 6, "fr-bail-entretien": 5, "it-responsabilita-medica": 5}
    assert bars["geometry"]["meets_all_criteria_on_every_bundle"] is False
    # Absolute bars are REPORTED, never enforced as a build blocker: the label
    # bar of 1.0 is red on every current artifact by construction, so
    # enforcing it would recreate the never-green loop.
    assert bars["label"]["enforced_as_build_blocker"] is False
    assert bars["geometry"]["enforced_as_build_blocker"] is False


def test_admission_fails_closed_when_no_verdict_is_readable(tmp_path):
    """An unreadable verdict must NOT open the gate (fail closed, not open)."""
    assert packet_admission(tmp_path / "missing.json")["admissible"] is False
    assert packet_admission(tmp_path / "missing.json")["ready_for_owner_session"] is False
    assert "no_accepted_verdict" in packet_admission(tmp_path / "missing.json")["blocked_by"]
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert packet_admission(broken)["admissible"] is False


def test_gate_is_load_bearing_on_a_failing_verdict(tmp_path):
    """NON-VACUITY.  Flipping only the two measured halves -- nothing else --
    must open the gate.  If this control could not fail, the blocking behaviour
    would be an artifact of something other than the bars."""
    path = _write(tmp_path, _verdict())
    assert packet_admission(path)["admissible"] is False

    passing = _verdict(
        label_half={"verdict": "SUPPORTED", "n_scored": 65, "n_supported": 65,
                    "support_rate": 1.0},
        geometry_half={"verdict": "PASS", "n_bundles": 3, "n_bundles_pass": 3,
                       "pass_counts": {"de": 11, "fr": 11, "it": 11},
                       "french_largest_share": 0.41},
        serve_recommendation="SERVE this packet.",
    )
    path = _write(tmp_path, passing)
    d = packet_admission(path)
    assert d["admissible"] is True
    assert d["ready_for_owner_session"] is True
    assert d["human_gate_ready"] is True
    assert d["blocked_by"] == []


def test_a_do_not_serve_order_alone_keeps_admission_closed(tmp_path):
    """The DO-NOT-SERVE order is an INDEPENDENT block: even with both bars
    green, a verdict that says do-not-serve keeps the packet closed."""
    passing = _verdict(
        label_half={"verdict": "SUPPORTED", "n_scored": 65, "n_supported": 65,
                    "support_rate": 1.0},
        geometry_half={"verdict": "PASS", "n_bundles": 3, "n_bundles_pass": 3,
                       "pass_counts": {"de": 11, "fr": 11, "it": 11}},
        serve_recommendation=f"{DO_NOT_SERVE} this packet unchanged.",
    )
    d = packet_admission(_write(tmp_path, passing))
    assert d["bars"]["label"]["meets_absolute_bar"] is True
    assert d["bars"]["geometry"]["meets_all_criteria_on_every_bundle"] is True
    assert d["admissible"] is False
    assert d["blocked_by"] == ["accepted_do_not_serve_order"]


def test_each_bar_alone_can_block_admission(tmp_path):
    """Neither half can be dropped silently."""
    label_only = _verdict(
        serve_recommendation="SERVE this packet.",
        geometry_half={"verdict": "PASS", "n_bundles": 3, "n_bundles_pass": 3},
    )
    d = packet_admission(_write(tmp_path, label_only))
    assert d["blocked_by"] == ["counter_label_support_below_absolute_bar"]

    geometry_only = _verdict(
        serve_recommendation="SERVE this packet.",
        label_half={"verdict": "SUPPORTED", "n_scored": 65, "n_supported": 65,
                    "support_rate": 1.0},
    )
    d = packet_admission(_write(tmp_path, geometry_only))
    assert d["blocked_by"] == ["geometry_below_frozen_bar"]


def test_finalize_summary_cannot_claim_owner_readiness_while_bars_are_unmet():
    """The concrete defect obligation (1) exists to prevent.

    A packet that passes EVERY run-time guard in live mode is exactly the shape
    that used to carry ``ready_for_owner_session=true`` while both accepted
    bars were unmet.
    """
    from gate_packet import finalize_summary

    summary = {"questions": [
        {"qid": qid, "status": "admissible", "guards_ok": True}
        for qid in ("de", "fr", "it")
    ]}
    out = finalize_summary(summary, 3, "live")
    assert out["ok"] is True and out["guards_all_ok"] is True
    assert out["packet_admission"]["run_time_ready_for_owner_session_before_gate"] is True
    assert out["packet_admission"]["gate_applied"] is True
    assert out["ready_for_owner_session"] is False


def test_enforce_owner_session_never_invents_readiness():
    """It can only ever close the field, never open one a caller set."""
    assert enforce_owner_session({"ready_for_owner_session": True})[
        "ready_for_owner_session"] is False
    assert enforce_owner_session({"ready_for_owner_session": False})[
        "ready_for_owner_session"] is False
    assert enforce_owner_session({})["ready_for_owner_session"] is False
    assert enforce_owner_session({"ready_for_owner_session": True})[
        "packet_admission"]["gate_applied"] is True


def test_forbidden_claim_constructions_are_detected():
    """Direction obligation (3): never assert a decision IS supporting etc."""
    # Patterns are carried verbatim from the accepted verdict.
    assert len(FORBIDDEN_CLAIM_PATTERNS) == 5
    assert is_admissible() is False  # sanity: the gate is currently closed

    for text, should_hit in [
        ("Decision bger_4A_219_2015 is supporting the answer.", True),
        ("Decision bger_4A_219_2015 is not limiting the duty.", True),
        ("bge_BGE_142_IV_333 is a supporting authority.", True),
        ("We classify bger_4A_219_2015 as contrary.", True),
        ("The measurement asserts that bger_6B_31_2019 is limiting.", True),
        # Legitimate product prose must NOT trip the gate.
        ("The counter-authority pass labelled 65 rows; 5 carry cited evidence "
         "and 60 do not. Inspect each row individually.", False),
        ("Unevidenced-count: 16 labels carry no cited evidence at uncertainty "
         "0.95-1.0.", False),
    ]:
        hits = find_forbidden_claims(text)
        assert bool(hits) is should_hit, (text, hits)


def test_evaluate_bars_reports_absence_rather_than_guessing():
    assert evaluate_bars(None)["available"] is False
    # An empty verdict has no halves: it reports available=False rather than
    # inventing measured numbers, and both bars read as unmet (fail closed).
    empty = evaluate_bars({})
    assert empty["available"] is False
    assert empty["label"]["meets_absolute_bar"] is False
    assert empty["geometry"]["meets_all_criteria_on_every_bundle"] is False