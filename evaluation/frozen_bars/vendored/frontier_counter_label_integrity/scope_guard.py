"""Offline scope self-check for the producer's write allow-list.

This module re-implements, in Python, the shell rule enforced by the workflow
step "Enforce team scope" in ``.github/workflows/frontier-team.yml`` (one line,
shown wrapped)::

    BAD=""; while IFS= read -r line; do p="${line:3}"; case "$p" in
    "frontier/$TEAM"/*|"tests/frontier/$TEAM"/*|"results/frontier/$TEAM"/*|
    "reports/frontier/$TEAM"/*|"state/frontier/$TEAM.json"|"data/frontier/$TEAM"/*|"")
    ;; *) BAD+="$p\n";; esac; done < <(git status --porcelain -uall)

so a producer can run the exact same check offline and before the workflow
does.  It is strictly a self-check of the *workflow's* rule and it never reads
``RULES.json``.

Why it must not read RULES.json (do NOT "fix" this mismatch by editing frozen
rules): the ``write_scope`` frozen in ``RULES.json`` legitimately lists
``results/audit/frontier/<team>/`` and ``reports/audit/frontier/<team>/``
because it describes the AUDIT job's checkout (the charter's placement
requirement is about the audit job's tree).  The PRODUCER job's allow-list is
narrower, comes from the workflow step, and excludes the audit tree, which the
audit job owns exclusively -- charter acceptance test (12) forbids producer
writes there.  The diagnosed operational failure (GitHub runs 38845649012
through 38851515402, eight dispatches) was exactly a producer writing audit
placement copies out of scope; this guard pins that rule so it cannot recur.

Offline, deterministic, no clock, no network.

    python3 -m frontier_counter_label_integrity.scope_guard --repo-root . [--json] [--quiet]
    python3 -m frontier_counter_label_integrity.cli --scope-check --out /tmp/lex_scope_check

Exit codes: 0 clean, 1 out-of-scope paths, 2 git error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Iterable

TEAM_ID = "frontier-counter-label-integrity"

WORKFLOW_REL = ".github/workflows/frontier-team.yml"


class ScopeGitError(RuntimeError):
    """git could not be run or exited non-zero."""


def allowed_prefixes(team_id: str = TEAM_ID) -> tuple[str, ...]:
    """The producer allow-list exactly as ordered in this team's charter.

    Every entry except the last is a directory prefix ending in ``/``; the
    ``state/...`` entry is a full path, not a prefix.
    """
    return (
        f"frontier/{team_id}/",
        f"tests/frontier/{team_id}/",
        f"results/frontier/{team_id}/",
        f"reports/frontier/{team_id}/",
        f"data/frontier/{team_id}/",
        f"state/frontier/{team_id}.json",
    )


def violations(paths: Iterable[str], team_id: str = TEAM_ID) -> list[str]:
    """Sorted paths that fall outside the allow-list.

    Matching semantics are the same as the workflow's bash ``case``: a path
    matches a directory entry iff it starts with it (the entry includes the
    trailing ``/``), the ``state/...json`` entry matches only itself, and the
    empty string is in scope.
    """
    entries = allowed_prefixes(team_id)
    out: list[str] = []
    for p in paths:
        if p == "":
            continue
        in_scope = any(
            p.startswith(entry) if entry.endswith("/") else p == entry
            for entry in entries
        )
        if not in_scope:
            out.append(p)
    return sorted(out)


def porcelain_paths(lines: Iterable[str]) -> list[str]:
    """Map porcelain v1 status lines to the path the workflow checks.

    The workflow takes ``${line:3}`` (the ``XY `` header is 3 characters).
    Deliberate one clarification of the workflow's literal behaviour: git
    writes a rename as ``XY old -> new`` and the workflow then carries the
    whole ``old -> new`` string; we take the part after `` -> `` because the
    destination is the path that actually exists in the tree (a literal
    `` -> `` inside a filename is not representable in this parsing either
    way, matching the workflow's own ambiguity).
    """
    out: list[str] = []
    for line in lines:
        p = line[3:]
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        out.append(p)
    return out


def git_status_paths(repo_root: str) -> list[str]:
    """``git status --porcelain -uall`` paths for ``repo_root``, workflow style."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo_root, "status", "--porcelain", "-uall"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ScopeGitError(f"git not found: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or str(exc)
        raise ScopeGitError(f"git status failed for {repo_root}: {detail}") from exc
    return porcelain_paths(proc.stdout.splitlines())


def check_repo_scope(repo_root: str) -> dict:
    """Self-check ``repo_root`` against the workflow's producer allow-list."""
    paths = git_status_paths(repo_root)
    bad = violations(paths)
    return {
        "ok": not bad,
        "violations": bad,
        "checked_paths": paths,
        "allowed_prefixes": list(allowed_prefixes()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scope-guard")
    ap.add_argument("--repo-root", default=".", help="repository root to check (default: .)")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    ap.add_argument("--quiet", action="store_true", help="print nothing")
    args = ap.parse_args(argv)

    try:
        result = check_repo_scope(args.repo_root)
    except ScopeGitError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        for p in result["violations"]:
            print(p)
        if result["ok"]:
            print(f"scope ok: {len(result['checked_paths'])} changed paths, all in scope")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
