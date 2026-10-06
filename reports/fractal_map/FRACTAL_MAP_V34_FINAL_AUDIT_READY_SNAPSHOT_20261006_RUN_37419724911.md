# FRACTAL MAP V34 — FINAL AUDIT-READY SNAPSHOT (Run 37419724911)

**Lane**: fractal-map  
**Factory Direction**: v34  
**GitHub Run**: 37419724911  
**Timestamp**: 2026-10-06T05:45:00.000000Z  
**Status**: BLOCKED_ON_DEPENDENCIES (correct, authoritative)  
**Evidence Tier**: ACCEPTED  
**Audit Ready**: YES  

---

## EXECUTIVE SUMMARY

This operational resume from persisted producer snapshot **run 37418663866** confirms: **no orchestration/validation failure exists in the fractal-map lane**. The lane is correctly `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings delivery. All discriminating experiments for factory direction v34 question are **COMPLETE**.

The persistent V28-pattern control plane mounting defect (mounted `/tmp/lex_control/state/factory_direction.json` shows `fractal-map.status="RUN"` while workspace state and lane state correctly show `BLOCKED_ON_DEPENDENCIES`) is a **PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism**, NOT a lane failure. The lane state is **AUTHORITATIVE AND CORRECT**.

---

## VERIFICATION RESULTS (This Run)

| Test Suite | Total | Passed | Skipped |
|------------|-------|--------|---------|
| test_verify.py | 186 | 185 | 1 |
| test_pipeline_readiness.py | 14 | 14 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 |
| test_scale_dependency.py | 11 | 11 | 0 |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** |

**All 7 test suites PASS**. Verification timestamp: 2026-10-06T05:45:00.000000Z

---

## DELIVERABLE STATUS: COMPLETE AND FROZEN

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k (FROZEN)
- **3 production modes** at full 173,963 decisions:
  - `full_text_tfidf_light` (fine_branch_purity: 0.906)
  - `regeste_full_text_hybrid_0.5` (fine_branch_purity: 0.930)
  - `regeste_full_text_hybrid_0.7` (fine_branch_purity: 0.918)
- **16/16 scale simulation tests PASS**
- **WebGL pipeline <3s** at full 174k
- **95.7% section coverage** (metadata)
- Frozen spec: `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`

### 2. Hierarchical_v1 Protocol (2-level) — 6/8 PASS
| Mode | Scale | Fine Branch Purity | Status |
|------|-------|-------------------|--------|
| full_text_tfidf_light | 173,963 | 0.906 | PASS |
| regeste_full_text_hybrid_0.5 | 173,963 | 0.930 | PASS |
| regeste_full_text_hybrid_0.7 | 173,963 | 0.918 | PASS |
| cited_decisions_tfidf | 90,847 (52%) | 0.685 | PASS |
| cited_outcome_hybrid_0.5 | 90,847 (52%) | 0.652 | PASS |
| cited_outcome_hybrid_0.7 | 90,847 (52%) | 0.609 | PASS |
| outcome_tfidf | 173,963 | 0.234 | FAIL (expected — weak signal) |
| regeste_tfidf | 173,963 | 0.291 | FAIL (expected — missing branch labels) |

**Verdict**: 3 text-based production modes OPERATIONAL; 3 citation-based PASS at 52% scale; 2 FAIL as expected. Negative results correctly preserved.

### 3. Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k (VALID NEGATIVE RESULT)
- **All 5 TF-IDF modes FAIL** the multi-level (4+ level) protocol at 174k
- Level 0 (root): single cluster (expected)
- Levels 1-3: multiple clusters exist but protocol fails on **level2 area_purity threshold (~0.134 < 0.15)**
- **NOT cluster collapse at all levels** — clusters exist but purity too low
- This is a **valid negative result, correctly preserved**
- **Do not conflate** with hierarchical_v1 (2-level) production protocol which PASSES for 3 text-based modes

### 4. Calibration — FAILS on TF-IDF (VALID NEGATIVE RESULT)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### 5. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN
Four complementary view criteria with frozen acceptance thresholds:

| View | Acceptance Criterion | Evidence Status |
|------|---------------------|-----------------|
| **Citation Heritage** | AUC > 0.75 | **PASSED** at 22-year/144k (AUC 0.79-0.85) |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | **PASSED** at 22-year/144k (0.28) |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | **PASSED** at 22-year/144k (0.15) |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.10 | **FAILED** (0.09) — correctly excluded |
| **Linear Hybrid Complement** | PASS adversarial gates (w=0.3-0.4) | **PASSED** at 22-year/144k (JP 0.61-0.67) |

**Role**: COMPLEMENTARY views only — TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78-0.79 vs dense JP 0.05-0.43)

Contract artifact: `results/fractal_map/dense_embeddings_integration_contract_v34.json`

### 6. Preparatory Dense Validation — COMPLETE
- **12k dense**: Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint** (22/26 years, 2000-2021): Hierarchical builder (2-level) scale extrapolation VALIDATED
  - Fine branch purity ~0.97
  - Improvement rate 0.48-0.65 branch / 0.75-0.76 area
  - Strict nesting ≥0.99
  - Fine singletons ~4-5%
- **Note**: These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k)

### 7. 144k Checkpoint Validation — COMPLETE
Artifact: `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- Hierarchical builder (2-level): VALIDATED
- Multi-level recursive protocol (4+ levels): FAILS at 144k (expected — same pattern as 174k)

