"""Answer-completeness contract tests (product/query/answer_contract.py).

These tests pin the properties that make the contract trustworthy:

1. it detects exactly what the durable truth gate detects (same normaliser);
2. it only ever appends a verbatim sentence that exists in the result bundle,
   cited with its own decision id;
3. it refuses to invent anything when no retrieved source states the condition;
4. it is registered against the frozen reality-check question matrix itself
   (``reality_check.LEGS``), not against look-alike question strings;
5. contract-guided generation (``product/query/contract_guided.py``) is purely
   additive to the accepted Frontier prompt and carries legal labels, never
   gate detection patterns.
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
from query.contract_guided import (  # noqa: E402
    BLOCK_MARKER,
    build_provider,
    condition_lines,
    material_conditions,
)
from reality_check import LEGS, evaluate, truth_gates, GateFailure  # noqa: E402

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
    # 2026-10-16 (run 38961254857): the joint Art. 257d(2) pair is a third,
    # separate gap — PARTIAL_ANSWER states the 30-day period and the month-end
    # effect in DIFFERENT sentences, which is what the durable rent gate
    # rejects (its patterns cannot cross a sentence boundary).
    assert missing == {"effective-dating-end-of-month", "notice-and-month-end"}
    # apostrophe/accent variants the durable gate accepts must count as present
    assert not missing_elements(contract, PARTIAL_ANSWER + " à la fin d'un mois.")


def test_fill_quotes_a_retrieved_decision_and_passes_the_truth_gate():
    bundle = _bundle(PARTIAL_ANSWER)
    report = ensure_coverage(bundle)
    assert report["changed"] is True
    assert report["missing_before"] == ["effective-dating-end-of-month", "notice-and-month-end"]
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
    assert [u["element"] for u in report["unfilled"]] == ["effective-dating-end-of-month",
                                                         "notice-and-month-end"]


def test_complete_answer_is_left_untouched():
    # The pair must live in ONE sentence: that is what the durable gate reads.
    prose = (
        PARTIAL_ANSWER + " Le délai de congé est de 30 jours et la résiliation prend "
        "effet à la fin du mois (art. 257d al. 2 CO)."
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
        "notice-and-month-end",
        "good-faith-limitation",
    ]
    assert len(CONTRACTS) == 4


# The frozen leg question itself (reality_check.LEGS), never a paraphrase: the
# contract must be proven to match the exact string the durable workflow runs,
# not a look-alike the test invented.
PETTY_QUESTION = LEGS["petty-theft-dismissal"]

# Bare phrase present, nuance absent: two consecutive live answers
# (results/product/reality_check/petty-theft-dismissal_live_20261016T184421Z.json
# and ..._193340Z.json) phrased the nuance as "la réponse dépend des
# circonstances, non du montant seul" — substantively correct, but the
# material condition (low value is not itself decisive) is not stated.
PETTY_BARE_PHRASE = (
    "Le vol de faible valeur peut fonder une résiliation immédiate lorsque "
    "l'employé occupe une position de confiance (4A_177/2017)."
)

# The nuance stated in the gate-visible phrasing.
PETTY_WITH_NUANCE = (
    "Un vol de faible valeur n'est pas décisif en soi : il peut justifier une "
    "résiliation immédiate selon les circonstances (4A_177/2017)."
)


def _petty_bundle(prose: str, *, source: str) -> dict:
    decisions = [
        {
            "decision_id": "bger_4A_177_2017",
            "court": "bger",
            "language": "de",
            "rank": 1,
            "snippet": source,
            "citation": "4A_177/2017",
            "x": 0.0,
            "y": 0.0,
        },
    ]
    return {
        "bundle_version": "1.0",
        "query": PETTY_QUESTION,
        "query_variants": [],
        "answer": {
            "prose": prose,
            "statements": [],
            "cited_decision_ids": ["bger_4A_177_2017"],
            "method": "generative_audit_llm_v2",
            "model": "opencode/test",
            "status": "ready",
        },
        "decisions": decisions,
        "clusters": [],
        "relations": [],
        "provenance": {},
    }


def test_petty_element_requires_the_nuance_not_the_bare_phrase():
    contract = match_contract(PETTY_QUESTION)
    assert contract["topic"] == "petty-theft-dismissal"
    missing = {e["id"] for e in missing_elements(contract, PETTY_BARE_PHRASE)}
    assert missing == {"low-value-not-decisive"}
    assert not missing_elements(contract, PETTY_WITH_NUANCE)


def test_petty_fill_refused_when_no_source_states_the_nuance():
    # The retrieved corpus holds the bare phrase (4A_177/2017's
    # "geringfügigen Diebstahl") but no sentence stating the non-decisiveness
    # nuance in gate-visible phrasing — the gap must be recorded, not filled.
    bundle = _petty_bundle(
        PETTY_BARE_PHRASE,
        source="Die fristlose Kündigung ist auch für einen geringfügigen Diebstahl "
               "gerechtfertigt, wenn das Vertrauensverhältnis zerstört ist.",
    )
    report = ensure_coverage(bundle)
    assert report["changed"] is False
    assert bundle["answer"]["prose"] == PETTY_BARE_PHRASE
    assert [u["element"] for u in report["unfilled"]] == ["low-value-not-decisive"]
    assert report["unfilled"][0]["reason"] == "no_retrieved_source_states_it"


def test_filled_answer_also_survives_full_gate_evaluation():
    bundle = _bundle(PARTIAL_ANSWER)
    ensure_coverage(bundle)
    answer = bundle["answer"]
    report = {
        "validation_errors": [],
        "total_seconds": 12.0,
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


# ---------------------------------------------------------------------------
# Contract-guided generation (product/query/contract_guided.py)
# ---------------------------------------------------------------------------

UNRELATED_QUESTION = "Comment former un recours au Tribunal fédéral ?"


def _bundle_for_prompt(query: str):
    from generative_audit.source_packing import Decision, DecisionBundle

    return DecisionBundle(
        query=query,
        decision_ids=["bger_4A_177_2017"],
        decisions=[
            Decision(
                decision_id="bger_4A_177_2017",
                title="4A_177/2017",
                text="Die fristlose Kündigung ist auch für einen geringfügigen "
                     "Diebstahl gerechtfertigt, wenn das Vertrauensverhältnis "
                     "zerstört ist.",
                metadata={"court": "bger", "rank": 1, "score": 1.0,
                          "evidence_hydrated": True},
            )
        ],
    )


def test_every_frozen_leg_question_has_registered_material_conditions():
    """The contract matrix covers the whole durable reality-check matrix.

    A frozen leg without a contract is a leg the product would happily ship
    incomplete, so the mapping is asserted against ``reality_check.LEGS``
    itself rather than against a hand-copied question string.
    """
    for slug, question in LEGS.items():
        conditions = material_conditions(question)
        assert conditions, f"frozen leg {slug} has no registered material conditions"
        block = condition_lines(question)
        assert BLOCK_MARKER in " ".join(block)
        assert all(c["label"] in " ".join(block) for c in conditions)


def test_no_contract_no_prompt_block():
    assert material_conditions(UNRELATED_QUESTION) == []
    assert condition_lines(UNRELATED_QUESTION) == []


def test_guided_prompt_is_the_parent_prompt_plus_the_block_only():
    """The block is additive: the accepted Frontier prompt is preserved verbatim.

    This is what keeps the three currently-green legs (rent-default,
    corporate-criminal-liability, business-judgment-rule) from regressing
    through a rewritten prompt: a leg whose query matches no contract gets the
    parent prompt byte-for-byte, and a leg that does match keeps every
    existing instruction and gains only the material-conditions block.
    """
    from generative_audit.provider import Provider

    petty = _bundle_for_prompt(PETTY_QUESTION)
    plain = Provider(fixture_mode=True).build_prompt(petty)
    guided = build_provider(PETTY_QUESTION, fixture_mode=True).build_prompt(petty)

    assert BLOCK_MARKER not in plain
    assert BLOCK_MARKER in guided
    assert guided.startswith(plain), "the accepted prompt must survive unchanged"
    assert "low value is not itself decisive" in guided
    assert "material conditions" in guided.lower()

    unrelated = _bundle_for_prompt(UNRELATED_QUESTION)
    unguided = build_provider(UNRELATED_QUESTION, fixture_mode=True)
    assert BLOCK_MARKER not in unguided.build_prompt(unrelated)
    assert unguided.build_prompt(unrelated) == Provider(fixture_mode=True).build_prompt(unrelated)


def test_guided_block_states_the_condition_not_the_gate_regex():
    """The prompt carries the legal label, never the gate's detection pattern.

    A gate strengthening must not silently re-author the prompt: nothing from
    ``reality_check.truth_gates`` may be copied into the block.
    """
    block = "\n".join(condition_lines(PETTY_QUESTION))
    assert "low value is not itself decisive for or against summary dismissal" in block
    for gate_token in ("n.est pas decisive", r"[^.!?\n]", "peut justifier", "geringfug"):
        assert gate_token not in block


def test_fixture_generation_still_returns_the_fixture_answer():
    """The seam must not disturb the offline deterministic path."""
    provider = build_provider(
        PETTY_QUESTION,
        fixture_mode=True,
        fixture_answer="Fixture grounded answer [bger_4A_177_2017]",
        fixture_cited_ids=["bger_4A_177_2017"],
    )
    result = provider.generate(_bundle_for_prompt(PETTY_QUESTION))
    assert result.error is None
    assert "Fixture grounded answer" in result.answer
    assert result.cited_decision_ids == ["bger_4A_177_2017"]
