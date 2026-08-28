# Fractal-Map Lane — Operational Resume Summary (GitHub Run 33219321753)

**Lane**: fractal-map  
**Factory Direction Version**: 6  
**GitHub Run**: 33219321753  
**Prior Operational Resume**: 33218009833  
**Timestamp**: 2026-08-28T23:15:00Z  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: COMPLETED  
**Continue Recommended**: false  
**Next Recommendation**: PRODUCTIZE  

---

## Executive Summary

This operational resume successfully **re-established the accepted branch mirroring** at `/tmp/lex_accepted/fractal_map/` which was lost due to `/tmp` ephemeral storage volatility between GitHub workflow runs. All 48 verification tests PASS, the loader API is fully functional, and the state file is updated with the current run ID. The fractal-map lane deliverable remains **audit-ready** and **PRODUCTIZE-ready**.

---

## Orchestration Diagnosis & Resolution

**Pathology**: `/tmp/lex_accepted/fractal_map/` mirroring was lost due to `/tmp` directory volatility between GitHub workflow runs (previously re-established in run 33218009833, but not persisted to current run 33219321753).

**Root Cause**: `/tmp` is ephemeral storage; accepted branch mirroring must be re-established as first step of every operational resume.

**Classification**: Orchestration completeness gap (environment volatility), **NOT scientific failure**.

**Fix Applied**:
1. Re-established `/tmp/lex_accepted/fractal_map/` mirroring from validated source (all artifacts confirmed)
2. Copied `state/fractal-map.json` and all `results/fractal_map/` to accepted branch mirror
3. Verified state file consistency between repo and accepted branch (diff clean)
4. Verified all key artifacts present (225 total artifacts)
5. Re-ran all 48 verification tests (all PASS)
6. Verified loader API functional with full artifact loading
7. Created audit gate `CYCLE_operational_resume_33219321753_GATE.json` atomically with verification

---

## Factory Direction v6 Requirements — ALL VERIFIED (Carried Forward)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Reproduce hierarchical Leiden on `center_projected` embeddings | ✅ VERIFIED | `center_projected_hierarchical_results.json`: purity=0.9571, nesting=1.0, best_config=coarse_0.5_fine_3.0 |
| Expose resolution ladder | ✅ VERIFIED | 7 levels: 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0 with label arrays for each |
| Cluster metadata & legal coherence at each zoom level | ✅ VERIFIED | `cluster_metadata.json` with 108 hierarchical clusters, branch/area/chamber/language per cluster |
| Integrate as default map structure | ✅ VERIFIED | `center_projected_hierarchical` replaces `hierarchical_leiden_concat` as default in `map_mode_registry.json` |
| Legal-distance selectable modes | ✅ VERIFIED | 5 modes at ACCEPTED tier: `debiased_citation_blended`, `legal_cited_decisions_only`, `hybrid_alpha_03`, `hybrid_alpha_05`, `legal_issues_outcomes` |

---

## Verification Results

**Test Suite**: `tests/fractal_map/test_verify.py`
- **Total Tests**: 48
- **Passed**: 48
- **Failed**: 0

| Test Class | Tests |
|------------|-------|
| TestArtifactIntegrity | 18 |
| TestHierarchicalLeiden | 6 |
| TestMetricConsistency | 7 |
| TestLegacyConcatPreserved | 10 |
| TestLegalDistanceModes | 3 |

**Loader API Verification** (all PASS):
- `list_modes`: 8 modes listed correctly
- `load_mode(center_projected_hierarchical)`: loads with 9 label arrays
- `get_resolution_labels`: all 7 resolutions return correct cluster counts (5, 7, 9, 11, 14, 16, 19)
- `get_hierarchical_labels`: 1000 hierarchical clusters (labels_hierarchical_best)
- `get_coarse_labels`: 7 parent clusters at res 0.5
- `get_zoom_mapping`: parent-child mappings for all 6 adjacent resolution pairs
- `get_decision_clusters`: decision lookup by ID works
- `get_cluster_metadata`: legal context per cluster (branch, area, chamber, language)
- `get_zoom_coherence`: per-cluster improvement metrics per resolution step

---

## Accepted Branch Mirroring Status

- **State file**: `/tmp/lex_accepted/fractal_map/state/fractal_map.json` ✅ (identical to repo)
- **Result directories**: 19
- **Total artifacts**: 225
- **State verified identical**: true

---

## Key Metrics (Unchanged from Prior Verification)

