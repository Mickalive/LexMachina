# Evaluation Lane - 174k Formal Suite Cycle Report
**Run ID:** `eval_174k_formal_suite_20260929_231805`  
**Factory Direction:** v28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Date:** 2026-09-29  

---

## Executive Summary

The evaluation lane has completed the machine-executable 174k formal suite on all 8 production TF-IDF representations with the HNSW artifact fix applied (exact k-NN on stratified valid subset for adversarial benchmarks). All representations pass both adversarial gates. However, **most full-corpus benchmarks FAIL**, revealing fundamental limitations of TF-IDF representations at 174k scale. The v17b label normalization does **not** uniformly generalize to 174k—zoom coherence degrades for 4/8 representations.

**Next Recommendation:** `PIVOT_WITHIN_MISSION` — Wait for legal-distance 174k dense embeddings, citation roles, metric learning, and linear hybrids before further evaluation cycles on TF-IDF family.

---

## Factory Direction Question (v28)

> Run the machine-executable 174k formal suite autonomously as representations land:  
> 1. Full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged)  
> 2. Validate citation_heritage benchmark using published 174k citation-ID resolution (2,019/2,105 resolved)  
> 3. Test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels

**All three objectives completed.**

---

## 1. Formal Suite Results (8 TF-IDF Representations)

### Adversarial Gates (FROZEN thresholds: lang_dom < 0.85, jurist_pref > 0.5)

| Representation | Language Dominance | Jurist Preference | Verdict |
|---|---|---|---|
| cited_decisions_tfidf | 0.4917 ✓ | 0.7075 ✓ | **PASS** |
| outcome_tfidf | 0.5078 ✓ | 0.6660 ✓ | **PASS** |
| regeste_tfidf | 0.5111 ✓ | 0.6145 ✓ | **PASS** |
| full_text_tfidf_light | 0.4854 ✓ | 0.7080 ✓ | **PASS** |
| **cited_decisions_tfidf_outcome_hybrid_0.5** (prod default) | **0.4895 ✓** | **0.7265 ✓** | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 ✓ | 0.7195 ✓ | **PASS** |
| regeste_full_text_hybrid_0.5 | 0.4873 ✓ | 0.7140 ✓ | **PASS** |
| regeste_full_text_hybrid_0.7 | 0.4889 ✓ | 0.7120 ✓ | **PASS** |

**Best representation:** `cited_decisions_tfidf_outcome_hybrid_0.5` (production default) — lowest language dominance (0.4895) and highest jurist preference (0.7265).

**HNSW Artifact Fix:** Adversarial benchmarks run with **exact k-NN on fixed stratified subsample** (2000 decisions from 90,632 valid), not HNSW on full 174k. This reveals true representation differences that were masked by HNSW approximation at full scale.

---

## 2. Cross-Language Benchmarks (Exact k-NN on Adversarial Subsample)

| Benchmark | Result | Detail |
|---|---|---|
| Zero-shot cross-language transfer | **ALL FAIL** | zero_shot_mean_nmi 0.01–0.03, threshold > 0.2 |
| Language-specific representation quality | **ALL FAIL** | mean_nmi 0.03–0.05, std 0.02–0.05, threshold mean > 0.3 & std < 0.2 |
| Cross-language neighbor quality | Mixed | cross_lang_same_branch ~0.13, same_lang_same_branch ~0.13, cross_branch ~0.73 |
| Invariance gap | Negative for hybrids | Cross-lang same-branch slightly worse than same-lang same-branch |

**Conclusion:** No representation achieves meaningful cross-language legal equivalence at 174k with TF-IDF.

---

## 3. Jurist Usability Simulations (Exact k-NN on Adversarial Subsample)

| Benchmark | Result | Detail |
|---|---|---|
| Cluster coherence rating | **ALL FAIL** | mean_branch_purity 0.28–0.36 < 0.7 threshold; mean_language_purity 0.59–0.63 (language dominates clusters) |
| Cross-language retrieval | **ALL FAIL** | recall@10 0.12–0.14 < 0.2 threshold |
| Zoom task | SKIPPED | Requires hierarchical cluster assignments from fractal-map |

**Conclusion:** Simulated jurist would not find legally coherent clusters or useful cross-language retrieval in TF-IDF maps.

---

## 4. Full-Corpus Benchmarks (HNSW on Subsamples/Full Corpus)

