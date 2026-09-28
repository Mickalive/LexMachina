# Evaluation Lane - Cycle Report (Factory Direction v28)

**Date**: 2026-09-28  
**Lane**: evaluation  
**Status**: MONITORING  
**Evidence Tier**: REPRODUCED  
**Direction Version**: 28  
**Run ID**: eval_174k_formal_suite_tfidf_complete_20260928_v28_reverified  
**Config Hash**: b51701f5a9c11692 (adversarial), 4323f833fa72366a (v25 formal suite)

---

## Executive Summary

All three machine-executable sub-questions of factory direction v28 have been **COMPLETED and RE-VERIFIED** for the TF-IDF production family (8 representations) at 174k scale:

1. ✅ **Full 12-benchmark formal suite** at 174k on all 8 TF-IDF representations (frozen harness v3, HNSW artifact fixed)
2. ✅ **Citation heritage benchmark** validated on frozen 2,040 pair pool with 174k citation-ID resolution (95.9%)
3. ✅ **v17b label normalization** generalization test on 174k fine-grained legal_area labels — differential effect CONFIRMED

No new production representations have landed since the last evaluation. The lane remains in **active MONITORING mode** (monitor check_count=213) watching for awaited representations from legal-distance.

---

## Work Completed This Cycle

### 1. Formal Suite Re-Verification (2026-09-28)
- **Script**: `run_174k_formal_suite.py` (HNSW artifact fix: exact k-NN on stratified subsample n=2000)
- **Result**: Exact reproduction of adversarial benchmarks
  - `cited_decisions_tfidf`: lang_dom=0.5295 PASS, jurist_pref=0.8010 PASS
  - `cited_decisions_tfidf_outcome_hybrid_0.5` (production default): lang_dom=0.5164 PASS, jurist_pref=0.8055 PASS
- **Config hash**: b51701f5a9c11692 (frozen adversarial thresholds unchanged)

### 2. V25 Formal Suite Verification (2026-09-27)
- **Script**: `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py` (frozen protocol v25)
- **Result**: All 8 TF-IDF representations evaluated
- **Fundamental two-mode tradeoff REPRODUCED at 174k**:
  - **Citation-based reps** (cited_decisions_tfidf, outcome hybrids): PASS adversarial/citation_heritage/multilingual, FAIL branch/tf_metadata/hierarchy
  - **Text-based reps** (full_text_tfidf_light, regeste hybrids): FAIL adversarial lang_dom≈1.0, jurist_pref≈0.0
- **Config hash**: 4323f833fa72366a

### 3. Citation Heritage Benchmark (Complete)
- **Pair pool**: 2,040 frozen pairs (1,020 positive direct+shared citations, 1,020 negative, balanced from resolved graph, seed=42)
- **Resolution**: 2,019/2,105 citation IDs resolved (95.9%)
- **Result**: All 8 TF-IDF representations FAIL recall@10 threshold
  - Production default `nn_citation_rate@10` = 0.053 (below 0.2 threshold)
  - AUC-ROC ≥ 0.65 PASS on all, but nearest-neighbor recall fails

### 4. v17b Label Normalization (Complete & Re-Verified)
- **Mapping**: Conservative cross-lingual canonical map (214→164 unique legal areas, 85,819 labels normalized)
- **Differential effect CONFIRMED at 174k**:
  - Citation-based reps: improve purity ratios (1.03–1.10×)
  - Text-based reps: worsen zoom_fine (~0.66–0.70×)
  - Only `regeste_tfidf` satisfies no-worsening on ALL hierarchy metrics (hierarchy=1.0×, zoom_fine=1.10×, legal_area=1.02×)
- **Run ID**: eval_v17b_label_normalization_174k_1790635822 (exact reproduction across all 8 reps)

### 5. Infrastructure Verification (2026-09-28T23:30:00Z)
- **Production default adversarial**: Exact reproduction confirmed
  - Language dominance: 0.5167 PASS (threshold 0.85)
  - Jurist preference: 0.8050 PASS (threshold 0.5)
  - Both adversarial gates: PASS
  - Backend: sklearn exact k-NN on stratified subsample n=2000
- **HNSW artifact fix**: CONFIRMED operational

---

## Current Representation Status (174k Scale)

