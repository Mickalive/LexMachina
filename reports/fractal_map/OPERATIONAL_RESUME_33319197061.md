# Fractal-Map Lane Operational Resume — Run 33319197061

**Date:** 2026-08-30  
**Lane:** fractal-map  
**Direction Version:** 10  
**GitHub Run:** 33319197061  
**Previous Accepted Run:** 33317287543 (+ repair 33317520019)

## Summary

Maintenance run completing hierarchical artifacts for 5 v6 baseline modes that were missing `labels_hierarchical_best.npy`, `labels_coarse_0.5.npy`, and `hierarchical_map_results.json`. After completion, all 21 legal-distance modes in `results/fractal_map/legal_distance_modes/` are artifact-complete. No new research claims — all metrics derived from existing accepted resolution labels.

## What Was Done

### 1. State Integrity Verification
- **135/135 existing tests PASS** (baseline before changes)
- All artifacts verified present and consistent

### 2. Artifact Completeness Audit
- Audited all 21 legal-distance modes for 10 required files (7 resolution labels + hierarchical_best + coarse_0.5 + hierarchical_map_results.json)
- **Found 5 incomplete modes** (v6 baselines built before parameterized builder existed):
  - `debiased_citation_blended`
  - `hybrid_alpha_03`
  - `hybrid_alpha_05`
  - `legal_cited_decisions_only`
  - `legal_issues_outcomes`
- All 5 had complete `labels_res_*.npy` (7 files) but were missing 3 hierarchical artifacts

### 3. Artifact Generation
- Created `fractal_map/hierarchical/complete_v6_hierarchical_artifacts.py`
- For each mode, derived:
  - `labels_hierarchical_best.npy` = `labels_res_3.0.npy` (legal-distance provenance rule)
  - `labels_coarse_0.5.npy` = `labels_res_0.5.npy`
  - `hierarchical_map_results.json` = nesting, zoom coherence, branch purity computed from resolution labels + baseline metadata
- **No re-clustering performed** — all artifacts derived from existing accepted labels

### 4. Independent Verification
- Created `results/fractal_map/evaluation/verify_v6_hierarchical_artifacts.py`
- Independently verified each mode:
  - Provenance rule holds (hierarchical_best == labels_res_3.0)
  - Coarse labels match (coarse_0.5 == labels_res_0.5)
  - JSON metrics consistent with label arrays
  - All 5 modes PASS verification

### 5. Test Suite Expansion
- Added 40 new tests (8 per mode × 5 modes) covering:
  - Label array existence and size (5 modes × 2 tests = 10)
  - Hierarchical labels existence and size (5 × 2 = 10)
  - Coarse labels existence and size (5 × 2 = 10)
  - Hierarchical map results existence (5 × 1 = 5)
  - Nesting perfect (5 × 1 = 5)
  - Hierarchical best == res_3.0 (5 × 1 = 5)
  - Coarse == res_0.5 (5 × 1 = 5)
- **175/175 tests PASS**

## Results

| Mode | Fine Clusters | Coarse Clusters | Nesting | Hier Purity | Coarse Purity |
|------|--------------|-----------------|---------|-------------|---------------|
| debiased_citation_blended | 19 | 8 | 1.0 | 0.947 | 0.975 |
| hybrid_alpha_03 | 22 | 7 | 1.0 | 0.927 | 0.791 |
| hybrid_alpha_05 | 24 | 9 | 1.0 | 0.882 | 0.757 |
| legal_cited_decisions_only | 195 | 9 | 1.0 | 0.728 | 0.738 |
| legal_issues_outcomes | 31 | 6 | 1.0 | 0.742 | 0.667 |

## Artifact Inventory After Completion

- **21 legal-distance modes**: ALL artifact-complete (10 required files each)
- **1 center_projected**: artifact-complete
- **1 legacy concat**: artifact-complete
- **2 N=1200 scalability**: artifact-complete
- **Total**: 25 mode directories, all artifact-complete

## State Update

- `tests_passed`: 135 → 175
- `evidence_refs`: +4 new refs
- `key_findings`: +1 new finding (v6 artifact completion)
- `timestamp`: updated

## Recommendation

**PRODUCTIZE.** All 21 legal-distance modes now have complete hierarchical artifacts. Lane remains BLOCKED on corpus lane for 192k scaling. No additional same-question research cycle justified until corpus delivers 192k decisions.

## Evidence Files

- `results/fractal_map/evaluation/complete_v6_hierarchical_artifacts_33319197061.json` — run results
- `results/fractal_map/evaluation/v6_hierarchical_artifact_verification.json` — independent verification
- `results/fractal_map/evaluation/verify_v6_hierarchical_artifacts.py` — verification script
- `fractal_map/hierarchical/complete_v6_hierarchical_artifacts.py` — generation script
- `tests/fractal_map/test_verify.py` — 175 tests (40 new)
