"""Freeze the sentence-level COUNTER-LABEL SUPPORT RUBRIC for this team.

Emits ``results/frontier/frontier-counter-label-integrity/RULES.json``.

Charter acceptance test (1): the rubric, every defect-class definition, every
threshold, the minimum-population requirement and the input paths with sha256
are committed BEFORE any label is scored.  This module therefore does NOT
contain, import or call any support-verdict logic: it only hashes inputs and
serialises the frozen constant block below.  All judgement content therefore
lives in the generated JSON, which the scorer loads read-only via
``--frozen-rules``; editing this file after scoring is detectable because the
report embeds ``rules_sha256`` and ``verify_freeze.py`` compares it against the
sha256 of the blob recorded in the freeze commit.

Usage:
    python3 frontier/frontier-counter-label-integrity/freeze_rules.py \
        --product-mount /tmp/lex_accepted/core/product \
        --out results/frontier/frontier-counter-label-integrity/RULES.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from typing import Any

RULES_SCHEMA = "frontier-counter-label-integrity/rules/1"
TEAM_ID = "frontier-counter-label-integrity"
CHARTER_VERSION = 1

# --------------------------------------------------------------------------
# FROZEN CONSTANT BLOCK.  Nothing below may be edited after the first scoring
# run.  Every entry is a threshold, definition or lexicon the rubric consults.
# --------------------------------------------------------------------------

FROZEN: dict[str, Any] = {
    "authority": {
        "master_prompt_non_negotiable": (
            "Never classify a case as supporting/contrary/limiting unless the evidence "
            "supports that label."
        ),
        "gate_question_under_test": (
            "Human product gate question 3: 'Did the map increase confidence that contrary "
            "authority had not been hidden?'"
        ),
        "claim_ceiling": (
            "This measurement is about the SUPPORT OF THE LABELS AS ISSUED by the product's "
            "counter-authority pass. It NEVER asserts that any specific decision IS supporting, "
            "contrary or limiting. Those remain the product's labels: reported here, not "
            "endorsed, not re-assigned."
        ),
    },

    # ---- normalisation -------------------------------------------------
    # Deterministic text normalisation used by every lexicon below.
    "normalization": {
        "unicode_form": "NFKC",
        "casefold": True,
        "soft_hyphen_removed": True,
        "whitespace": "collapse-and-strip",
        "diacritics": "fold-to-ascii",
        "umlaut_digraphs": "ue->u, oe->o, ae->a after folding (Swiss legal spelling)",
        "eszett": "ss",
        "ligatures": "oe->oe, ae->ae, fi->fi",
        "match_unit": "token",
        "stemming": {
            "algorithm": "frozen_suffix_stripper_v1",
            "strip_order": [
                "ungen", "ung", "heit", "keit", "lich", "isch", "ieren",
                "en", "er", "es", "e", "s",
            ],
            "min_stem_len": 4,
            "note": (
                "Applied to both anchors and evidence tokens. Anchor matches when an anchor "
                "token and an evidence token share a prefix of >=5 characters after stemming "
                "(prefix matching, not equality, so 'fuer_sorgepflicht' matches "
                "'fuer_sorgepflichtverletzung')."
            ),
        },
        "min_anchor_prefix_chars": 5,
        "min_match_chars": 4,
        "marker_match_rule": (
            "MARKERS match EXACTLY on stemmed tokens: a single-token marker must equal an "
            "evidence token after stemming; a multi-token marker must occur as a contiguous "
            "subsequence of stemmed evidence tokens. Prefix matching is NOT allowed for "
            "markers, because it would let 'limita' license a sentence that only says "
            "'procedimento limitato'."
        ),
        "anchor_match_rule": (
            "ANCHORS match with prefix tolerance: two stemmed tokens match when they share a "
            "prefix of >= min_anchor_prefix_chars characters, or when a multi-token anchor "
            "occurs as a contiguous subsequence. Prefix tolerance IS used for anchors because "
            "German compounds ('fuer_sorgepflicht' inside 'fuer_sorgepflichtverletzung') must "
            "match, and because the anchor is the question's own vocabulary."
        ),
        "sentence_split": "the product's own evidence string is already the cited sentence(s); "
                          "it is split on ';' into segments only for per-segment marker reporting",
    },

    # ---- criterion lexicon --------------------------------------------
    # (i) counter-intent markers.  Reused from the product's OWN declared
    # adversarial vocabulary (product/query/answer.py::ADVERSARIAL_TERMS at
    # accepted head 1668181a) so the rubric measures the labels against the
    # vocabulary the product itself claims to act on, plus a frozen addition
    # of limitation vocabulary.  Criterion (i) is NECESSARY, never sufficient.
    "lexicons": {
        "counter_intent_markers": {
            "provenance": {
                "product_adversarial_terms": (
                    "product/query/answer.py::ADVERSARIAL_TERMS @ accepted head 1668181a "
                    "(reused verbatim; REUSE-FIRST)"
                ),
                "addition": (
                    "frozen limitation/exception vocabulary added by this team, authored before "
                    "scoring and applied uniformly to all rows of all languages"
                ),
            },
            "de": {
                "product_adversarial_terms": [
                    "ausnahme", "einschränkung", "entgegen", "abweichend", "minderheit",
                    "vorbehalt", "jedoch", "dennoch", "abgelehnt", "abgewiesen", "nicht",
                    "unbegründet", "unzulässig", "ausschluss", "eng auszulegen",
                ],
                "frozen_additions": [
                    "nicht zu", "zu weit", "nur", "allein", "lediglich", "begrenzt",
                    "ausgeschlossen", "abweicht", "im gegensatz", "einschränken",
                    "ausschliesst", "folgt nicht", "soweit", "schrankt",
                ],
            },
            "fr": {
                "product_adversarial_terms": [
                    "exception", "contraire", "limiter", "rejete", "rejeté", "rejetée",
                    "irrecevable", "minorité", "toutefois", "néanmoins", "écarté", "réservé",
                ],
                "frozen_additions": [
                    "ne peut", "que si", "sous reserve", "se limite", "dans la limite",
                    "exclut", "ne va pas", "ne suffit pas", "sauf", "limité", "limitant",
                    "restriction", "aussi longtemps que", "doit être",
                ],
            },
            "it": {
                "product_adversarial_terms": [
                    "eccezione", "contrario", "contraria", "respinto", "respinta",
                    "irricevibile", "minoranza", "tuttavia", "riserva", "respinti",
                ],
                "frozen_additions": [
                    "non puo", "non può", "salvo", "limitatamente", "esclude", "escluso",
                    "esclusa", "non e sufficiente", "non è sufficiente", "in quanto",
                    "limita", "limitante", "vincolato", "deve essere dimostrato",
                    "non risulta", "non si evince",
                ],
            },
        },

        # (iii) procedural-disposal / procedural-admission constructions.
        "procedural_formula": {
            "de": [
                "im sinne der erwagungen", "im sinne der erwägungen",
                "gegen das urteil der vorinstanz", "gegen das urteil des vorinstanz",
                "auf die beschwerde ist nicht einzutreten", "auf die beschwerde einzutreten",
                "es ist nicht zu beanstanden", "gratische rechtspflege",
                "nicht eintreten", "eintreten in der sache",
            ],
            "fr": [
                "contre le jugement de la premiere instance", "contre le jugement de la preinstance",
                "dans le sens des considerants", "il y a lieu de rejeter",
                "la cour pleine", "ne peut etre examine", "entre en matiere",
                "gratuit de la procedure", "benefice de la matcher", "rejet de la demande",
            ],
            "it": [
                "nel senso della motivazione", "nei sensi della motivazione",
                "contro la sentenza del tribunale di prima istanza",
                "non va discusso", "si ritiene non di dover entrare",
                "il tribunale non entra", "gratuito patrocinio",
                "diniego di gratuito patrocinio", "ammissione del ricorso",
                "procedimento limitato per semplificazione",
            ],
        },

        # Affirmatively inverted / role-blind polarity: the cited sentence
        # states that the challenge FAILED or that the challenged ruling STOOD.
        # Charter criterion (ii) examples: 'steht ... nicht entgegen',
        # 'wird abgewiesen', 'rejete le recours', 'unter Vorbehalt ... vorbehalten'.
        "polarity_inversion": {
            "de": [
                r"steht\s+(?:\w+\s+){0,5}nicht\s+entgegen",
                r"nicht\s+zu\s+beanstanden",
                r"weicht\s+(?:\w+\s+){0,5}nicht\s+ab",
                r"wird\s+bestatigt", r"wurde\s+bestatigt", r"bestatigt\s+das",
                r"ist\s+richtig\s+entschieden", r"ist\s+entschieden",
                r"wird\s+(?:im\s+sinne\s+der\s+erwagungen\s+)?abgewiesen",
                r"wurde\s+abgewiesen", r"abgewiesen\.",
                r"unter\s+vorbehalt\s+vorbehalten",
            ],
            "fr": [
                r"ne\s+contredit\s+pas", r"n'est\s+pas\s+contredit",
                r"ne\s+remet\s+pas\s+en\s+cause",
                r"rejete\s+le\s+recours", r"rejette\s+le\s+recours",
                r"rejete\s+les\s+recours", r"rejete(?:s)?\s+(?:l['’])?recours",
                r"recours\s+(?:est\s+|ont\s+ete\s+)?rejete", r"rejete",
                r"n'entre\s+pas\s+en\s+matiere", r"n'est\s+pas\s+entre\s+en\s+matiere",
                r"est\s+confirme", r"confirme",
                r"sous\s+reserve\s+de",
            ],
            "it": [
                r"non\s+entra\s+in\s+materia", r"non\s+e\s+entrato\s+in\s+materia",
                r"non\s+contraddice", r"non\s+contraddic[ei]",
                r"non\s+rimette\s+in\s+discussione",
                r"viene\s+respint[oa]", r"respint[oi]\s+il\s+ricorso",
                r"ricorso\s+(?:viene\s+)?respint[oa]",
                r"viene\s+confermato", r"confermata",
                r"con\s+riserva\s+di",
            ],
        },

        # Evidence that is a bare pointer / placeholder with no proposition.
        # Charter defect class FRAGMENT.  'cited in generated answer' is the
        # accepted contract's own NON_QUOTE_REF
        # (frontier/frontier-generative-audit/generative_audit/evidence.py).
        "fragment_pointer": [
            r"^\s*cited\s+in\s+generated\s+answer\s*$",
            r"^\s*(?:see|voir|siehe)\b.*$",
            r"^\s*(?:vgl|cf)\.?\s*$",
            r"daruber\s+genaue\s+angaben", r"genauere\s+angaben",
            r"for\s+details\s+see", r"voir\s+ci-dessus", r"voir\s+plus\s+haut",
            r"maggiori\s+dettagli", r"per\s+maggiori\s+dettagli",
            r"^\s*\.{3}\s*$", r"^\s*\u2026\s*$",
            r"^\s*\u00a7{1,2}\s*\d+[a-z]?\s*$",
            r"^\s*art\.?\s*\d+[a-z]?\s*$",
            r"^\s*\[\s*\d+\s*[a-z]?\s*\]\s*$",
            r"^\s*bge\s*\d+\s+[ivx]+\s+\d+\s+s\.?\s*\d+\s*$",
            r"^\s*bgu\s+\d+\s+[ivx]+\s+\d+\s*$",
        ],

        # Procedural OUTCOME words.  Used only to decide whether a matched
        # procedural construction is 'boilerplate-only' (procedure, no
        # outcome) or a reversal (procedure with an outcome -> inverted).
        "procedural_outcome_words": {
            "de": ["abgewiesen", "abgelehnt", "bestatigt", "gutgeheissen", "heisst",
                   "zuruckgewiesen", "zuruckgenommen", "unzutreffend"],
            "fr": ["rejete", "rejete", "ecarte", "confirme", "declare", "admis", "recevable",
                   "irrecevable", "accorde"],
            "it": ["respinto", "respinta", "confermato", "confermata", " dichiarato",
                   "inammissibile", "ammesso", "accoglie"],
        },
    },

    # ---- question anchors ---------------------------------------------
    # TWO TIERS, both frozen before scoring, both authored ONLY from the
    # question's own text (bundle `query` string) and, for the three gate
    # questions, the gate-packet manifest's `legal_area` string.  No counter
    # row, counter_evidence, counter_reason or counter_status was consulted
    # while authoring them (see anchor_authoring_provenance).
    #
    #   DOMAIN anchors = the question's general legal area.
    #   PIVOT  anchors = the question's distinguishing subject matter, i.e. the
    #                     terms whose ABSENCE means the row does not speak to
    #                     the question at all.
    #
    # Criterion (iv) is tested against DOMAIN anchors; criterion (v) against
    # PIVOT anchors.  Both are reported, and a LENIENT variant of (v) that
    # drops the PIVOT test is reported as a pre-declared sensitivity analysis.
    "anchor_authoring_provenance": {
        "sources_used": [
            "bundle.decisions[*] is NOT a source",
            "bundle.query (the question text)",
            "results/product/gate_packet/38799024807/manifest.json -> questions[*].legal_area",
        ],
        "sources_not_used": [
            "counter_status", "counter_evidence", "counter_reason", "counter_confidence",
            "counter_uncertainty", "title", "regeste", "snippet", "full_text",
        ],
        "disclosure": (
            "Row ids, ranks and label COUNTS per bundle were read during population discovery "
            "before the anchors were authored; no support judgement of any row was made before "
            "this file was committed. The freeze commit is the proof."
        ),
        "declaration_on_variant_pivots": (
            "Bare 'aktiv'/'einzeln'/'einschrankt' style generic words were kept in DOMAIN, not "
            "PIVOT: PIVOT must be terms a row cannot plausibly share with a different question in "
            "the same legal area."
        ),
    },

    "question_anchors": {
        "de-kapitalverletzung": {
            "question": (
                "Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung: wie weit "
                "geht der aktive Eingriff, und welche Entscheidungen begrenzen ihn gegenüber einer "
                "blossen Überwachungspflicht?"
            ),
            "legal_area": "Arbeitsrecht — Sorgfaltspflichten des Arbeitgebers bei Kapitalverletzung (OR 321 ff., EOG)",
            "domain": [
                "arbeitsrecht", "sorgepflicht", "arbeitgeber", "kapitalverletzung",
                "eingriff", "ueberwachung", "ueberwachungspflicht", "entscheidung",
            ],
            "pivot": [
                "kapitalverletzung", "or321", "eog", "glaubiger", "schuldner", "untergang",
                "sanierung", "insolvenz", "konkurs", "liquiditaet", "aktiv", "eingriff",
            ],
            "expected_languages": ["de", "fr", "it"],
            "foreign_legal_area_fields": [],
        },
        "fr-bail-entretien": {
            "question": (
                "Résiliation du bail pour défaut d'entretien du bailleur : jusqu'où va la "
                "jurisprudence, et quelles décisions distinguent le défaut d'entretien grave de "
                "la simple négligence ?"
            ),
            "legal_area": "droit du bail — entretien de l'immeuble et résiliation (CP 257d ss.)",
            "domain": [
                "resiliation", "bail", "bailleur", "entretien", "travail", "defaut",
                "chose", "louee", "locataire", "jurisprudence", "negligence",
            ],
            "pivot": [
                "257d", "257f", "257h", "259b", "260a", "271", "resiliation", "defaut",
                "grave", "negligence", "consigner", "consignation", "graves",
            ],
            "expected_languages": ["de", "fr", "it"],
            "foreign_legal_area_fields": [],
        },
        "it-responsabilita-medica": {
            "question": (
                "Responsabilità del medico per errore terapeutico: quale obbligo di diligenza e "
                "quale nesso causale devono essere dimostrati, e quali decisioni escludono la "
                "responsabilità?"
            ),
            "legal_area": "responsabilità civile — responsabilità medica (c.c. 2052 ss.)",
            "domain": [
                "responsabilita", "medico", "errore", "terapeutico", "diligenza",
                "obbligo", "causale", "causalita", "decisioni", "escludere", "risarcimento",
                "danno",
            ],
            "pivot": [
                "medico", "2052", "causalita", "diligenza", "terapeutico", "terapeutica",
                "diagnosi", "art2052", "medic",
            ],
            "expected_languages": ["de", "fr", "it"],
            "foreign_legal_area_fields": [],
        },
        # Secondary replication population anchors (authored from the same two
        # sources; these bundles carry no manifest legal_area).
        "responsabilite-penale-entreprise-102cp": {
            "question": "Responsabilité pénale de l'entreprise selon l'art. 102 CP",
            "legal_area": "",
            "domain": [
                "responsabilite", "penale", "entreprise", "102", "cp", "infraction",
                "personne", "morale", "subsidiaire", "primaire",
            ],
            "pivot": [
                "102", "cp", "penale", "imputabilita", "attribuibilita", "personne",
                "morale", "vocation", "infraction", "comite", "dirigeant",
            ],
            "expected_languages": ["de", "fr", "it"],
            "foreign_legal_area_fields": [],
        },
        "kuendigung-mietrecht": {
            "question": "Kündigung Mietvertrag Mietrecht",
            "legal_area": "",
            "domain": ["kundigung", "mietvertrag", "mietrecht", "miet", "vertrag"],
            "pivot": ["kundigung", "mietvertrag", "257", "258", "271", "272", "ordnungswidrig"],
            "expected_languages": ["de", "fr", "it"],
            "foreign_legal_area_fields": [],
        },
    },

    # ---- the rubric -----------------------------------------------------
    "rubric": {
        "scored_statuses": ["candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting"],
        "reported_separately_never_scored": ["cited"],
        "reported_separately_never_scored_reason": (
            "counter_status='cited' carries the accepted contract's NON_QUOTE_REF placeholder "
            "'cited in generated answer' (evidence.py:40) and asserts NO limiting/contrary "
            "polarity, so it is not a counter label. It is counted and its placeholder share "
            "reported, never scored as a label."
        ),
        "criteria": {
            "i_intent_marker_in_cited_evidence": (
                "At least one frozen counter-intent marker occurs in the CITED EVIDENCE "
                "STRING ITSELF (the row's own counter_evidence), matched on the normalised "
                "stemmed tokens. Document-wide presence does not count."
            ),
            "ii_no_polarity_inversion": (
                "No frozen polarity-inversion construction occurs in the cited evidence "
                "(challenge failed / challenged ruling stood / role-blind negation)."
            ),
            "iii_not_procedural_boilerplate_only": (
                "The cited evidence is not exclusively a procedural-disposal or "
                "procedural-admission construction: either no frozen procedural construction "
                "matches, or the matched construction carries a procedural OUTCOME word, or a "
                "counter-intent marker also occurs in it."
            ),
            "iv_topical_term_in_evidence_or_title": (
                "A frozen DOMAIN-tier anchor of the row's own question occurs in the cited "
                "evidence string or in the row title/regeste. Without it the correct product "
                "verdict is counter_status='none'."
            ),
            "v_not_demonstrably_outside_question_domain": (
                "A frozen PIVOT-tier anchor of the row's own question occurs in the cited "
                "evidence string, the row title or the row regeste (the decision's own "
                "abstract); AND the row's language is in the question's expected_languages; "
                "AND the row's legal_area field is not in the question's "
                "foreign_legal_area_fields."
            ),
        },
        "supported_iff_all": ["i", "ii", "iii", "iv", "v"],
        "cited_evidence_string": (
            "At accepted head the bundle row carries no sentence pointer or offset and no "
            "counter_markers field, so the row's OWN counter_evidence string IS the cited "
            "evidence. Where full_text is present the harness additionally records whether the "
            "cited evidence occurs verbatim in the row's own text."
        ),

        "defect_classes": {
            "INVERTED": (
                "The cited evidence affirmatively inverts the polarity of the label: a frozen "
                "polarity-inversion construction occurs in the cited evidence itself."
            ),
            "OFF-DOMAIN": (
                "No frozen PIVOT-tier anchor of the row's own question occurs anywhere in the "
                "row's own text (cited evidence, title, regeste), or the row's language is "
                "outside the question's expected languages, or its legal_area field is listed as "
                "foreign. The row is a real decision in the right language that does not speak "
                "to the question."
            ),
            "BOILERPLATE-ONLY": (
                "The cited evidence is a procedural-disposal or procedural-admission "
                "construction with no counter-intent marker: form, not substance."
            ),
            "FRAGMENT": (
                "The cited evidence is a bare pointer or placeholder with no proposition "
                "('cited in generated answer', 'darüber genaue Angaben BGE ... S.', an ellipsis, "
                "a bare statute or case reference)."
            ),
            "UNBACKED": (
                "None of INVERTED/OFF-DOMAIN/BOILERPLATE-ONLY/FRAGMENT applies, but the label is "
                "still unsupported because criterion (i), (iv) or (v) fails. Reason codes are "
                "reported: evidence_absent, no_intent_marker, no_domain_anchor."
            ),
        },

        # Frozen assignment order.  FIRST MATCH WINS, exactly one primary class.
        "assignment_precedence": [
            {"step": 1, "when": "cited evidence string is empty or absent", "class": "UNBACKED", "reason_code": "evidence_absent"},
            {"step": 2, "when": "cited evidence matches a frozen fragment_pointer pattern", "class": "FRAGMENT", "reason_code": "pointer_only"},
            {"step": 3, "when": "a frozen procedural_formula matches the cited evidence AND no counter-intent marker occurs in it", "class": "BOILERPLATE-ONLY", "reason_code": "procedural_formula_no_intent"},
            {"step": 4, "when": "a frozen polarity_inversion pattern matches the cited evidence", "class": "INVERTED", "reason_code": "polarity_inverted"},
            {"step": 5, "when": "no PIVOT anchor in cited evidence, title or regeste; or language outside expected_languages; or legal_area foreign", "class": "OFF-DOMAIN", "reason_code": "pivot_absent"},
            {"step": 6, "when": "no counter-intent marker in the cited evidence", "class": "UNBACKED", "reason_code": "no_intent_marker"},
            {"step": 7, "when": "no DOMAIN anchor in the cited evidence or the row title/regeste", "class": "UNBACKED", "reason_code": "no_domain_anchor"},
            {"step": 8, "when": "all criteria i-v hold", "class": "SUPPORTED", "reason_code": "supported"},
        ],
        "precedence_rationale": (
            "Ordering follows the charter's own criterion order (iii before ii is required so a "
            "pure admission formula is not double-counted as inverted) and its defect-class "
            "enumeration. Absence of cited evidence outranks every substantive class because a "
            "label with no evidence cannot be assessed for polarity, topic or domain."
        ),
        "multi_label_reporting": (
            "Every criterion outcome is reported per row (criterion_marks: i..v pass/fail with "
            "the matched lexicon item), so the primary class is auditable and a reader can "
            "recompute any other precedence without re-running the harness."
        ),

        # Pre-declared sensitivity analyses.  They are REPORTED, never decisive.
        "sensitivity_variants": [
            {
                "id": "lenient-domain-only",
                "change": "criterion (v) is relaxed to a legal-area/language check only; the PIVOT-anchor test is dropped.",
                "why": (
                    "Criterion (v) is the only criterion whose operationalisation required an "
                    "authored interpretation (the question's distinguishing subject matter). "
                    "The Master Prompt non-negotiable is per-label, so one weak criterion cannot "
                    "be allowed to decide a verdict silently. This variant bounds the verdict."
                ),
            },
            {
                "id": "strict-no-product-vocabulary",
                "change": "the product's own ADVERSARIAL_TERMS (including the bare negations 'nicht'/'jedoch'/'toutefois'/'tuttavia') are dropped from the counter-intent vocabulary; only the frozen additions count.",
                "why": (
                    "The audit attributes a share of the defect to a bare-substring marker "
                    "vocabulary. This variant measures how much of the result depends on reusing "
                    "that vocabulary."
                ),
            },
        ],
    },

    # ---- verdict and thresholds ----------------------------------------
    "verdict_rule": {
        "verdict_classes": ["LABEL_SOUND", "LABEL_UNSOUND", "INSUFFICIENT_POPULATION"],
        "deciding_population": "primary",
        "LABEL_SOUND": (
            "primary population: n_scored == required_min_population_primary AND "
            "n_supported == n_scored (support_rate == 1.0, i.e. every issued label is supported "
            "by its own cited evidence under criteria i-v)."
        ),
        "LABEL_UNSOUND": (
            "primary population: n_scored == required_min_population_primary AND "
            "n_supported < n_scored (support_rate < 1.0). ANY single unsupported issued label "
            "makes the label set unsound, because the Master Prompt non-negotiable is per-label "
            "and is absolute, not averaged."
        ),
        "INSUFFICIENT_POPULATION": (
            "n_scored < required_min_population_primary, or any of the frozen primary rows could "
            "not be scored from the accepted evidence fields. This is a NON-RESULT: it must not "
            "be read as LABEL_SOUND nor as a pass of any product fix."
        ),
        "threshold_support_rate_sound": 1.0,
        "threshold_support_rate_unsound_below": 1.0,
        "aggregation": "no averaging, no weighting, no per-language or per-bundle exemption",
        "replication_reporting": (
            "The secondary population is reported with its own rate and verdict under the same "
            "frozen rubric. It is a REPLICATION, never a substitute: the charter's verdict is "
            "decided on the primary population. If the two disagree, both are reported and the "
            "verdict names the primary."
        ),
    },

    # ---- populations ----------------------------------------------------
    "populations": {
        "primary": {
            "definition": (
                "The three accepted gate-packet bundles named in the charter "
                "(results/product/gate_packet/38799024807/questions/*.bundle.json). The charter "
                "states the accepted-chain labelled population is exactly 7 candidate-limiting "
                "rows plus 7 'cited' placeholders."
            ),
            "required_min_population_primary": 7,
            "expected_rows": {
                "de-kapitalverletzung": {
                    "candidate-limiting": ["zh_bezirksgericht_buelach_AH240008", "zh_obergericht_LA190008", "zh_obergericht_LA250006"],
                    "cited": [],
                },
                "fr-bail-entretien": {
                    "candidate-limiting": ["ge_gerichte_4A_286_2015"],
                    "cited": ["bger_4A_257_2018", "vd_findinfo_HC___2015___163", "vd_findinfo_HC___2015___575", "ge_gerichte_C_1963_2017"],
                },
                "it-responsabilita-medica": {
                    "candidate-limiting": ["ti_gerichte_13.2019.12", "ti_gerichte_16.2021.24", "ti_gerichte_12.2025.23"],
                    "cited": ["ti_gerichte_35.2018.59_d20190513", "bger_4A_248_2013", "ti_gerichte_12.2013.100_d20130517"],
                },
            },
            "population_drift_policy": (
                "If the bundles' actual labelled rows differ from expected_rows, the harness "
                "records the drift in the report as population_drift and scores what is actually "
                "present. This file is NOT re-frozen."
            ),
        },
        "secondary": {
            "definition": (
                "Pre-declared replication over EVERY other accepted live bundle on the mount that "
                "issues counter statuses. Declared because the charter asserts the gate-packet "
                "bundles are the ONLY accepted-chain material issuing counter statuses; that "
                "assertion is falsified by the mount (7 further accepted live bundles issue 39 "
                "further counter labels). Scoring them under the identical frozen rubric is a "
                "replication, not a scope change: the verdict is still decided on primary."
            ),
            "required_min_population_secondary": 30,
            "excluded": [
                {"reason": "fixture_mode: synthetic fixture labels, not a served product artifact", "paths": ["clickable_slice/bundle_fixture_kundigung_100.json", "gate_packet/offline_machinery_rehearsal/questions/machinery-de.bundle.json", "gate_packet/offline_machinery_rehearsal/questions/machinery-fr.bundle.json", "gate_packet/offline_machinery_rehearsal/questions/machinery-it.bundle.json", "progressive_slice/bundle_CYCLE_38665681083_fixture.json"]},
                {"reason": "no counter_status != none row at all", "paths": ["clickable_slice/bundle_live_enriched_20261014T214600Z_noop.json"]},
            ],
        },
    },

    # ---- coverage (charter 6) -------------------------------------------
    "coverage_rule": {
        "min_bundles": 3,
        "min_pre_repair_bundles": 1,
        "pre_repair_definition": (
            "A bundle produced without results/product/adversarial_retrieval/** present, i.e. an "
            "artifact of the accepted head that has no product/query/adversarial_retrieval.py."
        ),
        "post_repair_artifact_probe": {
            "paths_probed": [
                "results/product/adversarial_retrieval/",
                "product/query/adversarial_retrieval.py",
            ],
            "found": False,
            "note": (
                "At mount time on the accepted product checkout there is no "
                "results/product/adversarial_retrieval/ directory and no "
                "product/query/adversarial_retrieval.py, so the audited population of core-lane "
                "run 38828034436 (22 of 40 new counter rows unsupported) is NOT a measurable "
                "population here. It is MECHANISM evidence only and is never quoted as an "
                "accepted-chain support rate. If a post-repair artifact appears at a later mount, "
                "the identical frozen rubric is applied to it and reported as a before/after pair; "
                "this file is not re-frozen for that."
            ),
        },
    },

    # ---- non-vacuity (charter 8) -----------------------------------------
    "non_vacuity": {
        "purpose": "tests the HARNESS, not the population. It does NOT satisfy the minimum-population requirement.",
        "min_criteria_flagged": 2,
        "injection_manifest_sha256_required": True,
        # Exact injected rows, frozen before scoring.  Each carries the full
        # set of fields the harness reads, so the non-vacuity test is a pure
        # function of this file.
        "injection_rows": [
            {"inject_id": "INV-INV-01", "anchor_profile": "fr-bail-entretien", "decision_id": "INJECTED_inverted_appeal_failed",
             "counter_status": "candidate-contrary", "language": "fr", "rank": 91, "court": "bger", "title": "bail a loyer; defaut de la chose louee",
             "regeste": "BAIL A LOYER; RESILIATION; DEFAUT D'ENTRETIEN; 257f CO",
             "counter_evidence": "La Cour a rejete le recours. Le jugement de la premiere instance est confirme.",
             "counter_reason": "limiting", "counter_confidence": 0.5, "counter_uncertainty": 0.4,
             "expected_class": "INVERTED", "expected_reason_code": "polarity_inverted",
             "note": "appeal rejected / lower ruling confirmed, labelled candidate-contrary"},
            {"inject_id": "INV-INV-02", "anchor_profile": "it-responsabilita-medica", "decision_id": "INJECTED_inverted_respinto",
             "counter_status": "candidate-limiting", "language": "it", "rank": 92, "court": "ti_gerichte", "title": "Responsabilita del medico",
             "regeste": "Responsabilita medica; nesso causale; 2052 cc",
             "counter_evidence": "Il ricorso e stato respinto e la sentenza e stata confermata.",
             "counter_reason": "distinguishing", "counter_confidence": 0.5, "counter_uncertainty": 0.4,
             "expected_class": "INVERTED", "expected_reason_code": "polarity_inverted",
             "note": "Italian reversal construction, labelled candidate-limiting"},
            {"inject_id": "INV-BOI-01", "anchor_profile": "fr-bail-entretien", "decision_id": "INJECTED_boilerplate_entretes",
             "counter_status": "candidate-limiting", "language": "fr", "rank": 93, "court": "bger", "title": "bail a loyer; resiliation",
             "regeste": "BAIL A LOYER; RESILIATION; DEFAUT D'ENTRETIEN",
             "counter_evidence": "Contre le jugement de la premiere instance, la Cour a statue dans le sens des considerants.",
             "counter_reason": "limiting", "counter_confidence": 0.4, "counter_uncertainty": 0.5,
             "expected_class": "BOILERPLATE-ONLY", "expected_reason_code": "procedural_formula_no_intent",
             "note": "standard procedural-disposal formula, no counter-intent marker"},
            {"inject_id": "INV-OFF-01", "anchor_profile": "it-responsabilita-medica", "decision_id": "INJECTED_offdomain_arbeitsrecht",
             "counter_status": "candidate-limiting", "language": "it", "rank": 94, "court": "zh_obergericht", "title": "Arbeitsrechtliche Forderung",
             "regeste": "VERTRETUNGSRECHT; ARBEITSRECHTLICHE FORDERUNG",
             "counter_evidence": "Il datore di lavoro deve rispettare il diritto del lavoratore alla sicurezza sul luogo di lavoro.",
             "counter_reason": "limiting", "counter_confidence": 0.45, "counter_uncertainty": 0.5,
             "expected_class": "OFF-DOMAIN", "expected_reason_code": "pivot_absent",
             "note": "labour-law sentence with no medico/2052/causalita/diligenza pivot term anywhere in the row"},
            {"inject_id": "INV-FRA-01", "anchor_profile": "fr-bail-entretien", "decision_id": "INJECTED_fragment_pointer",
             "counter_status": "candidate-limiting", "language": "fr", "rank": 95, "court": "bger", "title": "bail a loyer; defaut de la chose",
             "regeste": "BAIL A LOYER; DEFAUT D'ENTRETIEN; 257f CO",
             "counter_evidence": "daruber genaue Angaben BGE 143 III 157 S. 12",
             "counter_reason": "limiting", "counter_confidence": 0.4, "counter_uncertainty": 0.6,
             "expected_class": "FRAGMENT", "expected_reason_code": "pointer_only",
             "note": "bare pointer, no proposition"},
            {"inject_id": "INV-UNB-01", "anchor_profile": "de-kapitalverletzung", "decision_id": "INJECTED_unbacked_empty",
             "counter_status": "candidate-limiting", "language": "de", "rank": 96, "court": "bger", "title": "Kapitalverletzung; OR 321 ff.",
             "regeste": "Aktive Fuer sorgepflicht des Arbeitgebers bei Kapitalverletzung; OR 321 ff.; EOG",
             "counter_evidence": "",
             "counter_reason": "distinguishing", "counter_confidence": 0.3, "counter_uncertainty": 1.0,
             "expected_class": "UNBACKED", "expected_reason_code": "evidence_absent",
             "note": "on-topic regeste, no cited evidence at all, uncertainty 1.0"},
            {"inject_id": "INV-SUP-01", "anchor_profile": "it-responsabilita-medica", "decision_id": "INJECTED_supported_control",
             "counter_status": "candidate-limiting", "language": "it", "rank": 97, "court": "ti_gerichte", "title": "Responsabilita del medico",
             "regeste": "Responsabilita medica; nesso causale; 2052 cc",
             "counter_evidence": "La responsabilita del medico si presume solo se il nesso causale e dimostrato; in caso contrario si esclude la responsabilita.",
             "counter_reason": "limiting", "counter_confidence": 0.6, "counter_uncertainty": 0.3,
             "expected_class": "SUPPORTED", "expected_reason_code": "supported",
             "note": "positive control: limiting medical-liability sentence, intent marker present, no inversion, no boilerplate, domain and pivot terms present"},
        ],
        "pass_condition": (
            "every injected row is assigned its frozen expected_class, AND at least "
            "min_criteria_flagged distinct defect criteria (INVERTED, OFF-DOMAIN, "
            "BOILERPLATE-ONLY, FRAGMENT, UNBACKED) are exercised, AND the injected rows are "
            "excluded from the population support rate and the verdict."
        ),
    },

    # ---- reporting (charter 4, 5) ----------------------------------------
    "reporting": {
        "per_bundle": ["n_scored", "n_supported", "support_rate", "defect_class_counts", "defect_row_ids"],
        "overall": ["support_rate_primary", "support_rate_secondary", "defect_class_counts", "defect_row_ids"],
        "required_distributions": {
            "language_distribution_of_counter_rows": "count of scored rows per row.language, per bundle and overall (covers the D1 finding that no Italian vocabulary is ever probed)",
            "rank_distribution": "ranks of every scored row, plus the count of SUPPORTED rows outside the conventional top-20 (the pre-registered gate's route to a positive q1/q3)",
            "counter_markers_precision": (
                "markers reported by the artifact vs markers actually present in the cited "
                "evidence string. At accepted head the counter_markers field is ABSENT on every "
                "counter row; the harness therefore reports markers_reported (from the field when "
                "present, else the row's counter_reason), markers_in_cited_evidence and, where "
                "full_text exists, markers_in_row_text as the document-wide union proxy for the "
                "audit's scope finding."
            ),
            "uncertainty_distribution": "counter_uncertainty per scored row, and the subset of unsupported rows whose uncertainty is the LOWEST in their bundle",
            "verbatim_check": "whether counter_evidence occurs verbatim in the row's own full_text (reproducibility of the citation)",
        },
        "determinism": (
            "Identical inputs must produce a byte-identical report. The report embeds "
            "rules_sha256 and the sha256 of every input. No wall-clock, no randomness, no "
            "dict-order dependence: all iteration is over sorted keys / sorted row lists."
        ),
    },

    "write_scope": [
        "frontier/frontier-counter-label-integrity/",
        "tests/frontier/frontier-counter-label-integrity/",
        "results/frontier/frontier-counter-label-integrity/",
        "reports/frontier/frontier-counter-label-integrity/",
        "state/frontier/frontier-counter-label-integrity.json",
        "results/audit/frontier/frontier-counter-label-integrity/",
        "reports/audit/frontier/frontier-counter-label-integrity/",
    ],
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# relpath (under results/product/) -> anchor profile key
BUNDLE_ANCHORS = {
    "gate_packet/38799024807/questions/de-kapitalverletzung.bundle.json": "de-kapitalverletzung",
    "gate_packet/38799024807/questions/fr-bail-entretien.bundle.json": "fr-bail-entretien",
    "gate_packet/38799024807/questions/it-responsabilita-medica.bundle.json": "it-responsabilita-medica",
    "clickable_slice/bundle_live_enriched_20261014T214600Z.json": "responsabilite-penale-entreprise-102cp",
    "clickable_slice/bundle_live_enriched_CYCLE_38649613677.json": "responsabilite-penale-entreprise-102cp",
    "clickable_slice/bundle_live_enriched_CYCLE_38740365477.json": "responsabilite-penale-entreprise-102cp",
    "gate_rehearsal/CYCLE_38754777366_live_bundle.json": "responsabilite-penale-entreprise-102cp",
    "progressive_slice/bundle_CYCLE_38665681083.json": "responsabilite-penale-entreprise-102cp",
    "progressive_slice/bundle_CYCLE_38665681083_v2.json": "responsabilite-penale-entreprise-102cp",
}

PRIMARY_RELPATHS = [
    "gate_packet/38799024807/questions/de-kapitalverletzung.bundle.json",
    "gate_packet/38799024807/questions/fr-bail-entretien.bundle.json",
    "gate_packet/38799024807/questions/it-responsabilita-medica.bundle.json",
]

# Expected labelled-row counts, frozen before scoring (anti-cherry-pick).
EXPECTED_LABEL_COUNTS = {
    "gate_packet/38799024807/questions/de-kapitalverletzung.bundle.json": {"candidate-limiting": 3, "cited": 0},
    "gate_packet/38799024807/questions/fr-bail-entretien.bundle.json": {"candidate-limiting": 1, "cited": 4},
    "gate_packet/38799024807/questions/it-responsabilita-medica.bundle.json": {"candidate-limiting": 3, "cited": 3},
    "clickable_slice/bundle_live_enriched_20261014T214600Z.json": {"candidate-limiting": 9, "candidate-contrary": 2, "cited": 4},
    "clickable_slice/bundle_live_enriched_CYCLE_38649613677.json": {"candidate-limiting": 2, "cited": 10},
    "clickable_slice/bundle_live_enriched_CYCLE_38740365477.json": {"candidate-limiting": 4, "cited": 10},
    "gate_rehearsal/CYCLE_38754777366_live_bundle.json": {"candidate-limiting": 2, "candidate-contrary": 1, "cited": 3},
    "progressive_slice/bundle_CYCLE_38665681083.json": {"candidate-limiting": 5, "candidate-contrary": 4, "cited": 6},
    "progressive_slice/bundle_CYCLE_38665681083_v2.json": {"candidate-limiting": 8, "candidate-contrary": 2, "cited": 6},
}

EXCLUDED_FIXTURES = [
    "clickable_slice/bundle_fixture_kundigung_100.json",
    "gate_packet/offline_machinery_rehearsal/questions/machinery-de.bundle.json",
    "gate_packet/offline_machinery_rehearsal/questions/machinery-fr.bundle.json",
    "gate_packet/offline_machinery_rehearsal/questions/machinery-it.bundle.json",
    "progressive_slice/bundle_CYCLE_38665681083_fixture.json",
]


def build_rules(product_mount: str) -> dict[str, Any]:
    results_root = os.path.join(product_mount, "results", "product")
    if not os.path.isdir(results_root):
        raise SystemExit(f"product mount has no results/product: {product_mount}")

    inputs: list[dict[str, Any]] = []
    drift: list[dict[str, Any]] = []

    relpaths = PRIMARY_RELPATHS + [p for p in BUNDLE_ANCHORS if p not in PRIMARY_RELPATHS]
    for rel in sorted(relpaths):
        path = os.path.join(results_root, rel)
        if not os.path.exists(path):
            drift.append({"relpath": rel, "issue": "declared input missing at mount time"})
            continue
        with open(path, "rb") as fh:
            payload = json.loads(fh.read().decode("utf-8"))
        counts: dict[str, int] = {}
        for d in payload.get("decisions") or []:
            st = (d.get("counter_status") or "none")
            if st != "none":
                counts[st] = counts.get(st, 0) + 1
        expected = EXPECTED_LABEL_COUNTS[rel]
        if counts != expected:
            drift.append({"relpath": rel, "issue": "labelled-row counts differ from frozen expectation",
                          "frozen_expected": expected, "observed": counts})
        qid = os.path.basename(rel).replace(".bundle.json", "")
        entry = {
            "relpath_under_results_product": rel,
            "product_mount_path": path,
            "sha256": sha256_file(path),
            "bytes": os.path.getsize(path),
            "qid": qid,
            "anchor_profile": BUNDLE_ANCHORS[rel],
            "population": "primary" if rel in PRIMARY_RELPATHS else "secondary",
            "query": payload.get("query"),
            "answer_method": (payload.get("answer") or {}).get("method"),
            "fixture_mode": bool((payload.get("provenance") or {}).get("fixture_mode")),
            "frozen_expected_label_counts": expected,
            "n_decisions": len(payload.get("decisions") or []),
        }
        adm = os.path.join(os.path.dirname(path), qid + ".admissibility.json")
        if os.path.exists(adm):
            with open(adm, "rb") as fh:
                adm_payload = json.loads(fh.read().decode("utf-8"))
            entry["admissibility_relpath"] = os.path.relpath(adm, results_root)
            entry["admissibility_sha256"] = sha256_file(adm)
            entry["content_sha256"] = (adm_payload.get("measured") or {}).get("content_sha256")
            entry["admissible"] = adm_payload.get("admissible")
            entry["admissibility_findings"] = adm_payload.get("findings")
        inputs.append(entry)

    excluded = []
    for rel in EXCLUDED_FIXTURES:
        path = os.path.join(results_root, rel)
        excluded.append({
            "relpath_under_results_product": rel,
            "sha256": sha256_file(path) if os.path.exists(path) else None,
            "reason": "fixture_mode: synthetic labels, never a served product artifact",
        })

    post_repair_dir = os.path.join(results_root, "adversarial_retrieval")
    post_repair_src = os.path.join(product_mount, "product", "query", "adversarial_retrieval.py")

    rules = dict(FROZEN)
    rules["schema"] = RULES_SCHEMA
    rules["team_id"] = TEAM_ID
    rules["charter_version"] = CHARTER_VERSION
    rules["inputs"] = inputs
    rules["excluded_inputs"] = excluded
    rules["pre_scoring_drift"] = drift
    rules["post_repair_probe"] = {
        "adversarial_retrieval_results_dir_exists": os.path.isdir(post_repair_dir),
        "adversarial_retrieval_source_exists": os.path.exists(post_repair_src),
        "consequence": (
            "No post-repair artifact exists on the accepted product mount: the accepted chain "
            "has no adversarial-retrieval module and no adversarial-retrieval results. Only the "
            "pre-repair baseline is reported. No baseline is ever presented as a post-repair "
            "result."
        ),
    }
    rules["charter_claims_checked_at_freeze"] = {
        "claim_gate_packet_is_only_accepted_counter_material": (
            "FALSIFIED by the mount: 6 further accepted LIVE bundles issue 39 further counter "
            "labels. The primary population is unchanged (the charter's 7 rows are still decided "
            "on); the additional bundles are a pre-declared replication under the identical "
            "frozen rubric."
        ),
        "claim_adversarial_population_exists_at_accepted_head": (
            "FALSIFIED: results/product/adversarial_retrieval/ does not exist and "
            "product/query/adversarial_retrieval.py does not exist on the accepted mount. The "
            "38828034436 22-of-40 figures stay mechanism evidence and are never used as a "
            "support rate."
        ),
    }
    return rules


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--product-mount", default=os.environ.get("LEX_PRODUCT_MOUNT", "/tmp/lex_accepted/core/product"))
    ap.add_argument("--out", default="results/frontier/frontier-counter-label-integrity/RULES.json")
    ap.add_argument("--force", action="store_true", help="overwrite an existing frozen file (invalidates the freeze)")
    args = ap.parse_args()

    if os.path.exists(args.out) and not args.force:
        print(f"refusing to overwrite frozen rules: {args.out} (pass --force; this invalidates the freeze)")
        return 2

    rules = build_rules(args.product_mount)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    text = json.dumps(rules, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"wrote {args.out}")
    print(f"rules_sha256 {digest}")
    print(f"inputs {len(rules['inputs'])} excluded {len(rules['excluded_inputs'])} drift {len(rules['pre_scoring_drift'])}")
    for d in rules["pre_scoring_drift"]:
        print("  DRIFT:", json.dumps(d, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())