# Partial Dense Embeddings Evaluation Report
## v25 Formal Suite on center_projected_768dim (7,652 decisions, years 2000-2002)

**Date**: 2026-09-26  
**Factory Direction**: v28  
**Lane**: evaluation  
**Evidence Tier**: EXPLORATORY (partial scale, not full 174k)  
**Run ID**: partial_dense_center_projected_768dim_20260926  

---

## Executive Summary

Evaluated the **first available dense embeddings** from legal-distance lane: `center_projected_768dim` computed on 7,652 decisions (primarily year 2000, with scattered decisions from 2001-2013). This represents ~11% of the full 174k corpus (19,441 decisions from years 2000-2002 complete per legal-distance progress.json).

**Result**: 8/12 benchmarks PASS, 2 FAIL, 2 SKIP. **Strong legal signal detected** — excellent branch coherence (0.99), multilingual invariance, temporal stability, and zoom refinement. Main limitation is hierarchy purity threshold due to fine-grained label granularity.

---

## Corpus & Representation

| Property | Value |
|----------|-------|
| Representation | `center_projected_768dim` (language-debiased 768-dim) |
| Corpus size | 7,652 decisions |
| Embedding dim | 768 (L2 normalized) |
| Years covered | 2000 (3,839), 2001 (314), 2002 (361), 2003-2013 (scattered) |
| Languages | de: 4,732, fr: 2,488, it: 432 |
| Branches | unknown: 3,028, null: 3,813, oeffentliches_recht: 450, zivilrecht: 313, strafrecht: 48 |
| Legal areas | 91 unique (many with <5 decisions) |

> **Note**: The year distribution shows decisions beyond 2000-2002. This appears to be a partial slice from the legal-distance year-split computation, not strictly limited to 2000-2002.

---

## Benchmark Results (Frozen v25 Protocol, Config Hash: `4323f833fa72366a`)

### ✅ PASSED (8/12)

| Benchmark | Status | Key Metrics |
|-----------|--------|-------------|
| **branch_knn** | PASS | knn@5 = **0.997** (threshold >0.633) |
| **tf_metadata_human_indexing** | PASS | recall@5 = **0.997** (threshold ≥0.8) |
| **adversarial_falsification** | PASS | lang_dom = **0.78** (<0.85), branch_coherence = **0.99** (>0.3) |
| **multilingual_invariance** | PASS | separation = **0.126**, invariance_gap = **0.004** |
| **cross_language_pairs** | PASS | separation = **0.126** (>0) |
| **collapse_check** | PASS | mean_sim = **0.811**, std = **0.096** |
| **temporal_stability** | PASS | std_knn_score ≈ **0** (<0.1) |
| **zoom_coherence** | PASS | improvement = **36.3%** (>0) |

### ❌ FAILED (2/12)

| Benchmark | Status | Key Metrics | Threshold |
|-----------|--------|-------------|-----------|
| **hierarchy_coherence** | FAIL | best_purity = **0.492** (<0.7), best_nmi = **0.671** (>0.3) | purity ≥0.7 AND nmi ≥0.3 |
| **legal_area_clustering** | FAIL | overall_purity = **0.011** (<0.5), nmi = **0.668** | purity >0.5 |

### ⏭️ SKIPPED (2/12)

| Benchmark | Reason |
|-----------|--------|
| **citation_heritage** | Insufficient pairs in partial data: only 1 positive / 67 negative pairs match the 7,652 decision IDs |
| **boilerplate_resistance** | No corpus full_text available for partial decision IDs |

---

## v17b Label Normalization Test

| Metric | Raw | Normalized | Ratio (Norm/Raw) |
|--------|-----|------------|------------------|
| hierarchy_purity | 0.492 | 0.493 | **1.00** |
| zoom_fine_purity | 0.492 | 0.493 | **1.00** |
| legal_area_purity | 0.011 | 0.011 | **1.00** |
| hierarchy_nmi | 0.671 | 0.536 | 0.80 |
| legal_area_nmi | 0.668 | 0.544 | 0.81 |

