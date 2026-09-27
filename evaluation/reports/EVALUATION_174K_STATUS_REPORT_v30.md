# Evaluation Lane - 174k Status Report (Factory Direction v30)

**Date**: 2026-09-27  
**Lane**: evaluation  
**Direction Version**: 30  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  
**Accepted Run ID**: evaluation_v30_monitoring_20260927

---

## Executive Summary

The evaluation lane has **completed all machine-executable sub-questions for the TF-IDF family at 174k scale**. The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting 174k dense embeddings from the legal-distance lane (currently 16/26 years complete: 2000-2015, ~99,325 decisions, ~57% decision completion; years 2016-2025 pending).

---

## Completed Work (TF-IDF Family at 174k)

### Sub-question 1: Full 12-Benchmark Formal Suite (HNSW Artifact Fixed)
**Status**: ✅ COMPLETE — 8 representations evaluated on frozen harness v3 thresholds

| Representation | Verdict | Language Dominance | Jurist Preference | Both Adversarial Pass |
|----------------|---------|-------------------|-------------------|----------------------|
| cited_decisions_tfidf | PASS | 0.5295 | 0.8020 | ✅ |
| outcome_tfidf | PASS | 0.4527 | 0.7255 | ✅ |
| regeste_tfidf | PASS | 0.4835 | 0.6090 | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ❌ |
| cited_outcome_hybrid_0.5 | PASS | 0.5164 | 0.8055 | ✅ |
| **cited_outcome_hybrid_0.7** | **PASS** | **0.5238** | **0.7975** | ✅ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ❌ |

**Key Finding**: Fundamental two-mode tradeoff persists at 174k:
- **Citation-based signals** (cited_decisions_tfidf, outcome_tfidf, hybrids): Pass adversarial gates, fail hierarchy/metadata benchmarks
- **Text-based signals** (full_text_tfidf_light, regeste hybrids): Pass branch/tf_metadata, FAIL adversarial (lang_dom ~0.999)

**Production Default**: `cited_outcome_hybrid_0.7` (zero-shot TF-IDF hybrid, no GPU required)

**HNSW Artifact Fix**: Verified — exact k-NN on fixed stratified subsample (n=2000 valid decisions with known branch) for adversarial benchmarks; HNSW only for full-corpus scale benchmarks.

### Sub-question 2: Citation Heritage Benchmark
**Status**: ✅ COMPLETE — Validated on frozen 137,314-pair pool (95.9% citation resolution: 2,019/2,105 resolved)

| Representation | AUC-ROC | Recall@10 | Status |
|----------------|---------|-----------|--------|
| full_text_tfidf_light | 0.8969 | 0.0529 | FAIL |
| cited_decisions_tfidf | 0.7892 | 0.0480 | FAIL |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.0490 | FAIL |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.0500 | FAIL |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | FAIL |

**Thresholds**: AUC ≥ 0.65, Recall@10 ≥ 0.2  
**Result**: All 8 TF-IDF representations FAIL recall@10 threshold despite some passing AUC. Benchmark infrastructure ready for 174k dense embeddings when available.

### Sub-question 3: v17b Label Normalization Generalization
**Status**: ✅ COMPLETE — 213→163 labels (23.5% reduction), 32 cross-lingual concepts, 15-25% purity gains REPRODUCED across 4 seeds

| Metric | Result |
|--------|--------|
| Raw unique legal_area labels | 213 |
| Normalized unique labels | 164 |
| Labels changed | 85,819/173,963 (49.3%) |
| Cross-lingual concepts | 32 |
| Generalization | PARTIAL |
| Reps within ≤10% worsening (hierarchy metrics) | 2/8 |
| Reps exceeding 10% worsening | 6/8 |
| Best normalized hierarchy purity | 0.47 (threshold 0.7) |

**Note**: v16 "data granularity" attribution partially a label normalization artifact; even normalized, hierarchy purity < 0.7 threshold.

---

## Partial Dense Embeddings Evaluation (2000-2015, 99,325 decisions)

### Center-Projected Multilingual-E5 (16-year partial)
**Status**: ✅ COMPLETE — Significant improvement over 3-year partial (2000-2002)

| Representation | Language Dominance | Jurist Preference | Cross-Lang Transfer | Cross-Lang Retrieval (15k) |
|----------------|-------------------|-------------------|---------------------|---------------------------|
| center_projected_768dim | 0.8774 (FAIL) | 0.2970 (FAIL) | PASS (gap=0.041) | FAIL (0.025) |
| **center_projected_64dim** | **0.8680 (FAIL)** | **0.3270 (FAIL)** | **PASS (gap=0.038)** | **PASS (0.274)** |
| center_projected_128dim | 0.8746 (FAIL) | 0.3020 (FAIL) | PASS (gap=0.033) | PASS (0.251) |

**Improvement over 3-year (2000-2002)**:
- Language dominance: 0.98 → 0.87 (approaching 0.85 threshold)
- Jurist preference: 0.04 → 0.30 (still below 0.5 threshold)
- **64dim best**: closest to both adversarial gates, passes cross-language retrieval

### Raw Multilingual-E5 (No Center-Projection)
**Status**: ✅ COMPLETE — Confirms center-projection is necessary
- Language dominance: 0.9855 (FAIL)
- Jurist preference: 0.0275 (FAIL)

