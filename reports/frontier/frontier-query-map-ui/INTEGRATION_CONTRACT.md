# INTEGRATION CONTRACT — frontier-query-map-ui (charter v2)

Team: `frontier-query-map-ui`
Charter version: 2
GitHub run: 38179511140 (operational resume of producer snapshot 38175693552)
Status: ready for product-lane absorption

This document tells the **product lane exactly which files/components to absorb**
(charter acceptance item 9). Every item below is runnable today; nothing here is
a design proposal.

---

## 0. How to run the prototype

```bash
# from repository root
python3 frontier/frontier-query-map-ui/src/serve.py --port 8787
# then open http://127.0.0.1:8787/
```

Zero paid services. Stdlib HTTP server + accepted product static assets +
frozen fixture. No global 174k artifact is read at any point.

Regenerate the frozen fixture (offline, from the vendored 100-decision corpus):

```bash
python3 -m pip install numpy scikit-learn   # product/query/{qmap,pipeline} deps
python3 frontier/frontier-query-map-ui/src/build_fixture.py --top-n 150
```

Run the automated smoke tests (data + server + browser-equivalent):

```bash
python3 -m unittest discover -s tests/frontier/frontier-query-map-ui -v
```

---

## 1. Absorb these files (exact list)

| Absorb into product as | Frontier source | Kind |
|---|---|---|
| `product/query_map/adapter.py` | `frontier/frontier-query-map-ui/src/query_bundle_adapter.py` | bundle → visualization payload |
| `product/query_map/compat.py` | `frontier/frontier-query-map-ui/src/product_compat.py` | defect shim + `run_query` wrapper |
| `product/query_map/build_fixture.py` | `frontier/frontier-query-map-ui/src/build_fixture.py` | deterministic fixture builder |
| `product/query_map/server.py` (or merge routes into `product/server.py`) | `frontier/frontier-query-map-ui/src/serve.py` | route table (see §3) |
| `product/static/query_map.html` | `frontier/frontier-query-map-ui/ui/query_map.html` | single-page map UI |
| `product/static/query_map.css` | `frontier/frontier-query-map-ui/ui/query_map.css` | styles |
| `product/static/query_map_model.js` | `frontier/frontier-query-map-ui/ui/query_map_model.js` | pure model (no DOM) |
| `product/static/query_map.js` | `frontier/frontier-query-map-ui/ui/query_map.js` | controller / DOM wiring |
| `product/static/canvas2d_renderer.js` | `frontier/frontier-query-map-ui/ui/canvas2d_renderer.js` | Canvas2D fallback renderer |
| `tests/product/test_query_map_ui.py` | `tests/frontier/frontier-query-map-ui/*` | frozen smoke tests |

Do **not** absorb: `frontier/frontier-query-map-ui/fixtures/*.json` (test data only —
keep under tests/fixtures, or regenerate with `build_fixture.py`).

## 2. Required product-side defect fix (blocking, product lane owns `product/`)

`product/query/answer.py::counter_authority_pass()` references
`_status_counts(...)` but never defines it.

```
NameError: name '_status_counts' is not defined
```

Blast radius: `product.query.pipeline.run_query()` and therefore
`/api/query/run`, `/api/query/answer`, `/api/query/map` and
`product/static/query.html` all 500 before any bundle can be produced.

Fix on `main` by adding the three-line helper to `product/query/answer.py`
(the exact implementation is vendored in `product_compat.py::_status_counts`;
it counts hits by `candidate_status`/`counter_status` and returns a sorted dict).
After product applies the fix, `product_compat.install()` reports
`already_defined_by_product: true` and becomes a no-op — no code change needed
in this team's files. Tests assert the shim remains behaviour-preserving either way.

## 3. HTTP route contract (`serve.py`)

| Route | Serves | Notes |
|---|---|---|
| `GET /` | `ui/query_map.html` | the prototype page |
| `GET /ui/<file>` | `ui/*` (read-only) | team UI assets |
| `GET /vendor/<file>` | `product/static/<file>` (read-only) | **reuse** of accepted renderer/adapter; no copies made |
| `GET /data/visualization.json` | adapted visualization payload | map geometry |
| `GET /data/bundle.json` | raw `query_result_bundle` | answer + provenance |
| `GET /data/manifest.json` | fixture manifest | checksums, provenance |
| `GET /api/health` | liveness + payload sizes + vendor presence | |
| `GET /api/fixture` | raw bundle (alias) | |
| `POST/GET /api/query/run?q=&n=` | live pipeline via shimmed `product.query.pipeline.run_query` | offline fixture corpus |

Product should mount `/vendor/` semantics however it likes; the important seam
is that the UI only ever consumes `query_result_bundle` (§4), never a global
representation.

## 4. `query_result_bundle` seam (canonical, already validated)

