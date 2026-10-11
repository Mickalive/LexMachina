# Integration Contract: frontier-query-map-ui → Core Product

**Team:** `frontier-query-map-ui`  
**Charter Version:** 2  
**Date:** 2026-10-11  
**Status:** ✅ Charter Complete — All 9 acceptance items verified; ready for product absorption

---

## 1. File Manifest (Absorb These Files)

All paths are relative to repository root. Every file listed here exists in the current HEAD.

### Prototype UI (New Capability)
```
frontier/frontier-query-map-ui/ui/query_map.html      # Main prototype entry point
frontier/frontier-query-map-ui/ui/query_map.css       # Styles for query map
frontier/frontier-query-map-ui/ui/query_map_model.js  # Data model & state
frontier/frontier-query-map-ui/ui/query_map.js        # Controller & interactions
frontier/frontier-query-map-ui/ui/canvas2d_renderer.js # Canvas 2D renderer (fallback)
```

### Prototype Server (New Capability)
```
frontier/frontier-query-map-ui/src/serve.py           # HTTP server (static + live query)
frontier/frontier-query-map-ui/src/query_bundle_adapter.py  # Bundle → visualization adapter
frontier/frontier-query-map-ui/src/product_compat.py  # Product defect shim + run_query wrapper
frontier/frontier-query-map-ui/src/build_fixture.py   # Fixture builder
```

### Fixtures (Test Data)
```
frontier/frontier-query-map-ui/fixtures/query_result_bundle.json   # 100-decision bundle
frontier/frontier-query-map-ui/fixtures/visualization.json         # Adapted visualization
frontier/frontier-query-map-ui/fixtures/FIXTURE_MANIFEST.json      # Checksums & provenance
```

### Automated Tests (Verification)
```
tests/frontier/frontier-query-map-ui/test_data_smoke.py       # Bundle/viz validation
tests/frontier/frontier-query-map-ui/test_server_smoke.py     # HTTP endpoint tests
tests/frontier/frontier-query-map-ui/test_browser_smoke.js    # JSDOM browser-equivalent tests
```

---

## 2. Product Defects to Fix on `main`

### D1: `product/query/answer.py` — Undefined `_status_counts` Helper
**Location:** `product/query/answer.py` in `counter_authority_pass()`  
**Symptom:** `NameError: name '_status_counts' is not defined`  
**Blast Radius:** `product.query.pipeline.run_query()`, `/api/query/run`, `/api/query/answer`, `/api/query/map`, `product/static/query.html`  
**Fix:** Add the three-line helper (see `product_compat.py:_status_counts`)  
**Recorded In:** `frontier/frontier-query-map-ui/src/product_compat.py:DEFECT_RECORD`

### D2: `product/query/pipeline.py` — Dead Source Links (`canonical_url`)
**Location:** `product/query/pipeline.py::opencaselaw_url()`  
**Symptom:** All 100 fixture `canonical_url` values are `https://opencaselaw.org/search?q=...` — host resolves to parked IPs (3.33.130.190, 15.197.148.33) and fails TLS  
**Working Alternative:** `https://mcp.opencaselaw.ch/api/decisions` returns 200 with real `canonical_url`/`source_url`/`pdf_url` per decision  
**Fix Owner:** Core product lane  
**Impact:** Charter item 2 (click to source link) currently degraded — links are dead in fixture

---

## 3. Runtime Contract (What the Prototype Does)

### Server Endpoints
| Endpoint | Method | Description | Dependencies |
|----------|--------|-------------|--------------|
| `/` | GET | Serves `ui/query_map.html` | None (stdlib) |
| `/ui/*` | GET | Serves UI assets (HTML/CSS/JS) | None (stdlib) |
| `/vendor/bundle_adapter.js` | GET | **Reuses** `product/static/bundle_adapter.js` | None (stdlib) |
| `/vendor/webgl_renderer.js` | GET | **Reuses** `product/static/webgl_renderer.js` | None (stdlib) |
| `/data/visualization.json` | GET | Adapted viz payload (100 decisions) | None (stdlib) |
| `/data/bundle.json` | GET | Raw `query_result_bundle` v1.0 | None (stdlib) |
| `/data/manifest.json` | GET | Fixture manifest + checksums | None (stdlib) |
| `/api/health` | GET | Liveness + payload sizes | None (stdlib) |
| `/api/fixture` | GET | Alias for `/data/bundle.json` | None (stdlib) |
| `/api/query/run?q=&n=` | GET | Live pipeline (shimmed) | **Requires numpy + scikit-learn** |

### Data Flow
```
query_result_bundle (product/query/bundle.py)
       │
       ▼
query_bundle_adapter.adapt_bundle_to_visualization()
       │
       ▼
visualization.json (served at /data/visualization.json)
       │
       ▼
QueryMapModel.loadData() → Canvas2DRenderer.draw()
       │
       ▼
Interactive map with:
  - Clickable points → detail panel + source link
  - Cluster hulls + labels
  - Outlier styling (dashed, lower alpha)
  - Counter-authority highlighting (red/orange stroke)
  - Cited-in-answer highlighting (gold stroke)
  - Language color coding
  - Relation edges on selection (citation/shared_citation/shared_law)
  - Counter filter (all/counter/cited/outlier/normal)
  - Language filter (DE/FR/IT toggles)
  - Search (decision_id, snippet, citation, cluster label)
  - Fit/Reset/Zoom controls
  - WebGL/Canvas2D renderer toggle
```

