"""Audit-readiness self-check for the 41187766812 operational-resume snapshot.

Plain functions only (the lane's documented no-pytest shim executes these when
pytest is absent). They read committed/generated JSON artifacts and never import
Product, network, numpy or a frozen benchmark instrument.

They assert exactly the claims this cycle makes:
  * 41184425270's TEAM job succeeded (validate, write scope and persist all
    green) while only its AUDIT job died at 'Independent audit' with exit code
    78 caused by the 2700-second work-quantum guard (FACT from the annotations
    API), with every competing guard class excluded;
  * the producer delta is exactly the six documented paths, all new in the
    parent, all in lane scope, all byte-identically re-homed under the producing
    run's namespace because the originals are misnamed for the resumed run;
  * every load-bearing claim of the persisted reproduction still matches the
    benchmark of record by normalized field comparison (the instrument is NOT
    re-executed);
  * the producer-state validation predicate passed while the resumed run never
    advanced state - the vacuity observation survives this resume;
  * ordered item (2) is still NOT_YET_DISCRIMINATING at the unchanged product
    head and its protocol was not executed (currency check only);
  * the multilingual/provenance suite reads PASS 2/2;
  * the accepted pointer verifies on both halves of requirement 4;
  * no audit gate was minted for the resumed run or for this run, and posture
    stays closed;
  * the state update is additive (no key / no ref removed) and both state files
    stay in parity.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN = "41187766812"
RESUMED = "41184425270"
ARTIFACT_NAMED_RUN_ID = 41180176470
SNAPSHOT_COMMIT = "967a450f0a66cf6a151c87129cb0599ecab36687"
SNAPSHOT_PARENT = "036d6dc8d649a4a967da3c0ee11c5ef866961086"
EXPECTED_PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
EXPECTED_ACCEPTED_RUN = 40265377500
EXPECTED_ACCEPTED_COMMIT = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
MULT_TEST_SHA256 = "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"
BENCHMARK_OF_RECORD_SHA = "fd29a395f8b5307d67abeb79335337250518cc6de171a26ddbf09768840ade73"

PERSISTED = {
    "results/evaluation/minimal_ca_falsify_benchmark/41180176470.json",
    "results/evaluation/minimal_ca_falsify_benchmark/41180176470_engine_mapping_free_recall_falsifier.json",
    "results/evaluation/minimal_ca_falsify_benchmark/test_run.json",
    "results/evaluation/minimal_ca_falsify_benchmark/test_run_engine_mapping_free_recall_falsifier.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_41180176470.md",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_test_run.md",
}

REHOME_DIR = "results/evaluation/operational_resume/41184425270_reexecution"
PRIOR_NESTED_REFS = "results/evaluation/orchestration/41180176470_nested_evidence_refs.json"
PRIOR_INCONSISTENCY = f"results/evaluation/operational_resume/{RUN}_prior_nested_refs_inconsistency.json"
RELOCATED_HISTORICAL_REF = "reports/audit/evaluation/CYCLE_40153908549.md"
RELOCATED_PRESERVED_REF = (
    "results/evaluation/audit_namespace_recovery_40153908549/CYCLE_40153908549.md")
RELOCATED_SHA256 = "cd7698d33b1e4f2c7f042d27f4775198f66250ba7f6f8eb40b9f8658657f7880"

EXPECTED_FAILED_GATES = [
    "mf::concept_coverage::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::fr-bail-entretien",
    "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
]


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def test_audit_death_is_work_quantum_rc78() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_audit_quantum_expiry.json")
    assert d["schema"] == "lex-evaluation-audit-quantum-expiry-diagnosis/1"
    assert d["failed_run_id"] == int(RESUMED)
    assert d["resumed_by_run_id"] == int(RUN)
    assert d["failure_class"] == "AUDIT_WORK_QUANTUM_EXPIRED_rc78"
    assert d["failure_is_orchestration_not_measurement"] is True
    assert d["failure_is_validation_failure"] is False
    assert d["failure_is_zero_delta_guard"] is False
    assert d["failure_is_provider_auth_failure"] is False
    assert d["failed_job"] == "audit"
    assert d["failed_step_name"] == "Independent audit"
    assert d["exit_code"] == 78
    assert d["annotation_quantum_seconds_declared"] == 2700
    assert d["quantum_arithmetic"]["consistent"] is True
    dur = d["failed_step_duration_seconds"]
    assert dur is not None and 2700 <= dur <= 2715
    assert d["verdict_consistent_with_all_evidence"] is True
    assert d["mechanism_attribution"].startswith("FACT")
    assert set(d["chain_quantum_losses"]) >= {"41161273401", "41165748723",
                                              "41174962048", RESUMED}


def test_producer_post_steps_all_succeeded() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_audit_quantum_expiry.json")
    assert d["producer_job_conclusion"] == "success"
    assert d["producer_validation_passed"] is True
    assert d["producer_write_scope_passed"] is True
    assert d["producer_snapshot_persisted"] is True
    assert d["producer_post_steps"]["Validate active MVP producer state"] == "success"
    assert d["producer_post_steps"]["Enforce lane write scope"] == "success"
    assert d["producer_post_steps"]["Persist team snapshot"] == "success"
    assert "Enforce audit scope and read gate" in d["audit_steps_skipped"]
    assert "Persist audit snapshot" in d["audit_steps_skipped"]
    assert d["integrate_job"] == "skipped"


def test_every_competing_guard_class_is_excluded() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_audit_quantum_expiry.json")
    ex = d["guard_exclusion_checks"]
    for key in ("rc64_65_66_agent_registry_prints_error_annotation",
                "rc76_model_health_prints_error_annotation",
                "rc67_zero_delta_requires_head_unchanged",
                "rc75_network_stall",
                "auth_rotation",
                "provider_transient_retry"):
        assert key in ex, key
        assert str(ex[key]).startswith("EXCLUDED"), key


def test_annotations_are_the_primary_evidence() -> None:
    a = _load(f"results/evaluation/orchestration/{RESUMED}_audit_annotations.json")
    msgs = [x.get("message", "") for x in a]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)
    assert any("quantum ended cleanly" in m for m in msgs)


def test_snapshot_delta_is_exactly_six_in_scope_new_paths() -> None:
    s = _load(f"results/evaluation/orchestration/{RUN}_snapshot_scope.json")
    assert s["schema"] == "lex-evaluation-resumed-snapshot-scope/1"
    assert s["run_id"] == int(RUN)
    assert s["resumed_run_id"] == int(RESUMED)
    assert s["base_commit"] == SNAPSHOT_PARENT
    assert s["head_commit"] == SNAPSHOT_COMMIT
    assert s["verdict"] == "SCOPE_CLEAN"
    assert s["out_of_scope_paths"] == []
    assert s["n_paths_changed"] == 6
    assert set(s["changed_paths"]) == PERSISTED
    assert all(line.startswith("A\t") for line in s["name_status"]), s["name_status"]
    assert s["snapshot_ref_intact"] is True
    assert s["snapshot_ref_head"] == SNAPSHOT_COMMIT


def test_persisted_artifacts_are_new_and_byte_identically_rehomed() -> None:
    d = _load("results/evaluation/operational_resume/41184425270_persisted_artifact_disposition.json")
    assert d["schema"] == "lex-evaluation-persisted-artifact-disposition/1"
    assert d["run_id"] == int(RUN)
    assert d["resumed_run_id"] == int(RESUMED)
    assert d["n_paths"] == 6
    assert d["n_new_in_parent"] == 6
    assert d["historical_overwrite"] is False
    assert d["all_rehome_copies_byte_identical"] is True
    assert d["classification"] == "OPERATIONAL_REPRODUCTION_NOT_A_NEW_MEASUREMENT"
    assert d["naming_defect"]["present"] is True
    assert "41180176470" in d["naming_defect"]["detail"]
    assert "41184425270" in d["naming_defect"]["disposition"]
    for entry in d["artifacts"]:
        assert entry["path"] in PERSISTED
        assert entry["existed_in_parent"] is False
        assert entry["append_only_overwrite"] is False
        assert entry["reexecuted_copy_sha256"] == entry["sha256"]
        assert entry["reexecuted_copy"].startswith(REHOME_DIR + "/")
        assert "41184425270" in entry["reexecuted_copy"]
    prov = _load(f"{REHOME_DIR}/PROVENANCE.json")
    assert prov["schema"] == "lex-evaluation-reexecution-rehome-provenance/1"
    assert prov["producing_run_id"] == int(RESUMED)
    assert set(prov["source_to_copy"]) == PERSISTED
    assert "F-3B" in prov["rule"]


def test_validate_predicate_passed_and_the_resumed_run_never_advanced_state() -> None:
    v = _load(f"results/evaluation/orchestration/{RUN}_validate_step_replay.json")
    assert v["workflow_step"] == "Validate active MVP producer state"
    assert v["direction_version_in_state"] == 68
    assert v["cycle_status_in_state"] != "INITIALIZED"
    assert v["would_pass"] is True
    assert v["exit_code"] == 0
    obs = v["vacuity_observation"]
    assert v["github_run_in_state_at_replay"] != int(RESUMED)
    assert v["resumed_run_advanced_state"] is False
    assert v["state_update_block_for_resumed_run_present"] is False
    assert obs["resumed_producer_updated_state"] is False
    assert obs["passes_without_state_advance"] is True
    # and the resumed run's block is still absent from the live state
    s = _load("state/evaluation.json")
    assert f"state_update_{RESUMED}" not in s


def test_persisted_claims_verify_and_measurement_matches_benchmark_of_record() -> None:
    c = _load(f"results/evaluation/operational_resume/{RUN}_claim_verification.json")
    assert c["schema"] == "lex-evaluation-claim-verification/1"
    assert c["run_id"] == int(RUN)
    assert c["verified_run_id"] == int(RESUMED)
    assert c["verdict"] == "PRIOR_CLAIMS_VERIFIED"
    assert c["n_failed"] == 0
    assert c["n_checks"] >= 20
    for chk in c["checks"]:
        assert chk["ok"] is True, chk
    names = {chk["claim"] for chk in c["checks"]}
    for required in ("normalized_identity_vs_benchmark_of_record",
                     "normalized_identity_vs_second_record",
                     "primary_failed_gate_set",
                     "primary_generated_inside_run_window",
                     "disposition_naming_defect_present"):
        assert required in names, required

    primary = _load("results/evaluation/minimal_ca_falsify_benchmark/41180176470.json")
    assert primary["verdict"] == "PRODUCT_FALSIFIED"
    assert primary["exit_code"] == 1
    # named for 41180176470 (the run 41184425270 was resuming), not the producer
    assert primary["run_id"] == str(ARTIFACT_NAMED_RUN_ID)
    assert primary["packets_measured"] == ["39319405429"]
    assert primary["product_mount_head"] == EXPECTED_PRODUCT_MOUNT_HEAD
    assert primary["input_drift"] == []
    assert primary["run_valid"] is True
    assert (primary["n_gates"], primary["n_passed"], primary["n_failed"],
            primary["n_reported"]) == (18, 11, 4, 3)
    assert [g["gate"] for g in primary["failed_gates"]] == EXPECTED_FAILED_GATES
    bor = REPO_ROOT / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json"
    import hashlib
    assert hashlib.sha256(bor.read_bytes()).hexdigest() == BENCHMARK_OF_RECORD_SHA


def test_item2_currency_not_yet_discriminating_and_not_executed() -> None:
    i = _load(f"results/evaluation/operational_resume/{RUN}_item2_currency.json")
    assert i["schema"] == "lex-evaluation-item2-currency/1"
    assert i["run_id"] == int(RUN)
    assert i["head_unchanged"] is True
    assert i["adjudicator_unchanged"] is True
    assert i["product_mount_head_now"] == EXPECTED_PRODUCT_MOUNT_HEAD
    assert i["protocol_executed_this_run"] is False
    assert "NOT_YET_DISCRIMINATING" in i["item_2_full_protocol_status"]
    assert i["matched_members"] == 14 and i["of"] == 15
    assert i["H2_precondition_full_family_regenerated"] is False


def test_multilingual_suite_passes_two_of_two() -> None:
    m = _load(f"results/evaluation/operational_resume/{RUN}_multilingual_supplement.json")
    assert m["status"] == "PASS"
    assert m["n_passed"] == 2
    assert m["n_failed"] == 0
    assert m["n_skipped"] == 0
    assert m["n_unsupported"] == 0
    assert m["test_file_sha256"] == m["test_file_sha256_frozen"] == MULT_TEST_SHA256
    assert m["product_mount_head"] == EXPECTED_PRODUCT_MOUNT_HEAD


def test_accepted_pointer_verified_on_both_halves() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    p = r["accepted_pointer"]
    assert p["verified"] is True
    assert p["expected_accepted_run_id"] == EXPECTED_ACCEPTED_RUN
    assert p["expected_accepted_commit"] == EXPECTED_ACCEPTED_COMMIT
    assert p["lab_head"] == EXPECTED_ACCEPTED_COMMIT
    assert p["lab_head_subject"] == f"accept evaluation cycle {EXPECTED_ACCEPTED_RUN}"
    assert p["half_1_gate"] == "PASS"
    assert p["half_1_safe_to_integrate"] is True
    assert p["half_1_required_fixes"] == []
    assert p["half_2_accept_commit"] == EXPECTED_ACCEPTED_COMMIT
    assert p["reverified_by_run"] == int(RUN)


def test_no_audit_gate_minted_and_posture_closed() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    assert r["controls"]["no_audit_gate_minted"] is True
    assert not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN}_GATE.json").exists()
    assert not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json").exists()
    assert not (REPO_ROOT / f"reports/audit/evaluation/CYCLE_{RUN}.md").exists()
    assert r["human_gate_ready"] is False
    assert r["machine_gate_ready"] is False
    assert r["ready_for_owner_session"] is False
    assert r["owner_decision_required"] is False
    assert r["packet_admitted"] is False
    assert r["no_174k_benchmark_rerun"] is True
    assert r["no_frozen_bar_scored"] is True
    assert r["standing_falsification_not_rerun"] is True


def test_state_update_is_additive_and_lane_parity_holds() -> None:
    s = _load("state/evaluation.json")
    u = s[f"state_update_{RUN}"]
    assert u["additive_only"] is True
    assert u["no_key_removed"] is True
    assert u["no_ref_removed"] is True
    assert u["accepted_run_id_unchanged"] is True
    assert u["proposed_run_id_set_to"] == int(RUN)
    assert u["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    o = s[f"operational_resume_{RUN}"]
    assert o["failure_is_orchestration_not_measurement"] is True
    assert o["failure_is_validation_failure"] is False
    assert o["status"] == "AUDIT_READY_PRODUCER_SNAPSHOT"
    assert o["resumed_snapshot_commit"] == SNAPSHOT_COMMIT
    assert o["protocol_executed_this_run"] is False
    assert s["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert s["cycle_status"] == "COMPLETE"
    assert s["continue_recommended"] is False
    assert s["direction_version"] == 68
    assert s["accepted_run_id"] == EXPECTED_ACCEPTED_RUN
    assert s["accepted_commit"] == EXPECTED_ACCEPTED_COMMIT
    assert s["github_run"] == int(RUN)
    lane = _load("evaluation/state/evaluation.json")
    lu = lane[f"lane_parity_update_{RUN}"]
    assert lu["no_key_removed"] is True
    assert lu["no_ref_removed"] is True
    assert lane["accepted_run_id"] == s["accepted_run_id"]
    assert lane["direction_version"] == 68
    assert lane["github_run"] == int(RUN)
    assert lane["evidence_refs_n"] == len(lane["evidence_refs"])
    assert s["evidence_refs_n"] == len(s["evidence_refs"])


def test_audit_index_scopes_the_current_run_delta() -> None:
    idx = _load(f"results/evaluation/operational_resume/AUDIT_INDEX_{RUN}.json")
    assert idx["schema"] == "lex-evaluation-audit-index/1"
    assert idx["run_id"] == int(RUN)
    assert len(idx["delta_this_run"]) >= 10
    for item in idx["delta_this_run"]:
        assert (REPO_ROOT / item["path"]).exists(), item["path"]
    assert len(idx["fast_fail_checks_for_the_auditor"]) >= 3
    assert idx["do_not_rederive"]
    assert idx["posture_flags"]["human_gate_ready"] is False
    assert idx["posture_flags"]["packet_admitted"] is False


def test_result_record_claim_ceiling_stays_operational() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    assert r["schema"] == "lex-evaluation-operational-resume-verification/7"
    assert r["run_id"] == int(RUN)
    assert r["direction_version"] == 68
    assert r["verdict"] == "RESUME_VERIFIED_AUDIT_READY"
    assert r["exit_code"] == 0
    assert r["packet_of_record_not_scored"] is True
    assert r["standing_falsification_not_rerun"] is True
    assert r["d2_path_scope_probe_not_rerun"] is True
    assert r["no_174k_benchmark_rerun"] is True
    assert r["no_new_thresholds"] is True
    assert "Operational resume and audit-readiness only" in r["claim_ceiling"]
    assert r["resumed_snapshot_commit"] == SNAPSHOT_COMMIT
    assert r["resumed_snapshot_run_id"] == int(RESUMED)
    assert r["prior_deliverable"]["classification"] == \
        "OPERATIONAL_REPRODUCTION_NOT_A_NEW_MEASUREMENT"
    assert r["prior_deliverable"]["naming_defect_disclosed"] is True


def test_relocated_historical_pointer_is_formally_disclosed() -> None:
    import hashlib

    key = "nested_evidence_refs_disclosed_known_unresolvable"
    s = _load("state/evaluation.json")
    entries = [e for e in (s.get(key) or [])
               if isinstance(e, dict) and e.get("path") == RELOCATED_HISTORICAL_REF]
    assert len(entries) == 1
    e = entries[0]
    assert e["disclosed_by_run"] == int(RUN)
    assert e["not_this_cycles_claim"] is True
    assert e["relocated_to"] == RELOCATED_PRESERVED_REF
    assert e["relocated_sha256"] == RELOCATED_SHA256
    assert not (REPO_ROOT / RELOCATED_HISTORICAL_REF).exists()
    preserved = REPO_ROOT / RELOCATED_PRESERVED_REF
    assert preserved.is_file()
    assert hashlib.sha256(preserved.read_bytes()).hexdigest() == RELOCATED_SHA256
    lane = _load("evaluation/state/evaluation.json")
    lane_entries = [x for x in (lane.get(key) or [])
                    if isinstance(x, dict) and x.get("path") == RELOCATED_HISTORICAL_REF]
    assert lane_entries and lane_entries[0]["disclosed_by_run"] == int(RUN)


def test_prior_nested_refs_inconsistency_is_preserved_not_edited() -> None:
    import hashlib

    a = _load(PRIOR_INCONSISTENCY)
    assert a["schema"] == "lex-evaluation-prior-nested-refs-inconsistency/1"
    assert a["prior_declared_n_unresolved"] == 0
    assert a["prior_declared_unresolved_list_len"] == 0
    assert a["prior_counts_unresolved"] >= 2
    assert a["current_guard_recomputed_n_unresolved"] >= 2
    assert a["discrepancy"]["present"] is True
    assert a["discrepancy"]["class"] == "PRIOR_ARTIFACT_SELF_CONTRADICTION"
    assert a["classification"] == "REPORT_ONLY_PRIOR_INSTRUMENT_ARTIFACT_INCONSISTENCY"
    prior = REPO_ROOT / PRIOR_NESTED_REFS
    assert hashlib.sha256(prior.read_bytes()).hexdigest() == a["prior_artifact_sha256"]
    # the prior artifact was NOT rewritten to hide the inconsistency
    p = json.loads(prior.read_text())
    assert p["n_unresolved"] == 0
    assert p["unresolved"] == []
    assert p["resolution_counts"]["UNRESOLVED"] >= 2


def test_nested_refs_resolve_after_formal_disclosure() -> None:
    d = _load(f"results/evaluation/orchestration/{RUN}_nested_evidence_refs.json")
    assert d["verdict"] == "NESTED_REFS_RESOLVED"
    assert d["exit_code"] == 0
    assert d["n_unresolved"] == 0
    assert d["n_top_level_unresolved"] == 0
    assert d["n_disclosure_errors"] == 0
    assert RELOCATED_HISTORICAL_REF in d["disclosed_known_unresolvable"]
