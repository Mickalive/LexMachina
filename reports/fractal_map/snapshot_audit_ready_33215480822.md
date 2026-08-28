# Fractal-Map Lane — Snapshot Audit-Ready Report (Run 33215480822)

**Lane:** fractal-map  
**Factory Direction:** v6  
**GitHub Run:** 33215480822  
**Operational Resume From:** 33214779571  
**Timestamp:** 2026-08-28T22:03:00Z  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Gate:** PASS  
**Next Recommendation:** PRODUCTIZE  

---

## Executive Summary

The fractal-map lane has **successfully completed all Factory Direction v6 requirements**. The hierarchical Leiden fractal map on `center_projected` embeddings is validated, productized as the **DEFAULT map mode**, and integrated with **5 legal-distance selectable modes at ACCEPTED tier**. The deliverable is **audit-ready** with full evidence traceability, negative results preserved, accepted branch mirroring re-established and verified (219 artifacts), and loader API functional.

**No further fractal-map cycles under v6 are needed.** The Factory Director may promote to PRODUCTIZE.

---

## Orchestration Failure Diagnosed & Fixed

### Pathology
Accepted branch mirroring at `/tmp/lex_accepted/fractal_map/` was lost due to `/tmp` directory volatility between GitHub workflow runs (previously re-established in run 33214267286 and verified in 33214779571, but not persisted to current run 33215480822).

### Root Cause
`/tmp` is ephemeral storage; accepted branch mirroring must be re-established as first step of every operational resume.

### Classification
**Orchestration completeness gap (environment volatility), NOT scientific failure.**

### Fix Applied (This Run)
1. ✅ Re-established `/tmp/lex_accepted/fractal_map/` mirroring from validated source (219 artifacts confirmed)
2. ✅ Copied `state/fractal-map.json` and all `results/fractal_map/` to accepted branch mirror
3. ✅ Verified state file consistency between repo and accepted branch
4. ✅ Updated state files with current `github_run` (33215480822) and `operational_resume_from` (33214779571)
5. ✅ Verified all key artifacts present
6. ✅ Created audit gate atomically with verification

### Recommendation for Factory Orchestration
Factory orchestration must verify `/tmp/lex_accepted` mirroring at start of every operational resume; consider persistent storage for accepted branches or automated re-mirror step.

---

## Factory Direction v6 Requirements — ALL VERIFIED

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Reproduce hierarchical Leiden on center_projected | ✅ VERIFIED | `center_projected_hierarchical_results.json`: purity=0.9571, nesting=1.0, best_config=coarse_0.5_fine_3.0 |
| Expose resolution ladder | ✅ VERIFIED | 7 levels: 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0 with label arrays for each |
| Cluster metadata & legal coherence at each zoom level | ✅ VERIFIED | `cluster_metadata.json` with 108 hierarchical clusters, branch/area/chamber/language per cluster |
| Integrate as default map structure | ✅ VERIFIED | `center_projected_hierarchical` replaces `hierarchical_leiden_concat` as default in `map_mode_registry.json` |
| Legal-distance selectable modes | ✅ VERIFIED | 5 modes at ACCEPTED tier: debiased_citation_blended, legal_cited_decisions_only, hybrid_alpha_03, hybrid_alpha_05, legal_issues_outcomes |

---

## Key Metrics (Frozen Before Observation)

### Center Projected Hierarchical (DEFAULT)
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Hierarchical Purity (global) | 0.9571 | ≥ 0.95 | ✅ PASS |
| Nesting Score | 1.0 | = 1.0 | ✅ PASS |
| Flat Mean Purity | 0.9341 | — | — |
| Zoom Coherence Improvement Rate | 31.1% | > 0% | ✅ PASS |
| Hierarchical Clusters | 108 | — | — |
| Resolution Ladder Levels | 7 | 7 | ✅ PASS |
| Adversarial Language Dominance | 0.7593 | < 0.85 | ✅ PASS* |
| Jurist Pairwise Preference | 0.5215 | > 0.5 | ✅ PASS* |
| Jurivoc Benchmarks | 4/5 | ≥ 3/5 | ✅ PASS* |
| Min Cluster Size Filter | 3 | — | Applied |

*Source: evaluation_v2_cycle_33137354250 (carried forward, not independently recomputed in v6)

### Legacy Concat Baseline (Preserved for Comparison)
| Metric | Value |
|--------|-------|
| Hierarchical Purity (global) | 0.9491 |
| Nesting Score | 1.0 |
| Hierarchical Clusters | 98 |
| Zoom Coherence Improvement Rate | 59.2% (different methodology) |

### Improvement Over Concat Baseline
- **Purity improvement**: +0.0080 (0.84%)
- **Hierarchical clusters**: +10 (108 vs 98)

---

## Map Mode Registry — 8 Modes Total

| Mode ID | Type | Status | Tier | Default | Benchmarks |
|---------|------|--------|------|---------|------------|
| center_projected_hierarchical | hierarchical_leiden | available | REPRODUCED | ✅ | N/A (map structure) |
| hierarchical_leiden_concat | hierarchical_leiden | legacy | REPRODUCED | ❌ | N/A |
| debiased_citation_blended | legal_distance | available | ACCEPTED | ❌ | 14/14 PASS |
| legal_cited_decisions_only | legal_distance | available | ACCEPTED | ❌ | 14/14 PASS |
| hybrid_alpha_03 | legal_distance | available | ACCEPTED | ❌ | 13/14 PASS ⚠️ fails adversarial_falsification |
| hybrid_alpha_05 | legal_distance | available | ACCEPTED | ❌ | 13/14 PASS ⚠️ fails adversarial_falsification |
| legal_issues_outcomes | legal_distance | available | ACCEPTED | ❌ | 10/14 PASS ⚠️ fails 4 benchmarks |
| center_projected | legal_distance | placeholder | ACCEPTED | ❌ | pending reproduction |

