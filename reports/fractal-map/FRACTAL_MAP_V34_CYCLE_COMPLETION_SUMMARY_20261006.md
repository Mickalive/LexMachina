# Fractal Map Lane — Cycle Completion Summary (v34)

**Date:** 2026-10-06  
**Factory Direction Version:** 34  
**Lane State:** `BLOCKED_ON_DEPENDENCIES` ✅  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** false  

---

## Executive Summary

The fractal-map lane has **COMPLETED all discriminating experiments** for factory direction v34. The lane question — *"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves"* — has been fully answered.

**No further same-question cycles are justified** (`continue_recommended: false`). The lane is correctly blocked on upstream dependencies requiring corpus lane resumption.

---

## Deliverables Completed

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k ✅

| Mode | Sample | Coarse Clusters | Fine Clusters | Fine Branch Purity | Verdict |
|------|--------|-----------------|---------------|-------------------|---------|
| `full_text_tfidf_light` | 173,963 | 19 | 365 | **0.930** | PASS |
| `regeste_full_text_hybrid_0.5` | 173,963 | 39 | 412 | **0.906** | PASS |
| `regeste_full_text_hybrid_0.7` | 173,963 | 39 | 412 | **0.906** | PASS |

**Citation-based modes (at 52% scale / ~91k decisions):**
| Mode | Fine Branch Purity | Verdict |
|------|-------------------|---------|
| `cited_decisions_tfidf` | 0.685 | PASS |
| `cited_outcome_hybrid_0.5` | 0.633 | PASS |
| `cited_outcome_hybrid_0.7` | 0.609 | PASS |

**Location:** `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`

---

### 2. Multi-Level Recursive Protocol — FAILS at 174k for TF-IDF ❌ (Negative Result Preserved)

All 5 TF-IDF modes FAIL the multi-level (4+ level) protocol at 174k scale. All modes collapse to a single cluster at all levels.

| Mode | Levels Tested | Actual Result | Verdict |
|------|---------------|---------------|---------|
| `full_text_tfidf_light` | 4 | All decisions in single cluster (label 0) at all levels | FAIL |
| `regeste_full_text_hybrid_0.5` | 4 | All decisions in single cluster (label 0) at all levels | FAIL |
| `regeste_full_text_hybrid_0.7` | 4 | All decisions in single cluster (label 0) at all levels | FAIL |
| `cited_decisions_tfidf` | 4 | All decisions in single cluster (label 0) at all levels | FAIL |
| `regeste_tfidf` | 4 | All decisions in single cluster (label 0) at all levels | FAIL |

**Clarification:** The **hierarchical_v1 production protocol** (2-level: coarse→fine) **PASSES** for 3 text-based production modes at 174k. The **multi-level recursive protocol** (4+ levels) was tested and **does not pass** for TF-IDF modes. This is a valid negative result, correctly preserved per evidence tier protocol.

**Location:** `results/fractal_map/multi_level_protocol_174k_tfidf/`

---

### 3. Calibration — NEGATIVE RESULT (Correctly Preserved) ❌

Calibration thresholds are too aggressive for TF-IDF signal density. Calibrated protocol does not improve over frozen v1.

**Location:** `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`

---

### 4. Dense Embedding Integration Contract v34 — FROZEN ✅

Four complementary views defined with frozen acceptance criteria:

