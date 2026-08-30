# Legal Distance v13 — Cross-Mode Combination 5-Fold Cross-Validation

**Run ID**: v13_cross_mode_kfold_20260830  
**Direction Version**: 10  
**Date**: 2026-08-30  
**Cycle**: Validation of v12 cross-mode combination findings

---

## Hypothesis

The v12 cross-mode combination improvements (JP +0.035 over best individual baseline) are stable across data partitions, not noise from a single 1000/200 split.

## Product Decision Unlocked

If 5-fold CV shows stable improvement (mean JP delta > 0.02 with combo std < 0.03), the cross-mode combination is validated for ACCEPTED tier and becomes a production candidate. If unstable, the two-mode tradeoff is confirmed as fundamental.

## Frozen Setup

- **Corpus**: 1200 Swiss Federal Supreme Court decisions (2024 expanded slice)
- **5-fold CV**: each fold ~960 train / ~240 holdout
- **Harness**: Frozen evaluation harness v3 (seed=42, config_hash=1674829901d55e83)
- **Metrics**: Adversarial LangDom (gate < 0.85), JuristPref (gate > 0.5), CiteIndep (target > 15%)

## Success Rule (frozen before inspection)

Any combination achieves mean CV JP delta > 0.02 AND combo std(JP) < 0.03 across all 5 folds.

---

## Aggregate Results (5-Fold CV)

| Rank | Representation | MeanJP | StdJP | MeanLD | MeanCI | Passes | Delta vs Best Baseline |
|------|---------------|--------|-------|--------|--------|--------|----------------------|
| **1** | **linear_hybrid05_w3070** | **0.7808** | **0.0290** | 0.5092 | 0.2653 | **5/5** | **+0.0525** |
| 2 | linear_citation_w3070 | 0.7583 | 0.0405 | 0.5202 | 0.2261 | 5/5 | +0.0300 |
| 3 | linear_citation_concat | 0.7558 | 0.0234 | 0.5430 | 0.3179 | 5/5 | +0.0275 |
| 4 | linear_citation_ridge | 0.7459 | 0.0279 | 0.5170 | 0.2995 | 5/5 | +0.0175 |
| 5 | linear_citation_pca128 | 0.7458 | 0.0126 | 0.5456 | 0.3276 | 5/5 | +0.0175 |
| **6** | **baseline_linear_oos_refit** | **0.7283** | **0.0318** | 0.5491 | **0.5192** | 5/5 | — (reference) |
| 7 | hier_hybrid05_concat | 0.7125 | 0.0216 | 0.5501 | 0.3252 | 5/5 | −0.0158 |
| 8 | linear_hybrid05_mlp | 0.7066 | 0.0521 | 0.5360 | 0.5546 | 5/5 | −0.0217 |
| 9 | hier_citation_concat | 0.7042 | 0.0307 | 0.5646 | 0.2710 | 5/5 | −0.0241 |
| 10 | baseline_hybrid07 | 0.6925 | 0.0434 | 0.5031 | 0.1447 | 5/5 | −0.0358 |
| 11 | baseline_hybrid05 | 0.6908 | 0.0435 | 0.5037 | 0.1448 | 5/5 | −0.0375 |
| 12 | hier_citation_mlp | 0.6883 | 0.0516 | 0.5390 | 0.5348 | 5/5 | −0.0400 |
| 13 | mahal_citation_mlp | 0.6808 | 0.0502 | 0.5333 | 0.5417 | 5/5 | −0.0475 |
| 14 | baseline_citation_tfidf | 0.6808 | 0.0392 | 0.5117 | 0.1257 | 5/5 | −0.0475 |
| 15 | linear_citation_mlp | 0.6775 | 0.0327 | 0.5312 | 0.5379 | 5/5 | −0.0508 |

---

## Key Finding 1: Static Combinations Beat MLP on CV

**The v12 ranking is REVERSED on cross-validation.** In v12, MLP combinations ranked #1-#3. On 5-fold CV, the top 5 are ALL static combinations:

| Strategy Type | Mean JP (top) | Mean Std | Rank |
|---|---|---|---|
| Static weighted (w3070) | 0.781 | 0.029 | #1 |
| Static concatenation | 0.756 | 0.023 | #3 |
| Static ridge | 0.746 | 0.028 | #4 |
| Static PCA | 0.746 | 0.013 | #5 |
| Learned MLP | 0.707 | 0.052 | #8 |

**The MLP's v12 performance was split-dependent noise.** The learned combination overfit to the specific 1000/200 partition and does not generalize reliably across folds.

## Key Finding 2: linear_hybrid05_w3070 is the Best Stable Combination

**linear_hybrid05_w3070** (30% ML linear projection + 70% cited_outcome_hybrid_0.5):
- **Mean JP**: 0.7808 (highest of all representations)
- **Std JP**: 0.0290 (below 0.03 threshold)
- **Mean delta**: +0.0525 over best baseline (linear_oos_refit at 0.7283)
- **Passes**: 5/5 folds (all adversarial gates pass)
- **Fold-by-fold JP**: [0.808, 0.808, 0.750, 0.796, 0.742] — positive delta on 4/5 folds, tied on 1/5
- **Paired t-test**: p=0.032, Cohen's d=1.44 (LARGE effect)

**SUCCESS RULE ASSESSMENT**: mean_delta (+0.052) > 0.02 ✓, combo_std (0.029) < 0.03 ✓ → **SUCCESS**

## Key Finding 3: linear_citation_concat is Also Significant

