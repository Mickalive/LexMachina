"""Cycle 43572985556: operational resume of failed run 43572798128.

Locks the provider-rejection diagnosis, the zero-delta fact, the profile that
hands an auditor a bounded dossier, and the re-verified FAST-MVP deliverable.
It is intentionally a bounded, offline test: it reads committed artifacts and
never starts a server, fetches a ref or re-runs retrieval.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXECUTING_RUN_ID = "43572985556"
RESUMED_RUN_ID = "43572798128"
PREDECESSOR_RUN_ID = "43572630465"
SNAPSHOT_HEAD = "5de296f8c32d2e6688423e757eb917fe18c65e2f"
PREDECESSOR_HEAD = "5de296f8c32d2e6688423e757eb917fe18c65e2f"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
PRE_RAW = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_run_jobs_raw.json"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
LOG_EVIDENCE = ORCH / f"CYCLE_{EXECUTING_RUN_ID}_lane_cycle_log_evidence.json"
LOGS = ORCH / f"CYCLE_{EXECUTING_RUN_ID}_lane_cycle_logs"
PRE_LOGS = ORCH / f"CYCLE_{PREDECESSOR_RUN_ID}_logs"
STATE = ROOT / "state" / "product.json"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
SLICE = (ROOT / "results" / "product" / "offline_slice"
         / f"{EXECUTING_RUN_ID}_verify")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{EXECUTING_RUN_ID}_progressive_smoke.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
GATE = ROOT / "results" / "audit" / "product" / "CYCLE_40284658455_GATE.json"
OWN_GATE = ROOT / "results" / "audit" / "product" / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _steps(raw: dict, job_name: str) -> dict[str, str]:
    job = next(j for j in raw["jobs"] if j["name"] == job_name)
    return {s["name"]: s["conclusion"] for s in job.get("steps") or []}


def test_resume_diagnosis_is_observed_provider_rejection_zero_delta_unadjudicated():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID

    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["failed_job"] == "team"
    assert orch["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 16.0
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["team"]["producer_state_validation_ran"] is False
    assert orch["team"]["write_scope_step_ran"] is False

    mechanism = orch["mechanism"]
    assert mechanism["status"] == "OBSERVED_LOGS_AVAILABLE_NO_QUANTUM"
    assert mechanism["logs_available"] is True
    assert mechanism["logs_endpoint_status"] == 200
    assert mechanism["annotations_available"] is True
    assert mechanism["quantum_expired"] is False
    assert mechanism["quantum_seconds"] is None
    assert mechanism["exit_code"] == 1
    assert mechanism["lane_cycle_step_conclusion"] == "failure"
    assert mechanism["lane_cycle_step_seconds"] == 16.0
    assert mechanism["state_validation_step_conclusion"] == "skipped"
    assert mechanism["scope_step_conclusion"] == "skipped"

    assert orch["audit"]["skipped"] is True
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["gate_step"] is None
    assert orch["audit"]["persist_step"] is None

    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    assert delta["changed_files"] == 0
    assert delta["changed_paths_sample"] == []

    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["product_defect"] is False
    assert diag["adjudication"]["verdict_written"] is False
    assert diag["adjudication"]["audit"]["gate_file_present"] is False


def test_lane_cycle_logs_show_the_request_parameter_rejection():
    ev = _load(LOG_EVIDENCE)
    entry = ev["runs"][RESUMED_RUN_ID]
    assert entry["classification"] == "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER"
    assert entry["exit_codes"] == [1]
    upstream = entry["upstream_error"]
    assert upstream["signature"] == "unsupported_parameter"
    assert "permissions" in upstream["detail"]
    markers = entry["markers"]
    assert markers["quantum_expired"] is False
    assert markers["model_health_gate"] is False
    assert markers["non_transient_failure"] is True
    assert markers["annotation_echo_contamination"] is False

    assert (LOGS / "MANIFEST.json").is_file()
    team_log = (LOGS / "team.log").read_text(encoding="utf-8")
    assert "unsupported_parameter" in team_log
    assert "Unrecognized request argument supplied: permissions." in team_log
    assert "LEX_WORK_QUANTUM_EXPIRED" not in team_log


def test_public_run_evidence_matches_the_diagnosis():
    raw = _load(RAW)
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    assert raw["logs_endpoint_status"] == 200
    steps = _steps(raw, "team")
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    jobs = {j["name"]: j["conclusion"] for j in raw["jobs"]}
    assert jobs["team"] == "failure"
    assert jobs["audit"] == "skipped"
    assert jobs["integrate"] == "skipped"


def test_predecessor_run_died_the_same_way_so_the_cause_is_systematic():
    raw = _load(PRE_RAW)
    assert raw["run"]["id"] == int(PREDECESSOR_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    steps = _steps(raw, "team")
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    pre_team_log = (PRE_LOGS / "team.log").read_text(encoding="utf-8")
    assert "unsupported_parameter" in pre_team_log
    assert "Unrecognized request argument supplied: permissions." in pre_team_log


def test_audit_profile_hands_the_auditor_the_bounded_dossier():
    from product import audit_readiness as ar

    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert prof["mechanism_kind"] == "observed_log"
    assert prof["lane_cycle_classification"] == (
        "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER")
    assert prof["upstream_signature"] == "unsupported_parameter"
    assert prof["failed_job"] == "team"
    assert prof["exit_code"] == 1
    assert prof["delta_kind"] == "zero"
    assert prof["changed_files"] == 0
    assert prof["cycle_test"] == "product/tests/test_cycle_43572985556.py"
    assert prof["state_block"] == f"cycle_{EXECUTING_RUN_ID}_operational_resume"
    assert Path(prof["raw"]).is_file()
    assert Path(prof["resume_diag"]).is_file()
    assert Path(prof["lane_cycle_log_evidence"]).is_file()

    # The shipped server stage guard must be exercised by the core set; it is
    # this lane's real product fix and used to be invisible to the dossier.
    assert "product/tests/test_query_app_stage_guard.py" in ar.MVP_CORE_TESTS


def test_content_family_is_still_the_frozen_fixed_path_family():
    cf = _load(FAMILY)
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_decisions"] == 4900
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["still_verified"]
    assert cf["ordered_work_2_success_rule"]["met"] is True
    assert cf["ordered_work_2_full_success_rule"]["met"] is True
    hist = cf["all_committed"]["totals"]["defect_histogram"]
    # Historical bundles keep their known defects as evidence.
    assert hist["D2_letterhead_zone"] == 44
    assert hist["D3_markup_residue"] == 31
    assert hist["D4_language_marker_mismatch"] == 7


def test_offline_slice_and_progressive_api_still_answer():
    summary = _load(SLICE / "summary.json")
    assert summary["verified"] is True
    assert summary["page_contract"] is True
    assert summary["degraded"] is False
    assert summary["mode"] == "full_loop"
    stats = summary["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["counter_rows"] == 4
    assert stats["counter_status_bearing_rows"] == 8
    assert stats["answer_status"] == "ready"
    assert stats["cited_decision_ids"] == 4
    assert stats["rows_with_source_link"] == 100
    assert stats["rows_with_xy"] == 100
    assert stats["enriched"] is True
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["fixture_replay_cache_misses"] == 0
    assert stats["content_coverage"]["n_pointer_only"] == 0

    smoke = _load(SMOKE)
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23


def test_state_records_the_resume_and_stays_fail_closed():
    state = _load(STATE)
    assert str(state["current_cycle_run_id"]) == EXECUTING_RUN_ID
    assert state["accepted_run_id"] == ACCEPTED_RUN_ID
    assert state["accepted_commit"] == ACCEPTED_COMMIT
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["ready_for_owner_session"] is False

    block = state[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert str(block["run_id"]) == EXECUTING_RUN_ID
    assert block["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert block["resumed_snapshot"]["team_head"] == SNAPSHOT_HEAD
    assert block["resumed_snapshot"]["predecessor_run_id"] == int(
        PREDECESSOR_RUN_ID)
    assert block["resumed_snapshot"]["predecessor_head"] == PREDECESSOR_HEAD
    assert block["resumed_snapshot"]["delta_vs_predecessor_team"].startswith(
        "ZERO_DURABLE_DELTA")
    diagnosis = block["orchestration_failure_diagnosis"]
    assert diagnosis["classification"] == (
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE")
    assert diagnosis["mechanism"] == (
        "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER")
    assert diagnosis["exit_code"] == 1
    assert diagnosis["gate_file_written"] is False
    assert diagnosis["product_defect"] is False
    assert block["accepted_pointer"]["accepted_run_id"] == ACCEPTED_RUN_ID
    assert block["accepted_pointer"]["accepted_commit"] == ACCEPTED_COMMIT
    for name, rel in block["artifacts"].items():
        if name in ("audit_readiness", "report") and not (ROOT / rel).exists():
            continue
        path = ROOT / rel
        if rel.endswith("/") or name in ("job_logs", "slice"):
            assert path.is_dir(), name
        else:
            assert path.is_file(), name


def test_unaccepted_delta_manifest_is_committed_and_honest():
    man = _load(ROOT / "results" / "product" / "audit_readiness"
                / f"CYCLE_{EXECUTING_RUN_ID}_unaccepted_delta.json")
    assert man["base_commit"].startswith(ACCEPTED_COMMIT[:8])
    assert man["head_commit"] == SNAPSHOT_HEAD
    assert man["changed_files"] == 314
    assert man["by_status"] == {"A": 167, "M": 147}
    assert man["by_top_level"] == {
        "product": 20, "reports": 7, "results": 286, "state": 1,
    }
    assert man["deleted_paths"] == []
    code = {r["path"]: r["status"] for r in man["product_code_paths"]}
    assert code["product/query_app.py"] == "M"
    assert code["product/fetch_run_jobs_snapshot.py"] == "A"
    assert "product/tests/" not in "".join(code)
    assert "INVENTORY ONLY" in man["claim_ceiling"]

    state = _load(STATE)
    block = state[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["artifacts"]["unaccepted_delta_manifest"] == (
        f"results/product/audit_readiness/"
        f"CYCLE_{EXECUTING_RUN_ID}_unaccepted_delta.json")
    cumulative = block["cumulative_unaccepted_delta"]
    assert cumulative["manifest_head"] == SNAPSHOT_HEAD
    assert cumulative["cycle_delta"]["changed_files"] == 22
    assert cumulative["cycle_delta"]["by_status"] == {"A": 20, "M": 2}
    assert cumulative["accepted_to_current"]["changed_files"] == 334
    assert cumulative["accepted_to_current"]["by_status"] == {
        "A": 187, "M": 147,
    }
    assert cumulative["accepted_to_current"]["by_top_level"] == {
        "product": 23, "reports": 8, "results": 302, "state": 1,
    }


def test_no_gate_was_minted_and_accepted_pointer_is_intact():
    assert not OWN_GATE.exists()
    assert GATE.is_file()
    gate = _load(GATE)
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []


def test_report_exists_and_names_the_audit_entry_point():
    text = REPORT.read_text(encoding="utf-8")
    assert f"--run-id {EXECUTING_RUN_ID}" in text
    assert f"CYCLE_{EXECUTING_RUN_ID}_audit_readiness.json" in text
    assert "UNADJUDICATED" in text
