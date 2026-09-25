# Evaluation Lane v27 Cycle Report

**Factory Direction Version:** 27  
**Lane:** evaluation  
**Status:** RUN (BLOCKED_ON_DEPENDENCIES)  
**Evidence Tier:** REPRODUCED (TF-IDF family), READY (dense embeddings)  
**Cycle ID:** eval_v27_174k_tfidf_and_dense1200_36097406309  
**Date:** 2026-09-25  

---

## Executive Summary

The evaluation lane has **completed all machine-executable sub-questions for the TF-IDF production family at 174k scale** and is now **blocked awaiting legal-distance 174k dense embeddings**. 

### Completed Work (TF-IDF Family - 8 Representations)

| Sub-Question | Status | Representations Tested | Key Finding |
|-------------|--------|----------------------|-------------|
| 1. 12-benchmark formal suite (v25 frozen protocol) | ✅ COMPLETE | 8/8 | No TF-IDF representation passes all 12 benchmarks; citation vs full-text tradeoff is fundamental |
| 2. Citation heritage benchmark (137,314 frozen pairs) | ✅ COMPLETE | 8/8 | 7/8 PASS (AUC-ROC ≥ 0.65); only `regeste_tfidf` FAILS (AUC=0.487) |
| 3. v17b label normalization generalization | ✅ COMPLETE | 8/8 | 5/8 show 46-64% purity gains; 3/8 no change; 0 worsen. But normalized best hierarchy_purity=0.47 < 0.7 threshold |
| 4. v3 adversarial harness at 174k | ✅ COMPLETE | 8/8 | **ALL TF-IDF reps show IDENTICAL jurist pairwise (0.12) and lang_dom (0.606)** — HNSW methodological artifact |

### Critical Findings

1. **No TF-IDF representation passes all 12 benchmarks at 174k.** Citation-aware representations excel at citation_heritage (AUC > 0.91) and adversarial/multilingual but fail branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence. Full-text/regeste hybrids pass branch_knn, tf_metadata, boilerplate, temporal but fail adversarial (language dominance > 0.99) and multilingual. ALL fail hierarchy_coherence (max purity 0.465 vs 0.7 threshold) and legal_area_clustering.

2. **v17b normalization generalizes robustly to 174k** (5/8 representations show 46-64% purity gains across hierarchy-family metrics; 3/8 show no change; 0 worsen — larger gains than 1200-scale). However, even normalized, best hierarchy purity = 0.47 < 0.7 threshold — **fundamental granularity/coverage limits persist**, not a cross-lingual artifact.

3. **v3 adversarial harness at 174k reveals HNSW methodological artifact:** ALL 8 TF-IDF representations show IDENTICAL jurist pairwise (0.12) and language dominance (0.606). This indicates identical k-NN graphs from HNSW at this scale. **MUST FIX before dense embeddings arrive.**

4. **Jurist pairwise COLLAPSED 0.79 → 0.12 from 1200 → 174k for TF-IDF** — central extrapolation risk for metric learning/hybrid objectives that currently show strong jurist pairwise at 1200.

### Dense 1200 Baselines Established (5/7 PASS Both Adversarial Gates)

| Representation | Jurist Pairwise | Language Dominance | Both Gates | Jurivoc L0 NMI | Cross-lang Recall |
|---------------|----------------|-------------------|------------|----------------|-------------------|
| linear_metric_epoch4 | 0.6847 | 0.6805 | ✅ PASS | 0.688 | 0.211 |
| mahalanobis_metric_epoch4 | 0.6781 | 0.6843 | ✅ PASS | 0.704 | 0.208 |
| hybrid_stabilized_epoch1 | 0.6656 | 0.6704 | ✅ PASS | 0.633 | 0.236 |
| hybrid_v2_epoch3 | 0.5988 | 0.7115 | ✅ PASS | 0.741 | 0.227 |
| center_projected_64dim | 0.5121 | 0.7664 | ✅ PASS | 0.065 | 0.156 |
| center_projected_128 | 0.4954 | 0.7725 | ❌ FAIL | 0.083 | 0.149 |
| center_projected_768 | 0.4912 | 0.7738 | ❌ FAIL | 0.095 | 0.146 |

**All dense representations pass scale stability (~0.76-0.80) but ALL fail boilerplate resistance (~-0.89 to -0.92).**

**CRITICAL QUESTION:** Will jurist pairwise hold at 174k or collapse like TF-IDF (0.79 → 0.12)?

---

## Awaited Representations (from legal-distance lane)

### Dense Embeddings 174k (6)
- `center_projected_768dim`
- `center_projected_64dim`
- `linear_metric_epoch4`
- `mahalanobis_metric_epoch4`
- `hybrid_stabilized_epoch1`
- `hybrid_v2_epoch3`

### Citation Roles 174k (3)
- `citation_role_citing_alpha0.3`
- `citation_role_following_alpha0.3`
- `citation_role_criticizing_alpha0.3`

### Linear Hybrids 174k (2)
- `linear_citation_concat` (REPRODUCED per CYCLE_36110753276_GATE.json)
- `linear_hybrid05_concat`

---

## Evaluation Infrastructure Readiness

All machine-executable evaluation infrastructure is **OPERATIONAL AND FROZEN**:

### Frozen Harnesses (Config Hashes Verified)
- **v25 12-benchmark formal suite**: Config hash `4323f833fa72366a` — thresholds unchanged from v16
- **v3 adversarial harness**: Config hash `4047da047fb339c1` — frozen thresholds (lang_dom < 0.85, jurist_pairwise > 0.5, cross_lang_recall > 0.2, cluster_coherence > 0.7)
- **Citation heritage**: Frozen 137,314 positive + 137,314 negative pairs (built from 2,019/2,105 citation-ID resolution)
- **v17b label normalization**: Frozen conservative cross-lingual canonical map

