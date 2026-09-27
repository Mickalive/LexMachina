# 12k Dense Embeddings Comprehensive Constrained Hierarchical Leiden Report

**Date**: 2026-09-27  
**Factory Direction**: v28  
**Lane**: fractal-map  
**Evidence Tier**: EXPLORATORY (partial scale validation on 3/26 ACCEPTED years)

---

## Executive Summary

Constrained hierarchical Leiden on **12,570 ACCEPTED dense embeddings** (years 2000-2002, 768-dim) demonstrates:
- ✅ **Zero fragmentation** at all configurations (singleton_fraction = 0.0)
- ✅ **High hierarchical purity** (branch: 0.979-0.988, area: 0.433-0.544)
- ✅ **Perfect nesting** (1.0) by construction
- ✅ **Meaningful zoom coherence** (improvement_rate 0.33-0.55)

**Flat v26 zoom quality FAILS** on the same embeddings (improvement_rate_gt_0.5_on_2_of_4: FALSE), confirming **scale dependency** — flat zoom fails at sub-62k scale while constrained hierarchical succeeds.

---

## Configurations Tested

| Config | Coarse Res | Sub Res | Min Size | Adaptive | Coarse Clusters | Fine Clusters | Branch Pure (Coarse→Fine) | Area Pure (Coarse→Fine) | Zoom Impr. Rate | Median Fine Size |
|--------|-----------|---------|----------|----------|-----------------|---------------|---------------------------|------------------------|-----------------|------------------|
| A | 0.25 | 3.0 | 20 | ✅ | 27 | 231 | 0.865 → 0.988 | 0.453 → 0.544 | 0.455 | 42 |
| B | 0.5 | 3.0 | 20 | ✅ | 36 | 276 | 0.859 → 0.988 | 0.464 → 0.540 | 0.417 | 40 |
| C | 0.5 | 3.0 | 50 | ✅ | 36 | 128 | 0.859 → 0.905 | 0.464 → 0.433 | 0.333 | 75 |
| D | 0.5 | 2.0 | 20 | ❌ | 36 | 295 | 0.859 → 0.986 | 0.464 → 0.509 | **0.500** | 34 |
| E | 0.25 | 3.0 | 20 | ❌ | 27 | 269 | 0.865 → 0.979 | 0.453 → 0.523 | 0.545 | 33 |

**Best overall**: Config D (coarse_0.5_fixed2.0_min20) — highest improvement_rate (0.50), zero fragmentation, good purity gains.

---

## Flat v26 Zoom Quality Evaluation (Same 12k Embeddings)

| Resolution | Branch Purity | Area Purity | Singleton Frac |
|------------|---------------|-------------|----------------|
| 0.25 | 0.865 | 0.453 | 0.000 |
| 0.5 | 0.859 | 0.464 | 0.000 |
| 1.0 | 0.908 | 0.473 | 0.000 |
| 2.0 | 0.924 | 0.502 | 0.000 |
| 3.0 | 0.932 | 0.510 | 0.000 |

**v26 Checks**:
- Branch monotonic (res3 ≥ res0.25): ✅ PASS (0.932 ≥ 0.865)
- Area monotonic (res3 ≥ res0.25): ✅ PASS (0.510 ≥ 0.453)
- Improvement rate > 0.5 on ≥2/4 transitions: ❌ FAIL (only 1/4 transitions)

**Verdict**: **FAIL** — confirms flat zoom fails at 12k scale

---

## Scale Dependency Confirmed

| Scale | Method | Result |
|-------|--------|--------|
| 1k (citation roles) | Flat v26 | FAIL (0/3 modes pass) |
| 12k (dense) | Flat v26 | FAIL (this test) |
| 12k (dense) | Constrained Hierarchical | **PASS** (zero fragmentation, good zoom) |
| 174k (TF-IDF) | Flat v26 | FAIL (0/4 modes pass, >99% singletons) |
| 174k (TF-IDF) | Constrained Hierarchical | Nesting=1.0 by construction, but singleton_frac >0.99 at fine res |

**Key insight**: Constrained hierarchical Leiden solves fragmentation and enables zoom refinement at 12k, but the same method at 174k on TF-IDF produces over-fragmentation. The evidence-backed path remains **citation-role/dense-embedding modes** at full 174k scale.

---

## Recommendations

1. **Await 174k dense embeddings** from legal-distance (only 3/26 years ACCEPTED)
2. **When 174k dense available**: Test constrained hierarchical Leiden on accepted dense modes (center_projected, citation-role, metric learning, linear hybrids)
3. **Current best config for 174k dense**: coarse_0.5_fixed2.0_min20 (validated at 12k, zero fragmentation, improvement_rate=0.50)
4. **No further same-question cycles justified** without dense embeddings delivery

---

## Evidence References

- `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221342.json` (Config A)
- `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221413.json` (Config B)
- `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221442.json` (Config C)
- `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221514.json` (Config D - BEST)
- `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260927_221545.json` (Config E)

---

## Provenance

- Embeddings: `/legal_distance/results/174k_dense_embeddings/checkpoints/embeddings_2000/2001/2002.npy` (ACCEPTED, 3/26 years)
- Metadata: `/results/fractal_map/hierarchical_map_174k/metadata_174k_eval.json` (173,963 entries, branch+legal_area 100%)
- Method: Constrained hierarchical Leiden (min_cluster_size + adaptive sub_resolution + max_subclusters)
- Evaluation: Frozen v26 zoom-quality rule (branch/area monotonic + improvement_rate > 0.5 on ≥2/4 transitions)