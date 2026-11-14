#!/usr/bin/env python3
"""Regression locks for the operational resume of run 43531078358 (run 43531218191).

Executed under pytest where it exists and under the lane's
``evaluation.no_pytest_runner`` shim where it does not (the producer image has no
pytest - standing disclosure).

What is locked
--------------
1. Run 43531078358 failed at workflow step ``Run lane cycle`` only, the two
   pre-cycle steps skipped, audit/integrate skipped, exactly one failure class
   recorded: ``ORCHESTRATION_NO_HEALTHY_FREE_MODEL_RC76``
   (LEX_NO_HEALTHY_FREE_TOOL_MODEL, exit code 76, agent never launched).
2. The earlier agent attempt of THIS run executed the frozen wrapper and died
   before committing; the recovered delta is verified, not rewritten
   (22/22 checks, twin match outside volatile fields, out-of-tree replay
   reproduces exactly).
3. The fresh 43531218191 record still falsifies: PRODUCT_FALSIFIED, exit 1,
   18 gates = 11 passed / 4 failed / 3 reported, product mount head 7be4480e,
   input drift none, run_valid true.
4. Ordered items stand: item_1 PRESENT_AND_VERIFIED, item_2
   NOT_YET_DISCRIMINATING (lab/product + mount unchanged at 7be4480e), item_3
   STANDING_RECORD_UNTOUCHED, item_5 HONOURED.
5. The committed-tree defect of cycle 43405199129 is repaired: both previously
   dangling evidence refs exist in the committed tree.
6. The audit-ready report discloses the claim ceiling, the producer authorship
   and the standing order.

NOTE (disclosed, repo precedent): per-cycle state-pointer assertions like
``github_run == <cycle run id>`` go stale by construction the moment a later
cycle advances the pointer; see test_operational_resume_43359487892.py at HEAD
for the same pattern. This file pins THIS cycle's state as of this cycle.

stdlib only; no network at test time; no frozen bar, rubric, threshold or
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

RUN_ID = 43531218191
RESUMED = 43531078358
CHAIN_DELIVERABLE = 43397701490
ACCEPTED_RUN_ID = 40265377500
DIRECTION_VERSION = 68
PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
OUT_DIR = _REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
STATE_ROOT = _REPO_ROOT / "state" / "evaluation.json"
STATE_LANE = _REPO_ROOT / "evaluation" / "state" / "evaluation.json"
BENCH_RECORD = (
    _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" / f"{RUN_ID}.json"
)
BENCH_ENGINE = (
    _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" /
    f"{RUN_ID}_engine_mapping_free_recall_falsifier.json"
)
REPORT = (
    _REPO_ROOT / "reports" / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
)
DIAGNOSIS = OUT_DIR / "diagnosis_43531078358.json"
INRUN = OUT_DIR / "in_run_attempt_recovery_43531218191.json"
DELIVERABLE_VERIFICATION = OUT_DIR / "deliverable_verification_43531218191.json"
ORDERED_WORK = OUT_DIR / "ordered_work_43531218191.json"
STATE_INTEGRITY = OUT_DIR / "state_integrity_43531218191.json"
PRIOR_CYCLE_TEST = _REPO_ROOT / "tests" / "evaluation" / "test_operational_resume_43405199129.py"
PRIOR_CYCLE_REPORT = (
    _REPO_ROOT / "reports" / "evaluation" / "OPERATIONAL_RESUME_43405199129_AUDIT_READY.md"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_resumed_run_provider_health_failure_is_recorded():
    d = _load(DIAGNOSIS)
    assert d["run_id"] == str(RUN_ID)
    assert d["resumed_from_run"] == str(RESUMED)
    assert d["failure_class"] == "ORCHESTRATION_NO_HEALTHY_FREE_MODEL_RC76"
    assert d["all_hold"] is True
    assert d["agent_launched"] is False
    assert d["lex_signature"] == "LEX_NO_HEALTHY_FREE_TOOL_MODEL"
    assert d["exit_code"] == 76
    assert d["failing_step"] == "Run lane cycle"
    assert d["state_validation_skipped"] is True
    assert d["write_scope_skipped"] is True
    assert d["audit_job_skipped"] is True
    assert d["integrate_job_skipped"] is True
    assert d["not_a_product_defect"] is True
    assert d["not_an_evidence_defect"] is True
    # API evidence is committed alongside
    for rel in ("api/run_43531078358.json", "api/jobs_43531078358.json",
                "api/annotations_43531078358_team.json"):
        assert (OUT_DIR / rel).is_file(), rel


def test_in_run_recovery_and_committed_tree_defect_are_recorded():
    r = _load(INRUN)
    assert r["all_hold"] is True
    assert r["failure_class_inrun"].startswith("AGENT_ATTEMPT_DIED_BEFORE_COMMIT")
    assert len(r["recovered_delta"]) >= 6
    assert all(entry["status"].startswith("recovered") for entry in r["recovered_delta"])
    defect = r["committed_tree_defect_found"]
    assert defect["dangling_refs_at_HEAD"] == [
        "tests/evaluation/test_operational_resume_43405199129.py",
        "reports/evaluation/OPERATIONAL_RESUME_43405199129_AUDIT_READY.md",
    ]
    # repaired: both files exist in the tree now (additive commit of this cycle)
    for rel in defect["dangling_refs_at_HEAD"]:
        assert (_REPO_ROOT / rel).is_file(), rel
    assert defect["repaired_this_cycle"].startswith("both files committed")
    assert (PRIOR_CYCLE_TEST).is_file()
    assert (PRIOR_CYCLE_REPORT).is_file()


def test_recovered_deliverable_is_verified_and_still_falsifies():
    ver = _load(DELIVERABLE_VERIFICATION)
    assert ver["all_hold"] is True
    assert ver["n_passed"] == ver["n_checks"] == 22
    assert ver["deliverable"] == str(BENCH_RECORD.relative_to(_REPO_ROOT))
    assert ver["product_mount_head"] == PRODUCT_MOUNT_HEAD

    rec = _load(BENCH_RECORD)
    eng = _load(BENCH_ENGINE)
    assert rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["exit_code"] == 1
    assert rec["run_valid"] is True
    assert rec["input_drift"] == []
    assert rec["product_mount_head"] == PRODUCT_MOUNT_HEAD
    assert [rec[k] for k in ("n_gates", "n_passed", "n_failed", "n_reported")] == \
        [18, 11, 4, 3]
    assert rec["non_vacuity"]["all_hold"] is True
    assert rec["no_174k_benchmark_rerun"] is True
    # engine record and wrapper record agree on every measured field
    for k in ("n_gates", "n_passed", "n_failed", "n_reported",
              "n_questions_measured", "verdict", "product_mount_head"):
        assert rec[k] == eng[k], k


def test_ordered_items_stand():
    ow = _load(ORDERED_WORK)
    assert ow["all_hold"] is True
    assert ow["ordered_work"]["item_1"]["status"] == "PRESENT_AND_VERIFIED"
    assert ow["ordered_work"]["item_2"]["status"] == "NOT_YET_DISCRIMINATING"
    assert ow["ordered_work"]["item_2"]["product_head_unchanged"] is True
    assert ow["ordered_work"]["item_3"]["status"] == "STANDING_RECORD_UNTOUCHED"
    assert ow["ordered_work"]["item_3"]["re_run"] is False
    assert ow["ordered_work"]["item_5"]["status"] == "HONOURED"


def test_state_files_resolve_and_disclose_pending_audit():
    si = _load(STATE_INTEGRITY)
    assert si["verdict"] == "PASS"
    for path in (STATE_ROOT, STATE_LANE):
        state = _load(path)
        assert state["evidence_refs_n"] == len(state["evidence_refs"])
        for ref in state["evidence_refs"]:
            assert (_REPO_ROOT / ref.split(" ")[0].rstrip(",")).is_file(), ref
    root, lane = _load(STATE_ROOT), _load(STATE_LANE)
    for field in ("accepted_run_id", "direction_version", "github_run",
                  "proposed_run_id", "resumed_run_id", "audit_status"):
        assert root[field] == lane[field], field
    assert root["accepted_run_id"] == ACCEPTED_RUN_ID
    assert root["direction_version"] == DIRECTION_VERSION
    assert root["github_run"] == RUN_ID
    assert root["resumed_run_id"] == RESUMED
    assert root["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert root["continue_recommended"] is False
    assert root["human_gate_ready"] is False
    assert root["owner_decision_required"] is False
    block = root["operational_resume_43531218191"]
    assert block["claim_bearing_run"] == RUN_ID
    assert block["pending_independent_audit"] is True
    assert block["accepted_as_evidence"] is False


def test_audit_ready_report_discloses_ceiling_and_status():
    text = REPORT.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "not an independent audit" in lowered
    assert "producer-authored" in lowered
    assert "product_falsified" in lowered
    assert "not_yet_discriminating" in lowered
    assert "continue_recommended" in lowered
    assert "claim ceiling" in lowered
    assert "operational" in lowered
