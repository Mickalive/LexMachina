"""Answer-completeness contract tests (product/query/answer_contract.py).

These tests pin the three properties that make the fill trustworthy:

1. it detects exactly what the durable truth gate detects (same normaliser);
2. it only ever appends a verbatim sentence that exists in the result bundle,
   cited with its own decision id;
3. it refuses to invent anything when no retrieved source states the condition.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))

from query.answer_contract import (  # noqa: E402
    CONTRACTS,
    ensure_coverage,
    match_contract,
    missing_elements,
    norm,
)
from reality_check import evaluate, truth_gates, GateFailure  # noqa: E402

RENT_QUESTION = (
    "Sous quelles conditions un bailleur peut-il résilier un bail d'habitation "
    "pour retard dans le paiement du loyer selon le droit suisse, et quelles "
    "exceptions ou limites jurisprudentielles existent ?"
)

# Verbatim sentence already observed in the retrieved rent-arrears bundle
# (results/product/query_cache, docket ERZ 2010 25 / TF 4C.248/2002 style).
SOURCE_SENTENCE = (
    "Nach Art. 257d Abs. 2 OR kann der Vermieter bei Wohn- und Geschäftsräumen "
    "mit einer Frist von mindestens 30 Tagen auf Ende eines Monats kündigen, "
    "wenn der Mieter innert der gesetzten Frist nicht bezahlt."
)

PARTIAL_ANSWER = (
    "Le bailleur doit adresser une mise en demeure écrite fixant un délai d'au "
    "moins 30 jours sous menace de résiliation; la résiliation prononcée de "
    "mauvaise foi constitue un abus de droit (art. 257d CO)."
)


def _bundle(prose: str, *, with_source: bool = True) -> dict:
    decisions = [
        {
            "decision_id": "gr_gerichte_ERZ 2010 25",
            "court": "gr_gerichte",
            "language": "de",
            "rank": 8,
            "snippet": SOURCE_SENTENCE if with_source else "kein Treffer",
            "citation": "GR ERZ 2010 25",
            "x": 0.0,
            "y": 0.0,
        },
        {
            "decision_id": "bge_BGE_117_II_415",
            "court": "bge",
            "language": "de",
            "rank": 1,
            "snippet": "Auch die übrigen Voraussetzungen sind erfüllt.",
            "citation": "BGE 117 II 415",
            "x": 0.0,
            "y": 0.0,
        },
    ]
    return {
        "bundle_version": "1.0",
        "query": RENT_QUESTION,
        "query_variants": [],
        "answer": {
            "prose": prose,
            "statements": [],
            "cited_decision_ids": ["bge_BGE_117_II_415"],
            "method": "generative_audit_llm_v2",
            "model": "opencode/test",
            "status": "ready",
        },
        "decisions": decisions,
        "clusters": [],
        "relations": [],
        "provenance": {},
    }


def test_contract_matches_the_rent_question_and_not_an_unrelated_one():
    assert match_contract(RENT_QUESTION)["topic"] == "rent-arrears-termination"
    assert match_contract("Comment former un recours au TC ?") is None


def test_missing_elements_are_detected_with_gate_normalisation():
    contract = match_contract(RENT_QUESTION)
    missing = {e["id"] for e in missing_elements(contract, PARTIAL_ANSWER)}
    assert missing == {"effective-dating-end-of-month"}
    # apostrophe/accent variants the durable gate accepts must count as present
    assert not missing_elements(contract, PARTIAL_ANSWER + " à la fin d'un mois.")


def test_fill_quotes_a_retrieved_decision_and_passes_the_truth_gate():
    bundle = _bundle(PARTIAL_ANSWER)
    report = ensure_coverage(bundle)
    assert report["changed"] is True
    assert report["missing_before"] == ["effective-dating-end-of-month"]
    assert report["fills"][0]["decision_id"] == "gr_gerichte_ERZ 2010 25"
    # verbatim, markup-free, cited with its own id
    assert SOURCE_SENTENCE in bundle["answer"]["prose"]
    assert "<mark>" not in bundle["answer"]["prose"]
    assert "gr_gerichte_ERZ 2010 25" in bundle["answer"]["cited_decision_ids"]
    assert set(bundle["answer"]["cited_decision_ids"]) <= {
        d["decision_id"] for d in bundle["decisions"]
    }
    truth_gates("rent-default", {"bundle": bundle})  # must not raise
    assert bundle["provenance"]["answer_coverage"]["unfilled"] == []


def test_fill_never_fabricates_when_no_source_states_the_condition():
    bundle = _bundle(PARTIAL_ANSWER, with_source=False)
    report = ensure_coverage(bundle)
    assert report["changed"] is False
    assert bundle["answer"]["prose"] == PARTIAL_ANSWER
    assert bundle["answer"]["cited_decision_ids"] == ["bge_BGE_117_II_415"]
    assert [u["element"] for u in report["unfilled"]] == ["effective-dating-end-of-month"]


def test_complete_answer_is_left_untouched():
    prose = (
        PARTIAL_ANSWER + " La résiliation prend effet à la fin du mois suivant "
        "l'expiration du délai (art. 257d al. 2 CO)."
    )
    bundle = _bundle(prose)
    report = ensure_coverage(bundle)
    assert report["changed"] is False
    assert report["missing_before"] == []
    assert bundle["answer"]["prose"] == prose


def test_all_contract_elements_are_detectable_by_the_real_truth_gates():
    """Every contract element id is a documented, gate-visible condition."""
    rent = match_contract(RENT_QUESTION)
    assert [e["id"] for e in rent["elements"]] == [
        "notice-period-30-days",
        "effective-dating-end-of-month",
        "good-faith-limitation",
    ]
    assert len(CONTRACTS) == 4


def test_filled_answer_also_survives_full_gate_evaluation():
    bundle = _bundle(PARTIAL_ANSWER)
    ensure_coverage(bundle)
    answer = bundle["answer"]
    report = {
        "validation_errors": [],
        "bundle": {
            "decisions": bundle["decisions"],
            "answer": answer,
            "provenance": {
                "generative_audit": {
                    "provider_error": None,
                    "adversarial": {
                        "method": "independent_llm_adversarial_v2",
                        "model": "opencode/test",
                        "error": None,
                    },
                }
            },
        },
    }
    gates = {g["gate"]: g for g in evaluate("rent-default", report)}
    assert gates["structural"]["passed"], gates
    assert gates["truth::rent-default"]["passed"], gates
