# Fractal Map Lane — Snapshot Audit-Ready Report

**Run ID:** `operational_resume_33214267286`  
**GitHub Run:** `33214267286`  
**Factory Direction:** Version 6  
**Lane:** `fractal-map`  
**Evidence Tier:** `REPRODUCED`  
**Cycle Status:** `COMPLETED`  
**Continue Recommended:** `false`  
**Next Recommendation:** `PRODUCTIZE`  
**Timestamp:** `2026-08-28T21:55:00Z`

---

## Executive Summary

The fractal-map lane deliverable for **Factory Direction v6 is COMPLETE and AUDIT-READY**.

This operational resume re-establishes the accepted branch mirroring at `/tmp/lex_accepted/fractal_map/` (lost due to `/tmp` ephemeral storage volatility between GitHub workflow runs) and re-verifies all deliverables. All **48 verification tests PASS**. The state file is consistent with `direction_version=6`, `evidence_tier=REPRODUCED`, `cycle_status=COMPLETED`, `continue_recommended=false`.

**No further fractal-map cycles are required under current factory direction.**

---

## Factory Direction v6 Requirements — All SATISFIED

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Reproduce hierarchical Leiden on `center_projected` embeddings | ✅ VERIFIED | `center_projected_hierarchical_results.json`: purity=0.9571, nesting=1.0 |
| Expose resolution ladder | ✅ VERIFIED | 7 levels: 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0 |
| Cluster metadata with legal coherence at each zoom level | ✅ VERIFIED | `cluster_metadata.json` with 108 hierarchical clusters |
| Integrate as DEFAULT map structure | ✅ VERIFIED | `center_projected_hierarchical` replaces `hierarchical_leiden_concat` |
| Legal-distance selectable modes | ✅ VERIFIED | 5 modes at ACCEPTED tier integrated in registry |

---

## Key Metrics (Re-verified)

### Center Projected Hierarchical Leiden (DEFAULT mode)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Hierarchical Purity (global) | **0.9571** | > 0.95 | ✅ PASS |
| Nesting Score | **1.0** | = 1.0 | ✅ PASS |
| Flat Mean Purity | 0.9341 | — | — |
| Purity Improvement vs Flat | +2.46% | > 0% | ✅ PASS |
| Purity Improvement vs Concat Baseline | +0.84% | > 0% | ✅ PASS |
| Hierarchical Clusters | 108 | > 0 | ✅ PASS |
| Resolution Ladder Levels | 7 | 7 | ✅ PASS |
| Zoom Coherence Improvement Rate | 31.1% | — | Documented |
| Adversarial Language Dominance | 0.7593 | < 0.85 | ✅ PASS |
| Jurist Pairwise Preference | 0.5215 | > 0.5 | ✅ PASS |
| Jurivoc Benchmarks Passed | 4/5 | — | Documented |

**Best Config:** `coarse_0.5_fine_3.0`  
**Corpus:** BGer 2020-2024 (1,000 decisions)  
**Embeddings:** `center_projected` (768 dim, pure, no TF-IDF)  
**Min Cluster Size Filter:** 3 (avoids singleton inflation)  
**Evidence Tier:** REPRODUCED  
**Validation Run:** `33207149474`

### Legacy Concat Baseline (Preserved for Comparison)

| Metric | Value |
|--------|-------|
| Hierarchical Purity (global) | 0.9491 |
| Nesting Score | 1.0 |
| Hierarchical Clusters | 98 |
| Zoom Coherence Improvement Rate | 59.2% (different methodology) |
| Evidence Tier | REPRODUCED |
| Status | LEGACY |

---

## Map Mode Registry — Complete

| Category | Modes | Count | Evidence Tier |
|----------|-------|-------|---------------|
| **DEFAULT** | `center_projected_hierarchical` | 1 | REPRODUCED |
| **Legal-Distance (ACCEPTED)** | `debiased_citation_blended`, `legal_cited_decisions_only`, `hybrid_alpha_03`, `hybrid_alpha_05`, `legal_issues_outcomes` | 5 | ACCEPTED |
| **Legacy** | `hierarchical_leiden_concat` | 1 | REPRODUCED |
| **Placeholder** | `center_projected` (raw embedding) | 1 | ACCEPTED |
| **TOTAL** | | **8** | |

**Warnings documented:**
- `hybrid_alpha_03`, `hybrid_alpha_05`: Fail adversarial_falsification benchmark
- `legal_issues_outcomes`: Fails adversarial_falsification, multilingual_invariance, citation_heritage threshold, tf_metadata_human_indexing threshold

---

## Verification Results

**Test Suite:** `tests/fractal_map/test_verify.py`  
**Total Tests:** 48  
**Passed:** 48  
**Failed:** 0

| Test Class | Tests | Status |
|------------|-------|--------|
| `TestArtifactIntegrity` | 18 | ✅ ALL PASS |
| `TestHierarchicalLeiden` | 6 | ✅ ALL PASS |
| `TestMetricConsistency` | 7 | ✅ ALL PASS |
| `TestLegacyConcatPreserved` | 10 | ✅ ALL PASS |
| `TestLegalDistanceModes` | 3 | ✅ ALL PASS |

