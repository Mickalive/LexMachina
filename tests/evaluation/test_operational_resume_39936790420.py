"""Tests for the operational-resume verification of snapshot 39929883261.

These tests pin the committed *outputs* of the frozen instrument, not a live
re-execution: the claim-bearing re-open measurement is executed once by the
instrument, and the tests re-hash/parse the committed records.  A control that
only re-ran the instrument would overwrite the very records under test.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "39936790420"
RESUMED = "39929883261"
ACCEPTED_BASE = "3eeced9a25d486356870755e48422f8473a5f90c"
SNAPSHOT = "5cc6a326cdc77b821f73f7819acb6bd3b3303a1e"
PRODUCT_HEAD = "d22f9b633c9bce70258915579f5da5195f6b2f53"
PACKET = "39319405429"


def _load(rel: str):
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def _sha(rel: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()


def test_freeze_first_digests_still_match():
    freeze = _load("evaluation/OPERATIONAL_RESUME_39936790420_FREEZE_V2.json")
    assert freeze["hypothesis_sha256"] == _sha(
        "evaluation/OPERATIONAL_RESUME_39936790420_HYPOTHESIS_V2.json")
    assert freeze["diagnosis_sha256"] == _sha(
        "evaluation/snapshot_audit/orchestration_diagnosis_39936790420.json")
    assert freeze["rest_capture_sha256"] == _sha(
        "results/evaluation/orchestration/39936790420_rest_job_capture.json")
    assert freeze["instrument_sha256"] == _sha(
        "evaluation/operational_resume_39936790420.py")
    assert freeze["true_accepted_base"] == ACCEPTED_BASE
    assert freeze["snapshot_commit"] == SNAPSHOT


def test_resume_result_is_verified_and_all_gates_pass():
    res = _load("results/evaluation/operational_resume/39936790420.json")
    assert res["run_id"] == RUN_ID
    assert res["verdict"] == "RESUME_VERIFIED_AND_AUDIT_READY"
    assert res["exit_code"] == 0
    assert res["frozen_before_execution"] is True
    assert [g["name"] for g in res["gates"]] == [
        "R1_producer_snapshot_preserved_and_in_scope",
        "R2_orchestration_diagnosis_structured",
        "R3_frozen_and_accepted_pins_hold",
        "R4_lineage_byte_identity_and_claim_integrity",
        "R5_shim_reproduction_and_inherited_red_isolated",
        "R6_product_advance_resolved_by_frozen_reopen_measurement",
        "R7_state_and_evidence_refs_reconciled",
    ]
    assert all(g["pass"] for g in res["gates"])
    assert all(c["holds"] for c in res["controls"])


def test_snapshot_artifacts_are_preserved_byte_exact():
    pins = {
        "results/evaluation/minimal_retrieval_ca_benchmark/39929883261.json":
            "202ffeb5d653a34ee703358fc3b68d9914f9b37a5559b2bac18e06a63f31d416",
        "results/evaluation/minimal_retrieval_ca_benchmark/"
        "39929883261_engine_mapping_free_recall_falsifier.json":
            "373e77974c191477eff267d4fefb5f076e57aada69291a40ad340653258f9ef6",
        "results/evaluation/minimal_retrieval_ca_benchmark/"
        "39929883261_LINEAGE_DISCLOSURE.json":
            "04b72edecfbd98f13a0f515f14b30d5f473490050df1216afe7530d5aa4a38b7",
        "reports/evaluation/RETRIEVAL_CA_BENCHMARK_39929883261.md":
            "6572fd8300b8589b48c3396aa99bc92102a8a516784d1340f76cfc58aa17d931",
        "results/evaluation/orchestration/"
        "39929883261_multiling_prov_benchmark_pytest_shim.json":
            "643f1e0891cd8876361de057879b970a28ebeefe2566b401ce4e00b9ac491e77",
    }
    for rel, expected in pins.items():
        assert _sha(rel) == expected, rel


def test_accepted_records_are_not_overwritten():
    assert _sha("results/evaluation/minimal_retrieval_ca_benchmark/39927760701.json") == (
        "60d35b95bfe70c98784b136833495adf4b8036fea283e1f310419cfc6ab047b1")
    assert _sha(
        "results/evaluation/mapping_free_recall_falsifier/"
        "39927760701_engine_mapping_free_recall_falsifier.json") == (
        "06d73f9f0a1dec42de18fcdd687f4c170a75b5218ce16193de173bf261715f0c")


def test_frozen_bars_and_pins_are_unchanged():
    assert _sha("evaluation/frozen_bars/RULES_LABEL.json") == (
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608")
    assert _sha("evaluation/frozen_bars/RULES_GEOMETRY.json") == (
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633")
    assert _sha("evaluation/frozen_bars/VERDICT_CONTRACT.json") == (
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c")
    assert _sha("evaluation/retrieval_gate/frozen_retrieval_benchmark.json") == (
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72")


def test_diagnosis_carries_the_cancel_and_product_advance_facts():
    diag = _load("evaluation/snapshot_audit/orchestration_diagnosis_39936790420.json")
    steps = {s["number"]: s["conclusion"]
             for s in diag["team_job_steps_measured_via_rest_api"]}
    assert steps[6] == "cancelled"
    assert steps[7] == "skipped"
    assert steps[9] == "skipped"
    assert steps[10] == "success"
    assert diag["cancel_attribution"]["stale_threshold_seconds"] == 3300
    assert diag["cancel_attribution"]["measured_age_seconds"] == 3402
    assert diag["persisted_tree_facts_measured_via_git"]["remote_audit_branch_for_prior_run"] is None
    assert diag["persisted_tree_facts_measured_via_git"]["remote_lab_evaluation_head"] == SNAPSHOT
    adv = diag["product_advance_during_producer_run"]
    assert adv["accepted_product_commit"] == PRODUCT_HEAD
    assert adv["accepted_at"] == "2026-10-23T09:46:52Z"
    assert adv["packet_bytes_unchanged"] is True


def test_reopen_measurement_is_valid_and_on_the_new_accepted_head():
    rec = _load("results/evaluation/minimal_retrieval_ca_benchmark/39936790420.json")
    assert rec["run_id"] == RUN_ID
    assert rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["exit_code"] == 1
    assert rec["product_mount_head"] == PRODUCT_HEAD
    assert rec["packets_measured"] == [PACKET]
    assert rec["input_drift"] == []
    assert rec["non_vacuity"]["all_hold"] is True
    failed = {g["gate"] for g in rec["failed_gates"]}
    assert failed == {
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    }


def test_shim_reproduces_the_snapshot_counts():
    rec = _load("results/evaluation/orchestration/"
                "39936790420_multiling_prov_benchmark_pytest_shim.json")
    assert (rec["n_passed"], rec["n_failed"], rec["n_unsupported"]) == (88, 2, 6)
    per = {r["test_file"]: (r["n_passed"], r["n_failed"], r["n_unsupported"])
           for r in rec["results"]}
    assert per == {
        "tests/evaluation/test_minimal_retrieval_ca_benchmark.py": (21, 0, 0),
        "tests/evaluation/test_mapping_free_recall_falsifier.py": (22, 0, 2),
        "tests/evaluation/test_stand_ready_multilingual_probe.py": (16, 0, 0),
        "tests/evaluation/test_mount_provenance_gate.py": (8, 1, 4),
        "tests/evaluation/test_repair_39338699604_provenance.py": (21, 7, 0),
    }


def test_inherited_red_is_confirmed_at_the_true_accepted_base():
    red = _load("results/evaluation/orchestration/"
                "39936790420_inherited_red_3eeced9a.json")
    assert red["base"] == ACCEPTED_BASE
    assert red["verdict"] == "INHERITED_RED_CONFIRMED"
    for tf in ("tests/evaluation/test_mount_provenance_gate.py",
               "tests/evaluation/test_repair_39338699604_provenance.py"):
        assert red["snapshot_failed_cases"][tf] == red["tip_failed_cases"][tf]
        assert red["tip_failed_cases"][tf]


def test_state_reconciles_and_refs_resolve():
    state = _load("state/evaluation.json")
    assert state["direction_version"] == 63
    assert str(state["github_run"]) == RUN_ID
    assert str(state["proposed_run_id"]) == RUN_ID
    assert state["accepted_run_id"] == "39927760701"
    assert state["cycle_status"] == "COMPLETE"
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert state.get(flag) is not True
    assert state["product_advance_after_snapshot_measurement"][
        "accepted_product_commit"] == PRODUCT_HEAD
    assert state["minimal_retrieval_ca_benchmark"]["run_id"] == RUN_ID
    assert state["minimal_retrieval_ca_benchmark"]["product_mount_head"] == PRODUCT_HEAD
    refs = state["evidence_refs"]
    assert state["evidence_refs_n"] == len(refs)
    missing = [r for r in refs
               if not (REPO_ROOT / r.split(" ")[0].rstrip(",").replace(",", "")).exists()]
    assert not missing, missing


def test_lab_promotion_anomaly_is_disclosed_not_trusted():
    state = _load("state/evaluation.json")
    block = state[f"operational_resume_{RUN_ID}"]
    assert block["true_accepted_base"] == ACCEPTED_BASE
    assert "lab/evaluation == 5cc6a326" in block["lab_anomaly"]
    assert "no audit branch" in block["lab_anomaly"]