`product/query/bundle.py::validate_bundle` is the single validator. The UI never
sees anything outside this schema. Required top-level keys:
`bundle_version, query, query_variants, answer, decisions, clusters, relations, provenance`.
Required per-decision keys:
`decision_id, court, language, rank, score, provenance, snippet, cluster_id, x, y,
counter_status, canonical_url, citation`
(+ optional `is_outlier, counter_evidence, counter_markers, decision_date, docket_number`).

`src/query_bundle_adapter.py::adapt_bundle_to_visualization(bundle)` is the only
translation step (bundle → payload with `decisions/clusters/relations/answer/
provenance/bounds/summary/n_*`). It reuses `validate_bundle` and `bundle_summary`
from the product package rather than re-implementing them.

## 5. Front-end reuse contract (charter acceptance item 7)

The UI **loads accepted product assets at runtime** instead of copying them:

* `/vendor/bundle_adapter.js` → `adaptBundleForWebGL`, `getRelationsForDecision`
  (product/static, already accepted)
* `/vendor/webgl_renderer.js` → `WebGLRenderer` (product/static, already accepted)

`ui/canvas2d_renderer.js` implements the *same* surface
(`uploadPointData/uploadHullData/uploadEdgeData/render/hitTest/destroy`) and is
used only when a WebGL2 context is unavailable (headless CI, GPU-less hosts).
This is the fallback path the charter's `stop_promote_rule` explicitly endorses
("switch to a simpler 2D/Canvas path"), not a parallel renderer rewrite: all
scene assembly, colouring, hulls, relation indexing and filtering still come
from the accepted product adapter.

## 6. Front-end API contract (stable; tests bind to this)

Global `window.QueryMap` (also `module.exports` in node):

| Member | Type | Semantics |
|---|---|---|
| `ready` | `Promise<void>` | resolves after bundle + visualization are loaded |
| `state` | object | `{loaded, renderer, nDecisions, nClusters, nOutliers, nCounter, selectedId, counterFilter, searchTerm, visibleCount, edgeCount}`; `renderer` is `"webgl"` or `"canvas2d"` |
| `select(id)` | `bool` | select decision, open detail panel, draw its relation edges |
| `deselect()` | `void` | clear selection + edges |
| `setCounterFilter(f)` | `int` | `all\|counter\|cited\|outlier\|normal`; returns newly visible count |
| `search(term)` | `int` | case-insensitive substring over id/citation/court/docket/snippet/cluster label; returns visible count |
| `fit()` / `reset()` | `void` | fit to data bounds / restore default view |
| `clickAt(cx, cy)` | `string\|null` | hit-test client coords → selects and returns `decision_id` |
| `detailOf(id)` | `object\|null` | `{decision_id, court, decision_date, docket_number, language, rank, score, cluster_id, cluster_label, counter_status, counter_label, is_outlier, snippet, citation[], canonical_url, counter_evidence}` |
| `relationsOf(id)` | `array` | `[{target_id, kind, shared[], direction}]` — on selection only, never global spaghetti |
| `clusterLegend()` | `array` | `[{cluster_id, label, size, color, outlier_count, counter_count, cited_count}]` |
| `visibleDecisionIds()` | `string[]` | post-filter visibility |

Required DOM ids (stable selectors, used by the automated browser smoke test):
`map-canvas`, `renderer-badge`, `search-input`, `btn-fit`, `btn-reset`,
`btn-clear-selection`, `counter-filter`, `cluster-legend`, `status-bar`,
`result-count`, `detail-panel`, `detail-link`, `relation-list`, `answer-panel`,
`error-banner`.

`detail-link` is a real `<a href="{canonical_url}" target="_blank" rel="noopener">`
so every point is one click from its source (acceptance item 2).

## 7. Automated verification shipped with this contract

`tests/frontier/frontier-query-map-ui/` (stdlib `unittest`, plus `node` for the
browser-equivalent harness — node is present on the runner, no npm installs):

* **data smoke** — fixture validates against `product/query/bundle.py`, 100+
  decisions, 8 labelled clusters, outliers preserved, counter statuses present,
  no global-174k fields anywhere in the payload.
* **server smoke** — real HTTP round-trips: `/`, `/ui/*`, `/vendor/*` (proves
  product static is served, not copied), `/data/*`, `/api/health`, 404 shape.
* **browser smoke** — node VM harness boots `query_map.html`'s scripts against
  a stub DOM/canvas and the real fixture: bundle load → point click → detail
  panel + source link populated → counter filter changes visibility → search
  narrows → selection draws relation edges → fit/reset work → Canvas2D
  fallback activates when WebGL2 is absent.

## 8. Out of scope / explicitly not absorbed

* Global 174k id→cluster alignment, fractal hierarchy, dense 174k embeddings —
  not read, not required, no code path references them.
* Branding / visual redesign — the UI reuses the accepted colour palette and
  interaction patterns from `product/static/index.html`.
* Retrieval and answer generation — consumed as the bundle seam only.
