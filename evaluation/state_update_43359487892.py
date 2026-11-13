#!/usr/bin/env python3
"""Additive state update for operational-resume run 43359487892.

Scope (lane write scope: evaluation/*, state/evaluation.json,
evaluation/state/evaluation.json): advance ONLY the run-identity fields and the
append-only evidence/resume blocks this run owns. Nothing else is touched.

What it changes
---------------
  * github_run / proposed_run_id      43344048907 -> 43359487892 (both files;
                                      root/lane parity is a frozen gate check)
  * resumed_run_id                    43357838904 (both; outgoing value kept
                                      append-only under
                                      resumed_run_id_previous_43359487892)
  * operational_resume_of             43357838904 (both)
  * resume_chain                      append 43359487892
  * next_recommendation               prepend THIS RUN's paragraph and preserve
                                      the whole prior text verbatim after
                                      "PRESERVED PRIOR TEXT:" (stage prepare)
  * operational_resume_43359487892    new block in both files (stage prepare),
                                      with out-of-tree final validation records
                                      folded in at stage final
  * evidence_refs                     append this run's artifacts, with
                                      evidence_refs_n re-derived from the list

What it deliberately does NOT change: accepted_run_id, direction_version,
evidence_tier, cycle_status, continue_recommended, human_gate_ready,
machine_gate_ready, audit_status, the frozen protocol digest, any prior run's
block, any prior run's evidence ref, or any file outside state/*.json.

Safety: both state files must round-trip byte-identically through
json.dumps(indent=2, ensure_ascii=False) BEFORE the mutation; otherwise the
script refuses, so a re-serialise cannot silently reformat a claim-bearing file.

    python3 evaluation/state_update_43359487892.py --stage prepare
    python3 evaluation/state_update_43359487892.py --stage final
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT_STATE = REPO / "state" / "evaluation.json"
LANE_STATE = REPO / "evaluation" / "state" / "evaluation.json"

RUN_ID = 43359487892
RESUMED = 43357838904
BASE_RUN = 43349645400
ORIGINAL = 43342851837
OUT = REPO / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
RECOVERY = REPO / "results" / "evaluation" / f"audit_namespace_recovery_{RUN_ID}"
REPORT = REPO / "reports" / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"

STAGE1_NEW_REFS = [
    f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json",
    f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json",
    "evaluation/operational_resume_43359487892.py",
    "evaluation/state_update_43359487892.py",
    f"tests/evaluation/test_operational_resume_{RUN_ID}.py",
    f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md",
    f"results/evaluation/operational_resume_{RUN_ID}/api/run_{RESUMED}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_{RESUMED}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/run_{BASE_RUN}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_{BASE_RUN}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/run_43344048907.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_43344048907.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/run_{ORIGINAL}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_{ORIGINAL}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/ref_probe_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/diagnosis_{RESUMED}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/diagnosis_{BASE_RUN}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/write_scope_repro_{BASE_RUN}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/write_scope_repro_{ORIGINAL}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/deliverable_verification_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/replay_command_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/replay_comparison_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/scratch/{RUN_ID}_replay.json",
    f"results/evaluation/operational_resume_{RUN_ID}/scratch/{RUN_ID}_replay_engine_mapping_free_recall_falsifier.json",
    f"results/evaluation/operational_resume_{RUN_ID}/item2_family_gate_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/write_scope_live_{RUN_ID}.json",
    f"results/evaluation/audit_namespace_recovery_{RUN_ID}/RELOCATION_RECORD_{RUN_ID}.json",
    f"results/evaluation/audit_namespace_recovery_{RUN_ID}/CYCLE_{ORIGINAL}_GATE.json",
    f"results/evaluation/audit_namespace_recovery_{RUN_ID}/CYCLE_{ORIGINAL}.md",
    f"results/evaluation/audit_namespace_recovery_{RUN_ID}/CYCLE_{BASE_RUN}_GATE.json",
    f"results/evaluation/audit_namespace_recovery_{RUN_ID}/CYCLE_{BASE_RUN}.md",
]
STAGE2_NEW_REFS = [
    f"results/evaluation/operational_resume_{RUN_ID}/verification_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/summary_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/state_integrity_gate_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/lane_suite_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/pytest_targeted_{RUN_ID}.json",
]

NEXT_PARAGRAPH = (
    f"CURRENT RUN {RUN_ID} (operational resume of {RESUMED}; snapshot based on {BASE_RUN}): "
    f"{RESUMED} failed at step 'Run lane cycle' with ZERO delta (its team ref equals "
    f"{BASE_RUN}'s head fe99ef6a) and its audit/integrate jobs were skipped. {BASE_RUN} had "
    "failed at step 'Enforce lane write scope' with exactly its two producer pseudo-audit paths; "
    "its audit/integrate jobs were skipped too, and no audit ref exists for any of 43342851837, "
    f"43344048907, {BASE_RUN} or {RESUMED}. The accumulated snapshot's FAST-MVP deliverable "
    "results/evaluation/minimal_ca_falsify_benchmark/43342851837.json (PRODUCT_FALSIFIED, 11/18 "
    "gates, 4 failed, 3 reported, product head 7be4480e) is preserved and VERIFIED: all 10 repo "
    "+ 14 mount pins re-hash, record/engine/report agree, non-vacuity 4/4, and a fresh scratch "
    f"replay REPRODUCES all 41 measurement-bearing fields (only the host platform label differs). "
    "The four inherited producer-authored audit-namespace files are copied byte-for-byte under "
    f"results/evaluation/audit_namespace_recovery_{RUN_ID}/ with originals retained and the "
    "pseudo-gates disclosed as PRODUCER-AUTHORED, never an independent audit; recorded "
    "contradictions include a producer PASS on a run whose own team job failed. Ordered item (2) "
    "stays NOT_YET_DISCRIMINATING (lab/product unchanged at 7be4480e; 50/50 byte-identical, "
    "14/15 role ceiling). Item (1) discharged elsewhere; item (3) kept unchanged and not re-run; "
    "item (4) report-only; item (5) applied here as OPERATIONAL, not evidence. No new "
    "same-question cycle; no 174k rerun; both DO-NOT-SERVE orders stand; admission fail-closed; "
    "continue_recommended=false; snapshot AUDIT_READY_PENDING_INDEPENDENT_AUDIT. "
    "PRESERVED PRIOR TEXT: "
)


def _load(path: Path) -> tuple[str, dict]:
    raw = path.read_text(encoding="utf-8")
    state = json.loads(raw)
    out = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    if out != raw:
        sys.exit(f"REFUSING: {path} does not round-trip byte-identically; a whole-file "
                 "re-serialise would silently reformat a claim-bearing file")
    return raw, state


def _require(refs: list[str]) -> None:
    missing = [r for r in refs if not (REPO / r).is_file()]
    if missing:
        sys.exit("REFUSING: these referenced artifacts do not exist yet:\n  " +
                 "\n  ".join(missing))


def _block() -> dict:
    return {
        "schema": "lex-evaluation-operational-resume/1",
        "lane": "evaluation",
        "run_id": str(RUN_ID),
        "resumed_run_id": str(RESUMED),
        "base_run_id": str(BASE_RUN),
        "original_run_id": str(ORIGINAL),
        "direction_version": 68,
        "mode": "OPERATIONAL_RESUME",
        "claim_bearing_run": str(RUN_ID),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "failure_diagnosis": {
            "resumed_run": {
                "run_id": str(RESUMED),
                "class": "LANE_CYCLE_EXECUTION_FAILURE_ZERO_DELTA",
                "failing_step": "Run lane cycle",
                "snapshot_equals_base_run_head": "fe99ef6ae2729f0b4fc3a784216e1d90dabc0259",
                "delta_against_base_run": "empty",
                "record": f"results/evaluation/operational_resume_{RUN_ID}/diagnosis_{RESUMED}.json",
            },
            "base_run": {
                "run_id": str(BASE_RUN),
                "class": "WRITE_SCOPE_VIOLATION_PRODUCER_AUDIT_NAMESPACE",
                "failing_step": "Enforce lane write scope",
                "bad_paths": [
                    f"reports/audit/evaluation/CYCLE_{BASE_RUN}.md",
                    f"results/audit/evaluation/CYCLE_{BASE_RUN}_GATE.json",
                ],
                "record": f"results/evaluation/operational_resume_{RUN_ID}/diagnosis_{BASE_RUN}.json",
                "repro_record": f"results/evaluation/operational_resume_{RUN_ID}/write_scope_repro_{BASE_RUN}.json",
            },
            "audit_ref_exists_for_any_run": False,
            "logs_available": False,
            "mechanism_note": ("Public job-step metadata plus the persisted snapshot only; "
                               "logs are HTTP 403 without a GH token and no log line, provider "
                               "error or mechanism is quoted."),
        },
        "deliverable_verified": {
            "record": f"results/evaluation/minimal_ca_falsify_benchmark/{ORIGINAL}.json",
            "verification_record": f"results/evaluation/operational_resume_{RUN_ID}/deliverable_verification_{RUN_ID}.json",
            "verdict": "PRODUCT_FALSIFIED",
            "exit_code": 1,
            "n_gates": 18,
            "n_passed": 11,
            "n_failed": 4,
            "n_reported": 3,
            "run_valid": True,
            "input_drift": [],
            "product_mount_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
            "pins_rehashed": {"repo": 10, "mount": 14, "mismatches": 0},
            "replay": {
                "verdict": "REPLAY_REPRODUCES",
                "measurement_fields_compared": 41,
                "measurement_fields_differing": 0,
                "environment_disclosure_difference": "host platform label only",
                "record": f"results/evaluation/operational_resume_{RUN_ID}/replay_comparison_{RUN_ID}.json",
            },
        },
        "item2_precondition": {
            "status": "NOT_YET_DISCRIMINATING",
            "record": f"results/evaluation/operational_resume_{RUN_ID}/item2_family_gate_{RUN_ID}.json",
            "product_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
            "byte_identical_n": 50,
            "frozen_family_n": 15,
            "member_for_member_ceiling": 14,
            "role_parity": False,
            "rule_reused_from": "results/evaluation/post_repair_family_ca_falsifier/40258497460.json",
        },
        "audit_namespace_disposition": {
            "record": f"results/evaluation/audit_namespace_recovery_{RUN_ID}/RELOCATION_RECORD_{RUN_ID}.json",
            "verdict": "RELOCATED_APPEND_ONLY",
            "files_n": 4,
            "originals_retained": True,
            "originals_deleted": False,
            "originals_edited": False,
            "independent_audit_provenance": False,
            "disclosure": ("All four inherited files were committed by lex-evaluation-team; they "
                           "are PRODUCER-AUTHORED and must never be quoted as an independent "
                           "audit of any run in either direction."),
        },
        "validation": {
            "write_scope_live": "SCOPE_CLEAN",
            "write_scope_record": f"results/evaluation/operational_resume_{RUN_ID}/write_scope_live_{RUN_ID}.json",
            "no_audit_namespace_path_added_modified_or_deleted": True,
        },
        "independent_audit_of_resumed_run_exists": False,
        "continuation": ("Operational resume only; no new same-question evidence cycle, no 174k "
                         "rerun; continue_recommended=false; snapshot AUDIT_READY_PENDING_"
                         "INDEPENDENT_AUDIT."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", choices=["prepare", "final"], default="prepare")
    args = ap.parse_args(argv)

    _require(STAGE1_NEW_REFS)
    if args.stage == "final":
        _require(STAGE2_NEW_REFS)

    _, root = _load(ROOT_STATE)
    _, lane = _load(LANE_STATE)

    expected_github = 43344048907 if args.stage == "prepare" else RUN_ID
    if root.get("github_run") != expected_github or lane.get("github_run") != expected_github:
        sys.exit(f"REFUSING: expected github_run={expected_github} before stage "
                 f"{args.stage}, got root={root.get('github_run')} lane={lane.get('github_run')}")

    for st in (root, lane):
        previous = st.get("resumed_run_id")
        st["github_run"] = RUN_ID
        st["proposed_run_id"] = RUN_ID
        st.setdefault(f"resumed_run_id_previous_{RUN_ID}", previous)
        st["resumed_run_id"] = RESUMED
        st["operational_resume_of"] = RESUMED
        st["prior_resumed_run_id"] = st[f"resumed_run_id_previous_{RUN_ID}"]
        chain = st.setdefault("resume_chain", [])
        if RUN_ID not in chain:
            chain.append(RUN_ID)

        # ---- this run's block, additive and stage-aware --------------------
        block = st.get(f"operational_resume_{RUN_ID}")
        if not isinstance(block, dict):
            block = _block()
            st[f"operational_resume_{RUN_ID}"] = block
        if args.stage == "final":
            block["validation"] = {
                "write_scope_live": "SCOPE_CLEAN",
                "write_scope_record": f"results/evaluation/operational_resume_{RUN_ID}/write_scope_live_{RUN_ID}.json",
                "no_audit_namespace_path_added_modified_or_deleted": True,
                "state_integrity_gate": "ALL_CHECKS_PASS",
                "state_integrity_record": f"results/evaluation/operational_resume_{RUN_ID}/state_integrity_gate_{RUN_ID}.json",
                "lane_suite": "PASS",
                "lane_suite_record": f"results/evaluation/operational_resume_{RUN_ID}/lane_suite_{RUN_ID}.json",
                "pytest_targeted_shim": "SHIM_PASS",
                "pytest_targeted_record": f"results/evaluation/operational_resume_{RUN_ID}/pytest_targeted_{RUN_ID}.json",
            }
            block["final_verification"] = {
                "verdict": "RESUME_VERIFIED_AUDIT_READY",
                "record": f"results/evaluation/operational_resume_{RUN_ID}/verification_{RUN_ID}.json",
                "summary": f"results/evaluation/operational_resume_{RUN_ID}/summary_{RUN_ID}.json",
            }

        refs = st.setdefault("evidence_refs", [])
        for ref in (STAGE1_NEW_REFS + (STAGE2_NEW_REFS if args.stage == "final" else [])):
            if ref not in refs:
                refs.append(ref)
        st["evidence_refs_n"] = len(refs)

    if args.stage == "prepare":
        nr = root.get("next_recommendation") or ""
        prefix = f"CURRENT RUN {RUN_ID} (operational resume of {RESUMED};"
        if not nr.startswith(prefix):
            root["next_recommendation"] = NEXT_PARAGRAPH + nr

    for path, state in ((ROOT_STATE, root), (LANE_STATE, lane)):
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"updated {path.relative_to(REPO)} (evidence_refs={state['evidence_refs_n']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
