"""Operational resume 40263666190: finish and verify snapshot 40263483436.

Three consecutive attempts on the same tree (f9b0db25, the accepted lab tree
of cycle 40259640985) failed before any independent gate: 40262401687's agent
hit the fresh-runner ``ModuleNotFoundError`` (numpy/sklearn) and exited 0 with
an unchanged tree after ~526 s, so the wrapper's delta guard rejected it
(``LEX_ZERO_DELTA_REPAIR``, exit 67; ``quantum_expired=false`` - no work
quantum expired), then 40263308953 and 40263483436 were both rejected by the
model gateway on an unrecognized request parameter (``permissions``).  The
workflow persisted each unchanged tree with ``if: always()``, so the team ref
exists but proves no work (ZERO_DURABLE_DELTA), and no run was ever
adjudicated.

This test locks the resume's repairs and its evidence:

* the committed lane-cycle logs classify all three attempts, distinguishing
  workflow annotations from text the agent merely *quoted*;
* the step-diagnosis instrument no longer claims "logs are not downloadable"
  once the logs endpoint answered HTTP 200 (mechanism
  ``OBSERVED_LOGS_AVAILABLE_NO_QUANTUM``);
* the bounded-dossier profile accepts the third mechanism kind and cross-
  checks it against the log-evidence artifact;
* the query runtime self-heals through the test harness (``ensure()``), and
  the legacy-174k neighbors tests skip - never fail - when this lane mounts
  no fractal-map representations;
* the report and state name the *executing* run honestly (the resume chain
  40263666190 <- 40263483436 <- 40263308953 <- 40262401687 stays recorded as
  history), fail-closed.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUN_ID = "40263666190"
SNAPSHOT = "40263483436"
PREDECESSOR = "40263308953"
FIRST_ATTEMPT = "40262401687"
MIDDLE_ATTEMPT = "40263308953"

ORCH = ROOT / "results" / "product" / "orchestration"
LOGS_DIR = ORCH / f"CYCLE_{RUN_ID}_lane_cycle_logs"
LOG_EVIDENCE = ORCH / f"CYCLE_{RUN_ID}_lane_cycle_log_evidence.json"
DIAGNOSIS = ORCH / f"CYCLE_{SNAPSHOT}_resume_diagnosis.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
STATE = ROOT / "state" / "product.json"
CYCLE_TEST = ROOT / "product" / "tests" / f"test_cycle_{RUN_ID}_resume.py"

# Attribution convention (audit CYCLE_40267501346 R1): the state's current
# pointer is the EXECUTING run of the current cycle, never a resumed snapshot
# whose own block is UNADJUDICATED.  The repair of the rejected cycle 40267501346
# executes as run 40269774540.
EXECUTING_RUN_ID = "40269774540"
REPAIRED_RUN_ID = "40267501346"
CURRENT_REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"

UPSTREAM_SIGNATURE = "unsupported_parameter"
UPSTREAM_DETAIL = "Unrecognized request argument supplied: permissions."


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_lane_cycle_log_evidence_records_all_three_attempts():
    ev = _load(LOG_EVIDENCE)
    assert ev["resuming_run_id"] == RUN_ID
    runs = ev["runs"]
    assert set(runs) == {FIRST_ATTEMPT, MIDDLE_ATTEMPT, SNAPSHOT}

    first = runs[FIRST_ATTEMPT]
    assert first["classification"] == "AGENT_FINISHED_ZERO_DURABLE_DELTA"
    assert first["exit_codes"] == [67]
    assert first["model_pool"]["selected"] == "opencode/nemotron-3.5-lightning-free"
    assert first["markers"]["zero_delta_guard"] is True
    assert first["markers"]["quantum_expired"] is False
    assert first["markers"]["map_data_missing_positions"] is True

    for rid in (MIDDLE_ATTEMPT, SNAPSHOT):
        entry = runs[rid]
        assert entry["classification"] == (
            "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER"), rid
        assert entry["exit_codes"] == [1]
        assert entry["model_pool"]["selected"] == "opencode/beam-free"
        assert entry["upstream_error"]["signature"] == UPSTREAM_SIGNATURE
        assert entry["upstream_error"]["detail"] == UPSTREAM_DETAIL
        assert entry["markers"]["quantum_expired"] is False
        assert entry["markers"]["non_transient_failure"] is True

    control = ev.get("control_plane_items") or []
    joined = json.dumps(control)
    assert "model_pool" in joined or "tool_probe" in joined
    assert "bootstrap_query_env" in joined or "core-lane" in joined


def test_log_parser_separates_workflow_annotations_from_quoted_history():
    """The parser's core invariant, proven on synthetic text.

    An agent that writes its own diagnosis QUOTES old annotations
    (``"annotation": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"``).  Honouring
    that quote would label a model-gateway rejection as a work-quantum
    expiry - exactly the misclassification that stalled this snapshot's
    diagnosis for three cycles.  Only ``##[error]``-prefixed annotation
    lines are the run's own verdicts.
    """
    from product import lane_cycle_log_evidence as lcle

    quoted_only = (
        '2026-10-26T03:14:49.1742084Z    "quantum_seconds": 2700,\n'
        '2026-10-26T03:14:49.1742314Z    "exit_code": 78,\n'
        '2026-10-26T03:14:49.1742592Z    "annotation": '
        '"LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2468",\n'
        "2026-10-26T03:20:49.1000000Z LEX_MODEL_POOL size=4 "
        "slot=core:product:v68:40263483436 requested=opencode/x-preview-f-free "
        "selected=opencode/beam-free index=3\n"
        "2026-10-26T03:20:49.1800000Z Upstream request failed: "
        "[unsupported_parameter] Unrecognized request argument supplied: "
        "permissions.\n"
        "2026-10-26T03:20:49.2000000Z OpenCode failed without transient/auth "
        "signature (rc=1)\n"
        "2026-10-26T03:20:49.3000000Z LEX_AGENT_CARD_OK product\n"
        "2026-10-26T03:20:50.0000000Z ##[error]Process completed with exit "
        "code 1.\n"
    )
    rec = lcle.parse_lane_cycle_log(quoted_only)
    assert rec["classification"] == "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER"
    assert rec["markers"]["quantum_expired"] is False
    assert rec["markers"]["markers_quoted_from_history_only"] == [
        "LEX_WORK_QUANTUM_EXPIRED"]
    assert rec["upstream_error"]["signature"] == UPSTREAM_SIGNATURE

    annotated = (
        "2026-10-26T03:16:52Z LEX_AGENT_CARD_OK product\n"
        "2026-10-26T03:16:52Z ##[error]LEX_WORK_QUANTUM_EXPIRED "
        "seconds=2700 pid=2468\n"
        "2026-10-26T03:16:52Z ##[error]Process completed with exit code 78.\n"
    )
    rec2 = lcle.parse_lane_cycle_log(annotated)
    assert rec2["markers"]["quantum_expired"] is True
    assert rec2["classification"] == "WORK_QUANTUM_EXPIRED"
    assert rec2["exit_codes"] == [78]


def test_resume_diagnosis_is_observed_and_zero_delta():
    diag = _load(DIAGNOSIS)
    assert diag["run_id"] == SNAPSHOT
    assert diag["predecessor_run_id"] == PREDECESSOR
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 16.0
    assert orch["team"]["team_snapshot_persisted_after_failed_team_job"] is True
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_LOGS_AVAILABLE_NO_QUANTUM"
    assert mech["logs_available"] is True
    assert mech["logs_endpoint_status"] == 200
    assert mech["quantum_expired"] is False
    assert "WERE downloadable" in mech["claim"]
    assert "not downloadable" not in mech["claim"]

    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"]

    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    findings = diag["validation_findings"]
    assert findings["missing_claimed_cycle_tests"] == []
    assert findings["runtime_preflight"]["ok"] is True


def test_step_diagnosis_instrument_distinguishes_403_from_200_logs():
    """Regression pin for the instrument repair.

    A 403 snapshot (every historical raw) must still classify UNOBSERVED with
    the original claim; a 200 snapshot with no quantum annotation must say the
    logs WERE downloadable and must not assert a quantum expiry.
    """
    from product import audit_step_diagnosis as asd

    base = {
        "run": {"id": 1, "name": "x", "conclusion": "failure"},
        "jobs": [
            {"name": "team", "conclusion": "failure",
             "steps": [
                 {"name": "Run lane cycle", "conclusion": "failure",
                  "started_at": "2026-10-26T03:20:49Z",
                  "completed_at": "2026-10-26T03:21:05Z"},
                 {"name": "Persist team snapshot", "conclusion": "success"},
             ]},
            {"name": "audit", "conclusion": "skipped", "steps": []},
            {"name": "integrate", "conclusion": "skipped", "steps": []},
        ],
    }
    legacy = dict(base, logs_endpoint_status=403)
    rec = asd.classify(legacy)
    assert rec["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert rec["mechanism"]["status"] == "UNOBSERVED"
    assert "not downloadable" in rec["mechanism"]["claim"]

    fetched = dict(base, logs_endpoint_status=200)
    rec2 = asd.classify(fetched)
    assert rec2["mechanism"]["status"] == "OBSERVED_LOGS_AVAILABLE_NO_QUANTUM"
    assert rec2["mechanism"]["logs_available"] is True
    assert rec2["mechanism"]["quantum_expired"] is False
    assert "WERE downloadable" in rec2["mechanism"]["claim"]
    assert "not downloadable" not in rec2["mechanism"]["claim"]


def test_raw_run_jobs_snapshots_are_committed_with_fetchable_logs():
    for rid in (FIRST_ATTEMPT, MIDDLE_ATTEMPT, SNAPSHOT):
        snap = _load(ORCH / f"CYCLE_{rid}_team_step_raw.json")
        assert snap["schema"] == "github-actions-run-jobs-snapshot/1"
        assert snap["logs_endpoint_status"] == 200, rid
        jobs = {j["name"]: j for j in snap["jobs"]}
        assert jobs["team"]["conclusion"] == "failure", rid
        assert jobs["audit"]["conclusion"] == "skipped", rid
        assert snap["run"]["id"] == int(rid)
    committed = (LOGS_DIR / f"{SNAPSHOT}_team_lane_cycle.log").read_text(
        encoding="utf-8")
    assert "OpenCode failed without transient" in committed
    assert "ghs_" not in committed, "job logs must be redacted of tokens"


def test_query_runtime_self_heals_through_the_test_harness():
    """Run 40262401687 died on numpy/sklearn; the harness now owns the fix."""
    from product import query_env

    probe = query_env.probe()
    ensured = query_env.ensure(install=False)
    assert ensured["ensured"]["skipped"] in ("already_present",
                                             "install_disabled")
    assert ensured["ok"] == probe["ok"]
    if probe["ok"]:
        assert ensured["ensured"]["attempted"] is False
    # The skip switch must stay fail-closed: a caller that asks to observe an
    # uninstalled environment is never quietly given an install.
    import os
    old = os.environ.get("LEX_QUERY_ENV_NO_AUTOBOOTSTRAP")
    os.environ["LEX_QUERY_ENV_NO_AUTOBOOTSTRAP"] = "1"
    try:
        saved = query_env.REQUIRED.get("definitely_absent_xyz_cycle_test")
        query_env.REQUIRED["definitely_absent_xyz_cycle_test"] = "test"
        try:
            off = query_env.ensure()
        finally:
            if saved is None:
                query_env.REQUIRED.pop("definitely_absent_xyz_cycle_test",
                                        None)
    finally:
        if old is None:
            os.environ.pop("LEX_QUERY_ENV_NO_AUTOBOOTSTRAP", None)
        else:
            os.environ["LEX_QUERY_ENV_NO_AUTOBOOTSTRAP"] = old
    assert off["ensured"]["skipped"] == "LEX_QUERY_ENV_NO_AUTOBOOTSTRAP"
    assert off["ensured"]["attempted"] is False
    assert "definitely_absent_xyz_cycle_test" in off["missing"]

    conftest = (ROOT / "product" / "tests" / "conftest.py").read_text(
        encoding="utf-8")
    assert "query_env.ensure()" in conftest
    assert "40262401687" in conftest


def test_legacy_map_neighbors_tests_skip_instead_of_failing():
    """Absent fractal-map mounts are environmental, never a red test."""
    test_file = ROOT / "product" / "tests" / "test_http_api_integration.py"
    src = test_file.read_text(encoding="utf-8")
    assert "_skip_unless_legacy_map()" in src
    assert src.count("_skip_unless_legacy_map()") >= 2
    assert pytest_skip_reason_ok(src)

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q", "-p",
         "no:cacheprovider"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600,
        check=False)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1]
    assert proc.returncode == 0, tail
    assert "failed" not in tail.split(" passed")[0], tail


def pytest_skip_reason_ok(src: str) -> bool:
    return ("PEERS=()" in src and "environmental" in src
            and "fractal-map" in src)


def test_dossier_profile_wires_the_third_mechanism_kind():
    from product import audit_readiness as ar

    prof = ar.select_profile(RUN_ID)
    assert prof["resumed_run_id"] == SNAPSHOT
    assert prof["predecessor_run_id"] == PREDECESSOR
    assert prof["mechanism_kind"] == "observed_log"
    assert prof["delta_kind"] == "zero"
    assert prof["exit_code"] == 1
    assert prof["upstream_signature"] == UPSTREAM_SIGNATURE
    assert Path(prof["lane_cycle_log_evidence"]).is_file()
    assert Path(prof["raw"]).is_file()
    assert Path(prof["resume_diag"]).is_file()

    ar.PROFILE.clear()
    ar.PROFILE.update(prof)
    try:
        check = ar.check_resumed_diagnosis()
    finally:
        ar.PROFILE.clear()
    assert check["status"] == "PASS", check


def test_current_report_and_state_are_honest():
    """Attribution invariant (audit CYCLE_40267501346 R1), fail-closed.

    The state's current-cycle pointer and the producer report-of-record name
    the EXECUTING run (40269774540, repairing rejected cycle 40267501346); the
    resumed chain stays recorded as history.  The historical report named for
    40263666190 carries an authoring-correction header instead of silently
    posing as that run's own cycle report.
    """
    # Historical report keeps its body and gains the correction header.
    report = REPORT.read_text(encoding="utf-8")
    for needle in (
        f"Run:** {RUN_ID}", SNAPSHOT, PREDECESSOR, FIRST_ATTEMPT,
        "ZERO_DURABLE_DELTA", "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER",
        UPSTREAM_SIGNATURE, "permissions", "OBSERVED_LOGS_AVAILABLE_NO_QUANTUM",
        "human_gate_ready=false", "machine_gate_ready=false",
        "continue_recommended=true", "UNADJUDICATED", "ensure",
        "AUTHORING CORRECTION", EXECUTING_RUN_ID, REPAIRED_RUN_ID,
    ):
        assert needle in report, needle
    assert "ghs_" not in report

    # The report-of-record names the executing run and the repaired cycle.
    current = CURRENT_REPORT.read_text(encoding="utf-8")
    for needle in (
        f"Run:** {EXECUTING_RUN_ID}", REPAIRED_RUN_ID, RUN_ID, SNAPSHOT,
        "REVISE", "required fixes", "quantum_expired=false",
        "human_gate_ready=false", "continue_recommended=true",
    ):
        assert needle in current, needle
    assert "ghs_" not in current

    state = _load(STATE)
    assert state["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert state["direction_version"] == 68
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["ready_for_owner_session"] is False

    # The repair block records the rejected cycle and its audit of record.
    repair = state[f"cycle_{EXECUTING_RUN_ID}_repair_of_{REPAIRED_RUN_ID}"]
    assert repair["schema"] == "product-cycle-repair/1"
    assert repair["run_id"] == int(EXECUTING_RUN_ID)
    assert repair["repaired_run_id"] == int(REPAIRED_RUN_ID)
    assert repair["direction_version"] == 68
    assert repair["rejected_audit"]["gate"] == "REVISE"
    assert repair["rejected_audit"]["required_fixes_count"] == 2
    assert repair["resumed_chain"] == [int(RUN_ID), int(SNAPSHOT),
                                       int(PREDECESSOR), int(FIRST_ATTEMPT)]
    assert set(repair["required_fixes_discharged"]) == {
        "R1_run_id_attribution", "R2_false_quantum_sentence"}
    assert repair["posture"]["human_gate_ready"] is False
    assert repair["posture"]["continue_recommended"] is True

    # The resumed chain stays recorded as history, unchanged in substance.
    block = state[f"cycle_{RUN_ID}_operational_resume"]
    assert block["schema"] == "product-operational-resume/1"
    assert block["snapshot_run_id"] == int(SNAPSHOT)
    assert block["predecessor_run_id"] == int(PREDECESSOR)
    assert block["direction_version"] == 68
    assert block["posture"]["human_gate_ready"] is False
    assert block["orchestration_of_record"]["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert block["orchestration_of_record"]["mechanism"] == (
        "OBSERVED_LOGS_AVAILABLE_NO_QUANTUM")
    assert block["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    repairs = block["validation_repairs"]
    assert repairs["fresh_runner_self_heal_added"] is True
    assert repairs["legacy_map_tests_skip_on_absent_mounts"] is True
    assert repairs["logs_available_false_claim_removed"] is True
