#!/usr/bin/env python3
"""Append-only disclosure of a PRE-EXISTING nested-ref defect found by the
44864973813 nested-evidence-refs guard. Does not modify the guard, delete the
historical ref, or write to the auditor namespace.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "state/evaluation.json", ROOT / "evaluation/state/evaluation.json"]

DISCLOSURE = {
    "schema": "lex-evaluation-pre-existing-nested-ref-defect/1",
    "run_id": 44864973813,
    "direction_version": 68,
    "discovered_by": "evaluation/nested_evidence_refs_guard.py --run-id 44864973813",
    "guard_record": "results/evaluation/operational_resume_44864973813/nested_refs/44864973813_nested_evidence_refs.json",
    "guard_verdict": "UNRESOLVED_REFS_PRESENT",
    "n_unresolved": 1,
    "affected_json_path": "$.github_run_advance_40246705199.required_fixes_source",
    "known_unresolvable": "results/audit/evaluation/CYCLE_40246705199_GATE.json",
    "pre_existing": True,
    "present_in_HEAD_state": True,
    "introduced_by_this_resume": False,
    "mechanism": (
        "Historical pointer to a REVISE audit gate whose verification copy was "
        "recorded as mounted at /tmp/lex_prior_audit. That mount is absent in this "
        "image and no fetched git ref contains the gate path, so the guard's "
        "worktree / accepted-mount / branch-history resolution chain cannot resolve "
        "it. No prior operational-resume nested-refs record had an unresolved hit; "
        "the defect was latent in state from an earlier cycle that did not re-run "
        "the guard."
    ),
    "actions_taken": [
        "guard instrument NOT modified (no disclosure-set weakening)",
        "historical ref NOT deleted from state",
        "no results/audit/evaluation/ or reports/audit/evaluation/ write",
        "guard's UNRESOLVED_REFS_PRESENT record preserved as negative evidence",
    ],
    "claim": (
        "This resume does NOT claim NESTED_REFS_RESOLVED. It reports "
        "UNRESOLVED_REFS_PRESENT with exactly one pre-existing, formally disclosed "
        "ref that is unrelated to the 44861140260 snapshot or its verification."
    ),
}

ADDITIONAL_REFS = [
    "results/evaluation/operational_resume_44864973813/nested_refs/44864973813_nested_evidence_refs.json",
    "results/evaluation/operational_resume_44864973813/state_integrity_gate_44864973813.json",
]


def main() -> int:
    for path in FILES:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
        assert json.dumps(state, indent=2, ensure_ascii=False) + "\n" == raw, path
        state["pre_existing_nested_ref_defect_44864973813"] = json.loads(json.dumps(DISCLOSURE))
        verification = state["operational_resume_44864973813"]["verification"]
        verification["state_integrity"] = "ALL_CHECKS_PASS (11/11)"
        verification["nested_refs"] = (
            "UNRESOLVED_REFS_PRESENT: 1 pre-existing ref formally disclosed in "
            "pre_existing_nested_ref_defect_44864973813; not introduced by this resume"
        )
        refs = state["evidence_refs"]
        for ref in ADDITIONAL_REFS:
            if ref not in refs:
                refs.append(ref)
        missing = [r for r in refs if not (ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing, missing
        state["evidence_refs_n"] = len(refs)
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"disclosed in {path.relative_to(ROOT)}: refs {len(refs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
