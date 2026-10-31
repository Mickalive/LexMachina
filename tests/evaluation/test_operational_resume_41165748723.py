"""Audit-readiness self-check for the 41165748723 operational-resume snapshot.

Plain functions only (the lane's documented no-pytest shim executes these when
pytest is absent). They read committed JSON artifacts and never import Product,
network, numpy or a frozen benchmark instrument.

They assert exactly the claims this cycle makes:
  * 41161273401's producer cycle passed and only its independent audit job was
    killed by the 2700-second work-quantum guard (exit 78);
  * the persisted deliverable replays to a normalized-identical result;
  * the multilingual/provenance suite reads PASS 2/2 after the numeric env fix;
  * ordered item (2) is still NOT_YET_DISCRIMINATING at the current product head
    (14/15 member-for-member) and its protocol was not executed;
  * the accepted pointer 40265377500 verifies on both halves;
  * the snapshot's added paths were all inside the evaluation write scope;
  * the producer minted no audit gate for its own run and posture stays closed.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN = "41165748723"
RESUMED = "41161273401"


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def test_audit_failure_is_quantum_expiry_not_measurement() -> None:
    d = _load(f"results/evaluation/orchestration/CYCLE_{RESUMED}_audit_quantum_expiry.json")
    assert d["failure_class"] == "WORK_QUANTUM_EXPIRED"
    assert d["failure_is_orchestration_not_measurement"] is True
    assert d["failure_is_validation_failure"] is False
    assert d["exit_code"] == 78
    assert d["quantum_seconds"] == 2700
    assert d["failed_job_step"] == "Independent audit"
    assert d["snapshot_commit"] == "7ef7ffb56de0c0ce72af373f6e488cda04df6445"


def test_audit_failure_recorded_in_resume() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    nd = r["audit_failure"]
    assert nd["all_checks_pass"] is True
    assert nd["checks"]["team_validation_passed"] is True
    assert nd["checks"]["team_scope_passed"] is True
    assert nd["checks"]["team_snapshot_persisted"] is True
    assert nd["checks"]["audit_scope_step_skipped"] is True
    assert nd["checks"]["audit_persist_step_skipped"] is True
    assert nd["checks"]["integrate_job_skipped"] is True


def test_persisted_deliverable_replays_claim_payload_identically() -> None:
    rep = _load(f"results/evaluation/operational_resume/{RUN}_replay_of_41161273401.json")
    assert rep["exit_code"] == 0
    assert rep["normalized_equal"] is True
    assert rep["diff_paths"] == []
    assert rep["committed_normalized_sha256"] == rep["scratch_normalized_sha256"]
    assert rep["prior_inner_reproduction_of_41157741636"]["reproduced"] is True
    # The full diff must be published, not silently dropped.
    assert rep["full_diff_paths"]
    assert "state_update" in " ".join(rep["full_diff_paths"])
    assert any(p.endswith("_at_utc") for p in rep["full_diff_paths"])
    for path in rep["excluded_volatile_paths"]:
        assert path in rep["full_diff_paths"]


def test_replay_removes_no_claim_bearing_field() -> None:
    rep = _load(f"results/evaluation/operational_resume/{RUN}_replay_of_41161273401.json")
    rules = rep["volatile_exclusion_rules"]
    assert rules["key_suffixes_removed_recursively"] == ["_at_utc"]
    assert rules["top_level_blocks_removed"] == ["state_update", "state_integrity_gate"]
    assert set(rep["diff_paths"]).isdisjoint(rep["excluded_volatile_paths"])


def test_multilingual_suite_passes_after_numeric_env_fix() -> None:
    rep = _load(f"results/evaluation/operational_resume/{RUN}_replay_of_41161273401.json")
    assert rep["multilingual_supplement_status"] == "PASS"
    assert rep["multilingual_supplement_passed"] == 2
    assert rep["numeric_environment"]["numpy"]
    assert rep["numeric_environment"]["scipy"]
    assert rep["numeric_environment"]["scikit_learn"]


def test_item2_still_not_discriminating_at_current_product_head() -> None:
    i = _load(f"results/evaluation/operational_resume/{RUN}_item2_readjudication.json")
    assert i["H1_precondition_leg_landed"] is True
    assert i["H2_precondition_full_family_regenerated"] is False
    assert i["matched_members_at_current_head"] == 14
    assert i["of"] == 15
    per_role = i["member_for_member_matching"]["matched_per_role"]
    assert per_role["offline/rent-default"] == 11
    assert per_role["server/served"] == 3
    assert per_role["offline/business-judgment-rule"] == 0
    assert per_role["offline/corporate-criminal-liability"] == 0
    assert per_role["offline/petty-theft-dismissal"] == 0
    assert sum(per_role.values()) == 14
    assert i["roles_post_repair"] == {
        "offline/business-judgment-rule": 10,
        "offline/corporate-criminal-liability": 9,
        "offline/petty-theft-dismissal": 9,
        "offline/rent-default": 18,
        "server/served": 3,
    }
    assert i["product_mount_head"].startswith("7be4480e")
    assert i["protocol_executed"] is False
    assert i["item_2_full_protocol_status"].startswith("NOT_YET_DISCRIMINATING")
    assert i["item_2_leg_status"] == "LANDED"


def test_accepted_pointer_is_40265377500_on_both_halves() -> None:
    p = _load(f"results/evaluation/operational_resume/{RUN}.json")["accepted_pointer"]
    assert p["verified"] is True
    assert p["lab_head"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert p["half_1_gate"] == "PASS"
    assert p["half_1_safe_to_integrate"] is True
    assert p["half_1_required_fixes"] == []
    assert p["half_2_accept_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    s = _load("state/evaluation.json")
    assert s["accepted_run_id"] == 40265377500
    assert s["accepted_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert s["proposed_run_id"] == int(RUN)
    assert s["github_run"] == int(RUN)


def test_preserved_snapshot_added_paths_are_in_scope() -> None:
    w = _load("results/evaluation/orchestration/41161273401_snapshot_write_scope_repro.json")
    assert w["verdict"]["verdict"] == "SCOPE_CLEAN"
    assert w["verdict"]["scope_clean"] is True
    assert w["verdict"]["n_bad"] == 0
    assert w["verdict"]["bad_paths"] == []
    assert len(w["reconstruction"]["added_paths"]) > 0


def test_no_audit_gate_minted_and_posture_closed() -> None:
    r = _load(f"results/evaluation/operational_resume/{RUN}.json")
    assert r["controls"]["no_audit_gate_minted"] is True
    assert not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN}_GATE.json").exists()
    assert r["packet_admitted"] is False
    assert r["machine_gate_ready"] is False
    assert r["human_gate_ready"] is False
    assert r["ready_for_owner_session"] is False
    assert r["owner_decision_required"] is False
    assert r["no_frozen_bar_scored"] is True
    assert r["no_174k_benchmark_rerun"] is True


def test_state_update_is_additive() -> None:
    s = _load("state/evaluation.json")
    u = s[f"state_update_{RUN}"]
    assert u["additive_only"] is True
    assert u["no_key_removed"] is True
    assert u["no_ref_removed"] is True
    assert u["accepted_run_id_unchanged"] == 40265377500
    assert u["proposed_run_id_set_to"] == int(RUN)
    assert s[f"operational_resume_{RUN}"]["prior_result_reproduced_in_fresh_replay"] is True



def test_nested_refs_resolved_and_historical_dangling_ref_disclosed() -> None:
    n = _load(f"results/evaluation/orchestration/{RUN}_nested_evidence_refs.json")
    assert n["verdict"] == "NESTED_REFS_RESOLVED"
    assert n["n_unresolved"] == 0
    assert n["n_disclosure_errors"] == 0
    ref = "results/audit/evaluation/CYCLE_40246705199_GATE.json"
    assert ref in n["state_disclosed_known_unresolvable"]
    s = _load("state/evaluation.json")
    entries = s["nested_evidence_refs_disclosed_known_unresolvable"]
    assert any(e["path"] == ref and e["disclosed_by_run"] == int(RUN) for e in entries)
