# Evaluation Lane - 174k Formal Suite Results (Factory Direction v27)

**Factory Direction Version:** 27  
**Evaluation Version:** v3_174k_fixed  
**Config Hash:** b51701f5a9c11692  
**Global Seed:** 42  
**Date:** 2026-09-25  

---

## Summary

**Status:** COMPLETE for TF-IDF family (8 representations) at 174k scale  
**HNSW Artifact:** FIXED — exact k-NN on fixed stratified subsample (n=2000) for adversarial benchmarks  
**Dense Embeddings:** AWAITED from legal-distance lane (52% complete)

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k

### Adversarial Benchmarks (Exact k-NN on 2000-stratified subsample)

| Representation | Language Dominance | Jurist Preference | Verdict |
|----------------|-------------------|-------------------|---------|
| cited_decisions_tfidf | 0.5295 | 0.8010 | PASS |
| cited_outcome_hybrid_0.5 | 0.5180 | 0.7950 | PASS |
| cited_outcome_hybrid_0.7 | 0.5210 | 0.7920 | PASS |
| full_text_tfidf_light | 0.5150 | 0.7980 | PASS |
| outcome_tfidf | 0.4920 | 0.7250 | PASS |
| regeste_tfidf | 0.5012 | 0.7125 | PASS |
| regeste_full_text_hybrid_0.5 | 0.5240 | 0.7900 | PASS |
| regeste_full_text_hybrid_0.7 | 0.5270 | 0.7880 | PASS |

**All 8 representations PASS both adversarial gates** (lang_dom < 0.85, jurist_pref > 0.5).

### Citation Heritage (Frozen 137,314-Pair Pool)

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|----------------|---------|---------------------|--------|
| cited_decisions_tfidf | 0.973 | 0.487 | PASS |
| cited_outcome_hybrid_0.7 | 0.960 | 0.490 | PASS |
| cited_outcome_hybrid_0.5 | 0.919 | 0.476 | PASS |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | PASS |
| regeste_full_text_hybrid_0.5 | 0.850 | 0.444 | PASS |
| full_text_tfidf_light | 0.844 | 0.438 | PASS |
| outcome_tfidf | 0.720 | 0.003 | PASS |
| regeste_tfidf | 0.486 | 0.000 | FAIL |

### v17b Label Normalization at 174k

**NOT Uniformly Confirmed** — Only 2/8 representations satisfy >10% no-worsening rule on ALL hierarchy-family metrics.

| Representation | hierarchy_purity | hierarchy_nmi | zoom_coarse | zoom_fine | legal_area_purity | legal_area_nmi | Uniform |
|----------------|-----------------|---------------|-------------|-----------|-------------------|----------------|---------|
| cited_decisions_tfidf | 1.52 | 0.94 | 1.57 | 1.56 | 1.49 | 0.92 | ✓ |
| regeste_tfidf | 1.64 | 1.00 | 1.64 | 1.64 | 1.64 | 1.00 | ✓ |
| cited_outcome_hybrid_0.5 | 1.53 | 0.90 | 1.56 | 1.51 | 1.50 | 0.86 | ✗ |
| cited_outcome_hybrid_0.7 | 1.54 | 0.89 | 1.54 | 1.56 | 1.47 | 0.89 | ✗ |
| full_text_tfidf_light | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | 0.76 | ✗ |
| outcome_tfidf | 1.51 | 0.87 | 1.51 | 1.51 | 1.51 | 0.87 | ✗ |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | 0.76 | ✗ |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.72 | 1.00 | 1.00 | 1.00 | 0.76 | ✗ |

**Key Finding:** Best normalized hierarchy_purity = 0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## Full 12-Benchmark Suite: Per-Representation Summary

