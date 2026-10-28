#!/usr/bin/env python3
"""Pins the operational-resume diagnosis and verification of 40692326715.

Raw run/jobs snapshot unavailable in this checkout; orchestration mechanism
remains UNOBSERVED. The team snapshot at origin/cycle/core/product/
40692326715/team (079e6d53) carries a COMMITTED_DELTA over predecessor
40682733879's head 96d79c7e. No independent audit gate and no accept commit
observed — status UNADJUDICATED. This module pins diagnosis, fresh content-
family re-verification of the v68 rejection/incumbent deliverable, and audit-
readiness registration so a future auditor can re-derive this snapshot's
claims without guessing the orchestration cause.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
DIAG = ORCH / "CYCLE_40692326715_resume_diagnosis.json"
REPORT = ROOT / "reports" / "product" / "CYCLE_40692326715.md"
COUNTER_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40692326715.json")
DOSSIER = (ROOT / "results" / "product" / "audit_readiness"
           / "CYCLE_40692326715_audit_readiness.json")


def test_state_pointer_and_posture():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert "cycle_40692326715_operational_resume" in state
    assert state["continue_recommended"] is True
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["ready_for_owner_session"] is False
    assert state["packet_admitted"] is False


def test_diagnosis_unobserved_committed_delta():
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    assert diag["run_id"] == "40692326715"
    assert diag["predecessor_run_id"] == "40682733879"
    assert diag["raw_snapshot"] is None
    orch = diag["orchestration"]
    assert orch["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert orch["mechanism_unobserved"] is True
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["changed_files"] == 9
    assert delta["snapshot_head"] == "079e6d53268f0a942d274bdc633340b6608927fc"
    assert delta["predecessor_head"] == "96d79c7e42e745f59252ca8711ce58637df06073"
    adj = diag["adjudication"]
    assert adj["status"] == "UNADJUDICATED"
    assert adj["accepted"] is False
    assert adj["product_defect"] is False
    assert adj["audit"]["gate_file_present"] is False


def test_content_family_reverification_matches_expected():
    fam = json.loads(COUNTER_FAMILY.read_text(encoding="utf-8"))
    assert fam["run_id"] == "40692326715"
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


def test_report_exists():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "40692326715" in text
    assert "RAW_SNAPSHOT_UNAVAILABLE" in text
    assert "COMMITTED_DELTA" in text


def test_audit_readiness_profile_is_registered():
    import sys
    sys.path.insert(0, str(ROOT))
    from product.audit_readiness import PROFILES, select_profile
    assert "40692326715" in PROFILES
    prof = select_profile("40692326715")
    assert prof["resumed_run_id"] == "40692326715"
    assert prof["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert prof["mechanism_kind"] == "unobserved"
    assert prof["delta_kind"] == "committed"
    assert prof["cycle_test"] == "product/tests/test_cycle_40692326715.py"


def test_dossier_generated_if_present():
    if DOSSIER.exists():
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        assert dossier["run_id"] == "40692326715"
