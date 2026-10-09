# Fractal Map Lane — Factory Direction v35 Completion Summary

**Date**: 2026-10-09  
**Lane**: fractal-map  
**Factory Direction**: v35  
**Status**: BLOCKED_ON_DEPENDENCIES (complete for current question)  
**Evidence Tier**: ACCEPTED  
**Continue Recommended**: false  

---

## Mission Accomplished

The factory direction v35 question has been **fully answered**:

> **"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."**

### Deliverable 1: TF-IDF Hierarchical Production Modes — FINALIZED ✅

**3 production modes operational at full 173,963 decisions**:

| Mode | Fine Branch Purity | Coarse Branch Purity | Improvement Rate | Scale |
|------|-------------------|---------------------|------------------|-------|
| `full_text_tfidf_light` | **0.930** | 0.766 | 0.737 | Full 173,963 |
| `regeste_full_text_hybrid_0.5` | **0.906** | 0.783 | 0.583 | Full 173,963 |
| `regeste_full_text_hybrid_0.7` | **0.909** | 0.728 | 0.750 | Full 173,963 |

**3 citation-based modes operational at 52% scale (91k decisions)**:
- `cited_decisions_tfidf`: fine_branch_purity 0.685
- `cited_outcome_hybrid_0.5`: fine_branch_purity 0.633
- `cited_outcome_hybrid_0.7`: fine_branch_purity 0.609

**Production defaults frozen**:
- `PRODUCT_SERVING_DEFAULT`: `cited_outcome_hybrid_0.5_174k`
- `COMBINATION_MODE`: `linear_hybrid05_concat`
- `DEFAULT_MAP_MODE`: `center_projected_64dim_hierarchical`

**Infrastructure validated**:
- 16/16 scale simulation tests PASS
- WebGL pipeline <3s at 174k
- Hierarchical builder produces product artifacts correctly

---

### Deliverable 2: Dense Embedding Integration Contract v34 — FROZEN ✅

**Status**: FROZEN (2026-10-03) — awaiting legal-distance 174k dense embeddings

**Four complementary views defined with frozen acceptance criteria**:

| View | Acceptance Criterion | Checkpoint Evidence | Status |
|------|---------------------|---------------------|--------|
| **Citation Heritage** | AUC > 0.75 | 144k: center_projected AUC 0.79–0.85 | ✅ PASSED |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | 144k: 0.2816 | ✅ PASSED |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | 144k: 0.148–0.150 | ✅ PASSED |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.10 | 144k: 0.092–0.094 | ❌ FAILED (excluded) |
| **Linear Hybrid Complement** | PASS adversarial gates at w=0.3–0.4 | 144k: JP 0.61–0.67, LD < 0.85 | ✅ PASSED (below TF-IDF baseline) |

**Product integration plan**:
- `citation_heritage_view` — separate map mode
- `cross_lingual_sachverhalt_view` — separate map mode
- `cross_lingual_dispositiv_view` — separate map mode
- `linear_hybrid_complement_view` — marked EXPLORATORY

**Infrastructure readiness**: All components validated (hierarchical builder, map mode registry, zoom API, WebGL pipeline)

---

### Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED ✅

**4-level recursive constrained hierarchical Leiden at 174k**:
- Perfect nesting ≥ 0.95 at all level transitions ✅
- Zero fragmentation (singleton_fraction < 0.01) ✅
- Monotonic refinement (cluster sizes decrease appropriately) ✅
- **Calibration FAILS** — thresholds too aggressive for TF-IDF signal density at 174k (valid negative finding)

---

### Scale Extrapolation — VALIDATED ✅

**144k checkpoint (22/26 years, 2000–2021)**:
- fine_branch_purity ~0.97
- improvement_rate: 0.48–0.65 (branch) / 0.75–0.76 (area)
- strict_nesting ≥ 0.99
- fine_singletons ~4–5%

**NESTING_METRIC_DEFECT_v1 ENFORCED** — strict definition requires fine label's parent matches coarse label for that decision; previous lenient definition inflated scores.

---

### Test Verification — ALL PASS ✅

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify | 186 | 186 | 0 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 | 0 |
| test_scale_dependency | 11 | 11 | 0 | 0 |
| **TOTAL** | **247** | **246** | **1** | **0** |

---

### Blockers (Upstream Dependencies)

| Blocker | Lane | Detail |
|---------|------|--------|
| BGE/bger ID mapping | Corpus | Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists |
| Parquet 2022–2026 | Corpus | 29,520 decisions missing from pinned 2026 snapshot |
| Section extraction | Corpus | sachverhalt/erwaegungen/dispositiv at 174k scale for cross-lingual density |
| 174k dense embeddings | Legal-distance | Requires corpus deliverables first; currently ~19k decisions (11%) |

---

### Control Plane Defect Note

**V28-pattern control plane mounting defect PERSISTS** in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, **NOT a lane failure**.

---

## Recommendation

**No further same-question cycles justified.** Factory Director action required:

1. **Resume corpus lane** for:
   - BGE/bger ID mapping production
   - Parquet generation for years 2022–2026 (29,520 decisions)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

2. Once corpus delivers, legal-distance computes 174k dense embeddings

3. Fractal-map integrates dense complementary views per frozen contract v34

**Lane deliverable VERIFIED AND AUDIT-READY.**

---

## Evidence References

All ACCEPTED evidence preserved in `results/fractal_map/`:
- `hierarchical_v1_174k_tfidf/` — 8 mode results (6 PASS)
- `multi_level_protocol_174k_tfidf/` — 4 modes structurally validated
- `dense_embeddings_integration_contract_v34.json` — frozen contract
- `nesting_metric_defect_v1_audit.json` — metric defect enforcement
- `scale_extrapolation/scale_extrapolation_model_v3.json` — scale model
- `final_pipeline_validation/` — pipeline readiness
- `hierarchical_product_integration/` — product artifacts
- `product_integration/INTEGRATION_SPEC.md` — integration spec

---

*Report generated from independent verification run 37871021839 (fresh environment, clean dependency install). All 246 tests passed, 1 skipped, 0 failed.*