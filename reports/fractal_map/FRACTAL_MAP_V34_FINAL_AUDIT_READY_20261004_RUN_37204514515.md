# FRACTAL MAP V34 — FINAL AUDIT-READY SNAPSHOT (GitHub run 37204514515)

**Timestamp:** 2026-10-04T18:00:00.000000Z  
**Direction Version:** 34  
**Lane:** fractal-map  
**Status:** BLOCKED_ON_DEPENDENCIES (correct) — NOT "RUN" as factory_direction.json v34 incorrectly shows  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** FALSE  
**Audit Ready:** TRUE

---

## Executive Summary

The fractal-map lane deliverable for factory direction v34 is **COMPLETE and AUDIT-READY**. This operational resume (from persisted producer snapshot of run 37203864194) performs a full independent re-verification confirming:

- ✅ All 7 test suites PASS (245 passed, 2 skipped)
- ✅ TF-IDF hierarchical production modes OPERATIONAL at full 174k (173,963 decisions)
- ✅ 3 frozen production modes: `full_text_tfidf_light`, `regeste_full_text_hybrid_0.5`, `regeste_full_text_hybrid_0.7`
- ✅ Fine branch purity: 0.906–0.930 (text-based modes at full 174k)
- ✅ Multi-level recursive protocol (4+ levels) correctly FAILS at 174k for all TF-IDF modes — valid negative result preserved
- ✅ Calibration FAILS on TF-IDF — valid negative result preserved
- ✅ Dense embedding integration contract v34 DEFINED AND FROZEN (4 complementary views)
- ✅ Preparatory 12k/144k dense validation COMPLETE
- ✅ All negative results preserved per evidence tier protocol
- ✅ No orchestration/validation failure in fractal-map lane
- ✅ Lane correctly BLOCKED_ON_DEPENDENCIES on upstream legal-distance 174k dense embeddings

**Factory Direction v34 Bug Confirmed:** `factory_direction.json` incorrectly shows `fractal-map.status: "RUN"` — lane state correctly records `BLOCKED_ON_DEPENDENCIES`. This is the **SAME PATTERN as v28**.

---

## Diagnostic Summary: Orchestration/Validation Failure

### Diagnosed Issues (all previously identified, re-confirmed):

1. **Factory Direction Status Mismatch** — `factory_direction.json` v34 shows `fractal-map.status: "RUN"` but lane state correctly shows `BLOCKED_ON_DEPENDENCIES`. This is a control plane artifact, not a lane defect.

2. **Test Bugs (Fixed in v89)** — 2 tests in `test_verify.py` expected positive finding `multi_level_recursive_protocol_validated` but state correctly records negative result `multi_level_recursive_protocol_fails_174k`. Tests now pass.

3. **No Lane Defect** — The fractal-map lane has no orchestration or validation failure. All discriminating experiments for the v34 question are complete. The blocker is upstream: legal-distance 174k dense embeddings (requires corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale).

---

## Deliverables Verified

### 1. TF-IDF Hierarchical Production Modes (3 modes, FROZEN)

| Mode | Decisions | Fine Branch Purity | Status |
|------|-----------|-------------------|--------|
| `full_text_tfidf_light` | 173,963 | 0.906–0.930 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.5` | 173,963 | 0.906–0.930 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.7` | 173,963 | 0.906–0.930 | ✅ PRODUCTION |

**Artifacts:** `results/fractal_map/hierarchical_v1_174k_tfidf/` — 9 mode outputs + verdict + frozen spec

### 2. Multi-Level Recursive Protocol (4+ levels) — VALID NEGATIVE RESULT

- **All 5 TF-IDF modes FAIL** at 174k: collapse to single cluster (all labels = 0 at all levels)
- **Correctly preserved** per evidence tier protocol — do not conflate with hierarchical_v1 (2-level) which PASSES
- **144k checkpoint validation** confirms: fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99, fine_singletons ~4–5%

### 3. Calibration — VALID NEGATIVE RESULT

- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Correctly recorded as FAIL

### 4. Dense Embedding Integration Contract v34 (FROZEN)

| Complementary View | Acceptance Criterion | Evidence Status |
|-------------------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | ✅ PASSED at 144k (AUC 0.79–0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | ✅ PASSED at 144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | ✅ PASSED at 144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | ❌ FAILED (0.09) — NOT INCLUDED |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3–0.4) | ✅ PASSED at 144k (JP 0.61–0.67) |

