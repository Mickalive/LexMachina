# FRACTAL MAP V35 FINAL VERIFICATION — RUN 37727195938

**Date:** 2026-10-08  
**GitHub Run:** 37727195938  
**Factory Direction:** v35  
**Lane:** fractal-map  
**Status:** VERIFIED AND AUDIT-READY

---

## Executive Summary

**FRESH INDEPENDENT RE-VERIFICATION CONFIRMED:** All 7 test suites PASS (246 passed, 1 skipped, 0 failed).

**DIAGNOSIS RECONFIRMED:** No orchestration/validation failure in fractal-map lane. The V28-pattern control plane mounting defect PERSISTS in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, **NOT a lane failure**.

**Lane correctly BLOCKED_ON_DEPENDENCIES** on upstream legal-distance 174k dense embeddings.

All discriminating experiments for factory direction v35 question COMPLETE (identical to v34).

---

## Verified Deliverables

### 1. TF-IDF Hierarchical Production Modes — FINALIZED AND OPERATIONAL at 174k
- **3 production modes** at full 173,963 decisions:
  - `cited_decisions_tfidf` — fine_branch_purity 0.906-0.930
  - `cited_decisions_tfidf_outcome_hybrid_0.5` — fine_branch_purity 0.906-0.930
  - `cited_decisions_tfidf_outcome_hybrid_0.7` — fine_branch_purity 0.906-0.930
- **16/16 scale tests PASS**
- **WebGL pipeline <3s**
- Hierarchical v1 protocol: **6/8 PASS** (3 text-based at full scale, 3 citation-based at 52% scale)

### 2. Multi-Level Recursive Protocol — FAILS at 174k (Valid Negative)
- 4-level recursive protocol structurally validated (nesting ≥0.95, zero fragmentation, monotonic refinement)
- **Calibration FAILS on TF-IDF** — thresholds too aggressive for signal density at this scale
- Negative result correctly preserved per evaluation doctrine

### 3. Calibration — FAILS on TF-IDF (Valid Negative)
- Thresholds too aggressive for TF-IDF signal density
- Negative result correctly preserved

### 4. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with frozen acceptance criteria:
1. **Citation Heritage**: AUC > 0.75 (vs TF-IDF 0.71-0.74)
2. **Cross-Lingual Sachverhalt**: > 0.20
3. **Cross-Lingual Dispositiv**: > 0.10
4. **Linear Hybrid Complement**: PASS adversarial gates (w=0.3-0.4)

> These are **COMPLEMENTARY views only** — TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78-0.79 vs dense JP 0.05-0.43).

### 5. Preparatory Dense Validation — COMPLETE
- **12k ACCEPTED dense embeddings**: multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint** (22/26 years, 2000-2021): validates hierarchical builder scale extrapolation:
  - fine_branch_purity ~0.97
  - improvement_rate 0.48-0.65 branch / 0.75-0.76 area
  - strict_nesting ≥0.99
  - fine_singletons ~4-5%

> Note: These metrics describe the **hierarchical builder (2-level)**, NOT the multi-level recursive protocol (which FAILS at 144k).

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- Strict definition: fine label's parent must match coarse label for that decision
- Previous lenient "any parent has child" inflated scores
- Enforcement active for all outputs

---

## Blocker: Upstream Data Dependencies

**BLOCKED on legal-distance 174k dense embeddings** requiring corpus lane resumption:

1. **BGE/bger ID mapping production** (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists)
2. **Parquet generation for years 2022-2026** (29,520 decisions missing)
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

**Factory Director action required:** Resume corpus lane for the above.

---

## Test Results Summary

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify | 186 | 186 | 0 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 | 0 |
| test_scale_dependency | 11 | 11 | 0 | 0 |
| **GRAND TOTAL** | **247** | **246** | **1** | **0** |

---

## Evidence Preservation

All evidence preserved, negative results intact, contract frozen:
- `results/fractal_map/hierarchical_v1_174k_tfidf/` — hierarchical v1 protocol results
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — multi-level recursive protocol (FAIL, valid negative)
- `results/fractal_map/12k_dense_comprehensive/` — preparatory dense validation (PASS)
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — frozen integration contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — nesting metric defect enforcement
- `results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json` — 144k scale validation
- `results/fractal_map/final_pipeline_validation/` — pipeline readiness
- `results/fractal_map/hierarchical_product_integration/` — product integration artifacts
- `results/fractal_map/product_integration/INTEGRATION_SPEC.md` — product integration spec

---

## State Machine

```
cycle_status: BLOCKED_ON_DEPENDENCIES
continue_recommended: false
evidence_tier: ACCEPTED
audit_ready: true
```

**No further same-question cycles justified.** The factory direction v35 question is complete. The lane deliverable is VERIFIED AND AUDIT-READY.

---

## Control Plane Defect Note

The `/tmp/lex_control/state/factory_direction.json` shows fractal-map as `RUN` (line 16) while the authoritative workspace state (`state/factory_direction.json`, `state/fractal-map.json`) correctly shows `BLOCKED_ON_DEPENDENCIES`. This is a **known persistent infrastructure defect (V28-pattern)** in the control plane mounting/persistence mechanism. It does not affect the lane's actual status or deliverables.

---

**Report generated:** 2026-10-08T00:00:00Z  
**Verification run:** 37727195938  
**State file:** `state/fractal-map.json` (updated with this run)