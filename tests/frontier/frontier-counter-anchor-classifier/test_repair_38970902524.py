"""REPAIR regression tests for cycle 38970902524.

This cycle did NOT re-run the charter: Outcome A was already accepted in run
38964146628 and the charter's stop rule forbids continuing.  What it did was
independently verify that accepted claim and repair the four defects the
accepted audit recorded as non-binding advisories.  These tests pin the
repairs so they cannot regress:

  * ADVISORY D -- the harness compared the incumbent reproduction in a dict
    keyed by decision_id.  4 decision_ids occur TWICE in the 65-row
    population, so 65 rows collapsed to 61 keys and 4 rows escaped the
    reproduction proof entirely.  Now a multiset comparison over full verdict
    tuples, with the coverage count asserted.
  * ADVISORY E -- STATUS_TO_LABEL.get(proposed, LABEL_LIMITING) defaulted an
    unrecognised issued counter_status to the polarity ``limiting``, i.e. the
    component could name a position a row never carried, which the claim
    ceiling forbids.  Now a COUNTED abstention.
  * ADVISORY C -- REPORT.md stated the swapped-evidence control abstains with
    ``no_intent_marker``; the frozen-precedence truth is ``pivot_absent``.
  * CLI -- the documented module invocation resolved its default paths one
    directory too shallow and crashed on the frozen rubric.

Pure unit tests: no network, no mount, no clock.  The population-level
behaviour-preservation proof (the accepted 5/65 -> 5/5 measurement is
unchanged by the advisory-E repair) lives in
test_repair_population_preserved.py, which skips without the accepted mount.
"""

from __future__ import annotations

import json
import os

import pytest

from frontier_counter_anchor_classifier.counter_anchor_classifier import (
    LABEL_ABSTAIN,
    LABEL_LIMITING,
    REASON_UNMAPPED_STATUS,
    STATUS_TO_LABEL,
    decide_label,
)
from frontier_counter_anchor_classifier.run_head_to_head import (
    _compare_to_accepted,
    _verdict_key,
)
from frontier_counter_anchor_classifier.vendored.rules import load_rules

from conftest import RULES_PATH

IT_PROFILE = "it-responsabilita-medica"
IT_CONTRARY_ROW = "bger_9C_749_2012"
IT_LIMITING_ROW = "ti_gerichte_36.2001.90"
DE_LIMITING_ROW = "zh_kassationsgericht_AC040036"

_FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "real_emitted_rows.json")


@pytest.fixture(scope="module")
def rules():
    return load_rules(RULES_PATH)


