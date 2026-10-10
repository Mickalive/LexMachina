# Fractal Map Lane — V35 Lane Complete Confirmation

**Date:** 2026-10-10  
**Factory Direction Version:** 35  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** FALSE  
**Audit Ready:** TRUE

---

## Summary

The fractal-map lane has **completed all discriminating experiments** for the v34/v35 factory direction question:

> *"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."*

All deliverables are **FINALIZED and OPERATIONAL**. The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting corpus lane resumption.

---

## Accepted Deliverables (ACCEPTED Tier)

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
- **3 production modes** at full 173,963 decisions:
  - `cited_decisions_tfidf`
  - `cited_decisions_tfidf_outcome_hybrid_0.5`
  - `cited_decisions_tfidf_outcome_hybrid_0.7`
- **fine_branch_purity:** 0.906–0.930 (text-based, full corpus)
- **citation-based (52% scale):** 0.609–0.685
- **16/16 scale tests PASS** — WebGL pipeline <3s
- **Multi-level recursive protocol:** Structurally VALIDATED (perfect nesting ≥0.95, zero fragmentation, monotonic refinement)

### 2. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views defined with acceptance criteria:
| View | Acceptance Criterion |
|------|---------------------|
| Citation Heritage | AUC > 0.75 |
| Cross-Lingual Sachverhalt | same-branch > 0.20 |
| Cross-Lingual Dispositiv | same-branch > 0.10 |
| Linear Hybrid Complement | PASS adversarial gates |

### 3. Scale Extrapolation — VALIDATED at 144k Checkpoint
- 22/26 years (2000–2021)
- fine_branch_purity ~0.97
- improvement_rate: 0.48–0.65 branch / 0.75–0.76 area
- strict_nesting ≥0.99
- fine_singletons ~4–5%

### 4. Valid Negative Results Preserved
- **Multi-level recursive protocol calibration FAILS** on TF-IDF — thresholds too aggressive for signal density
- **Calibration FAILS** on TF-IDF modes at 174k
- **NESTING_METRIC_DEFECT_v1 enforced** — strict parent-child label matching replaces lenient definition
- **v28 flat Leiden FAIL** (expected)

---

## Verification Results (Fresh Independent Run)

| Test Suite | Passed | Skipped | Failed |
|------------|--------|---------|--------|
| test_verify.py | 186 | 0 | 0 |
| test_pipeline_readiness.py | 14 | 0 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 | 0 |
| test_12k_dense_comprehensive.py | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure.py | 14 | 1 | 0 |
| test_scale_dependency.py | 11 | 0 | 0 |
| **TOTAL** | **246** | **1** | **0** |

All 7 test suites PASS in clean environment with fresh dependency install.

---

## Blocker: Upstream Data Dependencies

The lane is **BLOCKED_ON_DEPENDENCIES** on legal-distance 174k dense embeddings, which require **corpus lane resumption**:

1. **BGE/bger ID mapping production** — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs (no mapping exists)
2. **Parquet generation for years 2022–2026** — 29,520 decisions missing
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

---

## Critical Findings (from state/fractal_map.json)

- **TF-IDF citation hybrids DOMINATE jurist preference** (JP 0.78–0.79) and PASS both adversarial gates at 174k
- **Dense embeddings FAIL jurist gate at ALL scales** (JP 0.05–0.43)
- **Dense embeddings EXCEL at complementary capabilities:** citation heritage recovery (AUC 0.79–0.85 > TF-IDF 0.71–0.74) and section cross-lingual alignment (sachverhalt gap 0.187 vs 0.452)
- **True OOS JuristPref ceiling ~0.53 < 0.7 factory target** — falsifies original dense-beats-TF-IDF hypothesis
- **v18 coarse hierarchy NEGATIVE** (4-label branch max purity 0.65 < 0.7)
- **V28-pattern control plane mounting defect PERSISTS** in `/tmp/lex_control` (shows RUN) while workspace state correctly shows BLOCKED_ON_DEPENDENCIES — infrastructure defect, NOT lane failure

---

## Next Recommendation (from lane state)

> **Lane deliverable COMPLETE for v34/v35 question.** TF-IDF hierarchical production modes FINALIZED and OPERATIONAL at full 173,963 decisions. Multi-level recursive protocol structurally validated but calibration FAILS on TF-IDF — valid negative preserved. Dense embedding integration contract v34 DEFINED AND FROZEN with 4 complementary views. Scale extrapolation VALIDATED at 144k checkpoint. NESTING_METRIC_DEFECT_v1 enforced. BLOCKED on legal-distance 174k dense embeddings requiring corpus lane resumption. **No further same-question cycles justified. Factory Director action: Resume corpus lane.**

---

## Evidence References

- `results/fractal_map/hierarchical_v1_174k_tfidf/` — TF-IDF hierarchical production modes at 174k
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — multi-level recursive protocol validation
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — calibration FAILURE (valid negative)
- `results/fractal_map/dense_12k_prep_validation/` — 12k dense embeddings preparatory validation (PASS)
- `results/fractal_map/144k_checkpoint_validation/` — scale extrapolation validation
- `results/fractal_map/144k_multi_level_validation/` — 144k multi-level validation
- `results/fractal_map/hierarchical_map_174k/` — 174k hierarchical map products
- `results/fractal_map/product_integration_174k/` — 16/16 scale tests PASS
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — frozen dense contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — nesting metric defect enforcement
- `reports/fractal_map/FRACTAL_MAP_V35_FINAL_AUDIT_READY_SNAPSHOT_20261010_RUN_38017982357.md`
- `reports/fractal_map/CONSTRAINED_HIERARCHICAL_174K_FULL_VALIDATION_20260926.md`
- `reports/fractal_map/SCALE_VALIDATION_EXTRAPOLATION_v28.md`

---

## Conclusion

The fractal-map lane has **successfully answered its factory direction question**. All evidence is preserved at ACCEPTED tier, negative results intact, contracts frozen. The lane is correctly **BLOCKED_ON_DEPENDENCIES** with `continue_recommended=false`.

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping, 2022–2026 parquet generation, and section extraction at 174k scale.

---
*Generated by fractal-map lane verification run 38019758055*