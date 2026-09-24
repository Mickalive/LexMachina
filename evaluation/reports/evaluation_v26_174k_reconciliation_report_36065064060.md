# Evaluation Lane — v26 174k Reconciliation Report

**GitHub Run**: 36065064060  
**Timestamp**: 2026-09-24T22:05:00Z  
**Factory Direction Version**: 26  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  
**Evidence Tier**: REPRODUCED  

---

## Executive Summary

This evaluation cycle (run 36065064060) is a **reconciliation/polling run** to verify whether legal-distance lane has delivered 174k dense embeddings for evaluation. The monitor scan confirms **no 174k dense embeddings have landed** from legal-distance. The TF-IDF production family (8 representations) remains **fully evaluated at 174k scale** with all three machine-executable sub-questions complete.

**No new evaluation work was performed** because no new representations are available. The evaluation lane remains correctly blocked on legal-distance lane's 174k dense embedding production.

---

## Current State

### ✅ COMPLETED: TF-IDF Production Family (8/8 representations)

All three machine-executable sub-questions from factory direction v25/v26 **COMPLETE** for the TF-IDF family:

| Sub-Question | Status | Details |
|--------------|--------|---------|
| **1. 12-benchmark formal suite** | ✅ COMPLETE | All 8 TF-IDF reps evaluated at 174k (173,963 decisions) against frozen v16 thresholds (config hash 4323f833fa72366a) |
| **2. Citation heritage benchmark** | ✅ COMPLETE | 7/8 reps PASS AUC≥0.65 on frozen 137,314-pair pool (2,019/2,105 citations resolved) |
| **3. v17b label normalization** | ✅ COMPLETE | 7/8 reps within ≤10% worsening rule; 1 exceeds (cited_outcome_hybrid_0.5 zoom_coherence -16%) |

**TF-IDF Representations Evaluated:**
- `cited_decisions_tfidf` — 6/12 pass, citation_heritage AUC=0.9731
- `outcome_tfidf` — 3/12 pass, citation_heritage FAIL (AUC=0.4865)
- `cited_outcome_hybrid_0.5` — 6/12 pass, citation_heritage AUC=0.9193
- `cited_outcome_hybrid_0.7` — 6/12 pass, citation_heritage AUC=0.9605 ⭐ **Production Default**
- `regeste_tfidf` — 5/12 pass, citation_heritage FAIL (AUC=0.4865)
- `full_text_tfidf_light` — 7/12 pass, citation_heritage AUC=0.6148
- `regeste_full_text_hybrid_0.5` — 7/12 pass, citation_heritage AUC=0.7442
- `regeste_full_text_hybrid_0.7` — 7/12 pass, citation_heritage AUC=0.7908

### ⏳ BLOCKED: Dense Embeddings from Legal-Distance (0/12 representations)

**Awaited representations (per factory direction v26):**

| Category | Representations | Status |
|----------|-----------------|--------|
| Center Projected | `center_projected_768dim`, `center_projected_64dim` | ❌ Not landed |
| Metric Learning | `linear_metric_epoch4`, `mahalanobis_metric_epoch4` | ❌ Not landed |
| Hybrid Objective | `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` | ❌ Not landed |
| Citation Roles | `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3` | ❌ Not landed |
| Linear Hybrids | `linear_citation_concat`, `linear_hybrid05_concat` | ❌ Not landed |

**Legal-distance lane status**: RUN (staged 174k CPU execution, year-split, TF-IDF first per factory direction v26)

---

## Infrastructure Readiness

All evaluation pipelines **verified and ready** for 174k dense embeddings (github run 36063000772):

- ✅ `run_full_corpus_evaluation.py` with HNSW backend (hnswlib) validated on 1000/1200 scale
- ✅ Frozen harness v3 config hash `4047da047fb339c1` matches exactly
- ✅ Citation heritage benchmark infrastructure: 137,314 pairs frozen and ready
- ✅ v17b label normalization test infrastructure ready for 174k clustering evaluation
- ✅ `monitor_and_evaluate_174k.py` operational for auto-evaluation on landing
- ✅ Results match legal-distance reported adversarial gate outcomes exactly

---

## Monitor Scan Result (This Run)

```
REPRESENTATION READINESS:
  priority_1_tfidf_signals:
    ✗ cited_decisions_tfidf
    ✗ outcome_tfidf
    ✗ cited_outcome_hybrid_0.5
    ✗ cited_outcome_hybrid_0.7
    ✗ linear_citation_concat
    ✗ linear_hybrid05_concat
    ✗ linear_citation_w3070
    ✗ linear_citation_ridge
  priority_2_dense_embeddings:
    ✗ center_projected_768dim
    ✗ center_projected_64dim
    ✗ linear_metric_epoch4
    ✗ linear_mahalanobis_epoch4
    ✗ hybrid_stabilized_epoch1
  priority_3_citation_roles:
    ✗ citation_role_citing_alpha0.3
    ✗ citation_role_following_alpha0.3
    ✗ citation_role_criticizing_alpha0.3
    ✗ citation_role_distinguishing_alpha0.3
    ✗ citation_role_overruling_alpha0.3
```

*Monitor watches `/tmp/lex_accepted/legal-distance/legal_distance/results/v5` — no 174k directories detected.*

---

## Key Findings (Unchanged from Prior Run)

### Universal 174k Failures (Corpus/Label Limitations)
- **hierarchy_coherence**: purity 0.08–0.47 < 0.7 threshold (all reps)
- **legal_area_clustering**: purity 0.003–0.08 < 0.5 threshold (all reps)
- **zoom_coherence**: negative improvement (all reps)
- **boilerplate_resistance_real_corpus**: correlation ~-0.9 (all reps)

*These are confirmed corpus/label granularity limitations, not representation defects (per v16/v18 findings).*

### Universal 174k Passes (All Representations)
- **branch_knn**, **adversarial_falsification**, **multilingual_invariance**, **cross_language_pairs**, **collapse_check**, **temporal_stability**

### Production Default Confirmed
**`cited_outcome_hybrid_0.7`** — zero-shot TF-IDF, no GPU required:
- Passes both adversarial gates (LangDom=0.569 < 0.85, BranchCoherence=0.356 > 0.3)
- Citation heritage AUC=0.9605, nn_citation_rate@10=0.490

---

## Recommendation

**NO ACTION REQUIRED** — Continue waiting for legal-distance lane to deliver 174k dense embeddings.

- `continue_recommended: false` — No additional same-question cycle justified for TF-IDF family
- Evaluation infrastructure fully operational and validated
- Jurist human study remains external dependency (5-10 Swiss jurists recruitment needed)
- Next material evaluation work triggered automatically when legal-distance 174k embeddings land in accepted state

---

## Evidence References

- `evaluation/state/evaluation.json` — Machine-readable lane state (updated this run)
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol
- `evaluation/results/v25_174k_formal_suite/results/_suite_summary.json` — Suite summary
- `evaluation/results/v25_174k_citation_heritage/` — Citation heritage results
- `evaluation/results/v25_174k_v17b/` — v17b normalization results
- `evaluation/monitor_and_evaluate_174k.py` — Auto-evaluation monitor
- `evaluation/state/monitor_174k_state.json` — Monitor state (14 checks, 0 detections)

---

*Report generated automatically by evaluation lane reconciliation cycle.*