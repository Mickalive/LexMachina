"""Tests for ``evaluation/minimal_ret_ca_benchmark.py`` (FAST-MVP 2-leg retrieval /
counter-authority falsification benchmark).

These tests pin the REUSE-FIRST contract of
``evaluation/minimal_ret_ca_benchmark.py``: it must shell out to the ACCEPTED
entry point ``evaluation.frozen_bars.run_bar_gates``, its two legs must have
the frozen exit-code expectations, and its combined verdict vocabulary must match
VERDICT_CONTRACT-aligned exit codes. They do NOT re-measure the two Frontier
candidates and do NOT touch any frozen rule/threshold/incumbent.

The heavy end-to-end leg (subprocess over the accepted-product mount) is exercised
once via the already-produced record of run 38989947869; pure-logic checks run
without the mount so the suite stays runnable in a bare checkout.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.minimal_ret_ca_benchmark import (  # noqa: E402
    GEOMETRY_INCUMBENT,
    LABEL_INCUMBENT,
    SCHEMA,
    _leg_summary,
)
from evaluation.frozen_bars.run_bar_gates import QIDS, SERVED_PACKET_DIR  # noqa: E402

RECORD_38989947869 = (
    _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark/38989947869.json")


def test_schema_and_engine_pin():
    assert SCHEMA == "lex-evaluation-minimal-ret-ca-benchmark/1"
    src = (_REPO_ROOT / "evaluation/minimal_ret_ca_benchmark.py").read_text(
        encoding="utf-8")
    # REUSE-FIRST: the benchmark must invoke the accepted entry point as a module,
    # never import Product code, never re-derive RULES_* shas.
    assert 'BAR_GATES_MODULE = "evaluation.frozen_bars.run_bar_gates"' in src
    assert "from product" not in src
    assert "RULES_LABEL.json\" sha" not in src  # no re-derivation of rubric shas


def test_incumbent_restatement_matches_accepted_pins():
    # These are re-statements only; the authoritative values live in
    # label_gate.INCUMBENT / geometry_gate.INCUMBENT_COUNTS. A mismatch here means
    # the summary block drifted and must be corrected to the accepted pins.
    from evaluation.frozen_bars import geometry_gate, label_gate
    assert LABEL_INCUMBENT == label_gate.INCUMBENT
    assert GEOMETRY_INCUMBENT == geometry_gate.INCUMBENT_COUNTS


def test_frozen_record_of_record_has_frozen_verdict():
    assert RECORD_38989947869.exists(), (
        "results/evaluation/retrieval_counter_authority_benchmark/38989947869.json missing")
    rec = json.loads(RECORD_38989947869.read_text(encoding="utf-8"))
    # The committed record uses the historical schema name; preserve it verbatim.
    # SCHEMA is the current wrapper's schema; the historical record's schema is pinned.
    assert rec["schema"] == "lex-evaluation-retrieval-ca-benchmark/1"
    assert rec["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert rec["exit_code"] == 0
    legs = {lg["leg"]: lg for lg in rec["legs"]}
    assert legs["served_baseline"]["exit_code"] == 0
    assert legs["geometry_falsification_hostile"]["exit_code"] == 1
    assert legs["label_falsification_blanked_evidence"]["exit_code"] == 1
    for lg in legs.values():
        assert lg["exit_code_matches_expectation"] is True


def test_end_to_end_on_accepted_mount_if_present(tmp_path):
    """Live end-to-end: only when the accepted-product mount is available.

    SCRATCH-RUN OBLIGATION (audit CYCLE_39164900837 F9): this test used to run
    the benchmark with its DEFAULT output directories, so every lane-suite run
    rewrote five committed claim-bearing artefacts
    (results/evaluation/minimal_ret_ca_benchmark/pytest_local*.json
    and reports/evaluation/RETRIEVAL_CA_BENCHMARK_pytest_local.md).  The
    workflow's `git add -A` persist step then carried those rewrites into the
    promoted snapshot, so a unit test became accepted evidence.  The benchmark now
    takes --out-dir/--report-dir and this test points both at tmp_path.
    test_scratch_output_isolation.py re-measures the committed tree afterwards.
    """
    if not SERVED_PACKET_DIR.exists():
        import pytest
        pytest.skip("accepted product mount absent; frozen record test still pins the verdict")
    out_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.minimal_ret_ca_benchmark",
         "--run-id", "pytest_local",
         "--out-dir", str(out_dir), "--report-dir", str(report_dir)],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600)
    assert proc.returncode in (0, 1, 2), (
        f"unexpected exit {proc.returncode}; stderr tail: {proc.stderr[-500:]}")
    if proc.returncode == 0:
        # exit 0 is only reachable when both legs fire as expected
        out = json.loads(proc.stdout)
        assert out["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
        assert out["falsification_proven"] is True
        # the redirected run must actually have written there, not to the repo
        assert (out_dir / "pytest_local.json").is_file()
        assert (report_dir / "RETRIEVAL_CA_BENCHMARK_pytest_local.md").is_file()


def test_committed_tree_is_not_a_benchmark_output_directory():
    """The defaults are the committed tree - so a scratch run must redirect.

    This is the contract half of F9: it makes the committed directories
    explicit and named, so the test above cannot quietly fall back to them.
    """
    from evaluation.minimal_ret_ca_benchmark import (
        DEFAULT_OUT_DIR, DEFAULT_REPORT_DIR,
    )
    assert DEFAULT_OUT_DIR.name == "minimal_ret_ca_benchmark"
    assert DEFAULT_OUT_DIR.parent.name == "evaluation"
    assert DEFAULT_REPORT_DIR.name == "evaluation"
    assert DEFAULT_OUT_DIR.is_dir() and DEFAULT_REPORT_DIR.is_dir()