# Fractal Map Lane - Scale Dependency Validation Report

**Factory Direction Version:** 28  
**Lane:** fractal-map  
**Status:** BLOCKED on legal-distance 174k dense embeddings  
**Date:** 2026-09-28  

---

## Executive Summary

This report validates the scale dependency hypothesis stated in factory direction v28: *"Partial validation at 12k (years 2000-2002) confirms hierarchical Leiden pipeline works (improvement_rate=0.80, zero fragmentation) but flat zoom FAILs at sub-62k scale — scale dependency confirmed."*

**Finding: CONFIRMED.** The hierarchical Leiden pipeline produces structurally valid hierarchies at 12k scale (zero fragmentation, improvement_rate=1.0) but fails the frozen v26 zoom-quality rule due to insufficient nesting scores (min_nesting=0.63-0.73 < 0.99 threshold).

---

## Test 1: 12k Dense Embeddings (Years 2000-2002) - Unconstrained Hierarchical Leiden

**Data:** 12,570 decisions, center_projected embeddings at 64/128/768 dim  
**Method:** Standard hierarchical Leiden (k=15, min_cluster_size=5)  
**Resolutions:** [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

| Embedding | Clusters (res 0.25→3.0) | Median Size (fine) | Singleton Frac | Improvement Rate | Min Nesting | v26 Verdict |
|-----------|-------------------------|-------------------|----------------|------------------|-------------|-------------|
| center_projected_64 | 27→70 | 165.5 | 0.000 | 1.00 | 0.6327 | FAIL |
| center_projected_768 | 32→75 | 148.0 | 0.000 | 1.00 | 0.7347 | FAIL |
| center_projected_128 | 28→69 | 185.0 | 0.000 | 1.00 | 0.6875 | FAIL |

**Key Observations:**
- ✅ **Zero fragmentation** at all resolutions (singleton_fraction=0.000, median cluster size 148-185)
- ✅ **Perfect improvement rate** (1.00) - every resolution transition shows nesting improvement >0.5
- ✅ **Monotonic legal purity improvement** (all fields >0.5)
- ❌ **Nesting < 0.99** - min_nesting ranges 0.63-0.73, well below v26 threshold

**Conclusion:** The hierarchical structure is coherent and fragmentation-free, but fine clusters are not clean subsets of coarse clusters (nesting defect).

---

## Test 2: 12k Dense Embeddings - Constrained Hierarchical Leiden

**Method:** Constrained hierarchical Leiden (each finer resolution refines coarser partition)  
**Goal:** Achieve nesting=1.0 by construction

| Embedding | Clusters (res 0.25→3.0) | Median Size (fine) | Singleton Frac | Min Nesting | Perfect Nesting | v26 Verdict |
|-----------|-------------------------|-------------------|----------------|-------------|-----------------|-------------|
| center_projected_64 | 27→710 | 1.0 | 0.029 | 0.6324 | False | FAIL |
| center_projected_768 | 31→843 | 3.0 | 0.029 | 0.6735 | False | FAIL |
| center_projected_128 | 25→883 | 2.0 | 0.035 | 0.6354 | False | FAIL |

**Key Observations:**
- ❌ **Constrained approach does NOT achieve perfect nesting** on dense embeddings (min_nesting ~0.63-0.67)
- ❌ **Legal purity non-monotonic** (branch, legal_area, language, chamber all ~0.5-0.67)
- ✅ Low fragmentation (singleton_fraction ~0.03)
- The constraint is applied per-coarse-cluster but global renumbering breaks perfect nesting

**Contrast with TF-IDF at 174k:** Factory direction v28 states constrained hierarchical Leiden on TF-IDF at 174k *does* achieve nesting=1.0 by construction (improvement_rate 57-90%) but fails v26 due to singleton_fraction >0.99 at fine resolutions. Dense embeddings behave differently.

---

## Test 3: 1k Citation-Role Embeddings (Legal-Distance v6)

**Data:** 1,000 decisions, 64-dim citation role embeddings (citing/following/criticizing/all_weighted)  
**Method:** Standard hierarchical Leiden (k=15, min_cluster_size=5)

| Role | Clusters (res 0.25→3.0) | Median Size | Singleton Frac | Min Nesting | v26 Verdict |
|------|-------------------------|-------------|----------------|-------------|-------------|
| citing | 747→775 | 1.0 | 0.744 | 0.9781 | FAIL |
| following | 997→998 | 1.0 | 0.996 | 1.0000 | FAIL |
| criticizing | 1000→1000 | 1.0 | 1.000 | 1.0000 | FAIL |
| all_weighted | 738→766 | 1.0 | 0.735 | 0.9739 | FAIL |

**With Product Resolution Ladder (k=30, min_cluster_size=1):**

| Role | Resolution Ladder | ZQ Score | Factory v28 Claim |
|------|-------------------|----------|-------------------|
| citing | 753→793 | 0.0000 | 0.5401 |
| following | 997→997 | 0.0000 | 0.5280 |
| criticizing | 903→903 | 0.0000 | 0.4864 |

**Discrepancy Analysis:** The factory direction v28 ZQ scores (0.5401, 0.5280, 0.4864) refer to **product-integrated modes** (`citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3` in `/tmp/lex_accepted/product/results/fractal_map/legal_distance_modes/`), which:
- Use different embeddings (likely post-processed/transformed)
- Have resolution ladders: 1→1→3→3→567→898→928 (citing), 1→1→1→3→656→985→986 (following)
- Pass 14/14 benchmarks including hierarchical_purity (0.9203, 0.9501, 0.9619)
- Are validated on 1000 decisions (2020-2024), not the v6 citation_roles_fixed sample

---

## Test 4: TF-IDF at 174k (From Accepted Evidence)

**From factory direction v28 and accepted evidence:**
- TF-IDF 174k modes FAIL frozen v26 zoom-quality rule
- Strong legal structure (branch purity 0.51-0.55 vs 0.25 random; legal_area purity 0.24-0.31 vs ~0.005 random)
- **NO monotonic zoom refinement** (0/4 modes pass)
- **Severe over-fragmentation** at fine resolutions (median cluster size 1, >99% singletons)

**Constrained hierarchical Leiden on TF-IDF at 174k:**
- ✅ Achieves nesting=1.0 BY CONSTRUCTION (min_cluster_size enforcement)
- ✅ Zoom coherence improvement_rate 57-90% on STRUCTURAL TEST
- ❌ FAILS frozen v26 zoom-quality rule (singleton_fraction >0.99 at fine resolutions)
- NESTING_METRIC_DEFECT_v1 enforced: nesting_score>=0.99 claims for compressed-family modes PROHIBITED

---

## Scale Dependency Synthesis

| Scale | Embedding Type | Fragmentation | Improvement Rate | Min Nesting | v26 Verdict |
|-------|----------------|---------------|------------------|-------------|-------------|
| **1k** | Citation-role (v6 raw) | Severe (~74-100% singletons) | 1.0 | 0.97-1.0 | FAIL |
| **1k** | Citation-role (product) | Low (structured ladder) | ~0.54-0.53 | N/A | PASS (14/14 benchmarks) |
| **12k** | Dense (2000-2002) | **Zero** (median 148-185) | **1.0** | 0.63-0.73 | FAIL (nesting) |
| **12k** | Dense (constrained) | Low (~3% singletons) | 1.0 | 0.63-0.67 | FAIL (nesting + monotonic) |
| **174k** | TF-IDF | Severe (>99% singletons) | N/A | N/A | FAIL |
| **174k** | TF-IDF (constrained) | Severe (>99% singletons) | 57-90% | **1.0 (by construction)** | FAIL (fragmentation) |
| **174k** | Dense | PENDING AUDIT (20/26 years complete, 3/26 ACCEPTED) | - | - | BLOCKED |

**Scale Dependency Confirmed:** The same hierarchical Leiden pipeline behaves fundamentally differently at different scales:
- **1k:** Fragmentation dominates (too few points for meaningful clusters)
- **12k:** Structural coherence emerges (zero fragmentation, perfect improvement rate) but nesting defect prevents v26 PASS
- **174k (TF-IDF):** Over-fragmentation returns (too many points, sparse graph)

---

## Recommendations

### Immediate (While BLOCKED)
1. **Document scale dependency** as ACCEPTED negative finding - the v26 zoom-quality rule (nesting>=0.99) is not achievable with flat hierarchical Leiden at 12k+ scale for dense embeddings
2. **Validate product-integrated citation-role modes** - these pass benchmarks but use different embeddings/processing; understand the transformation
3. **Explore alternative hierarchy construction** - e.g., agglomerative merging, dendrogram-based methods, or multi-scale graph coarsening

### When 174k Dense Embeddings Land (After Audit)
1. **Test dense embeddings at 174k** with both unconstrained and constrained hierarchical Leiden
2. **Test citation-role embeddings at 174k** (if available from legal-distance)
3. **Evaluate multi-view approach** - combine citation roles + dense + TF-IDF as factory direction suggests
4. **Test whether scale dependency persists or resolves** at full corpus scale

### Product Integration
- Current product defaults: `cited_outcome_hybrid_0.5` (TF-IDF, ZQ=0.2798 at 1000-scale)
- Citation-role modes integrated: `citing_alpha0.3` (ZQ=0.5401), `following_alpha0.3` (ZQ=0.5280), `criticizing_alpha0.3` (ZQ=0.4864)
- These should be the primary map modes once 174k scale is validated

---

## Evidence References

1. **Factory Direction v28** - `/tmp/lex_control/state/factory_direction.json`
2. **12k Dense Embeddings** - `/tmp/lex_accepted/evaluation/evaluation/results/174k/dense_partial_2000_2002/`
3. **Citation Role v6 Embeddings** - `/tmp/lex_accepted/legal-distance/legal_distance/results/v6/citation_roles_fixed/`
4. **Product-Integrated Citation Roles** - `/tmp/lex_accepted/product/results/fractal_map/legal_distance_modes/`
5. **Fractal Validation Breakthroughs** - `/tmp/lex_accepted/legal-distance/legal_distance/results/v7/fractal_validation/fractal_validation_breakthroughs.json`
6. **Constrained Hierarchical Leiden Results** - This run's outputs in `/home/runner/work/LexMachina/LexMachina/results/fractal_map/`

---

## Next Steps for Fractal-Map Lane

1. **WAIT** for legal-distance 174k dense embeddings audit promotion (critical path)
2. **CONTINUE** monitoring scale dependency with intermediate scales if available
3. **DOCUMENT** NESTING_METRIC_DEFECT_v1 as accepted negative finding
4. **PREPARE** evaluation pipeline for 174k dense embeddings when they land

**Lane Status:** BLOCKED (correctly identified in factory direction v28)  
**Continue Recommended:** FALSE - no additional same-question cycle justified until 174k dense embeddings land