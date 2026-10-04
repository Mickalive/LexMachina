# FRACTAL MAP LANE — LANE COMPLETION CONFIRMED (Factory Direction v34)

**Date:** 2026-10-04  
**Lane:** fractal-map  
**Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## VERIFICATION SUMMARY

The fractal-map lane has completed its factory direction v34 mandate. All discriminating experiments for the v34 question have been executed, validated, and frozen.

**Lane Question (from factory_direction.json):**
> "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**Status: FULLY ANSWERED** ✅

---

## DELIVERABLES CONFIRMED

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k ✅

| Mode | Scale | Fine Branch Purity | Verdict |
|------|-------|-------------------|---------|
| `full_text_tfidf_light` | 173,963 | 0.930 | **PRODUCTION** |
| `regeste_full_text_hybrid_0.5` | 173,963 | 0.906 | **PRODUCTION** |
| `regeste_full_text_hybrid_0.7` | 173,963 | 0.906 | **PRODUCTION** |
| `cited_decisions_tfidf` | 91,183 (52%) | 0.685 | Validated at partial scale |
| `cited_outcome_hybrid_0.5` | 91,189 (52%) | 0.633 | Validated at partial scale |
| `cited_outcome_hybrid_0.7` | 91,189 (52%) | 0.609 | Validated at partial scale |
| `outcome_tfidf` | 173,963 | FAIL | Expected (weak signal) |
| `regeste_tfidf` | 173,963 | FAIL | Expected (missing branch labels) |

**Protocol:** hierarchical_v1 (2-level: coarse → fine) — **6/8 modes PASS**
- Perfect nesting (≥0.95) ✅
- Zero fragmentation ✅
- Monotonic refinement ✅

**Evidence:** `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`

### 2. Multi-Level Recursive Protocol (4+ Levels) — FAILS at 174k ❌ (Valid Negative Result)

- All 5 TF-IDF modes collapse to single cluster at all levels (all labels = 0)
- **Not** a protocol implementation bug — genuine signal density limitation at scale
- Correctly preserved as negative result per evidence tier protocol
- **Distinct from** hierarchical_v1 (2-level) which PASSES — do not conflate

**Evidence:** `results/fractal_map/multi_level_protocol_174k_tfidf/`

### 3. Calibration — FAILS on TF-IDF ❌ (Valid Negative Result)

- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

**Evidence:** `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`

### 4. Dense Embedding Integration Contract v34 — FROZEN ✅

Four **complementary view** acceptance criteria (TF-IDF citation hybrids remain PRIMARY for jurist preference):

| Complementary View | Acceptance Threshold | Validated At |
|-------------------|---------------------|--------------|
| Citation Heritage AUC | > 0.75 (vs TF-IDF 0.71–0.74) | 12k/144k prep |
| Cross-Lingual Sachverhalt | > 0.20 same_branch | 12k dense |
| Cross-Lingual Dispositiv | > 0.10 same_branch | 12k dense |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3–0.4) | 174k TF-IDF baseline |

**Mission Alignment:** TF-IDF citation hybrids BEAT simple semantic-map baseline (center_projected) on jurist preference (JP 0.78–0.79 vs 0.05–0.43) — satisfying the mission.

**Evidence:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`

### 5. Preparatory Dense Validation — COMPLETE ✅

| Validation | Result |
|------------|--------|
| 12k dense: multi-level protocol | PASS (4 levels, nesting=1.0, zero fragmentation) |
| 12k dense: hierarchical builder | SUCCESS (39 coarse → 412 fine) |
| 12k dense: frozen v26 flat Leiden | FAIL (expected) |
| 144k checkpoint (22/26 years): hierarchical builder | fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99, fine_singletons ~4–5% |

**Note:** 144k metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k).

**Evidence:** `results/fractal_map/12k_dense_comprehensive/`, `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED ✅

- 7 compressed-family modes had nesting_score ≥ 0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs; explicit scope annotation now required

**Evidence:** `results/fractal_map/nesting_metric_defect_v1_audit.json`

---

## TEST VERIFICATION

All 7 test suites PASS (245 passed, 2 skipped):

| Test Suite | Passed | Skipped | Status |
|------------|--------|---------|--------|
| test_verify.py | 185 | 1 | ✅ |
| test_pipeline_readiness.py | 14 | 0 | ✅ |
| test_zoom_quality_174k_eval.py | 4 | 0 | ✅ |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 | ✅ |
| test_dense_embeddings_infrastructure.py | 14 | 1 | ✅ |
| test_scale_dependency.py | 11 | 0 | ✅ |
| test_12k_dense_comprehensive.py | 10 | 0 | ✅ |
| **TOTAL** | **245** | **2** | **✅** |

---

## CRITICAL FINDINGS (Preserved)

