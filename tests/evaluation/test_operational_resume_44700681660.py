"""Regression guard for the 44700681660 operational-resume deliverable.

Pins the claimed failure diagnosis and that all accepted reference hashes and
freeze inputs still resolve and match, so a later cycle cannot silently rewrite
this operational record or edit a frozen reference to obtain a pass.
"""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "44700681660"


def _sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def test_snapshot_and_gate_facts():
    result = json.loads((ROOT / f"results/evaluation/operational_resume_{RUN}/{RUN}.json").read_text())
    assert result["run_id"] == 44700681660
    assert result["resumes_snapshot_of_run"] == 44693400630
    assert result["snapshot_head"] == "ab5c822c7a33324bc2c9e99023d4835cfe38bf70"
    assert result["accepted_run_id"] == 40265377500
    assert result["direction_version"] == 68
    assert result["accepted_head_both_halves"]["half_i_audit_gate"]["gate"] == "PASS"
    assert result["accepted_head_both_halves"]["half_ii_accept_commit"]["passed"] is True
    assert result["failure_diagnosis"]["classification"] == "ORCHESTRATION_REDERIVATION_ZERO_DELTA"
    assert result["failure_diagnosis"]["n_head_changed_files"] == 5
    assert result["ordered_work"]["all_pins_match"] is True
    assert result["ordered_work"]["item_1"]["status"] == "DISCHARGED_ELSEWHERE_HASH_VERIFIED_NOT_RERUN"
    assert result["ordered_work"]["item_2"]["status"] == "NOT_YET_DISCRIMINATING"
    assert result["posture"]["human_gate_ready"] is False
    assert result["posture"]["owner_decision_required"] is False


def test_frozen_references_unedited():
    assert _sha("evaluation/frozen_bars/RULES_LABEL.json") == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert _sha("evaluation/frozen_bars/RULES_GEOMETRY.json") == \
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    assert _sha("evaluation/fast_mvp_retrieval_recall_benchmark.py") == \
        "fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283"


def test_freeze_pins_instrument():
    freeze = json.loads((ROOT / "evaluation/OPERATIONAL_RESUME_44700681660_FREEZE_V1.json").read_text())
    assert freeze["direction_version"] == 68
    assert freeze["failed_run"] == 44693400630
    assert freeze["instrument_sha256"] == \
        _sha("evaluation/operational_resume_44700681660.py")
    assert freeze["hypothesis_sha256"] == \
        _sha("evaluation/OPERATIONAL_RESUME_44700681660_HYPOTHESIS_V1.json")


def test_failed_run_files_preserved():
    d = json.loads((ROOT / f"results/evaluation/operational_resume_{RUN}/run_44693400630_failure_diagnosis.json").read_text())
    files = d["head_commit_changed_files"]
    assert len(files) == 5
    assert all("44686020252" in f for f in files)
    assert all((ROOT / f).is_file() for f in files)
    assert d["all_changes_named_for_prior_run"] is True
    assert d["prior_run_rederived"] == 44686020252