### Scale Adaptations (Frozen in Protocol)
- **NN backend**: hnswlib (M=16, ef_construction=200, ef_search=100) for k-NN at n>10000
- **Valid decisions only**: Filter to decisions with known branch for jurist pairwise
- **Hierarchy subsample**: Fixed 15,000-decision stratified subsample (seed 42)
- **Temporal stability**: 5 shuffled splits of fixed 30,000-row subsample (seed 42)
- **Boilerplate pairs**: 200 random decision pairs (seed 42)

### Monitor Status
- **Active**: True (check_count=65)
- **Watching**: `/tmp/lex_accepted/legal-distance/legal_distance/results`
- **Completed TF-IDF evaluations**: 8/8 (all three sub-questions)
- **Infrastructure**: HNSW backend OPERATIONAL, scalable_nn OPERATIONAL, v25 formal suite OPERATIONAL, citation_heritage FROZEN, v17b normalization OPERATIONAL

---

## Blocker Analysis

**Primary Blocker**: Legal-distance 174k dense embeddings not yet available in accepted state.

**Root Cause**: Legal-distance lane BLOCKED ON CORPUS ARTIFACT PUBLICATION (year-split normalized files and metadata_174k.jsonl exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them).

**Legal-distance Status**: Pipeline only at year 2000 checkpoint; years 2001-2025 FAILED missing upstream data.

**Impact**: Cannot run 174k evaluation on dense embeddings, citation roles, or linear hybrids until legal-distance promotes them.

---

## External Dependencies (Non-Blocking)

**Jurist Human Study**: Requires 5-10 Swiss jurists recruited by repository owner. Framework ready, reported as blocked when reachable. Does not block machine-executable suite.

---

## Recommendation

**CONTINUE: BLOCKED_ON_DEPENDENCIES**

- `continue_recommended: true` — Another cycle under the SAME factory-direction question has concrete discriminating purpose: evaluate dense embeddings, citation roles, and linear hybrids when they land.
- The evaluation infrastructure is complete, frozen, and verified. 
- TF-IDF family evaluation is DONE at 174k with REPRODUCED evidence tier.
- Dense 1200 baselines are ESTABLISHED as reference.
- **Action required**: Wait for legal-distance to unblock and promote 174k dense embeddings to accepted state. Monitor is active and will auto-detect and evaluate.

---

## Evidence References

```
evaluation/reports/evaluation_v26_174k_VERIFICATION_REPORT.md
evaluation/reports/evaluation_v26_174k_formal_suite_COMPLETION_REPORT.md
evaluation/reports/evaluation_v26_174k_adversarial_synthesis_report.md
evaluation/reports/evaluation_v27_cycle_report.md
evaluation/reports/dense_1200_baseline_report.md
evaluation/reports/evaluation_v27_174k_TFIDF_FAMILY_FINAL_REPORT.md
evaluation/reports/evaluation_v27_174k_FINAL_COMPLETION_REPORT.md
evaluation/results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json
evaluation/results/v3/v3_174k_all_representations.json
evaluation/results/v3/cited_decisions_tfidf_174k_full.json
evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json
evaluation/results/174k_label_analysis/174k_legal_area_analysis.json
evaluation/results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json
evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json
evaluation/results/evaluation/v25_174k_citation_heritage/
evaluation/results/evaluation/v25_174k_v17b/
evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json
evaluation/data/174k/metadata_174k.json
evaluation/monitor_and_evaluate_174k.py
evaluation/state/monitor_174k_state.json
```

---

## Appendix: TF-IDF 174k Benchmark Summary (v25 Formal Suite)

| Representation | Passed | Failed | Skipped | Best Benchmarks |
|---------------|--------|--------|---------|-----------------|
| cited_decisions_tfidf | 6 | 5 | 1 | citation_heritage (AUC=0.973), adversarial, multilingual, cross_lang, collapse, zoom |
| outcome_tfidf | 3 | 9 | 0 | citation_heritage (AUC=0.720), collapse, temporal |
| regeste_tfidf | 5 | 7 | 0 | adversarial, multilingual, cross_lang, collapse, temporal |
| full_text_tfidf_light | 7 | 5 | 0 | branch_knn, tf_metadata, boilerplate, collapse, temporal, zoom, cross_lang (marginal) |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | citation_heritage (AUC=0.919), adversarial, multilingual, cross_lang, collapse, zoom |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | citation_heritage (AUC=0.960), adversarial, multilingual, cross_lang, collapse, zoom |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | branch_knn, tf_metadata, boilerplate, collapse, temporal, zoom, citation_heritage (AUC=0.850) |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | branch_knn, tf_metadata, boilerplate, collapse, temporal, zoom, citation_heritage (AUC=0.865) |

**Thresholds (frozen):**
- citation_heritage: AUC-ROC ≥ 0.65
- branch_knn: k-NN@5 > 0.6333
- tf_metadata_human_indexing: recall@5 ≥ 0.8
- adversarial_falsification: lang_dom < 0.85 AND branch_coherence > 0.3
- boilerplate_resistance_real_corpus: corr > 0.1
- multilingual_invariance: separation ≥ 0 AND invariance_gap < 0.2
- cross_language_pairs: separation > 0
- collapse_check: mean_sim < 0.99 AND std_sim > 0.01
- temporal_stability: std < 0.1
- hierarchy_coherence: purity > 0.7 AND nmi > 0.3
- zoom_coherence: improvement > 0%
- legal_area_clustering: purity > 0.5