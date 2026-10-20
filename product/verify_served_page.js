#!/usr/bin/env node
/* Page <-> server integration for the shipped query-map product.
 *
 *   node product/verify_served_page.js BASE_URL QUERY [N]
 *
 * Why this exists
 * ---------------
 * Two instruments already cover the two halves of the clickable slice, and
 * neither covers the seam between them:
 *
 *   * ``product/server_slice.py`` drives the SHIPPED HTTP handler over a real
 *     socket with Python's ``urllib`` and proves the API contract end to end;
 *   * ``product/verify_query_page.js`` executes the SHIPPED page scripts in the
 *     minimal DOM and proves the page contract against a bundle it is handed.
 *
 * What no committed instrument proved is the thing a jurist actually touches:
 * the shipped ``query.html`` asking the shipped server for a query, waiting on
 * its own progressive job pipeline, and then rendering the returned bundle as a
 * clickable, source-linked map with a sourced answer.  That is this script.  It
 * is a composition, not new product logic: it injects a real ``fetch``
 * transport into the shared DOM shim (``product/dom_shim.js``), so the page's
 * own ``run()`` / ``advance()`` / ``waitJob()`` code paths execute exactly as
 * they would in a browser, against a real socket.
 *
 * It is a smoke test of the clickable slice, not a claim about legal
 * usefulness, retrieval quality or any frozen bar.
 */
"use strict";

const http = require("http");
const { createPage, HTML_PATH } = require("./dom_shim");

const BASE = process.argv[2];
const QUERY = process.argv[3];
const N = process.argv[4] || "100";
if (!BASE || !QUERY) {
  console.error("usage: node product/verify_served_page.js BASE_URL QUERY [N]");
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

function esc(v) {
  return String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

(async () => {
  const search = "?q=" + encodeURIComponent(QUERY) + "&n=" + encodeURIComponent(N);
  const page = createPage({ html: undefined, search, fetchImpl: httpFetch });
  const documentShim = page.documentShim;
  const assertions = [];
  const check = (condition, label) => assertions.push({ ok: !!condition, label });

  const inlineCount = page.runScripts();
  check(inlineCount >= 1, "query.html exposes an inline page script");

  /* boot() awaits run() -> advance(), so the boot promise resolves only after
   * the whole progressive pipeline (start -> expand -> enrich -> bundle) has
   * finished.  A timeout turns a wedged pipeline into a FAIL, never a hang. */
  let booted = false;
  let bootError = null;
  try {
    await Promise.race([
      page.evaluate("__LEX_BOOT_PROMISE__"),
      new Promise((_, reject) => setTimeout(
        () => reject(new Error("boot promise did not settle in 90s")), 90000)),
    ]);
    booted = true;
  } catch (err) {
    bootError = err.message;
  }
  check(booted, "the shipped page completed its progressive pipeline against the server"
    + (bootError ? " (" + bootError + ")" : ""));

  const statusText = documentShim.getElementById("status").innerHTML;
  const bundle = page.evaluate("typeof BUNDLE === 'undefined' ? null : BUNDLE");
  const decisions = (bundle && bundle.decisions) || [];
  const answer = (bundle && bundle.answer) || {};

  check(decisions.length > 0, "the served run returned decisions (" + decisions.length + ")");
  check(answer.status === "ready", "the served run produced a sourced answer (status="
    + JSON.stringify(answer.status) + ")");
  const cited = (answer.cited_decision_ids || []).filter(
    (id) => decisions.some((d) => d.decision_id === id));
  check(cited.length >= 1, "the answer cites at least one decision on the map ("
    + cited.length + " cited)");

  /* The map itself: one canvas point per decision, drawn by the page's own draw(). */
  const drawn = page.evaluate("(function(){ draw(); return PTS.length; })()");
  check(drawn === decisions.length,
    "the map draws one canvas point per decision (" + drawn + "/" + decisions.length + ")");

  /* The page really talked to the server - a stubbed bundle would make every
   * assertion above vacuous. */
  const calls = page.fetchCalls.map(String);
  check(calls.some((u) => u.indexOf("/api/query/start") !== -1),
    "the page called /api/query/start (" + calls.length + " fetch calls)");
  check(calls.some((u) => u.indexOf("/api/query/status") !== -1),
    "the page polled /api/query/status while the jobs ran");
  check(calls.some((u) => u.indexOf("/api/query/bundle") !== -1),
    "the page re-read /api/query/bundle after enrichment");

  /* Clickability: clicking a drawn point opens its decision panel with a source link. */
  const clicked = page.evaluate(
    "(function(){ const p = PTS[0]; if (!p) return null;" +
    "  const r = cv.getBoundingClientRect();" +
    "  cv.onclick({ clientX: r.left + p._px, clientY: r.top + p._py });" +
    "  return p.decision_id; })()");
  const detailHtml = documentShim.getElementById("detail").innerHTML;
  check(!!clicked && detailHtml.indexOf(esc(clicked)) !== -1,
    "clicking a drawn point opens its decision (" + clicked + ")");
  check(detailHtml.indexOf("Ouvrir la source") !== -1,
    "the clicked point's panel carries the source link");

  /* The sidebar panels the product exists to show: clusters and the independent
   * counter-authority / discovery pass. */
  const clusterHtml = documentShim.getElementById("clusterList").innerHTML;
  check((bundle && (bundle.clusters || []).length) > 0 && clusterHtml.indexOf("C0") !== -1,
    "the cluster panel lists the map's clusters");
  const counterHtml = documentShim.getElementById("counterList").innerHTML;
  check(counterHtml.length > 0, "the counter-authority panel rendered");

  let failed = 0;
  for (const a of assertions) {
    if (!a.ok) failed += 1;
    console.log((a.ok ? "ok" : "FAIL") + " - " + a.label);
  }
  console.log("status: " + esc(statusText));
  console.log(failed === 0
    ? "PASS " + assertions.length + " assertions"
    : "FAIL " + failed);
  process.exit(failed === 0 ? 0 : 1);
})().catch((err) => {
  console.error("driver error: " + (err && err.message ? err.message : err));
  process.exit(1);
});
