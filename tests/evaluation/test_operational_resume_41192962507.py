"""Self-check for the 41192962507 operational-resume verification record.

Plain functions only: the producer image has no pytest, so this file is executed
by evaluation.no_pytest_runner. A skip is never a pass.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "41192962507"
PRED_RUN_ID = "41192878248"
SNAPSHOT_COMMIT = "77574ac4f0ddf892874ae79de5dd5f0c19f8fe66"
SNAPSHOT_PARENT = "326f0e53dbad1fed42786039fe983c6f4a746881"
RESULT = ROOT / f"results/evaluation/operational_resume/{RUN_ID}.json"
STATE = ROOT / "state/evaluation.json"
LANE_STATE = ROOT / "evaluation/state/evaluation.json"
REPORT = ROOT / f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
BRIEF = ROOT / f"reports/evaluation/AUDIT_BRIEF_{RUN_ID}.md"
INDEX = ROOT / f"results/evaluation/operational_resume/AUDIT_INDEX_{RUN_ID}.json"


def _r() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_result_schema_and_run_id() -> None:
    r = _r()
    assert r["schema"] == "lex-evaluation-operational-resume-verification/1"
    assert r["run_id"] == int(RUN_ID)
    assert r["resumed_snapshot_run_id"] == int(PRED_RUN_ID)
    assert r["resumed_snapshot_commit"] == SNAPSHOT_COMMIT
    assert r["verdict"] in ("RESUME_VERIFIED_AUDIT_READY", "RESUME_VERIFIED_WITH_DISCLOSED_GAPS")


def test_producer_is_quantum_expiry_not_validation() -> None:
    p = _r()["producer"]
    assert p["failure_class"] == "PRODUCER_WORK_QUANTUM_EXPIRED_rc78"
    assert p["classification"] == "NON_MEASUREMENT_PRODUCER_WORK_QUANTUM_EXPIRY"
    assert p["exit_code"] == 78
    assert p["quantum_seconds_declared"] == 2700
    assert p["quantum_arithmetic"]["duration_within_one_tick_window"] is True
    assert p["failure_is_work_quantum_expiry"] is True
    assert p["failure_is_validation_failure"] is False
    assert p["failure_is_orchestration_not_measurement"] is True
    assert p["failure_mechanism_observed"] is True


def test_producer_skipped_both_gates_and_persisted_new_delta() -> None:
    p = _r()["producer"]
    assert p["producer_validation_ran"] is False
    assert p["producer_write_scope_ran"] is False
    assert p["producer_snapshot_persisted"] is True
    assert p["snapshot_is_new_delta_over_predecessor"] is True
    assert p["snapshot_ref_matches_head"] is True
    assert p["n_snapshot_delta_commits"] == 4
    assert p["n_snapshot_delta_paths"] == 57


def test_snapshot_scope_clean_and_new_delta() -> None:
    s = _r()["snapshot_scope"]
    assert s["verdict"] == "SCOPE_CLEAN"
    assert s["out_of_scope_paths"] == []
    assert s["head_commit"] == SNAPSHOT_COMMIT
    assert s["base_commit"] == SNAPSHOT_PARENT
    assert s["snapshot_ref_matches_head"] is True
    assert s["snapshot_is_new_delta_over_predecessor"] is True


def test_inherited_claims_verified_with_stale_binding_disclosed() -> None:
    c = _r()["claims"]
    assert c["n_failed"] == 0
    assert c["n_checks"] >= 70
    assert c["verdict"].startswith("INHERITED_CLAIMS_REVERIFIED")
    assert c["disclosures"]["prior_claim_binding_stale"] is False
    assert c["disclosures"]["committed_record_sha256"] == _sha(
        ROOT / f"results/evaluation/operational_resume/{PRED_RUN_ID}.json")
    assert c["disclosures"]["committed_claim_primary_sha256"] == c["disclosures"]["prior_claim_pinned_sha256"]


def test_inherited_gate_gap_disclosed() -> None:
    c = _r()["claims"]
    assert c["disclosures"]["inherited_gate_gap"] is True
    assert c["disclosures"]["inherited_freeze_timestamp_defect"][
        "classification"] == "HISTORICAL_TIMESTAMP_DEFECT_NOT_A_MEASUREMENT"


def test_item2_currency_unchanged_and_not_executed() -> None:
    i = _r()["item2"]
    assert i["head_unchanged"] is True
    assert i["adjudicator_unchanged"] is True
    assert i["protocol_executed_this_run"] is False
    assert i["matched_members"] == 14
    assert i["of"] == 15
    assert i["item_2_full_protocol_status"].startswith("NOT_YET")


def test_multilingual_passes_two_of_two() -> None:
    m = _r()["multilingual"]
    assert m["status"] == "PASS"
    assert m["n_passed"] == 2
    assert m["n_failed"] == 0
    assert m["test_file_sha256"] == "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"


def test_accepted_pointer_both_halves() -> None:
    s = json.loads(STATE.read_text(encoding="utf-8"))
    assert s["accepted_run_id"] == 40265377500
    assert s["accepted_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    gate = json.loads((ROOT / "results/audit/evaluation/CYCLE_40265377500_GATE.json").read_text())
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True


def test_benchmark_of_record_pins() -> None:
    b = json.loads((ROOT / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json").read_text())
    assert b["verdict"] == "PRODUCT_FALSIFIED"
    assert b["exit_code"] == 1
    assert b["packets_measured"] == ["39319405429"]
    assert b["n_gates"] == 18
    assert b["n_failed"] == 4
    names = sorted(g["gate"] for g in b["failed_gates"])
    assert names == sorted([
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ])


def test_gates_present_and_green() -> None:
    r = _r()
    assert r["gates"]["state_gate"]["verdict"] == "ALL_CHECKS_PASS"
    assert r["gates"]["lane_suite"]["overall_pass"] is True
    assert r["gates"]["write_scope"]["verdict"] == "SCOPE_CLEAN"
    assert r["gates"]["nested_refs"]["verdict"] == "NESTED_REFS_RESOLVED"
    assert r["self_check"]["verdict"] == "SHIM_PASS"
    assert r["state_gate"]["verdict"] == "ALL_CHECKS_PASS"


def test_no_audit_gate_minted_and_posture_closed() -> None:
    r = _r()
    assert r["posture_flags"] == {
        "accepted_as_evidence": False,
        "audit_gate_minted": False,
        "owner_decision_required": False,
        "product_falsified_this_run": False,
    }
    assert not (ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists()
    assert not (ROOT / f"results/audit/evaluation/CYCLE_{PRED_RUN_ID}_GATE.json").exists()


def test_state_update_additive_and_lane_parity() -> None:
    s = json.loads(STATE.read_text(encoding="utf-8"))
    ls = json.loads(LANE_STATE.read_text(encoding="utf-8"))
    for doc in (s, ls):
        assert doc["operational_resume_41192962507"]["status"] == "AUDIT_READY_PRODUCER_SNAPSHOT"
        assert doc["state_update_41192962507"]["additive_only"] is True
        assert doc["state_update_41192962507"]["no_key_removed"] is True
        assert doc["state_update_41192962507"]["no_ref_removed"] is True
        assert doc["accepted_run_id"] == 40265377500
        assert doc["continue_recommended"] is False
        assert doc["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
        assert doc["evidence_refs_n"] == len(doc["evidence_refs"])
        assert doc["github_run"] == int(RUN_ID)
    assert s["operational_resume_41192962507"]["artifact"] == str(
        Path(f"results/evaluation/operational_resume/{RUN_ID}.json"))
    assert ls["lane_parity_update_41192962507"]["additive_only"] is True


def test_validate_predicate_vacuity_disclosed() -> None:
    v = _r()["validate_replay"]
    assert v["would_pass"] is True
    assert v["exit_code"] == 0
    assert v["vacuity_observation"]["passes_without_state_advance"] is True


def test_report_and_audit_index_exist() -> None:
    assert REPORT.is_file() and REPORT.stat().st_size > 500
    assert BRIEF.is_file() and BRIEF.stat().st_size > 500
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    assert idx["run_id"] == int(RUN_ID)
    assert idx["not_a_measurement"] is True


def test_claim_ceiling_operational() -> None:
    r = _r()
    assert r["not_a_measurement"] is True
    assert "No frozen benchmark" in r["claim_ceiling"]
    assert r["producer"]["claim_ceiling"].startswith("Orchestration diagnosis only")
