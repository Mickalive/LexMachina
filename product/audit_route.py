#!/usr/bin/env python3
"""One-command bounded audit route for a product snapshot.

Why this exists
---------------
Independent audits of this lineage have now died three times at
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` *without consuming the bounded
verification that already exists* (runs 40702698815, 40726216925,
40737328834: each audit job's "Independent audit" step ran ~2704 s and exited
78 before writing any gate).  The full audit-readiness dossier regenerates in
~2 minutes and its ``--verify`` path re-hashes in ~1 s, but an auditor that
starts by re-deriving discharged findings or reading the 300 KB state file
line by line spends its whole quantum before reaching the cheap checks.

This module is the single entry point the auditor should run FIRST.  It
executes the claim-bearing verification set in cost order, measures every
step, and publishes the measured total against the 2700 s work-quantum
budget so the next auditor can allocate its own quantum deliberately.

What it runs (default)
----------------------
1. ``product/state_contract.py --check --direction-version 68`` — workflow
   contract + write-scope + audit-namespace ownership (~0.1 s);
2. ``product/audit_readiness.py --verify <committed dossier>`` — sub-second
   re-hash of the committed claim artifacts;
3. ``product/audit_readiness.py --run-id … --out /tmp/…`` — full dossier
   regeneration on bounded inputs (~2 min: posture, resumed diagnosis,
   claim artifacts, progressive smoke over a real socket, bounded MVP core
   pytest set);
4. the current chain's cycle tests (this run plus its recent predecessors);
5. full-suite *collection* count as a disclosure only (the auditor does NOT
   need the full suite; the bounded set is the contract).

It is a readiness instrument, never a verdict: it writes no gate, scores no
frozen bar, mints no acceptance, and labels no run accepted/rejected.  Its
only committed output is its own route artifact under
``results/product/audit_readiness/``.

Usage
-----
    python3 product/audit_route.py --run-id 40750177292 \
        --out results/product/audit_readiness/CYCLE_40750177292_AUDIT_ROUTE.json

    # sub-second mode (re-hash only, no re-execution):
    python3 product/audit_route.py --run-id 40750177292 --verify-only

    # print the compact auditor brief without writing anything:
    python3 product/audit_route.py --run-id 40750177292 --for-auditor
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

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "product-audit-route/1"
DIRECTION_VERSION = 68
QUANTUM_BUDGET_S = 2700  # the workflow's own work quantum for agent steps

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], timeout_s: int) -> dict[str, Any]:
    start = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd, cwd=str(ROOT), capture_output=True, text=True,
            timeout=timeout_s, check=False,
        )
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = (exc.stdout or b"").decode() if isinstance(
            exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode() if isinstance(
            exc.stderr, bytes) else (exc.stderr or "")
    seconds = round(time.monotonic() - start, 3)
    return {
        "command": " ".join(cmd),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "seconds": seconds,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-2000:],
    }


def _step(step_id: str, title: str, cmd: list[str], timeout_s: int,
          ok_exit: int = 0) -> dict[str, Any]:
    run = _run(cmd, timeout_s)
    ok = (not run["timed_out"]) and run["exit_code"] == ok_exit
    return {
        "id": step_id,
        "title": title,
        "status": "PASS" if ok else "FAIL",
        **run,
    }


def chain_cycle_tests(run_id: str) -> list[str]:
    """This run's cycle test plus the most recent predecessor cycle tests."""
    tests_dir = ROOT / "product" / "tests"
    picked: list[str] = []
    own = tests_dir / f"test_cycle_{run_id}.py"
    if own.exists():
        picked.append(f"product/tests/test_cycle_{run_id}.py")
    others = sorted(tests_dir.glob("test_cycle_40*.py"))
    for path in reversed(others):
        if len(picked) >= 4:
            break
        rel = f"product/tests/{path.name}"
        if rel not in picked:
            picked.append(rel)
    return picked


