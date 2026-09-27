# Evaluation Lane Cycle Report — Factory Direction v29

**Date:** 2026-09-27  
**Direction Version:** 29  
**Lane:** evaluation  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Evidence Tier:** REPRODUCED

---

## Executive Summary

The evaluation lane has completed all three machine-executable sub-questions from factory direction v29 for the TF-IDF family at 174k scale. The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance lane to produce full 174k dense embeddings, citation roles, and linear hybrids.

### Completed Work (TF-IDF Family at 174k)

| Sub-question | Status | Key Result |
|--------------|--------|------------|
| **(1) 12-benchmark formal suite** | COMPLETE | 8 representations evaluated with HNSW artifact fix (exact k-NN on stratified n=2000). 5 PASS both adversarial gates, 3 FAIL |
| **(2) Citation heritage benchmark** | COMPLETE | Frozen 137,314-pair pool, 95.9% citation resolution. All 8 TF-IDF reps FAIL recall@10 > 0.2 |
| **(3) v17b label normalization** | COMPLETE | 213→163 labels, 32 cross-lingual concepts. PARTIAL generalization (2/8 reps within ≤10% worsening rule) |

### Additional Evaluations Completed

| Evaluation | Corpus | Status | Key Finding |
|------------|--------|--------|-------------|
| Raw multilingual-e5 768dim | 2000-2015 (~99k) | COMPLETE | FAILS adversarial (lang_dom=0.9855), PASSES cross-language transfer (NMI=0.29) and per-language quality (NMI=0.44) — legal structure captured WITHIN language only |
| Partial dense (center_projected) | 2000-2002 (12,570) | COMPLETE | FAILS adversarial (lang_dom~0.98) — metadata coverage only 18.3%, incomplete center-projection on partial corpus |

---

## Formal Suite Results (TF-IDF at 174k)

**Config Hash:** `b51701f5a9c11692` (frozen v3 thresholds)  
**HNSW Artifact Fix:** Exact k-NN on fixed stratified subsample (n=2000, seed=42)

| Representation | Verdict | Lang Dominance | Jurist Pref | Both Adv Pass |
|----------------|---------|----------------|-------------|---------------|
| cited_decisions_tfidf | PASS | 0.5295 | 0.8020 | ✓ |
| outcome_tfidf | PASS | 0.4527 | 0.7255 | ✓ |
| regeste_tfidf | PASS | 0.4835 | 0.6090 | ✓ |
| cited_outcome_hybrid_0.5 | PASS | 0.5164 | 0.8055 | ✓ |
| cited_outcome_hybrid_0.7 | PASS | 0.5238 | 0.7975 | ✓ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ✗ |

**Best adversarial:** `cited_decisions_tfidf` (lang_dom=0.5295, jurist_pref=0.8020)  
**Production default:** `cited_outcome_hybrid_0.7` (per product lane)

**Universal 174k failures (corpus/label limitations):** hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance

---

## Citation Heritage Results (TF-IDF at 174k)

**Pair Pool:** 137,314 positive + 137,314 negative (frozen, seed=42)  
**Citation Resolution:** 2,019/2,105 (95.9%) resolved; 924 mapping to 174k corpus decisions

| Representation | AUC-ROC | Recall@10 | Status |
|----------------|---------|-----------|--------|
| cited_decisions_tfidf | 0.7892 | 0.0480 | FAIL |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.0490 | FAIL |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.0500 | FAIL |
| full_text_tfidf_light | 0.8969 | 0.0529 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | FAIL |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |

**Thresholds:** AUC ≥ 0.65, Recall@10 ≥ 0.2  
**Note:** All FAIL recall@10 despite some passing AUC. nn_citation_rate@10 ~3-5% for all reps.

---

## v17b Label Normalization at 174k

**Label Reduction:** 213 → 163 unique labels (23.5% reduction)  
**Decisions with legal_area:** 91,193  
**Cross-lingual concepts merged:** 32

| Representation | Hierarchy Purity Ratio | Hierarchy NMI Ratio | Within 10% Worsening |
|----------------|------------------------|---------------------|----------------------|
| cited_decisions_tfidf | 1.48 | 0.95 | ✓ |
| regeste_tfidf | 1.67 | null | ✓ |
| cited_outcome_hybrid_0.5 | 1.43 | 0.85 | ✗ (NMI -15%) |
| cited_outcome_hybrid_0.7 | 1.44 | 1.06 | ✓ |
| outcome_tfidf | 1.50 | 0.88 | ✗ (NMI -12%) |
| full_text_tfidf_light | 1.00 | 0.70 | ✗ (NMI -30%) |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.70 | ✗ (NMI -30%) |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.70 | ✗ (NMI -30%) |

**Key Finding:** v17b improves purity for citation-based reps (42-67%) but degrades NMI for 6/8 reps (11-30% worsening). Best normalized hierarchy_purity=0.47 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## Raw Multilingual-e5 768dim (2000-2015, ~99k decisions)

| Benchmark | Result | Score |
|-----------|--------|-------|
| Adversarial Language Dominance | FAIL | 0.9855 |
| Jurist Pairwise Preference | FAIL | 0.0275 |
| Zero-shot Cross-language Transfer | PASS | NMI=0.293 |
| Language-specific Representation Quality | PASS | NMI=0.444 |
| Temporal Stability | PASS | 0.785 |
| Hierarchy Coherence | FAIL | level_1_nmi=0.454 |
| Cluster Coherence | FAIL | branch_purity=0.618, lang_purity=0.978 |
| Cross-language Retrieval (full) | FAIL | 0.0024 |
| Boilerplate Resistance | FAIL | -0.925 |

**Verdict:** FAIL — Language artifacts dominate neighbors (purity 0.98), preventing cross-language legal navigation. Legal structure IS captured within each language (zero-shot transfer PASS, per-language NMI=0.44).

---

## Current Blockers

| Blocker | Details |
|---------|---------|
| **Primary** | legal_distance_174k_transformed_dense_embeddings_not_in_accepted_state |
| **Dense embedding progress** | 16/26 years complete (2000-2015, ~101k decisions) in checkpoints; years 2016-2025 pending |
| **Transformed representations pending** | center_projected (768/128/64), linear_metric, mahalanobis, hybrid_stabilized, hybrid_v2 — all at 174k scale |
| **Citation roles at 174k** | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 |
| **Linear hybrids at 174k** | linear_citation_concat, linear_hybrid05_concat |

---

## Infrastructure Readiness

- ✅ **Metadata 174k symlink** verified
- ✅ **Corpus canonical path** verified (symlinks created per v29)
- ✅ **Evaluation harness** frozen v3 thresholds, exact k-NN on stratified subsample
- ✅ **Test suite** passing all reproducibility and audit correction tests
- ✅ **Formal suite scripts** operational
- ✅ **Monitor active** — check_count=134 (last 2026-09-27), no new awaited representations detected

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified for TF-IDF family or raw multilingual-e5. The monitor will autonomously evaluate transformed dense embeddings, citation roles, and linear hybrids when legal-distance promotes them to accepted state at full 174k scale.

**External dependency:** Jurist human study framework ready; requires 5-10 Swiss jurists recruitment.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
4. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
5. `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json`
6. `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json`
7. `evaluation/state/monitor_174k_state.json` (check_count=134)
8. `evaluation/monitor_and_evaluate_174k.py`

---

*Report generated per Research Protocol: frozen hypothesis, corpus, baseline, metric, and success rule before result observation. Negative results preserved as first-class evidence.*