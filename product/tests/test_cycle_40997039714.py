#!/usr/bin/env python3
"""Pins the operational resume of the 40990419541 snapshot by 40997039714.

Run 40990419541's TEAM job was fully green (state validation and write scope
passed; snapshot persisted at e8e6eb94) and its AUDIT 'Independent audit'
step was then stopped by the workflow's own 2700 s work quantum (2704.0 s,
exit 78, LEX_WORK_QUANTUM_EXPIRED pid=2499) before writing a gate; the
gate/persist steps were skipped and the run is UNADJUDICATED.

This cycle preserves that snapshot, proves the failure and the 14-file
durable delta from committed evidence, re-verifies the inherited v68
deliverable (fresh offline slice, content family, progressive smoke, chain
cycle tests), corrects the predecessor report's duplicated 40863791646
chain-table row via a run_history correction (the historical report file is
not rewritten), applies the disclosed rotting-pointer maintenance repair to
test_cycle_40990419541.py, and re-keys state/report/test/profile/dossier/
route/intake to 40997039714.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
AR = ROOT / "results" / "product" / "audit_readiness"
REPORT = ROOT / "reports" / "product" / "CYCLE_40997039714.md"
RAW = ORCH / "CYCLE_40990419541_run_jobs_raw.json"
FLAT = ORCH / "CYCLE_40990419541_audit_step_diagnosis.json"
DIAG = ORCH / "CYCLE_40990419541_resume_diagnosis.json"
DELTA = ORCH / "CYCLE_40990419541_delta_substance.json"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40997039714.json")
SMOKE = (ROOT / "results" / "product" / "progressive_smoke"
         / "CYCLE_40997039714_progressive_smoke.json")
SLICE = ROOT / "results" / "product" / "offline_slice" / "20261030T033523Z"
DOSSIER = AR / "CYCLE_40997039714_audit_readiness.json"
ROUTE = AR / "CYCLE_40997039714_AUDIT_ROUTE.json"
INTAKE = AR / "CYCLE_40997039714_AUDIT_INTAKE.md"
PRED_TEST = ROOT / "product" / "tests" / "test_cycle_40990419541.py"
RUN = "40997039714"
RESUME = "40990419541"
PRED_RUN = "40985854750"
SNAPSHOT = "e8e6eb942ddeb4ca107a81a3c45fb5021b58a25d"
PREVSNAP = "6128caee40dd61945c5fb41b9e1bac8dd5233acf"
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_pointer_posture_and_append_only_blocks():
    state = _json(STATE)
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    assert state["current_cycle_run_id"] == RUN
    assert state["current_run"] == RUN
    assert state["current_run_id"] == RUN
    assert state["direction_version"] == 68
    assert state["cycle_status"] == "COMPLETE"
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    block = state[f"cycle_{RUN}_operational_resume"]
    assert block["run_id"] == RUN
    assert block["resumed_run_id"] == RESUME
    assert block["predecessor_run_id"] == PRED_RUN
    assert block["resumed_snapshot_head"] == SNAPSHOT
    assert block["predecessor_snapshot_head"] == PREVSNAP
    assert block["diagnosis_of_resumed"] == \
        f"results/product/orchestration/CYCLE_{RESUME}_resume_diagnosis.json"
    rf = block["resumed_failure"]
    assert rf["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert "SUCCESS" in rf["team_job"]
    assert "e8e6eb94" in rf["team_job"]
    assert "2704.0 s" in rf["audit_job"]
    assert "exit 78" in rf["audit_job"]
    assert "OBSERVED_QUANTUM_EXPIRED" in rf["mechanism"]
    assert "pid=2499" in rf["mechanism"]
    assert "not a product defect" in rf["mechanism"]
    assert rf["gate_file_written"] is False
    assert rf["adjudication"] == "UNADJUDICATED"
    assert "14 changed files" in rf["durable_delta"]
    pf = block["predecessor_failure"]
    assert pf["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert "2704.0 s" in pf["team_job"]
    assert "pid=2501" in pf["team_job"]
    assert pf["gate_file_written"] is False
    assert pf["adjudication"] == "UNADJUDICATED"
    corr = block["correction"]
    assert corr["applies_to_run"] == RESUME
    assert "40863791646" in corr["defect"]
    assert "NOT rewritten" in corr["disposition"]
    mr = block["maintenance_repair"]
    assert mr["file"] == "product/tests/test_cycle_40990419541.py"
    assert "preserved inline as comments" in mr["originals_preserved"]
    assert block["snapshot_audit_readiness"]["state_advanced"] is True
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False
    assert state["audit_route"]["artifact"] == \
        "results/product/audit_readiness/CYCLE_40997039714_AUDIT_ROUTE.json"
    # Append-only predecessors and their reports must survive.
    assert state[f"cycle_{RESUME}_operational_resume"]
    assert state["cycle_40863791646_operational_resume"]
    assert state["cycle_40858799166_operational_resume"]
    assert state["cycle_40840720468_operational_resume"]
    assert (ROOT / "reports" / "product" / f"CYCLE_{RESUME}.md").is_file()


def test_run_history_chain_is_append_only_with_correction():
    state = _json(STATE)
    hist = {str(e.get("run_id")): e for e in state["run_history"]}
    for run_id in ("40977042308", PRED_RUN, RESUME, RUN):
        assert run_id in hist, run_id
    cur = hist[RUN]
    assert cur["status"] == (
        "AUDIT_JOB_QUANTUM_DEATH_RESUME_SNAPSHOT_REVERIFIED_"
        "AUDIT_READY_UNADJUDICATED"
    )
    assert cur["resumed_run"] == RESUME
    assert cur["accepted"] is False
    assert cur["accepted_commit"] == ACCEPTED
    assert cur["report_of_record"] == f"reports/product/CYCLE_{RUN}.md"
    assert cur["cycle_test"] == f"product/tests/test_cycle_{RUN}.py"
    assert cur["audit_gate"] == "NONE_YET"
    assert "SUCCESS" in cur["team_job"]
    assert "2704.0 s" in cur["audit_job"]
    assert "pid=2499" in cur["audit_job"]
    assert "14 changed files" in cur["durable_delta"]
    # The resumed run's own entry gains a correction field, not a rewrite.
    resumed = hist[RESUME]
    assert resumed["status"] == (
        "TEAM_JOB_LANE_CYCLE_QUANTUM_DEATH_RESUME_FRESH_SLICES_REVERIFIED_"
        "AUDIT_READY_UNADJUDICATED"
    )  # unchanged by the correction
    corr = resumed["correction"]
    assert corr["corrected_by_run"] == RUN
    assert "40863791646" in corr["field"]
    assert "duplicates" in corr["to"] or "duplicates" in corr["reason"]
    assert "NOT rewritten" in corr["history_preserved"]
    # Earlier history stays append-only.
    assert "40863791646" in hist and "40858799166" in hist


def test_orchestration_failure_is_observed_audit_quantum_expiry():
    for path in (RAW, FLAT, DIAG, DELTA):
        assert path.is_file(), path
    raw = _json(RAW)
    assert raw["run"]["id"] == 40990419541
    assert raw["run"]["conclusion"] == "failure"
    jobs = {j["name"]: j for j in raw["jobs"]}
    assert jobs["team"]["conclusion"] == "success"
    assert jobs["audit"]["conclusion"] == "failure"
    assert jobs["integrate"]["conclusion"] == "skipped"
    flat = _json(FLAT)
    assert flat["run_id"] == RESUME
    assert flat["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert flat["team"]["conclusion"] == "success"
    assert flat["team"]["producer_state_validation_step_conclusion"] == "success"
    assert flat["team"]["write_scope_step_conclusion"] == "success"
    assert flat["audit"]["conclusion"] == "failure"
    assert flat["audit"]["failed_step"] == "Independent audit"
    assert flat["audit"]["independent_audit_step_seconds"] == 2704.0
    assert flat["audit"]["gate_step"] == "skipped"
    assert flat["audit"]["persist_step"] == "skipped"
    assert flat["audit"]["gate_file_written"] is False
    mech = flat["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert "pid=2499" in mech["claim"]
    assert flat["observed_failure"]["job"] == "audit"
    assert flat["adjudication"]["product_defect"] is False
    assert flat["adjudication"]["verdict_written"] is False
    diag = _json(DIAG)
    assert diag["run_id"] == RESUME
    assert diag["predecessor_run_id"] == PRED_RUN
    assert diag["durable_delta"]["classification"] == "COMMITTED_DELTA"
    assert diag["durable_delta"]["changed_files"] == 14
    assert diag["durable_delta"]["snapshot_head"] == SNAPSHOT
    assert diag["durable_delta"]["predecessor_head"] == PREVSNAP
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["audit"]["audit_ref_present"] is False
    assert diag["correction_disclosed"]["target"].endswith(
        "CYCLE_40990419541.md section 1 chain table")
    delta = _json(DELTA)
    assert delta["changed_files"] == 14
    assert delta["delta_substance"] == "SUBSTANTIVE"
    assert delta["product_work"] is True
    assert delta["counts"] == {
        "code": 3, "report": 1, "results_artifact": 9, "state": 1}
    assert any("test_cycle_40990419541.py" in p
               for p in delta["substantive_files"])
    assert any("CYCLE_40985854750_resume_diagnosis.json" in p
               for p in delta["substantive_files"])


def test_fresh_reverification_artifacts():
    summary = _json(SLICE / "summary.json")
    bundle = _json(SLICE / "rent-default.bundle.json")
    assert summary["mode"] == "full_loop"
    assert summary["verified"] is True
    assert summary["degraded"] is False
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 70 assertions"
    stats = summary["stats"]
    assert stats["fixture_replay"]["network"] == "none"
    assert stats["fixture_replay_cache_misses"] == 0
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["rows_with_canonical_url"] == 100
    assert stats["rows_with_xy"] == 100
    assert stats["answer_status"] == "ready"
    assert len(bundle["decisions"]) == 100
    fam = _json(CONTENT_FAMILY)
    assert fam["run_id"] == RUN
    totals = fam["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 69
    assert totals["n_decisions"] == 6900
    assert totals["n_verified"] == 97
    assert totals["n_verified_defective"] == 0
    assert totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert fam["false_reject_count"] == 0
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["met"] is True
    smoke = _json(SMOKE)
    assert smoke["run_id"] == RUN
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert all(c["ok"] for c in smoke["checks"])


def test_maintenance_repair_removed_the_rotting_pointer_assertions():
    text = PRED_TEST.read_text(encoding="utf-8")
    # The disclosed repair is present and the rotting forms are preserved
    # only as commented history.
    assert "DISCLOSED MAINTENANCE REPAIR (cycle 40997039714)" in text
    live = [ln for ln in text.splitlines()
            if not ln.lstrip().startswith("#")]
    live_text = "\n".join(live)
    assert 'state["current_cycle_run_id"] == RUN' not in live_text
    assert 'state["audit_route"]["artifact"] ==' not in live_text
    assert 'state["current_cycle_run_id"]' in live_text
    assert 'state["audit_route"]["artifact"]' in live_text


def test_report_and_cycle_test_are_addressable():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "CYCLE_40284658455" in text
    assert "DO-NOT-SERVE" in text
    assert "UNADJUDICATED" in text
    assert "2704.0 s" in text
    assert "pid=2499" in text
    assert "14 files" in text or "14-file" in text
    # The corrected chain-table row for 40863791646 and its disclosure.
    assert "provider/network-class agent exit 1 after 2164.0 s" in text
    assert "not run" in text
    assert "Correction to the predecessor report" in text
    assert "not rewritten" in text
    assert Path(__file__).is_file()


def test_no_producer_minted_gate_for_this_run():
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{RUN}.md").exists()


def test_dossier_generated_if_present():
    # Conditional on presence: this is the first-generation fixpoint break.
    # audit_readiness.py runs this cycle test as part of generating the
    # dossier, so the dossier cannot exist when the test first executes.
    if not DOSSIER.exists():
        return
    dossier = _json(DOSSIER)
    assert dossier["run_id"] == RUN
    assert dossier["direction_version"] == 68
    assert dossier["overall_status"] in ("PASS", "PARTIAL")
    check = next(c for c in dossier["checks"]
                 if c["id"] == "resumed_diagnosis")
    assert check["status"] == "PASS"
    assert check["detail"]["mechanism_kind"] == "observed"
    assert check["detail"]["delta_kind"] == "committed"
    assert check["detail"]["changed_files"] == 14


def test_audit_route_artifact_if_present():
    # Conditional on presence: same first-generation fixpoint break; the
    # bootstrap route run excludes only this self-referential test by name
    # via `pytest -k not test_audit_route_artifact_if_present` when it is the
    # route's own chain_cycle_tests step (see audit_route.py --bootstrap).
    if not ROUTE.exists():
        return
    route = _json(ROUTE)
    assert route["schema"] == "product-audit-route/1"
    assert route["run_id"] == RUN
    assert route["quantum_budget_s"] == 2700
    assert route["audit_target"]["audit_target_ref"] == \
        f"origin/cycle/core/product/{RUN}/team"
    assert route["snapshot_self_label"]["status"] in (
        "ALIGNED", "ALIGNED_AFTER_WRITE")
    ids = [s["id"] for s in route["steps"]]
    for step in ("snapshot_self_label", "state_contract",
                 "chain_cycle_tests"):
        assert step in ids
    assert "never a verdict" in route["contract"]


def test_intake_artifact_if_present():
    if not INTAKE.exists():
        return
    text = INTAKE.read_text(encoding="utf-8")
    assert f"AUDIT INTAKE — product run {RUN}" in text
    assert f"origin/cycle/core/product/{RUN}/team" in text
    assert "UPPERCASE" in text or "_GATE.json" in text
