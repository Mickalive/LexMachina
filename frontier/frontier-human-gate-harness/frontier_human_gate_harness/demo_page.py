"""Offline, self-contained clickable page: baseline list <-> map switch + card + capture.

This is the "single sitting" artifact of the charter: one HTML file, no network,
no server, containing

* the conventional ranked-list baseline rendered from the fixture bundle,
* the SAME bundle handed to the real switch component (``static/lex_gate_switch.js``)
  so the list<->map switch runs over one already-loaded bundle,
* the FR/DE owner card (rendered from the same ``owner_card`` model the standalone
  cards use),
* one export button producing a single session draft that
  ``python -m frontier_human_gate_harness.cli --finalize`` accepts.

The map pane is an explicitly labelled PLACEHOLDER: this team owns no map
renderer (``frontier-query-map-ui`` owns map rendering, the product owns the
real canvas). Nothing about the map is fabricated here — the pane states where
the product's map goes.
"""
from __future__ import annotations

import json
from pathlib import Path

from .baseline_view import BASELINE_LABEL_DE, BASELINE_LABEL_FR, esc, render_rows_html
from .bundle_io import bundle_sha256
from .owner_card import render_card_body

HARNESS_ROOT = Path(__file__).resolve().parents[1]
SWITCH_JS = HARNESS_ROOT / "static" / "lex_gate_switch.js"

DEMO_CSS = """
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#17191f;background:#f5f6f8}
*{box-sizing:border-box}
body{margin:0;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{padding:10px 14px;background:#fff;border-bottom:1px solid #e2e5ea}
h1{font-size:15px;margin:0}
.meta{color:#68707d;font-size:11px;margin:3px 0 0}
.note{color:#6b5b1e;background:#fffbe6;border:1px solid #f0d7a8;padding:6px 9px;
      border-radius:8px;font-size:11px;margin-top:7px;max-width:900px}
#lexToolbar{display:flex;gap:7px;align-items:center;padding:8px 12px;background:#fff;
            border-bottom:1px solid #e2e5ea;flex-wrap:wrap}
#lexToolbar button{border:1px solid #d7dbe2;border-radius:8px;padding:7px 10px;
                   background:#fff;cursor:pointer;font-weight:650;font-size:12px}
#lexToolbar button[aria-pressed="true"]{background:#17191f;color:#fff;border-color:#17191f}
#lexStage{flex:1;min-height:0;position:relative}
.lex-pane{position:absolute;inset:0;overflow:auto;padding:12px 16px}
.lex-pane[hidden]{display:none}
.lex-map-placeholder{display:flex;flex-direction:column;gap:8px;align-items:flex-start;
                     justify-content:center;height:100%;color:#59616d;font-size:13px;
                     background:repeating-linear-gradient(45deg,#fafbfc,#fafbfc 12px,#f2f4f7 12px,#f2f4f7 24px);
                     border:1px dashed #c9ced6;border-radius:10px;padding:18px}
.lex-map-placeholder b{color:#17191f}
.lex-card-lang{display:flex;gap:6px;margin-bottom:8px}
.lex-card-lang button{border:1px solid #d7dbe2;border-radius:8px;padding:5px 9px;
                      background:#fff;cursor:pointer;font-size:12px}
.lex-card-lang button[aria-pressed="true"]{background:#17191f;color:#fff;border-color:#17191f}
#lexDemoStatus{font-size:11px;color:#27845b}
footer{padding:7px 14px;background:#fff;border-top:1px solid #e2e5ea;color:#737b88;font-size:11px}
"""

DEMO_SCRIPT_BOOTSTRAP = r"""
(function () {
  var bundle = window.__LEX_FIXTURE_BUNDLE__;
  var cardView = document.getElementById("lexCardView");
  var controller = LexGateSwitch.attach({
    getBundle: function () { return bundle; },
    mapEl: document.getElementById("lexMapView"),
    listEl: document.getElementById("lexListView"),
    toolbarEl: document.getElementById("lexToolbar"),
    statusEl: document.getElementById("lexDemoStatus"),
    extraPanes: [cardView],
    mountExportButton: false,
    session_id: null
  });
  window.__LEX_SWITCH_CONTROLLER__ = controller;
  window.__LEX_ACTIVE_CARD__ = "fr";
  var cardRoots = {
    fr: document.getElementById("lexCardFr"),
    de: document.getElementById("lexCardDe")
  };

  function showCard(lang) {
    window.__LEX_ACTIVE_CARD__ = lang;
    cardRoots.fr.hidden = (lang !== "fr");
    cardRoots.de.hidden = (lang !== "de");
    cardView.hidden = false;
    document.getElementById("lexListView").hidden = true;
    document.getElementById("lexMapView").hidden = true;
    document.querySelectorAll(".lex-card-lang button").forEach(function (btn) {
      btn.setAttribute("aria-pressed", String(btn.dataset.lang === lang));
    });
    controller._record("render", "card:" + lang);
  }

  document.querySelectorAll(".lex-card-lang button").forEach(function (btn) {
    btn.addEventListener("click", function () { showCard(btn.dataset.lang); });
  });
  document.getElementById("lexDemoCardTab").addEventListener("click", function () {
    showCard(window.__LEX_ACTIVE_CARD__ || "fr");
  });

  function collectCardAnswers() {
    var root = cardRoots[window.__LEX_ACTIVE_CARD__ || "fr"];
    var answers = {};
    ["q1", "q2", "q3", "q4"].forEach(function (qid) {
      var section = root.querySelector('.lex-card-q[data-qid="' + qid + '"]');
      if (!section) { return; }
      var picked = section.querySelector('input[type="radio"]:checked');
      var box = section.querySelector("textarea.lex-q-text");
      var text = box ? box.value.trim() : "";
      if (!picked && !text) { return; }   /* unanswered: never invent */
      answers[qid] = {
        scale: picked ? parseInt(picked.value, 10) : null,
        text: text,
        answered_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z")
      };
    });
    return answers;
  }

  function exportSessionDraft() {
    var draft = controller.exportDraft({ session_id: null, view_mode_initial: "map" });
    draft.source = "demo";
    draft.answers = collectCardAnswers();
    draft.missing_answers = ["q1", "q2", "q3", "q4"].filter(function (qid) {
      return !Object.prototype.hasOwnProperty.call(draft.answers, qid);
    });
    var idBox = cardRoots[window.__LEX_ACTIVE_CARD__ || "fr"].querySelector(".lex-session-input");
    if (idBox && idBox.value.trim()) {
      draft.session_id = idBox.value.trim();
      draft.session_id_origin = "card_field";
    }
    return draft;
  }

  document.getElementById("lexDemoExport").addEventListener("click", function () {
    var draft = exportSessionDraft();
    var blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = (draft.session_id || "lex_session_draft") + ".json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    document.getElementById("lexDemoStatus").textContent =
      "brouillon export\u00e9 \u00b7 r\u00e9ponses " + Object.keys(draft.answers).length +
      "/4 \u00b7 manquantes: " + (draft.missing_answers.join(", ") || "aucune") +
      " \u00b7 actions " + draft.actions.length;
  });
})();
"""


