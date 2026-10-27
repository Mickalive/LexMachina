#!/usr/bin/env python3
"""Fail-closed write-scope guard for the independent-audit workspace.

Run 40427889739 showed the audit job can finish its agent step and then die in
``Enforce audit scope and read gate`` with the public annotation
``auditor crossed scope:`` (runner exit code 3).  Because the always-run
``Persist audit snapshot`` step is skipped, that failure publishes no audit ref
and no gate: the run stays UNADJUDICATED even though the product-side tree is
intact.

The auditor owns exactly two directories::

    results/audit/<lane>/
    reports/audit/<lane>/

This guard turns that rule into a command the auditor can run *before* handing
off, so a scope violation is caught with a path list instead of a bare exit
code.  It is intentionally small and pure:

* ``parse_status`` reads ``git status --porcelain -uall`` (including renames);
* ``classify_paths`` is a pure prefix check with a directory boundary, so
  ``results/audit/product_evil/`` does not pass as ``.../product/``;
* ``check`` shells out to git unless a status text is supplied;
* ``--json`` exits 3 on any out-of-scope path, 0 otherwise.

It writes no files, changes no index, and never adjudicates a gate.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

SCHEMA = "product-audit-scope-guard/1"

# Trailing slash is the directory boundary.  Do not "fix" this to a bare
# prefix: results/audit/product_backup/ must NOT look like results/audit/product/.
SCOPES: dict[str, tuple[str, ...]] = {
    "audit": (
        "results/audit/product/",
        "reports/audit/product/",
    ),
    "producer": (
        "product/",
        "tests/product/",
        "results/product/",
        "reports/product/",
        "data/product/",
        "state/product.json",
        "requirements.txt",
        "pyproject.toml",
        "uv.lock",
    ),
}


def parse_status(text: str) -> list[str]:
    """Paths from ``git status --porcelain -uall`` (rename -> destination).

    A rename line looks like ``R  old -> new``.  The destination is what the
    commit would contain, so the destination is the path the write-scope check
    must judge; removing ``old`` cannot itself violate a write allowlist.
    """
    paths: list[str] = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        path = path.strip()
        if path.startswith('"') and path.endswith('"'):
            # Git quotes unusual names with C escapes; a quoted path is not
            # silently treated as in scope.  Normalise the common case and
            # leave the rest for the disallowed branch.
            path = path[1:-1]
        if path:
            paths.append(path)
    return paths


def classify_paths(paths: Iterable[str], *, scope: str = "audit") -> dict:
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; choose from {sorted(SCOPES)}")
    prefixes = SCOPES[scope]
    allowed: list[str] = []
    disallowed: list[str] = []
    for path in paths:
        (allowed if any(path.startswith(p) for p in prefixes)
         else disallowed).append(path)
    return {
        "schema": SCHEMA,
        "scope": scope,
        "allowed_prefixes": list(prefixes),
        "allowed": allowed,
        "disallowed": disallowed,
        "ok": not disallowed,
    }


def check(repo_root: Path, *, scope: str = "audit",
          status_text: str | None = None) -> dict:
    if status_text is None:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            cwd=repo_root, text=True, capture_output=True, check=False,
        )
        if proc.returncode != 0:
            return {
                "schema": SCHEMA,
                "scope": scope,
                "ok": False,
                "error": f"git status failed: {proc.stderr.strip()}",
                "allowed": [],
                "disallowed": [],
            }
        status_text = proc.stdout
    result = classify_paths(parse_status(status_text), scope=scope)
    result["repo_root"] = str(repo_root)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scope", choices=sorted(SCOPES), default="audit")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--status-file",
                    help="read a captured `git status --porcelain -uall`")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    status_text = None
    if args.status_file:
        status_text = Path(args.status_file).read_text(encoding="utf-8")
    result = check(Path(args.repo_root), scope=args.scope,
                   status_text=status_text)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["ok"]:
        print(f"scope guard: OK ({args.scope}); no out-of-scope paths")
    else:
        print(f"scope guard: FAIL ({args.scope})", file=sys.stderr)
        for path in result.get("disallowed") or []:
            print(f"  out of scope: {path}", file=sys.stderr)
        if result.get("error"):
            print(f"  error: {result['error']}", file=sys.stderr)
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
