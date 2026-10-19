"""Core Product integration of the accepted NLCS-1 concept-seeded retrieval arm.

Provenance of the component (accepted evidence, not this cycle's invention)
--------------------------------------------------------------------------
Accepted Frontier team ``frontier-concept-seed-recall``, team run 39237146851:
independent audit
``results/audit/frontier/frontier-concept-seed-recall/CYCLE_39251875368_GATE.json``
gate=PASS / safe_to_integrate=true / required_fixes=[]; producer commit
``dba1cadc0294af6f18ec9b3fe015599c866c8828``; accepted module sha256
``306873c356b5a3cd06b12873d7e90d16922964125cafe690d005580851a1f7b8``.
Product vendors that pure module as ``product/query/nlcs.py`` and integrates it
through ``product/query/concept_seed.py`` (factory requirement 21; silent
non-consumption is not permitted).

These tests are offline and deterministic: no network, no model call, no
corpus.  They pin the four things the integration promises:

1. the frozen variant strings reproduce the accepted RULES strings byte-for-byte
   (so the vendored copy is not a re-tuned generator);
2. the plan emits only for the question's own language and only for
   under-covered concepts, capped at the accepted 2;
3. the merge is strictly additive - no existing row is removed, re-ranked or
   re-labelled, and a failed search leaves the baseline untouched;
4. the bundle provenance records the channel, model_calls=0 and the accepted
   claim ceiling, and offline/fixture mode issues nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT))

from product.query import concept_seed  # noqa: E402
from product.query import nlcs  # noqa: E402

#: Accepted RULES file from the mount.  Read-only in these tests; never written.
RULES_PATH = Path(
    "/tmp/lex_accepted/frontier/frontier-concept-seed-recall/results/frontier/"
    "frontier-concept-seed-recall/RULES.json"
)

DE_QUESTION = (
    "Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung: "
    "wie weit geht der aktive Eingriff, und welche Entscheidungen begrenzen ihn "
    "gegenüber einer blossen Überwachungspflicht?"
)
FR_QUESTION = (
    "La responsabilité pénale de l'entreprise selon l'art. 102 CP est-elle "
    "subsidiaire ou primaire, et pour quelles infractions ? Quelles exigences "
    "d'organisation doivent être prouvées ?"
)
IT_QUESTION = (
    "Un furto di lieve entità commesso da un dipendente giustifica il "
    "licenziamento immediato ex art. 337 CO? Quali circostanze modificano la "
    "risposta?"
)


# --------------------------------------------------------------------------
# 1. the vendored module reproduces the accepted frozen variant strings
# --------------------------------------------------------------------------

def _accepted_unit_variants() -> list[tuple[str, str, str, str]]:
    """(language, question_text, concept, query) for every frozen variant."""
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    out: list[tuple[str, str, str, str]] = []
    for unit in rules["units"]:
        lang = unit.get("language")
        text = unit.get("question_text")
        if not lang or not text:
            continue
        for variant in unit.get("variants") or []:
            out.append((lang, text, variant["concept"], variant["query"]))
    return out


@pytest.mark.skipif(
    not RULES_PATH.exists(),
    reason="accepted frontier-concept-seed-recall mount not provisioned",
)
def test_vendored_nlcs_reproduces_the_accepted_variant_strings_exactly():
    units = _accepted_unit_variants()
    assert len(units) >= 6, "the frozen variant set must be covered"
    for lang, text, concept, expected in units:
        built = nlcs.build_variant(text, lang, concept)
        assert built["query"] == expected, (
            f"vendored NLCS-1 string diverges for {lang}/{concept}"
        )


# --------------------------------------------------------------------------
# 2. language detection and planning
# --------------------------------------------------------------------------

def test_detect_question_language_for_the_three_accepted_languages():
    assert concept_seed.detect_question_language(DE_QUESTION) == "de"
    assert concept_seed.detect_question_language(FR_QUESTION) == "fr"
    assert concept_seed.detect_question_language(IT_QUESTION) == "it"


def test_detect_question_language_refuses_ambiguous_and_unknown_text():
    assert concept_seed.detect_question_language("") is None
    assert concept_seed.detect_question_language("business judgment rule") is None


def _de_rows(n: int = 6) -> list[dict]:
    """A retrieved set covering every DE concept except the two target ones.

    ``content_concepts`` of ``DE_QUESTION`` yields aktive / fursorgepflicht /
    arbeitgebers / kapitalverletzung / eingriff / uberwachungspflicht.  This
    text deliberately carries the first, second, third and fifth and none of
    the two under-covered ones, so the plan's under-covered set is exactly the
    accepted pair.
    """
    rows = []
    for i in range(n):
        rows.append({
            "decision_id": f"d{i:03d}",
            "rank": i,
            "language": "de",
            "regeste": (
                "Aktive Fürsorgepflicht des Arbeitgebers; Eingriff; "
                "Verletzung der Pflicht; Schadenersatz."
            ),
        })
    return rows


def test_plan_emits_one_variant_per_under_covered_concept_capped_at_two():
    plan = concept_seed.plan_concept_seed(DE_QUESTION, _de_rows())
    assert plan["enabled"] is True
    assert plan["language"] == "de"
    assert plan["under_covered"] == ["kapitalverletzung", "uberwachungspflicht"]
    assert len(plan["variants"]) == concept_seed.MAX_CONCEPTS_PER_QUERY == 2
    assert {v["concept"] for v in plan["variants"]} == {
        "kapitalverletzung", "uberwachungspflicht"
    }
    assert all(v["template_id"] == "NLCS-1" for v in plan["variants"])
    assert plan["model_calls"] == 0


def test_plan_emits_nothing_when_every_concept_is_covered():
    rows = _de_rows()
    # MIN_ROWS_PER_CONCEPT is 2, so both target concepts need two rows.
    for i in range(2):
        rows.append({
            "decision_id": f"cap{i}",
            "rank": 99 + i,
            "language": "de",
            "regeste": "Kapitalverletzung und Überwachungspflicht im Arbeitnehmerschutz.",
        })
    plan = concept_seed.plan_concept_seed(DE_QUESTION, rows)
    assert plan["under_covered"] == []
    assert plan["enabled"] is False
    assert plan["variants"] == []


def test_plan_emits_nothing_for_an_unknown_language():
    plan = concept_seed.plan_concept_seed("business judgment rule", _de_rows())
    assert plan["language"] is None
    assert plan["enabled"] is False


def test_plan_can_be_pinned_to_the_question_language_explicitly():
    plan = concept_seed.plan_concept_seed(
        "business judgment rule", _de_rows(), language="de"
    )
    assert plan["language"] == "de"
    assert plan["enabled"] is True


# --------------------------------------------------------------------------
# 3. strictly additive merge
# --------------------------------------------------------------------------

def _row(decision_id: str, *, channel: str = "search") -> dict:
    return {
        "decision_id": decision_id,
        "rank": 1,
        "language": "de",
        "channels": [channel],
        "regeste": "x",
    }


def test_augment_is_strictly_additive_and_channels_new_rows():
    baseline = {"candidates": [_row("a"), _row("b")], "provenance": {}}
    plan = {
        "enabled": True,
        "language": "de",
        "under_covered": ["kapitalverletzung"],
        "variants": [{"concept": "kapitalverletzung", "query": "Q", "surface_form": "Kapitalverletzung",
                      "morph_variants": ["Kapitalverletzung", "Kapitalverletzungen"],
                      "template_id": "NLCS-1"}],
    }
    seen_queries: list[str] = []

    def search_fn(query):
        seen_queries.append(query)
        return [_row("c"), _row("a")]  # "a" is already present -> dedupe

    out = concept_seed.augment_candidates(baseline, plan, search_fn=search_fn)

    assert seen_queries == ["Q"]
    assert [c["decision_id"] for c in out["candidates"]] == ["a", "b", "c"]
    # baseline rows are untouched objects
    assert out["candidates"][0] is baseline["candidates"][0]
    assert out["candidates"][1] is baseline["candidates"][1]
    new_row = out["candidates"][2]
    assert concept_seed.CHANNEL in new_row["channels"]
    assert new_row["channels"][0] == "search"  # original channel preserved
    prov = out["provenance"]["concept_seed"]
    assert prov["n_added_candidates"] == 1
    assert prov["added_decision_ids"] == ["c"]
    assert prov["network_calls"] == 1
    assert prov["model_calls"] == 0


def test_augment_dedupes_against_existing_rows():
    baseline = {"candidates": [_row("a")], "provenance": {}}
    plan = {
        "enabled": True,
        "language": "de",
        "under_covered": ["x"],
        "variants": [{"concept": "x", "query": "Q"}],
    }
    out = concept_seed.augment_candidates(
        baseline, plan, search_fn=lambda q: [_row("a")]
    )
    assert out is baseline  # nothing new -> baseline returned unchanged


def test_augment_is_a_noop_without_a_search_fn():
    baseline = {"candidates": [_row("a")], "provenance": {}}
    plan = {"enabled": True, "language": "de", "under_covered": ["x"],
            "variants": [{"concept": "x", "query": "Q"}]}
    assert concept_seed.augment_candidates(baseline, plan, search_fn=None) is baseline


def test_augment_fail_open_when_a_search_raises():
    baseline = {"candidates": [_row("a")], "provenance": {}}
    plan = {"enabled": True, "language": "de", "under_covered": ["x"],
            "variants": [{"concept": "x", "query": "Q"}]}

    def boom(_q):
        raise RuntimeError("upstream unavailable")

    out = concept_seed.augment_candidates(baseline, plan, search_fn=boom)
    assert out is baseline


def test_augment_noop_when_plan_disabled():
    baseline = {"candidates": [_row("a")], "provenance": {}}
    assert concept_seed.augment_candidates(
        baseline, {"enabled": False}, search_fn=lambda q: [_row("b")]
    ) is baseline


# --------------------------------------------------------------------------
# 4. bundle provenance and offline/fixture behaviour
# --------------------------------------------------------------------------

def test_apply_concept_seed_appends_variants_and_provenance_without_touching_rows():
    bundle = {
        "query": DE_QUESTION,
        "query_variants": [{"variant_id": "original:x", "text": DE_QUESTION, "kind": "original"}],
        "decisions": [{"decision_id": "a"}],
        "provenance": {"adapter": "ocl_adapter"},
    }
    plan = {
        "enabled": True,
        "language": "de",
        "under_covered": ["kapitalverletzung"],
        "variants": [{"concept": "kapitalverletzung", "query": "Q",
                      "surface_form": "Kapitalverletzung",
                      "morph_variants": ["Kapitalverletzung", "Kapitalverletzungen"],
                      "template_id": "NLCS-1"}],
    }
    out = concept_seed.apply_concept_seed(bundle, plan)
    assert len(out["query_variants"]) == 2
    added = out["query_variants"][1]
    assert added["kind"] == "nl_concept_seeded"
    assert added["language_filter"] is None
    assert added["text"] == "Q"
    assert out["decisions"] == [{"decision_id": "a"}]
    prov = out["provenance"]["concept_seed"]
    assert prov["enabled"] is True
    assert prov["model_calls"] == 0
    assert "human product gate" in prov["claim_ceiling"]


def test_apply_concept_seed_noop_when_plan_disabled():
    bundle = {"query_variants": [], "provenance": {}}
    assert concept_seed.apply_concept_seed(bundle, {"enabled": False}) is bundle


def test_arm_is_inert_in_offline_and_fixture_modes(monkeypatch):
    """The frozen offline slice and every committed packet byte stay unchanged."""
    from product.query import pipeline

    called = {"n": 0}

    def boom(_q):
        called["n"] += 1
        raise AssertionError("offline/fixture mode must not issue a search")

    monkeypatch.setattr(pipeline, "_concept_seed_search_fn", lambda mode: boom)
    candidate = {"candidates": [_row("a")], "provenance": {}}
    for mode in ("offline", "fixture"):
        out, plan = pipeline._apply_concept_seed_arm(candidate, DE_QUESTION, mode=mode)
        assert out is candidate
        assert plan["enabled"] is False
    assert called["n"] == 0


def test_arm_runs_in_live_mode_and_merges_additively():
    from product.query import pipeline

    candidate = {"candidates": [_row("a")], "provenance": {}}
    plan = {"enabled": True, "language": "de", "under_covered": ["kapitalverletzung"],
            "variants": [{"concept": "kapitalverletzung", "query": "Q",
                          "surface_form": "Kapitalverletzung",
                          "morph_variants": ["Kapitalverletzung"], "template_id": "NLCS-1"}]}

    monkeypatch_search = lambda mode: (lambda q: [_row("b")])
    # patch the plan builder to a deterministic one and the search fn to a stub
    orig_plan = concept_seed.plan_concept_seed
    orig_search = pipeline._concept_seed_search_fn
    try:
        concept_seed.plan_concept_seed = lambda *a, **k: plan
        pipeline._concept_seed_search_fn = monkeypatch_search
        out, out_plan = pipeline._apply_concept_seed_arm(candidate, DE_QUESTION, mode="live")
        assert out_plan is plan
        assert [c["decision_id"] for c in out["candidates"]] == ["a", "b"]
        assert concept_seed.CHANNEL in out["candidates"][1]["channels"]
    finally:
        concept_seed.plan_concept_seed = orig_plan
        pipeline._concept_seed_search_fn = orig_search


def test_arm_fail_open_in_live_mode_when_planning_raises():
    from product.query import pipeline

    candidate = {"candidates": [_row("a")], "provenance": {}}
    orig = concept_seed.plan_concept_seed
    try:
        concept_seed.plan_concept_seed = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
        out, plan = pipeline._apply_concept_seed_arm(candidate, DE_QUESTION, mode="live")
        assert out is candidate
        assert plan["enabled"] is False
    finally:
        concept_seed.plan_concept_seed = orig
