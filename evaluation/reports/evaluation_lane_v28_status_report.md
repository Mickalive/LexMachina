# Evaluation Lane v28 Status Report

**Date**: 2026-09-28  
**Factory Direction Version**: 28  
**Lane**: evaluation  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false

---

## Executive Summary

The evaluation lane has **completed all machine-executable formal suite evaluations for the TF-IDF family at 174k scale**. The lane is now **blocked on legal-distance 174k dense embeddings audit promotion**. No further evaluation cycles are justified on the current question until the blocked dependencies are resolved.

### Key Accomplishments (All REPRODUCED)

| Sub-Question | Status | Details |
|--------------|--------|---------|
| **1. 12-benchmark formal suite at 174k** | ✅ COMPLETE | 8 TF-IDF representations evaluated with frozen harness v3 thresholds; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000 valid decisions) |
| **2. Citation heritage benchmark** | ✅ COMPLETE | Frozen pair pool validated (137,314 pairs, 95.9% citation resolution); infrastructure ready for dense embeddings; TF-IDF citation-based AUC 0.76-0.79 but recall@10 < 0.2 (FAIL); text-based AUC ~0.49 (FAIL) |
| **3. v17b label normalization** | ✅ COMPLETE | 213→163 labels (23.5% reduction), 32 cross-lingual concepts; PARTIAL generalization (5/8 reps within ≤10% worsening rule on zoom_fine; text-based reps degrade 30-34%) |
| **4. Partial dense evaluation** | ✅ COMPLETE | 3 center_projected variants (768/64/128dim) on 12,570 decisions (years 2000-2002): ALL FAIL adversarial (lang_dom ~0.98, jurist_pref ~0.04). Root cause: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering. NOT comparable to 1,200-slice center_projected (which PASS adversarial). |

---

## TF-IDF Family Results at 174k (8 Representations)

### Adversarial Gates (Frozen Harness v3)

| Representation | Language Dominance (✓<0.85) | Jurist Preference (✓>0.5) | Both Pass | Verdict |
|----------------|----------------------------|---------------------------|-----------|---------|
| cited_decisions_tfidf | 0.529 (PASS) | 0.802 (PASS) | ✅ | PASS |
| outcome_tfidf | 0.453 (PASS) | 0.726 (PASS) | ✅ | PASS |
| regeste_tfidf | 0.484 (PASS) | 0.609 (PASS) | ✅ | PASS |
| full_text_tfidf_light | 1.000 (FAIL) | 0.000 (FAIL) | ❌ | FAIL |
| cited_outcome_hybrid_0.5 | 0.516 (PASS) | 0.806 (PASS) | ✅ | **PRODUCTION DEFAULT** |
| cited_outcome_hybrid_0.7 | 0.524 (PASS) | 0.798 (PASS) | ✅ | PASS |
| regeste_full_text_hybrid_0.5 | 0.999 (FAIL) | 0.000 (FAIL) | ❌ | FAIL |
| regeste_full_text_hybrid_0.7 | 0.999 (FAIL) | 0.000 (FAIL) | ❌ | FAIL |

### Fundamental Tradeoff (REPRODUCED at 174k)

**Citation-based representations** (cited_decisions_tfidf, outcome_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7):
- ✅ PASS adversarial gates (language_dom ~0.5, jurist_pref ~0.8)
- ❌ FAIL branch/hierarchy/legal_area clustering (purity ~0.25-0.40, NMI ~0.05-0.10)
- ❌ FAIL boilerplate resistance (resistance_score ~ -0.78)
- ❌ FAIL citation_heritage (recall@10 ~0.05)

**Text-based representations** (full_text_tfidf_light, regeste_tfidf, regeste_full_text_hybrid_0.5/0.7):
- ✅ PASS branch/legal_area clustering (purity ~0.50-0.75, NMI ~0.40-0.60)
- ❌ FAIL adversarial gates (language_dom = 1.0, jurist_pref = 0.0)
- ✅ PASS citation_heritage AUC (~0.85-0.90) but FAIL recall@10 (~0.05-0.10)

**No TF-IDF representation achieves both legal coherence AND language invariance at 174k scale.**

---

## Citation Heritage Benchmark (174k)

- **Pair pool**: 137,314 pairs (95.9% citation resolution: 2,019/2,105 IDs resolved)
- **Threshold**: AUC > 0.6 AND recall@10 > 0.2
- **Result**: **NEGATIVE for all TF-IDF representations**
  - Best AUC: full_text_tfidf_light (0.898) but recall@10 = 0.052
  - Best recall@10: full_text_tfidf_light (0.052) but citation-based reps only ~0.04-0.05
- **Interpretation**: Citation structure is NOT preserved in nearest neighbors at 174k for any TF-IDF representation

---

## v17b Label Normalization (174k)

