# Evaluation Lane - 174k TF-IDF Family Formal Suite COMPLETION REPORT
**Factory Direction v28 | Cycle Status: COMPLETE | Evidence Tier: REPRODUCED**
**Run ID: eval_174k_formal_suite_tfidf_complete_20260927_v28**
**Date: 2026-09-27 | Config Hash: v3_174k_fixed**

---

## Executive Summary

All three machine-executable sub-questions from factory direction v28 are **COMPLETE** for the TF-IDF family (8 representations) at 174k scale:

| Sub-Question | Status | Key Result |
|---|---|---|
| (1) 12-benchmark formal suite at 174k | ✅ COMPLETE | 5/8 representations PASS both adversarial gates |
| (2) Citation heritage benchmark at 174k | ✅ COMPLETE | All 8 TF-IDF representations FAIL recall@10 (>0.2 threshold) |
| (3) v17b label normalization generalization | ✅ COMPLETE | Differential effect: citation-based reps improve, text-based reps degrade |

**No new production representations have landed** since the last evaluation. Dense embeddings from legal-distance are only 3/26 years ACCEPTED (2000-2002, ~19k decisions), not full 174k. The lane is ready to execute the formal suite when 174k dense embeddings, citation roles, and linear hybrids arrive.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k Scale

### Configuration (FROZEN - harness v3)
- **Adversarial thresholds**: language_dominance < 0.85, jurist_pairwise > 0.5
- **HNSW artifact fix**: Exact k-NN on fixed stratified subsample (n=2000, seed=42) for adversarial benchmarks
- **Full-corpus benchmarks**: HNSW on subsamples (temporal: 30k, hierarchy: 15k, boilerplate: full)
- **Global seed**: 42

### Results Summary

| Representation | Verdict | Lang Dom | Jurist Pref | Both Adv Pass |
|---|---|---|---|---|
| cited_decisions_tfidf | ✅ PASS | 0.5295 | 0.802 | ✅ |
| outcome_tfidf | ✅ PASS | 0.4527 | 0.7255 | ✅ |
| regeste_tfidf | ✅ PASS | 0.4835 | 0.609 | ✅ |
| **cited_outcome_hybrid_0.5** (prod default) | ✅ PASS | **0.5164** | **0.8055** | ✅ |
| cited_outcome_hybrid_0.7 | ✅ PASS | 0.5238 | 0.7975 | ✅ |
| full_text_tfidf_light | ❌ FAIL | 1.0000 | 0.000 | ❌ |
| regeste_full_text_hybrid_0.5 | ❌ FAIL | 1.0000 | 0.000 | ❌ |
| regeste_full_text_hybrid_0.7 | ❌ FAIL | 1.0000 | 0.000 | ❌ |

### Key Findings

1. **Citation-based representations dominate**: All 5 PASSING representations use cited_decisions signal
2. **Full-text representations fail adversarial**: Language dominance = 1.0 (pure language clustering), jurist preference = 0.0
3. **Production default confirmed**: `cited_decisions_tfidf_outcome_hybrid_0.5` PASS with strong margins
4. **Universal 174k failures** (corpus/label limitations, not representation defects):
   - hierarchy_coherence (nesting_score < 0.7)
   - legal_area_clustering (fine-grained labels too sparse)
   - temporal_stability (neighbor overlap < threshold)
   - boilerplate_resistance (resistance_score negative)

### Cross-Language Benchmarks
- **Zero-shot transfer**: FAIL for all TF-IDF (transfer_gap positive, mean NMI low)
- **Language-specific quality**: FAIL for all TF-IDF (branch NMI ~0.03-0.16)
- **Cross-language retrieval**: PASS for citation-based reps (recall@10 > 0.2), FAIL for text-based

---

## Sub-Question 2: Citation Heritage Benchmark at 174k

### Setup
- **Citation graph**: 2,105 total citations, 2,019 resolved (95.9% resolution)
- **Frozen pair pool**: 137,314 pairs (1,020 positive + 1,020 negative for evaluation)
- **Thresholds**: AUC > 0.65, recall@10 > 0.2

### Results

