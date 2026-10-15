"""Admissibility scanner for human-gate evidence records.

Why this exists
---------------
The comparative human gate is the one product milestone an agent cannot pass,
so its evidence directory has to be boring in a way an auditor can check
mechanically rather than by reading prose:

* ``results/product/human_gate_sessions/`` holds **only** real owner/jurist
  sessions — attested provenance, a bundle that verifies against the draft, and
  a plausible number of decisions behind that draft;
* ``results/product/human_gate_sessions_simulated/`` holds **only** machine
  records, and each of them says so in its own ``claim_ceiling``;
* no record anywhere claims the gate itself was passed.

Cycle 38726191935 committed five pytest byproducts into the simulated directory,
two of which carried ``simulated: true`` next to the claim ceiling *"this record
documents one owner/jurist session"*, four fabricated ``yes`` ratings and a
synthesized 450 s wall clock. Nothing in the code detected that; this module is
the code that detects it, so the third occurrence cannot be a silent one.

Usage
-----
    python product/human_gate_evidence.py                 # scan the repo directories
    python product/human_gate_evidence.py --dir <path> --json
    python product/human_gate_evidence.py --quiet          # exit code only

Exit codes: 0 no blocking finding, 1 at least one blocking finding.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent

CANONICAL_DIR = REPO_ROOT / "results" / "product" / "human_gate_sessions"
SIMULATED_DIR = REPO_ROOT / "results" / "product" / "human_gate_sessions_simulated"

SIMULATED_MARKER = "SIMULATED SESSION"
REAL_CEILING_PREFIX = "human gate EVIDENCE only"

#: Session ids produced by a unit test rather than by the browser harness.
TEST_SCRATCH_ID = re.compile(r"^(session-session-|test-session-)")

#: Directory roles are decided by directory NAME, not by absolute path, so the
#: rules can be exercised on a synthetic tree and so a copy of the evidence tree
#: elsewhere is still judged by the rules that apply to it.
CANONICAL_DIR_NAME = "human_gate_sessions"
SIMULATED_DIR_NAME = "human_gate_sessions_simulated"


def role_of(directory: Path) -> str:
    """'canonical', 'simulated' or 'unknown' for a directory."""
    name = Path(directory).name
    if name == CANONICAL_DIR_NAME:
        return "canonical"
    if name == SIMULATED_DIR_NAME:
        return "simulated"
    return "unknown"

#: The comparative gate runs on a query-specific map of 100-300 decisions.
MIN_REAL_BUNDLE_DECISIONS = 10


def _walk(node: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    """Yield every (key, value) pair in a nested JSON structure."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield path + "/" + str(key), value
            yield from _walk(value, path + "/" + str(key))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk(item, f"{path}[{index}]")


