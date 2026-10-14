/* LexGateSwitch — list<->map view switch for product/static/query.html.
 *
 * Charter v1, team frontier-human-gate-harness.
 *
 * Contract (see frontier/frontier-human-gate-harness/INTEGRATION_CONTRACT.md):
 *   - BOTH views are rendered from the SAME already-loaded query_result_bundle
 *     object handed in by the host page (config.getBundle). This file contains
 *     NO network capability whatsoever - no HTTP client, no polling, no beacons,
 *     no event streams - so switching views can never re-retrieve anything.
 *   - The bundle is never mutated (no sort in place, no property writes); the
 *     offline test suite deep-freezes it and fails on any write.
 *   - The list is the CONVENTIONAL BASELINE: rank, decision_id, court, date,
 *     language, citation, snippet, source link — no cluster colour, no
 *     proximity, no counter grouping, no outlier flags.
 *   - buildListModel / renderRowsHtml mirror frontier_human_gate_harness.baseline_view
 *     byte for byte (parity enforced offline).
 *
 * Classic script: works as <script src="/static/lex_gate_switch.js"></script>
 * and can be required() by Node for tests (no DOM access at load time).
 */
var LexGateSwitch = (function () {
  "use strict";

  var LIST_FIELDS = ["rank", "decision_id", "court", "decision_date", "language",
                     "citation", "snippet", "canonical_url"];
  var QUESTION_IDS = ["q1", "q2", "q3", "q4"];
  var SNIPPET_LIMIT = 300;
  var LABEL = "Liste classée conventionnelle (baseline) / Konventionelle Rangliste (Baseline)";
  var NOTE_FR = "Aucune information de carte dans cette vue : rang, tribunal, date, langue, citation, extrait, source.";
  var NOTE_DE = "Keine Karteninformation in dieser Ansicht: Rang, Gericht, Datum, Sprache, Zitat, Auszug, Quelle.";
  var COUNTER_EXEMPT = ["none", "cited", "supporting-candidate", "context", "unclassified"];

  function text(value) {
    return (value === null || value === undefined) ? "" : String(value);
  }

  function esc(value) {
    return text(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /* rankOf mirrors frontier_human_gate_harness.baseline_view._rank exactly:
     JSON numbers/booleans truncate toward zero; strings must be DECIMAL
     numeric per Python float()'s grammar (underscores only between digits);
     Number()'s extra acceptance (hex "0x10", binary "0b101", non-ASCII digits)
     is deliberately rejected so both renderers coerce identically; anything
     else (null, arrays, objects, "abc", "", "inf", "nan") is 0. */
  var DECIMAL_RE = /^[+-]?(?:(?:\d(?:_?\d)*)(?:\.(?:\d(?:_?\d)*)?)?|\.\d(?:_?\d)*)(?:[eE][+-]?\d(?:_?\d)*)?$/;
  function rankOf(value) {
    var number;
    if (typeof value === "number" || typeof value === "boolean") {
      number = Number(value);
    } else if (typeof value === "string") {
      var trimmed = value.trim();
      if (!DECIMAL_RE.test(trimmed)) { return 0; }
      number = Number(trimmed.replace(/_/g, ""));
    } else {
      return 0;
    }
    if (!isFinite(number)) { return 0; }
    return Math.trunc(number);
  }

  function citationOf(value) {
    if (Array.isArray(value)) {
      var parts = [];
      for (var i = 0; i < value.length; i++) { parts.push(text(value[i])); }
      return parts.join(" · ");
    }
    return text(value);
  }

  /* snippetOf mirrors baseline_view._snippet: truncation counts CODE POINTS
     (Python str semantics), not UTF-16 units — Array.from splits by code point
     so astral characters (e.g. 𝄞) cannot desynchronise the two renderers. */
  function snippetOf(value) {
    var value0 = text(value);
    var chars = Array.from(value0);
    return chars.length > SNIPPET_LIMIT
      ? chars.slice(0, SNIPPET_LIMIT).join("") + "\u2026"
      : value0;
  }

  function buildListModel(bundle) {
    var raw = (bundle && Array.isArray(bundle.decisions)) ? bundle.decisions : [];
    var kept = [];
    for (var i = 0; i < raw.length; i++) {
      /* same filter as Python isinstance(d, dict): plain objects only —
         arrays and primitives are dropped by BOTH renderers */
      if (raw[i] && typeof raw[i] === "object" && !Array.isArray(raw[i])) {
        kept.push(raw[i]);
      }
    }
    var order = [];
    for (var j = 0; j < kept.length; j++) {
      order.push({ decision: kept[j], index: j, rank: rankOf(kept[j].rank) });
    }
    /* stable by construction: equal ranks keep bundle order */
    order.sort(function (a, b) { return (a.rank - b.rank) || (a.index - b.index); });
    var rows = [];
    for (var k = 0; k < order.length; k++) {
      var decision = order[k].decision;
      rows.push({
        rank: order[k].rank,
        decision_id: text(decision.decision_id),
        court: text(decision.court),
        decision_date: text(decision.decision_date),
        language: text(decision.language),
        citation: citationOf(decision.citation),
        snippet: snippetOf(decision.snippet),
        canonical_url: text(decision.canonical_url)
      });
    }
    return rows;
  }

  function sourceHtml(url) {
    var lowered = text(url).toLowerCase();
    if (lowered.indexOf("http://") === 0 || lowered.indexOf("https://") === 0) {
      return '<a class="lex-source" href="' + esc(url) +
             '" target="_blank" rel="noopener">source</a>';
    }
    return '<span class="lex-source-missing">\u2014</span>';
  }

  function renderRow(row) {
    return '<li class="lex-row" data-rank="' + row.rank +
           '" data-decision-id="' + esc(row.decision_id) + '">' +
           '<span class="lex-rank">#' + row.rank + '</span>' +
           '<span class="lex-citation">' + esc(row.citation) + '</span>' +
           '<span class="lex-court">' + esc(row.court) + '</span>' +
           '<span class="lex-date">' + esc(row.decision_date) + '</span>' +
           '<span class="lex-lang">' + esc(row.language) + '</span>' +
           '<span class="lex-decision-id">' + esc(row.decision_id) + '</span>' +
           sourceHtml(row.canonical_url) +
           '<p class="lex-snippet">' + esc(row.snippet) + '</p>' +
           '</li>';
  }

  function renderRowsHtml(bundle) {
    var rows = buildListModel(bundle);
    var out = [];
    for (var i = 0; i < rows.length; i++) { out.push(renderRow(rows[i])); }
    return out.join("\n");
  }

  function isCounterDecision(decision) {
    var status = decision && decision.counter_status;
    if (!status) { return false; }
    return COUNTER_EXEMPT.indexOf(status) === -1;
  }

  function bundleRefOf(bundle) {
    return {
      query: (bundle && bundle.query !== null && bundle.query !== undefined)
        ? String(bundle.query) : null,
      n_decisions: (bundle && Array.isArray(bundle.decisions)) ? bundle.decisions.length : 0
    };
  }

  function createController(opts) {
    opts = opts || {};
    if (typeof opts.getBundle !== "function") {
      throw new Error("LexGateSwitch.createController requires opts.getBundle");
    }
    var now = (typeof opts.now === "function") ? opts.now : function () {
      return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    };
    var controller = {
      viewMode: "map",
      actions: [],
      decisionsOpened: [],
      counterOpened: [],
      startedAt: now(),
      lastListHtml: null,

      getBundle: function () { return opts.getBundle(); },

      bundleRef: function () { return bundleRefOf(opts.getBundle()); },

      _record: function (event, ref) {
        var action = { at: now(), view_mode: controller.viewMode, event: event, ref: ref || null };
        controller.actions.push(action);
        if (typeof opts.onAction === "function") { opts.onAction(action); }
        return action;
      },

      switchTo: function (mode) {
        if (mode !== "list" && mode !== "map") { throw new Error("bad mode: " + mode); }
        controller.viewMode = mode;
        if (mode === "list") {
          controller.lastListHtml = renderRowsHtml(opts.getBundle());
        }
        controller._record("switch", null);
        return { view_mode: mode, bundle_ref: controller.bundleRef(), mutated: false };
      },

      toggle: function () {
        return controller.switchTo(controller.viewMode === "list" ? "map" : "list");
      },

      openDecision: function (id) {
        var ref = text(id);
        if (typeof opts.openDetail === "function") { opts.openDetail(ref); }
        controller._record("open_decision", ref);
        if (controller.decisionsOpened.indexOf(ref) === -1) {
          controller.decisionsOpened.push(ref);
        }
        return ref;
      },

      openCounter: function (id) {
        var ref = text(id);
        var bundle = opts.getBundle();
        var decisions = (bundle && Array.isArray(bundle.decisions)) ? bundle.decisions : [];
        var found = null;
        for (var i = 0; i < decisions.length; i++) {
          if (text(decisions[i].decision_id) === ref) { found = decisions[i]; break; }
        }
        if (!found || !isCounterDecision(found)) { return false; }
        controller._record("open_counter", ref);
        if (controller.counterOpened.indexOf(ref) === -1) {
          controller.counterOpened.push(ref);
        }
        return true;
      },

      exportDraft: function (meta) {
        meta = meta || {};
        var ref = controller.bundleRef();
        var sessionId = Object.prototype.hasOwnProperty.call(meta, "session_id")
          ? meta.session_id : null;
        return {
          schema_version: "1.0",
          record_type: "lex_human_gate_session",
          team_id: "frontier-human-gate-harness",
          charter_version: 1,
          session_id: sessionId || null,
          session_id_origin: sessionId ? (meta.session_id_origin || "draft") : null,
          status: "draft",
          source: "switch",
          query: ref.query,
          bundle_ref: ref,
          bundle_sha256: null,
          query_sha256: null,
          bundle_hash_status: "not_verified",
          started_at: controller.startedAt,
          ended_at: now(),
          wall_clock_seconds: null,
          view_mode_initial: meta.view_mode_initial || "map",
          view_mode_final: controller.viewMode,
          actions: controller.actions.slice(),
          decisions_opened: controller.decisionsOpened.slice(),
          counter_authorities_opened: controller.counterOpened.slice(),
          answers: {},
          missing_answers: QUESTION_IDS.slice(),
          latency: { baseline_render_ms: null, session_wall_clock_seconds: null }
        };
      }
    };
    return controller;
  }

  var attached = null;

  function renderListInto(element, bundle) {
    element.innerHTML =
      '<div class="lex-baseline-view">' +
      '<h2 class="lex-baseline-title">' + esc(LABEL) + '</h2>' +
      '<p class="lex-baseline-note">' + esc(NOTE_FR) + '</p>' +
      '<p class="lex-baseline-note">' + esc(NOTE_DE) + '</p>' +
      '<ol class="lex-ranked-list" start="1">' + renderRowsHtml(bundle) + '</ol>' +
      '</div>';
  }

  function setPressed(button, pressed) {
    if (button) { button.setAttribute("aria-pressed", pressed ? "true" : "false"); }
  }

  function applyVisibility(config, controller) {
    var showingList = controller.viewMode === "list";
    if (config.listEl) { config.listEl.hidden = !showingList; }
    if (config.mapEl) { config.mapEl.hidden = showingList; }
    var extras = config.extraPanes || [];
    for (var i = 0; i < extras.length; i++) { extras[i].hidden = true; }
    if (config.toggleButton) {
      config.toggleButton.textContent = showingList ? "\u25C6 Carte" : "\u25A2 Liste";
      setPressed(config.toggleButton, showingList);
    }
    if (config.statusEl) {
      var ref = controller.bundleRef();
      config.statusEl.textContent = showingList
        ? ("Vue : liste conventionnelle \u00b7 " + ref.n_decisions + " d\u00e9cisions")
        : ("Vue : carte (produit) \u00b7 " + ref.n_decisions + " d\u00e9cisions \u00b7 m\u00eame bundle");
    }
  }

  function attach(config) {
    config = config || {};
    if (attached) { return attached; }
    if (typeof config.getBundle !== "function") {
      throw new Error("LexGateSwitch.attach requires config.getBundle");
    }
    var controller = createController({
      getBundle: config.getBundle,
      now: config.now,
      onAction: config.onAction,
      openDetail: config.openDetail
    });

    if (config.toolbarEl && typeof document !== "undefined") {
      var toggle = document.createElement("button");
      toggle.type = "button";
      toggle.id = "lexViewToggle";
      toggle.className = "lex-view-toggle";
      toggle.setAttribute("aria-pressed", "false");
      toggle.textContent = "\u25A2 Liste";
      config.toolbarEl.insertBefore(toggle, config.toolbarEl.firstChild);
      config.toggleButton = toggle;
      toggle.addEventListener("click", function () {
        controller.toggle();
        applyVisibility(config, controller);
      });

      if (config.mountExportButton !== false) {
        var exportBtn = document.createElement("button");
        exportBtn.type = "button";
        exportBtn.id = "lexSessionExport";
        exportBtn.className = "lex-session-export";
        exportBtn.textContent = "Exporter la session";
        config.toolbarEl.appendChild(exportBtn);
        exportBtn.addEventListener("click", function () {
          var draft = controller.exportDraft({ session_id: config.session_id || null });
          var blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" });
          var url = URL.createObjectURL(blob);
          var link = document.createElement("a");
          link.href = url;
          link.download = (draft.session_id || "lex_session_draft") + ".json";
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        });
      }
    }

    if (config.listEl && typeof document !== "undefined") {
      renderListInto(config.listEl, config.getBundle());
      controller.lastListHtml = renderRowsHtml(config.getBundle());
    }

    attached = { controller: controller, config: config };
    if (typeof window !== "undefined") { window.__LEX_GATE_SWITCH__ = attached; }
    applyVisibility(config, controller);
    return controller;
  }

  function notifyBundleChanged() {
    if (!attached) { return; }
    var config = attached.config;
    var controller = attached.controller;
    if (controller.viewMode === "list" && config.listEl) {
      renderListInto(config.listEl, config.getBundle());
      controller.lastListHtml = renderRowsHtml(config.getBundle());
    }
  }

  return {
    LIST_FIELDS: LIST_FIELDS,
    QUESTION_IDS: QUESTION_IDS,
    LABEL: LABEL,
    NOTE_FR: NOTE_FR,
    buildListModel: buildListModel,
    renderRowsHtml: renderRowsHtml,
    createController: createController,
    attach: attach,
    notifyBundleChanged: notifyBundleChanged
  };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = LexGateSwitch;
}
if (typeof window !== "undefined") {
  window.LexGateSwitch = LexGateSwitch;
}
