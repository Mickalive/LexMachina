"""Self-check for the 41196128050 operational-resume verification record.

Plain functions only: the producer image is not guaranteed to carry pytest, so
this file is executed by evaluation.no_pytest_runner.  A skip is never a pass.

TIMING CONTRACT
---------------
This self-check executes BEFORE the state-integrity gate and before the final
state update.  It therefore asserts only facts that are stable at that point:
the producer diagnosis, snapshot scope, inherited verification, item-(2)
currency, multilingual supplement, accepted pointer, benchmark pins, the
lane/write-scope/nested-ref gates and the posture flags.  It must NOT assert
``state_gate`` or ``self_check`` in the record (both are still null when it
runs); asserting them was the inherited 41192962507 TypeError defect.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "41196128050"
INHERITED_RUN_ID = "41192962507"
SNAPSHOT_COMMIT = "bcd905aa14441bbf36a2e4de4720352d54a7315b"
SNAPSHOT_PARENT = "77574ac4f0ddf892874ae79de5dd5f0c19f8fe66"
RESULT = ROOT / f"results/evaluation/operational_resume/{RUN_ID}.json"
STATE = ROOT / "state/evaluation.json"
LANE_STATE = ROOT / "evaluation/state/evaluation.json"
REPORT = ROOT / f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
BRIEF = ROOT / f"reports/evaluation/AUDIT_BRIEF_{RUN_ID}.md"
INDEX = ROOT / f"results/evaluation/operational_resume/AUDIT_INDEX_{RUN_ID}.json"

BENCHMARK_OF_RECORD_SHA = "fd29a395f8b5307d67abeb79335337250518cc6de171a26ddbf09768840ade73"
MULT_TEST_SHA = "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"
EXPECTED_FAILED_GATES = [
    "mf::concept_coverage::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::fr-bail-entretien",
    "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
]


def _r() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_result_schema_and_identity() -> None:
    r = _r()
    assert r["schema"] == "lex-evaluation-operational-resume-verification/1"
    assert r["run_id"] == int(RUN_ID)
    assert r["dispatch_run_id"] == 41199310309
    assert r["lane"] == "evaluation"
    assert r["direction_version"] == 68
    assert r["resumed_snapshot_run_id"] == int(INHERITED_RUN_ID)
    assert r["resumed_snapshot_commit"] == SNAPSHOT_COMMIT
    assert r["not_a_measurement"] is True


def test_producer_is_quantum_expiry_not_validation() -> None:
    p = _r()["producer"]
    assert p["failure_class"] == "PRODUCER_WORK_QUANTUM_EXPIRED_rc78"
    assert p["classification"] == "NON_MEASUREMENT_PRODUCER_WORK_QUANTUM_EXPIRY"
    assert p["failed_job"] == "team"
    assert p["failed_job_id"] == 124522555422
    assert p["failed_step_name"] == "Run lane cycle"
    assert p["exit_code"] == 78
    assert p["quantum_seconds_declared"] == 2700
    assert p["failed_step_duration_seconds"] == 2704.0
    assert p["quantum_arithmetic"]["duration_within_one_tick_window"] is True
    assert p["failure_is_work_quantum_expiry"] is True
    assert p["failure_is_validation_failure"] is False
    assert p["failure_is_orchestration_not_measurement"] is True
    assert p["failure_mechanism_observed"] is True


def test_producer_skipped_both_gates_and_persisted_new_delta() -> None:
    p = _r()["producer"]
    assert p["producer_validation_ran"] is False
    assert p["producer_write_scope_ran"] is False
    assert p["producer_clean_generated_junk_conclusion"] == "success"
    assert p["producer_snapshot_persisted"] is True
    assert p["snapshot_ref_matches_head"] is True
    assert p["snapshot_is_new_delta_over_predecessor"] is True
    assert p["n_snapshot_delta_commits"] == 1
    assert p["n_snapshot_delta_paths"] == 62


def test_snapshot_scope_clean_and_new_delta() -> None:
    s = _r()["snapshot_scope"]
    assert s["verdict"] == "SCOPE_CLEAN"
    assert s["out_of_scope_paths"] == []
    assert s["head_commit"] == SNAPSHOT_COMMIT
    assert s["base_commit"] == SNAPSHOT_PARENT
    assert s["snapshot_ref_matches_head"] is True
    assert s["snapshot_is_new_delta_over_predecessor"] is True
    assert s["n_paths_changed"] == 62
    assert s["n_commits"] == 1


def test_inherited_deliverable_verified_with_corrections() -> None:
    c = _r()["inherited"]
    assert c["inherited_run_id"] == int(INHERITED_RUN_ID)
    assert c["n_failed"] == 0
    assert c["n_checks"] >= 50
    assert c["verdict"] == "INHERITED_DELIVERABLE_VERIFIED_WITH_CORRECTIONS"
    assert c["corrections"]["historical_record_preserved"] is True
    assert c["corrections"]["snapshot_is_new_delta_over_predecessor"][
        "corrected_value"] is True
    assert c["corrections"]["adjudicator_unchanged"]["corrected_value"] is True
    assert c["dangling_pointer"]["exists"] is False
    assert c["dangling_pointer"]["committed_on_any_ref"] is False
    assert str(c["dangling_pointer"]["actual_artifact_run_id"]) == INHERITED_RUN_ID


def test_item2_currency_gated_not_executed() -> None:
    i = _r()["item2"]
    assert i["head_unchanged"] is True
    assert i["adjudicator_unchanged"] is True
    assert i["protocol_executed_this_run"] is False
    assert i["matched_members"] == 14
    assert i["of"] == 15
    assert i["item_2_full_protocol_status"] == "NOT_YET_DISCRIMINATING_HEAD_UNCHANGED"
    assert i["drift_detected"] is False


def test_multilingual_passes_two_of_two() -> None:
    m = _r()["multilingual"]
    assert m["status"] == "PASS"
    assert m["n_passed"] == 2
    assert m["n_failed"] == 0
    assert m["test_file_sha256"] == MULT_TEST_SHA
    assert m["product_mount_head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"


def test_accepted_pointer_both_halves() -> None:
    c = _r()["inherited"]
    p = c["accepted_pointer"]
    assert p["verified"] is True
    assert p["lab_head"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert p["lab_head_subject"] == "accept evaluation cycle 40265377500"
    assert p["half_1_gate"] == "PASS"
    assert p["half_1_safe_to_integrate"] is True
    assert p["half_1_required_fixes"] == []
    gate = json.loads((ROOT / "results/audit/evaluation/CYCLE_40265377500_GATE.json")
                      .read_text(encoding="utf-8"))
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []


def test_benchmark_of_record_pins() -> None:
    path = ROOT / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json"
    assert _sha(path) == BENCHMARK_OF_RECORD_SHA
    b = json.loads(path.read_text(encoding="utf-8"))
    assert b["verdict"] == "PRODUCT_FALSIFIED"
    assert b["exit_code"] == 1
    assert b["packets_measured"] == ["39319405429"]
    assert b["n_gates"] == 18
    assert b["n_failed"] == 4
    names = sorted(g["gate"] for g in b["failed_gates"])
    assert names == sorted(EXPECTED_FAILED_GATES)


def test_validate_predicate_vacuity_disclosed() -> None:
    v = _r()["validate_replay"]
    assert v["would_pass"] is True
    assert v["exit_code"] == 0
    assert v["vacuity_observation"]["passes_without_state_advance"] is True


def test_pre_state_gate_gates_are_green() -> None:
    """Only the gates that run before the state gate are asserted here."""
    g = _r()["gates"]
    assert g["lane_suite"]["overall_pass"] is True
    assert g["lane_suite"]["n_failed"] == 0
    assert g["write_scope"]["scope_verdict"] == "SCOPE_CLEAN"
    assert g["write_scope"]["scope_clean"] is True
    assert g["nested_refs"]["verdict"] == "NESTED_REFS_RESOLVED"
    assert g["nested_refs"]["n_unresolved"] == 0


def test_no_audit_gate_minted_and_posture_closed() -> None:
    r = _r()
    assert r["posture_flags"] == {
        "accepted_as_evidence": False,
        "audit_gate_minted": False,
        "owner_decision_required": False,
        "product_falsified_this_run": False,
    }
    assert not (ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists()
    assert not (ROOT / f"results/audit/evaluation/CYCLE_{INHERITED_RUN_ID}_GATE.json").exists()


def test_report_and_audit_index_exist() -> None:
    assert REPORT.is_file() and REPORT.stat().st_size > 500
    assert BRIEF.is_file() and BRIEF.stat().st_size > 500
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    assert idx["run_id"] == int(RUN_ID)
    assert idx["not_a_measurement"] is True
    assert idx["lane"] == "evaluation"


def test_claim_ceiling_operational() -> None:
    r = _r()
    assert r["not_a_measurement"] is True
    assert "No frozen benchmark" in r["claim_ceiling"]
    assert r["producer"]["claim_ceiling"].startswith("Orchestration diagnosis only")
    assert r["structural_ok_before_final_gates"] is True
