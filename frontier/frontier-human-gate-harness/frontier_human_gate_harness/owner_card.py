"""The four Master Prompt human-gate questions as a short FR/DE owner card.

Acceptance test (3): an owner test card in FR and DE carrying the four Master
Prompt human-gate questions *in intent*, each with a short scale and a free-text
field, plus one suggested real Swiss-law question drawn from the frozen
reality-check legs.

Provenance rules honoured here:
* the four questions are quoted verbatim (EN) from ``LEXMACHINA_MASTER_PROMPT.md``
  § Human product gate; FR/DE are labelled renderings of those sentences;
* the suggested question is the verbatim ``rent-default`` leg question from the
  accepted ``product/reality_check.py`` ``LEGS`` dict (frozen reality-check leg),
  with its DE rendering explicitly labelled as a team translation, plus the DE
  default research query used by the product UI (verbatim source given).
"""
from __future__ import annotations

import json
from typing import Any

from .baseline_view import esc

CARD_SCHEMA_VERSION = "1.0"
QUESTION_IDS = ["q1", "q2", "q3", "q4"]
SCALE_MIN, SCALE_MAX = 1, 5

MASTER_PROMPT_SOURCE = "LEXMACHINA_MASTER_PROMPT.md § Human product gate (verbatim EN)"
LEG_SOURCE = "product/reality_check.py LEGS['rent-default'] (frozen reality-check leg, verbatim FR)"
DE_QUERY_SOURCE = "product/static/query.html #q default value (verbatim DE)"

QUESTIONS: list[dict] = [
    {
        "id": "q1",
        "en": "Did the map expose a relevant branch, exception or decision that was less visible in the list/answer?",
        "fr": "La carte a-t-elle fait apparaître une branche, une exception ou une décision "
              "pertinente qui l'était moins dans la liste / la réponse ?",
        "de": "Hat die Karte einen relevanten Zweck, eine Ausnahme oder eine Entscheidung "
              "sichtbar gemacht, die in der Liste / Antwort weniger sichtbar war?",
        "hint_fr": "Une seule occurrence concrète suffit : citez l'identifiant de décision.",
        "hint_de": "Ein konkreter Fall genügt: Entscheidungs-ID nennen.",
    },
    {
        "id": "q2",
        "en": "Did the map make the jurisprudential structure easier to understand?",
        "fr": "La carte a-t-elle rendu la structure jurisprudentielle plus facile à comprendre ?",
        "de": "Hat die Karte die rechtsprechende Struktur leichter verständlich gemacht?",
        "hint_fr": "Branches, lignes minoritaires, regroupements — ce qui a rendu la lecture plus rapide.",
        "hint_de": "Zweige, Minderheitenlinien, Gruppierungen — was das Lesen erleichtert hat.",
    },
    {
        "id": "q3",
        "en": "Did the map increase confidence that contrary authority had not been hidden?",
        "fr": "La carte a-t-elle augmenté la confiance dans le fait qu'aucune autorité "
              "contraire n'avait été masquée ?",
        "de": "Hat die Karte das Vertrauen erhöht, dass keine widersprechende Autorität "
              "verborgen wurde?",
        "hint_fr": "Contre-autorités visibles, exceptions localisées, absence de zone d'ombre.",
        "hint_de": "Sichtbare Gegenautoritäten, gefundene Ausnahmen, keine blinden Flecken.",
    },
    {
        "id": "q4",
        "en": "Was the combined answer + map preferable to the conventional interface?",
        "fr": "La combinaison réponse + carte était-elle préférable à l'interface conventionnelle ?",
        "de": "War die Kombination Antwort + Karte der konventionellen Schnittstelle vorzuziehen?",
        "hint_fr": "Comparaison directe avec la liste classée conventionnelle vue ci-dessus.",
        "hint_de": "Direkter Vergleich mit der konventionellen Rangliste oben.",
    },
]

SCALE_ANCHORS = {
    "fr": {1: "pas du tout", 2: "peu", 3: "partiellement", 4: "largement", 5: "totalement"},
    "de": {1: "überhaupt nicht", 2: "kaum", 3: "teilweise", 4: "weitgehend", 5: "vollständig"},
}