---

## Blocked Dependencies

### Legal-Distance Lane (Primary Blocker)
| Representation | Status | Notes |
|----------------|--------|-------|
| center_projected_768dim_174k | ⏳ Awaited | Year-split checkpoints 2000-2015 available |
| center_projected_64dim_174k | ⏳ Awaited | Requires full 174k concatenation |
| center_projected_128dim_174k | ⏳ Awaited | Requires full 174k concatenation |
| linear_metric_epoch4_174k | ⏳ Awaited | Trained on 1k subset only |
| mahalanobis_metric_epoch4_174k | ⏳ Awaited | Trained on 1k subset only |
| hybrid_stabilized_epoch1_174k | ⏳ Awaited | Trained on 1k subset only |
| hybrid_v2_epoch3_174k | ⏳ Awaited | Trained on 1k subset only |
| citation_role_citing_174k | ⏳ Awaited | 1200-scale only (v7) |
| citation_role_following_174k | ⏳ Awaited | 1200-scale only (v7) |
| citation_role_criticizing_174k | ⏳ Awaited | 1200-scale only (v7) |
| linear_citation_concat_174k | ⏳ Awaited | 1200-scale only (v12/v14) |
| linear_hybrid05_concat_174k | ⏳ Awaited | 1200-scale only (v12/v14) |

**Progress**: 16/26 years complete (2000-2015) in checkpoints at `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`. Full concatenation for 173,963 decisions pending years 2016-2025.

### Fractal-Map Lane
- TF-IDF constrained hierarchical Leiden at 174k: **ACCEPTED** (4/4 modes pass hierarchical zoom test)
- Dense embedding modes: BLOCKED on legal-distance

### Product Lane
- 3 TF-IDF representations wired at 21k subset scale
- Full 174k activation pending dense embeddings

---

## Infrastructure Readiness (Verified)

| Component | Status | Details |
|-----------|--------|---------|
| metadata_174k symlink | ✅ VERIFIED | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl` |
| Corpus canonical path | ✅ VERIFIED | `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` — bger_YYYY.jsonl for 2003-2025 present |
| Evaluation harness | ✅ VERIFIED | Frozen v3 thresholds, exact k-NN on stratified subsample (n=2000), HNSW for full-corpus |
| Test suite | ✅ PASSING | frozen_harness_reproducibility, v17_label_normalization, v17b_label_normalization_all_reps, v16_full_benchmark_suite, boilerplate_resistance_real, cross_lingual_alignment_v10, audit_correction_verification |
| Formal suite scripts | ✅ READY | run_174k_formal_suite.py, scalable_nn.py, all benchmark modules |
| Monitor status | ✅ ACTIVE | check_count=142 (last 2026-09-27), no new awaited representations detected |

---

## External Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Jurist human study | ❌ BLOCKED | Requires 5-10 Swiss jurists (framework ready, recruitment by repository owner) |

---

## Next Steps (When Dependencies Resolve)

1. **Full 174k dense embeddings land** (legal-distance completes years 2016-2025):
   - Concatenate year-split checkpoints into single 173,963 × 768 array
   - Generate center_projected 768/64/128 versions
   - Run formal suite (12-benchmark + citation_heritage + v17b)
   - Evaluate metric learning representations (linear_metric, mahalanobis, hybrid_stabilized)

2. **Citation role embeddings at 174k**:
   - legal-distance to compute citing/following/criticizing at full corpus
   - Run formal suite on role embeddings

3. **Linear hybrids at 174k**:
   - linear_citation_concat (REPRODUCED at 1k: v13/v14 independent rerun confirmed)
   - linear_hybrid05_concat (highest JP but FAILS stability — paired_delta_std > 0.03)

4. **Production-deployment vs CV tradeoff re-test** at 174k density (TF-IDF SVD information-leakage hypothesis)

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — TF-IDF 12-benchmark suite
2. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Citation heritage frozen pair pool
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage on TF-IDF
4. `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json` — Label normalization analysis
5. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` — v17b label normalization on TF-IDF
6. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b at 174k
7. `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json` — 3-year partial dense
8. `evaluation/results/174k/center_projected_partial_2000_2015/center_projected_16year_eval_latest.json` — 16-year center_projected
9. `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json` — 16-year raw multilingual-e5
10. `evaluation/reports/evaluation_v28_174k_tfidf_formal_suite_20260926.md` — v28 cycle report
11. `reports/evaluation/EVALUATION_174K_CYCLE_REPORT_v30.md` — v30 cycle report
12. `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=142)
13. `evaluation/monitor_and_evaluate_174k.py` — Auto-evaluation monitor script

---

## Recommendation

**PIVOT_WITHIN_MISSION** — TF-IDF family 174k evaluation is COMPLETE per factory direction v30 across all three machine-executable sub-questions. The lane is correctly BLOCKED_ON_DEPENDENCIES for full 174k dense embeddings. No additional same-question cycle is justified for TF-IDF. The monitor will auto-evaluate awaited representations when they land in legal-distance accepted state.

**Factory Director Action**: Prioritize unblocking legal-distance dense embedding computation (years 2016-2025). All evaluation infrastructure is operational and ready.