def render_demo_page(bundle: dict) -> str:
    if not SWITCH_JS.is_file():
        raise FileNotFoundError(
            f"switch component missing: {SWITCH_JS} — build static/lex_gate_switch.js first"
        )
    switch_source = SWITCH_JS.read_text(encoding="utf-8")
    bundle_json = json.dumps(bundle, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    rows = render_rows_html(bundle)
    sha = bundle_sha256(bundle)
    n = len(bundle.get("decisions") or [])
    fr_body = render_card_body("fr", name_suffix="_fr")
    de_body = render_card_body("de", name_suffix="_de")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LexMachina — harness propriétaire (liste ↔ carte)</title>
<style>{DEMO_CSS}</style>
</head>
<body>
<header>
  <h1>LEX / LexMachina — harness de porte humaine · {BASELINE_LABEL_FR} / {BASELINE_LABEL_DE}</h1>
  <p class="meta">requête / Abfrage : <b>{esc(bundle.get("query"))}</b> · {n} décisions ·
     bundle sha256 <code>{sha}</code></p>
  <p class="note">Une seule page, aucun réseau. La liste et la carte (dans le produit) lisent le
     <i>même</i> bundle chargé : la comparaison A/B porte sur littéralement les mêmes pièces.
     Les 4 questions du Main Prompt sont dans l'onglet Fiche ; l'export produit le brouillon de
     session que la CLI finalise en <code>results/frontier/frontier-human-gate-harness/session_&lt;id&gt;.json</code>.</p>
</header>
<div id="lexToolbar">
  <button type="button" id="lexDemoCardTab">✎ Fiche 4 questions</button>
  <button type="button" id="lexDemoExport">Exporter la session</button>
  <span id="lexDemoStatus" class="meta"></span>
</div>
<div id="lexStage">
  <div id="lexListView" class="lex-pane" hidden>
    <div class="lex-baseline-view">
      <h2>{BASELINE_LABEL_FR} / {BASELINE_LABEL_DE}</h2>
      <p class="note">Aucune information de carte dans cette vue : rang, tribunal, date, langue,
         citation, extrait, source. Rendu serveur (identique au rendu JS — parité vérifiée hors-ligne).</p>
      <ol class="lex-ranked-list" start="1">
{rows}
      </ol>
    </div>
  </div>
  <div id="lexMapView" class="lex-pane" hidden>
    <div class="lex-map-placeholder">
      <b>Panneau carte — endroit où le produit rend la carte.</b>
      <span>Ce harness ne fabrique aucune carte : le rendu de carte appartient au produit
            (<code>product/static/query.html</code>, canvas <code>#cv</code>) et à l'équipe
            frontier-query-map-ui. Le basculement liste ↔ carte s'exécute ici sur le même bundle
            chargé ; dans le produit, ce panneau est le <code>#mapWrap</code> réel.</span>
      <span>Bundle chargé : {n} décisions · sha256 {sha[:16]}… · aucune requête de récupération
            n'est déclenchée par le basculement.</span>
    </div>
  </div>
  <div id="lexCardView" class="lex-pane" hidden>
    <div class="lex-card-lang">
      <button type="button" data-lang="fr" aria-pressed="true">Français</button>
      <button type="button" data-lang="de" aria-pressed="false">Deutsch</button>
    </div>
    <div id="lexCardFr" class="lex-card-root">{fr_body}</div>
    <div id="lexCardDe" class="lex-card-root" hidden>{de_body}</div>
  </div>
</div>
<footer>frontier-human-gate-harness v1 · fixture {sha[:16]}… · rendu déterministe hors-ligne ·
        aucun flux, aucune requête réseau, aucune donnée personnelle collectée</footer>
<script>window.__LEX_FIXTURE_BUNDLE__ = {bundle_json};</script>
<script>{switch_source}</script>
<script>{DEMO_SCRIPT_BOOTSTRAP}</script>
<script>/* card tab handled in the bootstrap above */</script>
</body>
</html>
"""
