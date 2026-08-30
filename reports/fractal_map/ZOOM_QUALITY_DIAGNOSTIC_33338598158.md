# Zoom Quality Diagnostic — Run 33338598158

**Lane**: fractal-map  
**Direction version**: 10  
**Date**: 2026-08-30  
**Run ID**: zoom_quality_diagnostic_20260830_221957  
**Corpus**: 1000 BGer decisions (2020-2024)  
**Modes evaluated**: 22 (21 legal-distance + center_projected_hierarchical)

## Hypothesis

Multi-dimensional zoom quality profiling across all validated legal-distance modes will reveal which modes produce the most legally coherent zoom transitions, and which resolution transitions are most productive. This provides actionable guidance for 192k scaling and product zoom UI design.

## Method

For each mode, loaded the 7-resolution label arrays (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0) and analyzed all 6 coarse→fine transitions. Measured:

1. **Purity delta**: Branch purity change from coarse to fine level
2. **Split rate**: Fraction of coarse clusters that split into multiple fine clusters
3. **Meaningful split rate**: Fraction of splits where purity improves (not noise splitting)
4. **Stability**: Consistency of purity deltas across all 6 transitions
5. **Zoom quality score (ZQ)**: Composite of above metrics

## Results

### Mode Ranking (Top 10 by Zoom Quality)

| Rank | Mode | ZQ Score | Purity Δ | Meaningful Splits | Stability |
|------|------|----------|----------|-------------------|-----------|
| 1 | citing_alpha0.3 | 0.5401 | +0.1212 | 80.0% | 0.4167 |
| 2 | following_alpha0.3 | 0.5280 | +0.1214 | 66.7% | 0.5000 |
| 3 | criticizing_alpha0.3 | 0.4864 | +0.1215 | 50.0% | 0.5000 |
| 4 | cited_decisions_tfidf_hybrid_cp64_0.7 | 0.4781 | +0.0683 | 83.3% | 0.4167 |
| 5 | cited_decisions_tfidf_hybrid_cp768_0.7 | 0.4714 | +0.0630 | 83.8% | 0.4167 |
| 6 | cited_decisions_tfidf_hybrid_cp768_0.3 | 0.4698 | +0.0559 | 78.9% | 0.4167 |
| 7 | legal_cited_decisions_only | 0.4667 | +0.0389 | 51.2% | 0.3333 |
| 8 | cited_decisions_tfidf_hybrid_cp64_0.5 | 0.4660 | +0.0452 | 89.4% | 0.4167 |
| 9 | cited_decisions_tfidf_hybrid_cp64_0.3 | 0.4548 | +0.0274 | 66.1% | 0.4506 |
| 10 | hybrid_alpha_03 | 0.4476 | +0.0608 | 45.0% | 0.4167 |

### Bottom 5 (Worst Zoom Quality)

| Rank | Mode | ZQ Score | Purity Δ | Meaningful Splits | Stability |
|------|------|----------|----------|-------------------|-----------|
| 18 | linear_metric_epoch4 | 0.3257 | -0.0026 | 35.2% | 0.1667 |
| 19 | debiased_citation_blended | 0.2893 | +0.0087 | 20.0% | 0.1667 |
| 20 | cited_decisions_tfidf_outcome_hybrid_0.7 | 0.2799 | +0.0031 | 35.2% | 0.3333 |
| 21 | cited_decisions_tfidf_outcome_hybrid_0.5 | 0.2798 | -0.0010 | 36.5% | 0.3333 |
| 22 | mahalanobis_metric_epoch4 | 0.2780 | -0.0034 | 15.8% | 0.1667 |

### Default Mode (center_projected_hierarchical)

- ZQ Score: 0.3381 (rank 17/22)
- Purity Δ: +0.0148
- Meaningful splits: 39.0%
- Stability: 0.1667
- Finest purity: 0.9292

### Transition Quality Profile (Aggregate across all modes)

| Transition | Mean Purity Δ | Std | Meaningful Splits |
|------------|---------------|-----|-------------------|
| 0.25→0.5 | +0.0738 | ±0.1141 | 58.7% |
| 0.5→0.75 | +0.0379 | ±0.0778 | 53.4% |
| 0.75→1.0 | +0.0220 | ±0.0982 | 66.3% |
| 1.0→1.5 | +0.0664 | ±0.1853 | 54.3% |
| 1.5→2.0 | +0.0074 | ±0.0238 | 57.2% |
| 2.0→3.0 | +0.0266 | ±0.0750 | 49.7% |

## Key Findings

### Finding 1: Citation Role Views Dominate Zoom Quality

The top 3 modes by zoom quality are all citation role views (`citing_alpha0.3`, `following_alpha0.3`, `criticizing_alpha0.3`). These show the highest purity improvement (+0.12) across zoom transitions and high meaningful split rates. This makes legal sense: citation relationships naturally form hierarchical legal topic structures (a citing decision is about a specific legal issue within the broader domain of the cited decision).

### Finding 2: Tension Between Zoom Quality and Adversarial Scores

The BEST PRODUCTION mode (`cited_decisions_tfidf_outcome_hybrid_0.5`, JP=0.7990) ranks 21st in zoom quality (ZQ=0.2798). The BEST FRACTAL mode (`cited_decisions_tfidf_outcome_hybrid_0.7`, JP=0.7907) ranks 20th (ZQ=0.2799). These modes excel at flat neighborhood exploration but produce poor zoom transitions.

This suggests a **multi-view product design**:
- **Zoom navigation**: Citation role views for hierarchical browsing
- **Semantic similarity**: Outcome hybrids for flat neighborhood exploration
- **Default browsing**: center_projected_hierarchical for general use

### Finding 3: Most Productive Zoom Transitions

The coarsest transition (0.25→0.5) is most productive (+0.0738 avg purity gain). The mid-range transition (1.0→1.5) is second (+0.0664). The 1.5→2.0 transition adds almost no value (+0.0074) — this resolution range could potentially be skipped in the product UI.

### Finding 4: Low Stability Across All Modes

No mode achieves stability >0.5, meaning zoom quality is uneven across the resolution ladder. This is an inherent property of the hierarchical Leiden approach: some zoom steps reveal meaningful structure, others don't. The product UI should communicate this — some zoom levels are more informative than others.

## Product Implications

1. **Zoom mode recommendation**: For the zoom UI, expose citation role views (citing/following/criticizing) as dedicated zoom modes. These produce the most legally coherent hierarchical navigation.

2. **Resolution ladder optimization**: Consider reducing the resolution ladder from 7 levels to 5 (dropping 1.5 and/or 0.75) based on the transition quality profile. The 1.5→2.0 transition adds minimal value.

3. **Multi-view architecture validated**: The tension between zoom quality and adversarial scores confirms the multi-view design direction — different representations excel at different navigation tasks.

4. **192k scaling guidance**: When scaling to 192k, the citation role views should be tested first for zoom quality, as they show the most promise for hierarchical navigation at scale.

## Evidence

- Results: `results/fractal_map/evaluation/zoom_quality_diagnostic_results.json`
- Script: `fractal_map/evaluation/zoom_quality_diagnostic.py`
- Existing tests: 174/174 PASS, 1 skipped (optional deps)

## Recommendation

**CONTINUE** — This diagnostic provides actionable guidance for 192k scaling. No blockers introduced. The existing product integration remains valid. When corpus delivers 192k: test citation role zoom quality at scale, optimize resolution ladder, and implement multi-view zoom UI.
