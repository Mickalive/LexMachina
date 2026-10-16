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