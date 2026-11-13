#!/usr/bin/env python3
"""Regression locks for the operational resume of run 43378111582 (run 43379403095).

Executed under pytest where it exists and under the lane's
``evaluation.no_pytest_runner`` shim where it does not (the producer image has
no pytest - standing disclosure).

What is locked
--------------
1. Run 43378111582 is locked as the provider-rotation lane-cycle failure of
   factory-wide requirement 20: failing step ``Run lane cycle`` only, the two
   pre-cycle steps skipped, audit/integrate skipped, exactly eleven
   lane-namespace diagnostic paths added and zero audit-namespace paths.
2. The five-run chain diagnosis classes stay as recorded (two audit-quantum
   expiries, one zero-delta repair, two plain lane-cycle exits) with no audit
   ref for any of 43365482535, 43371675511 or 43378111582.
3. The claim-bearing FAST-MVP record of 43365482535 was not rewritten, its
   frozen pins still match, its scratch replay reproduces all 41 measurement
   fields, and its twin 43342851837 record still matches field-for-field.
4. Ordered item (2) is still NOT_YET_DISCRIMINATING at the accepted product
   head (zero-delta family, 14/15 role ceiling).
5. Write scope for the resumed run's delta and for this run is SCOPE_CLEAN,
   both state files stay internally consistent after the additive resume
   update, and the resume block carries a pending-independent-audit
   disclosure.

stdlib only; no network; no product import; no frozen bar, rubric, threshold or
verdict contract is touched.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RUN_ID = "43379403095"
RESUMED = "43378111582"
CHAIN_BASE = "43371675511"
DELIVERABLE = "43365482535"
TWIN = "43342851837"
OUT_DIR = _REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
STATE_ROOT = _REPO_ROOT / "state" / "evaluation.json"
STATE_LANE = _REPO_ROOT / "evaluation" / "state" / "evaluation.json"
FREEZE = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
HYPOTHESIS = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"
REPORT = (_REPO_ROOT / "reports" / "evaluation" /
          f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md")
WRAPPER_RECORD = (_REPO_ROOT / "results" / "evaluation" /
                  "minimal_ca_falsify_benchmark" / f"{DELIVERABLE}.json")

EXPECTED_FAILURE_CLASSES = {
    "43365313827": "LANE_CYCLE_EXECUTION_FAILURE (exit 1)",
    "43365482535": "AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
    "43371040309": "LANE_CYCLE_EXECUTION_FAILURE (exit 1)",
    "43371186416": "LEX_ZERO_DELTA_REPAIR (exit 67)",
    "43371675511": "AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_resumed_run_provider_rotation_failure_is_recorded():
    d = _load(OUT_DIR / f"diagnosis_{RESUMED}.json")
    assert d["failing_steps"] == ["Run lane cycle"]
    assert d["failure_class"] == "LANE_CYCLE_EXECUTION_FAILURE_PROVIDER_ROTATION"
    assert d["team_conclusion"] == "failure"
    assert d["audit_conclusion"] == "skipped"
    assert d["integrate_conclusion"] == "skipped"
    assert d["skipped_steps"] == ["Validate active MVP producer state",
                                  "Enforce lane write scope"]
    assert len(d["snapshot_added_paths"]) == 11
    assert d["snapshot_modified_paths"] == []
    assert d["snapshot_deleted_paths"] == []
    assert d["audit_namespace_paths_added"] == []
    for p in d["snapshot_added_paths"]:
        assert p.startswith("results/evaluation/operational_resume_"
                            f"{RESUMED}/"), p
        assert not p.startswith(("results/audit/", "reports/audit/")), p
    assert any("LEX_MODEL_AUTH_FAILURE" in a for a in d["annotations"])
    assert any("LEX_MODEL_ROTATE" in a for a in d["annotations"])
    assert d["checks"] and all(d["checks"].values()), d["checks"]
    assert d["holds"] is True and d["n_failed"] == 0


def test_chain_failure_classes_and_missing_audit_refs_are_recorded():
    c = _load(OUT_DIR / f"diagnosis_chain_{RUN_ID}.json")
    assert c["holds"] is True and c["n_failed"] == 0
    assert c["failure_classes"] == EXPECTED_FAILURE_CLASSES
    assert set(c["diagnosed_chain"]) == set(EXPECTED_FAILURE_CLASSES)
    assert all(v is False for v in c["audit_ref_present"].values())
    assert c["checks"] and all(c["checks"].values()), c["checks"]
    for run, per in c["per_run"].items():
        assert per["holds"] is True, run
        assert per["checks"] and all(per["checks"].values()), run


def test_freeze_record_pinned_before_execution_and_pins_still_match():
    freeze = _load(FREEZE)
    assert freeze["freeze_recorded_before_hypothesis_execution"] is True
    assert freeze["run_id"] == RUN_ID
    for rel, digest in freeze["rehash_before_execution"]["deliverable"].items():
        assert _sha(_REPO_ROOT / rel) == digest, rel
    hyp = _load(HYPOTHESIS)
    assert hyp["run_id"] == RUN_ID
    assert hyp["freeze_before_execution"] is True
    assert len(hyp["hypotheses"]) == 5


def test_deliverable_record_is_unchanged_and_falsifies():
    freeze = _load(FREEZE)["rehash_before_execution"]["deliverable"]
    assert _sha(WRAPPER_RECORD) == freeze[
        f"results/evaluation/minimal_ca_falsify_benchmark/{DELIVERABLE}.json"]
    rec = _load(WRAPPER_RECORD)
    assert rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["exit_code"] == 1
    assert [rec[k] for k in ("n_gates", "n_passed", "n_failed", "n_reported")] == \
        [18, 11, 4, 3]
    assert rec["run_valid"] is True
    assert rec["input_drift"] == []
    assert rec["product_mount_head"] == \
        "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    verification = _load(OUT_DIR / f"deliverable_verification_{RUN_ID}.json")
    assert verification["verdict"] == "DELIVERABLE_VERIFIED"
    assert verification["n_failed"] == 0
    assert all(verification["checks"].values()), verification["checks"]


def test_replay_reproduces_every_measurement_field():
    cmp = _load(OUT_DIR / f"replay_comparison_{RUN_ID}.json")
    assert cmp["verdict"] == "REPLAY_REPRODUCES"
    assert cmp["measurement_fields_compared"] == 41
    assert cmp["measurement_fields_differing"] == 0
    assert cmp["measurement_differences"] == []
    command = _load(OUT_DIR / f"replay_command_{RUN_ID}.json")
    assert command["replay_exists"] is True
    # the replay is a scratch invocation: the claim-bearing original keeps its
    # frozen sha (checked in test_deliverable_record_is_unchanged_and_falsifies)


def test_twin_records_match_outside_volatile_fields():
    t = _load(OUT_DIR / f"twin_comparison_{RUN_ID}.json")
    assert t["verdict"] == "RECORDS_MATCH"
    assert t["measurement_fields_compared"] == 41
    assert t["measurement_fields_differing"] == 0
    assert t["measurement_differences"] == []
    assert t["missing_fields"] == []
    env = t["environment_disclosure_differences"]
    assert set(env) == {"numeric_environment"}
    assert set(env["numeric_environment"]) == {"platform"}
    assert t["other_record"] == (
        f"results/evaluation/minimal_ca_falsify_benchmark/{TWIN}.json")


def test_item2_is_still_not_yet_discriminating():
    rec = _load(OUT_DIR / f"item2_family_gate_{RUN_ID}.json")
    assert rec["status"] == "NOT_YET_DISCRIMINATING"
    assert rec["product"]["head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert rec["zero_delta_check"]["byte_identical_n"] == 50
    assert rec["zero_delta_check"]["differing"] == []
    assert rec["role_cardinality"]["role_parity"] is False
    assert rec["role_cardinality"]["member_for_member_ceiling"] == 14
    assert rec["role_cardinality"]["frozen_family_n"] == 15


def test_write_scope_delta_and_live_are_clean():
    repro = _load(OUT_DIR / f"write_scope_repro_{RESUMED}.json")["verdict"]
    assert repro["verdict"] == "SCOPE_CLEAN"
    assert repro["n_bad"] == 0
    assert repro["scope_clean"] is True
    assert repro["bad_paths"] == []
    live = _load(OUT_DIR / f"write_scope_live_{RUN_ID}.json")["verdict"]
    assert live["verdict"] == "SCOPE_CLEAN"
    assert live["n_bad"] == 0
    assert live["bad_paths"] == []
    assert all(e["allowed"] for e in live["entries"]), live["entries"]
    for e in live["entries"]:
        assert not e["path"].startswith(("results/audit/", "reports/audit/"))


def test_no_audit_namespace_path_under_this_runs_output_dir():
    for p in OUT_DIR.rglob("*"):
        assert "audit" not in p.parts, p


def test_verification_prestate_all_five_hypotheses_hold():
    v = _load(OUT_DIR / f"verification_prestate_{RUN_ID}.json")
    assert v["phase"] == "prepare"
    assert v["n_hypotheses"] == 5
    assert v["n_hypotheses_holding"] == 5
    assert v["n_failed"] == 0
    assert all(h["holds"] for h in v["hypotheses"])
    assert v["continue_recommended"] is False
    assert v["independent_audit_of_resumed_run_exists"] is False
    assert v["exit_code"] == 0


def test_state_files_stay_consistent_and_disclose_pending_audit():
    root, lane = _load(STATE_ROOT), _load(STATE_LANE)
    for state in (root, lane):
        assert state["evidence_refs_n"] == len(state["evidence_refs"])
        for ref in state["evidence_refs"]:
            assert (_REPO_ROOT / ref.split(" ")[0].rstrip(",")).is_file(), ref
        assert state["github_run"] == int(RUN_ID)
        assert state["resumed_run_id"] == int(RESUMED)
        block = state[f"operational_resume_{RUN_ID}"]
        assert block["claim_bearing_run"] == RUN_ID
        assert block["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
        assert block["pending_independent_audit"] is True
        assert block["accepted_as_evidence"] is False
        assert block["independent_audit_of_resumed_run_exists"] is False
        assert int(RUN_ID) in state["resume_chain"]
    for field in ("accepted_run_id", "direction_version", "github_run"):
        assert root[field] == lane[field], field
    assert root["accepted_run_id"] == 40265377500
    assert root["direction_version"] == 68
    assert root["continue_recommended"] is False


def test_report_discloses_ceiling_and_producer_authorship():
    text = REPORT.read_text(encoding="utf-8").lower()
    assert "not an independent audit" in text or "not** an audit" in text
    assert "producer-authored" in text
    assert "product_falsified" in text
    assert "not_yet_discriminating" in text
    assert "continue_recommended" in text
