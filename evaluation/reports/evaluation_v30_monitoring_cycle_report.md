# Evaluation Lane v30 Monitoring Cycle Report

**Factory Direction**: v27 | **GitHub Run**: 36091515065 | **Date**: 2026-09-25

## Executive Summary

The evaluation lane completed its monitoring cycle. **No new 174k dense embeddings detected** in the legal-distance accepted state. The TF-IDF production family (8 representations) remains **fully evaluated at 174k scale** across all three machine-executable sub-questions. Infrastructure is **fully operational and verified**. The lane continues monitoring for legal-distance 174k dense embeddings (gh run 36071928708, staged year-split CPU execution).

## Monitoring Results

| Check | Status |
|-------|--------|
| Monitor scan (legal-distance v5-v14, fractal_map) | **NO 174k dense embeddings found** |
| Monitor check count | 33 |
| TF-IDF family evaluation | **COMPLETE** (8/8 representations) |
| Legal-distance 174k run | **ACTIVE** (gh run 36071928708) |

## Completed Work (TF-IDF Family at 174k)

All three machine-executable sub-questions from factory direction v25 **COMPLETE**:

1. **Full 12-benchmark formal suite** (frozen config hash `4323f833fa72366a`): All 8 TF-IDF representations evaluated at 173,963 decisions. Pass counts: `full_text_tfidf_light`=7/12, `regeste_full_text_hybrid_0.5`=7/12, `regeste_full_text_hybrid_0.7`=7/12, `cited_decisions_tfidf`=6/12, `cited_outcome_hybrid_0.5`=6/12, `cited_outcome_hybrid_0.7`=6/12, `regeste_tfidf`=5/12, `outcome_tfidf`=3/12.

2. **Citation heritage benchmark** (frozen 137,314 pairs): 7/8 representations PASS AUC≥0.65. Best: `cited_decisions_tfidf` AUC=0.9731, `cited_outcome_hybrid_0.7` AUC=0.9605. Production default `cited_outcome_hybrid_0.7` confirmed (passes both adversarial gates, nn_citation_rate@10=0.490).

3. **v17b label normalization at 174k**: 213→163 labels (23.5% reduction), 32 cross-lingual canonical concepts. 2/8 representations within ≤10% worsening rule (`cited_decisions_tfidf`, `regeste_tfidf`); 6 exceed (5 on hierarchy NMI: -10.8% to -27.6%; 1 on zoom_coherence: `cited_outcome_hybrid_0.5` -16.0%).

## Infrastructure Verification

| Component | Status | Evidence |
|-----------|--------|----------|
| `scalable_nn.py` HNSW backend | OPERATIONAL | hnswlib confirmed at 15k+ scale |
| `run_full_corpus_evaluation.py` | OPERATIONAL | Config hash `4047da047fb339c1` matches frozen v3; center_projected_64dim PASS both adversarial gates at 1200 scale (LangDom=0.7664, Jurist=0.5121) |
| `v25_174k_formal_suite` runner | OPERATIONAL | Tested `cited_outcome_hybrid_0.5`: 6 PASS / 5 FAIL / 1 SKIP in 88s |
| `validate_citation_heritage_174k.py` | OPERATIONAL | 137,314 pairs ready, 95.9% citation resolution (2,019/2,105) |
| `run_v17b_label_normalization_all_reps.py` | OPERATIONAL | Tested at 174k: hierarchy NMI worsening -9.6% (within ≤10% rule) |
| `monitor_and_evaluate_174k.py` | ENHANCED | `run_formal_suite_v25()` auto-evaluates new representations via full v25 protocol |

## Blockers

| Blocker | Type | Resolution Path |
|---------|------|-----------------|
| Legal-distance 174k dense embeddings | External dependency | Legal-distance RUN (gh run 36071928708, year-split, CPU-feasible staged computation) |
| Jurist human study | External dependency | Requires 5-10 Swiss jurists recruitment by repository owner |

## Awaited Representations (from factory direction v27)

**Dense embeddings (6)**: `center_projected_768dim`, `center_projected_64dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3`

**Citation roles (3)**: `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3`

**Linear hybrids (2)**: `linear_citation_concat`, `linear_hybrid05_concat`

## Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified for TF-IDF family. Evaluation infrastructure is **production-ready** for auto-evaluation when legal-distance 174k dense embeddings land in accepted state. Monitor continues running (33 checks completed).

## Evidence References

- State: `evaluation/state/evaluation.json` (updated with v30 cycle verification)
- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=33)
- v25 formal suite results: `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- Citation heritage: `results/evaluation/v25_174k_citation_heritage/`
- v17b 174k results: `results/evaluation/v25_174k_v17b/`
- Legal area analysis: `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
- Monitor log: `evaluation/logs/monitor_174k.log`