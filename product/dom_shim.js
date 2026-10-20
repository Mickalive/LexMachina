/* Minimal DOM + script runtime for executing product/static/query.html offline.
 *
 * Why this exists
 * ---------------
 * Two product scripts need to boot the REAL page (switch asset + inline page
 * script) without a browser and without a network:
 *
 *   - product/verify_query_page.js   — DOM smoke of the clickable slice;
 *   - product/export_session_draft.js — drives a real gate session and captures
 *     the draft the accepted switch exports.
 *
 * Before this module both needs lived inside verify_query_page.js, so the second
 * script would have had to copy ~150 lines of shim that would then drift. The
 * shim is extracted once here and both scripts require() it; verify keeps its
 * own assertions and output unchanged.
 *
 * What is deliberately NOT here: any assertion, any session logic, any network.
 * The sandbox's fetch always rejects so a page that tries to re-retrieve during
 * boot or view switching fails loudly instead of silently.
 *
 *   const { createPage } = require("./dom_shim");
 *   const page = createPage({ html, bundle });
 *   page.runScripts();                 // switch asset first, then inline scripts
 *   page.context.renderBundle(page.context.__TEST_BUNDLE__);
 *   page.context.__BLOBS__             // every Blob the page produced (exports)
 */
"use strict";

const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const HTML_PATH = path.join(ROOT, "product", "static", "query.html");

function loadHtml() {
  return require("fs").readFileSync(HTML_PATH, "utf8");
}

/**
 * Boot `html` against `bundle` in a minimal DOM.
 *
 * Returns { html, sandbox, context, documentShim, registry, fetchCalls,
 *           scriptSrc, inlineScripts, runScripts }.
 */
