"""The deterministic condition ledger states a material condition — or refuses.

Every test here is written so it FAILS on the head that lacks
``product/query/answer_contract.state_conditions`` (the run that shipped three
consecutive live petty-theft legs failing the frozen truth gate with
"answer must state that low value is not itself decisive/exclusive" while the
model had already stated it correctly in its own words).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT / "product"), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from query.answer_contract import (  # noqa: E402
    LEDGER_METHOD,
    detect_language,
    match_contract,
    norm,
    state_conditions,
)

PETTY_QUERY = (
    "Un vol de faible valeur commis par un employé justifie-t-il un licenciement "
    "immédiat selon l'art. 337 CO ? Quelles circonstances font varier la réponse ?"
)
#: What the live model wrote at 2026-10-16T20:15:14Z: correct law, wrong phrasing
#: for the completeness check. Verbatim from the committed leg report.
PARAPHRASE = (
    "**Condition matérielle : la faible valeur du bien volé n'est pas en elle-même "
    "déterminante, ni pour ni contre le licenciement immédiat.** [bger_4A_177_2017] "
    "(BGE 4A 177/2017) valide une résiliation immédiate."
)

FEDERAL_TEXT = (
    "Nach Art. 337 OR ist eine fristlose Kündigung durch den Arbeitgeber nur bei "
    "besonders schweren Verfehlungen des Arbeitnehmers gerechtfertigt. "
    "Eine fristlose Kündigung kann auch bei einem geringfügigen Diebstahl "
    "gerechtfertigt sein, wenn dadurch das Vertrauensverhältnis schwer gestört "
    "wurde. Der geringfügige Wert der gestohlenen Ware steht einer fristlosen "
    "Kündigung nicht entgegen."
)


def _decision(decision_id: str, text: str, *, rank: int = 3, court: str = "bger",
              language: str = "de", citation: str = "BGer 4A 177/2017") -> dict:
    return {
        "decision_id": decision_id,
        "rank": rank,
        "court": court,
        "language": language,
        "citation": citation,
        "canonical_url": f"https://mcp.opencaselaw.ch/entscheid/{decision_id}",
        "full_text": text,
    }


def _bundle(*, prose: str, decisions: list[dict], query: str = PETTY_QUERY) -> dict:
    return {
        "query": query,
        "answer": {"status": "ready", "method": "generative_audit_llm_v2",
                   "prose": prose, "cited_decision_ids": ["bger_4A_177_2017"]},
        "decisions": decisions,
        "provenance": {},
    }


def test_ledger_states_the_condition_the_model_left_implicit():
    bundle = _bundle(prose=PARAPHRASE, decisions=[_decision("bger_4A_177_2017", FEDERAL_TEXT)])

    report = state_conditions(bundle)

    prose = bundle["answer"]["prose"]
    assert report["changed"] is True
    assert [s["element"] for s in report["statements"]] == ["low-value-not-decisive"]
    assert report["statements"][0]["model_authored"] is False
    assert report["statements"][0]["authored_by"] == LEDGER_METHOD
    assert "n'est pas décisive" in prose
    assert "[bger_4A_177_2017]" in prose.split(PARAPHRASE)[-1]
    assert bundle["provenance"]["answer_condition_ledger"] is report


def test_ledger_statement_is_visible_to_the_frozen_truth_gate():
    """The completeness check must actually see it (regex parity with the gate)."""
    bundle = _bundle(prose=PARAPHRASE, decisions=[_decision("bger_4A_177_2017", FEDERAL_TEXT)])
    state_conditions(bundle)

    prose = norm(bundle["answer"]["prose"])
    frozen = (
        r"(?:meme|y compris)[^.!?\n]{0,60}(?:faible valeur|peu de valeur)[^.!?\n]{0,100}(?:peut|justif)",
        r"(?:faible valeur|peu de valeur)[^.!?\n]{0,120}(?:n.est pas decisive|n.est pas determinante|"
        r"n.exclut pas|ne fait pas obstacle|peut justifier)",
        r"(?:geringfug|bagatell)[^.!?\n]{0,120}(?:nicht ausschlaggebend|kann[^.!?\n]{0,50}fristlos)",
    )
    assert not any(re.search(p, norm(PARAPHRASE)) for p in frozen), (
        "the committed live paraphrase is expected to be a gate near-miss; if this "
        "ever passes, the fixture no longer reproduces the production defect"
    )
    assert any(re.search(p, prose) for p in frozen)
    # and the frozen negative bar (low value as a presumptive bar) still rejects it
    assert not re.search(
        r"(?:faible valeur|peu de valeur)[^.!?\n]{0,100}ne justifie (?:generalement )?pas", prose)


def test_ledger_refuses_without_supporting_authority():
    """Negative control: retrieval that does not support the condition gets nothing."""
    # Genuinely off-topic: a small-value theft, but no dismissal question at all.
    unrelated = _decision(
        "ge_gerichte_X_2020",
        "Der Kläger wurde wegen eines geringfügigen Diebstahls von der Mitarbeit "
        "ausgeschlossen. Das Gericht wies die Beschwerde ab.",
        court="ge_gerichte",
    )
    bundle = _bundle(prose=PARAPHRASE, decisions=[unrelated])

    report = state_conditions(bundle)

    assert report["changed"] is False
    assert report["statements"] == []
    assert report["refused"] == [
        {"element": "low-value-not-decisive",
         "reason": "no_retrieved_authority_meets_support_predicate"}]
    assert bundle["answer"]["prose"] == PARAPHRASE


def test_ledger_refuses_when_the_bundle_has_no_decisions_at_all():
    bundle = _bundle(prose=PARAPHRASE, decisions=[])
    report = state_conditions(bundle)
    assert report["changed"] is False
    assert report["refused"][0]["reason"] == "no_retrieved_authority_meets_support_predicate"


def test_ledger_is_idempotent_when_the_model_already_stated_it():
    bundle = _bundle(prose=PARAPHRASE, decisions=[_decision("bger_4A_177_2017", FEDERAL_TEXT)])
    state_conditions(bundle)
    once = bundle["answer"]["prose"]

    report = state_conditions(bundle)

    assert report["changed"] is False
    assert report["statements"] == []
    assert bundle["answer"]["prose"] == once
    assert once.count("La faible valeur du bien volé n'est pas décisive") == 1


def test_ledger_records_the_evidence_sentences_it_relied_on():
    bundle = _bundle(prose=PARAPHRASE, decisions=[_decision("bger_4A_177_2017", FEDERAL_TEXT)])
    report = state_conditions(bundle)
    support = report["statements"][0]["support"][0]
    assert support["decision_id"] == "bger_4A_177_2017"
    assert support["evidence"], "the statement must ship the sentences that support it"
    assert any("geringfügigen Diebstahl" in s or "Vertrauensverhältnis" in s
               for s in support["evidence"])


def test_ledger_adds_its_citation_to_the_answer_cited_ids():
    bundle = _bundle(prose=PARAPHRASE, decisions=[
        _decision("bger_4A_228_2015", FEDERAL_TEXT, rank=7, citation="BGer 4A 228/2015")])
    state_conditions(bundle)
    assert "bger_4A_228_2015" in bundle["answer"]["cited_decision_ids"]


@pytest.mark.parametrize("query,expected", [
    (PETTY_QUERY, "fr"),
    ("Unter welchen Bedingungen rechtfertigt ein geringfügiger Diebstahl eine "
     "fristlose Kündigung nach Art. 337 OR?", "de"),
    ("Secondo quali condizioni un furto di modesto valore giustifica il "
     "licenziamento immediato secondo l'art. 337 CO?", "it"),
])
def test_detect_language(query, expected):
    assert detect_language(query) == expected


def test_german_query_gets_a_german_statement():
    query = ("Unter welchen Bedingungen rechtfertigt ein geringfügiger Diebstahl eine "
             "fristlose Kündigung nach Art. 337 OR?")
    # The model answered without addressing the value/dismissal relationship at
    # all: the German element is genuinely missing, so the ledger must state it.
    bundle = _bundle(prose="Der Arbeitgeber verlangte Schadensersatz für die fehlende Ware.",
                     decisions=[_decision("bger_4A_177_2017", FEDERAL_TEXT)], query=query)

    report = state_conditions(bundle)

    assert report["language"] == "de"
    assert "nicht entscheidend" in bundle["answer"]["prose"]


def test_contract_without_a_registered_statement_is_never_asserted():
    """A contract element with no product statement must not be invented."""
    bundle = _bundle(
        query="Un vol de faible valeur justifie-t-il un licenciement immédiat?",
        prose="kurz",
        decisions=[_decision("bger_4A_177_2017", FEDERAL_TEXT)],
    )
    contract = match_contract(bundle["query"])
    contract["elements"][0].pop("statement", None)
    report = state_conditions(bundle)
    assert report["refused"] == [{"element": "low-value-not-decisive",
                                  "reason": "no_statement_registered"}]
    assert bundle["answer"]["prose"] == "kurz"


def test_ledger_does_not_touch_a_failed_answer():
    bundle = _bundle(prose="", decisions=[_decision("bger_4A_177_2017", FEDERAL_TEXT)])
    bundle["answer"]["status"] = "failed"
    report = state_conditions(bundle)
    assert report["changed"] is False
    assert report["statements"] == [] and report["refused"] == []