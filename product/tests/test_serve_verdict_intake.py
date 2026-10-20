"""Serve-verdict intake for packet-of-record V3 (direction v59 ordered work 1 + note b).

What is locked here
-------------------
1. The committed intake discloses PENDING_VERDICT fail-closed (the chartered
   frontier-packet-serve-audit has not produced an accepted verdict).
2. Packet admission consumes the serve channel as a machine gate INPUT: an
   accepted DO-NOT-SERVE covering the packet denies admission even when both
   frozen bars would otherwise pass (positive control with synthetic bars).
3. A pending or non-accepted serve verdict NEVER opens
   ready_for_owner_session / human_gate_ready and NEVER clears the frozen bars.
4. The packet-of-record pin is the exact V3 raw sha256; harvest refuses to
   overwrite an accepted intake (append-only evidence).
5. Existing standing DO-NOT-SERVE orders are named, not edited.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import packet_admission as pa  # noqa: E402
from product.query import serve_verdict as sv  # noqa: E402

INTAKE = ROOT / "results" / "product" / "frontier_verdicts" / "frontier-packet-serve-audit_intake.json"
V3_PACKET = ROOT / "results" / "product" / "gate_packet" / "39319405429" / "packet.json"


def _bars_snapshot(label_supported: int, label_scored: int,
                   geometry_pass: int, geometry_bundles: int) -> dict:
    return {
        "team_run_id": "synthetic-bars",
        "measured_packet": "gate_packet/39319405429",
        "label_half": {
            "verdict": "LABEL_SOUND" if label_supported == label_scored else "LABEL_UNSOUND",
            "n_scored": label_scored,
            "n_supported": label_supported,
            "support_rate": label_supported / label_scored,
        },
        "geometry_half": {
            "verdict": "PASS" if geometry_pass == geometry_bundles else "FAIL",
            "n_bundles_pass": geometry_pass,
            "n_bundles": geometry_bundles,
            "pass_counts": {"de": 11, "fr": 11, "it": 11},
        },
    }


def _serve_intake(
    *,
    status: str = "ACCEPTED_VERDICT",
    accepted: bool = True,
    rec: str | None = "DO-NOT-SERVE-UNCHANGED",
    measured_sha: str | None = None,
    owner_dec: bool | None = False,
) -> dict:
    return {
        "schema": sv.SCHEMA,
        "team_id": "frontier-packet-serve-audit",
        "status": status,
        "accepted": accepted,
        "evidence_tier": "ACCEPTED" if accepted else "REPRODUCED",
        "serve_recommendation": rec,
        "owner_decision_required": owner_dec,
        "packet_measured": {
            "packet_run_id": "39319405429",
            "packet_json_raw_sha256": measured_sha
            or sv.PACKET_OF_RECORD_V3["packet_json_raw_sha256"],
        },
    }


# --------------------------------------------------------------------------- #
# committed pending intake
# --------------------------------------------------------------------------- #

def test_committed_intake_is_pending_and_fail_closed() -> None:
    d = json.loads(INTAKE.read_text(encoding="utf-8"))
    assert d["schema"] == sv.SCHEMA
    assert d["team_id"] == "frontier-packet-serve-audit"
    assert d["status"] == "PENDING_VERDICT"
    assert d["accepted"] is False
    assert d["serve_recommendation"] is None
    assert d["owner_decision_required"] is None
    assert d["packet_measured"]["packet_json_raw_sha256"] == (
        "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
    )
    assert d["charter_observed"]["team_state_cycle_status"] == "INITIALIZED"
    assert d["charter_observed"]["accepted_run_id"] is None


def test_packet_of_record_bytes_still_match_the_pin() -> None:
    assert sv.packet_sha256_on_disk() == sv.PACKET_OF_RECORD_V3["packet_json_raw_sha256"]
    assert V3_PACKET.exists()


def test_current_serve_channel_discloses_pending_without_opening_owner_gate() -> None:
    out = sv.assess_for_packet()
    assert out["status"] == "PENDING_VERDICT"
    assert out["accepted"] is False
    assert out["deny_for_recommendation"] is False
    assert out["owner_decision_required_authorises_session"] is False
    assert "serve_audit_pending" in (out["blocking_reason"] or "")
    assert out["packet_pin"]["on_disk_matches_pin"] is True
    assert out["packet_pin"]["covers_this_packet"] is True


def test_live_admission_stays_fail_closed_and_carries_the_serve_channel() -> None:
    adm = pa.assess()
    assert adm["packet_admitted"] is False
    assert adm["ready_for_owner_session_allowed"] is False
    assert adm["serve_audit"]["status"] == "PENDING_VERDICT"
    assert adm["serve_audit"]["accepted"] is False
    # frozen bars remain the binding denial on live snapshots
    assert "5/65" in adm["blocking_reason"]
    assert "0/3" in adm["blocking_reason"]


# --------------------------------------------------------------------------- #
# serve channel as machine gate input
# --------------------------------------------------------------------------- #

def test_accepted_do_not_serve_denies_even_when_bars_would_pass() -> None:
    bars = _bars_snapshot(65, 65, 3, 3)
    serve = _serve_intake(rec="DO-NOT-SERVE-UNCHANGED", accepted=True)
    adm = pa.assess(
        snapshots=[("synthetic", bars)],
        serve_assessment=sv.assess_for_packet(intake=serve),
    )
    assert adm["bars"]["counter_label"]["satisfied"] is True
    assert adm["bars"]["map_geometry"]["satisfied"] is True
    assert adm["packet_admitted"] is False
    assert adm["ready_for_owner_session_allowed"] is False
    assert "DO-NOT-SERVE-UNCHANGED" in adm["blocking_reason"]
    assert adm["serve_audit"]["deny_for_recommendation"] is True


def test_accepted_serve_recommendation_alone_never_opens_unmet_bars() -> None:
    bars = _bars_snapshot(5, 65, 0, 3)
    serve = _serve_intake(rec="SERVE", accepted=True)
    adm = pa.assess(
        snapshots=[("synthetic", bars)],
        serve_assessment=sv.assess_for_packet(intake=serve),
    )
    assert adm["packet_admitted"] is False
    assert "5/65" in adm["blocking_reason"]
    assert adm["serve_audit"]["deny_for_recommendation"] is False


def test_non_accepted_verdict_never_denies_and_never_opens() -> None:
    bars = _bars_snapshot(65, 65, 3, 3)
    serve = _serve_intake(rec="DO-NOT-SERVE-UNCHANGED", accepted=False, status="REPRODUCED_VERDICT")
    out = sv.assess_for_packet(intake=serve)
    assert out["deny_for_recommendation"] is False
    assert out["accepted"] is False
    assert "serve_verdict_not_accepted" in (out["blocking_reason"] or "")
    adm = pa.assess(
        snapshots=[("synthetic", bars)],
        serve_assessment=out,
    )
    # non-accepted DO-NOT-SERVE does not deny (not accepted evidence);
    # bars alone open the synthetic positive control.
    assert adm["packet_admitted"] is True


def test_pending_serve_with_open_bars_is_not_a_silent_pass_channel() -> None:
    """Pending is disclosed; it neither denies nor claims serve readiness."""
    bars = _bars_snapshot(65, 65, 3, 3)
    adm = pa.assess(
        snapshots=[("synthetic", bars)],
        serve_assessment=sv.assess_for_packet(intake=_serve_intake(
            status="PENDING_VERDICT", accepted=False, rec=None,
        )),
    )
    assert adm["packet_admitted"] is True  # bars are the open gate here
    assert adm["serve_audit"]["status"] == "PENDING_VERDICT"
    assert adm["serve_audit"]["owner_decision_required_authorises_session"] is False


def test_offending_owner_claims_while_serve_pending() -> None:
    record = {
        "ready_for_owner_session": True,
        "human_gate_ready": True,
    }
    # live bars are unmet, so owner claims are offending regardless of serve
    out = pa.offending_owner_claims(record)
    assert "ready_for_owner_session" in out
    assert "human_gate_ready" in out


# --------------------------------------------------------------------------- #
# harvest append-only contract
# --------------------------------------------------------------------------- #

def test_harvest_refuses_to_overwrite_an_accepted_intake(tmp_path: Path) -> None:
    # Simulate an already-accepted intake in a temp module path by monkeypatching
    # only the write target — never touch the committed pending file.
    src = tmp_path / "verdict.json"
    src.write_text(json.dumps({
        "team_id": "frontier-packet-serve-audit",
        "serve_recommendation": "DO-NOT-SERVE-UNCHANGED",
        "packet_json_raw_sha256": sv.PACKET_OF_RECORD_V3["packet_json_raw_sha256"],
        "owner_decision_required": False,
    }), encoding="utf-8")

    original = sv.INTAKE_PATH
    try:
        sv.INTAKE_PATH = tmp_path / "intake.json"
        # pending first
        sv.harvest(src, accepted=False, overwrite=True)
        assert json.loads(sv.INTAKE_PATH.read_text())["accepted"] is False
        # accepted second
        sv.harvest(src, accepted=True, overwrite=True)
        assert json.loads(sv.INTAKE_PATH.read_text())["accepted"] is True
        # third accepted harvest must refuse
        try:
            sv.harvest(src, accepted=True, overwrite=False)
            raised = False
        except SystemExit as exc:
            raised = True
            assert "refusing to overwrite" in str(exc)
        assert raised, "accepted intake must be append-only"
    finally:
        sv.INTAKE_PATH = original


def test_missing_intake_file_fails_closed() -> None:
    original = sv.INTAKE_PATH
    try:
        sv.INTAKE_PATH = Path("/nonexistent/serve_intake.json")
        out = sv.assess_for_packet()
        assert out["accepted"] is False
        assert out["deny_for_recommendation"] is False
        assert "serve_audit_pending" in (out["blocking_reason"] or "")
    finally:
        sv.INTAKE_PATH = original
