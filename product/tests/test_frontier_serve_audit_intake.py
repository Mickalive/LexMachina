"""Honest-state invariants for the frontier-rebuilt-packet-serve-audit verdict intake.

WHAT CHANGED IN THIS MODULE, and why (factory direction v56, RF0)
-----------------------------------------------------------------
Five assertions below used to encode the PRE-ACCEPTANCE state: the verdict was
"not accepted", its audit was "REVISE with four fixes", the route-around was
"PENDING_ACCEPTANCE_NOT_FIRED" and the owner question was "PREPARED_NOT_FIRED".

All five had to move, because the underlying facts moved first:

  * the team's verdict was independently ACCEPTED at run 39061330426
    (gate=PASS, safe_to_integrate=true, required_fixes=[]), so "not accepted"
    became false; and
  * the accepted verdict carries owner_decision_required=FALSE, so the staged
    owner question rested on a FALSE claim and had to be deleted, not merely
    downgraded.

Those tests were not deleted. Each was re-pointed at the new truth and kept its
guard intent, because the underlying hazard never went away: the DO-NOT-SERVE
order still stands, admission is still fail-closed, and the label bar still must
be read BY INSTRUMENT/TEXT. What changed is WHICH direction the guard points.

The invariants this module still locks, so a future cycle cannot:
  * treat the now-ACCEPTED verdict as superseding the DO-NOT-SERVE order
    (acceptance of a DO-NOT-SERVE verdict is not a supersession of a DO-NOT-SERVE
    order - this is the subtle one);
  * re-stage or fire the map-versus-ranked-list owner question on this verdict;
  * carry ready_for_owner_session=true or human_gate_ready=true while either
    frozen bar is unmet;
  * state the label-bar status without the BY-INSTRUMENT/TEXT reading required by
    independent audit FIX-3;
  * delete the historical REVISE audit, which is evidence of the repair chain.

The companion module tests/test_no_owner_question_from_accepted_verdict.py holds
the executable guard on the withdrawal itself.
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


# --------------------------------------------------------------------------- #
# acceptance status
# --------------------------------------------------------------------------- #

def test_intake_record_records_the_accepted_verdict() -> None:
    """The verdict IS accepted as evidence now (audit run 39061330426, gate=PASS).

    Being ACCEPTED means the negative is evidence. It does NOT make the packet
    servable - the serve recommendation is unchanged.
    """
    d = _load(INTAKE_RECORD)
    assert d["schema"] == "product-frontier-verdict-intake/rebuilt-packet-serve-audit/2"
    assert d["team_id"] == "frontier-rebuilt-packet-serve-audit"
    assert d["evidence_tier"] == "ACCEPTED"
    assert d["accepted"] is True
    assert d["verdict"]["charter_outcome"] == "B"
    assert d["verdict"]["serve_recommendation"] == "DO-NOT-SERVE-UNCHANGED", (
        "accepting the verdict must not change its serve recommendation"
    )
    assert d["verdict"]["owner_decision_required"] is False


def test_accepted_audit_is_primary_and_the_revise_audit_is_preserved() -> None:
    """The REVISE audit is HISTORY, not deleted: it is the repair chain's evidence."""
    d = _load(INTAKE_RECORD)
    audit = d["independent_audit"]
    assert audit["run_id"] == "39061330426"
    assert audit["gate"] == "PASS"
    assert audit["safe_to_integrate"] is True
    assert audit["required_fixes"] == []

    history = d["independent_audit_history"]
    assert history, "the REVISE audit must be preserved, not overwritten"
    old = history[0]
    assert old["run_id"] == "39053132092"
    assert old["gate"] == "REVISE"
    assert old["safe_to_integrate"] is False
    assert {f["id"] for f in old["required_fixes"]} == {
        "FIX-1", "FIX-2", "FIX-3", "FIX-4"
    }


def test_team_is_terminated_not_rerun() -> None:
    """A team that reached its stop rule must not be re-dispatched."""
    d = _load(INTAKE_RECORD)
    assert d["team_state"]["cycle_status"] == "COMPLETE"
    assert d["team_state"]["continue_recommended"] is False
    assert d["team_state"]["portfolio_status"] == "TERMINATED"
    assert d["team_state"]["accepted_commit"] == "26582bc5"
    assert isinstance(d["team_state"]["accepted_run_id"], str)


