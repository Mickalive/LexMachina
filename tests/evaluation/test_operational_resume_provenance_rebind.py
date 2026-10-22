"""Dedicated suite for the run-39873360672 provenance/state repair.

The repair instrument is executed by the lane cycle before this suite. These
tests are read-only: they assert that the frozen-first artefacts, the preserved
source records, the run-bound rebind records, the lane state contract and the
orchestration diagnosis of run 39872787455 are all internally consistent.
They never re-run the minimal retrieval / counter-authority benchmark.
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

MOD = "evaluation.operational_resume_provenance_rebind_39873360672"


def sha256(path: str) -> str:
    return hashlib.sha256((REPO / path).read_bytes()).hexdigest()


def load(path: str) -> dict:
    return json.loads((REPO / path).read_text())


def test_freeze_first_artefacts_are_pinned():
    hyp = "evaluation/OPERATIONAL_RESUME_39873360672_HYPOTHESIS_V1.json"
    freeze_path = "evaluation/OPERATIONAL_RESUME_39873360672_FREEZE.json"
    freeze = load(freeze_path)
    assert freeze["frozen_before_execution"] is True
    assert freeze["hypothesis_sha256"] == sha256(hyp)
    assert freeze["diagnosis_sha256"] == sha256(freeze["diagnosis_file"])
    assert freeze["run_id_of_record"] == "39873360672"
    assert freeze["resumed_snapshot_run_id"] == "39872787455"


def test_source_records_are_preserved_verbatim():
    freeze = load("evaluation/OPERATIONAL_RESUME_39873360672_FREEZE.json")
    for rel, expected in freeze["source_artifact_pins"].items():
        assert sha256(rel) == expected, rel
    wrapper = load("results/evaluation/minimal_retrieval_ca_benchmark/local_verification.json")
    assert wrapper["run_id"] == "local_verification"  # the preserved D1 defect
    assert wrapper["verdict"] == "PRODUCT_FALSIFIED"
    assert wrapper["n_passed"] == 11 and wrapper["n_failed"] == 4 and wrapper["n_gates"] == 18


def test_rebind_records_self_identify_and_copy_measurement():
    wrapper_src = load("results/evaluation/minimal_retrieval_ca_benchmark/local_verification.json")
    engine_src = load(
        "results/evaluation/minimal_retrieval_ca_benchmark/local_verification_engine_mapping_free_recall_falsifier.json")
    wrapper = load("results/evaluation/minimal_retrieval_ca_benchmark/39873360672.json")
    engine = load(
        "results/evaluation/minimal_retrieval_ca_benchmark/39873360672_engine_mapping_free_recall_falsifier.json")
    for rec in (wrapper, engine):
        assert rec["run_id"] == "39873360672"
        assert rec["provenance_rebind"]["measurement_origin_run_id"] == "39870661520"
        assert rec["provenance_rebind"]["benchmark_reexecuted"] is False
        assert rec["provenance_rebind"]["preserved_verbatim"] is True
    allowed = {"run_id", "generated_at_utc", "engine_record_path"}
    changed = {k for k in wrapper_src if k not in allowed and wrapper.get(k) != wrapper_src[k]}
    assert changed == set()
    changed_e = {k for k in engine_src if k not in {"run_id", "generated_at_utc"} and engine.get(k) != engine_src[k]}
    assert changed_e == set()


def test_duplicate_disclosure_diff_is_exact():
    accepted = load("results/evaluation/minimal_retrieval_ca_benchmark/39854748616.json")
    wrapper = load("results/evaluation/minimal_retrieval_ca_benchmark/local_verification.json")
    diff = {k for k in set(wrapper) | set(accepted) if wrapper.get(k) != accepted.get(k)}
    assert diff == {"run_id", "generated_at_utc", "engine_record_path"}
    accepted_engine = load(
        "results/evaluation/minimal_retrieval_ca_benchmark/39806933576_engine_mapping_free_recall_falsifier.json")
    engine = load(
        "results/evaluation/minimal_retrieval_ca_benchmark/local_verification_engine_mapping_free_recall_falsifier.json")
    diff_e = {k for k in set(engine) | set(accepted_engine) if engine.get(k) != accepted_engine.get(k)}
    assert diff_e == {"run_id", "generated_at_utc", "product_mount_head"}


def test_state_contract_is_audit_ready():
    state = load("state/evaluation.json")
    assert state["direction_version"] == 63
    assert state["cycle_status"] == "COMPLETE"
    assert state["proposed_run_id"] == "39873360672"
    assert state["github_run"] == 39873360672
    assert state["accepted_run_id"] == "39866970583"
    assert state["acceptance_status"] == "PROPOSED_PENDING_INDEPENDENT_AUDIT"
    assert state["continue_recommended"] is False
    assert state["human_gate_ready"] is False and state["machine_gate_ready"] is False
    assert state["evidence_refs_n"] == len(state["evidence_refs"])
    assert all((REPO / r).exists() for r in state["evidence_refs"])
    assert "39854748616" in state["next_recommendation"]
    assert "NOT FIRED" in state["next_recommendation"]
    block = state["operational_resume_39873360672"]
    assert block["diagnosed_run"] == "39872787455"
    assert block["benchmark_reexecuted"] is False


def test_orchestration_diagnosis_is_structured_and_hedged():
    diag = load("results/evaluation/orchestration/39872787455_diagnosis.json")
    assert diag["run_id"] == 39872787455
    assert diag["conclusion"] == "failure"
    team = diag["rest_job_facts"]["team"]
    assert team["failed_step"]["name"] == "Run lane cycle"
    assert "Validate active MVP producer state" in {s["name"] for s in team["skipped_steps"]}
    assert diag["rest_job_facts"]["audit"]["conclusion"] == "skipped"
    assert diag["rest_job_facts"]["resilience"]["conclusion"] == "success"
    assert diag["snapshot_facts_measured_via_git"]["byte_identical_to_rejected_snapshot"] is True
    assert "INFERENCE" in json.dumps(diag)
    assert "403" in json.dumps(diag["provenance"])
    assert diag["remediation_in_this_cycle"]["benchmark_reexecuted"] is False


def test_cycle_record_reports_no_benchmark_reexecution():
    rec = load("results/evaluation/operational_resume/39873360672.json")
    assert rec["run_id"] == "39873360672"
    assert rec["benchmark_reexecuted"] is False
    assert rec["network_calls"] == []
    assert rec["verdict"] == "REPAIR_VERIFIED_AUDIT_READY"
    assert all(g["pass"] for g in rec["gates"])
    assert all(c["holds"] for c in rec["controls"])
    assert len(rec["gates"]) == 9
    assert len(rec["controls"]) == 5
