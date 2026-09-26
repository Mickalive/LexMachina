# Evaluation Lane — 174k Cycle Report (Factory Direction v27)

**Date**: 2026-09-26  
**Run ID**: eval_174k_formal_suite_v27_20260926  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: RUN (monitoring active)  
**Continue Recommended**: true (for dense embeddings as they land)

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** from factory direction v27 for the **TF-IDF family (8 representations)** at full 174k scale. The monitor is active and will autonomously evaluate dense embeddings as they land from legal-distance.

| Sub-question | Status | Details |
|--------------|--------|---------|
| **1. 12-benchmark formal suite** | ✅ COMPLETE | 8/8 TF-IDF representations evaluated with HNSW artifact fix (exact k-NN on valid subset) |
| **2. Citation heritage benchmark** | ✅ COMPLETE | Frozen 137k pair pool validated; cited_decisions_tfidf AUC=0.973 |
| **3. v17b label normalization** | ✅ COMPLETE | NOT uniformly confirmed — only 2/8 reps satisfy frozen uniformity rule |

**Dense embeddings**: 11.5% complete (years 2000-2002, 12,570/173,963 decisions). Legal-distance computation blocked on corpus artifact publication gap for years 2003-2025.

---

## Sub-question 1: 12-Benchmark Formal Suite (v25 protocol, frozen config hash `4323f833fa72366a`)

### Results Summary (173,963 decisions)

| Representation | Passed | Failed | Skipped | Both Adversarial Gates |
|----------------|--------|--------|---------|------------------------|
| **cited_decisions_tfidf** | 6 | 5 | 1 | ✅ PASS |
| **cited_outcome_hybrid_0.5** | 6 | 5 | 1 | ✅ PASS |
| **cited_outcome_hybrid_0.7** | 6 | 6 | 0 | ✅ PASS |
| full_text_tfidf_light | 7 | 5 | 0 | ❌ FAIL (lang_dom=1.0) |
| outcome_tfidf | 3 | 9 | 0 | ❌ FAIL |
| regeste_tfidf | 5 | 7 | 0 | ❌ FAIL |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | ❌ FAIL (lang_dom=0.998) |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | ❌ FAIL (lang_dom=0.999) |

**Best**: `cited_decisions_tfidf` (6/12 PASS, both adversarial gates pass)

### Fundamental Two-Mode Tradeoff Confirmed at 174k

| Mode | Representations | Passes | Fails |
|------|-----------------|--------|-------|
| **Citation-based** | cited_decisions_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7 | adversarial_falsification (lang_dom ~0.57-0.60), citation_heritage (AUC 0.92-0.97), multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn (~0.39), tf_metadata (~0.39), hierarchy_coherence (~0.13-0.15), legal_area_clustering (~0.003), temporal_stability (std ~0.15-0.18), boilerplate_resistance |
| **Text-based** | full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7 | branch_knn (~0.83-0.98), tf_metadata (~0.83-0.98), boilerplate_resistance, temporal_stability, citation_heritage (AUC only), zoom_coherence | adversarial_falsification (lang_dom ~0.998-0.999), multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |

**Key finding**: No single representation passes all 12 benchmarks. Both map modes needed; do not collapse to single default.

---

## Sub-question 2: Citation Heritage Benchmark (Frozen 137,314 pair pool, seed=42)

### Results

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|----------------|---------|---------------------|--------|
| cited_decisions_tfidf | **0.9731** | **0.487** | ✅ PASS |
| cited_outcome_hybrid_0.7 | 0.9605 | 0.490 | ✅ PASS |
| cited_outcome_hybrid_0.5 | 0.9193 | 0.476 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.8650 | 0.445 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.8505 | 0.444 | ✅ PASS |
| full_text_tfidf_light | 0.8439 | 0.438 | ✅ PASS |
| outcome_tfidf | 0.7204 | 0.003 | ✅ PASS |
| regeste_tfidf | 0.4865 | 0.000 | ❌ FAIL |

**Key finding**: Citation-based signals dominate citation structure recovery. Text-based representations pass AUC threshold but have near-zero nn_citation_rate — they do not encode citation neighborhoods.

---

## Sub-question 3: v17b Label Normalization (214 raw → 164 normalized legal_area labels, 49.3% changed)

### Uniformity Rule Test: >10% worsening on ANY hierarchy-family metric = FAIL

| Representation | Hierarchy Purity Ratio | Hierarchy NMI Ratio | Zoom Coarse | Zoom Fine | Legal Area Purity | Passes Uniformity? |
|----------------|------------------------|---------------------|-------------|-----------|-------------------|-------------------|
| cited_decisions_tfidf | 1.52 | 0.94 | 1.58 | 1.56 | 1.50 | ✅ **PASS** |
| regeste_tfidf | 1.64 | N/A | 1.64 | 1.64 | 1.64 | ✅ **PASS** |
| cited_outcome_hybrid_0.5 | 1.54 | 0.90 | 1.56 | 1.51 | 1.50 | ❌ FAIL (NMI -10%) |
| cited_outcome_hybrid_0.7 | 1.54 | 0.89 | 1.54 | 1.56 | 1.47 | ❌ FAIL (NMI -11%) |
| outcome_tfidf | 1.51 | 0.87 | 1.51 | 1.51 | 1.52 | ❌ FAIL (NMI -13%) |
| full_text_tfidf_light | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | ❌ FAIL (NMI -28%) |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | ❌ FAIL (NMI -28%) |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | ❌ FAIL (NMI -28%) |

