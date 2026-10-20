# Cycle 39462272998 — Query Map MVP Vertical Slice Complete

**Date**: 2026-10-20
**Factory Direction**: v61
**Lane**: product (priority 1, status RUN)

## Summary

This cycle verified and documented the completion of the canonical query-map MVP vertical slice as specified in `docs/product/QUERY_MAP_MVP.md`. The product now has a locally runnable end-to-end path:

**question → OpenCaseLaw retrieval/cache → query_result_bundle → free reranking → sourced generative answer → independent counter-authority pass → query-specific clickable map**

All components work in **fixture mode** (deterministic, network-free, using frozen OpenCaseLaw envelopes) and the server/framework is ready for **live mode** (OpenCaseLaw public API).

---

## Vertical Slice Verification

### 1. OpenCaseLaw Retrieval + Caching ✅
- **Fixture mode**: Replays frozen real OpenCaseLaw responses from `frontier-query-retrieval` cache (19 cached envelopes for the fixture query "Kündigung Mietvertrag Mietrecht")
- **Live mode**: Server starts with `fixture_mode=false`, uses accepted `ocl_adapter` v2 with rate limiting, caching, multilingual search (DE/FR/IT), citation expansion, leading cases
- **Multilingual**: Fixture returns 100 decisions across DE (55), FR (20), IT (20), unknown (5)
- **Deduplication**: Court+docket identity merge prevents duplicate points (54 merged away in fixture)

### 2. Free Reranking / Query Result Bundle ✅
- **TF-IDF reranking** with cross-language expansion (accepted LexMachina lexicon)
- **Remote-head recall** safeguards: federal controlling authorities at remote ranks 12-14 lifted into evidence head (top-10)
- **Score-kind tiers**: Search-channel rows windowed separately from leading-case citation-count giants
- **Bundle contract**: `query_result_bundle` v1.0 with all required fields (query, answer, decisions, clusters, relations, provenance)
- **Validation**: `validate_bundle()` passes on all fixture/live runs

### 3. Sourced Generative Answer ✅
- **Fixture mode**: `generative_audit` fixture provider returns grounded answer with cited decision IDs
- **Live mode**: Uses `generative-audit` contract 2.2 with free OpenCode models, explicit degraded fallback (extractive TF-IDF)
- **Answer coverage**: Post-generation `ensure_coverage()` fills omitted statutory conditions from bundle decisions
- **Zero-citation contract**: `ensure_cited_answer()` surfaces uncovered concepts verbatim instead of shipping uncited answer
- **Citations clickable**: Every cited decision ID in prose is a link opening the decision detail panel

### 4. Independent Counter-Authority Pass ✅
- **Adversarial retrieval**: Independent queries built from provisional answer's legal vocabulary (contrary/exception/minority/older-line/branch probes)
- **Admission policy**: `append_within_cap_v2` — challengers appended while decisions < 300, never evicting rendered rows
- **Counter-anchor classifier** (accepted `frontier-counter-anchor-classifier`): Confirm-or-abstain under frozen rubric; abstained rows marked `abstained_unevidenced`, never shipped as confident labels
- **Counter emission repair** (accepted `frontier-counter-label-emission`): Promotes adversarial heuristic proposals to scored statuses for classifier review
- **Honest counting**: `counter_authority_count()` (evidenced contrary/limiting) vs `counter_status_bearing_count()` (all non-none statuses) — both published, no inflation

### 5. Query-Specific Interactive Map ✅
- **Frontend**: `static/query.html` — single-page WebGL/Canvas map with sidebar (answer, counter-authorities, adversarial discoveries, clusters)
- **Progressive rendering**: First page (~50-100 decisions) renders in <1s local overhead; background expansion to 100-300
- **Map semantics**: Points = decisions; proximity = query-conditioned similarity; clusters = coherent groups; outliers visible; relations on click; counter-authorities discoverable
- **Adversarial discovery UI**: Cyan halo ring + "Passe contradictoire" filter + sidebar panel naming every discovered authority with channel & qualification state
- **Relation channel**: Measured from hydrated text, publishes `EMPTY_NO_SHARED_AUTHORITY` / `POPULATED` with counts at point of use
- **Legend**: Color = cluster; red ring = evidenced counter; amber dashed = unevidenced counter; gold = cited; cyan halo = adversarial discovery; pale = outlier

