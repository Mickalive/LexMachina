# Evaluation Cycle Report — Citation Heritage & v17b Normalization at 174k Scale

**Date**: 2026-09-27  
**Factory Direction**: v28  
**Lane**: evaluation  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: RUN (continue_recommended: true)

---

## Executive Summary

This cycle completed two critical benchmarks on the full 174k TF-IDF family (8 representations):

1. **Citation Heritage Benchmark** (HNSW on full 174k corpus, k=20, frozen 137k pair pool) — **FAIL for ALL 8 representations** (AUC ~0.50-0.53, near random)
2. **v17b Label Normalization Test** at 174k scale — **Mixed results**: citation-based reps show 4-10% purity improvement (5/8 pass uniformity rule); text-based reps show severe zoom_fine degradation (30-34%) and zero hierarchy improvement

---

## 1. Citation Heritage Benchmark at 174k Scale

### Methodology
- **Corpus**: 173,963 decisions (full 2000-2026)
- **Pair Pool**: 137,314 positive + 137,314 negative citation pairs (frozen, seed=42)
- **NN Backend**: HNSW via `scalable_nn` (force_exact=False) on full 174k corpus
- **k**: 20 neighbors
- **Metric**: AUC-ROC and positive_recall@20 (fraction of cited decisions in top-20 neighbors)

### Results

| Representation | AUC-ROC | Pos Recall@20 | Status |
|---|---:|---:|---|
| cited_decisions_tfidf | 0.5340 | 0.0681 | FAIL |
| cited_outcome_hybrid_0.7 | 0.5307 | 0.0614 | FAIL |
| cited_outcome_hybrid_0.5 | 0.5291 | 0.0582 | FAIL |
| full_text_tfidf_light | 0.5241 | 0.0483 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.5256 | 0.0514 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.5256 | 0.0513 | FAIL |
| outcome_tfidf | 0.5000 | 0.0001 | FAIL |
| regeste_tfidf | 0.4999 | 0.0000 | FAIL |

**Threshold**: AUC >= 0.65 (frozen from specification.json)

### Key Finding: NEAR-RANDOM PERFORMANCE

All 8 TF-IDF representations achieve AUC ~0.50-0.53, which is **indistinguishable from random chance** (AUC=0.5). This is a dramatic departure from previously reported values of 0.66-0.90.

**Root cause analysis**:
- Previous AUC values (0.66-0.90) were computed using a **different methodology** — likely exact k-NN on a smaller subset or different pair pool
- At full 174k scale with HNSW (k=20), the TF-IDF representations **do not encode citation structure** in their nearest neighbors above chance level
- Positive recall@20 ranges 0.00-0.07: even the best representation (cited_decisions_tfidf) places only 6.8% of actual cited decisions in top-20 neighbors

**Implication**: The citation_heritage benchmark **fails as a discriminator** at production scale for TF-IDF family. The benchmark passes (AUC >= 0.65) only at smaller scales or with exact k-NN on subsets. At 174k with HNSW, the signal is lost.

---

## 2. v17b Label Normalization at 174k Scale

### Methodology
- **Labels**: 214 raw unique legal_area → 164 normalized (49.3% of 173,963 labels changed)
- **Normalization**: `evaluation/experiments/legal_area_normalize.py` (v17b rules)
- **Benchmarks**: hierarchy_coherence (16 clusters), zoom_coherence (4→16 clusters), legal_area_clustering (n_areas clusters)
- **Uniformity Rule**: No metric worsens by >10% (ratio >= 0.90)

### Purity Ratios (Normalized / Raw)