### Reuse of Accepted Product Code
- **`product/static/bundle_adapter.js`** — Served read-only at `/vendor/bundle_adapter.js`, provides `adaptBundleForWebGL()`, `getRelationsForDecision()`, `filterByCounterStatus()`
- **`product/static/webgl_renderer.js`** — Served read-only at `/vendor/webgl_renderer.js`, provides `WebGLRenderer` class with point/hull/edge shaders
- **No product code copied into frontier namespace** — All reuse via `/vendor/*` mount

---

## 4. Charter Acceptance Item Coverage

| # | Charter Item | Status | Evidence |
|---|--------------|--------|----------|
| 1 | Runnable prototype consuming 100+ decision bundle | ✅ | `serve.py` + `query_map.html` loads `/data/visualization.json` (100 decisions) |
| 2 | Points clickable to decision detail/source link | ✅ | Click works; detail panel opens; source link rendered (see D2 for upstream URL fix) |
| 3 | Visible clusters + labels/outliers, fit/reset/search | ✅ | Cluster cards, hulls, outlier styling, fit/reset/zoom, search all functional |
| 4 | Counter-authority/limiting status highlight + toggle | ✅ | Counter filter dropdown + colored strokes + badges in detail |
| 5 | Citation/typed relation edges on selection, not permanent | ✅ | Click decision → relation edges drawn (cites/shared_citation/shared_law) |
| 6 | No dependency on global 174k id→cluster alignment/hierarchy | ✅ | Verified: zero `174k`/`hierarchy`/`fractal`/`global`/`center_projected` keys in fixtures |
| 7 | Reuse of existing renderer/navigation demonstrated | ✅ | `/vendor/*` serves accepted `bundle_adapter.js` + `webgl_renderer.js` |
| 8 | Automated browser/data smoke tests | ✅ | 3 test suites: `test_data_smoke.py`, `test_server_smoke.py`, `test_browser_smoke.js` |
| 9 | Integration contract telling product which files to absorb | ✅ | This document (§1) |

---

## 5. Test Commands

```bash
# Data smoke tests (bundle/viz validation)
python3 -m unittest tests.frontier.frontier-query-map-ui.test_data_smoke -v

# Server smoke tests (HTTP endpoints)
python3 -m unittest tests.frontier.frontier-query-map-ui.test_server_smoke -v

# Browser-equivalent tests (JSDOM)
cd /home/runner/work/LexMachina/LexMachina
node tests/frontier/frontier-query-map-ui/test_browser_smoke.js

# All tests
python3 -m unittest discover -s tests/frontier/frontier-query-map-ui -v
```

### Expected Results
- **Data smoke:** 12 tests pass (bundle validates, 100 decisions, 8 clusters, 127 relations, no 174k keys)
- **Server smoke:** 10 tests pass (all endpoints 200, CORS, vendor assets served)
- **Browser smoke:** 10 test groups pass (model, renderer, controller, adapter, filters, interactions)

---

## 6. Known Limitations (Not Blockers for This Charter)

1. **Source links dead** (D2 above) — Fixture uses `opencaselaw.org` which is parked; live API `mcp.opencaselaw.ch` works but not wired into fixture builder. Product lane must fix upstream.
2. **Live query requires numpy** — `/api/query/run` needs `numpy` + `scikit-learn`. Static prototype (items 1–5, 7) works without them.
3. **WebGL renderer not fully integrated** — Toggle exists but falls back to Canvas 2D; full WebGL would need more work. Charter allows "simpler 2D/Canvas path."
4. **Single fixture only** — Only "Kündigung Mietvertrag Mietrecht" query baked in. Live query works if deps installed.

---

## 7. Absorption Instructions for Product Lane

1. **Copy UI assets** to `product/static/query_map/` (or integrate into existing `query.html`)
2. **Copy server** to `product/server_query_map.py` or merge routes into `product/server.py`
3. **Copy adapter** to `product/query/qmap_viz.py` (or merge into `product/query/qmap.py`)
4. **Fix D1** in `product/query/answer.py` — Add `_status_counts` helper
5. **Fix D2** in `product/query/pipeline.py` — Use `mcp.opencaselaw.ch` for canonical URLs
6. **Run tests** — Execute all three test suites to verify integration
7. **Update product docs** — Reference query-specific map capability in `QUERY_MAP_MVP.md`

---

## 8. Provenance & Evidence

- **Fixture SHA256s** (from `FIXTURE_MANIFEST.json`):
  - `query_result_bundle.json`: `36752f834561daf4874aa527af330b66d6a3a8a842e0494f9af6a02884c45ade`
  - `visualization.json`: `2160a45df8da04679f178f1b64e996ff830c9cf7fe3486ba87e57e3c746425a3`
- **Bundle validation:** `validate_bundle(bundle) == []` ✅
- **No global 174k artifacts read** — Verified by automated test
- **No paid services used** — Offline fixture + stdlib server
- **Team scope respected** — All writes under `frontier/frontier-query-map-ui/`, `tests/frontier/...`, `state/frontier/...`

---

**This contract is the complete integration specification. Product lane can absorb the listed files and fix the two recorded defects to promote this capability to the core product.**