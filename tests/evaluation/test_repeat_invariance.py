"""Tests for the repeat-invariance harness (cycle 39023900270).

Mount-free by default: only the detection-control test executes a real entry
point, and that control needs no accepted product mount (it fails at the
missing-input check, which is exactly what it measures).  The two mount-gated
tests skip cleanly in a bare checkout, consistent with the lane suite's
environment-skip philosophy: an absent environment is never a pass and never
a failure.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

LANE_ROOT = Path(__file__).resolve().parents[2]
if str(LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(LANE_ROOT))

from evaluation.frozen_bars import repeat_invariance as ri  # noqa: E402

needs_mount = pytest.mark.skipif(
    not ri.SERVED_QUESTIONS_DIR.is_dir(),
    reason="accepted product mount absent")


# --------------------------------------------------------------------------- #
# normalization (the frozen comparison rule)
# --------------------------------------------------------------------------- #


def test_normalized_sha_ignores_elapsed_s_only():
    a = {"verdict": "PASS_NO_REGRESSION", "elapsed_s": 7.447,
         "nested": {"elapsed_s": 1.0, "n": 5}}
    b = {"verdict": "PASS_NO_REGRESSION", "elapsed_s": 99.0,
         "nested": {"elapsed_s": 2.0, "n": 5}}
    assert ri.normalized_sha(a) == ri.normalized_sha(b)


def test_normalized_sha_detects_a_real_change():
    a = {"verdict": "PASS_NO_REGRESSION", "n_supported": 5}
    b = {"verdict": "FAIL_REGRESSION", "n_supported": 5}
    assert ri.normalized_sha(a) != ri.normalized_sha(b)


def test_strip_varying_drops_only_declared_keys():
    src = {"elapsed_s": 1, "keep": {"elapsed_s": 2, "x": 3}, "y": [1, {"elapsed_s": 4}]}
    assert ri.strip_varying(src) == {"keep": {"x": 3}, "y": [1, {}]}
    assert ri.VARYING_KEYS == ("elapsed_s",)


# --------------------------------------------------------------------------- #
# non-zero classification: the harness must SEE a non-zero, and must NAME an
# unexplained one instead of swallowing it
# --------------------------------------------------------------------------- #


def test_classify_zero_is_not_detected():
    out = ri.classify_exit(0, "")
    assert out["detected_nonzero"] is False
    assert out["exit_class"] == "ZERO"


def test_classify_missing_inputs_is_environment_error():
    out = ri.classify_exit(
        2, "bar_gates environment error: missing inputs in /tmp/x: ['a.bundle.json']")
    assert out["detected_nonzero"] is True
    assert out["exit_class"] == "ENVIRONMENT_ERROR"
    assert out["signature"] == "ENVIRONMENT_MESSAGE"


def test_classify_empty_stderr_exit1_is_the_section11_class():
    """Exit 1 with nothing captured is precisely the unresolved anecdote."""
    out = ri.classify_exit(1, "")
    assert out["detected_nonzero"] is True
    assert out["exit_class"] == "UNEXPLAINED_EXIT_1"
    assert out["signature"] == "EMPTY_STDERR"


def test_classify_broken_pipe_is_named_closed_stdout():
    err = ("Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w'>\n"
           "BrokenPipeError: [Errno 32] Broken pipe\n")
    out = ri.classify_exit(120, err)
    assert out["detected_nonzero"] is True
    assert out["signature"] == "BROKEN_PIPE"
    assert out["exit_class"] == "CLOSED_STDOUT"


def test_classify_broken_pipe_traceback_at_exit1():
    err = ("Traceback (most recent call last):\n"
           "  File run_bar_gates.py, line 302, in <module>\n"
           "BrokenPipeError: [Errno 32] Broken pipe\n")
    out = ri.classify_exit(1, err)
    assert out["exit_class"] == "CLOSED_STDOUT"


# --------------------------------------------------------------------------- #
# invariance collapse
# --------------------------------------------------------------------------- #


def test_evaluate_invariance_single_record_is_invariant():
    trials = [{"exit_code": 0, "normalized_sha256": "aa"},
              {"exit_code": 0, "normalized_sha256": "aa"}]
    inv = ri.evaluate_invariance(trials)
    assert inv["invariant"] is True
    assert inv["distinct_normalized_records"] == 1
    assert inv["nonzero_count"] == 0


def test_evaluate_invariance_flags_a_nonzero_trial():
    trials = [{"exit_code": 0, "normalized_sha256": "aa"},
              {"exit_code": 1, "normalized_sha256": "aa"}]
    inv = ri.evaluate_invariance(trials)
    assert inv["invariant"] is False
    assert inv["nonzero_count"] == 1
    assert inv["nonzero_indices"] == [1]


def test_evaluate_invariance_flags_payload_drift():
    trials = [{"exit_code": 0, "normalized_sha256": "aa"},
              {"exit_code": 0, "normalized_sha256": "bb"}]
    inv = ri.evaluate_invariance(trials)
    assert inv["invariant"] is False
    assert inv["distinct_normalized_records"] == 2
    assert inv["nonzero_count"] == 0  # drift, not a crash: both reported


def test_evaluate_invariance_never_passes_an_empty_trial_set():
    """Vacuous success is unreachable: 0 trials is not invariant."""
    assert ri.evaluate_invariance([])["invariant"] is False


# --------------------------------------------------------------------------- #
# P6 digest pins
# --------------------------------------------------------------------------- #


def test_every_pinned_frozen_file_matches_its_full_digest():
    res = ri.check_frozen_digests()
    assert res["missing"] == []
    assert res["moved"] == {}
    assert res["all_matched"] is True
    assert len(ri.FROZEN_DIGEST_PINS) >= 12


def test_pins_are_full_length_hex_not_placeholders():
    for rel, pin in ri.FROZEN_DIGEST_PINS.items():
        assert len(pin) == 64, rel
        assert set(pin) <= set("0123456789abcdef"), rel
        assert "0" * 32 not in pin, f"{rel} looks like a placeholder pin"


# --------------------------------------------------------------------------- #
# P4 detection control: a REAL non-zero from a REAL entry point, no mount
# --------------------------------------------------------------------------- #


def test_detection_control_classifies_a_real_nonzero_without_the_mount():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "empty"
        empty.mkdir()
        trial = ri._run_once(
            ri.BAR_GATES + ["--packet-dir", str(empty)],
            Path(td) / "c.json", ri._LANE_ROOT)
    assert trial["exit_code"] == 2
    assert trial["classification"]["detected_nonzero"] is True
    assert trial["classification"]["exit_class"] == "ENVIRONMENT_ERROR"
    assert "missing inputs" in trial["stderr_head"]


def test_detection_control_writes_no_record_on_environment_error():
    """Exit 2 must never leave a verdict-shaped file behind."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "empty"
        empty.mkdir()
        out = Path(td) / "c.json"
        ri._run_once(ri.BAR_GATES + ["--packet-dir", str(empty)],
                     out, ri._LANE_ROOT)
        assert not out.exists()


