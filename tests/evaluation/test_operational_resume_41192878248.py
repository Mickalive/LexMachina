"""Plain-function self-checks for evaluation run 41192878248 (no pytest needed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "41192878248"
PRED_RUN_ID = "41187766812"
SNAPSHOT = "326f0e53dbad1fed42786039fe983c6f4a746881"
RESULT = REPO_ROOT / f"results/evaluation/operational_resume/{RUN_ID}.json"
CLAIMS = REPO_ROOT / f"results/evaluation/operational_resume/{RUN_ID}_claim_verification.json"
SCOPE = REPO_ROOT / f"results/evaluation/orchestration/{RUN_ID}_snapshot_scope.json"
PRODUCER = REPO_ROOT / f"results/evaluation/orchestration/CYCLE_{RUN_ID}_producer_start_failure.json"
PRED = REPO_ROOT / f"results/evaluation/orchestration/CYCLE_{PRED_RUN_ID}_audit_quantum_expiry.json"
ITEM2 = REPO_ROOT / f"results/evaluation/operational_resume/{RUN_ID}_item2_currency.json"
MULT = REPO_ROOT / f"results/evaluation/operational_resume/{RUN_ID}_multilingual_supplement.json"
PRIOR_INCONSISTENCY = REPO_ROOT / f"results/evaluation/operational_resume/{PRED_RUN_ID}_prior_nested_refs_inconsistency.json"
STATE = REPO_ROOT / "state/evaluation.json"
LANE_STATE = REPO_ROOT / "evaluation/state/evaluation.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_producer_is_non_measurement_failure():
    r = _load(PRODUCER)
    assert r["failure_class"] == "PRODUCER_LANE_CYCLE_EXIT1_BEFORE_GATES"
    assert r["exit_code"] == 1
    assert r["classification"] == "NON_MEASUREMENT_PRODUCER_START_FAILURE"
    assert r["zero_delta"] is True
    assert r["failed_step_duration_seconds"] <= 60


def test_current_producer_skipped_both_gates_and_mechanism_unobserved():
    r = _load(PRODUCER)
    assert r["producer_validation_ran"] is False
    assert r["producer_write_scope_ran"] is False
    assert r["producer_snapshot_persisted"] is True
    assert r["mechanism_evidence_available"] is False
    assert "UNOBSERVED" in r["mechanism_attribution"]
    assert r["failure_is_validation_failure"] is False
    assert r["failure_is_work_quantum_expiry"] is False


def test_persisted_ref_is_unchanged_predecessor_not_new_delta():
    r = _load(PRODUCER)
    assert r["snapshot_ref_head"] == SNAPSHOT
    assert r["predecessor_snapshot_ref_head"] == SNAPSHOT
    assert r["snapshot_is_predecessor_not_new_delta"] is True
    assert r["delta_commits"] == []


def test_predecessor_audit_is_rc78_quantum_not_validation():
    r = _load(PRED)
    assert r["failure_class"] == "AUDIT_WORK_QUANTUM_EXPIRED_rc78"
    assert r["exit_code"] == 78
    assert r["annotation_quantum_seconds_declared"] == 2700
    assert r["producer_job_conclusion"] == "success"
    assert r["producer_validation_passed"] is True
    assert r["producer_write_scope_passed"] is True
    assert r["quantum_arithmetic"]["consistent"] is True
    assert "Enforce audit scope and read gate" in r["audit_steps_skipped"]
    assert r["integrate_job"] == "skipped"


def test_snapshot_scope_clean_and_both_refs():
    s = _load(SCOPE)
    assert s["verdict"] == "SCOPE_CLEAN"
    assert s["out_of_scope_paths"] == []
    assert s["same_commit_on_both_cycle_refs"] is True
    assert s["head_commit"] == SNAPSHOT
    assert s["base_commit"] == "967a450f0a66cf6a151c87129cb0599ecab36687"
    assert s["n_paths_changed"] >= 30


def test_inherited_claims_verified():
    c = _load(CLAIMS)
    assert c["verdict"] == "PRIOR_CLAIMS_VERIFIED"
    assert c["n_failed"] == 0
    assert c["n_checks"] >= 50


def test_item2_currency_unchanged_and_not_executed():
    i = _load(ITEM2)
    assert i["head_unchanged"] is True
    assert i["adjudicator_unchanged"] is True
    assert i["protocol_executed_this_run"] is False
    assert i["matched_members"] == 14 and i["of"] == 15
    assert str(i["item_2_full_protocol_status"]).startswith("NOT_YET_DISCRIMINATING")


def test_multilingual_passes_two_of_two():
    m = _load(MULT)
    assert m["status"] == "PASS"
    assert m["n_passed"] == 2
    assert m["test_file_sha256"] == "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"
    assert m["product_mount_head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def test_accepted_pointer_both_halves():
    r = _load(RESULT)
    p = r["accepted_pointer"]
    assert p["verified"] is True
    assert p["lab_head"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert p["half_1_gate"] == "PASS"


def test_no_audit_gate_minted_and_posture_closed():
    assert not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists()
    assert not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{PRED_RUN_ID}_GATE.json").exists()
    r = _load(RESULT)
    assert r["controls"]["no_audit_gate_minted"] is True
    for key in ("packet_admitted", "machine_gate_ready", "human_gate_ready",
                "ready_for_owner_session", "owner_decision_required",
                "continue_recommended"):
        assert r[key] is False


def test_state_update_additive_and_lane_parity():
    state = _load(STATE)
    lane = _load(LANE_STATE)
    assert state["accepted_run_id"] == lane["accepted_run_id"] == 40265377500
    assert state["direction_version"] == lane["direction_version"] == 68
    assert state[f"operational_resume_{RUN_ID}"]["failure_class"] == "PRODUCER_LANE_CYCLE_EXIT1_BEFORE_GATES"
    assert state["evidence_refs_n"] == len(state["evidence_refs"])
    assert lane["evidence_refs_n"] == len(lane["evidence_refs"])
    assert state[f"state_update_{RUN_ID}"]["no_key_removed"] is True
    assert state[f"state_update_{RUN_ID}"]["no_ref_removed"] is True


def test_result_claim_ceiling_operational():
    r = _load(RESULT)
    assert r["no_frozen_bar_scored"] is True
    assert r["packet_of_record_not_scored"] is True
    assert r["standing_falsification_not_rerun"] is True
    assert r["no_174k_benchmark_rerun"] is True
    assert "Operational resume and audit-readiness only" in r["claim_ceiling"]


def test_validate_predicate_passed_vacuously():
    v = _load(REPO_ROOT / "results/evaluation/orchestration/41187766812_validate_step_replay.json")
    assert v["would_pass"] is True
    assert v["vacuity_observation"]["passes_without_state_advance"] is True


def test_prior_inconsistency_and_benchmark_pins():
    inc = _load(PRIOR_INCONSISTENCY)
    assert inc["discrepancy"]["present"] is True
    assert inc["classification"] == "REPORT_ONLY_PRIOR_INSTRUMENT_ARTIFACT_INCONSISTENCY"
    bench = _load(REPO_ROOT / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json")
    assert bench["verdict"] == "PRODUCT_FALSIFIED"
    assert bench["packets_measured"] == ["39319405429"]
