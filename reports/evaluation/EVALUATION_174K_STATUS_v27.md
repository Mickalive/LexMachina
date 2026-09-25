# Evaluation Lane Status Report — Factory Direction v27
**Date:** 2026-09-25  
**Run ID:** eval_174k_formal_suite_v27_20260925  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** RUN  
**Continue Recommended:** true

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** of factory direction v27 for the **TF-IDF family (8 representations)** at full 174k corpus scale (173,963 decisions). The dense embeddings from legal-distance lane are **36% complete (years 2000-2010)** but blocked on a corpus artifact publication gap. The HNSW adversarial artifact that masked true representation differences has been **FIXED** (exact k-NN on stratified subsample for adversarial benchmarks).

**Monitoring is ACTIVE** — the evaluation lane will autonomously run the formal suite on dense embeddings, citation roles, and linear hybrids as they land in accepted state.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k Scale — COMPLETE

### Protocol
- **Frozen config hash:** `4323f833fa72366a` (v16 thresholds unchanged)
- **Sample:** 173,963 decisions (frozen metadata from pinned parquet)
- **NN backend:** HNSW for full-corpus benchmarks; **exact k-NN on fixed stratified subsample (n=2000, seed=42)** for adversarial benchmarks (language_dominance, jurist_pairwise, cross-language, jurist_usability)
- **12 benchmarks with frozen thresholds:**
  1. citation_heritage (AUC ≥ 0.65)
  2. branch_knn (knn@5 ≥ 0.6333)
  3. tf_metadata_human_indexing (recall@5 ≥ 0.8)
  4. adversarial_falsification (lang_dom ≤ 0.85, branch_coherence ≥ 0.3)
  5. boilerplate_resistance_real_corpus (corr ≥ 0.1)
  6. multilingual_invariance (separation ≥ 0, invariance_gap ≤ 0.2)
  7. cross_language_pairs (separation ≥ 0)
  8. collapse_check (mean_sim ≤ 0.99, std_sim ≥ 0.01)
  9. temporal_stability (std ≤ 0.1)
  10. hierarchy_coherence (purity ≥ 0.7, NMI ≥ 0.3)
  11. zoom_coherence (improvement > 0)
  12. legal_area_clustering (purity ≥ 0.5)

### Results Summary (8 TF-IDF representations)

| Representation | Passed | Failed | Skipped | Key Findings |
|---|---:|---:|---:|---|
| **cited_decisions_tfidf** | 6 | 5 | 1 | **BEST** — citation_heritage AUC 0.973, passes adversarial, multilingual, cross_lang, collapse, zoom |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | Production default; strong citation signal |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | Best fractal quality; slightly weaker citation_heritage |
| full_text_tfidf_light | 7 | 5 | 0 | **FAILS** adversarial (lang_dom=0.999), multilingual, cross_lang |
| outcome_tfidf | 3 | 9 | 0 | Weak across most benchmarks |
| regeste_tfidf | 5 | 7 | 0 | **FAILS** citation_heritage (AUC 0.486) |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | **FAILS** adversarial (lang_dom=0.998) |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | **FAILS** adversarial (lang_dom=0.999) |

**Key Finding:** No TF-IDF representation passes all 12 benchmarks at 174k. The **fundamental two-mode tradeoff persists**:
- **Citation-based** (cited_decisions_tfidf, hybrids): Pass adversarial_falsification (lang_dom ~0.57-0.60), citation_heritage (AUC 0.92-0.97), multilingual/cross_lang — but FAIL branch_knn (~0.39), tf_metadata (~0.39), hierarchy_coherence (~0.13-0.15), legal_area_clustering (~0.003), temporal_stability (std ~0.15-0.18)
- **Text-based** (full_text_tfidf_light, regeste hybrids): Pass branch_knn (~0.83-0.98), tf_metadata (~0.83-0.98), boilerplate, temporal_stability — but FAIL adversarial_falsification (lang_dom ~0.998-0.999), multilingual, cross_lang
- **ALL fail** hierarchy_coherence (max purity 0.465 vs 0.7 threshold) and legal_area_clustering (max ~0.08 vs 0.5 threshold) — fundamental granularity/coverage limits

