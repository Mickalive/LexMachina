# Evaluation Lane - Cycle Summary (Factory Direction v28)

**Date:** 2026-09-27  
**Direction Version:** 28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** FALSE  

---

## Factory Direction v28 Question

> Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels.

---

## Work Completed

### 1. Full 12-Benchmark Formal Suite at 174k Scale ✅ COMPLETE
- **Representations evaluated:** 8 (TF-IDF family)
- **Frozen harness:** v3 thresholds (language_dominance ≤ 0.85, jurist_pairwise ≥ 0.5)
- **HNSW artifact fix:** Exact k-NN on fixed stratified subsample (n=2000 decisions with known branch); HNSW only for full-corpus scale benchmarks
- **Config hash:** `b51701f5a9c11692`

| Representation | Verdict | Language Dominance | Jurist Preference | Both Adversarial Pass |
|---|---|---|---|---|
| cited_decisions_tfidf | PASS | 0.5295 | 0.8020 | ✅ |
| outcome_tfidf | PASS | 0.4527 | 0.7255 | ✅ |
| regeste_tfidf | PASS | 0.4835 | 0.6090 | ✅ |
| cited_outcome_hybrid_0.5 | PASS | 0.5164 | 0.8055 | ✅ |
| cited_outcome_hybrid_0.7 | PASS | 0.5238 | 0.7975 | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ❌ |

**Production default:** `cited_outcome_hybrid_0.5` (PASS, lang_dom=0.5164, jurist_pref=0.8055)

**Universal failures (corpus/label limitations, not representation defects):**
- hierarchy_coherence
- legal_area_clustering
- temporal_stability
- boilerplate_resistance

---

### 2. Citation Heritage Benchmark Validation ✅ COMPLETE
- **Citation graph source:** 174k citation-ID resolution (2,019/2,105 resolved = 95.9%)
- **Frozen pair pool:** 1,020 positive / 1,020 negative pairs
- **Thresholds:** AUC ≥ 0.65, recall@10 ≥ 0.2

| Representation | AUC | recall@10 | Status |
|---|---|---|---|
| cited_decisions_tfidf | 0.7892 | 0.048 | FAIL |
| outcome_tfidf | 0.6575 | 0.000 | FAIL |
| regeste_tfidf | 0.4861 | 0.004 | FAIL |
| full_text_tfidf_light | 0.8969 | 0.053 | FAIL |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.050 | FAIL |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.049 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.035 | FAIL |

**Finding:** All 8 TF-IDF representations FAIL recall@10 threshold (0.2) despite some passing AUC. Benchmark infrastructure ready for 174k dense embeddings when available.

---

### 3. v17b Label Normalization Test at 174k ✅ COMPLETE
- **Raw unique labels:** 214 → **Normalized:** 164 (23.4% reduction)
- **Labels changed:** 85,819 / 91,193 decisions with legal_area
- **Cross-lingual concepts merged:** 32

**Differential effect confirmed:**
- **Citation-based representations IMPROVE** with normalization: hierarchy purity +5-6%, zoom_fine +3-4%
- **Text-based representations DEGRADE** with normalization: zoom_fine -31% to -34%

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio |
|---|---|---|---|
| cited_decisions_tfidf | 1.0568 | 1.0381 | 1.0616 |
| outcome_tfidf | 1.0458 | 1.0829 | 1.0437 |
| regeste_tfidf | 1.0000 | 1.1031 | 1.0173 |
| cited_outcome_hybrid_0.5 | 1.0558 | 1.0366 | 1.0627 |
| cited_outcome_hybrid_0.7 | 1.0530 | 1.0461 | 1.0583 |
| full_text_tfidf_light | 1.0000 | **0.6683** | 0.9732 |
| regeste_full_text_hybrid_0.5 | 1.0000 | **0.6607** | 0.9694 |
| regeste_full_text_hybrid_0.7 | 1.0001 | **0.6952** | 0.9634 |

**Note:** Even with normalization, best hierarchy purity = 0.47 < 0.7 threshold. v16 "data granularity" attribution partially a label normalization artifact.

---

## Blockers / Dependencies

| Blocker | Status | Details |
|---|---|---|
| **174k dense embeddings (legal-distance)** | BLOCKED | Only 3/26 years ACCEPTED (2000-2002); years 2003-2015 (16/26) pending audit per factory direction v28 |
| **Citation role embeddings** | BLOCKED | Evaluated at 1200-scale only (v7), not at 174k |
| **Linear hybrid embeddings** | BLOCKED | Evaluated at 1200-scale only (v12), not at 174k |
| **Jurist human study** | BLOCKED | Framework ready; requires 5-10 Swiss jurists (external dependency) |

**Awaited production representations (12):**
- center_projected_768dim/64dim/128dim_174k
- linear_metric_epoch4_174k
- mahalanobis_metric_epoch4_174k
- hybrid_stabilized_epoch1_174k
- hybrid_v2_epoch3_174k
- citation_role_citing/following/criticizing_174k
- linear_citation_concat_174k
- linear_hybrid05_concat_174k

---

## Infrastructure Readiness ✅ ALL OPERATIONAL

| Component | Status |
|---|---|
| Metadata 174k (173,963 entries, branch+legal_area 100% coverage) | VERIFIED |
| Corpus canonical path (bger_YYYY.jsonl 2003-2025) | VERIFIED |
| Evaluation harness (frozen v3, exact k-NN n=2000) | VERIFIED |
| Test suite (frozen_harness_reproducibility, v17b, v16, boilerplate, cross-lingual, audit) | PASSING |
| Formal suite scripts (run_174k_formal_suite.py, scalable_nn.py) | READY |
| Monitor (check_count=149, active) | ACTIVE |

---

## Recommendation

**continue_recommended = FALSE**

No additional same-question cycle is justified without new production representations from legal-distance. The evaluation lane has completed all three machine-executable sub-questions for the available TF-IDF family at 174k scale. The monitor is active and will automatically execute the formal suite when 174k dense embeddings, citation roles, and linear hybrids land in the accepted state.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/state/monitor_174k_state.json`
- `evaluation/monitor_and_evaluate_174k.py`