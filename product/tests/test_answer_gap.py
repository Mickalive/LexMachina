"""The zero-citation answer contract and the query-concept coverage it rests on.

What is pinned here
-------------------
Direction v52 backlog item (3) ships a three-question gate packet whose bundles
are re-verified for admissibility at run time.  One pre-registered question,
``de-kapitalverletzung``, was blocked with ``answer_cites_nothing`` and the
previous cycle's hypothesis was "the answer generator must cite retrieved
decision ids".

These tests freeze the *measured* reason instead, so the hypothesis cannot be
re-introduced by accident:

1. concept extraction is deterministic, multilingual and drops function words;
2. coverage is measured on the rows the product actually retrieved, and a
   concept with no supporting row is reported as uncovered - never as "the
   generator forgot to cite";
3. when the model cites, the contract does not run and the answer is untouched;
4. when the model declines, the product surfaces verbatim, cited quotes for the
   concepts the corpus does cover, and names the ones it does not;
5. every quote is really in the cited decision's own text, every citation is a
   decision on the map, and the bundle contract still validates;
6. when nothing in the bundle states any concept of the question, the contract
   refuses to run and the bundle stays blocked - an invented citation is worse
   than an uncited answer;
7. determinism: the same bundle yields byte-identical output;
8. the real shipped artifact from run 38799024807 is used as a regression
   fixture: it was blocked, and after the contract it is admissible, with the
   shortfall still disclosed.

Everything runs offline against committed artifacts; no network, no model.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT))

from product.query import gate_admissibility as ga  # noqa: E402
from product.query.answer_gap import detect_language, ensure_cited_answer  # noqa: E402
from product.query.bundle import build_bundle, validate_bundle  # noqa: E402
from product.query.concept_coverage import (  # noqa: E402
    concept_prefix, content_concepts, coverage_report, rows_for_concept,
)

DE_QUESTION = ("Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung: "
               "wie weit geht der aktive Eingriff, und welche Entscheidungen begrenzen ihn "
               "gegenüber einer blossen Überwachungspflicht?")

FR_QUESTION = ("Résiliation du bail pour défaut d'entretien du bailleur : jusqu'où va la "
               "jurisprudence, et quelles décisions distinguent le défaut d'entretien grave "
               "de la simple négligence ?")

IT_QUESTION = ("Responsabilità penale dell'impresa: criteri di imputazione del deficit di "
               "organizzazione e concorso della persona giuridica")

SHIPPED_DE_BUNDLE = (ROOT / "results" / "product" / "gate_packet" / "38799024807" / "questions"
                     / "de-kapitalverletzung.bundle.json")


def _decision(idx: int, *, regeste: str = "", full_text: str = "", rank: int | None = None,
              language: str = "de", court: str = "bger") -> dict:
    return {
        "decision_id": f"d{idx:03d}",
        "rank": idx if rank is None else rank,
        "court": court,
        "language": language,
        "citation": f"CITE-{idx}",
        "canonical_url": f"https://mcp.opencaselaw.ch/decisions/d{idx:03d}",
        "source_url": f"https://mcp.opencaselaw.ch/decisions/d{idx:03d}",
        "score": 1.0 / idx,
        "cluster_id": 0,
        "x": 0.1 * idx,
        "y": 0.2 * idx,
        "is_outlier": False,
        "counter_status": "none",
        "provenance": {},
        "snippet": (regeste or full_text or f"row {idx}")[:400],
        "regeste": regeste,
        "full_text": full_text,
        "title": f"Entscheid {idx}",
    }


def _bundle(*, query: str = DE_QUESTION, decisions=None, answer=None) -> dict:
    decisions = decisions if decisions is not None else [
        _decision(1, regeste="Regeste Art. 328 OR; Fürsorgepflicht des Arbeitgebers. "
                             "Der Arbeitgeber verletzt seine Fürsorgepflicht, wenn er das "
                             "zum Schutze der Gesundheit des Arbeitnehmers Notwendige nicht "
                             "vorkehrt, obwohl dies nach dem Stand der Technik möglich ist."),
        _decision(2, regeste="Regeste Art. 336 OR; missbräuchliche Kündigung; Fürsorgepflicht "
                             "des Arbeitgebers. Wer einem Arbeitnehmer nach 44 klaglosen "
                             "Dienstjahren kuendigen will, muss alle zumutbaren Vorkehren "
                             "treffen und die Verhaeltnisse genau kennen."),
    ]
    answer = answer if answer is not None else {
        "prose": "None of the retrieved decisions address the question.",
        "statements": [],
        "cited_decision_ids": [],
        "method": "generative_audit_llm_v2",
        "model": "opencode/test-free-model",
        "status": "ready",
    }
    return build_bundle(query=query, query_variants=[], answer=answer, decisions=decisions,
                        clusters=[{"cluster_id": 0, "label": "test", "member_ids": [d["decision_id"] for d in decisions]}],
                        relations=[], provenance={})


# --------------------------------------------------------------------------- #
# concept extraction
# --------------------------------------------------------------------------- #
def test_content_concepts_drops_function_words_and_keeps_order():
    concepts = content_concepts(DE_QUESTION)
    assert "fursorgepflicht" in concepts and "kapitalverletzung" in concepts
    assert "uberwachungspflicht" in concepts
    for junk in ("und", "der", "die", "welche", "gegenuber", "gegenüber", "wie", "weit"):
        assert junk not in concepts
    assert concepts == content_concepts(DE_QUESTION)  # deterministic


def test_content_concepts_is_multilingual():
    assert {"defaut", "entretien", "bailleur"} <= set(content_concepts(FR_QUESTION))
    assert {"responsabilita", "impresa", "deficit"} <= set(content_concepts(IT_QUESTION))
    assert "della" not in content_concepts(IT_QUESTION)


def test_concept_prefix_is_compound_tolerant():
    # German compounds: the prefix must match the declined/inflected forms.
    assert "kapitalverl" in "kapitalverletzungen"
    # NFKD + stripped combining marks is what turns "fürsorgepflicht" into
    # "fursorgepflicht"; the prefix then matches the inflected forms.
    assert concept_prefix("fursorgepflicht") in "die fursorgepflichten des arbeitgebers"


def test_coverage_report_measures_rows_not_claims():
    decisions = [_decision(1, regeste="Fürsorgepflicht des Arbeitgebers im Kontext der Gesundheit."),
                 _decision(2, regeste="Weitere Fürsorgepflicht des Arbeitgebers."),
                 _decision(3, regeste="Kapitalverletzung und Konkursrecht." * 3)]
    report = coverage_report(DE_QUESTION, decisions)
    assert report["rows_per_concept"]["fursorgepflicht"] == 2
    assert report["rows_per_concept"]["kapitalverletzung"] == 1
    assert "kapitalverletzung" in report["under_covered"]  # 1 row < MIN_ROWS_PER_CONCEPT
    assert report["concepts"] and report["method"] == "query_concept_coverage_v1"


def test_rows_for_concept_is_rank_ordered_and_bounded():
    decisions = [_decision(1, regeste="nichts"), _decision(2, regeste="Kapitalverletzug")]
    rows = rows_for_concept("kapitalverletzung", decisions, limit=5)
    assert [d["decision_id"] for d in rows] == ["d002"]


# --------------------------------------------------------------------------- #
# the contract
# --------------------------------------------------------------------------- #
def test_contract_does_not_touch_an_answer_that_cites():
    bundle = _bundle(answer={
        "prose": "Die Fürsorgepflicht folgt aus Art. 328 OR [d001].",
        "statements": [], "cited_decision_ids": ["d001"],
        "method": "generative_audit_llm_v2", "model": "m", "status": "ready",
    })
    before = copy.deepcopy(bundle["answer"])
    report = ensure_cited_answer(bundle)
    assert report["fired"] is False and report["reason"] == "answer already cites retrieved decisions"
    assert bundle["answer"] == before
    assert bundle["provenance"]["answer_gap_contract"]["fired"] is False


def test_contract_quotes_verbatim_cites_and_names_the_gap():
    bundle = _bundle()
    report = ensure_cited_answer(bundle)
    assert report["fired"] is True
    answer = bundle["answer"]
    assert answer["status"] == "degraded"
    assert answer["method"] == "concept_coverage_extractive_v1"
    assert answer["cited_decision_ids"], "a grounded fallback answer must cite something"
    assert validate_bundle(bundle) == []

    for statement in answer["statements"]:
        row = next(d for d in bundle["decisions"] if d["decision_id"] == statement["decision_id"])
        source = " ".join(str(row.get(k) or "") for k in ("full_text", "regeste", "snippet", "title"))
        assert statement["text"][:60] in " ".join(source.split()), \
            "a quote must be verbatim text of the decision it is attributed to"
        assert statement["decision_id"] in answer["cited_decision_ids"]
    prose = answer["prose"]
    assert "kapitalverletzung" in prose  # the uncovered concept is named, not hidden
    assert bundle["provenance"]["answer_gap_contract"]["fired"] is True
    assert {"kapitalverletzung", "uberwachungspflicht"} <= set(report["under_covered"])


def test_contract_preserves_the_models_own_assessment():
    bundle = _bundle()
    original = bundle["answer"]["prose"]
    ensure_cited_answer(bundle)
    answer = bundle["answer"]
    assert answer["superseded_prose"] == original
    assert original in answer["prose"]
    assert answer["model"] == "opencode/test-free-model"  # the model is not rewritten away


def test_contract_refuses_when_no_row_states_any_concept():
    bundle = _bundle(decisions=[
        _decision(1, regeste="Vollmilchkuhvertrag im Bergtal"),
        _decision(2, regeste="Zollrechtliche Abfertigung von Lastwagen"),
    ])
    report = ensure_cited_answer(bundle)
    assert report["fired"] is False
    assert "no retrieved decision states a concept" in report["reason"]
    assert bundle["answer"]["cited_decision_ids"] == []
    verdict = ga.verify_bundle(bundle, question={"qid": "x", "language": "de"},
                               min_decisions=1)
    assert not verdict["admissible"]
    assert "answer_cites_nothing" in {f["code"] for f in verdict["findings"]}


def test_contract_is_deterministic():
    first = ensure_cited_answer(_bundle())
    second = ensure_cited_answer(_bundle())
    assert first == second


def test_contract_answers_in_the_language_of_the_question():
    assert detect_language(DE_QUESTION, [{"language": "fr"}]) == "de"
    assert detect_language(FR_QUESTION, [{"language": "de"}]) == "fr"
    assert detect_language(IT_QUESTION, [{"language": "fr"}]) == "it"
    fr_text = ("Le bailleur a l'obligation d'entreprendre les travaux d'entretien destines a "
               "remedier aux defauts de la chose louee, selon la jurisprudence federale : le "
               "defaut doit etre grave, une simple negligence ne suffit pas.")
    fr = _bundle(query=FR_QUESTION,
                 decisions=[_decision(1, language="fr", regeste=fr_text),
                            _decision(2, language="fr", rank=2, regeste=fr_text)],
                 answer={"prose": "aucune citation", "statements": [], "cited_decision_ids": [],
                         "method": "generative_audit_llm_v2", "model": "m", "status": "ready"})
    ensure_cited_answer(fr)
    assert fr["answer"]["prose"].startswith("Couverture de la question")
    assert fr["answer"]["cited_decision_ids"] == ["d001"]


def test_gate_admissibility_discloses_the_uncovered_concepts():
    bundle = _bundle()
    verdict = ga.verify_bundle(bundle, question={"qid": "de", "language": "de"},
                               min_decisions=1)
    finding = next(f for f in verdict["findings"] if f["code"] == "answer_cites_nothing")
    assert finding["coverage_under_covered"], "a blocked answer must say which concept has no support"
    assert finding["gap_contract_fired"] is False
    assert verdict["measured"]["query_concepts_under_covered"] == finding["coverage_under_covered"]
    ensure_cited_answer(bundle)
    after = ga.verify_bundle(bundle, question={"qid": "de", "language": "de"}, min_decisions=1)
    assert after["admissible"], [f["code"] for f in after["findings"] if f["severity"] == "blocking"]
    assert after["measured"]["answer_gap_contract_fired"] is True
    assert after["measured"]["query_concepts_under_covered"]


def test_owner_card_discloses_the_coverage_boundary():
    import gate_packet as gp

    bundle = _bundle()
    ensure_cited_answer(bundle)
    verdict = ga.verify_bundle(bundle, question={"qid": "de", "language": "de"}, min_decisions=1)
    card = gp.owner_card(
        {
            "packet_id": "gate-packet-test", "mode": "live", "checked_at": "2026-01-01T00:00:00Z",
            "questions": [{
                "qid": "de-kapitalverletzung", "language": "de", "question": DE_QUESTION,
                "admissible": verdict["admissible"], "verdict": verdict,
                "bundle_path": "/tmp/opencode/x.bundle.json", "deep_link": "http://127.0.0.1:8791/?q=x",
            }],
        },
        base_url="http://127.0.0.1:8791", top_n=150,
    )
    assert "supports NO decision for these concepts" in card
    assert "kapitalverletzung" in card
    assert "concept_coverage_extractive_v1" in card
    assert "human_gate_ready is set by the director" in card


# --------------------------------------------------------------------------- #
# the real shipped artifact: run 38799024807, question de-kapitalverletzung
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not SHIPPED_DE_BUNDLE.exists(),
                    reason="the shipped gate-packet bundle is not in this checkout")
def test_shipped_blocked_bundle_becomes_admissible_with_the_shortfall_stated():
    shipped = json.loads(SHIPPED_DE_BUNDLE.read_text(encoding="utf-8"))
    question = {"qid": "de-kapitalverletzung", "language": "de"}

    before = ga.verify_bundle(copy.deepcopy(shipped), question=question)
    assert not before["admissible"]
    assert "answer_cites_nothing" in {f["code"] for f in before["findings"]}
    assert before["measured"]["query_concept_rows"]["kapitalverletzung"] == 0, \
        "the recorded reason must be the corpus, not the generator"
    assert before["measured"]["query_concept_rows"]["fursorgepflicht"] > 0

    report = ensure_cited_answer(shipped)
    assert report["fired"] is True and report["n_quotes"] >= 1
    after = ga.verify_bundle(shipped, question=question)
    assert after["admissible"], [f["code"] for f in after["findings"] if f["severity"] == "blocking"]
    assert after["measured"]["answer_cited"] >= 1
    assert "kapitalverletzung" in after["measured"]["query_concepts_under_covered"]
    assert after["measured"]["answer_gap_contract_fired"] is True

    # The two halves of the contract: cited where the corpus speaks, silent
    # about where it does not, and no invented authority in between.
    ids = {d["decision_id"] for d in shipped["decisions"]}
    assert set(shipped["answer"]["cited_decision_ids"]) <= ids
    for statement in shipped["answer"]["statements"]:
        row = next(d for d in shipped["decisions"] if d["decision_id"] == statement["decision_id"])
        haystack = " ".join(" ".join(str(row.get(k) or "") for k in
                                    ("full_text", "regeste", "snippet", "title")).split())
        assert statement["text"].rstrip() in haystack


# --------------------------------------------------------------------------- #
# counter-authority provenance (adopted from the accepted frontier verdict)
# --------------------------------------------------------------------------- #
def test_counter_rows_without_their_own_channel_are_disclosed():
    """frontier-adversarial-discoverability (accepted, cycle 38794235870, FAIL).

    On the 227-row bundle that team measured counter yield 1.3% against a 2%
    threshold and every counter row coming from the INITIAL retrieval channels.
    Gate question 3 asks whether the map increased confidence that contrary
    authority had not been hidden; without this disclosure the jurist judges
    something the artifact cannot show.  Disclosure only, never a refusal.
    """
    decisions = [_decision(i, regeste="Poursorgepflicht du bailleur." if i < 6 else "Autre sujet.")
                 for i in range(1, 11)]
    decisions[0]["counter_status"] = "candidate-limiting"
    decisions[1]["counter_status"] = "candidate-contrary"
    bundle = _bundle(decisions=decisions, answer={
        "prose": "Réponse fondée sur les décisions citées [d001].",
        "statements": [], "cited_decision_ids": ["d001"],
        "method": "generative_audit_llm_v2", "model": "m", "status": "ready",
    })
    verdict = ga.verify_bundle(bundle, question={"qid": "de", "language": "de"},
                               min_decisions=1)
    assert verdict["admissible"]
    assert verdict["measured"]["n_counter_authorities"] == 2
    assert verdict["measured"]["counter_rows_from_citation_channels"] == 0
    assert verdict["measured"]["counter_yield"] == 0.2
    finding = next(f for f in verdict["findings"]
                   if f["code"] == "counter_authority_has_no_own_channel")
    assert finding["severity"] == "warning"
    assert "cannot surface contrary authority" in finding["detail"]


def test_counter_rows_reached_through_a_citation_channel_are_not_disclosed():
    decisions = [_decision(i, regeste="Autre sujet.") for i in range(1, 5)]
    decisions[0]["counter_status"] = "candidate-limiting"
    decisions[0]["channels"] = ["citation.incoming"]
    decisions[0]["detail_status"] = "pending"
    bundle = _bundle(decisions=decisions, answer={
        "prose": "Antwort [d001].", "statements": [], "cited_decision_ids": ["d001"],
        "method": "generative_audit_llm_v2", "model": "m", "status": "ready",
    })
    verdict = ga.verify_bundle(bundle, question={"qid": "de", "language": "de"},
                               min_decisions=1)
    assert verdict["measured"]["counter_rows_from_citation_channels"] == 1
    assert "counter_authority_has_no_own_channel" not in {f["code"] for f in verdict["findings"]}
