# FRACTAL MAP V34 — FINAL AUDIT-READY SNAPSHOT

**GitHub Run:** 37186259441  
**Timestamp:** 2026-10-04T13:30:00.000000Z  
**Factory Direction:** v34  
**Lane:** fractal-map  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Operational Resume From:** Run 37185843755 (persisted producer snapshot)

---

## EXECUTIVE SUMMARY

The fractal-map lane deliverable for factory direction v34 is **COMPLETE and AUDIT-READY**. All discriminating experiments for the v34 question have been executed, validated, and frozen. The lane is correctly `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings (which requires corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale).

**Orchestration Failure Diagnosed:** `factory_direction.json` v34 reports `fractal-map.status="RUN"` but the lane state correctly records `BLOCKED_ON_DEPENDENCIES`. This is the **same pattern as v28**. The factory direction on `main` must be updated.

---

## DELIVERABLES COMPLETED

### 1. TF-IDF Hierarchical Production Modes at 174k — OPERATIONAL
- **3 production modes** at full 173,963 decisions:
  - `full_text_tfidf_light` — fine_branch_purity 0.906
  - `regeste_full_text_hybrid_0.5` — fine_branch_purity 0.917
  - `regeste_full_text_hybrid_0.7` — fine_branch_purity 0.930
- **16/16 scale simulation tests PASS**
- **WebGL pipeline <3s** at 174k
- **Metadata artifact:** `metadata_174k_full.json` COMPLETE

### 2. Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED
- **4 TF-IDF modes** pass structural validation at 174k:
  - Perfect nesting ≥0.95 (1.0 by construction via min_cluster_size)
  - Zero fragmentation
  - Monotonic refinement
  - 39 coarse → 412 fine clusters
- **Calibration FAILS on TF-IDF** — thresholds too aggressive for signal density (negative result preserved)

### 3. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN
**Primary Product Mode (unchanged):** TF-IDF citation hybrids (jurist preference JP 0.78-0.79)

**Four Complementary Views (dense embeddings only):**

| View | Acceptance Criterion | Evidence Status |
|------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | PASSED at 22yr/144k (cp768 AUC 0.7946) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | PASSED at 22yr/144k (0.2816) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | PASSED at 22yr/144k (0.1502) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | **FAILED** (0.0941) — correctly excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | PASSED (JP 0.61-0.67, below TF-IDF baseline) |

**Required dense modes:** `center_projected_64dim`, `center_projected_128dim`, `center_projected_768dim`

### 4. Preparatory Dense Validation — COMPLETE
- **12k dense embeddings:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint (22/26 years):** fine_branch_purity ~0.97, improvement_rate 0.48-0.65 branch / 0.75-0.76 area, strict_nesting ≥0.99, fine_singletons ~4-5%

### 5. Scale Extrapolation — VALIDATED
- 144k checkpoint confirms text-based fine_branch_purity ~0.97 at scale
- Improvement rates healthy, nesting ≥0.99, fine singletons ~4-5%
- NESTING_METRIC_DEFECT_v1 enforced: all nesting_score ≥0.99 claims require explicit scope annotation

### 6. All Negative Results Preserved
- Calibration failure on TF-IDF (thresholds too aggressive)
- v26 flat Leiden failure on dense embeddings (expected)
- Erwaegungen cross-lingual failure (below threshold)
- regeste_tfidf FAIL, outcome_tfidf FAIL (weak signal / missing branch labels)

---

## TEST VERIFICATION RESULTS

All 7 test suites **PASS** (245 passed, 2 skipped):

| Test Suite | Passed | Skipped | Status |
|------------|--------|---------|--------|
| test_verify | 185 | 1 | ✅ PASS |
| test_pipeline_readiness | 14 | 0 | ✅ PASS |
| test_zoom_quality_174k_eval | 4 | 0 | ✅ PASS |
| test_zoom_quality_174k_v26_eval | 7 | 0 | ✅ PASS |
| test_12k_dense_comprehensive | 10 | 0 | ✅ PASS |
| test_dense_embeddings_infrastructure | 14 | 1 | ✅ PASS |
| test_scale_dependency | 11 | 0 | ✅ PASS |
| **TOTAL** | **245** | **2** | ✅ **ALL PASS** |

**Skipped tests (correctly reflecting upstream blocker):**
- `test_dense_embeddings_infrastructure::TestDenseEmbeddingsDataReadiness::test_dense_mode_artifacts_exist` — dense artifacts don't exist at 174k yet
- `test_verify::TestLegalDistanceScaleReadiness::test_provenance_reproduced_by_recompute` — same blocker

---

## ORCHESTRATION FAILURE DIAGNOSIS

### Factory Direction v34 Discrepancy
```json
// factory_direction.json (mounted from main) — INCORRECT
"fractal-map": {
  "status": "RUN",  // ← WRONG
  ...
}

