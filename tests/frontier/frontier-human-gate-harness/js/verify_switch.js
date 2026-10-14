#!/usr/bin/env node
/* Offline verification for static/lex_gate_switch.js (zero dependencies).
 *
 *   node verify_switch.js                      -> assertions, exit 0/1
 *   node verify_switch.js --emit-fixture FILE  -> {"model":[...],"rows":"..."} on stdout
 *
 * Used by tests/frontier/frontier-human-gate-harness/test_switch.py, which
 * compares the emitted rows against the Python renderer byte for byte.
 */
"use strict";

const path = require("path");
const fs = require("fs");

const SWITCH_PATH = path.resolve(
  __dirname, "../../../../frontier/frontier-human-gate-harness/static/lex_gate_switch.js");
const LexGateSwitch = require(SWITCH_PATH);

const args = process.argv.slice(2);
if (args[0] === "--emit-fixture") {
  const bundle = JSON.parse(fs.readFileSync(args[1], "utf8"));
  /* fs.writeSync: process.exit() can truncate an in-flight async pipe write */
  fs.writeSync(1, Buffer.from(JSON.stringify({
    model: LexGateSwitch.buildListModel(bundle),
    rows: LexGateSwitch.renderRowsHtml(bundle),
    list_fields: LexGateSwitch.LIST_FIELDS
  }), "utf8"));
  process.exit(0);
}

let passed = 0;
let failed = 0;
function ok(condition, label) {
  if (condition) { passed += 1; console.log("ok " + (passed + failed) + " - " + label); }
  else { failed += 1; console.log("FAIL: " + label); }
}

/* ---- synthetic test data (test fixture only, not evidence) ---------------- */
const longSnippet = "x".repeat(320);
const syntheticBundle = {
  bundle_version: "1.0",
  query: "Synthetische Testanfrage",
  query_variants: [],
  answer: { status: "fixture", prose: "", cited_decision_ids: [] },
  decisions: [
    { decision_id: "d_b", court: "bger", decision_date: "2020-01-01", language: "de",
      rank: 2, citation: ["BGE 1", "BGE 2"], snippet: "zweite", canonical_url: "https://example.org/b",
      cluster_id: 0, x: 0.1, y: 0.2, counter_status: "unclassified", score: 1 },
    { decision_id: "d_a", court: "bge", decision_date: "2019-05-05", language: "fr",
      rank: 1, citation: "ATF 1", snippet: "erste", canonical_url: "https://example.org/a",
      cluster_id: 1, x: 0.3, y: 0.4, counter_status: "unclassified", score: 2 },
    { decision_id: "d_tie1", court: "gh", decision_date: "2021-02-02", language: "it",
      rank: 2, citation: null, snippet: longSnippet, canonical_url: "javascript:alert(1)",
      cluster_id: 1, x: 0.5, y: 0.6, counter_status: "unclassified", score: 3 },
    { decision_id: "d_contra", court: "gh", decision_date: "2022-03-03", language: "de",
      rank: 3, citation: "GC 1", snippet: "<img src=x onerror=alert(1)> & <b>raw</b>",
      canonical_url: "", cluster_id: 2, x: 0.7, y: 0.8, counter_status: "candidate-contrary",
      score: 4 },
    { decision_id: "d_nulls", court: null, decision_date: null, language: null,
      rank: "4", citation: null, snippet: null, canonical_url: null,
      cluster_id: 0, x: 0, y: 0, counter_status: "unclassified", score: 5 },
    { decision_id: "d_uncounted", court: "vd", decision_date: "2023-04-04", language: "fr",
      rank: 5, citation: "GH 2", snippet: "ok", canonical_url: "http://example.org/u",
      cluster_id: 3, x: 0, y: 0, counter_status: "unclassified", score: 6 }
  ],
  clusters: [],
  relations: [],
  provenance: {}
};

function deepFreeze(node) {
  if (node && typeof node === "object" && !Object.isFrozen(node)) {
    Object.freeze(node);
    Object.keys(node).forEach(function (key) { deepFreeze(node[key]); });
  }
  return node;
}

