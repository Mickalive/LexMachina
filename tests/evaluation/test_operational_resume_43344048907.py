#!/usr/bin/env python3
"""Regression locks for the operational resume of run 43342851837.

Executed under pytest where it exists and under the lane's
``evaluation.no_pytest_runner`` shim where it does not (the producer image has
no pytest - standing disclosure).

What is locked
--------------
1. The two files the resumed run wrote into the independent auditor's
   namespace are relocated byte-identically into the lane's namespace and the
   originals are RETAINED (AGENTS.md items 5-6; append-only evidence).
2. The producer-authored ``results/audit/evaluation/CYCLE_43342851837_GATE.json``
   is disclosed everywhere it is cited as NOT an independent audit, and this
   resume wrote nothing of its own into ``results/audit/`` or ``reports/audit/``.
3. The claim-bearing record of 43342851837 was not rewritten (F-3B: a file
   named for run X holds run X's measurement).
4. Both state files stay internally consistent after the resume update:
   ``evidence_refs_n == len(evidence_refs)``, every ref resolves, and the
   parity fields agree.
5. The resume verification instrument still reports all four frozen
   hypotheses holding.

stdlib only; no network; no product import; no frozen bar, rubric, threshold
or verdict contract is touched.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RUN_ID = "43344048907"
RESUMED = "43342851837"
RECOVERY = _REPO_ROOT / "results" / "evaluation" / f"audit_namespace_recovery_{RUN_ID}"
OUT_DIR = _REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
STATE_ROOT = _REPO_ROOT / "state" / "evaluation.json"
STATE_LANE = _REPO_ROOT / "evaluation" / "state" / "evaluation.json"
ORIGINAL_RECORD = (_REPO_ROOT / "results" / "evaluation" /
                   "minimal_ca_falsify_benchmark" / f"{RESUMED}.json")
ORIGINAL_RECORD_SHA = "8c0178a2a0bbf6e52784581edd307634879533bd16374232b468e38cae77941f"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_relocation_copies_are_byte_identical_and_originals_retained():
    rec = _load(RECOVERY / "RELOCATION_RECORD.json")
    assert rec["originals_retained"] is True
    assert rec["originals_deleted"] is False
    assert rec["originals_edited"] is False
    assert rec["independent_audit_provenance"] is False
    assert rec["verdict"] == "RELOCATED_APPEND_ONLY"
    assert rec["items"], "relocation recorded no items"
    for item in rec["items"]:
        src = _REPO_ROOT / item["source_path"]
        dst = _REPO_ROOT / item["copy_path"]
        assert src.is_file(), f"original deleted: {item['source_path']}"
        assert dst.is_file(), f"copy missing: {item['copy_path']}"
        assert _sha(src) == _sha(dst) == item["source_sha256_before"], (
            f"copy is not byte-identical to the original: {item['copy_path']}")
    assert all(c["passed"] for c in rec["checks"]), rec["checks"]


def test_pseudo_gate_is_disclosed_as_not_an_independent_audit():
    rec = _load(RECOVERY / "RELOCATION_RECORD.json")
    status = rec["independent_audit_status_of_43342851837"]
    assert status["audit_job_conclusion"] == "skipped"
    assert status["requirement_4_half_i"] is False
    assert status["requirement_4_half_ii"] is False
    assert "PRODUCER-AUTHORED" in status["conclusion"]
    assert rec["provenance_contradictions_recomputed_this_run"], (
        "the pseudo-gate's provenance contradictions must be recorded")
    for state_path in (STATE_ROOT, STATE_LANE):
        state = _load(state_path)
        block = state.get(f"operational_resume_{RUN_ID}")
        assert block, f"{state_path} has no operational_resume_{RUN_ID} block"
        assert block["failure_diagnosis"]["independent_audit_of_resumed_run_exists"] is False
        assert block["failure_diagnosis"]["requirement_4_both_halves_for_resumed_run"] is False
        assert block["resumed_run_deliverable"]["resumed_run_gate_is_producer_authored"] is True
        assert block["resumed_run_deliverable"]["accepted_as_evidence"] is False
        assert "PRODUCER-AUTHORED" in block["resumed_run_deliverable"]["resumed_run_gate_disposition"]
        assert block["accepted_as_evidence"] is False
        assert block["audit_status"] == "PENDING_INDEPENDENT_AUDIT"


def test_this_resume_wrote_nothing_into_the_audit_namespace():
    for rel in (f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json",
                f"reports/audit/evaluation/CYCLE_{RUN_ID}.md"):
        assert not (_REPO_ROOT / rel).exists(), (
            f"the resume wrote into the independent auditor's namespace: {rel}")
    # the pseudo-gate of the resumed run must still be the ONLY gate file at
    # that path, i.e. it was retained, not replaced by a second writer
    gate = _REPO_ROOT / f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json"
    assert gate.is_file()
    assert _sha(gate) == _load(RECOVERY / "RELOCATION_RECORD.json")["items"][0]["source_sha256_before"]


def test_claim_bearing_original_record_was_not_rewritten():
    freeze = _load(_REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json")
    pinned = freeze["snapshot_inputs"]["files"][
        f"results/evaluation/minimal_ca_falsify_benchmark/{RESUMED}.json"]
    assert _sha(ORIGINAL_RECORD) == pinned == ORIGINAL_RECORD_SHA
    cmp_rec = _load(OUT_DIR / f"replay_comparison_{RUN_ID}.json")
    assert cmp_rec["claim_bearing_original_rewritten"] is False
    assert cmp_rec["verdict"] == "REPLAY_REPRODUCES"
    assert cmp_rec["measurement_fields_differing"] == 0


def test_state_files_stay_consistent_after_the_resume_update():
    root, lane = _load(STATE_ROOT), _load(STATE_LANE)
    for label, state in (("root", root), ("lane", lane)):
        refs = state.get("evidence_refs")
        assert isinstance(refs, list), f"{label}: evidence_refs missing"
        assert state.get("evidence_refs_n") == len(refs), (
            f"{label}: evidence_refs_n {state.get('evidence_refs_n')} != {len(refs)}")
        missing = [r for r in refs
                   if not (_REPO_ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing, f"{label}: unresolving evidence_refs {missing[:5]}"
        assert state.get("direction_version") == 68
        assert state.get("github_run") == int(RUN_ID)
        assert state.get("proposed_run_id") == int(RUN_ID)
        assert state.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
    for field in ("accepted_run_id", "direction_version", "github_run"):
        assert root.get(field) == lane.get(field), f"parity broken on {field}"


def test_verification_record_holds_all_four_frozen_hypotheses():
    rec = _load(OUT_DIR / f"verification_{RUN_ID}.json")
    assert rec["verdict"] == "RESUME_VERIFIED_AUDIT_READY", rec.get("n_failed")
    assert rec["n_failed"] == 0
    assert rec["n_hypotheses_holding"] == 4
    assert rec["failure_mode_of_resumed_run"] == "VALIDATION_LANE_WRITE_SCOPE_ENFORCEMENT"
    assert rec["independent_audit_of_resumed_run_exists"] is False
    assert rec["claim_ceiling"].startswith("Operational-resume verification only")
