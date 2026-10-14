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
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const HTML_PATH = path.join(ROOT, "product", "static", "query.html");
const bundlePath = process.argv[2];
if (!bundlePath) {
  console.error("usage: node product/verify_query_page.js BUNDLE.json");
  process.exit(2);
}

const bundle = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
const html = fs.readFileSync(HTML_PATH, "utf8");

/* ---- minimal DOM ---------------------------------------------------------- */
const registry = new Map();
let fetchCalls = [];
const listeners = new WeakMap();

function makeEl(tag, id) {
  const el = {
    tagName: (tag || "div").toUpperCase(),
    _id: id || "",
    className: "",
    type: "",
    innerHTML: "",
    textContent: "",
    value: "",
    hidden: false,
    disabled: false,
    style: {},
    attributes: {},
    childNodes: [],
    parentElement: null,
    setAttribute(k, v) { this.attributes[k] = String(v); },
    getAttribute(k) { return this.attributes[k]; },
    appendChild(child) { child.parentElement = this; this.childNodes.push(child); return child; },
    insertBefore(child, before) {
      child.parentElement = this;
      const at = before ? this.childNodes.indexOf(before) : 0;
      this.childNodes.splice(at < 0 ? 0 : at, 0, child);
      return child;
    },
    removeChild(child) {
      const at = this.childNodes.indexOf(child);
      if (at >= 0) this.childNodes.splice(at, 1);
      return child;
    },
    addEventListener(type, fn) {
      const key = this.id || this.tagName + (this.childNodes.length);
      if (!listeners.has(this)) listeners.set(this, {});
      const byType = listeners.get(this);
      (byType[type] = byType[type] || []).push(fn);
      void key;
    },
    /* click() replays registered listeners synchronously, in registration order */
    click() {
      const byType = listeners.get(this) || {};
      for (const fn of byType.click || []) fn({ preventDefault() {} });
    },
    getBoundingClientRect() { return { width: 900, height: 600, left: 0, top: 0 }; },
    getContext() {
      return new Proxy({}, {
        get(target, prop) {
          if (prop in target) return target[prop];
          return () => {};
        },
        set(target, prop, value) { target[prop] = value; return true; },
      });
    },
    querySelectorAll() { return []; },
    focus() {},
  };
  Object.defineProperty(el, "firstChild", {
    get() { return this.childNodes[0] || null; },
  });
  /* dynamically created elements must become findable by id, exactly as in a browser */
  Object.defineProperty(el, "id", {
    get() { return this._id; },
    set(value) {
      this._id = String(value);
      if (this._id) registry.set(this._id, this);
    },
  });
  return el;
}

/* Register every id the page declares so getElementById resolves statically. */
const idRe = /id="([A-Za-z_][\w-]*)"/g;
let match;
while ((match = idRe.exec(html)) !== null) {
  if (!registry.has(match[1])) registry.set(match[1], makeEl("div", match[1]));
}
/* The canvas measures itself against its parent pane. */
if (registry.has("cv") && registry.has("mapWrap")) {
  registry.get("cv").parentElement = registry.get("mapWrap");
}

const documentShim = {
  body: makeEl("body"),
  createElement(tag) { return makeEl(tag); },
  createTextNode(text) { return { textContent: String(text) }; },
  getElementById(id) { return registry.get(id) || null; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  documentElement: makeEl("html"),
};

const sandbox = {
  document: documentShim,
  console,
  Math,
  Date,
  JSON,
  Object,
  Array,
  Number,
  String,
  Boolean,
  RegExp,
  Promise,
  Error,
  isFinite,
  parseInt,
  parseFloat,
  encodeURIComponent,
  decodeURIComponent,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  Blob: function Blob(parts) { this.parts = parts; },
  URL: { createObjectURL: () => "blob:offline", revokeObjectURL: () => {} },
  __TEST_BUNDLE__: bundle,
  __FETCHES__: fetchCalls,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.addEventListener = function () {};
sandbox.fetch = function (url) {
  fetchCalls.push(String(url));
  return Promise.reject(new Error("offline verification: network is disabled"));
};
sandbox.global = sandbox;

const ctx = vm.createContext(sandbox);

/* Run the switch asset first (it is a separate <script src>), then the page. */
function scriptSrc(src) {
  const re = new RegExp('<script src="' + src.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + '"></script>');
  const found = re.exec(html);
  if (!found) throw new Error("query.html does not load " + src);
  const file = path.join(ROOT, "product", "static", path.basename(src));
  return fs.readFileSync(file, "utf8");
}

function inlineScripts() {
  const out = [];
  const re = /<script>([\s\S]*?)<\/script>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.push(m[1]);
  return out;
}

const assertions = [];
function check(condition, label) { assertions.push({ ok: !!condition, label }); }

try {
  vm.runInContext(scriptSrc("/static/lex_gate_switch.js"), ctx, { filename: "lex_gate_switch.js" });
  const inlines = inlineScripts();
  check(inlines.length >= 1, "query.html exposes an inline page script");
  for (const src of inlines) vm.runInContext(src, ctx, { filename: "query.html" });
} catch (err) {
  console.error("page failed to boot: " + err.message);
  process.exit(1);
}

const toggle = documentShim.getElementById("lexViewToggle");
const toolbar = documentShim.getElementById("toolbar");
check(!!toggle, "boot mounts #lexViewToggle");
check(!!toggle && toolbar.childNodes[0] === toggle, "toggle is the first child of #toolbar");
check(!!documentShim.getElementById("lexSessionExport"), "boot mounts the session export button");

/* Render the real bundle the way a completed query does. */
vm.runInContext("renderBundle(__TEST_BUNDLE__);", ctx, { filename: "drive" });

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
  const controller = vm.runInContext("__LEX_GATE_SWITCH__.controller", ctx);
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

  let failed = 0;
  for (const a of assertions) {
    if (!a.ok) failed += 1;
    console.log((a.ok ? "ok" : "FAIL") + " - " + a.label);
  }
  console.log(failed === 0 ? "PASS " + assertions.length + " assertions" : "FAIL " + failed);
  process.exit(failed === 0 ? 0 : 1);
}, 0);