SUGGESTED_QUESTION = {
    "id": "suggested",
    "question_fr": (
        "Sous quelles conditions un bailleur peut-il résilier un bail d'habitation "
        "pour retard dans le paiement du loyer selon le droit suisse, et quelles "
        "exceptions ou limites jurisprudentielles existent ?"
    ),
    "question_fr_source": LEG_SOURCE,
    "question_de": (
        "Unter welchen Voraussetzungen kann ein Vermieter einen Wohnmietvertrag wegen "
        "Zahlungsverzugs kündigen, und welche Ausnahmen oder richterrechtlichen "
        "Einschränkungen bestehen? (Team-Übersetzung des französischen Originals)"
    ),
    "question_de_source": "Team-Übersetzung von question_fr (Original siehe question_fr_source)",
    "alternative_query_de": "Kündigung Mietvertrag Mietrecht",
    "alternative_query_de_source": DE_QUERY_SOURCE,
    "slug": "rent-default",
    "note": "Der Vorschlag stammt aus den eingefrorenen Reality-Check-Legs des Produkts "
            "/ La suggestion provient des legs reality-check figés du produit.",
}


def card_model() -> dict:
    """Machine-readable card content (also embedded by the offline demo page)."""
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "record_type": "lex_human_gate_card",
        "team_id": "frontier-human-gate-harness",
        "charter_version": 1,
        "question_source": MASTER_PROMPT_SOURCE,
        "question_ids": list(QUESTION_IDS),
        "scale": {"min": SCALE_MIN, "max": SCALE_MAX, "anchors": SCALE_ANCHORS},
        "questions": QUESTIONS,
        "suggested_question": SUGGESTED_QUESTION,
        "data_note": {
            "fr": "Aucune donnée personnelle n'est collectée : ni nom, ni e-mail, ni "
                  "identifiant. Le brouillon exporté ne contient que vos réponses, les "
                  "actions de la session et des horodatages.",
            "de": "Es werden keine personenbezogenen Daten erhoben: kein Name, keine "
                  "E-Mail, keine Kennung. Der exportierte Entwurf enthält nur Antworten, "
                  "Sitzungsaktionen und Zeitstempel.",
        },
        "next_step": {
            "fr": "Exportez le brouillon, puis : python -m frontier_human_gate_harness.cli "
                  "--finalize <brouillon.json> --out results/frontier/frontier-human-gate-harness",
            "de": "Entwurf exportieren, dann: python -m frontier_human_gate_harness.cli "
                  "--finalize <entwurf.json> --out results/frontier/frontier-human-gate-harness",
        },
    }


def _scale_radios(qid: str, lang: str, name_suffix: str = "") -> str:
    anchors = SCALE_ANCHORS[lang]
    out = []
    for value in range(SCALE_MIN, SCALE_MAX + 1):
        label = esc(anchors[value])
        out.append(
            f'<label class="lex-scale"><input type="radio" name="{esc(qid)}_scale{esc(name_suffix)}" '
            f'value="{value}"><span class="lex-scale-v">{value}</span>'
            f'<span class="lex-scale-a">{label}</span></label>'
        )
    return '<div class="lex-scale-row">' + "".join(out) + "</div>"


