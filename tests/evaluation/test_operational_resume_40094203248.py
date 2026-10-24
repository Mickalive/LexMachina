"""Tests for the operational resume of run 40089391202 (resume run 40094203248).

Pins the resume's durable invariants:
  1. the committed 40089391202 item-(1) deliverable VERIFIED as REPRODUCES by
     the frozen comparison contract (artifact committed under this run id);
  2. the finishable state-hygiene repair landed: no phantom
     local_eval_20261024T102833Z keys remain in evidence_ref_role_notes;
  3. canonical state carries this run's identity with disclosure, keeps
     accepted_run_id=40084716045 and the fail-closed posture flags;
  4. the frozen instrument digest is still the accepted one (never edited).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

STATE = json.loads((_REPO_ROOT / "state/evaluation.json").read_text(encoding="utf-8"))
REPRO = json.loads(
    (_REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile"
     / "40094203248_reproduction_check_vs_40089391202.json").read_text(encoding="utf-8"))
PROFILE = json.loads(
    (_REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile"
     / "40089391202.json").read_text(encoding="utf-8"))


def test_reproduction_check_verdict_reproduces():
    assert REPRO["verdict"] == "REPRODUCES"
    assert REPRO["n_mismatches"] == 0
    assert REPRO["n_discrimination_fields_compared"] == 19
    assert REPRO["controls_all_pass"] is True
    assert REPRO["file_byte_identity_claimed"] is False


def test_deliverable_of_record_untouched_and_frozen_instrument_pinned():
    # the resume must not have overwritten the 40089391202 deliverable
    sha = hashlib.sha256(
        (_REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile"
         / "40089391202.json").read_bytes()).hexdigest()
    assert sha == REPRO["resumed_deliverable_of_record"]["sha256"]
    assert PROFILE["frozen_predicate_instrument_sha256"] == (
        "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d")
    inst = hashlib.sha256(
        (_REPO_ROOT / "evaluation/counter_evidence_quality_benchmark.py"
         ).read_bytes()).hexdigest()
    assert inst == "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"


def test_no_phantom_role_note_keys_remain():
    role_notes = STATE.get("evidence_ref_role_notes") or {}
    assert not [k for k in role_notes if "102833Z" in k]
    # the renamed keys resolve on disk
    for k in role_notes:
        if "local_eval_20261024T102500Z" in k or "local_eval_1792837481" in k:
            assert (_REPO_ROOT / k).exists(), k


def test_state_run_identity_and_posture():
    assert STATE["github_run"] == "40094203248"
    assert STATE["operational_resume_of"] == "40089391202"
    assert STATE["direction_version"] == 67
    assert STATE["accepted_run_id"] == "40084716045"
    assert STATE["cycle_status"] == "COMPLETE"
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        assert STATE[flag] is False, flag
    assert STATE["evidence_refs_n"] == len(STATE["evidence_refs"])


def test_evidence_refs_all_resolve_or_are_disclosed():
    disclosed = set(STATE.get("evidence_index_defects_inherited_not_charged",
                              {}).get("known_unresolvable", []))
    missing = [
        r for r in STATE["evidence_refs"]
        if not (_REPO_ROOT / r).exists() and r not in disclosed]
    assert not missing, missing
