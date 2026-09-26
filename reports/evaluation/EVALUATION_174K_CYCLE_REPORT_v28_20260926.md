# Evaluation Lane — 174k Cycle Report (Factory Direction v28)

**Date**: 2026-09-26  
**Direction Version**: 28  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false

---

## Executive Summary

The TF-IDF family (8 representations) evaluation at **174,113 decisions** is **COMPLETE** across all three machine-executable sub-questions from factory direction v28. No representation passes all benchmarks; a fundamental two-mode tradeoff persists. The lane is blocked awaiting dense embeddings from legal-distance (only 3/26 years complete: 2000-2002, ~19k decisions, 11% corpus coverage).

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k (COMPLETE)

**Frozen harness**: v3, config hash `4323f833fa72366a`, seed=42  
**Adversarial benchmarks**: EXACT k-NN on fixed stratified subsample (n=2000, seed=42) — HNSW artifact FIXED  
**Full-corpus benchmarks**: HNSW on subsamples (30k temporal, 15k hierarchy, full boilerplate)

### Results Summary (8 TF-IDF representations)

| Representation | Verdict | LangDom | LD-Pass | Jurist | JP-Pass | Both-Adv |
|----------------|---------|---------|---------|--------|---------|----------|
| cited_decisions_tfidf | PASS | 0.5295 | ✓ | 0.8020 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | PASS | 0.5164 | ✓ | 0.8055 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | PASS | 0.5238 | ✓ | 0.7975 | ✓ | ✓ |
| outcome_tfidf | PASS | 0.4527 | ✓ | 0.7255 | ✓ | ✓ |
| regeste_tfidf | PASS | 0.4835 | ✓ | 0.6090 | ✓ | ✓ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |
| full_text_tfidf_light | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |

**Key Finding**: No TF-IDF representation passes all 12 benchmarks. Fundamental tradeoff persists:
- **Citation-based** (cited_decisions_tfidf, hybrids): Pass adversarial (lang_dom ~0.45-0.53, jurist_pref ~0.72-0.80) via EXACT k-NN; pass cross_language_retrieval_full via HNSW; **FAIL** zero_shot_cross_language_transfer (NMI ~0.03-0.09), language_specific_representation_quality (NMI ~0.09-0.13), temporal_stability (std ~0.39), hierarchy_coherence (level_1_nmi ~0.06-0.09), cluster_coherence (branch_purity ~0.37-0.41), boilerplate_resistance
- **Text-based** (full_text_tfidf_light, regeste hybrids): Pass zero_shot_cross_language_transfer (NMI ~0.21), language_specific_representation_quality (NMI ~0.51), cluster_coherence (branch_purity ~0.74), temporal_stability (mean overlap ~0.78); **FAIL** adversarial_falsification (lang_dom=1.0, jurist_pref=0.0) via EXACT k-NN and cross_language_retrieval (recall@10=0.0)

**Production default** (cited_outcome_hybrid_0.5): PASS adversarial, PASS cross_language_retrieval_full, FAIL all hierarchy/temporal/boilerplate benchmarks.

---

## Sub-Question 2: Citation Heritage at 174k (COMPLETE)

**Frozen pair pool**: 137,314 positive + 137,314 negative pairs (seed=42)  
**Citation resolution**: 2,019/2,105 (95.9%) resolved; 924 map to 174k corpus decisions  
**Method**: HNSW via scalable_nn on full 174k corpus (HNSW artifact fix applies ONLY to adversarial benchmarks)

### AUC-ROC Results (CORRECTED per audit CYCLE_36242734524)

| Representation | AUC-ROC | positive_recall@10 | Status |
|----------------|---------|-------------------|--------|
| full_text_tfidf_light | 0.8969 | 0.0529 | PASS |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | PASS |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | PASS |
| cited_decisions_tfidf | 0.7892 | 0.0480 | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7749 | 0.0490 | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7589 | 0.0500 | PASS |
| outcome_tfidf | 0.6575 | 0.0000 | PASS (barely) |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |

**Key Finding**: AUC ranges 0.66-0.90 (CORRECTED from fabricated 0.72-0.97). **Positive recall@10 ranges 0.00-0.053 (CORRECTED from fabricated 0.44-0.49)**. nn_citation_rate@10 (fraction of top-10 neighbors that are actual cited decisions) is ~0.03-0.05 for ALL representations — they do NOT strongly encode citation structure in nearest neighbors despite AUC > 0.65. Text-based representations achieve higher AUC (0.85-0.90) than citation-based (0.76-0.79) but ALL have very low positive recall@10 (3-5%).

---

## Sub-Question 3: v17b Label Normalization at 174k (COMPLETE)

**Label stats**: 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions  
**Uniformity rule**: >10% no-worsening on ALL hierarchy-family metrics (including NMI)

### Results

