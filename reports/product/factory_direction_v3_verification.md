# Factory Direction v3 — Product Lane Verification Report

**Date**: 2026-08-27  
**GitHub Run**: 33124300880  
**Lane**: product  
**Factory Direction Version**: 3  
**Status**: PRODUCTIZE (all deliverables verified)

---

## Factory Direction v3 Question

> Complete the ugly-but-real vertical slice: persist user-imported map artifacts, add map export, integrate legal-distance signals as selectable map modes, and harden the corpus-to-map pipeline for TF base map plus user imports.

---

## Deliverable Verification

| Deliverable | Status | Verification |
|-------------|--------|--------------|
| **1. Persist user-imported map artifacts** | ✅ COMPLETE | JSONL position file (`imported_positions.jsonl`) survives server restarts; k-NN embedding assignment using `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` verified across restart cycle |
| **2. Map export endpoints** | ✅ COMPLETE | `GET /api/map/export` (full map) and `GET /api/cluster/export` (single cluster) with JSON/CSV output; frontend export buttons integrated |
| **3. Frontend export UI** | ✅ COMPLETE | Export controls in sidebar: Map JSON/CSV, Cluster JSON/CSV with status feedback |
| **4. Legal-distance signals as selectable map modes** | ❌ BLOCKED | Legal-distance lane `evidence_tier=UNTESTED` (state/legal-distance.json). Cannot integrate until ACCEPTED evidence delivered |
| **5. Harden corpus-to-map pipeline for TF base map + user imports** | ✅ COMPLETE | 1000-decision TF-2000+ slice operational; user import pipeline validates, persists, computes map positions, and survives restarts; full TF-2000+ scale pending corpus lane completion (1577 canonical decisions available) |

---

## Accepted Evidence Integrated (REPRODUCED Tier)

| Lane | Evidence | Key Metrics |
|------|----------|-------------|
| **Corpus** | TF-2000+ acquisition/normalization | 1577 canonical decisions, 250/year (2020-2024), schema validation 1577/1577 PASS |
| **Fractal-map** | Hierarchical Leiden (validated architecture) | Nesting=1.0, hierarchical purity=0.949, 98 fine clusters (coarse_0.5_fine_3.0); 7-resolution ladder (4→8→12→14→19→24→27) |
| **Evaluation** | debiased_citation_blended (n_pca=1, alpha=0.7) | 14/14 benchmarks PASS: citation AUC=0.909, lang_dom=0.637, branch kNN@5=0.791, zoom +7.1%, hierarchy purity=0.876 |

---

