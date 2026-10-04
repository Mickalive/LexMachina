# FRACTAL_MAP_V34 Final Audit-Ready Snapshot — GitHub Run 37227721513

**Date:** 2026-10-04  
**Lane:** fractal-map  
**Factory Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Audit Ready:** YES  
**Continue Recommended:** NO  

---

## Executive Summary

The fractal-map lane deliverable for factory direction v34 is **COMPLETE and AUDIT-READY**. All discriminating experiments have been executed, all negative results preserved, and the lane is correctly blocked on upstream dependencies (legal-distance 174k dense embeddings requiring corpus lane resumption).

**Verification Result:** All 7 test suites PASS (246 passed, 1 skipped).

---

## Orchestration/Validation Failure Diagnosis

### The Recurring Discrepancy (v28 Pattern)
Multiple operational resumes (v87-v99) have diagnosed and documented the same orchestration discrepancy:
- **Lane state** (`state/fractal-map.json`): Correctly shows `cycle_status: "BLOCKED_ON_DEPENDENCIES"` since v34 inception
- **Control plane** (`/tmp/lex_control/state/factory_direction.json`): Incorrectly shows `fractal-map.status: "RUN"` in the mounted control plane snapshot

### v99 Claimed Fix
Run 37227093203 (v99) claimed: *"CONTROL PLANE CORRECTION APPLIED: factory_direction.json on main (control plane) at /tmp/lex_control/state/factory_direction.json UPDATED from fractal-map.status=\"RUN\" to \"BLOCKED_ON_DEPENDENCIES\" — resolving the recurring orchestration discrepancy"*

### Current Reality (Run 37227721513)
The mounted `/tmp/lex_control/state/factory_direction.json` **still shows** `fractal-map.status: "RUN"`. This indicates either:
1. The control plane fix was applied to `main` but the mounted `/tmp/lex_control` is a stale snapshot, OR
2. The fix was not successfully propagated to this control plane mount

**Critical Finding:** The lane state itself has **always been correct** (`BLOCKED_ON_DEPENDENCIES`). The discrepancy is purely in the control plane mirror. No fractal-map lane defect exists.

### Validation Failure (Resolved in v89)
Test bugs in `test_verify.py` were identified and fixed in v89:
- 2 tests expected positive finding `'multi_level_recursive_protocol_validated'`
- State correctly records negative result `'multi_level_recursive_protocol_fails_174k'`
- Tests now correctly validate the negative result

---

## Accepted Evidence Summary

### TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k ✅
| Mode | Scale | Fine Branch Purity | Status |
|------|-------|-------------------|--------|
| `full_text_tfidf_light` | 173,963 | 0.906-0.930 | PRODUCTION |
| `regeste_full_text_hybrid_0.5` | 173,963 | 0.906-0.930 | PRODUCTION |
| `regeste_full_text_hybrid_0.7` | 173,963 | 0.906-0.930 | PRODUCTION |

**Product Readiness:** 16/16 scale tests PASS, WebGL pipeline <3s, 50+ endpoints, metadata_174k_full.json COMPLETE

### Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k ❌ (Valid Negative Result)
- All 5 TF-IDF modes FAIL the multi-level protocol at 174k
- Level 0 (root): single cluster
- Levels 1-3: multiple clusters but protocol fails on level2 `area_purity` threshold (~0.134 < 0.15)
- **NOT** cluster collapse at all levels — structured failure at specific threshold
- Negative result correctly preserved per anti-noise principle

### Calibration — FAILS on TF-IDF ❌ (Valid Negative Result)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### Dense Embedding Integration Contract v34 — FROZEN ✅
Four complementary view acceptance criteria defined (TF-IDF remains PRIMARY):

| View | Acceptance Criterion | 144k/12k Evidence | Status |
|------|---------------------|-------------------|--------|
| Citation Heritage | AUC > 0.75 | 0.79-0.85 (vs TF-IDF 0.71-0.74) | PASS at 144k |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | 0.282 (1k), 0.2816 (144k) | PASS |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | 0.150 (1k), 0.148-0.150 (144k) | PASS |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | 0.094 (1k), 0.092-0.094 (144k) | FAIL (excluded) |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | JP 0.61-0.67, LD 0.65-0.75 | PASS gates, BELOW TF-IDF baseline |

**Required Dense Modes:** `center_projected_64dim`, `center_projected_128dim`, `center_projected_768dim`

