#!/usr/bin/env node
/* Frozen-question quick-pick: click a shipped button, get the clickable map.
 *
 *   node product/verify_quickpick.js BASE_URL SLUG EXPECTED_QUESTION [N]
 *
 * Why this exists
 * ---------------
 * ``product/verify_served_page.js`` proves the shipped page drives the shipped
 * server for a query it is *given* (via the deep link).  The FAST MVP lane
 * asks for the other half: a jurist who does not retype a frozen Swiss-law
 * fixture but *selects* it.  This driver executes the SHIPPED ``query.html``
 * in the shared DOM shim, clicks the quick-pick button for ``SLUG``, and proves
 * that the click
 *
 *   1. fills the search box with ``EXPECTED_QUESTION`` (byte-exact - the
 *      caller derives it from ``product/reality_check.py`` LEGS, which is the
 *      same source ``FROZEN_QUICKPICK`` is pinned against by
 *      product/tests/test_frozen_question_quickpick.py);
 *   2. actually runs the normal progressive pipeline against a real socket
 *      (``/api/query/start`` was called with that question);
 *   3. ends with a rendered, clickable, source-linked map (one drawn canvas
 *      point per decision, clusters present).
 *
 * It is a composition of the existing shim + transport, not new product logic,
 * and it is a smoke test of the selection path - never a claim about retrieval
 * quality, legal usefulness or any frozen bar.
 */
"use strict";

const http = require("http");
const { createPage } = require("./dom_shim");

const BASE = process.argv[2];
const SLUG = process.argv[3];
const EXPECTED = process.argv[4];
const N = process.argv[5] || "150";
if (!BASE || !SLUG || !EXPECTED) {
  console.error("usage: node product/verify_quickpick.js BASE_URL SLUG EXPECTED_QUESTION [N]");
  process.exit(2);
}

/** A real HTTP transport shaped like fetch, resolving relative URLs against BASE. */
function httpFetch(url) {
  const absolute = /^https?:\/\//i.test(url) ? url : BASE.replace(/\/$/, "") + url;
  return new Promise((resolve, reject) => {
    http.get(absolute, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => { body += chunk; });
      res.on("end", () => {
        let data = null;
        try { data = JSON.parse(body); } catch (e) { data = null; }
        resolve({
          ok: res.statusCode >= 200 && res.statusCode < 300,
          status: res.statusCode,
          json: () => Promise.resolve(data),
        });
      });
    }).on("error", reject);
  });
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

(async () => {
  const page = createPage({ search: "", fetchImpl: httpFetch });
  const documentShim = page.documentShim;
  const assertions = [];
  const check = (condition, label) => assertions.push({ ok: !!condition, label });

  const inlineCount = page.runScripts();
  check(inlineCount >= 1, "query.html exposes an inline page script");

  /* With an empty deep link the page must NOT auto-run: the quick-pick is the
   * only thing that should start a pipeline, or the click test would pass
   * vacuously on a page that runs by itself. */
  await page.evaluate("__LEX_BOOT_PROMISE__");
  const bootBundles = page.fetchCalls.filter((u) => u.indexOf("/api/query/start") !== -1);
  check(bootBundles.length === 0,
    "the page did not auto-run without a question (" + bootBundles.length + " start calls)");

  const qBefore = documentShim.getElementById("q").value;
  check(qBefore !== EXPECTED,
    "the search box starts on the default question, not the frozen one");

  const button = documentShim.getElementById("qp-" + SLUG);
  check(!!button, "the quick-pick button for " + SLUG + " exists in the shipped page");

  const map = page.evaluate("typeof FROZEN_QUICKPICK === 'undefined' ? null : FROZEN_QUICKPICK");
  check(!!map && map[SLUG] === EXPECTED,
    "FROZEN_QUICKPICK carries the expected question for " + SLUG);

  if (button) {
    const nSel = documentShim.getElementById("n");
    if (nSel) nSel.value = N;
    button.click();

    const qAfter = documentShim.getElementById("q").value;
    check(qAfter === EXPECTED,
      "clicking the quick-pick fills the search box with the frozen question ("
      + qAfter.length + "/" + EXPECTED.length + " chars)");

    /* Wait for the page's own pipeline to finish (status ends "terminé") or
     * fail loudly on the error branch; never hang past the budget. */
    const deadline = Date.now() + 150000;
    let phase = "timeout";
    for (;;) {
      const text = page.evaluate("document.getElementById('status').innerHTML");
      if (String(text).indexOf("terminé") !== -1) { phase = "done"; break; }
      if (String(text).indexOf("erreur") !== -1) { phase = "error"; break; }
      if (Date.now() > deadline) break;
      await sleep(500);
    }
    check(phase === "done",
      "the quick-picked run finished through the progressive pipeline (phase=" + phase + ")");

    const calls = page.fetchCalls.map(String);
    check(calls.some((u) => u.indexOf("/api/query/start?q=" + encodeURIComponent(EXPECTED)) !== -1),
      "the page called /api/query/start with the frozen question");
    check(calls.some((u) => u.indexOf("/api/query/status") !== -1),
      "the page polled /api/query/status while the jobs ran");
    check(calls.some((u) => u.indexOf("/api/query/bundle") !== -1),
      "the page re-read /api/query/bundle after enrichment");

    const bundle = page.evaluate("typeof BUNDLE === 'undefined' ? null : BUNDLE");
    const decisions = (bundle && bundle.decisions) || [];
    const clusters = (bundle && bundle.clusters) || [];
    check(decisions.length > 0,
      "the quick-picked run rendered decisions (" + decisions.length + ")");
    check(clusters.length > 0,
      "the quick-picked map carries clusters (" + clusters.length + ")");
    check((bundle && bundle.provenance && bundle.provenance.source)
      || decisions.length > 0,
      "the bundle is a real result bundle");

    const drawn = page.evaluate("(function(){ draw(); return PTS.length; })()");
    check(drawn === decisions.length && drawn > 0,
      "the map draws one canvas point per decision (" + drawn + "/" + decisions.length + ")");

    /* Clickability: a drawn point opens the decision panel with a source link. */
    const clicked = page.evaluate(
      "(function(){ const p = PTS[0]; if (!p) return null;" +
      "  const r = cv.getBoundingClientRect();" +
      "  cv.onclick({ clientX: r.left + p._px, clientY: r.top + p._py });" +
      "  return p.decision_id; })()");
    const detail = documentShim.getElementById("detail").innerHTML;
    check(!!clicked && String(detail).indexOf("Ouvrir la source") !== -1,
      "clicking a drawn point opens its source-linked panel (" + clicked + ")");
  }

  let failed = 0;
  for (const a of assertions) {
    if (!a.ok) failed += 1;
    console.log((a.ok ? "ok" : "FAIL") + " - " + a.label);
  }
  console.log("slug: " + SLUG);
  console.log(failed === 0
    ? "PASS " + assertions.length + " assertions"
    : "FAIL " + failed);
  process.exit(failed === 0 ? 0 : 1);
})().catch((err) => {
  console.error("driver error: " + (err && err.message ? err.message : err));
  process.exit(1);
});
