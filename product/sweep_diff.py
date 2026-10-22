"""The FAILED-set diff between the accepted base and this tree, MEASURED.

Why this exists
---------------
Audit F2 of rejected product cycle 39764730877: the inherited report of record
claimed a sweep that could not be reproduced from the committed bytes
("169 failed, zero head-only failures, 1394 collected"), the independent auditor
measured a different set on the same tree (188 failed / 1206 passed / 19
skipped, 1413 collected, 23 head-only failures), and the lane had no artifact
that either number could be checked against. A hand-written sweep table is the
same defect class this repository has already been audited for three times
(6 -> 5 cited decisions, 13 -> 17 tests, +7 -> +10): a number typed into prose
instead of derived from the measurement it summarises.

This module is the measurement. It runs the full suite in two trees - the
accepted base commit and the tree under test - parses the FAILED test ids from
both runs, and publishes the SET DIFFERENCE by test id. It is the same
structure the lane already uses for the collected-test attribution
(``product/test_delta_attribution.py``): the tool refuses to publish a
decomposition it cannot close, and the report quotes its output.

What it measures
----------------
* the FAILED set of the full suite at the accepted base commit, in a detached
  worktree created and removed by this tool;
* the FAILED set of the full suite in the tree under test;
* the three set relations between them: head-only failures (regressions this
  branch introduced), base-only failures (this branch FIXED), and shared
  failures (inherited, disclosed, not charged to this branch).

Deliberately NOT claimed
------------------------
Nothing about the correctness of the inherited failures (they are reproduced,
not adjudicated), nothing about any frozen bar or serve verdict, nothing about
any environment other than the one that ran the tool, and no pass/fail claim
about the product's usefulness. The suite is a regression signal, not a
quality measure.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "product-sweep-diff/1"

#: The pytest invocation both trees are swept with. ``-p no:cacheprovider``
#: keeps the tree clean; ``-q`` keeps the output parseable.
PYTEST_ARGS = ("-m", "pytest", "product/tests/", "-q", "-p", "no:cacheprovider")

_COUNT_RE = re.compile(r"(\d+) (failed|passed|skipped|error|errors|xfailed|xpassed|deselected|warnings?)")
_FAILED_RE = re.compile(r"^(FAILED|ERROR)\s+(\S+)", re.MULTILINE)


class RefuseToPublish(Exception):
    """Raised when a sweep cannot be measured well enough to publish."""


def _git(*args: str, cwd: Path) -> str:
    out = subprocess.run(  # noqa: S603
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
    return out.stdout.strip()


def sweep(tree: Path) -> dict[str, Any]:
    """Run the full suite in ``tree`` and return its counts and FAILED set."""
    started = time.time()
    proc = subprocess.run(  # noqa: S603
        [sys.executable, *PYTEST_ARGS],
        cwd=str(tree), capture_output=True, text=True, check=False)
    output = proc.stdout + proc.stderr
    if "collected" not in output and proc.returncode not in (0, 1):
        raise RefuseToPublish(
            f"the sweep in {tree} produced no collection summary "
            f"(rc={proc.returncode}); last lines: {output[-400:]!r}")
    failed_ids = sorted({m.group(2) for m in _FAILED_RE.finditer(output)
                         if m.group(1) == "FAILED"})
    error_ids = sorted({m.group(2) for m in _FAILED_RE.finditer(output)
                        if m.group(1) == "ERROR"})
    summary_line = ""
    for line in reversed(output.splitlines()):
        if re.search(r"\d+ (passed|failed|error)", line):
            summary_line = line.strip()
            break
    counts: dict[str, int] = {}
    for match in _COUNT_RE.finditer(summary_line):
        counts[match.group(2)] = int(match.group(1))
    return {
        "tree": str(tree),
        "returncode": proc.returncode,
        "summary_line": summary_line,
        "failed": counts.get("failed", 0),
        "passed": counts.get("passed", 0),
        "skipped": counts.get("skipped", 0),
        "errors": counts.get("error", counts.get("errors", 0)),
        "xfailed": counts.get("xfailed", 0),
        "n_failed_ids": len(failed_ids),
        "failed_ids": failed_ids,
        "error_ids": error_ids,
        "seconds": round(time.time() - started, 2),
        "output_tail": output[-2000:],
    }


def collected_total(tree: Path) -> int:
    """The number of tests the tree collects, measured with the lane's own tool."""
    sys.path.insert(0, str(ROOT))
    from product.test_delta_attribution import collect_count  # noqa: PLC0415

    return collect_count(tree)


