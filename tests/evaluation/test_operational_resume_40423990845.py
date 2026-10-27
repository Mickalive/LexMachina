"""Regression guards for the 40423990845 operational-resume records.

These tests do not execute the benchmark. They pin the committed record of the
resume: the failure diagnosis, the snapshot identity, the artifact-vs-audit
mismatch, the replay result, the item-(2) precondition and the additive state.
They skip cleanly before the records exist (for example on a fresh checkout that
has not run the instrument).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/evaluation/operational_resume_40423990845"
RUN = "40423990845"
RESUMED = "40423855962"


def _load(name: str):
    path = OUT / name
    if not path.is_file():
        pytest.skip(f"resume record not generated yet: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_diagnosis_is_the_model_health_pre_agent_exit():
    rec = _load(f"diagnosis_{RESUMED}.json")
    assert rec["verdict"] == "DIAGNOSIS_CONFIRMED"
    assert rec["failure_class"] == "ORCHESTRATION_MODEL_HEALTH_PRE_AGENT"
    assert rec["model_health"]["run_head"]["resolver_exit_code"] == 76
    assert rec["model_health"]["control_plane_head"]["resolver_exit_code"] == 0
    assert rec["audit_branch_probe"]["exists"] is False
    assert rec["step_durations_seconds"]["run_lane_cycle"] < 120.0


def test_snapshot_is_the_accepted_base_with_no_run_work():
    rec = _load(f"snapshot_{RESUMED}.json")
    assert rec["verdict"] == "SNAPSHOT_PRESERVED_ON_ACCEPTED_BASE"
    assert rec["snapshot_commit"] == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
    assert rec["lab_evaluation_commit"] == rec["snapshot_commit"]
    assert rec["snapshot_subject"] == "accept evaluation cycle 40265377500"
    assert rec["audit_branch"]["exists"] is False


def test_deliverable_verification_keeps_the_clean_accept_and_flags_the_mismatch():
    rec = _load(f"deliverable_verification_{RUN}.json")
    assert rec["verdict"] == "DELIVERABLE_VERIFIED_WITH_AUDIT_MISMATCH"
    clean = rec["last_clean_accepted_cycle"]
    assert clean["run"] == 40258497460
    assert clean["accepted_as_evidence"] is True
    struct = rec["structurally_accepted_cycle"]
    assert struct["run"] == 40265377500
    assert struct["accepted_as_evidence"] is False
    assert struct["artifact_verdict"] == "PRODUCT_FALSIFIED"
    assert struct["audit_gate_verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert all(struct["mismatch_markers"].values())
    assert rec["pending_cycle"]["run"] == 40261335674
    assert rec["pending_cycle"]["accepted_as_evidence"] is False
    assert rec["ordered_item_1"]["machine_verdict"] == "CORRECTION_NOT_CONFIRMED"


def test_replay_reproduces_the_committed_artifact():
    rec = _load(f"benchmark_replay_comparison_{RUN}.json")
    assert rec["verdict"] == "REPLAY_REPRODUCES"
    assert set(rec["diff_keys"]) <= {
        "run_id", "generated_at_utc", "product_mount", "engine_record_path"}
    assert rec["product_mount_head"] == "f9b0db254dc22a46a240c7937fd75e3eb2ec2e95"
    assert rec["n_failed"] == 0


def test_item2_precondition_is_not_yet_discriminating():
    rec = _load(f"item2_precondition_{RUN}.json")
    assert rec["verdict"] == "NOT_YET_DISCRIMINATING"
    matching = rec["member_for_member_matching"]
    assert matching["matched_members"] == 14
    assert matching["of"] == 15
    assert matching["matched_per_role"]["server/served"] == 3
    assert rec["H2_precondition_full_family_regenerated"] is False


def test_frozen_hypothesis_hash_matches_the_freeze_record():
    freeze_path = ROOT / "evaluation/OPERATIONAL_RESUME_40423990845_FREEZE_V1.json"
    hyp_path = ROOT / "evaluation/OPERATIONAL_RESUME_40423990845_HYPOTHESIS_V1.json"
    if not freeze_path.is_file() or not hyp_path.is_file():
        pytest.skip("freeze records not present")
    import hashlib

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    got = hashlib.sha256(hyp_path.read_bytes()).hexdigest()
    assert freeze["hypothesis"]["sha256"] == got


def test_state_keeps_the_accepted_pointer_and_adds_the_resume_block():
    for rel in ("state/evaluation.json", "evaluation/state/evaluation.json"):
        path = ROOT / rel
        state = json.loads(path.read_text(encoding="utf-8"))
        assert state["accepted_run_id"] == 40258497460
        assert state["github_run"] == 40423990845
        assert state["resumed_run_id"] == 40423855962
        assert state["continue_recommended"] is False
        block = state["operational_resume_40423990845"]
        assert block["run"] == 40423990845
        assert block["accepted_run_id_unchanged"] == 40258497460
        assert block["state_pointer_advanced"] is False
        assert state["evidence_refs_n"] == len(state["evidence_refs"])


def test_no_audit_namespace_file_is_modified_by_this_run():
    proc = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0
    bad = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip()
        if path.startswith("results/audit/") or path.startswith("reports/audit/"):
            bad.append(path)
    assert bad == [], f"producer wrote the auditor namespace: {bad}"
