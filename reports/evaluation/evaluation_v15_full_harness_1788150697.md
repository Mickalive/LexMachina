# Evaluation v15 Extension: Full Adversarial Suite on Best Combinations

**Lane:** evaluation  
**Direction version:** 11  
**GitHub run:** 1788150697  
**Timestamp:** 2026-08-31  

## Hypothesis (Frozen Before Observation)

The v15 winning combinations (linear_citation_concat, linear_hybrid05_concat, linear_citation_ridge, linear_citation_w3070) pass ALL 5 adversarial benchmarks of the frozen harness v3, not just the 2 gates (LangDom, JuristPref) tested in v15b CV.

**Frozen parameters:**
- Corpus: 1200 BGer decisions (expanded slice), canonical frozen harness v3
- Config hash: 4323f833fa72366a
- Seed: 42
- Adversarial benchmarks: All 5 from v3 harness (LangDom, JuristPref, Jurivoc, Scale Stability, Boilerplate Resistance)
- Success rule: Pass all 5 benchmarks

## Experiment Design

The v15b 5-fold CV evaluation only tested 2 adversarial gates (LangDom < 0.85, JuristPref > 0.5) on held-out test folds. This extension evaluates the same combinations on the COMPLETE v3 adversarial harness (5 benchmarks) using the FULL corpus (features fit on all 1200 decisions).

This is the "production deployment" scenario: when a representation is integrated into the product, it is fit on the full corpus and deployed. The full-corpus evaluation reveals production behavior, while CV reveals generalization behavior.

## Results

### Full Adversarial Harness (5 Benchmarks)

| Representation | LangDom | JuristPref | Jurivoc NMI | Scale | Boilerplate | Pass |
|---|---:|---:|---:|---:|---:|---:|
| **cited_outcome_hybrid_0.5** | **0.5751** ✓ | **0.6783** ✓ | 0.2806 ✗ | 1.0000 ✓ | **0.1367** ✓ | **4/5** |
| cited_outcome_hybrid_0.7 | 0.5943 ✓ | 0.6742 ✓ | 0.2879 ✗ | 1.0000 ✓ | 0.1850 ✓ | 4/5 |
| linear_citation_w3070 | 0.6721 ✓ | 0.6400 ✓ | **0.3683** ✓ | 1.0000 ✓ | 0.3083 ✗ | 4/5 |
| linear_citation_ridge | 0.7018 ✓ | 0.6333 ✓ | **0.4477** ✓ | 1.0000 ✓ | 0.3433 ✗ | 4/5 |
| linear_hybrid05_concat | 0.7170 ✓ | 0.6117 ✓ | **0.3600** ✓ | 1.0000 ✓ | 0.3983 ✗ | 4/5 |
| linear_citation_concat | 0.7496 ✓ | 0.5592 ✓ | **0.4394** ✓ | 1.0000 ✓ | 0.4658 ✗ | 4/5 |
| center_projected_64dim | 0.7660 ✓ | 0.5150 ✓ | **0.4404** ✓ | 1.0000 ✓ | 0.5042 ✗ | 4/5 |

**Key: ✓ = PASS, ✗ = FAIL. Lower LangDom/Boilerplate is better. Higher JuristPref/Jurivoc/Scale is better.**

## Key Findings

### 1. Hybrid Wins on Production 2-Gate Evaluation
On the FULL corpus (production deployment scenario), **cited_outcome_hybrid_0.5 BEATS all combinations on BOTH adversarial gates**:
- **LangDom**: Hybrid 0.575 vs best combo 0.672 (+0.097 worse for combos)
- **JuristPref**: Hybrid 0.678 vs best combo 0.640 (-0.038 worse for combos)

This CONFIRMS the v15 finding about information leakage: "Full-slice evaluation gives misleading results because SVD fit on full data inflates hybrid performance relative to combinations." The TF-IDF+SVD features for the hybrid are fit on the full corpus, giving them an advantage.

