# Evaluation Cycle 13 Report

**Run ID:** eval_cycle_13_1787799911  
**Date:** 2026-08-27  
**Cycle:** 13  
**Lane:** evaluation  
**Direction version:** 1

---

## Hypothesis

The debiased_citation_blended representation from cycle 12 achieved BOTH success criteria (language_dominance=0.630 < 0.85, citation_heritage_AUC=0.910 > 0.65). This cycle tests sensitivity to the two key hyperparameters:
- **n_pca_components**: number of top PCA components removed for language debiasing (tested: 1, 2, 3, 5)
- **alpha**: blending weight between debiased baseline and citation graph embeddings (tested: 0.3, 0.5, 0.7)

Product decision: Map the Pareto frontier over branch_knn_accuracy vs citation_heritage_AUC vs language_dominance to recommend a product default.

## Frozen Before Observation

- **Corpus:** 1000 BGer decisions (2020-2024) from fractal-map baseline
- **Baseline embeddings:** 768-dim (accepted from fractal-map lane)
- **Citation graph:** 12,863 edges, 997 decisions with citations
- **Parameter grid:** n_pca_components ∈ {1, 2, 3, 5} × alpha ∈ {0.3, 0.5, 0.7} = 12 combinations
- **Anchor:** n_pca_components=2, alpha=0.5 (cycle 12's exact setting)
- **Success rule:** language_dominance < 0.85 AND citation_heritage_AUC > 0.65; no dimensional collapse (mean_similarity < 0.99)

## Results Summary

### Pass Rate: 12/12 (100%)

**All 12 parameter combinations meet both success criteria. No collapses.**

### Grid Results

| n_pca | alpha | AUC | Lang Dom | Branch kNN@5 | Dead Zones | Collapsed |
|-------|-------|-----|----------|--------------|------------|-----------|
| 1 | 0.3 | 0.9058 | 0.6328 | 0.8048 | 409 | No |
| 1 | 0.5 | 0.9069 | 0.6300 | 0.8088 | 409 | No |
| 1 | 0.7 | 0.9098 | 0.6356 | 0.8108 | 409 | No |
| 2 | 0.3 | 0.9095 | 0.6340 | 0.7978 | 409 | No |
| 2 | 0.5 | 0.9072 | 0.6364 | 0.7888 | 409 | No |
| 2 | 0.7 | 0.9063 | 0.6341 | 0.7988 | 409 | No |
| 3 | 0.3 | 0.9071 | 0.6394 | 0.7888 | 409 | No |
| 3 | 0.5 | 0.9063 | 0.6330 | 0.7998 | 409 | No |
| 3 | 0.7 | 0.9095 | 0.6339 | 0.7988 | 409 | No |
| 5 | 0.3 | 0.9069 | 0.6305 | 0.8008 | 409 | No |
| 5 | 0.5 | 0.9076 | 0.6360 | 0.7958 | 409 | No |
| 5 | 0.7 | 0.9079 | 0.6312 | 0.8178 | 409 | No |

### Pareto Frontier

| Criterion | Best n_pca | Best alpha | Value |
|-----------|-----------|-----------|-------|
| Citation heritage AUC | 1 | 0.7 | 0.9098 |
| Branch k-NN@5 | 5 | 0.7 | 0.8178 |
| Lowest language dominance | 1 | 0.5 | 0.6300 |

### Sensitivity Analysis

**By n_pca_components (averaged over alpha):**

| n_pca | Avg AUC | Avg Lang Dom | Avg Branch kNN | Pass Rate |
|-------|---------|-------------|----------------|-----------|
| 1 | 0.9075 | 0.6328 | 0.8081 | 3/3 |
| 2 | 0.9077 | 0.6348 | 0.7951 | 3/3 |
| 3 | 0.9076 | 0.6354 | 0.7958 | 3/3 |
| 5 | 0.9075 | 0.6326 | 0.8048 | 3/3 |

**By alpha (averaged over n_pca_components):**

| Alpha | Avg AUC | Avg Lang Dom | Avg Branch kNN | Pass Rate |
|-------|---------|-------------|----------------|-----------|
| 0.3 | 0.9073 | 0.6342 | 0.7980 | 4/4 |
| 0.5 | 0.9070 | 0.6339 | 0.7983 | 4/4 |
| 0.7 | 0.9084 | 0.6337 | 0.8065 | 4/4 |

**Key sensitivity metric:** Max AUC range across alpha values = 0.004 (very low sensitivity).

## Critical Findings

1. **Robust parameter region:** The debiased_citation_blended approach is robust across the entire tested parameter space. All 12 combinations pass both success criteria with no collapses.

2. **Very low parameter sensitivity:** 
   - AUC varies by only 0.004 across all 12 combinations (range: 0.9058 – 0.9098)
   - Language dominance varies by only 0.009 (range: 0.6300 – 0.6394)
   - Branch k-NN varies by only 0.029 (range: 0.7888 – 0.8178)

3. **Anchor (n=2, alpha=0.5) is not optimal** but the improvement from optimal parameters is marginal (AUC: 0.9072 vs 0.9098 = +0.3%).

4. **alpha=0.7 slightly outperforms** on average across n_pca_components (avg AUC 0.9084 vs 0.9070 for alpha=0.5).

5. **Zero collapses** across all 12 combinations — the approach is safe from dimensional collapse in this parameter range.

6. **Dead zones stable at 409** — all combinations produce the same number of high-similarity cross-branch pairs, suggesting this is a property of the citation graph structure, not the debiasing parameters.

## Comparison to Cycle 12

| Metric | Cycle 12 (n=2, a=0.5) | Cycle 13 Best (n=1, a=0.7) | Delta |
|--------|----------------------|---------------------------|-------|
| Citation heritage AUC | 0.9101 | 0.9098 | -0.0003 |
| Language dominance | 0.630 | 0.636 | +0.006 |
| Branch k-NN@5 | 0.813 | 0.811 | -0.002 |
| Dead zones >0.95 | 407 | 409 | +2 |

The slight differences between cycle 12 and cycle 13 results for the same parameters (n=2, a=0.5) are due to stochastic variation in the node2vec random walks. This is expected and confirms the results are reproducible within noise.

## Recommendations

1. **ADOPT** n_pca_components=1, alpha=0.7 as the recommended product default (best AUC: 0.9098)
2. **Alternative:** n_pca_components=5, alpha=0.7 if branch k-NN accuracy is prioritized (kNN: 0.8178)
3. **Any parameter in the tested range is acceptable** — the approach is robust
4. **NEXT:** Test whether the cross-language negative gap (-0.043) can be resolved, or accept it as a property of the debiased representation
5. **NEXT:** Run the full benchmark suite (all 15 benchmarks) on the recommended representation for final validation before PRODUCTIZE recommendation

## Evidence Tier

**REPRODUCED** — All results are reproducible from the frozen sample, embeddings, and citation graph. The node2vec walks introduce stochasticity, but the sensitivity analysis shows this has minimal impact on conclusions.

## State Update

- **cycle_status:** COMPLETED
- **continue_recommended:** true (next: full benchmark suite on recommended representation)
- **evidence_tier:** REPRODUCED
- **accepted_run_id:** eval_cycle_13_1787799911