# --------------------------------------------------------------------------- #
# record shape + exit-code contract
# --------------------------------------------------------------------------- #


@needs_mount
def test_zero_trials_cannot_pass_and_record_is_complete():
    rec = ri.run_measurement(n=0, run_id="unit_zero", with_probe=False)
    # n=0 produces an empty trial set, which must NOT be read as success
    assert rec["exit_code"] == 1
    assert rec["all_predicates_hold"] is False
    assert set(rec["predicates"]) == {
        "P1_served_lineage_runs_are_invariant",
        "P2_lineage_sweep_runs_are_invariant",
        "P3_section11_nonzero_does_not_reproduce",
        "P4_detection_control_proves_the_harness_is_not_blind",
        "P6_nothing_accepted_moves",
    }
    assert rec["schema"] == ri.RECORD_SCHEMA
    assert rec["freeze_sha256"] and len(rec["freeze_sha256"]) == 64


@needs_mount
def test_probe_nonzero_never_changes_the_invariance_exit_code():
    """Frozen P5 separation: the mechanism probe may exit 1/120 while the
    measurement itself is clean, and the harness must still exit 0."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rec = ri.run_measurement(
            n=1, run_id="unit_separation", with_probe=True, probe_trials=1,
            probe_out=Path(td) / "probe.json")
        probe = json.loads((Path(td) / "probe.json").read_text(encoding="utf-8"))
    p5 = probe["P5_closed_stdout_reaches_the_mechanism_class_separately"]
    # the probe DID reach a non-zero (otherwise this control is vacuous)
    assert p5["nonzero_trials"] >= 1
    assert p5["empty_stderr_with_nonzero"] == 0
    # ... and the invariance verdict/exit code is unaffected by it
    assert probe["separation_rule"].startswith("P5 is recorded separately")
    assert rec["exit_code"] == 0
    assert rec["all_predicates_hold"] is True
    assert rec["probe_recorded_separately"] is True


def test_environment_absence_is_exit2_never_a_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(ri, "SERVED_QUESTIONS_DIR", tmp_path / "definitely_absent")
    rec = ri.run_measurement(n=1, run_id="unit_env", with_probe=False)
    assert rec["exit_code"] == 2
    assert rec["environment"] == "ENVIRONMENT_ABSENT"
    assert "all_predicates_hold" not in rec


def test_frozen_hypothesis_file_is_readable_and_pins_this_run():
    assert ri.FREEZE_PATH.exists()
    freeze = json.loads(ri.FREEZE_PATH.read_text(encoding="utf-8"))
    assert freeze["run_id"] == "39023900270"
    assert freeze["direction_version"] == 50
    assert "P5_closed_stdout_reaches_the_mechanism_class_separately" in freeze["predicates"]
    assert freeze["success_rule"]["p5_is_not_part_of_the_pass_rule"].startswith("P5")
