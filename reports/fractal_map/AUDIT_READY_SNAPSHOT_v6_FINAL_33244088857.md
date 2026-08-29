# Fractal Map Lane — Audit-Ready Snapshot v6 (GitHub Run 33244088857)

**Lane:** fractal-map  
**Factory Direction Version:** 6  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  
**Next Recommendation:** PRODUCTIZE  
**Accepted Run ID:** center_projected_hierarchical_v6_final_audit_33244088857  
**Timestamp:** 2026-08-29T08:55:00Z  
**Operational Resume From:** 33243676197  

---

## Executive Summary

**FACTORY DIRECTION v6 COMPLETE** — All fractal-map lane objectives for v6 have been satisfied and independently verified.

The **center_projected_hierarchical** (Center Projected Hierarchical Leiden) is now the **DEFAULT map mode**, replacing the concat-based hierarchical_leiden. This was validated on 1,000 BGer decisions (2020–2024) using center_projected embeddings (768-dim, pure, no TF-IDF).

### Key Validated Metrics

| Metric | Value | Baseline (concat) | Status |
|--------|-------|-------------------|--------|
| Hierarchical purity (min_size=3) | **0.9571** | 0.9491 | ✅ +0.0080 |
| Perfect nesting | **1.0** | 1.0 | ✅ Guaranteed |
| Resolution ladder | **7 levels** | 7 levels | ✅ 5→7→9→11→14→16→19 |
| Hierarchical clusters (validated) | **108** (91 size≥3) | 98 | ✅ +10 |
| Zoom coherence improvement rate | **62.96%** | 59.18% | ✅ +3.78% |
| Adversarial language dominance | 0.7593 (< 0.85) | — | ✅ PASS (v5 carried forward) |
| Jurist pairwise preference | 0.5215 (> 0.5) | — | ✅ PASS (v5 carried forward) |
| Jurivoc hierarchy alignment | 4/5 PASS | — | ✅ PASS (v5 carried forward) |

---

## Deliverables Verified

### 1. Hierarchical Map Artifacts (`results/fractal_map/hierarchical_map_center_projected/`)
- `center_projected_hierarchical_results.json` — Complete experimental results with best_config=`coarse_0.5_fine_3.0`
- `hierarchical_map_results.json` — Full hierarchical structure
- `cluster_assignments.json` — Decision-to-cluster mappings for all 7 resolutions
- `cluster_metadata.json` — Legal context per cluster (branch, area, chamber, language)
- `zoom_mappings.json` — Bidirectional parent-child navigation (6 resolution transitions)
- `zoom_coherence.json` — Per-cluster zoom improvement metrics
- `decision_clusters.json` — Decision index (1000 × 7 resolutions)
- 9 label arrays (`.npy`): 7 resolutions + hierarchical_best + coarse_0.5

### 2. Map Mode Registry — 8 Modes Operational
| Mode ID | Type | Status | Evidence Tier |
|---------|------|--------|---------------|
| **center_projected_hierarchical** | hierarchical_leiden | **DEFAULT** | REPRODUCED |
| hierarchical_leiden_concat | hierarchical_leiden | legacy | REPRODUCED |
| debiased_citation_blended | legal_distance | available | ACCEPTED (14/14) |
| legal_cited_decisions_only | legal_distance | available | ACCEPTED (14/14) |
| hybrid_alpha_03 | legal_distance | available | ACCEPTED (13/14) ⚠️ |
| hybrid_alpha_05 | legal_distance | available | ACCEPTED (13/14) ⚠️ |
| legal_issues_outcomes | legal_distance | available | ACCEPTED (10/14) ⚠️ |
| center_projected | placeholder | placeholder | ACCEPTED |

⚠️ = warnings for failed adversarial/multilingual benchmarks (documented in registry)

### 3. Product Integration (`results/fractal_map/product_integration/`)
- `PRODUCT_INTEGRATION_SPEC.md` — Complete specification for product lane
- `map_mode_registry.json` / `map_mode_registry.py` — Machine-readable registry
- `map_mode_loader.py` — Unified loader API for all 8 modes
- `product_map_loader.py` — Product-facing simplified API
- `integration_summary.json` / `cluster_metadata.json` / `zoom_mappings.json` / `zoom_coherence.json` / `decision_clusters.json`

### 4. Verification Tests
**48/48 tests PASS** — All artifact integrity, hierarchical metrics, state consistency, legacy preservation, and legal-distance mode integration tests pass.

---

## Orchestration Gap Resolution

**Diagnosed Issue:** `/tmp/lex_accepted/fractal_map/` mirroring was lost due to ephemeral storage volatility between GitHub Actions runs.

**Fix Applied (re-verified in this run):**
- Re-established mirror with **273 artifacts** copied from `results/fractal_map/`
- Re-ran all 48 verification tests — **ALL PASS**
- Validated loader API across all 8 modes
- Verified state file consistency (diff clean between repo and accepted branch)
- Snapshot confirmed **audit-ready**

---

## Evidence Provenance

All claim-bearing results trace to:
- `results/fractal_map/hierarchical_map_center_projected/center_projected_hierarchical_results.json`
- `results/fractal_map/evaluation/center_projected_hierarchical_zoom_validation_results.json`
- `results/fractal_map/product_integration/PRODUCT_INTEGRATION_SPEC.md`
- `state/fractal-map.json` (canonical state file)

Frozen evaluation harness: **evaluation v2** (carried forward from run 33137354250) with global seed=42.

---

## Dependencies for Next Phase

| Dependency | Owner | Status |
|------------|-------|--------|
| Legal-distance: reproduce center_projected on full v1+v2 benchmark suite | legal-distance | PENDING |
| Corpus: scale to full 2000–2024 (~192k decisions) | corpus | PENDING |
| Product: consume center_projected_hierarchical artifacts | product | READY |

---

## Audit Gates

| Gate | Status | Evidence |
|------|--------|----------|
| Artifact completeness | ✅ PASS | 273 artifacts mirrored, 48/48 tests pass |
| Metric reproducibility | ✅ PASS | State metrics match recomputed values (abs diff < 1e-6) |
| Hierarchical validity | ✅ PASS | Nesting=1.0, purity=0.9571, 108 clusters |
| Zoom coherence superiority | ✅ PASS | 62.96% > 59.18% concat baseline |
| Multi-mode integration | ✅ PASS | 8 modes loadable via unified API |
| Legacy preservation | ✅ PASS | Concat baseline artifacts intact |
| State consistency | ✅ PASS | fractal-map.json updated, diff verified |

---

## Final Verdict

**AUDIT STATUS: PASS**

The fractal-map lane has **completed all factory direction v6 requirements**. The center_projected_hierarchical map mode is validated, integrated, and ready for productization. The snapshot is frozen and audit-ready.

**Next Action:** Factory Director to promote to PRODUCTIZE; product lane consumes artifacts from `results/fractal_map/hierarchical_map_center_projected/`.

---

*Generated: 2026-08-29T08:55:00Z | Lane: fractal-map | Factory Direction: v6 | Run: 33244088857*
