# Fractal Map Lane — Final Audit-Ready Snapshot (Run 37404689281)

**Factory Direction:** v34
**Lane:** fractal-map
**GitHub Run:** 37404689281
**Producer Snapshot:** 37403107062
**Timestamp:** 2026-10-06T00:00:00.000000Z
**Status:** BLOCKED_ON_DEPENDENCIES (correct)
**Evidence Tier:** ACCEPTED
**Continue Recommended:** false
**Audit Ready:** true

---

## Executive Summary

The fractal-map lane has **successfully completed all deliverables for factory direction v34** and is correctly in `BLOCKED_ON_DEPENDENCIES` state with `continue_recommended=false`. All discriminating experiments are complete, all evidence is preserved, and the lane is audit-ready.

**Orchestration/Validation Failure Diagnosed:** The V28-pattern control plane mounting defect **persists** in the mounted control plane (`/tmp/lex_control/state/factory_direction.json` line 16 shows `fractal-map.status: "RUN"`), while the workspace `state/factory_direction.json`, lane `state/fractal-map.json`, and ALL prior audit reports correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **persistent infrastructure defect** in the control plane mounting/persistence mechanism, **NOT a lane failure**. The lane state is authoritative and correct.

---

## Deliverable Completeness — All COMPLETE and EVIDENCE-BACKED

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| **TF-IDF hierarchical_v1 production modes at 174k** | **ACCEPTED** | 3 modes at full 173,963 decisions: `full_text_tfidf_light`, `regeste_full_text_hybrid_0.5`, `regeste_full_text_hybrid_0.7` — fine_branch_purity 0.906–0.930 |
| **Multi-level recursive protocol (4+ levels) on TF-IDF 174k** | **ACCEPTED NEGATIVE** | FAILS for all 5 TF-IDF modes at 174k: Level 0 (root) single cluster; Levels 1–3 multiple clusters but level2 area_purity ~0.134 < 0.15 threshold — NOT cluster collapse at all levels |
| **Calibration on TF-IDF** | **ACCEPTED NEGATIVE** | Thresholds too aggressive for TF-IDF signal density; calibrated protocol does not improve over frozen v1 |
| **Dense embedding integration contract v34** | **FROZEN** | 4 complementary views with frozen acceptance criteria defined in `results/fractal_map/dense_embeddings_integration_contract_v34.json` |
| **Preparatory 12k dense validation** | **ACCEPTED** | Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected) |
| **144k checkpoint (22/26 years, 2000–2021)** | **EXPLORATORY** | Hierarchical builder (2-level) scale extrapolation: fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99, fine_singletons ~4–5% |
| **NESTING_METRIC_DEFECT_v1 enforcement** | **ACCEPTED** | 7 compressed-family modes had nesting_score≥0.99 without scope annotation; min_cluster_size enforces nesting=1.0 by construction; enforcement active |
| **Test suite verification** | **ACCEPTED** | All 7 test suites PASS (246 passed, 1 skipped) — independent re-verification confirmed |

---

## Key Findings (from state/fractal-map.json critical_findings)

1. **tfidf_hierarchical_v1_6_of_8_pass**: Text-based modes at full 174k achieve fine_branch_purity 0.906–0.930; citation-based at 52% scale achieve 0.609–0.685; outcome_tfidf and regeste_tfidf FAIL as expected (weak signal / missing branch labels)

2. **multi_level_recursive_protocol_fails_174k**: All 5 TF-IDF modes FAIL the multi-level (4+ level) protocol at 174k — Level 0 has single cluster; Levels 1–3 have multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15). This is a valid negative result, correctly preserved. The hierarchical_v1 (2-level) production protocol PASSES for 3 text-based modes — do not conflate the two protocols.

3. **calibration_fails_tfidf**: Thresholds too aggressive for TF-IDF signal density; calibrated protocol does not improve over frozen v1; negative result correctly recorded.

4. **dense_integration_contract_frozen**: Four complementary view criteria defined with acceptance thresholds; validated against 12k/144k evidence where available.

5. **scale_extrapolation_validated**: 144k checkpoint confirms hierarchical builder (2-level) fine_branch_purity ~0.97, improvement rates healthy, nesting ≥0.99, fine singletons ~4–5%. Note: These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k).

6. **nesting_metric_defect_enforced**: 7 compressed-family modes had nesting_score≥0.99 without scope annotation; min_cluster_size enforces nesting=1.0 by construction; enforcement active for all outputs.

