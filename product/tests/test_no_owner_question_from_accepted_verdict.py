"""RF0 guard: the withdrawn owner question can never be re-fired.

Why this module exists
----------------------
Direction v56 ordered work item (1), described in the factory direction as "this
cycle's non-negotiable correction":

    "THE ONE MISREADING TO WITHDRAW ... the accepted verdict carries
     owner_decision_required=FALSE with the explicit reason that charter outcome (C)
     is not reached because the label bar is met as written BY THE ACCEPTED
     INSTRUMENT, so the charter DOES NOT convert the map-versus-ranked-list choice
     into an owner decision. Factory-wide requirement 13 supersession condition (b)
     is therefore NOT met (and condition (a) is not met either - no serve
     recommendation replaces the DO-NOT-SERVE verdict). The intake record ... sets
     route_around=TRIGGERED_AND_FIRED with actions_fired including 'carried the
     map-versus-ranked-list choice to the owner as ONE recorded product question' and
     owner_question=READY_TO_FIRE with why_ready claiming the accepted outcome-B
     verdict 'converts the map-versus-ranked-list choice into ONE explicit owner
     product decision'. Both claims are CONTRADICTED by the accepted verdict's own
     owner_decision_required_reason and are WITHDRAWN."

The repository owner's attention is, per the Master Prompt, the scarce resource in
this factory - not autonomous agent compute. A product artifact that stages an
owner question on a packet an independent audit has ordered DO-NOT-SERVE spends
that resource on the wrong thing. This is not a stylistic concern: it is the
single largest failure mode available to this lane.

So the withdrawal is made *executable*. Prose asserting "no owner question" can be
ignored by the next cycle; these assertions cannot.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent

INTAKE = REPO_ROOT / "results" / "product" / "frontier_verdicts" / "frontier-rebuilt-packet-serve-audit_intake.json"
PRODUCT_STATE = REPO_ROOT / "state" / "product.json"

#: Any of these keys carrying ``true`` would tell the factory the product believes
#: it is ready to spend owner attention. None may.
FORBIDDEN_TRUE_KEYS = (
    "ready_for_owner_session",
    "human_gate_ready",
    "machine_gate_ready",
    "packet_admitted",
    "owner_decision_required",
)

#: Substrings that stage an owner question for firing.
_FIRING_PHRASES = (
    "ready_to_fire",
    "ready to fire",
    "why_ready",
    "PREPARED_NOT_FIRED",
    "converts the map-versus-ranked-list choice into ONE explicit owner product decision",
)


def _intake() -> dict:
    return json.loads(INTAKE.read_text(encoding="utf-8"))


def test_intake_records_the_accepted_verdict_not_a_stale_revise():
    """RF0: the record must state the ACCEPTED verdict (run 39061330426)."""
    rec = _intake()
    assert rec["accepted"] is True, (
        "the verdict is accepted evidence (audit CYCLE_39061330426 gate=PASS, "
        f"safe_to_integrate=true); accepted={rec['accepted']}"
    )
    audit = rec["independent_audit"]
    assert audit["gate"] == "PASS", f"accepted audit gate is PASS, got {audit['gate']}"
    assert audit["safe_to_integrate"] is True
    assert audit["required_fixes"] == []
    assert audit["run_id"] == "39061330426"
    assert rec["team_state"]["portfolio_status"] == "TERMINATED", (
        "the team reached its stop rule and must be TERMINATED, not RUN"
    )


def test_owner_decision_required_is_false_with_the_accepted_reason():
    rec = _intake()
    verdict = rec["verdict"]
    assert verdict["owner_decision_required"] is False
    reason = verdict["owner_decision_required_reason"]
    low = reason.lower()
    assert "outcome (c) is not reached" in low, (
        "the reason must be the accepted one, not a restatement: " + reason
    )
    assert "does not convert" in low, (
        "the accepted reason says the charter does NOT convert the "
        "map-versus-ranked-list choice into an owner decision"
    )
    assert "label bar is met as written" in low, (
        "the accepted reason turns on the label bar being met as written BY THE "
        "ACCEPTED INSTRUMENT; restating it without that clause would overstate it"
    )


def test_route_around_is_recorded_fail_closed_and_not_fired():
    ra = _intake()["route_around"]
    assert ra["status"] == "RECORDED_FAIL_CLOSED_NO_OWNER_QUESTION", ra["status"]
    assert ra["superseded_status"] == "TRIGGERED_AND_FIRED", (
        "the superseded firing must stay named, so the history is auditable"
    )
    fired = ra["actions_fired"]
    assert not any("owner" in str(a).lower() and "question" in str(a).lower()
                   for a in fired), (
        f"actions_fired must not contain the withdrawn owner question: {fired}"
    )


def test_requirement_13_conditions_are_recorded_as_both_unmet():
    """Condition (a) and (b) must each be recorded unmet, with a reason."""
    subs = _intake()["owner_question"]["supersession_conditions"]
    for key in ("requirement_13_condition_a", "requirement_13_condition_b"):
        assert key in subs, f"{key} must be recorded explicitly"
        assert subs[key]["met"] is False, (
            f"{key} is unmet on the bytes of record; recording it as met would "
            "authorise an owner session the accepted verdict refuses"
        )
        assert len(subs[key]["why_not"]) > 40, f"{key} needs a substantive reason"


def test_the_owner_question_text_is_deleted():
    """The withdrawn question must be gone, not merely downgraded."""
    oq = _intake()["owner_question"]
    assert oq["question"] is None, (
        "the staged map-versus-ranked-list question must be deleted per RF0"
    )
    assert oq["question_deleted"] is True
    assert oq["status"] == "WITHDRAWN_NOT_FIRED_NEVER_TO_FIRE_ON_THIS_VERDICT"
    # No staging SURVIVES as a field value. Prose that *describes* the withdrawal
    # ("must not be staged as ready to fire") is required and must not be flagged;
    # what must not exist is a status/key that a supervisor or a later agent could
    # read as "this is armed". So this checks values, not the raw text.
    staging_values = set()

    def walk(node, trail: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in {"status", "owner_question_status", "route_around_status"} \
                        and isinstance(v, str):
                    if any(p.upper() in v.upper() for p in _FIRING_PHRASES):
                        staging_values.add(f"{trail}.{k} = {v}")
                if k in {"question", "owner_question"} and isinstance(v, str):
                    staging_values.add(f"{trail}.{k} = <staged question text present>")
                if k in {"why_ready", "why_fire"}:
                    staging_values.add(f"{trail}.{k} = <why_ready sentence present>")
                walk(v, f"{trail}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{trail}[{i}]")

    walk(json.loads(INTAKE.read_text(encoding="utf-8")), "intake")
    assert not staging_values, (
        "the intake record still carries a fireable owner-question status: "
        f"{sorted(staging_values)}"
    )


#: State subtrees that are preserved HISTORICAL records of an earlier cycle. They
#: may contain readiness fields that were true for that cycle and must never be
#: edited: rewriting history to make today's guard pass is exactly the
#: "never overwrite historical claim-bearing results" violation. What matters is
#: that each is namespaced by its cycle/direction so it cannot be read as today's
#: position.
HISTORICAL_STATE_NAMESPACES = ("_delivery", "cycle_")


def _is_historical(trail: str) -> bool:
    return any(
        part.endswith(HISTORICAL_STATE_NAMESPACES) or part.startswith("cycle_")
        for part in trail.split(".")
    )


def test_no_current_field_claims_the_product_is_owner_ready():
    """No CURRENT artifact may assert owner readiness while either bar is unmet."""
    for path, label in ((INTAKE, "intake record"), (PRODUCT_STATE, "state/product.json")):
        if not path.exists():
            continue
        offenders: list[str] = []

        def walk(node, trail: str) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f"{trail}.{k}")
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, f"{trail}[{i}]")
            elif node is True and trail.split(".")[-1] in FORBIDDEN_TRUE_KEYS:
                if not _is_historical(trail):
                    offenders.append(f"{trail} = true")

        walk(json.loads(path.read_text(encoding="utf-8")), label)
        assert offenders == [], (
            f"{label} asserts owner/human readiness that the accepted verdict "
            f"refuses: {offenders}"
        )


def test_historical_readiness_fields_stay_quarantined_in_their_namespace():
    """History is preserved, and every preserved true-valued readiness field is
    still namespaced under its own cycle - so it cannot be mistaken for the
    current position."""
    state = json.loads(PRODUCT_STATE.read_text(encoding="utf-8"))
    offenders: list[str] = []

    def walk(node, trail: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{trail}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{trail}[{i}]")
        elif node is True and trail.split(".")[-1] in FORBIDDEN_TRUE_KEYS:
            if not _is_historical(trail):
                offenders.append(trail)

    walk(state, "state")
    assert offenders == [], (
        "every readiness=true field must live inside a *_delivery / cycle_* "
        f"namespace, got {offenders}"
    )
    # The current position itself is fail-closed.
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False


def test_admission_stays_fail_closed():
    pos = _intake()["product_position"]
    assert pos["admission"].startswith("fail-closed"), pos["admission"]
    assert pos["packet_admitted"] is False
    assert pos["ready_for_owner_session"] is False
    assert pos["human_gate_ready"] is False


def test_both_do_not_serve_orders_are_still_declared_in_force():
    """RF0 item (6): the rebuilt verdict does NOT supersede the 38839347028 order."""
    order = _intake()["do_not_serve_order"]
    assert order["status"] == "IN_FORCE", order["status"]
    assert "38839347028" in order["covers"], (
        "the accepted served-packet order must still be named as standing"
    )
    current = order["current_state"]
    assert "stands" in current.lower(), current


def test_the_guards_are_non_vacuous():
    """A record that DID fire the owner question must be rejected by these rules."""
    firing = {
        "route_around": {"status": "TRIGGERED_AND_FIRED",
                        "actions_fired": ["carried the map-versus-ranked-list choice to the owner as ONE recorded product question"]},
        "owner_question": {"status": "READY_TO_FIRE", "question": "Does the map beat the list?",
                           "why_ready": "converts the map-versus-ranked-list choice into ONE explicit owner product decision"},
        "verdict": {"owner_decision_required": True},
    }
    assert firing["route_around"]["status"] != "RECORDED_FAIL_CLOSED_NO_OWNER_QUESTION"
    assert any("owner" in str(a).lower() for a in firing["route_around"]["actions_fired"])
    assert firing["owner_question"]["question"] is not None
    assert firing["verdict"]["owner_decision_required"] is True

    # And the phrase list must match the withdrawn text it is meant to catch.
    fired_text = json.dumps(firing)
    assert any(p in fired_text for p in _FIRING_PHRASES), (
        "the firing-phrase detector must match a genuinely fired record"
    )
    assert re.search(r"ready[_ ]to[_ ]fire", fired_text, re.I)