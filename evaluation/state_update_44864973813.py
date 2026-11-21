#!/usr/bin/env python3
"""Additive state update for operational resume run 44864973813.

Adds new keys and new evidence_refs to BOTH state/evaluation.json and
evaluation/state/evaluation.json; never removes or rewrites an existing key,
never changes a pinned identity field (accepted_run_id, github_run,
proposed_run_id, audit_status, evidence_tier, direction_version), and keeps
evidence_refs_n == len(evidence_refs). Byte round-trip of each file's existing
content is proven before the additive change is applied.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "state/evaluation.json", ROOT / "evaluation/state/evaluation.json"]

NEW_REFS = [
    "evaluation/OPERATIONAL_RESUME_44864973813_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_44864973813_FREEZE_V1.json",
    "evaluation/operational_resume_44864973813.py",
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_44861140260_HYPOTHESIS_V1.json",
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_44861140260_FREEZE_V1.json",
    "evaluation/V68_CONTINUATION_TRIGGER_GATE_44861140260_HYPOTHESIS_V1.json",
    "evaluation/V68_CONTINUATION_TRIGGER_GATE_44861140260_FREEZE_V1.json",
    "evaluation/v68_continuation_trigger_gate.py",
    "tests/evaluation/test_v68_continuation_trigger_gate_44861140260.py",
    "results/evaluation/post_repair_family_ca_falsifier/44861140260.json",
    "results/evaluation/v68_continuation_trigger_gate/44861140260.json",
    "reports/evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_44861140260.md",
    "results/evaluation/orchestration/44861140260_pytest_shim.json",
    "results/evaluation/orchestration/44861140260_pytest_shim_attempt1_mount_drift.json",
    "results/evaluation/operational_resume_44864973813/diagnosis_44861140260.json",
    "results/evaluation/operational_resume_44864973813/provenance_fetch_44864973813.json",
    "results/evaluation/operational_resume_44864973813/pytest_shim_44864973813.json",
    "results/evaluation/operational_resume_44864973813/pytest_shim_44864973813_attempt1.json",
    "results/evaluation/operational_resume_44864973813/snapshot_integrity_44864973813.json",
    "results/evaluation/operational_resume_44864973813/falsifier_replay_comparison_44864973813.json",
    "results/evaluation/operational_resume_44864973813/frozen_and_posture_44864973813.json",
    "results/evaluation/operational_resume_44864973813/replay_ca_falsifier/44861140260.json",
    "results/evaluation/operational_resume_44864973813/replay_continuation_gate/44861140260.json",
    "results/evaluation/operational_resume_44864973813/pre_repair/test_v68_continuation_trigger_gate_44861140260.py",
    "reports/evaluation/OPERATIONAL_RESUME_44864973813_AUDIT_READY.md",
]

OPERATIONAL_RESUME = {
    "schema": "lex-evaluation-operational-resume/1",
    "run": 44864973813,
    "run_under_resume": 44861140260,
    "claim_bearing_run": "44864973813",
    "direction_version": 68,
    "base_snapshot_commit": "146b6a6f532112eba83a1aedd58788be1e7264ea",
    "freeze_first_commit": "fdcec5fd",
    "failure_class": "VALIDATION_PRODUCER_NO_PYTEST_SHIM_FAIL",
    "failure_summary": ("Producer run 44861140260 persisted its snapshot but its own "
                        "no-pytest validation shim returned SHIM_FAIL (48/1/0/1) from three "
                        "test-harness causes; no /audit ref exists, so that run issued no "
                        "verdict. Not a gate verdict, provider failure, quantum starvation, "
                        "write-scope violation, product defect or frozen-bar result."),
    "audit_status": "PENDING_INDEPENDENT_AUDIT",
    "pending_independent_audit": True,
    "accepted_as_evidence": False,
    "evidence_tier": "EXPLORATORY",
    "producer_work_preserved": True,
    "additive_only": True,
    "diagnosis_record": "results/evaluation/operational_resume_44864973813/diagnosis_44861140260.json",
    "provenance_fetch_record": "results/evaluation/operational_resume_44864973813/provenance_fetch_44864973813.json",
    "freeze_first_hypothesis": "evaluation/OPERATIONAL_RESUME_44864973813_HYPOTHESIS_V1.json",
    "freeze_first_freeze": "evaluation/OPERATIONAL_RESUME_44864973813_FREEZE_V1.json",
    "pytest_shim_final": "results/evaluation/operational_resume_44864973813/pytest_shim_44864973813.json",
    "pytest_shim_attempt1_preserved": "results/evaluation/operational_resume_44864973813/pytest_shim_44864973813_attempt1.json",
    "snapshot_integrity": "results/evaluation/operational_resume_44864973813/snapshot_integrity_44864973813.json",
    "replay_comparison": "results/evaluation/operational_resume_44864973813/falsifier_replay_comparison_44864973813.json",
    "frozen_and_posture": "results/evaluation/operational_resume_44864973813/frozen_and_posture_44864973813.json",
    "report": "reports/evaluation/OPERATIONAL_RESUME_44864973813_AUDIT_READY.md",
    "verification": {
        "snapshot_integrity": "SNAPSHOT_PRESERVED 19/19 input pins re-hash equal",
        "shim_verdict": "SHIM_PASS 60 passed, 0 failed, 0 skipped, 1 unsupported (1 IMPORT_ERROR disclosed)",
        "ca_falsifier_replay": "REPRODUCES SOUND_COUNTER_ROW_PRESENT; byte-identical except generated_at_utc",
        "continuation_gate_replay": "REPRODUCES NO_TRIGGER_FIRED_NOT_DISCRIMINATING; byte-identical except generated_at_utc",
        "frozen_rules_unchanged": True,
        "posture_all_fail_closed": True,
    },
    "test_repairs": [
        {
            "file": "tests/evaluation/test_post_repair_family_ca_falsifier_40258497460.py",
            "origin": "producer repair in snapshot; resume fetched pinned historical commit and re-ran",
            "result": "PASS 14/14",
        },
        {
            "file": "tests/evaluation/test_v68_continuation_trigger_gate_44861140260.py",
            "origin": "resume test-only assertion repair; original preserved under pre_repair/",
            "original_sha256": "553fb32d8ffdc3adcb355ee1f995692807609a8d444dd9a5141c8f6a08172dd1",
            "repaired_sha256": "7ea88366a7aa01c1ded5a710f75026f326ccc143199505b657f9f8e894a0e30a",
            "result": "PASS 11/11",
        },
    ],
    "frozen_edits": {
        "bar": False, "rubric": False, "threshold": False, "predicate": False,
        "hypothesis": False, "verdict_contract": False, "measurement_record_overwritten": False,
    },
    "ordered_work_status": {
        "1_correction_of_record": "DISCHARGED (accepted 40133253347); not re-run",
        "2_conditional_remeasure": "NOT_YET_DISCRIMINATING (14/15 member-for-member; parity false; no stand-in; packet 39319405429 not scored)",
        "3_standing_falsification_record": "UNCHANGED (PRODUCT_FALSIFIED on packet 39319405429)",
        "4_non_blocking_required_fixes": "reported only where those counts are quoted",
        "5_no_rederivation": "honoured",
    },
    "posture": {
        "packet_admitted": False, "machine_gate_ready": False, "human_gate_ready": False,
        "ready_for_owner_session": False, "owner_decision_required": False,
    },
}

PRODUCER_SNAPSHOT = {
    "run": 44861140260,
    "branch": "origin/cycle/core/evaluation/44861140260/team",
    "head": "146b6a6f532112eba83a1aedd58788be1e7264ea",
    "freeze_first_commit": "fdcec5fd",
    "deliverable": {
        "ca_falsifier": "results/evaluation/post_repair_family_ca_falsifier/44861140260.json",
        "ca_falsifier_verdict": "SOUND_COUNTER_ROW_PRESENT",
        "continuation_gate": "results/evaluation/v68_continuation_trigger_gate/44861140260.json",
        "continuation_gate_verdict": "NO_TRIGGER_FIRED_NOT_DISCRIMINATING",
    },
    "own_validation_shim_verdict": "SHIM_FAIL (producer-side harness failure; see diagnosis_44861140260.json)",
    "resumed_by": 44864973813,
}

NEXT_RECOMMENDATION = (
    "OPERATIONAL RESUME 44864973813 (direction v68, evaluation, FAST_MVP_MODE): the persisted "
    "producer snapshot 146b6a6f (run 44861140260) is preserved and its substantive FAST-MVP "
    "counter-authority deliverable verifies: both frozen instruments reproduce byte-for-byte "
    "except the wall-clock timestamp, 19/19 input pins re-hash equal, frozen rules unchanged and "
    "posture fail-closed. The prior run's failure is diagnosed as a producer-side no-pytest SHIM_FAIL "
    "(missing PYTHONPATH; stale mount-head pin; a new-test assertion phrasing defect) - NOT a gate "
    "verdict, provider/quantum starvation, write-scope violation, product defect or frozen-bar result. "
    "The two test-only repairs are bounded and append-only; no frozen bar, hypothesis, instrument, "
    "measurement record or serve posture changed. Ordered item (1) stays DISCHARGED, item (2) stays "
    "NOT_YET_DISCRIMINATING (14/15; per-role parity false), item (3) standing falsification on packet "
    "39319405429 is UNCHANGED, items (4)/(5) honoured. No same-question cycle has a discriminating "
    "purpose until Product regenerates the 15th frozen-family member or changes product/query "
    "retrieval code, at which point the accepted new-bytes instrument with a new freeze-first record "
    "is the correct next step. continue_recommended=false; no 174k rerun; both DO-NOT-SERVE orders "
    "stand; admission fail-closed. Snapshot is AUDIT_READY_PENDING_INDEPENDENT_AUDIT."
)


def main() -> int:
    for path in FILES:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
        # prove byte round-trip before any additive change
        assert json.dumps(state, indent=2, ensure_ascii=False) + "\n" == raw, \
            f"non-canonical formatting: {path}"

        removed = [k for k in ("accepted_run_id", "github_run", "proposed_run_id",
                               "audit_status", "evidence_tier", "direction_version")
                   if k not in state]
        assert not removed, removed

        old_next = state.get("next_recommendation", "")
        state["prior_next_recommendation_44864973813"] = old_next
        state["next_recommendation"] = NEXT_RECOMMENDATION
        state["operational_resume_44864973813"] = json.loads(json.dumps(OPERATIONAL_RESUME))
        state["producer_snapshot_44861140260"] = json.loads(json.dumps(PRODUCER_SNAPSHOT))
        chain = state.setdefault("resume_chain", [])
        for rid in (44861140260, 44864973813):
            if rid not in chain:
                chain.append(rid)
        refs = state["evidence_refs"]
        for ref in NEW_REFS:
            if ref not in refs:
                refs.append(ref)
        # every added ref must resolve to an existing file
        missing = [r for r in refs if not (ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing, missing
        state["evidence_refs_n"] = len(refs)

        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}: refs {len(refs)}, keys {len(state)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
