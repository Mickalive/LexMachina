"""Cycle 43538547811: resume run 43531125031 after an audit quantum expiry.

Run 43531125031 did real work: it resumed the zero-delta model-health-gated
snapshot 43530889474, restored the historical ``CYCLE_43373102286.json`` bytes
that an earlier run had rewritten in place, re-homed that later measurement,
repaired two instruments and re-verified the v68 lane deliverable.  Its team
job succeeded in 17 m; its audit job then consumed the workflow's full
2700 s agent quantum (exit 78) after two read-only tool calls and wrote no
gate.  The snapshot therefore carries a committed delta and is UNADJUDICATED.

This cycle preserves that work, diagnoses the audit quantum expiry from the
run's own committed job log and annotations, and re-verifies the lane
deliverable on the snapshot bytes.  The assertions are fact-level: every
number below is read back from a committed artifact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EXECUTING_RUN_ID = "43538547811"
RESUMED_RUN_ID = "43531125031"
PREDECESSOR_RUN_ID = "43530889474"
SNAPSHOT_HEAD = "183e9d79372be6fff794149c2ff4178477990df7"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

ORCH = ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
LOGS = ORCH / f"CYCLE_{RESUMED_RUN_ID}_job_logs"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
HISTORICAL_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                     / "CYCLE_43531125031.json")
HISTORICAL_FAMILY_SHA256 = (
    "14eed134ad98872900863d3cb553d70bb9088774130e38941dce6bd7a0b8a5ae"
)
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
SLICE = (ROOT / "results" / "product" / "offline_slice"
         / f"{EXECUTING_RUN_ID}_verify")
BUNDLE = SLICE / "rent-default.bundle.json"
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
STATE = ROOT / "state" / "product.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_43531125031_stopped_at_the_audit_quantum_not_in_the_team_job():
    raw = _load(RAW)
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    audit_steps = {s["name"]: s["conclusion"]
                   for s in jobs["audit"]["steps"]}
    assert audit_steps["Independent audit"] == "failure"
    assert audit_steps["Enforce audit scope and read gate"] == "skipped"
    assert audit_steps["Persist audit snapshot"] == "skipped"

    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    orch = diag["orchestration"]
    assert orch["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert orch["team"]["conclusion"] == "success"
    assert orch["team"]["producer_state_validation_step_conclusion"] == "success"
    assert orch["team"]["write_scope_step_conclusion"] == "success"
    assert orch["audit"]["conclusion"] == "failure"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2705.0
    assert orch["audit"]["gate_file_written"] is False
    assert orch["audit"]["gate_step"] == "skipped"
    assert orch["audit"]["persist_step"] == "skipped"
    assert orch["integrate"]["conclusion"] == "skipped"

    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    observed = orch["observed_failure"]
    assert observed["job"] == "audit"
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700" in observed[
        "quantum_message"]

    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == ACCEPTED_HEAD
    assert delta["changed_files"] == 209
    assert "product/audit_readiness.py" in delta["changed_paths_sample"]

    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["audit"]["audit_ref_present"] is False
    assert adj["audit"]["gate_file_present"] is False
    assert adj["product_defect"] is False


def test_audit_log_shows_the_model_and_the_quantum_and_no_gate():
    log = (LOGS / "audit.log").read_text(encoding="utf-8", errors="replace")
    assert "selected=opencode/glm-5.3-flash-free" in log
    assert "LEX_OX_ATTEMPT=1/8 quantum=2700s" in log
    assert "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2587" in log
    assert "Process completed with exit code 78." in log
    # The auditor made two read-only calls, then no gate was written.
    assert "ls /tmp/lex_team; echo ---; ls" in log
    assert "git log --oneline -5; git status --short | head -20" in log
    assert "results/audit/product/CYCLE_43531125031_GATE.json" not in log

    manifest = _load(LOGS / "MANIFEST.json")
    captured = {row["job_name"]: row for row in manifest["logs"]}
    assert captured["audit"]["http_status"] == 200
    assert captured["audit"]["file"] == "audit.log"
    for row in manifest["logs"]:
        if row.get("file"):
            path = LOGS / row["file"]
            assert path.is_file()
            assert row["bytes"] == path.stat().st_size


def test_resumed_work_is_preserved_and_the_new_measurement_is_its_own_artifact():
    raw = HISTORICAL_FAMILY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == HISTORICAL_FAMILY_SHA256
    old = json.loads(raw)
    assert old["run_id"] == RESUMED_RUN_ID
    assert old["fixed_path_family"]["totals"]["n_bundles"] == 49

    new = _load(FAMILY)
    assert new["run_id"] == EXECUTING_RUN_ID
    fp = new["fixed_path_family"]["totals"]
    assert fp["n_bundles"] == 49
    assert fp["n_decisions"] == 4900
    assert fp["n_verified"] == 55
    assert fp["n_verified_defective"] == 0
    assert fp["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert new["false_reject_count"] == 0
    assert new["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert new["confirmed_set"]["still_verified"] is True
    assert new["ordered_work_2_success_rule"]["met"] is True
    assert new["ordered_work_2_full_success_rule"]["met"] is True
    assert new["all_committed"]["totals"]["n_bundles"] == 151
    assert new["all_committed"]["totals"]["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 44,
        "D3_markup_residue": 31,
        "D4_language_marker_mismatch": 7,
    }


def test_end_to_end_slice_and_page_contract_on_current_bytes():
    summary = _load(SLICE / "summary.json")
    assert summary["bundle"] == str(BUNDLE.relative_to(ROOT))
    assert summary["mode"] == "full_loop"
    assert summary["degraded"] is False
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    stats = summary["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["rows_with_source_link"] == 100
    assert stats["rows_with_canonical_url"] == 100
    assert stats["rows_with_source_url"] == 100
    assert stats["rows_with_xy"] == 100
    assert stats["rows_with_cluster_id"] == 100
    assert stats["answer_status"] == "ready"
    assert stats["cited_decision_ids"] == 4
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["fixture_replay"]["network"] == "none"

    bundle = _load(BUNDLE)
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert len(bundle.get("clusters") or []) == 8
    assert all(r.get("x") is not None and r.get("y") is not None for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    answer = bundle.get("answer") or {}
    assert answer.get("status") == "ready"
    assert len(answer.get("cited_decision_ids") or []) == 4
    offline = bundle["provenance"]["offline_slice"]
    assert offline["network"] == "none"
    assert offline["geometry_preserved"] is True

    from offline_slice import verify_page

    ok, detail = verify_page(BUNDLE)
    assert ok, detail


def test_audit_readiness_profile_state_posture_and_no_gate():
    from product import audit_readiness as ar

    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["predecessor_run_id"] == PREDECESSOR_RUN_ID
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert prof["failed_job"] == "audit"
    assert prof["quantum_seconds"] == 2700
    assert prof["exit_code"] == 78
    assert prof["changed_files"] == 209
    assert prof["cycle_test"] == (
        f"product/tests/test_cycle_{EXECUTING_RUN_ID}.py")
    for field in ("raw", "resume_diag", "content_family", "current_report"):
        assert Path(prof[field]).is_file(), field

    st = _load(STATE)
    assert st["current_cycle_run_id"] == int(EXECUTING_RUN_ID)
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_HEAD
    block = st[f"cycle_{EXECUTING_RUN_ID}_operational_resume"]
    assert block["run_id"] == EXECUTING_RUN_ID
    assert block["resumed_snapshot"]["run_id"] == RESUMED_RUN_ID
    assert block["resumed_snapshot"]["team_head"] == SNAPSHOT_HEAD
    assert block["orchestration_failure_diagnosis"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    assert block["orchestration_failure_diagnosis"][
        "gate_file_written"] is False
    assert block["gate_minted"] is False
    assert block["auditor_namespace_written"] is False
    assert block["posture"]["owner_decision_required"] is False
    assert block["status"] == "AUDIT_READY_PENDING_INDEPENDENT_AUDIT"
    assert REPORT.is_file()

    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists()