---

## Sub-Question 2: Citation Heritage Benchmark — COMPLETE

### Protocol
- **Pair pool:** 137,314 positive + 137,314 negative (frozen, seed=42)
- **Built from:** Published 174k citation-ID resolution (2,019/2,105 = 95.9% resolved; 924 mapping to 174k corpus decisions)
- **Threshold:** AUC-ROC ≥ 0.65

### Results

| Representation | AUC-ROC | NN Citation Rate@10 | Status |
|---|---:|---:|:---|
| cited_decisions_tfidf | **0.973** | 0.487 | ✅ PASS |
| cited_outcome_hybrid_0.7 | 0.960 | 0.490 | ✅ PASS |
| cited_outcome_hybrid_0.5 | 0.919 | 0.476 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.850 | 0.444 | ✅ PASS |
| full_text_tfidf_light | 0.844 | 0.438 | ✅ PASS |
| outcome_tfidf | 0.720 | 0.003 | ✅ PASS |
| regeste_tfidf | 0.486 | 0.000 | ❌ FAIL |

**Key Finding:** Citation-based signals **dominate** citation_heritage recovery. `cited_decisions_tfidf` achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions in top-10 neighbors. Text-based representations pass AUC threshold but have **near-zero nn_citation_rate** — they do not encode citation structure.

---

## Sub-Question 3: v17b Label Normalization Generalization — COMPLETE

### Protocol
- **Mapping:** Conservative cross-lingual canonical map (frozen from v17b)
- **Comparison:** Raw vs normalized legal_area on hierarchy_coherence + zoom_coherence + legal_area_clustering
- **Success rule:** No representation worsens by >10% on any hierarchy-family metric at 174k (mirrors v17b 1200-scale uniformity rule)

### Results

| Representation | Hierarchy Purity | Hierarchy NMI | Zoom Coarse | Zoom Fine | Legal Area Purity | Legal Area NMI | Passes Uniformity? |
|---|---:|---:|---:|---:|---:|---:|:---|
| **cited_decisions_tfidf** | **1.52** | **0.94** | **1.57** | **1.56** | **1.49** | **0.92** | ✅ YES |
| cited_outcome_hybrid_0.5 | 1.53 | 0.90 | 1.56 | 1.51 | 1.50 | 0.86 | ❌ NO (NMI -10%) |
| cited_outcome_hybrid_0.7 | 1.54 | 0.89 | 1.54 | 1.56 | 1.47 | 0.89 | ❌ NO (NMI -11%) |
| full_text_tfidf_light | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | 0.76 | ❌ NO (NMI -28%) |
| outcome_tfidf | 1.51 | 0.87 | 1.51 | 1.51 | 1.51 | 0.87 | ❌ NO (NMI -13%) |
| **regeste_tfidf** | **1.64** | **1.00** | **1.64** | **1.64** | **1.64** | **1.00** | ✅ YES |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | 0.76 | ❌ NO (NMI -28%) |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | 0.76 | ❌ NO (NMI -28%) |

**Key Finding:** v17b normalization **improves purity for citation-based reps (42-64%)** but **degrades NMI for 6/8 reps (11-28% worsening)**. Text-based reps show **ZERO purity improvement (ratios=1.00)** and severe NMI degradation (-24% to -28%). Only **2/8 reps satisfy frozen uniformity rule**. Best normalized hierarchy_purity=0.465 < 0.7 threshold — **fundamental granularity/coverage limits persist at 174k**.

---

## Critical HNSW Artifact — FIXED

**Problem:** HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produced nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

**Evidence:**
- v3 harness (HNSW on full 174k): All 8 reps showed identical jurist_pairwise=0.122 and similar lang_dom ~0.606
- Exact k-NN on fixed stratified subsample (n=2000, seed=42) from valid decisions (n=90,632): jurist_pairwise=0.71-0.80, lang_dom=0.43-0.53, **differentiated across representations**

**Impact:** Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was **HNSW artifact, NOT representation failure**. Fixed before dense 174k evaluation.

**Implemented Fix:** Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch for adversarial benchmarks; HNSW reserved for full-corpus scale benchmarks (citation_heritage on 137k pairs, temporal_stability on 30k subsample, hierarchy family on 15k stratified subsample, boilerplate on full corpus).