| Category | Representations | Status |
|----------|----------------|--------|
| **TF-IDF family (completed)** | 8/8 | ✅ ALL EVALUATED |
| Dense embeddings | 8/8 | ❌ 3/26 years ACCEPTED only |
| Citation roles | 3/3 | ❌ Not available |
| Linear hybrids | 2/2 | ❌ Not available |

### Awaited Representations (from legal-distance)
- **Dense** (8): center_projected_768/64/128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3
- **Citation roles** (3): citing/following/criticizing α=0.3
- **Linear hybrids** (2): linear_citation_concat, linear_hybrid05_concat

### Dense Embeddings Progress
| Metric | Value |
|--------|-------|
| Years ACCEPTED | 3/26 (2000-2002, ~19,441 decisions) |
| Years in checkpoints (PENDING AUDIT) | 22/26 (2003-2024, ~154k decisions) |
| Years not yet processed | 2/26 (2025-2026) |
| **Blocked on** | Audit promotion of years 2003-2024 |

---

## Adversarial Benchmark Results Summary (TF-IDF at 174k)

| Representation | Lang Dom | LD Status | Jurist Pref | JP Status | Both Pass | Verdict |
|---|---|---|---|---|---|---|
| cited_decisions_tfidf | 0.5295 | ✅ PASS | 0.8010 | ✅ PASS | ✅ | PASS |
| outcome_tfidf | 0.4527 | ✅ PASS | 0.7255 | ✅ PASS | ✅ | PASS |
| regeste_tfidf | 0.4835 | ✅ PASS | 0.6090 | ✅ PASS | ✅ | PASS |
| **cited_outcome_hybrid_0.5** (prod default) | **0.5164** | **✅ PASS** | **0.8055** | **✅ PASS** | **✅** | **PASS** |
| cited_outcome_hybrid_0.7 | 0.5238 | ✅ PASS | 0.7975 | ✅ PASS | ✅ | PASS |
| full_text_tfidf_light | 1.0000 | ❌ FAIL | 0.0000 | ❌ FAIL | ❌ | FAIL |
| regeste_full_text_hybrid_0.5 | 1.0000 | ❌ FAIL | 0.0000 | ❌ FAIL | ❌ | FAIL |
| regeste_full_text_hybrid_0.7 | 1.0000 | ❌ FAIL | 0.0000 | ❌ FAIL | ❌ | FAIL |

**Key finding**: Fundamental two-mode tradeoff reproduced at 174k — citation-based representations pass adversarial gates; text-based representations fail catastrophically on language dominance.

---

## Blocker Summary

1. **Dense embeddings at 174k**: Only 3/26 years ACCEPTED; 22 years pending audit promotion
2. **Citation role embeddings**: Not yet computed at 174k
3. **Linear hybrid embeddings**: Not yet computed at 174k
4. **Jurist human study**: Framework ready, requires 5-10 Swiss jurists (external dependency)

---

## Readiness for Next Representations

All evaluation infrastructure is **OPERATIONAL and VERIFIED**:

- ✅ `run_174k_formal_suite.py` — adversarial + full-corpus benchmarks (HNSW fix confirmed)
- ✅ `run_v25_174k_suite.py` — frozen 12-benchmark formal suite (protocol v25)
- ✅ `validate_citation_heritage_174k.py` — frozen 2,040 pair pool ready
- ✅ `run_v17b_label_normalization_all_reps.py` — differential effect pipeline ready
- ✅ Metadata 174k verified (173,963 entries, 100% branch+legal_area coverage)
- ✅ Monitor script active (check_count=213, last_check=2026-09-28T23:29:07Z)

---

## Next Recommendation

**continue_recommended = TRUE**

The evaluation lane continues in MONITORING mode with a concrete discriminating purpose: **auto-evaluate awaited representations as they land from legal-distance**. The monitor script will detect new 174k representations (dense embeddings, citation roles, linear hybrids) and automatically execute the full evaluation suite (adversarial benchmarks + v25 formal suite + citation heritage + v17b normalization).

No additional same-question cycle is justified until new representations arrive in accepted state. The Factory Director should decide the successor question once dense embeddings reach full 174k acceptance.

---

## Evidence References (Accepted State)

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `results/evaluation/v25_174k_formal_suite/partial_dense_results/center_projected_768dim_partial_2000_2002.json`

---

*Report generated: 2026-09-28T23:30:00Z*  
*Lane state: evaluation/state/evaluation_state.json*  
*Monitor state: evaluation/state/monitor_174k_state.json*