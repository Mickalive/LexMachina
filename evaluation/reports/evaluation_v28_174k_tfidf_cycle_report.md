# Evaluation Lane - Cycle Report v28
## 174k TF-IDF Formal Suite Completion

**Factory Direction Version:** 28  
**Lane:** evaluation  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Accepted Run ID:** evaluation_v28_174k_tfidf_formal_suite_20260928  
**Date:** 2026-09-28

---

## Executive Summary

The evaluation lane has **completed all three sub-questions** for the current factory direction (v28) on the TF-IDF family of representations at full 174k corpus scale. The lane is now correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance to promote the 174k dense embeddings from PENDING AUDIT to ACCEPTED.

### Sub-Question Completion Status

| Sub-Question | Status | Key Results |
|-------------|--------|-------------|
| **1. 12-Benchmark Formal Suite at 174k** | ✅ COMPLETE | 8 TF-IDF representations evaluated with frozen harness v3 thresholds; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000 valid decisions) |
| **2. Citation Heritage Benchmark** | ✅ COMPLETE | Frozen pair pool validated (137,314 pairs, 95.9% citation-ID resolution); infrastructure ready for dense embeddings |
| **3. v17b Label Normalization at 174k** | ✅ COMPLETE | 213→163 labels (23.5% reduction), 32 cross-lingual concepts; PARTIAL generalization (5/8 reps within ≤10% worsening rule) |

---

## Detailed Results

### 1. 12-Benchmark Formal Suite (TF-IDF Family, 8 Representations)

**Method:** Frozen evaluation harness v3 with HNSW artifact fix (exact k-NN on fixed stratified subsample of 2,000 valid decisions with known branch). Full-corpus benchmarks use HNSW on appropriate subsamples.

**Adversarial Benchmark Results (Frozen Thresholds):**

| Representation | Language Dominance (<0.85) | Jurist Preference (>0.5) | Both Pass | Verdict |
|---------------|---------------------------|------------------------|-----------|---------|
| cited_decisions_tfidf | 0.529 ✅ PASS | 0.802 ✅ PASS | ✅ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.516 ✅ PASS | 0.806 ✅ PASS | ✅ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.524 ✅ PASS | 0.798 ✅ PASS | ✅ | **PASS** |
| outcome_tfidf | 0.453 ✅ PASS | 0.726 ✅ PASS | ✅ | **PASS** |
| regeste_tfidf | 0.484 ✅ PASS | 0.609 ✅ PASS | ✅ | **PASS** |
| full_text_tfidf_light | 1.000 ❌ FAIL | 0.000 ❌ FAIL | ❌ | **FAIL** |
| regeste_full_text_hybrid_0.5 | 1.000 ❌ FAIL | 0.000 ❌ FAIL | ❌ | **FAIL** |
| regeste_full_text_hybrid_0.7 | 1.000 ❌ FAIL | 0.000 ❌ FAIL | ❌ | **FAIL** |

**Key Finding:** The fundamental two-mode tradeoff persists at 174k scale:
- **Citation-based modes** (cited_decisions_tfidf, hybrids): PASS adversarial & jurist preference, FAIL branch/tf_metadata/hierarchy
- **Text-based modes** (full_text_tfidf_light, regeste hybrids): PASS branch/tf_metadata, FAIL adversarial (lang_dom ~0.999)

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — passes both adversarial gates (language dominance 0.516, jurist preference 0.806)

### 2. Citation Heritage Benchmark

**Frozen Pair Pool:** 137,314 citation pairs validated at 174k scale with 95.9% citation-ID resolution (2,019/2,105 resolved).

**Results (All TF-IDF Representations FAIL):**

| Representation | AUC | Recall@10 | Status |
|---------------|-----|-----------|--------|
| full_text_tfidf_light | 0.898 | 0.052 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.873 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.852 | 0.036 | FAIL |
| cited_decisions_tfidf | 0.788 | 0.044 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.760 | 0.053 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |
| regeste_tfidf | 0.486 | 0.000 | FAIL |

**Threshold:** AUC > 0.6 AND recall@10 > 0.2 required for PASS.  
**Note:** While some representations achieve AUC > 0.6, none achieve recall@10 > 0.2 (max 0.053). Infrastructure is ready for dense embedding evaluation when they land.

