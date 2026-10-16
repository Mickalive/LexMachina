"""Verdict contract + exit-code reachability of the frozen-bar gates.

Companion to (not a modification of) tests/evaluation/test_frozen_bar_gates.py.
Pins the three falsifiable findings of run 38972887369:

* H1: default served-lineage execution stays byte-identical to the accepted
  record 38971202786.json (modulo elapsed_s) after the adjudicate mode was
  added — the mode is additive, the frozen lineage is untouched;
* H2: the entry point's exit-1 build-blocking path is UNREACHABLE through
  served_lineage mode on every input (served bytes recompute the incumbent
  by construction; any drift exits 2 before scoring);
* H3/H4: the blocking paths are reachable through adjudicate mode, and the
  naive-consumer trap is reachable — exit 0 with label regression_verdict
  NOT_APPLICABLE and n_supported 0 in the same record, which falsifies any
  consumer rule reading exit 0 / gate_blocks_build false as "the
  counter-label bar was met".

No threshold is asserted beyond the frozen incumbents already accepted.
Served-packet tests skip when the accepted product mount is absent.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation.frozen_bars import label_gate, verdict_contract
from evaluation.frozen_bars.run_bar_gates import QIDS, SERVED_PACKET_DIR

BAR_DIR = Path("evaluation/frozen_bars")
ACCEPTED_RECORD = Path("results/evaluation/bar_gates/38971202786.json")
REACHABILITY_RECORD = Path("results/evaluation/verdict_contract/38972887369_reachability.json")
MOUNT_AVAILABLE = all((SERVED_PACKET_DIR / f"{qid}.bundle.json").exists() for qid in QIDS)
needs_mount = pytest.mark.skipif(not MOUNT_AVAILABLE, reason="accepted product mount absent")


# ---- mount-independent: contract integrity ------------------------------

def test_verdict_contract_digest_is_pinned():
    digest = verdict_contract.contract_digest()
    assert digest["matches"], f"VERDICT_CONTRACT.json drifted: {digest}"
    assert digest["expected_sha256"] == (
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c")


def test_verdict_contract_drift_refuses_to_classify(tmp_path):
    """A one-byte edit of the contract must be a visible red, not a silent pass."""
    src = BAR_DIR / "VERDICT_CONTRACT.json"
    tampered = tmp_path / "VERDICT_CONTRACT.json"
    tampered.write_bytes(src.read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        verdict_contract.load_contract(tampered)


def test_verdict_contract_predicates_match_accepted_code_constants():
    """The contract may restate the accepted predicates, never redefine them."""
    contract = verdict_contract.load_contract()
    frozen = contract["frozen_inputs"]
    assert frozen["incumbent_label"] == label_gate.INCUMBENT
    assert frozen["incumbent_qids"] == list(label_gate.INCUMBENT_QIDS)
    from evaluation.frozen_bars import geometry_gate
    assert frozen["incumbent_geometry"] == geometry_gate.INCUMBENT_COUNTS
    assert frozen["rules_label_sha256"] == label_gate.EXPECTED_RULES_SHA256
    assert frozen["rules_geometry_sha256"] == geometry_gate.EXPECTED_RULES_SHA256


def test_incumbent_constants_are_pinned_to_accepted_literals():
    """Defense-in-depth (auditor-recommended, cycle 38972043610): the two
    incumbent CONSTANTS themselves are pinned to the accepted literals here,
    mount-independently. Without this, weakening label_gate.INCUMBENT
    (n_supported 5 -> 1-4) or geometry_gate.INCUMBENT_COUNTS (6/5/5 -> 2/2/2)
    leaves every other test green: the with-mount tests compare recomputed
    values against hard-coded literals rather than against the constants, and
    the contract-vs-code test above follows the constant if both move
    together. The served-bundle sha pin still fires first on real drift, so
    this is depth, not a new gate.
    """
    from evaluation.frozen_bars import geometry_gate
    assert label_gate.INCUMBENT == {
        "n_scored": 65,
        "n_supported": 5,
        "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5, "INVERTED": 0},
    }
    assert label_gate.INCUMBENT_QIDS == (
        "de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
    assert geometry_gate.INCUMBENT_COUNTS == {
        "de-kapitalverletzung": 6, "fr-bail-entretien": 5, "it-responsabilita-medica": 5}


def test_admission_reading_classifies_not_applicable_as_not_a_pass():
    """Library-level trap pin: NOT_APPLICABLE + zero support is flagged."""
    reading = verdict_contract.admission_reading(
        {"regression_verdict": "NOT_APPLICABLE", "absolute_status": "LABEL_UNSOUND",
         "n_supported": 0},
        {"regression_verdict": "PASS_NO_REGRESSION", "absolute_status": "GEOMETRY_UNSOUND"},
        exit_code=0)
    assert reading["naive_consumer_trap_fires"] is True
    assert reading["label"]["is_regression_not_a_pass"] is True
    assert "NOTHING about label soundness" in reading["label"]["regression_certifies"]


def test_admission_reading_served_pass_is_not_an_absolute_bar_claim():
    reading = verdict_contract.admission_reading(
        {"regression_verdict": "PASS_NO_REGRESSION", "absolute_status": "LABEL_UNSOUND",
         "n_supported": 5},
        {"regression_verdict": "PASS_NO_REGRESSION", "absolute_status": "GEOMETRY_UNSOUND"},
        exit_code=0)
    assert reading["naive_consumer_trap_fires"] is False
    assert "does not certify the absolute bar" in reading["label"]["regression_does_not_certify"]


def test_adjudicate_missing_packet_is_environment_error():
    rc = subprocess.run(
        [sys.executable, "-m", "evaluation.frozen_bars.run_bar_gates",
         "--adjudicate", "/nonexistent/packet/dir"],
        capture_output=True, text=True, cwd=str(Path.cwd()))
    assert rc.returncode == 2
    assert "environment error" in rc.stderr


def test_committed_reachability_record_claims_are_true():
    """Durable evidence integrity: the committed matrix proves all three claims."""
    rec = json.loads(REACHABILITY_RECORD.read_text(encoding="utf-8"))
    claims = rec["claims_tested"]
    assert claims["default_exit1_unreachable"] is True
    assert claims["adjudicate_exit1_reachable"] is True
    assert claims["naive_consumer_trap_reachable"] is True
    assert rec["verdict_contract_sha256"]["matches"] is True
    served = [p for p in rec["probes"] if p["mode"] == "served_lineage"]
    assert [p["exit_code"] for p in served] == [0, 2, 2, 2, 2]


# ---- mount-dependent: executable re-derivation --------------------------

@pytest.fixture(scope="module")
def probe_matrix(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("reachability")
    rc = subprocess.run(
        [sys.executable, "-m", "evaluation.frozen_bars.run_adjudication_probes",
         "--run-id", "test", "--out-dir", str(out_dir),
         "--bar-out-dir", str(out_dir)],
        capture_output=True, text=True, cwd=str(Path.cwd()))
    assert rc.returncode == 0, f"probe runner failed: {rc.stdout[-800:]} {rc.stderr[-800:]}"
    return json.loads((out_dir / "test_reachability.json").read_text(encoding="utf-8"))


@needs_mount
def test_h1_default_mode_record_stays_byte_identical_to_accepted(tmp_path):
    """H1: adding adjudicate mode changed nothing on the frozen lineage."""
    out = tmp_path / "record.json"
    rc = subprocess.run(
        [sys.executable, "-m", "evaluation.frozen_bars.run_bar_gates", "--out", str(out)],
        capture_output=True, text=True, cwd=str(Path.cwd()))
    assert rc.returncode == 0
    fresh = json.loads(out.read_text(encoding="utf-8"))
    accepted = json.loads(ACCEPTED_RECORD.read_text(encoding="utf-8"))
    fresh.pop("elapsed_s", None)
    accepted.pop("elapsed_s", None)
    assert fresh == accepted, "default served-lineage record drifted from the accepted record"
    assert "mode" not in fresh and "admission_reading" not in fresh, (
        "adjudicate-only fields leaked into the served_lineage record")


@needs_mount
def test_h2_served_lineage_exit1_unreachable_across_probe_matrix(probe_matrix):
    served = [p for p in probe_matrix["probes"] if p["mode"] == "served_lineage"]
    assert [p["exit_code"] for p in served] == [0, 2, 2, 2, 2]
    assert probe_matrix["claims_tested"]["default_exit1_unreachable"] is True


@needs_mount
def test_h3_blocking_paths_reachable_in_adjudicate_mode(probe_matrix):
    by_key = {(p["probe"], p["mode"]): p for p in probe_matrix["probes"]}
    blanked = by_key[("blanked_full_population", "adjudicate")]
    assert blanked["exit_code"] == 1
    assert blanked["key_fields"]["label_regression_verdict"] == "FAIL_REGRESSION"
    assert blanked["key_fields"]["label_blocks"] is True
    hostile = by_key[("hostile_geometry", "adjudicate")]
    assert hostile["exit_code"] == 1
    assert hostile["key_fields"]["geometry_regression_verdict"] == "FAIL_REGRESSION"
    assert hostile["key_fields"]["geometry_blocks"] is True


@needs_mount
def test_h4_naive_consumer_trap_reachable_and_flagged(probe_matrix):
    trap = [p for p in probe_matrix["probes"]
            if p["probe"] == "naive_consumer_trap" and p["mode"] == "adjudicate"][0]
    assert trap["exit_code"] == 0
    assert trap["key_fields"]["label_regression_verdict"] == "NOT_APPLICABLE"
    assert trap["key_fields"]["label_n_supported"] == 0
    assert trap["key_fields"]["label_blocks"] is False
    assert trap["naive_consumer_trap"] is True
    adjudicate_record = json.loads(
        Path("results/evaluation/bar_gates/38972887369_adjudicate_naive_consumer_trap.json")
        .read_text(encoding="utf-8"))
    assert adjudicate_record["admission_reading"]["naive_consumer_trap_fires"] is True
    assert adjudicate_record["label_negative_control_required"] is False
    assert "not_applicable_reason" in (
        adjudicate_record["label_gate"]["negative_control_blanked_evidence"])
