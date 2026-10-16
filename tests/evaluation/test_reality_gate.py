#!/usr/bin/env python3
"""Frozen tests for the evaluation-lane reality benchmark (direction v49).

These tests pin the benchmark itself: they fail if the frozen spec is
tampered with (digest pin) and they prove every gate CAN fail — a gate that
cannot fail is not a benchmark.  Pure standard library + pytest.
"""
import json

import pytest

from evaluation.reality_gate import frozen, gates

SPEC = frozen.load_frozen()
QUESTIONS = frozen.question_by_slug(SPEC)

# --------------------------------------------------------------------------- #
# freeze discipline
# --------------------------------------------------------------------------- #


def test_frozen_spec_digest_pin():
    import hashlib
    raw = frozen._PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == frozen.FROZEN_SHA256


def test_frozen_question_set_exact():
    assert [q["slug"] for q in SPEC["questions"]] == [
        "rent-default",
        "corporate-criminal-liability",
        "business-judgment-rule",
        "petty-theft-dismissal",
    ]
    assert SPEC["direction_version"] == 49
    assert SPEC["latency_budget_seconds"] == 300.0


def test_frozen_controlling_authorities_pinned():
    """The controlling authorities the observed reality-check failures turned on."""
    ccl = QUESTIONS["corporate-criminal-liability"]
    assert set(ccl["required_citation_ids"]) == {"bge_BGE_142_IV_333", "bger_6B_124_2016"}
    bjr = QUESTIONS["business-judgment-rule"]
    assert set(bjr["required_citation_ids"]) == {
        "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
        "bger_4A_603_2014", "bger_4A_62_2024",
    }
    petty = QUESTIONS["petty-theft-dismissal"]
    assert set(petty["required_citation_ids"]) == {"bger_4A_228_2015", "bger_4A_177_2017"}
    assert set(petty["required_retrieval_ids"]) == {"bger_4A_228_2015", "bger_4A_177_2017"}


def test_frozen_phrases_match_their_normalized_form():
    """The frozen phrase lists survive the normalization unchanged (apostrophe variants)."""
    for q in SPEC["questions"]:
        for gate in q["truth_gates"]:
            phrases = gate.get("contains_any") or gate.get("absent_any") or []
            for phrase in phrases:
                norm = gates.normalize_text(phrase)
                if "’" not in phrase and "'" not in phrase:
                    assert norm == phrase.casefold(), (phrase, norm)


# --------------------------------------------------------------------------- #
# truth gates: every gate can fail
# --------------------------------------------------------------------------- #

POSITIVE_PROSE = {
    "rent-default": (
        "Le bailleur peut résilier le bail d'habitation pour retard de loyer: "
        "préavis de 30 jours, prise d'effet à la fin d'un mois. "
        "L'abus de droit et l'exigence de bonne foi limitent cette prérogative."
    ),
    "corporate-criminal-liability": (
        "L'art. 102 CP connaît deux régimes: la responsabilité subsidiaire de "
        "l'entreprise (al. 1) et la responsabilité primaire (al. 2)."
    ),
    "business-judgment-rule": (
        "Le juge suisse exige une information suffisante du conseil "
        "d'administration, l'absence de conflit d'intérêt et fait preuve de "
        "retenue: il s'abstient de revoir le fond (abstention/deference)."
    ),
    "petty-theft-dismissal": (
        "Un vol de faible valeur (bagatell, geringfugig) commis par un employé "
        "peut justifier un licenciement immédiat selon l'art. 337 CO."
    ),
}


@pytest.mark.parametrize("slug", list(POSITIVE_PROSE))
def test_truth_gates_pass_on_positive_prose(slug):
    outcomes = gates.evaluate_truth_gates(QUESTIONS[slug], POSITIVE_PROSE[slug])
    assert outcomes, slug
    assert all(o["passed"] for o in outcomes), (slug, outcomes)