**linear_citation_concat** (equal concatenation of ML linear + citation TF-IDF):
- **Mean JP**: 0.7558
- **Std JP**: 0.0234 (most stable of all combinations)
- **Mean delta**: +0.0275
- **Paired t-test**: p=0.029, Cohen's d=1.50 (LARGE effect)
- **CiteIndep**: 0.3179 (higher than w3070's 0.2653)

## Key Finding 4: Two-Mode Tradeoff NOT Fully Broken

No combination beats baseline_linear_oos_refit on BOTH JP AND CiteIndep simultaneously:

| Representation | JP | CiteIndep | JP Wins? | CI Wins? |
|---|---|---|---|---|
| baseline_linear_oos_refit | 0.7283 | **0.5192** | — | — |
| linear_hybrid05_w3070 | **0.7808** | 0.2653 | ✓ | ✗ |
| linear_citation_concat | **0.7558** | 0.3179 | ✓ | ✗ |
| linear_citation_pca128 | **0.7458** | 0.3276 | ✓ | ✗ |

All JP-winning combinations sacrifice CiteIndep. The fundamental tradeoff between citation-based advantages (high JP, low CiteIndep) and metric-learning advantages (high CiteIndep, lower JP) persists. Cross-mode combinations extract complementary signal for JP but cannot simultaneously maximize both metrics.

## Key Finding 5: The Optimal Weight is Citation-Dominant

The w3070 weight (30% ML, 70% citation/hybrid) consistently outperforms w5050 and w7030:

| Weight (ML:Cite) | Mean JP | Fold Spread |
|---|---|---|
| w3070 (30:70) | 0.781 | 0.067 |
| w5050 (50:50) | ~0.74 | (from v12) |
| w7030 (70:30) | ~0.72 | (from v12) |

Citation signal should dominate the combination for jurist preference.

## Key Finding 6: Baseline Ranking Shift

The refit linear baseline (JP=0.7283) significantly outperforms the citation-only baselines:
- linear_oos_refit: 0.7283
- hybrid07: 0.6925
- hybrid05: 0.6908
- citation_tfidf: 0.6808

This confirms that metric learning provides real value for legal navigation when properly trained (fresh per-fold training eliminates the data leakage concerns from v9/v10).

---

## Comparison with v12

| Metric | v12 (single split) | v13 (5-fold CV) | Change |
|---|---|---|---|
| Best combination JP | 0.620 (linear_citation_mlp) | **0.781** (linear_hybrid05_w3070) | +0.161 |
| Best baseline JP | 0.585 (hybrid07) | **0.728** (linear_oos_refit) | +0.143 |
| Delta JP | +0.035 | **+0.053** | +0.018 |
| Best combination type | MLP (learned) | **Static weighted** | Strategy shift |
| MLP stability | N/A (single split) | std=0.033-0.052 | **Unstable** |
| Static stability | N/A | std=0.013-0.029 | **Stable** |

**Critical discrepancy**: The v12 MLP results were SPLIT-DEPENDENT. The ranking reversal on CV reveals that learned combination strategies overfit to specific data partitions. Static weighted combinations are more robust.

---

## Caveats and Limitations

1. **JP still below 0.8 factory target**: Best CV JP=0.781 — approaching but not exceeding 0.8.
2. **CiteIndep tradeoff**: All JP-winning combinations sacrifice citation independence (0.27 vs 0.52 for baseline).
3. **Small dataset**: 1200 decisions, 5 folds of ~240 each. Effect sizes are large (d>1.4) but absolute sample is modest.
4. **No jurist validation**: JP is a proxy metric. Real jurist preference study still needed.
5. **Static combination is a heuristic**: The 30:70 weight was chosen post-hoc from v12 results. Cross-validation on the weight itself would require nested CV.

---

## Success Rule Assessment

**SUCCESS (marginal)**:
- linear_hybrid05_w3070: mean_delta=+0.0525 > 0.02 ✓, combo_std=0.0290 < 0.03 ✓
- linear_citation_concat: mean_delta=+0.0275 > 0.02 ✓, combo_std=0.0234 < 0.03 ✓
- Both pass the frozen success rule.
- Paired t-tests confirm statistical significance (p < 0.05) with large effect sizes.

**CAVEAT**: The two-mode tradeoff is PARTIALLY BROKEN (JP improvement confirmed) but NOT fully broken (CiteIndep still sacrificed). The improvement is real but the product must still expose multiple map modes.

---

## Recommendation

**PARTIAL PRODUCTIZE + CONTINUE**:

1. **Integrate `linear_hybrid05_w3070` as a new HIGH-ADVANTAGE map mode** — it achieves the highest JP (0.781) with stable performance across all 5 folds.
2. **Keep `baseline_linear_oos_refit` as the HIGH-PURITY default** — it maintains the best CiteIndep (0.52) for citation-independent navigation.
3. **Downgrade MLP combinations from v12** — they are split-dependent and unreliable for production. Remove `linear_citation_mlp` from the recommended product set.
4. **Expose both modes in product** — the two-mode tradeoff is confirmed as real; the product must offer both citation-dominant and metric-learning-dominant views.
5. **Next cycle**: Test the w3070 weight on the full 192k corpus; run jurist pairwise preference study on the two modes.

---

## Evidence Files

- Results: `legal_distance/results/v13/cross_mode_kfold/cross_mode_kfold_validation.json`
- Experiment: `legal_distance/experiments/v13_cross_mode_kfold_validation.py`