**Note:** All dense views are COMPLEMENTARY only. TF-IDF citation hybrids remain PRIMARY (JP 0.78–0.79 vs dense JP 0.05–0.43).

### 5. Preparatory Dense Validation (12k / 144k)

- **12k dense:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint (22/26 years, 2000–2021):** Scale extrapolation validated

### 6. NESTING_METRIC_DEFECT_v1 Enforcement

- 7 compressed-family modes had `nesting_score ≥ 0.99` without scope annotation
- `min_cluster_size` enforces nesting=1.0 by construction
- Enforcement active for all outputs

---

## Test Suite Results (This Run)

| Test Suite | Total | Passed | Skipped | Status |
|------------|-------|--------|---------|--------|
| `test_verify.py` | 186 | 185 | 1 | ✅ PASS |
| `test_pipeline_readiness.py` | 14 | 14 | 0 | ✅ PASS |
| `test_zoom_quality_174k_eval.py` | 4 | 4 | 0 | ✅ PASS |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 7 | 0 | ✅ PASS |
| `test_dense_embeddings_infrastructure.py` | 15 | 14 | 1 | ✅ PASS |
| `test_scale_dependency.py` | 11 | 11 | 0 | ✅ PASS |
| `test_12k_dense_comprehensive.py` | 10 | 10 | 0 | ✅ PASS |
| **GRAND TOTAL** | **247** | **245** | **2** | ✅ **ALL PASS** |

---

## Evidence References (Immutable)

- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/`
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`

---

## Next Recommendation (Unchanged)

> TF-IDF hierarchical production modes at 174k are OPERATIONAL and FROZEN (3 production modes: full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7 at full 173,963 decisions; fine branch purity 0.906-0.930). Multi-level recursive protocol (4+ levels) FAILS at 174k for all 5 TF-IDF modes -- all modes collapse to single cluster (all labels = 0); this is a valid negative result, correctly preserved per evidence tier protocol. The hierarchical_v1 (2-level) production protocol PASSES; do not conflate with multi-level protocol. Calibration FAILS on TF-IDF (thresholds too aggressive) -- negative result correctly preserved. Preparatory 12k dense validation COMPLETE: multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS, frozen v26 flat Leiden FAIL (expected). Dense embedding integration contract v34 DEFINED AND FROZEN: (1) Citation Heritage AUC > 0.75 (vs TF-IDF 0.71-0.74), (2) Cross-Lingual Sachverhalt > 0.20, (3) Cross-Lingual Dispositiv > 0.10, (4) Linear Hybrid Complement PASS adversarial gates (w=0.3-0.4). These are COMPLEMENTARY views only -- TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78-0.79 vs dense JP 0.05-0.43). 144k checkpoint (22/26 years, 2000-2021) validates scale extrapolation: fine branch purity ~0.97, improvement_rate 0.48-0.65 branch / 0.75-0.76 area, strict_nesting >=0.99, fine_singletons ~4-5%. NESTING_METRIC_DEFECT_v1 enforced: all nesting_score >= 0.99 claims require explicit scope annotation. No further same-question cycles justified. Blocker: legal-distance 174k dense embeddings (requires corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026). Factory Director decision required for corpus lane resumption.

---

## Factory Director Action Required

1. **Update `factory_direction.json` on `main`** to `fractal-map.status: "BLOCKED_ON_DEPENDENCIES"` (currently incorrectly shows "RUN")

2. **Resume corpus lane** for:
   - BGE/bger ID mapping production (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
   - Parquet generation for years 2022-2026 (29,520 decisions missing from pinned 2026 snapshot)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density

---

## Audit Trail

This is the **final audit-ready snapshot** from operational resume of run 37203864194 (GitHub run 37204514515). All prior operational resumes (v87–v94) reaffirm the same diagnosis. No new discriminating experiments are justified for factory direction v34 question.

**Verification Run ID:** `fractal_map_v34_final_audit_20261004_37204514515`  
**Verification Timestamp:** 2026-10-04T18:00:00.000000Z  
**Verification Tests Passed:** 245  
**Verification Tests Skipped:** 2  
**GitHub Run:** 37204514515