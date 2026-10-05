# Fractal Map Lane — Factory Direction v34 Completion Confirmed

**GitHub Run:** 37279384092  
**Date:** 2026-10-05  
**Lane State:** `state/fractal-map.json` (evidence_tier=ACCEPTED, cycle_status=BLOCKED_ON_DEPENDENCIES, continue_recommended=false)  
**Factory Direction:** v34  

---

## Executive Summary

The fractal-map lane has **completed all discriminating experiments** for factory direction v34 question:

> *"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."*

**All work is complete.** No further same-question cycles are justified (`continue_recommended=false`). The lane is correctly `BLOCKED_ON_DEPENDENCIES` awaiting upstream delivery of 174k dense embeddings from legal-distance lane (blocked on corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale).

---

## Verification Results

**All 7 test suites PASS (245 passed, 2 skipped):**

| Test Suite | Tests | Passed | Skipped |
|------------|-------|--------|---------|
| test_verify.py | 186 | 185 | 1 |
| test_pipeline_readiness.py | 14 | 14 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 |
| test_scale_dependency.py | 11 | 11 | 0 |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 |
| **TOTAL** | **247** | **245** | **2** |

---

## Accepted Evidence (Frozen)

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
- **3 production modes** at full 173,963 decisions:
  - `full_text_tfidf_light` — fine_branch_purity: 0.906
  - `regeste_full_text_hybrid_0.5` — fine_branch_purity: 0.922
  - `regeste_full_text_hybrid_0.7` — fine_branch_purity: 0.930
- **Hierarchical v1 protocol:** 6/8 PASS (3 text-based at full 174k; 3 citation-based at 52% scale: 0.609-0.685)
- **16/16 scale simulation tests PASS** (product integration)
- **WebGL pipeline:** <3s at 174k

### 2. Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k (Valid Negative)
- All 5 TF-IDF modes FAIL the multi-level protocol at 174k
- Level 0 (root): single cluster
- Levels 1-3: multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15)
- **NOT cluster collapse at all levels** — valid negative result correctly preserved

### 3. Calibration — FAILS on TF-IDF (Valid Negative)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### 4. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN
**4 Complementary Views** (TF-IDF citation hybrids remain PRIMARY — JP 0.78-0.79 vs dense JP 0.05-0.43):

| View | Acceptance Criterion | Evidence |
|------|---------------------|----------|
| **Citation Heritage** | AUC > 0.75 (vs TF-IDF 0.71-0.74) | 144k: cp768 AUC 0.7946, cp64 AUC 0.7922 |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | 144k: cp768 0.2816, cp64 0.2816 |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | 144k: cp768 0.1481, cp64 0.1502 |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.10 | **FAILS** (0.0925-0.0941) — excluded |
| **Linear Hybrid Complement** | PASS adversarial gates at w=0.3-0.4 | 144k: cited_decisions_tfidf+dense w0.4 JP 0.6725 |

### 5. Preparatory Dense Validation — COMPLETE
- **12k dense:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine)
- **144k checkpoint (22/26 years, 2000-2021):** Hierarchical builder (2-level) validates scale extrapolation:
  - fine_branch_purity ~0.97
  - improvement_rate 0.48-0.65 branch / 0.75-0.76 area
  - strict_nesting >=0.99
  - fine_singletons ~4-5%
- **Note:** These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k)

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had nesting_score>=0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs: any nesting_score >= 0.99 requires explicit scope_annotation with scale, representation, config

---

## Blockers (Upstream — Not Lane Defects)

| Blocker | Owner | Status |
|---------|-------|--------|
| BGE/bger ID mapping production | Corpus lane | PENDING (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs) |
| Parquet generation for years 2022-2026 | Corpus lane | PENDING (29,520 decisions missing from pinned 2026 snapshot) |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale | Corpus lane | PENDING (required for cross-lingual evaluation density) |
| 174k dense embeddings computation | Legal-distance lane | PENDING (currently 3/26 years complete, ~19,441 decisions, 11%) |

---

## Control Plane Consistency Note

The V28-pattern control plane mounting defect **persists** in the mounted `/tmp/lex_control/state/factory_direction.json` (shows `fractal-map.status="RUN"`) while workspace `state/factory_direction.json` and lane `state/fractal-map.json` correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **persistent infrastructure defect in the control plane mounting/persistence mechanism**, NOT a lane failure. The lane state is authoritative and correct.

---

## Recommendation

**NO FURTHER SAME-QUESTION CYCLES JUSTIFIED.** (`continue_recommended=false`)

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022-2026 (29,520 decisions)
3. Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

Once corpus lane delivers, legal-distance lane can compute 174k dense embeddings, after which fractal-map lane will integrate the 4 complementary dense views per the frozen v34 contract.

---

## Evidence References (Preserved)

- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/`
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`
- All test suites in `tests/fractal_map/`

---

*Report generated by fractal-map lane agent — GitHub run 37279384092*