/* ---- 1. model order and fields ------------------------------------------- */
const model = LexGateSwitch.buildListModel(syntheticBundle);
ok(model.length === 6, "one row per decision");
ok(JSON.stringify(model.map(r => r.rank)) === JSON.stringify([1, 2, 2, 3, 4, 5]),
   "rows sorted ascending by rank");
ok(model[1].decision_id === "d_b" && model[2].decision_id === "d_tie1",
   "equal ranks keep bundle order (stable sort)");
ok(JSON.stringify(Object.keys(model[0])) === JSON.stringify(LexGateSwitch.LIST_FIELDS),
   "row has exactly the 8 LIST_FIELDS keys, no extras");
ok(model[0].decision_id === "d_a" && model[0].citation === "ATF 1" && model[0].rank === 1,
   "first row is rank 1 with its fields");
ok(model[2].snippet.length === 301 && model[2].snippet.slice(-1) === "\u2026",
   "snippet longer than 300 chars truncated to 300 + ellipsis");
ok(model[4].court === "" && model[4].decision_date === "" && model[4].language === ""
   && model[4].snippet === "" && model[4].canonical_url === "",
   "null values coerce to empty string, never null/undefined/None");
ok(model[0].citation === "ATF 1" && model[1].citation === "BGE 1 \u00b7 BGE 2",
   "array citation joined with ' \u00b7 '");
ok(model[4].rank === 4 && typeof model[4].rank === "number",
   "numeric string rank coerced to number");