@pytest.fixture(scope="module")
def real_rows():
    """The rows the component actually EMITS on the served packet, copied
    verbatim into the fixture.  They pass every frozen criterion, so a test
    can mutate only ``counter_status`` and observe the mapping in isolation."""
    with open(_FIXTURE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["frozen_rules_sha256"] == (
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608")
    out = {}
    for entry in data["rows"]:
        out[entry["row"]["decision_id"]] = (entry["anchor_profile"], dict(entry["row"]))
    return out


def _real(rules, real_rows, decision_id, **over):
    profile_key, row = real_rows[decision_id]
    row.update(over)
    return row, rules.anchor_profile(profile_key)


# ---------------------------------------------------------------- advisory E
def test_unmapped_status_never_invents_a_polarity(rules, real_rows):
    """An issued counter_status outside STATUS_TO_LABEL must ABSTAIN, and must
    NOT be silently renamed to ``limiting``.  The row is one the component
    really does emit, so nothing but the status mapping can divert it."""
    row, profile = _real(rules, real_rows, IT_LIMITING_ROW, counter_status="candidate-vibes")
    d = decide_label(row, rules, profile)
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == REASON_UNMAPPED_STATUS
    # The regression this pins: the old code returned LABEL_LIMITING here.
    assert d.label != LABEL_LIMITING


def test_unmapped_status_abstains_even_when_evidence_is_strong(rules, real_rows):
    """The refusal is about the LABEL MAPPING, not the evidence quality: a
    perfectly evidenced row with an unmapped status still abstains, while the
    frozen evidence criteria are recorded as passing."""
    row, profile = _real(rules, real_rows, IT_LIMITING_ROW, counter_status="totally-unknown-status")
    d = decide_label(row, rules, profile)
    assert d.reason_code == REASON_UNMAPPED_STATUS
    ev = d.criterion_evidence
    assert ev["i_intent_marker_in_cited_evidence"]["pass"] is True
    assert ev["v_not_demonstrably_outside_question_domain"]["pass"] is True
    assert ev["vi_proposed_status_mappable"]["pass"] is False


def test_empty_status_abstains_unmapped(rules, real_rows):
    """A row carrying no usable status must never be handed a polarity."""
    row, profile = _real(rules, real_rows, IT_LIMITING_ROW, counter_status="")
    d = decide_label(row, rules, profile)
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == REASON_UNMAPPED_STATUS


def test_every_mapped_status_still_emits_its_own_polarity(rules, real_rows):
    """The repair must not break the six documented statuses: each one still
    emits, and the mapped polarity is the row's own, never another's."""
    expected = {
        "candidate-contrary": "contrary",
        "contrary": "contrary",
        "contrary_or_exception": "limiting",
        "candidate-limiting": "limiting",
        "limiting": "limiting",
        "supporting": "supporting",
    }
    assert set(expected) == set(STATUS_TO_LABEL)
    base_id = IT_LIMITING_ROW
    for status, label in expected.items():
        row, profile = _real(rules, real_rows, base_id, counter_status=status)
        d = decide_label(row, rules, profile)
        assert d.label == label, status
        assert d.reason_code == "supported", status


def test_contrary_row_stays_contrary_and_is_not_renamed(rules, real_rows):
    """The one emitted row whose issued status is candidate-contrary keeps its
    own polarity; the repair must not collapse it to ``limiting``."""
    row, profile = _real(rules, real_rows, IT_CONTRARY_ROW)
    d = decide_label(row, rules, profile)
    assert d.label == "contrary"
    assert row["counter_status"] == "candidate-contrary"


def test_unmapped_reason_is_in_the_uncertainty_table():
    from frontier_counter_anchor_classifier.counter_anchor_classifier import (
        ABSTAIN_UNCERTAINTY,
    )
    assert REASON_UNMAPPED_STATUS in ABSTAIN_UNCERTAINTY
    assert 0.0 < ABSTAIN_UNCERTAINTY[REASON_UNMAPPED_STATUS] <= 1.0


# ---------------------------------------------------------------- advisory D
def _vrow(bundle, did, status, dc, rc, sup):
    return {
        "_bundle": bundle,
        "decision_id": did,
        "counter_status": status,
        "primary_defect_class": dc,
        "reason_code": rc,
        "supported": sup,
    }


def test_duplicate_decision_ids_are_compared_not_collapsed():
    """The exact advisory-D shape: a decision_id that appears TWICE with
    DIFFERENT verdicts.  A dict keyed by decision_id silently kept only one
    copy and reported the reproduction as byte-identical."""
    accepted_rows = [
        {"decision_id": "dup", "counter_status": "candidate-contrary",
         "primary_defect_class": "SUPPORTED", "reason_code": "supported", "supported": True},
        {"decision_id": "dup", "counter_status": "candidate-limiting",
         "primary_defect_class": "UNBACKED", "reason_code": "no_intent_marker", "supported": False},
    ]
    # Reproduced with the SECOND copy's verdict swapped: a real divergence.
    reproduced = [
        _vrow("de-x", "dup", "candidate-contrary", "SUPPORTED", "supported", True),
        _vrow("de-x", "dup", "candidate-limiting", "UNBACKED", "no_domain_anchor", False),
    ]
    cmp = _compare_to_accepted(
        reproduced, accepted_rows, {"de-x": accepted_rows})
    assert cmp["n_accepted_rows"] == 2
    assert cmp["n_reproduced_rows"] == 2
    assert cmp["n_accepted_unique_decision_id_keys"] == 1
    assert cmp["n_rows_matched"] == 1
    # Divergence is reported as a symmetric difference: the disagreeing copy is
    # listed once as only-in-accepted and once as only-in-reproduced.
    assert cmp["n_rows_divergent"] == 2
    assert cmp["only_in_accepted"] and cmp["only_in_reproduced"]
    assert cmp["reproduced_byte_identical_verdicts"] is False
    assert cmp["coverage_is_full_population"] is True
    assert cmp["n_duplicate_decision_ids"] == 1


def test_duplicate_decision_ids_all_matching_is_byte_identical():
    accepted_rows = [
        {"decision_id": "dup", "counter_status": "candidate-limiting",
         "primary_defect_class": "UNBACKED", "reason_code": "pivot_absent", "supported": False},
        {"decision_id": "dup", "counter_status": "candidate-contrary",
         "primary_defect_class": "SUPPORTED", "reason_code": "supported", "supported": True},
    ]
    reproduced = [
        _vrow("de-x", "dup", "candidate-limiting", "UNBACKED", "pivot_absent", False),
        _vrow("de-x", "dup", "candidate-contrary", "SUPPORTED", "supported", True),
    ]
    cmp = _compare_to_accepted(reproduced, accepted_rows, {"de-x": accepted_rows})
    assert cmp["n_rows_matched"] == 2
    assert cmp["n_rows_divergent"] == 0
    assert cmp["reproduced_byte_identical_verdicts"] is True


def test_same_id_different_bundle_is_not_a_collision():
    """Bundle provenance is part of the key: the same decision cited in two
    bundles is two rows, and swapping one bundle's verdict IS a divergence."""
    accepted_rows = [
        {"decision_id": "same", "counter_status": "candidate-limiting",
         "primary_defect_class": "SUPPORTED", "reason_code": "supported", "supported": True},
        {"decision_id": "same", "counter_status": "candidate-limiting",
         "primary_defect_class": "UNBACKED", "reason_code": "pivot_absent", "supported": False},
    ]
    by_bundle = {"de-x": [accepted_rows[0]], "it-y": [accepted_rows[1]]}
    reproduced = [
        _vrow("de-x", "same", "candidate-limiting", "SUPPORTED", "supported", True),
        _vrow("it-y", "same", "candidate-limiting", "UNBACKED", "no_intent_marker", False),
    ]
    cmp = _compare_to_accepted(reproduced, accepted_rows, by_bundle)
    assert cmp["n_rows_matched"] == 1
    assert cmp["n_rows_divergent"] == 2
    assert cmp["reproduced_byte_identical_verdicts"] is False


def test_verdict_key_is_the_full_tuple_not_the_id():
    k = _verdict_key(
        "de-x",
        {"decision_id": "d", "counter_status": "s",
         "_verdict": {"primary_defect_class": "UNBACKED",
                      "reason_code": "pivot_absent", "supported": False}},
    )
    assert k == ("de-x", "d", "s", "UNBACKED", "pivot_absent", False)


# ------------------------------------------------------------------- CLI
def test_cli_default_paths_point_at_the_repo_root():
    """REPAIR: the documented module invocation used three dirname() hops and
    resolved to <repo>/frontier, so --rules defaulted to a nonexistent
    <repo>/frontier/results/... and the CLI crashed before scoring."""
    from frontier_counter_anchor_classifier import run_head_to_head as h
    import inspect
    src = inspect.getsource(h.main)
    # Four dirname hops, not three.
    assert src.count("os.path.dirname") >= 4
    assert "HEAD_TO_HEAD_R2_38970902524.json" in src
    # And the default rules path must be the real accepted rubric location.
    from conftest import RULES_PATH
    assert os.path.basename(RULES_PATH) == "RULES_LABEL.json"


def test_cli_default_out_never_clobbers_the_accepted_claim_artifact():
    """Running with defaults must not overwrite the accepted Outcome A
    artifact HEAD_TO_HEAD.json (no overwrite of claim-bearing results)."""
    import inspect
    from frontier_counter_anchor_classifier import run_head_to_head as h
    src = inspect.getsource(h.main)
    assert '"--out"' in src
    assert 'HEAD_TO_HEAD.json' not in src.split("--out")[-1]


# ---------------------------------------------------------------- advisory C
def test_swapped_evidence_control_is_pivot_absent_not_no_intent_marker(
    rules, real_rows
):
    """The non-vacuity control the report describes: an emitted row with its
    cited evidence swapped for another BUNDLE's emitted evidence.  The donor
    passage still carries an intent marker, but it speaks to a different
    question, so the FROZEN precedence fires the PIVOT test (step 5) before the
    intent-marker test (step 6) and the reason is ``pivot_absent``.

    REPORT.md (accepted cycle 38964146628, line 80) stated
    ``no_intent_marker``; the accepted audit advisory and this cycle's re-run
    both show ``pivot_absent``.  This test pins the true reason so the report
    cannot drift again.
    """
    donor_profile, donor = real_rows[IT_LIMITING_ROW]
    _, target = real_rows[DE_LIMITING_ROW]
    swapped = dict(target)
    swapped["counter_evidence"] = donor["counter_evidence"]
    # The harness control nulls title/regeste/row_text so the ONLY text is the
    # donor's cited sentence.  That is what makes the PIVOT test fire: the
    # context window (evidence + title + regeste) then carries no pivot anchor
    # of the target's own question.  Keeping the target's regeste would
    # instead let the PIVOT test pass and fire the intent-marker test at
    # step 6 -- a different control with a different (also abstain) reason.
    swapped.update({"title": None, "regeste": None, "row_text": donor["counter_evidence"]})
    d = decide_label(swapped, rules, rules.anchor_profile("de-kapitalverletzung"))
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "pivot_absent"
    assert d.reason_code != "no_intent_marker"
    # The donor passage itself does carry an intent marker, which is exactly
    # why the report's original claim was wrong.
    donor_decision = decide_label(donor, rules, rules.anchor_profile(donor_profile))
    assert donor_decision.criterion_evidence[
        "i_intent_marker_in_cited_evidence"]["pass"] is True


def test_swapped_control_keeps_the_marker_but_loses_the_pivot(rules, real_rows):
    """Documented negative control for the test above: if the target's regeste
    (which carries the pivot anchor) is retained, the SAME donor evidence
    abstains under a different frozen reason.  Both abstain -- the report's
    claim was about which one the harness actually builds."""
    donor_profile, donor = real_rows[IT_LIMITING_ROW]
    _, target = real_rows[DE_LIMITING_ROW]
    swapped = dict(target)
    swapped["counter_evidence"] = donor["counter_evidence"]
    d = decide_label(swapped, rules, rules.anchor_profile("de-kapitalverletzung"))
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "no_intent_marker"