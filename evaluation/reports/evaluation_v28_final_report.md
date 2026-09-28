# Evaluation Lane — Factory Direction v28 Final Report

**Date:** 2026-09-28  
**Lane:** evaluation  
**Direction Version:** 28  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane has **completed all required work** for factory direction v28. The 174k formal benchmark suite has been executed on all production representations that have landed at full corpus scale:

| Representation Family | Representations Evaluated | Scale | Adversarial Gates |
|----------------------|--------------------------|-------|-------------------|
| TF-IDF (8 reps) | cited_decisions, outcome, regeste, full_text, 4 hybrids | 173,963 | 5 PASS / 3 FAIL |
| Dense (3 years) | center_projected 768/128/64 | 12,570 | 0 PASS / 3 FAIL |

**Key Finding:** The fundamental two-mode tradeoff persists at 174k scale — citation-based representations pass both adversarial gates while text-based representations fail catastrophically due to language dominance (~1.0).

---

## 1. Formal Suite Results (12 Benchmarks, Frozen Harness v3)

### Adversarial Benchmarks (Gatekeepers)

| Representation | Language Dominance (thresh < 0.85) | Jurist Preference (thresh > 0.5) | Both Gates | Verdict |
|----------------|-----------------------------------|----------------------------------|------------|---------|
| cited_decisions_tfidf | 0.5295 ✓ PASS | 0.8020 ✓ PASS | ✓ | **PASS** |
| outcome_tfidf | 0.4527 ✓ PASS | 0.7255 ✓ PASS | ✓ | **PASS** |
| regeste_tfidf | 0.4835 ✓ PASS | 0.6090 ✓ PASS | ✓ | **PASS** |
| **full_text_tfidf_light** | **1.0000 ✗ FAIL** | **0.0000 ✗ FAIL** | ✗ | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.5164 ✓ PASS | 0.8055 ✓ PASS | ✓ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.5238 ✓ PASS | 0.7975 ✓ PASS | ✓ | **PASS** |
| **regeste_full_text_hybrid_0.5** | **1.0000 ✗ FAIL** | **0.0000 ✗ FAIL** | ✗ | **FAIL** |
| **regeste_full_text_hybrid_0.7** | **1.0000 ✗ FAIL** | **0.0000 ✗ FAIL** | ✗ | **FAIL** |

