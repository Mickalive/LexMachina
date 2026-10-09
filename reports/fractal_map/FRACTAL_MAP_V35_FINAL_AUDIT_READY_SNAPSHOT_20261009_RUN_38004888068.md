# Fractal Map Lane — Final Audit-Ready Snapshot (Factory Direction v35)

**Run ID:** 38004888068  
**Timestamp:** 2026-10-09T23:45:00Z  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Audit Ready:** true  

---

## Executive Summary

The fractal-map lane deliverable for factory direction v35 is **COMPLETE, VERIFIED, AND AUDIT-READY**. All discriminating experiments for the v34/v35 question have been executed and validated. The lane is correctly **BLOCKED_ON_DEPENDENCIES** on upstream legal-distance 174k dense embeddings, which require corpus lane resumption.

### Key Deliverables Finalized

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| TF-IDF hierarchical production modes (3 modes at 173,963 decisions) | **OPERATIONAL** | fine_branch_purity 0.906–0.930; 16/16 scale tests PASS; WebGL <3s |
| Multi-level recursive protocol (4 levels) | **STRUCTURALLY VALIDATED** | perfect nesting ≥0.95, zero fragmentation, monotonic refinement |
| Calibration on TF-IDF | **FAILS (valid negative)** | thresholds too aggressive for signal density at 174k |
| Dense embedding integration contract v34 | **FROZEN** | 4 complementary views with specific acceptance criteria |
| Scale extrapolation | **VALIDATED at 144k** | fine_branch_purity ~0.97, strict_nesting ≥0.99 |
| NESTING_METRIC_DEFECT_v1 | **ENFORCED** | strict parent-child label matching replaces lenient definition |

---

## Test Verification Results

**Fresh Independent Re-verification (clean environment, fresh dependency install):**

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 185 | 1 | 0 |
| test_pipeline_readiness.py | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | 0 |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | 0 |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | 0 |
| test_scale_dependency.py | 11 | 11 | 0 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** | **0** |

All test suites PASS. Zero failures.

---

## Critical Findings (Preserved)

1. **TF-IDF hierarchical_v1 protocol: 6/8 PASS at 174k** — 3 text-based modes at full 173,963 (fine_branch_purity 0.906–0.930); 3 citation-based at 52% scale (0.609–0.685). All 6 exceed 0.5 threshold.

2. **Multi-level recursive protocol structurally VALIDATED at 174k** — perfect nesting ≥0.95, zero fragmentation, monotonic refinement. **Calibration FAILS** on TF-IDF (thresholds too aggressive for signal density) — valid negative preserved.

3. **Calibration FAILS on TF-IDF at 174k** — valid negative result preserved; adaptive thresholding needed for production.

4. **Dense embedding integration contract v34 FROZEN** — 4 complementary views with specific acceptance criteria:
   - Citation Heritage: AUC > 0.75
   - Cross-Lingual Sachverhalt: same-branch > 0.20
   - Cross-Lingual Dispositiv: same-branch > 0.10
   - Linear Hybrid Complement: PASS adversarial gates

5. **Scale extrapolation VALIDATED at 144k checkpoint** (22/26 years, 2000–2021): fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99, fine_singletons ~4–5%.

6. **NESTING_METRIC_DEFECT_v1 ENFORCED** — strict definition: fine label's parent must equal coarse label for that decision; previous lenient "any parent has child" inflated scores.

7. **BLOCKER: upstream legal-distance 174k dense embeddings** require corpus lane resumption:
   - (a) BGE/bger ID mapping production
   - (b) Parquet generation 2022–2026 (29,520 decisions missing)
   - (c) Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

8. **Dense embeddings FAIL jurist preference at ALL scales** (JP 0.05–0.43); TF-IDF citation hybrids DOMINATE (JP 0.78–0.79) and PASS both adversarial gates at 174k.

9. **Dense embeddings EXCEL at complementary capabilities**: citation heritage recovery (AUC 0.79–0.85 > TF-IDF 0.71–0.74) and section cross-lingual alignment (sachverhalt gap 0.187 vs 0.452).

10. **True OOS JuristPref ceiling ~0.53 < 0.7 factory target** — falsifies original dense-beats-TF-IDF hypothesis.

11. **v18 coarse hierarchy NEGATIVE** (4-label branch max purity 0.65 < 0.7).

12. **V28-pattern control plane mounting defect PERSISTS** in `/tmp/lex_control/state/factory_direction.json` (shows RUN at line 16) while workspace state/factory_direction.json and lane state correctly show BLOCKED_ON_DEPENDENCIES. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in control plane mounting/persistence, NOT a lane failure. Zero impact on deliverables.

---

## Evidence References

- `results/fractal_map/hierarchical_v1_174k_tfidf/` — TF-IDF hierarchical production modes at 174k
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — Multi-level recursive protocol validation
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — Calibration FAILURE (valid negative)
- `results/fractal_map/dense_12k_prep_validation/` — 12k dense embeddings preparatory validation (PASS)
- `results/fractal_map/144k_checkpoint_validation/` — Scale extrapolation validation
- `results/fractal_map/144k_multi_level_validation/` — 144k multi-level validation
- `results/fractal_map/hierarchical_map_174k/` — 174k hierarchical map products
- `results/fractal_map/product_integration_174k/` — 16/16 scale tests PASS
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen dense contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — Nesting metric defect enforcement
- `reports/fractal_map/FRACTAL_MAP_V35_FINAL_AUDIT_READY_SNAPSHOT_20261009_RUN_37940877297.md`
- `reports/fractal_map/CONSTRAINED_HIERARCHICAL_174K_FULL_VALIDATION_20260926.md`
- `reports/fractal_map/SCALE_VALIDATION_EXTRAPOLATION_v28.md`

---

## Next Recommendation

**Lane deliverable COMPLETE for v34/v35 question.** No further same-question cycles justified.

- TF-IDF hierarchical production modes (cited_decisions_tfidf, cited_decisions_tfidf_outcome_hybrid_0.5, cited_decisions_tfidf_outcome_hybrid_0.7) FINALIZED and OPERATIONAL at full 173,963 decisions.
- Multi-level recursive protocol structurally validated; calibration FAILS on TF-IDF — valid negative preserved.
- Dense embedding integration contract v34 DEFINED AND FROZEN with 4 complementary views.
- Scale extrapolation VALIDATED at 144k checkpoint.
- NESTING_METRIC_DEFECT_v1 enforced.
- **BLOCKED** on legal-distance 174k dense embeddings requiring corpus lane resumption.

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping, 2022–2026 parquet (29,520 decisions), section extraction at 174k scale. Blocker: upstream dense embeddings at 174k depend on corpus data.

---

## Orchestration/Validation Failure Diagnosis

**Diagnosis:** No orchestration/validation failure in fractal-map lane.

The V28-pattern control plane mounting defect **PERSISTS** in `/tmp/lex_control/state/factory_direction.json` (shows `fractal-map.status = "RUN"` at line 16) while:
- Workspace `state/factory_direction.json` correctly shows `BLOCKED_ON_DEPENDENCIES`
- Lane `state/fractal_map.json` correctly shows `cycle_status: "BLOCKED_ON_DEPENDENCIES"`

This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, NOT a lane failure. The lane has correctly been BLOCKED_ON_DEPENDENCIES since v34. All deliverables are complete, verified, and audit-ready.

---

**Signed:** Fractal Map Lane — Final Audit-Ready Snapshot  
**Run:** 38004888068  
**Factory Direction:** v35
