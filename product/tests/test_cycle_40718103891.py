#!/usr/bin/env python3
"""Pins the operational-resume chain diagnosis and audit readiness of 40718103891.

Resumed run 40717587477 died at 'Run lane cycle' exit 1 in 17.0 s with
ZERO_DURABLE_DELTA over 40717159827's head 876d1a82 (mechanism UNOBSERVED at
log level; requirement-20 provider/early-exit class; no product defect). Its
predecessor 40717159827 died the same way in 16.0 s. The producer run before
them, 40702698815, SUCCEEDED (committed 7-file delta 876d1a82) and its
independent AUDIT died at the 2700 s work quantum with no gate — the fifth
audit-quantum instance of this lineage and the first with a committed public
raw. This module pins the machine diagnoses of all three, the resolved
accepted-head relation (the new --ensure-accepted-ref fallback), the PROFILES
registry entries, the fresh content-family re-verification, and the state/report
of this cycle.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
REPORT = ROOT / "reports" / "product" / "CYCLE_40718103891.md"
COUNTER_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40718103891.json")
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / "CYCLE_40718103891_audit_readiness.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "876d1a82f70548a8b789b1ff23c5900029951b6f"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    assert "cycle_40718103891_operational_resume" in state
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40718103891_operational_resume"]
    assert block["resumed_run_id"] == "40717587477"
    assert block["audit_quantum_finding"]["run"] == "40702698815"


def test_run_history_covers_the_chain_tail():
    # Maintenance repair by cycle 40726216925 (disclosed, no claim weakened):
    # this entry asserted the producer-recorded status against the LIVE state
    # file, which rots the moment a later resume corrects the run's fate. The
    # producer wrote "OPERATIONAL_RESUME_..." at 16:18:57Z BEFORE the run died
    # at the 2700 s quantum; 40726216925 corrected the status and preserved
    # the original inline. Both the corrected fate and the preserved original
    # remain claim-bearing, so both are asserted.
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    for rid, expect in (
        ("40702698815", "TEAM_SUCCESS_AUDIT_QUANTUM_DEATH_UNADJUDICATED"),
        ("40717159827", "TEAM_EXIT_1_ZERO_DURABLE_DELTA_UNADJUDICATED"),
        ("40717587477", "TEAM_EXIT_1_ZERO_DURABLE_DELTA_UNADJUDICATED"),
        ("40718103891", "TEAM_JOB_QUANTUM_DEATH_COMMITTED_DELTA_UNADJUDICATED"),
    ):
        assert rid in hist, rid
        assert hist[rid]["status"] == expect
        assert hist[rid]["accepted"] is False
    entry = hist["40718103891"]
    assert entry["status_original_producer_record"] == \
        "OPERATIONAL_RESUME_CHAIN_DIAGNOSIS_AND_AUDIT_READINESS"
    assert "fate_correction" in entry


def test_diagnosed_audit_quantum_death_of_40702698815():
    diag = json.loads((ORCH / "CYCLE_40702698815_resume_diagnosis.json")
                      .read_text(encoding="utf-8"))
    assert diag["run_id"] == "40702698815"
    assert diag["predecessor_run_id"] == "40692326715"
    orch = diag["orchestration"]
    assert orch["classification"] == "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert orch["team"]["conclusion"] == "success"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2704.0
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 7
    assert delta["snapshot_head"] == SNAPSHOT
    rel = diag["accepted_head_relation"]
    assert rel["accepted_head"] == ACCEPTED
    assert rel["classification"] == "SNAPSHOT_NOT_ACCEPTED_HEAD"
    assert rel["is_accepted_head"] is False
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_diagnosed_exit1_zero_delta_deaths():
    for rid, pred in (("40717159827", "40702698815"), ("40717587477", "40717159827")):
        diag = json.loads((ORCH / f"CYCLE_{rid}_resume_diagnosis.json")
                          .read_text(encoding="utf-8"))
        assert diag["run_id"] == rid
        assert diag["predecessor_run_id"] == pred
        orch = diag["orchestration"]
        assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE"
        mech = orch["mechanism"]
        assert mech["status"] == "UNOBSERVED"
        assert mech["quantum_expired"] is False
        assert mech["exit_code"] == 1
        assert orch["team"]["failed_step"] == "Run lane cycle"
        assert orch["team"]["team_snapshot_persisted_after_failed_team_job"] is True
        delta = diag["durable_delta"]
        assert delta["classification"] == "ZERO_DURABLE_DELTA"
        assert delta["snapshot_head"] == delta["predecessor_head"] == SNAPSHOT
        assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_raw_snapshots_exist_for_the_chain_tail():
    for rid in ("40702698815", "40717159827", "40717587477"):
        raw = json.loads((ORCH / f"CYCLE_{rid}_run_jobs_raw.json")
                         .read_text(encoding="utf-8"))
        assert raw["run"]["id"] == int(rid)
        assert raw["run"]["conclusion"] == "failure"
    raw = json.loads((ORCH / "CYCLE_40717587477_run_jobs_raw.json")
                     .read_text(encoding="utf-8"))
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values() for a in v]
    assert any("exit code 1" in m for m in msgs)


def test_content_family_reverification_matches_expected():
    fam = json.loads(COUNTER_FAMILY.read_text(encoding="utf-8"))
    assert fam["run_id"] == "40718103891"
    totals = fam["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 52
    assert totals["n_decisions"] == 5200
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    hist = totals["defect_histogram"]
    assert hist["D2_letterhead_zone"] == 0
    assert hist["D3_markup_residue"] == 0
    assert hist["D4_language_marker_mismatch"] == 0
    assert hist["D1_empty_evidence"] == 0
    assert fam["false_reject_count"] == 0
    assert fam["ordered_work_2_success_rule"]["met"] is True
    assert fam["ordered_work_2_full_success_rule"]["met"] is True


def test_audit_readiness_profiles_are_registered():
    import sys
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    for rid, resumed, kind in (
        ("40702698815", "40702698815", "observed"),
        ("40717159827", "40717159827", "observed_steps"),
        ("40717587477", "40717587477", "observed_steps"),
        ("40718103891", "40717587477", "observed_steps"),
    ):
        assert rid in PROFILES
        prof = select_profile(rid)
        assert prof["resumed_run_id"] == resumed
        assert prof["mechanism_kind"] == kind
    assert select_profile("40718103891")["cycle_test"] == \
        "product/tests/test_cycle_40718103891.py"


def test_report_exists_and_states_the_chain():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    for needle in ("40717587477", "OBSERVED_QUANTUM_EXPIRED", "ZERO_DURABLE_DELTA",
                   "ensure-accepted-ref", "requirement-20", ACCEPTED):
        assert needle in text, needle


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == "40718103891"
        assert dossier["overall_status"] == "PASS"