**Production Default Validated:** `cited_decisions_tfidf_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT) passes both gates with strong jurist preference (0.8055) and moderate language dominance (0.5164).

### Supporting Benchmarks (10 additional)

| Benchmark | Citation-based Reps | Text-based Reps |
|-----------|---------------------|-----------------|
| Cross-language neighbor quality | PASS (cross_lang_same_branch > same_lang_same_branch) | FAIL (language dominates) |
| Zero-shot cross-language transfer | FAIL (low NMI) | PASS (but language-driven) |
| Language-specific representation quality | FAIL (low branch NMI) | PASS (high within-lang NMI) |
| Cluster coherence rating | FAIL (branch purity ~0.4) | PASS (purity ~0.74 but lang=1.0) |
| Cross-language retrieval | PASS (recall@10 ~0.23) | FAIL (recall@10 = 0.0) |
| Temporal stability (30k subsample) | FAIL (overlap ~0.38) | PASS (overlap ~0.78) |
| Hierarchy coherence (15k subsample) | FAIL (L0 NMI ~0.0) | FAIL (L1 NMI high but lang-driven) |
| Cluster coherence (15k subsample) | FAIL (branch purity ~0.37) | PASS (purity ~0.74, lang ~1.0) |
| Cross-language retrieval full (15k) | PASS (recall@10 ~0.23) | FAIL (recall@10 ~0.0) |
| Boilerplate resistance (full corpus) | FAIL (resistance ~ -0.77) | FAIL (resistance ~ -0.56) |

**Pattern:** Citation-based representations excel at legal relevance (jurist preference, cross-lang retrieval) but struggle with structural coherence. Text-based representations achieve high cluster coherence and temporal stability but purely through language artifacts.

---

## 2. Citation Heritage Validation

**Status:** COMPLETE — Validated on all 8 TF-IDF representations using 174k citation-ID resolution (2,019/2,105 resolved)

**Constraint:** Only 174 decisions (0.1%) have outgoing citations in the 174k corpus, severely limiting statistical power.

| Representation | AUC | Recall@10 | Status |
|----------------|-----|-----------|--------|
| cited_decisions_tfidf | 0.788 | 0.044 | FAIL (recall < 0.2) |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.760 | 0.053 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| full_text_tfidf_light | 0.898 | 0.052 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.873 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.852 | 0.036 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |
| regeste_tfidf | 0.486 | 0.000 | FAIL |

**Interpretation:** Citation-based representations show meaningful citation structure preservation (AUC > 0.6) but recall@10 remains below the 0.2 threshold due to extreme sparsity. The "best" AUC belongs to full_text_tfidf_light but this is a language artifact.

---

## 3. v17b Label Normalization at 174k Scale

**Status:** COMPLETE — Tested on all 8 TF-IDF representations with 85,819 labels normalized (214 raw → 164 normalized unique areas, 49.3% labels changed)

### Divergent Effects by Signal Type

| Representation | Hierarchy Purity Δ | Zoom Fine Δ | Legal Area Purity Δ | Net Effect |
|----------------|-------------------|-------------|---------------------|------------|
| cited_decisions_tfidf | **+5.7%** | **+3.8%** | **+6.2%** | **IMPROVED** |
| outcome_tfidf | +4.6% | +8.3% | +4.4% | **IMPROVED** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | +5.6% | +3.7% | +6.3% | **IMPROVED** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | +5.3% | +4.6% | +5.8% | **IMPROVED** |
| regeste_tfidf | 0% | +10.3% | +1.7% | MIXED |
| **full_text_tfidf_light** | 0% | **-33.2%** | -2.7% | **DEGRADED** |
| **regeste_full_text_hybrid_0.5** | 0% | **-33.9%** | -3.1% | **DEGRADED** |
| **regeste_full_text_hybrid_0.7** | +0.01% | **-30.5%** | -3.7% | **DEGRADED** |

**Critical Finding:** v17b normalization **helps structured signals** (citation/outcome-based) but **destroys cross-lingual alignment** in text-based signals. This confirms the signal-type dependency observed at smaller scales.

---

## 4. Dense Embeddings Evaluation (3 Years: 2000-2002)

**Status:** COMPLETE — All 3 representations FAIL both adversarial gates

| Representation | Language Dominance | Jurist Preference | Verdict |
|----------------|-------------------|-------------------|---------|
| center_projected_768 | 0.9972 | 0.0078 | FAIL |
| center_projected_64 | 0.9782 | 0.0448 | FAIL |
| center_projected_128 | 0.9804 | 0.0409 | FAIL |

**Interpretation:** Even with center-projected language debiasing, multilingual-e5 embeddings overcluster by language at 12.5k scale. The debiasing is insufficient — hierarchy-preserving contrastive losses are needed (confirms earlier findings).

---

## 5. Infrastructure Verification

### Frozen Harness v3 Reproducibility
✅ **PASSED** — All 6 baseline representations (center_projected, linear_metric, mahalanobis, hybrids) reproduce within 0.001 tolerance vs. accepted baseline (GitHub run 33283750508).

### Embedding Artifact Integrity
✅ **PASSED** — All 8 TF-IDF embeddings at 174k:
- Shape: (173963, 128), float32, finite
- Hybrid determinism: bitwise exact reconstruction from bases
- Zero-row patterns: consistent with frozen v16 semantics
- Fixed subsamples: deterministic at seed 42

---

## 6. Blocked Dependencies

The evaluation lane cannot proceed further on the current question without deliveries from **legal-distance**:

| Dependency | Status | Impact |
|------------|--------|--------|
| 174k dense embeddings | 3/26 years ACCEPTED (2000-2002) | Cannot evaluate full-corpus dense |
| Citation role embeddings | NOT YET at 174k | Cannot test citation-role modes |
| Linear hybrid embeddings | NOT YET at 174k | Cannot test linear_hybrid05_concat at scale |
| Section-specific cross-lingual | Requires 174k dense | Blocked |

---

## 7. Recommendations

### For Factory Director
1. **No further same-question cycles** — The current question is exhausted. Set `continue_recommended = false`.
2. **Critical path:** legal-distance 174k dense embeddings audit promotion (currently 20/26 years pending audit, only 3/26 ACCEPTED).
3. **Next evaluation question** should trigger when legal-distance delivers ≥10 years of dense embeddings at 174k.

### For Product
- **Production default confirmed:** `cited_decisions_tfidf_outcome_hybrid_0.5` remains the best available representation.
- Zero-shot TF-IDF hybrid requires no GPU and scales to full corpus.

### For Legal-Distance
- Priority: Complete dense embedding computation for remaining 23 years.
- Investigate hierarchy-preserving losses to fix language overclustering in dense embeddings.

---

## 8. Evidence References

| Artifact | Path | Description |
|----------|------|-------------|
| Formal suite latest | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` | 8 reps × 12 benchmarks |
| Citation heritage | `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` | 8 reps validated |
| v17b normalization | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` | 8 reps × 3 benchmarks |
| Dense 3yr eval | `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json` | 3 dense reps |
| Reproducibility test | `tests/evaluation/test_frozen_harness_v3_reproducibility.py` | PASSED |

---

## 9. Conclusion

**The evaluation lane has delivered its v28 commitment in full.** All three mandated tasks completed with ACCEPTED evidence tier. The two-mode tradeoff is confirmed at production scale. Dense embeddings remain the critical blocker — no further evaluation cycles are justified until legal-distance delivers.

**Next recommendation:** `BLOCKED_ON_DEPENDENCIES` — Await legal-distance 174k dense embeddings delivery.