/* ---- 2. no map/semantic leakage in the baseline --------------------------- */
const rows = LexGateSwitch.renderRowsHtml(syntheticBundle);
ok(!/cluster/i.test(rows), "rendered rows mention no cluster");
ok(!/counter/i.test(rows), "rendered rows mention no counter status");
ok(!/#[0-9a-fA-F]{6}\b/.test(rows), "rendered rows contain no hex colour");
ok(!/\sx="/.test(rows) && !/\sy="/.test(rows), "rendered rows contain no x/y proximity");
ok(!/candidate-contrary/.test(rows), "counter classification never reaches the baseline");
ok(!/<img/i.test(rows) && rows.indexOf("<img src=x") === -1, "HTML in snippets is escaped");
ok(rows.indexOf("&lt;img src=x onerror=alert(1)&gt; &amp; &lt;b&gt;raw&lt;/b&gt;") !== -1,
   "escaping matches the product esc() rule");
ok(rows.indexOf("lex-source-missing") !== -1,
   "non-http(s) canonical_url replaced by the source-missing placeholder");
ok(rows.split("\n").length === 6, "one line per decision");

/* ---- 3. switch controller: no mutation, no retrieval ---------------------- */
const frozen = deepFreeze(JSON.parse(JSON.stringify(syntheticBundle)));
const snapshot = JSON.stringify(frozen);
const clock = "2026-01-01T00:00:00Z";
const opened = [];
const controller = LexGateSwitch.createController({
  getBundle: function () { return frozen; },
  now: function () { return clock; },
  openDetail: function (id) { opened.push(id); }
});
let threw = false;
try {
  controller.switchTo("list");
  controller.switchTo("map");
  controller.toggle();
  controller.openDecision("d_a");
  controller.openDecision("d_a");
  controller.openCounter("d_contra");
  controller.openCounter("d_uncounted");
} catch (err) { threw = true; console.log("   threw: " + err.message); }
ok(!threw, "controller never writes to a deep-frozen bundle");
ok(JSON.stringify(frozen) === snapshot, "bundle JSON byte-identical after switching");
ok(opened.length === 2 && opened[0] === "d_a", "openDetail called with the decision id");
ok(controller.viewMode === "list", "toggle ends on the opposite view");
ok(controller.actions.filter(a => a.event === "switch").length === 3,
   "one action per switch/view change");
ok(controller.actions.every(a => a.view_mode === "map" || a.view_mode === "list"),
   "every action records its view mode");
ok(controller.actions.every(a => a.at === clock),
   "actions carry the injected timestamp (deterministic)");
ok(JSON.stringify(controller.decisionsOpened) === JSON.stringify(["d_a"]),
   "decisions_opened is order-preserving unique");
ok(controller.openCounter("d_contra") === true
   && controller.openCounter("d_contra") === true
   && controller.openCounter("d_uncounted") === false,
   "openCounter records only real counter authorities");
ok(JSON.stringify(controller.counterOpened) === JSON.stringify(["d_contra"]),
   "counter_authorities_opened holds only counter decisions");
ok(controller.bundleRef().query === "Synthetische Testanfrage"
   && controller.bundleRef().n_decisions === 6,
   "bundleRef reports query and decision count");

/* ---- 4. capture draft schema --------------------------------------------- */
const draft = controller.exportDraft({ session_id: null, view_mode_initial: "map" });
const expectedKeys = ["schema_version", "record_type", "team_id", "charter_version",
  "session_id", "session_id_origin", "status", "source", "query", "bundle_ref",
  "bundle_sha256", "bundle_hash_status", "started_at", "ended_at",
  "wall_clock_seconds", "view_mode_initial", "view_mode_final", "actions",
  "decisions_opened", "counter_authorities_opened", "answers", "missing_answers",
  "latency"];
ok(JSON.stringify(Object.keys(draft)) === JSON.stringify(expectedKeys),
   "draft has exactly the capture schema keys in order");
ok(JSON.stringify(draft.missing_answers) === JSON.stringify(["q1", "q2", "q3", "q4"]),
   "draft lists all four unanswered questions explicitly");
ok(Object.keys(draft.answers).length === 0, "draft never invents an answer");
ok(draft.bundle_sha256 === null && draft.bundle_hash_status === "not_verified",
   "draft does not claim a bundle hash it did not compute");
ok(draft.source === "switch" && draft.status === "draft"
   && draft.record_type === "lex_human_gate_session" && draft.charter_version === 1,
   "draft identity fields");
const withId = controller.exportDraft({ session_id: "owner-1", session_id_origin: "draft" });
ok(withId.session_id === "owner-1" && withId.session_id_origin === "draft",
   "session id and its origin travel together");

/* ---- 5. offline guarantees ------------------------------------------------ */
const rawSource = fs.readFileSync(SWITCH_PATH, "utf8");
/* scan BOTH the raw file and a comment-stripped form (a token hidden in a
   comment would still be a greppable liability for the offline audit) */
const codeOnly = rawSource
  .replace(/\/\*[\s\S]*?\*\//g, " ")
  .replace(/(^|[^:])\/\/[^\n]*/g, "$1 ");
["fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon",
 "importScripts", "@import"].forEach(function (token) {
  ok(rawSource.indexOf(token) === -1 && codeOnly.indexOf(token) === -1,
     "source contains no network token: " + token);
});
let domRequired = false;
try {
  /* requiring the module in Node (no DOM) must not throw or touch document */
  delete require.cache[require.resolve(SWITCH_PATH)];
  require(SWITCH_PATH);
} catch (err) { domRequired = true; }
ok(!domRequired, "module loads in Node without a DOM");
ok(typeof LexGateSwitch.attach === "function"
   && typeof LexGateSwitch.notifyBundleChanged === "function",
   "attach/notifyBundleChanged are exported for product integration");

/* ---- 6. badge: explicit baseline labelling -------------------------------- */
ok(LexGateSwitch.LABEL.indexOf("baseline") !== -1
   && LexGateSwitch.LABEL.indexOf("Baseline") !== -1,
   "switch renders the explicit conventional-baseline label");

console.log((failed === 0 ? "ALL " + passed + " ASSERTIONS PASSED"
                          : failed + " FAILED / " + (passed + failed)) + " ("
            + passed + " passed)");
process.exit(failed === 0 ? 0 : 1);
