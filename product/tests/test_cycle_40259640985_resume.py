"""Operational resume 40259640985: finish and verify snapshot 40257469937.

The snapshot committed real work (the live-cache replay and the v68 diagnosis)
but the team job ended without an independent audit ref, and its own report
claimed a cycle test that was never committed.  This test locks the repair:

* the snapshot is diagnosed as a committed delta but UNADJUDICATED;
* the pre-repair validation gap is recorded, and the missing test now exists;
* the current report and state block name the resume honestly;
* the audit-readiness dossier is wired to the snapshot, not to a stale run.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUN_ID = "40259640985"
SNAPSHOT = "40257469937"
PREDECESSOR = "40257275384"

DIAGNOSIS = (ROOT / "results" / "product" / "orchestration"
             / f"CYCLE_{SNAPSHOT}_resume_diagnosis.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
STATE = ROOT / "state" / "product.json"
MISSING_TEST = ROOT / "product" / "tests" / f"test_cycle_{PREDECESSOR}.py"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_snapshot_diagnosis_records_a_committed_delta_without_a_gate():
    diag = _load(DIAGNOSIS)
    assert diag["run_id"] == SNAPSHOT
    assert diag["predecessor_run_id"] == PREDECESSOR
    assert diag["orchestration"]["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert diag["orchestration"]["mechanism_unobserved"] is True
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 12
    assert "product/live_cache_replay.py" in (
        diag["durable_delta"]["changed_paths_sample"])
    assert diag["adjudication"]["audit"]["audit_ref_present"] is False
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_validation_gap_is_recorded_and_repaired():
    diag = _load(DIAGNOSIS)
    gap = diag["validation_findings"]
    # The diagnosis preserves the snapshot state: the report claimed this test
    # but the snapshot commit did not contain it.
    assert f"product/tests/test_cycle_{PREDECESSOR}.py" in (
        gap["missing_claimed_cycle_tests"])
    assert gap["dossiers_with_skipped_mandatory_reruns"]
    fresh = gap["runtime_preflight"]["fresh_runner_no_site_probe"]
    assert fresh["ok"] is False
    assert "numpy" in (fresh["missing"] or [])
    # The resuming cycle committed the missing test.
    assert MISSING_TEST.is_file()


def test_current_report_and_state_are_honest():
    report = REPORT.read_text(encoding="utf-8")
    assert f"Run:** {RUN_ID}" in report or f"run {RUN_ID}" in report
    for needle in (
        "fresh-runner",
        "numpy",
        "test_cycle_40257275384.py",
        "human_gate_ready=false",
        "UNADJUDICATED",
        "preserv",
    ):
        assert needle in report, needle

    state = _load(STATE)
    # The executing cycle id advances monotonically; this historical test
    # must not pin the state to an already-superseded run.
    assert state["current_cycle_run_id"] >= int(RUN_ID)
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["ready_for_owner_session"] is False
    # The accepted pointer also advances; a historical resume must not pin
    # it to the pointer that was current when the test was written.
    assert state["accepted_run_id"].startswith("CYCLE_")
    assert int(state["accepted_run_id"].split("_")[-1]) >= int(RUN_ID)
    assert state["accepted_commit"]
    block = state[f"cycle_{RUN_ID}_operational_resume"]
    assert int(block["snapshot_run_id"]) == int(SNAPSHOT)
    assert block["posture"]["human_gate_ready"] is False
    assert block["validation_repairs"]["missing_cycle_test_added"] is True

    history = {str(row["run_id"]): row for row in state["run_history"]}
    assert history[SNAPSHOT]["status"] == "COMMITTED_DELTA_NO_AUDIT"
    assert history[RUN_ID]["status"] == "OPERATIONAL_RESUME_VALIDATION_REPAIR"


def test_audit_readiness_profile_targets_the_snapshot_not_a_stale_run():
    spec = importlib.util.spec_from_file_location(
        "audit_readiness_cycle", ROOT / "product" / "audit_readiness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    profile = module.select_profile(RUN_ID)
    assert profile["resumed_run_id"] == SNAPSHOT
    assert profile["predecessor_run_id"] == PREDECESSOR
    assert (ROOT / profile["resume_diag"]).is_file()
    assert (ROOT / profile["cycle_test"]).is_file()
    assert (ROOT / profile["current_report"]).is_file()
    assert profile["changed_files"] == 12
