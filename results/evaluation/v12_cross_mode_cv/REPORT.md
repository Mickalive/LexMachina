# v12 Cross-Mode Combination: 5-Fold Cross-Validation Report

**Date:** 2026-08-30
**Lane:** evaluation
**Config:** seed=42, config_hash=4323f833fa72366a, canonical frozen harness v3

---

## Hypothesis (Frozen Before Observation)

The v12 finding that combining citation-based features with metric-learning embeddings improves JuristPref by +0.035 over the best individual baseline is **stable** across different data splits.

---

## Experimental Setup

- **Corpus:** 1000 BGer decisions (2020-2024), canonical fractal-map baseline
- **Method:** 5-fold cross-validation (800 train / 200 test per fold)
- **Baselines:** center_projected_64dim, citation_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7
- **Combinations:** linear_citation_concat, linear_hybrid05_concat, linear_citation_w3070, linear_citation_pca128, linear_citation_ridge
- **Adversarial gates:** LangDom < 0.85, JuristPref > 0.5
- **Success rule:** Mean JP improvement > 0 across folds AND all folds pass both adversarial gates

---

## Results Summary

### Per-Fold Results

| Fold | Best Baseline JP | Best Combination JP | Delta |
|------|------------------|---------------------|-------|
| 1 | 0.8000 | 0.5850 | -0.2150 |
| 2 | 0.8350 | 0.4250 | -0.4100 |
| 3 | 0.8300 | 0.5950 | -0.2350 |
| 4 | 0.8450 | 0.6050 | -0.2400 |
| 5 | 0.8500 | 0.6400 | -0.2100 |

### Aggregate Rankings (by JP mean)

| Representation | JP Mean | JP Std | LD Mean | AdvPass |
|----------------|---------|--------|---------|---------|
| cited_outcome_hybrid_0.5 | 0.8220 | 0.0196 | 0.5026 | 100% |
| cited_outcome_hybrid_0.7 | 0.8210 | 0.0252 | 0.5104 | 100% |
| citation_tfidf | 0.8090 | 0.0211 | 0.5080 | 100% |
| linear_citation_w3070 | 0.5700 | 0.0748 | 0.7297 | 80% |
| linear_citation_ridge | 0.3550 | 0.0659 | 0.8242 | 0% |
| linear_citation_pca128 | 0.2520 | 0.0612 | 0.8992 | 0% |
| linear_hybrid05_concat | 0.2500 | 0.0532 | 0.8980 | 0% |
| linear_citation_concat | 0.2440 | 0.0533 | 0.8988 | 0% |
| center_projected_64dim | 0.1650 | 0.0446 | 0.9322 | 0% |

---

## Key Findings

### 1. Citation-Only Dominates
Citation-only representations (citation_tfidf, cited_outcome_hybrid) achieve JP=0.80-0.82 with LD=0.49-0.51. They pass both adversarial gates on all 5 folds. The language independence advantage is genuine and stable.

### 2. center_projected_64dim Fails Adversarial Gates
On fresh 5-fold splits (not the static 80/10/10 holdout), center_projected_64dim achieves JP=0.165, LD=0.932. This is far below the adversarial thresholds. The production default is dominated.

### 3. Combinations WORSE Than Baselines
Every combination strategy performs worse than citation-only baselines:
- linear_citation_concat: JP=0.244 (-0.588 vs best baseline)
- linear_hybrid05_concat: JP=0.250 (-0.582 vs best baseline)
- linear_citation_w3070: JP=0.570 (-0.262 vs best baseline)
- linear_citation_pca128: JP=0.252 (-0.580 vs best baseline)
- linear_citation_ridge: JP=0.355 (-0.477 vs best baseline)

Combining a language-dependent representation (center_projected_64dim) with a language-independent one (citation_tfidf) introduces language dominance signal that degrades jurist preference.

### 4. v12 Claim FALSIFIED
The claimed +0.035 improvement does not replicate. Instead, we observe a **-0.262 degradation** (mean across folds). Zero of five folds show positive improvement.

---

## Verdict

**FALSIFIED** — The v12 cross-mode combination improvement does not replicate under5-fold cross-validation on the canonical frozen harness v3. The degradation is consistent (0/5 positive folds) and large (mean Δ = -0.262).

---

## Negative Result Provenance

- Experiment script: `evaluation/experiments/evaluate_v12_cross_mode_cv.py`
- Raw results: `results/evaluation/v12_cross_mode_cv/v12_cross_mode_cv_eval_v12_cv_1788127322.json`
- Canonical corpus: `/tmp/lex_accepted/corpus/corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl`
- Baseline embeddings: `/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy`
- Frozen config: seed=42, config_hash=4323f833fa72366a

---

## Implications

1. **Production default is center_projected_64dim** — but this is dominated by citation-only representations
2. **No combination strategy improves over citation-only** — the language-dependence signal in center_projected_64dim is noise, not signal
3. **The real question shifts** — not "how to combine modes" but "should we replace center_projected_64dim with citation-only as the production default?"
4. **v12 combination hypotheses are closed** — all five combination strategies tested and falsified
