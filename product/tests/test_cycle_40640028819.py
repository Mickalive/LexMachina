#!/usr/bin/env python3
"""Pins the operational-resume chain diagnosis and verification of 40640028819.

The three-run unadjudicated chain (40633276503 audit quantum expiry ->
40639072630 rc-67 zero-delta -> 40639812991 exit-1 zero-delta), the resumed
run's classification, the fresh content-family verification and the honest
zero-delta wording of the audit-readiness profile are all pinned here so a
future auditor can re-derive this snapshot's claims without re-tracing the
orchestration history.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
DIAG = ORCH / "CYCLE_40639812991_resume_diagnosis.json"
RAW_RESUMED = ORCH / "CYCLE_40639812991_run_jobs_raw.json"
RAW_PREDECESSOR = ORCH / "CYCLE_40639072630_run_jobs_raw.json"
RAW_CHAIN_ROOT = ORCH / "CYCLE_40633276503_run_jobs_raw.json"
REPORT = ROOT / "reports" / "product" / "CYCLE_40640028819.md"
COUNTER_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40640028819.json")
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / "CYCLE_40640028819_audit_readiness.json")


def test_state_pointer_and_block():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert "cycle_40640028819_operational_resume" in state
    # current_run is the MOVING latest-resume pointer, advanced by every later
    # operational resume; the durable delivery record for THIS cycle is its
    # own state block (asserted above) plus the accepted pointers. Equality of
    # current_run to this cycle rots on the next resume and is not re-asserted
    # against live state (rot repair disclosed in CYCLE_40718103891).
    assert state["current_run"]  # truthy, non-empty
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False


def test_run_history_covers_the_whole_chain():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    ids = {str(r.get("run_id")) for r in state.get("run_history") or []}
    for run_id in ("40633276503", "40639072630", "40639812991", "40640028819"):
        assert run_id in ids, run_id


def test_diagnosis_classifies_the_resumed_failure():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == "40639812991"
    assert diag["predecessor_run_id"] == "40639072630"
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
    assert orch["mechanism"]["status"] == "UNOBSERVED"
    assert orch["mechanism"]["quantum_expired"] is False
    assert orch["mechanism"]["exit_code"] == 1
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 16.0
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    chain = diag["chain_context"]["runs"]
    assert [c["run_id"] for c in chain] == [40633276503, 40639072630, 40639812991]
    root = chain[0]
    assert root["audit_exit_code"] == 78
    assert "LEX_WORK_QUANTUM_EXPIRED" in root["audit_signature"]
    assert chain[1]["exit_code"] == 67


def test_raw_snapshots_are_committed_and_observed():
    for path, run_id, team_conclusion in (
        (RAW_RESUMED, 40639812991, "failure"),
        (RAW_PREDECESSOR, 40639072630, "failure"),
        (RAW_CHAIN_ROOT, 40633276503, "success"),
    ):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["run"]["id"] == run_id
        assert doc["logs_endpoint_status"] == 403
        jobs = {j["name"]: j for j in doc["jobs"]}
        assert jobs["team"]["conclusion"] == team_conclusion
        steps = {s["name"]: s["conclusion"] for s in jobs["team"]["steps"]}
        assert steps["Persist team snapshot"] == "success"
    resumed = json.loads(RAW_RESUMED.read_text(encoding="utf-8"))
    steps = {s["name"]: s["conclusion"]
             for s in next(j for j in resumed["jobs"]
                           if j["name"] == "team")["steps"]}
    assert steps["Run lane cycle"] == "failure"
    assert steps["Validate active MVP producer state"] == "skipped"
    chain_root = json.loads(RAW_CHAIN_ROOT.read_text(encoding="utf-8"))
    audit_steps = {s["name"]: s["conclusion"]
                   for s in next(j for j in chain_root["jobs"]
                                 if j["name"] == "audit")["steps"]}
    assert audit_steps["Independent audit"] == "failure"
    assert audit_steps["Persist audit snapshot"] == "skipped"


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

    prof = ar.select_profile("40640028819")
    assert prof["resumed_run_id"] == "40639812991"
    assert prof["predecessor_run_id"] == "40639072630"
    assert prof["mechanism_kind"] == "observed_steps"
    assert prof["delta_kind"] == "zero"
    assert prof["cycle_test"] == "product/tests/test_cycle_40640028819.py"
    # The alias resolves to the same profile; unknown runs still fail closed.
    assert ar.select_profile("40639812991")["resumed_run_id"] == "40639812991"
    ref = prof["zero_delta_reference"]
    assert "predecessor" in ref and "7be4480e" in ref
    # Legacy profiles keep the default wording (accepted head), so their
    # historical dossiers still reproduce byte-for-byte.
    legacy = ar.select_profile("40423889401")
    assert "zero_delta_reference" not in legacy


def test_report_published():
    txt = REPORT.read_text(encoding="utf-8")
    assert "40640028819" in txt
    assert "40639812991" in txt
    assert "LEX_WORK_QUANTUM_EXPIRED" in txt
    assert "LEX_ZERO_DELTA_REPAIR" in txt


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
    assert doc["run_id"] == "40640028819"
    assert doc["resumed_run_id"] == "40639812991"
    assert doc["overall_status"] in ("PASS", "PARTIAL")
    assert doc["posture"]["gate_minted"] is False
    assert doc["posture"]["human_gate_ready"] is False
    failed = [c["id"] for c in doc.get("checks") or [] if c.get("status") == "FAIL"]
    # Mandatory non-skipped checks must be green on the committed dossier.
    mandatory_failed = [
        c["id"] for c in doc.get("checks") or []
        if c.get("status") == "FAIL" and c.get("mandatory", True)
    ]
    assert not mandatory_failed, (failed, mandatory_failed)
