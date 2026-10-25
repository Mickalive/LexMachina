#!/usr/bin/env python3
"""No evaluation instrument may default an OUTPUT into the audit namespace.

Why this exists (direction v68, operational resume of run 40232590665)
----------------------------------------------------------------------
Run 40232590665 executed the FAST-MVP minimal retrieval/counter-authority
falsification benchmark with defaults and therefore wrote
``reports/audit/evaluation/RETRIEVAL_CA_BENCHMARK_40228275848.md``.  The core
lane's "Enforce lane write scope" step (``.github/workflows/core-lane.yml``,
control plane, read-only here) allows a producer only::

    evaluation/*  tests/evaluation/*  results/evaluation/*
    reports/evaluation/*  state/evaluation.json  data/evaluation/*

so the run failed that step with exit 3 after ~22 minutes of otherwise valid
producer work; audit and integrate were skipped and no verdict was ever issued.
The same class already failed runs 38982176936, 39470495546, 40167904552 and
40186604273 (see ``evaluation/snapshot_audit/write_scope.py`` and
``results/evaluation/audit_namespace_recovery_40182692670/RELOCATION_RECORD.json``).

The audit namespaces ``results/audit/<lane>/`` and ``reports/audit/<lane>/``
belong to the INDEPENDENT AUDITOR, which writes them from the audit-job
checkout.  A producer instrument that defaults its output there both breaks the
producer's own write scope and risks publishing a self-authored pseudo-gate.

What is asserted
----------------
1. No module under ``evaluation/`` assigns a default output/report directory
   into ``results/audit`` or ``reports/audit`` (the assignment pattern the
   defect uses, not mere path strings that merely *reference* audit evidence).
2. The known offender and every benchmark wrapper default to the lane's own
   namespaces (``results/evaluation``, ``reports/evaluation``).
3. ``evaluation.snapshot_audit.write_scope`` still classifies the exact defect
   as a violation, so the guard cannot rot silently.

stdlib only, no network, no product import; a failure here is a producer-scope
defect, never a frozen-bar or product-claim change.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

EVAL_DIR = _REPO_ROOT / "evaluation"

# Default-directory assignment forms that write a produced artifact.
_ASSIGN_MARKERS = (
    '= REPO_ROOT / "reports/audit',
    "= REPO_ROOT / 'reports/audit",
    '/ "reports/audit/evaluation"',
    '/ "results/audit/evaluation"',
)


def _modules() -> list[Path]:
    return sorted(p for p in EVAL_DIR.glob("*.py") if p.is_file())


def test_no_evaluation_module_defaults_an_output_into_the_audit_namespace():
    offenders: list[str] = []
    for path in _modules():
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not any(marker in line for marker in _ASSIGN_MARKERS):
                continue
            # A default/constant assignment, not a comment or a citation string.
            if stripped.startswith("#") or stripped.startswith('"'):
                continue
            if "=" not in stripped:
                continue
            offenders.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}: {stripped}")
    assert not offenders, (
        "evaluation instruments must not default an output into the audit namespace:\n"
        + "\n".join(offenders))


def test_benchmark_wrappers_default_to_lane_namespaces():
    from evaluation import minimal_ca_falsify_benchmark as BM
    assert BM.DEFAULT_REPORT_DIR == _REPO_ROOT / "reports" / "evaluation"
    assert BM.DEFAULT_OUT_DIR == _REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark"
    assert not str(BM.DEFAULT_REPORT_DIR).startswith(str(_REPO_ROOT / "reports" / "audit"))
    assert not str(BM.DEFAULT_OUT_DIR).startswith(str(_REPO_ROOT / "results" / "audit"))


def test_write_scope_classifier_still_flags_the_40232590665_defect():
    """The instrument that diagnoses this run must keep reproducing the failure."""
    with tempfile.TemporaryDirectory(prefix="lex_scope_repro_") as td:
        out_path = Path(td) / "repro.json"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.snapshot_audit.write_scope",
             "--lane", "evaluation",
             "--repro-from-git",
             "bb75f263e7857a82f4c3f1322d12283d7365188e",
             "0003921a0f35a35f516716eb10b3c3db99277f7d",
             "--out", str(out_path)],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=300)
        # exit 1 = SCOPE_VIOLATION in the ported classifier
        assert proc.returncode == 1, (
            f"expected SCOPE_VIOLATION (rc 1), got {proc.returncode}: {proc.stdout} {proc.stderr}")
        assert out_path.is_file(), f"no record written: {proc.stdout} {proc.stderr}"
        record = json.loads(out_path.read_text(encoding="utf-8"))
    verdict = record.get("verdict", record)
    bad = set(verdict.get("bad_paths", []))
    expected = {
        "results/audit/evaluation/CYCLE_40228275848_GATE.json",
        "reports/audit/evaluation/CYCLE_40228275848.md",
        "reports/audit/evaluation/RETRIEVAL_CA_BENCHMARK_40228275848.md",
    }
    assert bad == expected, f"bad_paths drifted: {sorted(bad)}"
    # the two deliverable artifacts of that cycle must classify as IN scope
    allowed = {e["path"] for e in verdict.get("entries", []) if e.get("allowed")}
    assert "results/evaluation/minimal_ca_falsify_benchmark/40228275848.json" in allowed


def test_lane_report_namespace_exists_on_disk():
    assert (_REPO_ROOT / "reports" / "evaluation").is_dir()
    assert (_REPO_ROOT / "results" / "evaluation").is_dir()
