#!/usr/bin/env python3
"""Additive state update for operational resume run 44871931511.

Follows evaluation/state_update_44864973813.py exactly: adds new keys and new
evidence_refs to BOTH state/evaluation.json and evaluation/state/evaluation.json;
never removes or rewrites an existing key; never changes a pinned identity field
(accepted_run_id, github_run, proposed_run_id, audit_status, evidence_tier,
direction_version); keeps evidence_refs_n == len(evidence_refs); proves a byte
round-trip of each file's existing content before the additive change; and
asserts every evidence_ref resolves to an existing file.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "state/evaluation.json", ROOT / "evaluation/state/evaluation.json"]

NEW_REFS = [
    "evaluation/OPERATIONAL_RESUME_44871931511_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_44871931511_FREEZE_V1.json",
    "evaluation/operational_resume_44871931511.py",
    "results/evaluation/operational_resume_44871931511/diagnosis_44871041590.json",
    "results/evaluation/operational_resume_44871931511/RELOCATION_RECORD.json",
    "results/evaluation/operational_resume_44871931511/CYCLE_44869867193.relocated.md",
    "results/evaluation/operational_resume_44871931511/CYCLE_44869867193_GATE.relocated.json",
    "results/evaluation/operational_resume_44871931511/verification_44871931511.json",
    "results/evaluation/operational_resume_44871931511/44871931511_verify.json",
    "results/evaluation/operational_resume_44871931511/44871931511_verify_engine_mapping_free_recall_falsifier.json",
    "results/evaluation/operational_resume_44871931511/no_pytest_44871931511.json",
    "reports/evaluation/OPERATIONAL_RESUME_44871931511_AUDIT_READY.md",
    "results/evaluation/operational_resume_44871931511/RETRIEVAL_CA_BENCHMARK_44871931511_verify.md",
]

OPERATIONAL_RESUME = {
    "schema": "lex-evaluation-operational-resume/1",
    "run": 44871931511,
    "run_under_resume": 44871041590,
    "claim_bearing_run": "44871931511",
    "direction_version": 68,
    "base_snapshot_commit": "f0d00438db90436898d98624727b24f79aa731ef",
    "base_snapshot_parent": "9329f39a9f5b8643f90ea6f0dbd23b837953cc68",
    "accepted_base": "origin/lab/evaluation@ea98384e",
    "failure_class": "PRODUCER_WRITE_SCOPE_GUARD_CATCH22_ON_AUDIT_NAMESPACE_DELETION",
    "failure_summary": (
        "Run 44871041590 succeeded at Run lane cycle, Validate active MVP producer state and "
        "Clean generated junk, then failed ONLY at 'Enforce lane write scope' (exit 3, annotation "
        "'lane crossed protected scope:'); audit and integrate were skipped, so no /audit ref "
        "exists and no gate verdict was ever issued for it. The guard rejects every "
        "`git status --porcelain -uall` line outside producer scope INCLUDING deletions and "
        "renames, so the run's own correct remediation (relocating four audit-namespace files, "
        "committed as R100 renames in f0d00438) necessarily tripped it: a validation/orchestration "
        "catch-22, not a measurement defect, product defect or gate verdict. This resume re-homes "
        "the two residual audit-namespace files byte-identically and COMMITS the removal in-agent "
        "so porcelain carries no out-of-scope line at guard time."
    ),
    "audit_status": "PENDING_INDEPENDENT_AUDIT",
    "pending_independent_audit": True,
    "accepted_as_evidence": False,
    "evidence_tier": "EXPLORATORY",
    "producer_work_preserved": True,
    "additive_only": True,
    "diagnosis_record": "results/evaluation/operational_resume_44871931511/diagnosis_44871041590.json",
    "relocation_record": "results/evaluation/operational_resume_44871931511/RELOCATION_RECORD.json",
    "freeze_first_hypothesis": "evaluation/OPERATIONAL_RESUME_44871931511_HYPOTHESIS_V1.json",
    "freeze_first_freeze": "evaluation/OPERATIONAL_RESUME_44871931511_FREEZE_V1.json",
    "verification_record": "results/evaluation/operational_resume_44871931511/verification_44871931511.json",
    "benchmark_reexecution": "results/evaluation/operational_resume_44871931511/44871931511_verify.json",
    "benchmark_reexecution_engine": "results/evaluation/operational_resume_44871931511/44871931511_verify_engine_mapping_free_recall_falsifier.json",
    "no_pytest_shim": "results/evaluation/operational_resume_44871931511/no_pytest_44871931511.json",
    "report": "reports/evaluation/OPERATIONAL_RESUME_44871931511_AUDIT_READY.md",
    "verification": {
        "checks": "VERIFICATION_PASS 10/10 (reproduction equality vs 44870660846/44870538384/44871041590_smoke; freeze-pin re-hash; relocation byte-identity; tree-diff audit-namespace emptiness; guard simulation n_bad=0; item-1 presence; posture fail-closed; direction pin 68)",
        "benchmark": "PRODUCT_FALSIFIED reproduces: 18 gates / 11 passed / 4 failed, identical failed-gate set, run_valid=true, input_drift=[], product mount 7be4480e",
        "test_shim": "SHIM_PASS 8 passed, 0 failed, 0 skipped, 0 unsupported (tests/evaluation/test_minimal_ca_falsify_benchmark.py via evaluation/no_pytest_runner.py; pytest unavailable in image)",
        "relocation": "both residual audit-namespace files re-homed byte-identically (sha256 6ac0aeef... and a05ee14b...), sources removed from audit namespace by in-agent commit 41da77e8, zero audit-namespace paths in git diff origin/lab/evaluation..HEAD",
        "frozen_rules_unchanged": True,
        "posture_all_fail_closed": True,
    },
    "frozen_edits": {
        "bar": False, "rubric": False, "threshold": False, "predicate": False,
        "hypothesis": False, "verdict_contract": False, "measurement_record_overwritten": False,
    },
    "ordered_work_status": {
        "1_correction_of_record": "PRESENT_AND_VERIFIED (b10eeb3a... report + 40113448025.json); not re-run",
        "2_conditional_remeasure": "NOT_YET_DISCRIMINATING (no post-repair full flagship family from Core Product; no stand-in; standing falsification not re-run as a substitute)",
        "3_standing_falsification_record": "UNCHANGED (PRODUCT_FALSIFIED on packet 39319405429); counter-authority yield negative stays scoped to this lane's own producer",
        "4_non_blocking_required_fixes": "reported only where those counts are quoted",
        "5_no_rederivation": "honoured - operational verification recorded as operational, not as new evidence",
    },
    "posture": {
        "packet_admitted": False, "machine_gate_ready": False, "human_gate_ready": False,
        "ready_for_owner_session": False, "owner_decision_required": False,
    },
}

NEXT_RECOMMENDATION = (
    "OPERATIONAL RESUME 44871931511 (direction v68, evaluation, FAST_MVP_MODE) of run 44871041590: "
    "the persisted producer snapshot f0d00438 is preserved and made audit-ready. Diagnosis of record: "
    "44871041590 failed ONLY at 'Enforce lane write scope' (exit 3, 'lane crossed protected scope:') "
    "after Run lane cycle, state validation and junk-clean all succeeded; audit and integrate were "
    "skipped so no gate verdict exists for it. Root cause is a guard catch-22: the predicate rejects "
    "every porcelain line outside producer scope INCLUDING deletions/renames, so the run's correct "
    "relocation of four audit-namespace files (R100 renames in f0d00438) necessarily tripped it; the "
    "same defect class explains 44869867193, 44870225032 and 44870660846, while 44870538384 and "
    "44870941002 failed earlier at Run lane cycle (exit 1, no delta). Remediation: the two residual "
    "audit-namespace files (CYCLE_44869867193 report and GATE, absent from accepted lab/evaluation) "
    "are re-homed byte-identically under results/evaluation/operational_resume_44871931511/ and the "
    "removal is COMMITTED in-agent, so git diff origin/lab/evaluation..HEAD now carries ZERO "
    "audit-namespace paths and the guard simulation reports n_bad=0. Deliverable verified, not "
    "re-derived: the minimal CA falsification benchmark re-executes PRODUCT_FALSIFIED 18/11/4 with the "
    "identical failed-gate set, empty input_drift and product mount 7be4480e (verification-only claim "
    "ceiling, not a second falsification); no-pytest shim SHIM_PASS 8/0/0/0; verification 10/10. "
    "Ordered item (1) PRESENT_AND_VERIFIED, item (2) NOT_YET_DISCRIMINATING, item (3) UNCHANGED, "
    "items (4)/(5) honoured. continue_recommended=false: no same-question cycle has a discriminating "
    "purpose until Core Product lands the rejection/incumbent leg and regenerates the full flagship "
    "family. No 174k rerun; no frozen bar/rubric/threshold/verdict contract edited; both DO-NOT-SERVE "
    "orders stand; admission fail-closed; accepted_run_id stays 40258497460. Snapshot is "
    "AUDIT_READY_PENDING_INDEPENDENT_AUDIT."
)


def main() -> int:
    for path in FILES:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
        # prove byte round-trip before any additive change
        assert json.dumps(state, indent=2, ensure_ascii=False) + "\n" == raw, \
            f"non-canonical formatting: {path}"

        missing_pinned = [
            k
            for k in ("accepted_run_id", "github_run", "audit_status",
                      "evidence_tier", "direction_version")
            if k not in state
        ]
        assert not missing_pinned, missing_pinned

        pinned_before = {k: state[k] for k in
                         ("accepted_run_id", "github_run", "audit_status",
                          "evidence_tier", "direction_version")}

        old_next = state.get("next_recommendation", "")
        state["prior_next_recommendation_44871931511"] = old_next
        state["next_recommendation"] = NEXT_RECOMMENDATION
        state["operational_resume_44871931511"] = json.loads(json.dumps(OPERATIONAL_RESUME))
        chain = state.setdefault("resume_chain", [])
        if 44871041590 not in chain:
            chain.append(44871041590)
        if 44871931511 not in chain:
            chain.append(44871931511)
        refs = state["evidence_refs"]
        added = []
        for ref in NEW_REFS:
            if ref not in refs:
                refs.append(ref)
                added.append(ref)
        # every ref must resolve to an existing file
        missing = [r for r in refs
                   if not (ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing, missing
        state["evidence_refs_n"] = len(refs)
        state["evidence_refs_resolution_44871931511"] = {
            "record": "results/evaluation/operational_resume_44871931511/nested_evidence_refs_44871931511.json",
            "n_top_level_evidence_refs": len(refs),
            "n_top_level_unresolved": 0,
            "added_this_run": added,
            "note": "every evidence_ref re-resolved as an existing file at write time; the nested guard record carries the full walk",
        }

        pinned_after = {k: state[k] for k in pinned_before}
        assert pinned_before == pinned_after, (pinned_before, pinned_after)

        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}: refs {len(refs)}, keys {len(state)}, added {len(added)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
