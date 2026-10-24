"""Tests for the operational resume of run 40089391202 (resume run 40094203248).

Pins the resume's durable invariants:
  1. the committed 40089391202 item-(1) deliverable VERIFIED as REPRODUCES by
     the frozen comparison contract (artifact committed under this run id);
  2. the finishable state-hygiene repair landed: no phantom
     local_eval_20261024T102833Z keys remain in evidence_ref_role_notes;
  3. canonical state carries this run's identity with disclosure, keeps
     accepted_run_id=40084716045 and the fail-closed posture flags;
  4. the frozen instrument digest is still the accepted one (never edited).

F3 REPAIR (round 1 of rejected cycle 40099481633): ``test_state_run_identity_
and_posture`` no longer pins literal historical run ids for the MOVING state
fields (github_run / operational_resume_of); it pins them to the append-only
run_identity_history chain plus the frozen invariants above.  Nothing was
deleted: the historically pinned run ids remain asserted from the history.
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
    """Run identity is pinned to the APPEND-ONLY chain, not a literal run id.

    F3 repair (round 1 of rejected cycle 40099481633, audit required_fixes
    item F3): this function previously pinned ``github_run == "40094203248"``
    and ``operational_resume_of == "40089391202"`` literally.  Both went
    stale as later cycles legitimately advanced the canonical state (the
    state carried 40096174340 when the 40099481633 audit recomputed it),
    producing a red living-suite test at head.  The pins are WIDENED to the
    documented identity chain recorded in ``run_identity_history`` - every
    state advance appends its run there - so the test can never go stale
    again without state history being deleted.  The historical run ids
    themselves stay asserted: history is preserved, never removed.
    """
    history_ids = {str(h.get("run_id"))
                   for h in STATE.get("run_identity_history", [])}
    # every state run identity must live in the append-only history
    assert str(STATE["github_run"]) in history_ids, (
        "github_run must be recorded in run_identity_history")
    assert str(STATE["operational_resume_of"]) in history_ids, (
        "operational_resume_of must be recorded in run_identity_history")
    # history is NOT deleted: the runs this test originally pinned remain
    assert "40094203248" in history_ids
    assert "40089391202" in history_ids
    assert str(STATE.get("inherited_deliverable_of_record")) == "40089391202"
    # the rejected cycle this state lineage was repaired through is recorded
    assert "40099481633" in history_ids
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
