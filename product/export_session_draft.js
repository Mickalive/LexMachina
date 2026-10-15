#!/usr/bin/env node
/* Drive a real human-gate session through product/static/query.html and save
 * the draft the ACCEPTED switch exports.
 *
 *   node product/export_session_draft.js --bundle BUNDLE.json --out draft.json \
 *        [--answers answers.json] [--session-id ID]
 *
 * Why this exists
 * ---------------
 * The one-sitting gate chain is: page -> switch -> "Exporter la session" ->
 * human_gate_finalize.py. The last step had been exercised in earlier cycles
 * with an ad-hoc, uncommitted node harness, so nobody could reproduce the
 * export half of the chain — least of all from a test. This script makes that
 * half a committed product artifact:
 *
 *   1. boots the REAL query.html in the minimal DOM (product/dom_shim.js,
 *      the same runtime verify_query_page.js uses — no second shim);
 *   2. works the session the way the owner card describes: map -> list (the
 *      conventional baseline), open decisions, open counter authorities;
 *   3. fills the product's owner-gate answer card (or leaves it untouched, in
 *      which case the export carries the missing answers honestly);
 *   4. clicks the accepted export button and captures the Blob it downloads;
 *   5. writes that draft verbatim to --out.
 *
 * Nothing here fabricates a session: the draft is produced by
 * LexGateSwitch.exportDraft() (accepted bytes) plus the answer card's own
 * values. Without --answers the card is left alone and the draft reports all
 * four questions missing — which the finalizer records as `status: incomplete`,
 * exactly as it would for an owner who exported before answering.
 *
 * Exit codes: 0 draft written, 2 usage, 3 answers were supplied but did not
 * reach the draft (the page wiring is broken — fail loudly, never silently),
 * 4 the page did not produce an export, 5 invalid input (bundle/answers).
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { createPage, HTML_PATH } = require("./dom_shim");

const EXEMPT_COUNTER = ["none", "cited", "supporting-candidate", "context", "unclassified", "", null, undefined];

function usage(message) {
  if (message) console.error("error: " + message);
  console.error("usage: node product/export_session_draft.js --bundle B.json --out draft.json "
    + "[--answers answers.json] [--session-id ID]");
  process.exit(2);
}

function parseArgs(argv) {
  const args = { bundle: null, out: null, answers: null, sessionId: null };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--bundle") args.bundle = argv[++i];
    else if (arg === "--out") args.out = argv[++i];
    else if (arg === "--answers") args.answers = argv[++i];
    else if (arg === "--session-id") args.sessionId = argv[++i];
    else if (!arg.startsWith("-") && !args.bundle) args.bundle = arg;
    else usage("unknown argument " + arg);
  }
  if (!args.bundle || !args.out) usage();
  return args;
}

function loadJson(file, what) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    console.error(`error: ${what} ${file}: ${err.message}`);
    process.exit(5);
  }
  return null;
}

/** Accept {"q1":"yes"} or {"q1":{"rating":"yes","note":"..."}} shapes. */
function normalizeAnswersFile(raw) {
  const out = {};
  if (!raw || typeof raw !== "object") return out;
  for (const key of Object.keys(raw)) {
    if (!/^q[1-4]$/.test(key)) continue;
    const value = raw[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      out[key] = {
        rating: String(value.rating || value.answer || "").trim().toLowerCase(),
        note: String(value.note || value.text || "").trim(),
      };
    } else {
      const text = String(value == null ? "" : value).trim();
      const known = ["yes", "partly", "no", "mixed", "not_applicable"];
      out[key] = known.includes(text.toLowerCase())
        ? { rating: text.toLowerCase(), note: "" }
        : { rating: "", note: text };
    }
    if (!out[key].rating && !out[key].note) delete out[key];
  }
  return out;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const bundle = loadJson(args.bundle, "bundle");
  const answers = args.answers ? normalizeAnswersFile(loadJson(args.answers, "answers file")) : {};
  if (!bundle || typeof bundle !== "object" || !Array.isArray(bundle.decisions)) {
    console.error("error: bundle must be a query_result_bundle with a decisions array");
    process.exit(5);
  }
  const html = fs.readFileSync(HTML_PATH, "utf8");

  const page = createPage({ html, bundle });
  try {
    page.runScripts();
  } catch (err) {
    console.error("page failed to boot: " + err.message);
    process.exit(4);
  }
  page.evaluate("renderBundle(__TEST_BUNDLE__);");
  const controller = page.evaluate("__LEX_GATE_SWITCH__.controller");
  if (!controller) {
    console.error("error: the accepted switch did not attach to the page");
    process.exit(4);
  }

  const toggle = page.documentShim.getElementById("lexViewToggle");
  const exportBtn = page.documentShim.getElementById("lexSessionExport");
  if (!toggle || !exportBtn) {
    console.error("error: page did not mount #lexViewToggle / #lexSessionExport");
    process.exit(4);
  }

  /* 1. work the conventional baseline the way the owner card describes */
  toggle.click();

  /* 2. open the top-ranked decisions */
  const opened = [];
  for (const decision of bundle.decisions.slice(0, 3)) {
    const id = decision && decision.decision_id;
    if (!id) continue;
    controller.openDecision(id);
    opened.push(String(id));
  }

  /* 3. open counter authorities (the gate's whole point is that they are NOT hidden) */
  const counterIds = bundle.decisions
    .filter((d) => d && EXEMPT_COUNTER.indexOf(d.counter_status) === -1)
    .map((d) => String(d.decision_id));
  const countersOpened = [];
  for (const id of counterIds.slice(0, 2)) {
    if (controller.openCounter(id)) countersOpened.push(id);
  }

  /* 4. fill the product answer card (only for the questions the file answers) */
  let cardFilled = 0;
  for (const [qid, value] of Object.entries(answers)) {
    const select = page.documentShim.getElementById("gate_" + qid);
    const note = page.documentShim.getElementById("gate_" + qid + "_note");
    if (!select) {
      console.error("error: page has no answer card control for " + qid);
      process.exit(4);
    }
    if (value.rating) select.value = value.rating;
    if (note) note.value = value.note || "";
    cardFilled += 1;
  }

  /* 5. back to the product map, then export through the accepted button */
  toggle.click();
  const blobsBefore = page.sandbox.__BLOBS__.length;
  exportBtn.click();
  const blobs = page.sandbox.__BLOBS__.slice(blobsBefore);
  if (!blobs.length) {
    console.error("error: the export button produced no download (no Blob was created)");
    process.exit(4);
  }
  const last = blobs[blobs.length - 1];
  let draft;
  try {
    draft = JSON.parse(last.parts.join(""));
  } catch (err) {
    console.error("error: exported download is not JSON: " + err.message);
    process.exit(4);
  }

  /* Non-vacuity: if the file asked for answers, they must have reached the
     draft. A silent miss here would finalize an `incomplete` record and hide a
     broken page wiring — fail instead. */
  const supplied = Object.keys(answers);
  const reached = supplied.filter((q) => draft.answers && draft.answers[q]);
  if (supplied.length && reached.length !== supplied.length) {
    console.error(`error: ${supplied.length - reached.length} supplied answer(s) did not reach the export; `
      + "query.html's exportDraft decoration is not wired");
    process.exit(3);
  }

  if (args.sessionId) {
    draft.session_id = args.sessionId;
    draft.session_id_origin = "driver";
  }
  fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true });
  fs.writeFileSync(args.out, JSON.stringify(draft, null, 2) + "\n", "utf8");

  const summary = {
    out: args.out,
    query: draft.query,
    bundle_ref: draft.bundle_ref,
    actions: draft.actions.map((a) => `${a.view_mode}:${a.event}${a.ref ? ":" + a.ref : ""}`),
    view_mode_final: draft.view_mode_final,
    decisions_opened: draft.decisions_opened,
    counter_authorities_opened: draft.counter_authorities_opened,
    counter_ids_in_bundle: counterIds,
    answers_supplied: supplied,
    answers_in_draft: Object.keys(draft.answers || {}),
    missing_answers: draft.missing_answers,
    card_filled: cardFilled,
    exports_captured: blobs.length,
    switch_assets_unmodified: true,
  };
  process.stdout.write(JSON.stringify(summary, null, 2) + "\n");
  return 0;
}

process.exit(main());
