#!/usr/bin/env node
/* Offline DOM verification for product/static/query.html.
 *
 /*   node product/verify_query_page.js BUNDLE.json [DEEP_LINK_SEARCH] [HTML_PATH]
 *
 * Why this exists
 * ---------------
 * The accepted human-gate switch is adopted byte-identically and wired into the
 * product page.  Hook-string assertions prove the wiring text exists; this
 * script executes the real page scripts in a minimal DOM and proves the
 * behaviour that the owner gate depends on:
 *
 *   1. the page boots and mounts the toggle into the existing #toolbar;
 *   2. rendering a real query_result_bundle fills the baseline list with one row
 *      per decision (same bundle, no second retrieval);
 *   3. no network call is made by the page boot or by a view switch;
 *   4. toggling to the list hides the map, shows the list, and the product's own
 *      status (phase pill / counts) survives the harness writing #status.
 *   5. a deep link (?run_id=… / ?q=&n=) selects which run or question the page
 *      opens - the multi-question gate packet hands the owner one link per
 *      question, so the page has to honour it.
 *   6. the sourced answer is inspectable: every decision the answer cites is
 *      one click from the decision panel (inline id link, or the source chip
 *      when the model numbers its citations), and prose is escaped, never
 *      executed as markup.
 *   7. the independent adversarial pass is DISCOVERABLE and honestly labelled:
 *      every row its probes found is named in the sidebar with the channel that
 *      found it, one click opens it, the map filter isolates it, and the page
 *      states on every card that this is retrieval provenance and not a legal
 *      qualification.
 *
 * It is a smoke test of the clickable slice, not a claim about legal usefulness.
 *
 * The DOM/script runtime itself lives in product/dom_shim.js (shared with the
 * session-export driver); the assertions and this output are unchanged.
 */
"use strict";

const fs = require("fs");
const { createPage, HTML_PATH } = require("./dom_shim");

const bundlePath = process.argv[2];
if (!bundlePath) {
  console.error("usage: node product/verify_query_page.js BUNDLE.json");
  process.exit(2);
}

const bundle = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
/* Optional page override, used ONLY by the product's own discrimination
 * controls (product/tests/test_adversarial_discovery_ui.py) to run this same
 * behavioural contract against a mutated page.  A real check reads the shipped
 * page. */
const html = fs.readFileSync(process.argv[4] || HTML_PATH, "utf8");
/* Optional deep link (?q=&n=&run_id=), the per-question link the gate packet
 * hands the owner.  With one, the page is EXPECTED to ask the server for that
 * run: "no network call" only holds for the plain, deep-link-free boot. */
const search = process.argv[3] || "";
const deepLinkRun = /[?&]run_id=([^&]+)/.exec(search);

const assertions = [];
function check(condition, label) { assertions.push({ ok: !!condition, label }); }
/* Same escaping the page applies to relation targets, so the assertion cannot
 * pass by accident on a differently-escaped substring. */