| Representation | hierarchy_purity | hierarchy_nmi | zoom_coarse | zoom_fine | legal_area_purity | legal_area_nmi | Uniform PASS? |
|----------------|------------------|---------------|-------------|-----------|-------------------|----------------|---------------|
| cited_decisions_tfidf | 1.48 | 0.95 | 1.59 | 1.50 | 1.26 | 0.83 | ✗ (nmi<0.9) |
| cited_outcome_hybrid_0.5 | 1.43 | 0.85 | 1.51 | 1.50 | 1.26 | 0.73 | ✗ |
| cited_outcome_hybrid_0.7 | 1.44 | 1.06 | 1.53 | 1.47 | 1.29 | 0.79 | ✗ |
| full_text_tfidf_light | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ✗ |
| outcome_tfidf | 1.50 | 0.88 | 1.51 | 1.50 | 1.50 | 0.88 | ✗ |
| regeste_tfidf | 1.67 | null | 1.67 | 1.67 | 1.67 | null | ✗ |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ✗ |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ✗ |

**Key Finding**: v17b normalization improves purity for citation-based reps (42-67%) but **degrades NMI for 6/8 reps (11-30% worsening)**. Text-based reps show **ZERO purity improvement (ratios=1.00) and severe NMI degradation (-24% to -30%)**. Only **2/8 reps** (cited_decisions_tfidf, regeste_tfidf) satisfy frozen uniformity rule on purity metrics, but **NONE satisfy it on ALL metrics including NMI**. Best normalized hierarchy_purity=0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## HNSW Adversarial Artifact — FIXED (Scope: Adversarial Benchmarks Only)

**Problem**: HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produced nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences.

**Evidence**: v3 harness (HNSW on full 174k): all 8 reps showed identical jurist_pairwise=0.122 and similar lang_dom ~0.606. Exact k-NN on fixed stratified subsample (n=2000, seed=42) from valid decisions (n=90,632): jurist_pairwise=0.71-0.80, lang_dom=0.43-0.53, differentiated across representations.

**Fix Applied**: Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch for **ADVERSARIAL BENCHMARKS ONLY** (adversarial_language_dominance, jurist_pairwise_preference); HNSW still used for citation_heritage, temporal_stability, hierarchy family on subsample, cross_language_retrieval_full, boilerplate — by design for full-corpus scale.

---

## Awaited Representations (Legal-Distance Dependency)

| Category | Representations | Status |
|----------|-----------------|--------|
| Dense embeddings (8) | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | **BLOCKED** — 3/26 years complete (2000-2002, 19,441 decisions) |
| Citation roles (3) | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | **BLOCKED** — requires dense embeddings |
| Linear hybrids (2) | linear_citation_concat, linear_hybrid05_concat | **BLOCKED** — requires dense embeddings |

**Root Cause**: Corpus artifact publication gap — year-split normalized files exist at `/tmp/lex_accepted/core/corpus/...` but legal-distance expects them at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths. Years 2003-2025 blocked pending resolution.

---

## Monitor Status

- **Active**: true
- **Check count**: 124
- **Last check**: 2026-09-26T14:48:30
- **Watching**: `/tmp/lex_accepted/legal-distance/legal_distance/results`
- **Infrastructure**: HNSW backend OPERATIONAL_ON_GITHUB_RUNNERS; scalable_nn OPERATIONAL_WITH_SKLEARN_FALLBACK; v25 formal suite OPERATIONAL; citation_heritage FROZEN_137314_PAIRS_READY; v17b_normalization OPERATIONAL

---

## Audit Corrections Applied (CYCLE_36242734524_GATE.json REVISE gate)

1. Corrected citation heritage AUC-ROC values to match actual computed results (0.789, 0.774, 0.758, 0.871, 0.850, 0.896, 0.657, 0.486)
2. Corrected positive_recall@10 (nn_citation_rate@10) values (actual ~0.03-0.05, not ~0.44-0.49)
3. Corrected formal suite pass/fail/skip/run_separately counts to match actual benchmark statuses
4. Clarified HNSW artifact fix scope: only adversarial benchmarks use exact k-NN; citation heritage, temporal_stability, hierarchy family, boilerplate still use HNSW by design

**Corrected report**: `reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926_CORRECTED.md`  
**Original report with fabrications**: `reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926.md`

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified for TF-IDF family. Fundamental tradeoffs established, negative results preserved. Monitor active; will evaluate dense representations autonomously as they land in accepted state. Jurist human study external dependency recorded (framework ready, requires 5-10 Swiss jurists).

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_results.json`
- `evaluation/run_174k_formal_suite.py` (frozen harness v3, HNSW artifact fix)
- `evaluation/validate_citation_heritage_174k.py`
- `evaluation/run_v17b_label_normalization_174k.py`
- `evaluation/monitor_and_evaluate_174k.py` (active monitor)
- `evaluation/state/monitor_174k_state.json`
- `reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926_CORRECTED.md`