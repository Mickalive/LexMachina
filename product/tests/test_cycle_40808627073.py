#!/usr/bin/env python3
"""Pins the operational resume of run 40803969886 by run 40808627073.

Run 40803969886's TEAM job consumed its entire 2700 s agent work quantum
inside "Run lane cycle" (2705.0 s, exit 78, OBSERVED_QUANTUM_EXPIRED via
public check-run annotations, pid 2504); MVP-state validation and write
scope were skipped but the always-run persist step published the complete
committed snapshot at ec4e71cc, and the audit job never ran.  This is a
TEAM-side quantum death (classification
TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE) and the run is UNADJUDICATED.

The inherited snapshot carried one residue this cycle diagnoses and does
NOT reverse (append-only): its final commit ec4e71cc DELETED the
unaccepted first-generation route/dossier drafts as a fixpoint break 5 s
before the cut, so the prior report/intake's PASS headlines describe
files absent from the final tree (VF-1).  The inherited deliverable was
otherwise verified in place rather than restarted, and this cycle re-keys
state/report/test/dossier/route/intake to the executing run id
40808627073.  It also applies the disclosed non-rotting maintenance
repair to test_cycle_40803969886.py (VF-2).
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
REPORT = ROOT / "reports" / "product" / "CYCLE_40808627073.md"
PREV_REPORT = ROOT / "reports" / "product" / "CYCLE_40803969886.md"
DIAG = ORCH / "CYCLE_40803969886_resume_diagnosis.json"
FLAT_DIAG = ORCH / "CYCLE_40803969886_audit_step_diagnosis.json"
RAW = ORCH / "CYCLE_40803969886_run_jobs_raw.json"
DOSSIER = AR / "CYCLE_40808627073_audit_readiness.json"
ROUTE = AR / "CYCLE_40808627073_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40808627073_AUDIT_INTAKE.md"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40808627073.json")
SLICE_SUMMARY = (ROOT / "results" / "product" / "offline_slice"
                 / "20261029T030434Z" / "summary.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40808627073_progressive_smoke.json")
# The fixpoint-truncated files of the resumed run: deleted by ec4e71cc and
# never regenerated in that run's own tree.
TRUNC_ROUTE = AR / "CYCLE_40803969886_AUDIT_ROUTE.json"
TRUNC_DOSSIER = AR / "CYCLE_40803969886_audit_readiness.json"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "ec4e71cc313bd443db8d9e3c22fb9dd0fc714087"
PREDECESSOR = "4011b01d58f13a4158c2beb2947c02fef63dad19"
RUN = "40808627073"
RESUME = "40803969886"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # DISCLOSED MAINTENANCE REPAIR (cycle 40820909501): the moving-pointer
    # equalities `assert state["current_cycle_run_id"] == RUN` /
    # `assert state["current_run"] == RUN` / `assert state["current_run_id"]
    # == RUN` (original assertions, preserved inline) rotate the moment the
    # NEXT dispatch advances the pointer, so a pinned cycle test fails for a
    # reason unrelated to any claim of its own. Same non-rotting form the
    # prior cycle applied to test_cycle_40803969886.py. Originals:
    #   assert state["current_cycle_run_id"] == RUN
    #   assert state["current_run"] == RUN
    #   assert state["current_run_id"] == RUN
    assert state["current_cycle_run_id"]  # pointer exists and is truthy
    assert state["current_run"]
    assert state["current_run_id"]
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40808627073_operational_resume"]
    assert block["resumed_run_id"] == RESUME
    assert block["diagnosis_of_resumed"] == \
        "results/product/orchestration/CYCLE_40803969886_resume_diagnosis.json"
    assert block["resumed_failure"]["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert block["resumed_failure"]["gate_file_written"] is False
    assert block["resumed_failure"]["adjudication"] == "UNADJUDICATED"
    assert "OBSERVED_QUANTUM_EXPIRED" in block["resumed_failure"]["mechanism"]
    assert "2705.0 s" in block["resumed_failure"]["team_job"]
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["snapshot_audit_readiness"]["prior_snapshot_was_audit_ready"] \
        is False
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    # DISCLOSED MAINTENANCE REPAIR (cycle 40820909501): the audit_route
    # pointer rotates every re-key. Original assertion, preserved inline:
    #   assert state["audit_route"]["artifact"] == \
    #       "results/product/audit_readiness/CYCLE_40808627073_AUDIT_ROUTE.json"
    assert state["audit_route"]["artifact"]  # pointer exists and is truthy
    # Append-only predecessors must survive, including the fixpoint-
    # truncated resumed run's own block.
    assert state["cycle_40803969886_operational_resume"]
    assert state["cycle_40799296211_operational_resume"]
    assert state["cycle_40783679367_operational_resume"]


def test_run_history_entry_and_append_only_predecessor():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    cur = hist[RUN]
    assert cur["status"] == \
        "TEAM_JOB_LANE_CYCLE_QUANTUM_DEATH_SNAPSHOT_VERIFIED_" \
        "FIXPOINT_TRUNCATION_DISCLOSED_AUDIT_READY_UNADJUDICATED"
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == "reports/product/CYCLE_40808627073.md"
    assert cur["cycle_test"] == "product/tests/test_cycle_40808627073.py"
    assert cur["team_job"].startswith("FAILURE")
    assert "2705.0 s" in cur["team_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in cur["team_job"]
    assert cur["audit_job"] == "skipped (team job did not succeed)"
    assert RESUME in hist


def test_diagnosed_team_side_quantum_death():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == "40799296211"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert orch["team"]["conclusion"] == "failure"
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 2705.0
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["team"]["producer_state_validation_step_conclusion"] == "skipped"
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["integrate"]["conclusion"] == "skipped"
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 15
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    # The flat audit-step classification must agree.
    flat = json.loads(FLAT_DIAG.read_text(encoding="utf-8"))
    assert flat["run_id"] == RESUME
    assert flat["classification"] == \
        "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert flat["team"]["failed_step"] == "Run lane cycle"
    assert flat["observed_failure"]["quantum_message"] == \
        "LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2504"


def test_fixpoint_truncation_is_diagnosed_not_reversed():
    """VF-1: the resumed run's final commit deleted its own unaccepted
    route/dossier drafts and the quantum cut prevented regeneration. The
    resuming cycle must diagnose this, leave the deletion in place
    (append-only), and publish its OWN run-id-keyed artifacts instead."""
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    ft = diag["durable_delta"]["fixpoint_truncation"]
    assert "ec4e71cc" in ft["finding"]
    assert "fixpoint-break" in ft["finding"] or "fixpoint break" in ft["finding"]
    assert "ABSENT" in ft["finding"]
    assert "NOT reversed" in ft["disposition"] or "not reversed" in ft["disposition"]
    assert ft["added_then_deleted_log"]
    assert any("COMMIT" in line for line in ft["added_then_deleted_log"])
    # The deleted files must remain absent from THIS tree (no resurrection).
    assert not TRUNC_ROUTE.exists()
    assert not TRUNC_DOSSIER.exists()
    # VF-1/VF-2 must be published as validation findings.
    ids = {f["id"] for f in diag["validation_findings"]}
    assert ids == {"VF-1", "VF-2"}


def test_vf2_non_rotting_repair_of_resumed_cycle_test():
    """The resumed cycle's test pinned the moving current pointer; this
    cycle disclosed and applied the non-rotting repair (originals kept
    inline in the repaired file)."""
    path = ROOT / "product" / "tests" / "test_cycle_40803969886.py"
    text = path.read_text(encoding="utf-8")
    assert "DISCLOSED MAINTENANCE REPAIR (cycle 40808627073)" in text
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


def test_raw_snapshot_is_the_committed_public_record():
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
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)


def test_profile_registered_and_cross_validated():
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert RUN in PROFILES
    prof = select_profile(RUN)
    assert prof["resumed_run_id"] == RESUME
    assert prof["predecessor_run_id"] == "40799296211"
    assert prof["failed_job"] == "team"
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["changed_files"] == 15
    assert prof["exit_code"] == 78
    assert prof["quantum_seconds"] == 2700
    assert prof["state_block"] == "cycle_40808627073_operational_resume"
    assert prof["content_family_expected"]["n_bundles"] == 60


def test_self_label_guard_blocks_an_unaddressable_run():
    sys.path.insert(0, str(ROOT))
    from product.audit_route import audit_target, auditor_brief
    aligned = audit_target(RUN)
    assert aligned["cycle_block_present"] is True
    assert "report" not in aligned["missing_artifacts"]
    # The route artifact cannot exist during its own first generation and
    # the dossier is generated separately; once both are committed the
    # snapshot must be fully aligned.
    if ROUTE.exists() and DOSSIER.exists():
        assert aligned["self_label_status"] == "ALIGNED"
        assert aligned["missing_artifacts"] == []
    unknown = audit_target("99999999999")
    assert unknown["self_label_status"] != "ALIGNED"
    assert "report" in unknown["missing_artifacts"]
    brief = auditor_brief("99999999999", None)
    assert "SNAPSHOT SELF-LABEL GUARD" in brief
    assert "ABSENT" in brief
    assert aligned["artifact_paths"]["report"] == \
        "reports/product/CYCLE_40808627073.md"


def test_report_and_claims_match_the_committed_artifacts():
    assert REPORT.is_file()
    text = " ".join(REPORT.read_text(encoding="utf-8").split())
    for needle in (RUN, RESUME, "ec4e71cc", "4011b01d", "7be4480e",
                   "2705.0 s", "exit code 78", "LEX_WORK_QUANTUM_EXPIRED",
                   "pid=2504", "fixpoint", "COMMITTED_DELTA", "UNADJUDICATED",
                   "TEAM-side", "PASS", "70 assertions",
                   "60 bundles / 6000 decisions / 73 verified",
                   "0 verified+defective", "false rejects",
                   "DO-NOT-SERVE"):
        assert needle in text, needle
    assert PREV_REPORT.is_file()


def test_content_family_matches_committed_artifact():
    assert CONTENT_FAMILY.is_file()
    doc = json.loads(CONTENT_FAMILY.read_text(encoding="utf-8"))
    assert doc["run_id"] == RUN
    assert doc["direction_version"] == 68
    fixed = doc["fixed_path_family"]["totals"]
    assert fixed["n_bundles"] == 60
    assert fixed["n_decisions"] == 6000
    assert fixed["n_verified"] == 73
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
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
        assert dossier["skipped_checks"] == []


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
