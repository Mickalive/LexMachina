# Fractal Map Lane - 15-Year Checkpoint Validation Report

**Run ID**: `15yr_checkpoint_validation_partial_20261001`  
**Timestamp**: 2026-10-01T03:19:15+00:00  
**Factory Direction**: v29  
**Lane Status**: BLOCKED_ON_DEPENDENCIES (awaiting legal-distance 174k dense embeddings)  
**Evidence Tier**: EXPLORATORY (PENDING AUDIT data)  

---

## Executive Summary

Validated the constrained hierarchical Leiden production pipeline (`coarse_0.5_fixed2.0_min20`) on **91,929 decisions** from 15-year checkpointed dense embeddings (years 2000-2014, PENDING AUDIT for 2003-2014). 

**Key Result**: **5/7 hierarchical_v1 checks PASS** — the pipeline maintains perfect nesting, zero fragmentation, excellent branch/area purity, and legal structure at both branch and area levels, but **zoom coherence fails** (improvement_rate=0.3478 < 0.5 threshold).

This confirms the pipeline is **structurally sound at 100k scale** but reveals a **non-monotonic scale dependency** that invalidates simple power-law extrapolation from the 28k checkpoint alone.

---

## Detailed Results

### Production Config: `coarse_0.5_fixed2.0_min20`

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| N decisions | 91,929 | — | — |
| Embedding dim | 768 | — | — |
| Coarse clusters | 54 | — | — |
| Fine clusters | 780 | — | — |
| Coarse branch purity | 0.8947 | — | — |
| **Fine branch purity** | **0.9842** | > 0.5 | ✅ PASS |
| Coarse area purity | 0.6090 | — | — |
| **Fine area purity** | **0.6276** | > 0.5 | ✅ PASS |
| Branch improvement | +0.0895 | > 0 | ✅ PASS |
| Area improvement | +0.0186 | > 0 | ✅ PASS |
| **Nesting** | **1.0** | ≥ 0.99 | ✅ PASS |
| Fine singleton fraction | 0.0% | < 1% | ✅ PASS |
| Fine median size | 95 | — | — |
| **Zoom improvement_rate** | **0.3478** | > 0.5 | ❌ FAIL |
| Zoom mean improvement | 0.0956 | — | — |
| Parents with children | 23 | — | — |

### Hierarchical_v1 Protocol (7 Checks)

| Check | Result |
|-------|--------|
| singleton_fraction_below_0.01 | ✅ PASS |
| nesting_perfect | ✅ PASS |
| branch_purity_improves | ✅ PASS |
| area_purity_improves | ✅ PASS |
| zoom_coherence_ok | ❌ FAIL (0.3478 < 0.5) |
| legal_structure_branch | ✅ PASS (0.9842 > 0.5) |
| legal_structure_area | ✅ PASS (0.6276 > 0.5) |
| **Overall** | **5/7 PASS** |

---

## Scale Dependency Analysis: Non-Monotonic Behavior Confirmed

| Scale | Years | Decisions | Composition | hier_impr (production config) |
|-------|-------|-----------|-------------|------------------------------|
| 12k | 2000-2002 | 12,570 | ACCEPTED, recent | 0.50 (fixed) / 0.75-0.80 (adaptive) |
| 28k | 2000-2005 | 28,006 | Checkpoint, recent | **0.67** |
| 99k (16yr) | 2000-2015 | 99,325 | Checkpoint, broad | 0.57-0.71 |
| **100k (15yr)** | **2000-2014** | **91,929** | **Checkpoint, broad** | **0.35** |
| 174k | 2000-2026 | 173,963 | Full corpus | ~0.67 (power law prediction) |

### Critical Finding: Composition > Scale

The **28k checkpoint (2000-2005)** achieved hier_impr=0.67, but the **100k checkpoint (2000-2014)** achieves only 0.35. The difference is **temporal breadth and legal domain diversity**:

