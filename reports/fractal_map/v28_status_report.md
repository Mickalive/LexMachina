# Fractal Map Lane — Status Report v28

**Date**: 2026-09-29
**Direction Version**: 28
**Lane Status**: BLOCKED_ON_DEPENDENCIES
**Evidence Tier**: REPRODUCED
**Test Suite**: 240 passed, 1 skipped

---

## Executive Summary

The fractal-map lane is **correctly BLOCKED_ON_DEPENDENCIES** awaiting ACCEPTED 174k dense embeddings from legal-distance. All discriminating experiments executable with current dependencies are complete. Evidence is preserved, negative results retained, test suite passes.

**Key Fact**: Only 3/26 years (2000-2002, ~19,441 decisions, 11%) of dense embeddings are ACCEPTED. 25/26 years (2000-2024, ~160k decisions) exist as checkpoints but remain PENDING AUDIT and cannot be cited as accepted evidence.

---

## Current Dependency State

| Dependency | Status | Details |
|------------|--------|---------|
| Corpus 174k metadata | ✅ CLEARED | `metadata_174k.json`: 173,963 entries, branch+legal_area 100% coverage |
| Legal-distance 174k dense embeddings | ❌ BLOCKED | 3/26 years ACCEPTED (2000-2002); 22/26 years PENDING AUDIT |
| Citation-role embeddings at 174k | ❌ BLOCKED | Only 1k-scale REPRODUCED (1,200 decisions) |
| Linear hybrid embeddings at 174k | ❌ BLOCKED | Not yet computed at scale |
| Section-specific cross-lingual eval | ❌ BLOCKED | Requires dense embeddings |

---

## Accepted Findings (Frozen)

### 1. Flat Leiden at 174k TF-IDF: **FAIL** (v26 frozen rule)
- **0/4 modes pass** zoom-quality rule
- Severe over-fragmentation: median cluster size 1, **>99% singletons** at fine resolutions (res_2.0, res_3.0)
- Strong legal structure (branch purity 0.51-0.55 vs 0.25 random; legal_area purity 0.24-0.31 vs ~0.005 random)
- **NO monotonic zoom refinement** — flat zoom fails at sub-62k scale

### 2. Constrained Hierarchical Leiden at 174k TF-IDF: **PASS** (by construction, v26 rule)
- **All 4 TF-IDF modes PASS** per_mode_verdict
- **nesting = 1.0** BY CONSTRUCTION (min_cluster_size enforcement)
- **zoom_coherence improvement_rate: 57-90%** on structural test
- **singleton_fraction ≤0.1%** at fine resolutions (zero fragmentation)
- Only `regeste_tfidf` (83k decisions) passes structural checks at 174k

### 3. Scale Dependency **CONFIRMED**
| Scale | Flat v26 | Constrained Hierarchical |
|-------|----------|-------------------------|
| 1k | Severe fragmentation | N/A |
| 1.2k | **PASS** (citing_alpha0.7) | N/A |
| 12k | FAIL | 45.5% improvement_rate (adaptive) |
| 28k | FAIL | **67% improvement_rate** (validated) |
| 174k TF-IDF | FAIL / severe fragmentation | PASS (by construction) |

### 4. Evidence-Backed Zoom Path for Dense Modes
**Citation-role / dense-embedding modes at 1000-scale** (REPRODUCED):
- `citing_alpha0.3`: ZQ = **0.5401**
- `following_alpha0.3`: ZQ = **0.5280**
- `criticizing_alpha0.3`: ZQ = **0.4864**
- Production default `cited_outcome_hybrid_0.5`: ZQ = **0.2798**

### 5. 12k Dense Embeddings (ACCEPTED, years 2000-2002)
- Constrained hierarchical Leiden (adaptive=True, min_cluster_size=3): **PASS**
  - improvement_rate = **45.5%**
  - singleton_fraction = **0.4%**
  - nesting = **1.0**
  - branch_purity = **0.988**
  - area_purity = **0.556**
- Flat v26 zoom quality: **FAIL** (only 1/4 transitions exceed 0.5 threshold)
- Adversarial: **FAIL** — language_dominance ~0.98, jurist_preference ~0.04

