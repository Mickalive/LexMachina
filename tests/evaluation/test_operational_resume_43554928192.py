#!/usr/bin/env python3
"""Regression locks for the operational resume of snapshot 43554928192.

Executed under pytest where it exists and under the lane's
``evaluation.no_pytest_runner`` shim where it does not (the producer image has no
pytest - standing disclosure).  Module-level ``test_*`` functions so the shim's
call-without-fixtures discovery actually runs every assertion.

What is locked
--------------
1. Run 43554928192's TEAM job succeeded end to end and its AUDIT job failed
   only at ``Independent audit`` after 2750s with
   ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` / exit 78; gate-read and
   persist-audit were skipped, integrate was skipped, no audit ref or gate
   exists.  The snapshot head is 35d8d649.
2. The same audit quantum expiry consumed 43531218191, 43542378874,
   43550420112 and 43554928192; the zero-delta and launch-failure resumes are
   recorded; root cause is AUDIT_WORK_QUANTUM_EXPIRY_RECURRENCE.
3. The five-file snapshot delta is present with the committed hashes; the
   smallest-CA record is PRODUCT_FALSIFIED exit 1 on packet 39319405429 with
   zero issued rows; the out-of-tree replay reproduces measurement-bearing
   fields; standing records and frozen pins are intact; the prior re-execution
   is OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM.
4. Ordered work stays: item_1 PRESENT_AND_VERIFIED, item_2
   NOT_YET_DISCRIMINATING (full 15-member family not regenerated, 14/15,
   zero-delta, no re-measure), item_3 STANDING_RECORD_UNTOUCHED, item_4
   REPORT_ONLY_WHERE_QUOTED, item_5 HONOURED_OPERATIONAL.
5. Audit-readiness H5 holds: state integrity passes, nested refs resolve,
   write scope is clean with zero auditor-namespace paths, the lane suite
   passes, both state files agree on accepted_run_id 40265377500 /
   direction_version 68 / github_run 43559166421, and this run is disclosed
   PENDING_INDEPENDENT_AUDIT / accepted_as_evidence=false.

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

RUN_ID = 43559166421
RESUMED = 43554928192
SNAPSHOT_HEAD = "35d8d64941b76ab59f931915f1f59ac97e07041f"
PARENT = "d835bad49ce52ebdbdc792d03f88ef1e030fd009"
ACCEPTED_RUN_ID = 40265377500
DIRECTION_VERSION = 68
PRODUCT_HEAD_DIRECTION = "8b5b08dd"
PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
CHAIN = [43531218191, 43542378874, 43550420112, 43554928192]

PACK = _REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RESUMED}"
STATE_ROOT = _REPO_ROOT / "state" / "evaluation.json"
STATE_LANE = _REPO_ROOT / "evaluation" / "state" / "evaluation.json"
FREEZE = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json"
HYPOTHESIS = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json"
INSTRUMENT = _REPO_ROOT / "evaluation" / f"operational_resume_{RESUMED}.py"
DIAGNOSIS = PACK / f"diagnosis_{RESUMED}.json"
CHAIN_RECORD = PACK / f"diagnosis_chain_{RUN_ID}.json"
VERIFICATION = PACK / f"deliverable_verification_{RUN_ID}.json"
ORDERED_WORK = PACK / f"ordered_work_{RUN_ID}.json"
AUDIT_READY = PACK / f"audit_readiness_{RUN_ID}.json"
REPORT = _REPO_ROOT / "reports" / "evaluation" / (
    f"OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md")
FAMILY_GATE = (
    _REPO_ROOT / "results" / "evaluation" / "v68_item2_family_gate"
    / f"{RUN_ID}.json"
)
DELIVERABLE = (
    _REPO_ROOT / "results" / "evaluation" / "smallest_ca_benchmark"
    / f"{RESUMED}.json"
)
STANDING = [
    _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / "43397701490.json",
    _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    / "43531218191.json",
]
CORRECTION = _REPO_ROOT / "reports" / "evaluation" / (
    "BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_all_hold(path: Path) -> dict:
    rec = _load(path)
    assert rec.get("all_hold") is True, f"{path.name}: all_hold is false"
    checks = rec.get("checks") or {}
    failed = [k for k, v in checks.items() if v is not True]
    assert not failed, f"{path.name}: failed checks {failed}"
    return rec


def test_freeze_and_hypothesis_exist_with_matching_pins():
    assert FREEZE.is_file()
    assert HYPOTHESIS.is_file()
    assert INSTRUMENT.is_file()
    freeze = _load(FREEZE)
    assert str(freeze.get("run_id")) == str(RUN_ID)
    assert str(freeze.get("resumed_run_id")) == str(RESUMED)
    assert freeze.get("direction_version") == DIRECTION_VERSION
    assert freeze.get("snapshot_head") == SNAPSHOT_HEAD
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
    assert {h["id"] for h in hyp["hypotheses"]} == {"H1", "H2", "H3", "H4", "H5"}
    ast.parse(INSTRUMENT.read_text(encoding="utf-8"))


def test_resumed_team_success_and_audit_quantum_expiry():
    d = _assert_all_hold(DIAGNOSIS)
    assert d["failure_class"] == "ORCHESTRATION_AUDIT_WORK_QUANTUM_EXPIRED"
    assert d["team"]["conclusion"] == "success"
    assert d["team"]["steps"]["Run lane cycle"] == "success"
    assert d["team"]["steps"]["Persist team snapshot"] == "success"
    assert d["audit"]["conclusion"] == "failure"
    assert d["audit"]["duration_seconds"] == 2750
    assert d["checks"]["audit_quantum_expired_annotation"] is True
    assert d["checks"]["audit_exit_78_annotation"] is True
    assert d["checks"]["gate_step_skipped"] is True
    assert d["checks"]["persist_audit_step_skipped"] is True
    assert d["checks"]["integrate_skipped"] is True
    assert d["checks"]["no_audit_ref"] is True
    assert d["checks"]["no_audit_gate_file"] is True
    assert d["snapshot_head"] == SNAPSHOT_HEAD
    assert d["team_ref"] == SNAPSHOT_HEAD
    assert d["attempt_ref"] == SNAPSHOT_HEAD


def test_chain_is_audit_quantum_expiry_recurrence():
    c = _assert_all_hold(CHAIN_RECORD)
    assert c["root_cause"].startswith("AUDIT_WORK_QUANTUM_EXPIRY_RECURRENCE")
    assert [int(r) for r in c["chain"]] == CHAIN
    for run, row in c["per_run"].items():
        assert row["team_conclusion"] == "success", run
        assert row["audit_conclusion"] == "failure", run
        assert row["audit_duration_seconds"] >= 2700, run
        assert any("LEX_WORK_QUANTUM_EXPIRED seconds=2700" in m
                   for m in row["audit_annotations"]), run
        assert row["audit_steps"]["Enforce audit scope and read gate"] == "skipped"
        assert row["audit_steps"]["Persist audit snapshot"] == "skipped"
    assert c["zero_delta_resume"]["failure_class"].endswith("RC67")
    assert c["launch_failure_resume"]["failure_class"].endswith(
        "EXIT_1_NO_RETRYABLE_SIGNATURE")
    assert not any(c["audit_refs_exist"].values())
    assert not any(c["audit_gate_files_exist"].values())


def test_snapshot_delta_and_replay_verify():
    v = _assert_all_hold(VERIFICATION)
    assert v["classification"] == "OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM"
    assert v["delta"]["parent"] == PARENT
    assert len(v["delta"]["files"]) == 5
    assert v["delta"]["hashes"] == v["delta"]["committed_hashes"]
    assert v["deliverable"]["verdict"] == "PRODUCT_FALSIFIED"
    assert v["deliverable"]["exit_code"] == 1
    assert v["deliverable"]["packet"] == "39319405429"
    assert v["deliverable"]["direction_version"] == DIRECTION_VERSION
    assert v["deliverable"]["n_questions"] == 3
    assert v["deliverable"]["total_issued"] == 0
    assert v["replay"]["returncode"] == 1
    assert v["replay_comparison"]["differing_outside_volatile"] == []
    assert v["replay_comparison"]["differing_measurement_fields"] == []
    assert v["replay"]["network_calls"] == 0
    assert _load(DELIVERABLE)["verdict"] == "PRODUCT_FALSIFIED"


def test_standing_records_and_frozen_pins_intact():
    assert _sha(STANDING[0]) == (
        "461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad")
    assert _sha(STANDING[1]) == (
        "ab187272ff3eb4f6eda65614462b31dd5ef1d3181a81dc38aae4bfe923c17edd")
    assert _sha(CORRECTION) == (
        "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d")
    v = _load(VERIFICATION)
    assert v["pins_all_match"] is True
    assert v["standing_records"][
        "results/evaluation/minimal_ca_falsify_benchmark/43397701490.json"] == (
            "461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad")


def test_ordered_work_not_yet_discriminating():
    o = _assert_all_hold(ORDERED_WORK)
    work = o["ordered_work"]
    assert work["item_1"]["status"] == "PRESENT_AND_VERIFIED"
    assert work["item_2"]["status"] == "NOT_YET_DISCRIMINATING"
    assert work["item_2"]["full_named_family_regenerated"] is False
    assert work["item_2"]["member_for_member_ceiling"] == 14
    assert work["item_2"]["frozen_family_n"] == 15
    assert work["item_2"]["zero_delta"] is True
    assert work["item_2"]["re_measure_executed"] is False
    assert work["item_2"]["direction_accepted_product_head"] == PRODUCT_HEAD_DIRECTION
    assert work["item_2"]["product_mount_head"].startswith(PRODUCT_MOUNT_HEAD)
    assert work["item_3"]["status"] == "STANDING_RECORD_UNTOUCHED"
    assert work["item_4"]["status"] == "REPORT_ONLY_WHERE_QUOTED"
    assert work["item_5"]["status"] == "HONOURED_OPERATIONAL"
    assert _load(FAMILY_GATE)["status"] == "NOT_YET_DISCRIMINATING"


def test_audit_readiness_h5_holds():
    a = _assert_all_hold(AUDIT_READY)
    assert a["state_integrity"]["exit_code"] == 0
    assert a["state_integrity"]["verdict"] == "ALL_CHECKS_PASS"
    assert a["nested_refs"]["n_unresolved"] == 0
    assert a["write_scope"]["verdict"] == "SCOPE_CLEAN"
    assert a["write_scope"]["audit_namespace_count"] == 0
    assert a["lane_suite"]["exit_code"] == 0
    assert a["state_identity"]["root_accepted_run_id"] == ACCEPTED_RUN_ID
    assert a["state_identity"]["lane_accepted_run_id"] == ACCEPTED_RUN_ID
    assert a["state_identity"]["root_direction_version"] == DIRECTION_VERSION
    assert a["state_identity"]["root_github_run"] == RUN_ID
    assert a["state_identity"]["lane_github_run"] == RUN_ID


def test_state_discloses_pending_audit_and_refs_resolve():
    for path in (STATE_ROOT, STATE_LANE):
        st = _load(path)
        assert st["accepted_run_id"] == ACCEPTED_RUN_ID
        assert st["direction_version"] == DIRECTION_VERSION
        assert st["github_run"] == RUN_ID
        assert st["resumed_run_id"] == RESUMED
        assert st["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
        block = st[f"operational_resume_{RESUMED}"]
        assert block["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
        assert block["accepted_as_evidence"] is False
        assert st["evidence_refs_n"] == len(st["evidence_refs"])
        for ref in st["evidence_refs"]:
            assert (_REPO_ROOT / ref).is_file(), f"unresolved ref: {ref}"


def test_report_and_no_auditor_namespace_paths():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "PENDING_INDEPENDENT_AUDIT" in text
    assert "OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM" in text
    assert "NOT_YET_DISCRIMINATING" in text
    a = _load(AUDIT_READY)
    assert not any(
        p.startswith(("results/audit/evaluation/", "reports/audit/evaluation/"))
        for p in a["write_scope"]["porcelain"]
    )
