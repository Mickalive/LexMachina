"""Tests for the three-leg retrieval/counter-authority falsification benchmark.

These tests pin the REUSE-FIRST contract of
evaluation/benchmark_retrieval_counter_authority.py: it must shell out to the
ACCEPTED run_bar_gates entry point (never re-implement scoring), its three legs
must have the frozen exit-code expectations, and its combined verdict vocabulary
must match VERDICT_CONTRACT-aligned exit codes. They do NOT re-measure the two
Frontier candidates and do NOT touch any frozen rule/threshold/incumbent.

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

from evaluation.benchmark_retrieval_counter_authority import (  # noqa: E402
    GEOMETRY_INCUMBENT,
    LABEL_INCUMBENT,
    SCHEMA,
    _leg_summary,
)
from evaluation.frozen_bars.run_bar_gates import QIDS, SERVED_PACKET_DIR  # noqa: E402

RECORD_38989947869 = (
    _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark/38989947869.json")


def test_schema_and_engine_pin():
    assert SCHEMA == "lex-evaluation-retrieval-ca-benchmark/1"
    src = (_REPO_ROOT / "evaluation/benchmark_retrieval_counter_authority.py").read_text(
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


def test_leg_summary_maps_missing_keys_without_crash():
    # Regression pin for the 38986445355 defect: the original script KeyError'd on
    # geom_res["negative_control_proven"] because score_packet does not emit it.
    # The rewritten _leg_summary must tolerate a minimal record.
    out = _leg_summary("x", 0, {"verdict": "PASS_NO_REGRESSION"}, expected_rc=0)
    assert out["exit_code"] == 0
    assert out["exit_code_matches_expectation"] is True
    assert out["label"]["n_scored"] is None  # absent keys become None, never KeyError


def test_frozen_record_of_record_has_frozen_verdict():
    assert RECORD_38989947869.exists(), (
        "results/evaluation/retrieval_counter_authority_benchmark/38989947869.json missing")
    rec = json.loads(RECORD_38989947869.read_text(encoding="utf-8"))
    assert rec["schema"] == SCHEMA
    assert rec["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
    assert rec["exit_code"] == 0
    assert rec["falsification_proven"] is True
    assert rec["reuses_entry_point"] == "evaluation.frozen_bars.run_bar_gates"
    legs = {lg["leg"]: lg for lg in rec["legs"]}
    assert legs["served_baseline"]["exit_code"] == 0
    assert legs["geometry_falsification_hostile"]["exit_code"] == 1
    assert legs["label_falsification_blanked_evidence"]["exit_code"] == 1
    for lg in legs.values():
        assert lg["exit_code_matches_expectation"] is True
    # served-bundle identity pins match the accepted LABEL_HALF inputs
    assert set(rec["served_bundle_sha256"]) == set(QIDS)


def test_end_to_end_on_accepted_mount_if_present():
    """Live end-to-end: only when the accepted-product mount is available."""
    if not SERVED_PACKET_DIR.exists():
        import pytest
        pytest.skip("accepted product mount absent; frozen record test still pins the verdict")
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.benchmark_retrieval_counter_authority",
         "--run-id", "pytest_local"],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600)
    assert proc.returncode in (0, 2), (
        f"unexpected exit {proc.returncode}; stderr tail: {proc.stderr[-500:]}")
    if proc.returncode == 0:
        # exit 0 is only reachable when both falsification legs fired
        out = json.loads(proc.stdout)
        assert out["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
        assert out["falsification_proven"] is True
