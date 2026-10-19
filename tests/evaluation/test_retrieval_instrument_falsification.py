"""Tests for the FAST MVP retrieval-instrument falsification legs.

Pins the contract of evaluation/retrieval_instrument_falsification.py: the
accepted run of record must re-score to its accepted reading through the
accepted pure entry point, the two hostile transforms must produce exactly the
frozen named gate flips (multilingual authority recall + provenance duplicate),
and a drifted pinned input is exit 2.  Everything here is offline over
committed bytes; no network, no frozen-file write, no universal-174k benchmark.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.retrieval_gate import frozen, gates  # noqa: E402
from evaluation.retrieval_instrument_falsification import (  # noqa: E402
    LEG_B_EXPECTED_NEW, LEG_B_MUST_STAY_PASSING, LEG_B_QUERY_KEY,
    LEG_C_EXPECTED_NEW, LEG_C_QUERY_KEY, SCHEMA, VERDICT_ENV, VERDICT_FAIL,
    VERDICT_OK, _blank_query, _duplicate_first_row, verify_inputs,
)

HYP = _REPO_ROOT / "evaluation/RETRIEVAL_INSTRUMENT_FALSIFICATION_HYPOTHESIS_V1.json"
ACCEPTED = _REPO_ROOT / "results/evaluation/retrieval_benchmark/39098571937.json"


def test_hypothesis_pins_frozen_legs_and_exit_rules():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    assert hyp["schema"] == "lex-evaluation-retrieval-instrument-falsification-hypothesis/1"
    assert set(hyp["success_rule"]) == {"exit_0", "exit_1", "exit_2", "no_weakening"}
    assert set(hyp["frozen_legs"]) == {"leg_a_reproduction", "leg_b_hostile_blank",
                                       "leg_c_hostile_duplicate"}
    assert hyp["inputs"]["accepted_run_of_record"]["sha256"] == hashlib.sha256(
        ACCEPTED.read_bytes()).hexdigest()


def test_verify_inputs_flags_drift():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.json"
        p.write_text("{}", encoding="utf-8")
        resolved, problems = verify_inputs(
            {"inputs": {"a": {"path": str(p), "sha256": "f" * 64}}})
        assert resolved == {} and len(problems) == 1


def test_transforms_touch_exactly_one_query():
    rec = json.loads(ACCEPTED.read_text(encoding="utf-8"))
    blanked = copy.deepcopy(rec)
    assert _blank_query(blanked, LEG_B_QUERY_KEY) == 1
    orig = {q["query_key"]: q for q in rec["queries"]}
    for q in blanked["queries"]:
        if q["query_key"] == LEG_B_QUERY_KEY:
            assert q["rows"] == [] and q["n_results"] == 0
        else:
            assert q["rows"] == orig[q["query_key"]]["rows"]
    duped = copy.deepcopy(rec)
    assert _duplicate_first_row(duped, LEG_C_QUERY_KEY) == 1
    for q in duped["queries"]:
        if q["query_key"] == LEG_C_QUERY_KEY:
            assert len(q["rows"]) == len(orig[q["query_key"]]["rows"]) + 1
        else:
            assert len(q["rows"]) == len(orig[q["query_key"]]["rows"])


def test_frozen_legs_behave_as_hypothesised():
    spec = frozen.load_frozen()
    rec = json.loads(ACCEPTED.read_text(encoding="utf-8"))
    base = gates.evaluate(spec, rec)
    pin = json.loads(HYP.read_text(encoding="utf-8"))["inputs"]["accepted_run_of_record"][
        "accepted_reading"]
    assert base["n_gates"] == pin["n_gates"] == 40
    assert base["n_passed"] == pin["n_passed"]
    assert base["n_failed"] == pin["n_failed"]
    assert base["n_not_measurable"] == pin["n_not_measurable"]
    assert base["overall_pass"] is pin["overall_pass"] is False
    failed_base = set(base["failed_gates"])

    hostile_b = copy.deepcopy(rec)
    assert _blank_query(hostile_b, LEG_B_QUERY_KEY) == 1
    vb = gates.evaluate(spec, hostile_b)
    assert set(vb["failed_gates"]) - failed_base == LEG_B_EXPECTED_NEW
    assert failed_base - set(vb["failed_gates"]) == set()
    gates_b = {g["gate"]: g for g in vb["gates"]}
    for gate_name in LEG_B_MUST_STAY_PASSING:
        assert gates_b[gate_name]["passed"] is True

    hostile_c = copy.deepcopy(rec)
    assert _duplicate_first_row(hostile_c, LEG_C_QUERY_KEY) == 1
    vc = gates.evaluate(spec, hostile_c)
    assert set(vc["failed_gates"]) - failed_base == LEG_C_EXPECTED_NEW
    assert failed_base - set(vc["failed_gates"]) == set()


def test_end_to_end_offline_is_deterministic_and_falsifying():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "rec.json"
        report_dir = Path(td) / "reports"
        proc = subprocess.run(
            [sys.executable, "-m", "evaluation.retrieval_instrument_falsification",
             "--run-id", "pytest_scratch", "--out", str(out),
             "--report-dir", str(report_dir)],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, f"{proc.returncode}: {proc.stderr[-400:]}"
        rec = json.loads(out.read_text(encoding="utf-8"))
        assert rec["schema"] == SCHEMA
        assert rec["verdict"] == VERDICT_OK
        assert rec["reproduction_matches"] is True
        assert rec["falsification_proven"] is True
        assert rec["human_gate_ready"] is False
        assert rec["owner_decision_required"] is False
        assert (report_dir / "RETRIEVAL_INSTRUMENT_FALSIFICATION_pytest_scratch.md").is_file()


def test_verdict_vocabulary_is_frozen():
    assert VERDICT_OK == "REPRODUCTION_MATCHES_AND_FALSIFICATION_PROVEN"
    assert VERDICT_FAIL == "FALSIFICATION_OR_REPRODUCTION_FAILURE"
    assert VERDICT_ENV == "ENVIRONMENT"


def test_frozen_cache_integrity_module_imports_from_foreign_cwd():
    """Regression pin for the sys.insert defect repaired in run 39180276526.

    ``python evaluation/frozen_cache_integrity.py --help`` from a foreign cwd
    puts only the evaluation/ directory on sys.path, so the lane-root insert
    branch actually executes; before the repair it raised AttributeError and the
    frozen-input integrity instrument was un-importable outside the repo root.
    """
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "evaluation/frozen_cache_integrity.py"),
             "--help"],
            cwd=td, capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stderr[-400:]
        assert "restore-from" in proc.stdout
