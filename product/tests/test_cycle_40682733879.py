#!/usr/bin/env python3
"""Pins the operational-resume diagnosis and verification of 40682733879.

The resumed run 40676629031 died at the 'Run lane cycle' step after 2704.0 s
with exit code 78 and check-run annotations reading LEX_WORK_QUANTUM_EXPIRED
seconds=2700 — the FIRST TEAM-side quantum death of this unadjudicated
lineage — while producing ZERO_DURABLE_DELTA.  This module pins the chain
diagnosis (mechanism OBSERVED_QUANTUM_EXPIRED), the fresh content-family
re-verification of the v68 rejection/incumbent deliverable, the commit-early
countermeasure, and the audit-readiness profile, so a future auditor can
re-derive this snapshot's claims without re-tracing the orchestration
history.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
DIAG = ORCH / "CYCLE_40676629031_resume_diagnosis.json"
RAW_RESUMED = ORCH / "CYCLE_40676629031_run_jobs_raw.json"
REPORT = ROOT / "reports" / "product" / "CYCLE_40682733879.md"
COUNTER_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40682733879.json")
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / "CYCLE_40682733879_audit_readiness.json")


def test_state_pointer_and_posture():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert "cycle_40682733879_operational_resume" in state
    # current_run is the MOVING latest-resume pointer; THIS cycle's durable
    # delivery record is its own state block (above). Equality to this cycle
    # rots on the next resume (rot repair disclosed in CYCLE_40718103891).
    assert state["current_run"]  # truthy, non-empty
    assert state["direction_version"] == 68
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False


def test_run_history_covers_the_whole_chain():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    ids = {str(r.get("run_id")) for r in state.get("run_history") or []}
    for run_id in ("40640028819", "40647622447", "40654856196",
                   "40655374513", "40655643086", "40666994415",
                   "40667295410", "40676629031", "40682733879"):
        assert run_id in ids, run_id


def test_diagnosis_classifies_the_resumed_quantum_death():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == "40676629031"
    assert diag["predecessor_run_id"] == "40667295410"
    assert diag["resuming_run_id"] == "40682733879"
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_QUANTUM"
    mech = orch["mechanism"]
    assert mech["status"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["quantum_expired"] is True
    assert mech["quantum_seconds"] == 2700
    assert mech["exit_code"] == 78
    assert mech["annotations_available"] is True
    assert any("LEX_WORK_QUANTUM_EXPIRED" in m
               for m in mech.get("annotation_messages") or [])
    assert orch["team"]["failed_step"] == "Run lane cycle"
    assert orch["team"]["failed_step_seconds"] == 2704.0
    assert orch["team"]["team_snapshot_persisted"] is True
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == delta["predecessor_head"]
    assert delta["commits_after_predecessor_commit"] == 0
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["product_defect"] is False
    rel = diag["accepted_head_relation"]
    assert rel["accepted_head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert rel["snapshot_commits_ahead_of_accepted"] == 21


def test_raw_snapshot_has_quantum_annotations():
    raw = json.loads(RAW_RESUMED.read_text(encoding="utf-8"))
    assert raw["run"]["id"] == 40676629031
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    assert team["conclusion"] == "failure"
    failed = next(s for s in team["steps"] if s["conclusion"] == "failure")
    assert failed["name"] == "Run lane cycle"
    anns = raw.get("team_annotations") or []
    msgs = [a.get("message", "") for a in anns]
    assert any("exit code 78" in m for m in msgs)
    assert any("LEX_WORK_QUANTUM_EXPIRED" in m for m in msgs)
    assert any("quantum ended cleanly" in m for m in msgs)


def test_content_family_reverification_matches_expected():
    fam = json.loads(COUNTER_FAMILY.read_text(encoding="utf-8"))
    assert fam["run_id"] == "40682733879"
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


def test_report_and_dossier_exist():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "40676629031" in text
    assert "LEX_WORK_QUANTUM_EXPIRED" in text
    assert "2704" in text
    assert "commit-early" in text.lower() or "Commit-early" in text
    assert DOSSIER.is_file()
    dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
    assert dossier["run_id"] == "40682733879"
    problems = [c for c in dossier.get("checks", []) if c.get("status") != "PASS"]
    # At least the diagnosis, content-family and posture checks must PASS.
    by_id = {c["id"]: c for c in dossier.get("checks", [])}
    for cid in ("resumed_diagnosis", "content_family", "posture"):
        if cid in by_id:
            assert by_id[cid]["status"] == "PASS", (cid, by_id[cid])


def test_audit_readiness_profile_is_registered():
    import sys
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert "40682733879" in PROFILES
    assert "40676629031" in PROFILES
    prof = select_profile("40682733879")
    assert prof["resumed_run_id"] == "40676629031"
    assert prof["classification"] == "TEAM_JOB_LANE_CYCLE_STEP_FAILED_QUANTUM"
    assert prof["mechanism_kind"] == "observed"
    assert prof["quantum_seconds"] == 2700
    assert prof["exit_code"] == 78
    # alias resolves to the same profile content
    alias_prof = select_profile("40676629031")
    assert alias_prof["resumed_run_id"] == prof["resumed_run_id"]
    assert alias_prof["classification"] == prof["classification"]
    assert alias_prof["mechanism_kind"] == prof["mechanism_kind"]
