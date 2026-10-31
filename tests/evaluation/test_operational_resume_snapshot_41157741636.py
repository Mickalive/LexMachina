"""Executable audit-readiness self-check for the 41157741636 resume snapshot.

These tests read only committed JSON artifacts. They do not import Product,
network, numpy or the frozen benchmark instruments. They are deliberately plain
functions so the lane's documented no-pytest shim can execute them when pytest
is absent.

They assert the exact claims the resume makes:
  * the prior result is complete and reproducible;
  * the orchestration failure was a 2700-second work-quantum expiry (exit 78),
    not a measurement failure;
  * the accepted pointer is 40265377500 on both halves of requirement 4;
  * the multilingual/provenance supplement passed 2/2 while preserving the
    prior IMPORT_ERROR;
  * the producer minted no audit gate for its own run.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def test_prior_result_complete_and_not_rederived() -> None:
    r = _load("results/evaluation/operational_resume/41157741636.json")
    assert r["verdict"] == "OPERATIONAL_RESUME_VERIFICATION_COMPLETE"
    assert r["exit_code"] == 0
    assert r["pins_before_execution"]["all_match"] is True
    assert r["pins_after_execution"]["all_match"] is True
    assert r["controls"]["C4_no_audit_gate_minted"]["holds"] is True
    assert r["precondition"]["H2_precondition_full_family_regenerated"] is False
    assert "NOT_YET_DISCRIMINATING" in r["item_2_full_protocol_status"]
    assert r["no_frozen_bar_scored"] is True
    assert r["packet_of_record_not_scored"] is True
    assert r["closed_bytes_not_rescored"] is True


def test_prior_result_reproduced_byte_identically() -> None:
    rep = _load("results/evaluation/operational_resume/41161273401_prior_result_reproduction.json")
    assert rep["reproduced"] is True
    assert rep["normalized_equal"] is True
    assert rep["diff_paths"] == []
    assert rep["only_field_removed_before_comparison"] == "generated_at_utc"
    assert rep["committed_normalized_sha256"] == rep["scratch_normalized_sha256"]
    assert rep["scratch_exit_code"] == 0


def test_orchestration_failure_is_quantum_expiry_not_measurement() -> None:
    d = _load("results/evaluation/orchestration/CYCLE_41157741636_quantum_expiry.json")
    assert d["run_id"] == "41157741636"
    assert d["failure_class"] == "WORK_QUANTUM_EXPIRED"
    assert d["not_a_measurement_failure"] is True
    assert d["exit_code"] == 78
    assert d["quantum_seconds"] == 2700
    assert d["failed_step"] == "Run lane cycle"
    assert d["downstream"]["audit_job"] == "skipped"
    assert d["downstream"]["integrate_job"] == "skipped"
    assert d["downstream"]["persist_team_snapshot"] == "success"
    assert d["snapshot"]["commit"] == "afe5506dc8db3e775a544e97eafcdebb4294bc70"


def test_accepted_pointer_is_40265377500_on_both_halves() -> None:
    s = _load("state/evaluation.json")
    assert s["accepted_run_id"] == 40265377500
    assert s["accepted_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    advance = s["accepted_run_id_advance_41161273401"]
    assert advance["from"] == 40258497460
    assert advance["to"] == 40265377500
    assert "PASS" in advance["both_halves_of_requirement_4"]["half_i_audit_gate"]
    assert "accept evaluation cycle 40265377500" in advance["both_halves_of_requirement_4"]["half_ii_accept_commit"]
    gate = _load("results/audit/evaluation/CYCLE_40265377500_GATE.json")
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    upd = s["state_update_41161273401"]
    assert upd["no_key_removed"] is True
    assert upd["no_ref_removed"] is True
    assert upd["accepted_run_id_from"] == 40258497460
    assert upd["accepted_run_id_to"] == 40265377500


def test_multilingual_supplement_passed_and_prior_error_preserved() -> None:
    m = _load("results/evaluation/operational_resume/41161273401_multilingual_supplement.json")
    assert m["status"] == "PASS"
    assert m["n_passed"] == 2
    assert m["n_failed"] == 0
    assert m["n_skipped"] == 0
    assert m["n_unsupported"] == 0
    assert m["product_mount_head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert m["prior_41157741636_status"] == "IMPORT_ERROR"
    assert m["numeric_environment"]["numpy"] is not None
    assert m["test_file_sha256"] == "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"


def test_state_integrity_gate_and_root_lane_parity_pass() -> None:
    g = _load("results/evaluation/orchestration/41161273401_state_integrity_gate.json")
    assert g["verdict"] == "ALL_CHECKS_PASS"
    assert g["exit_code"] == 0
    assert g["n_checks"] == 11
    assert g["n_failed"] == 0
    assert g["failed_checks"] == []
    r = _load("results/evaluation/operational_resume/41161273401.json")
    assert r["state_integrity_gate"]["verdict"] == "ALL_CHECKS_PASS"
    assert r["state_integrity_gate"]["exit_code"] == 0
    root = _load("state/evaluation.json")
    lane = _load("evaluation/state/evaluation.json")
    for field in ("accepted_run_id", "direction_version", "github_run"):
        assert root[field] == lane[field], field
    assert root["state_integrity_gate_41161273401"]["verdict"] == "ALL_CHECKS_PASS"
    assert lane["lane_parity_update_41161273401"]["no_key_removed"] is True
    assert lane["lane_parity_update_41161273401"]["no_ref_removed"] is True


def test_lane_suite_post_check_passed() -> None:
    s = _load("results/evaluation/orchestration/41161273401_lane_suite.json")
    assert s["overall_pass"] is True
    assert s["n_checks"] == 89
    assert s["n_passed"] == 88
    assert s["n_failed"] == 0
    assert s["n_skipped"] == 1
    assert s["failed_checks"] == []
    assert s["skipped_checks"][0]["skipped"] is True
    state = _load("state/evaluation.json")
    assert state["lane_suite_41161273401"]["overall_pass"] is True
    assert state["lane_suite_41161273401"]["n_passed"] == 88


def test_producer_minted_no_audit_gate() -> None:
    assert not (REPO_ROOT / "results/audit/evaluation/CYCLE_41161273401_GATE.json").exists()
    assert not (REPO_ROOT / "reports/audit/evaluation/CYCLE_41161273401.md").exists()
    r = _load("results/evaluation/operational_resume/41161273401.json")
    assert r["controls"]["no_audit_gate_minted"] is True
    assert r["verdict"] == "RESUME_VERIFIED_AUDIT_READY"
    assert r["human_gate_ready"] is False
    assert r["machine_gate_ready"] is False
    assert r["owner_decision_required"] is False
