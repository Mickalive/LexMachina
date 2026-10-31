"""Operational resume 41163295014: finish the 41162767461 snapshot audit-readiness.

The resumed run 41162767461 was a fresh v68 product cycle dispatched off the
persisted delta of run 41159331087.  Its lane-cycle step failed after **301 s**
with wrapper exit **67** AND the public check-run annotation names the branch
``LEX_ZERO_DELTA_REPAIR``; both team refs stayed at the predecessor snapshot
``665a4205``, so the run added zero durable delta.

The predecessor chain itself had never reached an independent audit, and the
persisted snapshot was also **not audit-ready**: its own dossier profile names
``reports/product/CYCLE_41159331087.md`` as the current report, and that report
was never written because 41159331087's lane-cycle step died of quantum expiry
(2704 s, exit 78) and the workflow's ``if: always()`` snapshot step committed
the working tree instead.  The dossier's measured FAIL was exactly
``claim_artifacts`` with ``missing = [reports/product/CYCLE_41159331087.md]``.

This test locks, fail-closed:

* the public record of 41162767461 (301 s, exit 67, `LEX_ZERO_DELTA_REPAIR`,
  skipped validation/scope steps, HTTP 403 logs, zero delta);
* the predecessor's own quantum death and the fact that its delta was persisted
  by the snapshot step, not by a successful producer run;
* the restored report of record under its own run id, with the authoring
  correction, and the false `lab/product is at f7bc77a0` parenthetical
  superseded (lab/product is 7be4480e);
* the additive run_history correction (old status preserved);
* the new audit-readiness profile that pins ``exit_code_meaning`` and the two
  fast dossier checks (resumed_diagnosis, claim_artifacts) reading PASS;
* the unchanged fail-closed posture and accepted pointer.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41163295014"
RESUMED_RUN_ID = "41162767461"
PREDECESSOR_RUN_ID = "41159331087"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "665a4205aab327cb5cafc9ae75f61786045d0f14"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
ORCH_DOC = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
PRED_ORCH = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_orchestration.json"
PRED_RAW = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_team_step_raw.json"
RESTORED_REPORT = ROOT / "reports" / "product" / f"CYCLE_{PREDECESSOR_RUN_ID}.md"
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{RESUMED_RUN_ID}_audit_readiness.json")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _step_seconds(step: dict) -> float:
    from datetime import datetime
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(step["completed_at"], fmt)
            - datetime.strptime(step["started_at"], fmt)).total_seconds()


def test_public_record_names_the_zero_delta_guard_and_zero_delta():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["logs_endpoint_status"] == 403
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert _step_seconds(steps["Run lane cycle"]) == 301.0
    assert _step_seconds(steps["Run lane cycle"]) < 2700  # not a quantum death
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    messages = [a["message"] for a in raw.get("annotations") or []]
    assert "Process completed with exit code 67." in messages
    # The branch name is OBSERVED, not inferred from the number.
    assert "LEX_ZERO_DELTA_REPAIR" in messages


def test_orchestration_document_pins_exit_67_and_the_surviving_branch():
    doc = _load(ORCH_DOC)
    assert doc["run_id"] == int(RESUMED_RUN_ID)
    assert doc["classification"]["class"] == "TEAM_JOB_FAILED"
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 67
    assert diag["failing_step"] == "Run lane cycle"
    assert diag["failing_step_duration_s"] == 301.0
    assert diag["step_duration_used_s"] == 301.0
    assert diag["candidates"]["surviving_named_branches"] == [
        "LEX_ZERO_DELTA_REPAIR"]
    assert diag["candidates"]["generic_passthrough_possible"] is False
    assert doc["team_branch_exists"] is True


def test_predecessor_quantum_death_and_snapshot_persist_are_recorded():
    doc = _load(PRED_ORCH)
    assert doc["run_id"] == int(PREDECESSOR_RUN_ID)
    assert doc["classification"]["class"] == "TEAM_JOB_FAILED"
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 78
    assert diag["failing_step"] == "Run lane cycle"
    assert diag["failing_step_duration_s"] == 2704.0
    assert diag["candidates"]["surviving_named_branches"] == [
        "LEX_WORK_QUANTUM_EXPIRED"]
    raw = _load(PRED_RAW)
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    # The delta reached the branch through the workflow's snapshot step.
    assert steps["Persist team snapshot"]["conclusion"] == "success"
    messages = [a["message"] for a in raw.get("annotations") or []]
    assert any("LEX_WORK_QUANTUM_EXPIRED" in m for m in messages)


def test_resume_diagnosis_records_zero_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["resumed_by_run_id"] == EXECUTING_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["failed_step"] == "Run lane cycle"
    assert orch["failed_step_seconds"] == 301.0
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_LANE_CYCLE_STEP_FAILED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 67
    assert mech["exit_code_meaning"] == "LEX_ZERO_DELTA_REPAIR"
    assert orch["audit"]["skipped"] is True
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["audit_ref_exists"] is False


def test_restored_report_of_record_closes_the_measured_audit_readiness_fail():
    # The exact gap this resume found: the profile's current_report was absent.
    assert RESTORED_REPORT.is_file()
    assert CURRENT_REPORT.is_file()
    body = RESTORED_REPORT.read_text(encoding="utf-8")
    assert "AUTHORING CORRECTION" in body
    assert "41163295014" in body        # names the finalizing resume
    assert "2704" in body               # the observed quantum death
    assert "LEX_WORK_QUANTUM_EXPIRED" in body
    assert "7be4480e" in body           # the true origin/lab/product head
    # The false parenthetical is superseded, not silently repeated.
    assert "lab/product is at this same commit" not in body


def test_state_corrects_history_additively_and_keeps_the_pointer():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_HEAD
    from product.state_contract import accepted_pointer_evidence
    ev = accepted_pointer_evidence(st, ROOT)
    assert not ev["problems"], ev
    assert ev["gate_ok"] and ev["accept_commit_present"]

    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    pred = hist[PREDECESSOR_RUN_ID]
    assert pred["status_before_correction"] == (
        "OPERATIONAL_RESUME_AUDIT_READINESS_REPAIR")
    assert pred["status"] == "OPERATIONAL_RESUME_QUANTUM_EXPIRED_DELTA_PERSISTED"
    assert pred["corrected_by_run_id"] == int(EXECUTING_RUN_ID)
    assert pred["exit_code"] == 78
    assert pred["failed_step_seconds"] == 2704.0
    assert pred["snapshot_commit"] == SNAPSHOT_HEAD
    assert hist[RESUMED_RUN_ID]["status"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_ZERO_DURABLE_DELTA")
    assert hist[RESUMED_RUN_ID]["exit_code"] == 67
    assert hist[RESUMED_RUN_ID]["audit_gate"] == "NONE"

    block = st["cycle_41163295014_operational_resume"]
    assert block["run_id"] == int(EXECUTING_RUN_ID)
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_ref_head"] == SNAPSHOT_HEAD
    assert block["exit_code_meaning"] == "LEX_ZERO_DELTA_REPAIR"
    assert (ROOT / block["diagnosis"]).is_file()
    assert (ROOT / block["raw_snapshot"]).is_file()
    assert (ROOT / block["report"]).is_file()
    assert block["adjudication"]["status"] == "UNADJUDICATED"
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
    ):
        assert st[key] == expected, (key, st[key])


def test_audit_readiness_profile_pins_the_branch_and_the_fast_checks_pass():
    from product import audit_readiness as ar
    prof = ar.select_profile(RESUMED_RUN_ID)
    assert prof["mechanism_kind"] == "observed_step_failure"
    assert prof["exit_code"] == 67
    assert prof["exit_code_meaning"] == "LEX_ZERO_DELTA_REPAIR"
    assert prof["lane_cycle_step_seconds"] == 301.0
    assert prof["state_block"] == "cycle_41163295014_operational_resume"
    assert prof["cycle_test"] == "product/tests/test_cycle_41163295014.py"
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


def test_dossier_is_committed_and_reads_pass():
    assert DOSSIER.is_file(), "generate it with product/audit_readiness.py"
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
    # The point of the repair: the report of record is now present and hashed,
    # and the claim-artifact check no longer has a missing path.
    claim = next(c for c in doc["checks"] if c["id"] == "claim_artifacts")
    assert claim["detail"]["missing"] == []
    assert claim["detail"]["sha256"][
        "reports/product/CYCLE_41159331087.md"
    ].startswith("cdf5ad317fb75796")
    # Posture changes only once an independent audit lands.
    posture = doc["posture"]
    assert posture["run_label"] == "UNADJUDICATED"
    assert posture["gate_minted"] is False
    assert posture["human_gate_ready"] is False
    assert posture["machine_gate_ready"] is False
    assert posture["frozen_bar_scored"] is False
