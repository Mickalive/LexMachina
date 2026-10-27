#!/usr/bin/env python3
"""One read-only command that hands an independent auditor a verified snapshot.

Why this exists
---------------
Four consecutive core-product runs produced no gate for reasons that are all
about the *cost* of auditing this tree, not about its content:

| run | audit outcome (public record) |
|---|---|
| 40423889401 | agent step OK, gate=REVISE - dossier hashes were stale |
| 40427889739 | agent step OK, then ``auditor crossed scope:`` exit 3 |
| 40429931848 | ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` exit 78 |
| 40436981920 | ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` exit 78 |

Two of those four are the auditor spending its whole 2700 s quantum
re-deriving facts the product can re-derive itself, and at least one is an
accidental write outside ``results/audit/<lane>/`` / ``reports/audit/<lane>/``
- ``git status --porcelain -uall`` sees any regenerated artifact as crossing
scope, and the workflow's own annotation then reports only a bare exit code.

The product lane cannot edit ``.github/**`` (control-plane scope), but it does
control how expensive its own claims are to check.  This module bundles the
existing instruments - ``state_contract.py``, ``cycle_verify.py``,
``audit_readiness.py --verify``, ``audit_scope_guard.py`` - behind one command
that is:

* **read-only by construction** - it never writes into the repository; its own
  ``git status --porcelain -uall`` before/after is part of its output, so a
  scope crossing it caused would be visible to the auditor as
  ``read_only_ok: false`` instead of as a workflow exit 3;
* **time-boxed** - ``--budget-seconds`` (default 600, well under the 2700 s
  quantum) turns a slow sub-check into a FAIL with the elapsed time recorded,
  never into a silent overrun;
* **fail-closed** - a check that cannot run is FAIL, never PASS, and the exit
  code is non-zero unless every selected check passed.

It writes no gate, adjudicates nothing, and labels no run accepted or
rejected.  A gate stays exactly what the workflow says it is.

Checks
------
``scope``     ``audit_scope_guard.py`` - are the working tree's dirty paths
              inside the directories the caller's role owns?
``state``     ``state_contract.py --check --json`` - lane state, write scope,
              audit-artifact ownership, direction version.
``dossier``   ``audit_readiness.py --verify <dossier>`` - every recorded claim
              artifact hash still matches the bytes on disk.
``ledger``    ``cycle_verify.py --json`` - the product's own one-command claim
              ledger, with the failing claim names copied into the handoff.
``tests``     ``pytest`` over a caller-chosen target (default: the product
              suite), counted from the tool's own summary line.

Usage
-----
    python3 product/audit_handoff.py --json                 # all checks
    python3 product/audit_handoff.py --only scope,ledger    # a subset
    python3 product/audit_handoff.py --dossier results/product/audit_readiness/CYCLE_<id>_audit_readiness.json
    python3 product/audit_handoff.py --root /tmp/lex_team   # run against a producer worktree
    python3 product/audit_handoff.py --out /tmp/handoff.json  # outside the repo
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

SCHEMA = "product-audit-handoff/1"

#: Default wall-clock ceiling.  The workflow's audit quantum is 2700 s; the
#: product's own handoff must finish with a large margin so the auditor keeps
#: its budget for *attacking* the work instead of re-deriving it.
DEFAULT_BUDGET_SECONDS = 600

#: Ordered so the cheap structural checks run before the expensive ones: a
#: broken state contract should not cost a suite run to discover.
CHECKS: tuple[str, ...] = ("scope", "state", "dossier", "ledger", "tests")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _porcelain(root: Path) -> list[str]:
    """``git status --porcelain -uall`` as a sorted path list (never raises)."""
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(root), capture_output=True, text=True, check=False,
        )
    except OSError:
        return ["<git-unavailable>"]
    if proc.returncode != 0:
        return [f"<git-status-failed rc={proc.returncode}>"]
    out: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) > 3:
            out.append(line[3:])
    return sorted(out)


def _run(args: list[str], cwd: Path, budget: float) -> dict[str, Any]:
    """Run a subprocess under the remaining budget; never raise on timeout."""
    started = time.monotonic()
    try:
        proc = subprocess.run(  # noqa: S603
            args, cwd=str(cwd), capture_output=True, text=True,
            timeout=max(1.0, budget), check=False,
        )
        timed_out = False
        rc: int | None = proc.returncode
        out, err = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = None
        out = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(
            exc.stdout, bytes) else (exc.stdout or "")
        err = (exc.stderr or b"").decode("utf-8", "replace") if isinstance(
            exc.stderr, bytes) else (exc.stderr or "")
    except OSError as exc:
        return {"command": args, "rc": None, "ok": False, "elapsed_s": 0.0,
                "error": f"{type(exc).__name__}: {exc}"}
    return {
        "command": args,
        "rc": rc,
        "ok": (rc == 0 and not timed_out),
        "timed_out": timed_out,
        "elapsed_s": round(time.monotonic() - started, 3),
        "stdout_full": out,
        "stdout_tail": out[-4000:],
        "stderr_tail": err[-2000:],
    }


def _emit(root: Path, name: str, run: dict[str, Any],
          observed: dict[str, Any] | None = None) -> dict[str, Any]:
    ok = bool(run.get("ok")) and not run.get("timed_out")
    return {
        "check": name,
        "status": "PASS" if ok else "FAIL",
        "ok": ok,
        "command": " ".join(run.get("command") or []),
        "rc": run.get("rc"),
        "timed_out": bool(run.get("timed_out")),
        "elapsed_s": run.get("elapsed_s"),
        "root": str(root),
        **({"error": run["error"]} if "error" in run else {}),
        **(observed or {}),
        "stdout_tail": (run.get("stdout_tail") or "")[-2000:],
        # Full stream for callers that must parse the sub-tool's JSON document;
        # stripped before the report is published (it is not claim content).
        "_stdout_full": run.get("stdout_full") or "",
    }


def _finalise(entry: dict[str, Any]) -> dict[str, Any]:
    entry.pop("_stdout_full", None)
    return entry


def _parse_json_tail(text: str) -> dict[str, Any] | None:
    """Last JSON object in a stream (the sub-tools print one document)."""
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def build(root: Path, *, checks: tuple[str, ...], budget: float,
          dossier: str | None, scope: str, tests: str | None,
          skip_tests: bool) -> dict[str, Any]:
    """Pure-ish driver: runs the selected sub-tools under one shared budget."""
    started = time.monotonic()
    status_before = _porcelain(root)
    results: list[dict[str, Any]] = []
    remaining = budget

    def spend(name: str, args: list[str]) -> dict[str, Any]:
        nonlocal remaining
        run = _run(args, root, remaining)
        remaining = max(0.0, remaining - float(run.get("elapsed_s") or 0.0))
        return _emit(root, name, run)

    if "scope" in checks:
        entry = spend("scope", [sys.executable,
                                str(root / "product" / "audit_scope_guard.py"),
                                "--scope", scope, "--json"])
        results.append(_finalise(entry))

    if "state" in checks:
        entry = spend("state", [sys.executable,
                                str(root / "product" / "state_contract.py"),
                                "--check", "--json"])
        payload = _parse_json_tail(entry.get("_stdout_full") or "")
        if payload is not None:
            entry["observed"] = {
                "ok": payload.get("ok"),
                "write_scope_ok": (payload.get("write_scope") or {}).get("ok"),
                "audit_ownership_ok": (
                    payload.get("audit_artifact_ownership") or {}).get("ok"),
                "workflow_validation_ok": (
                    payload.get("workflow_validation") or {}).get("ok"),
            }
            # A structurally parsed report that says "not ok" must fail the
            # handoff even though the subprocess exit code is what we saw.
            if payload.get("ok") is False:
                entry["status"], entry["ok"] = "FAIL", False
        results.append(_finalise(entry))

    if "dossier" in checks:
        if not dossier:
            results.append({
                "check": "dossier", "status": "FAIL", "ok": False,
                "command": "", "rc": None, "timed_out": False, "elapsed_s": 0.0,
                "root": str(root),
                "observed": {"reason": "NO_DOSSIER_NAMED",
                             "hint": "pass --dossier <path> or --skip-dossier"},
            })
        else:
            entry = spend("dossier", [sys.executable,
                                      str(root / "product" / "audit_readiness.py"),
                                      "--verify", dossier])
            payload = _parse_json_tail(entry.get("_stdout_full") or "")
            if payload is not None:
                entry["observed"] = {
                    "dossier_ok": payload.get("ok"),
                    "n_checked": payload.get("n_checked"),
                    "problems": payload.get("problems"),
                }
                if payload.get("ok") is False:
                    entry["status"], entry["ok"] = "FAIL", False
            results.append(_finalise(entry))

    if "ledger" in checks:
        entry = spend("ledger", [sys.executable,
                                 str(root / "product" / "cycle_verify.py"),
                                 "--json"])
        payload = _parse_json_tail(entry.get("_stdout_full") or "")
        if payload is not None:
            failed = [c for c in (payload.get("claims") or [])
                      if c.get("status") == "FAIL"]
            entry["observed"] = {
                "verdict": payload.get("verdict"),
                "n_claims": payload.get("n_claims"),
                "n_failed": payload.get("n_failed"),
                "failed_claims": [{"claim": c.get("claim"),
                                   "observed": c.get("observed")}
                                  for c in failed],
            }
            if payload.get("n_failed"):
                entry["status"], entry["ok"] = "FAIL", False
        results.append(_finalise(entry))

    if "tests" in checks and not skip_tests:
        target = tests or f"{root / 'product' / 'tests'}"
        entry = spend("tests", [sys.executable, "-m", "pytest", target,
                                "-q", "-p", "no:cacheprovider"])
        tail = entry.get("_stdout_full") or ""
        entry["observed"] = {"summary": tail.splitlines()[-1] if tail else None}
        results.append(_finalise(entry))

    status_after = _porcelain(root)
    read_only_ok = status_before == status_after
    if not read_only_ok:
        added = sorted(set(status_after) - set(status_before))
        removed = sorted(set(status_before) - set(status_after))
    else:
        added, removed = [], []

    passed = all(r["ok"] for r in results)
    budget_ok = (time.monotonic() - started) <= budget
    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "root": str(root),
        "budget_seconds": budget,
        "elapsed_s": round(time.monotonic() - started, 3),
        "budget_ok": budget_ok,
        "checks_requested": list(checks),
        "checks": results,
        "n_checks": len(results),
        "n_failed": sum(1 for r in results if not r["ok"]),
        "verdict": "PASS" if (passed and budget_ok) else "FAIL",
        "read_only": {
            "ok": read_only_ok,
            "n_paths_before": len(status_before),
            "n_paths_after": len(status_after),
            "added": added,
            "removed": removed,
            "meaning": "the handoff made no change to the repository; an "
                       "auditor that runs only this command cannot cross the "
                       "workflow's write-scope check by accident",
        },
        "claim_ceiling": (
            "Engineering verification of a committed snapshot by the product's "
            "own read-only instruments. It writes no gate, adjudicates no run, "
            "scores no frozen bar, measures no live OpenCaseLaw latency, and "
            "makes no answer-quality, legal-usefulness, serve or human-gate "
            "claim. A FAIL here is a product-owned finding, not an audit "
            "verdict; the audit verdict belongs to the independent auditor."),
    }


def _writable_target(path: Path, root: Path) -> str | None:
    """Refuse to write inside the repo outside the auditor's own directories."""
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None  # outside the repository: always fine
    parts = rel.parts
    if (parts[:3] == ("results", "audit", "product")
            or parts[:3] == ("reports", "audit", "product")):
        return None
    return (f"refusing to write {rel}: a producer checkout may only be written "
            "under product/, tests/product/, results/product/, reports/product/, "
            "data/product/ and state/product.json - and this tool writes "
            "nothing there by design; use a path outside the repository")


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=default_root,
                    help="checkout to verify (defaults to this file's checkout)")
    ap.add_argument("--only", default=None,
                    help=f"comma-separated subset of {','.join(CHECKS)}")
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--skip-dossier", action="store_true")
    ap.add_argument("--dossier", default=None)
    ap.add_argument("--scope", choices=("audit", "producer"), default="audit")
    ap.add_argument("--tests", default=None,
                    help="pytest target (file or directory) for the tests check")
    ap.add_argument("--budget-seconds", type=float, default=DEFAULT_BUDGET_SECONDS)
    ap.add_argument("--out", default=None,
                    help="write the JSON report to this path (outside the repo, "
                         "or under results/audit/product/ / reports/audit/product/)")
    ap.add_argument("--json", action="store_true", help="machine-readable stdout")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    if not (root / "product").is_dir():
        print(f"::error::no product/ under {root}", file=sys.stderr)
        return 2

    if args.only:
        wanted = [c.strip() for c in args.only.split(",") if c.strip()]
        unknown = [c for c in wanted if c not in CHECKS]
        if unknown:
            print(f"::error::unknown check(s): {unknown}", file=sys.stderr)
            return 2
        checks = tuple(c for c in CHECKS if c in wanted)
    else:
        checks = CHECKS

    dossier = args.dossier
    skip_tests = args.skip_tests
    if args.skip_dossier:
        # Drop the check entirely rather than reporting a synthetic pass.
        checks = tuple(c for c in checks if c != "dossier")
        dossier = None

    report = build(root, checks=checks, budget=args.budget_seconds,
                   dossier=dossier, scope=args.scope, tests=args.tests,
                   skip_tests=skip_tests)

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        target = Path(args.out)
        if not target.is_absolute():
            target = (Path.cwd() / target).resolve()
        problem = _writable_target(target, root)
        if problem:
            print(f"::error::{problem}", file=sys.stderr)
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")

    if args.json:
        print(text)
    else:
        for entry in report["checks"]:
            mark = "PASS" if entry["ok"] else "FAIL"
            print(f"[{mark}] {entry['check']:<8} {entry['elapsed_s']:>7.2f}s "
                  f"{entry['command'][:100]}")
        ro = report["read_only"]["ok"]
        print(f"[{'PASS' if ro else 'FAIL'}] read-only  "
              f"({report['read_only']['n_paths_before']} -> "
              f"{report['read_only']['n_paths_after']} paths)")
        print(f"verdict={report['verdict']} failed={report['n_failed']}/"
              f"{report['n_checks']} elapsed={report['elapsed_s']}s "
              f"budget={report['budget_seconds']}s")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
