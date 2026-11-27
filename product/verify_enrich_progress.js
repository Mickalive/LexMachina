#!/usr/bin/env node
/* Behavioural contract of the shipped enrich progress tick.
 *
 *   node product/verify_enrich_progress.js BUNDLE.json [HTML_PATH]
 *
 * Why this exists
 * ---------------
 * The enrich leg (sourced answer + independent counter-authority pass) is the
 * one part of the query path that is NOT sub-second.  Measured live on
 * 2026-11-27 against real OpenCaseLaw (run 61e701394b1b): 319.68 s inside
 * ``enrich_query_bundle``, of which the model answer, the adversarial retrieval
 * and the counter-surface hydration are the bulk.  Before this change the
 * browser had exactly one signal for those five minutes — an elapsed-seconds
 * counter — so a jurist could not tell a running generation from a hung tab,
 * and nothing was painted until the whole leg finished.
 *
 * QUERY_MAP_MVP 9A asks for the opposite: "stream/generate the sourced answer"
 * and "run the adversarial/counter-authority pass in parallel or immediately
 * after the provisional answer" are separate milestones, and the map must not
 * wait for either.  The product therefore publishes the answer bundle as soon
 * as the answer contract is complete, keeps the counter pass running behind it,
 * and names the leg that is running.
 *
 * This script executes the SHIPPED page script in a minimal DOM and proves the
 * three properties the jurist's first five minutes depend on:
 *
 *   1. a pending tick names the running leg in both the answer panel and the
 *      status line, instead of only counting seconds;
 *   2. the first ready tick paints the answer milestone exactly once;
 *   3. subsequent ready ticks (the counter pass is still running) never wipe
 *      the painted answer with a placeholder.
 *
 * It is a page-behaviour smoke test.  It makes no claim about answer quality,
 * counter-authority soundness or legal usefulness — that is the human gate.
 *
 * The DOM/script runtime lives in product/dom_shim.js.
 */
"use strict";

const fs = require("fs");
const { createPage, HTML_PATH } = require("./dom_shim");

const bundlePath = process.argv[2];
if (!bundlePath) {
  console.error("usage: node product/verify_enrich_progress.js BUNDLE.json [HTML_PATH]");
  process.exit(2);
}

const bundle = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
const html = fs.readFileSync(process.argv[3] || HTML_PATH, "utf8");

const assertions = [];
function check(condition, label) { assertions.push({ ok: !!condition, label }); }

let page;
try {
  page = createPage({ html, bundle, search: "" });
  const inlineCount = page.runScripts();
  check(inlineCount >= 1, "query.html exposes an inline page script");
} catch (err) {
  console.error("page failed to boot: " + err.message);
  process.exit(1);
}

const documentShim = page.documentShim;
const statusEl = documentShim.getElementById("status");
const proseEl = documentShim.getElementById("prose");

/* The shim keeps innerHTML and textContent as two independent slots, exactly
 * like a browser element the page only ever writes ONE of.  renderAnswer()
 * writes innerHTML; the pending placeholder writes textContent.  Both are read
 * separately so an assertion can never pass on the other slot's stale value. */
function proseHTML() { return proseEl.innerHTML || ""; }
function proseText() { return proseEl.textContent || ""; }
function status() { return statusEl.innerHTML || ""; }
function tick(state, job) {
  return page.evaluate("enrichTick(" + JSON.stringify(state) + "," + JSON.stringify(job) + ")");
}
function stateOf(o) {
  const s = {
    run_id: "verify",
    counts: { decisions: 163, clusters: 8 },
    answer: { status: "pending", method: "", model: "", cited: 0 },
    jobs: { enrich: { status: "running", elapsed_s: 42, error: null, detail: {} } },
  };
  if (!o) return s;
  if (o.counts) s.counts = Object.assign({}, s.counts, o.counts);
  if (o.answer) s.answer = Object.assign({}, s.answer, o.answer);
  if (o.jobs) {
    s.jobs = Object.assign({}, s.jobs, o.jobs);
    s.jobs.enrich = Object.assign(
      { status: "running", elapsed_s: 42, error: null, detail: {} },
      (o.jobs && o.jobs.enrich) || s.jobs.enrich
    );
  }
  return s;
}

/* --- 1. the shipped page exposes the tick ------------------------------ */
check(page.evaluate("typeof enrichTick") === "function",
      "the shipped page exposes enrichTick()");