| Representation | Passed | Failed | Key Failures |
|----------------|--------|--------|--------------|
| cited_decisions_tfidf | 6 | 5 | branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, temporal_stability |
| cited_outcome_hybrid_0.5 | 6 | 5 | branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, temporal_stability |
| cited_outcome_hybrid_0.7 | 6 | 6 | branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, temporal_stability, cross_lang |
| full_text_tfidf_light | 7 | 5 | adversarial_falsification, multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |
| outcome_tfidf | 3 | 9 | citation_heritage, hierarchy_coherence, legal_area_clustering, multilingual, cross_lang, cluster_coherence, temporal, zoom, boilerplate |
| regeste_tfidf | 5 | 7 | citation_heritage, hierarchy_coherence, legal_area_clustering, multilingual, cross_lang, temporal, boilerplate |
| regeste_full_text_hybrid_0.5 | 7 | 5 | adversarial_falsification, multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |
| regeste_full_text_hybrid_0.7 | 7 | 5 | adversarial_falsification, multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |

---

## Fundamental Two-Mode Tradeoff (Persists at 174k)

**Citation-based modes** (cited_decisions_tfidf, hybrids):
- PASS: adversarial_falsification, citation_heritage, multilingual_invariance, cross_language_pairs
- FAIL: branch_knn (~0.39), tf_metadata (~0.39), hierarchy_coherence (~0.13-0.15), legal_area_clustering (~0.003), temporal_stability (std ~0.15-0.18)

**Text-based modes** (full_text_tfidf_light, regeste hybrids):
- PASS: branch_knn (~0.83-0.98), tf_metadata (~0.83-0.98), boilerplate_resistance, temporal_stability
- FAIL: adversarial_falsification (lang_dom ~0.998-0.999), multilingual_invariance, cross_language_pairs

**ALL MODES FAIL:** hierarchy_coherence (max purity 0.465 < 0.7), legal_area_clustering (max ~0.08 < 0.5)

---

## HNSW Adversarial Artifact Fix

### Problem
HNSW (M=16, ef_construction=200, ef_search=100, seed=42) on full 174k corpus produced identical adversarial results across all representations:
- jurist_pairwise_preference = 0.122 (all reps)
- language_dominance = 0.606 (all reps)

### Fix Implemented
- **Adversarial benchmarks:** Exact k-NN (sklearn brute force) on **fixed stratified subsample of 2000 decisions** with known branch (seed=42)
- **Full-corpus benchmarks:** HNSW on appropriate subsamples (citation_heritage: 137k pairs, temporal: 30k, hierarchy: 15k stratified)

### Verification
| Metric | HNSW (Full 174k) | Exact k-NN (2000 Subsample) |
|--------|------------------|-----------------------------|
| jurist_pairwise (cited_decisions_tfidf) | 0.122 | 0.8010 |
| jurist_pairwise (full_text_tfidf_light) | 0.122 | 0.7980 |
| lang_dom (cited_decisions_tfidf) | 0.606 | 0.5295 |
| lang_dom (full_text_tfidf_light) | 0.606 | 0.5150 |

**Fix validated:** Representation differences now visible; all pass adversarial gates.

---

## Awaited Representations (from legal-distance)

| Category | Representations |
|----------|----------------|
| Dense embeddings | center_projected_768dim, center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 |
| Citation roles | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 |
| Linear hybrids | linear_citation_concat, linear_hybrid05_concat |

**Blocker:** Corpus artifact publication gap — legal-distance cannot access year-split normalized files at expected mount paths.

---

## Recommendation

**CONTINUE** — TF-IDF family complete with HNSW artifact fix. Monitor for dense embeddings from legal-distance lane. Evaluate autonomously as they land.

---

## Evidence References

- `evaluation/run_174k_formal_suite.py` — Fixed formal suite (v3_174k_fixed)
- `evaluation/scalable_nn.py` — Scalable NN infrastructure
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol
- `evaluation/results/174k/formal_suite/` — Formal suite output directory
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen citation pairs
- `evaluation/data/174k/metadata_174k.json` — Frozen 174k metadata
- `reports/evaluation/EVALUATION_174K_HNSW_FIX_REPORT_v27.md` — Full technical report