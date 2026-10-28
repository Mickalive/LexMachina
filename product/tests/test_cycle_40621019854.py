#!/usr/bin/env python3
"""Pins the operational-resume repair for cycle 40621019854."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state" / "product.json"
DIAG = ROOT / "results" / "product" / "orchestration" / "CYCLE_40621019854_validation_diagnosis.json"
REPORT = ROOT / "reports" / "product" / "CYCLE_40621019854.md"
COUNTER_FAMILY = ROOT / "results" / "product" / "counter_content_family" / "CYCLE_40621019854.json"


def test_state_pointer_restored_to_accepted_head():
    state = json.loads(STATE.read_text())
    assert state["accepted_run_id"] == "CYCLE_40284658455"
    assert state["accepted_commit"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert "cycle_40621019854_operational_resume" in state


def test_run_history_includes_resumed_runs():
    state = json.loads(STATE.read_text())
    ids = [str(r.get('run_id')) for r in state.get("run_history") or []]
    assert "40606019054" in ids
    assert "40620804872" in ids
    assert "40621019854" in ids


def test_diagnosis_artifact_exists_and_classifies():
    diag = json.loads(DIAG.read_text())
    assert diag["run_id"] == "40621019854"
    assert diag["resumed_run_id"] == "40620804872"
    assert diag["classification"] == "STATE_POINTER_REGRESSION_PLUS_PARTIAL_COMMIT"
    assert diag["orchestration"]["mechanism_unobserved"] is True


def test_report_published():
    assert REPORT.exists()
    txt = REPORT.read_text()
    assert "40621019854" in txt
    assert "7be4480e" in txt


def test_counter_family_reverified():
    cf = json.loads(COUNTER_FAMILY.read_text())
    # totals may be embedded differently; check rules
    assert cf.get("ordered_work_2_full_success_rule", {}).get("met") is True
    assert cf.get("ordered_work_2_success_rule", {}).get("met") is True
    assert cf.get("false_reject_count") == 0