7. **blocker_upstream_data**: Legal-distance 174k dense embeddings require BGE/bger ID mapping + parquet 2022–2026 from corpus lane; no fractal-map lane defect exists.

---

## Dense Embedding Integration Contract v34 (FROZEN)

**Primary Product Mode**: TF-IDF citation hybrids (cited_decisions_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7) — jurist preference 0.78–0.79, beats simple semantic baseline (JP 0.43).

**Complementary Views** (dense embeddings only, not primary navigation):

| View | Acceptance Criterion | Evidence Status |
|------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 (vs TF-IDF 0.71–0.74) | PASSED at 144k (center_projected AUC 0.79–0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | PASSED at 144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | PASSED at 144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | FAILED (0.09) — reasoning most language-specific |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3–0.4 | PASSED (JP 0.61–0.67, LD < 0.85) but BELOW TF-IDF baseline |

**Blockers** (all upstream):
- Corpus lane: BGE/bger ID mapping production
- Corpus lane: Parquet generation for years 2022–2026 (29,520 decisions missing)
- Corpus lane: Section extraction at 174k scale for cross-lingual evaluation density
- Legal-distance lane: 174k dense embeddings computation (currently ~11% complete)

---

## Test Suite Results (Independent Re-verification)

| Test Suite | Total | Passed | Skipped | Status |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 186 | 0 | ✅ PASS |
| test_pipeline_readiness.py | 14 | 14 | 0 | ✅ PASS |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | ✅ PASS |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | ✅ PASS |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | ✅ PASS |
| test_scale_dependency.py | 11 | 11 | 0 | ✅ PASS |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | ✅ PASS |
| **GRAND TOTAL** | **247** | **246** | **1** | **✅ ALL PASS** |

---

## Orchestration Failure — Control Plane Discrepancy

### Root Cause
The mounted control plane at `/tmp/lex_control/state/factory_direction.json` shows:
```json
"fractal-map": {
  "status": "RUN",  // INCORRECT
  ...
}
```

While the authoritative sources all correctly show:
- **Workspace** `state/factory_direction.json` line 16: `"status": "BLOCKED_ON_DEPENDENCIES"`
- **Lane state** `state/fractal-map.json`: `"cycle_status": "BLOCKED_ON_DEPENDENCIES"`
- **All audit reports**: Consistently document BLOCKED_ON_DEPENDENCIES

### Impact
- External observers / downstream lanes see fractal-map as runnable (incorrect)
- Could trigger premature product integration attempts
- Masks the true critical path: **legal-distance 174k dense embeddings audit promotion** → requires **corpus lane resumption** for BGE/bger ID mapping + parquet 2022–2026 + section extraction

### Resolution
This is a **control plane infrastructure defect** (V28-pattern persistent mounting issue). No lane action can fix it. The lane has correctly self-diagnosed, self-blocked, and preserved all evidence.

---

## Audit Readiness Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Provenance preserved | ✅ | All result files referenced in state |
| Negative results preserved | ✅ | Multi-level protocol FAIL, calibration FAIL, flat zoom FAIL |
| Frozen benchmarks unchanged | ✅ | v26 frozen spec referenced; v34 contract frozen |
| Evidence tiers accurate | ✅ | Table in deliverables section |
| Blockers documented | ✅ | 4 specific upstream dependencies in state & contract |
| Next steps unambiguous | ✅ | Await corpus lane resumption → legal-distance 174k dense embeddings |
| No fabricated data | ✅ | All results from actual computation |
| No overwritten claim-bearing outputs | ✅ | All historical results preserved in results/ |
| Test suites pass | ✅ | 246/247 tests pass (1 skipped) |

---

## Next Steps

**No further same-question cycles justified** (`continue_recommended=false`).

**Factory Director action required:**
1. **Resume corpus lane** for: (a) BGE/bger ID mapping production, (b) parquet generation for years 2022–2026, (c) section extraction at 174k scale
2. **Then** legal-distance lane can complete 174k dense embeddings computation and audit promotion
3. **Then** fractal-map lane can resume with: "Test constrained hierarchical Leiden at 174k on ACCEPTED dense modes (center_projected, citation-role, metric learning, linear hybrids) for complementary views"

---

## Conclusion

The fractal-map lane has **successfully completed its v34 deliverable**. The orchestration failure (control plane mounting defect) and validation failure (legal-distance progress vs. accepted state gap) are **control plane issues**, not lane failures. The lane correctly self-diagnosed, self-blocked, and preserved all evidence with accurate evidence tiers.

**The lane is audit-ready.** All evidence preserved, negative results intact, contract frozen. No further work required until upstream dependencies are resolved.