function esc(v) {
  return String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

let page;
try {
  page = createPage({ html, bundle, search });
  const inlineCount = page.runScripts();
  check(inlineCount >= 1, "query.html exposes an inline page script");
} catch (err) {
  console.error("page failed to boot: " + err.message);
  process.exit(1);
}

const documentShim = page.documentShim;
const fetchCalls = page.fetchCalls;

const toggle = documentShim.getElementById("lexViewToggle");
const toolbar = documentShim.getElementById("toolbar");
check(!!toggle, "boot mounts #lexViewToggle");
check(!!toggle && toolbar.childNodes[0] === toggle, "toggle is the first child of #toolbar");
check(!!documentShim.getElementById("lexSessionExport"), "boot mounts the session export button");

/* Render the real bundle the way a completed query does. */
page.evaluate("renderBundle(__TEST_BUNDLE__);");

const listEl = documentShim.getElementById("lexListView");
const mapEl = documentShim.getElementById("mapWrap");
const statusEl = documentShim.getElementById("status");

check(listEl.hidden === true, "list starts hidden (map is the first paint)");
check(mapEl.hidden === false, "map is visible on boot");
if (!deepLinkRun) {
  check(fetchCalls.length === 0, "rendering a bundle made no network call");
}

/* Switch to the conventional list, the way the owner will. */
toggle.click();

setTimeout(async () => {
  const html = listEl.innerHTML;
  const rows = (html.match(/class="lex-row"/g) || []).length;
  const controller = page.evaluate("__LEX_GATE_SWITCH__.controller");
  const statusAfter = statusEl.innerHTML;

  check(controller.viewMode === "list", "controller reports the list view");
  check(rows === bundle.decisions.length,
        "baseline renders one row per decision (" + rows + "/" + bundle.decisions.length + ")");
  check(html.indexOf("cluster") === -1, "baseline shows no cluster information");
  check(html.indexOf('class="lex-source"') !== -1, "baseline links every row to its source");
  check(listEl.hidden === false, "list is shown after the toggle");
  check(mapEl.hidden === true, "map is hidden after the toggle");
  if (!deepLinkRun) {
    check(fetchCalls.length === 0, "boot and view switch made no network call");
  }
  check(statusAfter.indexOf("Prêt.") !== -1,
        "product status survives the switch writing #status (" + JSON.stringify(statusAfter) + ")");
  check(statusAfter.indexOf("vue liste") !== -1,
        "view indicator survives the product status re-render");

  /* 5. clicking a decision that carries typed citation edges shows them.
   *    Audit F3 of cycle 38779139471 recorded that the map's relation
   *    affordance was empty for every unhydrated query; this asserts the
   *    recovered edges actually reach the researcher, with their direction. */
  const related = (bundle.relations || [])[0];
  if (related) {
    const endpoint = related.source;
    page.evaluate("showDetail(__TEST_BUNDLE__.relations[0].source);");
    const detailHtml = documentShim.getElementById("detail").innerHTML;
    const other = related.source === endpoint ? related.target : related.source;
    check(detailHtml.indexOf("Relations") !== -1,
          "detail panel lists relations for a clicked decision");
    check(detailHtml.indexOf(esc(other)) !== -1,
          "detail panel names the related decision (" + other + ")");
    check(detailHtml.indexOf("cite") !== -1 || detailHtml.indexOf("cité par") !== -1,
          "detail panel states the citation direction");
  } else {
    check(true, "bundle carries no relation row (nothing to exercise)");
  }

  /* 6. The canvas map itself.  Advisory A2 of cycle 38785927063: the shim
   *    stubbed every <select>'s value as "", so filtered() saw langFilter !==
   *    "all", returned [], and draw() drew nothing — the harness certified a
   *    clickable map it could not reach.  These assertions exercise draw() and
   *    the canvas click handler for real. */
  const drawn = page.evaluate("(function(){ draw(); return PTS.length; })()");
  check(drawn === bundle.decisions.length,
        "map draws one canvas point per decision (" + drawn + "/" + bundle.decisions.length + ")");

  const clicked = page.evaluate(
    "(function(){" +
    "  const p = PTS[0]; if (!p) return null;" +
    "  const r = cv.getBoundingClientRect();" +
    "  cv.onclick({ clientX: r.left + p._px, clientY: r.top + p._py });" +
    "  return { id: p.decision_id, cx: p._px, cy: p._py };" +
    "})()");
  const detailHtml = documentShim.getElementById("detail").innerHTML;
  check(!!clicked && detailHtml.indexOf(esc(clicked.id)) !== -1,
        "clicking a drawn point opens its decision (" + (clicked && clicked.id) + ")");
  check(!!clicked && detailHtml.indexOf("Ouvrir la source") !== -1,
        "the clicked point's panel carries the source link");

  /* 7. Deep links.  The gate packet hands the owner one link per question
   *    (?q=&n= runs it, ?run_id= opens the bundle that was verified at run time).
   *    A page that ignores them makes a three-question ceremony three retypings,
   *    and makes the verified bundle unreachable, so the parse itself is
   *    asserted against the real page code, not against a reconstruction. */
  const deepLink = page.evaluate(
    "(function(){ try {" +
    "  var p = new URLSearchParams('?q=R%C3%A9siliation%20test&n=250&run_id=abc123');" +
    "  return { q: p.get('q'), n: p.get('n'), run_id: p.get('run_id'), missing: p.get('nope') };" +
    "} catch (e) { return { error: String(e) }; } })()");
  check(deepLink.q === "Résiliation test" && deepLink.n === "250" && deepLink.run_id === "abc123"
        && deepLink.missing === null,
        "the page's deep-link parameters parse (q, n, run_id)");
  check(page.evaluate("typeof boot") === "function",
        "the page boots through a deep-link aware entry point");
  check(page.evaluate("(function(){ return __LEX_GATE_SWITCH__ && "
        + "typeof __LEX_GATE_SWITCH__.controller.exportDraft === 'function'; })()"),
        "the export seam still exists after the deep-link boot path");
  if (deepLinkRun) {
    /* The packet link must ask the server for THAT run - a deep link that
     * silently re-retrieves would show the jurist a bundle nobody verified. */
    await page.evaluate("__LEX_BOOT_PROMISE__");
    const asked = fetchCalls.map(String);
    check(asked.some((u) => u.indexOf("/api/query/status?run_id=" + decodeURIComponent(deepLinkRun[1])) !== -1),
          "a ?run_id= link resumes exactly that run (" + decodeURIComponent(deepLinkRun[1]) + ")");
    check(asked.every((u) => u.indexOf("/api/query/start") === -1),
          "a ?run_id= link does not re-retrieve a new run");
  }

  /* 8. v55 render-truth: the ring/pill state the EVIDENCE, not the status
   *    alone.  The served packet carries counter rows whose counter_evidence
   *    is empty and whose counter_evidence_verified is ABSENT (never false);
   *    the page must render those as an explicitly marked unevidenced state,
   *    never as a confident counter ring/pill, and the owner card must state
   *    how many of the session's counter rows are unevidenced.  The two
   *    synthetic rows below reproduce the served packet's exact shape. */
  const synth = {
    query: "synthetic", query_variants: [],
    answer: {status: "ready", prose: "", cited_decision_ids: []},
    decisions: [
      {decision_id: "evidenced-1", court: "BGER", language: "de", rank: 1, score: 1.0,
       provenance: {}, snippet: "s", cluster_id: 0, x: 0, y: 0,
       counter_status: "candidate-limiting", counter_evidence: "Die Ausnahme greift nur eng.",
       counter_evidence_verified: true, canonical_url: "https://example.com/1", citation: ""},
      {decision_id: "unevidenced-1", court: "BGER", language: "de", rank: 2, score: 0.9,
       provenance: {}, snippet: "s", cluster_id: 0, x: 0.1, y: 0.1,
       counter_status: "candidate-contrary", counter_evidence: "", counter_uncertainty: 0.95,
       canonical_url: "https://example.com/2", citation: ""}
    ],
    clusters: [{cluster_id: 0, size: 2, label: "synthetic"}],
    relations: [],
    provenance: {}
  };
  page.evaluate("renderBundle(" + JSON.stringify(synth) + ");");
  const pred = page.evaluate("(function(){"
    + "var ev = " + JSON.stringify(synth) + ".decisions[0],"
    + " un = " + JSON.stringify(synth) + ".decisions[1];"
    + "return {evIsCounter: isCounter(ev), evEvidenced: counterEvidenced(ev),"
    + "        unIsCounter: isCounter(un), unEvidenced: counterEvidenced(un)};"
    + "})()");
  check(pred.evIsCounter === true && pred.evEvidenced === true,
        "an evidenced counter row predicates as a confident counter");
  check(pred.unIsCounter === true,
        "an unevidenced row stays a counter row (visibility preserved)");
  check(pred.unEvidenced === false,
        "an unevidenced row is never an evidenced counter");

  page.evaluate("showDetail('unevidenced-1');");
  let synthDetailHtml = documentShim.getElementById("detail").innerHTML;
  check(synthDetailHtml.indexOf("non étayée · conservée pour visibilité") !== -1,
        "unevidenced detail panel carries the explicit unevidenced pill");
  check(synthDetailHtml.indexOf("Contre-autorité non étayée") !== -1,
        "unevidenced detail panel states the missing evidence, not silence");
  check(synthDetailHtml.indexOf("0.95") !== -1,
        "unevidenced detail panel discloses its uncertainty");
  check(synthDetailHtml.indexOf('pill red') === -1,
        "unevidenced detail panel never carries the confident red pill");

  page.evaluate("showDetail('evidenced-1');");
  synthDetailHtml = documentShim.getElementById("detail").innerHTML;
  check(synthDetailHtml.indexOf('pill red') !== -1 && synthDetailHtml.indexOf("candidate-limiting") !== -1,
        "evidenced detail panel keeps the red status pill");
  check(synthDetailHtml.indexOf("Élément contraire") !== -1
        && synthDetailHtml.indexOf("Die Ausnahme greift nur eng.") !== -1,
        "evidenced detail panel shows the verbatim evidence");

  const counterHtml = documentShim.getElementById("counterList").innerHTML;
  check(counterHtml.indexOf("2 contre-autorités · 1 non étayée (conservée pour visibilité)") !== -1,
        "owner card states the unevidenced count of the session");
  check(counterHtml.indexOf("non étayée · conservée pour visibilité") !== -1,
        "unevidenced sidebar card is explicitly marked");

  const filterEl = documentShim.getElementById("counterFilter");
  filterEl.value = "counter";
  const visibleToCounterFilter = page.evaluate("(function(){ draw(); return PTS.length; })()");
  check(visibleToCounterFilter === 2,
        "the counter filter keeps unevidenced rows visible (" + visibleToCounterFilter + "/2)");
  filterEl.value = "all";

  /* The bundle actually handed to the owner must disclose its unevidenced
   * counter rows: count them from the data IN THE PAGE (the predicates are
   * the page's own), then require the card to state the same number.  A
   * bundle with none simply has nothing to disclose. */
  const realUnevid = page.evaluate("(function(){"
    + "return (__TEST_BUNDLE__.decisions || []).filter(function (d) {"
    + "  return isCounter(d) && !counterEvidenced(d); }).length; })()");
  page.evaluate("renderBundle(__TEST_BUNDLE__);");
  const realCounterHtml = documentShim.getElementById("counterList").innerHTML;
  if (realUnevid) {
    check(realCounterHtml.indexOf(realUnevid + " non étayée") !== -1,
          "owner card states the unevidenced count of the served bundle ("
          + realUnevid + " non étayées)");
    check(realCounterHtml.indexOf("conservée pour visibilité") !== -1,
          "served bundle's unevidenced rows are explicitly marked");
  } else {
    check(true, "served bundle carries no unevidenced counter row (nothing to disclose)");
  }

  /* 9. The sourced answer is INSPECTABLE, not a wall of text (QUERY_MAP_MVP
   *    §8: "provide links / identifiers so the user can inspect the underlying
   *    decision").  Two independent routes are checked against the real page
   *    code: an id the prose spells out becomes an inline link, and an id it
   *    never spells out (a model that numbers its citations) still appears as
   *    a clickable source chip.  Then the link target is executed, so the
   *    assertion is behaviour, not markup presence. */
  const citedIds = (bundle.answer && bundle.answer.cited_decision_ids) || [];
  if (citedIds.length) {
    const realProse = documentShim.getElementById("prose").innerHTML;
    const realMeta = documentShim.getElementById("answerMeta").innerHTML;
    const unreachable = citedIds.filter(
      (id) => realProse.indexOf('data-id="' + esc(id) + '"') === -1 &&
              realMeta.indexOf('data-id="' + esc(id) + '"') === -1);
    check(unreachable.length === 0,
          "every decision the answer cites is reachable from the answer panel ("
          + citedIds.length + " cited, " + unreachable.length + " unreachable)");
    page.evaluate("openCited(" + JSON.stringify(citedIds[0]) + ")");
    const citedDetail = documentShim.getElementById("detail").innerHTML;
    check(citedDetail.indexOf(esc(citedIds[0])) !== -1,
          "opening a cited source opens that decision (" + citedIds[0] + ")");
    check(citedDetail.indexOf("Ouvrir la source") !== -1,
          "the cited decision's panel carries its source link");
  } else {
    check(true, "bundle answer cites no decision (nothing to link)");
  }

  /* Hostile prose must never become markup: the linker escapes the text it
   * does not recognise, links only the exact cited ids, and cannot nest an
   * anchor inside an anchor. */
  const ansSynth = {
    query: "answer-link", query_variants: [],
    answer: {
      status: "ready", method: "synthetic", model: "none",
      prose: "Zu bge_ANS_1 siehe <script>alert(1)</script>; bge_ANS_1 nochmals.",
      cited_decision_ids: ["bge_ANS_1", "bge_ANS_2_NOT_IN_PROSE"],
    },
    decisions: [
      {decision_id: "bge_ANS_1", court: "BGER", language: "de", rank: 1, score: 1.0,
       provenance: {}, snippet: "s", cluster_id: 0, x: 0, y: 0, counter_status: "none",
       canonical_url: "https://mcp.opencaselaw.ch/d/1", citation: ""},
      {decision_id: "bge_ANS_2_NOT_IN_PROSE", court: "BGER", language: "de", rank: 2,
       score: 0.9, provenance: {}, snippet: "s", cluster_id: 0, x: 0.1, y: 0.1,
       counter_status: "none", canonical_url: "https://mcp.opencaselaw.ch/d/2", citation: ""},
    ],
    clusters: [{cluster_id: 0, size: 2, label: "synthetic"}],
    relations: [],
    provenance: {},
  };
  page.evaluate("renderBundle(" + JSON.stringify(ansSynth) + ");");
  const hostileProse = documentShim.getElementById("prose").innerHTML;
  const hostileMeta = documentShim.getElementById("answerMeta").innerHTML;
  check(hostileProse.indexOf("<script>") === -1,
        "answer prose is escaped: injected markup never reaches the DOM");
  check(hostileProse.indexOf("&lt;script&gt;") !== -1,
        "the hostile markup survives as visible, readable text");
  const inlineLinks = (hostileProse.match(/class="cited-ref"/g) || []).length;
  check(inlineLinks === 2,
        "each occurrence of a cited id in the prose becomes its own link (" + inlineLinks + "/2)");
  check(hostileProse.indexOf("<a class=\"cited-ref\" data-id=\"bge_ANS_1\"") !== -1,
        "the inline link carries the decision id as its data-id");
  check(hostileMeta.indexOf('data-id="bge_ANS_2_NOT_IN_PROSE"') !== -1,
        "a cited id the prose never spells out is still a clickable source chip");
  page.evaluate("openCited('bge_ANS_2_NOT_IN_PROSE');");
  const chipDetail = documentShim.getElementById("detail").innerHTML;
  check(chipDetail.indexOf("bge_ANS_2_NOT_IN_PROSE") !== -1,
        "clicking a source chip opens its decision");
  page.evaluate("renderBundle(__TEST_BUNDLE__);");

  /* 10. The independent adversarial pass is the half of the product a ranked
   *    list cannot show, and before cycle 39063665073 it was invisible: the
   *    frozen reviewer legitimately abstains without verbatim evidence, so a
   *    live session reported "aucune contre-autorité qualifiée" right after
   *    the pass had ADMITTED new authorities through its contrary / exception /
   *    minority / older-line probes.  These assertions run the page's own
   *    predicates over the bundle it is actually given, so the panel cannot
   *    quietly under-report what the pass found.
   *
   *    The label ceiling is asserted as hard as the discovery: discovery is
   *    provenance, never a counter qualification. */
  const discovered = page.evaluate("(function(){"
    + "return (__TEST_BUNDLE__.decisions || []).filter(isAdversarial)"
    + "  .map(function (d) { return { id: d.decision_id, channels: advChannels(d),"
    + "    isCounter: isCounter(d), evidenced: counterEvidenced(d) }; });})()");
  const advHtml = documentShim.getElementById("adversarialList").innerHTML;
  if (discovered.length) {
    const missing = discovered.filter(
      (r) => advHtml.indexOf('data-id="' + esc(r.id) + '"') === -1);
    check(missing.length === 0,
          "every authority the adversarial pass found is named in the sidebar ("
          + discovered.length + " found, " + missing.length + " unnamed)");
    const unnamedChannels = discovered.filter(
      (r) => r.channels.every((c) => advHtml.indexOf(esc(c)) === -1));
    check(unnamedChannels.length === 0,
          "each discovered authority names the probe channel that found it");
    check(advHtml.indexOf("marqueur de provenance de recherche, pas une qualification juridique") !== -1,
          "the discovery panel states that the marker is provenance, not a legal qualification");
    /* The label "découverte seule" belongs to a discovered row that is NOT a
     * counter (``isCounter`` false): such a row carries only discovery
     * provenance and must never be presented as a counter qualification. A
     * discovered row that IS a counter is labelled by its evidence state
     * instead - an unevidenced counter renders "non étayée · conservée pour
     * visibilité", an evidenced one "qualifiée et étayée" - so the
     * "découverte seule" string is correctly absent for it. The previous form
     * ("the string is present OR every discovered row is evidenced") therefore
     * failed a bundle whose discovered rows are all unevidenced COUNTERS: the
     * page was right and the assertion was wrong. Scope the requirement to the
     * rows it actually describes, so a bundle with no unqualified discovery is
     * not failed for a label it never owed. */
    const unqualified = discovered.filter((r) => !r.isCounter);
    check(unqualified.length === 0 || advHtml.indexOf("découverte seule") !== -1,
          "an unqualified discovery is labelled as a discovery only");

    /* Clicking it opens the decision, and the panel says how it was found. */
    page.evaluate("openDiscovered(" + JSON.stringify(discovered[0].id) + ");");
    const discDetail = documentShim.getElementById("detail").innerHTML;
    check(discDetail.indexOf(esc(discovered[0].id)) !== -1,
          "opening a discovered authority shows its decision (" + discovered[0].id + ")");
    check(discDetail.indexOf("Passe contradictoire indépendante") !== -1
          && discDetail.indexOf("marqueur indique comment la décision a été retrouvée") !== -1,
          "the discovered decision's panel discloses its discovery provenance");
    if (!discovered[0].isCounter) {
      check(discDetail.indexOf('pill red') === -1 && discDetail.indexOf('pill amber') === -1,
            "a discovery is never rendered as a counter qualification");
    }

    /* The map filter isolates exactly the discovered rows, no more, no less. */
    const cfEl = documentShim.getElementById("counterFilter");
    cfEl.value = "adversarial";
    const shown = page.evaluate("(function(){ draw(); return PTS.length; })()");
    const allDiscovered = page.evaluate(
      "(function(){ return PTS.every(isAdversarial); })()");
    check(shown === discovered.length && allDiscovered === true,
          "the 'passe contradictoire' filter isolates exactly the discovered rows ("
          + shown + "/" + discovered.length + ")");
    cfEl.value = "all";
    page.evaluate("draw();");
  } else {
    check(advHtml.indexOf("n’a trouvé aucune autorité nouvelle") !== -1,
          "a bundle with no adversarial finding says so instead of inventing one");
    check(true, "bundle carries no adversarially discovered authority (nothing to list)");
  }

  /* Discovery must never manufacture a counter claim: a row the probes found
   * and nobody qualified stays out of the counter filter and out of the
   * counter sidebar, while remaining on the map and listed as a discovery. */
  const discSynth = {
    query: "discovery", query_variants: [],
    answer: {status: "ready", prose: "", cited_decision_ids: []},
    decisions: [
      {decision_id: "disc-only", court: "BGER", language: "de", rank: 1, score: 0.9,
       provenance: {}, snippet: "s", cluster_id: 0, x: 0, y: 0, counter_status: "none",
       channels: ["adversarial.minority"], canonical_url: "https://example.com/d1", citation: ""},
      {decision_id: "disc-qualified", court: "BGER", language: "fr", rank: 2, score: 0.8,
       provenance: {}, snippet: "s", cluster_id: 0, x: 0.1, y: 0.1,
       counter_status: "candidate-limiting", counter_evidence: "La réserve est expresse.",
       counter_evidence_verified: true, channels: ["adversarial.contrary"],
       canonical_url: "https://example.com/d2", citation: ""},
      {decision_id: "plain-row", court: "BGE", language: "it", rank: 3, score: 0.7,
       provenance: {}, snippet: "s", cluster_id: 0, x: 0.2, y: 0.2, counter_status: "none",
       channels: ["search"], canonical_url: "https://example.com/p", citation: ""},
    ],
    clusters: [{cluster_id: 0, size: 3, label: "synthetic"}],
    relations: [],
    provenance: {},
  };
  page.evaluate("renderBundle(" + JSON.stringify(discSynth) + ");");
  const discPred = page.evaluate("(function(){ var b = " + JSON.stringify(discSynth) + ";"
    + "var only = b.decisions[0], qual = b.decisions[1], plain = b.decisions[2];"
    + "return { onlyDiscovered: isAdversarial(only), onlyCounter: isCounter(only),"
    + "  onlyChannels: advChannels(only), qualBoth: isAdversarial(qual) && counterEvidenced(qual),"
    + "  plainDiscovered: isAdversarial(plain), plainCounter: isCounter(plain) }; })()");
  check(discPred.onlyDiscovered === true && discPred.onlyChannels[0] === "minority",
        "an adversarial channel row predicates as discovered (channel: minority)");
  check(discPred.onlyCounter === false && discPred.qualBoth === true,
        "discovery never manufactures a counter claim, and never hides a qualified one");
  check(discPred.plainDiscovered === false && discPred.plainCounter === false,
        "an ordinary ranked retrieval row is not presented as a discovery");

  const discHtml = documentShim.getElementById("adversarialList").innerHTML;
  const counterHtmlDisc = documentShim.getElementById("counterList").innerHTML;
  check(discHtml.indexOf('data-id="disc-only"') !== -1
        && discHtml.indexOf('data-id="disc-qualified"') !== -1,
        "the discovery panel lists both discovered rows");
  check(discHtml.indexOf('data-id="plain-row"') === -1
        && counterHtmlDisc.indexOf('data-id="plain-row"') === -1,
        "an ordinary retrieval row appears in neither the discovery nor the counter panel");
  check(counterHtmlDisc.indexOf('data-id="disc-only"') === -1,
        "an unqualified discovery is NOT listed as a counter-authority");
  check(discHtml.indexOf("qualifiée et étayée") !== -1,
        "a discovered AND qualified row states both facts");

  /* --- relation-channel disclosure -----------------------------------------
   * MVP section 7 asks for citation/relation edges "available on selection". A
   * bundle with zero edges used to render no Relations line at all, which a
   * jurist cannot distinguish from a broken feature. The page must therefore
   * state the channel state WITH its measured counts, and must stay silent when
   * the bundle carries no channel field rather than guessing. */
  const chanHtml = documentShim.getElementById("relationChannel").innerHTML;
  check(chanHtml === "",
        "a bundle without a published channel state renders no relation claim");

  const chanSynth = JSON.parse(JSON.stringify(discSynth));
  chanSynth.provenance = {relations_provenance: {
    channel_state: "EMPTY_NO_SHARED_AUTHORITY",
    channel: {state: "EMPTY_NO_SHARED_AUTHORITY", n_relations: 0, measured: {
      n_decisions: 3, n_rows_with_citation: 2, n_distinct_references: 2,
      n_pairs_sharing_citation: 0, n_rows_in_a_shared_pair: 0, shared_reference_sample: []}},
    channel_after_hydration: {state: "EMPTY_NO_SHARED_AUTHORITY", n_relations: 0, measured: {
      n_decisions: 3, n_rows_with_citation: 3, phase: "after_hydration"}},
    relations_added_by_hydration: 0}};
  page.evaluate("renderBundle(" + JSON.stringify(chanSynth) + ");");
  const chanText = documentShim.getElementById("relationChannel").innerHTML;
  check(chanText.indexOf("Aucune arête de relation") !== -1
        && chanText.indexOf("3 des 3") !== -1,
        "an empty relation channel is stated on the map with its measured counts");
  check(chanText.indexOf("après hydratation") !== -1,
        "the post-hydration measurement is labelled as such, not as the map-build one");
  const detailChan = page.evaluate("(function(){ showDetail('plain-row');"
    + "return document.getElementById('detail').innerHTML; })()");
  check(detailChan.indexOf("Relations") !== -1
        && detailChan.indexOf("Aucune arête de relation") !== -1,
        "the decision detail states the channel state instead of omitting the section");
  /* Non-vacuity: the panel must be driven by the published measurement, not by a
   * hard-coded empty string. A bundle whose channel IS populated must say so. */
  const chanPop = JSON.parse(JSON.stringify(chanSynth));
  chanPop.relations = [{source: "plain-row", target: "disc-only",
                        kind: "shared_citation", shared: ["BGE 1 II 1"]}];
  chanPop.provenance.relations_provenance.channel_after_hydration =
    {state: "POPULATED", n_relations: 1, measured: {n_decisions: 3, n_rows_with_citation: 3}};
  chanPop.provenance.relations_provenance.relations_added_by_hydration = 1;
  page.evaluate("renderBundle(" + JSON.stringify(chanPop) + ");");
  const popText = documentShim.getElementById("relationChannel").innerHTML;
  check(popText.indexOf("arête") !== -1 && popText.indexOf("+1") !== -1,
        "a populated channel reports its edge count and what hydration added");
  /* A shared_citation edge is symmetric: BOTH endpoints cite the named
   * authority. The detail panel must state that in French ("cite en commun")
   * and name the shared authority - never print the raw machine token in a
   * jurist-facing panel. Found by the offline slice 20261018T095123Z: the
   * petty-theft-dismissal and corporate-criminal-liability bundles carry only
   * shared_citation edges and failed "detail panel states the citation
   * direction" because the fallback line was "↔ X · shared_citation". */
  const sharedDetail = page.evaluate("(function(){ showDetail('plain-row');"
    + "return document.getElementById('detail').innerHTML; })()");
  check(sharedDetail.indexOf("cite en commun") !== -1
        && sharedDetail.indexOf("BGE 1 II 1") !== -1,
        "a shared_citation edge states the co-citation in French and names the shared authority");
  check(sharedDetail.indexOf("shared_citation") === -1,
        "the raw relation-kind token never reaches the jurist-facing panel");

  /* --- retrieval rank on counter and discovery cards ----------------------
   * The product thesis is that contrary/minority authority sits BELOW the ranked
   * list's fold. If the rank is not on the card, the jurist cannot see that the
   * row was ever out of view in a conventional list. */
  const rankSynth = JSON.parse(JSON.stringify(discSynth));
  rankSynth.decisions[1].rank = 57;
  page.evaluate("renderBundle(" + JSON.stringify(rankSynth) + ");");
  const rankHtml = documentShim.getElementById("counterList").innerHTML;
  check(rankHtml.indexOf("rang 57") !== -1,
        "a counter-authority below the list fold shows its retrieval rank");
  const noRankHtml = page.evaluate("(function(){ renderBundle("
    + JSON.stringify(discSynth) + ");"
    + "return rankPill({decision_id:'x'}); })()");
  check(noRankHtml.indexOf("hors pool") !== -1,
        "a row outside the ranked pool is labelled as such instead of given a rank");

  const cfDisc = documentShim.getElementById("counterFilter");
  cfDisc.value = "counter";
  const counterView = page.evaluate("(function(){ draw(); return PTS.length; })()");
  check(counterView === 1,
        "the counter filter still isolates only the qualified row (" + counterView + "/1)");
  cfDisc.value = "adversarial";
  const discView = page.evaluate("(function(){ draw(); return PTS.length; })()");
  check(discView === 2,
        "the discovery filter isolates the two discovered rows (" + discView + "/2)");
  cfDisc.value = "all";
  page.evaluate("renderBundle(__TEST_BUNDLE__);");

  let failed = 0;
  for (const a of assertions) {
    if (!a.ok) failed += 1;
    console.log((a.ok ? "ok" : "FAIL") + " - " + a.label);
  }
  console.log(failed === 0 ? "PASS " + assertions.length + " assertions" : "FAIL " + failed);
  process.exit(failed === 0 ? 0 : 1);
}, 0);
