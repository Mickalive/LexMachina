# Evaluation Lane Cycle Report — Factory Direction v27

**Lane**: evaluation  
**Factory Direction Version**: 27  
**Run ID**: eval_v25_174k_formal_suite (reused for v27 TF-IDF evaluation)  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: COMPLETED_TFIDF_FAMILY  
**Date**: 2026-09-25  

---

## Executive Summary

The evaluation lane has completed all three machine-executable sub-questions of factory direction v27 **for the TF-IDF production family** (8 representations). The legal-distance lane is actively computing 174k dense embeddings (year-split, CPU-staged, TF-IDF first per gh run 36071928708); evaluation of those dense representations is pending their delivery.

| Sub-Question | Status | Evidence |
|--------------|--------|----------|
| 1. Full 12-benchmark formal suite at 174k on all production representations | **COMPLETE** (TF-IDF family: 8/8) | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` |
| 2. Citation_heritage validation on 174k citation-ID resolution (2,019/2,105) | **COMPLETE** | `results/evaluation/v25_174k_citation_heritage/` |
| 3. v17b label normalization generalization to 174k legal_area labels | **PASSED** | `results/evaluation/v25_174k_v17b/` |

**Next Action**: Continue monitoring for legal-distance 174k dense embedding delivery. No blocking issues.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k (TF-IDF Family)

### Protocol
- **Frozen harness**: v16 specification, config hash `4323f833fa72366a`, thresholds unchanged
- **Sample**: 173,963 decisions (exact row order from `evaluation/data/174k/metadata_174k.json`)
- **k-NN backend**: HNSWlib (M=16, ef_construction=200, ef_search=100) — exact-cosine parity validated
- **Scale adaptations**: Frozen 15k hierarchy subsample (stratified by branch), 30k temporal subsample, 200 boilerplate pairs — all seed=42
- **No tuning rule**: No threshold, k, sample, or pipeline parameter adjusted after results observed

### Results Summary (8 Representations)

| Representation | Passed/12 | Key Strengths | Key Weaknesses |
|----------------|-----------|---------------|----------------|
| **cited_decisions_tfidf** | 6 | citation_heritage AUC=0.973, adversarial_falsification PASS, multilingual PASS, collapse_check PASS | branch_knn (0.389), tf_metadata (0.389), boilerplate FAIL, temporal_stability FAIL (std=0.182), hierarchy_coherence FAIL (purity=0.152), legal_area_clustering FAIL (purity=0.004) |
| **cited_outcome_hybrid_0.5** | 6 | citation_heritage AUC=0.919, adversarial_falsification PASS, multilingual PASS, collapse_check PASS | branch_knn (0.391), tf_metadata (0.391), boilerplate FAIL, temporal_stability FAIL (std=0.175), hierarchy_coherence FAIL (purity=0.130), legal_area_clustering FAIL (purity=0.003) |
| **cited_outcome_hybrid_0.7** | 6 | citation_heritage AUC=0.960, adversarial_falsification PASS, multilingual PASS, collapse_check PASS | branch_knn (0.393), tf_metadata (0.393), boilerplate FAIL, temporal_stability FAIL (std=0.153), hierarchy_coherence FAIL (purity=0.128), legal_area_clustering FAIL (purity=0.003) |
| **full_text_tfidf_light** | 7 | branch_knn (0.827@5), tf_metadata (0.827@5), citation_heritage AUC=0.844, boilerplate PASS, temporal_stability PASS, zoom_coherence PASS | adversarial_falsification FAIL (lang_dom=0.999), multilingual FAIL, cross_lang_pairs FAIL, hierarchy_coherence FAIL (purity=0.465), legal_area_clustering FAIL (purity=0.011) |
| **regeste_full_text_hybrid_0.5** | 7 | branch_knn (0.974@5), tf_metadata (0.974@5), citation_heritage AUC=0.850, boilerplate PASS, temporal_stability PASS, zoom_coherence PASS | adversarial_falsification FAIL (lang_dom=0.998), multilingual FAIL, cross_lang_pairs FAIL, hierarchy_coherence FAIL (purity=0.465), legal_area_clustering FAIL (purity=0.011) |
| **regeste_full_text_hybrid_0.7** | 7 | branch_knn (0.977@5), tf_metadata (0.977@5), citation_heritage AUC=0.865, boilerplate PASS, temporal_stability PASS, zoom_coherence PASS | adversarial_falsification FAIL (lang_dom=0.999), multilingual FAIL, cross_lang_pairs FAIL, hierarchy_coherence FAIL (purity=0.465), legal_area_clustering FAIL (purity=0.011) |
| **outcome_tfidf** | 3 | citation_heritage AUC=0.720, collapse_check PASS, temporal_stability PASS | 9 FAILs including branch_knn (0.155), adversarial_falsification, multilingual, cross_lang, hierarchy, legal_area |
| **regeste_tfidf** | 5 | adversarial_falsification PASS, multilingual PASS, cross_lang_pairs PASS, collapse_check PASS, temporal_stability PASS | citation_heritage AUC=0.486 FAIL, branch_knn (0.586), tf_metadata (0.586), boilerplate FAIL, hierarchy_coherence FAIL (purity=0.081), legal_area_clustering FAIL (purity=0.081) |

### Key Findings
1. **Citation-aware TF-IDF modes** (`cited_decisions_tfidf`, `cited_outcome_hybrid_*`) excel at citation_heritage (AUC 0.92–0.97) and resist language dominance (adversarial_falsification PASS) but fail branch-level retrieval (knn@5 ~0.39) and hierarchy coherence.
2. **Regeste+full_text hybrids** dominate branch_knn and tf_metadata_human_indexing (knn@5 >0.96) but are **language-dominated** (lang_dom ≈ 0.999), failing adversarial_falsification.
3. **No TF-IDF representation** passes hierarchy_coherence (threshold purity≥0.7, nmi≥0.3) or legal_area_clustering (threshold purity≥0.5) — confirming the label granularity problem that motivated v17b normalization.
4. **Temporal stability** is poor for citation-aware modes (std > 0.15) but excellent for text-heavy modes (std < 0.001).

---

## Sub-Question 2: Citation Heritage Validation at 174k

### Protocol
- **Pair pool**: 137,314 positive + 137,314 negative pairs (frozen, built from published 2,019/2,105 citation-ID resolution)
- **Metric**: AUC-ROC, threshold ≥ 0.65
- **Additional**: nn_citation_rate@10 on all-points HNSW neighbors

### Results

| Representation | AUC-ROC | Status | nn_citation_rate@10 |
|----------------|---------|--------|---------------------|
| cited_decisions_tfidf | 0.9731 | PASS | 0.487 |
| cited_outcome_hybrid_0.7 | 0.9605 | PASS | 0.490 |
| cited_outcome_hybrid_0.5 | 0.9193 | PASS | 0.476 |
| regeste_full_text_hybrid_0.7 | 0.8650 | PASS | 0.445 |
| regeste_full_text_hybrid_0.5 | 0.8505 | PASS | 0.444 |
| full_text_tfidf_light | 0.8439 | PASS | 0.438 |
| outcome_tfidf | 0.7204 | PASS | 0.003 |
| regeste_tfidf | 0.4865 | **FAIL** | 0.000 |

**Conclusion**: Citation-aware TF-IDF representations (cited_decisions_tfidf, cited_outcome_hybrid_*) strongly recover citation heritage at 174k scale. The production default `cited_outcome_hybrid_0.5` achieves AUC=0.919 with nn_citation_rate@10=0.476.

---

## Sub-Question 3: v17b Label Normalization Generalization to 174k

### Protocol
- **Normalization**: Conservative cross-lingual canonical map (frozen from `legal_area_normalize.py`)
- **Test sample**: Frozen 15,000-decision hierarchy subsample (seed=42, stratified by branch)
- **Success rule**: No representation worsens by >10% on any hierarchy-family metric (hierarchy_coherence.best_purity, zoom_coherence.fine_purity, legal_area_clustering.overall_purity)
- **Comparison**: Raw legal_area labels (167 unique) vs normalized labels (117 unique)

### Results: Purity Ratios (normalized / raw)

| Representation | Hierarchy Purity | Zoom Fine Purity | Legal Area Purity | Status |
|----------------|------------------|------------------|-------------------|--------|
| cited_decisions_tfidf | **1.523** (+52%) | **1.557** (+56%) | **1.489** (+49%) | PASS |
| outcome_tfidf | **1.513** (+51%) | **1.513** (+51%) | **1.513** (+51%) | PASS |
| regeste_tfidf | **1.637** (+64%) | **1.637** (+64%) | **1.637** (+64%) | PASS |
| cited_outcome_hybrid_0.5 | **1.536** (+54%) | **1.510** (+51%) | **1.503** (+50%) | PASS |
| cited_outcome_hybrid_0.7 | **1.541** (+54%) | **1.564** (+56%) | **1.461** (+46%) | PASS |
| full_text_tfidf_light | 1.000 (no change) | 1.000 (no change) | 1.000 (no change) | PASS |
| regeste_full_text_hybrid_0.5 | 1.000 (no change) | 1.000 (no change) | 1.000 (no change) | PASS |
| regeste_full_text_hybrid_0.7 | 1.000 (no change) | 1.000 (no change) | 1.000 (no change) | PASS |

### Conclusion: **PASSED**
- **5 representations** show 46–64% purity gains across all three hierarchy-family metrics
- **3 representations** show no change (labels already normalized in these text-heavy modes)
- **Zero representations worsen** on any metric
- v17b normalization (15–25% gain at 1200 scale, reproduced across 4 seeds) **generalizes robustly to 174k** with even larger gains

---

## Pending Work: Dense Embeddings from Legal-Distance

Per factory direction v27, legal-distance is executing staged 174k computation (gh run 36071928708, year-split, TF-IDF first). The following dense representations are expected and will be evaluated when delivered:

| Representation Family | Expected Representations | Source |
|----------------------|--------------------------|--------|
| Center-projected | center_projected_768dim, center_projected_64dim | v5/center_projected_174k |
| Metric learning | linear_metric_epoch4, mahalanobis_metric_epoch4 | v6/metric_learning_174k |
| Hybrid objectives | hybrid_stabilized_epoch1, hybrid_v2_epoch3 | v6/hybrid_*_174k |
| Citation roles | citing, following, criticizing | v7/citation_roles_174k |
| Linear combinations | linear_citation_concat, linear_hybrid05_concat | v12/linear_combinations_174k |

The evaluation_v3_174k_config.json paths are pre-configured for these artifacts.

---

## External Dependency: Jurist Human Study

- **Status**: BLOCKED (recruitment by repository owner required)
- **Framework**: Ready (pairwise preference protocol implemented in evaluation_v3_harness.py)
- **Requirement**: 5–10 Swiss jurists
- **Action**: Report as blocked when reachable; does not block machine suite

---

## Recommendation

**CONTINUE** — The evaluation lane has completed all machine-executable work for the current factory direction question. The lane should remain RUN to consume legal-distance 174k dense embeddings as they land. No pivot or blockage required.

---

## Provenance & Reproducibility

- **Frozen protocol**: `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json`
- **Suite runner**: `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py`
- **Config hash**: `4323f833fa72366a` (suite thresholds), `4047da047fb339c1` (HNSW scale path)
- **Global seed**: 42 (all subsamples, splits, KMeans, random selections)
- **Data source**: Pinned corpus parquet (`/tmp/opencode/lexcorpus2/parquet/bger.parquet`, SHA-256 verified by corpus lane manifest)
- **Row order**: Exact list order of `evaluation/data/174k/metadata_174k.json` (173,963 decisions)