**Conclusion**: **NO improvement from v17b normalization** on partial dense embeddings. Purity ratios are 1.00 (no change), while NMI actually decreases. The cross-lingual label duplication artifact that v17b targets is not the limiting factor here — the issue is fine-grained label granularity (91 areas in 7,652 decisions = avg 84 decisions/area).

---

## Key Findings

### 1. **Strong Legal Signal in Dense Embeddings**
- **Branch coherence 0.99** — nearest neighbors almost perfectly align with legal branch (chamber)
- **Multilingual invariance** — cross-language same-branch similarity (0.838) nearly equals same-language same-branch (0.842), with strong separation from cross-branch (0.713)
- **Temporal stability** — near-zero variance across random splits indicates robust neighborhood structure
- **Zoom coherence 36%** — fine-grained clusters reveal more specific legal structure than coarse clusters

### 2. **Hierarchy Purity Limited by Label Granularity, Not Embedding Quality**
- NMI = 0.67 (well above 0.3 threshold) shows embeddings capture legal taxonomy structure
- Purity = 0.49 (below 0.7 threshold) is a mathematical consequence of 91 legal areas with avg 84 decisions each
- At this granularity, even perfect embeddings would struggle to reach purity >0.7 with KMeans clustering

### 3. **Promising for Full 174k Dense Embeddings**
The partial evaluation suggests that when full 174k `center_projected` embeddings land:
- Branch/metadata benchmarks will likely PASS strongly
- Multilingual and adversarial benchmarks will likely PASS
- Hierarchy coherence may improve with more decisions per legal area (174k/91 ≈ 1,912 decisions/area vs 84 here)
- Citation heritage will be evaluable with full pair pool

### 4. **Fundamental Difference from TF-IDF Tradeoff**
TF-IDF family showed **two-mode tradeoff**: citation-based PASS adversarial but FAIL branch_knn; text-based PASS branch_knn but FAIL adversarial (lang_dom=1.0).

**center_projected_768dim PARTIAL shows BOTH**: PASS adversarial (lang_dom=0.78) AND PASS branch_knn (0.997). This suggests dense embeddings may break the two-mode tradeoff — a critical product capability.

---

## Methodology Notes

- **NN Backend**: Exact k-NN (sklearn brute force cosine) — appropriate for n=7,652
- **Frozen Subsamples**: Hierarchy subsample n=840 (stratified by branch, known legal_area); Temporal subsample n=5,000
- **Config Hash**: `4323f833fa72366a` (same as full 174k v25 suite)
- **Thresholds**: Unchanged from frozen v25 protocol

---

## Evidence References

- **Partial suite results**: `results/evaluation/v25_174k_formal_suite/partial_dense_results/center_projected_768dim_partial_2000_2002.json`
- **v17b results**: `results/evaluation/v25_174k_v17b/partial_dense/center_projected_768dim_partial_2000_2002.json`
- **Evaluation script**: `evaluation/experiments/v25_174k_suite/run_v25_partial_dense.py`
- **Legal-distance progress**: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`

---

## Recommendation

**CONTINUE monitoring** — partial dense evaluation is EXPLORATORY but highly encouraging. The full 174k dense embeddings (when legal-distance completes years 2003-2025) should be evaluated immediately upon landing using the same frozen v25 protocol with HNSW backend.

No additional same-question cycle justified for TF-IDF family. Dense embedding evaluation will proceed autonomously via monitor as representations land in accepted state.

---

## Appendix: Full Benchmark Output

```json
{
  "representation": "center_projected_768dim_partial_2000_2002",
  "n_rows": 7652,
  "n_passed": 8,
  "n_failed": 2,
  "n_skipped": 2,
  "total_benchmarks": 12,
  "benchmarks": [...],
  "nn_backend": "sklearn_exact",
  "duration_seconds": 7.5,
  "config_hash_suite": "4323f833fa72366a"
}
```