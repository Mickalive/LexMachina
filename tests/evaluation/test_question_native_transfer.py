"""Tests for the question-native concept-gap DISCLOSURE transfer instrument.

Run 39120832665 (factory direction v56). The instrument measures whether the
ACCEPTED disclosure defect of cycle 39113690481 (packet 38839347028) transfers
to the REBUILT packet rebuilt-39027045675. These tests pin the frozen predicate,
the verdict classes, the non-vacuity controls and the accepted record's own
headline - they do NOT re-run the live measurement and do NOT touch any frozen
rubric, bar or accepted DO-NOT-SERVE order.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.question_native_transfer import (
    DISCLOSURE_MARKERS,
    EXIT_FALSIFIED,
    EXIT_NOT_MEASURED,
    EXIT_OK,
    FROZEN_QIDS,
    PACKET_A,
    PACKET_B,
    _synthetic_admissibility,
    disclosure_gap_predicate,
    independent_zero_set,
    run_non_vacuity_controls,
)
from evaluation import subject_match_audit as sma

ROOT = Path(__file__).resolve().parents[2]
HYP = ROOT / "evaluation" / "QUESTION_NATIVE_TRANSFER_HYPOTHESIS.json"
RECORD = ROOT / "results" / "evaluation" / "question_native_transfer" / "39120832665.json"


def _load(p: Path) -> dict:
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# frozen-constant pins
# --------------------------------------------------------------------------- #
def test_frozen_qids_are_the_three_accepted_anchor_qids():
    assert FROZEN_QIDS == (
        "de-kapitalverletzung",
        "fr-bail-entretien",
        "it-responsabilita-medica",
    )


def test_disclosure_markers_are_frozen_and_substring_based():
    assert DISCLOSURE_MARKERS == (
        "concept", "under_covered", "undercovered", "query_concept",
    )


def test_hypothesis_file_pins_the_module_constants():
    hyp = _load(HYP)
    assert tuple(hyp["frozen_inputs"]["frozen_qids_UNCHANGED"]) == FROZEN_QIDS
    assert PACKET_B in hyp["frozen_inputs"]["packet_b_rebuilt"]
    assert PACKET_A in hyp["frozen_inputs"]["packet_a_prior_served"]
    assert hyp["frozen_before_execution"] is True
    # the exploratory pre-check must stay disclosed, never laundered
    assert "exploratory_pre_check_DISCLOSED" in hyp
    assert hyp["exploratory_pre_check_DISCLOSED"]["status"].startswith("EXPLORATORY")


def test_exit_code_contract_is_pinned():
    hyp = _load(HYP)
    contract = hyp["exit_code_contract"]
    # The frozen hypothesis carries a short parenthetical on 1 and 2; the
    # hypothesis is frozen and is NEVER edited after execution, so the test
    # pins the frozen wording itself, not a paraphrase of it.
    assert contract["0"] == "DISCLOSURE_DEFECT_NOT_TRANSFERRED"
    assert contract["1"] == "DISCLOSURE_DEFECT_TRANSFERRED (falsification kept)"
    assert contract["2"].startswith("NOT_MEASURED")
    assert (EXIT_OK, EXIT_FALSIFIED, EXIT_NOT_MEASURED) == (0, 1, 2)


# --------------------------------------------------------------------------- #
# the frozen disclosure predicate
# --------------------------------------------------------------------------- #
def test_predicate_fires_on_measured_gap_with_no_disclosing_finding():
    m = disclosure_gap_predicate(
        _synthetic_admissibility(["kapitalverletzung"], []))
    assert m["disclosure_gap_predicate_fires"] is True


def test_predicate_does_not_fire_when_a_disclosing_finding_exists():
    m = disclosure_gap_predicate(
        _synthetic_admissibility(["kapitalverletzung"], ["query_concepts_under_covered"]))
    assert m["disclosure_gap_predicate_fires"] is False
    assert m["disclosing_finding_codes"] == ["query_concepts_under_covered"]


def test_predicate_does_not_fire_on_empty_under_covered():
    m = disclosure_gap_predicate(_synthetic_admissibility([], []))
    assert m["disclosure_gap_predicate_fires"] is False


def test_predicate_does_not_fire_when_inadmissible():
    m = disclosure_gap_predicate(
        _synthetic_admissibility(["kapitalverletzung"], [], admissible=False))
    assert m["disclosure_gap_predicate_fires"] is False


def test_unrelated_warning_codes_do_not_satisfy_disclosure():
    """warning_count>0 for an unrelated reason must never count as disclosure."""
    m = disclosure_gap_predicate(
        _synthetic_admissibility(
            ["kapitalverletzung"],
            ["counter_authority_has_product_owned_channel"]))
    assert m["warning_count"] == 1
    assert m["disclosing_finding_codes"] == []
    assert m["disclosure_gap_predicate_fires"] is True


# --------------------------------------------------------------------------- #
# independent recomputation reuses the FROZEN imported functions
# --------------------------------------------------------------------------- #
def test_independent_recompute_zero_set():
    q = {"question": "Kapitalverletzung und Uberwachungspflicht des Arbeitgebers"}
    empty = {"decisions": [{"decision_id": "y", "title": "Nichts"}]}
    rec = independent_zero_set(q, empty, sma)
    assert "kapitalverletzung" in rec["zero_set"]


def test_independent_recompute_covered_concept_is_not_zero():
    q = {"question": "Kapitalverletzung und Uberwachungspflicht des Arbeitgebers"}
    covered = {"decisions": [{"decision_id": "x", "title": "Zur Kapitalverletzung"}]}
    rec = independent_zero_set(q, covered, sma)
    assert "kapitalverletzung" not in rec["zero_set"]


def test_non_vacuity_controls_all_pass():
    controls = run_non_vacuity_controls(sma)
    assert len(controls) == 5
    failed = [c["control"] for c in controls if not c["passed"]]
    assert failed == [], f"non-vacuity controls failed: {failed}"


# --------------------------------------------------------------------------- #
# the accepted claim-bearing record of this run (immutable once written)
# --------------------------------------------------------------------------- #
def test_accepted_record_verdict_is_the_transferred_defect():
    rec = _load(RECORD)
    assert rec["verdict"] == "DISCLOSURE_DEFECT_TRANSFERRED"
    assert rec["exit_code"] == EXIT_FALSIFIED
    assert rec["network_requests"] == 0
    assert rec["pins"]["all_match"] is True
    assert rec["non_vacuity_all_passed"] is True
    assert rec["any_disclosure_gap_fires"] is True


def test_accepted_record_de_qid_fires_and_fr_it_do_not():
    rec = _load(RECORD)
    by_qid = {r["qid"]: r for r in rec["per_qid"]}
    assert set(by_qid) == set(FROZEN_QIDS)
    assert by_qid["de-kapitalverletzung"]["rebuilt_predicate"][
        "disclosure_gap_predicate_fires"] is True
    assert by_qid["fr-bail-entretien"]["rebuilt_predicate"][
        "disclosure_gap_predicate_fires"] is False
    assert by_qid["it-responsabilita-medica"]["rebuilt_predicate"][
        "disclosure_gap_predicate_fires"] is False


def test_accepted_record_independent_recomputation_agrees_on_every_qid():
    rec = _load(RECORD)
    for row in rec["per_qid"]:
        assert row["product_vs_independent_agreement"]["agree"] is True, row["qid"]
    assert rec["independent_recomputation_disagreements"] == []


def test_accepted_record_de_zero_set_is_exactly_the_two_frozen_concepts():
    rec = _load(RECORD)
    de = next(r for r in rec["per_qid"] if r["qid"] == "de-kapitalverletzung")
    assert de["rebuilt_predicate"]["query_concepts_under_covered"] == [
        "kapitalverletzung", "uberwachungspflicht"]
    assert de["rebuilt_independent_recomputation"]["zero_set"] == [
        "kapitalverletzung", "uberwachungspflicht"]
    assert de["rebuilt_predicate"]["warning_count"] == 0
    assert de["rebuilt_predicate"]["blocking_count"] == 0
    assert de["rebuilt_predicate"]["disclosing_finding_codes"] == []


def test_accepted_record_prior_packet_also_fired_on_the_same_qid():
    rec = _load(RECORD)
    de = next(r for r in rec["per_qid"] if r["qid"] == "de-kapitalverletzung")
    prior = de["prior_packet_38839347028_predicate"]
    assert prior is not None
    assert prior["disclosure_gap_predicate_fires"] is True


def test_record_never_claims_unchanged_items_were_changed():
    rec = _load(RECORD)
    unchanged = " ".join(rec["unchanged"])
    assert "human_gate_ready=false" in unchanged
    assert "DO-NOT-SERVE" in unchanged
    assert "no frozen rubric" in unchanged
