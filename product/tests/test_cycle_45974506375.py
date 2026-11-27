"""Cycle 45974506375 — audit-ready resume of run 45965956701.

Run 45965956701's producer persisted a real seven-file audit-readiness delta,
but its independent audit died on the annotation-observed 2700 s work quantum,
so no gate was written.  This test pins the raw job facts, the diagnosis, the
new audit-readiness profile, the repaired head-independent inheritance test and
the fail-closed state posture.  It mints no gate and scores no frozen bar.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import audit_readiness as ar  # noqa: E402

RUN = "45974506375"
RESUMED = "45965956701"
PREDECESSOR = "45954836439"
SNAPSHOT_HEAD = "2150d0a9a4568f9c5db1d77c7c8ce5326a826176"
PARENT_HEAD = "2301799cef1483cc29fc517278a78ae4c3deb00b"

RAW = ROOT / "results/product/orchestration" / f"CYCLE_{RESUMED}_run_jobs_raw.json"
DIAG = ROOT / "results/product/orchestration" / f"CYCLE_{RESUMED}_resume_diagnosis.json"
STATE = json.loads((ROOT / "state/product.json").read_text(encoding="utf-8"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_run_jobs_pin_an_annotation_observed_audit_quantum_death():
    doc = _load(RAW)
    assert doc["schema"] == "github-actions-run-jobs-snapshot/1"
    assert doc["fetched_from"].endswith(f"/actions/runs/{RESUMED}")
    assert doc["run"]["id"] == int(RESUMED)
    assert doc["run"]["conclusion"] == "failure"
    assert doc["logs_endpoint_status"] == 403
    assert doc["annotations_endpoint_status"] == 200
    messages = [a.get("message") for a in doc["annotations"]]
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2380" in messages
    assert "Process completed with exit code 78." in messages

    jobs = {j["name"]: j for j in doc["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    team_steps = {s["name"]: s for s in jobs["team"]["steps"]}
    assert team_steps["Run lane cycle"]["conclusion"] == "success"
    assert team_steps["Validate active MVP producer state"]["conclusion"] == "success"
    assert team_steps["Enforce lane write scope"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    audit_steps = {s["name"]: s for s in jobs["audit"]["steps"]}
    assert audit_steps["Independent audit"]["conclusion"] == "failure"
    assert audit_steps["Independent audit"]["seconds"] == 2706.0
    assert audit_steps["Enforce audit scope and read gate"]["conclusion"] == "skipped"
    assert audit_steps["Persist audit snapshot"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert jobs["resilience"]["conclusion"] == "success"


def test_diagnosis_keeps_the_committed_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    orch = diag["orchestration"]
    mech = orch["mechanism"]
    assert diag["run_id"] == RESUMED
    assert diag["resuming_run_id"] == RUN
    assert diag["predecessor_run_id"] == PREDECESSOR
    assert diag["direction_version"] == 68
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["failed_job"] == "audit"
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["evidence_basis"] == "check_run_annotation"
    assert mech["annotation_observed"] is True
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    assert orch["remote_ref_check"]["audit_ref_present"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 7
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PARENT_HEAD
    assert diag["validation_failure_of_record"]["classification"] == (
        "HEAD_PINNED_CYCLE_TEST_STALE_ON_COMMITTED_SNAPSHOT")
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["continue_recommended"] is True


def test_audit_readiness_profile_is_distinct_from_the_team_step_profile():
    current = ar.select_profile(RUN)
    resumed = ar.select_profile(RESUMED)
    assert current == resumed
    assert current["mechanism_kind"] == "observed"
    assert current["resumed_run_id"] == RESUMED
    assert current["cycle_test"] == "product/tests/test_cycle_45974506375.py"
    assert current["state_block"] == "cycle_45965956701_operational_resume"
    assert current["changed_files"] == 7
    # The prior alias described run 45965956701 as the *resumer* of the
    # 45965383491 team-step failure.  It must not silently misreport this
    # snapshot's own audit quantum death.
    assert ar.select_profile("45965383491")["mechanism_kind"] == (
        "observed_team_step_failure")


def test_inherited_head_pinned_test_is_repaired_and_still_green():
    source = (ROOT / "product/tests/test_cycle_45965956701.py").read_text(
        encoding="utf-8")
    assert "rev-parse\", \"HEAD" not in source
    assert "AUTHORING CORRECTION (run 45974506375)" in source
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "product/tests/test_cycle_45965956701.py",
         "-q", "--maxfail=1"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]


def test_no_auditor_namespace_path_was_minted_for_any_run_in_the_chain():
    for run_id in (RUN, RESUMED, PREDECESSOR, "45965383491"):
        assert not (ROOT / "results/audit/product" /
                    f"CYCLE_{run_id}_GATE.json").exists()
        assert not (ROOT / "reports/audit/product" /
                    f"CYCLE_{run_id}.md").exists()
    pending = subprocess.run(["git", "status", "--porcelain", "-uall"],
                             cwd=str(ROOT), capture_output=True, text=True,
                             check=True).stdout.splitlines()
    assert not [line for line in pending
                if line[3:].startswith(("results/audit/product/",
                                        "reports/audit/product/"))]


def test_state_advances_the_cycle_pointer_without_moving_posture():
    assert STATE["current_cycle_run_id"] == RUN
    assert STATE["direction_version"] == 68
    block = STATE["cycle_45965956701_operational_resume"]
    assert block["resuming_run_id"] == RUN
    assert block["resumed_run_id"] == RESUMED
    assert block["snapshot_head"] == SNAPSHOT_HEAD
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        assert STATE[flag] is False, flag
    assert STATE["continue_recommended"] is True
    assert STATE["accepted_run_id"] == "CYCLE_40284658455"
    for rel, digest in block["artifact_sha256"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel


def test_one_command_dossier_is_partial_only_because_slow_checks_are_skipped():
    dossier = ar.run(RUN, direction_version=68, include_tests=False,
                     include_smoke=False, auto_bootstrap=False)
    assert dossier["failed_checks"] == [], dossier["failed_checks"]
    assert dossier["overall_status"] == "PARTIAL"
    assert set(dossier["skipped_checks"]) == {
        "cycle_test", "progressive_smoke", "mvp_core_tests"}
    assert all(c["status"] == "PASS" for c in dossier["checks"]
               if c["status"] != "SKIP")
    assert dossier["resumed_run"]["mechanism"] == "OBSERVED_QUANTUM_EXPIRED"
