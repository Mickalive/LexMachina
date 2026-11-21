#!/usr/bin/env python3
"""Additive state update for operational resume run 44882968860.

Follows evaluation/state_update_44871931511.py: adds new keys and new evidence_refs
to BOTH state/evaluation.json and evaluation/state/evaluation.json; never removes
or rewrites an existing key; never changes a pinned identity field; keeps
evidence_refs_n == len(evidence_refs); proves a byte round-trip of each file's
existing content before the additive change; and asserts every evidence_ref
resolves to an existing file.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "state/evaluation.json", ROOT / "evaluation/state/evaluation.json"]
D = "results/evaluation/operational_resume_44882968860"

NEW_REFS = [
    "evaluation/OPERATIONAL_RESUME_44882968860_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_44882968860_FREEZE_V1.json",
    "evaluation/operational_resume_44882968860.py",
    "evaluation/state_update_44882968860.py",
    f"{D}/diagnosis_44879155219.json",
    f"{D}/snapshot_integrity_44882968860.json",
    f"{D}/write_scope_44882968860.json",
    f"{D}/verification_44882968860.json",
    f"{D}/44882968860_verify.json",
    f"{D}/44882968860_verify_engine_mapping_free_recall_falsifier.json",
    f"{D}/no_pytest_44882968860.json",
    f"{D}/nested_refs/44882968860_nested_evidence_refs.json",
    f"{D}/RETRIEVAL_CA_BENCHMARK_44882968860_verify.md",
    "reports/evaluation/OPERATIONAL_RESUME_44882968860_AUDIT_READY.md",
]

OPERATIONAL_RESUME = {
    "schema": "lex-evaluation-operational-resume/1",
    "run": 44882968860,
    "run_under_resume": 44879155219,
    "claim_bearing_run": "44882968860",
    "direction_version": 68,
    "base_snapshot_commit": "519d6bc79b6097f06c724ae137a5be651d5ba2ef",
    "base_snapshot_parent": "cc0ad6089cc062dbb89495ee8ca04b1c5a0000f3",
    "accepted_base": "origin/lab/evaluation@ea98384e",
    "failure_class": "AUDIT_AGENT_STEP_FAILURE_NO_GATE",
    "failure_summary": (
        "Run 44879155219 completed its TEAM job end-to-end (including 'Enforce lane write scope' "
        "and 'Persist team snapshot', force-pushing snapshot 519d6bc7) and failed ONLY in the AUDIT "
        "job at step 5 'Independent audit' (audit job ran ~46 min, 07:16:16Z->08:02:03Z). Gate-read "
        "and audit-snapshot-persist were skipped, no CYCLE_44879155219_GATE.json exists on any ref, "
        "no /audit branch resolves and integrate was skipped. Audit-agent death (requirements 20/33), "
        "NOT a gate verdict, product defect, measurement failure, write-scope violation or human event. "
        "The precise in-agent cause (quantum expiry vs provider rotation) is a held inference: job logs "
        "are HTTP 403 unauthenticated."
    ),
    "audit_status": "PENDING_INDEPENDENT_AUDIT",
    "pending_independent_audit": True,
    "accepted_as_evidence": False,
    "evidence_tier": "EXPLORATORY",
    "producer_work_preserved": True,
    "additive_only": True,
    "diagnosis_record": f"{D}/diagnosis_44879155219.json",
    "snapshot_integrity": f"{D}/snapshot_integrity_44882968860.json",
    "write_scope": f"{D}/write_scope_44882968860.json",
    "freeze_first_hypothesis": "evaluation/OPERATIONAL_RESUME_44882968860_HYPOTHESIS_V1.json",
    "freeze_first_freeze": "evaluation/OPERATIONAL_RESUME_44882968860_FREEZE_V1.json",
    "verification_record": f"{D}/verification_44882968860.json",
    "benchmark_reexecution": f"{D}/44882968860_verify.json",
    "benchmark_reexecution_engine": f"{D}/44882968860_verify_engine_mapping_free_recall_falsifier.json",
    "no_pytest_shim": f"{D}/no_pytest_44882968860.json",
    "nested_refs_guard": f"{D}/nested_refs/44882968860_nested_evidence_refs.json",
    "report": "reports/evaluation/OPERATIONAL_RESUME_44882968860_AUDIT_READY.md",
    "verification": {
        "checks": "VERIFICATION_PASS 13/13 (H1 no audit ref/no gate; H2 reproduction equality vs 44870660846 + 44870538384 with identical failed-gate set; freeze-pin and frozen-rubric re-hash; H3 snapshot shim byte-identity; item-(1) presence; shim SHIM_PASS 8/8; tree-diff audit-namespace emptiness; guard simulation n_bad=0; posture fail-closed; direction pin 68)",
        "benchmark": "PRODUCT_FALSIFIED reproduces: 18 gates / 11 passed / 4 failed, identical failed-gate set, run_valid=true, input_drift=[], product mount 7be4480e; verification-only claim ceiling, not a second falsification or re-score",
        "test_shim": "SHIM_PASS 8 passed, 0 failed, 0 skipped, 0 unsupported (tests/evaluation/test_minimal_ca_falsify_benchmark.py via evaluation/no_pytest_runner.py; pytest unavailable; multilingual test_retrieval_benchmark.py module-import error disclosed and not counted as passed)",
        "snapshot": "snapshot 519d6bc7 preserved; its only delta (local_pytest_shim.json) re-hashes byte-identical to the git blob and is not edited",
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
    "OPERATIONAL RESUME 44882968860 (direction v68, evaluation, FAST_MVP_MODE) of run 44879155219: "
    "the persisted producer snapshot 519d6bc7 is preserved and made audit-ready. Diagnosis of record: "
    "44879155219's TEAM job fully succeeded (write scope + snapshot persist) and its AUDIT job died at "
    "step 'Independent audit' after ~46 min; gate-read/persist and integrate were skipped, no gate file "
    "or /audit ref exists, so no verdict was ever issued. This is an audit-agent death (requirements "
    "20/33), not a gate verdict, product defect, measurement failure or human event; the exact in-agent "
    "cause is a held inference (logs 403). The snapshot's sole delta (a no-pytest shim repair) is valid "
    "completed work, preserved byte-for-byte. Deliverable verified, not re-derived: the minimal CA "
    "falsification benchmark re-executes PRODUCT_FALSIFIED 18/11/4 with the identical failed-gate set, "
    "empty input_drift and product mount 7be4480e (verification-only claim ceiling); shim SHIM_PASS 8/8; "
    "verification 13/13; nested-refs guard discloses exactly one inherited pre-existing unresolved "
    "historical ref (CYCLE_40246705199_GATE.json), top-level unresolved 0. No audit-namespace path in "
    "the tree diff; write-scope simulation n_bad=0. Ordered item (1) PRESENT_AND_VERIFIED, item (2) "
    "NOT_YET_DISCRIMINATING, item (3) UNCHANGED, items (4)/(5) honoured. continue_recommended=false: no "
    "same-question cycle has a discriminating purpose until Core Product lands the rejection/incumbent "
    "leg and regenerates the full flagship family. No 174k rerun; no frozen bar/rubric/threshold/"
    "verdict contract edited; both DO-NOT-SERVE orders stand; admission fail-closed; accepted_run_id "
    "stays 40258497460. Snapshot is AUDIT_READY_PENDING_INDEPENDENT_AUDIT."
)


def main() -> int:
    for path in FILES:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
        assert json.dumps(state, indent=2, ensure_ascii=False) + "\n" == raw, f"non-canonical formatting: {path}"
        pinned_keys = ("accepted_run_id", "github_run", "audit_status", "evidence_tier", "direction_version")
        assert not [k for k in pinned_keys if k not in state], "missing pinned field"
        pinned_before = {k: state[k] for k in pinned_keys}

        state["prior_next_recommendation_44882968860"] = state.get("next_recommendation", "")
        state["next_recommendation"] = NEXT_RECOMMENDATION
        state["operational_resume_44882968860"] = json.loads(json.dumps(OPERATIONAL_RESUME))
        chain = state.setdefault("resume_chain", [])
        for rid in (44879155219, 44882968860):
            if rid not in chain:
                chain.append(rid)
        refs = state["evidence_refs"]
        added = []
        for ref in NEW_REFS:
            if ref not in refs:
                refs.append(ref)
                added.append(ref)
        missing = [r for r in refs if not (ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing, missing
        state["evidence_refs_n"] = len(refs)
        state["evidence_refs_resolution_44882968860"] = {
            "record": f"{D}/nested_refs/44882968860_nested_evidence_refs.json",
            "n_top_level_evidence_refs": len(refs),
            "n_top_level_unresolved": 0,
            "added_this_run": added,
            "nested_guard_verdict": "UNRESOLVED_REFS_PRESENT",
            "nested_unresolved": 1,
            "nested_unresolved_detail": "inherited pre-existing historical ref $.github_run_advance_40246705199.required_fixes_source -> results/audit/evaluation/CYCLE_40246705199_GATE.json (mounted verification copy at /tmp/lex_prior_audit, absent in this image); not introduced by this run",
            "note": "every top-level evidence_ref re-resolved as an existing file at write time; the nested guard record carries the full walk",
        }
        assert pinned_before == {k: state[k] for k in pinned_keys}, "pinned field changed"
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}: refs {len(refs)}, keys {len(state)}, added {len(added)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