| Metric | Value | Notes |
|--------|-------|-------|
| **Hierarchical Purity (global)** | **0.9571** | +0.0080 vs concat baseline (0.9491), min_cluster_size=3 |
| **Nesting Score** | **1.0** | Perfect nesting guaranteed by hierarchical construction |
| **Flat Mean Purity** | 0.9341 | |
| **Zoom Coherence Improvement Rate** | **31.1%** | Per-resolution-step methodology: 19/61 parent clusters improve |
| **Resolution Ladder** | 7 levels | 0.25→0.5→0.75→1.0→1.5→2.0→3.0 (5→7→9→11→14→16→19 clusters) |
| **Hierarchical Clusters (coarse_0.5_fine_3.0)** | 108 | Branch purity 0.9571 |
| **Adversarial Language Dominance** | 0.7593 | PASS (< 0.85 threshold) — from evaluation v2 |
| **Jurist Pairwise Preference** | 0.5215 | PASS (> 0.5 threshold) — from evaluation v2 |
| **Jurivoc Benchmarks** | 4/5 PASS | From evaluation v2 |

---

## Map Mode Registry — Complete (8 Modes)

| Mode ID | Type | Status | Evidence Tier | Notes |
|---------|------|--------|---------------|-------|
| **center_projected_hierarchical** | hierarchical_leiden | **DEFAULT** | REPRODUCED | New default per v6 |
| hierarchical_leiden_concat | hierarchical_leiden | legacy | REPRODUCED | Preserved for comparison |
| debiased_citation_blended | legal_distance | available | ACCEPTED | 14/14 benchmarks PASS |
| legal_cited_decisions_only | legal_distance | available | ACCEPTED | 14/14 benchmarks PASS |
| hybrid_alpha_03 | legal_distance | available | ACCEPTED | 13/14 PASS (fails adversarial_falsification) |
| hybrid_alpha_05 | legal_distance | available | ACCEPTED | 13/14 PASS (fails adversarial_falsification) |
| legal_issues_outcomes | legal_distance | available | ACCEPTED | 10/14 PASS (multiple warnings) |
| center_projected | legal_distance | placeholder | ACCEPTED | Raw embedding; use hierarchical for navigation |

---

## Negative Results Preserved

1. **Flat Leiden nesting imperfect** (mean ~0.50 across resolution ladder)
2. **Some clusters already homogeneous at coarse resolution** (no zoom improvement expected)
3. **igraph version sensitivity**: cluster counts vary but key invariants preserved (nesting=1.0, purity>0.94)
4. **legal_issues_outcomes fails multilingual_invariance and adversarial_falsification benchmarks**
5. **Hybrid modes (alpha_03, alpha_05) fail adversarial_falsification benchmark**
6. **Zoom coherence methodology difference**: per-resolution-step (31.1%) vs hierarchical_zoom_validation (59.2% for concat baseline) — different methodologies, not directly comparable

---

## Audit Trail (20 Gates)

1. CYCLE_operational_resume_33132507730_GATE.json
2. CYCLE_operational_resume_33132986797_GATE.json
3. CYCLE_operational_resume_33133395447_GATE.json
4. CYCLE_operational_resume_33134184565_GATE.json
5. CYCLE_operational_resume_33134755365_GATE.json
6. CYCLE_operational_resume_33135281890_GATE.json
7. CYCLE_center_projected_hierarchical_v5_33137354250_GATE.json
8. CYCLE_center_projected_hierarchical_v6_33139587950_GATE.json
9. CYCLE_operational_resume_33207149474_GATE.json
10. CYCLE_operational_resume_33209861284_GATE.json
11. CYCLE_operational_resume_33211353804_GATE.json
12. CYCLE_operational_resume_33212512155_GATE.json
13. CYCLE_operational_resume_33213824979_GATE.json
14. CYCLE_operational_resume_33214267286_GATE.json
15. CYCLE_operational_resume_33214779571_GATE.json
16. CYCLE_operational_resume_33215480822_GATE.json
17. CYCLE_operational_resume_33216227907_GATE.json
18. CYCLE_operational_resume_33217119966_GATE.json
19. CYCLE_operational_resume_33217485684_GATE.json
20. CYCLE_operational_resume_33218009833_GATE.json
21. **CYCLE_operational_resume_33219321753_GATE.json (THIS RUN)**

---

## Final Verdict

**GATE: PASS** — The fractal-map lane has successfully completed all Factory Direction v6 requirements. The hierarchical Leiden fractal map on `center_projected` embeddings is validated, productized as the DEFAULT map mode, and integrated with 5 legal-distance selectable modes at ACCEPTED tier. The deliverable is audit-ready with full evidence traceability, negative results preserved, accepted branch mirroring re-established and verified (225 artifacts), and loader API functional.

**Next Action**: Factory Director may promote to PRODUCTIZE. No further fractal-map cycles under v6.

---

*This summary documents the operational resume completion. All evidence references are verifiable in the repository and accepted branch mirror.*
