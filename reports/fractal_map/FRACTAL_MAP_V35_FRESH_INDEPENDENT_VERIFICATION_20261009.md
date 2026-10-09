# Fractal-Map Lane — Fresh Independent Verification Report

**Date:** 2026-10-09  
**Factory Direction Version:** 35  
**Lane:** fractal-map  
**Verification Type:** Fresh independent re-verification (clean environment, fresh dependency install)

---

## Executive Summary

**Status:** VERIFIED AND AUDIT-READY  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** FALSE  

All 7 test suites PASS (246 passed, 1 skipped, 0 failed). The fractal-map lane has completed all discriminating experiments for the factory direction v35 question and is correctly blocked on upstream dependencies.

---

## Test Suite Results

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 186 | 0 | 0 |
| test_pipeline_readiness.py | 14 | 14 | 0 | 0 |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | 0 |
| test_scale_dependency.py | 11 | 11 | 0 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | 0 |
| **Grand Total** | **247** | **246** | **1** | **0** |

---

## Deliverables Confirmed

### 1. TF-IDF Hierarchical Production Modes — FINALIZED AND OPERATIONAL at 174k
- **3 production modes** at full 173,963 decisions:
  - `cited_decisions_tfidf`
  - `cited_outcome_hybrid_0.5`
  - `cited_outcome_hybrid_0.7`
- **Fine branch purity:** 0.906–0.930
- **16/16 scale tests PASS**
- **WebGL pipeline:** <3s at 174k

### 2. Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED at 174k
- **4 levels** with perfect nesting (≥0.95)
- **Zero fragmentation**
- **Monotonic refinement**
- **Calibration FAILS** (valid negative result — thresholds too aggressive for signal density)

### 3. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with frozen acceptance criteria:

| View | Acceptance Criterion | Status at Checkpoint Scale |
|------|---------------------|---------------------------|
| Citation Heritage | AUC > 0.75 | PASSED (AUC 0.79–0.85 at 144k) |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.20 | PASSED (0.28 at 144k) |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.10 | PASSED (0.15 at 144k) |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch > 0.10 | FAILED (0.09 at 144k) — NOT INCLUDED |
| Linear Hybrid Complement | PASS both adversarial gates at w=0.3–0.4 | PASSED (JP 0.61–0.67, LD 0.65–0.75) |

### 4. Scale Extrapolation Validated — 144k Checkpoint
- **22/26 years** (2000–2021)
- **Fine branch purity:** ~0.97
- **Improvement rate:** 0.48–0.65 branch / 0.75–0.76 area
- **Strict nesting:** ≥0.99
- **Fine singletons:** ~4–5%

### 5. NESTING_METRIC_DEFECT_v1 — ENFORCED
Strict definition requires fine label's parent matches coarse label for that decision. Any nesting_score ≥ 0.99 requires explicit scope_annotation (scale, representation, config).

---

## Blockers (Upstream Dependencies)

| Lane | Blocker | Impact |
|------|---------|--------|
| **Corpus** | BGE/bger ID mapping production | Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists |
| **Corpus** | Parquet generation for years 2022–2026 | 29,520 decisions missing from pinned 2026 snapshot |
| **Corpus** | Section extraction at 174k scale | Required for cross-lingual evaluation density (sachverhalt/erwaegungen/dispositiv) |
| **Legal-Distance** | 174k dense embeddings computation | Currently ~3/26 years complete (~19,441 decisions, 11%) |

---

## Critical Findings Preserved

- `tfidf_hierarchical_v1_6_of_8_pass`: 3 text-based at full 173,963 (fine_branch_purity 0.906–0.930); 3 citation-based at 52% scale (0.609–0.685)
- `multi_level_recursive_protocol_fails_174k`: Structurally valid but calibration fails (valid negative)
- `calibration_fails_tfidf`: Thresholds too aggressive for signal density (valid negative)
- `dense_integration_contract_frozen`: 4 complementary views with acceptance criteria
- `scale_extrapolation_validated`: 144k checkpoint validates hierarchical builder
- `nesting_metric_defect_enforced`: Strict definition prevents overclaiming
- `blocker_upstream_data`: Corpus lane resumption required for legal-distance 174k dense embeddings

---

## Control Plane Defect Note

**V28-pattern control plane mounting defect PERSISTS** in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`.

This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, **NOT a lane failure**. The lane state in the workspace is authoritative.

---

## Recommendation

**No further same-question cycles justified.** The factory direction v35 question for fractal-map has been fully answered:

> "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022–2026 (29,520 decisions)
3. Section extraction at 174k scale

Once corpus lane delivers, legal-distance lane can compute 174k dense embeddings, enabling multi-view deployment per the frozen v34 integration contract.

---

## Evidence References

- `results/fractal_map/hierarchical_v1_174k_tfidf/` — TF-IDF 174k hierarchical results (4 modes)
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — Multi-level recursive protocol results (4 TF-IDF modes)
- `results/fractal_map/calibrate_multi_level_174k_tfidf/` — Calibration results (FAIL, valid negative)
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen integration contract
- `results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json` — 144k checkpoint validation
- `results/fractal_map/audit/` — Audit gate results
- `state/fractal_map.json` — Machine-readable lane state (this verification recorded)

---

## Verification Environment

- Python 3.12.3
- pytest 9.1.1
- numpy, igraph, leidenalg, scikit-learn (fresh install)
- Clean environment, no cached artifacts