---

## Accepted Branch Mirroring — RE-ESTABLISHED

| Component | Path | Artifacts |
|-----------|------|-----------|
| State File | `/tmp/lex_accepted/fractal_map/state/fractal_map.json` | 1 |
| Hierarchical Map (center_projected) | `/tmp/lex_accepted/fractal_map/results/fractal_map/hierarchical_map_center_projected/` | 17 |
| Hierarchical Map (legacy concat) | `/tmp/lex_accepted/fractal_map/results/fractal_map/hierarchical_map_legacy/` | 11 |
| Product Integration | `/tmp/lex_accepted/fractal_map/results/fractal_map/product_integration/` | 12 |
| Legal Distance Modes | `/tmp/lex_accepted/fractal_map/results/fractal_map/legal_distance_modes/` | 40 |
| Evaluation | `/tmp/lex_accepted/fractal_map/results/fractal_map/evaluation/` | 7 |
| Audit | `/tmp/lex_accepted/fractal_map/results/fractal_map/audit/` | 72 |
| **TOTAL** | | **160** |

**State file verified identical:** ✅

---

## Orchestration Diagnosis

### Pathology
Accepted branch mirroring at `/tmp/lex_accepted/fractal_map/` was lost due to `/tmp` directory volatility between GitHub workflow runs (run 33213103456 established mirroring, but run 33213824979 starts with clean `/tmp`).

### Root Cause
`/tmp` is ephemeral storage; accepted branch mirroring must be re-established as first step of every operational resume.

### Classification
**Orchestration completeness gap (environment volatility), NOT scientific failure.**

### Fix Applied
1. Created `/tmp/lex_accepted/fractal_map/state/` and `/tmp/lex_accepted/fractal_map/results/fractal_map/`
2. Mirrored `state/fractal-map.json` → `/tmp/lex_accepted/fractal_map/state/fractal_map.json`
3. Mirrored all 6 fractal-map result directories
4. Verified all 160 artifacts present
5. Re-ran all 48 verification tests — **all PASS**
6. Created audit gate atomically with mirroring

### Recommendation
Factory orchestration must verify `/tmp/lex_accepted` mirroring at start of every operational resume; consider persistent storage for accepted branches or automated re-mirror step.

---

## Negative Results Preserved (Per Research Protocol)

1. Flat Leiden nesting imperfect (mean ~0.50 across resolution ladder)
2. Some clusters already homogeneous at coarse resolution (no zoom improvement expected)
3. igraph version sensitivity: cluster counts vary but key invariants preserved (nesting=1.0, purity>0.94)
4. `legal_issues_outcomes` fails multilingual_invariance and adversarial_falsification benchmarks
5. Hybrid modes (`alpha_03`, `alpha_05`) fail adversarial_falsification benchmark

---

## Evidence Traceability

| Artifact | Location |
|----------|----------|
| Primary Results | `results/fractal_map/hierarchical_map_center_projected/center_projected_hierarchical_results.json` |
| Map Mode Registry | `results/fractal_map/product_integration/map_mode_registry.json` |
| Product Integration Spec | `results/fractal_map/product_integration/PRODUCT_INTEGRATION_SPEC.md` |
| Legal Distance Modes | `results/fractal_map/legal_distance_modes/` |
| Loader API | `results/fractal_map/product_integration/map_mode_loader.py` |
| Accepted Branch State | `/tmp/lex_accepted/fractal_map/state/fractal_map.json` |
| Accepted Branch Results | `/tmp/lex_accepted/fractal_map/results/fractal_map/` |
| State File (repo) | `state/fractal-map.json` |

### Audit Trail
1. `CYCLE_operational_resume_33132507730_GATE.json`
2. `CYCLE_operational_resume_33132986797_GATE.json`
3. `CYCLE_operational_resume_33133395447_GATE.json`
4. `CYCLE_operational_resume_33134184565_GATE.json`
5. `CYCLE_operational_resume_33134755365_GATE.json`
6. `CYCLE_operational_resume_33135281890_GATE.json`
7. `CYCLE_center_projected_hierarchical_v5_33137354250_GATE.json`
8. `CYCLE_center_projected_hierarchical_v6_33139587950_GATE.json`
9. `CYCLE_operational_resume_33207149474_GATE.json`
10. `CYCLE_operational_resume_33209861284_GATE.json`
11. `CYCLE_operational_resume_33211353804_GATE.json`
12. `CYCLE_operational_resume_33212512155_GATE.json`
13. `CYCLE_operational_resume_33213824979_GATE.json`
14. **`CYCLE_operational_resume_33214267286_GATE.json` (THIS RUN)**

---

## Final Verdict

**GATE: PASS**

The fractal-map lane has successfully completed all Factory Direction v6 requirements. The hierarchical Leiden fractal map on `center_projected` embeddings is validated, productized as the DEFAULT map mode, and integrated with 5 legal-distance selectable modes at ACCEPTED tier. The deliverable is audit-ready with full evidence traceability, negative results preserved, and accepted branch mirroring re-established.

**Next Action:** Factory Director may promote to PRODUCTIZE. No further fractal-map cycles under v6.