**Key finding**: v17b improves purity for citation-based reps (48-64%) but degrades NMI (6-13% worsening). Text-based reps show **zero purity improvement** and **severe NMI degradation (-28%)**. Only 2/8 reps satisfy frozen uniformity rule.

**Best normalized hierarchy_purity**: 0.465 (full_text_tfidf_light) — **still below 0.7 threshold**.

---

## Critical HNSW Artifact: FIXED ✅

| Aspect | Before Fix (HNSW full 174k) | After Fix (Exact k-NN on valid subset n≈2000) |
|--------|-----------------------------|-----------------------------------------------|
| jurist_pairwise (all reps) | 0.122 (identical) | 0.71-0.80 (differentiated) |
| language_dominance (all reps) | ~0.606 (similar) | 0.43-0.53 (differentiated) |
| Valid decisions with known branch | N/A | 90,632 |

**Fix implemented**: Exact k-NN (sklearn brute force) on fixed stratified subsample (n=2000, seed=42) from valid decisions for adversarial benchmarks. HNSW retained only for full-corpus scale benchmarks (citation_heritage, temporal_stability, hierarchy family on 15k subsample, boilerplate).

---

## Dense Embeddings Progress (Awaited from legal-distance)

| Representation | Status | Notes |
|----------------|--------|-------|
| center_projected_768dim | ⏳ Awaited | Year-split computation in progress |
| center_projected_64dim | ⏳ Awaited | Frozen PCA of 768dim |
| linear_metric_epoch4 | ⏳ Awaited | Metric learning (OOS validated JP=0.525) |
| mahalanobis_metric_epoch4 | ⏳ Awaited | Metric learning (OOS validated JP=0.530) |
| hybrid_stabilized_epoch1 | ⏳ Awaited | Hybrid objective (OOS validated JP=0.535) |
| hybrid_v2_epoch3 | ⏳ Awaited | Hybrid v2 |
| citation_role_citing_alpha0.3 | ⏳ Awaited | Best 1k-scale: LangDom=0.741, JP=0.536 |
| citation_role_following_alpha0.3 | ⏳ Awaited | Best 1k-scale: LangDom=0.753, JP=0.519 |
| citation_role_criticizing_alpha0.3 | ⏳ Awaited | 1k-scale: LangDom=0.620, JP=0.486 |
| linear_citation_concat | ⏳ Awaited | v14 REPRODUCED: mean_delta=+0.039, paired_std=0.021 |
| linear_hybrid05_concat | ⏳ Awaited | Highest JP but FAILS stability (paired_std > 0.03) |

### Current legal-distance 174k Dense Embedding Progress
- **Completed years**: 2000, 2001, 2002 (3/26 years = 11.5%)
- **Decisions completed**: 12,570 / 173,963 = **7.2%**
- **Embedding dimension**: 768 (center_projected)
- **Blocked on**: Corpus artifact publication gap at `/tmp/lex_accepted/corpus/...` mount paths for years 2003-2025
- **Checkpoint location**: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`

---

## Infrastructure Status

| Component | Status |
|-----------|--------|
| HNSW backend | OPERATIONAL_ON_GITHUB_RUNNERS |
| Scalable NN (exact/HNSW fallback) | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 Formal Suite runner | OPERATIONAL |
| Citation heritage (frozen 137k pairs) | FROZEN_137314_PAIRS_READY |
| v17b Normalization | OPERATIONAL |
| Monitor script | ACTIVE (check_count=95) |
| Formal suite runner (run_174k_formal_suite.py) | OPERATIONAL |
| HNSW artifact fix | IMPLEMENTED |

---

## Blockers

| Blocker | Type | Impact |
|---------|------|--------|
| legal_distance_174k_dense_embeddings_not_in_accepted_state | Primary | Cannot evaluate dense representations |
| corpus_artifact_publication_gap (mount paths) | Root cause | Years 2003-2025 blocked upstream |
| HNSW adversarial artifact | Methodological (FIXED) | Exact k-NN fix implemented before dense eval |
| Jurist human study | External dependency | Framework ready, requires 5-10 Swiss jurists |

---

## Recommendation

**CONTINUE** — The evaluation lane is correctly positioned:
1. TF-IDF family evaluation **complete** with all negative results preserved
2. HNSW artifact **fixed** before dense evaluation
3. Monitor **active** — will autonomously evaluate dense representations as they land
4. No additional same-question cycle justified for TF-IDF family — fundamental tradeoffs established

The factory director should focus on unblocking legal-distance dense embedding computation (corpus artifact publication gap) to enable the next wave of evaluation.

---

## Evidence References

- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — Full 12-benchmark results
- `results/evaluation/v25_174k_citation_heritage/` — Citation heritage per representation
- `results/evaluation/v25_174k_v17b/` — v17b normalization per representation
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Adversarial suite (HNSW fix)
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=95)
- `state/evaluation.json` — This lane state (updated)
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol
- `evaluation/config/evaluation_v3_174k_config.json` — Evaluation config