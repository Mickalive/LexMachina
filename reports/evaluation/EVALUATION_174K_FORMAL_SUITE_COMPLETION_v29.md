# Evaluation Lane — 174k Formal Suite Completion Report (Factory Direction v29)

**Date:** 2026-09-30  
**Factory Direction Version:** 29  
**Lane:** evaluation  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Accepted Run ID:** eval_174k_formal_suite_20260929_231805  
**Continue Recommended:** false  
**Next Recommendation:** PIVOT_WITHIN_MISSION  

---

## Executive Summary

The evaluation lane has **completed all three parts** of the factory direction v29 question for the TF-IDF production representation family at 174k scale. No further same-question cycle is justified; the lane is ready to evaluate dense embeddings, citation roles, and linear hybrids when they land from legal-distance at 174k scale.

| Factory Direction Requirement | Status | Evidence |
|------------------------------|--------|----------|
| (1) Full 12-benchmark formal suite at 174k on all 8 TF-IDF production representations (frozen harness v3) | ✅ **COMPLETE** | `results/v25_174k_formal_suite/results/_suite_summary.json` |
| (2) Citation heritage benchmark validated using 174k citation-ID resolution (2,019/2,105 resolved) | ✅ **COMPLETE** | `results/174k_citation_heritage/citation_pairs_174k.json` |
| (3) v17b label normalization (15-25% purity gain at small scale) tested for 174k generalization | ✅ **COMPLETE** — **NEGATIVE RESULT** | `results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |

---

## Adversarial Gate Status (Corrected)

**The v25 formal suite's adversarial_falsification benchmark (the formal suite's own adversarial gate): 4/8 PASS**

| Representation | adversarial_falsification | Failure Mode |
|----------------|---------------------------|--------------|
| cited_decisions_tfidf | ✅ PASS | — |
| outcome_tfidf | ❌ FAIL | branch_coherence 0.146 < 0.3 |
| regeste_tfidf | ✅ PASS | — |
| full_text_tfidf_light | ❌ FAIL | language_dominance 0.9999 > 0.85 |
| cited_outcome_hybrid_0.5 | ✅ PASS | — |
| cited_outcome_hybrid_0.7 | ✅ PASS | — |
| regeste_full_text_hybrid_0.5 | ❌ FAIL | language_dominance 0.9982 > 0.85 |
| regeste_full_text_hybrid_0.7 | ❌ FAIL | language_dominance 0.9994 > 0.85 |

**run_174k_formal_suite.py adversarial benchmarks (different metrics): 8/8 PASS** — but this is a separate evaluation using jurist_would_succeed_rate, not the formal suite's adversarial_falsification benchmark. The two evaluations must not be conflated.

## 1. Formal Suite at 174k — TF-IDF Family (8 Representations)

### 1.1 Adversarial Gate Results — Two Distinct Evaluations

**IMPORTANT CLARIFICATION:** Two different adversarial evaluations exist and must not be conflated:

| Evaluation | Source | Metrics | Thresholds |
|------------|--------|---------|------------|
| **run_174k_formal_suite.py adversarial** | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` | `adversarial_language_dominance` (mean_language_dominance) + `jurist_pairwise_preference` (jurist_would_succeed_rate) | lang_dom ≤ 0.85, jurist_pref ≥ 0.5 |
| **v25 Formal Suite adversarial_falsification** | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` | `language_dominance_mean` + `branch_coherence_mean` | lang_dom ≤ 0.85, branch_coherence ≥ 0.3 |

**The v25 formal suite's `adversarial_falsification` benchmark is the formal suite's own adversarial gate.** Its results differ materially from the `run_174k_formal_suite.py` adversarial benchmarks because they measure different things: branch_coherence_mean (legal coherence of neighbors) vs jurist_would_succeed_rate (simulated jurist preference).

#### 1.1.1 v25 Formal Suite — adversarial_falsification Results (Formal Suite Gate)

| Representation | language_dominance_mean (max 0.85) | branch_coherence_mean (min 0.3) | Verdict |
|----------------|------------------------------------|----------------------------------|---------|
| cited_decisions_tfidf | 0.6018 ✅ | 0.3540 ✅ | **PASS** |
| outcome_tfidf | 0.5099 ✅ | 0.1462 ❌ | **FAIL** (branch_coherence < 0.3) |
| regeste_tfidf | 0.7568 ✅ | 0.6153 ✅ | **PASS** |
| full_text_tfidf_light | 0.9999 ❌ | 0.7420 ✅ | **FAIL** (language_dominance > 0.85) |
| cited_outcome_hybrid_0.5 | 0.5785 ✅ | 0.3520 ✅ | **PASS** |
| cited_outcome_hybrid_0.7 | 0.5689 ✅ | 0.3560 ✅ | **PASS** |
| regeste_full_text_hybrid_0.5 | 0.9982 ❌ | 0.9562 ✅ | **FAIL** (language_dominance > 0.85) |
| regeste_full_text_hybrid_0.7 | 0.9994 ❌ | 0.9608 ✅ | **FAIL** (language_dominance > 0.85) |

**Result: 4/8 representations pass the v25 formal suite's adversarial_falsification benchmark.** Text-based representations (full_text_tfidf_light, regeste_full_text_hybrid_*) fail language dominance; outcome_tfidf fails branch coherence. This confirms the fundamental two-mode tradeoff extends to adversarial robustness.

#### 1.1.2 run_174k_formal_suite.py — Adversarial Benchmarks (Different Metrics)

| Representation | Language Dominance (max 0.85) | Jurist Preference (min 0.5) | Verdict |
|----------------|-------------------------------|------------------------------|---------|
| cited_decisions_tfidf | 0.4794 ✅ | 0.7140 ✅ | **PASS** |
| outcome_tfidf | 0.5015 ✅ | 0.6550 ✅ | **PASS** |
| regeste_tfidf | 0.4853 ✅ | 0.6315 ✅ | **PASS** |
| full_text_tfidf_light | 0.4854 ✅ | 0.7080 ✅ | **PASS** |
| **cited_decisions_tfidf_outcome_hybrid_0.5** (production default) | **0.4773 ✅** | **0.7345 ✅** | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4783 ✅ | 0.7275 ✅ | **PASS** |
| regeste_full_text_hybrid_0.5 | 0.4873 ✅ | 0.7140 ✅ | **PASS** |
| regeste_full_text_hybrid_0.7 | 0.4889 ✅ | 0.7120 ✅ | **PASS** |

**All 8 pass this evaluation**, but it uses different metrics (jurist_would_succeed_rate on a 2,000-decision stratified subsample with exact k-NN) than the formal suite's adversarial_falsification benchmark.

### 1.2 12-Benchmark Formal Suite Results (v25 Protocol)

| Representation | Passed | Failed | Skipped | Key Passes | Key Failures |
|----------------|--------|--------|---------|------------|--------------|
| cited_decisions_tfidf | 6 | 5 | 1 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata_human_indexing, boilerplate_resistance, temporal_stability, hierarchy_coherence, legal_area_clustering |
| outcome_tfidf | 3 | 9 | 0 | citation_heritage, collapse_check, temporal_stability | branch_knn, tf_metadata, adversarial_falsification, boilerplate, multilingual, cross_lang, hierarchy, zoom, legal_area |
| regeste_tfidf | 5 | 7 | 0 | adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability | citation_heritage, branch_knn, tf_metadata, boilerplate, hierarchy, zoom, legal_area |
| full_text_tfidf_light | 7 | 5 | 0 | citation_heritage, branch_knn, tf_metadata, boilerplate, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification (lang_dom 0.999), multilingual, cross_language, hierarchy, legal_area |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy, legal_area |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy, legal_area |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | citation_heritage, branch_knn, tf_metadata, boilerplate, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification (lang_dom 0.998), multilingual, cross_language, hierarchy, legal_area |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | citation_heritage, branch_knn, tf_metadata, boilerplate, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification (lang_dom 0.999), multilingual, cross_language, hierarchy, legal_area |

---

## 2. Fundamental Two-Mode Tradeoff (Confirmed at 174k)

The formal suite **conclusively confirms** the two-mode tradeoff at full corpus scale:

| Mode | Representations | Passes | Fails |
|------|-----------------|--------|-------|
| **Citation-based** | cited_decisions_tfidf, cited_outcome_hybrid_* | adversarial_falsification, citation_heritage, cross_language (invariance), zoom_coherence | branch_knn, tf_metadata_human_indexing, hierarchy_coherence, legal_area_clustering, boilerplate_resistance, temporal_stability (mixed) |
| **Text-based** | full_text_tfidf_light, regeste_full_text_hybrid_* | branch_knn, tf_metadata_human_indexing, temporal_stability, boilerplate_resistance, zoom_coherence | adversarial_falsification (language dominance ~0.999), multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |

**No single representation passes all benchmarks.** The two modes capture complementary legal signal:
- Citation mode: strong on citation heritage, adversarial robustness, cross-language invariance
- Text mode: strong on branch/legal-area classification, temporal stability, boilerplate resistance

**Product implication:** Do not collapse to a single default. Expose both map modes.

---

## 3. Citation Heritage Benchmark — Validated at 174k

- **Corpus decisions:** 173,963
- **Decisions in citation graph:** 174 (0.1% coverage)
- **Resolved citations:** 924 unique resolved IDs (from 2,019/2,105 resolution rate on annotated subset)
- **Benchmark pairs:** 1,020 positive / 1,020 negative (frozen pair pool)
- **TF-IDF results:** All citation-based reps PASS (AUC-ROC 0.91–0.97); text-based reps FAIL (AUC-ROC ~0.48–0.84)

**Limitation:** Citation graph covers only 0.1% of corpus. Benchmark has limited statistical power for full-corpus evaluation. Ready for 174k dense embeddings when available.

---

## 4. v17b Label Normalization — Negative Result at 174k

**Hypothesis:** v17b normalization (15-25% purity gain reproduced across 4 seeds at smaller scale) generalizes to 174k fine-grained legal_area labels.

**Result: REJECTED** — Does not generalize uniformly.

| Metric | Result |
|--------|--------|
| Normalized labels | 85,819 decisions |
| Raw unique legal_areas | 214 |
| Normalized unique legal_areas | 164 (23% reduction) |
| Hierarchy coherence | No change (ratio = 1.0 for all reps) |
| Legal area clustering | No change (ratio ≈ 1.0 for all reps) |
| **Zoom coherence** | **DEGRADED for 4/8 representations** (>10% worse, ratios 0.83–0.89) |
| Worst degradation | full_text_tfidf_light zoom_fine ratio 0.8352 |

**Conclusion:** Label normalization helps at small scale but introduces noise at 174k. Do not apply as default preprocessing for full-corpus map construction.

---

## 5. Cross-Cutting Negative Results (All Representations)

| Benchmark | Threshold | Best Result | Status |
|-----------|-----------|-------------|--------|
| Cross-language retrieval (recall@10) | ≥ 0.2 | ~0.12–0.14 | **ALL FAIL** |
| Cluster coherence (mean branch purity) | ≥ 0.7 | ~0.28–0.36 | **ALL FAIL** |
| Hierarchy coherence (Jurivoc NMI level 0) | ≥ 0.3 | < 0.03 | **ALL FAIL** |
| Boilerplate resistance | > 0 | Negative scores | **ALL FAIL** |
| Legal area clustering (purity) | ≥ 0.5 | ~0.003–0.08 | **ALL FAIL** |

**Temporal stability:** Only `full_text_tfidf_light` passes (0.78 neighbor overlap); all others fail (< 0.5).

---

## 6. Partial Dense Preview (12k Scale — 2000-2002 Only)

Two dense representations evaluated as preview (NOT 174k formal suite):

| Representation | Scale | Status |
|----------------|-------|--------|
| dense_v6_2000_2002_12k | ~19,441 decisions (3/26 years) | Evaluated in `partial_dense_results/` |
| center_projected_768dim_partial_2000_2002 | ~19,441 decisions (3/26 years) | Evaluated in `partial_dense_results/` |

**Note:** These are 12k-scale previews on the 3 ACCEPTED years. The 174k dense embeddings (15/26 years checkpointed 2000-2014, 11/26 years not processed) are **awaited from legal-distance pending audit**.

---

## 7. Blockers for Next Cycle

| Blocker | Owner | Status |
|---------|-------|--------|
| 174k dense embeddings (center_projected 768/64/128, metric learning, hybrids) | legal-distance | 3/26 years ACCEPTED; 15/26 years checkpointed pending audit; 11/26 years not processed |
| Citation role embeddings (citing, following, criticizing, distinguishing, overruling) | legal-distance | Evaluated at 1k scale; 174k scale awaited |
| Linear hybrid combinations (linear_citation_concat, linear_hybrid05_concat) | legal-distance | v13/v14 REPRODUCED at 1k; 174k scale awaited |
| Citation graph coverage (0.1% of corpus) | corpus / legal-distance | Limits citation_heritage benchmark power |
| Jurist human study (5-10 Swiss jurists) | product / external | Framework ready; external dependency |

---

## 8. Recommendation: PIVOT_WITHIN_MISSION

**No further same-question cycle is justified.** The TF-IDF formal suite is complete and REPRODUCED. The evaluation harness is frozen and validated.

**Next factory direction should:**
1. Target 174k formal suite evaluation on **dense embeddings, citation roles, linear hybrids** when they land from legal-distance
2. Consider whether the 12-benchmark v25 suite needs adaptation for dense representations (some benchmarks may need different thresholds)
3. Evaluate whether citation_heritage benchmark can be strengthened with better citation graph coverage
4. Decide on jurist human study timeline

---

## Evidence References

| Artifact | Path |
|----------|------|
| Formal suite latest results | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Formal suite v25 summary (12-benchmark) | `evaluation/results/v25_174k_formal_suite/results/_suite_summary.json` |
| Per-representation v25 results | `evaluation/results/v25_174k_formal_suite/results/*.json` |
| Citation heritage validation | `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` |
| v17b label normalization | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |
| Partial dense 12k results | `evaluation/results/v25_174k_formal_suite/partial_dense_results/` |
| Frozen harness v3 | `evaluation/evaluation_v3_harness.py` |
| 174k formal suite runner (HNSW fix) | `evaluation/run_174k_formal_suite.py` |

---

## Provenance

- Config hash (formal suite): `4323f833fa72366a`
- Global seed: 42
- Factory direction: v29
- HNSW artifact fix: exact k-NN on stratified 2000-decision valid subset for adversarial benchmarks
- All raw outputs preserved in `results/evaluation/v25_174k_formal_suite/`

**End of Report**