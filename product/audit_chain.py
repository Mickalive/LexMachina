#!/usr/bin/env python3
"""Bounded audit-scope manifest for the product snapshot.

Why this exists
---------------
The product lane's operational resumes started stacking unaccepted cycles on a
persisted team snapshot.  By run 41199556067 the team ref held **10 commits and
103 changed files / 74k inserted lines over the accepted base**, and three
consecutive independent audits died at the 2700 s work quantum without writing
a gate.  The audit was not slow because a single check was slow: it was asked
to re-derive a whole unadjudicated chain.

This module makes the audit scope **explicit, bounded and machine-checkable**
without becoming an audit verdict:

* it names the accepted base (default ``origin/lab/product``) and the snapshot
  HEAD;
* it enumerates every commit between them and labels the ones that belong to
  the current run id (``CURRENT_CYCLE``) versus carried unadjudicated work
  (``CARRIED_UNJUDICATED``);
* it inventories the changed paths and rejects any path outside the product
  write scope or inside the auditor namespace;
* it verifies the cheap, local snapshot claims (state contract, both halves of
  the accepted pointer, current dossier/report/test/served slice, no gate) in
  **seconds**, using only the Python standard library and ``git``.

It never writes ``results/audit/**``, never mints a gate, never scores a frozen
bar and never calls a run accepted or rejected.  It is the *entry point* an
auditor can run first; the full re-derivation stays in
``product/audit_readiness.py``.

Usage
-----
    python3 product/audit_chain.py --run-id 41204598789
    python3 product/audit_chain.py --run-id 41204598789 --verify
    python3 product/audit_chain.py --run-id 41204598789 --out /tmp/chain.json

    # from the auditor's accepted-base checkout, pointing at the mounted team:
    python3 /tmp/lex_team/product/audit_chain.py --run-id 41204598789 \\
        --repo /tmp/lex_team --verify
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "product-audit-chain-scope/1"
DEFAULT_BASE = "origin/lab/product"
BASE_CANDIDATES = ("origin/lab/product", "lab/product", "refs/heads/lab/product")

#: The workflow's producer write scope plus the lane's own results/report dirs.
OWNED_PREFIXES = (
    "product/",
    "tests/product/",
    "results/product/",
    "reports/product/",
    "data/product/",
)
OWNED_EXACT = ("state/product.json",)
#: Paths that belong to the independent auditor, never to the producer.
AUDIT_PREFIXES = ("results/audit/product/", "reports/audit/product/")

DEFAULT_DIRECTION_VERSION = 68


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True,
                          text=True, check=False)


def _rev(repo: Path, ref: str) -> str | None:
    proc = _git(repo, "rev-parse", "--verify", "--quiet", ref)
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def _resolve_base(repo: Path, requested: str) -> str | None:
    if _rev(repo, requested):
        return requested
    for candidate in BASE_CANDIDATES:
        if _rev(repo, candidate):
            return candidate
    return None


def _in_scope(path: str) -> bool:
    return path in OWNED_EXACT or path.startswith(OWNED_PREFIXES)


def _is_audit_path(path: str) -> bool:
    return path.startswith(AUDIT_PREFIXES)


def _commits(repo: Path, base: str, head: str) -> list[dict[str, Any]]:
    proc = _git(repo, "log", "--reverse", "--format=%H%x09%s", f"{base}..{head}")
    rows: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition("\t")
        status = _git(repo, "diff-tree", "--no-commit-id", "--name-status",
                      "-r", sha).stdout
        changed: list[dict[str, str]] = []
        for entry in status.splitlines():
            parts = entry.split("\t")
            if len(parts) < 2:
                continue
            code, path = parts[0], parts[-1]
            changed.append({"status": code[:1], "path": path})
        rows.append({"sha": sha, "subject": subject, "changed": changed})
    return rows


def _diff_stat(repo: Path, base: str, head: str) -> dict[str, Any]:
    proc = _git(repo, "diff", "--numstat", f"{base}..{head}")
    inserted = deleted = 0
    files = 0
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        files += 1
        if parts[0].isdigit():
            inserted += int(parts[0])
        if parts[1].isdigit():
            deleted += int(parts[1])
    return {"files": files, "insertions": inserted, "deletions": deleted}


def _worktree_changed(repo: Path) -> list[str]:
    proc = _git(repo, "status", "--porcelain", "-uall")
    paths = []
    for line in proc.stdout.splitlines():
        if len(line) > 3:
            paths.append(line[3:])
    return sorted(paths)


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _check(check_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"id": check_id, "status": "PASS" if ok else "FAIL", "detail": detail}


def build(repo: Path, run_id: str,
          direction_version: int = DEFAULT_DIRECTION_VERSION,
          base_ref: str = DEFAULT_BASE,
          require_dossier: bool = True) -> dict[str, Any]:
    """Build the chain-scope record.  Pure local reads; no network, no gate."""
    started = time.monotonic()
    repo = repo.resolve()
    base = _resolve_base(repo, base_ref)
    head = _rev(repo, "HEAD")
    worktree = _worktree_changed(repo)
    commit_rows: list[dict[str, Any]] = []
    stat = {"files": 0, "insertions": 0, "deletions": 0}
    base_sha = _rev(repo, base) if base else None
    if base and head:
        commit_rows = _commits(repo, base, head)
        stat = _diff_stat(repo, base, head)
        ancestor = _git(repo, "merge-base", "--is-ancestor", base, head)
        base_is_ancestor = ancestor.returncode == 0
    else:
        base_is_ancestor = False

    run_token = str(run_id)
    for row in commit_rows:
        row["attribution"] = (
            "CURRENT_CYCLE" if run_token in row["subject"]
            else "CARRIED_UNJUDICATED")
        row["changed_paths"] = [c["path"] for c in row["changed"]]
        row["out_of_scope"] = sorted(
            p for p in row["changed_paths"] if not _in_scope(p))
        row["audit_namespace_paths"] = sorted(
            p for p in row["changed_paths"] if _is_audit_path(p))

    carried = [r for r in commit_rows if r["attribution"] != "CURRENT_CYCLE"]
    current = [r for r in commit_rows if r["attribution"] == "CURRENT_CYCLE"]
    all_changed = sorted({p for r in commit_rows for p in r["changed_paths"]})
    out_of_scope = sorted(p for p in all_changed if not _in_scope(p))
    audit_paths = sorted(p for p in all_changed if _is_audit_path(p))
    # Pre-final-commit builds legitimately have no commit yet; the in-scope
    # working tree is then the audit subject and must be declared as such.
    building_uncommitted = bool(base_sha) and base_sha == head and bool(worktree)

    if carried:
        scope_class = "CARRIED_CHAIN"
    elif current:
        scope_class = "CLEAN_SINGLE_CYCLE"
    elif building_uncommitted:
        scope_class = "UNCOMMITTED_BUILD"
    else:
        scope_class = "EMPTY"

    state_path = repo / "state" / "product.json"
    state = _load(state_path)
    checks = [
        _check(
            "state_contract",
            state.get("direction_version") == direction_version
            and state.get("cycle_status") not in (None, "INITIALIZED"),
            {
                "direction_version": state.get("direction_version"),
                "expected_direction_version": direction_version,
                "cycle_status": state.get("cycle_status"),
                "path": "state/product.json",
            },
        ),
        _check(
            "accepted_pointer_present",
            bool(state.get("accepted_run_id")) and bool(state.get("accepted_commit")),
            {
                "accepted_run_id": state.get("accepted_run_id"),
                "accepted_commit": state.get("accepted_commit"),
                "both_halves_rechecked_by": "product/audit_readiness.py check_posture",
            },
        ),
        _check(
            "current_dossier",
            (not require_dossier)
            or (repo / "results" / "product" / "audit_readiness"
                / f"CYCLE_{run_id}_audit_readiness.json").is_file(),
            {"path": f"results/product/audit_readiness/CYCLE_{run_id}_audit_readiness.json",
             "required": require_dossier},
        ),
        _check(
            "current_report",
            (repo / "reports" / "product" / f"CYCLE_{run_id}.md").is_file(),
            {"path": f"reports/product/CYCLE_{run_id}.md"},
        ),
        _check(
            "current_cycle_test",
            (repo / "product" / "tests" / f"test_cycle_{run_id}.py").is_file(),
            {"path": f"product/tests/test_cycle_{run_id}.py"},
        ),
        _check(
            "current_served_slice",
            (repo / "results" / "product" / "server_slice" / run_id
             / "summary.json").is_file(),
            {"path": f"results/product/server_slice/{run_id}/summary.json"},
        ),
        _check(
            "no_gate_minted",
            not (repo / "results" / "audit" / "product"
                 / f"CYCLE_{run_id}_GATE.json").exists(),
            {"path": f"results/audit/product/CYCLE_{run_id}_GATE.json"},
        ),
        _check(
            "no_audit_namespace_write",
            not audit_paths,
            {"paths": audit_paths},
        ),
        _check(
            "paths_in_product_scope",
            not out_of_scope and all(_in_scope(p) for p in worktree),
            {"committed_out_of_scope": out_of_scope,
             "worktree_out_of_scope": sorted(
                 p for p in worktree if not _in_scope(p))},
        ),
        _check(
            "bounded_audit_scope",
            not carried,
            {
                "classification": scope_class,
                "current_cycle_commits": [r["sha"] for r in current],
                "carried_unadjudicated_commits": [
                    {"sha": r["sha"], "subject": r["subject"]}
                    for r in carried
                ],
                "rule": (
                    "a snapshot promoted for audit must be a clean delta for "
                    "the current run; prior unaccepted chain commits stay on "
                    "their own cycle refs and are not re-derived here"
                ),
            },
        ),
    ]
    failed = [c["id"] for c in checks if c["status"] != "PASS"]
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": str(run_id),
        "direction_version": direction_version,
        "accepted_base": {
            "requested_ref": base_ref,
            "resolved_ref": base,
            "head": base_sha,
            "is_ancestor_of_head": base_is_ancestor,
        },
        "snapshot": {
            "head": head,
            "commits_since_base": len(commit_rows),
            "current_cycle_commits": len(current),
            "carried_unadjudicated_commits": len(carried),
            "diff_stat": stat,
            "changed_paths": all_changed,
            "commits": commit_rows,
        },
        "scope_classification": scope_class,
        "worktree_changed_paths": worktree,
        "checks": checks,
        "failed_checks": failed,
        "overall_status": "PASS" if not failed else "FAIL",
        "measured_seconds": round(time.monotonic() - started, 3),
        "claim_ceiling": (
            "An audit-scope manifest, not an audit. It labels the snapshot's "
            "commits, inventories paths and re-checks local file presence and "
            "state fields; it writes no gate, scores no frozen bar and makes "
            "no legal, serve or acceptance claim."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=None,
                    help="cycle run id (default: state current_cycle_run_id)")
    ap.add_argument("--repo", default=None,
                    help="repository/worktree root (default: this script's repo)")
    ap.add_argument("--base", default=DEFAULT_BASE,
                    help=f"accepted-base ref (default {DEFAULT_BASE})")
    ap.add_argument("--direction-version", type=int,
                    default=DEFAULT_DIRECTION_VERSION)
    ap.add_argument("--out", default=None, help="write the JSON record here")
    ap.add_argument("--verify", action="store_true",
                    help="exit non-zero unless every check passes")
    args = ap.parse_args(argv)

    default_repo = Path(__file__).resolve().parents[1]
    repo = Path(args.repo).resolve() if args.repo else default_repo
    run_id = args.run_id
    if not run_id:
        state = _load(repo / "state" / "product.json")
        run_id = str(state.get("current_cycle_run_id") or "")
    if not run_id:
        print("no run id and state/product.json has no current_cycle_run_id",
              file=sys.stderr)
        return 2

    record = build(repo, run_id, args.direction_version, args.base)
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    if args.verify and record["overall_status"] != "PASS":
        print("AUDIT_SCOPE_VERIFY_FAILED " + ",".join(record["failed_checks"]),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
