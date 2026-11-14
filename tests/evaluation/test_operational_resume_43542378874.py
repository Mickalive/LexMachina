#!/usr/bin/env python3
"""Regression locks for the operational resume of run 43542234373 (run 43542378874).

Executed under pytest where it exists and under the lane's
``evaluation.no_pytest_runner`` shim where it does not (the producer image has no
pytest - standing disclosure). Module-level ``test_*`` functions so the shim's
call-without-fixtures discovery actually runs every assertion.

What is locked
--------------
1. Run 43542234373 failed at workflow step ``Run lane cycle`` only, with exit
   code 1 and NO retryable ``LEX_*`` annotation
   (``ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE``),
   empty durable delta, audit/integrate/state-validation/write-scope skipped.
2. The chain diagnosis stays as recorded (producer audit quantum expiry +
   exit 78; first resume zero-delta guard exit 67; second resume exit-1
   no-signature) with no audit ref for any of the three runs.
3. The snapshot's FAST-MVP deliverable verifies PRODUCT_FALSIFIED 18=11/4/3
   outside volatile fields against the claim-bearing 43397701490 record; the
   claim-bearing original is not rewritten; the standing freeze pin is intact.
4. Ordered items stay as recorded: item_1 PRESENT_AND_VERIFIED, item_2
   NOT_YET_DISCRIMINATING at product head 7be4480e (family gate 14/15),
   item_3 STANDING_RECORD_UNTOUCHED, item_5 HONOURED operational.
5. State identity: both state files agree on accepted_run_id 40265377500,
   direction_version 68, github_run 43542378874; this run is disclosed
   PENDING_INDEPENDENT_AUDIT / accepted_as_evidence false.
6. Audit-readiness H5 all_hold; write scope SCOPE_CLEAN with zero auditor
   namespace paths produced by this cycle; the audit-ready report discloses
   the claim ceiling and producer authorship.

stdlib only; no network; no product import; no frozen bar, rubric, threshold or
verdict contract is touched.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RUN_ID = 43542378874
RESUMED = 43542234373
PRODUCER = 43531218191
FIRST_RESUME = 43541879339
CLAIM = 43397701490
ACCEPTED_RUN_ID = 40265377500
DIRECTION_VERSION = 68
SNAPSHOT_HEAD = "8c07cacab54e12a008cf50f207898154d43f5926"
PRODUCT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
FREEZE_PIN = "ff466aa8ff16d5767c498587a6755103ed212088876f1aa43f2d04120e29e9fe"

OUT_DIR = _REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
STATE_ROOT = _REPO_ROOT / "state" / "evaluation.json"
STATE_LANE = _REPO_ROOT / "evaluation" / "state" / "evaluation.json"
FREEZE = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
HYPOTHESIS = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"
INSTRUMENT = _REPO_ROOT / "evaluation" / f"operational_resume_{RUN_ID}.py"
DIAGNOSIS = OUT_DIR / f"diagnosis_{RESUMED}.json"
CHAIN = OUT_DIR / f"diagnosis_chain_{RUN_ID}.json"
DELIVERABLE_VERIFICATION = OUT_DIR / f"deliverable_verification_{RUN_ID}.json"
ORDERED_WORK = OUT_DIR / f"ordered_work_{RUN_ID}.json"
PREPARE = OUT_DIR / f"prepare_{RUN_ID}.json"
AUDIT_READY = OUT_DIR / f"audit_readiness_{RUN_ID}.json"
CLAIM_RECORD = (
    _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / f"{CLAIM}.json"
)
VERIFY_RECORD = (
    _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / f"{PRODUCER}.json"
)
REPORT = (
    _REPO_ROOT / "reports" / "evaluation"
    / f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
)
FAMILY_GATE = (
    _REPO_ROOT / "results" / "evaluation" / "v68_item2_family_gate"
    / f"{RUN_ID}.json"
)
STANDING_FREEZE = (
    _REPO_ROOT / "evaluation" / "MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_all_hold(path: Path, key: str = "checks") -> dict:
    rec = _load(path)
    assert rec.get("all_hold") is True, f"{path.name}: all_hold is false"
    checks = rec.get(key) or {}
    failed = [k for k, v in checks.items() if v is not True]
    assert not failed, f"{path.name}: failed checks {failed}"
    return rec


def test_freeze_and_hypothesis_exist_with_matching_pins():
    assert FREEZE.is_file()
    assert HYPOTHESIS.is_file()
    assert INSTRUMENT.is_file()
    freeze = _load(FREEZE)
    assert str(freeze.get("run_id")) == str(RUN_ID)
    assert freeze.get("direction_version") == DIRECTION_VERSION
    pins = freeze["rehash_before_execution"]
    assert len(pins) >= 5
    for rel, expected in pins.items():
        path = _REPO_ROOT / rel
        assert path.is_file(), f"pinned file missing: {rel}"
        want = expected["sha256"] if isinstance(expected, dict) else expected
        assert _sha(path) == want, f"freeze pin mismatch for {rel}"
    hyp = _load(HYPOTHESIS)
    assert str(hyp.get("run_id")) == str(RUN_ID)
    assert str(hyp.get("resumed_run_id")) == str(RESUMED)
    ids = {h["id"] for h in hyp["hypotheses"]}
    assert ids == {"H1", "H2", "H3", "H4", "H5"}
    ast.parse(INSTRUMENT.read_text(encoding="utf-8"))
    src = INSTRUMENT.read_text(encoding="utf-8")
    for token in (str(RUN_ID), str(RESUMED), str(PRODUCER), str(CLAIM), SNAPSHOT_HEAD):
        assert token in src, f"instrument missing {token}"


def test_resumed_run_exit1_no_signature_is_recorded():
    d = _assert_all_hold(DIAGNOSIS)
    assert (
        d["failure_class"]
        == "ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE"
    )
    assert d["team_duration_seconds"] == 77
    assert d["checks"]["no_retryable_lex_signature"] is True
    assert d["checks"]["delta_vs_base_empty"] is True
    assert d["checks"]["audit_job_skipped"] is True
    assert d["checks"]["integrate_job_skipped"] is True
    assert d["checks"]["no_zero_delta_annotation"] is True
    assert d["checks"]["failing_step_is_run_lane_cycle"] is True
    assert d["refs"][f"cycle/core/evaluation/{PRODUCER}/team"] == SNAPSHOT_HEAD
    assert d["refs"][f"cycle/core/evaluation/{RESUMED}/team"] == SNAPSHOT_HEAD
    assert all(v is False for v in d["audit_refs_exist"].values())


def test_chain_root_cause_is_audit_starvation_loop():
    c = _assert_all_hold(CHAIN)
    assert c["root_cause"].startswith(
        "AUDIT_SIDE_STARVATION_PLUS_RESUME_FAILURE_LOOP"
    )
    assert c["checks"]["producer_audit_quantum_expired"] is True
    assert c["checks"]["producer_audit_duration_ge_quantum"] is True
    assert c["checks"]["producer_audit_exit_78"] is True
    assert c["checks"]["producer_team_success"] is True
    assert c["checks"]["first_resume_zero_delta_guard"] is True
    assert c["checks"]["second_resume_exit_1_no_lex_signature"] is True
    assert c["checks"]["no_audit_ref_for_any"] is True
    assert c["checks"]["no_gate_file_for_any"] is True
    assert c["producer"]["audit_duration_seconds"] >= 2700
    assert c["producer"]["audit_conclusion"] == "failure"


def test_deliverable_verification_holds_outside_volatile_fields():
    rec = _assert_all_hold(DELIVERABLE_VERIFICATION)
    twin = rec["twin_comparison"]
    assert twin["differing_outside_volatile"] == []
    assert set(twin["differing_fields"]) == {
        "run_id",
        "engine_record_path",
        "generated_at_utc",
    }
    assert rec["checks"]["replay_reproduces"] is True
    assert rec["checks"]["claim_bearing_record_intact"] is True
    assert rec["checks"]["pins_all_match"] is True
    assert rec["checks"]["verdict_product_falsified"] is True
    assert rec["checks"]["gates_18_11_4_3"] is True
    assert rec["checks"]["product_mount_head"] is True


def test_claim_bearing_and_snapshot_records_intact():
    cb = _load(CLAIM_RECORD)
    assert cb["verdict"] == "PRODUCT_FALSIFIED"
    assert cb["exit_code"] == 1
    assert str(CLAIM) in str(cb["run_id"])
    assert cb["product_mount_head"] == PRODUCT_HEAD
    assert cb["run_valid"] is True
    assert cb["input_drift"] == []

    sv = _load(VERIFY_RECORD)
    assert sv["verdict"] == "PRODUCT_FALSIFIED"
    assert str(sv["run_id"]) == str(PRODUCER)
    assert sv["direction_version"] == DIRECTION_VERSION
    assert sv["product_mount_head"] == PRODUCT_HEAD
    assert sv["run_valid"] is True
    assert sv["input_drift"] == []

    assert STANDING_FREEZE.is_file()
    assert _sha(STANDING_FREEZE) == FREEZE_PIN


def test_prepare_summary_all_hypotheses_hold():
    rec = _load(PREPARE)
    assert rec["status"] == "ALL_HYPOTHESES_HOLD"
    assert rec["hypotheses_failed"] == []
    for key in ("H1", "H2", "H3", "H4"):
        assert rec["results"][key] is True, key


def test_ordered_items_match_direction_v68():
    rec = _assert_all_hold(ORDERED_WORK)
    items = rec["ordered_work"]
    assert items["item_1"]["status"] == "PRESENT_AND_VERIFIED"
    assert items["item_2"]["status"] == "NOT_YET_DISCRIMINATING"
    assert items["item_2"]["re_measure_executed"] is False
    assert items["item_2"]["product_head"] == PRODUCT_HEAD
    assert items["item_3"]["status"] == "STANDING_RECORD_UNTOUCHED"
    assert items["item_3"]["re_run"] is False
    assert items["item_4"]["status"] == "REPORT_ONLY_WHERE_QUOTED"
    assert items["item_5"]["status"] == "HONOURED"
    assert items["item_5"]["new_same_question_measurement"] is False


def test_family_gate_still_not_discriminating():
    assert FAMILY_GATE.is_file()
    rec = _load(FAMILY_GATE)
    assert rec["status"] == "NOT_YET_DISCRIMINATING"
    assert rec["product"]["head"] == PRODUCT_HEAD
    assert rec["role_cardinality"]["member_for_member_ceiling"] == 14
    assert rec["role_cardinality"]["frozen_family_n"] == 15


def test_state_identity_and_pending_audit_disclosure():
    root = _load(STATE_ROOT)
    lane = _load(STATE_LANE)
    for field in ("accepted_run_id", "direction_version", "github_run"):
        assert root[field] == lane[field], field
    assert root["accepted_run_id"] == ACCEPTED_RUN_ID
    assert root["direction_version"] == DIRECTION_VERSION
    assert root["github_run"] == RUN_ID
    assert root["resumed_run_id"] == RESUMED
    assert root["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    block = root[f"operational_resume_{RUN_ID}"]
    assert block["pending_independent_audit"] is True
    assert block["accepted_as_evidence"] is False
    assert block["direction_version"] == DIRECTION_VERSION
    for path in (STATE_ROOT, STATE_LANE):
        state = _load(path)
        assert state["evidence_refs_n"] == len(state["evidence_refs"]), path


def test_this_cycle_wrote_no_auditor_namespace_paths():
    for rel in (
        f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json",
        f"reports/audit/evaluation/CYCLE_{RUN_ID}.md",
        f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json",
        f"reports/audit/evaluation/CYCLE_{RESUMED}.md",
    ):
        assert not (_REPO_ROOT / rel).exists(), f"auditor namespace write: {rel}"
    for p in OUT_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(_REPO_ROOT).as_posix()
            assert not rel.startswith(
                ("results/audit/evaluation/", "reports/audit/evaluation/")
            ), rel
    # live write-scope record from H5
    scope = _load(OUT_DIR / f"write_scope_live_{RUN_ID}.json")
    assert scope["verdict"] == "SCOPE_CLEAN"
    assert scope["audit_namespace_count"] == 0
    assert scope["bad_paths"] == []


def test_audit_readiness_h5_all_hold():
    rec = _assert_all_hold(AUDIT_READY)
    assert rec["checks"]["state_integrity_pass"] is True
    assert rec["checks"]["nested_refs_zero_unresolved"] is True
    assert rec["checks"]["write_scope_clean"] is True
    assert rec["checks"]["zero_audit_namespace_paths"] is True
    assert rec["checks"]["lane_suite_pass"] is True
    assert rec["checks"]["github_run_is_this_run"] is True
    assert rec["checks"]["block_discloses_pending_audit"] is True
    assert rec["checks"]["state_files_agree_on_run_identity"] is True
    assert rec["checks"]["accepted_run_id_unchanged"] is True
    identity = rec["state_identity"]
    assert identity["root_accepted_run_id"] == ACCEPTED_RUN_ID
    assert identity["lane_accepted_run_id"] == ACCEPTED_RUN_ID
    assert identity["root_github_run"] == RUN_ID
    assert identity["audit_status"] == "PENDING_INDEPENDENT_AUDIT"


def test_audit_ready_report_discloses_ceiling_and_status():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    lowered = text.lower()
    assert str(RUN_ID) in text
    assert "PRODUCT_FALSIFIED" in text
    assert "PENDING_INDEPENDENT_AUDIT" in text
    assert "producer-authored" in lowered
    assert "not an independent audit" in lowered
    assert "continue_recommended=false" in text
    assert "43397701490" in text
