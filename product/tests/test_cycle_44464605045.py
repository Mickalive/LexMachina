"""Operational resume 44464605045 of team-quantum snapshot 44459256873.

Unlike the earlier 44452532371 snapshot (audit job died at ``Independent
audit``), run 44459256873 failed in the TEAM job's ``Run lane cycle`` step:
public check-run annotations show ``LEX_WORK_QUANTUM_EXPIRED seconds=2700``
and exit 78 after 2705.0 s, so state validation, write-scope enforcement and
the audit job never ran. This test pins that observed mechanism, the committed
13-file durable delta, the fail-closed state block, and the audit-readiness
profile that lets the next independent audit consume the slice without
re-deriving GitHub facts. No gate, verdict or human-gate readiness is asserted.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "44464605045"
RESUMED_RUN_ID = "44459256873"
PREDECESSOR_HEAD = "294f1cfc847a584d3099c04a1f5a95322661d88c"
SNAPSHOT_HEAD = "c3bd920c"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_team_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
GATE = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{EXECUTING_RUN_ID}_GATE.json")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_snapshot_shows_rc78_quantum_in_the_team_lane_cycle_step():
    raw = _load(RAW)
    assert raw["schema"] == "product-run-jobs-snapshot/1"
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    assert raw["run"]["html_url"].endswith("/actions/runs/44459256873")
    assert raw["logs_endpoint_status"] == 403
    jobs = {j["name"]: j for j in raw["jobs"]}
    team_steps = {s["name"]: s for s in jobs["team"]["steps"]}
    assert jobs["team"]["conclusion"] == "failure"
    assert team_steps["Run lane cycle"]["conclusion"] == "failure"
    assert team_steps["Run lane cycle"]["started_at"]
    assert team_steps["Validate active MVP producer state"]["conclusion"] == "skipped"
    assert team_steps["Enforce lane write scope"]["conclusion"] == "skipped"
    assert team_steps["Persist team snapshot"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    anns = raw["annotations"]["135341777688"]
    messages = [a["message"] for a in anns]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in messages)
    assert any("Process completed with exit code 78." in m for m in messages)
    assert any("Agent quantum ended cleanly" in m for m in messages)
    assert not any("LEX_ZERO_DELTA_REPAIR" in m for m in messages)


def test_classifier_reproduces_team_quantum_mechanism():
    from product import audit_step_diagnosis as asd
    result = asd.classify(_load(RAW))
    assert result["run_id"] == RESUMED_RUN_ID
    assert result["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert result["mechanism"]["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert result["mechanism"]["quantum_expired"] is True
    assert result["mechanism"]["quantum_seconds"] == 2700
    assert result["mechanism"]["exit_code"] == 78
    assert result["mechanism"]["annotations_available"] is True
    assert result["team"]["failed_step"] == "Run lane cycle"
    assert result["team"]["failed_step_seconds"] == 2705.0
    assert result["audit"]["gate_file_written"] is False
    assert result["adjudication"]["product_defect"] is False
    assert result["adjudication"]["verdict_written"] is False


def test_resume_diagnosis_is_reproducible_and_commits_a_13_file_delta():
    diag = _load(DIAG)
    assert diag["schema"] == "product-resume-snapshot-diagnosis/1"
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == "44452532371"
    assert diag["raw_snapshot"].endswith(
        f"CYCLE_{RESUMED_RUN_ID}_team_jobs_raw.json")
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["mechanism"]["quantum_seconds"] == 2700
    assert orch["mechanism"]["exit_code"] == 78
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 13
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    assert "product/query/counter_evidence_span.py" in delta["changed_paths_sample"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False

    # The diagnosis is a generated artifact: verify it can be reproduced from
    # the committed raw snapshot plus the resolved predecessor head.
    out = ROOT / "results" / "product" / "orchestration"
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "reproduced.json"
        proc = subprocess.run([
            sys.executable, "product/resume_snapshot_diagnosis.py",
            "--run-id", RESUMED_RUN_ID,
            "--predecessor-run-id", "44452532371",
            "--predecessor-ref", PREDECESSOR_HEAD,
            "--raw", str(RAW.relative_to(ROOT)),
            "--out", str(target),
        ], cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr
        reproduced = _load(target)
    assert reproduced["orchestration"]["classification"] == orch["classification"]
    assert reproduced["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert reproduced["durable_delta"]["changed_files"] == 13


def test_state_is_fail_closed_and_records_this_resume():
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == 68
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    assert st["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    hist = [r for r in st["run_history"]
            if r.get("run_id") == int(EXECUTING_RUN_ID)]
    assert len(hist) == 1
    assert hist[0]["audit_gate"] == "NONE_YET"
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["status"] == "UNADJUDICATED_OPERATIONAL_RESUME_TEAM_QUANTUM"
    assert block["mechanism"] == "OBSERVED_QUANTUM_EXPIRED"
    assert block["durable_delta"] == "COMMITTED_DELTA"
    assert block["verdict"] == "NONE_UNADJUDICATED"
    assert block["accepted_this_cycle"] is False
    assert block["gate_minted"] is False
    assert block["audit_namespace_written"] is False


def test_audit_readiness_profile_pins_this_run_without_minting_a_gate():
    from product import audit_readiness as ar
    profile = ar.PROFILES[EXECUTING_RUN_ID]
    assert profile["alias_of"] if "alias_of" in profile else True
    assert profile["resumed_run_id"] == RESUMED_RUN_ID
    assert profile["predecessor_run_id"] == "44452532371"
    assert profile["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert profile["mechanism_kind"] == "observed"
    assert profile["failed_job"] == "team"
    assert profile["quantum_seconds"] == 2700
    assert profile["exit_code"] == 78
    assert profile["failed_step_seconds"] == 2705.0
    assert profile["delta_kind"] == "committed"
    assert profile["changed_files"] == 13
    assert profile["cycle_test"].endswith(f"test_cycle_{EXECUTING_RUN_ID}.py")
    assert profile["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert REPORT.is_file() and "UNADJUDICATED" in REPORT.read_text()
    assert not GATE.exists(), "producer must never write an audit gate"


def test_content_family_still_proves_the_v68_rejection_leg():
    cf = _load(ROOT / "results" / "product" / "counter_content_family"
               / "CYCLE_40257275384.json")
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_decisions"] == 4900
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["still_verified"]
    assert cf["ordered_work_2_success_rule"]["met"] is True
