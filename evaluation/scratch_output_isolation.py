#!/usr/bin/env python3
"""Measure whether a scratch benchmark run mutates the lane's committed evidence.

WHY THIS FILE EXISTS (audit ``CYCLE_39164900837`` F9)
-----------------------------------------------------
The lane had an accepted convention that the ``pytest_local*`` scratch artefacts
were "removed before commit" - which is a promise that the next person breaks.
Cycle ``39173770080`` measured the promise as false: one invocation of

    python -m evaluation.benchmark_retrieval_counter_authority --run-id pytest_local

rewrote all five committed artefacts

    results/evaluation/retrieval_counter_authority_benchmark/pytest_local.json
    results/evaluation/retrieval_counter_authority_benchmark/pytest_local_leg1_served_baseline.json
    results/evaluation/retrieval_counter_authority_benchmark/pytest_local_leg2_hostile_geometry.json
    results/evaluation/retrieval_counter_authority_benchmark/pytest_local_leg3_blanked_evidence.json
    reports/evaluation/RETRIEVAL_CA_BENCHMARK_pytest_local.md

because the benchmark hard-coded its output directories.  The workflow's
``git add -A`` persist step then carried those rewrites into the promoted
snapshot, so a unit test silently became part of the accepted evidence tree.

The convention is replaced here by a measurement.  This module re-hashes the
committed evidence tree, runs the benchmark with its output redirected outside
the repository, re-hashes, and publishes the comparison.  ``n_mutated == 0`` is
the claim; the before/after digests are the evidence, so the claim is
re-derivable and not asserted.

NO NETWORK.  NO FROZEN FILE IS WRITTEN.  NO PRODUCT CODE IS IMPORTED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-scratch-output-isolation/1"
BENCHMARK_MODULE = "evaluation.benchmark_retrieval_counter_authority"

#: Every committed file a scratch run of the benchmark used to rewrite.  Listed
#: explicitly so a NEW leak is a visible diff rather than an invisible one.
COMMITTED_EVIDENCE = [
    "results/evaluation/retrieval_counter_authority_benchmark/pytest_local.json",
    "results/evaluation/retrieval_counter_authority_benchmark/pytest_local_leg1_served_baseline.json",
    "results/evaluation/retrieval_counter_authority_benchmark/pytest_local_leg2_hostile_geometry.json",
    "results/evaluation/retrieval_counter_authority_benchmark/pytest_local_leg3_blanked_evidence.json",
    "reports/evaluation/RETRIEVAL_CA_BENCHMARK_pytest_local.md",
]


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(repo: Path) -> dict:
    return {rel: _sha256(repo / rel) for rel in COMMITTED_EVIDENCE}


def run_scratch(repo: Path, run_id: str = "pytest_local") -> dict:
    """Invoke the benchmark with its output redirected outside the repository."""
    with tempfile.TemporaryDirectory(prefix="lex-scratch-isolation-") as td:
        out_dir = Path(td) / "results"
        report_dir = Path(td) / "reports"
        proc = subprocess.run(
            [sys.executable, "-m", BENCHMARK_MODULE, "--run-id", run_id,
             "--out-dir", str(out_dir), "--report-dir", str(report_dir)],
            cwd=str(repo), capture_output=True, text=True, timeout=900)
        written = sorted(
            str(p.relative_to(td)) for p in Path(td).rglob("*") if p.is_file())
        summary = None
        try:
            payload = json.loads(proc.stdout)
            summary = {k: payload.get(k) for k in
                       ("verdict", "exit_code", "falsification_proven")}
        except json.JSONDecodeError:
            pass
    return {"argv_tail": ["--run-id", run_id, "--out-dir", "<tmp>",
                          "--report-dir", "<tmp>"],
            "exit_code": proc.returncode,
            "scratch_summary": summary,
            "files_written_outside_repo": written,
            "stderr_tail": (proc.stderr or "").strip().splitlines()[-5:]}


def measure(repo: Path, run_id: str = "pytest_local") -> dict:
    before = snapshot(repo)
    run = run_scratch(repo, run_id)
    after = snapshot(repo)
    rows = []
    for rel in COMMITTED_EVIDENCE:
        rows.append({"path": rel, "sha256_before": before[rel],
                     "sha256_after": after[rel],
                     "present_before": before[rel] is not None,
                     "mutated": before[rel] != after[rel]})
    n_mutated = sum(1 for r in rows if r["mutated"])
    return {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "measured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "instrument": "evaluation/scratch_output_isolation.py",
        "remediated_fix": (
            "audit CYCLE_39164900837 F9: the benchmark now takes --out-dir and "
            "--report-dir, and tests/evaluation/"
            "test_benchmark_retrieval_counter_authority.py points both at "
            "tmp_path instead of the committed defaults."),
        "committed_evidence": rows,
        "n_committed_artifacts": len(rows),
        "n_mutated": n_mutated,
        "verdict": "SCRATCH_RUN_ISOLATED" if n_mutated == 0 else "SCRATCH_RUN_LEAKS",
        "scratch_run": run,
        "pre_fix_measurement_39173770080": {
            "n_mutated": 5,
            "n_committed_artifacts": 5,
            "method": ("sha256 of the same five files before and after one "
                       "invocation of the pre-fix command "
                       "`python -m evaluation.benchmark_retrieval_counter_authority "
                       "--run-id pytest_local`, which hard-coded the committed "
                       "output directories"),
            "verdict": "SCRATCH_RUN_LEAKS",
        },
        "claim_ceiling": (
            "Delivery hygiene only. It shows that a scratch benchmark run no "
            "longer rewrites committed lane evidence; it says nothing about "
            "retrieval quality, counter-authority recall or the query map, and "
            "it does not by itself make any existing record trustworthy."),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="pytest_local")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    report = measure(_REPO_ROOT, args.run_id)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("schema", "run_id", "verdict", "n_committed_artifacts",
                       "n_mutated")}, indent=1))
    return 0 if report["verdict"] == "SCRATCH_RUN_ISOLATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())