"""Tests for the operational-resume completion of 44642744588 (run 44651501043)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation import operational_resume_44651501043 as C
from evaluation import nested_evidence_refs_guard as NERG
from evaluation import state_integrity_gate as SIG
from evaluation.snapshot_audit import write_scope as WS

REPO = Path(__file__).resolve().parents[2]


def load(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def test_freeze_pins_hypothesis_hash():
    freeze = load(C.FREEZE_REL)
    assert freeze["hypothesis_sha256_at_freeze"] == C.sha(C.HYP_REL)
    assert load(C.HYP_REL)["frozen_before_execution"] is True
    assert freeze["run_id"] == C.RUN


def test_all_claims_and_controls_pass():
    result = load(C.RESULT_REL)
    assert result["verdict"] == "AUDIT_READY_VERIFIED", result["failed_claims_or_controls"]
    assert all(v["ok"] for v in result["checks"].values())
    assert all(v["holds"] for v in result["controls"].values())


def test_failure_chain_both_classes_committed():
    result = load(C.RESULT_REL)
    chain = result["details"]["V2_failure_chain"]
    assert chain["failure_classes"] == [
        "ORCHESTRATION_RC1_NONZERO_EXIT",
        "ORCHESTRATION_AUDIT_QUANTUM_EXPIRY_RC78",
    ]
    assert chain["gates_absent"] and chain["accept_absent"]
    assert (REPO / C.CAPTURE_REL).is_file()


def test_item2_still_non_discriminating_and_no_falsifier():
    result = load(C.RESULT_REL)
    item2 = result["details"]["V3_V4"]["item2"]
    assert item2["status"].startswith("NOT_YET_DISCRIMINATING")
    assert item2["H1"] is True and item2["H2"] is False
    assert item2["matched"] == 14 and item2["of"] == 15
    assert result["falsifier_reexecuted"] is False
    assert result["packet_of_record_scored"] is False
    assert result["universal_174k_benchmark_run"] is False


def test_item2_rederived_from_frozen_gate():
    item2 = load(C.RESULT_REL)["details"]["V3_V4"]["item2"]
    gate = item2["gate"]
    assert gate["H1_precondition_leg_landed"] == item2["H1"]
    mfm = gate["set_relations_REQUIREMENT_16"]["member_for_member_matching"]
    assert mfm["matched_members"] == item2["matched"]
    assert mfm["of"] == item2["of"]


def test_state_hygiene_and_parity():
    root, lane = load(C.ROOT_STATE), load(C.LANE_STATE)
    for f in ("accepted_run_id", "direction_version", "github_run", "proposed_run_id"):
        assert root[f] == lane[f], f
    assert root["accepted_run_id"] == C.ACCEPTED
    assert root["github_run"] == C.RUN
    assert root["evidence_refs_n"] == len(root["evidence_refs"])
    assert lane["evidence_refs_n"] == len(lane["evidence_refs"])
    # The dangling historical ref existed only in the root state; the lane
    # state received the divergence/resume annotations without that field.
    src = root["github_run_advance_40246705199"]["required_fixes_source"]
    assert src.startswith("HISTORICAL_AUDIT_BRANCH_GATE_NOT_FETCHED")
    assert "results/audit/evaluation/CYCLE_40246705199_GATE.json" in src
    for st in (root, lane):
        assert f"evidence_tier_divergence_disclosure_{C.RUN}" in st
        assert f"operational_resume_{C.RUN}" in st
        assert st["resumed_run_id"] == C.UNDER_RESUME
        assert "40261335674" not in st["next_recommendation"]


def test_nested_refs_and_integrity_gate_pass():
    code, record = NERG.run("pytest_" + str(C.RUN), REPO / "results/evaluation/orchestration")
    assert code == 0 and record["n_unresolved"] == 0
    assert record["n_top_level_unresolved"] == 0
    sig_code, sig = SIG.run(REPO)
    assert sig_code == 0 and sig["verdict"] == "ALL_CHECKS_PASS"


def test_write_scope_rejects_producer_audit_path():
    assert not WS.classify_path(
        f"results/audit/evaluation/CYCLE_{C.RUN}_GATE.json", "evaluation")
    assert WS.classify_path(C.INSTRUMENT_REL, "evaluation")
    assert WS.classify_path(C.RESULT_REL, "evaluation")
    assert WS.classify_path(C.ROOT_STATE, "evaluation")


def test_no_falsifier_import_in_completion_source():
    src = (REPO / C.INSTRUMENT_REL).read_text(encoding="utf-8")
    forbidden = "fast_mvp_" + "current_head_ca_falsifier"
    assert forbidden not in src