---

## Loader API Verification

All API methods functional:

| Method | Status | Details |
|--------|--------|---------|
| `list_modes()` | ✅ PASS | 8 modes listed correctly |
| `load_default()` | ✅ PASS | center_projected_hierarchical loads with 9 label arrays |
| `get_resolution_labels(mode, res)` | ✅ PASS | All 7 resolutions return correct cluster counts |
| `get_hierarchical_labels(mode)` | ✅ PASS | 108 hierarchical clusters |
| `get_coarse_labels(mode)` | ✅ PASS | 7 parent clusters at res 0.5 |
| `get_zoom_mapping(mode, from, to)` | ✅ PASS | Parent-child mappings for all adjacent resolutions |
| `get_decision_clusters(mode, decision_id)` | ✅ PASS | Decision lookup by ID works |
| `get_cluster_metadata(mode, res)` | ✅ PASS | Legal context per cluster |
| `get_zoom_coherence(mode, from, to)` | ✅ PASS | Per-cluster improvement metrics per resolution step |

---

## Negative Results Preserved (First-Class Evidence)

1. **Flat Leiden nesting imperfect** — mean ~0.50 across resolution ladder (not a failure; expected for non-hierarchical method)
2. **Some clusters already homogeneous at coarse resolution** — no zoom improvement expected (correct behavior)
3. **igraph version sensitivity** — cluster counts vary but key invariants preserved (nesting=1.0, purity>0.94)
4. **legal_issues_outcomes fails multilingual_invariance and adversarial_falsification benchmarks** — marked with warnings
5. **Hybrid modes (alpha_03, alpha_05) fail adversarial_falsification benchmark** — marked with warnings
6. **Zoom coherence methodology difference** — per-resolution-step (31.1%) vs hierarchical_zoom_validation (59.2% for concat baseline); both reported transparently

---

## Evidence Traceability

| Artifact | Path |
|----------|------|
| Primary Results | `results/fractal_map/hierarchical_map_center_projected/center_projected_hierarchical_results.json` |
| Map Mode Registry | `results/fractal_map/product_integration/map_mode_registry.json` |
| Product Integration Spec | `results/fractal_map/product_integration/PRODUCT_INTEGRATION_SPEC.md` |
| Legal Distance Modes | `results/fractal_map/legal_distance_modes/` |
| Loader API | `results/fractal_map/product_integration/map_mode_loader.py` |
| Accepted Branch State | `/tmp/lex_accepted/fractal_map/state/fractal_map.json` |
| Accepted Branch Results | `/tmp/lex_accepted/fractal_map/results/fractal_map/` |
| State File (Repo) | `state/fractal-map.json` |

---

## Audit Trail (Complete)

16 audit gates preserved from v4→v6:
- CYCLE_operational_resume_33132507730_GATE.json
- CYCLE_operational_resume_33132986797_GATE.json
- CYCLE_operational_resume_33133395447_GATE.json
- CYCLE_operational_resume_33134184565_GATE.json
- CYCLE_operational_resume_33134755365_GATE.json
- CYCLE_operational_resume_33135281890_GATE.json
- CYCLE_center_projected_hierarchical_v5_33137354250_GATE.json
- CYCLE_center_projected_hierarchical_v6_33139587950_GATE.json
- CYCLE_operational_resume_33207149474_GATE.json
- CYCLE_operational_resume_33209861284_GATE.json
- CYCLE_operational_resume_33211353804_GATE.json
- CYCLE_operational_resume_33212512155_GATE.json
- CYCLE_operational_resume_33213824979_GATE.json
- CYCLE_operational_resume_33214267286_GATE.json
- CYCLE_operational_resume_33214779571_GATE.json
- **CYCLE_operational_resume_33215480822_GATE.json (THIS RUN)**

---

## Product Integration Ready

The product lane can now consume:
- **Default map artifacts**: `results/fractal_map/hierarchical_map_center_projected/`
- **Map mode registry**: `results/fractal_map/product_integration/map_mode_registry.json`
- **Unified loader API**: `results/fractal_map/product_integration/map_mode_loader.py`
- **Integration spec**: `results/fractal_map/product_integration/PRODUCT_INTEGRATION_SPEC.md`

### Recommended Product Flows (from integration spec)
- **Flow A**: Domain → Subdomain → Microcluster (Center Projected Hierarchical Leiden)
- **Flow B**: Search → Context Zoom
- **Flow C**: Decision Inspection
- **Flow D**: Map Mode Switching (8 modes available)

---

## Dependencies for Next Factory Direction

1. **Legal-Distance Lane**: Must reproduce `center_projected` on full v1+v2 benchmark suite for legal-distance mode integration
2. **Corpus Lane**: Scale to full 2000-2024 corpus (~192k decisions) — current validation on 1000 decisions (2020-2024)
3. **Product Lane**: Implement map mode selector UI, side-by-side comparison view

---

## Final Verdict

**GATE: PASS** — The fractal-map lane has successfully completed all Factory Direction v6 requirements. The hierarchical Leiden fractal map on center_projected embeddings is validated, productized as the DEFAULT map mode, and integrated with 5 legal-distance selectable modes at ACCEPTED tier. The deliverable is audit-ready with full evidence traceability, negative results preserved, accepted branch mirroring re-established and verified (219 artifacts), and loader API functional.

**Next Action**: Factory Director may promote to PRODUCTIZE. No further fractal-map cycles under v6.