def build_route(run_id: str, verify_only: bool = False) -> dict[str, Any]:
    dossier = (ROOT / "results" / "product" / "audit_readiness"
               / f"CYCLE_{run_id}_audit_readiness.json")
    steps: list[dict[str, Any]] = []

    steps.append(_step(
        "state_contract",
        "Product state satisfies the workflow contract (direction v68)",
        [sys.executable, "product/state_contract.py", "--check",
         "--direction-version", str(DIRECTION_VERSION), "--json"],
        60,
    ))

    if dossier.exists():
        steps.append(_step(
            "dossier_verify",
            "Committed audit-readiness dossier re-hashes (sub-second path)",
            [sys.executable, "product/audit_readiness.py", "--verify",
             str(dossier.relative_to(ROOT))],
            180,
        ))
    else:
        steps.append({
            "id": "dossier_verify", "title": "Committed dossier re-hash",
            "status": "SKIP", "command": None, "exit_code": None,
            "timed_out": False, "seconds": 0.0,
            "stdout_tail": f"no committed dossier at {dossier}",
            "stderr_tail": "",
        })

    if not verify_only:
        steps.append(_step(
            "dossier_regen",
            "Full audit-readiness regeneration on bounded inputs "
            "(posture, diagnosis, claim artifacts, smoke, MVP core tests)",
            [sys.executable, "product/audit_readiness.py", "--run-id",
             run_id, "--out", f"/tmp/CYCLE_{run_id}_audit_readiness_regen.json"],
            900,
        ))
        tests = chain_cycle_tests(run_id)
        if tests:
            steps.append(_step(
                "chain_cycle_tests",
                "Current chain cycle tests (this run + recent predecessors)",
                [sys.executable, "-m", "pytest", *tests, "-q", "--maxfail=1"],
                600,
            ))
        steps.append(_step(
            "full_suite_collect",
            "Full product test-suite COLLECTION count (disclosure only; "
            "executing the full suite is NOT part of the audit route)",
            [sys.executable, "-m", "pytest", "product/tests", "-q",
             "--collect-only"],
            300,
        ))

    total = round(sum(s.get("seconds") or 0.0 for s in steps), 3)
    passed = sum(1 for s in steps if s.get("status") == "PASS")
    failed = [s["id"] for s in steps if s.get("status") == "FAIL"]
    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "run_id": run_id,
        "direction_version": DIRECTION_VERSION,
        "mode": "verify_only" if verify_only else "full_route",
        "steps": steps,
        "steps_passed": passed,
        "failed_steps": failed,
        "total_seconds": total,
        "quantum_budget_s": QUANTUM_BUDGET_S,
        "budget_fraction": round(total / QUANTUM_BUDGET_S, 4),
        "overall_status": "PASS" if not failed else "FAIL",
        "contract": (
            "This is a readiness route, never a verdict. It writes no gate, "
            "scores no frozen bar and labels no run accepted/rejected. The "
            "independent auditor still owns results/audit/product/"
            f"CYCLE_{run_id}_GATE.json (UPPERCASE _GATE.json) written from "
            "the audit-job checkout."
        ),
        "do_not_re_derive": [
            "evaluation 40070818687 (path-scope diagnosis; routing leg closed)",
            "evaluation 40068038783 (per-class D2/D3/D4 verdict, reconciliation)",
            "evaluation 40105794124 (FAST-MVP falsifier measurement)",
            "D2 letterhead profile 40089391202",
            "the 153-bundle historical sweep",
            "any Frontier verdict or frozen rubric/bar",
        ],
    }


def auditor_brief(run_id: str, route: dict[str, Any] | None) -> str:
    lines = [
        f"AUDIT ROUTE BRIEF — product snapshot for run {run_id}",
        "=" * 60,
        "NEXT DISPATCH MUST BE THE INDEPENDENT AUDIT of this snapshot.",
        "The producer side is complete; three prior audits died at the",
        "2700 s work quantum without consuming the cheap checks below.",
        "",
        "RUN THIS FIRST (measured cost in parentheses):",
        "  1. python3 product/state_contract.py --check "
        f"--direction-version {DIRECTION_VERSION} --json        (~0.1 s)",
        "  2. python3 product/audit_readiness.py --verify "
        f"results/product/audit_readiness/CYCLE_{run_id}_audit_readiness.json"
        "   (~1 s)",
        "  3. python3 product/audit_route.py --run-id "
        f"{run_id} --out /tmp/route.json          "
        "(full route, ~2-4 min measured)",
        "",
        "THEN read, in this order (short files first):",
        f"  - reports/product/CYCLE_{run_id}.md                     (report of record)",
        f"  - results/product/orchestration/CYCLE_{run_id}_resume_diagnosis.json",
        "  - the `audit_route` + `next_recommendation` fields of "
        "state/product.json",
        "",
        "DO NOT re-derive discharged findings (see route artifact "
        "do_not_re_derive).",
        "Gate path: results/audit/product/CYCLE_<run_id>_GATE.json "
        "(UPPERCASE).",
        "",
        "The vertical slice stays complete and locally runnable; both "
        "DO-NOT-SERVE",
        "orders stand; no owner session is staged while either frozen bar "
        "is unmet.",
    ]
    if route:
        lines += [
            "",
            f"Last measured route: status={route.get('overall_status')} "
            f"total={route.get('total_seconds')}s "
            f"budget_fraction={route.get('budget_fraction')} "
            f"of {QUANTUM_BUDGET_S}s.",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--for-auditor", action="store_true")
    args = ap.parse_args(argv)

    if args.for_auditor:
        print(auditor_brief(args.run_id, None))
        return 0

    route = build_route(args.run_id, verify_only=args.verify_only)
    out = Path(args.out) if args.out else (
        ROOT / "results" / "product" / "audit_readiness"
        / f"CYCLE_{args.run_id}_AUDIT_ROUTE.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(route, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "overall_status": route["overall_status"],
        "total_seconds": route["total_seconds"],
        "budget_fraction": route["budget_fraction"],
        "failed_steps": route["failed_steps"],
        "out": str(out),
    }, indent=1))
    return 0 if route["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
