# Evaluation Lane v29 Verification Report
## 174k Formal Suite Completion Status

**Date**: 2026-10-01  
**Factory Direction Version**: 29  
**Lane**: evaluation  
**Cycle Status**: COMPLETED  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false  

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** from Factory Direction v29 for the currently available production representations (TF-IDF family). The dense embeddings from legal-distance remain BLOCKED (only 3/26 years ACCEPTED).

### Sub-question 1: Full 12-benchmark formal suite at 174k scale ✅ COMPLETED
- **8 TF-IDF representations** evaluated on frozen harness v3 (exact k-NN on valid subset for adversarial benchmarks)
- **All 8 PASS both adversarial gates** (Language Dominance < 0.85, Jurist Pairwise > 0.5)
- **Best representation**: `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4773, JuristPref=0.7345)
- **Production default validated** and wired in product lane

### Sub-question 2: Citation heritage benchmark at 174k ✅ COMPLETED
- **1,020 positive + 1,020 negative citation pairs** from resolved citation graph (2,019/2,105 citations resolved)
- **4/8 representations PASS** (citation-based signals dominate)
- **Production default PASS** (AUC=0.7163)
- **Text-based signals FAIL** (regeste_tfidf AUC=0.503 ~random)
- **Confirms fundamental two-mode tradeoff**

### Sub-question 3: v17b label normalization generalization ✅ TESTED (NEGATIVE RESULT)
- **v17b at 1000 scale**: 15-25% hierarchy purity gain REPRODUCED across 4 seeds (6 reps)
- **At 174k scale**: Label normalization still improves hierarchy purity (ratios 4-10x) but **regime fundamentally different**
  - 213 raw labels → 111 normalized (vs 104→54 at 1000)
  - NMI decreases on normalized labels at 174k
- **Conclusion**: v17b method REPRODUCED but does not "generalize" in same-magnitude sense; 174k fine-grained labels require separate validation

---

## Critical Findings

### 1. TF-IDF Formal Suite Complete at 174k
| Representation | LangDom | JuristPref | Both Pass | Verdict |
|---|---|---|---|---|
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.4773 | 0.7345 | ✅ | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4783 | 0.7275 | ✅ | PASS |
| cited_decisions_tfidf | 0.4794 | 0.7140 | ✅ | PASS |
| full_text_tfidf_light | 0.4855 | 0.7080 | ✅ | PASS |
| regeste_tfidf | 0.4853 | 0.6315 | ✅ | PASS |
| outcome_tfidf | 0.5015 | 0.6550 | ✅ | PASS |
| regeste_full_text_hybrid_0.5 | 0.4855 | 0.6315 | ✅ | PASS |
| regeste_full_text_hybrid_0.7 | 0.4783 | 0.6315 | ✅ | PASS |

**Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` operational at full 173,963 decisions.

### 2. Citation Heritage at 174k - Two-Mode Tradeoff Confirmed
| Representation | AUC-ROC | Status |
|---|---|---|
| cited_decisions_tfidf | 0.7426 | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7290 | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7163 | PASS |
| regeste_full_text_hybrid_0.7 | 0.6595 | PASS |
| full_text_tfidf_light | 0.6257 | FAIL |
| outcome_tfidf | 0.6262 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.6365 | FAIL |
| regeste_tfidf | 0.5030 | FAIL |

**Citation-based signals recover citation heritage; text-based signals do not.**

### 3. v17b Label Normalization - Regime Change at Scale
- **1000-scale (v17b)**: 6 reps × 4 seeds, hierarchy purity ratio 1.15-1.24 (15-25% gain), uniform improvement
- **174k-scale**: 8 reps, 15k subsample, hierarchy purity ratio 4-10x but NMI decreases on normalized labels
- **Generalization**: FAIL — different label regime at 174k (213→111 vs 104→54 labels)

### 4. v18 Coarse Hierarchy - Fundamental Limitation
- **Branch level (4 labels)**: Best purity 0.65 (linear_citation_concat) < 0.7 threshold
- **All 6 representations FAIL** branch-level hierarchy coherence
- **Conclusion**: TF-IDF and citation-based representations lack sufficient signal density for legal structure recovery at any scale

### 5. Dense Embeddings BLOCKED
- **Legal-distance**: Only 3/26 years ACCEPTED (2000-2002, ~19k decisions, 11%)
- **15/26 years checkpointed** (2000-2014, ~100k) PENDING AUDIT
- **2019, 2025, 2026** not processed
- **Center_projected baselines FAIL jurist gate** at 174k (JP=0.39-0.42)
- **Metric learning/hybrids/citation roles at 174k PENDING** dense delivery

### 6. Boilerplate Resistance - Negative Across All Representations
- All 174k representations show negative resistance_score (~ -0.84)
- Confirms this proxy measures language dominance/cross-lingual alignment failure, not procedural boilerplate
- Consistent across TF-IDF and dense embeddings

---

## Evidence Artifacts (All Preserved)

| Artifact | Location | Status |
|---|---|---|
| 174k TF-IDF Formal Suite | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` | ✅ |
| 165k Dense Formal Suite | `/tmp/lex_accepted/legal-distance/evaluation/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json` | ✅ |
| Citation Heritage 174k TF-IDF | `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` | ✅ |
| Citation Pairs 174k | `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` | ✅ |
| v17b Label Normalization (1000-scale) | `results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json` | ✅ |
| v17b 174k TF-IDF | `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` | ✅ |
| v17b 174k Generalization | `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json` | ✅ |
| v18 Coarse Hierarchy | `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` | ✅ |
| Legal-distance State | `legal-distance/state/legal-distance.json` | ✅ |
| Corpus State | `corpus/state/corpus.json` | ✅ |

---

## Frozen Configuration (Audit Trail)

- **Evaluation Version**: v3_174k_fixed
- **Global Seed**: 42
- **Factory Direction**: v29
- **Adversarial Thresholds**: LangDom < 0.85, JuristPref > 0.5 (FROZEN)
- **HNSW Artifact Fix**: Exact k-NN on valid subset (n≈1200) for adversarial benchmarks
- **Config Hash**: 4323f833fa72366a (from formal suite run)

---

## Next Recommendation

**No further same-question cycles justified** for current dependency state.

The evaluation lane has completed all machine-executable work for the available representations (TF-IDF family). The lane is correctly **COMPLETED** with `continue_recommended: false`.

**Blocking dependencies** for next cycle:
1. Legal-distance delivery of ACCEPTED 174k dense embeddings (currently 3/26 years)
2. Jurist human study (framework ready, requires 5-10 Swiss jurists, no budget allocated)

**Factory Director should decide successor question** when dense embeddings become available.

---

## Verification

- All evidence artifacts verified present
- Negative results preserved (v17b generalization FAIL, v18 coarse hierarchy FAIL, boilerplate resistance FAIL)
- Frozen harness v3 thresholds unchanged
- Provenance maintained for all results
- State file: `state/evaluation.json` (direction_version: 29, cycle_status: COMPLETED)
