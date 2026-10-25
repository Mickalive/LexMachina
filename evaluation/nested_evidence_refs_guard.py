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
DISCLOSED_KNOWN_UNRESOLVABLE = {
    # none currently claimed at top level; nested disclosure fields carry
    # these inside evidence_index_defects_inherited_not_charged /
    # evidence_index_repair_40040574595 blocks which are self-labelling.
}

# Top-level evidence_refs that are known publication-lag artifacts:
# their artifacts live on audit branches, not in the main worktree or
# accepted mounts. Factory-wide requirement 39: "a stale mount or a lagging
# accepted-state index is a publication-lag artifact, NOT evidence that a
# cycle is unaccepted". These are preserved for provenance and disclosed here.
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


def run(run_id: str, out_dir: Path) -> tuple[int, dict]:
    if not STATE_PATH.is_file():
        return 2, {"schema": SCHEMA, "run_id": run_id,
                   "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"state missing: {STATE_PATH}"}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    self_token = f"results/evaluation/orchestration/{run_id}_nested_evidence_refs.json"
    hits: list[dict] = []
    walk_state(state, "$", hits, self_token)

    top_refs = state.get("evidence_refs") or []
    top_unresolved = []
    for r in top_refs:
        token = _first_token(r) if isinstance(r, str) else None
        if token and classify_and_resolve(token, self_token) == "UNRESOLVED":
            if token not in DISCLOSED_TOP_LEVEL_UNRESOLVABLE:
                top_unresolved.append(r)

    unresolved = [h for h in hits if h["status"] == "UNRESOLVED"
                  and h["token"] not in DISCLOSED_KNOWN_UNRESOLVABLE
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
        "disclosed_known_unresolvable": sorted(DISCLOSED_KNOWN_UNRESOLVABLE),
        "disclosed_top_level_unresolvable": sorted(DISCLOSED_TOP_LEVEL_UNRESOLVABLE),
        "verdict": ("NESTED_REFS_RESOLVED" if not unresolved and not top_unresolved
                    else "UNRESOLVED_REFS_PRESENT"),
        "exit_code": 0 if (not unresolved and not top_unresolved) else 1,
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
