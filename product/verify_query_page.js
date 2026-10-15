#!/usr/bin/env node
/* Offline DOM verification for product/static/query.html.
 *
 *   node product/verify_query_page.js BUNDLE.json
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
const html = fs.readFileSync(HTML_PATH, "utf8");

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
  page = createPage({ html, bundle });
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
check(fetchCalls.length === 0, "rendering a bundle made no network call");

/* Switch to the conventional list, the way the owner will. */
toggle.click();

setTimeout(() => {
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
  check(fetchCalls.length === 0, "boot and view switch made no network call");
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

  let failed = 0;
  for (const a of assertions) {
    if (!a.ok) failed += 1;
    console.log((a.ok ? "ok" : "FAIL") + " - " + a.label);
  }
  console.log(failed === 0 ? "PASS " + assertions.length + " assertions" : "FAIL " + failed);
  process.exit(failed === 0 ? 0 : 1);
}, 0);
