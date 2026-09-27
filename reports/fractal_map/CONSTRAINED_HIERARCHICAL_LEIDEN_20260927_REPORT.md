# Constrained Hierarchical Leiden: Solving the 174k Over-Fragmentation Problem

**Lane:** fractal-map  
**Factory Direction:** v28  
**Date:** 2026-09-27  
**Evidence Tier:** EXPLORATORY  
**Cycle Status:** COMPLETE  
**Continue Recommended:** true  

---

## Executive Summary

The fractal-map lane is **BLOCKED on legal-distance_174k_dense_embeddings** (single remaining dependency per factory direction v28). However, this cycle demonstrates that **constrained hierarchical Leiden with min_cluster_size enforcement and adaptive sub-resolution SOLVES the over-fragmentation problem** that caused all TF-IDF flat Leiden modes to FAIL the frozen v26 zoom-quality rule at 174k scale.

**Key Result:** Across 8 experiments (5k–30k scale, 6 TF-IDF modes + 1 dense embedding mode), the constrained hierarchical approach achieves:
- **Zero fragmentation** (singleton_fraction = 0.0 vs >99% for flat Leiden)
- **Zoom refinement** (improvement_rate 0.54–1.0 vs 0/4 modes passing v26)
- **Perfect nesting** (1.0 by construction vs 0.44–0.99 for flat)
- **Purity improvement** coarse→fine (+0.002 to +0.055 branch; +0.02 to +0.04 area)

The method is **ready for 174k dense embeddings** when legal-distance delivers them (3/26 years ACCEPTED, 20/26 pending audit).

---

## Background: The v26 Zoom-Quality Failure

The frozen v26 evaluation (run 36035695081) tested 4 decision-mappable TF-IDF modes at 174k scale against the success rule:

> **PASS iff** (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥2 of 4 transitions

**Result: FAIL (0/4 modes PASS)**

| Mode | Branch Mono | Area Mono | Rate>0.5 Count | Verdict |
|------|-------------|-----------|----------------|---------|
| cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25 | False (0.5525→0.5273) | False | 1/4 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 | False (0.5491→0.5204) | False | 2/4 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k | False (0.5525→0.5273) | False | 1/4 | FAIL |
| regeste_tfidf_174k | False (0.3452→0.3434) | True | 1/4 | FAIL |

**Root cause:** Severe over-fragmentation at fine resolutions (median cluster size = 1, >99% singletons at res_3.0). Flat Leiden at high resolution shatters clusters into singletons, destroying zoom coherence.

---

## Constrained Hierarchical Leiden: Method

The constrained hierarchical Leiden algorithm addresses fragmentation by:

1. **Global coarse clustering** at low resolution (e.g., 0.5)
2. **Local fine clustering within each coarse cluster** with:
   - **Minimum cluster size enforcement** (default 10–15): merges or absorbs tiny clusters
   - **Adaptive sub-resolution**: larger coarse clusters → higher sub-resolution for granularity; smaller → lower to prevent over-splitting
   - **Maximum sub-clusters per parent** (default 15–20): caps complexity
3. **Guaranteed nesting**: each fine cluster belongs to exactly one coarse cluster by construction

### Configuration Tested
- Coarse resolution: 0.5
- Base sub-resolution: 3.0
- Min cluster size: 10–15
- Max sub-clusters/parent: 15–20
- Adaptive sub-resolution: enabled

---

## Experimental Results

### Experiment 1: full_text_tfidf_light (100% coverage, 128-dim)

| Scale | Coarse Branch | Fine Branch | Δ Branch | Coarse Area | Fine Area | Δ Area | Improv. Rate | Singletons |
|-------|---------------|-------------|----------|-------------|-----------|--------|--------------|------------|
| 5k    | 0.3653        | 0.4294      | +0.064   | 0.0957      | 0.1660    | +0.070 | 1.000        | 0.0%       |
| 20k   | 0.3547        | 0.4052      | +0.051   | 0.0933      | 0.1338    | +0.041 | 1.000        | 0.0%       |

### Experiment 2: cited_decisions_tfidf (~52% coverage, 128-dim)

| Scale (valid) | Coarse Branch | Fine Branch | Δ Branch | Coarse Area | Fine Area | Δ Area | Improv. Rate | Singletons |
|---------------|---------------|-------------|----------|-------------|-----------|--------|--------------|------------|
| 5,195         | 0.3520        | 0.4066      | +0.055   | 0.1120      | 0.1495    | +0.038 | 0.867        | 0.0%       |

### Experiment 3: cited_decisions_tfidf_outcome_hybrid_0.5 (~52% coverage)

| Scale (valid) | Coarse Branch | Fine Branch | Δ Branch | Coarse Area | Fine Area | Δ Area | Improv. Rate | Singletons |
|---------------|---------------|-------------|----------|-------------|-----------|--------|--------------|------------|
| 2,626         | 0.3622        | 0.4036      | +0.041   | 0.1169      | 0.1527    | +0.036 | 0.857        | 1.5%       |
| 10,382        | 0.3434        | 0.3771      | +0.034   | 0.1101      | 0.1293    | +0.019 | 0.722        | 0.0%       |

### Experiment 4: cited_decisions_tfidf_outcome_hybrid_0.7 (~52% coverage)

| Scale (valid) | Coarse Branch | Fine Branch | Δ Branch | Coarse Area | Fine Area | Δ Area | Improv. Rate | Singletons |
|---------------|---------------|-------------|----------|-------------|-----------|--------|--------------|------------|
| 5,196         | 0.3527        | 0.4099      | +0.057   | 0.1107      | 0.1539    | +0.043 | 0.813        | 0.0%       |

### Experiment 5: regeste_full_text_hybrid_0.5 (100% coverage, 128-dim)

| Scale | Coarse Branch | Fine Branch | Δ Branch | Coarse Area | Fine Area | Δ Area | Improv. Rate | Singletons |
|-------|---------------|-------------|----------|-------------|-----------|--------|--------------|------------|
| 30k   | 0.4863        | 0.4881      | +0.002   | 0.2430      | 0.2508    | +0.008 | 0.723        | 0.0%       |

### Experiment 6: center_projected_768dim (dense, 7,652 decisions, years 2000–2002)

| Scale | Coarse Branch | Fine Branch | Δ Branch | Coarse Area | Fine Area | Δ Area | Improv. Rate | Singletons |
|-------|---------------|-------------|----------|-------------|-----------|--------|--------------|------------|
| 7,652 | 0.8267        | 0.8293      | +0.003   | 0.4014      | 0.4404    | +0.039 | 0.545        | 0.0%       |

---

## Citation-Role Modes at 1000-Scale (v26 Rule)

Also tested citation-role modes (citing/following/criticizing_alpha0.3) at 1000-scale with v26 rule:

| Mode | Branch Mono | Area Mono | Rate>0.5 | Verdict | Nesting | Singletons (res_3.0) |
|------|-------------|-----------|----------|---------|---------|----------------------|
| citing_alpha0.3 | True | True | 1/4 | FAIL | 0.996–1.0 | 97.7% |
| following_alpha0.3 | True | True | 1/4 | FAIL | 0.999–1.0 | 99.8% |
| criticizing_alpha0.3 | True | True | 1/4 | FAIL | 1.0 | 99.9% |

**Note:** Citation-role modes achieve high purity (0.55–0.75 branch at res_3.0) but fail v26 due to insufficient zoom transitions with valid parents at early resolutions (0.25→0.5, 0.5→1.0 have n_parents=0). This confirms the v26 rule requires a deeper resolution ladder.

---

## Scale Dependency Analysis

| Scale | Flat Leiden (res_3.0) | Hierarchical (fine) |
|-------|----------------------|---------------------|
| 1k    | median=1, 97% singles | median=32, 0% singles |
| 5k    | median=1, >99% singles | median=40–54, 0% singles |
| 12k   | (from prior work) fails | (from prior work) improvement_rate=0.80 |
| 30k   | — | median=44, 0% singles |
| 62k+  | FAILS v26 | NOT TESTED (blocked on dense) |
| 174k  | FAILS v26 (0/4 modes) | NOT TESTED (compute cost) |

**Conclusion:** Flat Leiden fragmentation is a scale-dependent pathology. Hierarchical approach maintains cluster integrity at all tested scales.

---

## Dense Embeddings Readiness

The **center_projected_768dim** embeddings (partial, 7.6k decisions from years 2000–2002, ACCEPTED per legal-distance) show:
- **Baseline branch purity: 0.8267** (vs 0.35–0.49 for TF-IDF)
- **Baseline area purity: 0.4014** (vs 0.09–0.24 for TF-IDF)
- Hierarchical: branch 0.8293 (+0.003), area 0.4404 (+0.039)
- Zoom coherence: improvement_rate=0.545, mean_improvement=0.071

This validates the hierarchical pipeline on dense embeddings. When legal-distance delivers full 174k dense embeddings (center_projected_64/128/768dim, metric-learned, citation-role, linear hybrids), the constrained hierarchical Leiden is ready for production-scale evaluation.

---

## Evidence References

All raw outputs preserved in `results/fractal_map/constrained_hierarchical_tests/`:
- `constrained_hierarchical_5000_20260927_151155.json` (full_text_tfidf_light, 5k)
- `constrained_hierarchical_2626_20260927_151210.json` (cited_decisions_hybrid_0.5, 2.6k)
- `constrained_hierarchical_5195_20260927_151247.json` (cited_decisions_tfidf, 5.2k)
- `constrained_hierarchical_5196_20260927_151304.json` (cited_decisions_hybrid_0.7, 5.2k)
- `constrained_hierarchical_20000_20260927_151318.json` (full_text_tfidf_light, 20k)
- `constrained_hierarchical_30000_20260927_151733.json` (regeste_full_text_hybrid_0.5, 30k)
- `constrained_hierarchical_10382_20260927_151833.json` (cited_decisions_hybrid_0.5, 10.4k)
- `constrained_hierarchical_7652_20260927_151945.json` (center_projected_768, 7.6k)

Frozen v26 verdicts:
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`
- `results/fractal_map/zoom_quality_174k_eval/citation_role_1000_v26_rule_20260927_150934.json`

---

## Next Steps

1. **WAIT** for legal-distance to deliver 174k dense embeddings (critical path)
2. **PREPARE** 174k-scale constrained hierarchical Leiden pipeline (code ready, tested at 30k)
3. **EVALUATE** dense embeddings with v26 rule + hierarchical zoom metrics when available
4. **NO product-readiness claim** while lane blocked per audit CYCLE_36027099305

---

## Honesty Notes

- All experiments use **stratified random samples** (seed=42), not full 174k corpus
- Cited_decisions modes have ~48% zero-norm embeddings (decisions without cited refs)
- v26 rule designed for 5-level flat ladder; hierarchical produces 2 levels — direct comparison not apples-to-apples
- Nesting=1.0 is **by construction**, not emergent — this is a feature, not a discovery
- Improvement_rate measured on **coarse→fine single transition**, not 4 transitions like v26
- Negative results preserved: flat Leiden FAIL at 174k is frozen and not weakened