#!/usr/bin/env python3
"""Pins the operational-resume diagnosis and verification of 40667295410.

The resumed run 40666994415 died at the 'Run lane cycle' step after 17.0 s
with ZERO_DURABLE_DELTA, while its predecessor 40655643086's independent
audit had already failed the 'Independent audit' step at exactly 2705 s —
the fourth audit-side ~2700 s work-quantum death of this unadjudicated
lineage.  This module pins the chain diagnosis, the fresh content-family
re-verification of the v68 rejection/incumbent deliverable, and the honest
zero-delta wording of the audit-readiness profile, so a future auditor can
re-derive this snapshot's claims without re-tracing the orchestration
history.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
DIAG = ORCH / "CYCLE_40666994415_resume_diagnosis.json"
RAW_RESUMED = ORCH / "CYCLE_40666994415_run_jobs_raw.json"
RAW_PREDECESSOR = ORCH / "CYCLE_40655643086_run_jobs_raw.json"
REPORT = ROOT / "reports" / "product" / "CYCLE_40667295410.md"
COUNTER_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40667295410.json")
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / "CYCLE_40667295410_audit_readiness.json")


def test_state_pointer_and_block():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert "cycle_40667295410_operational_resume" in state
    # current_run is the MOVING latest-resume pointer; THIS cycle's durable
    # delivery record is its own state block (above). Equality to this cycle
    # rots on the next resume (rot repair disclosed in CYCLE_40718103891).
    assert state["current_run"]  # truthy, non-empty
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False


def test_run_history_covers_the_whole_chain():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    ids = {str(r.get("run_id")) for r in state.get("run_history") or []}
    for run_id in ("40640028819", "40647622447", "40654856196",
                   "40655374513", "40655643086", "40666994415",
                   "40667295410"):
        assert run_id in ids, run_id


def test_diagnosis_classifies_the_resumed_failure():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == "40666994415"
    assert diag["predecessor_run_id"] == "40655643086"
    assert diag["resuming_run_id"] == "40667295410"
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["mechanism"]["status"] == "UNOBSERVED"
    assert orch["mechanism"]["logs_endpoint_status"] == 403
    assert orch["mechanism"]["quantum_expired"] is False
    assert orch["mechanism"]["exit_code"] is None
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 17.0
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["team"]["producer_state_validation_ran"] is False
    assert orch["team"]["write_scope_step_ran"] is False
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    assert diag["adjudication"]["product_defect"] is False
    rel = diag["accepted_head_relation"]
    assert rel["accepted_head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert rel["snapshot_commits_ahead_of_accepted"] == 20
    chain = diag["chain_context"]["runs"]
    assert [c["run_id"] for c in chain] == [
        40640028819, 40647341524, 40647622447, 40654856196, 40655374513,
        40655643086, 40666994415]
    assert chain[0]["audit_step_seconds"] == 2705.0
    assert chain[2]["audit_step_seconds"] == 2705.0
    assert chain[5]["audit_step_seconds"] == 2705.0
    assert chain[5]["run_id"] == 40655643086
    assert chain[6]["durable_delta"] == "ZERO_DURABLE_DELTA"


def test_raw_snapshots_are_committed_and_observed():
    resumed = json.loads(RAW_RESUMED.read_text(encoding="utf-8"))
    assert resumed["run"]["id"] == 40666994415
    assert resumed["logs_endpoint_status"] == 403
    team = next(j for j in resumed["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    assert steps["Enforce lane write scope"] == "skipped"
    assert steps["Persist team snapshot"] == "success"
    audit = next(j for j in resumed["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "skipped"

    pred = json.loads(RAW_PREDECESSOR.read_text(encoding="utf-8"))
    assert pred["run"]["id"] == 40655643086
    assert next(j for j in pred["jobs"] if j["name"] == "team")["conclusion"] == "success"
    audit_steps = {s["name"]: s for s in
                   next(j for j in pred["jobs"] if j["name"] == "audit")["steps"]}
    assert audit_steps["Independent audit"]["conclusion"] == "failure"
    assert audit_steps["Persist audit snapshot"]["conclusion"] == "skipped"
    from datetime import datetime as _dt
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    ind = audit_steps["Independent audit"]
    elapsed = (_dt.strptime(ind["completed_at"], fmt)
               - _dt.strptime(ind["started_at"], fmt)).total_seconds()
    assert elapsed == 2705.0


def test_counter_family_reverified_this_cycle():
    cf = json.loads(COUNTER_FAMILY.read_text(encoding="utf-8"))
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 52
    assert totals["n_decisions"] == 5200
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert all(v == 0 for v in totals["defect_histogram"].values())
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["still_verified"] is True
    assert cf["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert cf["ordered_work_2_success_rule"]["met"] is True
    assert cf["ordered_work_2_full_success_rule"]["met"] is True


def test_audit_readiness_profile_is_honest_about_the_zero_delta_target():
    from product import audit_readiness as ar

    prof = ar.select_profile("40667295410")
    assert prof["resumed_run_id"] == "40666994415"
    assert prof["predecessor_run_id"] == "40655643086"
    assert prof["mechanism_kind"] == "observed_steps"
    assert prof["delta_kind"] == "zero"
    assert prof["exit_code"] is None
    assert prof["cycle_test"] == "product/tests/test_cycle_40667295410.py"
    # The alias resolves to the same profile; unknown runs still fail closed.
    assert ar.select_profile("40666994415")["resumed_run_id"] == "40666994415"
    ref = prof["zero_delta_reference"]
    assert "predecessor" in ref and "7be4480e" in ref and "7d411a69" in ref
    expected = prof["content_family_expected"]
    assert expected["n_bundles"] == 52
    assert expected["n_verified_defective"] == 0


def test_dossier_advises_a_measured_audit_cost_budget():
    # The binding stall of this lineage is four audit-side deaths at the
    # ~2700 s work-quantum boundary.  The dossier must therefore publish a
    # measured, bounded verification path so the auditor's first minutes are
    # pinned: sub-second re-hash of the committed claim artifacts, then only
    # the failing check regenerated, and no re-run of the 153-bundle
    # historical sweep.
    if DOSSIER.is_file():
        doc = json.loads(DOSSIER.read_text(encoding="utf-8"))
        budget = doc["audit_entry_points"].get("audit_cost_budget")
        assert budget and "0.061" in budget and "153-bundle" in budget
        return
    # Before the dossier exists (first pytest run of this module), the source
    # pin is the binding claim.
    from product import audit_readiness as ar

    src = Path(ar.__file__).read_text(encoding="utf-8")
    assert "audit_cost_budget" in src
    assert "0.061" in src
    assert "153-bundle" in src


def test_report_published():
    txt = REPORT.read_text(encoding="utf-8")
    assert "40667295410" in txt
    assert "40666994415" in txt
    assert "2705" in txt
    assert "ZERO_DURABLE_DELTA" in txt or "zero" in txt.lower()


def test_dossier_when_present_is_bounded():
    # The dossier is generated by the same producer run AFTER this test file
    # exists (the dossier's cycle_test check runs this module), so existence
    # is not asserted here — that would be a chicken-and-egg failure.  When
    # the committed dossier is present it must be bounded and non-minting;
    # its claim_artifacts hashes are independently re-checkable with
    # `python3 product/audit_readiness.py --verify <dossier>`.
    if not DOSSIER.is_file():
        return
    doc = json.loads(DOSSIER.read_text(encoding="utf-8"))
    assert doc["run_id"] == "40667295410"
    assert doc["resumed_run_id"] == "40666994415"
    assert doc["overall_status"] in ("PASS", "PARTIAL")
    assert doc["posture"]["gate_minted"] is False
    assert doc["posture"]["human_gate_ready"] is False
    mandatory_failed = [
        c["id"] for c in doc.get("checks") or []
        if c.get("status") == "FAIL" and c.get("mandatory", True)
    ]
    assert not mandatory_failed, mandatory_failed