---

## Awaited Representations (from legal-distance lane)

### Dense Embeddings (36% complete — years 2000-2010)
| Representation | Status | Notes |
|---|---|---|
| center_projected_768dim | AWAITED | Baseline reference |
| center_projected_64dim | AWAITED | Production default (64-dim frozen PCA) |
| linear_metric_epoch4 | AWAITED | Best holdout JP (0.605), HIGH-PURITY |
| mahalanobis_metric_epoch4 | AWAITED | Balanced holdout (JP=0.585, LD=0.581), HIGH-PURITY |
| hybrid_stabilized_epoch1 | AWAITED | Best cite-indep (36.95%), hierarchy loss +0.030 JP |
| hybrid_v2_epoch3 | AWAITED | Earlier hybrid objective |

### Citation Role Embeddings
- citation_role_citing_alpha0.3 (ZQ=0.5401 at 1000-scale)
- citation_role_following_alpha0.3 (ZQ=0.5280 at 1000-scale)
- citation_role_criticizing_alpha0.3 (ZQ=0.4864 at 1000-scale)

### Linear Hybrid Combinations
- linear_citation_concat (REPRODUCED: mean_delta=+0.0392, paired_std=0.0212 — PASSES frozen success rule)
- linear_hybrid05_concat (HIGHEST JP=0.7925 but FAILS stability, paired_std=0.042)

---

## Monitor Status

| Component | Status |
|---|---|
| Monitor script | ACTIVE (check_count=68, last_check=2026-09-25T21:30:00) |
| HNSW backend | OPERATIONAL_ON_GITHUB_RUNNERS |
| Scalable NN (sklearn fallback) | OPERATIONAL |
| v25 formal suite runner | OPERATIONAL |
| Citation heritage pair pool | FROZEN_137314_PAIRS_READY |
| v17b normalization | OPERATIONAL |
| HNSW artifact fix | IMPLEMENTED (exact k-NN on valid subset) |

**Completed evaluations tracked:** All 8 TF-IDF representations (v25_formal_suite, citation_heritage, v17b all ✅)

**Dense embeddings progress:** 11/27 years complete (2000-2010), **36%**, blocked on corpus artifact publication gap.

---

## Blockers

| Blocker | Details |
|---|---|
| **Primary** | legal_distance_174k_dense_embeddings not in accepted state |
| **Root Cause** | Corpus artifact publication gap: year-split normalized files and metadata_174k.jsonl exist in corpus workspace but NOT at /tmp/lex_accepted/corpus/... and /tmp/lex_accepted/evaluation/... mount paths where legal-distance expects them |
| **Legal-distance Status** | Years 2000-2010 complete; years 2011-2025 blocked missing upstream data |
| **Methodological** | HNSW adversarial artifact requires exact k-NN fix (IMPLEMENTED) |
| **External** | Jurist human study: requires 5-10 Swiss jurists (framework ready, non-blocking) |

---

## Next Actions

1. **Monitor** legal-distance accepted state for dense embeddings landing (years 2011+)
2. **Auto-evaluate** each dense representation as it appears using the frozen v25 formal suite
3. **Report** dense embedding results incrementally
4. **Jurist human study** framework ready — report as blocked when recruitment reaches threshold

---

## Evidence References

- `reports/evaluation/EVALUATION_174K_HNSW_FIX_REPORT_v27.md` — HNSW artifact analysis and fix
- `reports/evaluation/EVALUATION_174K_FORMAL_SUITE_v27.md` — Full formal suite results
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol specification
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen citation pair pool
- `evaluation/data/174k/metadata_174k.json` — Frozen evaluation metadata (173,963 decisions)
- `state/evaluation.json` — Machine-readable lane state

---

**Conclusion:** The evaluation lane has **delivered on all three machine-executable sub-questions for the TF-IDF family at 174k scale**. The fundamental two-mode tradeoff is confirmed, the HNSW artifact is fixed, and the monitoring infrastructure is operational and ready for dense embeddings. No same-question cycles justified for TF-IDF family; evaluation lane correctly continues in RUN state to absorb dense representations as they land.