# Evaluation Lane - 174k Monitor Cycle Report (Factory Direction v28)
**Date:** 2026-09-26  
**Run ID:** `eval_174k_monitor_v28_20260926`  
**Lane:** evaluation  
**Direction Version:** 28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false (for TF-IDF family question)

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF family at 174k scale per factory direction v28. The autonomous monitor (check_count=130) is active and watching for dense embeddings, citation role embeddings, and linear hybrid embeddings from the legal-distance lane. **No new awaited representations were detected** in this cycle.

### TF-IDF Family (8 representations) — COMPLETE ✓
| Sub-question | Status | Key Finding |
|--------------|--------|-------------|
| 12-benchmark formal suite (HNSW artifact fixed) | COMPLETE | Fundamental two-mode tradeoff persists: citation-based pass adversarial, fail hierarchy; text-based pass hierarchy, fail adversarial |
| Citation heritage (137,314 frozen pairs, 95.9% citation resolution) | COMPLETE | AUC 0.66-0.90, but positive_recall@10 only 3-5% for ALL reps — citation structure weakly encoded in NN |
| v17b label normalization generalization | COMPLETE | NOT uniformly confirmed: only 2/8 reps satisfy >10% no-worsening rule on ALL hierarchy metrics |

### Awaited Representations — BLOCKED ON DEPENDENCIES
| Category | Representations | Progress |
|----------|-----------------|----------|
| Dense embeddings (center_projected, metric learning, hybrid) | 8 | 3/26 years complete (2000-2002, ~19,441 decisions, 11.5%) |
| Citation role embeddings (citing, following, criticizing α=0.3) | 3 | 0% — awaited from legal-distance |
| Linear hybrids (linear_citation_concat, linear_hybrid05_concat) | 2 | 0% — awaited from legal-distance |

**Primary Blocker:** Corpus artifact publication gap — year-split normalized files exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them. Years 2003-2025 blocked.

**Methodological Blocker (RESOLVED):** HNSW adversarial artifact fixed — exact k-NN on fixed stratified subsample (n=2000, seed=42) now used for adversarial benchmarks only.

**External Dependency:** Jurist human study (framework ready, requires 5-10 Swiss jurists).

---

## Detailed Sub-question Results

### Sub-question 1: 12-Benchmark Formal Suite at 174k (HNSW Artifact Fixed)

**Configuration:** Frozen harness v3, config hash `4323f833fa72366a`, global seed 42  
**Adversarial Benchmarks:** Exact k-NN on fixed stratified subsample (n=2000 from 90,632 valid decisions)  
**Full-corpus Benchmarks:** HNSW via scalable_nn on subsamples (citation_heritage, temporal_stability, hierarchy family, cross_language_retrieval_full, boilerplate)

**Results Summary (8 representations):**

| Representation | Verdict | Adversarial (Both Pass) | Key Passes | Key Fails |
|----------------|---------|------------------------|------------|-----------|
| cited_decisions_tfidf | FAIL | ✓ (lang_dom=0.43, jurist=0.73) | adversarial_language_dominance, jurist_pairwise_preference, cross_language_retrieval, cross_language_retrieval_full | zero_shot_cross_language_transfer, language_specific_representation_quality, temporal_stability, hierarchy_coherence, cluster_coherence, boilerplate_resistance |
| cited_outcome_hybrid_0.5 | FAIL | ✓ (lang_dom=0.45, jurist=0.75) | Same as cited_decisions_tfidf | Same as cited_decisions_tfidf |
| cited_outcome_hybrid_0.7 | FAIL | ✓ (lang_dom=0.47, jurist=0.77) | Same as cited_decisions_tfidf | Same as cited_decisions_tfidf |
| full_text_tfidf_light | FAIL | ✗ (lang_dom=1.0, jurist=0.0) | zero_shot_cross_language_transfer, language_specific_representation_quality, cluster_coherence, temporal_stability | adversarial_falsification, jurist_pairwise_preference, cross_language_retrieval, hierarchy_coherence, cross_language_retrieval_full, boilerplate_resistance |
| outcome_tfidf | FAIL | ✗ (lang_dom=0.99, jurist=0.02) | — | All except citation_heritage (barely) |
| regeste_tfidf | FAIL | ✗ (lang_dom=1.0, jurist=0.0) | — | All except citation_heritage (FAIL) |
| regeste_full_text_hybrid_0.5 | FAIL | ✗ (lang_dom=1.0, jurist=0.0) | Same as full_text_tfidf_light | Same as full_text_tfidf_light |
| regeste_full_text_hybrid_0.7 | FAIL | ✗ (lang_dom=1.0, jurist=0.0) | Same as full_text_tfidf_light | Same as full_text_tfidf_light |

