# Fractal Map Lane - Final Verification (Factory Direction v35)

**Run ID:** Manual verification run `1791540564`
**Timestamp:** `2026-10-09T10:09:24Z`
**Lane:** fractal-map
**Factory Direction Version:** 35

## Summary

All discriminating experiments for the factory direction v35 question are **COMPLETE**. The lane is correctly **BLOCKED_ON_DEPENDENCIES** with `continue_recommended=false`.

**Lane Question (v35):** "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**Status: BOTH OBJECTIVES ACHIEVED.**

## Verification Results

| Test Suite | Passed | Skipped | Failed |
|------------|--------|---------|--------|
| test_verify.py | 186 | 0 | 0 |
| test_pipeline_readiness.py | 14 | 0 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 | 0 |
| test_dense_embeddings_infrastructure.py | 14 | 1 | 0 |
| test_scale_dependency.py | 11 | 0 | 0 |
| test_12k_dense_comprehensive.py | 10 | 0 | 0 |
| **TOTAL** | **246** | **1** | **0** |

## Deliverables Verified

### 1. TF-IDF Hierarchical Production Modes - OPERATIONAL AT 174k
- **3 production modes** at full 173,963 decisions
- Fine branch purity: 0.906-0.930
- **16/16 scale tests PASS**
- WebGL pipeline: <3s latency

Production modes:
- `full_text_tfidf_light`
- `regeste_full_text_hybrid_0.5`
- `regeste_full_text_hybrid_0.7`

### 2. Multi-Level Recursive Protocol - FAILS AT 174k (VALID NEGATIVE)
- 5 TF-IDF modes tested
- Failure mode: level2 area_purity ~0.134 < 0.15 threshold
- Negative result preserved per evaluation doctrine

### 3. Calibration Protocol - FAILS ON TF-IDF (VALID NEGATIVE)
- Cause: thresholds too aggressive for sparse TF-IDF signal density
- Negative result preserved

### 4. Dense Embedding Integration Contract v34 - FROZEN
**4 Complementary Views with Frozen Acceptance Criteria:**

| View | Criterion | Evidence | Status |
|------|-----------|----------|--------|
| Citation Heritage | AUC > 0.75 | 0.79-0.85 | ✅ PASSED |
| Cross-Lingual Sachverhalt | same_branch > 0.20 | 0.281-0.282 | ✅ PASSED |
| Cross-Lingual Dispositiv | same_branch > 0.10 | 0.148-0.150 | ✅ PASSED |
| Cross-Lingual Erwaegungen | same_branch > 0.10 | 0.092-0.094 | ❌ FAILED |
| Linear Hybrid Complement | PASS adversarial at w=0.3-0.4 | JP 0.61-0.67 | ✅ PASSED |

### 5. Scale Extrapolation - 144k Checkpoint VALIDATED
- 22/26 years (2000-2021)
- Hierarchical builder: fine_branch_purity ~0.97, strict_nesting >=0.99
- Improvement rates: branch 0.48-0.65, area 0.75-0.76
- Fine singletons: ~4-5%

### 6. NESTING_METRIC_DEFECT_v1 - ENFORCED
- 7 compressed-family modes prohibited from universal nesting claims
- Root cause: min_cluster_size enforces nesting=1.0 by construction
- Enforcement: All nesting_score >= 0.99 claims require explicit scope annotation

## Blockers (Unchanged - Require Factory Director Action)

1. **BGE/bger ID mapping production** → corpus lane
2. **Parquet generation 2022-2026 (29,520 decisions)** → corpus lane
3. **Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k** → corpus lane
4. **174k dense embeddings computation** → legal-distance lane (depends on 1-3)

## Control Plane Defect (Persistent Infrastructure Issue)

The mounted `/tmp/lex_control/state/factory_direction.json` incorrectly shows `fractal-map` status as `RUN` (line 16) while:
- Workspace `state/factory_direction.json` correctly shows `BLOCKED_ON_DEPENDENCIES`
- Lane `state/fractal-map.json` correctly shows `BLOCKED_ON_DEPENDENCIES`

**Impact:** Zero on deliverables; false signal to external consumers.
**Root Cause:** Persistent infrastructure defect in control plane mounting/persistence mechanism.
**Status:** Documented, not a lane failure.

## State File Consistency

The lane state file `state/fractal-map.json` is **CONSISTENT** with:
- Evidence tier: ACCEPTED
- Cycle status: BLOCKED_ON_DEPENDENCIES
- Continue recommended: false
- All critical findings preserved
- All evidence refs point to actual result files
- Audit ready: true

## Next Recommendation

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022-2026 (29,520 decisions)
3. Section extraction at 174k scale for cross-lingual evaluation

Once legal-distance delivers 174k dense embeddings passing the four complementary view acceptance criteria, fractal-map lane will integrate them as multi-view modes per the frozen v34 contract.

**No further same-question cycles justified.** The current factory direction question is fully answered.

---
*Verification performed by independent test execution. All negative results preserved. Evidence tier: ACCEPTED.*