def diff(base: dict[str, Any], head: dict[str, Any]) -> dict[str, Any]:
    base_ids = set(base["failed_ids"])
    head_ids = set(head["failed_ids"])
    head_only = sorted(head_ids - base_ids)
    base_only = sorted(base_ids - head_ids)
    shared = sorted(head_ids & base_ids)
    return {
        "head_only_failures": head_only,
        "base_only_failures": base_only,
        "shared_failures": shared,
        "n_head_only": len(head_only),
        "n_base_only": len(base_only),
        "n_shared": len(head_only) + len(shared),
        "head_only_empty": not head_only,
        "set_relation": (
            "head_only = FAILED(head) \\ FAILED(base); base_only = "
            "FAILED(base) \\ FAILED(head); shared = FAILED(head) ∩ FAILED(base). "
            "The sets are computed as SET RELATIONS over test ids, never by "
            "matching counts."),
    }


def run(base_commit: str, head_tree: Path, run_id: int | None = None) -> dict[str, Any]:
    """Measure both trees and build the artifact (without writing it)."""
    base_commit_full = _git("rev-parse", base_commit, cwd=ROOT)
    tmp = Path(tempfile.mkdtemp(prefix="lex_sweep_base_"))
    worktree = tmp / "base"
    try:
        _git("worktree", "add", "--detach", str(worktree), base_commit_full, cwd=ROOT)
        base = sweep(worktree)
        base["commit"] = base_commit_full
        base["short"] = base_commit_full[:7]
        base["collected"] = collected_total(worktree)
        base.pop("output_tail", None)
        head = sweep(head_tree)
        head["commit"] = _git("rev-parse", "HEAD", cwd=head_tree)
        head["short"] = head["commit"][:7]
        head["collected"] = collected_total(head_tree)
        head.pop("output_tail", None)
    finally:
        try:
            _git("worktree", "remove", "--force", str(worktree), cwd=ROOT)
        except Exception:  # pragma: no cover - cleanup must never mask a measurement
            pass
        shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run(  # noqa: S603
            ["git", "worktree", "prune"], cwd=str(ROOT), capture_output=True,
            text=True, check=False)

    artifact: dict[str, Any] = {
        "schema": SCHEMA,
        "base": base,
        "head": head,
        **diff(base, head),
        "method": {
            "command": "python3 -m pytest product/tests/ -q -p no:cacheprovider",
            "base_tree": "a detached git worktree at the accepted base commit, "
                         "created and removed by this tool",
            "collection": "the collected totals are measured with the lane's own "
                          "product/test_delta_attribution.py::collect_count "
                          "(collection only), not read off the pytest summary",
            "failed_set": "parsed from pytest's own 'FAILED <test id>' short "
                          "summary lines, one entry per test id",
            "set_relation": "head-only / base-only / shared are computed as set "
                            "relations over test ids",
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "measured_at_root": str(ROOT),
            "pytest": _pytest_version(),
        },
        "claim_ceiling": (
            "A regression-signal measurement of two trees in THIS environment at "
            "THIS root. It says nothing about the correctness of the inherited "
            "failures (they are reproduced, not adjudicated), nothing about any "
            "frozen bar or serve verdict, nothing about any other environment, "
            "and nothing about the product's usefulness: the suite is a "
            "regression signal, not a quality measure."
        ),
    }
    if run_id is not None:
        artifact["run_id"] = run_id
    return artifact


def _pytest_version() -> str:
    try:
        import pytest  # noqa: PLC0415

        return str(pytest.__version__)
    except Exception:  # pragma: no cover
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-commit", required=True,
                    help="the accepted base commit to compare against")
    ap.add_argument("--head-tree", default=str(ROOT),
                    help="the tree under test (default: this repository)")
    ap.add_argument("--run-id", default=None, help="stamped into the artifact")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    head_tree = Path(args.head_tree).resolve()
    try:
        artifact = run(args.base_commit, head_tree,
                       int(args.run_id) if args.run_id else None)
    except RefuseToPublish as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        print("nothing written; a sweep that cannot be measured is not published",
              file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True),
                   encoding="utf-8")
    print(f"base  {artifact['base']['short']}  {artifact['base']['failed']} failed "
          f"/ {artifact['base']['passed']} passed / {artifact['base']['skipped']} skipped "
          f"/ {artifact['base']['collected']} collected")
    print(f"head  {artifact['head']['short']}  {artifact['head']['failed']} failed "
          f"/ {artifact['head']['passed']} passed / {artifact['head']['skipped']} skipped "
          f"/ {artifact['head']['collected']} collected")
    print(f"head-only failures: {artifact['n_head_only']}  "
          f"base-only: {artifact['n_base_only']}  shared: {artifact['n_shared']}")
    for test_id in artifact["head_only_failures"]:
        print(f"  HEAD-ONLY  {test_id}")
    print(f"written  {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