// state/fractal_map.json — CORRECT
"cycle_status": "BLOCKED_ON_DEPENDENCIES",  // ← CORRECT
"continue_recommended": false,
```

**Root Cause:** The factory direction on `main` was not updated when the lane transitioned to `BLOCKED_ON_DEPENDENCIES` after completing all v34 discriminating experiments. This is the **same pattern as v28** where the factory direction lagged behind the actual lane state.

**Impact:** None on lane deliverable — all work is complete, validated, and frozen. The discrepancy is purely in the control plane reporting.

**Required Fix (Factory Director action on main):**
1. Update `factory_direction.json` v34: `fractal-map.status = "BLOCKED_ON_DEPENDENCIES"`
2. Resume corpus lane for data acquisition per director_note (BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale)

---

## BLOCKER STATUS (UPSTREAM)

| Blocker | Lane | Status |
|---------|------|--------|
| BGE/bger ID mapping production | corpus | REQUIRED — no mapping exists |
| Parquet generation 2022-2026 (29,520 decisions) | corpus | REQUIRED — missing from pinned snapshot |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | corpus | REQUIRED — for cross-lingual density |
| 174k dense embeddings computation | legal-distance | BLOCKED on corpus (3/26 years complete, ~11%) |

**No fractal-map lane defect exists.** All fractal-map work for v34 is complete.

---

## ACCEPTANCE CRITERIA — ALL MET

✅ TF-IDF hierarchical production modes at 174k OPERATIONAL (3 modes, 16/16 scale tests PASS)  
✅ Multi-level recursive protocol STRUCTURALLY VALIDATED at 174k (4 TF-IDF modes)  
✅ Dense embedding integration contract v34 DEFINED AND FROZEN (4 complementary views)  
✅ Preparatory 12k/144k dense validation COMPLETE  
✅ Scale extrapolation VALIDATED (144k checkpoint)  
✅ All negative results PRESERVED (calibration, v26 flat Leiden, Erwaegungen, regeste_tfidf, outcome_tfidf)  
✅ NESTING_METRIC_DEFECT_v1 ENFORCED  
✅ All validation tests PASS (245 passed, 2 correctly skipped)  
✅ Provenance INTACT, evidence REPRODUCIBLE  
✅ Lane state BLOCKED_ON_DEPENDENCIES correctly reflects upstream dependency  

---

## NEXT RECOMMENDATION

**No further same-question cycles justified.** The fractal-map lane deliverable for factory direction v34 is complete.

**Factory Director decision required:**
1. Update `factory_direction.json` on `main` to `fractal-map.status = "BLOCKED_ON_DEPENDENCIES"`
2. Resume corpus lane for data acquisition per director_note (BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale)
3. Determine successor question for fractal-map lane after dense embeddings delivery

---

## PROVENANCE

- **Accepted Run ID:** FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261004_37177664341
- **This Verification Run:** 37186259441
- **State File:** `state/fractal_map.json` (updated with this verification)
- **Dense Contract:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`
- **Test Suites:** `tests/fractal_map/` (7 suites, all passing)
- **Evidence Refs:** 35 artifacts referenced in state file

---

## AUDIT READINESS CHECKLIST

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Provenance preserved | ✅ | All result files referenced in state |
| Negative results preserved | ✅ | v26_verdict.json, flat zoom FAILs, calibration FAILs, regeste_tfidf FAIL, outcome_tfidf FAIL |
| Frozen benchmarks unchanged | ✅ | v26 frozen spec, hierarchical_v1 protocol, multi-level protocol |
| Evidence tiers accurate | ✅ | Table above — ACCEPTED, EXPLORATORY, ACCEPTED NEGATIVE correctly assigned |
| Blockers documented | ✅ | 4 specific dependencies in state + integration contract |
| Next steps unambiguous | ✅ | Await corpus lane resumption for BGE/bger mapping + parquet 2022-2026 |
| No fabricated data | ✅ | All results from actual computation |
| No overwritten claim-bearing outputs | ✅ | All historical results preserved in results/ and reports/ |
| Dense integration contract frozen | ✅ | `dense_embeddings_integration_contract_v34.json` immutable until delivery |
| Orchestration failure diagnosed | ✅ | Control plane status mismatch documented; lane correctly self-blocked |

---

## RECOMMENDATION

**BLOCKED_ON_DEPENDENCIES — continue_recommended: false**

The fractal-map lane has completed all available work for the current factory direction question. The single blocker (legal-distance 174k dense embeddings) requires upstream data acquisition resolution (corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 per factory_direction v34 director_note). No further cycles under this question are justified.

**Factory Director decision required:** Successor question (corpus lane resumption for data acquisition; FRONTIER_TEAM_REQUIRED not justified per legal-distance v34 — true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria; no ACCEPTED evidence opens a credible independent path).

---

## ARTIFACT LOCATIONS (Immutable)

| Artifact | Path |
|----------|------|
| Hierarchical_v1 174k verdict | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` |
| Frozen spec | `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json` |
| Multi-level protocol (4 modes) | `results/fractal_map/multi_level_protocol_174k_tfidf/` |
| 12k dense validation | `results/fractal_map/12k_dense_comprehensive/` |
| 144k checkpoint | `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json` |
| NESTING_METRIC_DEFECT_v1 audit | `results/fractal_map/nesting_metric_defect_v1_audit.json` |
| Calibration results | `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` |
| Dense integration contract | `results/fractal_map/dense_embeddings_integration_contract_v34.json` |
| State file | `state/fractal_map.json` |

---

## SIGN-OFF

**Lane:** fractal-map  
**Factory Direction:** v34  
**Verification:** All 245/247 tests PASS (2 correctly SKIPPED)  
**Deliverable:** COMPLETE for current question  
**Blocker:** Upstream data dependency (BGE/bger ID mapping + parquet 2022-2026)  
**Orchestration Failure:** factory_direction.json status="RUN" should be "BLOCKED_ON_DEPENDENCIES"  
**Audit Readiness:** CONFIRMED — all evidence preserved, negative results maintained, provenance intact, tests passing, lane deliverable complete

*This report is the final verification artifact for fractal-map lane under factory direction v34. Lane deliverable complete; awaiting Factory Director decision on successor question.*