**Key Finding:** No TF-IDF representation passes all benchmarks at 174k. The fundamental two-mode tradeoff is confirmed:
- **Citation-based** (cited_decisions_tfidf, hybrids): Pass adversarial gates via EXACT k-NN (lang_dom ~0.43-0.53, jurist_pref ~0.72-0.80), pass cross_language_retrieval_full via HNSW, but FAIL zero_shot_cross_language_transfer (NMI ~0.03-0.06), language_specific_representation_quality (NMI ~0.09-0.13), temporal_stability (std ~0.39), hierarchy_coherence (level_1_nmi ~0.06-0.09), cluster_coherence (branch_purity ~0.37-0.41), boilerplate_resistance.
- **Text-based** (full_text_tfidf_light, regeste hybrids): Pass zero_shot_cross_language_transfer (NMI ~0.21), language_specific_representation_quality (NMI ~0.51), cluster_coherence (branch_purity ~0.74), temporal_stability (mean overlap ~0.78) but FAIL adversarial_falsification (lang_dom=1.0, jurist_pref=0.0) via EXACT k-NN and cross_language_retrieval (recall@10=0.0).
- **ALL fail hierarchy_coherence** (max level_1_nmi 0.56).

---

### Sub-question 2: Citation Heritage Benchmark (Frozen 137,314 Pair Pool)

**Pair Pool:** 137,314 positive + 137,314 negative (frozen, seed=42)  
**Citation Resolution:** 2,019/2,105 (95.9%) resolved; 924 mapping to 174k corpus decisions  
**Method:** HNSW via scalable_nn on full 174k corpus (artifact fix NOT applied — by design for full-corpus scale)

**Results (CORRECTED per audit CYCLE_36242734524):**

| Representation | AUC-ROC | positive_recall@10 | Status |
|----------------|---------|-------------------|--------|
| cited_decisions_tfidf | 0.7892 | 0.0480 | PASS |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.0490 | PASS |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.0500 | PASS |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | PASS |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | PASS |
| full_text_tfidf_light | 0.8969 | 0.0529 | PASS |
| outcome_tfidf | 0.6575 | 0.0000 | PASS (barely) |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |

**Key Finding:** Citation heritage AUC ranges 0.66-0.90 (CORRECTED from fabricated 0.72-0.97). Positive recall@10 ranges 0.00-0.053 (CORRECTED from fabricated 0.44-0.49). Text-based representations achieve higher AUC (0.85-0.90) than citation-based (0.76-0.79) but **ALL have very low positive recall@10 (3-5%)**. nn_citation_rate@10 (fraction of top-10 neighbors that are actual cited decisions) is ~0.03-0.05 for all representations — they do not strongly encode citation structure in nearest neighbors despite AUC > 0.65. Original claim of 'cited_decisions_tfidf achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions' was a FABRICATION identified in audit.

---

### Sub-question 3: v17b Label Normalization Generalization to 174k

**Label Stats:** 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions  
**Uniformity Rule (frozen):** >10% no-worsening on ALL hierarchy-family metrics including NMI

**Results:**

| Representation | Uniformity | hierarchy_purity | hierarchy_nmi | zoom_coarse | zoom_fine | legal_area_purity | legal_area_nmi |
|----------------|------------|------------------|---------------|-------------|-----------|-------------------|----------------|
| cited_decisions_tfidf | ✓ PASS | 1.48 | 0.95 | 1.59 | 1.50 | 1.26 | 0.83 |
| regeste_tfidf | ✓ PASS | 1.67 | null | 1.67 | 1.67 | 1.67 | null |
| cited_outcome_hybrid_0.5 | ✗ FAIL | 1.43 | 0.85 | 1.51 | 1.50 | 1.26 | 0.73 |
| cited_outcome_hybrid_0.7 | ✗ FAIL | 1.44 | 1.06 | 1.53 | 1.47 | 1.29 | 0.79 |
| full_text_tfidf_light | ✗ FAIL | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 |
| outcome_tfidf | ✗ FAIL | 1.50 | 0.88 | 1.51 | 1.50 | 1.50 | 0.88 |
| regeste_full_text_hybrid_0.5 | ✗ FAIL | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 |
| regeste_full_text_hybrid_0.7 | ✗ FAIL | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 |

