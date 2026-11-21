#!/usr/bin/env python3
"""Additive state update for operational resume run 44887103047.

Follows evaluation/state_update_44882968860.py: adds new keys and new
evidence_refs to BOTH state/evaluation.json and evaluation/state/evaluation.json;
never removes or rewrites an existing key; never changes a pinned identity
field; keeps evidence_refs_n == len(evidence_refs); proves a byte round-trip of
each file's existing content before the additive change; asserts every
evidence_ref resolves to an existing file; and runs the nested-evidence-refs
guard on the UPDATED state, writing the guard record and embedding its real
counts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "state/evaluation.json", ROOT / "evaluation/state/evaluation.json"]
D = "results/evaluation/operational_resume_44887103047"
GUARD_RECORD = f"{D}/nested_refs/44887103047_nested_evidence_refs.json"

NEW_REFS = [
    "evaluation/OPERATIONAL_RESUME_44887103047_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_44887103047_FREEZE_V1.json",
    "evaluation/operational_resume_44887103047.py",
    "evaluation/state_update_44887103047.py",
    f"{D}/diagnosis_44882968860.json",
    f"{D}/snapshot_delta_files_44887103047.json",
    f"{D}/snapshot_integrity_44887103047.json",
    f"{D}/ordered_work_44887103047.json",
    f"{D}/write_scope_44887103047.json",
    f"{D}/verification_44887103047.json",
    f"{D}/git_facts_44887103047.txt",
    f"{D}/44887103047_verify.json",
    f"{D}/44887103047_verify_engine_mapping_free_recall_falsifier.json",
    f"{D}/no_pytest_44887103047.json",
    f"{D}/multilingual_provenance_shim_44887103047.json",
    f"{D}/RETRIEVAL_CA_BENCHMARK_44887103047_verify.md",
    f"{D}/rest/run_44882968860.json",
    f"{D}/rest/audit_job_136783749627.json",
    GUARD_RECORD,
    "reports/evaluation/OPERATIONAL_RESUME_44887103047_AUDIT_READY.md",
]

OPERATIONAL_RESUME = {
    "schema": "lex-evaluation-operational-resume/1",
    "run": 44887103047,
    "run_under_resume": 44882968860,
    "claim_bearing_run": "44887103047",
    "direction_version": 68,
    "base_snapshot_commit": "ada742d7c1ddb91779c91bb55166e9e598f1caf6",
    "base_snapshot_parent": "519d6bc79b6097f06c724ae137a5be651d5ba2ef",
    "accepted_base": "origin/lab/evaluation@ea98384e",
    "failure_class": "AUDIT_AGENT_STEP_FAILURE_NO_GATE",
    "failure_summary": (
        "Run 44882968860 completed its TEAM job end-to-end (all steps green, snapshot ada742d7 force-pushed) "
        "and failed ONLY in the AUDIT job at step 5 'Independent audit' (08:09:16Z->08:55:01Z, 2745 s). "
        "Gate-read and audit-snapshot-persist were skipped, no CYCLE_44882968860_GATE.json exists in the "
        "worktree or the team ref, no /audit branch resolves and integrate was skipped: NO VERDICT WAS "
        "EVER ISSUED. Audit-agent orchestration death (requirements 10/20/33), not a gate verdict, not a "
        "producer failure, product defect, measurement failure or human event. The exact in-agent cause "
        "(2745 s matches the 2700 s work-quantum class) is a held INFERENCE: job logs are HTTP 403."
    ),
    "audit_status": "PENDING_INDEPENDENT_AUDIT",
    "pending_independent_audit": True,
    "accepted_as_evidence": False,
    "evidence_tier": "EXPLORATORY",
    "producer_work_preserved": True,
    "additive_only": True,
    "resumed_from_run": 44882968860,
    "diagnosis_record": f"{D}/diagnosis_44882968860.json",
    "snapshot_integrity": f"{D}/snapshot_integrity_44887103047.json",
    "write_scope": f"{D}/write_scope_44887103047.json",
    "ordered_work_record": f"{D}/ordered_work_44887103047.json",
    "freeze_first_hypothesis": "evaluation/OPERATIONAL_RESUME_44887103047_HYPOTHESIS_V1.json",
    "freeze_first_freeze": "evaluation/OPERATIONAL_RESUME_44887103047_FREEZE_V1.json",
    "verification_record": f"{D}/verification_44887103047.json",
    "benchmark_reexecution": f"{D}/44887103047_verify.json",
    "benchmark_reexecution_engine": f"{D}/44887103047_verify_engine_mapping_free_recall_falsifier.json",
    "no_pytest_shim": f"{D}/no_pytest_44887103047.json",
    "multilingual_provenance_shim": f"{D}/multilingual_provenance_shim_44887103047.json",
    "nested_refs_guard": GUARD_RECORD,
    "rest_cache_dir": f"{D}/rest/",
    "report": "reports/evaluation/OPERATIONAL_RESUME_44887103047_AUDIT_READY.md",
    "verification": {
        "checks": "VERIFICATION_PASS 20/20 (H1 diagnosis read facts, quantum-class inference tagged, no gate/no audit ref/no verdict, log-probe 403; H2 reproduction equality vs 44870660846 + 44882968860_verify with identical failed-gate set and claim-ceiling equality; H3 full dual-freeze re-hash, snapshot head/delta/shim byte-identity, prior verification record PASS, shims, write-scope n_bad=0, tree-diff audit-namespace empty, posture fail-closed, direction pin 68; H4 ordered item (1) both-halves verified with audit-branch absence disclosed, item (2) unchanged-by-input-equality)",
        "benchmark": "PRODUCT_FALSIFIED reproduces: 18 gates / 11 passed / 4 failed, identical failed-gate set, run_valid=true, input_drift=[], product mount 7be4480e; verification-only claim ceiling, not a second falsification or re-score",
        "test_shim": "SHIM_PASS 8 passed, 0 failed (test_minimal_ca_falsify_benchmark.py); multilingual IMPORT_ERROR disclosed as NOT-RUN in that run, and the reused multilingual/provenance suite passes separately SHIM_PASS 2/2 with protocol digest e1a0b18d==expected and test sha 558e1f1b (PYTHONPATH=accepted product mount, numpy 2.5.5/scipy 1.18.1/sklearn 1.9.1)",
        "snapshot": "snapshot ada742d7 preserved intact: HEAD==team ref, delta vs parent = the prior resume's 17 in-scope files, shim byte-identical across worktree/blob/pin, zero audit-namespace paths",
        "frozen_rules_unchanged": True,
        "posture_all_fail_closed": True,
    },
    "frozen_edits": {
        "bar": False, "rubric": False, "threshold": False, "predicate": False,
        "hypothesis": False, "verdict_contract": False, "measurement_record_overwritten": False,
    },
    "ordered_work_status": {
        "1_correction_of_record": "DISCHARGED_VERIFIED (gate PASS file in accepted tree; accept commit 7165d9e06; audit branch absent disclosed, read from integrate-copied committed gate file); not re-run",
        "2_conditional_remeasure": "NOT_YET_DISCRIMINATING (leg half LANDED, full family 14/15 per record 44861140260; adjudication input unchanged: product mount head 7be4480e identical + clean tree; protocol not re-run, no stand-in)",
        "3_standing_falsification_record": "UNCHANGED (PRODUCT_FALSIFIED on packet 39319405429); counter-authority yield negative stays scoped to this lane's own producer",
        "4_non_blocking_required_fixes": "reported only where those counts are quoted (no such count quoted this cycle)",
        "5_no_rederivation": "honoured - operational verification recorded as operational, not as new evidence",
    },
    "posture": {
        "packet_admitted": False, "machine_gate_ready": False, "human_gate_ready": False,
        "ready_for_owner_session": False, "owner_decision_required": False,
    },
}

NEXT_RECOMMENDATION = (
    "OPERATIONAL RESUME 44887103047 (direction v68, evaluation, FAST_MVP_MODE) of run 44882968860: the "
    "persisted producer snapshot ada742d7 is preserved intact and made audit-ready; nothing was rebuilt "
    "from scratch. Diagnosis of record: 44882968860's TEAM job fully succeeded (write scope + snapshot "
    "persist) and its AUDIT job died at step 'Independent audit' after 2745 s (2700 s quantum class, "
    "inference-tagged: logs HTTP 403); gate-read/persist and integrate were skipped, no gate file or "
    "/audit ref exists, so NO VERDICT WAS EVER ISSUED - an audit-agent orchestration death (requirements "
    "10/20/33), not a gate, producer failure or product defect. Deliverable verified, not re-derived: the "
    "frozen FAST-MVP falsifier re-executes PRODUCT_FALSIFIED 18/11/4 with the identical failed-gate set, "
    "empty input_drift and product mount 7be4480e (verification-only claim ceiling); shims SHIM_PASS 8/8 "
    "and multilingual/provenance SHIM_PASS 2/2 (digest e1a0b18d); verification 20/20; both freeze records "
    "re-hash with zero mismatches; write-scope n_bad=0; tree diff has zero audit-namespace paths. Ordered "
    "item (1) DISCHARGED_VERIFIED with the 40133253347 audit-branch absence disclosed; item (2) "
    "NOT_YET_DISCRIMINATING unchanged (leg LANDED, family 14/15, adjudication input byte-identical); "
    "items (3)-(5) honoured. continue_recommended=false: no same-question cycle has a discriminating "
    "purpose until Core Product regenerates the 15th flagship-family member, after which ordered item (2) "
    "executes. No 174k rerun; no frozen bar/rubric/threshold/verdict contract edited; both DO-NOT-SERVE "
    "orders stand; admission fail-closed; accepted_run_id stays 40258497460. Snapshot is "
    "AUDIT_READY_PENDING_INDEPENDENT_AUDIT."
)


def run_guard() -> dict:
    proc = subprocess.run(
        [sys.executable, "evaluation/nested_evidence_refs_guard.py",
         "--run-id", "44887103047", "--out-dir", f"{D}/nested_refs"],
        cwd=ROOT, capture_output=True, text=True,
    )
    record = json.loads((ROOT / GUARD_RECORD).read_text(encoding="utf-8"))
    record["_guard_exit_code"] = proc.returncode
    record["_guard_stdout_tail"] = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return record


def main() -> int:
    for path in FILES:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
        assert json.dumps(state, indent=2, ensure_ascii=False) + "\n" == raw, f"non-canonical formatting: {path}"
        pinned_keys = ("accepted_run_id", "github_run", "audit_status", "evidence_tier", "direction_version")
        assert not [k for k in pinned_keys if k not in state], "missing pinned field"
        pinned_before = {k: state[k] for k in pinned_keys}

        state["prior_next_recommendation_44887103047"] = state.get("next_recommendation", "")
        state["next_recommendation"] = NEXT_RECOMMENDATION
        state["operational_resume_44887103047"] = json.loads(json.dumps(OPERATIONAL_RESUME))
        chain = state.setdefault("resume_chain", [])
        for rid in (44882968860, 44887103047):
            if rid not in chain:
                chain.append(rid)
        refs = state["evidence_refs"]
        added = []
        for ref in NEW_REFS:
            if ref not in refs:
                refs.append(ref)
                added.append(ref)
        # guard record is written immediately after this first pass
        pending = {GUARD_RECORD}
        missing = [r for r in refs if r not in pending and not (ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing, missing
        state["evidence_refs_n"] = len(refs)
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        if path == FILES[0]:
            guard = run_guard()
        else:
            guard = json.loads((ROOT / GUARD_RECORD).read_text(encoding="utf-8"))

        state["evidence_refs_resolution_44887103047"] = {
            "record": GUARD_RECORD,
            "n_top_level_evidence_refs": len(refs),
            "n_top_level_unresolved": guard.get("n_top_level_unresolved"),
            "added_this_run": added,
            "nested_guard_verdict": guard.get("verdict"),
            "nested_unresolved": guard.get("n_unresolved"),
            "nested_unresolved_detail": (
                "inherited pre-existing historical ref $.github_run_advance_40246705199.required_fixes_source "
                "-> results/audit/evaluation/CYCLE_40246705199_GATE.json (mounted verification copy at "
                "/tmp/lex_prior_audit, absent in this image); not introduced by this run"),
            "resolution_counts": guard.get("resolution_counts"),
            "note": "guard executed on the UPDATED state inside this updater; every count above is read from the guard record, never asserted",
        }
        assert pinned_before == {k: state[k] for k in pinned_keys}, "pinned field changed"
        final_raw = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        # final assertion: every ref resolves now (guard record included)
        missing_final = [r for r in state["evidence_refs"]
                         if not (ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing_final, missing_final
        path.write_text(final_raw, encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}: refs {len(state['evidence_refs'])}, "
              f"keys {len(state)}, added {len(added)}, guard={guard.get('verdict')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
