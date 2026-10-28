#!/usr/bin/env python3
"""Pins the operational resume of run 40726216925 (audit-side quantum death).

Resumed run 40726216925's TEAM job was FULLY GREEN (every step success,
including state validation, write scope and persist) and carried an 8-file
committed delta df6c81fb over predecessor 40718103891's team head 7cf7a11e.
Its AUDIT "Independent audit" step then died at the 2700 s work quantum
(exit 78, LEX_WORK_QUANTUM_EXPIRED, OBSERVED via public check-run
annotations, 2704.0 s); the gate and persist steps were skipped, no audit
branch and no gate exist, and integrate was skipped — the run is
UNADJUDICATED. This module pins that machine diagnosis, the PROFILES
registry entry of the resuming cycle 40737328834, the truth-corrected
40726216925 run_history fate (original preserved), the fail-closed posture
and the two-half accepted pointer.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
REPORT = ROOT / "reports" / "product" / "CYCLE_40737328834.md"
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / "CYCLE_40737328834_audit_readiness.json")
ACCEPTED = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
SNAPSHOT = "df6c81fb0cf7829cb0b5a19bee121f907685b228"
PREDECESSOR = "7cf7a11ecb46a99eeca93a9a0515c0cbd2342fd0"


def test_state_pointer_and_posture_non_rotting():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == ACCEPTED
    # current_run is the MOVING latest-resume pointer; THIS cycle's durable
    # delivery record is its own run_history entry + state block. Equality
    # to this cycle rots on the next resume. Disclosed maintenance repair by
    # cycle 40750177292 (the same non-rotting form used in
    # test_cycle_40682733879.py since CYCLE_40718103891). Original
    # assertion, preserved inline so no claim is silently weakened:
    #     assert state["current_run"] == "40737328834"
    assert state["current_run"]  # truthy, non-empty
    hist_ids = {str(e.get("run_id")) for e in state.get("run_history") or []}
    assert "40737328834" in hist_ids
    assert "cycle_40737328834_operational_resume" in state
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False
    assert state["owner_decision_required"] is False
    assert state["direction_version"] == 68
    block = state["cycle_40737328834_operational_resume"]
    assert block["resumed_run_id"] == "40726216925"
    assert block["resumed_death"]["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    assert "OBSERVED_QUANTUM_EXPIRED" in block["resumed_death"]["mechanism"]
    assert block["posture"]["continue_recommended"] is True
    assert block["posture"]["human_gate_ready"] is False


def test_run_history_fates():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    hist = {str(e["run_id"]): e for e in state["run_history"]}
    # The producer-recorded status of 40726216925 predates its own audit
    # death; this cycle corrected it and preserved the original inline.
    entry = hist["40726216925"]
    assert entry["status"] == \
        "AUDIT_JOB_QUANTUM_DEATH_COMMITTED_DELTA_UNADJUDICATED"
    assert entry["status_original_producer_record"] == \
        "OPERATIONAL_RESUME_VERIFY_AND_AUDIT_READINESS"
    assert entry["team_job"].startswith("SUCCESS")
    assert "OBSERVED_QUANTUM_EXPIRED" in entry["audit_job"]
    assert hist["40726216925"]["resumed_run"] == 40718103891
    assert hist["40726216925"]["accepted"] is False
    assert "40737328834" in hist
    assert hist["40737328834"]["resumed_run"] == 40726216925
    assert hist["40737328834"]["accepted"] is False
    for rid in ("40702698815", "40717159827", "40717587477", "40718103891"):
        assert rid in hist


def test_diagnosed_audit_quantum_death_of_40726216925():
    diag = json.loads((ORCH / "CYCLE_40726216925_resume_diagnosis.json")
                      .read_text(encoding="utf-8"))
    assert diag["run_id"] == "40726216925"
    assert diag["predecessor_run_id"] == "40718103891"
    orch = diag["orchestration"]
    assert orch["classification"] == \
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert orch["team"]["conclusion"] == "success"
    assert orch["team"]["producer_state_validation_step_conclusion"] == "success"
    assert orch["team"]["write_scope_step_conclusion"] == "success"
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["audit"]["conclusion"] == "failure"
    assert orch["audit"]["failed_step"] == "Independent audit"
    assert orch["audit"]["independent_audit_step_seconds"] == 2704.0
    assert orch["audit"]["gate_step"] == "skipped"
    assert orch["audit"]["persist_step"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 8
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    paths = " ".join(delta.get("changed_paths_sample") or [])
    assert "reports/product/CYCLE_40726216925.md" in paths
    assert "state/product.json" in paths
    rel = diag["accepted_head_relation"]
    assert rel["accepted_head"] == ACCEPTED
    assert rel["classification"] == "SNAPSHOT_NOT_ACCEPTED_HEAD"
    assert rel["is_accepted_head"] is False
    assert diag["adjudication"]["status"] == "UNADJUDICATED"


def test_raw_snapshot_for_40726216925():
    raw = json.loads((ORCH / "CYCLE_40726216925_run_jobs_raw.json")
                     .read_text(encoding="utf-8"))
    assert raw["run"]["id"] == 40726216925
    assert raw["run"]["conclusion"] == "failure"
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "success"
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert steps["Run lane cycle"] == "success"
    assert steps["Validate active MVP producer state"] == "success"
    assert steps["Enforce lane write scope"] == "success"
    assert steps["Persist team snapshot"] == "success"
    audit = next(j for j in raw["jobs"] if j["name"] == "audit")
    assert audit["conclusion"] == "failure"
    asteps = {s["name"]: s["conclusion"] for s in audit["steps"]}
    assert asteps["Independent audit"] == "failure"
    assert asteps["Enforce audit scope and read gate"] == "skipped"
    assert asteps["Persist audit snapshot"] == "skipped"
    integrate = next(j for j in raw["jobs"] if j["name"] == "integrate")
    assert integrate["conclusion"] == "skipped"
    msgs = [a["message"] for v in (raw.get("annotations") or {}).values()
            for a in v]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)


def test_profiles_registered_for_this_cycle():
    import sys
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert "40737328834" in PROFILES
    prof = select_profile("40737328834")
    assert prof["resumed_run_id"] == "40726216925"
    assert prof["failed_job"] == "audit"
    assert prof["mechanism_kind"] == "observed"
    assert prof["delta_kind"] == "committed"
    assert prof["quantum_seconds"] == 2700
    assert prof["exit_code"] == 78
    assert prof["changed_files"] == 8
    assert prof["cycle_test"] == "product/tests/test_cycle_40737328834.py"
    # The prior cycle's own profile is preserved in role.
    old = select_profile("40726216925")
    assert old["resumed_run_id"] == "40718103891"
    assert old["failed_job"] == "team"


def test_report_exists_and_states_the_fate():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    for needle in ("40726216925", "OBSERVED_QUANTUM_EXPIRED", "COMMITTED_DELTA",
                   "df6c81fb", "7cf7a11e", "7be4480e", "UNADJUDICATED",
                   "Independent audit", "AUDIT_JOB_INDEPENDENT_AUDIT"
                   "_STEP_FAILED_NO_GATE"):
        assert needle in text, needle


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == "40737328834"
        assert dossier["overall_status"] == "PASS"
        assert dossier["failed_checks"] == []
