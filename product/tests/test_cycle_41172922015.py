"""Operational resume 41172922015: diagnose 41172772289 and re-verify the slice.

The resumed run 41172772289 was dispatched off the persisted snapshot of run
41168174298 (commit ``72d10431``).  Its lane-cycle step failed after **16 s**
with the generic exit code **1**; the logs endpoint is HTTP 403, so the
innermost cause is UNOBSERVED and none is asserted.  Both team refs stayed at
``72d10431``, so the run added zero durable delta.

What this cycle locks, fail-closed:

* the public record of 41172772289 (16 s, generic exit 1, validation and
  write-scope steps skipped, audit/integrate skipped, HTTP 403 logs);
* why snapshot ``72d10431`` has never been audited: its own run 41168174298
  had a SUCCESSFUL team job and an audit job that died at 2705 s of a 2700 s
  quantum (exit 78), i.e. an audit-timeout, not a producer defect;
* the repaired dangling evidence reference
  ``results/product/audit_readiness/CYCLE_41159331087_audit_readiness.json``
  (the only test that turned red relative to the accepted base 7be4480e);
* a fresh SERVED vertical-slice run at this head (query -> bundle -> sourced
  answer -> counter pass -> clickable page), re-derived from its own artifact;
* the unchanged fail-closed posture, the unchanged accepted pointer, and that
  this producer minted no gate and wrote no auditor-namespace path.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41172922015"
RESUMED_RUN_ID = "41172772289"
PREDECESSOR_RUN_ID = "41168174298"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "72d10431d6bcab0b9a134d9a18fa5048f303919d"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
SLICE = ROOT / "results" / "product" / "server_slice" / EXECUTING_RUN_ID
SLICE_SUMMARY = SLICE / "summary.json"
REPAIRED_DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
                    / "CYCLE_41159331087_audit_readiness.json")
PRED_REPORT = ROOT / "reports" / "product" / f"CYCLE_{PREDECESSOR_RUN_ID}.md"
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"

FMT = "%Y-%m-%dT%H:%M:%SZ"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _step_seconds(step: dict) -> float:
    return (datetime.strptime(step["completed_at"], FMT)
            - datetime.strptime(step["started_at"], FMT)).total_seconds()


# --------------------------------------------------------------------------
# the orchestration failure we were asked to diagnose
# --------------------------------------------------------------------------

def test_public_record_names_a_generic_exit_1_step_failure():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["logs_endpoint_status"] == 403
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert _step_seconds(steps["Run lane cycle"]) == 16.0
    assert _step_seconds(steps["Run lane cycle"]) < 2700  # not a quantum death
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    messages = [a["message"] for a in raw.get("annotations") or []]
    assert "Process completed with exit code 1." in messages
    # No wrapper branch name is observed: the test refuses a fabricated
    # LEX_ZERO_DELTA_REPAIR / LEX_WORK_QUANTUM_EXPIRED narrative.
    assert not any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)
    assert not any("LEX_WORK_QUANTUM_EXPIRED" in m for m in messages)
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "skipped"


def test_orchestration_document_rules_out_every_named_wrapper_branch():
    doc = _load(ORCH_DOC)
    assert doc["run_id"] == int(RESUMED_RUN_ID)
    assert doc["classification"]["class"] == "TEAM_JOB_FAILED"
    assert doc["job_conclusions"] == {
        "team": "failure", "audit": "skipped", "integrate": "skipped",
        "resilience": "success",
    }
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 1
    assert diag["failing_step"] == "Run lane cycle"
    assert diag["failing_step_duration_s"] == 16.0
    assert diag["preflight"]["all_pass"] is True  # registry + model health clean
    assert diag["candidates"]["surviving_named_branches"] == []
    for branch in diag["candidates"]["named_branches"]:
        assert branch["ruled_out"] is True, branch
    assert doc["team_branch_exists"] is True
    assert doc["audit_branch_exists"] is False


def test_resume_diagnosis_records_zero_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["failed_step"] == "Run lane cycle"
    assert orch["failed_step_seconds"] == 16.0
    assert orch["producer_state_validation_conclusion"] == "skipped"
    assert orch["write_scope_enforcement_conclusion"] == "skipped"
    # The public annotation carries the generic exit 1; no wrapper branch name
    # and no quantum message exist, so no exit_code_meaning is asserted.
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["skipped"] is True
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_LANE_CYCLE_STEP_FAILED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 1
    assert mech["exit_code_meaning"] is None
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_the_snapshot_is_unaudited_because_its_audit_job_hit_the_quantum():
    """Why 72d10431 has never reached an independent audit.

    The producer side of the predecessor 41168174298 SUCCEEDED; what failed was
    the AUDIT job at 2705 s of a 2700 s work quantum.  Recording this keeps the
    next dispatch from re-diagnosing the producer for an audit-side timeout.
    """
    doc = _load(ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_orchestration.json")
    assert doc["run_id"] == int(PREDECESSOR_RUN_ID)
    assert doc["job_conclusions"]["team"] == "success"
    assert doc["job_conclusions"]["audit"] == "failure"
    assert doc["job_conclusions"]["integrate"] == "skipped"
    step = next(s for s in doc["steps"] if s["step"] == "Independent audit")
    assert step["conclusion"] == "failure"
    assert step["duration_s"] == 2705.0
    assert doc["diagnosis"]["exit_code"] == 78
    assert doc["diagnosis"]["failing_step"] == "Independent audit"
    assert PRED_REPORT.is_file()


# --------------------------------------------------------------------------
# the lane deliverable, verified at this head rather than asserted
# --------------------------------------------------------------------------

def test_served_vertical_slice_is_green_at_this_head():
    summary = _load(SLICE_SUMMARY)
    assert summary["schema"] == "product-server-slice/1"
    assert summary["verdict"] == "PASS"
    assert summary["failures"] == []
    assert len(summary["checks"]) == 10
    assert all(c["status"] == "PASS" for c in summary["checks"])
    counts = summary["counts"]
    assert counts["n_first_page"] == counts["n_final"] == 100
    assert counts["n_clusters_final"] == 8
    assert counts["n_cited"] >= 1
    assert counts["counter_authorities"] >= 1
    assert counts["rows_with_source_url"] == counts["n_final"]
    assert counts["page_contract_assertions"] >= 60
    assert summary["timing_s"]["total_s"] < 60  # local overhead, fixture mode
    assert (SLICE / "served.bundle.json").is_file()
    assert (SLICE / "first_page.bundle.json").is_file()


def test_the_dangling_state_evidence_reference_now_resolves():
    """The one test that turned red relative to accepted base 7be4480e.

    ``state/product.json``'s ``evidence_refs`` has named
    ``CYCLE_41159331087_audit_readiness.json`` since run 41163295014, but that
    file was never produced - so ``test_the_state_names_only_files_that_exist``
    was the ONLY failing test id this snapshot added over the accepted base.
    The artifact is produced now (profile 41159331087, disclosed as produced by
    this run) and the reference resolves.
    """
    assert REPAIRED_DOSSIER.is_file()
    dossier = _load(REPAIRED_DOSSIER)
    assert dossier["overall_status"] == "PASS"
    assert dossier["failed_checks"] == []
    assert dossier["skipped_checks"] == []
    assert len(dossier["checks"]) == 9

    from product.tests.test_state_cycle_39764730877 import (
        test_the_state_names_only_files_that_exist as check,
    )
    check()  # was red at 72d10431, must be green here

    st = _load(STATE)
    assert "results/product/audit_readiness/CYCLE_41159331087_audit_readiness.json" \
        in st["evidence_refs"]


# --------------------------------------------------------------------------
# state, posture, and no self-minted gate
# --------------------------------------------------------------------------

def test_state_records_the_run_and_keeps_the_pointer_and_posture():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_HEAD
    from product.state_contract import accepted_pointer_evidence
    ev = accepted_pointer_evidence(st, ROOT)
    assert not ev["problems"], ev
    assert ev["gate_ok"] and ev["accept_commit_present"]

    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    entry = hist[RESUMED_RUN_ID]
    assert entry["status"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_ZERO_DURABLE_DELTA"
    assert entry["exit_code"] == 1
    assert entry["exit_code_meaning"] is None
    assert entry["failed_step_seconds"] == 16.0
    assert entry["snapshot_commit"] == SNAPSHOT_HEAD
    assert entry["audit_gate"] == "NONE"

    pred = hist[PREDECESSOR_RUN_ID]
    assert pred["audit_gate"] == "NONE"  # audit died before any gate could land
    assert pred["failed_step"] == "Independent audit"
    assert pred["exit_code"] == 78

    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_ref_head"] == SNAPSHOT_HEAD
    assert block["lane_deliverable"]["status"] == "VERIFIED_AT_THIS_HEAD"
    assert (ROOT / block["diagnosis"]).is_file()
    assert (ROOT / block["raw_snapshot"]).is_file()
    assert (ROOT / block["report"]).is_file()
    assert (ROOT / block["lane_deliverable"]["served_slice"]).is_dir()
    assert (ROOT / block["lane_deliverable"]["artifact"]).is_file()
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
    ):
        assert st[key] == expected, (key, st[key])


def test_audit_readiness_profile_pins_generic_exit_1_and_is_selectable():
    from product import audit_readiness as ar
    prof = ar.select_profile(RESUMED_RUN_ID)
    assert prof["mechanism_kind"] == "observed_step_failure"
    assert prof["exit_code"] == 1
    assert "exit_code_meaning" not in prof  # generic exit must stay generic
    assert prof["lane_cycle_step_seconds"] == 16.0
    assert prof["delta_kind"] == "zero"
    assert prof["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert prof["cycle_test"] == "product/tests/test_cycle_41172922015.py"
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown run id must not inherit another profile")


def test_no_producer_minted_gate_and_no_auditor_namespace_write():
    st = _load(STATE)
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["adjudication"]["gate_minted"] is False
    assert block["adjudication"]["audit_namespace_written"] is False
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists()


def test_the_lane_deliverable_is_consumed_not_re_measured():
    """Ordered work (1)/(2) stay accepted evidence; this cycle re-measures neither."""
    st = _load(STATE)
    assert st["v68_delivery"]["status"] == "LANDED"
    cf = _load(ROOT / st["v68_delivery"]["reverified_evidence"][5])
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["bundle_bytes_written"] is False
    assert block["frozen_bar_scored"] is False