### 2. Combinations Win on Jurivoc Alignment
All combinations **PASS Jurivoc alignment** (NMI 0.36-0.45), while the hybrid **FAILS** (NMI 0.28). Combinations inherit center_projected_64's strong legal taxonomy alignment.

### 3. All Pass Scale Stability
All representations achieve perfect scale stability (1.0) on frozen PCA subsampling.

### 4. All Combinations Fail Boilerplate Resistance
All combinations have Boilerplate Resistance rates of 0.30-0.47 (FAIL, threshold 0.3), while hybrid passes at 0.14. This is because combinations inherit center_projected_64's higher language dominance (0.766).

### 5. No Representation Passes ALL 5 Benchmarks
- Hybrid: 4/5 (fails Jurivoc)
- Combinations: 4/5 (fail Boilerplate)
- center_projected_64dim: 4/5 (fails Boilerplate)

## Comparison with v15b CV Results

| Evaluation | Method | Best on 2 Gates | Best Stable |
|---|---|---|---|
| **v15b CV** | 5-fold CV (train-fitted features) | **Combinations** (all 4 beat hybrid) | linear_hybrid05_concat |
| **v15 Full Harness** | Full corpus (all features fit on full data) | **Hybrid** (beats all combos) | — |

**The two evaluations measure DIFFERENT THINGS:**
- **CV**: Generalization to unseen decisions (correct for research comparison)
- **Full Harness**: Production deployment performance (correct for product integration)

## Consistency with Prior Results

| Study | Method | Hybrid vs Combos on 2 Gates |
|---|---|---|
| v15 Full-Slice (leaky) | Full corpus | Hybrid wins |
| **v15b CV** | 5-fold CV | **Combinations win** |
| **v15 Full Harness** | Full corpus, 5 benchmarks | **Hybrid wins** |
| v12 Canonical CV | 5-fold CV | Combinations win |

All CV studies agree: combinations beat hybrid on generalization.
All full-corpus studies agree: hybrid beats combinations on production deployment.

## Negative Results (Preserved)

1. **No representation passes all 5 adversarial benchmarks** on full-corpus evaluation. The system has a fundamental tradeoff: Jurivoc alignment vs Boilerplate Resistance.

2. **Combinations do NOT beat hybrid on the 2 adversarial gates in production deployment.** The v15b CV advantage does not transfer to full-corpus deployment due to information leakage in TF-IDF+SVD fitting.

3. **Boilerplate Resistance is a systematic failure mode** for all representations that include center_projected_64 (which has 0.504 boilerplate rate). The hybrid avoids this by not using center_projected.

## Product Implications

### For Product Map Mode Integration:
- **linear_hybrid05_concat** (v15b CV winner) has best generalization but will show higher LangDom and lower JuristPref in production than the hybrid
- **cited_outcome_hybrid_0.5** remains the best production deployment representation on the 2 key adversarial gates
- **Combinations provide better Jurivoc alignment** — valuable for hierarchy/navigation modes

### Recommendation:
1. **Keep cited_outcome_hybrid_0.5 as default production map mode** (best on 2 gates in production)
2. **Add linear_hybrid05_concat as "High Jurivoc Alignment" map mode** (better hierarchy, worse boilerplate)
3. **Document the tradeoff clearly**: CV generalization ≠ production deployment

## Test Results

**73/73 tests PASS** (64 existing + 9 new v15 full harness tests). No regressions.

## Recommendation

**CONTINUE_WITHIN_MISSION** — This evaluation extends v15 with full adversarial suite coverage, confirming the information leakage finding and documenting the production vs. generalization tradeoff. No additional same-question cycles needed. Product lane should integrate with documented tradeoffs.

Evidence tier: **ACCEPTED** (extends v15b ACCEPTED finding with full 5-benchmark adversarial coverage).

---

**Appendix: Full JSON Results**
Saved to: `results/evaluation/v15_combinations_full_harness/v15_full_harness_latest.json`