def scan_record(record: Any, *, directory: Path, source: str, role: str | None = None) -> list[dict[str, Any]]:
    """Return the findings for one record. An empty list means admissible."""
    findings: list[dict[str, Any]] = []

    def finding(code: str, detail: str, severity: str = "blocking") -> None:
        findings.append(
            {"record": source, "directory": str(directory), "code": code, "detail": detail, "severity": severity}
        )

    if not isinstance(record, dict):
        finding("not_a_session_record", f"expected a JSON object, got {type(record).__name__}")
        return findings
    if record.get("record_type") != "lex_human_gate_session":
        finding("not_a_session_record", f"record_type={record.get('record_type')!r}")

    simulated = record.get("simulated") is True
    ceiling = str(record.get("claim_ceiling") or "")
    role = role or role_of(directory)
    canonical_dir = role == "canonical"
    simulated_dir = role == "simulated"

    # The claim ceiling and the simulated flag must tell the same story.
    if simulated and SIMULATED_MARKER not in ceiling:
        finding(
            "contradictory_claim_ceiling",
            "simulated=true but the claim ceiling does not say SIMULATED SESSION: "
            f"{ceiling[:120]!r}",
        )
    if not simulated and SIMULATED_MARKER in ceiling:
        finding("contradictory_claim_ceiling", "non-simulated record carries the simulated claim ceiling")
    if not simulated and not ceiling.startswith(REAL_CEILING_PREFIX):
        finding(
            "unexpected_claim_ceiling",
            f"non-simulated record claim ceiling is not the canonical one: {ceiling[:120]!r}",
        )

    if canonical_dir:
        if simulated:
            finding("simulated_in_canonical_dir", "a machine-generated record is in the canonical evidence directory")
        if not record.get("finalized_by"):
            finding("missing_finalized_by", "canonical records must record who finalized the session")
        if not record.get("run_id"):
            finding("missing_run_id", "canonical records must record the core-lane run")
        wall = (record.get("session_metrics") or {}).get("wall_clock_seconds")
        if not isinstance(wall, (int, float)) or isinstance(wall, bool) or wall <= 0:
            finding("non_positive_wall_clock", f"session_metrics.wall_clock_seconds={wall!r} (a real session takes time)")
        if record.get("bundle_hash_status") != "verified":
            finding(
                "bundle_not_verified",
                f"bundle_hash_status={record.get('bundle_hash_status')!r}; unverified binding is draft evidence",
            )
        if record.get("owner_session_confirmed") is not True:
            finding(
                "unconfirmed_owner_session",
                "canonical records must carry owner_session_confirmed=true, i.e. a person "
                "declared they were answering the gate; a rehearsal or autonomous run does not",
            )
        count = (record.get("bundle_evidence") or {}).get("bundle_decision_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < MIN_REAL_BUNDLE_DECISIONS:
            finding(
                "implausible_decision_count",
                f"bundle_decision_count={count!r} < {MIN_REAL_BUNDLE_DECISIONS}",
            )
    elif simulated_dir and not simulated:
        finding(
            "real_record_in_simulated_dir",
            "a record claiming to be an owner session is filed as machine-generated",
        )

    if TEST_SCRATCH_ID.match(str(record.get("session_id") or "")):
        finding(
            "test_scratch_session_id",
            f"session_id={record.get('session_id')!r} is a unit-test identifier, not a harness export",
            severity="blocking" if canonical_dir else "warning",
        )

    for key, _ in _walk(record):
        if key.rsplit("/", 1)[-1] == "human_gate_ready":
            finding("claims_human_gate_ready", f"record contains a {key} field; only the director may set the gate")
            break

    return findings


def scan_dir(directory: Path, *, role: str | None = None) -> list[dict[str, Any]]:
    """Scan every ``session_*.json`` in a directory."""
    findings: list[dict[str, Any]] = []
    if not directory.exists():
        return findings
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            findings.append(
                {
                    "record": str(path),
                    "directory": str(directory),
                    "code": "unreadable_record",
                    "detail": str(exc),
                    "severity": "blocking",
                }
            )
            continue
        findings.extend(scan_record(record, directory=directory, source=path.name, role=role))
    return findings


def scan(directories: Sequence[Path] | None = None) -> dict[str, Any]:
    """Scan the canonical + simulated directories (or an explicit list)."""
    targets = [Path(d) for d in directories] if directories else [CANONICAL_DIR, SIMULATED_DIR]
    findings: list[dict[str, Any]] = []
    for directory in targets:
        findings.extend(scan_dir(directory, role=role_of(directory)))
    blocking = [f for f in findings if f["severity"] == "blocking"]
    return {
        "scanned": [f"{d} ({role_of(d)})" for d in targets],
        "findings": findings,
        "blocking_count": len(blocking),
        "warning_count": len(findings) - len(blocking),
        "admissible": not blocking,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan human-gate evidence records for admissibility defects.")
    parser.add_argument("--dir", action="append", default=None, help="directory to scan (repeatable); default: canonical + simulated")
    parser.add_argument(
        "--role",
        choices=("canonical", "simulated", "unknown"),
        default=None,
        help="force the directory role instead of inferring it from the directory name",
    )
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    parser.add_argument("--quiet", action="store_true", help="print nothing; use the exit code")
    args = parser.parse_args(argv)

    if args.dir:
        targets = [Path(d) for d in args.dir]
        report = scan(targets)
        if args.role:
            extra: list[dict] = []
            for directory in targets:
                extra.extend(scan_dir(directory, role=args.role))
            report["findings"] = extra
            report["blocking_count"] = len([f for f in extra if f["severity"] == "blocking"])
            report["warning_count"] = len(extra) - report["blocking_count"]
            report["admissible"] = report["blocking_count"] == 0
    else:
        report = scan()
    if args.quiet:
        pass
    elif args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for directory in report["scanned"]:
            print(f"scanned {directory}")
        for finding in report["findings"]:
            print(f"  [{finding['severity']}] {finding['code']}: {finding['record']} — {finding['detail']}")
        print(
            f"human-gate evidence: {report['blocking_count']} blocking, {report['warning_count']} warning"
            f" -> {'ADMISSIBLE' if report['admissible'] else 'NOT ADMISSIBLE'}"
        )
    return 0 if report["admissible"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())