# Fractal Map Lane — Operational Resume 33207149474 Report

**Lane:** fractal-map  
**Factory Direction Version:** 6  
**GitHub Run:** 33207149474  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Recommendation:** PRODUCTIZE  
**Date:** 2026-08-28

---

## Executive Summary

This operational resume **diagnoses and fixes an orchestration/validation failure** in the accepted branch mirroring for factory direction v6. The `/tmp/lex_accepted/fractal-map` state and results (mirrored in run 33204555939) were missing due to `/tmp` directory volatility between workflow runs. This run re-establishes complete mirroring and verifies all 48 tests pass.

**Root Cause:** `/tmp` is volatile storage; accepted branch mirroring must be re-established on each operational resume. This is an **orchestration completeness gap, NOT a scientific failure**.

**Fix Applied:** Recreated `/tmp/lex_accepted/state/` and `/tmp/lex_accepted/results/fractal_map/`; mirrored state file and 5 result artifact directories (47 evidence_refs + audit trail); re-verified all 48 tests pass.

---

## Factory Direction v6 Requirements — All SATISFIED

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Reproduce hierarchical Leiden on center_projected | ✅ VERIFIED | `hierarchical_map_center_projected/` artifacts |
| Nesting = 1.0 | ✅ PASS | Hierarchical construction guarantees perfect nesting |
| Purity ≥ 0.949 | ✅ PASS | 0.9638 (exceeds concat baseline 0.9491 by 1.55%) |
| Resolution ladder exposed (7 levels) | ✅ VERIFIED | 0.25→0.5→0.75→1.0→1.5→2.0→3.0 |
| Cluster metadata & legal coherence per zoom | ✅ VERIFIED | `cluster_metadata.json` (251KB, branch/language/area/chamber/year) |
| Default map structure = center_projected_hierarchical | ✅ VERIFIED | `map_mode_registry.json` default entry |
| Legal-distance selectable modes (5 ACCEPTED) | ✅ VERIFIED | All 5 modes integrated with warnings where applicable |

---

## Key Metrics (Re-verified)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Hierarchical Purity (global) | 0.9638 | > 0.95 | ✅ PASS |
| Nesting Score | 1.0 | = 1.0 | ✅ PASS |
| Fine Clusters (coarse_0.5_fine_3.0) | 108 | > 0 | ✅ PASS |
| Flat Mean Purity | 0.9341 | — | baseline |
| Purity Improvement vs Flat | +3.18% | > 0% | ✅ PASS |
| Purity Improvement vs Concat | +1.55% | > 0% | ✅ PASS |
| Adversarial Language Dominance | 0.7593 | < 0.85 | ✅ PASS (v5 carried forward) |
| Jurist Pairwise Preference | 0.5215 | > 0.5 | ✅ PASS (v5 carried forward) |
| Jurivoc Hierarchy Alignment | 4/5 | — | ✅ PASS (v5 carried forward) |

---

## Verification Test Results

| Test Category | Tests | Passed | Failed |
|---------------|-------|--------|--------|
| TestArtifactIntegrity | 18 | 18 | 0 |
| TestHierarchicalLeiden | 6 | 6 | 0 |
| TestMetricConsistency | 7 | 7 | 0 |
| TestLegacyConcatPreserved | 10 | 10 | 0 |
| TestLegalDistanceModes | 3 | 3 | 0 |
| **TOTAL** | **48** | **48** | **0** |

---

## Accepted Branch Mirroring — RE-ESTABLISHED

| Component | Source | Target | Status |
|-----------|--------|--------|--------|
| State file | `state/fractal-map.json` | `/tmp/lex_accepted/state/fractal_map.json` | ✅ IDENTICAL |
| hierarchical_map_center_projected | 17 artifacts | `/tmp/lex_accepted/results/fractal_map/hierarchical_map_center_projected/` | ✅ COMPLETE |
| hierarchical_map (legacy) | 11 artifacts | `/tmp/lex_accepted/results/fractal_map/hierarchical_map/` | ✅ COMPLETE |
| product_integration | 12 artifacts | `/tmp/lex_accepted/results/fractal_map/product_integration/` | ✅ COMPLETE |
| legal_distance_modes | 5 modes × ~8 artifacts | `/tmp/lex_accepted/results/fractal_map/legal_distance_modes/` | ✅ COMPLETE |
| evaluation | 8 artifacts | `/tmp/lex_accepted/results/fractal_map/evaluation/` | ✅ COMPLETE |
| audit trail | 40+ gates | `/tmp/lex_accepted/results/fractal_map/audit/` | ✅ COMPLETE |

**All 47 `evidence_refs` from state file verified present in `/tmp/lex_accepted/`.**

---

## Negative Results Preserved

- Flat Leiden nesting imperfect (mean ~0.50 across resolution ladder)
- Some clusters already homogeneous at coarse resolution (no zoom improvement expected)
- igraph version sensitivity: cluster counts vary but key invariants preserved (nesting=1.0, purity>0.94)
- Legal_issues_outcomes fails multilingual_invariance and adversarial_falsification benchmarks
- Hybrid modes (alpha_03, alpha_05) fail adversarial_falsification benchmark

---

## Audit Trail

All claim-bearing results preserved in:
- `state/fractal-map.json` (machine-readable lane state, direction_version=6)
- `results/fractal_map/hierarchical_map_center_projected/` (center_projected hierarchical validation)
- `results/fractal_map/product_integration/` (product integration artifacts)
- `results/fractal_map/legal_distance_modes/` (5 ACCEPTED legal-distance map modes)
- `results/fractal_map/audit/` (audit gates for all completed cycles, including this fix)

**New audit gate:** `CYCLE_operational_resume_33207149474_GATE.json`

---

## Recommendation

**PRODUCTIZE** — The fractal-map lane has delivered all v6 requirements and the orchestration gap is fixed. The lane is ready for product integration. No further fractal-map cycles required under current factory direction.

**Dependencies for next factory direction:**
1. Legal-distance reproduction of center_projected (unblocks full mode validation)
2. Full corpus scale (~192k decisions) map computation and persistence
3. Product hardening for production deployment

---

*Report generated per Research Protocol §12: "Write machine-readable lane state plus human-readable report."*