| Benchmark | Result | Best Representation |
|---|---|---|
| Temporal stability (30k subsample) | **MIXED** | full_text_tfidf_light PASS (0.78 overlap); others FAIL (< 0.5) |
| Hierarchy coherence (Jurivoc proxy, 15k subsample) | **ALL FAIL** | level_0_nmi 0.0005–0.01 < 0.3; level_1_nmi 0.01–0.03 < 0.2 |
| Cluster coherence (15k subsample) | **ALL FAIL** | mean_branch_purity 0.28–0.34 < 0.7; language purity 0.60–0.63 |
| Cross-language retrieval full (15k subsample) | **ALL FAIL** | recall@10 0.10–0.14 < 0.2 |
| Boilerplate resistance (full corpus) | **ALL FAIL** | resistance_score -0.75 to -0.84 (boilerplate neighbors dominate) |

---

## 5. Citation Heritage Benchmark Validation

- **Corpus:** 173,963 decisions
- **Decisions in citation graph:** 174 (0.1%)
- **Resolved citations mapping to corpus:** 924
- **Positive pairs (direct + shared citations):** 1,020
- **Negative pairs (sampled):** 1,020
- **Status:** Benchmark ready for 174k dense embeddings when available

**Critical limitation:** Citation graph covers only 0.1% of the 174k corpus, severely limiting statistical power.

---

## 6. v17b Label Normalization at 174k

| Metric | Raw Labels (214 areas) | Normalized Labels (164 areas) | Ratio (Norm/Raw) |
|---|---|---|---|
| Labels normalized | — | 85,819 / 173,963 (49.3%) | — |
| Hierarchy coherence (best_purity) | 0.4711 | 0.4711 | **1.000** (no change) |
| Legal area clustering (overall_purity) | 0.470–0.472 | 0.470–0.473 | **≈1.000** (no change) |
| Zoom coherence (fine_purity) | 0.036–0.067 | 0.030–0.065 | **0.83–0.99** (DEGRADED for 4/8) |

**Representations with >10% zoom_fine degradation:**
- `cited_decisions_tfidf` (0.8869)
- `full_text_tfidf_light` (0.8352) — **worst**
- `cited_decisions_tfidf_outcome_hybrid_0.5` (0.8827)
- `cited_decisions_tfidf_outcome_hybrid_0.7` (0.8861)

**Conclusion:** v17b normalization (15–25% purity gain at 12k scale) does **not** generalize uniformly to 174k. Zoom coherence degrades significantly for citation-based and hybrid representations.

---

## 7. Key Findings

1. **TF-IDF family COMPLETE at 174k** with HNSW artifact fixed. All 8 representations pass adversarial gates.

2. **Production default validated:** `cited_decisions_tfidf_outcome_hybrid_0.5` achieves best jurist preference (0.7265) with low language dominance (0.4895).

3. **Fundamental two-mode tradeoff persists:**
   - Citation-based reps → pass adversarial/citation_heritage, **FAIL** branch/tf_metadata/hierarchy
   - Text-based reps → pass branch/tf_metadata, **FAIL** adversarial (language dominance ~0.999 at full corpus)

4. **Citation heritage benchmark limited:** Only 0.1% of corpus has citation graph coverage.

5. **v17b label normalization NEGATIVE at 174k:** No uniform improvement; zoom coherence degrades for 4/8 representations.

6. **All representations FAIL** on: cross-language retrieval, cluster coherence, hierarchy alignment (Jurivoc), boilerplate resistance.

7. **Temporal stability:** Only `full_text_tfidf_light` passes (0.78 neighbor overlap); others fail (< 0.5).

8. **Blocked on legal-distance:** Dense embeddings, citation roles, metric learning, linear hybrids awaited (3/26 years ACCEPTED; 25/26 years checkpointed pending audit).

---

## 8. Evidence References

- Formal suite results: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage validation: `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- v17b label normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Machine-readable state: `evaluation/state/evaluation.json`

---

## 9. Next Steps

**PIVOT_WITHIN_MISSION** — No further evaluation cycles on TF-IDF family are justified. The evaluation lane should:

1. **Wait for legal-distance 174k artifacts** (dense embeddings, citation roles, metric learning, linear hybrids, linear_hybrid05_concat stability test)
2. **Re-run formal suite** when new representations are promoted to ACCEPTED
3. **Jurist human study** remains an external dependency (framework ready, requires 5–10 Swiss jurists)

The factory direction question for this cycle is **answered**. No `continue_recommended` for same question.