def test_core_evaluation_adjudication_is_not_promoted_by_the_acceptance() -> None:
    """Accepting the FRONTIER verdict does not accept Evaluation's separate run.

    Two different lanes, two different audits. Core Evaluation's run 39049030442 was
    never independently accepted, and the frontier verdict's acceptance says nothing
    about it. Conflating the two would launder an unaudited record.
    """
    d = _load(INTAKE_RECORD)
    ce = d["core_evaluation_adjudication"]
    assert "NOT independently accepted" in ce["acceptance_status"]
    assert d["accepted"] is True, "the frontier verdict IS accepted"
    # ... yet Evaluation's own record is still not. Both facts hold at once.
    assert ce["run_id"] == "39049030442"
    assert int(ce["run_id"]) != int(d["independent_audit"]["run_id"])


# --------------------------------------------------------------------------- #
# route-around and owner question
# --------------------------------------------------------------------------- #

def test_route_around_recorded_fail_closed_with_no_owner_question() -> None:
    """The route-around fired on acceptance, but only the fail-closed half.

    Recording the accepted negative and keeping admission closed are correct and
    required. Carrying the owner question was not, and is now named as withdrawn.
    """
    d = _load(INTAKE_RECORD)
    ra = d["route_around"]
    assert ra["status"] == "RECORDED_FAIL_CLOSED_NO_OWNER_QUESTION"
    assert ra["superseded_status"] == "TRIGGERED_AND_FIRED", (
        "the superseded firing stays named so the withdrawal is auditable"
    )
    assert "independently" in ra["trigger_condition"].lower()
    # the accepted negative WAS recorded and admission WAS kept closed
    assert any("accepted negative" in a for a in ra["actions_fired"])
    # the owner question WAS withdrawn, and is named as prohibited
    assert any("owner" in a.lower() and "question" in a.lower()
               for a in ra["actions_prohibited"])
    # prohibited actions are still recorded as prohibitions
    assert "re-build the packet" in ra["actions_prohibited"]
    assert "re-run geometry or classifier work" in ra["actions_prohibited"]


def test_owner_question_withdrawn_never_to_fire_on_this_verdict() -> None:
    """The staged question is DELETED, because its justification was false.

    It claimed the accepted verdict "converts the map-versus-ranked-list choice
    into ONE explicit owner product decision". The accepted verdict says the
    opposite. Downgrading the status would leave the claim standing; the direction
    ordered deletion.
    """
    d = _load(INTAKE_RECORD)
    oq = d["owner_question"]
    assert oq["status"] == "WITHDRAWN_NOT_FIRED_NEVER_TO_FIRE_ON_THIS_VERDICT"
    assert oq["question"] is None, "the question text must be deleted"
    assert oq["question_deleted"] is True
    assert "owner_decision_required" in oq["question_deleted_reason"]
    for key in ("requirement_13_condition_a", "requirement_13_condition_b"):
        assert oq["supersession_conditions"][key]["met"] is False


def test_do_not_serve_order_in_force_after_acceptance() -> None:
    """Accepting a DO-NOT-SERVE verdict does NOT supersede a DO-NOT-SERVE order.

    This is the subtle trap. The trigger fired - the verdict is now accepted
    evidence - yet neither supersession condition is met, so the order stands
    unreviewed rather than being lifted.
    """
    d = _load(INTAKE_RECORD)
    dns = d["do_not_serve_order"]
    assert dns["status"] == "IN_FORCE"
    assert "order stands" in dns["current_state"].lower()
    assert "(a) is unmet" in dns["current_state"]
    assert "(b) is unmet" in dns["current_state"]
    # and the pre-acceptance reading is kept, so the change is auditable
    hist = dns["status_history"]
    assert "39053132092" in hist["v1_2026_10_17"]
    assert "39061330426" in hist["v2_this_cycle"]


def test_admission_fail_closed() -> None:
    d = _load(INTAKE_RECORD)
    pos = d["product_position"]
    assert pos["machine_gate_ready"] is False
    assert pos["human_gate_ready"] is False
    assert pos["ready_for_owner_session"] is False
    assert pos["packet_admitted"] is False
    assert "fail-closed" in pos["admission"]


# --------------------------------------------------------------------------- #
# unchanged invariants
# --------------------------------------------------------------------------- #

def test_label_bar_reading_nuance_by_instrument() -> None:
    """Unchanged by RF0 - the FIX-3 BY-INSTRUMENT/TEXT requirement still binds."""
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
    # The cycle_39056694835_* block is a HISTORICAL record of that cycle's state and
    # is deliberately left untouched: it said the verdict was not accepted, which was
    # true on that day. Rewriting it to match today would destroy the record that the
    # verdict was later accepted.
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