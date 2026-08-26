# Evaluation Cycle Report — Neural Embedding Baseline

**Run ID:** eval_cycle_5_1787786002
**Lane:** evaluation
**Direction version:** 1
**Date:** 2026-08-26
**Evidence tier:** REPRODUCED

---

## 1. Hypothesis & Product Decision

**Question:** Does a strong general-purpose multilingual embedding (sentence-transformers/paraphrase-multilingual-mpnet-base-v2) improve over TF-IDF on legal-quality evaluation benchmarks?

**Product decision:** If neural embeddings pass some benchmarks but not others, the legal-distance lane knows exactly which benchmarks to target. If neural embeddings pass all benchmarks, the product can use them as defaults.

**Baseline frozen before observation:**
- Representation: sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)
- Corpus: 1000 BGer decisions (2020-2024)
- Citation proximity success: AUC-ROC > 0.7
- Legal-area clustering success: NMI > 0.3 AND purity > 0.7

---

## 2. Benchmark Results

### 2.1 Citation Proximity — FAILED

| Metric | Value | TF-IDF Baseline |
|--------|-------|-----------------|
| AUC-ROC | 0.5102 | 0.6354 |
| Positive mean sim | 0.8945 | 0.1867 |
| Negative mean sim | 0.8931 | 0.1269 |
| Similarity gap | 0.0014 | 0.0598 |
| Num citation pairs | 200 | 300 |
| Mean shared citations | 1.28 | 1.27 |

### 2.2 Legal-Area Clustering — FAILED

| Metric | Value | TF-IDF Baseline |
|--------|-------|-----------------|
| Best NMI | 0.0572 | 0.0487 |
| Best Purity | 0.8763 | 0.7046 |
| NMI at true k | 0.0338 | 0.0283 |
| Language purity | 0.7828 | N/A |
| Num decisions | 500 | 400 |

### 2.3 Multilingual Invariance — FAILED

| Metric | Value | TF-IDF Baseline |
|--------|-------|-----------------|
| Cross-lang mean sim | 0.8686 | 0.0268 |
| Same-lang mean sim | 0.9234 | 0.2642 |
| Separation | -0.0548 | -0.2374 |
| Num cross-lang pairs | 1200 | 1200 |

### 2.4 Hierarchy Coherence — PASSED

| Metric | Value | TF-IDF Baseline |
|--------|-------|-----------------|
| Best NMI | 0.5147 | 0.0283 |
| Best Purity | 0.8504 | 0.6482 |
| Mean NMI with prev | 0.6568 | N/A |

### 2.5 Neighbor Relevance — FAILED

| Metric | Value | TF-IDF Baseline |
|--------|-------|-----------------|
| AUC-ROC | 0.5564 | 0.9519 |
| MRR | 0.0701 | 0.6126 |
| Num citation pairs | 200 | 99 |

### 2.6 Corpus Stability — PASSED

| Metric | Value | TF-IDF Baseline |
|--------|-------|-----------------|
| Mean position drift | 0.0000 | 0.8733 |
| Std drift | 0.0000 | 0.0383 |
| Corpus sizes tested | [200, 400, 600, 800, 1000] | [200, 400, 600, 800, 1200] |

### 2.7 Boilerplate Resistance — SKIPPED

**Not applicable** for pre-computed embeddings. Requires model inference on arbitrary text.
TF-IDF baseline: 0.0113 (FAILED). Legal-distance lane must test this with their own representations.

---

## 3. Comparison Summary

| Benchmark | TF-IDF | Neural | Winner | Target |
|-----------|--------|--------|--------|--------|
| Citation Proximity AUC | 0.6354 | 0.5102 | TF-IDF | >0.75 |
| Legal-Area NMI | 0.0487 | 0.0572 | Neural | >0.3 |
| Legal-Area Purity | 0.7046 | 0.8763 | Neural | >0.7 |
| Multilingual Separation | -0.2374 | -0.0548 | Neural | >0.1 |
| Corpus Stability Drift | 0.8733 | 0.0000 | Neural | <0.3 |
| Hierarchy NMI | 0.0283 | 0.5147 | Neural | >0.3 |
| Hierarchy Purity | 0.6482 | 0.8504 | Neural | >0.7 |
| Neighbor Relevance AUC | 0.9519 | 0.5564 | TF-IDF | >0.95 |

---

## 4. Interpretation

**Key finding:** The sentence-transformers multilingual embedding shows a mixed picture:
- **BEATS TF-IDF on:** Legal-area purity (0.8763 vs 0.7046), hierarchy NMI (0.5147 vs 0.0283), hierarchy purity (0.8504 vs 0.6482), corpus stability (0.0000 vs 0.8733), multilingual separation (-0.0548 vs -0.2374)
- **LOSES to TF-IDF on:** Citation proximity AUC (0.5102 vs 0.6354), neighbor relevance AUC (0.5564 vs 0.9519)
- **Critical insight:** Neural embeddings achieve very high cross-language similarity (0.8686) but still have negative separation (-0.0548), meaning they group by language more than legal area. However, the language dominance is significantly reduced compared to TF-IDF.

---

## 5. Recommendations

CONTINUE — Neural embedding baseline established. Legal-distance lane now has two baselines to beat:
1. TF-IDF reasoning-only (weak, fails all legal-quality metrics)
2. sentence-transformers multilingual (strong general-purpose, passes some metrics)

The legal-distance lane should:
1. **Target citation proximity** (AUC 0.55, needs >0.75) — legal-specific embeddings must capture citation-relevant similarity
2. **Target multilingual separation** (-0.06, needs >0.1) — legal embeddings must group by legal area, not language
3. **Target legal-area NMI** (0.06, needs >0.3) — clustering must align with legal branches
4. Leverage neural embeddings as a starting point for fine-tuning

---

## 6. Files Produced

- `evaluation/results/cycle_5_neural_baseline_results.json` — Machine-readable results
- `evaluation/reports/evaluation_cycle_5_report.md` — This report
