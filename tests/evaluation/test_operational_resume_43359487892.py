#!/usr/bin/env python3
"""Regression locks for the operational resume of run 43357838904 (run 43359487892).

Executed under pytest where it exists and under the lane's
``evaluation.no_pytest_runner`` shim where it does not (the producer image has
no pytest - standing disclosure).

What is locked
--------------
1. Run 43357838904 is locked as a zero-delta lane-cycle failure, and run
   43349645400 as the write-scope failure with exactly its two producer
   pseudo-audit paths.
2. The four inherited producer-authored files are copied byte-identically into
   the lane namespace with originals retained, and are disclosed everywhere as
   NOT independent audits.
3. The claim-bearing FAST-MVP record of 43342851837 was not rewritten, its
   pins still match, and its scratch replay reproduces all 41 measurement
   fields.
4. Ordered item (2) is still NOT_YET_DISCRIMINATING at the accepted product
   head (zero-delta family, 14/15 role ceiling).
5. Both state files stay internally consistent after the resume update and the
   resume block carries a pending-independent-audit disclosure.

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

RUN_ID = "43359487892"
RESUMED = "43357838904"
BASE_RUN = "43349645400"
ORIGINAL = "43342851837"
OUT_DIR = _REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
RECOVERY = _REPO_ROOT / "results" / "evaluation" / f"audit_namespace_recovery_{RUN_ID}"
STATE_ROOT = _REPO_ROOT / "state" / "evaluation.json"
STATE_LANE = _REPO_ROOT / "evaluation" / "state" / "evaluation.json"
FREEZE = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
ORIGINAL_RECORD = (_REPO_ROOT / "results" / "evaluation" /
                   "minimal_ca_falsify_benchmark" / f"{ORIGINAL}.json")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_zero_delta_lane_cycle_failure_is_recorded():
    d = _load(OUT_DIR / f"diagnosis_{RESUMED}.json")
    assert d["failing_steps"] == ["Run lane cycle"]
    assert d["audit_conclusion"] == "skipped"
    assert d["integrate_conclusion"] == "skipped"
    assert d["delta_against_base_run"] == ""
    assert d["snapshot_refs"][f"refs/heads/cycle/core/evaluation/{RESUMED}/team"] == \
        d["snapshot_refs"][f"refs/heads/cycle/core/evaluation/{BASE_RUN}/team"]


def test_write_scope_failure_has_exactly_two_producer_pseudo_audit_paths():
    d = _load(OUT_DIR / f"diagnosis_{BASE_RUN}.json")
    assert d["failing_steps"] == ["Enforce lane write scope"]
    assert d["bad_paths"] == sorted([
        f"reports/audit/evaluation/CYCLE_{BASE_RUN}.md",
        f"results/audit/evaluation/CYCLE_{BASE_RUN}_GATE.json",
    ])
    assert d["audit_ref_present"] == {
        "43342851837": False, "43344048907": False,
        "43349645400": False, "43357838904": False,
    }
    assert all(v["producer_authored"] for v in d["provenance_of_inherited_files"].values())


def test_relocation_is_byte_identical_append_only_and_disclosed():
    rec = _load(RECOVERY / f"RELOCATION_RECORD_{RUN_ID}.json")
    assert rec["verdict"] == "RELOCATED_APPEND_ONLY"
    assert rec["originals_retained"] is True
    assert rec["originals_deleted"] is False
    assert rec["originals_edited"] is False
    assert rec["independent_audit_provenance"] is False
    assert len(rec["items"]) == 4
    for item in rec["items"]:
        src = _REPO_ROOT / item["source_path"]
        dst = _REPO_ROOT / item["copy_path"]
        assert src.is_file(), item["source_path"]
        assert dst.is_file(), item["copy_path"]
        assert _sha(src) == _sha(dst) == item["copy_sha256"]
        src_rel = src.relative_to(_REPO_ROOT)
        assert src_rel.parts[1:3] == ("audit", "evaluation")  # original stays put
    assert len(rec["contradictions"]) >= 3


def test_deliverable_pins_and_record_are_unchanged():
    freeze = _load(FREEZE)["rehash_before_execution"]["deliverable"]
    for rel, digest in freeze.items():
        assert _sha(_REPO_ROOT / rel) == digest, rel
    record = _load(ORIGINAL_RECORD)
    assert record["verdict"] == "PRODUCT_FALSIFIED"
    assert record["exit_code"] == 1
    assert [record[k] for k in ("n_gates", "n_passed", "n_failed", "n_reported")] == [18, 11, 4, 3]
    assert record["run_valid"] is True
    assert record["input_drift"] == []


def test_replay_reproduces_every_measurement_field():
    cmp = _load(OUT_DIR / f"replay_comparison_{RUN_ID}.json")
    assert cmp["verdict"] == "REPLAY_REPRODUCES"
    assert cmp["measurement_fields_compared"] == 41
    assert cmp["measurement_fields_differing"] == 0
    assert cmp["measurement_differences"] == []
    assert list(cmp["environment_disclosure_differences"]) == ["numeric_environment"]
    assert _sha(ORIGINAL_RECORD) == _load(FREEZE)["rehash_before_execution"][
        "deliverable"][str(ORIGINAL_RECORD.relative_to(_REPO_ROOT))]


def test_item2_is_still_not_yet_discriminating():
    rec = _load(OUT_DIR / f"item2_family_gate_{RUN_ID}.json")
    assert rec["status"] == "NOT_YET_DISCRIMINATING"
    assert rec["product"]["head"] == "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
    assert rec["zero_delta_check"]["byte_identical_n"] == 50
    assert rec["zero_delta_check"]["differing"] == []
    assert rec["role_cardinality"]["role_parity"] is False
    assert rec["role_cardinality"]["member_for_member_ceiling"] == 14
    assert rec["role_cardinality"]["frozen_family_n"] == 15


def test_state_files_stay_consistent_and_disclose_pending_audit():
    root, lane = _load(STATE_ROOT), _load(STATE_LANE)
    for state in (root, lane):
        assert state["evidence_refs_n"] == len(state["evidence_refs"])
        for ref in state["evidence_refs"]:
            assert (_REPO_ROOT / ref.split(" ")[0].rstrip(",")).is_file(), ref
        assert state["github_run"] == int(RUN_ID)
        block = state[f"operational_resume_{RUN_ID}"]
        assert block["claim_bearing_run"] == RUN_ID
        assert block["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
        assert block["pending_independent_audit"] is True
        assert block["accepted_as_evidence"] is False
    for field in ("accepted_run_id", "direction_version", "github_run"):
        assert root[field] == lane[field], field
    assert root["accepted_run_id"] == 40265377500
    assert root["direction_version"] == 68


def test_claim_bearing_original_is_not_named_as_an_audit():
    rec = _load(OUT_DIR / f"diagnosis_{BASE_RUN}.json")
    assert rec["failure_class"] == "WRITE_SCOPE_VIOLATION_PRODUCER_AUDIT_NAMESPACE"
    report = (_REPO_ROOT / "reports" / "evaluation" /
              f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md").read_text(encoding="utf-8")
    assert "not an independent audit" in report.lower() or "not** an audit" in report.lower()
    assert "producer-authored" in report.lower()