- **28k**: 6 years, narrower legal domain distribution, more homogeneous
- **100k/15yr**: 15 years, full legal domain diversity, heterogeneous
- **99k/16yr**: 16 years, but showed 0.57-0.71 (different config: adaptive min20)

**Conclusion**: Simple power-law extrapolation from a single checkpoint is **invalid**. Zoom coherence depends on the **homogeneity of the legal domain distribution**, not just scale. The 174k power-law prediction of ~0.67 based on 28k alone is unreliable.

---

## Pipeline Readiness Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Structural integrity (nesting=1.0) | ✅ READY | By construction at all scales |
| Zero fragmentation | ✅ READY | singleton_fraction=0.0% at 100k |
| Branch purity | ✅ READY | 0.9842 at 100k (exceeds 0.5) |
| Area purity | ✅ READY | 0.6276 at 100k (exceeds 0.5) |
| Legal structure (branch) | ✅ READY | Fine branch purity > 0.5 |
| Legal structure (area) | ✅ READY | Fine area purity > 0.5 |
| Zoom coherence | ⚠️ DEGRADED | 0.35 at 100k vs 0.5 threshold |
| v26 flat zoom quality | ❌ FAIL | Confirmed at all TF-IDF scales |

**Verdict**: Pipeline is **structurally production-ready** but **zoom refinement degrades at broad-coverage scales**. The evidence-backed zoom path requires dense embeddings that maintain semantic coherence across diverse legal domains.

---

## Implications for 174k Dense Embeddings Delivery

1. **Current blocker is correct**: Lane cannot claim production readiness for dense embeddings at 174k without ACCEPTED 174k dense embeddings.

2. **Scale extrapolation model needs revision**: The power-law model (hier_impr ~0.67 at 174k) based on 28k checkpoint is contradicted by 100k validation. Need multi-checkpoint validation strategy.

3. **Recommended validation path for legal-distance**:
   - Validate on compositionally diverse checkpoints (e.g., 2000-2005, 2006-2010, 2011-2014, 2015-2018)
   - Test whether embedding quality (not just clustering) degrades with temporal breadth
   - Consider domain-adaptive clustering for heterogeneous corpora

4. **Production config remains**: `coarse_0.5_fixed2.0_min20` is still the best validated config — it maintains structural guarantees even when zoom coherence degrades.

---

## Evidence Artifacts

- **Primary**: `results/fractal_map/15yr_checkpoint_validation/15yr_validation_partial_20261001.json`
- **Prior**: `results/fractal_map/28k_checkpoint_validation/28k_validation_20260928_212756.json`
- **Prior**: `results/fractal_map/constrained_hierarchical_dense_16yr/constrained_hierarchical_dense_16yr_results.json`
- **Prior**: `results/fractal_map/12k_dense_comprehensive/` (ACCEPTED 12k validation)

---

## Next Recommendation

**No same-question cycle justified** without ACCEPTED 174k dense embeddings delivery.

**New discriminating question for when dense embeddings arrive**: 
> "Does the constrained hierarchical Leiden pipeline achieve hier_impr > 0.5 on ACCEPTED 174k dense embeddings across the full 2000-2026 temporal range, or does the non-monotonic scale dependency persist?"

This requires:
1. Legal-distance to deliver ACCEPTED 174k dense embeddings (all 26 years through audit)
2. Fractal-map to run production config on full 174k
3. Compare against revised scale extrapolation model incorporating composition effects

---

## Provenance

- **Checkpoint source**: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2014)
- **Embedding model**: 768-dim sentence transformer (paraphrase-multilingual-MiniLM-L12-v2) on `erwaegungen` section
- **Metadata**: Branch and legal_area from corpus normalization
- **Global seed**: 42
- **Leiden seed**: 42
- **K-neighbors**: 15

**Status**: PENDING AUDIT data — results for pipeline validation only, NOT ACCEPTED evidence.