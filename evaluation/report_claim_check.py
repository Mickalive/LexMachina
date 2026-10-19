#!/usr/bin/env python3
"""Re-derive this cycle's own report claims from the committed bytes.

Audit CYCLE_39164900837 F2 rejected a report that printed fabricated digests
(`a1b2c3d4...`), because nothing in the control plane compared them against the
files on disk.  The lane's regression guard for that,
``tests/evaluation/test_v57_open_items.py::test_report_evidence_table_digests_match_files``,
is hard-coded to another run's report path and therefore skips for every other
cycle.  This instrument performs the SAME verification against the current
cycle's report, plus the numeric claims that are easy to get wrong.

    python3 evaluation/report_claim_check.py \
        --report reports/evaluation/CYCLE_39200567493_REPAIR.md

Exit 0 when every checkable claim reproduces; exit 1 with the divergence
otherwise.  It writes nothing unless --out is given.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

#: ``| path | sha256 |`` -- the trailing pipe is deliberately NOT consumed so that
#: the shared cell separator between two consecutive rows can open the next row.
ROW_RE = re.compile(r"\|\s*`?([A-Za-z0-9_./-]+\.(?:json|md|py))`?[^|]*\|\s*`?([0-9a-f]{64})`?")
PLACEHOLDER_RE = re.compile(r"\b[a-zA-Z]{8}\.\.\.")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_report(report: Path, repo: Path) -> dict:
    text = report.read_text(encoding="utf-8")
    rows = ROW_RE.findall(text)
    digest_problems = []
    for rel, printed in rows:
        path = repo / rel
        if not path.is_file():
            digest_problems.append(f"evidence table names a missing file: {rel}")
            continue
        actual = sha256_file(path)
        if actual != printed:
            digest_problems.append(
                f"digest mismatch for {rel}: printed {printed[:16]}... actual {actual[:16]}...")
    if not rows:
        digest_problems.append("no digest rows found in the evidence table")

    placeholders = PLACEHOLDER_RE.findall(text)

    # Numeric claims that are easy to state wrongly.
    numeric_problems = []
    shim_path = repo / "results/evaluation/orchestration/39200567493_pytest_shim.json"
    shim = json.loads(shim_path.read_text(encoding="utf-8"))
    n_fail_cases = sum(1 for r in shim["results"] for c in r.get("cases", [])
                       if c["status"] == "FAIL")
    stated = re.search(r"\| Cases passed \| \*\*(\d+)\*\* \|", text)
    if not stated or int(stated.group(1)) != shim["n_passed"]:
        numeric_problems.append(
            f"report 'Cases passed' != record n_passed ({shim['n_passed']})")
    stated_fail = re.search(r"\| Failing cases \| \*\*(\d+)\*\* \|", text)
    if not stated_fail or int(stated_fail.group(1)) != n_fail_cases:
        numeric_problems.append(
            f"report 'Failing cases' != record ({n_fail_cases})")
    stated_unsup = re.search(r"NOT-RUN\*\* \| \*\*(\d+)\*\* \|", text)
    if not stated_unsup or int(stated_unsup.group(1)) != shim["n_unsupported"]:
        numeric_problems.append(
            f"report NOT-RUN count != record n_unsupported ({shim['n_unsupported']})")
    stated_files = re.search(r"\| Test files in scope \| \*\*(\d+)\*\*", text)
    if not stated_files or int(stated_files.group(1)) != shim["n_files"]:
        numeric_problems.append(
            f"report 'Test files in scope' != record n_files ({shim['n_files']})")
    stated_files_failing = re.search(r"\| Files with ≥1 failing case \| \*\*(\d+)\*\*", text)
    if not stated_files_failing or int(stated_files_failing.group(1)) != shim["n_failed"]:
        numeric_problems.append(
            f"report failing-FILE count != record n_failed ({shim['n_failed']})")
    stated_skipped = re.search(r"\| Cases skipped \| \*\*(\d+)\*\*", text)
    if not stated_skipped or int(stated_skipped.group(1)) != shim["n_skipped"]:
        numeric_problems.append(
            f"report skipped count != record n_skipped ({shim['n_skipped']})")

    # The frozen digests must still be the pinned ones.
    for rel, pinned in (
        ("evaluation/retrieval_gate/frozen_retrieval_benchmark.json",
         "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"),
        ("evaluation/retrieval_gate/FREEZE_RECORD.json",
         "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49"),
        ("evaluation/frozen_bars/RULES_LABEL.json",
         "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"),
        ("evaluation/frozen_bars/RULES_GEOMETRY.json",
         "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"),
    ):
        actual = sha256_file(repo / rel)
        if actual != pinned:
            numeric_problems.append(f"FROZEN DRIFT {rel}: {actual[:16]} != {pinned[:16]}")

    # The "all tests pass" class of claim must not have crept back in as an
    # ASSERTION.  A QUOTATION of the withdrawn phrase (inside quotation marks)
    # is disclosure, not a claim, and is allowed; an unquoted assertion is not.
    banned = ["All core evaluation tests pass",
              "No further same-question cycle is justified",
              "Lane State: COMPLETE"]
    for phrase in banned:
        for m in re.finditer(re.escape(phrase), text):
            before = text[max(0, m.start() - 1):m.start()]
            after = text[m.end():m.end() + 1]
            quoted = before in ("\"", "'", "\u201c") or after in ("\"", "'", "\u201d")
            if not quoted:
                numeric_problems.append(
                    f"withdrawn phrase asserted unquoted: {phrase!r}")

    ok = not (digest_problems or placeholders or numeric_problems)
    return {
        "schema": "lex-evaluation-report-claim-check/1",
        "report": str(report.relative_to(repo)),
        "report_sha256": sha256_file(report),
        "n_digest_rows": len(rows),
        "digest_problems": digest_problems,
        "placeholder_hits": placeholders,
        "numeric_problems": numeric_problems,
        "shim_record": {
            "path": str(shim_path.relative_to(repo)),
            "verdict": shim["verdict"],
            "n_files": shim["n_files"],
            "n_passed": shim["n_passed"],
            "n_failed_files": shim["n_failed"],
            "n_failing_cases": n_fail_cases,
            "n_skipped": shim["n_skipped"],
            "n_unsupported": shim["n_unsupported"],
        },
        "pass": ok,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", required=True)
    ap.add_argument("--repo-root", default=str(_REPO_ROOT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    res = check_report(Path(args.report).resolve(),
                       Path(args.repo_root).resolve())
    text = json.dumps(res, indent=1, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())