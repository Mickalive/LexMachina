"""Operational resume 41159331087: diagnosis of failed run 41159162128.

The resumed run was a fresh v68 product cycle dispatched off the accepted
snapshot ``f7bc77a0``.  Its team job failed at ``Run lane cycle`` in **17 s**
with an OBSERVED exit code 1, so the two producer-verification steps and the
entire audit/integrate chain were skipped and the team ref stayed byte-identical
to the accepted snapshot.  This test locks the resume's diagnosis and its
instrument repairs fail-closed:

* the failure is recorded from the PUBLIC run/jobs snapshot (step conclusions
  and timings) plus the public check-run annotation that carries exit code 1;
  the log-level cause stays UNOBSERVED because the logs endpoint answered
  HTTP 403 - no cause is invented, and no model defect is asserted;
* exit code 1 is not one of the wrapper's own named exits, so it is reported as
  a generic passthrough with every named branch ruled out by arithmetic (the
  step ran 17 s, so it cannot have outrun a 2700 s quantum nor completed a
  90 s retry sleep);
* the durable delta over the accepted snapshot is ZERO and the run is
  UNADJUDICATED (no /audit ref, no gate) - the snapshot has still never been
  independently audited, because its auditor died of quantum expiry in 41152471808;
* the failing-step duration fix is pinned: the diagnosis uses the FAILING
  step's duration (17 s) instead of borrowing a non-existent audit-step one,
  and the predecessor regression (audit death at 2705 s > 2700 s) stays recorded;
* the pointer stays on the accepted snapshot CYCLE_40284658455 / 7be4480e and
  the direction version stays 68;
* the vertical slice still runs from fixture bytes and produces a
  source-linked, clickable map with finite coordinates and >=2 clusters.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "41159331087"
RESUMED_RUN_ID = "41159162128"
PREDECESSOR_RUN_ID = "41152471808"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT_HEAD = "f7bc77a00d7a548f753b7466199d1fa72c834337"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
ORCH_RESUMED = ORCH / f"CYCLE_{RESUMED_RUN_ID}_orchestration.json"
ORCH_PRED = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_orchestration.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_snapshot_records_the_step_failure_and_the_observed_exit_code():
    raw = _load(RAW)
    assert raw["schema"] == "github-actions-run-jobs-snapshot/1"
    assert raw["logs_endpoint_status"] == 403
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s for s in team["steps"]}
    assert steps["Run lane cycle"]["conclusion"] == "failure"
    assert steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert steps["Enforce lane write scope"]["conclusion"] == "skipped"
    from datetime import datetime
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    run_s = (datetime.strptime(steps["Run lane cycle"]["completed_at"], fmt)
             - datetime.strptime(steps["Run lane cycle"]["started_at"], fmt)
             ).total_seconds()
    assert run_s == 17.0
    assert run_s < 2700  # a quantum-expiry narrative would be false
    # The exit code is OBSERVED from the public check-run annotation, not guessed.
    messages = [a["message"] for a in raw.get("annotations") or []]
    assert "Process completed with exit code 1." in messages


def test_orchestration_diagnosis_uses_the_failing_step_duration():
    doc = _load(ORCH_RESUMED)
    assert doc["run_id"] == int(RESUMED_RUN_ID)
    assert doc["classification"]["class"] == "TEAM_JOB_FAILED"
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 1
    assert diag["failing_step"] == "Run lane cycle"
    assert diag["failing_step_duration_s"] == 17.0
    assert diag["step_duration_used_s"] == 17.0
    assert "Run lane cycle" in diag["step_duration_source"]
    # Exit 1 is not a wrapper code: every named branch is ruled out, and the
    # only surviving statement is that a generic passthrough is possible.
    assert diag["candidates"]["surviving_named_branches"] == []
    assert diag["candidates"]["generic_passthrough_possible"] is True
    quantum = next(c for c in diag["candidates"]["named_branches"] if c["rc"] == 78)
    retry = next(c for c in diag["candidates"]["named_branches"] if c["rc"] == 75)
    assert quantum["ruled_out"] is True
    assert retry["ruled_out"] is True
    # Preflight (registry + model health) replays clean locally, so the
    # pre-opencode exits are ruled out too; that is why no model defect may be
    # asserted from this exit code.
    assert diag["preflight"]["all_pass"] is True
    for rc in (64, 65, 66, 76, 77):
        cand = next(c for c in diag["candidates"]["named_branches"] if c["rc"] == rc)
        assert cand["ruled_out"] is True, rc
    assert doc["team_branch_exists"] is True
    assert "NOT a product verdict" in doc["claim_ceiling"]


def test_predecessor_audit_quantum_death_is_recorded_as_evidence():
    """The snapshot has never been audited: its auditor died on the quantum.

    This is why the resume stays fail-closed instead of promoting the snapshot,
    and it is measured (2705 s > 2700 s, exit 78 survives the arithmetic) rather
    than narrated.
    """
    doc = _load(ORCH_PRED)
    assert doc["run_id"] == int(PREDECESSOR_RUN_ID)
    assert doc["classification"]["class"] == "AUDIT_STEP_FAILED_NO_GATE"
    diag = doc["diagnosis"]
    assert diag["exit_code"] == 78
    assert diag["failing_step"] == "Independent audit"
    assert diag["step_duration_used_s"] > 2700
    assert diag["candidates"]["surviving_named_branches"] == [
        "LEX_WORK_QUANTUM_EXPIRED"]
    assert diag["candidates"]["generic_passthrough_possible"] is False


def test_resume_diagnosis_records_zero_delta_and_unadjudicated_status():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["resumed_by_run_id"] == EXECUTING_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["failed_step"] == "Run lane cycle"
    assert orch["failed_step_seconds"] == 17.0
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_LANE_CYCLE_STEP_FAILED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] == 1
    assert orch["audit"]["skipped"] is True
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert diag["adjudication"] == {
        "status": "UNADJUDICATED", "accepted": False,
        "audit_ref_exists": False, "reason": diag["adjudication"]["reason"]}


def test_state_pointer_stays_on_the_accepted_snapshot_and_records_both_runs():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_HEAD
    from product.state_contract import accepted_pointer_evidence
    ev = accepted_pointer_evidence(st, ROOT)
    assert not ev["problems"], ev
    assert ev["gate_ok"] and ev["accept_commit_present"]
    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    # 41152471808 was itself a resume, not a failure run: its history entry is
    # the resume status and it never reached a gate (its auditor died on the
    # quantum), which is the gap this cycle records.
    assert hist[PREDECESSOR_RUN_ID]["status"] == (
        "OPERATIONAL_RESUME_AUDIT_READINESS_REPAIR")
    assert hist[PREDECESSOR_RUN_ID]["audit_gate"] == "NONE_YET"
    assert hist[RESUMED_RUN_ID]["status"].startswith(
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED")
    assert hist[EXECUTING_RUN_ID]["audit_gate"] == "NONE_YET"
    # The predecessor's own attribution block must survive later resumes, the
    # same durable invariant this cycle pinned in test_cycle_41152471808.py.
    pred_block = st["cycle_41152471808_operational_resume"]
    assert pred_block["run_id"] == int(PREDECESSOR_RUN_ID)
    assert pred_block["resumed_snapshot"]["run_id"] == 41149776023
    assert (ROOT / pred_block["diagnosis"]).is_file()
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
    ):
        assert st[key] is expected or st[key] == expected, (key, st[key])
    block = st["cycle_41159331087_operational_resume"]
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert (ROOT / block["diagnosis"]).is_file()
    assert (ROOT / block["raw_snapshot"]).is_file()


def test_audit_readiness_models_this_cycle_and_fails_closed_on_unknown_runs():
    from product import audit_readiness as ar
    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["mechanism_kind"] == "observed_step_failure"
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["delta_kind"] == "zero"
    assert prof["exit_code"] == 1
    assert prof["lane_cycle_step_seconds"] == 17.0
    assert prof["cycle_test"] == "product/tests/test_cycle_41159331087.py"
    # The predecessor profile must keep its own measured facts.
    pred = ar.select_profile(PREDECESSOR_RUN_ID)
    assert pred["exit_code"] is None  # not observed in that run's annotations
    assert pred["lane_cycle_step_seconds"] == 1670.0
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_previous_cycle_tests_are_green_on_this_tree():
    for test in ("product/tests/test_cycle_41152471808.py",
                 "product/tests/test_cycle_40284658455.py"):
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", test],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600)
        assert proc.returncode == 0, test + "\n" + proc.stdout[-4000:]


def test_vertical_slice_still_produces_a_source_linked_clickable_map():
    with tempfile.TemporaryDirectory(prefix="slice-41159331087-") as tmp:
        proc = subprocess.run(
            [sys.executable, "product/offline_slice.py",
             "--slug", "rent-default", "--top-n", "100",
             "--no-enrich", "--verify", "--quiet", "--out", tmp],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
        bundle = _load(Path(tmp) / "rent-default.bundle.json")
        rows = bundle.get("decisions") or []
        assert len(rows) >= 40
        assert all(r.get("canonical_url") for r in rows)
        assert all(isinstance(r.get("x"), (int, float))
                   and isinstance(r.get("y"), (int, float)) for r in rows)
        assert len({r.get("cluster_id") for r in rows}) >= 2
        summary = _load(Path(tmp) / "summary.json")
        assert summary["verified"] is True
        assert summary["page_contract"] is True
