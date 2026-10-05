# FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261005_RUN_37321604475

**Run ID:** 37321604475  
**Timestamp:** 2026-10-05T23:59:59.000000Z  
**Factory Direction Version:** 34  
**Lane:** fractal-map  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  

---

## Executive Summary

This run performs an independent re-verification of the fractal-map lane state for factory direction v34. All discriminating experiments for the current lane question are **COMPLETE**. The lane is correctly **BLOCKED_ON_DEPENDENCIES** on upstream legal-distance 174k dense embeddings delivery. No further same-question cycles are justified (`continue_recommended=false`).

**Verdict:** TF-IDF hierarchical production modes are **OPERATIONAL** at full 174k scale. Dense embedding integration contract v34 is **DEFINED AND FROZEN**. All evidence preserved, negative results intact.

---

## Verification Results

### Test Suite Execution
- **Total test suites:** 7
- **Total tests:** 247
- **Passed:** 245
- **Skipped:** 2 (dense embedding artifacts not yet delivered — expected)
- **Failed:** 0

| Test Suite | Total | Passed | Skipped |
|------------|-------|--------|---------|
| test_12k_dense_comprehensive.py | 10 | 10 | 0 |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 |
| test_pipeline_readiness.py | 14 | 14 | 0 |
| test_scale_dependency.py | 11 | 11 | 0 |
| test_verify.py | 186 | 185 | 1 |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 |
| **Grand Total** | **247** | **245** | **2** |

All tests pass. The 2 skipped tests are correctly gated on dense embedding delivery (upstream blocker).

---

## Confirmed Findings (from factory direction v34)

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
**3 production modes at full 173,963 decisions:**

| Mode | Fine Branch Purity | Coarse Clusters | Fine Clusters | Verdict |
|------|-------------------|-----------------|---------------|---------|
| `full_text_tfidf_light` | 0.930 | 19 | 365 | **PASS** |
| `regeste_full_text_hybrid_0.5` | 0.906 | 31 | 285 | **PASS** |
| `regeste_full_text_hybrid_0.7` | 0.910 | 31 | 285 | **PASS** |

- Zero fragmentation (singleton_fraction = 0.0)
- Perfect nesting (1.0 by construction)
- Monotonic refinement (branch_purity_delta > 0, area_purity_delta > 0)
- Zoom coherence improvement_rate > 0.7
- Legal structure: fine_purity > 2× random baseline
- WebGL pipeline: <3s at 174k
- **16/16 scale simulation tests PASS**

### 2. Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k for ALL TF-IDF modes
- Level 0 (root): single cluster (expected)
- Levels 1-3: multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15)
- **This is a valid negative result — correctly preserved**
- Do not conflate with hierarchical_v1 (2-level) production protocol which PASSES for 3 text-based modes

### 3. Calibration — FAILS on TF-IDF
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- **Negative result correctly recorded**

### 4. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with frozen acceptance criteria:

| Complementary View | Acceptance Criterion | Status |
|-------------------|---------------------|--------|
| Citation Heritage | AUC > 0.75 (vs TF-IDF 0.71-0.74) | PASSED at 22-year/144k |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.20 | PASSED at 22-year/144k |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.10 | PASSED at 22-year/144k |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch > 0.10 | **FAILED** (0.094) — excluded |
| Linear Hybrid Complement | PASS both adversarial gates at w=0.3-0.4 | PASSED at 22-year/144k (JP 0.61-0.67, below TF-IDF 0.78-0.79) |

**Note:** Dense embeddings are COMPLEMENTARY views only. TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78-0.79 vs dense JP 0.05-0.43).

### 5. Preparatory Dense Validation — COMPLETE
- 12k dense: multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation)
- 12k dense: hierarchical builder SUCCESS (39 coarse → 412 fine)
- Frozen v26 flat Leiden: FAIL (expected)
- 144k checkpoint (22/26 years, 2000-2021): hierarchical builder validates scale extrapolation
  - Fine branch purity ~0.97
  - Improvement rate 0.48-0.65 branch / 0.75-0.76 area
  - Strict nesting ≥0.99
  - Fine singletons ~4-5%

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had nesting_score ≥ 0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs

---

## Blockers (Upstream — Not Lane Defects)

| Blocker | Owner | Status |
|---------|-------|--------|
| BGE/bger ID mapping production | Corpus lane | REQUIRED (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs) |
| Parquet generation 2022-2026 | Corpus lane | REQUIRED (29,520 decisions missing from pinned 2026 snapshot) |
| Section extraction at 174k scale | Corpus lane | REQUIRED (for cross-lingual evaluation density) |
| 174k dense embeddings computation | Legal-distance lane | 3/26 years complete (~19,441 decisions, 11%) |

---

## Control Plane Discrepancy Note

**Persistent V28-pattern defect:** The mounted control plane at `/tmp/lex_control/state/factory_direction.json` shows `fractal-map.status="RUN"` (line 16) while:
- Workspace `state/factory_direction.json` correctly shows `BLOCKED_ON_DEPENDENCIES`
- Lane `state/fractal_map.json` correctly shows `BLOCKED_ON_DEPENDENCIES`
- All prior audit reports confirm `BLOCKED_ON_DEPENDENCIES`

This is a **PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism**, NOT a lane failure. The lane state is AUTHORITATIVE and CORRECT.

---

## Recommendation

**continue_recommended = false**

No further same-question cycles justified. All discriminating experiments for factory direction v34 question COMPLETE.

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022-2026 (29,520 decisions)
3. Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

Once corpus lane delivers, legal-distance lane can compute 174k dense embeddings, unblocking fractal-map multi-view deployment per the frozen integration contract.

---

## Artifacts Referenced

- `state/fractal_map.json` — Authoritative lane state (updated with this run)
- `results/fractal_map/hierarchical_v1_174k_tfidf/` — TF-IDF 174k hierarchical_v1 results
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen integration contract
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json` — 144k scale extrapolation
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — Nesting defect enforcement
- `reports/fractal_map/FRACTAL_MAP_V34_DELIVERABLE_COMPLETE_CONFIRMATION_20261005_FINAL.md` — Deliverable confirmation

---

*Generated by independent verification run 37321604475*