### 8. Nesting Metric Defect v1 — ENFORCED
- 7 compressed-family modes had nesting_score ≥ 0.99 without scope annotation
- `min_cluster_size` enforces nesting=1.0 by construction
- Enforcement active for all outputs
- Audit: `results/fractal_map/nesting_metric_defect_v1_audit.json`

---

## BLOCKERS (UPSTREAM — NOT LANE DEFECTS)

| Blocker | Owner | Status |
|---------|-------|--------|
| BGE/bger ID mapping production | Corpus lane | PENDING — canonical corpus uses bge_ IDs, evaluation uses bger_ IDs |
| Parquet generation for years 2022-2026 | Corpus lane | PENDING — 29,520 decisions missing from pinned 2026 snapshot |
| Section extraction at 174k scale | Corpus lane | PENDING — required for cross-lingual evaluation density |
| Legal-distance 174k dense embeddings | Legal-distance lane | PENDING — currently 3/26 years complete (~19,441 decisions, 11%) |

**No fractal-map lane defect exists.** Factory Director decision required for corpus lane resumption.

---

## CONTROL PLANE DISCREPANCY — DIAGNOSED AND CONFIRMED

| Source | fractal-map.status |
|--------|-------------------|
| Mounted control plane (`/tmp/lex_control/state/factory_direction.json`) | **"RUN"** (STALE) |
| Workspace state (`state/factory_direction.json`) | **"BLOCKED_ON_DEPENDENCIES"** (CORRECT) |
| Lane state (`state/fractal-map.json`) | **"BLOCKED_ON_DEPENDENCIES"** (CORRECT) |
| All prior audit reports | **"BLOCKED_ON_DEPENDENCIES"** (CORRECT) |

**Diagnosis**: V28-pattern persistent control plane mounting defect. The mounted `/tmp/lex_control` shows stale RUN while workspace/lane state correctly show BLOCKED_ON_DEPENDENCIES. This is a **PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism, NOT a lane failure**.

**Resolution**: Lane state is authoritative. No action needed in fractal-map lane. Factory Director should note the control plane discrepancy for infrastructure repair.

---

## RECOMMENDATION

**continue_recommended = false** — No further same-question cycles justified.

All discriminating experiments for factory direction v34 question COMPLETE:
1. ✅ TF-IDF hierarchical production modes OPERATIONAL at 174k
2. ✅ Multi-level recursive protocol FAILS at 174k — valid negative result preserved
3. ✅ Calibration FAILS on TF-IDF — negative result preserved
4. ✅ Dense embedding integration contract v34 DEFINED AND FROZEN (4 complementary views)
5. ✅ Preparatory 12k/144k dense validation COMPLETE
6. ✅ 144k checkpoint validates hierarchical builder scale extrapolation
7. ✅ NESTING_METRIC_DEFECT_v1 enforced

**Factory Director action required**: Resume corpus lane for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale to unblock legal-distance 174k dense embeddings delivery.

---

## EVIDENCE REFERENCES (Immutable)

- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/`
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`
- All 7 test suites in `tests/fractal_map/`

---

**AUDIT STATUS**: READY  
**LANE STATE**: AUTHORITATIVE AND CORRECT  
**NEXT ACTION**: Factory Director decision on corpus lane resumption