page.evaluate("ENRICH_ANSWER_PAINTED=false;");

/* --- 2. a pending tick names the running leg --------------------------- */
const pending = stateOf({
  jobs: { enrich: {
    status: "running", elapsed_s: 42, error: null,
    detail: { stage: "answer", stage_label: "génération de la réponse" },
  } },
});
const pendingPainted = tick(pending, { status: "running", elapsed_s: 42 });
check(pendingPainted === false,
      "a pending tick does not claim the answer milestone");
check(proseText().indexOf("génération de la réponse") !== -1,
      "the answer panel names the running leg: " + JSON.stringify(proseText().slice(0, 100)));
check(status().indexOf("génération de la réponse") !== -1,
      "the status line names the running leg");
check(status().indexOf("42") !== -1,
      "the status line keeps reporting elapsed seconds");

/* --- 3. the milestone bundle paints the answer -------------------------- */
page.evaluate(
  "renderBundle(Object.assign({},__TEST_BUNDLE__,{answer:{status:'ready',"
  + "method:'generative_audit_llm_v2',model:'verify',"
  + "prose:'Réponse sourc\u00e9e de test.',cited_decision_ids:[]}}));"
);
const paintedHTML = proseHTML();
check(paintedHTML.length > 0,
      "the answer panel carries the sourced answer once the milestone lands");
check(paintedHTML.indexOf("Analyse en cours") === -1,
      "the painted answer is a real answer, not the pending placeholder");

/* --- 4. first ready tick claims the milestone exactly once --------------- */
const ready = stateOf({
  answer: { status: "ready" },
  jobs: { enrich: {
    status: "running", elapsed_s: 301, error: null,
    detail: { stage: "counter_surface", stage_label: "balayage de la surface contredite" },
  } },
});
const firstReady = tick(ready, { status: "running", elapsed_s: 301 });
check(firstReady === true, "the first ready tick paints the answer milestone");
check(page.evaluate("ENRICH_ANSWER_PAINTED") === true,
      "the milestone is recorded as painted");

/* --- 5. later ticks never wipe the painted answer ----------------------- */
const secondReady = tick(ready, { status: "running", elapsed_s: 315 });
check(secondReady === false, "the milestone is painted once, not on every poll");
check(proseHTML() === paintedHTML,
      "the running counter pass never wipes the painted answer");
check(status().indexOf("réponse prête") !== -1,
      "the status line reports the answer as ready while the counter pass runs");
check(status().indexOf("passe contradictoire") !== -1,
      "the status line says the contradicting-authority pass is what is left");

/* --- 6. the honest degraded fallback is a milestone too ------------------ *
 * Measured live 2026-11-27 (run c03af101f48a): the generative writer produced
 * no citations, the answer-gap contract composed the extractive fallback and
 * status came back "degraded".  That answer is still complete and sourced, so
 * hiding it behind the same wait would defeat the milestone entirely. */
page.evaluate("ENRICH_ANSWER_PAINTED=false;");
const degradedMilestone = stateOf({
  answer: { status: "degraded" },
  jobs: { enrich: {
    status: "running", elapsed_s: 80, error: null,
    detail: { stage: "counter_retrieval", stage_label: "recherche des autorités contraires" },
  } },
});
const degradedPainted = tick(degradedMilestone, { status: "running", elapsed_s: 80 });
check(degradedPainted === true,
      "a degraded fallback answer is a milestone too, not a reason to keep waiting");
check(status().indexOf("mode dégradé") !== -1,
      "the status line discloses that the fallback answer, not a generated one, is ready");
check(status().indexOf("recherche des autorités contraires") !== -1,
      "the status line still names the leg that is running");

/* --- 7. an unexpected job shape degrades, it never throws ---------------- */
let threw = false;
try {
  tick({ counts: { decisions: 0, clusters: 0 },
         answer: { status: "pending" },
         jobs: { enrich: { status: "running" } } }, { status: "running" });
} catch (e) { threw = true; }
check(!threw, "a status without a stage detail still does not throw");

let failed = 0;
for (const a of assertions) {
  if (!a.ok) failed += 1;
  console.log((a.ok ? "ok" : "FAIL") + " - " + a.label);
}
console.log(failed === 0 ? "PASS " + assertions.length + " assertions" : "FAIL " + failed);
process.exit(failed === 0 ? 0 : 1);
