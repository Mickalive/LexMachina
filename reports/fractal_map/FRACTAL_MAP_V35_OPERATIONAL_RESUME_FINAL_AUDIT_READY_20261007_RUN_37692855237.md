# FRACTAL MAP LANE — V35 OPERATIONAL RESUME FINAL AUDIT-READY SNAPSHOT
**GitHub Run:** 37692855237 | **Factory Direction:** v35 | **Date:** 2026-10-07
**Status:** VERIFIED AND AUDIT-READY | **Lane State:** BLOCKED_ON_DEPENDENCIES

---

## Executive Summary

This report documents the final independent re-verification of the fractal-map lane deliverable for factory direction v35. All 7 test suites pass (245 tests passed, 2 skipped). The lane has completed all discriminating experiments for the v34/v35 question and is correctly BLOCKED_ON_DEPENDENCIES awaiting upstream data from corpus and legal-distance lanes.

**Key Finding:** No orchestration/validation failure exists in the fractal-map lane. The V28-pattern control plane mounting defect persists in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **persistent infrastructure defect in the control plane mounting/persistence mechanism**, NOT a lane failure.

---

## Verification Results

### Test Suite Summary (All 7 Suites PASS)

| Test Suite | Tests | Passed | Skipped | Status |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 186 | 0 | ✅ PASS |
| test_pipeline_readiness.py | 14 | 14 | 0 | ✅ PASS |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | ✅ PASS |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | ✅ PASS |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | ✅ PASS |
| test_scale_dependency.py | 11 | 11 | 0 | ✅ PASS |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | ✅ PASS |
| **TOTAL** | **247** | **245** | **2** | ✅ **PASS** |

---

## Accepted Evidence (ACCEPTED Tier)

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
- **3 production modes at full 173,963 decisions:**
  - `full_text_tfidf_light` — fine_branch_purity 0.906-0.930
  - `regeste_full_text_hybrid_0.5` — fine_branch_purity 0.906-0.930
  - `regeste_full_text_hybrid_0.7` — fine_branch_purity 0.906-0.930
- **Protocol:** hierarchical_v1 (2-level) — 6/8 PASS at 174k
- **Scale validation:** 16/16 174k scale simulation tests PASS
- **WebGL pipeline:** <3s render time at full 174k

### 2. Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k (Valid Negative)
- All 5 TF-IDF modes FAIL the multi-level protocol at 174k
- Level 0 (root): single cluster (expected)
- Levels 1-3: multiple clusters exist but protocol fails on level2 area_purity threshold (~0.134 < 0.15)
- **NOT** cluster collapse at all levels — correctly diagnosed as signal density limitation
- Negative result preserved per evaluation doctrine

### 3. Calibration Protocol — FAILS on TF-IDF (Valid Negative)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### 4. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN
**Location:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`

Four complementary views with frozen acceptance criteria:

| View | Acceptance Criterion | Evidence Status |
|------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | ✅ PASSED at 22yr/144k (AUC 0.79-0.85) |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.20 | ✅ PASSED at 22yr/144k (0.28) |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.10 | ✅ PASSED at 22yr/144k (0.15) |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch > 0.10 | ❌ FAILED (0.09) — excluded |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3-0.4) | ✅ PASSED at 22yr/144k (JP 0.61-0.67) |

**Note:** TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78-0.79). Dense embeddings are COMPLEMENTARY views only.

### 5. Preparatory Dense Validation — COMPLETE
- **12k scale:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation, 39 coarse → 412 fine)
- **144k scale (22/26 years, 2000-2021):** Hierarchical builder SUCCESS, frozen v26 flat Leiden FAIL (expected)

### 6. Scale Extrapolation — VALIDATED at 144k Checkpoint
- Hierarchical builder (2-level) fine_branch_purity ~0.97
- Improvement rate: 0.48-0.65 branch / 0.75-0.76 area
- Strict nesting ≥0.99
- Fine singletons ~4-5%
- **Note:** These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k)

### 7. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had nesting_score≥0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs

---

## Critical Blockers (Upstream Dependencies)

The fractal-map lane is **correctly BLOCKED_ON_DEPENDENCIES** on:

1. **Corpus Lane:** BGE/bger ID mapping production (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. **Corpus Lane:** Parquet generation for years 2022-2026 (29,520 decisions missing from pinned 2026 snapshot)
3. **Corpus Lane:** Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density
4. **Legal-Distance Lane:** 174k dense embeddings computation (currently 3/26 years complete, ~19,441 decisions, 11%)

**No fractal-map lane defect exists.** Factory Director action required: Resume corpus lane.

---

## State File Verification

**File:** `state/fractal-map.json` (workspace) — **CORRECT**
- `direction_version`: 35 ✅
- `evidence_tier`: ACCEPTED ✅
- `cycle_status`: BLOCKED_ON_DEPENDENCIES ✅
- `continue_recommended`: false ✅
- `audit_ready`: true ✅
- `verification_tests_passed`: 245 ✅
- `verification_tests_skipped`: 2 ✅

**File:** `/tmp/lex_control/state/factory_direction.json` (mounted control plane) — **DEFECTIVE**
- Line 16: `"fractal-map": { "status": "RUN", ... }` — **INCORRECT**
- Workspace state correctly shows `BLOCKED_ON_DEPENDENCIES`
- This is the V28-pattern control plane mounting defect (persistent infrastructure issue)

---

## No Further Cycles Justified

**continue_recommended: false** — No additional same-question cycles have a concrete discriminating purpose. All evidence for the v34/v35 question is ACCEPTED and frozen:

1. TF-IDF hierarchical production modes FINALIZED
2. Multi-level recursive protocol NEGATIVE (valid)
3. Calibration NEGATIVE (valid)
4. Dense integration contract FROZEN
5. Scale extrapolation VALIDATED
6. NESTING_METRIC_DEFECT_v1 ENFORCED

The only remaining work is **upstream data delivery** (corpus lane resumption → legal-distance 174k dense embeddings → fractal-map multi-view deployment).

---

## Evidence References (Machine-Readable)

Key artifacts preserved in `results/fractal_map/`:
- `hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `multi_level_protocol_174k_tfidf/`
- `multi_level_protocol_174k_tfidf_calibrated/`
- `12k_dense_comprehensive/`
- `144k_multi_level_validation/multi_level_144k_results.json`
- `nesting_metric_defect_v1_audit.json`
- `dense_embeddings_integration_contract_v34.json`

---

## Conclusion

**Lane deliverable COMPLETE and AUDIT-READY.**

The fractal-map lane has successfully:
1. Finalized TF-IDF hierarchical production modes at 174k (3 production modes operational)
2. Validated multi-level recursive protocol structure at 174k (negative result preserved)
3. Tested and failed calibration on TF-IDF (negative result preserved)
4. Froze dense embedding integration contract v34 with 4 complementary view criteria
5. Validated scale extrapolation via 144k checkpoint
6. Enforced NESTING_METRIC_DEFECT_v1 across all outputs

**All evidence preserved. Negative results intact. Contract frozen. continue_recommended=false.**

**Factory Director Decision Required:** Resume corpus lane for BGE/bger ID mapping, 2022-2026 parquet generation, and section extraction at 174k scale to unblock legal-distance dense embeddings and enable multi-view fractal map deployment.

---
*Generated by independent re-verification run 37692855237 (factory direction v35)*