"""Rubric unit tests: normalisation, marker/anchor matching, defect classes."""

from __future__ import annotations

import pytest

from frontier_counter_label_integrity.rubric import (
    VARIANT_LENIENT,
    VARIANT_PRIMARY,
    VARIANT_STRICT,
    make_context,
    score_row,
)


def _row(**kw):
    base = {
        "decision_id": "X1",
        "rank": 1,
        "language": "de",
        "court": "bger",
        "title": "",
        "regeste": "",
        "counter_status": "candidate-limiting",
        "counter_evidence": "",
        "counter_reason": "limiting",
        "counter_confidence": 0.4,
        "counter_uncertainty": 0.4,
        "counter_evidence_verified": True,
        "counter_markers": None,
        "full_text_len": 0,
        "row_text": "",
    }
    base.update(kw)
    base["field_presence"] = {k: (k in kw or k in base) for k in base if k != "field_presence"}
    base["field_presence"]["counter_markers"] = kw.get("counter_markers") is not None
    return base


# -- normalisation ---------------------------------------------------------

def test_german_umlaut_and_sharp_s_fold(rules):
    nz = rules.normalizer
    assert nz.text("Fürsorgepflicht") == "fursorgepflicht"   # ue fold is applied after uumlaut fold
    assert nz.text("Ueberwachungspflicht") == "uberwachungspflicht"
    assert nz.text("Straße") == "strasse"
    assert nz.text("Maßnahme").startswith("massn")


def test_marker_match_is_exact_not_prefix(rules):
    """'limita' must not license a sentence that only says 'limitato'."""
    nz = rules.normalizer
    toks = nz.stems("Procedimento limitato per semplificazione")
    assert nz.match_marker(toks, "limita") is None
    assert nz.match_marker(toks, "procedimento limitato") is not None


def test_anchor_match_is_prefix_tolerant(rules):
    nz = rules.normalizer
    toks = nz.stems("gegen die Fuer sorgepflichtverletzung")
    assert nz.match_anchor(toks, "sorgepflicht") is not None


def test_regex_patterns_see_undigraphed_text(rules):
    """The frozen pointer pattern is authored as 'genaue'; folding ue->u would break it."""
    nz = rules.normalizer
    assert nz.regex_text("darüber genaue Angaben") == "daruber genaue angaben"
    assert nz.match_regex(nz.regex_text("darüber genaue Angaben BGE 143 III 157 S. 12"),
                          r"daruber\s+genaue\s+angaben") is not None


# -- defect classes --------------------------------------------------------

def _score(rules, profile, **kw):
    return score_row(_row(**kw), make_context(rules, profile, VARIANT_PRIMARY))


def test_supported_control(rules):
    res = _score(
        rules, "it-responsabilita-medica", language="it",
        title="Responsabilita del medico",
        regeste="Responsabilita medica; nesso causale; 2052 cc",
        counter_evidence=(
            "La responsabilita del medico si presume solo se il nesso causale e dimostrato; "
            "in caso contrario si esclude la responsabilita."
        ),
    )
    assert res["primary_defect_class"] == "SUPPORTED"
    assert all(m["pass"] for m in res["criterion_marks"].values())


def test_inverted_french_appeal_rejected(rules):
    res = _score(
        rules, "fr-bail-entretien", language="fr", title="bail a loyer; defaut d'entretien",
        regeste="BAIL A LOYER; RESILIATION; 257f CO",
        counter_evidence="La Cour a rejete le recours. Le jugement de la premiere instance est confirme.",
    )
    assert res["primary_defect_class"] == "INVERTED"
    assert res["criterion_marks"]["ii"]["pass"] is False


def test_inverted_italian_appeal_rejected(rules):
    res = _score(
        rules, "it-responsabilita-medica", language="it", title="Responsabilita del medico",
        regeste="Responsabilita medica; 2052 cc",
        counter_evidence="Il ricorso e stato respinto e la sentenza e stata confermata.",
    )
    assert res["primary_defect_class"] == "INVERTED"


def test_boilerplate_only(rules):
    res = _score(
        rules, "fr-bail-entretien", language="fr", title="bail a loyer; resiliation",
        regeste="BAIL A LOYER; RESILIATION; 257f CO",
        counter_evidence=(
            "Contre le jugement de la premiere instance, la Cour a statue dans le sens des considerants."
        ),
    )
    assert res["primary_defect_class"] == "BOILERPLATE-ONLY"
    assert res["criterion_marks"]["iii"]["pass"] is False


