#!/usr/bin/env python3
"""Operational-resume state update for evaluation run 40034814235.

Idempotent: re-running only advances state_updated_at when every data field is
already correct. Never touches claim ceilings, posture flags, historical
measurement-of-record fields, benchmark_result (accepted run 39927760701) or
any evidence_ref. Corrections applied, all disclosed in
results/evaluation/orchestration/40034814235_verification_of_repair_40017649220_r1.json
and reports/evaluation/OPERATIONAL_RESUME_40034814235.md:
  * evidence_index_defects_inherited_not_charged.defects[0].detail text wrongly
    said the duplicated ref does not resolve; measured fact: it resolves
    (DUPLICATE_ONLY). Text corrected; ref list unchanged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RUN = "40034814235"
RESUME_FROM = "40034534808"
STATE = Path("state/evaluation.json")

NEW_EVIDENCE_REFS = [
    "evaluation/OPERATIONAL_RESUME_40034814235_HYPOTHESIS_V1.json",
    "results/evaluation/orchestration/40034814235_failure_chain_diagnosis.json",
    "results/evaluation/orchestration/40034814235_verification_of_repair_40017649220_r1.json",
    "results/evaluation/orchestration/40034814235_minimal_ret_ca_pytest_shim.json",
    "results/evaluation/orchestration/40034814235_multiling_prov_pytest_shim.json",
    "results/evaluation/orchestration/40034814235_repair_r1_suite_shim.json",
    "results/evaluation/minimal_ret_ca_benchmark/40034814235.json",
    "results/evaluation/minimal_ret_ca_benchmark/40034814235_leg1_served_baseline.json",
    "results/evaluation/minimal_ret_ca_benchmark/40034814235_leg2_hostile_geometry.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_40034814235.md",
    "reports/evaluation/OPERATIONAL_RESUME_40034814235.md",
    "evaluation/operational_resume_40034814235_update_state.py",
    "tests/evaluation/test_operational_resume_40034814235.py",
    "results/evaluation/orchestration/40034814235_self_suite_shim.json",
]

RESUME_BLOCK = {
    "schema": "lex-evaluation-operational-resume/1",
    "run_id": RUN,
    "resumed_from_run": RESUME_FROM,
    "direction_version": 65,
    "mode": "operational resume of persisted producer snapshot (team tip b8d526bc at dispatch)",
    "resume_chain": [
        "40017649220 (repair0 producer; audit gate REVISE F1/F2/F3)",
        "40023576675 (repair r1 producer; rc-78 quantum AFTER committing b9870cb9+b8d526bc; audit skipped)",
        "40029231841 (rc-67 zero-delta; external_directory auto-reject)",
        "40029524205 (rc-67 zero-delta after read-only session)",
        "40033424089 (rc-67 zero-delta; external_directory auto-reject)",
        "40033628306 (rc-67 zero-delta after read-only session)",
        "40034534808 (rc-67 zero-delta; token-probe external_directory auto-reject)",
        RUN,
    ],
    "failure_class": "rc-78 LEX_WORK_QUANTUM_EXPIRED then five rc-67 LEX_ZERO_DELTA_REPAIR; ORCHESTRATION, not product/evidence/human-gate (factory-wide requirements 10/12)",
    "work_loss": "ZERO - all six failed snapshots byte-identical at b8d526bc12cf3b5384524b31036d01d20e27bb21 (verified by fetching and comparing every team branch)",
    "recurring_anti_pattern": "3 of 6 producers ended their only session on an auto-rejected external_directory token probe under /home/runner/work/_temp; recorded for the control plane, .github/** never edited from here",
    "diagnosis_record": "results/evaluation/orchestration/40034814235_failure_chain_diagnosis.json",
    "hypothesis_record": "evaluation/OPERATIONAL_RESUME_40034814235_HYPOTHESIS_V1.json",
    "freeze_commit": "da2fadea2",
    "freeze_committed_before_claim_bearing_execution": True,
    "freeze_margin_disclosure": "freeze commit 2026-10-23T22:54:29Z; benchmark execution began 2026-10-23T22:54:34Z (5s margin, disclosed rather than glossed)",
    "verification_record": "results/evaluation/orchestration/40034814235_verification_of_repair_40017649220_r1.json",
    "report": "reports/evaluation/OPERATIONAL_RESUME_40034814235.md",
    "verdict": "REPAIR_DISCHARGE_VERIFIED_SNAPSHOT_AUDIT_READY",
    "f1_reexecuted": "SHIM_PASS 4/0/0/1UNSUPPORTED + 73/0/0/0 + 32/0/0/0 - identical counts to the committed 40017649220 R1 records",
    "f2_rederived": "evidence_refs_n==len==173 at repair time; all nine claim-bearing artifacts of 40017649220 indexed and resolving; 172/173 resolve with the two inherited defects disclosed; one inherited detail-text inconsistency corrected (duplicate ref DOES resolve; ref list unchanged). After this run appends its 14 refs the index re-derives at evidence_refs_n==len==187.",
    "f3_rechecked": "NOT_FREEZE_FIRST declaration, inherited frozen spec pins and no-post-hoc-tuning proofs all re-verified at this head",
    "benchmark_confirmation": {
        "freeze_first": True,
        "record": "results/evaluation/minimal_ret_ca_benchmark/40034814235.json",
        "verdict": "BENCHMARK_VALID_NO_FALSIFICATION",
        "exit_code": 0,
        "falsification_proven": True,
        "leg1": "PASS_NO_REGRESSION (label 65/5 rate 0.076923 LABEL_UNSOUND; geometry 6/5/5; 0/3 bundles pass all 11)",
        "leg2": "FAIL_REGRESSION (de+fr regressed; controls proven)",
        "normalized_identical_to_measurement_of_record": "v65_eval_40017649220",
    },
    "multilingual_reuse_confirmation": {
        "verdict": "PARTIAL_MISS 0/3 reproduced",
        "raw_output_sha256": "82ae91b536623e77dbd39888db3b0df4dce45c9a3c21879549b6b755b07da428",
        "byte_identical_to_historical_record": True,
        "disposition": "accepted negative carried, never repaired",
    },
    "frozen_inputs_unchanged_after_execution": True,
    "frozen_files_edited": 0,
    "historical_records_overwritten": 0,
    "no_174k_benchmark_rerun": True,
}

TEST_SUITE_BLOCK = {
    "schema": "lex-evaluation-no-pytest-runner/1",
    "run_id": RUN,
    "measurement_env": "python 3.12.3, pytest ABSENT (find_spec -> None), committed shim evaluation/no_pytest_runner.py sha256 c12097da9d910574380b32c5dafa371a3b24ec14ef2551d92bb9453b8ed57584; UNSUPPORTED counted NOT-RUN, never passed; accepted product mount present",
    "minimal_ret_ca_benchmark": {
        "file": "tests/evaluation/test_minimal_ret_ca_benchmark.py",
        "verdict": "SHIM_PASS",
        "passed": 4,
        "failed": 0,
        "skipped": 0,
        "unsupported": 1,
        "unsupported_case_restated_as": "test_end_to_end_on_accepted_mount_if_present = NOT-RUN under the shim (needs tmp_path). Its committed out-of-shim record 40017649220_R1_e2e_fixture_injected.json is cross-checked by the repair suite (test_f1_e2e_cited_elapsed_matches_definitive_record, re-executed green here) and is not re-counted here.",
        "record": "results/evaluation/orchestration/40034814235_minimal_ret_ca_pytest_shim.json",
    },
    "multilingual_provenance_reuse": {
        "files": [
            "tests/evaluation/test_stand_ready_multilingual_probe.py",
            "tests/evaluation/test_f3b_restore_disposition.py",
            "tests/evaluation/test_v59_stand_ready_verification.py",
            "tests/evaluation/test_packet_of_record_stand_ready.py",
        ],
        "verdict": "SHIM_PASS",
        "passed": 73,
        "failed": 0,
        "skipped": 0,
        "unsupported": 0,
        "reuse_instrument_reexecution": {
            "verdict": "PARTIAL_MISS 0/3 reproduced",
            "raw_output_sha256": "82ae91b536623e77dbd39888db3b0df4dce45c9a3c21879549b6b755b07da428",
            "byte_identical_to_historical_record": True,
            "scratch_cwd_only": True,
        },
        "record": "results/evaluation/orchestration/40034814235_multiling_prov_pytest_shim.json",
    },
    "repair_r1_suite": {
        "verdict": "SHIM_PASS",
        "passed": 32,
        "failed": 0,
        "skipped": 0,
        "unsupported": 0,
        "record": "results/evaluation/orchestration/40034814235_repair_r1_suite_shim.json",
    },
}


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    n_before = len(state["evidence_refs"])

    # 1. run identity
    state["github_run"] = RUN
    state["proposed_run_id"] = RUN
    state["repair_round"] = 1

    # 2. operational-resume block
    state[f"operational_resume_{RUN}"] = RESUME_BLOCK

    # 3. repair discharge verification pointer
    r1 = state.setdefault("repair_round1_40017649220", {})
    r1["discharge_verified_by_run"] = RUN
    r1["discharge_verification_record"] = RESUME_BLOCK["verification_record"]
    r1["discharge_verification_verdict"] = "VERIFIED_UNDER_INDEPENDENT_REEXECUTION"
    r1["discharge_never_audited_note"] = (
        "Producer 40023576675 died rc-78 ~2s after committing the discharge, so no "
        "CYCLE_40023576675 gate exists; the discharge rides on this run's team tip for "
        "the independent auditor of run 40034814235."
    )

    # 4. benchmark confirmation pointer (measurement-of-record fields untouched)
    b = state.setdefault("minimal_ret_ca_benchmark", {})
    b["latest_confirmation_run"] = RUN
    b["latest_confirmation_record"] = "results/evaluation/minimal_ret_ca_benchmark/40034814235.json"
    b["latest_confirmation_verdict"] = "BENCHMARK_VALID_NO_FALSIFICATION"
    b["latest_confirmation_freeze_first"] = True
    b["latest_confirmation_note"] = (
        "Operational-resume re-execution at run 40034814235, freeze commit da2fadea2, "
        "normalized-identical to the measurement of record v65_eval_40017649220; claim "
        "ceiling unchanged."
    )

    # 5. test-suite re-execution block (nested; does not disturb historical keys)
    state.setdefault("test_suite", {})[f"operational_resume_{RUN}"] = TEST_SUITE_BLOCK

    # 6. evidence index: append-only
    refs = state["evidence_refs"]
    added = []
    for ref in NEW_EVIDENCE_REFS:
        if ref not in refs:
            refs.append(ref)
            added.append(ref)
    state["evidence_refs_n"] = len(refs)
    state["evidence_index_resolving_refs_n"] = len(refs) - state.get(
        "evidence_index_unresolvable_n", 1
    )

    # 7. truthful correction of the inherited-defect detail text (ref list unchanged)
    defects = (
        state.get("evidence_index_defects_inherited_not_charged", {})
        .get("defects", [])
    )
    for defect in defects:
        if defect.get("kinds") == ["DUPLICATE_ONLY"] and "39875239812_diagnosis" in str(
            defect.get("ref", "")
        ):
            defect["detail"] = (
                "Appears twice in evidence_refs; DOES resolve to a committed file at this "
                "head (results/evaluation/orchestration/39875239812_diagnosis.json exists). "
                "Kind is DUPLICATE_ONLY. Corrected by run 40034814235, which found the "
                "earlier detail text wrongly claiming non-resolution; the ref list itself "
                "is unchanged. Introduced before run 40017649220."
            )
            defect["detail_corrected_by_run"] = RUN

    # 8. continuation posture (flags untouched; reasons updated)
    state["continue_recommended"] = True
    state["continue_recommended_reason"] = (
        "v65 same-question cycle continues: the un-audited F1/F2/F3 repair discharge is "
        "now verified under independent re-execution at run 40034814235 and the frozen "
        "2-leg minimal retrieval/counter-authority benchmark reproduces "
        "BENCHMARK_VALID_NO_FALSIFICATION freeze-first on the pinned served packet bytes; "
        "the binding counter-authority evidence gap (n_emitted=0 on all three V3 "
        "questions) keeps the comparative map-vs-ranked-list half VACUOUS, both "
        "DO-NOT-SERVE orders stand and admission stays fail-closed, so the next "
        "discriminating cycle is the cross-check of the next accepted product head."
    )
    state["next_recommendation"] = (
        "CONTINUE under the SAME v65 question: cross-check the NEXT accepted product head "
        "as it lands (requirement-4 lineage: PASS gate file AND accept commit), and "
        "execute the coverage-v2 re-freeze ONLY IF the coverage family is resumed. The "
        "operational-resume chain 40023576675..40034534808 is closed: repair work "
        "preserved, verified and audit-ready on this run's tip; rc-67/rc-78 were "
        "orchestration guards, not evidence. The counter-authority evidence gap remains "
        "the binding blocker; both DO-NOT-SERVE orders stand; admission fail-closed; "
        "frozen absolute bars stay REPORTED-ONLY and unmet on the v3 bytes; "
        "human_gate_ready=false; owner_decision_required=false. The Factory Director "
        "decides the successor question."
    )

    # 9. bookkeeping
    state["state_updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": "lex-evaluation-state-update/1",
                "run_id": RUN,
                "evidence_refs_before": n_before,
                "evidence_refs_after": len(refs),
                "refs_added": added,
                "refs_n_equals_len": state["evidence_refs_n"] == len(refs),
                "posture_false": {
                    k: state[k]
                    for k in (
                        "human_gate_ready",
                        "machine_gate_ready",
                        "packet_admitted",
                        "ready_for_owner_session",
                        "owner_decision_required",
                    )
                },
                "applied": [
                    f"github_run/proposed_run_id -> {RUN}",
                    f"operational_resume_{RUN} block added",
                    "repair_round1_40017649220 verification pointers added",
                    "minimal_ret_ca_benchmark latest_confirmation_* added",
                    f"test_suite.operational_resume_{RUN} added",
                    f"{len(added)} evidence refs appended",
                    "inherited-defect detail text corrected (duplicate ref resolves; list unchanged)",
                    "continue_recommended_reason + next_recommendation updated",
                ],
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
