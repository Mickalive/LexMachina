"""Cycle 44856384487: audit-readiness of resumed snapshot 44856191029.

This test re-derives the operational resume's claims from committed artifacts
only.  It locks:

* the orchestration failure classification (team lane-cycle step failed, job
  logs HTTP 403 => mechanism UNOBSERVED, audit/integrate skipped) and the
  git-ref proof that the persisted snapshot has ZERO_DURABLE_DELTA;
* UNADJUDICATED / not-a-product-defect / no-verdict, with no /audit gate and
  no promotion of the resumed run;
* the executed verification of the landed v68 deliverable: state contract,
  170 passing MVP core tests, and the fixed-path content family's zero defect
  histogram with zero false rejects (P0 not re-diagnosed);
* accepted-pointer requirement 4 (PASS gate AND accept commit) and the
  fail-closed posture;
* the bounded dossier, report of record and this test as the audit-ready
  handoff set - a dossier is a handoff aid, never a gate or serve decision.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "44856384487"
RESUMED_RUN_ID = "44856191029"
SNAPSHOT_HEAD = "1cda48f19c895261e62527e156ee9c4852a62ac2"

STATE = ROOT / "state" / "product.json"
RAW = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json")
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json")
FAMILY = ROOT / "results" / "product" / "counter_content_family" / (
    f"CYCLE_{EXECUTING_RUN_ID}.json")
DOSSIER = ROOT / "results" / "product" / "audit_readiness" / (
    f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
ACCEPTED_GATE = ROOT / "results" / "audit" / "product" / (
    "CYCLE_40269774540_GATE.json")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def test_orchestration_failure_is_classified_without_inventing_a_cause():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    team = orch["team"]
    assert team["conclusion"] == "failure"
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 16.0
    assert team["producer_state_validation_step_conclusion"] == "skipped"
    assert team["write_scope_step_conclusion"] == "skipped"
    assert team["team_snapshot_step_conclusion"] == "success"
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"
    mech = orch["mechanism"]
    assert mech["status"] == "UNOBSERVED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["exit_code"] is None
    assert orch["observed_failure"]["source"] == "none"


def test_raw_jobs_snapshot_agrees_with_the_diagnosis():
    raw = _load(RAW)
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["logs_endpoint_status"] == 403
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "failure"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    assert jobs["resilience"]["conclusion"] == "success"
    steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"


def test_snapshot_has_zero_durable_delta_and_stays_unadjudicated():
    diag = _load(DIAG)
    delta = diag["durable_delta"]
    assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT_HEAD
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["product_defect"] is False
    assert diag["adjudication"]["verdict_written"] is False
    assert diag["adjudication"]["audit"]["audit_ref_present"] is False
    assert diag["adjudication"]["audit"]["gate_file_present"] is False
    assert diag["adjudication"]["accepted"] is False
    # No producer-minted audit gate may be laundered into an audit verdict.
    assert not (ROOT / "results" / "audit" / "product" /
                f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists()
    audit_ref = _git("ls-remote", "--heads", "origin",
                     f"refs/heads/cycle/core/product/{RESUMED_RUN_ID}/audit")
    assert audit_ref == "", f"unexpected /audit ref for {RESUMED_RUN_ID}"


def test_state_attributes_the_executing_run_and_keeps_posture_fail_closed():
    st = _load(STATE)
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    blk = st["cycle_44856384487_operational_resume"]
    assert blk["resumed_run_id"] == RESUMED_RUN_ID
    assert blk["executing_run_id"] == EXECUTING_RUN_ID
    assert blk["orchestration_failure_of_record"]["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert blk["orchestration_failure_of_record"]["mechanism_status"] == (
        "UNOBSERVED")
    assert blk["orchestration_failure_of_record"]["durable_delta"] == (
        "ZERO_DURABLE_DELTA")
    assert blk["orchestration_failure_of_record"]["adjudication"] == (
        "UNADJUDICATED")
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
        ("owner_decision_required", False),
        ("direction_version", 68),
    ):
        assert st[key] is expected or st[key] == expected, (key, st[key])


def test_accepted_pointer_still_satisfies_both_halves_of_requirement_4():
    st = _load(STATE)
    assert st["accepted_run_id"] == "CYCLE_40269774540"
    assert st["accepted_commit"] == (
        "5adaa66d4ad2b9702cd023bfd49d743667f9e638")
    gate = _load(ACCEPTED_GATE)
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    # lab/product may have advanced with a newer accept commit; requirement 4
    # holds while this accept commit remains an ancestor of its HEAD.
    head = _git("ls-remote", "--heads", "origin", "refs/heads/lab/product").split()[0]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", st["accepted_commit"], head],
        cwd=str(ROOT))
    assert ancestor.returncode == 0, (head, st["accepted_commit"])
    msg = _git("log", "-1", "--format=%s", st["accepted_commit"])
    assert msg == "accept product cycle 40269774540", msg


def test_landed_v68_deliverable_is_reverified_not_rediagnosed():
    fam = _load(FAMILY)
    assert fam["run_id"] == EXECUTING_RUN_ID
    assert fam["direction_version"] == 68
    fixed = fam["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 49
    assert fixed["n_decisions"] == 4900
    assert fixed["n_verified"] == 55
    assert fixed["n_verified_defective"] == 0
    hist = fixed["defect_histogram"]
    assert hist == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert fam["false_reject_count"] == 0
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["met"] is True
    # Frozen packet-of-record bytes are REPORTED-ONLY, never an emission claim.
    pkt = fam["packet_v3_reemission"]
    assert pkt["checks"]["packet_bytes_unchanged"] is True
    assert pkt["v68_rejection_effect_on_v3"]["total_downgrades"] == 0


def test_audit_readiness_dossier_is_bounded_and_matches_the_claimed_numeric_state():
    d = _load(DOSSIER)
    assert d["schema"] == "product-audit-readiness-dossier/1"
    assert d["run_id"] == EXECUTING_RUN_ID
    assert d["resumed_run_id"] == RESUMED_RUN_ID
    assert d["direction_version"] == 68
    assert d["readiness"] == "AUDIT_READY"
    assert d["gates_minted"] == 0
    assert d["frozen_bars_scored"] == 0
    assert d["serve_verdict_rerun"] is False
    assert d["posture"]["continue_recommended"] is True
    for key in ("human_gate_ready", "machine_gate_ready",
                "ready_for_owner_session", "packet_admitted",
                "owner_decision_required"):
        assert d["posture"][key] is False, (key, d["posture"][key])
    orch = d["checks"]["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["mechanism_status"] == "UNOBSERVED"
    assert orch["logs_endpoint_status"] == 403
    assert orch["durable_delta"] == "ZERO_DURABLE_DELTA"
    assert orch["audit_gate_written"] is False
    fam = d["checks"]["content_family"]
    assert fam["n_bundles"] == 49 and fam["n_decisions"] == 4900
    assert fam["n_verified_defective"] == 0
    assert fam["success_rule_met"] is True
    assert d["problems"] == []
    installed = d["checks"]["verification"]["environment"]["installed"]
    assert installed["numpy"] == "2.5.4"
    assert installed["scipy"] == "1.18.1"
    assert installed["scikit_learn"] == "1.9.1"
    assert installed["pytest"] == "9.1.1"


def test_report_of_record_names_both_runs_and_the_claim_ceiling():
    text = REPORT.read_text(encoding="utf-8")
    assert EXECUTING_RUN_ID in text
    assert RESUMED_RUN_ID in text
    assert "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE" in text
    assert "ZERO_DURABLE_DELTA" in text
    assert "UNADJUDICATED" in text
    assert "170 passed" in text
    assert "49 bundles" in text
    assert "no gate" in text.lower() or "no gate is minted" in text.lower()
    assert "continue_recommended" in text
