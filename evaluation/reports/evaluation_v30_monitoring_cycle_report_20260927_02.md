# Evaluation Lane v30 Monitoring Cycle Report (Second Check)

**Factory Direction**: v30 | **GitHub Run**: 36291318078 | **Date**: 2026-09-27

## Executive Summary

The evaluation lane completed its v30 monitoring cycle (check #141). **No new 174k dense embeddings detected** in the legal-distance accepted state. The TF-IDF production family (8 representations) remains **fully evaluated at 174k scale** across all three machine-executable sub-questions from factory direction v30. Infrastructure is **fully operational and verified**. The lane continues monitoring for legal-distance 174k dense embeddings (year-split CPU execution, 16/26 years complete in checkpoints).

## Monitoring Results

| Check | Status |
|-------|--------|
| Monitor scan (legal-distance v5-v14, fractal-map) | **NO 174k dense embeddings found** |
| Monitor check count | **141** (incremented from 139) |
| TF-IDF family evaluation | **COMPLETE** (8/8 representations) |
| Legal-distance 174k dense checkpoints | **16/26 years complete** (2000-2015, ~99,325 decisions, ~57% decision completion) |

## Completed Work (TF-IDF Family at 174k — All Three Sub-Questions COMPLETE)

All three machine-executable sub-questions from factory direction v30 **COMPLETE**:

1. **Full 12-benchmark formal suite** (frozen config hash `4323f833fa72366a`): All 8 TF-IDF representations evaluated at 173,963 decisions with HNSW artifact fix (exact k-NN on fixed stratified subsample n=2000).
   - **PASS both adversarial gates (5)**: `cited_decisions_tfidf`, `outcome_tfidf`, `regeste_tfidf`, `cited_outcome_hybrid_0.5`, `cited_outcome_hybrid_0.7`
   - **FAIL both adversarial gates (3)**: `full_text_tfidf_light`, `regeste_full_text_hybrid_0.5`, `regeste_full_text_hybrid_0.7` (language dominance = 1.0, jurist preference = 0.0)

2. **Citation heritage benchmark** (frozen 137,314 pairs): Validated on published 174k citation-ID resolution (95.9%, 2,019/2,105 resolved).
   - All 8 TF-IDF representations **FAIL recall@10 > 0.2 threshold** (best `cited_decisions_tfidf`: 0.048)
   - Some pass AUC ≥ 0.65 but recall@10 is the binding gate

3. **v17b label normalization at 174k**: 214→164 labels (23.4% reduction), 49 cross-lingual canonical concepts.
   - **PARTIAL generalization**: 2/8 representations within ≤10% worsening rule (`cited_decisions_tfidf`, `regeste_tfidf`)
   - 6 exceed worsening threshold (5 on hierarchy NMI: -10.8% to -27.6%; 1 on zoom_coherence)
   - Best normalized hierarchy purity: 0.465 (threshold: 0.7)

## Partial Dense Embedding Trajectory (Informational — Not 174k Scale)

Center-projected evaluation on **16-year partial** (2000-2015, 99,325 decisions) shows **SIGNIFICANT IMPROVEMENT** over 3-year partial:

| Representation | 3-year lang_dom | 16-year lang_dom | Δ | 3-year jurist_pref | 16-year jurist_pref | Δ |
|---|---|---|---|---|---|---|
| center_projected_768dim | 0.9806 | 0.8774 | -0.1032 | 0.0400 | 0.2970 | +0.2570 |
| **center_projected_64dim** | **0.9782** | **0.8680** | **-0.1102** | **0.0448** | **0.3270** | **+0.2822** |
| center_projected_128dim | 0.9804 | 0.8746 | -0.1058 | 0.0409 | 0.3020 | +0.2611 |

**Key findings**:
- **Best**: `center_projected_64dim_partial_2000_2015` (lang_dom=0.868, jurist_pref=0.327) — closest to both adversarial thresholds
- Cross-language transfer **PASSES** for all three (transfer_gap 0.033-0.041)
- Language-specific quality **PASSES** for all three (mean_nmi 0.38-0.40)
- Cross-language retrieval on 15k subsample: **64dim PASS** (recall=0.274), 128dim PASS (recall=0.251), 768dim FAIL (recall=0.025)
- Hierarchy coherence **FAIL** for all (level_0_nmi 0.27-0.30, level_1_nmi 0.40-0.42, nesting_score 0.67-0.70)
- Raw multilingual-e5 768dim (no center-projection): lang_dom=0.9855, jurist_pref=0.0275 — **confirms center-projection is necessary and effective**

**Trajectory interpretation**: Language dominance dropped from ~0.98 to ~0.87 (approaching 0.85 threshold). Jurist preference rose from ~0.04 to ~0.30 (still below 0.5 threshold). Clear positive trajectory with corpus scale; full 174k center-projected evaluation needed for definitive verdict.

## Infrastructure Verification

| Component | Status | Evidence |
|-----------|--------|----------|
| `scalable_nn.py` HNSW backend | OPERATIONAL | hnswlib confirmed at 15k+ scale |
| `run_174k_formal_suite.py` (HNSW artifact fixed) | OPERATIONAL | Exact k-NN on valid subset (n≈2000) for adversarial; HNSW for full-corpus |
| `run_full_corpus_evaluation.py` | OPERATIONAL | Config hash matches frozen v3; center_projected_64dim PASS at 1200 scale |
| `validate_citation_heritage_174k.py` | OPERATIONAL | 137,314 pairs ready, 95.9% citation resolution |
| `run_v17b_label_normalization_all_reps.py` | OPERATIONAL | Tested at 174k: hierarchy NMI worsening -9.6% (within ≤10% rule) |
| `monitor_and_evaluate_174k.py` | ENHANCED | `run_formal_suite_v25()` auto-evaluates new representations via full v25 protocol |
| Test suite | PASSING | frozen_harness_reproducibility, v17_label_normalization, v17b_all_reps, v16_full_benchmark_suite, boilerplate_resistance_real, cross_lingual_alignment_v10, audit_correction_verification |

## Blockers

| Blocker | Type | Resolution Path |
|---------|------|-----------------|
| Legal-distance 174k dense embeddings (full concatenation + transformations) | External dependency | Legal-distance RUN (year-split, CPU-feasible staged computation; checkpoints 2000-2015 complete; years 2016-2025 pending) |
| Jurist human study | External dependency | Requires 5-10 Swiss jurists recruitment by repository owner |

## Awaited Representations (from factory direction v30)

**Dense embeddings (7)**: `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3`

**Citation roles (3)**: `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3`

**Linear hybrids (2)**: `linear_citation_concat`, `linear_hybrid05_concat`

## State Update

- `state/evaluation.json`: Updated `monitor_status.check_count` to 141, `last_check` to 2026-09-27T03:29:22
- `evaluation/state/monitor_174k_state.json`: check_count=141, last_check=2026-09-27T03:29:22

## Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified for TF-IDF family. Evaluation infrastructure is **production-ready** for auto-evaluation when legal-distance 174k dense embeddings land in accepted state. Monitor continues running (141 checks completed). Factory Director to decide successor question.

## Evidence References

- State: `state/evaluation.json` (updated with v30 cycle verification, direction_version=30)
- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=141)
- v25 formal suite results: `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- Citation heritage: `results/evaluation/v25_174k_citation_heritage/`
- v17b 174k results: `results/evaluation/v25_174k_v17b/`
- Legal area analysis: `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
- Monitor log: `evaluation/logs/monitor_174k.log`
- Partial dense 16-year evaluation: `evaluation/results/174k/center_projected_partial_2000_2015/`