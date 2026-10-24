#!/usr/bin/env python3
"""Operational-resume state repair for run 40094203248 (resume of 40089391202).

FINISHES the one incomplete piece of the 40089391202 state repair (its R1):
the 8 phantom local_eval_20261024T102833Z strings were corrected inside the
top-level evidence_refs list but left as dict KEYS inside
evidence_ref_role_notes, naming files that exist nowhere in the tree. This
script renames those 8 keys to the real committed artifact paths (values =
role labels, unchanged; nothing deleted), advances the run identity to this
resume run with full disclosure, appends the resume-verification evidence
refs, and records the verified reproduction result.

Append-only conventions honoured:
  - no historical artifact is overwritten (F-3B);
  - the 40089391202 deliverable of record stays untouched;
  - role-note VALUES (role labels) are preserved verbatim;
  - accepted_run_id stays 40084716045 (no new accept exists).
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
STATE = _REPO_ROOT / "state" / "evaluation.json"

# Same rename map the 40089391202 repair used for evidence_refs; applied here
# to the evidence_ref_role_notes KEYS it missed.
PHANTOM_FIX = {
    "results/evaluation/minimal_ret_ca_benchmark/local_eval_20261024T102833Z.json":
        "results/evaluation/minimal_ret_ca_benchmark/local_eval_20261024T102500Z.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_eval_20261024T102833Z.md":
        "reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_eval_20261024T102500Z.md",
    "results/evaluation/counter_evidence_quality_benchmark/local_eval_20261024T102833Z.json":
        "results/evaluation/counter_evidence_quality_benchmark/local_eval_20261024T102500Z.json",
    "reports/evaluation/COUNTER_EVIDENCE_QUALITY_BENCHMARK_local_eval_20261024T102833Z.md":
        "reports/evaluation/COUNTER_EVIDENCE_QUALITY_BENCHMARK_local_eval_20261024T102500Z.md",
    "results/evaluation/current_head_slice_quality/local_eval_20261024T102833Z.json":
        "results/evaluation/current_head_slice_quality/local_eval_20261024T102500Z.json",
    "reports/evaluation/CURRENT_HEAD_SLICE_QUALITY_local_eval_20261024T102833Z.md":
        "reports/evaluation/CURRENT_HEAD_SLICE_QUALITY_local_eval_20261024T102500Z.md",
    "results/evaluation/d2_path_scope_probe/local_eval_20261024T102833Z.json":
        "results/evaluation/d2_path_scope_probe/local_eval_1792837481.json",
    "reports/evaluation/D2_PATH_SCOPE_PROBE_local_eval_20261024T102833Z.md":
        "reports/evaluation/D2_PATH_SCOPE_PROBE_local_eval_1792837481.md",
}

NEW_REFS = [
    "evaluation/OPERATIONAL_RESUME_40094203248_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_40094203248_FREEZE_V1.json",
    "evaluation/operational_resume_40094203248_state_repair.py",
    "results/evaluation/d2_letterhead_pattern_profile/40094203248.json",
    "reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40094203248.md",
    "results/evaluation/d2_letterhead_pattern_profile/40094203248_reproduction_check_vs_40089391202.json",
    "results/evaluation/orchestration/40094203248_failure_chain_diagnosis.json",
    "reports/evaluation/OPERATIONAL_RESUME_40094203248.md",
]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    repairs: list[str] = []

    # R1 (FINISH of 40089391202's incomplete R1): rename phantom role-note keys
    role_notes = state.get("evidence_ref_role_notes") or {}
    renamed = 0
    new_notes: dict[str, str] = {}
    for k, v in role_notes.items():
        nk = PHANTOM_FIX.get(k, k)
        if nk != k:
            renamed += 1
        if nk in new_notes and new_notes[nk] != v:
            raise SystemExit(f"role-note merge conflict at {nk}")
        new_notes[nk] = v
    if renamed:
        state["evidence_ref_role_notes"] = dict(sorted(new_notes.items()))
        repairs.append(
            f"R1-finish: renamed {renamed} phantom evidence_ref_role_notes keys "
            f"from local_eval_20261024T102833Z names to their real committed "
            f"artifact paths (local_eval_20261024T102500Z / "
            f"local_eval_1792837481); role-label VALUES unchanged; nothing "
            f"deleted. Verified: all renamed keys resolve on disk."
        )
    assert renamed == 8, f"expected 8 phantom role-note keys, found {renamed}"
    import os
    missing = [k for k in new_notes if not ( _REPO_ROOT / k).exists()]
    # disclosed-historical keys may legitimately not exist on disk; only the
    # 8 renamed ones must resolve
    renamed_missing = [k for k in PHANTOM_FIX.values() if not (_REPO_ROOT / k).exists()]
    assert not renamed_missing, f"renamed keys still missing: {renamed_missing}"

    # R2: run identity advance with disclosure (never overwrite history)
    state.setdefault("run_identity_history", [])
    if state.get("github_run") == "40089391202":
        state["run_identity_history"].append({
            "run_id": "40089391202",
            "role": "item-(1) deliverable producer + state repair R1-R6",
            "team_commit": "9ae71fcff13d45f44df76a6a4c436dade701e699",
            "chain_outcome": "producer SUCCESS; audit job died without a gate "
                             "(orchestration class, requirement 20); NOT ACCEPTED",
        })
    state["github_run"] = "40094203248"
    state["operational_resume_of"] = "40089391202"
    repairs.append(
        "R2: run identity advanced to this operational-resume run 40094203248 "
        "(resume of 40089391202) with the run_identity_history disclosure; "
        "the 40089391202 artifacts remain the item-(1) deliverable of record"
    )

    # R3: reproduction-verification block (verified claim, references committed artifacts)
    repro = json.loads((_REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile"
                        / "40094203248_reproduction_check_vs_40089391202.json").read_text())
    assert repro["verdict"] == "REPRODUCES" and repro["n_mismatches"] == 0
    state["operational_resume_40094203248"] = {
        "resumed_producer_run": "40089391202",
        "resumed_team_commit": "9ae71fcff13d45f44df76a6a4c436dade701e699",
        "diagnosis": (
            "Run 40089391202 completed its producer job (team branch pushed, "
            "all steps green) but its audit job FAILED at the 'Independent "
            "audit' step after 2744s (~the 2700s agent work quantum + cleanup; "
            "rc attribution is a timing-based inference, logs unauthenticated-"
            "403) with no gate file and no audit branch; integrate was skipped; "
            "resilience dispatched this resume. ORCHESTRATION class per "
            "factory-wide requirement 20 — not a verdict, not a product "
            "defect, not a human-gate problem. See "
            "results/evaluation/orchestration/40094203248_failure_chain_diagnosis.json."),
        "work_preserved": (
            "The full 40089391202 producer snapshot preserved intact: freeze-"
            "first v67 item-(1) D2 letterhead pattern profile (hypothesis "
            "11:30:00Z -> freeze 11:32:00Z -> execution 11:34:28Z), controls "
            "C3-C6 all pass, LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED, 93 "
            "sha256-pinned bundles, 41 D2 rows -> 2 distinct P1 offset-0 "
            "multi-line court-header patterns, baseline 40062917685 unmoved, "
            "no bar movement."),
        "verification_this_run": {
            "reproduction_check": (
                "Fresh re-execution of the byte-identical frozen instrument "
                "(sha aac86527...) against the same sha256-pinned bundle "
                "population under run id 40094203248: REPRODUCES — all 19 "
                "frozen discrimination fields identical to 40089391202.json, "
                "0 mismatches, controls C3-C6 all pass; JSON file byte-identity "
                "NOT claimed (requirement 30). Artifact: "
                "results/evaluation/d2_letterhead_pattern_profile/"
                "40094203248_reproduction_check_vs_40089391202.json"),
            "product_p0_reverified_this_run": (
                "origin/lab/product head e2270c37 (accept 40080810801) still "
                "bypasses the filter on the fixture path: product/offline_slice.py:79 "
                "retrieval_mode='fixture', fixture_generation=True; product/query/"
                "pipeline.py:1339 'if not fixture_generation and "
                "adversarial_retrieval'. v67 item (2) therefore stays "
                "NOT_YET_DISCRIMINATING; no synthetic stand-in invented; the "
                "standing falsification record (item 3) not re-run."),
        },
        "repairs_applied": repairs,
        "claim_ceiling": (
            "Operational-resume disclosure only: names what was preserved, "
            "verified and repaired; makes no product, bar or serve claim."),
    }

    # R4: append new evidence refs (append-only)
    refs = state.setdefault("evidence_refs", [])
    for r in NEW_REFS:
        if r not in refs:
            refs.append(r)
    state["evidence_refs_n"] = len(refs)
    repairs.append(
        f"R4: appended {len(NEW_REFS)} resume-verification evidence refs "
        f"(hypothesis/freeze, re-execution artifact + report, reproduction "
        f"check, failure-chain diagnosis, this script, resume report); "
        f"evidence_refs_n={state['evidence_refs_n']}"
    )

    # refresh the operational resume disclosure's repair list
    state["operational_resume_40094203248"]["repairs_applied"] = repairs

    # posture stays fail-closed; nothing frozen touched
    state["cycle_status"] = "COMPLETE"
    state["evidence_tier"] = "REPRODUCED"
    state["acceptance_status"] = "PROPOSED_PENDING_INDEPENDENT_AUDIT"
    state["human_gate_ready"] = False
    state["machine_gate_ready"] = False
    state["packet_admitted"] = False
    state["ready_for_owner_session"] = False
    state["owner_decision_required"] = False
    state["state_updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["state_updated_by"] = "operational_resume_40094203248"

    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print(json.dumps({
        "state_sha256": _sha256_file(STATE),
        "repairs": repairs,
        "evidence_refs_n": state["evidence_refs_n"],
        "github_run": state["github_run"],
        "accepted_run_id": state["accepted_run_id"],
        "continue_recommended": state["continue_recommended"],
        "direction_version": state["direction_version"],
    }, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
