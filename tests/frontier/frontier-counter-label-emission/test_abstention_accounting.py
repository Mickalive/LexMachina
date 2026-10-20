"""Abstention accounting + absolute-bar tests (acceptance tests 3, 6)."""

from __future__ import annotations

import json

from conftest import PACKET, requires_accepted
from frontier_counter_label_emission import (
    SCORED_STATUSES,
    promote_heuristic_proposals,
    run_classifier_on_bundle,
)
from frontier_counter_label_emission.absolute_bar import (
    STATUS_INSUFFICIENT,
    STATUS_NOT_APPLICABLE,
    STATUS_NOT_MEASURED,
    compute_absolute_bar_status,
)


@requires_accepted
def test_abstention_accounting_invariant():
    for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"):
        bundle = json.loads(
            (PACKET / "questions" / f"{qid}.bundle.json").read_text(encoding="utf-8")
        )
        repaired = promote_heuristic_proposals(bundle, scored_statuses=SCORED_STATUSES)
        em = run_classifier_on_bundle(repaired, qid=qid)
        assert em["n_scored"] == em["n_emitted"] + em["n_abstained"]
        assert em["abstained_status_marker"] == "abstained_unevidenced"
        for row in em["abstained"]:
            assert row["reason_code"]


@requires_accepted
def test_before_emission_is_zero_scored():
    bundle = json.loads(
        (PACKET / "questions" / "de-kapitalverletzung.bundle.json").read_text(encoding="utf-8")
    )
    em = run_classifier_on_bundle(bundle, qid="de-kapitalverletzung")
    assert em["n_scored"] == 0
    assert em["n_emitted"] == 0
    assert em["n_abstained"] == 0


def test_not_measured_never_a_pass():
    rules = {"populations": {"primary": {"required_min_population_primary": 7}},
             "verdict_rule": {}}
    status = compute_absolute_bar_status(
        {"n_scored": 0, "n_emitted": 0, "support_rate_among_issued": 0.0}, rules,
    )
    assert status["status"] == STATUS_NOT_MEASURED
    assert status["satisfied"] is False


def test_not_applicable_never_a_pass():
    status = compute_absolute_bar_status(
        {"n_scored": 10, "n_emitted": 10, "support_rate_among_issued": 1.0},
        {"populations": {}, "verdict_rule": {}},
    )
    assert status["status"] == STATUS_NOT_APPLICABLE
    assert status["satisfied"] is False


def test_insufficient_population():
    rules = {"populations": {"primary": {"required_min_population_primary": 7}},
             "verdict_rule": {}}
    status = compute_absolute_bar_status(
        {"n_scored": 4, "n_emitted": 0, "support_rate_among_issued": 0.0}, rules,
    )
    assert status["status"] == STATUS_INSUFFICIENT
    assert status["satisfied"] is False


def test_label_sound_only_when_full_support():
    rules = {"populations": {"primary": {"required_min_population_primary": 7}},
             "verdict_rule": {}}
    ok = compute_absolute_bar_status(
        {"n_scored": 7, "n_emitted": 7, "support_rate_among_issued": 1.0}, rules,
    )
    assert ok["satisfied"] is True
    bad = compute_absolute_bar_status(
        {"n_scored": 7, "n_emitted": 5, "support_rate_among_issued": 5 / 7}, rules,
    )
    assert bad["satisfied"] is False
