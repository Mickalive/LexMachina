#!/usr/bin/env python3
"""Operational-resume state update for evaluation run 40044626742.

Idempotent: re-running only advances state_updated_at when every data field is
already correct. Never touches claim ceilings, posture flags, historical
measurement-of-record fields (benchmark_result, minimal_ret_ca_benchmark,
minimal_retrieval_ca_benchmark, offline_emission_path_benchmark, ...) or any
pre-existing evidence_ref.

Disclosed corrections (all justified in
results/evaluation/orchestration/40044626742_verification_of_40040574595.json):
  * accepted_run_id 39986080045 -> 40034814235: 39986080045 carries a PASS gate
    file but NO 'accept evaluation cycle 39986080045' commit anywhere in the
    repository (git log --all), so under factory-wide requirement 4 it is not an
    accepted run of record. The verified accept-commit lineage after 39936790420
    is 40002636192 -> 40012474431 -> 40034814235, each with both halves. The
    prior accepted_run_id_advance block is preserved verbatim under
    accepted_run_id_advance.superseded_advance.
  * run identity github_run/proposed_run_id -> 40044626742 (this resume).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RUN = "40044626742"
RESUME_FROM = "40040574595"
STATE = Path("state/evaluation.json")

NEW_EVIDENCE_REFS = [
    "evaluation/OPERATIONAL_RESUME_40044626742_HYPOTHESIS_V1.json",
    "results/evaluation/orchestration/40044626742_failure_chain_diagnosis.json",
    "results/evaluation/orchestration/40044626742_verification_of_40040574595.json",
    "results/evaluation/v65_head_advance_crosscheck/40044626742.json",
    "results/evaluation/v65_head_advance_crosscheck/40044626742_attempt1_shallow_mount_lineage_vacuous.json",
    "results/evaluation/v65_head_advance_crosscheck/falsification/40044626742.json",
    "results/evaluation/v65_head_advance_crosscheck/falsification/40044626742_engine_mapping_free_recall_falsifier.json",
    "results/evaluation/v65_head_advance_crosscheck/falsification/40044626742_attempt1.json",
    "results/evaluation/v65_head_advance_crosscheck/falsification/40044626742_attempt1_engine_mapping_free_recall_falsifier.json",
    "results/evaluation/orchestration/40044626742_self_suite_pytest_shim.json",
    "results/evaluation/orchestration/40044626742_multiling_prov_pytest_shim.json",
    "results/evaluation/orchestration/40044626742_falsification_family_pytest_shim.json",
    "results/evaluation/operational_resume/40044626742.json",
    "results/evaluation/orchestration/40044626742_resume_guard_pytest_shim.json",
    "reports/evaluation/V65_HEAD_ADVANCE_CROSSCHECK_40044626742.md",
    "reports/evaluation/V65_HEAD_ADVANCE_CROSSCHECK_40044626742_attempt1.md",
    "reports/evaluation/OPERATIONAL_RESUME_40044626742.md",
    "evaluation/operational_resume_40044626742_update_state.py",
    "tests/evaluation/test_operational_resume_40044626742.py",
]

RESUME_BLOCK = {
    "schema": "lex-evaluation-operational-resume/1",
    "run_id": RUN,
    "resumed_from_run": RESUME_FROM,
    "direction_version": 65,
    "mode": "operational resume of persisted producer snapshot (team tip e9f3f379 at dispatch; workflow input resume_from_run_id=40040574595)",
    "freeze_first": "hypothesis + pre-registered verification plan V1-V6 + orchestration diagnosis committed at 23459653 BEFORE this run's claim-bearing re-executions",
    "orchestration_diagnosis": "results/evaluation/orchestration/40044626742_failure_chain_diagnosis.json",
    "verification_record": "results/evaluation/orchestration/40044626742_verification_of_40040574595.json",
    "result_file": "results/evaluation/operational_resume/40044626742.json",
    "reexecution": "instrument v65_head_advance_crosscheck_v2 (sha 8a7e19c9 unchanged) re-run under --run-id 40044626742: NORMALIZED_IDENTICAL to the producer measurement of record 40040574595 (0 diffs); PASS_NO_FALSIFICATION; currency ALL_CONFIRMED 36/0/2/1; H2_FALSIFIED 14/14 (D2=10 D3=4 D4=4, 2 distinct decisions); falsification PRODUCT_FALSIFIED with the identical accepted 4-gate set and empty input_drift; controls 5/5; pins 25/25 re-identical",
    "shims": "self 12/0/0/0; multilingual-provenance 73/0/0/0; falsification family 51/0/21 (producer's one state-hygiene failure cleared, proving the producer's dangling-ref removal landed); this run's resume guard suite 14/0/0/0",
    "attempt1_disclosure": "first execution under this run returned NOT_MEASURED_VACUOUS solely because the depth-1 checkout's product mount lacked git history for the requirement-4 lineage grep; preserved under *_attempt1_* names; repaired by git fetch --depth=150 origin lab/product (no mount worktree file written); re-execution then normalized-identical",
    "state_corrections": "accepted_run_id 39986080045 -> 40034814235 (39986080045 has no accept-commit half of requirement 4; verified by git log --all; prior advance block preserved under accepted_run_id_advance.superseded_advance); run identity -> 40044626742; evidence_refs +19 all resolving; updater idempotency defect (double-wrap on re-run) disclosed and fixed in-run with a strengthened guard assertion",
    "verdict": "RESUME_VERIFIED_AND_AUDIT_READY",
    "posture_unchanged": {
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    },
}


def main() -> int:
    s = json.loads(STATE.read_text())
    s["accepted_run_id"] = "40034814235"
    cur = s.get("accepted_run_id_advance") or {}
    if cur.get("to") == "40034814235" and cur.get("from") == "39986080045":
        # already applied; unwrap one accidental double-wrap if a pre-fix run
        # nested the correction block inside itself, then keep byte-stable.
        inner = cur.get("superseded_advance")
        if isinstance(inner, dict) and inner.get("from") == "39986080045" \
                and inner.get("to") == "40034814235":
            cur = dict(cur)
            cur["superseded_advance"] = inner.get("superseded_advance", inner)
        advance = cur
    else:
        advance = {
            "from": "39986080045",
            "to": "40034814235",
            "reason": (
                "state-hygiene correction by operational resume 40044626742: the previous "
                "accepted_run_id 39986080045 carries a PASS gate file but NO 'accept "
                "evaluation cycle 39986080045' commit anywhere in the repository (verified "
                "by git log --all), so under factory-wide requirement 4 it is not an "
                "accepted run of record. The verified accept-commit lineage after "
                "39936790420 is 40002636192 -> 40012474431 -> 40034814235, each carrying "
                "both halves (PASS gate + accept commit). Disclosed, never laundered."
            ),
        }
        if cur:
            # preserve the inherited block; if a prior buggy double-run nested the
            # original one level deeper, unwrap it so the preserved block is the
            # ORIGINAL 39927760701 -> 39986080045 advance, exactly once.
            inner = cur.get("superseded_advance")
            if cur.get("from") == "39986080045" and isinstance(inner, dict) and \
                    inner.get("to") == "39986080045":
                cur = inner
            advance["superseded_advance"] = cur
    s["accepted_run_id_advance"] = advance
    s["github_run"] = RUN
    s["proposed_run_id"] = RUN
    s["cycle_status"] = "COMPLETE"
    s["operational_resume_40044626742"] = RESUME_BLOCK

    reason = s.get("continue_recommended_reason", "")
    addendum = (
        " RESUME 40044626742 (2026-10-24): the 40040574595 producer snapshot is now "
        "VERIFIED under independent re-execution (normalized-identical, 0 diffs; shims "
        "12/0/0/0, 73/0/0/0, 51/0/21; pins 25/25) and audit-ready; the orchestration "
        "failure was the producer dying after its state update but before committing "
        "results (workflow snapshot step preserved everything; audit skipped); "
        "accepted_run_id corrected 39986080045 -> 40034814235 with disclosure. The "
        "binding blocker remains unchanged: the counter-evidence extractor itself "
        "(14/14 verified rows on the flagship slice are letterhead/markup/"
        "language-mismatch)."
    )
    if "RESUME 40044626742" not in reason:
        s["continue_recommended_reason"] = reason + addendum

    refs = s.get("evidence_refs", [])
    added = 0
    for r in NEW_EVIDENCE_REFS:
        if r not in refs:
            refs.append(r)
            added += 1
    s["evidence_refs"] = refs
    s["evidence_refs_n"] = len(refs)
    s["state_updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    STATE.write_text(json.dumps(s, indent=2, sort_keys=False) + "\n")
    print(json.dumps({
        "run_id": RUN,
        "accepted_run_id": s["accepted_run_id"],
        "github_run": s["github_run"],
        "proposed_run_id": s["proposed_run_id"],
        "evidence_refs_n": s["evidence_refs_n"],
        "refs_added": added,
        "cycle_status": s["cycle_status"],
        "posture": {k: s.get(k) for k in (
            "human_gate_ready", "machine_gate_ready", "packet_admitted",
            "ready_for_owner_session", "owner_decision_required")},
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