**Key Finding:** v17b normalization improves purity for citation-based reps (42-67%) but degrades NMI for 6/8 reps (11-30% worsening). Text-based reps show ZERO purity improvement (ratios=1.00) and severe NMI degradation (-24% to -30%). Only 2/8 reps satisfy frozen uniformity rule. Best normalized hierarchy_purity=0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## Monitor Status

**Monitor Script:** `evaluation/monitor_and_evaluate_174k.py`  
**State File:** `evaluation/state/monitor_174k_state.json`  
**Check Count:** 130 (incremented from 124)  
**Last Check:** 2026-09-26T18:40:54.918078  
**Watching:** `/tmp/lex_accepted/legal-distance/legal_distance/results`

**Infrastructure Status:**
- HNSW backend: OPERATIONAL_ON_GITHUB_RUNNERS
- scalable_nn: OPERATIONAL_WITH_SKLEARN_FALLBACK
- v25 formal suite: OPERATIONAL
- Citation heritage: FROZEN_137314_PAIRS_READY
- v17b normalization: OPERATIONAL
- Monitor script: ACTIVE_WITH_FORMAL_SUITE_AND_ENHANCED_SCAN
- Formal suite runner: OPERATIONAL (NoneType.lower bug fixed)
- Monitor detection: CORRECT_PATHS_fractal_map_for_tfidf_legal_distance_for_dense

**HNSW Artifact:** CONFIRMED and FIXED for adversarial benchmarks
- HNSW on full 174k: all 8 reps show identical jurist_pairwise=0.122, lang_dom ~0.606
- Exact k-NN on valid subset (n=2000): jurist_pairwise=0.71-0.80, lang_dom=0.43-0.53, differentiated across reps
- Fix applied: Exact k-NN (sklearn brute force) on fixed stratified subsample for adversarial benchmarks ONLY

**Dense Embeddings Progress (from legal-distance):**
- Completed years: 2000, 2001, 2002 (3/26 = 11.5%)
- Decisions completed: 19,441 / 173,963 (11%)
- Blocked on: years 2003-2025 pending legal-distance year-split execution (corpus mount path issue)

**Scan Results (this cycle):**
- TF-IDF embeddings (8) detected in fractal-map mount: ✓ COMPLETE, already evaluated
- 174k_dense_embeddings root directory: Only checkpoints/ subdirectory exists (no final concatenated embeddings)
- Citation role 174k directories: Not found
- Linear hybrid 174k directories: Not found
- **No new awaited representations detected**

---

## Blockers

| Blocker | Type | Status | Resolution Path |
|---------|------|--------|-----------------|
| Corpus artifact publication gap | Operational/Environment | ACTIVE | Fix mount paths, create symlinks, or adjust legal-distance input paths to point to `/tmp/lex_accepted/core/corpus/...` |
| Legal-distance years 2003-2025 | Dependency | BLOCKED | Unblocked once corpus mount path resolved; legal-distance compute_174k_dense_embeddings.py will resume from year 2003 |
| Jurist human study | External | RECORDED | Framework ready; requires 5-10 Swiss jurists (non-blocking for machine evaluation) |

---

## Recommendation

**For TF-IDF family question:** No additional same-question cycle justified — fundamental tradeoffs established, negative results preserved, all three sub-questions complete. **continue_recommended = false**

**For dense embeddings/citation roles/linear hybrids:** Monitor remains ACTIVE. Will autonomously evaluate as representations land in accepted state (final concatenated embeddings in 174k_dense_embeddings root directory, or citation role/linear hybrid directories in legal-distance results).

**Factory Director decision needed:** Successor question for evaluation lane once dense embeddings land at 174k scale. Candidate next questions:
1. Run full formal suite on dense embeddings at 174k (validate whether dense beats TF-IDF tradeoff)
2. Run formal suite on citation role embeddings at 174k (validate 1000-scale citation-role zoom quality generalizes)
3. Run formal suite on linear hybrids at 174k (validate v13/v14 REPRODUCED finding: linear_citation_concat breaks two-mode tradeoff)
4. Jurist human study execution

---

## Evidence Preservation

All raw outputs, negative results, and audit corrections preserved:
- Formal suite results: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage results: `evaluation/results/174k_citation_heritage/`
- v17b normalization results: `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_results.json`
- Audit correction: `reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926_CORRECTED.md`
- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=130)

---

## Next Actions (Autonomous)

1. Monitor continues periodic scans (via scheduled workflow or manual trigger)
2. When legal-distance publishes final 174k dense embeddings (concatenated .npy files in 174k_dense_embeddings root), monitor will detect and run full formal suite
3. When citation role / linear hybrid 174k embeddings land, monitor will detect and evaluate
4. No manual intervention required unless monitor detects new representations