- **Normalization**: 213 → 163 unique legal_area labels (23.5% reduction), 32 cross-lingual concepts
- **Citation-based reps**: 5-7% purity GAIN on hierarchy/legal_area/zoom_fine
- **Text-based reps**: 30-34% zoom_fine purity LOSS (degradation >10% rule violated)
- **Partial generalization**: 5/8 representations within ≤10% worsening on zoom_fine

---

## Partial Dense Evaluation (12,570 decisions, years 2000-2002)

| Variant | Language Dominance | Jurist Preference | Adversarial |
|---------|-------------------|-------------------|-------------|
| center_projected_768dim | 0.981 | 0.040 | ❌ FAIL |
| center_projected_64dim | 0.978 | 0.045 | ❌ FAIL |
| center_projected_128dim | 0.980 | 0.041 | ❌ FAIL |

**Root cause confirmed**: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering. **NOT comparable** to 1,200-slice center_projected (which PASS adversarial). Scale/metadata coverage is critical for dense embeddings.

---

## Blocked Dependencies

| Dependency | Status | Detail |
|------------|--------|--------|
| **legal-distance: 174k dense embeddings** | ❌ BLOCKED | 3/26 years ACCEPTED (2000-2002, ~19,441 decisions); 22/26 years (2003-2024, ~154k decisions) in checkpoints PENDING AUDIT; 2/26 years (2025-2026) not yet processed |
| **legal-distance: citation role embeddings** | ⏳ AWAITS | Requires dense completion first |
| **legal-distance: linear hybrid embeddings** | ⏳ AWAITS | Requires dense completion first |

**Critical path**: legal-distance must complete audit promotion of 25 years (2000-2024) of dense embeddings checkpoints. Only then will final concatenated 174k embeddings appear in the accepted state mount for auto-evaluation.

---

## External Dependencies

- **Jurist human study**: Framework ready, requires 5-10 Swiss jurists (recruitment by repository owner required)

---

## Monitor Status

- **Script**: `monitor_and_evaluate_174k.py` (ACTIVE)
- **Check count**: 205
- **Last check**: 2026-09-28T20:35:01
- **Detection**: No new awaited representations found in accepted state mount
- **Infrastructure**: HNSW backend operational, scalable_nn with sklearn fallback, v25 formal suite operational, citation heritage frozen pair pool ready, v17b normalization operational

---

## Key Findings (Accepted Tier)

1. **Fundamental tradeoff persists at 174k**: No single TF-IDF representation wins on both legal coherence and language invariance
2. **Citation heritage NEGATIVE**: No TF-IDF representation preserves citation structure in nearest neighbors at 174k (AUC>0.6 but recall@10<0.2)
3. **v17b normalization asymmetric**: Helps citation-based reps, harms text-based reps on zoom_fine
4. **HNSW artifact confirmed & fixed**: Fixed HNSW params produce nearly identical k-NN graphs across TF-IDF reps; exact k-NN on valid subset used for adversarial benchmarks
5. **Scale dependency for dense**: 12k partial dense FAILS adversarial; 1,200-slice center_projected PASSES. Metadata coverage and corpus completeness critical.

---

## Production Default Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| **Representation** | cited_decisions_tfidf_outcome_hybrid_0.5 | — | DEFAULT |
| Language dominance | 0.5164 | < 0.85 | ✅ PASS |
| Jurist preference | 0.8055 | > 0.5 | ✅ PASS |
| Citation heritage AUC | 0.7597 | > 0.6 | ✅ PASS |
| Citation heritage recall@10 | 0.0529 | > 0.2 | ❌ FAIL |
| v17b zoom_fine ratio | 1.0366 | ≤ 1.10 | ✅ PASS |

---

## Next Recommendation

**Await legal-distance 174k dense embeddings audit promotion**. The monitor script (`monitor_and_evaluate_174k.py`) will automatically detect final concatenated embeddings in the accepted state mount and execute the full evaluation suite (12-benchmark formal suite + citation_heritage + v17b normalization).

**No further evaluation cycle recommended on current question** (`continue_recommended: false`). The Factory Director should advance to the successor question once dense embeddings are promoted.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` - Full 12-benchmark suite results
2. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` - Frozen citation pair pool
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` - Citation heritage benchmark results
4. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` - v17b label normalization results
5. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` - v17b clustering on normalized labels
6. `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json` - Partial dense evaluation
7. `evaluation/state/monitor_174k_state.json` - Monitor state (check_count=205)

---

## Acceptance Status

All completed evaluations are at **REPRODUCED** evidence tier with:
- Frozen harness v3 thresholds unchanged
- Exact k-NN on stratified subsample (HNSW artifact fix)
- Multiple independent verification runs
- Negative results preserved as first-class evidence
- No benchmark weakening after seeing results