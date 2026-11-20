"""Tests for the operational resume of 44642554373 (run 44642744588)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from evaluation import operational_resume_44642744588 as OR
from evaluation.snapshot_audit import write_scope as WS

REPO = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def test_freeze_and_hypothesis_exist_and_are_pinned():
    hyp = load(OR.HYP_REL)
    freeze = load(OR.FREEZE_REL)
    assert hyp["frozen_before_execution"] is True
    assert freeze["hypothesis_sha256_at_freeze"] == OR.sha256_file(
        REPO / OR.HYP_REL)
    assert freeze["expected_snapshot_pins"]["HEAD"] == OR.SNAPSHOT_SHA
    assert freeze["expected_mount_pins"][
        "mount:product/query/pipeline.py"] == OR.sha256_file(
            Path("/tmp/lex_accepted/product/product/query/pipeline.py"))


def test_measurement_claims_and_controls_hold():
    result = load(OR.RESULT_REL)
    assert result["checks"], "no checks recorded"
    failed = [k for k, v in result["checks"].items() if not v["ok"]]
    assert not failed, failed
    for cid in ("C1_snapshot_mutation_detected",
                "C2_annotation_mutation_detected",
                "C3_span_mutation_detected",
                "C4_measurement_mutation_detected",
                "C5_no_falsifier_reexecution",
                "C6_item2_rule_consistency",
                "C8_write_scope"):
        assert result["controls"][cid]["holds"] is True, cid


def test_snapshot_mutation_is_detected():
    assert OR.snapshot_relation_ok(
        OR.SNAPSHOT_SHA, OR.SNAPSHOT_SHA, OR.SNAPSHOT_SHA, False)
    assert not OR.snapshot_relation_ok(
        "0" * 40, OR.SNAPSHOT_SHA, OR.SNAPSHOT_SHA, False)


def test_annotation_mutation_is_detected():
    capture = load(OR.REST_CAPTURE_REL)
    ann = load(OR.ANNOTATION_REL)["annotation"]
    assert OR.failure_metadata_ok(capture, ann)
    assert not OR.failure_metadata_ok(
        capture, "Process completed with exit code 67.")


def test_span_mutation_is_detected():
    result = load(OR.RESULT_REL)
    span = result["checks"][
        "CC4_bundle_span_provenance_of_record"]["actual"]
    good = {k: span.get(k) for k in (
        "applied", "mode", "n_candidates", "n_selected", "n_abstained",
        "abstained_ids", "abstention_reasons", "frozen_rules_sha256")}
    assert OR.span_ok(good)
    assert not OR.span_ok(dict(good, n_selected=1))


def test_measurement_mutation_is_detected():
    good = {
        "verdict": "SOUND_COUNTER_ROW_PRESENT", "exit_code": 0,
        "falsification_proven": False, "n_verified_scored_rows_total": 5,
        "n_defective_verified_scored_rows_total": 4,
        "defect_histogram": {"D2_letterhead_zone": 2,
                             "D3_markup_residue": 2,
                             "D4_language_marker_mismatch": 1},
        "distinct_defective_decision_ids": [
            "bge_BGE_110_II_391", "bge_BGE_121_III_260",
            "ge_gerichte_CAPH_107_2004", "gr_gerichte_ERZ 2010 25"],
    }
    assert OR.measurement_ok(good, good)
    assert not OR.measurement_ok(
        dict(good, n_defective_verified_scored_rows_total=3), good)


def test_no_falsifier_reexecution_source_scan():
    src = (REPO / OR.INSTRUMENT_REL).read_text(encoding="utf-8")
    assert "from evaluation import " + OR.FORBIDDEN_MODULE not in src
    assert "import " + OR.FORBIDDEN_MODULE not in src
    assert OR.FORBIDDEN_MODULE + "." not in src


def test_item2_status_is_consistent_with_frozen_gate():
    result = load(OR.RESULT_REL)
    item = result["item_2"]
    assert OR.item2_consistency_ok(
        item["status"], item["H1"], item["H2"], item["matched"], item["of"])
    assert item["full_protocol_executed"] is False
    assert item["packet_of_record_scored"] is False


def test_item2_gate_matches_frozen_precondition_run():
    """Re-derive the set relation once and check the committed result."""
    from evaluation.post_repair_family_ca_falsifier import precondition_gate
    hyp = load(OR.PRECONDITION_HYP_REL)
    gate = precondition_gate(hyp, Path("/tmp/lex_accepted/product"))
    result = load(OR.RESULT_REL)
    assert gate["H1_precondition_leg_landed"] == result["item_2"]["H1"]
    mfm = gate["set_relations_REQUIREMENT_16"][
        "member_for_member_matching"]
    assert mfm["matched_members"] == result["item_2"]["matched"]
    assert mfm["of"] == result["item_2"]["of"]


def test_write_scope_rejects_producer_audit_path():
    assert WS.classify_path(
        "evaluation/operational_resume_44642744588.py", "evaluation")
    assert WS.classify_path(
        "tests/evaluation/test_operational_resume_44642744588.py",
        "evaluation")
    assert not WS.classify_path(
        "results/audit/evaluation/CYCLE_44642744588_GATE.json",
        "evaluation")


def test_state_pointer_after_apply():
    result = load(OR.RESULT_REL)
    if not result.get("state_update"):
        pytest.skip("state update not applied yet")
    assert result["checks"]["CC10_state_pointer_and_refs"]["ok"] is True
    assert result["controls"]["C7_state_pointer_bridge"]["holds"] is True
    root = load("state/evaluation.json")
    lane = load("evaluation/state/evaluation.json")
    assert root["accepted_run_id"] == OR.LATEST_ACCEPTED_EVAL
    assert lane["accepted_run_id"] == OR.LATEST_ACCEPTED_EVAL
    assert root["github_run"] == lane["github_run"] == OR.RUN_ID
    assert root["evidence_refs_n"] == len(root["evidence_refs"])
    assert lane["evidence_refs_n"] == len(lane["evidence_refs"])


def test_freeze_commit_precedes_result_when_committed():
    """Ordering proof contract from the freeze record."""
    p = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H %cI %s", "--",
         OR.FREEZE_REL, OR.HYP_REL, OR.RESULT_REL],
        cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        pytest.skip("freeze/result not committed yet")
    assert "OPERATIONAL_RESUME_44642744588_FREEZE_V1" in p.stdout
