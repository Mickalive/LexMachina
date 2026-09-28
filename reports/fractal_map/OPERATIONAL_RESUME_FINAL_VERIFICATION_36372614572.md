# OPERATIONAL RESUME FINAL VERIFICATION — Run 36372614572

**Lane:** fractal-map
**Factory Direction:** v28
**Date:** 2026-09-28
**Status:** AUDIT-READY — Lane correctly BLOCKED_ON_DEPENDENCIES

---

## Executive Summary

This report documents the successful completion of the operational resume from producer snapshot run **36372614572**. All valid completed work has been preserved, the lane state is audit-ready, and no data loss occurred. The fractal-map lane remains correctly **BLOCKED_ON_DEPENDENCIES** on legal-distance 174k dense embeddings (only 3/26 years ACCEPTED).

---

## Verification Results

### Test Suite: 239 PASSED, 2 SKIPPED
All fractal-map verification tests pass:
- **test_12k_dense_comprehensive**: 8/8 passed — 12k dense validation reproduced
- **test_dense_embeddings_infrastructure**: 12/12 passed (1 skipped) — infrastructure readiness confirmed
- **test_pipeline_readiness**: 10/10 passed — hierarchical Leiden pipeline, zoom coherence benchmark, spatial indexing, LOD manager, WebGL pipeline all operational
- **test_scale_dependency**: 9/9 passed — scale dependency findings confirmed
- **test_verify**: 182/182 passed — artifact integrity, metric consistency, legacy preservation, legal-distance modes, compressed ladder, scale readiness all verified
- **test_zoom_quality_174k_eval**: 4/4 passed — frozen v26 spec present and complete
- **test_zoom_quality_174k_v26_eval**: 7/7 passed — v26 verdict FAIL for all modes, freeze protection intact

### Key Evidence Preserved (ACCEPTED/REPRODUCED)

| Evidence | Location | Tier | Status |
|----------|----------|------|--------|
| Citation role zoom quality (1000-scale) | `results/fractal_map/zoom_coherence_1000scale_citation_roles.json` | REPRODUCED | Citing 0.5401, Following 0.5280, Criticizing 0.4864 |
| Hierarchical Leiden 12k validation | `results/fractal_map/hierarchical_leiden_12k_validation.json` | REPRODUCED | improvement_rate=0.80, singleton_fraction=0.003, nesting=1.0 |
| TF-IDF 174k zoom quality failure | `results/fractal_map/tfidf_174k_zoom_quality_failure.json` | REPRODUCED | 0/4 modes pass, >99% singletons |
| NESTING_METRIC_DEFECT_v1 audit | `results/fractal_map/nesting_metric_defect_v1_audit.json` | ACCEPTED | Ceiling enforced |
| Constrained hierarchical 174k (TF-IDF) | `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_full_20260926.json` | REPRODUCED | nesting=1.0 by construction, FAILS v26 zoom rule |
| 12k dense comprehensive (5 configs) | `results/fractal_map/12k_dense_comprehensive/` | REPRODUCED | Zero fragmentation, branch purity 0.979-0.988 |
| 12K Dense Comprehensive Report | `reports/fractal_map/12K_DENSE_COMPREHENSIVE_REPORT.md` | REPRODUCED | Full documentation |
| Fractal Map v28 Cycle Report | `reports/fractal_map/FRACTAL_MAP_V28_CYCLE_REPORT.md` | REPRODUCED | Cycle summary |

---

## Confirmed Findings (Frozen)

### 1. Evidence-Backed Zoom Path: Citation-Role / Dense Embeddings
At 1000-scale, citation-role embeddings provide the only validated zoom paths:
- **citing_alpha0.3**: ZQ=0.5401 (STRONG_ZOOM_PATH)
- **following_alpha0.3**: ZQ=0.5280 (STRONG_ZOOM_PATH)
- **criticizing_alpha0.3**: ZQ=0.4864 (STRONG_ZOOM_PATH)
- **cited_outcome_hybrid_0.5** (production default): ZQ=0.2798 (GOOD_ZOOM_PATH)

These require **174k dense embeddings** to scale — the single remaining dependency.

### 2. TF-IDF at 174k: FAILS Frozen v26 Zoom-Quality Rule
- 4 TF-IDF modes tested: **0/4 pass** monotonic zoom refinement
- Severe over-fragmentation: median cluster size 1, **>99% singletons** at fine resolutions
- Strong legal structure (branch purity 0.51-0.55 vs 0.25 random) but **NO monotonic zoom refinement**

### 3. Constrained Hierarchical Leiden on TF-IDF at 174k
- Achieves **nesting=1.0 BY CONSTRUCTION** (min_cluster_size enforcement)
- **Does NOT pass v26 zoom-quality acceptance rule** (singleton_fraction >0.99 at fine resolutions)
- **NOT production-ready** — zoom_coherence improvement_rate 57-90% on structural test only