def test_off_domain_labour_decision_on_medical_question(rules):
    res = _score(
        rules, "it-responsabilita-medica", language="it", title="Arbeitsrechtliche Forderung",
        regeste="VERTRETUNGSRECHT; ARBEITSRECHTLICHE FORDERUNG",
        counter_evidence="Il datore di lavoro deve rispettare il diritto del lavoratore alla sicurezza.",
    )
    assert res["primary_defect_class"] == "OFF-DOMAIN"
    assert "pivot_absent" in res["defect_signals"]


def test_fragment_pointer(rules):
    res = _score(
        rules, "fr-bail-entretien", language="fr", title="bail a loyer", regeste="BAIL A LOYER; 257f CO",
        counter_evidence="darüber genaue Angaben BGE 143 III 157 S. 12",
    )
    assert res["primary_defect_class"] == "FRAGMENT"


def test_placeholder_is_fragment(rules):
    res = _score(
        rules, "it-responsabilita-medica", language="it", title="Responsabilita per atti illeciti",
        regeste="Responsabilita; risarcimento danni",
        counter_evidence="cited in generated answer",
    )
    assert res["primary_defect_class"] == "FRAGMENT"
    assert res["reason_code"] == "pointer_only"


def test_empty_evidence_is_unbacked_evidence_absent(rules):
    res = _score(
        rules, "de-kapitalverletzung", language="de", title="Kapitalverletzung; OR 321 ff.",
        regeste="Aktive Fuer sorgepflicht bei Kapitalverletzung; OR 321 ff.; EOG", counter_evidence="",
    )
    assert res["primary_defect_class"] == "UNBACKED"
    assert res["reason_code"] == "evidence_absent"
    assert res["criterion_marks"]["v"]["pass"] is True  # on-topic, but nothing is cited


def test_no_intent_marker_is_unbacked(rules):
    res = _score(
        rules, "fr-bail-entretien", language="fr", title="bail a loyer; defaut d'entretien",
        regeste="BAIL A LOYER; DEFAUT D'ENTRETIEN; 257f CO",
        counter_evidence="Le locataire a依旧是 refinanced le bail en未被中断 for three years.",
    )
    assert res["primary_defect_class"] == "UNBACKED"
    assert res["reason_code"] in ("no_intent_marker", "no_domain_anchor")


def test_precedence_is_the_frozen_order(rules):
    order = [s["class"] for s in sorted(rules.rubric["assignment_precedence"], key=lambda s: s["step"])]
    assert order == ["UNBACKED", "FRAGMENT", "BOILERPLATE-ONLY", "INVERTED", "OFF-DOMAIN",
                     "UNBACKED", "UNBACKED", "SUPPORTED"]


# -- variants --------------------------------------------------------------

def test_lenient_variant_drops_the_pivot_test(rules):
    row = _row(language="de", title="Arbeitsrechtliche Forderung", regeste="",
               counter_evidence="Das Impfobligatorium verstiess gegen die Fuer sorgepflicht der Arbeitgeberin.")
    strict = score_row(row, make_context(rules, "de-kapitalverletzung", VARIANT_PRIMARY))
    lenient = score_row(row, make_context(rules, "de-kapitalverletzung", VARIANT_LENIENT))
    assert strict["primary_defect_class"] == "OFF-DOMAIN"
    assert lenient["criterion_marks"]["v"]["pivot_test_applied"] is False


def test_strict_variant_drops_product_vocabulary(rules):
    row = _row(language="de", title="Kapitalverletzung", regeste="Kapitalverletzung; OR 321 ff.",
               counter_evidence="Die aktive Fuer sorgepflicht geht nicht weiter, wenn die Kapitalverletzung eintritt.")
    primary = score_row(row, make_context(rules, "de-kapitalverletzung", VARIANT_PRIMARY))
    strict = score_row(row, make_context(rules, "de-kapitalverletzung", VARIANT_STRICT))
    assert primary["criterion_marks"]["i"]["pass"] is True     # via the product's 'nicht'
    assert strict["criterion_marks"]["i"]["pass"] is False     # dropped with the product vocabulary


def test_marker_precision_reports_document_wide_only_markers(rules):
    row = _row(language="de", title="Kapitalverletzung", regeste="Kapitalverletzung; OR 321 ff.",
               counter_evidence="Die Kapitalverletzung ist hier nicht massgeblich.",
               row_text="abgewiesen. Die Kapitalverletzung ist hier nicht massgeblich.")
    res = score_row(row, make_context(rules, "de-kapitalverletzung", VARIANT_PRIMARY))
    mp = res["markers_precision"]
    assert "abgewiesen" in mp["document_wide_only_markers"]
    assert "abgewiesen" not in mp["markers_in_cited_evidence"]
    assert mp["reported_field_present"] is False