#!/usr/bin/env node
/* Canvas-level probe for the REAL map draw() of product/static/query.html.
 *
 *   node product/canvas_probe.js BUNDLE.json [HTML_PATH]   -> JSON on stdout
 *   const { measure } = require("./canvas_probe");
 *
 * Why this exists
 * ---------------
 * The DOM shim's default 2D context is a no-op Proxy, so every assertion about
 * the map was predicate-level: the ring a researcher actually SEES was not
 * assertable.  Cycle 38877693206's audit recorded that hole as "minor
 * observation"; cycle 38885055655 then shipped a one-line render change that
 * silently removed 16 of 16 amber "unevidenced, retained for visibility"
 * contours from the served packet while the frozen suite stayed green
 * (429 passed / 2 skipped) — the exact defect surface.
 *
 * This probe closes it.  It boots the unmodified page in the shipped dom_shim,
 * patches ONLY the `cv.getContext("2d")` acquisition so a recording context
 * captures stroke() calls with the strokeStyle/dash live at that instant, then
 * runs the real `draw()` against a real bundle and reports how many contours of
 * each contract colour were drawn.  No draw() logic, no predicate and no
 * assertion lives here: this module measures, the test asserts.
 *
 * What it deliberately does NOT do: touch the page source, fetch anything
 * (dom_shim's fetch always rejects), or interpret "more rings = better map".
 * The counts are a render-contract check against the accepted v55 state, never
 * a quality claim.
 */
"use strict";

const fs = require("fs");
const { createPage, HTML_PATH } = require("./dom_shim");

/* Contract colours, verbatim from query.html's draw(). */
const STROKE = {
  red: "#b72736",     /* evidenced counter authority: confident ring      */
  amber: "#8a6d1f",   /* unevidenced counter, retained for visibility    */
  gold: "#d59b00",    /* cited authority                                 */
  discovery: "#00b3c8", /* found by the independent adversarial pass:
                            DISCOVERY provenance, never a qualification */
};

/**
 * A recording 2D context.  Properties are read at stroke() time, so a stroke
 * records the style/dash the page had set for THAT call — exactly what a
 * browser would paint.
 */
function recordingContext() {
  return {
    ops: [],
    strokeStyle: null,
    fillStyle: null,
    lineWidth: null,
    globalAlpha: 1,
    _dash: [],
    clearRect() {},
    beginPath() {},
    arc() {},
    fill() { this.ops.push({ kind: "fill", fillStyle: this.fillStyle }); },
    stroke() {
      this.ops.push({
        kind: "stroke",
        strokeStyle: this.strokeStyle,
        dash: (this._dash || []).slice(),
      });
    },
    setLineDash(d) { this._dash = Array.isArray(d) ? d.slice() : []; },
    reset() { this.ops.length = 0; },
  };
}

function countByStyle(ops) {
  const out = { red: 0, amber: 0, gold: 0, discovery: 0, dashed_other: 0, stroke_total: 0 };
  for (const op of ops) {
    if (op.kind !== "stroke") continue;
    out.stroke_total += 1;
    if (op.strokeStyle === STROKE.red) out.red += 1;
    else if (op.strokeStyle === STROKE.amber) out.amber += 1;
    else if (op.strokeStyle === STROKE.gold) out.gold += 1;
    else if (op.strokeStyle === STROKE.discovery) out.discovery += 1;
    else if (op.dash && op.dash.length) out.dashed_other += 1;
  }
  return out;
}

/* direction v50 obligation (4): per-colour fill counts.  A fill with fillStyle === undefined or null is
 * an INVALID value the real canvas ignores — exactly the negative-cluster_id
 * defect RENDERER_PRECONDITION.json names.  `fill_undefined` makes that bug
 * assertable from a test instead of invisible. */
function countFills(ops) {
  const byColor = {};
  let undefinedFills = 0;
  for (const op of ops) {
    if (op.kind !== "fill") continue;
    if (op.fillStyle === undefined || op.fillStyle === null) undefinedFills += 1;
    else byColor[op.fillStyle] = (byColor[op.fillStyle] || 0) + 1;
  }
  return { fill_colors: byColor, fill_undefined: undefinedFills };
}

/**
 * Run the page's own draw() once against `bundle` and report what it painted.
 *
 * @param {{html?: string, bundle: object, search?: string}} opts
 * @returns {{pts:number, fills:number, red:number, amber:number, gold:number, discovery:number, ...}}
 */
function measure(opts) {
  const options = opts || {};
  if (!options.bundle) throw new Error("canvas_probe.measure requires a bundle");
  const html = options.html != null ? options.html : fs.readFileSync(HTML_PATH, "utf8");

  const page = createPage({ html, bundle: options.bundle, search: options.search || "" });
  const ctx = recordingContext();
  /* Patch ONLY the context acquisition, before the inline page script evaluates
   * `const cv=..., ctx=cv.getContext("2d")`.  draw() itself is untouched. */
  const cv = page.registry.get("cv");
  if (!cv) throw new Error("query.html exposes no #cv canvas to the dom_shim");
  cv.getContext = () => ctx;

  page.runScripts();
  page.evaluate("renderBundle(__TEST_BUNDLE__);");
  /* fit() sizes the canvas against its parent pane the way a browser would, and
   * it draws once; reset afterwards so the report is exactly ONE draw() pass. */
  page.evaluate("fit();");
  ctx.reset();
  page.evaluate("draw();");

  const counts = countByStyle(ctx.ops);
  const fillCounts = countFills(ctx.ops);
  const pts = page.evaluate("PTS.length");
  const fills = ctx.ops.filter((op) => op.kind === "fill").length;
  return Object.assign({ pts, fills, draw_calls: 1 }, counts, fillCounts);
}

function main(argv) {
  const bundlePath = argv[2];
  if (!bundlePath) {
    console.error("usage: node product/canvas_probe.js BUNDLE.json [HTML_PATH]");
    process.exit(2);
  }
  const htmlPath = argv[3];
  const bundle = JSON.parse(fs.readFileSync(bundlePath, "utf8"));
  const html = htmlPath ? fs.readFileSync(htmlPath, "utf8") : undefined;
  const report = measure({ html, bundle });
  report.bundle = bundlePath;
  report.html = htmlPath || HTML_PATH;
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}

if (require.main === module) {
  try {
    main(process.argv);
  } catch (err) {
    console.error("canvas probe failed: " + (err && err.stack || err));
    process.exit(1);
  }
}

module.exports = { measure, recordingContext, STROKE };
