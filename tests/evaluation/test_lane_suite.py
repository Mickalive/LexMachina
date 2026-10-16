#!/usr/bin/env python3
"""Tests for the stdlib-only lane-suite entry point (cycle 38945976309).

``evaluation/lane_suite.py`` exists because no workflow in this repository runs
the lane's two v49 gate test files: the only pytest invocation in CI is
``evaluation/query_map/test_harness.py`` and its path filter does not cover
``evaluation/reality_gate/**``, ``evaluation/retrieval_gate/**`` or
``tests/evaluation/**``.  ``.github/**`` is control-plane scope and is not edited
from a lane, so the lane ships a dependency-free entry point instead and records
the gap.

These tests run it as a subprocess with ``--skip-pytest`` so it cannot recurse
into pytest.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _run(tmp_path: Path) -> tuple[int, dict]:
    out = tmp_path / "lane_suite.json"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.lane_suite", "--skip-pytest",
         "--out", str(out)],
        cwd=str(REPO), capture_output=True, text=True, timeout=600)
    assert out.exists(), proc.stdout + proc.stderr
    return proc.returncode, json.loads(out.read_text(encoding="utf-8"))


def test_lane_suite_passes_end_to_end(tmp_path):
    code, report = _run(tmp_path)
    assert code == 0, json.dumps(report["failed_checks"], indent=2)
    assert report["overall_pass"] is True
    assert report["n_failed"] == 0


def test_lane_suite_covers_the_frozen_digests_and_every_record(tmp_path):
    _, report = _run(tmp_path)
    names = [c["check"] for c in report["checks"]]
    assert "reality frozen benchmark" in names
    assert "retrieval frozen benchmark" in names
    assert "reality gate contract" in names
    assert sum(1 for n in names if n.startswith("record integrity ")) >= 2
    assert any(n.startswith("re-score reproduces ") for n in names)


def test_lane_suite_declares_a_falsification_matrix(tmp_path):
    _, report = _run(tmp_path)
    families = report["falsifiable_families"]
    assert len(families) == 20, families
    # every declared family must have been broken by its fixture
    broken = {c["check"].removeprefix("fixture breaks ")
              for c in report["checks"] if c["check"].startswith("fixture breaks ")}
    assert set(families) <= broken, sorted(set(families) - broken)


def test_lane_suite_states_its_claim_ceiling(tmp_path):
    _, report = _run(tmp_path)
    assert "not a product pass" in report["claim_ceiling"]
    assert "does not re-measure Product" in report["claim_ceiling"]


def test_lane_suite_makes_no_network_call_and_imports_no_product_code(tmp_path):
    """The suite must stay runnable in an offline audit checkout."""
    source = (REPO / "evaluation" / "lane_suite.py").read_text(encoding="utf-8")
    assert "import requests" not in source
    assert "urlopen" not in source
    assert "product" not in {line.split()[1].split(".")[0]
                             for line in source.splitlines()
                             if line.startswith("from ") or line.startswith("import ")
                             for line in [line] if len(line.split()) > 1}
    # it must only read the ACCEPTED mount if told to, and by default reads nothing
    code, report = _run(tmp_path)
    assert code == 0
    assert not any("lex_accepted" in str(c) for c in report["checks"])


def test_skip_pytest_flag_emits_no_pytest_check(tmp_path):
    """--skip-pytest means the pytest sub-check is absent, not skipped."""
    _, report = _run(tmp_path)
    names = [c["check"] for c in report["checks"]]
    assert not any("pytest" in n for n in names), names
    assert report.get("n_skipped", 0) == 0


def _run_bare(tmp_path: Path) -> tuple[int, dict]:
    """Run the suite the way a bare audit checkout without pytest would.

    ``python -S`` disables site-packages, so the installed pytest becomes
    unimportable while the stdlib stays intact — a faithful, dependency-free
    simulation of the missing-pytest environment.  No --skip-pytest: the
    skip path itself is what is under test.
    """
    out = tmp_path / "lane_suite_bare.json"
    proc = subprocess.run(
        [sys.executable, "-S", "-m", "evaluation.lane_suite",
         "--out", str(out)],
        cwd=str(REPO), capture_output=True, text=True, timeout=600)
    assert out.exists(), proc.stdout + proc.stderr
    return proc.returncode, json.loads(out.read_text(encoding="utf-8"))


def test_pytest_absent_is_a_skip_not_a_failure(tmp_path):
    """Cycle 38951152192 (F7): a bare checkout without pytest must stay green.

    Before the fix the missing-pytest check was a FAIL and the whole suite
    reported 41/42 FAIL for an environment gap its own message called 'not a
    benchmark failure'.  Now it must be a recorded SKIP with zero failures.
    """
    code, report = _run_bare(tmp_path)
    assert code == 0, json.dumps(report["failed_checks"], indent=2)
    assert report["overall_pass"] is True
    assert report["n_failed"] == 0
    assert report["n_skipped"] == 1, json.dumps(report["checks"][-3:],
                                                indent=2)
    skips = report["skipped_checks"]
    assert len(skips) == 1 and "pytest" in skips[0]["check"], skips
    assert skips[0]["passed"] is None
    # the authoritative stdlib checks still ran and passed
    assert report["n_passed"] == report["n_checks"] - 1
    names = [c["check"] for c in report["checks"]]
    assert "reality frozen benchmark" in names
    assert any(n.startswith("re-score reproduces ") for n in names)


def test_present_but_red_pytest_is_still_a_failure(tmp_path, monkeypatch):
    """The skip must not become a blanket amnesty: a red pytest run fails."""
    sys.path.insert(0, str(REPO))
    try:
        from evaluation import lane_suite
    finally:
        sys.path.remove(str(REPO))

    class _Boom:
        returncode = 1
        stdout = "1 failed\n"
        stderr = ""

    monkeypatch.setattr(lane_suite.subprocess, "run",
                        lambda *a, **k: _Boom())
    log = lane_suite._Log()
    lane_suite.run_pytest(log)
    assert len(log.failed) == 1
    assert "pytest" in log.failed[0]["check"]
    assert log.skipped == []