function createPage(opts) {
  const options = opts || {};
  const html = options.html != null ? options.html : loadHtml();
  const bundle = options.bundle;

  const registry = new Map();
  const fetchCalls = [];
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

  /* Register every id the page declares so getElementById resolves statically.
   *
   * A <select> must report the value a browser would give it: its first
   * <option>'s value.  Stubbing value as "" made query.html's filtered() see
   * langFilter !== "all" and return [], so draw() never ran and no assertion
   * could touch the canvas - the harness certified a map it could not see. */
  const tagRe = /<([a-zA-Z][\w-]*)\b([^>]*)>/g;
  let match;
  while ((match = tagRe.exec(html)) !== null) {
    const tag = match[1];
    const attrs = match[2];
    const idMatch = /\bid="([A-Za-z_][\w-]*)"/.exec(attrs);
    if (!idMatch || registry.has(idMatch[1])) continue;
    const el = makeEl(tag, idMatch[1]);
    if (tag === "select") {
      const rest = html.slice(match.index + match[0].length);
      const close = rest.indexOf("</select>");
      const inner = close >= 0 ? rest.slice(0, close) : rest;
      const option = /<option\b([^>]*)>/.exec(inner);
      if (option) {
        const value = /\bvalue="([^"]*)"/.exec(option[1]);
        el.value = value ? value[1] : "";
      }
      /* select.options, as a browser exposes it: query.html's deep-link boot
       * only accepts ?n= values that are real options of this select. */
      el.options = [];
      const optionRe = /<option\b([^>]*)>/g;
      let opt;
      while ((opt = optionRe.exec(inner)) !== null) {
        const value = /\bvalue="([^"]*)"/.exec(opt[1]);
        el.options.push({ value: value ? value[1] : (opt[1].trim() || "") });
      }
    }
    registry.set(idMatch[1], el);
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
    /* Every Blob the page constructs is recorded so a script can read back the
       exported download (the switch serialises the draft into a Blob). */
    __BLOBS__: [],
    Blob: function Blob(parts) {
      this.parts = parts;
      sandbox.__BLOBS__.push(this);
    },
    URL: { createObjectURL: () => "blob:offline", revokeObjectURL: () => {} },
    /* Minimal URLSearchParams: the page parses its deep link (?q=&n=&run_id=) with
     * it at boot.  Parsing only, which is all boot() needs. */
    URLSearchParams: function URLSearchParams(query) {
      const params = new Map();
      String(query == null ? "" : query).replace(/^\?/, "").split("&").forEach((pair) => {
        if (!pair) return;
        const i = pair.indexOf("=");
        const key = decodeURIComponent(i < 0 ? pair : pair.slice(0, i));
        const value = i < 0 ? "" : decodeURIComponent(pair.slice(i + 1).replace(/\+/g, " "));
        if (!params.has(key)) params.set(key, value);
      });
      return {
        get(name) { return params.has(name) ? params.get(name) : null; },
        has(name) { return params.has(name); },
        keys() { return Array.from(params.keys()); },
      };
    },
    /* A page URL.  query.html reads window.location.search exactly once, at
     * boot, to decide whether to resume a deep-linked run or run a question.
     * The default empty search keeps the pre-deep-link behaviour (resume the
     * last local run) for every existing harness. */
    location: { search: (options && options.search) || "", href: "http://127.0.0.1/" },
    /* localStorage keeps resumeLastRun() honest offline: an empty store means
     * "nothing to resume", which is what a fresh browser looks like. */
    localStorage: {
      _store: new Map(),
      getItem(key) { return this._store.has(String(key)) ? this._store.get(String(key)) : null; },
      setItem(key, value) { this._store.set(String(key), String(value)); },
      removeItem(key) { this._store.delete(String(key)); },
    },
    __TEST_BUNDLE__: bundle,
    __FETCHES__: fetchCalls,
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.addEventListener = function () {};
  /* Every fetch the page makes is recorded.  By default the sandbox stays
   * offline (the pre-existing contract: a page that re-retrieves during a
   * render is a defect), but a caller may inject a real transport via
   * `options.fetchImpl` to drive the shipped page against a live server - the
   * page<->server integration seam.  The injected transport receives the same
   * absolute-or-relative URL string the browser would and must resolve with a
   * `{ ok, status, json() }` response, exactly as `fetch` does; a rejected
   * promise propagates as a fetch failure, so an unreachable server is a test
   * failure, never a silent pass. */
  sandbox.fetch = function (url) {
    fetchCalls.push(String(url));
    if (options.fetchImpl) return options.fetchImpl(String(url));
    return Promise.reject(new Error("offline verification: network is disabled"));
  };
  sandbox.global = sandbox;

  const context = vm.createContext(sandbox);

  /* Run the switch asset first (it is a separate <script src>), then the page. */
  function scriptSrc(src) {
    const re = new RegExp('<script src="' + src.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + '"></script>');
    const found = re.exec(html);
    if (!found) throw new Error("query.html does not load " + src);
    const file = path.join(ROOT, "product", "static", path.basename(src));
    return require("fs").readFileSync(file, "utf8");
  }

  function inlineScripts() {
    const out = [];
    const re = /<script>([\s\S]*?)<\/script>/g;
    let m;
    while ((m = re.exec(html)) !== null) out.push(m[1]);
    return out;
  }

  /** Execute the accepted switch asset, then every inline page script. */
  function runScripts() {
    vm.runInContext(scriptSrc("/static/lex_gate_switch.js"), context, { filename: "lex_gate_switch.js" });
    const inlines = inlineScripts();
    for (const src of inlines) vm.runInContext(src, context, { filename: "query.html" });
    return inlines.length;
  }

  /** Evaluate an expression inside the page context (driver sugar). */
  function evaluate(code) {
    return vm.runInContext(code, context, { filename: "driver" });
  }

  return {
    html,
    sandbox,
    context,
    documentShim,
    registry,
    fetchCalls,
    scriptSrc,
    inlineScripts,
    runScripts,
    evaluate,
  };
}

module.exports = { createPage, loadHtml, HTML_PATH, ROOT };
