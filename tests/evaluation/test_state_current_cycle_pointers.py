"""Durable guards for the two provenance/pointer defects of rejected cycle 38996043415.

Audit of record: ``results/audit/evaluation/CYCLE_38996043415_GATE.json``
(gate=REVISE, ref ``origin/cycle/core/evaluation/38996043415/audit`` — audit
artifacts live on the audit branch, never in the producer tree).

* **D2 (this file's primary target):** the TOP-LEVEL canonical pointers
  ``state.report`` and ``state.execution_records_this_cycle`` named cycle
  38989947869 while ``cycle_status``/``proposed_run_id`` named 38996043415 —
  the *second* consecutive cycle with stale current-cycle pointers. The correct
  values existed only inside the nested cycle block, so no information was lost,
  but the fields a control-plane integrator reads were wrong. The audit's fix
  wording is explicit: *"Add a small test that top-level
  report/execution_records_this_cycle agree with cycle_status before the next
  cycle ships."* A recurrence after this REVISE is BLOCK-worthy, not
  REVISE-worthy, so the agreement must be executable rather than promised.

* **D1 (this file's secondary target):** the frozen hypothesis file carries a
  ``frozen_at_utc`` that postdates its own execution while asserting
  ``frozen_before_execution=true``. The fix is a *disclosed erratum* — the
  frozen bytes stay untouched, the correction is published beside them. These
  tests pin that the erratum exists, still names the untouched subject file, and
  still matches the subject file's live sha256 (so the erratum can never drift
  away from the artifact it corrects).

Mount-independent by design: only ``state/evaluation.json``, this lane's reports
and this lane's records are read. No Product import, no network, no threshold.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATE_PATH = _REPO_ROOT / "state" / "evaluation.json"

FREEZE_REL = "results/evaluation/reground_semantics/FROZEN_HYPOTHESIS_38996043415.json"
ERRATUM_REL = "results/evaluation/reground_semantics/ERRATUM_FROZEN_AT_38996043415.json"


def _state() -> dict:
    return json.loads(_STATE_PATH.read_text(encoding="utf-8"))


def _cycle_run_id(state: dict) -> str:
    """The run id embedded in ``cycle_status`` (its trailing digit run).

    Every cycle_status in this lane ends with the GitHub run id that produced
    the cycle (e.g. ``V50_REGROUND_SEMANTICS_38996043415``). If a future status
    does not, this raises and the test fails loudly instead of silently
    agreeing with itself.
    """
    status = state.get("cycle_status") or ""
    m = re.search(r"(\d{6,})$", status)
    assert m, (f"cycle_status {status!r} does not end in a run id; the pointer "
               "agreement cannot be derived, so the convention itself is broken")
    return m.group(1)


# ------------------------------------------------------------- cycle_status --

def test_cycle_status_run_id_matches_proposed_run_id():
    """The first disagreement D2 named must be impossible: one run id everywhere."""
    state = _state()
    run = _cycle_run_id(state)
    assert state.get("proposed_run_id") == run, (
        f"proposed_run_id={state.get('proposed_run_id')!r} disagrees with the "
        f"run id embedded in cycle_status={state.get('cycle_status')!r}")


def test_cycle_status_has_a_matching_cycle_block():
    """``cycle_status.lower()`` is this lane's cycle-block key convention.

    D2's correct values existed only inside that block, so the block has to stay
    addressable from the top level.
    """
    state = _state()
    block = state.get((state.get("cycle_status") or "").lower())
    assert isinstance(block, dict), (
        f"no cycle block keyed by cycle_status.lower()="
        f"{(state.get('cycle_status') or '').lower()!r}")


# ------------------------------------------------------------- state.report --

def test_top_level_report_is_the_current_cycle_report():
    """D2 defect, asserted directly: report == CYCLE_<cycle run id>.md and it exists."""
    state = _state()
    run = _cycle_run_id(state)
    expected = f"reports/evaluation/CYCLE_{run}.md"
    assert state.get("report") == expected, (
        f"state.report={state.get('report')!r} is stale; it must be {expected!r} "
        f"(D2 of audit CYCLE_{run}: canonical current-cycle pointers must agree "
        f"with cycle_status)")
    assert (_REPO_ROOT / expected).is_file(), f"{expected} does not exist"


def test_top_level_report_agrees_with_the_cycle_block_report():
    """Top level and cycle block must not be able to name different reports."""
    state = _state()
    block = state[(state.get("cycle_status") or "").lower()]
    if "report" in block:
        assert state.get("report") == block["report"], (
            f"top-level report {state.get('report')!r} != cycle block report "
            f"{block['report']!r}")


def test_report_body_names_the_cycle_run_id():
    """A report that exists but describes another cycle is the same silent failure."""
    state = _state()
    run = _cycle_run_id(state)
    body = (_REPO_ROOT / state["report"]).read_text(encoding="utf-8")[:4000]
    assert run in body, (
        f"{state['report']} never mentions run {run} in its first 4000 chars")


# ------------------------------------------- execution_records_this_cycle ----

def test_execution_records_this_cycle_run_id_matches_cycle_status():
    """D2 defect, asserted directly on the second stale field."""
    state = _state()
    run = _cycle_run_id(state)
    recs = state.get("execution_records_this_cycle")
    assert isinstance(recs, dict), "execution_records_this_cycle is missing"
    assert recs.get("run_id") == run, (
        f"execution_records_this_cycle.run_id={recs.get('run_id')!r} is stale; "
        f"it must be {run!r} (D2 of audit CYCLE_{run})")
    assert len(recs) > 1, "execution_records_this_cycle must name real records"


def _record_paths(recs: dict) -> list[str]:
    """Every repo-relative path named anywhere in the execution-records block."""
    out: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("record", "path", "fresh_record") and isinstance(value, str):
                    out.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str) and "/" in node and node.endswith((".json", ".md")):
            out.append(node)

    walk(recs)
    return out


def test_every_execution_record_path_resolves_and_carries_the_run_id():
    """Paths must exist AND the records they name must belong to this cycle."""
    state = _state()
    run = _cycle_run_id(state)
    recs = state["execution_records_this_cycle"]
    paths = _record_paths(recs)
    assert paths, "execution_records_this_cycle names no record paths"
    for rel in paths:
        p = _REPO_ROOT / rel
        assert p.is_file(), f"execution record path does not exist: {rel}"
        assert run in rel, (
            f"execution record path {rel} does not belong to cycle run {run}")
        if p.suffix == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "run_id" in data:
                assert data["run_id"] == run, (
                    f"{rel} carries run_id={data['run_id']!r}, expected {run!r}")


# --------------------------------------------------------- D1 erratum pins --

def test_freeze_erratum_exists_and_pins_the_untouched_subject():
    """D1 fix is durable only if the erratum keeps matching the frozen bytes."""
    erratum_path = _REPO_ROOT / ERRATUM_REL
    assert erratum_path.is_file(), (
        f"{ERRATUM_REL} missing: the freeze-timestamp erratum (audit D1) must be "
        "co-located with the freeze it corrects")
    freeze_path = _REPO_ROOT / FREEZE_REL
    assert freeze_path.is_file(), f"{FREEZE_REL} missing"

    err = json.loads(erratum_path.read_text(encoding="utf-8"))
    assert err["schema"] == "lex-evaluation-freeze-erratum/1"
    assert err["subject"]["file"] == FREEZE_REL
    assert err["subject"]["edited_in_place"] is False
    assert err["subject"]["bytes_preserved_unchanged"] is True
    assert err["repairs_audit_required_fix"] == "D1"

    live = hashlib.sha256(freeze_path.read_bytes()).hexdigest()
    assert err["subject"]["sha256"] == live, (
        "the erratum's pinned subject sha256 no longer matches the frozen file: "
        f"erratum={err['subject']['sha256']} live={live}. The frozen file must "
        "never be edited in place — publish a NEW erratum instead.")


def test_freeze_timestamp_contradiction_is_disclosed_not_silently_repaired():
    """The wrong field must still be visible as wrong, next to the right one."""
    err = json.loads((_REPO_ROOT / ERRATUM_REL).read_text(encoding="utf-8"))
    freeze = json.loads((_REPO_ROOT / FREEZE_REL).read_text(encoding="utf-8"))

    both = err["both_timestamps"]
    assert freeze["frozen_at_utc"] == \
        both["freeze_declared_frozen_at_utc_AS_WRITTEN_IN_THE_FROZEN_FILE"], \
        "the erratum must quote the frozen file's own (wrong) timestamp verbatim"
    assert both["freeze_commit_utc_AUTHORITATIVE"] == "2026-10-17T02:52:58Z"
    assert freeze["frozen_at_utc"] == "2026-10-17T03:05:00Z"
    # the contradiction itself, stated by the erratum
    assert err["defect"]["declared_value"] == "2026-10-17T03:05:00Z"
    assert err["defect"]["contradicts_field"] == "frozen_before_execution"
    assert err["defect"]["is_leakage"] is False
    assert err["supersession"]["frozen_before_execution_remains_true"] is True
    # authoritative ordering: freeze commit precedes the claim-bearing execution
    events = err["authoritative_ordering_evidence"]
    freeze_event = next(e for e in events if e["seq"] == 1)
    exec_event = next(e for e in events if e["seq"] == 2)
    assert freeze_event["utc"] < exec_event["utc"], (
        "the erratum's own ordering table must show the freeze commit first")


def test_state_discloses_the_freeze_erratum():
    """The report and the state must both point at the erratum (audit D1 wording)."""
    state = _state()
    erratum = json.dumps(state.get("erratum_frozen_at_38996043415") or {})
    assert ERRATUM_REL in erratum, (
        "state.erratum_frozen_at_38996043415 does not name the erratum record")
    assert "2026-10-17T02:52:58Z" in erratum and "2026-10-17T03:05:00Z" in erratum, (
        "the state disclosure must carry BOTH timestamps (audit D1 wording)")
    block = state[(state.get("cycle_status") or "").lower()]
    frozen_hyp = block.get("frozen_hypothesis")
    assert isinstance(frozen_hyp, dict) and "erratum" in frozen_hyp, (
        "the cycle block's frozen_hypothesis must carry the erratum pointer")
    report = (_REPO_ROOT / state["report"]).read_text(encoding="utf-8")
    assert ERRATUM_REL in report, "the cycle report must cite the erratum record"
    assert "2026-10-17T02:52:58Z" in report and "2026-10-17T03:05:00Z" in report, (
        "the cycle report must state BOTH timestamps (audit D1 wording)")


def test_freeze_file_is_not_modified_by_the_repair():
    """Byte-preservation guard: the frozen hypothesis stays at its original digest."""
    freeze = json.loads((_REPO_ROOT / FREEZE_REL).read_text(encoding="utf-8"))
    # the original content markers must survive the repair untouched
    assert freeze["schema"] == "lex-evaluation-reground-semantics-freeze/1"
    assert freeze["frozen_before_execution"] is True
    assert freeze["run_id"] == "38996043415"
    assert set(freeze["non_vacuity_battery_frozen"][i]["id"] for i in range(5)) == \
        {"N1", "N2", "N3", "N4", "N5"}
    assert set(k for k in freeze["discriminating_predicates"]) == \
        {"R1_order_grounding", "R2_anchor_freedom", "R3_real_degradation_detection",
         "R4_non_vacuity", "R5_no_new_threshold"}
    assert hashlib.sha256((_REPO_ROOT / FREEZE_REL).read_bytes()).hexdigest() == \
        "fccdbb9edeb4f592a93b20869cfbd5aa14a066c5d1dcb2d9c3ecfceb0acc991c", (
            "the frozen hypothesis bytes changed; a freeze may only be superseded "
            "by a NEW filename, never edited in place")
