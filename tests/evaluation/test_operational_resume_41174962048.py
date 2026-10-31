"""Audit-readiness self-check for the 41174962048 operational-resume snapshot.

Plain functions only (the lane's documented no-pytest shim executes these when
pytest is absent). They read committed JSON artifacts and never import Product,
network, numpy or a frozen benchmark instrument.

They assert exactly the claims this cycle makes:
  * 41171918973 died at 'Run lane cycle' with exit code 78 caused by the
    2700-second work-quantum guard (FACT from the annotations API), with every
    competing guard class excluded;
  * the two workflow steps skipped by that death — write scope and producer-state
    validation — now pass when replayed over the committed snapshot;
  * every load-bearing claim of the persisted 41171918973 record still matches
    its primary committed artifact;
  * ordered item (2) is still NOT_YET_DISCRIMINATING at the unchanged product
    head and its protocol was not executed (currency check only);
  * the multilingual/provenance suite reads PASS 2/2;
  * the accepted pointer verifies on both halves of requirement 4;
  * the producer minted no audit gate for its own run and posture stays closed;
  * the state update is additive (no key / no ref removed).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN = "41174962048"
RESUMED = "41171918973"
SNAPSHOT_COMMIT = "1580bf9e30a3cd49712dd4b7cc35dfd29a1b2aa8"


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def test_producer_death_is_work_quantum_rc78() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_producer_quantum_expiry.json")
    assert d["schema"] == "lex-evaluation-producer-quantum-expiry-diagnosis/1"
    assert d["failed_run_id"] == int(RESUMED)
    assert d["resumed_by_run_id"] == int(RUN)
    assert d["failure_class"] == "PRODUCER_WORK_QUANTUM_EXPIRED_rc78"
    assert d["failure_is_orchestration_not_measurement"] is True
    assert d["failure_is_validation_failure"] is False
    assert d["failure_is_zero_delta_guard"] is False
    assert d["failure_is_provider_auth_failure"] is False
    assert d["failed_step_number"] == 6
    assert d["exit_code"] == 78
    assert d["annotation_quantum_seconds_declared"] == 2700
    assert d["quantum_arithmetic"]["consistent"] is True
    dur = d["failed_step_duration_seconds"]
    assert dur is not None and 2700 <= dur <= 2715
    assert d["verdict_consistent_with_all_evidence"] is True
    assert d["mechanism_attribution"].startswith("FACT")
    assert len(d["chain_quantum_losses"]) == 3


def test_every_competing_guard_class_is_excluded() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_producer_quantum_expiry.json")
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
    a = _load(f"results/evaluation/orchestration/{RESUMED}_annotations.json")
    msgs = [x.get("message", "") for x in a]
    assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m for m in msgs)
    assert any("exit code 78" in m for m in msgs)
    assert any("quantum ended cleanly" in m for m in msgs)


def test_skipped_write_scope_step_replays_clean() -> None:
    s = _load(f"results/evaluation/orchestration/{RUN}_snapshot_scope.json")
    assert s["schema"] == "lex-evaluation-resumed-snapshot-scope/1"
    assert s["resumed_run_id"] == int(RESUMED)
    assert s["base_commit"] == "6d73946d279032d8d10c82f6dfa21793595c3887"
    assert s["head_commit"] == SNAPSHOT_COMMIT
    assert s["verdict"] == "SCOPE_CLEAN"
    assert s["out_of_scope_paths"] == []
    assert s["n_paths_changed"] > 0
    assert s["snapshot_ref_intact"] is True


def test_skipped_producer_state_validation_replays_pass() -> None:
    v = _load(f"results/evaluation/orchestration/{RUN}_validate_step_replay.json")
    assert v["workflow_step"] == "Validate active MVP producer state"
    assert v["direction_version_in_state"] == 68
    assert v["cycle_status_in_state"] != "INITIALIZED"
    assert v["would_pass"] is True
    assert v["exit_code"] == 0


def test_prior_deliverable_claims_all_verified() -> None:
    c = _load(f"results/evaluation/operational_resume/{RUN}_claim_verification.json")
    assert c["schema"] == "lex-evaluation-claim-verification/1"
    assert c["verified_run_id"] == int(RESUMED)
    assert c["verdict"] == "PRIOR_CLAIMS_VERIFIED"
    assert c["n_failed"] == 0
    assert c["n_checks"] >= 12
    for chk in c["checks"]:
        assert chk["ok"] is True, chk


def test_item2_currency_not_yet_discriminating_and_not_executed() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    i = r["item2"]
    assert i["head_unchanged"] is True
    assert i["adjudicator_unchanged"] is True
    assert i["protocol_executed_this_run"] is False
    assert "NOT_YET_DISCRIMINATING" in i["item_2_full_protocol_status"]
    assert i["matched_members"] == 14 and i["of"] == 15


def test_multilingual_suite_passes_two_of_two() -> None:
    m = _load(f"results/evaluation/operational_resume/{RUN}_multilingual_supplement.json")
    assert m["status"] == "PASS"
    assert m["n_passed"] == 2
    assert m["n_failed"] == 0
    assert m["test_file_sha256"] == m["test_file_sha256_frozen"]


def test_accepted_pointer_verified_on_both_halves() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    p = r["accepted_pointer"]
    assert p["verified"] is True
    assert p["expected_accepted_run_id"] == 40265377500
    assert p["reverified_by_run"] == int(RUN)


def test_no_audit_gate_minted_and_posture_closed() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    assert r["controls"]["no_audit_gate_minted"] is True
    assert not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN}_GATE.json").exists()
    assert not (REPO_ROOT / f"reports/audit/evaluation/CYCLE_{RUN}.md").exists()
    assert r["human_gate_ready"] is False
    assert r["machine_gate_ready"] is False
    assert r["ready_for_owner_session"] is False
    assert r["owner_decision_required"] is False
    assert r["no_174k_benchmark_rerun"] is True
    assert r["no_frozen_bar_scored"] is True


def test_state_update_is_additive() -> None:
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
    assert o["status"] == "AUDIT_READY_PRODUCER_SNAPSHOT"
    assert s["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert s["cycle_status"] == "COMPLETE"
    assert s["continue_recommended"] is False
    assert s["direction_version"] == 68
    assert s["accepted_run_id"] == 40265377500
    lane = _load("evaluation/state/evaluation.json")
    lu = lane[f"lane_parity_update_{RUN}"]
    assert lu["no_key_removed"] is True
    assert lu["no_ref_removed"] is True
    assert lane["accepted_run_id"] == s["accepted_run_id"]
    assert lane["direction_version"] == 68
    assert lane["github_run"] == int(RUN)


def test_audit_index_scopes_the_current_run_delta() -> None:
    idx = _load(f"results/evaluation/operational_resume/AUDIT_INDEX_{RUN}.json")
    assert idx["run_id"] == int(RUN)
    assert len(idx["delta_this_run"]) >= 8
    for item in idx["delta_this_run"]:
        assert (REPO_ROOT / item["path"]).exists(), item["path"]
    assert len(idx["fast_fail_checks_for_the_auditor"]) >= 3
    assert idx["posture_flags"]["human_gate_ready"] is False


def test_result_record_claim_ceiling_stays_operational() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    assert r["schema"] == "lex-evaluation-operational-resume-verification/5"
    assert r["direction_version"] == 68
    assert r["packet_of_record_not_scored"] is True
    assert r["standing_falsification_not_rerun"] is True
    assert r["d2_path_scope_probe_not_rerun"] is True
    assert r["no_new_thresholds"] is True
    assert "Operational resume and audit-readiness only" in r["claim_ceiling"]
    assert r["resumed_snapshot_commit"] == SNAPSHOT_COMMIT
