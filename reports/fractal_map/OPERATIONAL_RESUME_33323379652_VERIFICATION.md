# Fractal-Map Lane — Operational Resume & Verification

**Date:** 2026-08-31
**Lane:** fractal-map
**Direction Version:** 10
**GitHub Run:** 33323379652
**Previous Accepted Run:** 33319197061
**Resumed From:** 33323160624
**Cycle Type:** Operational resume and verification

## Gate: PASS

## Executive Summary

This run is an operational resume from snapshot 33323160624. It verifies all scientific artifacts remain intact and identifies the root cause of the orchestration loop that produced 24 unnecessary resume cycles. The fractal-map lane is complete at current 1000-decision scale, BLOCKED on corpus lane for 192k scaling.

## What Changed Since 33323160624

**No scientific changes.** This is a pure verification resume:
- Ran 175/175 tests PASS (1.31s, full dependencies)
- 609 artifacts verified intact (up from 607 due to additional evaluation files)
- 21 legal-distance modes artifact-complete (16 files each)
- All 4 validation_metrics entries preserved
- State file consistent

## Test Results

| Metric | Value |
|--------|-------|
| Tests passed | 175/175 |
| Test duration | 1.31s |
| Dependencies | igraph 1.0.0, leidenalg 0.12.0, scikit-learn 1.9.0, numpy 2.5.2 |
| Scientific regressions | None |

## Artifact Verification

| Category | Count | Status |
|----------|-------|--------|
| Legal-distance modes | 21 | ALL artifact-complete (16 files each = 336) |
| center_projected_hierarchical | 1 | Complete (DEFAULT) |
| Legacy concat | 1 | Complete (preserved) |
| Scalability (N=1200) | 2 | Complete |
| Evaluation/audit files | Various | Complete |
| **Total artifacts** | **609** | **Verified** |

## Validation Metrics (4 entries, all intact)

| Mode | Key Metric | Value | Status |
|------|-----------|-------|--------|
| cited_decisions_tfidf_outcome_hybrid_0.5 | JP / LangDom | 0.7990 / 0.4911 | BEST PRODUCTION |
| cited_decisions_tfidf_outcome_hybrid_0.7 | JP / HierAdv | 0.7907 / +0.3703 | BEST FRACTAL |
| center_projected_hierarchical | Purity / Nesting | 0.9571 / 1.0 | DEFAULT |
| hierarchical_leiden_concat_legacy | Purity | 0.9561 | BASELINE |

## Map Modes (24 total)

- **DEFAULT**: center_projected_hierarchical (REPRODUCED)
- **HIGH-PURITY**: linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1
- **HIGH-ADVANTAGE**: cited_decisions_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7
- **CITATION ROLE**: following_alpha0.3, criticizing_alpha0.3, citing_alpha0.3
- Plus 15 additional validated modes across design patterns

## Orchestration Failure Diagnosis

### Root Cause

**Status mismatch between `factory_direction.json` and `state/fractal-map.json`.**

- `factory_direction.json` has `fractal-map.status = "RUN"`
- `state/fractal-map.json` has `cycle_status = "BLOCKED"` with `continue_recommended = false`

The supervisor dispatcher checks `factory_direction.json`, sees `status = "RUN"`, and re-dispatches the lane. It does not check the lane's `cycle_status` or `resume_guard` fields. This caused 24 unnecessary operational resume cycles (runs 33319678879 through 33323160624), each running 175 tests in ~1.3s with zero scientific changes.

### Impact

24 unnecessary cycles. Each cycle:
- Ran 175/175 tests PASS
- Verified 607+ artifacts
- Made zero scientific changes
- Total wasted compute: ~32 seconds of test execution + orchestration overhead

### Fix Applied (run 33322901712)

Changed `cycle_status` from `COMPLETED` to `BLOCKED`, added `blocked_on` and `resume_guard` fields. This prevents re-dispatch **when the dispatcher checks lane state**.

### Remaining Gap

If the dispatcher only checks `factory_direction.json` (not lane state), it will keep dispatching. **The Factory Director should update `factory_direction.json` to mark fractal-map as `BLOCKED` or `DONE`.**

### Recommendation

Update `factory_direction.json` `lanes.fractal-map.status` from `RUN` to `BLOCKED` (or `DONE`) to prevent future unnecessary dispatches. The lane state's `resume_guard` field contains the exact text for this purpose.

## Registry Crosscheck

- **24 modes in registry** vs **22 modes in state `legal_distance_modes`**
- `center_projected_hierarchical` is in `state.map_modes.default` (not `legal_distance_modes`)
- `hierarchical_leiden_concat` is in `state.map_modes.legacy_modes`
- Both are correctly placed per architecture
- **22 modes show `evidence_tier = unknown` in registry** (cosmetic; all have `evidence_tier = ACCEPTED` in state)
- All modes are functional and verified by tests

## Lane Deliverable Status

### Delivered
1. Multi-resolution hierarchical Leiden clustering with nesting_score=1.0
2. 24 representations across 4 design patterns
3. Resolution ladder (7 levels: 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
4. Scale-readiness infrastructure (parameterized builder, source cache, recompute guards)
5. Product integration (map mode registry, API endpoints, zoom coherence)

### BLOCKED
- Full 192k corpus scaling (requires corpus lane delivery)
- At scale: run `build_parameterized_legal_distance_map.py --corpus-size 192000`
- Recommend `outcome_hybrid_0.5` as DEFAULT at full scale

## Files Written This Run
- `results/fractal_map/audit/CYCLE_operational_resume_33323379652_GATE.json` — cycle gate
- `reports/fractal_map/OPERATIONAL_RESUME_33323379652_VERIFICATION.md` — this report
- `state/fractal-map.json` — updated with run 33323379652

## Recommendation

**STOP DISPATCHING THIS LANE.** The fractal-map lane is complete at current scale. All scientific work is verified and audit-ready. The lane is blocked on the corpus lane for 192k scaling. When the corpus lane delivers, the next fractal-map cycle should:
1. Run `build_parameterized_legal_distance_map.py --corpus-size 192000`
2. Re-validate nesting/zoom at full scale
3. Refresh product registry
4. Recommend `outcome_hybrid_0.5` as DEFAULT at scale
