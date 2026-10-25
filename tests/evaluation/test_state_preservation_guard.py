"""Regression guard for the destructive state-rewrite defect class.

Discharges the durable half of required fix 1 of independent audit
CYCLE_40237863325_GATE.json (gate=REVISE, repair round 0): the rejected
producer commit 5116e644 replaced ``state/evaluation.json`` instead of
updating it, dropping 47 of the 57 accepted-base keys - 30 of them present
in no other file - and shrinking ``evidence_refs`` from 222 to 6.  That is
the defect class AGENTS.md #6 and the Master Prompt forbid (never overwrite
claim-bearing outputs), and nine consecutive earlier producer commits passed
the lane's state-integrity gate before it appeared.

These tests are a STATE-CLAIM guard only.  They never read, re-score or
re-derive a frozen bar, rubric, threshold, gate predicate or verdict
contract; they run no benchmark; they make no product, serve or
human-gate claim.

Convention (deliberate, disclosed): the pinned inventory below is the
ACCEPTED BASE snapshot 1617f224 ("accept evaluation cycle 40234421521").
Removing a key or an evidence ref is therefore impossible without editing
this file explicitly, with the reason recorded in the edit - never silently
by rewriting the state file.  Adding keys and refs is always allowed.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT_STATE = REPO / "state" / "evaluation.json"
LANE_STATE = REPO / "evaluation" / "state" / "evaluation.json"

ACCEPTED_BASE_COMMIT = "1617f224eea229379651bbfa3172e526e5d885ae"
BASE_KEYS = [
    "lane",
    "direction_version",
    "evidence_tier",
    "cycle_status",
    "continue_recommended",
    "accepted_run_id",
    "evidence_refs",
    "evidence_refs_resolution",
    "next_recommendation",
    "metrics_summary",
    "frozen_protocol_digest",
    "fixture_query",
    "fixture_candidate_count",
    "known_relevant_source",
    "known_counter_source",
    "reused_accepted_assets",
    "no_universal_174k_benchmarks",
    "no_network_calls",
    "deterministic_offline_only",
    "v68_correction",
    "open_items",
    "open_items_restoration",
    "evidence_refs_n",
    "github_run",
    "proposed_run_id",
    "audit_status",
    "resumed_run_id",
    "pin_drift_fix",
    "resume_dispatch_path",
    "accepted_run_id_advance",
    "audit_status_scope",
    "current_cycle_audit_status",
    "operational_resume_of",
    "resume_chain",
    "provenance_disclosure",
    "metrics_summary_40168466708",
    "metrics_summary_40171237606",
    "proposed_run_id_previous_40187594111",
    "resumed_run_id_previous_40187594111",
    "operational_resume_40187594111",
    "evidence_index_corrections_40187594111",
    "prior_resumed_run_id",
    "operational_resume_40192868113",
    "v68_item_2_reconciliation_40192868113",
    "operational_resume_40198184759",
    "audit_status_scope_40204378896",
    "network_calls_this_resume",
    "no_network_calls_scope",
    "operational_resume_40204378896",
    "human_gate_ready",
    "machine_gate_ready",
    "resumed_run_id_previous_40209360877",
    "operational_resume_40209360877",
    "operational_resume_40213041041",
    "prior_next_recommendation_40213041041",
    "prior_next_recommendation_40234421521",
    "operational_resume_40234421521",
]
# evidence_refs count of the accepted base (the rejected commit shipped 6)
BASE_EVIDENCE_REFS_N = 222


def _root() -> dict:
    return json.loads(ROOT_STATE.read_text(encoding="utf-8"))


def _lane() -> dict:
    return json.loads(LANE_STATE.read_text(encoding="utf-8"))


def test_no_accepted_base_state_key_was_dropped():
    state = _root()
    missing = [k for k in BASE_KEYS if k not in state]
    assert not missing, (
        "state/evaluation.json dropped accepted-base keys "
        f"({ACCEPTED_BASE_COMMIT}): {missing} - restore them additively, "
        "never replace the file")


def test_the_thirty_keys_present_nowhere_else_are_back():
    # the exact orphan set named by required fix 1 of CYCLE_40237863325
    orphans = [
        "open_items", "open_items_restoration", "provenance_disclosure",
        "evidence_refs_resolution", "metrics_summary",
        "metrics_summary_40168466708", "metrics_summary_40171237606",
        "v68_correction", "network_calls_this_resume", "no_network_calls",
        "no_network_calls_scope", "accepted_run_id_advance",
        "audit_status_scope", "pin_drift_fix", "resume_dispatch_path",
        "human_gate_ready", "machine_gate_ready", "frozen_protocol_digest",
        "fixture_query", "fixture_candidate_count", "known_relevant_source",
        "known_counter_source", "reused_accepted_assets",
        "no_universal_174k_benchmarks", "deterministic_offline_only",
        "proposed_run_id_previous_40187594111",
        "resumed_run_id_previous_40187594111",
        "resumed_run_id_previous_40209360877",
        "operational_resume_40187594111", "evidence_index_corrections_40187594111",
        "v68_item_2_reconciliation_40192868113", "audit_status_scope_40204378896",
        "prior_next_recommendation_40213041041",
        "prior_next_recommendation_40234421521",
    ]
    state = _root()
    missing = [k for k in orphans if k not in state]
    assert not missing, f"orphan claim-bearing keys still missing: {missing}"


def test_evidence_refs_were_never_shrunk_below_the_accepted_base():
    state = _root()
    assert state["evidence_refs_n"] == len(state["evidence_refs"])
    assert len(state["evidence_refs"]) >= BASE_EVIDENCE_REFS_N, (
        "evidence_refs shrank below the accepted-base count "
        f"({BASE_EVIDENCE_REFS_N}); removals must be disclosed, not silent")


def test_the_accepted_38_of_38_record_stays_referenced():
    # required fix 4: the '(38 passed)' clause is backed by this accepted
    # record, reused not re-executed this cycle
    state = _root()
    assert "results/evaluation/test_retrieval_benchmark_40143419165.json" \
        in state["evidence_refs"]
    rec = json.loads(
        (REPO / "results/evaluation/test_retrieval_benchmark_40143419165.json"
         ).read_text(encoding="utf-8"))
    assert rec["total_tests"] == 38 and rec["passed"] == 38 and rec["failed"] == 0


def test_root_and_lane_state_carry_the_same_run_identity():
    root, lane = _root(), _lane()
    for field in ("accepted_run_id", "direction_version", "github_run"):
        assert root[field] == lane[field], field
    assert root["accepted_run_id"] == 40159747851
    assert root["github_run"] == "40237863325"
    assert root["proposed_run_id"] == 40237863325
    assert root["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert root["evidence_tier"] == "ACCEPTED"


def test_every_evidence_ref_resolves_in_the_worktree():
    state = _root()
    missing = [r for r in state["evidence_refs"]
               if not (REPO / str(r).split(" ")[0].rstrip(",")).is_file()]
    assert not missing, f"unresolvable evidence refs: {missing}"
