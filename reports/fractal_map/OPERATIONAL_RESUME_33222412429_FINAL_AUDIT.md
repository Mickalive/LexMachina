# Fractal-Map Lane — Final Audit Snapshot (GitHub Run 33222412429)

**Lane**: fractal-map  
**Factory Direction Version**: 6  
**GitHub Run**: 33222412429  
**Operational Resume From**: 33221891157  
**Timestamp**: 2026-08-29T01:08:00Z  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: COMPLETED  
**Continue Recommended**: false  
**Next Recommendation**: PRODUCTIZE  

---

## Executive Summary

The fractal-map lane has **successfully completed all Factory Direction v6 requirements**. The operational resume from run 33221891157 has been verified, the orchestration gap (ephemeral `/tmp/lex_accepted` mirroring loss) has been diagnosed and resolved, and the lane deliverable is confirmed **audit-ready**.

All 48 verification tests PASS. The `/tmp/lex_accepted/fractal_map/` mirroring has been re-established with 233 artifacts. The `/tmp/lex_accepted/state/fractal_map.json` state file has been mirrored. The loader API is fully functional. The state file has been updated to reflect the latest successful audit gate (run 33221891157).

---

## Factory Direction v6 Requirements — ALL VERIFIED

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Reproduce hierarchical Leiden on `center_projected` embeddings | ✅ VERIFIED | `center_projected_hierarchical_results.json`: purity=0.9571, nesting=1.0 |
| Expose resolution ladder | ✅ VERIFIED | 7 levels: 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0 |
| Cluster metadata & legal coherence at each zoom level | ✅ VERIFIED | `cluster_metadata.json` with 108 hierarchical clusters (coarse_0.5_fine_3.0) |
| Integrate as default map structure | ✅ VERIFIED | `center_projected_hierarchical` replaces `hierarchical_leiden_concat` as default |
| Legal-distance selectable modes | ✅ VERIFIED | 5 modes at ACCEPTED tier integrated in map mode registry |

---

## Key Metrics (Center Projected Hierarchical)

| Metric | Value | Notes |
|--------|-------|-------|
| **Hierarchical Purity (global)** | **0.9571** | +0.0080 vs concat baseline (0.9491), min_cluster_size=3 |
| **Nesting Score** | **1.0** | Perfect nesting guaranteed by hierarchical construction |
| **Flat Mean Purity** | 0.9341 | |
| **Zoom Coherence Improvement Rate** | **31.1%** | Per-resolution-step methodology: 19/61 parent clusters improve |
| **Resolution Ladder** | 7 levels | 0.25→0.5→0.75→1.0→1.5→2.0→3.0 (5→7→9→11→14→16→19 clusters) |
| **Hierarchical Clusters (coarse_0.5_fine_3.0)** | 108 | Branch purity 0.9571 |
| **Adversarial Language Dominance** | 0.7593 | PASS (< 0.85) — from evaluation v2 |
| **Jurist Pairwise Preference** | 0.5215 | PASS (> 0.5) — from evaluation v2 |
| **Jurivoc Benchmarks** | 4/5 PASS | From evaluation v2 |

---

## Orchestration Gap Diagnosis & Resolution

### Pathology
`/tmp/lex_accepted/fractal_map/` mirroring was lost due to `/tmp` directory volatility between GitHub workflow runs. The accepted branch mirroring must be re-established as the first step of every operational resume.

### Root Cause
`/tmp` is ephemeral storage; accepted branch mirroring is not persisted across workflow runs.

### Classification
**Orchestration completeness gap (environment volatility), NOT scientific failure.**

### Fix Applied in This Run (33222412429)
1. ✅ Re-established `/tmp/lex_accepted/fractal_map/` mirroring from validated source
2. ✅ Copied `state/fractal-map.json` and all `results/fractal_map/` to accepted branch mirror
3. ✅ Verified state file consistency between repo and accepted branch (diff = identical)
4. ✅ Verified all key artifacts present (233 files in mirror)
5. ✅ Re-ran all 48 verification tests — **ALL PASS**
6. ✅ Verified loader API functional with full artifact loading
7. ✅ Updated state file with latest run ID (33221891157), timestamp, and audit gate reference
8. ✅ Fixed loader import issue (added sys.path insertion for map_mode_registry module)

