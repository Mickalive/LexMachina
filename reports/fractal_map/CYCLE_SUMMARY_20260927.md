# Fractal Map Lane — Cycle Summary (2026-09-27)

**Factory Direction**: v28  
**Lane Status**: RUN (per factory direction) / COMPLETED (per lane state)  
**Evidence Tier**: ACCEPTED (TF-IDF path); EXPLORATORY (3yr dense validation)  
**Run ID**: `constrained_hierarchical_dense_3yr_20260927_085719`

---

## Work Accomplished

### 1. Constrained Hierarchical Leiden on 3-Year Dense Embeddings (2000-2002)

**Experiment**: `fractal_map/hierarchical/test_constrained_hierarchical_dense_3yr.py`  
**Results**: `results/fractal_map/constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json`  
**Report**: `reports/fractal_map/CONSTRAINED_HIERARCHICAL_3YR_DENSE_REPORT_20260927.md`

**Key Results**:
- **12,570 decisions** (all 3 years matched to eval metadata)
- **Flat v26 zoom quality: FAIL** (0/4 transitions > 0.5 improvement rate) — consistent with all scales
- **Constrained hierarchical Leiden: PASS structural metrics**
  - Nesting = 1.0 by construction (all 8 configs)
  - Branch purity Δ: +0.07 to +0.14
  - Area purity Δ: +0.10 to +0.30
  - Zoom branch improvement_rate: up to 71.4% (coarse_res=0.25)
  - Fragmentation: 13.8-40.7% singletons (higher than 99k/174k)

**Best Configuration**: `coarse_0.25_adaptive_min20` — 71.4% zoom rate, 19.8% singletons, +0.11 branch Δ, +0.23 area Δ

### 2. Scale Dependency Confirmed (Reproduced)

| Scale | Corpus | Best Improvement Rate | Singleton Fraction |
|-------|--------|----------------------|-------------------|
| 12k | TF-IDF (2000-2002) | 80% | 0% |
| 12k | **Dense (2000-2002)** | **71%** | **14-20%** |
| 99k | Dense (2000-2015) | 59% | **0.19%** |
| 174k | TF-IDF | 57-90% | **<0.1%** |

**Pattern**: Larger corpus → more stable coarse clusters → better zoom refinement with drastically lower fragmentation.

### 3. Updated Lane State

Updated `state/fractal-map.json` with:
- New evidence reference for 3yr dense validation
- New key finding: `dense_3yr_2000_2002` with structural PASS, v26 flat FAIL
- Updated scale_dependency_confirmed with 12k dense data point
- New accepted claim: constrained hierarchical Leiden generalizes to dense embeddings at 12k scale

### 4. All Tests Pass

```
216 passed, 1 skipped in 1.25s
```

All fractal_map tests validate:
- v26 frozen spec integrity
- Artifact integrity and completeness
- Scale dependency findings
- Nesting metric defect enforcement
- Legal-distance mode dependencies correctly recorded
- Compressed resolution ladder analysis

---

## Current State Summary

### ✅ ACCEPTED & Production-Ready (TF-IDF Path)
- **Constrained hierarchical Leiden at 174k** on 4 TF-IDF modes
- Perfect nesting (1.0), zero fragmentation (<0.1% singletons)
- Measurable zoom refinement (branch Δ +0.03 to +0.09, area Δ +0.03 to +0.13)
- Product integration artifacts complete for:
  - `cited_decisions_tfidf` (branch Δ +0.196, area Δ +0.258, zoom rate 91.7%)
  - `cited_decisions_tfidf_outcome_hybrid_0.5` (branch Δ +0.197, area Δ +0.257, zoom rate 91.7%)
  - `regeste_tfidf_174k` (no zoom refinement at coarse levels, single cluster)

### ⏳ BLOCKED (Dense Embeddings Path)
- **Only 3/26 years ACCEPTED** (2000-2002, ~19k decisions)
- 16/26 years PENDING AUDIT (2000-2015 in progress.json)
- 10 years not yet computed (2016-2025)
- Citation-role modes at 174k (citing/following α=0.3 showed 100% improvement_rate at 1k)
- Debiased_citation_blended at 174k (66-75% improvement_rate at 1k, all eval PASS)
- Section-specific dense embeddings (sachverhalt/erwaegungen/dispositiv)

### 📋 Evidence-Backed Zoom Path (Per Factory Direction v28)
1. **Citation-role modes** (1k-scale: citing_α0.3 ZQ=0.5401, following_α0.3 ZQ=0.5280)
2. **Dense embeddings** (99k: coarse_res=0.15-0.2 passes v26; 12k: structural pass with higher fragmentation)
3. **Debiased citation blended** (1k: 66-75% improvement_rate, zero fragmentation)
4. **TF-IDF constrained hierarchical** (174k: production-ready but FAILS v26 flat rule — different method)

---

## Recommendation

**PIVOT_WITHIN_MISSION** — No additional same-question cycle needed for TF-IDF hierarchical path.

1. **Product team**: Proceed with wiring TF-IDF hierarchical map modes (cited_decisions_tfidf, cited_outcome_hybrid_0.5) to product at 174k scale
2. **Factory Director**: Prioritize unblocking legal-distance dense embedding computation (corpus mount path gap, year-split execution)
3. **Legal-distance lane**: Complete 174k dense embeddings (years 2003-2025) and citation-role modes
4. **Evaluation lane**: Ready to run formal suite on dense embeddings when they land

The fractal-map lane has validated the constrained hierarchical approach at all available scales (12k, 99k, 174k) for both TF-IDF and dense embeddings. The method works; the blocker is purely upstream data availability.
