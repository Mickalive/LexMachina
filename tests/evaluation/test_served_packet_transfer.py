"""Tests for evaluation/served_packet_transfer.py (cycle 39092033997).

The cross-packet transfer instrument answers one product question: when a
served-artifact falsifier FIRES on one accepted served packet, is it a property
of the serve pipeline (fix upstream) or of that one packet (fix its serve gate)?

POST-FREEZE ADDITION in the sense established by evaluation/retrieval_gate/
id_hygiene.py and evaluation/served_bundle_scope.py: it adds no gate to any
frozen verdict file, writes no frozen file, re-scores nothing, and changes
neither accepted DO-NOT-SERVE order. The transfer RULE was frozen and committed in
results/evaluation/served_bundle_scope/FROZEN_HYPOTHESIS_39092033997.json BEFORE
the second packet was measured.

pytest is ABSENT in the producer image, so these tests are committed but not
executed there. The equivalent non-vacuity controls ARE executed there via
`python -m evaluation.served_packet_transfer --self-check`, and their result is
recorded beside this file's output.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation import served_packet_transfer as spt

ROOT = Path(__file__).resolve().parents[2]
HYP = ROOT / "results/evaluation/served_bundle_scope/FROZEN_HYPOTHESIS_39092033997.json"
RECORD = ROOT / "results/evaluation/served_packet_transfer/39092033997.json"
SIDE_B = ROOT / "results/evaluation/served_bundle_scope/39092033997.json"
SIDE_A = ROOT / "results/evaluation/served_bundle_scope/39086856920.json"


# --- the frozen hypothesis is a frozen hypothesis -----------------------------

def test_transfer_hypothesis_is_frozen_and_committed_before_execution():
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    assert hyp["schema"] == "lex-evaluation-served-bundle-scope-hypothesis/1"
    assert hyp["run_id"] == "39092033997"
    assert hyp["frozen_before_execution"] is True
    # the transfer rule itself must be in the frozen file, not invented afterwards
    assert set(hyp["transfer_rule"]) >= {"SYSTEMIC", "PACKET_SPECIFIC", "INCONCLUSIVE"}
    # the side being measured must be a DIFFERENT artifact of record
    assert hyp["input_of_record"]["served_packet"].endswith("38839347028")
    assert hyp["input_of_record"]["transfer_anchor"]["prior_packet"].endswith(
        "rebuilt-39027045675")


def test_transfer_hypothesis_pins_the_anchor_record_it_transfers_from():
    import hashlib
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    anchor = hyp["input_of_record"]["transfer_anchor"]
    got = hashlib.sha256(SIDE_A.read_bytes()).hexdigest()
    assert got == anchor["prior_record_sha256"], (
        "the accepted side-A record moved; the frozen transfer anchor is stale and the "
        "transfer must be re-frozen before it may be read as current")


def test_instrument_is_used_byte_identically_against_the_accepted_record():
    import hashlib
    hyp = json.loads(HYP.read_text(encoding="utf-8"))
    instr = (ROOT / "evaluation" / "served_bundle_scope.py").read_bytes()
    assert hashlib.sha256(instr).hexdigest() == \
        hyp["input_of_record"]["transfer_anchor"]["instrument_sha256"], (
        "the served-bundle instrument changed; the accepted 39086856920 record would no "
        "longer be reproducible from the frozen hypothesis")


# --- NOT_APPLICABLE is not a pass, at every layer -----------------------------

def test_not_measured_on_both_sides_is_inconclusive_not_refuted():
    rec = {"id": "f", "total": 0, "fired": False, "verdict": "NOT_MEASURED",
           "per_bundle": {}, "counted_field": "n_unusable_decision_id"}
    hyp = {"run_id": "t", "question": "q", "success_rule": "s", "_path": None,
           "transfer_rule": {}, "claim_ceiling": "c", "explicitly_not_gates": [],
           "frozen_bars_untouched": {}}
    side = {"verdict": "BENCHMARK_NOT_MEASURED", "n_decisions_total": 0,
            "bundle_sha256": {}, "falsifiers": [rec]}
    out = spt.transfer(hyp, side, Path("a.json"), side, Path("b.json"),
                       {"measurable": True})
    assert out["transfer_matrix"][0]["transfer"] == "INCONCLUSIVE"
    assert out["verdict"] == "NO_TRANSFER_FALSIFICATION"


def test_a_falsifier_missing_from_one_side_is_never_transferred():
    hyp = {"run_id": "t", "question": "q", "success_rule": "s", "_path": None,
           "transfer_rule": {}, "claim_ceiling": "c", "explicitly_not_gates": [],
           "frozen_bars_untouched": {}}
    a = {"verdict": "V", "n_decisions_total": 1, "bundle_sha256": {},
         "falsifiers": [{"id": "f", "total": 3, "fired": True, "verdict": "FALSIFIED",
                         "per_bundle": {"x": 1}, "counted_field": "n_unusable_decision_id"}]}
    b = {"verdict": "V", "n_decisions_total": 1, "bundle_sha256": {},
         "falsifiers": [{"id": "other", "total": 0, "fired": False, "verdict": "REFUTED",
                         "per_bundle": {"x": 1}, "counted_field": "n_unusable_decision_id"}]}
    out = spt.transfer(hyp, a, Path("a.json"), b, Path("b.json"), {"measurable": True})
    assert {r["transfer"] for r in out["transfer_matrix"]} == {"INCONCLUSIVE"}
    assert out["systemic_falsifiers"] == []


def test_unmeasurable_membership_withholds_the_transfer_verdict():
    hyp = {"run_id": "t", "question": "q", "success_rule": "s", "_path": None,
           "transfer_rule": {}, "claim_ceiling": "c", "explicitly_not_gates": [],
           "frozen_bars_untouched": {}}
    f = {"id": "f", "total": 3, "fired": True, "verdict": "FALSIFIED",
         "per_bundle": {"x": 1}, "counted_field": "n_unusable_decision_id"}
    side = {"verdict": "V", "n_decisions_total": 1, "bundle_sha256": {}, "falsifiers": [f]}
    out = spt.transfer(hyp, side, Path("a.json"), side, Path("b.json"),
                       {"measurable": False})
    assert out["verdict"] == "INCONCLUSIVE"


# --- the CLI must never emit a verdict it cannot support ---------------------

def test_missing_hypothesis_is_an_environment_error_never_a_pass():
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.served_packet_transfer", "--run-id", "t"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2, proc
    assert "--hypothesis is required" in proc.stderr


def test_unresolvable_predecessor_ref_is_an_environment_error():
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.served_packet_transfer", "--run-id", "t",
         "--hypothesis", str(HYP), "--prior-record", "results/evaluation/nope.json"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2, proc
    assert "side A unusable" in proc.stderr


def test_self_check_proves_every_transfer_branch_is_reachable():
    rc, lines = spt._self_check()
    assert rc == 0, "\n".join(lines)
    for branch in ("SYSTEMIC", "PACKET_SPECIFIC", "REFUTED_ON_BOTH",
                   "UNMEASURABLE_MEMBERSHIP_IS_INCONCLUSIVE"):
        assert any(branch in ln for ln in lines), (branch, lines)


# --- the executed record -----------------------------------------------------

@pytest.mark.skipif(not RECORD.exists(), reason="record not produced in this image")
def test_executed_record_is_a_negative_result_that_is_kept():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["schema"] == spt.SCHEMA
    assert rec["verdict"] == "SYSTEMIC_FALSIFICATION_REPRODUCED_ACROSS_SERVED_PACKETS"
    assert rec["falsification_proven"] is True
    # the two fired scope/source falsifiers must be SYSTEMIC
    got = {r["id"]: r["transfer"] for r in rec["transfer_matrix"]}
    assert got["source::decision_id_unusable"] == "SYSTEMIC"
    assert got["scope::outside_mission_date_window"] == "SYSTEMIC"
    assert got["scope::adversarial_seed_contamination"] == "SYSTEMIC"
    # a falsifier that never fired must NOT be laundered into a SYSTEMIC claim
    assert got["source::canonical_url_not_opencaselaw"] == "REFUTED_ON_BOTH"
    assert got["map::point_missing_geometry_or_cluster"] == "REFUTED_ON_BOTH"


@pytest.mark.skipif(not RECORD.exists(), reason="record not produced in this image")
def test_the_record_pins_both_sides_it_transfers():
    import hashlib
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["sides"]["side_a"]["record_sha256"] == \
        hashlib.sha256(SIDE_A.read_bytes()).hexdigest()
    assert rec["sides"]["side_b"]["record_sha256"] == \
        hashlib.sha256(SIDE_B.read_bytes()).hexdigest()


@pytest.mark.skipif(not RECORD.exists(), reason="record not produced in this image")
def test_the_record_discloses_that_the_two_sides_share_one_candidate_set():
    """The single strongest objection to the SYSTEMIC label is that the identical
    counts are a consequence of one retrieval, not independent replication. The
    record MUST carry that disclosure rather than the reader having to find it."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    prov = rec["side_provenance"]
    assert prov["one_retrieval_two_builds"] is True
    assert "ONE_RETRIEVAL_TWO_BUILDS" in prov["relation"]
    assert "NOT\nindependent" in prov["why_it_matters"] or \
        "NOT independent" in prov["why_it_matters"]
    d = rec["population_disclosure"]
    assert "NOT two independent retrievals" in d
    assert "not upgraded by repetition" in d
    # and the membership/presentation pair must actually support the label
    m = rec["membership"]
    assert m["decision_id_set_identical"] is True
    assert m["row_order_identical"] is False
    assert set(m["presentation_fields_that_moved"]) >= {"rank", "x", "y", "cluster_id"}
    assert m["independent_builds"] is True


@pytest.mark.skipif(not RECORD.exists(), reason="record not produced in this image")
def test_the_record_touches_no_frozen_bar():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    frozen = rec["frozen_bars_untouched"]
    assert frozen["RULES_LABEL.json"].startswith("4457e971")
    assert frozen["RULES_GEOMETRY.json"].startswith("a7452748")
    # a negative result is kept, not rounded up to a pass
    assert rec["systemic_falsifiers"], "a fired falsification must stay fired"