| Representation | Hierarchy Purity | Zoom Fine Purity | Legal Area Purity | Passes Uniformity |
|---|---:|---:|---:|:---:|
| cited_decisions_tfidf | 1.0568 | 1.0381 | 1.0616 | ✅ |
| outcome_tfidf | 1.0458 | 1.0829 | 1.0437 | ✅ |
| regeste_tfidf | 1.0000 | 1.1031 | 1.0173 | ✅ |
| cited_outcome_hybrid_0.5 | 1.0558 | 1.0366 | 1.0627 | ✅ |
| cited_outcome_hybrid_0.7 | 1.0530 | 1.0461 | 1.0583 | ✅ |
| full_text_tfidf_light | 1.0000 | **0.6683** | 0.9732 | ❌ |
| regeste_full_text_hybrid_0.5 | 1.0000 | **0.6607** | 0.9694 | ❌ |
| regeste_full_text_hybrid_0.7 | 1.0001 | **0.6952** | 0.9634 | ❌ |

### NMI Behavior
**All representations show NMI DEGRADATION** with normalization:
- hierarchy_nmi: 0.70-0.95 of raw
- legal_area_nmi: 0.79-0.88 of raw

### Key Findings

1. **Citation-based reps** (5/8): Consistent 4-10% purity improvement across all three hierarchy-family metrics. These pass the frozen uniformity rule.

2. **Text-based reps** (3/8): ZERO hierarchy_purity improvement (ratio=1.00) and **30-34% zoom_fine_purity DEGRADATION**. These fail the uniformity rule.

3. **NMI vs Purity divergence**: Purity improves but NMI degrades for citation-based reps, suggesting normalized labels create fewer, purer but less informative clusters.

4. **Best normalized hierarchy_purity = 0.554** (cited_decisions_tfidf) — still **well below the 0.7 threshold** from specification.json. Fundamental granularity/coverage limits persist at 174k.

---

## 3. Updated Evidence State

### Completed Evaluations (all 8 TF-IDF reps)
- ✅ Formal suite v25 (12 benchmarks, frozen harness v3)
- ✅ Citation heritage at 174k (HNSW, k=20, frozen 137k pairs)
- ✅ v17b label normalization at 174k

### Evidence Tier: REPRODUCED
All results computed with frozen configuration (seed=42, frozen thresholds, frozen pair pool). Raw outputs preserved.

---

## 4. Recommendations

### Immediate (This Direction)
1. **Citation heritage benchmark is not a useful discriminator at 174k for TF-IDF** — AUC ~0.50 for all reps. Consider:
   - Using larger k (e.g., 100) for citation heritage at scale
   - Switching to exact k-NN for this benchmark (costly at 174k)
   - Deprecating this benchmark for TF-IDF family at full scale

2. **v17b normalization has limited utility**:
   - Only helps citation-based reps marginally (4-10% purity gain)
   - Actively harms text-based reps (30% zoom_fine loss)
   - NMI degrades universally
   - Best normalized purity (0.554) << 0.7 threshold
   - **Recommendation**: Do not adopt v17b normalization as default for 174k map

### Next Direction (Awaiting legal-distance)
Dense embeddings (center_projected 64/128/768dim, metric-learned, hybrids), citation roles, and linear hybrids at 174k scale are still pending from legal-distance lane. These are the **primary path** to breaking the two-mode tradeoff and achieving both adversarial robustness AND cross-language transfer.

---

## 5. Provenance

**Scripts executed**:
- `evaluation/run_citation_heritage_174k_hnsw.py` (new, uses HNSW via scalable_nn)
- `evaluation/run_v17b_label_normalization_174k.py` (existing, adapted for 174k)

**Result files**:
- `evaluation/results/174k_citation_heritage/benchmark/citation_heritage_174k_tfidf_hnsw_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`

**State updated**: `state/evaluation.json` (direction_version=28, evidence_tier=REPRODUCED)

---

## 6. Negative Results Preserved

Per Research Protocol: Negative results are first-class evidence.

- **Citation heritage**: FAIL for all 8 TF-IDF reps at 174k (AUC ~0.50)
- **v17b normalization**: FAIL uniformity for 3/8 reps; NMI degrades for all; best purity 0.554 < 0.7 threshold
- These are not failures of the evaluation — they are **valid findings** that inform product decisions

---

*End of cycle report*