@pytest.mark.parametrize("slug", list(POSITIVE_PROSE))
def test_truth_gates_fail_when_each_required_branch_is_removed(slug):
    base = POSITIVE_PROSE[slug]
    for gate in QUESTIONS[slug]["truth_gates"]:
        if gate["kind"] == "phrase_absent":
            continue
        # remove the branch: drop the sentence containing the first phrase
        phrase = gate["contains_any"][0]
        norm = gates.normalize_text(base)
        assert phrase in norm
        sentences = norm.split(". ")
        mutated = ". ".join(s for s in sentences if phrase not in s)
        if mutated == norm:
            mutated = norm.replace(phrase, phrase[0] + "X" + phrase[2:])
        outcomes = gates.evaluate_truth_gates(QUESTIONS[slug], mutated)
        by_id = {o["gate"]: o for o in outcomes}
        assert by_id[f"truth::{gate['id']}"]["passed"] is False, (slug, gate["id"])


def test_art102_reversal_gate_fails_on_reversed_classification():
    q = QUESTIONS["corporate-criminal-liability"]
    reversed_prose = (
        "L'art. 102 CP ne cree pas une responsabilite primaire pour l'entreprise."
    )
    outcomes = gates.evaluate_truth_gates(q, reversed_prose)
    by_id = {o["gate"]: o for o in outcomes}
    # the phrase-presence gates still fire on the (negated) phrase — this is
    # exactly why the frozen benchmark carries a dedicated phrase_absent gate:
    # phrase presence alone cannot detect a reversed classification.
    assert by_id["truth::art102_primary"]["passed"] is True
    assert by_id["truth::art102_no_reversal"]["passed"] is False


# --------------------------------------------------------------------------- #
# language gate
# --------------------------------------------------------------------------- #


def test_language_gate_rejects_wrong_language_answer():
    q = QUESTIONS["rent-default"]
    en = ("The landlord may terminate the residential lease for rent default. "
          "The notice period is thirty days and ends at the end of the month. "
          "Good faith limits the termination.")
    outcome = gates.evaluate_language_gate(q, en, SPEC)
    assert outcome["passed"] is False
    assert "wrong-language" in outcome["detail"]


def test_language_gate_accepts_question_language_and_german_fallback():
    q = QUESTIONS["rent-default"]
    fr = POSITIVE_PROSE["rent-default"]
    de = ("Der Vermieter kann den Mietvertrag wegen Mietrückständen kündigen: "
          "Frist von 30 Jahren, Ende eines Monats, Rechtsmissbrauch schränkt ein.")
    assert gates.evaluate_language_gate(q, fr, SPEC)["passed"] is True
    assert gates.evaluate_language_gate(q, de, SPEC)["passed"] is True


# --------------------------------------------------------------------------- #
# corruption gate
# --------------------------------------------------------------------------- #


def test_corruption_gate_flags_repetition_loop():
    prose = ("Le juge s'abstient de revoir la décision. " * 40)
    outcome = gates.evaluate_corruption_gate(prose)
    assert outcome["passed"] is False
    assert any("repeated sentence" in r for r in outcome["measured"]["corruption_reasons"])


def test_corruption_gate_flags_mojibake():
    outcome = gates.evaluate_corruption_gate("Le juge � s'abstient de revoir la d�cision.")
    assert outcome["passed"] is False
    assert any("U+FFFD" in r for r in outcome["measured"]["corruption_reasons"])


def test_corruption_gate_accepts_clean_prose():
    outcome = gates.evaluate_corruption_gate(POSITIVE_PROSE["business-judgment-rule"])
    assert outcome["passed"] is True
    assert outcome["measured"]["corruption_reasons"] == []


# --------------------------------------------------------------------------- #
# latency gate
# --------------------------------------------------------------------------- #


def test_latency_gate_boundary():
    assert gates.evaluate_latency(299.9, 300.0)["passed"] is True
    assert gates.evaluate_latency(300.0, 300.0)["passed"] is False
    assert gates.evaluate_latency(861.409, 300.0)["passed"] is False


def test_latency_gate_not_measurable_without_timing():
    outcome = gates.evaluate_latency(None, 300.0)
    assert outcome["passed"] is None
    assert "not_measurable" in outcome["detail"]


# --------------------------------------------------------------------------- #
# recall gates
# --------------------------------------------------------------------------- #