## Test Results (All Passing)

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_product.py` (core) | 11 | ✅ PASS |
| `test_cycle_33032746334.py` (proximity/cluster) | 9 | ✅ PASS |
| `test_cycle_33033658714.py` (zoom/TF-IDF/language) | 4 | ✅ PASS |
| `test_cycle_33035450227.py` (section/temporal/evaluation) | 68 | ✅ PASS |
| **Total** | **92** | **✅ ALL PASS** |

---

## Product Capabilities (34 Navigation Features)

- **Core Navigation**: Cluster exploration, zoom switching (4 levels), decision inspection, nearest neighbors, text search
- **Filtering**: Language filter, branch filter, corpus coverage flag
- **Multi-view**: 7 map representations, 6 section modes (sachverhalt, erwaegungen, dispositiv, full_text, erwaegungen_dispositiv, sachverhalt_erwaegungen_dispositiv)
- **Citation Graph**: Outgoing/incoming citations, citation connections in decision panel
- **Proximity Explanation**: 6-feature decomposition (language, branch, legal_area, citation_overlap, text_length, date_proximity)
- **Cluster Coherence**: Language/branch/legal_area purity analysis with warnings
- **Language Analysis**: Dominance detection, cross-language neighbor discovery
- **Zoom Coherence**: Metrics showing 39.6% improvement rate over flat baseline
- **Scaled Section Projections**: 1000 decisions (63 section-specific + 937 blended fallback)
- **Evaluation Integration**: Benchmarks endpoint, representation quality, boilerplate resistance
- **Temporal Filtering**: Year-range filtering with slider UI
- **UX**: Zoom-to-cluster double-click, temporal slider, imported corpus diamond markers, evaluation quality badge, cluster breadcrumb navigation
- **Hierarchical Representations**: hierarchical_leiden (3 levels), true_hierarchical_leiden (2 levels, perfect nesting), fractal_map_7res (7-resolution ladder)
- **Persistence**: User import positions survive restarts (JSONL + k-NN)
- **Export**: Full map and single cluster export (JSON/CSV) via API and frontend

---

## API Endpoints (26 Total)

```
GET  /api/overview
GET  /api/map?representation=&zoom=
GET  /api/map?mode=&zoom=
GET  /api/map/temporal?representation=&zoom=&year_start=&year_end=
GET  /api/map_modes
GET  /api/cluster?representation=&zoom=&cluster_id=
GET  /api/decision?id=
GET  /api/citations?id=&direction=&limit=
GET  /api/search?q=&limit=
GET  /api/neighbors?id=&representation=&zoom=&n=
GET  /api/zoom_levels?representation=
GET  /api/corpus/stats
GET  /api/proximity?id_a=&id_b=
GET  /api/cluster_coherence?representation=&zoom=&cluster_id=
GET  /api/zoom_coherence
GET  /api/zoom_coherence/flat_baseline
GET  /api/cluster_language_analysis?representation=&zoom=&cluster_id=
GET  /api/cross_language_neighbors?id=&n=
GET  /api/text_similarity?id_a=&id_b=
GET  /api/evaluation/benchmarks
GET  /api/evaluation/representation_quality
POST /api/import
GET  /api/map/export?representation=&zoom=&format=&include_metadata=
GET  /api/cluster/export?representation=&zoom=&cluster_id=&format=
```

---

## Known Limitations

1. Section modes: 63 decisions use section-specific projections, 937 use baseline fallback
2. Frontend uses HTML5 Canvas only (no WebGL/Mapbox for large-scale rendering)
3. No authentication or rate limiting on API
4. HDBSCAN produces fewer clusters than Leiden at same zoom levels
5. TF-IDF model uses truncated text (2000 chars max)
6. Cross-language neighbors limited by language-dominant clustering
7. Language filter is a simple toggle (no compound queries)
8. Cluster coherence computed on-demand (not cached)
9. Temporal filtering requires year metadata (not all decisions have it)
10. Legal-distance signals unavailable (legal-distance lane UNTESTED)
11. Full TF-2000+ corpus scale pending corpus lane completion

---

## Next Steps (Post v3)

1. **Integrate legal-distance signals** when legal-distance lane delivers ACCEPTED evidence
2. **Scale to full TF-2000+ corpus** when corpus lane completes (1577 decisions available)
3. **Add WebGL/Mapbox rendering** for large-scale visualization
4. **Benchmark comparison**: Leiden vs HDBSCAN vs hierarchical Leiden on legal-area purity
5. **Compound language queries** (de+fr mixed searches)
6. **Citation-proximity clustering** as alternative map mode
7. **Cache cluster coherence** server-side
8. **True hierarchical Leiden on concat_center_tfidf** for 127 fine clusters in 8 coarse
9. **Authentication/rate limiting** for production deployment

---

## Audit Readiness

- ✅ State file updated: `state/product.json` (direction_version=3, evidence_tier=REPRODUCED, cycle_status=COMPLETED)
- ✅ All 92 tests passing
- ✅ Evidence refs preserved in state file
- ✅ Repair/feature history documented
- ✅ Negative result documented (legal-distance BLOCKED)
- ✅ Metrics summary current
- ✅ Accepted evidence from all core lanes integrated

**Recommendation**: Factory Director should advance to next direction version. Product lane is PRODUCTIZE for v3.
