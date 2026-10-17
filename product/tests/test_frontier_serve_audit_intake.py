"""Honest-state invariants for the frontier-rebuilt-packet-serve-audit verdict intake.

Factory direction v55 ordered the product lane to record the CURRENT acceptance status
of the frontier-rebuilt-packet-serve-audit verdict and to keep the OUTCOME-B route-around
PENDING until that verdict is independently accepted. The verdict was measured as
outcome (B) DO-NOT-SERVE-UNCHANGED but its independent audit (run 39053132092) returned
gate=REVISE with 4 required fixes, so it is REPRODUCED, NOT accepted.

These tests lock the honest-state invariants so a future cycle cannot:
  * cite the verdict as accepted evidence or as superseding the DO-NOT-SERVE order;
  * fire the OUTCOME-B route-around (record the accepted negative / carry the owner
    question) before the verdict is independently accepted;
  * carry ready_for_owner_session=true or human_gate_ready=true while either frozen
    bar is unmet;
  * state the label-bar status without the BY-INSTRUMENT/TEXT reading required by
    independent audit FIX-3.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "product") not in sys.path:
    sys.path.insert(0, str(ROOT / "product"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INTAKE_RECORD = ROOT / "results" / "product" / "frontier_verdicts" / "frontier-rebuilt-packet-serve-audit_intake.json"
PRODUCT_STATE = ROOT / "state" / "product.json"
REBUILT_PACKET = ROOT / "results" / "product" / "gate_packet" / "rebuilt-39027045675" / "packet.json"

EXPECTED_PACKET_SHA256 = "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_intake_record_exists_and_marks_verdict_not_accepted() -> None:
    d = _load(INTAKE_RECORD)
    assert d["schema"] == "product-frontier-verdict-intake/rebuilt-packet-serve-audit/1"
    assert d["team_id"] == "frontier-rebuilt-packet-serve-audit"
    assert d["evidence_tier"] == "REPRODUCED"
    assert d["accepted"] is False
    assert d["verdict"]["charter_outcome"] == "B"
    assert d["verdict"]["serve_recommendation"] == "DO-NOT-SERVE-UNCHANGED"


def test_independent_audit_recorded_as_revise_with_four_fixes() -> None:
    d = _load(INTAKE_RECORD)
    audit = d["independent_audit"]
    assert audit["run_id"] == "39053132092"
    assert audit["gate"] == "REVISE"
    assert audit["safe_to_integrate"] is False
    fix_ids = {f["id"] for f in audit["required_fixes"]}
    assert fix_ids == {"FIX-1", "FIX-2", "FIX-3", "FIX-4"}


def test_route_around_pending_not_fired() -> None:
    d = _load(INTAKE_RECORD)
    ra = d["route_around"]
    assert ra["status"] == "PENDING_ACCEPTANCE_NOT_FIRED"
    # the trigger is an independent ACCEPTED verdict; a REVISE verdict does not fire it
    assert "independently" in ra["trigger_condition"].lower()
    # prohibited actions are still recorded as prohibitions, not done
    assert "re-build the packet" in ra["actions_prohibited"]
    assert "re-run geometry or classifier work" in ra["actions_prohibited"]


def test_do_not_serve_order_in_force() -> None:
    d = _load(INTAKE_RECORD)
    dns = d["do_not_serve_order"]
    assert dns["status"] == "IN_FORCE"
    # neither supersession condition is met
    assert dns["current_state"] == (
        "Neither supersession condition is met: the rebuilt packet's geometry bar is unmet "
        "(0/3 at 11/11) and the frontier verdict is REVISE (not accepted). The order stands."
    )


def test_admission_fail_closed() -> None:
    d = _load(INTAKE_RECORD)
    pos = d["product_position"]
    assert pos["machine_gate_ready"] is False
    assert pos["human_gate_ready"] is False
    assert pos["ready_for_owner_session"] is False
    assert pos["packet_admitted"] is False
    assert "fail-closed" in pos["admission"]


def test_owner_question_prepared_not_fired() -> None:
    d = _load(INTAKE_RECORD)
    oq = d["owner_question"]
    assert oq["status"] == "PREPARED_NOT_FIRED"
    # the question is recorded but explicitly NOT presented to the owner now
    assert "NOT presented to the owner now" in oq["why_prepared_not_fired"]


def test_label_bar_reading_nuance_by_instrument() -> None:
    d = _load(INTAKE_RECORD)
    nuance = d["route_around"]["label_bar_reading_nuance"]
    assert nuance["instrument_reading"].startswith("LABEL_SOUND")
    assert "INSUFFICIENT_POPULATION" in nuance["frozen_rules_text_residual"]
    # both readings present; never an unqualified 'met'
    assert "BY INSTRUMENT/TEXT" in nuance["note"]


def test_three_numbers_published_together() -> None:
    d = _load(INTAKE_RECORD)
    three = d["core_evaluation_adjudication"]["three_numbers_required_together"]
    assert three["support_rate_among_issued_labels_frozen_rubric"] == 1.0
    assert three["abstention_count"] == 60
    assert abs(three["yield_on_packet_row_population"] - 0.07692307692307693) < 1e-12


def test_core_evaluation_adjudication_recorded_as_existing_not_accepted() -> None:
    d = _load(INTAKE_RECORD)
    ce = d["core_evaluation_adjudication"]
    assert ce["run_id"] == "39049030442"
    # the adjudication EXISTS (contra the frontier team's false ABSENT claim) but is not accepted
    assert ce["packet_json_raw_sha256"] == EXPECTED_PACKET_SHA256
    assert "NOT independently accepted" in ce["acceptance_status"]
    assert ce["headline"]["label_absolute_status"] == "LABEL_SOUND"
    assert ce["headline"]["geometry_absolute_status"] == "GEOMETRY_UNSOUND"
    assert ce["headline"]["n_bundles_pass_all_11"] == 0
    assert ce["headline"]["packet_admitted"] is False


def test_product_state_carries_no_owner_readiness_claim() -> None:
    d = _load(PRODUCT_STATE)
    assert d["machine_gate_ready"] is False
    assert d["human_gate_ready"] is False
    assert d["continue_recommended"] is True
    cycle_key = "cycle_39056694835_frontier_serve_audit_intake"
    assert cycle_key in d
    assert d[cycle_key]["route_around_status"] == "PENDING_ACCEPTANCE_NOT_FIRED"
    assert d[cycle_key]["do_not_serve_order"] == "IN_FORCE"
    assert d[cycle_key]["verdict_status"]["accepted"] is False


def test_rebuilt_packet_bytes_unchanged() -> None:
    import hashlib

    raw = REBUILT_PACKET.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_PACKET_SHA256
    d = _load(REBUILT_PACKET)
    # the rebuilt packet itself carries no owner-readiness claim
    assert d["ready_for_owner_session"] is False
    assert d["packet_admission"]["packet_admitted"] is False
    assert d["packet_admission"]["ready_for_owner_session_allowed"] is False
    assert d["packet_admission_blocked"] is True
