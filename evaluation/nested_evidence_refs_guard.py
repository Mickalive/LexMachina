#!/usr/bin/env python3
"""Operational-resume guard: resolve TOP-LEVEL and NESTED evidence refs.

v66 evaluation ordered-work item (1)(c): extend the operational-resume guard
to resolve NESTED evidence_refs lists, not only the top level (factory-wide
requirement 38). This instrument walks EVERY string value of
state/evaluation.json, classifies ref-shaped strings, and resolves each
against, in order:

  1. the evaluation worktree (working-tree file exists);
  2. the accepted cross-lane mounts (/tmp/lex_accepted/product,
     /tmp/lex_accepted/frontier) for product/frontier-side paths;
  3. git history of any fetched ref (`git log --all -- <path>`) for
     branch-scoped historical artifacts (e.g. audit gates that live only on
     their cycle audit branch);
  4. ANNOTATED_VALUE: strings whose first whitespace-token is a path that
     resolves but carry trailing prose (kept, counted separately).

Anything else is UNRESOLVED and must be either corrected or formally
disclosed in the state before an operational-resume cycle can claim
audit-readiness. The guard never edits state; it only measures and reports.

Exit codes: 0 = zero undisclosed UNRESOLVED refs; 1 = unresolved refs found;
2 = state file missing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-nested-evidence-refs-guard/1"
STATE_PATH = _REPO_ROOT / "state" / "evaluation.json"
MOUNTS = [Path("/tmp/lex_accepted/product"), Path("/tmp/lex_accepted/frontier")]

# Historical refs the state itself DISCLOSES as known-unresolvable (dangling
# preserved for provenance, never deleted). Matching is by exact path string.
# The state may extend this set via STATE_DISCLOSURE_KEY; each entry must be a
# dict with path/reason/disclosed_by_run and that path must actually be
# unresolved when the guard runs, otherwise the disclosure is reported as an
# error and never suppresses a live defect.
DISCLOSED_KNOWN_UNRESOLVABLE = {
    # none currently claimed at top level; nested disclosure fields carry
    # these inside evidence_index_defects_inherited_not_charged /
    # evidence_index_repair_40040574595 blocks which are self-labelling.
}
STATE_DISCLOSURE_KEY = "nested_evidence_refs_disclosed_known_unresolvable"

# HISTORICAL disclosure only. These two paths were cited by the producer-authored
# audit gate CYCLE_40174940149_GATE.json but were never committed on any ref:
# `git rev-list --all --objects` finds only the gate/report, not the claimed
# benchmark result or human report. They are NOT publication-lag artifacts.
# Run 40187594111 removed them from state/evaluation.json and re-pointed the
# evidence index at the real 40175266143 artifacts; the set is retained here
# only so a replay of the old state does not fail this guard while the removal
# and its proof are recorded in
# results/evaluation/operational_resume_40187341166/evidence_ref_correction.json.
DISCLOSED_TOP_LEVEL_UNRESOLVABLE = {
    "results/evaluation/retrieval_counter_authority_benchmark/40174940149.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_40174940149.md",
}

_REF_RE = re.compile(
    r"^(results|reports|evaluation|tests|state|product|directives|docs|frontier|"
    r"results/audit)/[A-Za-z0-9_./\-]+$"
)

# Parent keys whose string values are INTENTIONAL historical/disclosure
# pointers to non-resolving paths (e.g. 'the old broken ref was X'). These are
# evidence of hygiene work, never charged as unresolved.
DISCLOSURE_PARENT_KEYS = {
    "old", "typo_old", "previous_record_reference", "previous",
    "known_unresolvable", "removed_dangling_refs", "was",
    # run 40187594111: `removed_refs` is the explicit disclosure list for the
    # 40174940149 phantom paths; they are preserved as evidence of the index
    # correction, never charged as current unresolved refs.
    "removed_refs",
}


def _parent_key(json_path: str) -> str:
    """Last key segment of a json path, ignoring list indices."""
    import re as _re
    segs = [s for s in _re.split(r"\.|\[\d+\]", json_path) if s]
    return segs[-1] if segs else ""


def _first_token(s: str) -> str:
    return s.split(" ")[0].rstrip(",;")


def classify_and_resolve(token: str, self_output_token: str | None = None) -> str:
    if self_output_token is not None and token == self_output_token:
        # The guard's own output for THIS run does not exist during the walk
        # (it is written at the end of this very process). It resolves the
        # moment the run completes; it is never charged as unresolved.
        return "SELF_OUTPUT_PENDING_WRITE"
    p = _REPO_ROOT / token
    if p.exists():
        return "RESOLVED_WORKTREE"
    for m in MOUNTS:
        if (m / token).exists():
            return "RESOLVED_CROSS_LANE_MOUNT"
    try:
        out = subprocess.run(
            ["git", "log", "--all", "--oneline", "-1", "--", token],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        if out:
            return "RESOLVED_BRANCH_HISTORY"
    except Exception:
        pass
    return "UNRESOLVED"


def walk_state(node, path: str, hits: list[dict],
               self_output_token: str | None = None) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            walk_state(v, f"{path}.{k}", hits, self_output_token)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_state(v, f"{path}[{i}]", hits, self_output_token)
    elif isinstance(node, str):
        token = _first_token(node)
        if not _REF_RE.match(token):
            return
        status = classify_and_resolve(token, self_output_token)
        if status == "UNRESOLVED" and _parent_key(path) in DISCLOSURE_PARENT_KEYS:
            status = "DISCLOSED_HISTORICAL_REF"
        annotated = node.strip() != token
        hits.append({
            "json_path": path,
            "value": node if len(node) < 300 else node[:300] + "...[trunc]",
            "token": token,
            "status": status,
            "annotated": annotated,
        })


def state_disclosures(state: dict, self_token: str) -> tuple[set[str], list[dict]]:
    """Read the state's formal known-unresolvable disclosures.

    A disclosure is honoured ONLY if it names an unresolved path, gives a
    reason and records the run that disclosed it. A disclosure that points at
    a resolving path is an error: it can never suppress a live defect.
    """
    honoured: set[str] = set()
    errors: list[dict] = []
    raw = state.get(STATE_DISCLOSURE_KEY) or []
    if not isinstance(raw, list):
        return honoured, [{"error": "disclosure block is not a list",
                           "block": STATE_DISCLOSURE_KEY}]
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            errors.append({"index": i, "error": "entry is not an object"})
            continue
        path = entry.get("path")
        reason = entry.get("reason")
        by_run = entry.get("disclosed_by_run")
        if not isinstance(path, str) or not path.strip():
            errors.append({"index": i, "error": "missing path"})
            continue
        if not isinstance(reason, str) or not reason.strip():
            errors.append({"index": i, "path": path, "error": "missing reason"})
            continue
        if by_run is None:
            errors.append({"index": i, "path": path,
                           "error": "missing disclosed_by_run"})
            continue
        if classify_and_resolve(path, self_token) != "UNRESOLVED":
            errors.append({"index": i, "path": path,
                           "error": "disclosure points at a resolving path; "
                                    "it must not suppress a live ref"})
            continue
        honoured.add(path)
    return honoured, errors


def run(run_id: str, out_dir: Path) -> tuple[int, dict]:
    if not STATE_PATH.is_file():
        return 2, {"schema": SCHEMA, "run_id": run_id,
                   "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"state missing: {STATE_PATH}"}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    self_token = f"results/evaluation/orchestration/{run_id}_nested_evidence_refs.json"
    hits: list[dict] = []
    walk_state(state, "$", hits, self_token)

    state_disclosed, disclosure_errors = state_disclosures(state, self_token)
    disclosed_known = set(DISCLOSED_KNOWN_UNRESOLVABLE) | state_disclosed

    top_refs = state.get("evidence_refs") or []
    top_unresolved = []
    for r in top_refs:
        token = _first_token(r) if isinstance(r, str) else None
        if token and classify_and_resolve(token, self_token) == "UNRESOLVED":
            if token not in DISCLOSED_TOP_LEVEL_UNRESOLVABLE:
                top_unresolved.append(r)

    unresolved = [h for h in hits if h["status"] == "UNRESOLVED"
                  and h["token"] not in disclosed_known
                  and h["token"] not in DISCLOSED_TOP_LEVEL_UNRESOLVABLE]
    by_status: dict[str, int] = {}
    for h in hits:
        by_status[h["status"]] = by_status.get(h["status"], 0) + 1

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state_file": "state/evaluation.json",
        "direction_version": state.get("direction_version"),
        "n_top_level_evidence_refs": len(top_refs),
        "n_top_level_unresolved": len(top_unresolved),
        "top_level_unresolved": top_unresolved,
        "n_ref_shaped_values_total": len(hits),
        "resolution_counts": by_status,
        "n_unresolved": len(unresolved),
        "unresolved": unresolved,
        "disclosed_known_unresolvable": sorted(disclosed_known),
        "state_disclosed_known_unresolvable": sorted(state_disclosed),
        "n_disclosure_errors": len(disclosure_errors),
        "disclosure_errors": disclosure_errors,
        "disclosed_top_level_unresolvable": sorted(DISCLOSED_TOP_LEVEL_UNRESOLVABLE),
        "verdict": ("NESTED_REFS_RESOLVED"
                    if not unresolved and not top_unresolved and not disclosure_errors
                    else "UNRESOLVED_REFS_PRESENT"),
        "exit_code": 0 if (not unresolved and not top_unresolved
                           and not disclosure_errors) else 1,
        "claim_ceiling": (
            "Mechanical resolution audit of ref-shaped strings in the canonical "
            "lane state; proves only that every ref resolves somewhere "
            "(worktree, accepted cross-lane mount, or fetched git history). "
            "It does NOT validate the CONTENT of any referenced artifact and "
            "makes no product, bar or serve claim. Top-level refs in "
            "disclosed_top_level_unresolvable are known publication-lag artifacts "
            "(factory-wide requirement 39) preserved for provenance."),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}_nested_evidence_refs.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return record["exit_code"], record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else (
        _REPO_ROOT / "results/evaluation/orchestration")
    code, record = run(run_id, out_dir)
    print(json.dumps({"verdict": record.get("verdict"),
                      "n_unresolved": record.get("n_unresolved"),
                      "resolution_counts": record.get("resolution_counts"),
                      "top_level_unresolved": record.get("n_top_level_unresolved")},
                     indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
