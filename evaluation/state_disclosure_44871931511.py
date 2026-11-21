#!/usr/bin/env python3
"""Post-guard disclosure patch for operational resume run 44871931511.

Two additive corrections after the first nested-evidence-refs guard run:
  1. point evidence_refs_resolution_44871931511.record at the filename the
     guard actually emits (<run_id>_nested_evidence_refs.json), so the state
     does not carry a self-inflicted unresolved ref;
  2. formally disclose the ONE unresolved nested ref that this resume
     INHERITED (results/audit/evaluation/CYCLE_40246705199_GATE.json under
     $.github_run_advance_40246705199.required_fixes_source), which was
     already the sole unresolved entry in the prior resume's final guard
     record and is not introduced by this run.
Pinned identity fields are asserted unchanged. Additive only; canonical
formatting round-trip proven before writing.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "state/evaluation.json", ROOT / "evaluation/state/evaluation.json"]

CORRECT_RECORD = (
    "results/evaluation/operational_resume_44871931511/"
    "44871931511_nested_evidence_refs.json"
)

DISCLOSURE = {
    "record": CORRECT_RECORD,
    "prior_record_showing_same_unresolved": (
        "results/evaluation/operational_resume_44864973813/"
        "nested_refs_final/44864973813_nested_evidence_refs.json"
    ),
    "json_path": "$.github_run_advance_40246705199.required_fixes_source",
    # key name is load-bearing: nested_evidence_refs_guard.py treats a parent
    # key of 'known_unresolvable' as an intentional historical disclosure
    # (DISCLOSURE_PARENT_KEYS) instead of charging it as a new unresolved ref.
    "known_unresolvable": "results/audit/evaluation/CYCLE_40246705199_GATE.json",
    "status": "INHERITED_UNRESOLVED_NOT_INTRODUCED_BY_44871931511",
    "detail": (
        "The gate file for run 40246705199 is not present in this worktree and "
        "not on any fetched ref; the state value itself annotates it as 'mounted "
        "verification copy at /tmp/lex_prior_audit'. It was already the single "
        "unresolved entry in the prior resume's final guard record "
        "(n_unresolved=1) and the key pre_existing_nested_ref_defect_44864973813 "
        "carries the original disclosure. Run 44871931511 neither introduced nor "
        "removed it; it is reported, not silently dropped."
    ),
    "introduced_by_this_run": False,
}


def main() -> int:
    for path in FILES:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
        assert json.dumps(state, indent=2, ensure_ascii=False) + "\n" == raw, \
            f"non-canonical formatting: {path}"

        pinned_before = {k: state[k] for k in
                         ("accepted_run_id", "github_run", "audit_status",
                          "evidence_tier", "direction_version")}
        assert state["direction_version"] == 68
        assert state["accepted_run_id"] == 40258497460

        res = state.setdefault("evidence_refs_resolution_44871931511", {})
        res["record"] = CORRECT_RECORD
        res["n_top_level_unresolved"] = 0
        state["pre_existing_nested_ref_defect_44871931511"] = json.loads(
            json.dumps(DISCLOSURE)
        )

        pinned_after = {k: state[k] for k in pinned_before}
        assert pinned_before == pinned_after

        refs = state["evidence_refs"]
        missing = [r for r in refs
                   if not (ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
        assert not missing, missing
        state["evidence_refs_n"] = len(refs)

        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"disclosed/patched {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
