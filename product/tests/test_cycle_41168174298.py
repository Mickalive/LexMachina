"""Operational resume 41168174298: diagnose 41168007766 and re-verify the v68 deliverable.

The resumed run 41168007766 was a fresh v68 product cycle dispatched off the
persisted snapshot of run 41163295014 (commit ``cf441eb3``).  Its lane-cycle
step failed after **16 s** with the generic exit code **1** (the public
annotation does not name a wrapper branch); the logs endpoint is HTTP 403, so
the innermost cause is UNOBSERVED and none is asserted.  Both team refs stayed
at ``cf441eb3``, so the run added zero durable delta.

This resume is a diagnosis-and-verification cycle, not a new measurement.  It
locks, fail-closed:

* the public record of 41168007766 (16 s, exit 1, skipped validation/scope
  steps, HTTP 403 logs, zero delta);
* the resume diagnosis and its chain through the six unadjudicated predecessors;
* that the lane's v68 rejection/incumbent deliverable is ACCEPTED evidence
  (state ``v68_delivery`` LANDED, accepted fixed-path family success rule met),
  consumed REPORTED-ONLY and never re-derived here;
* the new audit-readiness profile and its fast checks;
* the unchanged fail-closed posture and accepted pointer;
* that no producer-authored gate exists for the resumed run (audit namespace
  is not written by this lane).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41168174298"
RESUMED_RUN_ID = "41168007766"
PREDECESSOR_RUN_ID = "41163295014"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "cf441eb33351d951036ddf6728e79aa63424ed9a"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
PRED_REPORT = ROOT / "reports" / "product" / f"CYCLE_{PREDECESSOR_RUN_ID}.md"
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{RESUMED_RUN_ID}_audit_readiness.json")
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40257275384.json")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _step_seconds(step: dict) -> float:
    from datetime import datetime
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(step["completed_at"], fmt)
            - datetime.strptime(step["started_at"], fmt)).total_seconds()


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
    # No wrapper branch name is observed for exit 1; the test refuses a
    # fabricated LEX_ZERO_DELTA_REPAIR / LEX_WORK_QUANTUM_EXPIRED narrative.
    assert not any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)
    assert not any("LEX_WORK_QUANTUM_EXPIRED" in m for m in messages)


def test_orchestration_document_pins_exit_1_as_generic_passthrough():
    doc = _load(ORCH_DOC)
    assert doc["run_id"] == int(RESUMED_RUN_ID)
    assert doc["classification"]["class"] == "TEAM_JOB_FAILED"
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 1
    assert diag["failing_step"] == "Run lane cycle"
    assert diag["failing_step_duration_s"] == 16.0
    assert diag["candidates"]["generic_passthrough_possible"] is True
    assert diag["candidates"]["surviving_named_branches"] == []
    # Both named wrapper branches are arithmetically ruled out.
    for branch in diag["candidates"]["named_branches"]:
        assert branch["ruled_out"] is True, branch
    assert doc["team_branch_exists"] is True
    assert doc["audit_branch_exists"] is False


def test_resume_diagnosis_records_zero_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["resumed_by_run_id"] == EXECUTING_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["failed_step"] == "Run lane cycle"
    assert orch["failed_step_seconds"] == 16.0
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_LANE_CYCLE_STEP_FAILED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 1
    assert mech["exit_code_meaning"] is None
    assert orch["audit"]["skipped"] is True
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["audit_ref_exists"] is False


def test_predecessor_snapshot_is_the_persisted_resume_delta():
    # The predecessor 41163295014 committed a report of record (but no separate
    # orchestration snapshot), so this resume inherits the report rather than
    # restoring one. The earlier 41159331087 situation was different.
    assert PRED_REPORT.is_file()
    assert (ROOT / "reports" / "product" / "CYCLE_41159331087.md").is_file()
    diag = _load(DIAG)
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert diag["durable_delta"]["predecessor_head"] == SNAPSHOT_HEAD


def test_lane_deliverable_is_accepted_evidence_not_re_derived():
    st = _load(STATE)
    delivery = st["v68_delivery"]
    assert delivery["status"] == "LANDED"
    assert delivery["component"] == "counter_evidence_span rejection/incumbent leg"
    assert delivery["evidence_run"] == "40125024681"
    # Consume the accepted fixed-path family pins REPORTED-ONLY.
    cf = _load(CONTENT_FAMILY)
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_decisions"] == 4900
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["still_verified"] is True
    assert cf["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert cf["ordered_work_2_full_success_rule"]["met"] is True
    assert cf["ordered_work_2_success_rule"]["met"] is True


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

    block = st["cycle_41168174298_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_ref_head"] == SNAPSHOT_HEAD
    assert block["exit_code"] == 1
    assert block["exit_code_meaning"] is None
    assert (ROOT / block["diagnosis"]).is_file()
    assert (ROOT / block["raw_snapshot"]).is_file()
    assert (ROOT / block["report"]).is_file()
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    assert block["lane_deliverable"]["status"] == "ACCEPTED_EVIDENCE_CONSUMED"
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
    ):
        assert st[key] == expected, (key, st[key])


def test_audit_readiness_profile_pins_generic_exit_1_and_fast_checks_pass():
    from product import audit_readiness as ar
    prof = ar.select_profile(RESUMED_RUN_ID)
    assert prof["mechanism_kind"] == "observed_step_failure"
    assert prof["exit_code"] == 1
    # A generic exit code must NOT be dressed up as a named wrapper branch.
    assert "exit_code_meaning" not in prof
    assert prof["lane_cycle_step_seconds"] == 16.0
    assert prof["state_block"] == "cycle_41168174298_operational_resume"
    assert prof["cycle_test"] == "product/tests/test_cycle_41168174298.py"
    # Unknown runs still fail closed.
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown run id must not inherit another profile")

    ar.PROFILE = ar.select_profile(RESUMED_RUN_ID)
    diag_check = ar.check_resumed_diagnosis()
    assert diag_check["status"] == "PASS", diag_check["detail"]
    assert diag_check["detail"]["problems"] == []
    claim_check = ar.check_claim_artifacts()
    assert claim_check["status"] == "PASS", claim_check["detail"]
    assert claim_check["detail"]["missing"] == []
    assert claim_check["detail"]["d2_before_after"]["before_verified"] is True
    assert claim_check["detail"]["d2_before_after"]["after_verified"] is False
    assert claim_check["detail"]["d2_before_after"]["after_reason"] == (
        "pivot_absent")


def test_no_producer_authored_gate_exists_for_the_resumed_run():
    # The lane writes only product-owned paths; a producer-minted gate is the
    # 40283048553 failure class and is refused here.
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists()
    assert CURRENT_REPORT.is_file()


def test_dossier_is_committed_and_reads_pass():
    # During dossier GENERATION this file does not exist yet: the dossier runs
    # this very test as its ``cycle_test`` check, so a hard assert here would be
    # circular. Skip while absent, then validate the committed dossier on every
    # later run (the second generation and all audits).
    if not DOSSIER.is_file():
        import pytest
        pytest.skip("generate with product/audit_readiness.py")
    doc = _load(DOSSIER)
    assert doc["schema"] == "product-audit-readiness/1"
    assert doc["run_id"] == RESUMED_RUN_ID
    assert doc["overall_status"] == "PASS", doc.get("failed_checks")
    assert doc["failed_checks"] == []
    assert doc["skipped_checks"] == []
    statuses = {c["id"]: c["status"] for c in doc["checks"]}
    assert statuses == {
        "runtime_preflight": "PASS",
        "state_contract": "PASS",
        "posture": "PASS",
        "resumed_diagnosis": "PASS",
        "claim_artifacts": "PASS",
        "cycle_test": "PASS",
        "progressive_smoke": "PASS",
        "mvp_core_tests": "PASS",
        "audit_namespace": "PASS",
    }
    claim = next(c for c in doc["checks"] if c["id"] == "claim_artifacts")
    assert claim["detail"]["missing"] == []
    posture = doc["posture"]
    assert posture["run_label"] == "UNADJUDICATED"
    assert posture["gate_minted"] is False
    assert posture["human_gate_ready"] is False
    assert posture["machine_gate_ready"] is False
    assert posture["frozen_bar_scored"] is False
