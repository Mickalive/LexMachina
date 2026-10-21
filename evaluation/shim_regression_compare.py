"""Compare two no-pytest-shim records and decide whether a change REGRESSED the lane suite.

Run 39631600439 (repair round 1 of cycle 39628161040).

Why this exists
---------------
The producer image has no pytest, so the lane's own test files are executed by
``evaluation/no_pytest_runner.py`` (a stdlib shim, an UPPER BOUND on pytest, not
pytest).  A raw "SHIM_FAIL" verdict is therefore not actionable on its own: the
rejected branch snapshot already carried failing lane tests before any repair
work.  What matters for a repair cycle is the DELTA: did the change introduce a
failure that was not already there?

This tool answers exactly that question and nothing else, and it says so in its
own record.  It does not "fix" anything, does not suppress a failure, and does
not convert an UNSUPPORTED case into a pass.  A pre-existing failure stays
visible as a pre-existing failure.

Usage
-----
    python3 -m evaluation.shim_regression_compare \
        --baseline <baseline_shim_record.json> \
        --current  <current_shim_record.json> \
        --baseline-label "<what the baseline is>" \
        --out <out.json>

Exit codes: 0 = no new failure, 1 = at least one new failure, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lex-evaluation-shim-regression-compare/1"
REPO_ROOT = Path(__file__).resolve().parents[1]

EXIT_NO_NEW_FAILURE = 0
EXIT_NEW_FAILURE = 1
EXIT_USAGE = 2


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def case_map(record: dict) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for f in record.get("results", []):
        for c in f.get("cases", []):
            out[(f["test_file"], c["test"])] = c["status"]
    return out


def file_map(record: dict) -> dict[str, str]:
    return {f["test_file"]: f.get("status") for f in record.get("results", [])}


def compare(baseline: dict, current: dict) -> dict:
    b_cases, c_cases = case_map(baseline), case_map(current)
    new_failures = sorted(
        f"{tf}::{t}" for (tf, t), s in c_cases.items()
        if s == "FAIL" and b_cases.get((tf, t)) != "FAIL")
    no_longer_failing = sorted(
        f"{tf}::{t}" for (tf, t), s in b_cases.items()
        if s == "FAIL" and c_cases.get((tf, t)) != "FAIL")
    vanished = sorted(
        f"{tf}::{t}" for (tf, t) in c_cases if (tf, t) not in b_cases)
    appeared = sorted(
        f"{tf}::{t}" for (tf, t) in b_cases if (tf, t) not in c_cases)
    b_files, c_files = file_map(baseline), file_map(current)
    return {
        "baseline_verdict": baseline.get("verdict"),
        "current_verdict": current.get("verdict"),
        "baseline_counts": {k: baseline.get(k) for k in
                            ("n_files", "n_passed", "n_failed", "n_skipped",
                             "n_unsupported", "n_absent")},
        "current_counts": {k: current.get(k) for k in
                           ("n_files", "n_passed", "n_failed", "n_skipped",
                            "n_unsupported", "n_absent")},
        "n_new_failures": len(new_failures),
        "new_failures": new_failures,
        "n_no_longer_failing": len(no_longer_failing),
        "no_longer_failing": no_longer_failing,
        "n_cases_only_in_current": len(vanished),
        "cases_only_in_current": vanished,
        "n_cases_only_in_baseline": len(appeared),
        "cases_only_in_baseline": appeared,
        "n_files_failing_baseline": sum(1 for s in b_files.values() if s == "FAIL"),
        "n_files_failing_current": sum(1 for s in c_files.values() if s == "FAIL"),
        "regression": bool(new_failures),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--current", required=True)
    ap.add_argument("--baseline-label", default="")
    ap.add_argument("--current-label", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    bp, cp = Path(args.baseline), Path(args.current)
    if not bp.is_file() or not cp.is_file():
        print("baseline or current record missing", file=sys.stderr)
        return EXIT_USAGE
    baseline, current = load(bp), load(cp)
    body = compare(baseline, current)
    verdict = "SHIM_REGRESSION" if body["regression"] else "SHIM_NO_NEW_FAILURE"
    record = {
        "schema": SCHEMA,
        "verdict": verdict,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_record": str(bp),
        "current_record": str(cp),
        "baseline_label": args.baseline_label,
        "current_label": args.current_label,
        **body,
        "what_this_is": (
            "A DELTA over two no-pytest-shim records. It answers one question: "
            "did the current tree introduce a lane-test failure that the baseline "
            "tree did not have? Pre-existing failures are reported as "
            "pre-existing, not hidden; UNSUPPORTED and SKIPPED cases are never "
            "counted as passes and never converted."),
        "what_this_is_not": (
            "NOT pytest, and NOT a statement that the lane suite is green. The "
            "shim is an upper bound on pytest and pytest is absent in the "
            "producer image, so the standing disclosure that the lane's pytest "
            "scope is unexecuted in the producer image is unchanged by this "
            "record. A 'no new failure' verdict is exactly that and nothing "
            "more."),
    }
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    verdict = "SHIM_REGRESSION" if body["regression"] else "SHIM_NO_NEW_FAILURE"
    verdict = "SHIM_REGRESSION" if body["regression"] else "SHIM_NO_NEW_FAILURE"
    print(json.dumps({"verdict": verdict,
                      "n_new_failures": body["n_new_failures"],
                      "n_no_longer_failing": body["n_no_longer_failing"]},
                     ensure_ascii=False))
    return EXIT_NEW_FAILURE if body["regression"] else EXIT_NO_NEW_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
