"""Factory direction v50, product obligation (1): the two accepted frozen bars
are a MACHINE-READABLE input of packet admission.

While counter-label support (frozen rubric 4457e971...) or map-geometry
minimum semantics (frozen rule a7452748...) is unmet, no packet, owner card,
disclosure or state field may claim ready_for_owner_session=true or
human_gate_ready=true.

These tests pin: the accepted snapshot is the only source; the frozen rule
digests must be identifiable in it; a failing bar blocks admission with the
reason recorded; a MET bar does not block (positive control, so the gate cannot
be silently sticky); an unreadable source fails CLOSED; and the owner card
prints the admission block.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "product") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "product"))

from product.query import bar_admission as ba  # noqa: E402
import gate_packet as gp  # noqa: E402

ACCEPTED_BARS_OUT = REPO_ROOT / "results" / "product" / "bar_admission" / "ACCEPTED_BARS.json"


def _synthetic_snapshot(*, support: int = 5, scored: int = 65,
                        bundles_pass: int = 0, bundles: int = 3) -> dict:
    return {
        "team_run_id": "38880639079",
        "status": "PROMOTED",
        "measured_packet": "gate_packet/synthetic-control",
        "serve_recommendation": "SERVE (synthetic control only)",
        "label_half": {
            "verdict": "LABEL_SOUND" if support == scored else "LABEL_UNSOUND",
            "n_scored": scored, "n_supported": support,
            "support_rate": support / scored if scored else 0.0,
            "claim_text": f"frozen rubric rules_sha256 {ba.LABEL_RULES_SHA256} measured",
        },
        "geometry_half": {
            "verdict": "PASS" if bundles_pass == bundles else "FAIL",
            "n_bundles_pass": bundles_pass, "n_bundles": bundles,
            "pass_counts": {"a": 11, "b": 11, "c": 11},
            "baseline_pass_counts": {"a": 5, "b": 5, "c": 4},
            "french_largest_share": 0.2, "french_bar": 0.6,
            "claim_text": f"frozen rule rules_sha256 {ba.GEOMETRY_RULES_SHA256} measured",
        },
    }


@pytest.fixture()
def snapshot(tmp_path: Path) -> Path:
    p = tmp_path / "snapshot.json"
    p.write_text(json.dumps(_synthetic_snapshot()), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# 1. the accepted bars, as consumed
# --------------------------------------------------------------------------- #
def test_accepted_bars_are_unmet_and_carried_machine_readably() -> None:
    bars = ba.accepted_bars()
    assert bars["schema"] == ba.SCHEMA
    assert bars["all_bars_met"] is False
    assert set(bars["unmet_bars"]) == {"counter_label_support", "map_geometry_semantics"}
    label = bars["bars"]["counter_label_support"]
    assert label["rules_sha256"] == ba.LABEL_RULES_SHA256
    assert label["n_scored"] == 65 and label["n_supported"] == 5
    assert label["met"] is False
    geometry = bars["bars"]["map_geometry_semantics"]
    assert geometry["rules_sha256"] == ba.GEOMETRY_RULES_SHA256
    assert geometry["n_bundles_pass"] == 0 and geometry["n_bundles"] == 3
    assert geometry["met"] is False
    assert "DO-NOT-SERVE" in str(bars["serve_recommendation"])


def test_the_machine_readable_artifact_on_disk_matches_the_accepted_bars() -> None:
    assert ACCEPTED_BARS_OUT.is_file(), (
        "the machine-readable bar input must be published under results/product/")
    on_disk = json.loads(ACCEPTED_BARS_OUT.read_text(encoding="utf-8"))
    assert on_disk == ba.accepted_bars()


def test_a_snapshot_without_the_frozen_rule_digest_is_refused(tmp_path: Path) -> None:
    snap = _synthetic_snapshot()
    snap["label_half"]["claim_text"] = "some other rubric, no frozen digest here"
    p = tmp_path / "snap.json"
    p.write_text(json.dumps(snap), encoding="utf-8")
    with pytest.raises(ba.BarSourceError, match="counter_label_support"):
        ba.accepted_bars(p)


def test_a_missing_or_foreign_snapshot_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ba.BarSourceError, match="missing"):
        ba.accepted_bars(tmp_path / "nope.json")
    foreign = tmp_path / "foreign.json"
    foreign.write_text(json.dumps({"team_run_id": "1", "status": "PROMOTED"}), encoding="utf-8")
    with pytest.raises(ba.BarSourceError, match="not the accepted"):
        ba.accepted_bars(foreign)


# --------------------------------------------------------------------------- #
# 2. admission enforcement
# --------------------------------------------------------------------------- #
def test_enforcement_forces_ready_false_and_records_why(snapshot: Path) -> None:
    summary = {"ok": True, "guards_all_ok": True, "ready_for_owner_session": True}
    out = ba.enforce_packet_admission(summary, path=snapshot)
    assert out["ready_for_owner_session"] is False
    block = out["ready_for_owner_session_blocked_by_bars"]
    assert block["would_have_been_ready"] is True
    assert set(block["unmet_bars"]) == {"counter_label_support", "map_geometry_semantics"}
    assert out["accepted_bars"]["source_snapshot"]["sha256"]


def test_enforcement_leaves_a_ready_packet_alone_when_both_bars_are_met(tmp_path: Path) -> None:
    p = tmp_path / "met.json"
    p.write_text(json.dumps(_synthetic_snapshot(support=65, bundles_pass=3)), encoding="utf-8")
    summary = {"ok": True, "guards_all_ok": True, "ready_for_owner_session": True}
    out = ba.enforce_packet_admission(summary, path=p)
    assert out["ready_for_owner_session"] is True
    assert out["accepted_bars"]["all_bars_met"] is True
    assert "ready_for_owner_session_blocked_by_bars" not in out


def test_a_single_unsupported_label_is_enough_to_block(tmp_path: Path) -> None:
    p = tmp_path / "one_bad.json"
    p.write_text(json.dumps(_synthetic_snapshot(support=64, bundles_pass=3)), encoding="utf-8")
    out = ba.enforce_packet_admission({"ready_for_owner_session": True}, path=p)
    assert out["ready_for_owner_session"] is False
    assert out["accepted_bars"]["unmet_bars"] == ["counter_label_support"]


def test_zero_scored_rows_never_counts_as_a_met_label_bar(tmp_path: Path) -> None:
    """Non-vacuity: an empty scored population must not read as 'all supported'."""
    p = tmp_path / "empty.json"
    p.write_text(json.dumps(_synthetic_snapshot(scored=0, support=0)), encoding="utf-8")
    bars = ba.accepted_bars(p)
    assert bars["bars"]["counter_label_support"]["met"] is False


# --------------------------------------------------------------------------- #
# 3. gate_packet integration
# --------------------------------------------------------------------------- #
def test_gate_packet_owner_card_prints_the_admission_block() -> None:
    card = gp.owner_card(
        {"packet_dir": "results/product/gate_packet/38839347028", "questions": []},
        base_url="http://127.0.0.1:8791", top_n=150)
    assert "Accepted frozen bars (packet-admission input" in card
    assert "ADMISSION: BLOCKED" in card
    assert "counter-label support" in card and "map-geometry semantics" in card


def test_gate_packet_module_exposes_the_bar_gate() -> None:
    src = (REPO_ROOT / "product" / "gate_packet.py").read_text(encoding="utf-8")
    assert "enforce_packet_admission" in src
    assert src.count("enforce_packet_admission") >= 2  # preflight AND recheck