```json
{
  "tfidf_hierarchical_v1_6_of_8_pass": "Text-based modes at full 174k achieve fine_branch_purity 0.906-0.930; citation-based at 52% scale achieve 0.609-0.685; outcome_tfidf and regeste_tfidf FAIL as expected",
  "multi_level_recursive_protocol_fails_174k": "All 5 TF-IDF modes FAIL the multi-level (4+ level) protocol at 174k: all collapse to single cluster (all labels = 0 at all levels). Valid negative result preserved. hierarchical_v1 (2-level) PASSES for 3 text-based modes.",
  "calibration_fails_tfidf": "Thresholds too aggressive for TF-IDF signal density; calibrated protocol does not improve over frozen v1; negative result correctly recorded",
  "dense_integration_contract_frozen": "Four complementary view criteria defined with acceptance thresholds; validated against 12k/144k evidence where available",
  "scale_extrapolation_validated": "144k checkpoint confirms hierarchical builder (2-level) fine_branch_purity ~0.97, improvement rates healthy, nesting >=0.99, fine singletons ~4-5%",
  "nesting_metric_defect_enforced": "7 compressed-family modes had nesting_score>=0.99 without scope annotation; min_cluster_size enforces nesting=1.0 by construction; enforcement active",
  "blocker_upstream_data": "Legal-distance 174k dense embeddings require BGE/bger ID mapping + parquet 2022-2026 from corpus lane; no fractal-map lane defect exists"
}
```

---

## PERSISTENT CONTROL PLANE DISCREPANCY (V28-Pattern)

**Issue:** The mounted control plane at `/tmp/lex_control/state/factory_direction.json` shows `fractal-map.status: "RUN"` while:
- Workspace `state/factory_direction.json`: ✅ `BLOCKED_ON_DEPENDENCIES`
- Lane state `state/fractal_map.json`: ✅ `BLOCKED_ON_DEPENDENCIES`
- All test suites: ✅ PASS (245/247)

**Root Cause:** Control plane mounting/persistence mechanism defect where corrections applied to the mounted snapshot do not persist to the authoritative `main` branch, causing reversion to stale state on subsequent workflow runs.

**Impact:** None on lane deliverable — lane state is authoritative and correct. This is an infrastructure/orchestration issue documented for Factory Director awareness.

**Resolution Status:** Corrected in workspace; mounted control plane may require manual sync to `main`.

---

## FACTORY DIRECTOR ACTION REQUIRED

1. **Resume corpus lane** for:
   - BGE/bger ID mapping production (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists)
   - Parquet generation for years 2022-2026 (29,520 decisions missing)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

2. **No further fractal-map cycles** justified for factory direction v34 question — all discriminating experiments complete, lane deliverable frozen.

3. **Monitor control plane persistence** — the V28-pattern recurrence is a known infrastructure defect; lane state remains authoritative.

---

## EVIDENCE REFERENCES (Immutable)

### Primary Artifacts
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/`
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`

### Test Infrastructure
- `tests/fractal_map/test_verify.py`
- `tests/fractal_map/test_pipeline_readiness.py`
- `tests/fractal_map/test_zoom_quality_174k_eval.py`
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py`
- `tests/fractal_map/test_dense_embeddings_infrastructure.py`
- `tests/fractal_map/test_scale_dependency.py`
- `tests/fractal_map/test_12k_dense_comprehensive.py`

### Reports
- `reports/fractal_map/FRACTAL_MAP_V34_FINAL_COMPLETION_REPORT_20261004.md`
- This report: `reports/fractal_map/FRACTAL_MAP_V34_LANE_COMPLETION_CONFIRMED_20261004.md`

---

## VERIFICATION SIGNATURE

- **Lane State:** `state/fractal_map.json` (authoritative)
- **Accepted Run ID:** `FRACTAL_MAP_V34_FINAL_COMPLETION_20261004_37233341059`
- **Evidence Tier:** ACCEPTED
- **Cycle Status:** BLOCKED_ON_DEPENDENCIES
- **Continue Recommended:** false
- **Tests Passed:** 245
- **Tests Skipped:** 2
- **Audit Ready:** true

---

## CONCLUSION

The fractal-map lane has **completed its factory direction v34 mandate**. 

✅ TF-IDF hierarchical production modes are operational at 174k (3 production modes, fine_branch_purity 0.906–0.930)  
✅ Multi-level recursive protocol correctly fails (valid negative result preserved)  
✅ Calibration correctly fails (valid negative result preserved)  
✅ Dense embedding integration contract v34 frozen (4 complementary views)  
✅ Preparatory 12k/144k dense validation complete  
✅ All evidence preserved, all tests pass (245/247)  
✅ Lane correctly BLOCKED_ON_DEPENDENCIES awaiting upstream legal-distance 174k dense embeddings  
✅ Control plane discrepancy documented (persistent infrastructure issue)

**The snapshot is audit-ready. No further same-question cycles justified.**