# Fractal Map Lane — Deliverable Confirmed (Factory Direction v35)

**Date:** 2026-10-08  
**Lane:** fractal-map  
**Direction Version:** 35  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Executive Summary

The fractal-map lane deliverable for factory direction v35 is **COMPLETE, VERIFIED, and AUDIT-READY**. All discriminating experiments for the current question have been executed, validated across 10+ independent verification runs, and evidence is preserved.

**Lane Question:** "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**Answer:** ✅ **COMPLETE**

---

## Deliverables Finalized

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 173,963 Decisions

| Mode | Scale | Fine Branch Purity | Verdict |
|------|-------|-------------------|---------|
| `cited_decisions_tfidf` | 173,963 (full) | 0.906 | PASS |
| `cited_outcome_hybrid_0.5` | 173,963 (full) | 0.921 | PASS |
| `cited_outcome_hybrid_0.7` | 173,963 (full) | 0.930 | PASS |
| `regeste_tfidf` | 52% (91k) | 0.609 | PASS |
| `regeste_full_text_hybrid_0.5` | 52% (91k) | 0.633 | PASS |
| `regeste_full_text_hybrid_0.7` | 52% (91k) | 0.685 | PASS |

**All 6 modes PASS hierarchical_v1 protocol** (7 checks: fragmentation, nesting, branch/area purity improvement, zoom coherence, legal structure thresholds).

### 2. Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED at 174k

- **4 resolution levels** with perfect nesting ≥ 0.95
- **Zero fragmentation** (singleton_fraction = 0.0 at all levels)
- **Monotonic refinement** (each level reveals more specific legal structure)
- **Calibration FAILS** on TF-IDF (thresholds too aggressive for signal density) — **valid negative result**

### 3. Dense Embedding Integration Contract v34 — FROZEN

Four complementary views defined with specific acceptance criteria:

| View | Acceptance Criterion | Status |
|------|---------------------|--------|
| Citation Heritage | AUC > 0.75 | PASSED at 144k (0.79-0.85) |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.20 | PASSED at 144k (0.28) |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.10 | PASSED at 144k (0.15) |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch > 0.10 | FAILED (0.09) — excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | PASSED (JP 0.61-0.67) |

**Infrastructure readiness:** Hierarchical builder VALIDATED (12k dense: 4 levels, nesting=1.0, zero fragmentation, 39→412 clusters), map mode registry READY, WebGL pipeline VALIDATED (<3s at 174k TF-IDF).

### 4. Scale Extrapolation Validated

144k checkpoint (22/26 years, 2000-2021) validates extrapolation model:
- Fine branch purity: ~0.97
- Improvement rate: 0.48-0.65 (branch) / 0.75-0.76 (area)
- Strict nesting: ≥0.99
- Fine singletons: ~4-5%

### 5. NESTING_METRIC_DEFECT_v1 — ENFORCED

Strict nesting definition enforced: fine label's parent must match coarse label for that decision. Previous lenient "any parent has child" definition inflated scores.

---

## Test Verification Summary

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify | 186 | 185 | 1 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 | 0 |
| test_scale_dependency | 11 | 11 | 0 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** | **0** |

**Verified in 10+ independent GitHub runs** (37707252501 through 37756858623).

---

## Blocker Status

**Lane correctly BLOCKED_ON_DEPENDENCIES** on upstream legal-distance 174k dense embeddings, which requires corpus lane resumption:

1. **BGE/bger ID mapping production** — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs, no mapping exists
2. **Parquet generation for years 2022-2026** — 29,520 decisions missing from pinned 2026 snapshot
3. **Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale** — required for cross-lingual evaluation density

**No further same-question cycles justified** — `continue_recommended=false`.

---

## Evidence Preservation

All claim-bearing outputs preserved in:
- `results/fractal_map/hierarchical_v1_174k_tfidf/` — Hierarchical_v1 protocol results
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — 4-level recursive protocol results
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — Calibration results (negative)
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — Metric defect enforcement
- `results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json` — Extrapolation model
- `results/fractal_map/final_pipeline_validation/` — Pipeline validation
- `results/fractal_map/product_integration/INTEGRATION_SPEC.md` — Product integration spec
- `state/fractal-map.json` — Machine-readable lane state

---

## Recommendation

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping, 2022-2026 parquet generation, and section extraction at 174k scale. Once legal-distance delivers 174k dense embeddings passing the four complementary view acceptance criteria, integrate dense embedding views per contract v34.

**Lane deliverable VERIFIED AND AUDIT-READY.**