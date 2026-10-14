# Integration contract — `frontier-human-gate-harness` v1 → product

**Product owns final integration. This team owns no product file.**
No file under `product/` is written, patched or owned by this team. Everything below is a
copy/attach instruction for the product lane; evaluation owns the gate judgement.

Charter: `frontier-human-gate-harness` charter v1 · producer run `38600279890` · resume run `38611364746` · acceptance test (7).

---

## 1. What product must copy

| # | Source (this team, read-only for product) | Target (product's choice, product's repo path) | Why |
|---|---|---|---|
| 1 | `frontier/frontier-human-gate-harness/static/lex_gate_switch.js`<br>sha256 `38d4b20fd08b68ac1fc76753fd080a3f67dfbdf908641134bbd7857ac2e3aaa3` | `product/static/lex_gate_switch.js` **or** inlined into the `<script>` block of `product/static/query.html` | the list↔map switch + capture draft (acceptance 2/4) |
| 2 | `frontier/frontier-human-gate-harness/static/lex_gate_switch.css`<br>sha256 `1a8cf48683ae80c673f00ba4747ff4312f4ad8b6faeef8fcfb8dd79ba6ff3a21` | `product/static/lex_gate_switch.css` **or** inlined into `<style>` in `query.html` | baseline-row + toggle styling |
| 3 | *(optional, server-side baseline)* `frontier/frontier-human-gate-harness/frontier_human_gate_harness/baseline_view.py` → `render_rows_html(bundle)` / `build_model(bundle)`<br>sha256 `70e2d7cb9968521cf3b28a1adfee1bea158c07169469d3e7ce349a560edf5d1c` | product may call it from its own server path, or skip it and let `attach()` render the list client-side | byte-identical rows either way (test `test_python_and_javascript_renderers_are_byte_identical`, `test_coercion_parity_with_python`) |

`query.html` currently ships only `index.html` + `query.html` (all JS inline), so the inline
option is legitimate: paste the file verbatim, keep the `LexGateSwitch` UMD-style global.

## 2. Exact hooks in `product/static/query.html`

Verified against `lab/product` HEAD file (`query.html`, ids/functions as they exist today):

| Hook | Product code today | Integration change |
|---|---|---|
| toolbar host | `<div id="toolbar">` (line ~47) | none — `attach` **inserts** `#lexViewToggle` as its first child |
| map element | `<div id="mapWrap">` inside `<main>` | none — pass as `mapEl` |
| list element | *(absent)* | add `<div id="lexListView" hidden></div>` as a sibling of `#mapWrap` inside `<main>` |
| already-loaded bundle | `let BUNDLE=null` + `function renderBundle(b){ BUNDLE=b; …draw(); }` | none — read it, never fetch it |
| bundle changed | `renderBundle(b)` (~114), reset `BUNDLE=null` (~164) | append `LexGateSwitch.notifyBundleChanged();` after each |
| escaping rule | product `esc()` = `[&<>"']` → `&amp; &lt; &gt; &quot; &#39;` | none — identical to the harness `esc()` (parity-tested) |

Boot snippet (product adapts names, not semantics):

```html
<script src="lex_gate_switch.js"></script>   <!-- or the inlined file -->
<link rel="stylesheet" href="lex_gate_switch.css">
<div id="lexListView" hidden></div>          <!-- next to #mapWrap -->
<script>
  var controller = LexGateSwitch.attach({
    getBundle: function () { return BUNDLE; },              // the SAME object the map draws
    mapEl:     document.getElementById("mapWrap"),
    listEl:    document.getElementById("lexListView"),
    toolbarEl: document.getElementById("toolbar"),
    statusEl:  document.getElementById("status"),
    session_id: null,                                       // owner types it on the card
    mountExportButton: true
  });
</script>
```

and, inside `renderBundle()` and the `BUNDLE=null` reset:

```js
  LexGateSwitch.notifyBundleChanged();   // re-renders the list from the new bundle, no fetch
```

## 3. Contract the caller must honour

1. **`getBundle()` returns the bundle already in memory** (`BUNDLE`). The switch contains no
   network capability (no fetch/XHR/beacon/event-stream token — greppable, asserted by
   `tests/.../js/verify_switch.js` assertions 36–42). If product ever points `getBundle` at a
   URL-producing function, the A/B comparison silently becomes two different queries.
2. **No mutation**: the switch deep-reads and copies before sorting. Product must not re-order
   `BUNDLE.decisions` for the list; `rank` order is authoritative.
3. **Required bundle fields** for the conventional list — `rank, court, decision_date,
   language, citation, canonical_url` plus `decision_id, snippet` (same set the product
   validator already enforces). A missing field is a **product contract defect**: the harness
   terminates and prints the exact field name (exit 3) instead of inventing data.
4. **`notifyBundleChanged()` on every new bundle**, otherwise the list shows the previous
   query — the failure mode this contract exists to prevent.
5. **Capture flow**: `controller.exportDraft({session_id})` → 23-key draft JSON (schema in
   `frontier/.../capture.py::RECORD_KEYS`; `query_sha256` stays `null` in client drafts and
   is derived from the record's own query string at `finalize` time, mirroring
   `bundle_sha256`); finalise offline with

   ```bash
   python -m frontier_human_gate_harness.cli --finalize <draft.json> \
       --fixture <the bundle json> --out results/frontier/frontier-human-gate-harness
   ```

   A missing answer exits 2 (`MissingAnswerError`); `--allow-incomplete` writes an explicitly
   `status:"incomplete"` record with `missing_answers` spelled out. Nothing is ever defaulted.

## 4. What product gets and what it must check

- `controller.viewMode`, `controller.actions` (`{at, view_mode, event, ref}`),
  `controller.decisions_opened` / `counter_authorities_opened`,
  `controller.bundleRef()` → `{query, n_decisions}`, `controller.exportDraft(meta)`.
- `window.__LEX_GATE_SWITCH__ = {controller, config}` for console inspection.
- Existing product detail hooks stay product's: pass `openDetail: function (decisionId) { … }`
  to `attach` if product wants the list rows to open `#detail` the way the map does.

## 5. Out of scope for this team (explicitly)

Retrieval, generation, reranking, benchmark changes, any edit to `product/**`, any ownership of
the final integration decision, and any counter-authority classification (all fixture
`counter_status` stay `unclassified`; classification belongs to product/evaluation evidence).

## 6. Acceptance mapping

| Acceptance | Evidence |
|---|---|
| (1) baseline component | `frontier/.../baseline_view.py`, test `test_baseline_view.*` |
| (2) same-bundle switch, no mutation | `static/lex_gate_switch.js`, tests `test_switch.*` + node assertions 19–23 |
| (3) FR/DE card + frozen-leg question | `frontier/.../owner_card.py`, tests `test_owner_card.*` |
| (4) session capture record | `frontier/.../capture.py`, tests `test_capture.*` |
| (5) one-command offline path | `python -m frontier_human_gate_harness.cli …`, `smoke.sh` step 4 |
| (6) ≥8 deterministic offline tests | 45 tests: `python tests/frontier/frontier-human-gate-harness/run_tests.py` |
| (7) this contract | `INTEGRATION_CONTRACT.md` + `INTEGRATION_CONTRACT.json` |
| (8) zero writes outside the five paths | `smoke.sh` step 6 + `results/.../evidence/scope_violations.txt` |
