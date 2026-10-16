"""Contract tests for the sentence-anchored counter-anchor classifier.

These pin the ABSTAIN contract (charter acceptance test 2 and 6) with
self-contained synthetic rows: an empty-evidence row can NEVER receive a
confident label, and each frozen-precedence defect produces a COUNTED ABSTAIN
with the matching reason code.  The supported case emits a label.

Pure unit tests: no network, no mount, no clock.
"""

from __future__ import annotations

import pytest

from frontier_counter_anchor_classifier.counter_anchor_classifier import (
    LABEL_ABSTAIN,
    LABEL_CONTRARY,
    LABEL_LIMITING,
    decide_label,
)
from frontier_counter_anchor_classifier.vendored.rules import load_rules

from conftest import RULES_PATH

IT_PROFILE = "it-responsabilita-medica"
FR_PROFILE = "fr-bail-entretien"


@pytest.fixture(scope="module")
def rules():
    return load_rules(RULES_PATH)


@pytest.fixture(scope="module")
def it_profile(rules):
    return rules.anchor_profile(IT_PROFILE)


@pytest.fixture(scope="module")
def fr_profile(rules):
    return rules.anchor_profile(FR_PROFILE)


def _row(**over):
    base = {
        "decision_id": "TEST",
        "counter_status": "candidate-limiting",
        "counter_evidence": "",
        "counter_reason": "limiting",
        "counter_uncertainty": 0.5,
        "language": "it",
        "legal_area": "",
        "title": "",
        "regeste": "",
        "rank": 1,
    }
    base.update(over)
    return base


# -- the ABSTAIN contract ---------------------------------------------------

def test_empty_evidence_can_never_receive_a_confident_label(rules, it_profile):
    """Acceptance test 6: an empty-evidence row abstains, never a label."""
    for status in ("candidate-limiting", "candidate-contrary", "contrary_or_exception"):
        d = decide_label(_row(counter_status=status, counter_evidence=""), rules, it_profile)
        assert d.label == LABEL_ABSTAIN
        assert d.abstained
        assert d.reason_code == "evidence_absent"
        assert d.uncertainty >= 0.95  # unevidenced by construction
        assert d.cited_sentence == ""


def test_whitespace_only_evidence_is_still_absent(rules, it_profile):
    d = decide_label(_row(counter_evidence="   \n  "), rules, it_profile)
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "evidence_absent"


def test_fragment_pointer_abstains(rules, it_profile):
    d = decide_label(_row(counter_evidence="cited in generated answer"), rules, it_profile)
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "pointer_only"


def test_bare_statute_reference_abstains(rules, it_profile):
    d = decide_label(_row(counter_evidence="art. 2052"), rules, it_profile)
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "pointer_only"


def test_polarity_inversion_abstains(rules, it_profile):
    # appeal rejected / lower ruling confirmed, labelled contrary -> inverted
    d = decide_label(
        _row(
            counter_status="candidate-contrary",
            counter_evidence="Il ricorso e stato respinto e la sentenza e stata confermata.",
        ),
        rules,
        it_profile,
    )
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "polarity_inverted"


def test_procedural_boilerplate_without_marker_abstains(rules, fr_profile):
    # French Eintretens-style disposal formula, no counter-intent marker.
    d = decide_label(
        _row(
            language="fr",
            counter_status="candidate-limiting",
            counter_evidence=(
                "Contre le jugement de la premiere instance, la Cour a statue "
                "dans le sens des considerants."
            ),
        ),
        rules,
        fr_profile,
    )
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "procedural_formula_no_intent"


def test_no_intent_marker_abstains(rules, it_profile):
    # domain anchor (medico) + pivot (medico) present, but NO frozen marker
    d = decide_label(
        _row(counter_evidence="Il medico deve rispondere del nesso causale."),
        rules,
        it_profile,
    )
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "no_intent_marker"


def test_no_domain_anchor_abstains(rules, it_profile):
    # pivot (diagnosi) + marker (limita) present, but NO DOMAIN-tier anchor.
    # NB: the 4-char pivot "2052" cannot prefix-match (min_anchor_prefix_chars=5),
    # so a real pivot token is required to reach the domain check.
    d = decide_label(
        _row(counter_evidence="La diagnosi limita la prova."),
        rules,
        it_profile,
    )
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "no_domain_anchor"


def test_pivot_absent_abstains(rules, it_profile):
    # domain (responsabilita/danno) + marker (limita) present, but NO PIVOT anchor
    d = decide_label(
        _row(counter_evidence="La responsabilita si limita al danno diretto."),
        rules,
        it_profile,
    )
    assert d.label == LABEL_ABSTAIN
    assert d.reason_code == "pivot_absent"


# -- the emission case -------------------------------------------------------

def test_supported_sentence_emits_a_label(rules, it_profile):
    # mirrors the frozen supported control: limiting medical-liability
    # sentence, intent marker present, no inversion, no boilerplate,
    # domain and pivot terms present
    d = decide_label(
        _row(
            counter_evidence=(
                "La responsabilita del medico si presume solo se il nesso "
                "causale e dimostrato; in caso contrario si esclude la "
                "responsabilita."
            ),
        ),
        rules,
        it_profile,
    )
    assert d.label == LABEL_LIMITING
    assert not d.abstained
    assert d.reason_code == "supported"
    assert d.uncertainty < 0.5
    assert d.criterion_evidence["i_intent_marker_in_cited_evidence"]["pass"]
    assert d.criterion_evidence["iv_topical_term_in_evidence_or_title"]["pass"]
    assert d.criterion_evidence["v_not_demonstrably_outside_question_domain"]["pass"]


def test_emitted_label_never_inverted(rules, it_profile):
    """No synthetic inverted construction may ever be emitted."""
    for evidence in (
        "Il ricorso e stato respinto e la sentenza e stata confermata.",
        "La Cour a rejete le recours. Le jugement est confirme.",
        "Das Rechtsmittel wird abgewiesen, die Vorinstanz wird bestatigt.",
    ):
        d = decide_label(
            _row(counter_status="candidate-contrary", counter_evidence=evidence),
            rules,
            it_profile,
        )
        assert d.label == LABEL_ABSTAIN, evidence


def test_decision_is_deterministic(rules, it_profile):
    row = _row(
        counter_evidence=(
            "La responsabilita del medico si presume solo se il nesso causale "
            "e dimostrato; in caso contrario si esclude."
        )
    )
    a = decide_label(row, rules, it_profile)
    b = decide_label(row, rules, it_profile)
    assert a == b


def test_status_to_label_mapping(rules, it_profile):
    cases = {
        "candidate-contrary": LABEL_CONTRARY,
        "contrary_or_exception": LABEL_LIMITING,
        "candidate-limiting": LABEL_LIMITING,
        "supporting": "supporting",
    }
    for status, expected in cases.items():
        d = decide_label(
            _row(
                counter_status=status,
                counter_evidence=(
                    "La responsabilita del medico si presume solo se il nesso "
                    "causale e dimostrato; in caso contrario si esclude."
                ),
            ),
            rules,
            it_profile,
        )
        assert d.label == expected
