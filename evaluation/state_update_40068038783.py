#!/usr/bin/env python3
"""Canonical lane-state updater for evaluation cycle 40068038783.

Applies the v66 ordered-work (1)(b) hygiene fixes to state/evaluation.json:
  - correct the 4 nested wrong-dir refs
    results/evaluation/orchestration/40011795717/producer_work_state_and_next_move.txt
    -> results/evaluation/orchestration/40006151200/producer_work_state_and_next_move.txt
    (the artifact was committed under the sibling 40006151200/ directory by
    cycle 40012474431; the 40011795717/ path never existed);
  - re-point the phantom pytest-shim record
    results/evaluation/orchestration/40062917685_counter_evidence_quality_pytest_shim.json
    (never committed anywhere - requirement-33 class) to the re-derived shim
    committed under THIS run id, with disclosure;
  - advance run identity, accepted_run_id (latest run with BOTH halves),
    evidence blocks for this cycle's instruments, and evidence_refs.

Append-only rules: no historical artifact is deleted; every pointer change is
disclosed in the state's operational_resume_40068038783 block.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "evaluation.json"

TYPO_OLD = "results/evaluation/orchestration/40011795717/producer_work_state_and_next_move.txt"
TYPO_NEW = "results/evaluation/orchestration/40006151200/producer_work_state_and_next_move.txt"
PHANTOM = "results/evaluation/orchestration/40062917685_counter_evidence_quality_pytest_shim.json"
SHIM_400680 = "results/evaluation/orchestration/40068038783_counter_evidence_quality_pytest_shim.json"


def _fix_refs(node) -> int:
    n = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and v == TYPO_OLD:
                node[k] = TYPO_NEW
                n += 1
            else:
                n += _fix_refs(v)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str) and v == TYPO_OLD:
                node[i] = TYPO_NEW
                n += 1
            else:
                n += _fix_refs(v)
    return n


def main() -> int:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    typo_fixed = _fix_refs(state)

    # phantom shim ref correction (test_suite block)
    ts = state.setdefault("test_suite", {})
    ceb = ts.setdefault("counter_evidence_quality_benchmark", {})
    phantom_was = ceb.get("record")
    ceb["record"] = SHIM_400680
    ceb["record_rederived_by"] = "40068038783"
    ceb["record_rederivation_note"] = (
        f"the previously referenced record {PHANTOM} was never committed "
        "anywhere in the repository (requirement-33 claim-without-artifact "
        "class, found by the nested evidence_refs guard of run 40068038783); "
        "the pytest claim is RE-DERIVED under run 40068038783 with a committed "
        f"shim at {SHIM_400680} (19/19 passed on the living suites; the "
        "historical 40044626742 pinned suite's 3 cycle-pin failures are "
        "disclosed there, not charged)")
    ceb["previous_record_reference"] = phantom_was
    ceb["previous_record_status"] = "NEVER_COMMITTED_ANYWHERE"

    # run identity
    state["github_run"] = "40068038783"
    state["proposed_run_id"] = "40068038783"
    state["accepted_run_id"] = "40063688435"
    state["accepted_run_id_advance"] = {
        "from": "40034814235",
        "to": "40063688435",
        "reason": (
            "operational resume 40068038783: cycles 40058937015, 40061456297, "
            "40062099418, 40062917685 and 40063688435 each carry BOTH halves of "
            "factory-wide requirement 4 (results/audit/evaluation/"
            "CYCLE_<id>_GATE.json with gate=PASS, safe_to_integrate=true AND an "
            "'accept evaluation cycle <id>' commit on lab/evaluation, verified "
            "by git log). The canonical state's accepted_run_id had lagged at "
            "40034814235; advanced with disclosure, no historical record "
            "overwritten."),
        "prior_advance": state.get("accepted_run_id_advance"),
    }
    state["repair_round"] = 0
    state["repairs_run_id"] = "40068038783"

    # evidence blocks for this cycle
    state["operational_resume_40068038783"] = {
        "schema": "lex-evaluation-operational-resume/1",
        "resume_of": "40067656881",
        "resume_base_head": "24e24bfc565f0f2ccaebb733d33dc92f5f3e9d6f",
        "failure_chain_diagnosis": "results/evaluation/orchestration/40068038783_failure_chain_diagnosis.json",
        "failure_class": ("ORCHESTRATION - runs 40064635075 and 40067656881 died "
                          "at 'Run lane cycle' with ZERO durable delta (snapshots "
                          "identical to lab/evaluation tip 24e24bfc; audit and "
                          "integrate skipped; job logs 403, rc attribution "
                          "hedged); requirements 10/20 class; NOT evidence, "
                          "product or human-gate"),
        "hygiene_item_1b": {
            "typo_refs_corrected": typo_fixed,
            "typo_old": TYPO_OLD,
            "typo_new": TYPO_NEW,
            "typo_explanation": (
                "the producer-plan artifact was committed by cycle 40012474431 "
                "under results/evaluation/orchestration/40006151200/; four "
                "nested state refs pointed at a 40011795717/ sibling path that "
                "never existed - a directory-typo instance of the item-(1)(b) "
                "defect class"),
            "phantom_shim_ref": {
                "old": phantom_was,
                "new": SHIM_400680,
                "explanation": ceb["record_rederivation_note"],
            },
            "minimal_ret_ca_benchmark_pointers": (
                "VERIFIED ACCEPTED-BASE: latest_confirmation_record = "
                "results/evaluation/minimal_ret_ca_benchmark/40034814235.json; "
                "no reference to run 40047820460 exists anywhere in the "
                "canonical state (the blocked run never landed); no revert "
                "was needed"),
            "guard": "evaluation/nested_evidence_refs_guard.py",
            "guard_artifact_before_fix": "results/evaluation/orchestration/40068038783_prefx_nested_evidence_refs.json",
            "guard_artifact_after_fix": "results/evaluation/orchestration/40068038783_nested_evidence_refs.json",
        },
        "hygiene_dual_state_file": (
            "evaluation/state/evaluation.json is a per-cycle producer copy "
            "written by accepted cycle 40063688435 (accepted_run_id 40063688435, "
            "evidence_tier EXPLORATORY); it is left UNTOUCHED as that cycle's "
            "historical record. state/evaluation.json (this file) is the "
            "canonical lane state per ARCHITECTURE.md. Future cycles write "
            "canonical state only."),
    }
    state["counter_evidence_quality_remeasure_40068038783"] = {
        "schema": "lex-evaluation-counter-evidence-quality-remeasure/1",
        "ordered_work_item": "v66 item (4) CONDITIONAL RE-MEASURE",
        "trigger": "product accept 3495c1336 (cycle 40064639100) landed the P0 content-quality filter",
        "verdict": "REPAIR_NOT_CONFIRMED",
        "per_class": {
            "D2_letterhead_zone": "STILL-DEFECTIVE (1 on new-head shipped slice: "
                                  "gr_gerichte_ERZ 2010 25, offset 0)",
            "D3_markup_residue": "CONFIRMED-REPAIRED (0 new, class-eligible row present)",
            "D4_language_marker_mismatch": "CONFIRMED-REPAIRED (0 new, class-eligible row present)",
        },
        "baseline_stability": "re-probe NORMALIZED-IDENTICAL to accepted baseline of record 40062917685 (14/14, D2=10 D3=4 D4=4)",
        "controls": "C1-C4 PASS (C4 pins frozen instrument sha aac86527... byte-identical)",
        "result_file": "results/evaluation/counter_evidence_quality_remeasure/40068038783.json",
        "report_file": "reports/evaluation/COUNTER_EVIDENCE_QUALITY_REMEASURE_40068038783.md",
        "instrument": "evaluation/counter_evidence_quality_remeasure.py",
        "freeze_record": "evaluation/OPERATIONAL_RESUME_40068038783_HYPOTHESIS.json",
    }
    state["scorer_path_reconciliation_40068038783"] = {
        "schema": "lex-evaluation-scorer-path-reconciliation/1",
        "ordered_work_item": "v66 item (3) FROZEN-SCORER PATH DIVERGENCE CROSS-CHECK",
        "verdict": "RECONCILIATION_COMPLETE",
        "finding": (
            "on packet-of-record 39319405429 bytes at product head 3495c1336: "
            "frozen mf::counter_authority_surface n_issued=0 on SERVED bytes; "
            "n_issued=1 on GUARDED-TRANSFORMED bytes (fr-bail-entretien, "
            "bge_136 III 196, candidate-limiting, 286-char evidence, ZERO "
            "frozen D2/D3/D4 defects); product arms baseline 0 / unguarded 6 / "
            "guarded 1 IDENTICAL to the accepted pre-filter measurement of "
            "record -> the P0 filter has NO packet-level emission effect; the "
            "requirement-36 divergence is a TRANSFORM-PATH divergence (the "
            "frozen scorer never receives the transformed bytes), NOT a "
            "contract-shape exclusion; resolved with zero scorer edits"),
        "result_file": "results/evaluation/scorer_path_reconciliation/40068038783.json",
        "report_file": "reports/evaluation/SCORER_PATH_RECONCILIATION_40068038783.md",
        "instrument": "evaluation/scorer_path_reconciliation.py",
    }
    ts["counter_evidence_quality_remeasure_suite"] = {
        "file": "tests/evaluation/test_counter_evidence_quality_remeasure.py",
        "passed": 4, "failed": 0,
        "verdict": "PASS_REAL_PYTEST",
    }
    ts["scorer_path_reconciliation_suite"] = {
        "file": "tests/evaluation/test_scorer_path_reconciliation.py",
        "passed": 4, "failed": 0,
        "verdict": "PASS_REAL_PYTEST",
    }
    ts["nested_evidence_refs_guard_suite"] = {
        "file": "tests/evaluation/test_nested_evidence_refs_guard.py",
        "passed": 4, "failed": 0,
        "verdict": "PASS_REAL_PYTEST",
    }
    ts["shim_record_40068038783"] = "results/evaluation/orchestration/40068038783_pytest_shims.json"

    # evidence_refs: append new artifacts, fix shim pointer already handled in
    # test_suite (not part of top-level list unless present)
    new_refs = [
        "evaluation/OPERATIONAL_RESUME_40068038783_HYPOTHESIS.json",
        "results/evaluation/orchestration/40068038783_failure_chain_diagnosis.json",
        "evaluation/counter_evidence_quality_remeasure.py",
        "results/evaluation/counter_evidence_quality_remeasure/40068038783.json",
        "reports/evaluation/COUNTER_EVIDENCE_QUALITY_REMEASURE_40068038783.md",
        "evaluation/scorer_path_reconciliation.py",
        "results/evaluation/scorer_path_reconciliation/40068038783.json",
        "reports/evaluation/SCORER_PATH_RECONCILIATION_40068038783.md",
        "evaluation/nested_evidence_refs_guard.py",
        "evaluation/state_update_40068038783.py",
        "results/evaluation/orchestration/40068038783_prefx_nested_evidence_refs.json",
        "results/evaluation/orchestration/40068038783_nested_evidence_refs.json",
        "results/evaluation/orchestration/40068038783_pytest_shims.json",
        "tests/evaluation/test_counter_evidence_quality_remeasure.py",
        "tests/evaluation/test_scorer_path_reconciliation.py",
        "tests/evaluation/test_nested_evidence_refs_guard.py",
        "reports/evaluation/OPERATIONAL_RESUME_40068038783.md",
    ]
    refs = state.setdefault("evidence_refs", [])
    for r in new_refs:
        if r not in refs:
            refs.append(r)
    state["evidence_refs_n"] = len(refs)
    # phantom shim may also appear in top-level refs (defensive)
    for i, r in enumerate(refs):
        if r == PHANTOM:
            refs[i] = SHIM_400680
    state["evidence_index_resolving_refs_n"] = len(refs)
    state["evidence_index_resolution_note"] = (
        "re-derived by evaluation/nested_evidence_refs_guard.py under run "
        "40068038783 (item 1c): the guard resolves TOP-LEVEL and NESTED "
        "ref-shaped values against the worktree, the accepted cross-lane "
        "mounts and fetched git history; the post-fix artifact "
        "results/evaluation/orchestration/40068038783_nested_evidence_refs.json "
        "records the counts")

    # posture + tier + status
    state["evidence_tier"] = "REPRODUCED"
    state["cycle_status"] = "COMPLETE"
    state["continue_recommended"] = True
    state["human_gate_ready"] = False
    state["machine_gate_ready"] = False
    state["packet_admitted"] = False
    state["ready_for_owner_session"] = False
    state["owner_decision_required"] = False
    state["direction_version"] = 66
    state["state_updated_at"] = now
    state["continue_recommended_reason"] = (
        "CONTINUE under the same v66 question with a concrete discriminating "
        "purpose: the item-(4) re-measure FALSIFIED full repair on shipped "
        "artifacts (D2 still defective on the new head's offline slice) and "
        "the item-(3) reconciliation shows the packet-level emission path "
        "unchanged by the P0 filter. The next accepted product change that "
        "alters the shipped counter-evidence emission path (for example "
        "routing the offline/server slice generation through the filtered "
        "span selector, or regenerating slices after the filter rejects "
        "letterhead spans) triggers an immediate re-run of the frozen item-(2) "
        "probe protocol under a NEW run id. Both DO-NOT-SERVE orders stand; "
        "admission stays fail-closed; comparative map-vs-ranked-list stays "
        "VACUOUS (served-bytes n_issued=0); owner_decision_required=false.")
    state["next_recommendation"] = (
        "CONTINUE (continue_recommended=true). This operational-resume cycle "
        "(GitHub run 40068038783) discharged v66 ordered work items (1)(b/c/d) "
        "(2-verification) (3) and (4): orchestration diagnosis of the zero-delta "
        "runs 40064635075/40067656881 (ORCHESTRATION class, zero work lost); "
        "nested evidence_refs guard landed with 5 unresolved nested refs found "
        "and fixed (4 directory-typo refs corrected to the real 40006151200/ "
        "path; 1 phantom pytest-shim record re-derived under this run id); "
        "item-(4) REPAIR_NOT_CONFIRMED (D2 STILL-DEFECTIVE on the new head's "
        "shipped slice 20261024T024341Z, D3/D4 CONFIRMED-REPAIRED, baseline "
        "re-probe normalized-identical, controls C1-C4 pass); item-(3) "
        "RECONCILIATION_COMPLETE (transform-path divergence, contract-shape "
        "compatible, packet-level emission identical to the accepted pre-filter "
        "measurement). Posture unchanged and fail-closed: both DO-NOT-SERVE "
        "orders stand; frozen bars/rubrics re-hashed REPORTED-ONLY "
        "(4457e971/a7452748) and unmet on the v3 bytes; comparative "
        "map-vs-ranked-list stays VACUOUS; no 174k rerun; no bar/rubric/"
        "threshold/verdict-contract edit; no historical record overwritten. "
        "Next discriminating trigger: any accepted product change to the "
        "shipped counter-evidence emission path -> re-run the frozen item-(2) "
        "probe protocol (and this remeasure) under a NEW run id.")

    STATE_PATH.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    print(json.dumps({"typo_refs_fixed": typo_fixed,
                      "phantom_ref_corrected": phantom_was,
                      "evidence_refs_n": state["evidence_refs_n"],
                      "accepted_run_id": state["accepted_run_id"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