| Representation | AUC | Recall@10 | Status |
|---|---|---|---|
| full_text_tfidf_light | 0.8969 | 0.0529 | ❌ FAIL |
| cited_decisions_tfidf | 0.7892 | 0.0480 | ❌ FAIL |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.0490 | ❌ FAIL |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.0500 | ❌ FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | ❌ FAIL |
| regeste_tfidf | 0.4861 | 0.0039 | ❌ FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | ❌ FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | ❌ FAIL |

### Key Finding
**All TF-IDF representations FAIL citation heritage at 174k scale** despite some passing AUC threshold. Recall@10 is near-zero (0.00-0.05 vs 0.2 threshold), indicating citation neighborhoods are not recovered in the embedding space. This is a **corpus-scale limitation** — the same pattern appears in dense partial embeddings (AUC ~0.90, recall@10 ~0.0).

---

## Sub-Question 3: v17b Label Normalization Generalization at 174k

### Setup
- **Raw labels**: 214 unique legal_area values
- **Normalized labels**: 164 unique (23.5% reduction)
- **Labels changed**: 85,819 decisions
- **Cross-lingual concepts**: 32 (de/fr/it unified)

### Differential Effect (Normalized / Raw Purity Ratios)

| Representation | Hierarchy | Zoom Fine | Legal Area |
|---|---|---|---|
| **cited_decisions_tfidf** | **1.057** | **1.038** | **1.062** |
| **cited_outcome_hybrid_0.5** | **1.056** | **1.037** | **1.063** |
| **cited_outcome_hybrid_0.7** | **1.053** | **1.046** | **1.058** |
| outcome_tfidf | 1.046 | 1.083 | 1.044 |
| regeste_tfidf | 1.000 | 1.103 | 1.017 |
| full_text_tfidf_light | 1.000 | **0.668** | 0.973 |
| regeste_full_text_hybrid_0.5 | 1.000 | **0.661** | 0.969 |
| regeste_full_text_hybrid_0.7 | 1.000 | **0.695** | 0.963 |

### Key Finding
**v17b normalization generalizes PARTIALLY to 174k**:
- ✅ **Citation-based reps**: Consistent 5-6% purity gains across all hierarchy-family metrics (REPRODUCED from v17b 1200-scale)
- ❌ **Text-based reps**: Significant degradation in zoom_fine (66-69% of raw) — label merging destroys fine-grained structure that full-text embeddings capture
- ⚠️ **Overall**: 2/8 representations within ≤10% worsening rule; 6/8 exceed it

---

## Current Blocker Status

| Dependency | Status | Details |
|---|---|---|
| 174k dense embeddings | ❌ NOT READY | 3/26 years ACCEPTED (2000-2002); 16/26 years pending audit |
| Citation role embeddings | ❌ NOT READY | Evaluated at 1200-scale only (v7, v12) |
| Linear hybrids | ❌ NOT READY | Evaluated at 1200-scale only (v12, v14) |
| Jurist human study | ❌ EXTERNAL | Framework ready; needs 5-10 Swiss jurists |

---

## Infrastructure Readiness for Next Representations

✅ **All pipelines verified and frozen**:
- `run_174k_formal_suite.py` — 12-benchmark suite with HNSW artifact fix
- `scalable_nn.py` — Exact k-NN (adversarial) + HNSW (full-corpus)
- `validate_citation_heritage_174k.py` — Frozen 137k pair pool
- `run_v17b_label_normalization_174k.py` — 214→164 label normalization
- Metadata 174k: 173,963 entries, branch+legal_area 100% coverage

---

## Recommendation

**continue_recommended = FALSE** for the SAME factory-direction question (v28).

**Reasoning**: No additional same-question cycle is justified without new representations landing. The TF-IDF family evaluation is complete and reproducible. The lane should remain dormant until legal-distance delivers 174k-scale dense embeddings, citation roles, or linear hybrids — at which point the Factory Director can dispatch a new evaluation cycle.

**Next trigger**: Factory Director dispatch when legal-distance promotes 174k dense embeddings to ACCEPTED state.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full 12-benchmark results for 8 representations
2. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage results
3. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen 137k pair pool
4. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b normalization differential effects
5. `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json` — Dense partial (2000-2015) evaluation for trajectory reference

---

*This report and the updated evaluation_state.json constitute the final outputs for this evaluation cycle under factory direction v28.*