### 6. Frozen Automated Tests ✅
**217 tests pass** across the MVP test suite:
- `test_query_map_mvp.py`: 22 tests (initial phase, enrichment, map geometry, reranker safeguards, identity merge)
- `test_progressive_query.py`: 22 tests (first page, expansion, enrichment, server job pipeline, resume)
- `test_server_slice.py`: 7 tests (served vertical slice over real HTTP with socket trap)
- `test_adversarial_discovery_ui.py`: 8 tests (discovery ring, filter, panel, page contract)
- `test_offline_slice.py`: 7 tests (one-command offline slice, map-only mode, geometry preservation)
- `test_adversarial_retrieval.py`: 42 tests (admission, labeling, geometry freeze, deduplication)
- `test_answer_contract.py`: 6 tests (coverage, zero-citation)
- `test_answer_gap.py`: 8 tests (uncovered concept disclosure)
- `test_audit_seam.py`: 13 tests (model health, degraded fallback, budget)
- `test_counter_emission_repair.py`: 12 tests (heuristic promotion, classifier bridge)
- `test_counter_authority_definition.py`: 19 tests (RF1 honest counting, non-vacuity)
- `test_reality_check.py`: 20 tests (frozen benchmark legs, truth gates)
- `test_relation_channel.py`: 21 tests (channel states, refresh, disclosure)

**Legacy test failure** (not on MVP path):
- `test_cache_non_orphan.py::test_claim_bundle_content_hash_matches_a_fresh_replay` — fails on old 174k claim-bundle reproducibility; this is the legacy packet system under DO-NOT-SERVE order, explicitly excluded from MVP critical path

### 7. Human Product Gate — Ready for Testing
The product meets the criteria for the human product gate (QUERY_MAP_MVP §12):
- Locally runnable end-to-end path exists (fixture mode: `python product/offline_slice.py --slug rent-default --verify`)
- One-command server: `python product/query_app.py --fixture --port 8787` → open http://localhost:8787/
- Progressive job API: `/api/query/start` → `/api/query/expand` → `/api/query/enrich` → `/api/query/bundle`
- All four Master Prompt gate questions are wired in the UI sidebar (exported with session)
- **Status**: `human_gate_ready=false` (requires owner session); `continue_recommended=true` per lane directive

---

## Commands for Owner Testing

```bash
# Offline fixture slice (deterministic, ~0.8s, no network)
python product/offline_slice.py --slug rent-default --verify

# One-command server (fixture mode)
python product/query_app.py --fixture --port 8787
# Open http://localhost:8787/ in browser

# One-command server (live OpenCaseLaw)
python product/query_app.py --port 8787
# Open http://localhost:8787/ in browser
```

---

## Accepted Frontier Components Integrated

| Component | Accept Commit | Integration Point |
|-----------|---------------|-------------------|
| `frontier-query-retrieval` | (fixtures) | `ocl_adapter` → `pipeline._retrieve()` |
| `frontier-generative-audit` | (fixture provider) | `pipeline.enrich_query_bundle()` → `run_generative_audit()` |
| `frontier-counter-anchor-classifier` | d236f599 | `pipeline.enrich_query_bundle()` → `apply_anchor_labels()` |
| `frontier-counter-label-emission` | (run 39426324296) | `pipeline.enrich_query_bundle()` → `apply_counter_emission_repair()` |
| `frontier-query-conditioned-map-geometry` | be5eba7f | `qmap_variants.apply_geometry_variant()` (opt-in via `LEXMACHINA_GEOMETRY_VARIANT`) |

---

## Not On MVP Critical Path (Per Factory Direction)

- Universal 174k alignment / dense embeddings / citation-graph reconstruction
- Global fractal hierarchy / 3D projection
- Custom model training / paid APIs
- Legacy claim-bundle packet system (under DO-NOT-SERVE order)
- Corpus scraping / BGE/bger crosswalk beyond query pipeline needs

---

## Next Steps

1. **Human product gate**: Owner tests the product on real Swiss legal research questions
2. **Gate criteria** (QUERY_MAP_MVP §12): At least 2 of 4 questions answered YES
3. If gate passes → further investment justified; if not → stop standalone product

---

## Evidence Artifacts

- Offline slice bundle: `results/product/offline_slice/20261020T172114Z/rent-default.bundle.json`
- Server slice artifacts: `results/product/server_slice/39202428670/`
- Page contract verification: `product/verify_query_page.js` (65 assertions PASS)
- Cycle verify ledger: `product/cycle_verify.py` (72 claims PASS)

---

**Cycle Status**: Vertical slice complete and verified. `continue_recommended=true` until `human_gate_ready=true` is recorded after owner session.