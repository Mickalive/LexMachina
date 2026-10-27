"""Operational resume 40429931848: audit write-scope failure, not a rejection.

The resumed producer snapshot (run 40427889739, commit 4b8101f9) is intact and
carries an 8-file repair delta over its predecessor.  The independent-audit
job's ``Independent audit`` agent step SUCCEEDED, then the workflow's
``Enforce audit scope and read gate`` step failed with the public annotation
``auditor crossed scope:`` (runner exit code 3).  The always-run
``Persist audit snapshot`` step was skipped, so there is no audit ref and no
gate: the run is UNADJUDICATED.

This test locks the observable facts, the new classifier/profile wiring, the
fail-closed scope guard, and the state/report posture.  It does not claim the
unobservable per-path list (job logs are HTTP 403) and does not treat the audit
scope failure as a product defect.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product import audit_readiness as ar
from product import audit_scope_guard as guard
from product import audit_step_diagnosis as asd
from product import capture_run_snapshot as capture

EXECUTING_RUN_ID = "40429931848"
SNAPSHOT_RUN_ID = "40427889739"
PREDECESSOR_RUN_ID = "40423889401"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{SNAPSHOT_RUN_ID}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{SNAPSHOT_RUN_ID}_resume_diagnosis.json"
STATE = ROOT / "state" / "product.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
SCOPE_FAILED_STEP = "Enforce audit scope and read gate"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _audit(raw: dict) -> dict:
    return next(j for j in raw["jobs"] if j["name"] == "audit")


def test_raw_snapshot_observes_agent_success_then_gate_failure() -> None:
    raw = _load(RAW)
    assert raw["run"]["id"] == int(SNAPSHOT_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    assert raw["logs_endpoint_status"] == 403
    audit = _audit(raw)
    steps = {s["name"]: s["conclusion"] for s in audit["steps"]}
    assert audit["conclusion"] == "failure"
    assert steps["Independent audit"] == "success"
    assert steps[SCOPE_FAILED_STEP] == "failure"
    assert steps["Persist audit snapshot"] == "skipped"
    assert "Persist audit snapshot" in steps


def test_public_annotations_name_scope_violation_not_product_rejection() -> None:
    raw = _load(RAW)
    audit = _audit(raw)
    messages = " ".join(
        str(a.get("message") or "")
        for a in (raw.get("annotations") or {}).get(str(audit["id"])) or []
    ).lower()
    assert "auditor crossed scope" in messages
    assert "exit code 3" in messages
    # The public record contains no verdict or product-rejection language.
    assert "reject" not in messages
    assert "revise" not in messages


def test_classifier_names_audit_scope_failure_and_writes_no_gate() -> None:
    rec = asd.classify(_load(RAW))
    assert rec["classification"] == (
        "AUDIT_JOB_AUDIT_SCOPE_ENFORCEMENT_FAILED_NO_GATE")
    assert rec["audit"]["failed_step"] == SCOPE_FAILED_STEP
    assert rec["audit"]["gate_step"] == "failure"
    assert rec["audit"]["persist_step"] == "skipped"
    assert rec["audit"]["gate_file_written"] is False
    assert rec["mechanism"]["status"] == (
        "OBSERVED_AUDIT_SCOPE_ENFORCEMENT_FAILED")
    assert rec["mechanism"]["exit_code"] == 3
    assert rec["mechanism"]["quantum_expired"] is False
    assert rec["adjudication"]["product_defect"] is False
    assert rec["adjudication"]["verdict_written"] is False
    attention = rec["adjudication"]["control_plane_attention"].lower()
    assert "gate-reader" in attention
    assert "audit_scope_guard" in attention
    # Producer must never self-mint the independent gate.
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{SNAPSHOT_RUN_ID}_GATE.json").exists()


def test_resume_diagnosis_is_committed_delta_and_unadjudicated() -> None:
    diag = _load(DIAG)
    assert diag["run_id"] == SNAPSHOT_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 8
    assert "product/audit_readiness.py" in delta["changed_paths_sample"]
    assert "results/product/repair_40427889739/" in " ".join(
        delta["changed_paths_sample"])
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["audit"]["audit_ref_present"] is False
    assert adj["audit"]["gate_file_present"] is False


def test_profile_is_wired_to_the_observed_audit_scope_mechanism() -> None:
    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["resumed_run_id"] == SNAPSHOT_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["mechanism_kind"] == "observed_audit_scope"
    assert prof["classification"] == (
        "AUDIT_JOB_AUDIT_SCOPE_ENFORCEMENT_FAILED_NO_GATE")
    assert prof["exit_code"] == 3
    assert prof["changed_files"] == 8
    saved = dict(ar.PROFILE)
    try:
        ar.PROFILE.clear()
        ar.PROFILE.update(prof)
        check = ar.check_resumed_diagnosis()
    finally:
        ar.PROFILE.clear()
        ar.PROFILE.update(saved)
    assert check["status"] == "PASS", check["detail"]


def test_scope_guard_rejects_out_of_scope_paths_with_exit_three(
        tmp_path: Path) -> None:
    status = "\n".join([
        "?? results/audit/product/CYCLE_1_GATE.json",
        "?? reports/audit/product/CYCLE_1.md",
        " M product/audit_readiness.py",
        "R  old.py -> results/audit/product_backup/x.json",
    ])
    result = guard.classify_paths(guard.parse_status(status), scope="audit")
    assert result["ok"] is False
    assert result["disallowed"] == [
        "product/audit_readiness.py",
        "results/audit/product_backup/x.json",
    ]
    assert result["allowed"] == [
        "results/audit/product/CYCLE_1_GATE.json",
        "reports/audit/product/CYCLE_1.md",
    ]
    status_file = tmp_path / "status.txt"
    status_file.write_text(status, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "product/audit_scope_guard.py", "--scope", "audit",
         "--status-file", str(status_file), "--json"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 3, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["disallowed"]


def test_scope_guard_accepts_the_two_auditor_directories() -> None:
    result = guard.classify_paths([
        "results/audit/product/CYCLE_1_GATE.json",
        "reports/audit/product/CYCLE_1.md",
    ], scope="audit")
    assert result["ok"] is True
    assert result["disallowed"] == []


def test_capture_snapshot_shape_classifies_without_network() -> None:
    run = {"id": 7, "name": "run", "conclusion": "failure", "status": "completed"}
    jobs = {"jobs": [{
        "id": 69,
        "name": "team",
        "conclusion": "success",
        "steps": [{"number": 1, "name": "Run lane cycle",
                   "conclusion": "success"}],
    }, {
        "id": 70,
        "name": "audit",
        "conclusion": "failure",
        "steps": [
            {"number": 5, "name": "Independent audit", "conclusion": "success"},
            {"number": 6, "name": SCOPE_FAILED_STEP, "conclusion": "failure"},
            {"number": 7, "name": "Persist audit snapshot",
             "conclusion": "skipped"},
        ],
    }]}
    snapshot = capture.build_snapshot(
        run, jobs,
        [{"job_id": 70, "job": "audit", "annotation_level": "failure",
          "message": "auditor crossed scope:"},
         {"job_id": 70, "job": "audit", "annotation_level": "failure",
          "message": "Process completed with exit code 3."}],
        logs_status=403, source="test", fetched_at="2026-10-27T00:00:00Z",
    )
    assert snapshot["schema"] == "github-actions-run-jobs-snapshot/1"
    assert snapshot["logs_endpoint_status"] == 403
    assert "HTTP 403" in snapshot["logs_endpoint_note"]
    rec = asd.classify(snapshot)
    assert rec["classification"] == (
        "AUDIT_JOB_AUDIT_SCOPE_ENFORCEMENT_FAILED_NO_GATE")
    assert rec["mechanism"]["exit_code"] == 3


def test_report_state_and_posture_are_recorded() -> None:
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert SNAPSHOT_RUN_ID in text
    assert "auditor crossed scope" in text
    assert "UNADJUDICATED" in text

    st = _load(STATE)
    block = st["cycle_40429931848_operational_resume"]
    assert block["resumed_run"] == SNAPSHOT_RUN_ID
    assert block["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert block["orchestration_failure_of_record"]["classification"] == (
        "AUDIT_JOB_AUDIT_SCOPE_ENFORCEMENT_FAILED_NO_GATE")
    assert block["orchestration_failure_of_record"]["mechanism"] == (
        "OBSERVED_AUDIT_SCOPE_ENFORCEMENT_FAILED")
    assert block["orchestration_failure_of_record"]["product_defect"] is False
    assert block["accepted_this_cycle"] is False
    assert block["durable_delta"]["changed_files"] == 8

    assert str(st["current_cycle_run_id"]) == EXECUTING_RUN_ID
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["ready_for_owner_session"] is False
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(st, ROOT)
    assert not pointer["problems"], pointer