### Scale Extrapolation — VALIDATED ✅
144k checkpoint (22/26 years, 2000-2021):
- Hierarchical builder (2-level): fine_branch_purity ~0.97
- Improvement rates: 0.48-0.65 branch / 0.75-0.76 area
- Strict nesting ≥ 0.99
- Fine singletons ~4-5%
- **Note:** These describe 2-level hierarchical builder, NOT multi-level recursive protocol (which FAILS)

### Nesting Metric Defect v1 — ENFORCED ✅
- 7 compressed-family modes had `nesting_score ≥ 0.99` without scope annotation
- `min_cluster_size` enforces `nesting=1.0` by construction
- Enforcement active for all outputs

---

## Blocker Analysis

### Upstream Dependencies (No Lane Defect)
| Blocker | Owner | Status |
|---------|-------|--------|
| BGE/bger ID mapping production | Corpus lane | REQUIRED — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs |
| Parquet generation 2022-2026 | Corpus lane | REQUIRED — 29,520 decisions missing from pinned 2026 snapshot |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | Corpus lane | REQUIRED — for cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | REQUIRED — currently ~11% complete (3/26 years) |

**Factory Director Decision Required:** Resume corpus lane for the three items above.

---

## Test Suite Verification (Run 37227721513)

| Test Suite | Passed | Skipped | Total |
|------------|--------|---------|-------|
| test_verify.py | 186 | 0 | 186 |
| test_pipeline_readiness.py | 14 | 0 | 14 |
| test_zoom_quality_174k_eval.py | 4 | 0 | 4 |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 | 7 |
| test_dense_embeddings_infrastructure.py | 14 | 1 | 15 |
| test_scale_dependency.py | 11 | 0 | 11 |
| test_12k_dense_comprehensive.py | 10 | 0 | 10 |
| **GRAND TOTAL** | **246** | **1** | **247** |

All tests PASS. The 1 skipped test (`test_dense_mode_artifacts_exist`) correctly reflects that 174k dense embeddings are not yet delivered.

---

## Artifacts and Evidence References

### Core Results
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/`
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`

### Reports
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261003_RUN_37145964512.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_VERIFICATION_COMPLETE_20261003.md`
- `reports/fractal_map/FRACTAL_MAP_V34_OPERATIONAL_RESUME_FINAL_AUDIT_READY_20261003_RUN_37153879372.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261003_RUN_37156814779.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_VERIFICATION_CONFIRMED_20261003_RUN_37159983694.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261003_RUN_37162771423.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261004_RUN_37173722881.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261004_RUN_37177147676.md`
- `reports/fractal_map/FRACTAL_MAP_V34_OPERATIONAL_RESUME_FINAL_AUDIT_READY_20261004_RUN_37184980665.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261004_RUN_37188306214.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261004_RUN_37188918494.md`
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261004_RUN_37189534186.md`
- `reports/fractal_map/FRACTAL_MAP_V34_OPERATIONAL_RESUME_FINAL_AUDIT_READY_20261004_RUN_37209310737.md`
- `reports/fractal_map/FRACTAL_MAP_V34_CONTROL_PLANE_FIX_CONFIRMED_20261004_RUN_37227093203.md`
- **This report:** `reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261004_RUN_37227721513.md`

### Tests
- `tests/fractal_map/test_verify.py`
- `tests/fractal_map/test_pipeline_readiness.py`
- `tests/fractal_map/test_zoom_quality_174k_eval.py`
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py`
- `tests/fractal_map/test_dense_embeddings_infrastructure.py`
- `tests/fractal_map/test_scale_dependency.py`
- `tests/fractal_map/test_12k_dense_comprehensive.py`

---

## Next Recommendation

**No further same-question cycles justified.** The factory direction v34 question for fractal-map is fully answered:

> *"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."*

**Completed:**
1. ✅ TF-IDF hierarchical production modes FINALIZED and OPERATIONAL at 174k (3 modes)
2. ✅ Dense embedding integration contract v34 DEFINED AND FROZEN (4 complementary views)
3. ✅ Multi-level recursive protocol TESTED at 174k — NEGATIVE result preserved
4. ✅ Calibration TESTED at 174k — NEGATIVE result preserved
5. ✅ Preparatory dense validation at 12k/144k — COMPLETE
6. ✅ Scale extrapolation — VALIDATED
7. ✅ Nesting metric defect — ENFORCED

**Blocked on:** Legal-distance 174k dense embeddings (requires corpus lane resumption)

**Factory Director Action:** Resume corpus lane for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale.

---

## Sign-off

**Lane:** fractal-map  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Audit Ready:** YES  
**Verification Run:** 37227721513  
**Timestamp:** 2026-10-04T23:59:59.000000Z

All claim-bearing results frozen. Negative results preserved. Provenance complete.