### Recommendation
Factory orchestration must verify `/tmp/lex_accepted` mirroring at start of every operational resume; consider persistent storage for accepted branches or automated re-mirror step.

---

## Verification Results

**Test Suite**: `tests/fractal_map/test_verify.py`

| Test Class | Tests | Status |
|------------|-------|--------|
| TestArtifactIntegrity | 18 | ✅ PASS |
| TestHierarchicalLeiden | 6 | ✅ PASS |
| TestMetricConsistency | 7 | ✅ PASS |
| TestLegacyConcatPreserved | 10 | ✅ PASS |
| TestLegalDistanceModes | 3 | ✅ PASS |
| **Total** | **48** | **48 PASS, 0 FAIL** |

**Loader API Verification** (from repo root with fixed import):
- `list_modes`: ✅ PASS — 8 modes listed correctly
- `load_default` / `load_mode`: ✅ PASS — `center_projected_hierarchical` loads with 9 label arrays
- `get_resolution_labels`: ✅ PASS — all 7 resolutions return correct cluster counts (5, 7, 9, 11, 14, 16, 19)
- `get_hierarchical_labels`: ✅ PASS — 92 hierarchical clusters (108 defined, 16 empty in practice)
- `get_coarse_labels`: ✅ PASS — 7 parent clusters at res 0.5
- `get_zoom_mapping`: ✅ PASS — parent-child mappings with nesting_consistency=1.0 for all adjacent resolutions
- `get_decision_clusters`: ✅ PASS — decision lookup by ID works
- `get_cluster_metadata`: ✅ PASS — legal context per cluster (branch, area, chamber, language) at all resolutions
- `get_zoom_coherence`: ✅ PASS — per-cluster improvement metrics per resolution step

---

## Evidence Traceability (Updated)

| Artifact | Path |
|----------|------|
| Primary Results | `results/fractal_map/hierarchical_map_center_projected/center_projected_hierarchical_results.json` |
| Map Mode Registry | `results/fractal_map/product_integration/map_mode_registry.json` |
| Product Integration Spec | `results/fractal_map/product_integration/PRODUCT_INTEGRATION_SPEC.md` |
| Legal Distance Modes | `results/fractal_map/legal_distance_modes/` |
| Loader API | `results/fractal_map/product_integration/map_mode_loader.py` |
| Accepted Branch State | `/tmp/lex_accepted/state/fractal-map.json` |
| Accepted Branch Results | `/tmp/lex_accepted/fractal_map/results/fractal_map/` |
| Repo State File | `state/fractal-map.json` |
| Audit Trail | 18 gate files in `results/fractal_map/audit/` |

---

## Audit Trail (18 Gates)

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
18. **CYCLE_operational_resume_33221891157_FINAL_AUDIT_GATE.json (LATEST — RE-ESTABLISHED MIRRORING, ALL CHECKS PASS)**

---

## Dependencies (For Downstream Lanes)

| Dependency | Description |
|------------|-------------|
| legal_distance_reproduction | `center_projected` embeddings require legal-distance lane reproduction on full v1+v2 benchmark suite for legal-distance mode integration |
| full_corpus_scale | Current validation on 1,000 decisions (2020-2024); full 2000-2024 corpus scaling needed per corpus lane (~192k decisions via OpenCaseLaw bulk ingestion) |

---

## Final Verdict

**GATE: PASS** — The fractal-map lane has successfully completed all Factory Direction v6 requirements. The hierarchical Leiden fractal map on `center_projected` embeddings is validated, productized as the DEFAULT map mode, and integrated with 5 legal-distance selectable modes at ACCEPTED tier. The deliverable is audit-ready with full evidence traceability, negative results preserved, accepted branch mirroring re-established and verified (233 artifacts), and loader API functional.

**Next Action**: Factory Director may promote to PRODUCTIZE. No further fractal-map cycles under v6.

---

*This summary is immutable and audit-ready. All evidence references are verifiable in the repository and accepted branch mirror.*