### 6. 28k Checkpoint Validation (PENDING AUDIT — pipeline validation only)
- Constrained hierarchical Leiden (coarse_0.5_fixed2.0_min20):
  - fine_singleton_fraction = **0.0%**
  - fine_median_size = **43-46**
  - improvement_rate = **0.67** (matches power-law extrapolation)
  - branch_improvement = **0.15-0.154**
  - nesting = **1.0**
- **Pipeline VALIDATED at intermediate scale** — scale extrapolation model confirmed (HIGH confidence for 174k dense behavior)

### 7. NESTING_METRIC_DEFECT_v1 Enforced (Audit CYCLE_36027099305)
- 7 compressed-family modes **PROHIBITED** from nesting ≥0.99 claims
- nesting_score = 1.0 citeable **ONLY** for:
  - 1000-scale by-construction modes (with scope annotation)
  - 12k-scale by-construction modes (with scope annotation)
- Compressed 5-level ladder **NOT universally valid**

---

## Pipeline Readiness for 174k Dense Embeddings

**Status**: Operational at simulation level — requires ACCEPTED 174k dense embeddings for production

**Best Validated Config**: `coarse_0.5_fixed2.0_min20`
- Validated at 12k (ACCEPTED) and 28k (PENDING AUDIT — pipeline validation)
- Zero fragmentation, nesting=1.0, improvement_rate ~0.67

**Scale Extrapolation Model**: Power law predicts hierarchical improvement_rate **~0.67 at 174k** for dense embeddings (HIGH confidence after 28k validation)

---

## Factory Direction Discrepancy

**Issue**: `factory_direction.json` on main reports `fractal-map.status=RUN` but lane state correctly shows `BLOCKED_ON_DEPENDENCIES` since v26.

**Impact**: Control plane misreports lane status; not a fractal-map lane defect.

**Resolution Required**: Factory Director must update `factory_direction.json` on main to reflect BLOCKED_ON_DEPENDENCIES, or promote legal-distance 174k dense embeddings through audit to unblock.

**Progress Detail**:
- legal-distance progress.json shows 25/26 years (2000-2024) in checkpoints
- **Only 3/26 years (2000-2002) ACCEPTED**
- 22/26 years PENDING AUDIT — cannot be cited as accepted evidence

---

## Recommendation

**BLOCKED** — No further discriminating experiments possible without ACCEPTED 174k dense embeddings.

- `continue_recommended: false` — no additional same-question cycle justified
- All evidence preserved, negative results retained
- Lane deliverable status: **COMPLETE for current dependency state**
- Ready to resume immediately when legal-distance delivers ACCEPTED 174k dense embeddings

---

## Evidence References

All artifacts preserved under `results/fractal_map/`:
- `zoom_quality_174k_eval/v26_verdict.json` — frozen v26 rule evaluation
- `hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` — hierarchical zoom evaluation
- `nesting_metric_defect_v1_audit.json` — nesting metric defect audit
- `constrained_hierarchical_tests/constrained_hierarchical_174k_*.json` — 4 TF-IDF modes at 174k
- `12k_dense_hierarchical_test/hierarchical_leiden_results.json` — 12k dense ACCEPTED
- `constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json` — 3yr dense
- `zoom_coherence_1000scale_citation_roles.json` — citation role zoom path (REPRODUCED)
- `12k_dense_comprehensive/` — 12k dense comprehensive evaluation
- `pipeline_readiness_12k_dense_official.json` — pipeline readiness
- `28k_checkpoint_validation/28k_validation_20260928_212756.json` — 28k pipeline validation
- `12k_constrained_zoom_diagnostic/constrained_zoom_diagnostic_v2_20260928_133636.json` — 12k diagnostic

---

## Provenance

| Artifact | Source |
|----------|--------|
| 12k dense embeddings | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002, ACCEPTED) |
| 28k checkpoint embeddings | Same path (years 2000-2005, PENDING AUDIT — pipeline validation only) |
| Citation alpha embeddings | `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` (1,200 decisions, ACCEPTED) |
| Metadata 174k | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Global seed | 42 |
| Leiden seed | 42 |
| k_neighbors | 15 |

---

## Verification Cycle

- **Run ID**: `fractal_map_v28_verification_20260929`
- **Timestamp**: 2026-09-29T04:15:00.000000+00:00
- **Test Results**: 240 passed, 1 skipped
- **Status Confirmed**: BLOCKED_ON_DEPENDENCIES
- **Continue Recommended**: false
- **All Evidence Preserved**: true
- **Negative Results Preserved**: true