def render_card_body(lang: str, name_suffix: str = "") -> str:
    """HTML fragment for one language (no <script>; the export script is separate).

    ``name_suffix`` disambiguates radio groups when both languages are embedded in
    one page (the offline demo); the export script scopes by section, not by name.
    """
    if lang not in ("fr", "de"):
        raise ValueError(f"unsupported card language: {lang}")
    model = card_model()
    title = {"fr": "Porte humaine du Main Prompt — fiche de test propriétaire",
             "de": "Menschliche Product-Gate des Master Prompt — Owner-Testkarte"}[lang]
    intro = {
        "fr": ("Répondez aux 4 questions après avoir vu <b>réponse + liste</b> ET "
               "<b>réponse + carte</b> sur la <i>même</i> requête. Échelle 1–5, "
               "puis commentaire libre."),
        "de": ("Beantworten Sie die 4 Fragen, nachdem Sie <b>Antwort + Liste</b> UND "
               "<b>Antwort + Karte</b> zur <i>gleichen</i> Anfrage gesehen haben. "
               "Skala 1–5, dann freier Kommentar."),
    }[lang]
    questions_html = []
    for q in QUESTIONS:
        text = q[lang]
        hint = q[f"hint_{lang}"]
        questions_html.append(f"""
<section class="lex-card-q" data-qid="{q['id']}">
  <h3><span class="lex-qid">{q['id'].upper()}</span> {esc(text)}</h3>
  <p class="lex-q-en">{esc(q['en'])}</p>
  <p class="lex-q-hint">{esc(hint)}</p>
  {_scale_radios(q['id'], lang, name_suffix)}
  <textarea class="lex-q-text" data-qid="{q['id']}" rows="2"
            placeholder="{esc({'fr': 'Commentaire libre (facultatif si l’échelle suffit)…',
                               'de': 'Freier Kommentar (optional, wenn die Skala reicht)…'}[lang])}"></textarea>
</section>""")
    sq = SUGGESTED_QUESTION
    sq_html = f"""
<section class="lex-card-sq">
  <h3>{'Question suggérée (leg figé rent-default)' if lang == 'fr' else 'Vorgeschlagene Frage (eingefrorenes Leg rent-default)'}</h3>
  <p class="lex-sq">{'<b>FR (original):</b> ' + esc(sq['question_fr']) if lang == 'fr' else '<b>DE:</b> ' + esc(sq['question_de'])}</p>
  <p class="lex-src">{'source : ' + esc(sq['question_fr_source']) if lang == 'fr' else 'Quelle: ' + esc(sq['question_de_source'])}</p>
  <p class="lex-sq-alt">{'requête alternative DE : <code>' + esc(sq['alternative_query_de']) + '</code>'
      if lang == 'de' else 'requête alternative DE : <code>' + esc(sq['alternative_query_de']) + '</code>'}</p>
  <p class="lex-src">{'source : ' + esc(sq['alternative_query_de_source'])}</p>
</section>"""
    return f"""
<h1>{esc(title)}</h1>
<p class="lex-intro">{intro}</p>
<p class="lex-src">{'Questions : ' + esc(model['question_source'])}</p>
<div class="lex-card-questions">{''.join(questions_html)}</div>
{sq_html}
<section class="lex-card-export">
  <label class="lex-session">ID de session / Sitzungs-ID
    <input type="text" class="lex-session-input" id="lexSessionId{esc(name_suffix)}"
           placeholder="z. B. owner-2026-10-14-a" autocomplete="off">
  </label>
  <button type="button" id="lexCardExport">{'Exporter le brouillon de réponses / Antworten exportieren'}</button>
  <p class="lex-src">{esc(model['data_note'][lang])}</p>
  <p class="lex-src">{esc(model['next_step'][lang])}</p>
</section>
"""


