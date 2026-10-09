# Fractal Map Lane — Factory Direction v35 Cycle Completion Report

**Date**: 2026-10-09  
**Lane**: fractal-map  
**Factory Direction**: v35  
**GitHub Run**: 37876842198  
**Status**: BLOCKED_ON_DEPENDENCIES (complete for current question)  
**Evidence Tier**: ACCEPTED  
**Continue Recommended**: false  

---

## Question Answered

> **"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."**

**STATUS: COMPLETE ✅**

---

## Deliverable 1: TF-IDF Hierarchical Production Modes — FINALIZED ✅

### 3 Production Modes at Full 173,963 Decisions (Text-Based)

| Mode | Fine Branch Purity | Coarse Clusters | Fine Clusters | Improvement Rate |
|------|-------------------|-----------------|---------------|------------------|
| `full_text_tfidf_light` | **0.930** | 19 | 365 | 0.737 |
| `regeste_full_text_hybrid_0.5` | **0.906** | 39 | 412 | 0.583 |
| `regeste_full_text_hybrid_0.7` | **0.909** | 39 | 412 | 0.750 |

### 3 Citation-Based Modes at 52% Scale (~91k decisions)

| Mode | Fine Branch Purity | Verdict |
|------|-------------------|---------|
| `cited_decisions_tfidf` | 0.685 | PASS |
| `cited_outcome_hybrid_0.5` | 0.633 | PASS |
| `cited_outcome_hybrid_0.7` | 0.609 | PASS |

**Production Defaults Frozen**:
- `PRODUCT_SERVING_DEFAULT`: `cited_outcome_hybrid_0.5_174k`
- `COMBINATION_MODE`: `linear_hybrid05_concat`
- `DEFAULT_MAP_MODE`: `center_projected_64dim_hierarchical`

**Infrastructure**: 16/16 scale tests PASS, WebGL pipeline <3s at 174k.

---

## Deliverable 2: Dense Embedding Integration Contract v34 — FROZEN ✅

**Location**: `results/fractal_map/dense_embeddings_integration_contract_v34.json`

| Complementary View | Acceptance Criterion | Checkpoint Status |
|-------------------|---------------------|-------------------|
| **Citation Heritage** | AUC > 0.75 | ✅ PASSED at 144k (AUC 0.79–0.85) |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | ✅ PASSED at 144k (0.2816) |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | ✅ PASSED at 144k (0.148–0.150) |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.10 | ❌ FAILED (0.092–0.094) — excluded |
| **Linear Hybrid Complement** | PASS adversarial gates at w=0.3–0.4 | ✅ PASSED (JP 0.61–0.67, LD < 0.85) |

**Note**: Dense embeddings remain BELOW TF-IDF baseline (JP 0.61–0.67 vs 0.78–0.79). These are COMPLEMENTARY views only. TF-IDF citation hybrids remain PRIMARY product mode.

---

## Multi-Level Recursive Protocol — VALID NEGATIVE RESULT ❌

**4-level recursive constrained hierarchical Leiden at 174k**: All 5 TF-IDF modes FAIL — all decisions collapse to single cluster (label 0) at all levels.

**Calibration FAILS**: Thresholds too aggressive for TF-IDF signal density at 174k.

**Valid negative findings preserved per evidence tier protocol**.

---

## Scale Extrapolation — VALIDATED ✅

**144k checkpoint (22/26 years, 2000–2021)**:
- fine_branch_purity ~0.97 (hierarchical builder / 2-level)
- improvement_rate: 0.48–0.65 branch / 0.75–0.76 area
- strict_nesting ≥ 0.99
- fine_singletons ~4–5%

**NESTING_METRIC_DEFECT_v1 ENFORCED** — strict definition required.

---

## Test Verification — ALL PASS ✅

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

## Blocker Chain (Upstream — No Lane Defect)

```
fractal-map (BLOCKED_ON_DEPENDENCIES)
    └── legal-distance: 174k dense embeddings (~11% complete, 3/26 years)
            └── corpus: BGE/bger ID mapping + parquet 2022-2026 (29,520 decisions) + section extraction at 174k scale
```

---

## Control Plane Defect Note

**V28-pattern persistent defect**: `/tmp/lex_control/state/factory_direction.json` (mounted control plane) incorrectly shows `fractal-map.status="RUN"` while workspace `state/fractal-map.json` and `state/factory_direction.json` correctly show `BLOCKED_ON_DEPENDENCIES`. This is an **infrastructure defect in control plane mounting**, NOT a lane failure.

---

## Recommendation

**No further same-question cycles justified** (`continue_recommended: false`).

**Factory Director actions required**:
1. Update mounted control plane (`factory_direction.json` on `main`): set `fractal-map.status = "BLOCKED_ON_DEPENDENCIES"`
2. Resume corpus lane for: BGE/bger ID mapping, parquet 2022–2026 (29,520 decisions), section extraction at 174k scale
3. Define successor question for fractal-map lane once dense embeddings are delivered

---

## Evidence Preservation

All ACCEPTED evidence preserved in `results/fractal_map/` with full provenance:
- `hierarchical_v1_174k_tfidf/` — 8 mode results (6 PASS, 2 FAIL)
- `multi_level_protocol_174k_tfidf/` — 5 modes FAIL (valid negative)
- `dense_embeddings_integration_contract_v34.json` — frozen contract
- `nesting_metric_defect_v1_audit.json` — metric enforcement
- `scale_extrapolation/` — scale model
- `final_pipeline_validation/` — pipeline readiness
- `hierarchical_product_integration/` — product artifacts

**Lane deliverable VERIFIED AND AUDIT-READY.**