"""Audit-readiness self-check for the 41171918973 operational-resume snapshot.

Plain functions only (the lane's documented no-pytest shim executes these when
pytest is absent). They read committed JSON artifacts and never import Product,
network, numpy or a frozen benchmark instrument.

They assert exactly the claims this cycle makes:
  * 41171827286's producer died at 'Run lane cycle' (exit 1, ~16 s) with every
    wrapper guard class excluded and a zero-delta snapshot;
  * 41165748723's independent audit job was killed by the 2700-second work-quantum
    guard (exit 78) — the second occurrence in this chain;
  * the persisted 41165748723 deliverable replays to a normalized-identical
    claim-bearing payload and the committed bytes are unchanged since freeze;
  * ordered item (2) is still NOT_YET_DISCRIMINATING at the unchanged product
    head (14/15) and its protocol was not executed (currency check only);
  * the multilingual/provenance suite reads PASS 2/2 under the accepted numeric
    environment;
  * the accepted pointer 40265377500 verifies on both halves;
  * the failed run's snapshot added ZERO paths (git-object identity);
  * the producer minted no audit gate for its own run and posture stays closed;
  * the state update is additive (no key / no ref removed).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN = "41171918973"
RESUMED = "41171827286"
PRIOR_PRODUCER = "41165748723"
SNAPSHOT_COMMIT = "6d73946d279032d8d10c82f6dfa21793595c3887"


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def test_producer_death_is_exit1_without_transient_signature() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_producer_exit1.json")
    assert d["schema"] == "lex-evaluation-producer-death-diagnosis/1"
    assert d["failed_run_id"] == int(RESUMED)
    assert d["failure_class"] == "PRODUCER_SESSION_DIED_EXIT_1_WITHOUT_TRANSIENT_SIGNATURE"
    assert d["failure_is_orchestration_not_measurement"] is True
    assert d["failure_is_validation_failure"] is False
    assert d["failure_is_zero_delta_guard"] is False
    assert d["failure_is_quantum_expiry"] is False
    assert d["failed_job"] == "team"
    assert d["failed_step_number"] == 6
    assert d["exit_code"] == 1
    # ~16 s: far below any quantum and far below any timeout class
    assert d["failed_step_duration_seconds"] is not None
    assert 0 < d["failed_step_duration_seconds"] < 600
    assert d["verdict_consistent_with_all_evidence"] is True
    assert d["mechanism_attribution"].startswith("INFERENCE")


def test_every_wrapper_guard_class_is_excluded() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_producer_exit1.json")
    ex = d["guard_exclusion_checks"]
    assert ex["rc_64_65_66_registry_guard_excluded"] is True
    assert ex["rc_76_model_health_guard_excluded"] is True
    assert ex["rc_67_zero_delta_guard_excluded"] is True
    assert ex["rc_78_quantum_expiry_excluded"] is True
    assert ex["wrapper_error_annotations_absent"] is True
    assert all(ex.values())
    # downstream steps: validate/scope skipped, persist still succeeded,
    # audit+integrate skipped — the zero-delta snapshot pattern
    assert d["downstream"]["validate_active_mvp_producer_state"] == "skipped"
    assert d["downstream"]["enforce_lane_write_scope"] == "skipped"
    assert d["downstream"]["persist_team_snapshot"] == "success"
    assert d["downstream"]["audit_job"] == "skipped"
    assert d["downstream"]["integrate_job"] == "skipped"


def test_zero_delta_snapshot_proof_both_refs_identical() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_producer_exit1.json")
    z = d["zero_delta_proof"]
    assert z["identical"] is True
    assert z["team_ref_41171827286"] == SNAPSHOT_COMMIT
    assert z["team_ref_41165748723"] == SNAPSHOT_COMMIT


def test_audit_quantum_expiry_is_second_occurrence_exit_78() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{PRIOR_PRODUCER}_audit_quantum_expiry.json")
    assert d["schema"] == "lex-evaluation-orchestration-resume-diagnosis/1"
    assert d["failure_class"] == "WORK_QUANTUM_EXPIRED"
    assert d["not_a_measurement_failure"] is True
    assert d["exit_code"] == 78
    assert d["quantum_seconds"] == 2700
    assert d["failed_run_id"] == int(PRIOR_PRODUCER)
    occ = d["second_occurrence_in_chain"]
    assert "41161273401" in occ["first"]
    assert PRIOR_PRODUCER in occ["second"]
    assert "two consecutive" in occ["pattern"]


def test_persisted_deliverable_replays_claim_payload_identically() -> None:
    rep = _load(f"results/evaluation/operational_resume/{RUN}_replay_of_{PRIOR_PRODUCER}.json")
    assert rep["schema"] == "lex-evaluation-operational-resume/2"
    assert rep["replayed_run_id"] == int(PRIOR_PRODUCER)
    assert rep["normalized_equal"] is True
    assert rep["diff_paths"] == []
    assert rep["committed_result_sha256_frozen"] == \
        "fa555a897e36018fa9f596e5910c9d1dd091b8b103ea7f5311b2d2f72fa52d22"
    assert rep["committed_bytes_unchanged_since_freeze"] is True
    assert rep["committed_result_sha256_now"] == rep["committed_result_sha256_frozen"]
    # full diff is published, never silently dropped
    assert rep.get("full_diff_paths")
    assert any(p.endswith("_at_utc") for p in rep["full_diff_paths"])
    for path in rep["excluded_volatile_paths"]:
        assert path in rep["full_diff_paths"]
    chain = rep["prior_chain_still_verifies_in_reexecution"]
    assert chain["audit_failure_all_checks_pass"] is True
    assert chain["accepted_pointer_verified"] is True
    assert chain["item2_status"].startswith("NOT_YET_DISCRIMINATING")


def test_numeric_environment_matches_accepted_reference() -> None:
    rep = _load(f"results/evaluation/operational_resume/{RUN}_replay_of_{PRIOR_PRODUCER}.json")
    env = rep["numeric_environment"]
    assert env["numpy"] == "2.5.4"
    assert env["scipy"] == "1.18.1"
    assert env["scikit_learn"] == "1.9.1"
    assert "accepted" in env["accepted_environment_reference"]


def test_item2_currency_check_only_protocol_not_executed() -> None:
    i = _load(f"results/evaluation/operational_resume/{RUN}_item2_currency.json")
    assert i["schema"] == "lex-evaluation-item2-currency/1"
    assert i["run_id"] == int(RUN)
    assert i["head_unchanged"] is True
    assert i["adjudicator_unchanged"] is True
    assert i["product_mount_head_now"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert i["product_mount_head_now"] == i["product_mount_head_expected"]
    assert i["product_mount_head_now"] == i["product_mount_head_in_prior_record"]
    assert i["protocol_executed_this_run"] is False
    assert i["H1_precondition_leg_landed"] is True
    assert i["H2_precondition_full_family_regenerated"] is False
    assert i["matched_members"] == 14
    assert i["of"] == 15
    assert i["item_2_full_protocol_status"].startswith("NOT_YET_DISCRIMINATING")


def test_multilingual_suite_passes_2_of_2_at_expected_head() -> None:
    m = _load(f"results/evaluation/operational_resume/{RUN}_multilingual_supplement.json")
    assert m["status"] == "PASS"
    assert m["n_passed"] == 2
    assert m["product_mount_head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert m["test_file_sha256"] == m["test_file_sha256_frozen"] == \
        "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be"
    env = m["numeric_environment"]
    assert env["numpy"] and env["scipy"] and env["scikit_learn"]


def test_accepted_pointer_is_40265377500_on_both_halves() -> None:
    p = _load(f"results/evaluation/operational_resume/{RUN}.json")["accepted_pointer"]
    assert p["verified"] is True
    assert p["expected_accepted_run_id"] == 40265377500
    assert p["expected_accepted_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert p["lab_head"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert p["half_1_gate"] == "PASS"
    assert p["half_1_safe_to_integrate"] is True
    assert p["half_1_required_fixes"] == []
    assert p["half_2_accept_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert p["reverified_by_run"] == int(RUN)
    s = _load("state/evaluation.json")
    assert s["accepted_run_id"] == 40265377500
    assert s["accepted_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert s["proposed_run_id"] == int(RUN)
    assert s["github_run"] == int(RUN)


def test_failed_run_snapshot_scope_is_zero_delta() -> None:
    w = _load(f"results/evaluation/orchestration/{RUN}_snapshot_write_scope_repro.json")
    assert w["resumed_run_id"] == int(RESUMED)
    assert w["snapshot_commit"] == SNAPSHOT_COMMIT
    assert w["mode"] == "tree-identity (zero-delta proof)"
    assert w["verdict"] == "SCOPE_CLEAN_ZERO_DELTA"
    assert w["added_paths"] == []
    assert w["n_added_paths"] == 0


def test_result_verdict_is_audit_ready_with_all_controls_true() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    assert r["verdict"] == "RESUME_VERIFIED_AUDIT_READY"
    assert r["exit_code"] == 0
    assert r["direction_version"] == 68
    assert r["resumed_snapshot_run_id"] == int(RESUMED)
    assert r["resumed_snapshot_commit"] == SNAPSHOT_COMMIT
    for key, val in r["controls"].items():
        assert val is True, f"control {key} is not True"
    assert r["no_frozen_bar_scored"] is True
    assert r["no_174k_benchmark_rerun"] is True
    assert r["packet_admitted"] is False
    assert r["machine_gate_ready"] is False
    assert r["human_gate_ready"] is False
    assert r["ready_for_owner_session"] is False
    assert r["owner_decision_required"] is False
    assert "NOT_YET_DISCRIMINATING" in r["ordered_work_status"]["item_2_conditional_remeasure"]
    assert "PRODUCT_FALSIFIED" in r["ordered_work_status"]["item_3_standing_falsification_record"]
    assert r["ordered_work_status"]["item_5_no_zero_delta_rederivation"].startswith("HONOURED")


def test_no_audit_gate_minted_and_posture_closed() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    assert r["controls"]["no_audit_gate_minted"] is True
    assert not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN}_GATE.json").exists()
    assert not (REPO_ROOT / f"reports/audit/evaluation/CYCLE_{RUN}.md").exists()


def test_state_update_is_additive() -> None:
    s = _load("state/evaluation.json")
    u = s[f"state_update_{RUN}"]
    assert u["additive_only"] is True
    assert u["no_key_removed"] is True
    assert u["no_ref_removed"] is True
    assert u["accepted_run_id_unchanged"] == 40265377500
    assert u["proposed_run_id_set_to"] == int(RUN)
    assert u["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert s[f"operational_resume_{RUN}"]["prior_result_reproduced_in_reexecution"] is True
    assert s[f"operational_resume_{RUN}"]["failure_is_orchestration_not_measurement"] is True
    assert s["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert s["cycle_status"] == "COMPLETE"
    assert s["continue_recommended"] is False
    lane = _load("evaluation/state/evaluation.json")
    lu = lane[f"lane_parity_update_{RUN}"]
    assert lu["no_key_removed"] is True
    assert lu["no_ref_removed"] is True
    assert lane["accepted_run_id"] == s["accepted_run_id"]
    assert lane["direction_version"] == 68
    assert lane["github_run"] == int(RUN)


def test_snapshot_scope_embedded_in_result() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    # snapshot_scope is computed before self_check runs; the other audit-readiness
    # instruments (state_gate / nested_refs / lane_suite / write_scope / self_check)
    # are only attached to the result AFTER this self-check finishes, so they are
    # deliberately not asserted here.
    assert r["snapshot_scope"]["verdict"] == "SCOPE_CLEAN_ZERO_DELTA"
    assert r["snapshot_scope"]["added_paths"] == []
