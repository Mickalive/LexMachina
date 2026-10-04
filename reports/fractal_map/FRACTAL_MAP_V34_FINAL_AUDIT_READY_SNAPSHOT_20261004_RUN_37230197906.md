# FRACTAL MAP V34 — FINAL AUDIT-READY SNAPSHOT
**GitHub Run:** 37230197906 | **Date:** 2026-10-04 | **Lane:** fractal-map | **Direction Version:** 34

---

## EXECUTIVE SUMMARY

The fractal-map lane deliverable for factory direction v34 is **COMPLETE, VERIFIED, AND AUDIT-READY**.

- **Lane Status:** `BLOCKED_ON_DEPENDENCIES` (correctly set in lane state)
- **Evidence Tier:** `ACCEPTED`
- **Cycle Status:** All discriminating experiments complete; no further same-question cycles justified
- **Test Verification:** 7/7 test suites PASS (245 passed, 2 skipped)
- **Control Plane Discrepancy:** `factory_direction.json` on control plane (`/tmp/lex_control`) still shows `fractal-map.status="RUN"` — lane state correctly shows `BLOCKED_ON_DEPENDENCIES`. This is a known recurring orchestration discrepancy (same pattern as v28).

---

## DELIVERABLES COMPLETED

### 1. TF-IDF Hierarchical Production Modes at 174k — OPERATIONAL (ACCEPTED)

| Mode | Scale | Fine Branch Purity | Status |
|------|-------|-------------------|--------|
| `full_text_tfidf_light` | 173,963 | 0.930 | PRODUCTION |
| `regeste_full_text_hybrid_0.5` | 173,963 | 0.906 | PRODUCTION |
| `regeste_full_text_hybrid_0.7` | 173,963 | 0.921 | PRODUCTION |
| `cited_decisions_tfidf` | 90,671 (52%) | 0.685 | PRODUCTION (partial scale) |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 90,671 (52%) | 0.609 | PRODUCTION (partial scale) |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 90,671 (52%) | 0.642 | PRODUCTION (partial scale) |

- **Hierarchical v1 protocol:** 6/8 modes PASS at their respective scales
- **Product integration:** 16/16 scale simulation tests PASS, 50+ endpoints, WebGL <3s
- **Frozen spec:** `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`

### 2. Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k (VALID NEGATIVE RESULT)

- All 5 TF-IDF modes FAIL the multi-level protocol at full 174k scale
- Root cause: Level 2 `area_purity` threshold (~0.134 < 0.15), NOT cluster collapse
- Level 0 (root) = single cluster; Levels 1-3 = multiple clusters
- **Correctly preserved as negative result** — do not conflate with hierarchical_v1 (2-level) which PASSES

### 3. Calibration — FAILS on TF-IDF (VALID NEGATIVE RESULT)

- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- **Correctly preserved as negative result**

### 4. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN (ACCEPTED)

| Complementary View | Acceptance Threshold | Current Evidence |
|-------------------|---------------------|------------------|
| Citation Heritage AUC | > 0.75 | 12k: 0.79-0.85 ✓ (vs TF-IDF 0.71-0.74) |
| Cross-Lingual Sachverhalt | > 0.20 | 12k: 0.187 gap (needs 174k validation) |
| Cross-Lingual Dispositiv | > 0.10 | 12k: 0.452 gap (needs 174k validation) |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3-0.4) | 12k: PASS at optimal weight |

- **Contract artifact:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`
- These are **COMPLEMENTARY views only** — TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78-0.79 vs dense JP 0.05-0.43)

### 5. Preparatory Dense Validation — COMPLETE (ACCEPTED)

- **12k dense embeddings:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint (22/26 years, 2000-2021):** Hierarchical builder (2-level) scale extrapolation validated — fine_branch_purity ~0.97, improvement_rate 0.48-0.65 branch / 0.75-0.76 area, strict_nesting >=0.99, fine_singletons ~4-5%
- **Note:** 144k metrics describe hierarchical builder (2-level), NOT multi-level recursive protocol (which FAILS at 144k)

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED

- 7 compressed-family modes had `nesting_score >= 0.99` without scope annotation
- `min_cluster_size` enforces nesting=1.0 by construction
- Enforcement active for all outputs

---

## BLOCKER (UPSTREAM DEPENDENCY)

**Legal-distance 174k dense embeddings** required for multi-view deployment.

**Root cause (corpus lane):**
1. **BGE/bger ID mapping** — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists
2. **Parquet generation for years 2022-2026** — 29,520 decisions missing
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

**No fractal-map lane defect exists.** Factory Director action required to resume corpus lane.

---

## TEST VERIFICATION (Run 37230197906)

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

## EVIDENCE REFERENCES (Machine-Readable)

```
results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json
results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json
results/fractal_map/multi_level_protocol_174k_tfidf/
results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/
results/fractal_map/12k_dense_comprehensive/
results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json
results/fractal_map/nesting_metric_defect_v1_audit.json
results/fractal_map/dense_embeddings_integration_contract_v34.json
```

---

## STATE FILE (Updated)

The lane state file `/home/runner/work/LexMachina/LexMachina/state/fractal-map.json` has been updated with this verification run:

```json
{
  "verification_run_id": "fractal_map_v34_final_audit_20261004_37230197906",
  "verification_timestamp": "2026-10-04T23:59:59.000000Z",
  "verification_tests_passed": 245,
  "verification_tests_skipped": 2,
  "github_run": 37230197906,
  "final_audit_run_id": "FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261004_37230197906",
  "final_audit_timestamp": "2026-10-04T23:59:59.000000Z",
  "final_audit_report": "reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261004_RUN_37230197906.md"
}
```

---

## FACTORY DIRECTOR ACTION REQUIRED

1. **Update control plane** (`main` branch): Set `fractal-map.status = "BLOCKED_ON_DEPENDENCIES"` in `state/factory_direction.json` (resolves recurring orchestration discrepancy)
2. **Resume corpus lane** for: BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale

---

## AUDIT TRAIL

This is the final audit-ready snapshot for factory direction v34, GitHub run 37230197906. All prior operational resumes (v87 through v100) are preserved in the lane state file. No claim-bearing outputs have been overwritten. Negative results (multi-level protocol failure, calibration failure) are correctly preserved as first-class evidence.