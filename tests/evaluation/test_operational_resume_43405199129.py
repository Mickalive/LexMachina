#!/usr/bin/env python3
"""Regression locks for the operational resume of run 43404713001 (run 43405199129).

Executed under pytest where it exists and under the lane's
``evaluation.no_pytest_runner`` shim where it does not (the producer image has no
pytest - standing disclosure).

What is locked
--------------
1. Run 43404713001 failed at workflow step ``Run lane cycle`` only, the two
   pre-cycle steps skipped, audit/integrate skipped, exactly one failure class
   recorded: ``ORCHESTRATION_ZERO_DELTA_GUARD_RC67``.
2. The chain diagnosis classes stay as recorded (producer audit quantum expiry + exit 78,
   first resume exit 1 without retryable signature, second resume zero-delta guard) with
   no audit ref for any of 43397701490 / 43404561250 / 43404713001.
3. The claim-bearing FAST-MVP record of 43397701490 is not rewritten and still
   falsifies: PRODUCT_FALSIFIED, exit 1, 18 gates = 11 passed / 4 failed / 3 reported,
   product mount head 7be4480e, replay reproduces, twin matches outside volatile fields.
4. Ordered item (2) is still NOT_YET_DISCRIMINATING at the accepted product head.
5. The audit-readiness instrument recorded the two validation gaps this cycle closed:
   the state-integrity ``evidence_refs_resolve`` check failed and the nested
   evidence-refs guard reported ``UNRESOLVED_REFS_PRESENT``; after the additive repair of
   this cycle every ``evidence_refs`` entry resolves again in the committed tree.
6. The audit-ready report discloses the claim ceiling, the producer authorship and the
   standing order.

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

RUN_ID = 43405199129
RESUMED = 43404713001
DELIVERABLE = 43397701490
ACCEPTED_RUN_ID = 40265377500
DIRECTION_VERSION = 68
PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
OUT_DIR = _REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
STATE_ROOT = _REPO_ROOT / "state" / "evaluation.json"
STATE_LANE = _REPO_ROOT / "evaluation" / "state" / "evaluation.json"
FREEZE = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
HYPOTHESIS = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"
DELIVERABLE_RECORD = (
    _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" / f"{DELIVERABLE}.json"
)
REPORT = (
    _REPO_ROOT / "reports" / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
)
DIAGNOSIS = OUT_DIR / f"diagnosis_{RESUMED}.json"
CHAIN = OUT_DIR / f"diagnosis_chain_{RUN_ID}.json"
DELIVERABLE_VERIFICATION = OUT_DIR / f"deliverable_verification_{RUN_ID}.json"
ORDERED_WORK = OUT_DIR / f"ordered_work_{RUN_ID}.json"
AUDIT_READY = OUT_DIR / f"audit_readiness_{RUN_ID}.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state_files() -> list[Path]:
    return [STATE_ROOT, STATE_LANE]


def test_resumed_run_zero_delta_failure_is_recorded():
    d = _load(DIAGNOSIS)
    assert d["run_id"] == str(RUN_ID)
    assert d["resumed_run_id"] == str(RESUMED)
    assert d["failure_class"] == "ORCHESTRATION_ZERO_DELTA_GUARD_RC67"
    assert d["all_hold"] is True
    assert d["direction_version"] == DIRECTION_VERSION
    assert d["checks"]["failing_step_is_run_lane_cycle"] is True
    assert d["checks"]["team_conclusion_is_failure"] is True
    assert d["checks"]["audit_job_skipped"] is True
    assert d["checks"]["integrate_job_skipped"] is True
    assert d["checks"]["state_validation_skipped"] is True
    assert d["checks"]["write_scope_skipped"] is True
    assert d["checks"]["delta_vs_base_empty"] is True
    assert d["checks"]["team_ref_equals_snapshot"] is True
    assert d["audit_refs_exist"] == {"43397701490": False, "43404561250": False,
                                     "43404713001": False}


def test_chain_root_cause_is_recorded():
    c = _load(CHAIN)
    assert c["root_cause"].startswith("AUDIT_SIDE_STARVATION_PLUS_ZERO_DELTA_RESUME_LOOP")
    assert c["producer"]["audit_conclusion"] == "failure"
    assert c["producer"]["audit_duration_seconds"] >= 2700
    assert c["producer"]["audit_annotations"][0].startswith("Process completed with exit code 78.")
    assert c["second_resume"]["failure_class"] == "ORCHESTRATION_ZERO_DELTA_GUARD_RC67"
    assert c["chain"] == ["43397701490", "43404561250", "43404713001"]
    assert c["gate_files_in_tree"] == []


def test_deliverable_is_unchanged_and_still_falsifies():
    freeze = _load(FREEZE)
    assert freeze["freeze_recorded_before_hypothesis_execution"] is True
    assert freeze["run_id"] == str(RUN_ID)
    for rel, digest in freeze["rehash_before_execution"].items():
        assert _sha(_REPO_ROOT / rel) == digest, rel
    hyp = _load(HYPOTHESIS)
    assert hyp["run_id"] == str(RUN_ID)
    assert hyp["freeze_before_execution"] is True
    assert len(hyp["hypotheses"]) == 5

    verification = _load(DELIVERABLE_VERIFICATION)
    assert verification["all_hold"] is True
    assert all(verification["checks"].values()), verification["checks"]
    assert verification["checks"]["verdict_product_falsified"] is True
    assert verification["deliverable"] == (
        "results/evaluation/minimal_ca_falsify_benchmark/43397701490.json")
    assert verification["deliverable_sha256"] == (
        "461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad")
    assert verification["report"] == "reports/evaluation/RETRIEVAL_CA_BENCHMARK_43397701490.md"

    rec = _load(DELIVERABLE_RECORD)
    assert rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["exit_code"] == 1
    assert rec["run_valid"] is True
    assert rec["input_drift"] == []
    assert rec["product_mount_head"] == PRODUCT_MOUNT_HEAD
    assert [rec[k] for k in ("n_gates", "n_passed", "n_failed", "n_reported")] == \
        [18, 11, 4, 3]


def test_ordered_work_items_stand():
    ow = _load(ORDERED_WORK)
    assert ow["all_hold"] is True
    assert ow["ordered_work"]["item_1"]["status"] == "PRESENT_AND_VERIFIED"
    assert ow["ordered_work"]["item_2"]["status"] == "NOT_YET_DISCRIMINATING"
    assert ow["ordered_work"]["item_3"]["status"] == "STANDING_RECORD_UNTOUCHED"
    assert ow["ordered_work"]["item_5"]["status"] == "HONOURED"


def test_audit_readiness_pre_repair_gaps_are_recorded():
    ar = _load(AUDIT_READY)
    assert ar["run_id"] == str(RUN_ID)
    assert ar["direction_version"] == DIRECTION_VERSION
    assert ar["checks"]["accepted_run_id_unchanged"] is True
    assert ar["checks"]["audit_status_pending"] is True
    assert ar["checks"]["block_discloses_pending_audit"] is True
    assert ar["checks"]["direction_version_current"] is True
    assert ar["checks"]["github_run_is_this_run"] is True
    assert ar["checks"]["lane_suite_pass"] is True
    assert ar["checks"]["state_integrity_pass"] is False
    assert ar["checks"]["nested_refs_zero_unresolved"] is False
    assert ar["state_integrity"]["verdict"] == "AT_LEAST_ONE_CHECK_FAILED"
    assert ar["nested_refs"]["verdict"] == "UNRESOLVED_REFS_PRESENT"
    assert ar["state_identity"]["root_accepted_run_id"] == ACCEPTED_RUN_ID
    assert ar["state_identity"]["root_direction_version"] == DIRECTION_VERSION


def test_repaired_state_refs_all_resolve():
    """The additive repair of this cycle closes the dangling declared refs."""
    bad = []
    for path in _state_files():
        state = _load(path)
        refs = state.get("evidence_refs") or []
        if state.get("evidence_refs_n") != len(refs):
            bad.append((str(path), "evidence_refs_n", state.get("evidence_refs_n"),
                        len(refs)))
        for ref in refs:
            token = str(ref).split(" ")[0].rstrip(",")
            if not (_REPO_ROOT / token).is_file():
                bad.append((str(path), "unresolved", ref, ""))
    assert bad == [], bad
    root = _load(STATE_ROOT)
    lane = _load(STATE_LANE)
    for field in ("accepted_run_id", "direction_version", "github_run"):
        assert root[field] == lane[field], field
    assert root["accepted_run_id"] == ACCEPTED_RUN_ID
    assert root["direction_version"] == DIRECTION_VERSION
    # Pointer assertions made point-in-time-safe BEFORE this file's first-ever
    # commit (disclosed in results/evaluation/operational_resume_43531218191/
    # in_run_attempt_recovery_43531218191.json): the run pointer advances every
    # cycle by lane convention, and cycle 43531218191 advanced it after this
    # text was written but before the file was ever committed. The pointer
    # identity between the two state files is still asserted above; every
    # measurement and verification assertion in this file is byte-intact.
    assert root["github_run"] >= RUN_ID
    assert root["resumed_run_id"] >= RESUMED
    assert root["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert root["continue_recommended"] is False
    assert root["human_gate_ready"] is False
    assert root["owner_decision_required"] is False


def test_audit_ready_report_discloses_ceiling_and_status():
    text = REPORT.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "not an independent audit" in lowered
    assert "producer-authored" in lowered
    assert "product_falsified" in lowered
    assert "not_yet_discriminating" in lowered
    assert "continue_recommended" in lowered
    assert "claim ceiling" in lowered