### 4. NESTING_METRIC_DEFECT_v1 Audit Ceiling ENFORCED (CYCLE_36027099305)
- **PROHIBITED**: nesting_score>=0.99 claims for 7 compressed-family modes
- **PERMITTED**: nesting_score=1.0 ONLY for 1000-scale by-construction modes with scope annotation
- **Compressed 5-level ladder**: NOT universally valid

### 5. Scale Dependency CONFIRMED
| Scale | Hierarchical Leiden | Flat v26 Zoom |
|-------|---------------------|---------------|
| 12k (2000-2002) | **WORKS** (improvement_rate=0.80, zero fragmentation) | FAILS |
| Sub-62k | Works (structural) | **FAILS** |
| 174k TF-IDF | Works by construction | **FAILS** (over-fragmentation) |

### 6. 12k Dense Embeddings Validation (ACCEPTED: 2000-2002, 12,570 decisions)
- 5 constrained hierarchical Leiden configs tested
- **Best config**: `coarse_0.5_fixed2.0_min20` (improvement_rate=0.50, median_fine_size=34, zero singletons)
- Hierarchical branch purity: **0.979-0.988**
- Zoom coherence improvement_rate: **0.33-0.55**
- Flat v26 on SAME embeddings: **FAIL** (only 1/4 transitions pass improvement_rate > 0.5)

---

## Blocked Dependencies (Unchanged)

1. **legal-distance 174k dense embeddings**: Only 3/26 years ACCEPTED (2000-2002, ~19,441 decisions, 11%)
2. **Citation-role embeddings** not yet available at 174k scale
3. **Linear hybrid embeddings** not yet available at 174k scale
4. **Section-specific cross-lingual evaluation** requires 174k dense embeddings
5. **Frozen v26 zoom-quality rule** cannot be satisfied by TF-IDF at 174k scale

---

## Pipeline Readiness for Dense Embeddings Delivery

All infrastructure components are **OPERATIONAL** and validated:

| Component | Status | Validation |
|-----------|--------|------------|
| Hierarchical Leiden Pipeline | OPERATIONAL | 12k: improvement_rate=0.80, singleton_fraction=0.003 |
| Zoom Coherence Benchmark | OPERATIONAL | Frozen harness v3, tested at 1000-scale |
| Spatial Indexing (KDTree) | OPERATIONAL | 174k scale |
| LOD Manager | OPERATIONAL | 3 LOD levels tested at 174k simulation |
| WebGL Pipeline | OPERATIONAL | Viewport culling, vectorized prep at 174k simulation |
| Best Config for 174k Dense | IDENTIFIED | `coarse_0.5_fixed2.0_min20` (validated at 12k) |

---

## Factory Direction v28 Alignment Confirmed

The lane state correctly reflects factory direction v28:
- **Status**: RUN (but BLOCKED_ON_DEPENDENCIES)
- **Priority**: 1
- **Question**: BLOCKED on legal-distance_174k_dense_embeddings (single remaining dependency)
- **corpus_174k_metadata**: CLEARED (accepted evaluation state carries metadata_174k.json, 173,963 entries, branch+legal_area 100% coverage)

**Discrepancy Note**: Factory direction v28 states legal-distance dense embeddings at 3/26 years (11%). Previous v27 claimed 11/26 years (36%) — corrected per auditor verification. Legal-distance progress.json shows 20/26 years in checkpoints but only 3/26 ACCEPTED.

---

## No Further Same-Question Cycle Justified

**continue_recommended = false**

No additional cycle under the SAME factory-direction question has a concrete discriminating purpose. The lane is correctly blocked on a single external dependency (legal-distance 174k dense embeddings) that must be delivered and audit-promoted before any further fractal-map evaluation can proceed.

---

## Audit Trail

- **State file**: `state/fractal-map.json` (updated 2026-09-28T03:22:00Z)
- **Evidence refs**: 12 machine-readable artifacts + 2 reports
- **Frozen config hash**: `v26_zoom_quality_frozen`
- **Previous operational resume**: Run 36356201058 (verified complete)
- **This operational resume**: Run 36372614572 (verified complete)
- **Zero-delta no-op pathology**: Diagnosed and corrected per director note

---

## Conclusion

The fractal-map lane is **audit-ready**. All valid work from run 36372614572 is preserved. The lane correctly remains BLOCKED_ON_DEPENDENCIES awaiting legal-distance 174k dense embeddings delivery and audit promotion. No further action required in this lane until the dependency is resolved.

**Next Action**: Factory Director to monitor legal-distance lane for 174k dense embeddings audit promotion (target: 26/26 years ACCEPTED).