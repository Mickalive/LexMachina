#!/usr/bin/env python3
"""Pins the operational resume of run 40820694435 by run 40820909501.

Run 40820694435's TEAM job failed in "Run lane cycle" after 16.0 s with exit
code 1.  The public annotation says only `Process completed with exit code 1.`
(logs are HTTP 403), so the mechanism is UNOBSERVED; the always-run persist
step published the unchanged tree at bed9a218 (ZERO_DURABLE_DELTA, 0 files).
The predecessor 40814271020 had a green team job whose entire 22-file delta was
query-cache content (CACHE_REFRESH, product_work=false), then its audit job
consumed the 2700 s work quantum (2705.0 s, exit 78, public annotation
`LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2505`) without writing a gate.

The inherited v68 deliverable is 40808627073's and is re-verified in place,
not restarted.  This cycle re-keys state/report/test/dossier/route/intake to
40820909501, preserves both failure diagnoses, and discloses the non-rotting
pointer repair of test_cycle_40808627073.py (VF-3).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40820909501.md"
DIAG = ORCH / "CYCLE_40820694435_resume_diagnosis.json"
FLAT_DIAG = ORCH / "CYCLE_40820694435_audit_step_diagnosis.json"
RAW = ORCH / "CYCLE_40820694435_run_jobs_raw.json"
PRED_DIAG = ORCH / "CYCLE_40814271020_resume_diagnosis.json"
PRED_FLAT = ORCH / "CYCLE_40814271020_audit_step_diagnosis.json"
PRED_RAW = ORCH / "CYCLE_40814271020_run_jobs_raw.json"
PRED_DELTA = ORCH / "CYCLE_40814271020_delta_substance.json"
DOSSIER = AR / "CYCLE_40820909501_audit_readiness.json"
ROUTE = AR / "CYCLE_40820909501_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40820909501_AUDIT_INTAKE.md"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40820909501.json")
SLICE_SUMMARY = (ROOT / "results" / "product" / "offline_slice"
                 / "20261029T050600Z" / "summary.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40820909501_progressive_smoke.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "bed9a21827b1f2d9ffb14d98cc5d19fe382590cb"
PREDECESSOR = "65b6e82b3f653294b6d4222fcb8f7a14224eee93"
RUN = "40820909501"
RESUME = "40820694435"
PRED_RUN = "40814271020"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # The pointer rotates by design; this cycle's own block carries the pin.
    assert state["current_cycle_run_id"]
    assert state["current_run"]
    assert state["current_run_id"]
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40820909501_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40820694435_resume_diagnosis.json"
    rf = block["resumed_failure"]
    assert rf["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "16.0 s" in rf["team_job"]
    assert "UNOBSERVED" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "ZERO_DURABLE_DELTA" in rf["durable_delta"]
    pf = block["predecessor_failure"]
    assert pf["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert "OBSERVED_QUANTUM_EXPIRED" in pf["mechanism"]
    assert "2705.0 s" in pf["audit_job"]
    assert "CACHE_REFRESH" in pf["durable_delta"]
    assert pf["adjudication"] == "UNADJUDICATED"
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["snapshot_audit_readiness"]["prior_snapshot_was_audit_ready"] \
        is False
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert state["audit_route"]["artifact"] == \
        "results/product/audit_readiness/CYCLE_40820909501_AUDIT_ROUTE.json"
    # Append-only predecessors must survive.
    assert state["cycle_40808627073_operational_resume"]
    assert state["cycle_40803969886_operational_resume"]
    assert state["cycle_40799296211_operational_resume"]


def test_run_history_entry_and_append_only_predecessor():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    cur = hist[RUN]
    assert cur["status"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE_ZERO_DELTA_SNAPSHOT_" \
        "REVERIFIED_AUDIT_READY_UNADJUDICATED"
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == \
        "reports/product/CYCLE_40820909501.md"
    assert cur["cycle_test"] == \
        "product/tests/test_cycle_40820909501.py"
    assert cur["team_job"].startswith("FAILURE")
    assert "16.0 s" in cur["team_job"]
    assert "UNOBSERVED" in cur["team_job"]
    assert cur["audit_job"] == "skipped (team job did not succeed)"
    # 40820694435 produced zero durable delta and 40814271020 produced only a
    # cache refresh, so neither published a run-history entry; the chain
    # evidence lives in the orchestration artifacts and this cycle's block.
    assert RUN in hist
    assert "40808627073" in hist
    assert hist["40808627073"]["accepted"] is False


def test_diagnosed_team_side_failure_is_unobserved_not_zero_delta_guard():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "UNOBSERVED"
    assert mech["logs_available"] is False
    assert mech["logs_endpoint_status"] == 403
    assert mech["quantum_expired"] is False
    assert mech["quantum_seconds"] is None
    assert mech["exit_code"] == 1
    team = orch["team"]
    assert team["conclusion"] == "failure"
    assert team["failed_step"] == "Run lane cycle"
    assert team["failed_step_seconds"] == 16.0
    assert team["team_snapshot_persisted"] is True
    assert team["team_snapshot_persisted_after_failed_team_job"] is True
    assert team["producer_state_validation_step_conclusion"] == "skipped"
    assert team["write_scope_step_conclusion"] == "skipped"
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == SNAPSHOT
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    ids = {f["id"] for f in diag["chain_findings"]}
    assert ids == {"CF-1", "CF-2"}
    ctx = diag["predecessor_context"]
    assert ctx["run_id"] == PRED_RUN
    assert ctx["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert ctx["durable_delta"]["classification"] == "CACHE_REFRESH"
    assert ctx["durable_delta"]["product_work"] is False


def test_predecessor_audit_quantum_death_and_cache_refresh_delta():
    diag = json.loads(PRED_DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == PRED_RUN
    assert diag["predecessor_run_id"] == "40808627073"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert orch["team"]["conclusion"] == "success"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2705.0
    assert orch["audit"]["gate_file_written"] is False
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 22
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    ds = diag["delta_substance"]
    assert ds["classification"] == "CACHE_REFRESH"
    assert ds["product_work"] is False
    assert ds["changed_files"] == 22
    assert ds["substantive_files"] == []


def test_raw_snapshots_are_the_committed_public_record():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    assert raw["run"]["id"] == int(RESUME)
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "skipped"
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values()
            for a in v]
    assert any("exit code 1" in m for m in msgs)
    assert not any("LEX_WORK_QUANTUM_EXPIRED" in m for m in msgs)

    pred = json.loads(PRED_RAW.read_text(encoding="utf-8"))
    assert pred["run"]["id"] == int(PRED_RUN)
    pa = next(j for j in pred["jobs"] if j["name"] == "audit")
    assert pa["conclusion"] == "failure"
    pmsgs = [a["message"] for v in (pred.get("annotations") or {}).values()
             for a in v]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2505" in m
               for m in pmsgs)
    assert any("exit code 78" in m for m in pmsgs)


def test_flat_diagnoses_agree():
    flat = json.loads(FLAT_DIAG.read_text(encoding="utf-8"))
    assert flat["run_id"] == RESUME
    assert flat["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert flat["team"]["failed_step"] == "Run lane cycle"
    assert flat["team"]["failed_step_seconds"] == 16.0
    assert flat["observed_failure"]["exit_code"] == 1
    assert flat["observed_failure"]["quantum_message"] is None
    assert flat["integrate"]["conclusion"] == "skipped"

    pflat = json.loads(PRED_FLAT.read_text(encoding="utf-8"))
    assert pflat["run_id"] == PRED_RUN
    assert pflat["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert pflat["observed_failure"]["quantum_message"] == \
        "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2505"
    assert pflat["observed_failure"]["exit_code"] == 78


def test_delta_substance_classifies_cache_refresh():
    ds = json.loads(PRED_DELTA.read_text(encoding="utf-8"))
    assert ds["run_id"] == PRED_RUN
    assert ds["delta_substance"] == "CACHE_REFRESH"
    assert ds["product_work"] is False
    assert ds["changed_files"] == 22
    assert ds["cache_content_count"] == 22
    assert ds["cache_timestamp_only_count"] == 0
    assert ds["substantive_files"] == []


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert RUN in PROFILES
    prof = select_profile(RUN)
    assert prof["resumed_run_id"] == RESUME
    assert prof["predecessor_run_id"] == PRED_RUN
    assert prof["failed_job"] == "team"
    assert prof["mechanism_kind"] == "observed_steps"
    assert prof["delta_kind"] == "zero"
    assert prof["changed_files"] == 0
    assert prof["exit_code"] == 1
    assert prof["quantum_seconds"] is None
    assert prof["state_block"] == "cycle_40820909501_operational_resume"
    assert prof["content_family_expected"] == {
        "n_bundles": 61,
        "n_decisions": 6100,
        "n_verified": 76,
        "n_verified_defective": 0,
        "false_reject_count": 0,
    }
    extras = {str(Path(x)) for x in prof["extra_claim_artifacts"]}
    assert str(PRED_DIAG) in extras
    assert str(PRED_DELTA) in extras


def test_vf3_non_rotting_repair_of_prior_cycle_test():
    """The prior cycle test pinned the moving current pointer; this cycle
    disclosed and applied the same non-rotting repair the prior cycle used."""
    path = ROOT / "product" / "tests" / "test_cycle_40808627073.py"
    text = path.read_text(encoding="utf-8")
    assert "DISCLOSED MAINTENANCE REPAIR (cycle 40820909501)" in text
    # Originals preserved inline, not silently deleted.
    assert 'assert state["current_cycle_run_id"] == RUN' in text
    # Non-rotting form in force: the equality line is commented out.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == 'assert state["current_cycle_run_id"] == RUN':
            raise AssertionError(
                "the rotating equality is live again; keep it preserved "
                "only as an inline comment"
            )


def test_report_and_claims_match_the_committed_artifacts():
    assert REPORT.is_file()
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in (RUN, RESUME, PRED_RUN, SNAPSHOT[:8], PREDECESSOR[:8],
                   ACCEPTED[:8], "16.0 s", "exit code 1", "UNOBSERVED",
                   "2705.0 s", "exit code 78", "LEX_WORK_QUANTUM_EXPIRED",
                   "pid=2505", "CACHE_REFRESH", "ZERO_DURABLE_DELTA",
                   "UNADJUDICATED", "PASS", "70 assertions",
                   "61 bundles / 6100 decisions / 76 verified",
                   "0 verified+defective", "false rejects",
                   "DO-NOT-SERVE", "CF-1", "CF-2"):
        assert needle in text, needle


def test_content_family_matches_committed_artifact():
    assert CONTENT_FAMILY.is_file()
    doc = json.loads(CONTENT_FAMILY.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["direction_version"] == 68
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 61
    assert fixed["n_decisions"] == 6100
    assert fixed["n_verified"] == 76
    assert fixed["n_verified_defective"] == 0
    assert fixed["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert doc["false_reject_count"] == 0
    assert doc["confirmed_set"]["still_verified"] is True
    assert doc["ordered_work_2_success_rule"]["met"] is True
    assert doc["ordered_work_2_full_success_rule"]["met"] is True


def test_fresh_offline_slice_is_the_committed_bytes():
    assert SLICE_SUMMARY.is_file()
    summary = json.loads(SLICE_SUMMARY.read_text(encoding="utf-8"))
    assert summary["verified"] is True
    assert summary["mode"] == "full_loop"
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    stats = summary["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["answer_status"] == "ready"
    assert stats["geometry_preserved_by_enrich"] is True
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["rows_with_source_url"] == 100


def test_progressive_smoke_is_committed_and_passing():
    assert SMOKE.is_file()
    doc = json.loads(SMOKE.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["verdict"] == "PASS"
    assert doc["checks_passed"] == doc["checks_total"] == 23
    assert doc["timings_s"]["server_boot_s"] < 3.0
    assert doc["timings_s"]["start_s"] < 1.0


def test_audit_route_artifact_if_present():
    if ROUTE.exists():
        route = json.loads(ROUTE.read_text(encoding="utf-8"))
        assert route["schema"] == "product-audit-route/1"
        assert route["run_id"] == RUN
        assert route["quantum_budget_s"] == 2700
        assert route["audit_target"]["audit_target_ref"] == \
            f"origin/cycle/core/product/{RUN}/team"
        label = route["snapshot_self_label"]["status"]
        assert label in ("ALIGNED", "ALIGNED_AFTER_WRITE")
        if label == "ALIGNED_AFTER_WRITE":
            assert route["snapshot_self_label"]["missing_artifacts"] == \
                ["route"]
        ids = [s["id"] for s in route["steps"]]
        assert "snapshot_self_label" in ids
        assert "state_contract" in ids
        assert "chain_cycle_tests" in ids
        assert "never a verdict" in route["contract"]
        if route.get("mode") != "bootstrap":
            assert route["overall_status"] == "PASS"
            assert route["failed_steps"] == []
            assert route["total_seconds"] < route["quantum_budget_s"]


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == RUN
        assert dossier["resumed_run_id"] == RESUME
        assert dossier["predecessor_run_id"] == PRED_RUN
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
        assert dossier["skipped_checks"] == []
        check = next(c for c in dossier["checks"]
                     if c["id"] == "claim_artifacts")
        hashes = check["detail"]["sha256"]
        for path in (PRED_DIAG, PRED_DELTA, PRED_FLAT,
                     ORCH / "CYCLE_40814271020_run_jobs_raw.json"):
            assert str(path.relative_to(ROOT)) in hashes


def test_audit_brief_never_mints_a_gate():
    proc = subprocess.run(
        [sys.executable, "product/audit_route.py", "--for-auditor",
         "--run-id", RUN],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert "AUDIT TARGET" in proc.stdout
    assert "PRESENT" in proc.stdout
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN}_GATE.json").exists()
    assert INTAKE.is_file()