CARD_SCRIPT = r"""
(function () {
  var QIDS = ["q1", "q2", "q3", "q4"];
  function nowIso() { return new Date().toISOString().replace(/\.\d{3}Z$/, "Z"); }
  function collectAnswers() {
    var answers = {};
    QIDS.forEach(function (qid) {
      var section = document.querySelector('.lex-card-q[data-qid="' + qid + '"]');
      if (!section) { return; }
      var picked = section.querySelector('input[type="radio"]:checked');
      var box = section.querySelector("textarea.lex-q-text");
      var text = box ? box.value.trim() : "";
      if (!picked && !text) { return; }            /* unanswered: never invent */
      answers[qid] = {
        scale: picked ? parseInt(picked.value, 10) : null,
        text: text,
        answered_at: nowIso()
      };
    });
    return answers;
  }
  function exportDraft() {
    var answers = collectAnswers();
    var sessionInput = document.getElementById("lexSessionId");
    var sessionId = sessionInput && sessionInput.value.trim() ? sessionInput.value.trim() : null;
    var missing = QIDS.filter(function (qid) { return !Object.prototype.hasOwnProperty.call(answers, qid); });
    return {
      schema_version: "1.0",
      record_type: "lex_human_gate_session",
      team_id: "frontier-human-gate-harness",
      charter_version: 1,
      session_id: sessionId,
      session_id_origin: sessionId ? "card_field" : null,
      status: "draft",
      source: "card",
      query: null,
      bundle_ref: { query: null, n_decisions: null },
      bundle_sha256: null,
      query_sha256: null,
      bundle_hash_status: "not_verified",
      started_at: null,
      ended_at: nowIso(),
      wall_clock_seconds: null,
      view_mode_initial: null,
      view_mode_final: null,
      actions: [],
      decisions_opened: [],
      counter_authorities_opened: [],
      answers: answers,
      missing_answers: missing,
      latency: { baseline_render_ms: null, session_wall_clock_seconds: null }
    };
  }
  function download() {
    var draft = exportDraft();
    var blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = (draft.session_id || "lex_card_draft") + ".json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    var status = document.getElementById("lexCardExportStatus");
    if (status) {
      status.textContent = "brouillon exporté · " + Object.keys(draft.answers).length +
        "/4 réponses · manquantes: " + (draft.missing_answers.join(", ") || "aucune");
    }
  }
  window.LexCard = { collectAnswers: collectAnswers, exportDraft: exportDraft };
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("lexCardExport");
    if (btn) { btn.addEventListener("click", download); }
  });
})();
"""


CARD_CSS = """
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#17191f;background:#f5f6f8}
*{box-sizing:border-box}
body{margin:0;padding:22px;max-width:760px}
h1{font-size:18px;margin:0 0 6px}
h3{font-size:14px;margin:16px 0 4px}
.lex-intro{font-size:13px;line-height:1.5;color:#33383f}
.lex-src{font-size:11px;color:#737b88;margin:3px 0}
.lex-card-q{background:#fff;border:1px solid #e2e5ea;border-radius:10px;padding:10px 12px;margin:10px 0}
.lex-qid{display:inline-block;background:#eef0f4;border-radius:20px;padding:1px 7px;font-size:11px;color:#59616d;margin-right:6px}
.lex-q-en{font-size:11px;color:#737b88;margin:2px 0}
.lex-q-hint{font-size:12px;color:#59616d;margin:2px 0 8px}
.lex-scale-row{display:flex;flex-wrap:wrap;gap:6px}
.lex-scale{display:inline-flex;align-items:center;gap:4px;border:1px solid #d7dbe2;border-radius:8px;padding:4px 7px;font-size:12px;background:#fff}
.lex-scale-v{font-weight:700}
.lex-scale-a{color:#59616d}
textarea{width:100%;margin-top:8px;border:1px solid #d7dbe2;border-radius:8px;padding:7px;font:inherit;font-size:12px;resize:vertical}
.lex-card-sq{background:#f7f8fa;border:1px solid #eceef2;border-radius:10px;padding:10px 12px;margin:10px 0}
.lex-sq{font-size:13px;line-height:1.5;margin:4px 0}
.lex-card-export{margin-top:14px;background:#fff;border:1px solid #e2e5ea;border-radius:10px;padding:10px 12px}
.lex-session{display:block;font-size:12px;color:#59616d;margin-bottom:8px}
.lex-session input{display:block;width:100%;margin-top:4px;border:1px solid #d7dbe2;border-radius:8px;padding:7px;font:inherit}
button{cursor:pointer;font-weight:650;border:1px solid #17191f;background:#17191f;color:#fff;border-radius:8px;padding:9px 12px}
#lexCardExportStatus{font-size:12px;color:#27845b;margin-top:7px}
"""


def render_card_document(lang: str) -> str:
    """Self-contained offline card page (FR or DE). No network, no external asset."""
    body = render_card_body(lang)
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LexMachina — {'Fiche porte humaine' if lang == 'fr' else 'Owner-Testkarte'}</title>
<style>{CARD_CSS}</style>
</head>
<body data-lex-card-lang="{lang}">
{body}
<p id="lexCardExportStatus" class="lex-src"></p>
<script>{CARD_SCRIPT}</script>
</body>
</html>
"""


def card_json_bytes() -> bytes:
    return (json.dumps(card_model(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
