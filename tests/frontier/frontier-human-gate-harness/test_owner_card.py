"""Acceptance (3): the FR/DE owner card with the four gate questions."""
from __future__ import annotations

import ast
import re
from _bootstrap import MASTER_PROMPT, REALITY_CHECK

from frontier_human_gate_harness import owner_card as oc
from frontier_human_gate_harness.baseline_view import esc

SCALE_MIN, SCALE_MAX = 1, 5


def test_four_questions_present_in_fr_and_de_with_scale_and_freetext():
    model = oc.card_model()
    assert model["question_ids"] == ["q1", "q2", "q3", "q4"]
    assert len(model["questions"]) == 4
    for question in model["questions"]:
        assert question["id"].startswith("q")
        for lang in ("fr", "de", "en"):
            assert question[lang].strip(), f"{question['id']} missing {lang}"
        assert question["hint_fr"].strip() and question["hint_de"].strip()
    assert model["scale"]["min"] == SCALE_MIN and model["scale"]["max"] == SCALE_MAX
    assert set(model["scale"]["anchors"]) == {"fr", "de"}
    assert set(model["scale"]["anchors"]["fr"]) == {1, 2, 3, 4, 5}

    for lang in ("fr", "de"):
        body = oc.render_card_body(lang)
        assert body.count('type="radio"') == 4 * 5, f"{lang}: 4 questions x 5 scale steps"
        assert body.count("<textarea") == 4, f"{lang}: one free-text field per question"
        for question in model["questions"]:
            assert esc(question[lang]) in body, \
                f"{lang} wording of {question['id']} not rendered"
        assert 'name="%s_scale"' % question["id"] in body
        assert "answered_at" in oc.render_card_document(lang), \
            "each answer must be timestamped on export"
        assert "1..5" in body or "scale" in body.lower()


def test_en_questions_verbatim_from_master_prompt_source():
    if not MASTER_PROMPT.is_file():
        from unittest import SkipTest

        raise SkipTest(f"Master Prompt not mounted: {MASTER_PROMPT}")
    text = MASTER_PROMPT.read_text(encoding="utf-8")
    section = text.split("## Human product gate", 1)[-1].split("\n## ", 1)[0]
    lines = [ln.strip() for ln in section.splitlines() if re.match(r"^[1-4]\.\s+\S", ln.strip())]
    assert len(lines) == 4, f"expected 4 numbered gate questions, found {len(lines)}"
    for line, question in zip(lines, oc.QUESTIONS):
        assert line == f"{question['id'][-1]}. {question['en']}", \
            f"{question['id']} EN is not verbatim from the Master Prompt: {line!r}"
    assert oc.MASTER_PROMPT_SOURCE.startswith("LEXMACHINA_MASTER_PROMPT.md")


def test_suggested_question_is_the_frozen_rent_default_leg():
    if not REALITY_CHECK.is_file():
        from unittest import SkipTest

        raise SkipTest(f"accepted product mount not present: {REALITY_CHECK}")
    tree = ast.parse(REALITY_CHECK.read_text(encoding="utf-8"))
    legs = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id == "LEGS":
                    legs = ast.literal_eval(node.value)
    assert legs, "LEGS dict not found in product/reality_check.py"
    value = legs["rent-default"]
    if isinstance(value, (tuple, list)):
        value = "".join(value)
    suggested = oc.SUGGESTED_QUESTION
    assert suggested["question_fr"] == value
    assert suggested["slug"] == "rent-default"
    assert suggested["question_fr_source"] == oc.LEG_SOURCE
    assert suggested["question_de_source"].startswith("Team-Übersetzung"), \
        "the DE rendering must be labelled as a team translation, never as a quote"
    assert suggested["alternative_query_de"] == "Kündigung Mietvertrag Mietrecht"
    assert suggested["alternative_query_de_source"] == oc.DE_QUERY_SOURCE


def test_suggested_question_rendered_on_both_language_cards():
    # each card carries the suggested question in its own language
    for lang in ("fr", "de"):
        body = oc.render_card_body(lang)
        key = "question_fr" if lang == "fr" else "question_de"
        assert esc(oc.SUGGESTED_QUESTION[key]) in body, lang
        assert esc(oc.SUGGESTED_QUESTION["alternative_query_de"]) in body
        assert esc(oc.SUGGESTED_QUESTION["alternative_query_de_source"]) in body
        source_key = "question_fr_source" if lang == "fr" else "question_de_source"
        assert esc(oc.SUGGESTED_QUESTION[source_key]) in body, \
            f"{lang} card must show the provenance of its suggested question"
    # the DE rendering is explicitly labelled as a team translation, never a quote
    assert esc(oc.SUGGESTED_QUESTION["question_de_source"]) in oc.render_card_body("de")
    assert "Team-Übersetzung" in oc.SUGGESTED_QUESTION["question_de_source"]
    # both languages point at the same frozen leg
    assert oc.SUGGESTED_QUESTION["slug"] == "rent-default"
    assert "rent-default" in oc.render_card_body("fr")
    assert "rent-default" in oc.render_card_body("de")


def test_card_document_is_deterministic_and_collects_no_personal_data():
    first = oc.render_card_document("fr").encode("utf-8")
    second = oc.render_card_document("fr").encode("utf-8")
    assert first == second
    doc = first.decode("utf-8")
    assert doc.startswith("<!DOCTYPE html>")
    assert 'lang="fr"' in doc
    assert 'name="name"' not in doc and 'name="email"' not in doc
    assert "Aucune donnée personnelle" in doc or "personenbezogene Daten" in doc
    assert len(oc.card_json_bytes()) > 0
    import json

    payload = json.loads(oc.card_json_bytes())
    assert payload["team_id"] == "frontier-human-gate-harness"
    assert payload["charter_version"] == 1
    assert payload["record_type"] == "lex_human_gate_card"


def test_card_questions_cover_the_four_gate_intents():
    joined = " ".join(q["en"].lower() for q in oc.QUESTIONS)
    for intent in ("visible in the list/answer", "structure", "contrary authority",
                   "preferable to the conventional interface"):
        assert intent in joined, f"gate intent missing: {intent}"