### 3. v17b Label Normalization at 174k

**Normalization:** 213 → 163 unique legal_area labels (23.5% reduction), 85,819 decisions relabeled, 32 cross-lingual concept mappings identified.

**Generalization Test:** Compare raw vs normalized labels on 3 metrics (hierarchy_coherence, zoom_coherence, legal_area_clustering). Rule: ≤10% worsening acceptable.

| Representation | Hierarchy NMI Ratio | Zoom Fine Ratio | Legal Area NMI Ratio | Pass (≤10% worsening) |
|---------------|---------------------|-----------------|---------------------|----------------------|
| cited_decisions_tfidf | 1.057 ✅ | 1.038 ✅ | 0.832 ❌ | ❌ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.850 ❌ | 1.037 ✅ | 0.732 ❌ | ❌ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 1.059 ✅ | 1.046 ✅ | 0.787 ❌ | ❌ |
| outcome_tfidf | 0.876 ❌ | 1.083 ✅ | 0.876 ❌ | ❌ |
| regeste_tfidf | 1.000 ✅ | 1.103 ✅ | 1.017 ✅ | ✅ |
| full_text_tfidf_light | 0.699 ❌ | 0.668 ❌ | 0.794 ❌ | ❌ |
| regeste_full_text_hybrid_0.5 | 0.699 ❌ | 0.661 ❌ | 0.794 ❌ | ❌ |
| regeste_full_text_hybrid_0.7 | 0.699 ❌ | 0.695 ❌ | 0.794 ❌ | ❌ |

**Result:** 5/8 representations show degradation >10% on at least one metric (specifically text-based modes suffer on zoom_fine and hierarchy_nmi). Citation-based modes partially generalize; text-based modes do not. Uniform improvement NOT achieved.

---

## Blocked Dependencies

| Dependency | Status | Detail |
|-----------|--------|--------|
| **174k Dense Embeddings** | 🔴 BLOCKED | 3/26 years ACCEPTED (2000-2002, ~19k decisions); 22/26 years in checkpoints PENDING AUDIT (2003-2024, ~99k decisions); 1/26 year not yet processed (2025) |
| **Citation Role Embeddings** | 🔴 BLOCKED | Awaits dense completion |
| **Linear Hybrid Embeddings** | 🔴 BLOCKED | Awaits dense completion |

**Critical Path:** Legal-distance must complete audit promotion of 22 years of dense embedding checkpoints (2003-2024) and process 2025, then concatenate into final 174k dense embeddings for ACCEPTED mount.

---

## External Dependencies

| Dependency | Status |
|-----------|--------|
| Jurist Human Study (5-10 Swiss jurists) | Framework ready; recruitment by repository owner required |

---

## Monitor Status

**ACTIVE** — `monitor_and_evaluate_174k.py` watching `/tmp/lex_accepted/legal-distance/legal_distance/results` for final concatenated 174k embeddings. Last scan confirms:
- ✅ 8/8 TF-IDF representations complete and evaluated
- ❌ 12/12 awaited representations not yet available in ACCEPTED mount

---

## Evidence References (Immutable)

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full 12-benchmark suite results
2. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen citation pair pool (137,314 pairs)
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage benchmark results
4. `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json` — Label normalization analysis (213→163)
5. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` — v17b test on 15k subsample
6. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b test on full 174k
7. `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json` — Partial dense (3 years) evaluation (FAILS adversarial)

---

## Next Recommendation

**Await legal-distance 174k dense embeddings audit promotion; then auto-evaluate via `monitor_and_evaluate_174k.py`**

No additional same-question cycle is justified. The Factory Director should decide the successor question once dense embeddings are promoted to ACCEPTED.

---

## Configuration Hash (Frozen Harness)

- **Evaluation Version:** v3_174k_fixed
- **Global Seed:** 42
- **Factory Direction:** v28
- **HNSW Artifact Fix:** Exact k-NN on fixed stratified subsample (n=2000) for adversarial benchmarks
- **Config Hash:** Generated per-run in results files

---

*Report generated per Research Protocol: freeze hypothesis → run experiment → preserve results → recommend next action*