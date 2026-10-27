"""Operational resume 40423889401: accepted-head no-op diagnosis + repair.

The resumed snapshot (run 40423595480) was byte-identical to the accepted
product head ``7be4480e``: the scheduler kept dispatching resumes after the
cycle it was resuming had already been accepted, so no producer delta was
possible and the always-run persist step republished the unchanged tree.
This test locks the honest diagnosis and the repairs:

* run 40423595480's team job failed at ``Run lane cycle`` (observed from the
  public jobs snapshot), job logs returned HTTP 403, so no log-level cause is
  asserted;
* its durable delta against ``origin/lab/product`` is ``ZERO_DURABLE_DELTA``
  and the accepted-head relation is ``SNAPSHOT_IS_ACCEPTED_HEAD`` with the
  explicit route-around ``NO_PRODUCER_DELTA_POSSIBLE``;
* the accepted pointer is the independently accepted cycle 40284658455 /
  ``7be4480e``, verified through product.state_contract (both halves of
  requirement 4), never through the mount;
* the accepted head's own cycle test
  ``test_cycle_40284658455.py`` was repaired because it still asserted that
  this accepted run had no gate - it now verifies the post-acceptance truth;
* ``product/audit_readiness.py`` models the new ``observed_steps`` mechanism;
* posture remains fail-closed and no frozen bar is touched.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "40423889401"
SNAPSHOT_RUN_ID = "40423595480"
ACCEPTED_RUN_ID = "40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{SNAPSHOT_RUN_ID}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{SNAPSHOT_RUN_ID}_resume_diagnosis.json"
STATE = ROOT / "state" / "product.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def test_raw_jobs_snapshot_observes_the_failed_step_and_the_always_persist():
    raw = _load(RAW)
    assert raw["run"]["id"] == int(SNAPSHOT_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    assert raw["logs_endpoint_status"] == 403
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert team["conclusion"] == "failure"
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"


def test_diagnosis_records_zero_delta_no_op_resume_and_no_asserted_cause():
    diag = _load(DIAG)
    assert diag["run_id"] == SNAPSHOT_RUN_ID
    assert diag["predecessor_run_id"] == ACCEPTED_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["team"]["team_snapshot_persisted_after_failed_team_job"] is True
    mech = orch["mechanism"]
    assert mech["status"] == "UNOBSERVED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert (orch.get("audit") or {}).get("gate_file_written") is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"] == ACCEPTED_COMMIT
    rel = diag["accepted_head_relation"]
    assert rel["classification"] == "SNAPSHOT_IS_ACCEPTED_HEAD"
    assert rel["is_accepted_head"] is True
    assert "NO_PRODUCER_DELTA_POSSIBLE" in rel["resume_action"]
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["audit"]["audit_ref_present"] is False


def test_state_advances_to_the_verified_accepted_pointer():
    from product.state_contract import accepted_pointer_evidence

    st = _load(STATE)
    assert st["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    pointer = accepted_pointer_evidence(st, ROOT)
    assert pointer["problems"] == [], pointer
    accept = _git("log", "--all", "--format=%H%x09%s", "--grep="
                  f"^accept product cycle {ACCEPTED_RUN_ID}$")
    assert any(line.endswith(f"accept product cycle {ACCEPTED_RUN_ID}")
               for line in accept.splitlines())
    gate = _load(ROOT / "results" / "audit" / "product"
                 / f"CYCLE_{ACCEPTED_RUN_ID}_GATE.json")
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []


def test_previous_accepted_head_cycle_test_is_green_after_the_repair():
    """The accepted head's cycle test must no longer assert pre-gate absence."""
    test_path = ROOT / "product" / "tests" / "test_cycle_40284658455.py"
    text = test_path.read_text(encoding="utf-8")
    assert "test_acceptance_materialized_for_the_executing_run" in text
    assert "unexpected /audit ref" not in text
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-q"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]


def test_accepted_head_guard_is_reusable_and_does_not_guess():
    from product.resume_snapshot_diagnosis import _accepted_head_relation

    same = _accepted_head_relation({
        "snapshot_head": ACCEPTED_COMMIT,
        "classification": "ZERO_DURABLE_DELTA",
    })
    assert same["classification"] in {
        "SNAPSHOT_IS_ACCEPTED_HEAD", "ACCEPTED_REF_ABSENT",
        "SNAPSHOT_REF_ABSENT",
    }
    if same["classification"] == "SNAPSHOT_IS_ACCEPTED_HEAD":
        assert "NO_PRODUCER_DELTA_POSSIBLE" in same["resume_action"]
    absent = _accepted_head_relation({"snapshot_head": None})
    assert absent["classification"] in {"ACCEPTED_REF_ABSENT",
                                        "SNAPSHOT_REF_ABSENT"}
    assert absent["is_accepted_head"] is None


def test_audit_readiness_models_this_failure_mode_and_this_run():
    from product import audit_readiness as ar

    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["resumed_run_id"] == SNAPSHOT_RUN_ID
    assert prof["predecessor_run_id"] == ACCEPTED_RUN_ID
    assert prof["mechanism_kind"] == "observed_steps"
    assert prof["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert prof["delta_kind"] == "zero"
    assert prof["cycle_test"] == "product/tests/test_cycle_40423889401.py"


def test_posture_stays_fail_closed_and_no_gate_is_minted():
    st = _load(STATE)
    for key, expected in (
        ("lane", "product"),
        ("direction_version", 68),
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
    ):
        assert st[key] == expected, (key, st[key])
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}.md").exists()
    assert REPORT.is_file()