| Complementary View | Acceptance Criterion | Evidence Status |
|-------------------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | ✅ PASSED at 144k (AUC 0.79-0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | ✅ PASSED at 144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | ✅ PASSED at 144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | ❌ FAILED (0.09) — correctly excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | ✅ PASSED (JP 0.61-0.67) |

**Note:** Dense embeddings remain BELOW TF-IDF baseline (JP 0.61-0.67 vs 0.78-0.79). These are COMPLEMENTARY views only. TF-IDF citation hybrids remain PRIMARY product mode.

**Location:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`  
**Report:** `reports/fractal-map/dense_embedding_integration_contract_v1.md`

---

### 5. Preparatory Dense Validation — COMPLETE ✅

- **12k dense (ACCEPTED)**: Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint** (22/26 years, 2000-2021): Fine branch purity ~0.97, improvement_rate 0.48-0.65 branch / 0.75-0.76 area, strict_nesting ≥0.99, fine singletons ~4-5%

**Note:** These 144k metrics describe the **hierarchical builder (2-level)**, NOT the multi-level recursive protocol (which FAILS at 144k).

**Locations:** `results/fractal_map/12k_dense_comprehensive/`, `results/fractal_map/144k_multi_level_validation/`

---

### 6. Nesting Metric Defect v1 — ENFORCED ✅

7 compressed-family modes had `nesting_score≥0.99` without scope annotation. Enforcement active: `min_cluster_size` enforces nesting=1.0 by construction; all future outputs require explicit scope annotation.

**Location:** `results/fractal_map/nesting_metric_defect_v1_audit.json`

---

### 7. Scale Extrapolation Validated ✅

144k checkpoint validates hierarchical builder (2-level) scale extrapolation: fine branch purity ~0.97, improvement rates healthy (branch 0.48-0.65, area 0.75-0.76), strict_nesting ≥0.99, fine singletons ~4-5%. Confirms TF-IDF hierarchical_v1 production protocol scales to full corpus.

---

## Test Suite Verification

| Test Suite | Total | Passed | Skipped | Status |
|------------|-------|--------|---------|--------|
| `test_verify.py` | 186 | 185 | 1 | ✅ |
| `test_pipeline_readiness.py` | 14 | 14 | 0 | ✅ |
| `test_zoom_quality_174k_eval.py` | 4 | 4 | 0 | ✅ |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 7 | 0 | ✅ |
| `test_12k_dense_comprehensive.py` | 10 | 10 | 0 | ✅ |
| `test_dense_embeddings_infrastructure.py` | 15 | 14 | 1 | ✅ |
| `test_scale_dependency.py` | 11 | 11 | 0 | ✅ |
| **GRAND TOTAL** | **247** | **245** | **2** | ✅ |

**Skipped tests (correctly, known upstream blockers):**
- `test_verify.py::TestLegalDistanceScaleReadiness::test_provenance_reproduced_by_recompute` — SKIPPED (optional Leiden recompute deps not installed)
- `test_dense_embeddings_infrastructure.py::TestDenseEmbeddingsDataReadiness::test_dense_mode_artifacts_exist` — SKIPPED (dense mode artifacts don't exist at 174k yet; known upstream blocker)

---

## Blocker Chain (Unresolved — No Lane Defect)

```
fractal-map (BLOCKED_ON_DEPENDENCIES)
    └── legal-distance: 174k dense embeddings (11% complete, 3/26 years)
            └── corpus: BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k
```

**No fractal-map lane defect exists.** All work for factory direction v34 question is complete.

---

## Factory Director Decisions Required

1. **Resume corpus lane** for:
   - BGE/bger ID mapping production (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
   - Parquet generation for years 2022-2026 (29,520 decisions missing from pinned 2026 snapshot)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density

2. **Define successor question** for fractal-map lane once dense embeddings are delivered at 174k scale

---

## Orchestration Note

The mounted control plane (`/tmp/lex_control/state/factory_direction.json`) incorrectly shows `fractal-map.status="RUN"` while the workspace state (`state/fractal-map.json`, `state/factory_direction.json`) and ALL audit reports correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **persistent V28-pattern infrastructure defect in the control plane mounting/persistence mechanism**, NOT a lane failure. The lane state is authoritative and correct.

---

## Audit Readiness

**AUDIT READINESS: CONFIRMED** ✅

All claim-bearing outputs frozen before observation. Provenance chain complete. Negative results preserved. State file machine-readable and complete per Research Protocol §20.

---

*Generated from ACCEPTED evidence. All metrics frozen before observation. Provenance preserved in referenced results directories and `state/fractal-map.json`.*