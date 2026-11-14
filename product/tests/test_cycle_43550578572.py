"""Cycle 43550578572: resume after write-scope failure + state truncation.

Run 43550578572's lane-cycle agent finished inside the work quantum (541 s)
and state validation passed, but ``Enforce lane write scope`` rejected 15
pending paths under ``results/frontier/frontier-query-retrieval/fixtures/cache/**``
because the agent ran ``fixture_config(mode='live')`` /
``run_query_initial(..., retrieval_mode='live')`` against the frontier fixture
cache. The always-run persist step then committed those paths and truncated
``state/product.json`` (accepted pointer nulled, history/posture lost).

This cycle restores the full predecessor state, records the write-scope and
state-truncation diagnosis, and re-verifies the v68 lane deliverable
REPORTED-ONLY. Assertions are fact-level against committed artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EXECUTING_RUN_ID = "43550578572"
RESUMED_RUN_ID = "43550578572"  # this cycle diagnoses the failed run itself
PREDECESSOR_RUN_ID = "43545195662"
SNAPSHOT_HEAD = "07ba7143854f482fefad4a8bce5cb288ce802ec6"
PREDECESSOR_HEAD = "5a9fa02c23b29a17bc33eb9c49cee2da6d7b7438"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
LOGS = ORCH / f"CYCLE_{RESUMED_RUN_ID}_job_logs"
AUDIT_STEP = ORCH / f"CYCLE_{RESUMED_RUN_ID}_audit_step_diagnosis.json"
RESUME_DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
LOG_EVIDENCE = ORCH / f"CYCLE_{RESUMED_RUN_ID}_lane_cycle_log_evidence.json"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
SLICE = (ROOT / "results" / "product" / "offline_slice"
         / f"{EXECUTING_RUN_ID}_verify")
BUNDLE = SLICE / "rent-default.bundle.json"
SUMMARY = SLICE / "summary.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
STATE = ROOT / "state" / "product.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_43550578572_died_at_write_scope_not_at_the_lane_cycle_step():
    raw = _load(RAW)
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "failure"
    assert jobs["audit"]["conclusion"] == "skipped"
    assert jobs["integrate"]["conclusion"] == "skipped"
    steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
    assert steps["Run lane cycle"] == "success"
    assert steps["Validate active MVP producer state"] == "success"
    assert steps["Enforce lane write scope"] == "failure"
    assert steps["Persist team snapshot"] == "success"

    a = _load(AUDIT_STEP)
    assert a["classification"] == "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert a["failed_step"] == "Enforce lane write scope"
    assert a["failed_job"] == "team"
    assert a["mechanism"]["status"] == "OBSERVED_SCOPE_ENFORCEMENT_FAILED"
    assert a["mechanism"]["lane_cycle_step_conclusion"] == "success"
    assert a["mechanism"]["scope_step_conclusion"] == "failure"
    assert a["mechanism"]["quantum_expired"] is False
    assert a["mechanism"]["exit_code"] == 3
    assert a["audit"]["skipped"] is True
    assert a["audit"]["gate_file_written"] is False
    assert a["team"]["team_snapshot_persisted"] is True

    diag = _load(RESUME_DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert orch["failed_step"] == "Enforce lane write scope"
    assert orch["mechanism"]["status"] == "OBSERVED_SCOPE_ENFORCEMENT_FAILED"
    assert orch["mechanism"]["lane_cycle_step_seconds"] == 541.0
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 37
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == PREDECESSOR_HEAD
    sample = delta["changed_paths_sample"]
    assert any(p.startswith("results/frontier/frontier-query-retrieval/fixtures/cache/")
               for p in sample)
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False

    log = _load(LOG_EVIDENCE)
    entry = log["runs"][RESUMED_RUN_ID]
    assert entry["classification"] == "WRITE_SCOPE_ENFORCEMENT_FAILED"
    assert entry["markers"]["write_scope_enforcement"] is True
    assert entry["markers"]["quantum_expired"] is False
    assert entry["exit_codes"] == [3]
    assert "lane crossed protected scope" in "\n".join(
        entry["markers"]["annotation_error_lines"])


def test_out_of_scope_frontier_fixture_paths_are_the_scope_violation():
    raw = _load(RAW)
    # the workflow error annotation lists the rejected paths
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    # path list is in the commit delta, not only annotations
    diag = _load(RESUME_DIAG)
    paths = diag["durable_delta"]["changed_paths_sample"]
    frontier = [p for p in paths if p.startswith("results/frontier/")]
    assert len(frontier) >= 10, frontier
    # product-owned query_cache refreshes are in-scope and preserved
    full_sample_note = diag["durable_delta"]["meaning"]
    assert "committed delta" in full_sample_note
    # no auditor-namespace mint
    assert not any(p.startswith("results/audit/") or p.startswith("reports/audit/")
                   for p in paths)


def test_state_is_restored_fail_closed_with_accepted_pointer():
    state = _load(STATE)
    assert state["accepted_run_id"] == ACCEPTED_RUN_ID
    assert state["accepted_commit"] == ACCEPTED_HEAD
    assert state["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert state[flag] is False, flag
    # registers the failed run truncated must be back
    assert isinstance(state.get("run_history"), list) and state["run_history"]
    assert any(e.get("run_id") == int(EXECUTING_RUN_ID)
               for e in state["run_history"])
    assert "v68_delivery" in state
    assert "vertical_slice_verification" in state
    block = state["cycle_43550578572_operational_resume"]
    assert block["status"] == "AUDIT_READY_PENDING_INDEPENDENT_AUDIT"
    assert block["gate_minted"] is False
    assert block["auditor_namespace_written"] is False
    assert block["orchestration_failure_diagnosis"]["classification"] == (
        "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE")
    assert block["orchestration_failure_diagnosis"]["state_truncation"][
        "observed"] is True
    # both halves of requirement 4 still name the accepted head
    gate = _load(ROOT / "results" / "audit" / "product"
                 / f"{ACCEPTED_RUN_ID}_GATE.json")
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True


def test_lane_deliverable_reverified_reported_only():
    cf = _load(FAMILY)
    fp = cf["fixed_path_family"]["totals"]
    assert fp["n_bundles"] == 49
    assert fp["n_decisions"] == 4900
    assert fp["n_verified"] == 55
    assert fp["n_verified_defective"] == 0
    assert all(v == 0 for v in fp["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    assert cf["ordered_work_2_full_success_rule"]["met"] is True

    summary = _load(SUMMARY)
    assert summary["verified"] is True
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    assert summary["mode"] == "full_loop"
    assert summary["degraded"] is False
    stats = summary["stats"]
    assert stats["answer_status"] == "ready"
    assert len(stats["cited_decision_ids"]) >= 1
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["content_coverage"]["n_decisions"] == 100

    bundle = _load(BUNDLE)
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert sum(1 for r in rows if r.get("x") is not None and r.get("y") is not None) == 100
    assert sum(1 for r in rows if r.get("cluster_id") is not None) == 100
    assert sum(1 for r in rows if r.get("canonical_url")) == 100
    assert len(bundle.get("clusters") or []) >= 5
    answer = bundle.get("answer") or {}
    assert answer.get("status") in ("ready", "delivered")
    cited = set(answer.get("cited_decision_ids") or [])
    assert cited
    ids = {r.get("decision_id") or r.get("id") for r in rows}
    assert cited <= ids, "every cited decision must be on the map"


def test_report_and_profile_exist_and_posture_stays_fail_closed():
    assert REPORT.is_file(), "cycle report must be committed"
    text = REPORT.read_text(encoding="utf-8")
    assert EXECUTING_RUN_ID in text
    assert "UNADJUDICATED" in text
    assert "write scope" in text.lower() or "write-scope" in text.lower()
    assert "human_gate" in text or "human-gate" in text

    # profile registered for this run
    from product import audit_readiness as ar
    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["mechanism_kind"] == "observed_scope"
    assert prof["classification"] == (
        "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE")
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["exit_code"] == 3
    assert prof["changed_files"] == 37

    state = _load(STATE)
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