def test_recall_gate_citation_hits_and_misses():
    q = QUESTIONS["business-judgment-rule"]
    hit = gates.evaluate_required_hits(q["required_citation_ids"],
                                      {"bger_4A_626_2013"}, "citation", True)
    assert hit["passed"] is True
    miss = gates.evaluate_required_hits(q["required_citation_ids"],
                                       {"some_other_id"}, "citation", True)
    assert miss["passed"] is False
    assert "bger_4A_219_2015" in miss["measured"]["missing"]


def test_recall_gate_retrieval_requires_artifact_id_list():
    q = QUESTIONS["petty-theft-dismissal"]
    ok = gates.evaluate_required_hits(q["required_retrieval_ids"],
                                      {"bger_4A_228_2015", "x"}, "retrieval", True)
    assert ok["passed"] is True
    nm = gates.evaluate_required_hits(q["required_retrieval_ids"], set(),
                                      "retrieval", False)
    assert nm["passed"] is None  # slim artifact: honestly not measurable


# --------------------------------------------------------------------------- #
# structural gates (single bundle)
# --------------------------------------------------------------------------- #


def _bundle(decisions, cited):
    return {
        "answer": {"status": "ready", "cited_decision_ids": cited, "prose": "x" * 200},
        "decisions": decisions,
        "provenance": {"phase": "complete", "latency_seconds_total": 10.0},
    }


def _decision(i, **kw):
    d = {"decision_id": f"d{i}", "canonical_url": f"https://mcp.opencaselaw.ch/entscheid/d{i}",
         "language": "fr", "cluster_id": 0, "x": 0.1, "y": 0.2, "is_outlier": False}
    d.update(kw)
    return d


def test_structural_bundle_clean_passes():
    checks = gates.bundle_structural(_bundle([_decision(1), _decision(2)], ["d1"]))
    assert all(checks[k] for k in ("bundle_nonempty", "duplicate_free",
                                   "source_urls_valid", "answer_citations_constrained",
                                   "counter_classifications_supported"))


def test_structural_bundle_duplicates_fail():
    checks = gates.bundle_structural(_bundle([_decision(1), _decision(1)], []))
    assert checks["duplicate_free"] is False


def test_structural_bad_source_url_fails():
    checks = gates.bundle_structural(
        _bundle([_decision(1, canonical_url="https://example.com/d1")], []))
    assert checks["source_urls_valid"] is False
    assert checks["bad_source_ids"] == ["d1"]


def test_structural_invented_citation_fails():
    checks = gates.bundle_structural(_bundle([_decision(1)], ["invented"]))
    assert checks["answer_citations_constrained"] is False


def test_structural_counter_without_evidence_fails():
    checks = gates.bundle_structural(
        _bundle([_decision(1, counter_status="contrary_or_exception")], []))
    assert checks["counter_classifications_supported"] is False


# --------------------------------------------------------------------------- #
# multilingual robustness
# --------------------------------------------------------------------------- #


def test_multilingual_coverage_per_bundle():
    bundle = {
        "query": "Wann endet ein Mietvertrag?",
        "decisions": [
            _decision(1, language="de"), _decision(2, language="de"),
            _decision(3, language="fr"), _decision(4, language="it"),
        ],
    }
    out = gates.evaluate_multilingual_coverage([dict(bundle, _label="de-tenancy")])
    assert out[0]["passed"] is True


def test_multilingual_coverage_rejects_single_language_bundle():
    bundle = {
        "query": "Wann endet ein Mietvertrag?",
        "decisions": [_decision(1, language="de"), _decision(2, language="de")],
    }
    out = gates.evaluate_multilingual_coverage([dict(bundle, _label="de-tenancy")])
    assert out[0]["passed"] is False


# --------------------------------------------------------------------------- #
# frozen spec loads through the public loader (used by the runner)
# --------------------------------------------------------------------------- #


def test_loader_round_trip():
    spec = frozen.load_frozen()
    assert spec["schema"] == "lex-frozen-reality-benchmark/1"
    assert len(spec["questions"]) == 4
