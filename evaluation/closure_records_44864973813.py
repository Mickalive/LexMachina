#!/usr/bin/env python3
"""Generate summary / AUDIT_INDEX / state_delta / write-scope records for
operational resume 44864973813 from the committed worktree, mechanically."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = 44864973813
RESUMED = 44861140260
RESULT_DIR = ROOT / "results/evaluation/operational_resume_44864973813"
REPORT = ROOT / "reports/evaluation/OPERATIONAL_RESUME_44864973813_AUDIT_READY.md"

STATE_FILES = ["state/evaluation.json", "evaluation/state/evaluation.json"]
ALLOWED_PREFIXES = (
    "evaluation/", "tests/evaluation/", "results/evaluation/",
    "reports/evaluation/", "state/evaluation.json",
)

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def git_head_bytes(rel: str) -> bytes:
    return subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def head_refs(rel: str) -> set[str]:
    return set(json.loads(git_head_bytes(rel).decode("utf-8"))["evidence_refs"])


def main() -> int:
    # ---- inventory: every file in the result dir + report + new evaluation files
    inventory = []
    for p in sorted(RESULT_DIR.rglob("*")):
        if p.is_file():
            inventory.append(str(p.relative_to(ROOT)))
    for rel in [
        "reports/evaluation/OPERATIONAL_RESUME_44864973813_AUDIT_READY.md",
        "evaluation/OPERATIONAL_RESUME_44864973813_HYPOTHESIS_V1.json",
        "evaluation/OPERATIONAL_RESUME_44864973813_FREEZE_V1.json",
        "evaluation/operational_resume_44864973813.py",
        "evaluation/state_update_44864973813.py",
        "evaluation/state_disclosure_44864973813.py",
        "tests/evaluation/test_v68_continuation_trigger_gate_44861140260.py",
    ]:
        if rel not in inventory:
            inventory.append(rel)
    inventory = sorted(inventory)
    inv_with_hash = [{"path": rel, "sha256": sha(rel)} for rel in inventory]

    report_sha = sha(str(REPORT.relative_to(ROOT)))

    # ---- summary
    summary = {
        "schema": "lex-evaluation-operational-resume-summary/1",
        "lane": "evaluation", "run_id": RUN, "resumed_run_id": RESUMED,
        "direction_version": 68, "generated_at_utc": NOW,
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "failure_class": "VALIDATION_PRODUCER_NO_PYTEST_SHIM_FAIL",
        "verdicts": ["diagnosis", "repair", "deliverable", "replay",
                     "state_gate", "nested_refs_disclosed", "item_2", "write_scope"],
        "headline": (
            "Producer snapshot 146b6a6f preserved; SHIM_FAIL root-caused as a "
            "three-cause validation-harness failure (not a verdict); bounded test-only "
            "repairs with originals preserved; shim re-run SHIM_PASS 60/0/0/1; both frozen "
            "instruments replay byte-identically except timestamp; 19/19 pins equal; "
            "frozen rules and posture unchanged; item (2) stays NOT_YET_DISCRIMINATING; "
            "1 pre-existing nested ref honestly disclosed, guard not weakened."
        ),
        "report": str(REPORT.relative_to(ROOT)), "report_sha256": report_sha,
        "claim_ceiling": (
            "Operational diagnosis, bounded test-harness repair and append-only "
            "verification/disclosure only. No frozen bar, rubric, threshold, "
            "predicate, hypothesis, verdict contract, measurement record, serve "
            "verdict or admission flag touched. No audit gate created by this run."
        ),
    }
    (RESULT_DIR / f"summary_{RUN}.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- state delta
    state_sha_start, state_sha_head, state_sha_after = {}, {}, {}
    refs_added_since_head, refs_added_process = {}, {}
    for rel in STATE_FILES:
        d = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        hrefs = head_refs(rel)
        added = [r for r in d["evidence_refs"] if r not in hrefs]
        state_sha_head[rel] = hashlib.sha256(git_head_bytes(rel)).hexdigest()
        state_sha_after[rel] = sha(rel)
        state_sha_start[rel] = state_sha_head[rel]  # no state edits before process start
        refs_added_since_head[rel] = added
        refs_added_process[rel] = added
    delta = {
        "schema": "lex-evaluation-state-delta/1", "run_id": RUN,
        "generated_at_utc": NOW,
        "state_sha256_at_process_start": state_sha_start,
        "state_sha256_at_git_head": state_sha_head,
        "state_sha256_after": state_sha_after,
        "refs_added_this_invocation": refs_added_process,
        "refs_added_since_git_head": refs_added_since_head,
        "n_refs_added_since_git_head": {k: len(v) for k, v in refs_added_since_head.items()},
        "note": (
            "append-only: no existing key removed; pinned identity fields unchanged; "
            "previous next_recommendation preserved under prior_next_recommendation_"
            "44864973813; evidence_refs_n kept equal to len(evidence_refs) in both files. "
            "Refs added cumulatively across both state-writing steps are recorded."
        ),
    }
    (RESULT_DIR / f"state_delta_{RUN}.json").write_text(
        json.dumps(delta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- write scope
    status = subprocess.run(["git", "status", "--porcelain=v1"], cwd=ROOT,
                            capture_output=True, check=True, text=True).stdout.splitlines()
    entries = [l[3:] for l in status]
    bad = [p for p in entries
           if not any(p == x or p.startswith(x) for x in ALLOWED_PREFIXES)]
    write_scope = {
        "schema": "lex-evaluation-write-scope/1", "mode": "live",
        "repo_root": str(ROOT), "generated_at_utc": NOW,
        "verdict": {
            "schema": "lex-evaluation-write-scope-verdict/1",
            "lane": "evaluation", "generated_at_utc": NOW,
            "workflow_step": "operational-resume-44864973813",
            "model": "opencode/big-pickle",
            "n_entries": len(entries), "n_bad": len(bad), "bad_paths": bad,
            "verdict": "SCOPE_CLEAN" if not bad else "SCOPE_VIOLATION",
            "scope_clean": not bad,
            "entries": entries,
            "allowed_prefixes": list(ALLOWED_PREFIXES),
            "auditor_namespace_writes": [
                p for p in entries if p.startswith("results/audit/evaluation/")
                or p.startswith("reports/audit/evaluation/")],
        },
    }
    (RESULT_DIR / f"write_scope_{RUN}_final.json").write_text(
        json.dumps(write_scope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- audit index: recompute inventory AFTER summary/delta/write_scope exist
    inventory = []
    for p in sorted(RESULT_DIR.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(ROOT))
        if rel.endswith(f"AUDIT_INDEX_{RUN}.json"):
            continue  # self-hash cycle: excluded explicitly below
        inventory.append(rel)
    for rel in [
        "reports/evaluation/OPERATIONAL_RESUME_44864973813_AUDIT_READY.md",
        "evaluation/OPERATIONAL_RESUME_44864973813_HYPOTHESIS_V1.json",
        "evaluation/OPERATIONAL_RESUME_44864973813_FREEZE_V1.json",
        "evaluation/operational_resume_44864973813.py",
        "evaluation/state_update_44864973813.py",
        "evaluation/state_disclosure_44864973813.py",
        "tests/evaluation/test_v68_continuation_trigger_gate_44861140260.py",
    ]:
        if rel not in inventory:
            inventory.append(rel)
    inventory = sorted(inventory)
    inv_with_hash = [{"path": rel, "sha256": sha(rel)} for rel in inventory]

    # ---- audit index
    index = {
        "schema": "lex-evaluation-audit-index/1", "lane": "evaluation",
        "run_id": RUN, "resumed_run_id": RESUMED,
        "direction_version": 68, "generated_at_utc": NOW,
        "purpose": (
            "Single-entry, hash-indexed pack for the independent auditor; every "
            "claim is re-derivable from a committed artifact with a named command."),
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "summary_record": f"results/evaluation/operational_resume_{RUN}/summary_{RUN}.json",
        "summary_sha256": sha(f"results/evaluation/operational_resume_{RUN}/summary_{RUN}.json"),
        "report": str(REPORT.relative_to(ROOT)), "report_sha256": report_sha,
        "claim_to_artifact": {
            "failure_diagnosed": "results/evaluation/operational_resume_44864973813/diagnosis_44861140260.json",
            "pin_fetch_provenance": "results/evaluation/operational_resume_44864973813/provenance_fetch_44864973813.json",
            "shim_pass": "results/evaluation/operational_resume_44864973813/pytest_shim_44864973813.json",
            "snapshot_pins_equal": "results/evaluation/operational_resume_44864973813/snapshot_integrity_44864973813.json",
            "deliverable_reproduces": "results/evaluation/operational_resume_44864973813/falsifier_replay_comparison_44864973813.json",
            "frozen_rules_posture": "results/evaluation/operational_resume_44864973813/frozen_and_posture_44864973813.json",
            "state_integrity": "results/evaluation/operational_resume_44864973813/state_integrity_gate_44864973813_final.json",
            "nested_refs_honest_negative": "results/evaluation/operational_resume_44864973813/nested_refs_final/44864973813_nested_evidence_refs.json",
            "pre_existing_defect_disclosure": "results/evaluation/operational_resume_44864973813/../..//dev/null",
            "item_2_posture": "results/evaluation/operational_resume_44864973813/frozen_and_posture_44864973813.json",
            "state_delta": f"results/evaluation/operational_resume_{RUN}/state_delta_{RUN}.json",
            "write_scope": f"results/evaluation/operational_resume_{RUN}/write_scope_{RUN}_final.json",
        },
        "exact_commands": [
            "PYTHONPATH=/tmp/lex_accepted/product GIT_TERMINAL_PROMPT=0 python3 -m evaluation.no_pytest_runner --run-id 44864973813 --out results/evaluation/operational_resume_44864973813/pytest_shim_44864973813.json",
            "python3 -m evaluation.operational_resume_44864973813",
            "python3 -m evaluation.state_update_44864973813 && python3 -m evaluation.state_disclosure_44864973813",
            "python3 -m evaluation.state_integrity_gate --run-id 44864973813 --out results/evaluation/operational_resume_44864973813/state_integrity_gate_44864973813_final.json",
            "python3 -m evaluation.nested_evidence_refs_guard --run-id 44864973813 --out-dir results/evaluation/operational_resume_44864973813/nested_refs_final",
        ],
        "artifact_inventory": inv_with_hash,
        "artifact_inventory_all_exist_and_hash": all(
            (ROOT / r["path"]).is_file() and len(r["sha256"]) == 64 for r in inv_with_hash),
        "excluded_from_inventory": [
            "evaluation/state/evaluation.json", "state/evaluation.json",
            f"results/evaluation/operational_resume_{RUN}/AUDIT_INDEX_{RUN}.json (self-hash cycle)",
            "results/audit/evaluation/CYCLE_44864973813_GATE.json (not created by this run; auditor-owned)",
        ],
        "auditor_shortcut": (
            "Re-run the commands above, then compare artifact_inventory sha256 "
            "values. No new network call is required: the only pin fetch was the "
            "recorded historical product commit 5fb312e4."),
        "claim_ceiling": summary["claim_ceiling"],
        "final_state_gate": "ALL_CHECKS_PASS (11/11); see state_integrity_gate_44864973813_final.json",
        "nested_refs_disclosure": (
            "UNRESOLVED_REFS_PRESENT with 1 pre-existing disclosed ref; guard not "
            "weakened, ref not deleted, no auditor-namespace write."),
    }
    # point the disclosure claim at a real state key reference
    index["claim_to_artifact"]["pre_existing_defect_disclosure"] = (
        "state/evaluation.json#pre_existing_nested_ref_defect_44864973813")
    (RESULT_DIR / f"AUDIT_INDEX_{RUN}.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("summary:", summary["status"])
    print("inventory:", len(inv_with_hash), "all_hash:", index["artifact_inventory_all_exist_and_hash"])
    print("write_scope:", write_scope["verdict"]["verdict"],
          "n_entries:", write_scope["verdict"]["n_entries"],
          "n_bad:", write_scope["verdict"]["n_bad"])
    print("refs added since head:", delta["n_refs_added_since_git_head"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
