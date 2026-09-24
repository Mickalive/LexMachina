# Evaluation Lane v26 — TF-IDF Family 174k Evaluation Completion Report

**Factory Direction Version:** 26  
**Lane:** evaluation  
**Status:** TF-IDF FAMILY COMPLETE — BLOCKED ON LEGAL-DISTANCE 174K DENSE EMBEDDINGS  
**Date:** 2026-09-24  
**GitHub Run:** 36070490081 (this cycle)

---

## Executive Summary

The TF-IDF production family (8 representations) has been **fully evaluated at 174k scale** (173,963 decisions) against the frozen 12-benchmark formal suite, the dedicated citation heritage benchmark (137,314 positive + 137,314 negative pairs), and the v17b cross-lingual label normalization test. All three machine-executable sub-questions from factory direction v25 are **COMPLETE** for the TF-IDF family.

**No additional same-question cycle is justified for the TF-IDF family.** The evaluation lane is now **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance lane delivery of 174k dense embeddings.

---

## 1. Scope of Completed Evaluation

### 1.1 Representations Evaluated (8 TF-IDF production family)

| Representation | Field/Recipe | Dimensions | Scale |
|---------------|--------------|------------|-------|
| `cited_decisions_tfidf` | Cited decisions (TF-IDF 5k, bi-gram, SVD 128) | 128 | 173,963 |
| `outcome_tfidf` | Outcome text (TF-IDF 3k, bi-gram, SVD 128) | 128 | 173,963 |
| `regeste_tfidf` | Regeste summary (TF-IDF 10k, bi-gram, SVD 128) | 128 | 173,963 |
| `full_text_tfidf_light` | Full text truncated 5k chars (TF-IDF 3k, uni-gram, SVD 128) | 128 | 173,963 |
| `cited_outcome_hybrid_0.5` | 0.5 × cited + 0.5 × outcome (L2-norm) | 128 | 173,963 |
| `cited_outcome_hybrid_0.7` | 0.7 × cited + 0.3 × outcome (L2-norm) | 128 | 173,963 |
| `regeste_full_text_hybrid_0.5` | 0.5 × regeste + 0.5 × full_text_light (L2-norm) | 128 | 173,963 |
| `regeste_full_text_hybrid_0.7` | 0.7 × regeste + 0.3 × full_text_light (L2-norm) | 128 | 173,963 |

**Provenance:** All embeddings built from pinned parquet (`/tmp/opencode/lexcorpus2/parquet/bger.parquet`) with row order exactly matching frozen `evaluation/data/174k/metadata_174k.json` (173,963 decisions, language mix: de=106,501, fr=57,489, it=9,973).

### 1.2 Benchmark Suites Executed

| Suite | Configuration | Scale | Thresholds |
|-------|---------------|-------|------------|
| **12-benchmark formal suite** | v16 spec, config hash `4323f833fa72366a`, seed 42 | 173,963 (HNSW) | Frozen v16 thresholds |
| **Citation heritage (dedicated)** | 137,314 positive + 137,314 negative pairs | 173,963 | AUC-ROC ≥ 0.65 |
| **v17b label normalization** | 15k frozen subsample, raw vs normalized legal_area | 15,000 | ≤10% worsening rule |

---

## 2. Results Summary

### 2.1 12-Benchmark Formal Suite Pass Counts (174k)

| Representation | Pass / Total | Key Passes | Key Fails |
|---------------|--------------|------------|-----------|
| `full_text_tfidf_light` | **7/12** | branch_knn, tf_metadata, boilerplate, collapse, temporal, zoom_coherence, citation_heritage | adversarial (lang_dom=0.999), multilingual, cross_lang, hierarchy, legal_area |
| `regeste_full_text_hybrid_0.5` | **7/12** | branch_knn, tf_metadata, boilerplate, collapse, temporal, zoom_coherence, citation_heritage | adversarial (lang_dom=0.998), multilingual, cross_lang, hierarchy, legal_area |
| `regeste_full_text_hybrid_0.7` | **7/12** | branch_knn, tf_metadata, boilerplate, collapse, temporal, zoom_coherence, citation_heritage | adversarial (lang_dom=0.999), multilingual, cross_lang, hierarchy, legal_area |
| `cited_decisions_tfidf` | **6/12** | adversarial, multilingual, cross_lang, collapse, zoom_coherence, citation_heritage | branch_knn, tf_metadata, boilerplate, temporal, hierarchy, legal_area |
| `cited_outcome_hybrid_0.5` | **6/12** | adversarial, multilingual, cross_lang, collapse, zoom_coherence, citation_heritage | branch_knn, tf_metadata, boilerplate, temporal, hierarchy, legal_area |
| `cited_outcome_hybrid_0.7` | **6/12** | adversarial, multilingual, cross_lang, collapse, zoom_coherence, citation_heritage | branch_knn, tf_metadata, boilerplate, temporal, hierarchy, legal_area |
| `regeste_tfidf` | **5/12** | adversarial, multilingual, cross_lang, collapse, temporal | citation_heritage (AUC=0.486), branch_knn, tf_metadata, boilerplate, zoom_coherence, hierarchy, legal_area |
| `outcome_tfidf` | **3/12** | collapse, temporal, citation_heritage | adversarial, branch_knn, tf_metadata, boilerplate, multilingual, cross_lang, zoom_coherence, hierarchy, legal_area |

### 2.2 Universal 174k Results (All Representations)

| Benchmark Category | Result | Notes |
|-------------------|--------|-------|
| **citation_heritage** | 7/8 PASS | `regeste_tfidf` FAIL (AUC=0.486) — regeste lacks citation IDs |
| **hierarchy_coherence** | 8/8 FAIL | Best purity 0.15–0.47 << 0.7 threshold (label granularity limitation) |
| **legal_area_clustering** | 8/8 FAIL | Best purity 0.003–0.08 << 0.5 threshold (213→163 labels, sparse) |
| **boilerplate_resistance_real_corpus** | 8/8 FAIL | Correlation ~-0.06 to +0.09; proxy measures language failure not boilerplate |
| **collapse_check** | 8/8 PASS | No dimensional collapse |
| **zoom_coherence** | Citation-based PASS, full-text FAIL | Citation hybrids show 20-27% improvement; full-text ~104% but language-dominated |
| **temporal_stability** | Mixed | Citation-based FAIL (high variance); full-text/regeste PASS (very stable) |
| **adversarial_falsification** | Citation-based PASS, full-text/regeste FAIL | Citation: lang_dom 0.57-0.60, branch_coherence 0.35; Full-text: lang_dom ~0.99 |

### 2.3 Citation Heritage Benchmark (137,314 pairs)

| Representation | AUC-ROC | Status | nn_citation_rate@10 |
|---------------|---------|--------|---------------------|
| `cited_decisions_tfidf` | **0.9731** | ✅ PASS | **0.4870** |
| `cited_outcome_hybrid_0.7` | **0.9605** | ✅ PASS | **0.4900** |
| `cited_outcome_hybrid_0.5` | **0.9193** | ✅ PASS | **0.4757** |
| `regeste_full_text_hybrid_0.7` | **0.8650** | ✅ PASS | **0.4448** |
| `regeste_full_text_hybrid_0.5` | **0.8505** | ✅ PASS | **0.4442** |
| `full_text_tfidf_light` | **0.8439** | ✅ PASS | **0.4381** |
| `outcome_tfidf` | **0.7204** | ✅ PASS | **0.0034** |
| `regeste_tfidf` | **0.4865** | ❌ FAIL | **0.0000** |

### 2.4 v17b Label Normalization (Raw → Normalized: 213 → 163 labels, 23.5% reduction)

| Representation | Hierarchy Purity Ratio | Zoom Coherence Ratio | Legal Area Ratio | Within ≤10% Rule? |
|---------------|------------------------|----------------------|------------------|-------------------|
| `cited_decisions_tfidf` | 1.52× | 0.93× | 1.49× | ✅ YES |
| `cited_outcome_hybrid_0.5` | 1.52× | 0.93× | 1.48× | ⚠️ Zoom -16% (exceeds) |
| `cited_outcome_hybrid_0.7` | 1.52× | 0.93× | 1.48× | ✅ YES |
| `regeste_tfidf` | 1.00× | 1.00× | 1.00× | ✅ YES (coarse 1:1 mapping) |
| `full_text_tfidf_light` | 1.00× | 1.00× | 1.00× | ✅ YES (coarse 1:1 mapping) |
| `regeste_full_text_hybrid_0.5` | 1.00× | 1.00× | 1.00× | ✅ YES (coarse 1:1 mapping) |
| `regeste_full_text_hybrid_0.7` | 1.00× | 1.00× | 1.00× | ✅ YES (coarse 1:1 mapping) |
| `outcome_tfidf` | 1.00× | 1.00× | 1.00× | ✅ YES (coarse 1:1 mapping) |

**Key Finding:** v17b normalization **partially generalizes** to 174k: 7/8 representations within ≤10% worsening rule on hierarchy-family metrics. `cited_outcome_hybrid_0.5` exceeds threshold on zoom_coherence (-16%). Normalized hierarchy purity gains: 1.5-1.6× for citation-based reps, 1.0× for full-text/regeste reps (coarse labels map 1:1). Even normalized, best hierarchy purity = 0.47 (full_text_tfidf_light) < 0.7 threshold.

---

## 3. Production Default Confirmation

**`cited_outcome_hybrid_0.7` confirmed as production default:**
- ✅ Passes both adversarial gates (lang_dom=0.569 < 0.85, branch_coherence=0.356 > 0.3)
- ✅ Citation heritage AUC = 0.9605
- ✅ nn_citation_rate@10 = 0.490
- ✅ Zero-shot TF-IDF, no GPU required
- ✅ `cited_outcome_hybrid_0.5` equivalent (AUC=0.9193, nn_rate=0.476)

---

## 4. Infrastructure Readiness for Dense Embeddings

| Component | Status | Notes |
|-----------|--------|-------|
| **Scalable NN (HNSW)** | ✅ VALIDATED at 1200 scale | Exact-cosine parity with frozen harness v3 (config hash `4047da047fb339c1`) |
| **Full corpus evaluation pipeline** | ✅ OPERATIONAL | `run_full_corpus_evaluation.py` with batched HNSW backend |
| **Citation heritage benchmark** | ✅ READY | 137,314 frozen pairs, infrastructure validated |
| **v17b label normalization** | ✅ READY | Label-level confirmed at 174k (213→163), clustering-level tested on 8 TF-IDF reps |
| **Monitor script** | ✅ OPERATIONAL | `monitor_and_evaluate_174k.py` scans legal-distance accepted state |
| **Distributed evaluation** | ✅ SUPPORTED | Model-level sharding via `DistributedEvaluator` |

**Verified against accepted dense embeddings (github run 36063000772):**
- `center_projected_768dim` (1000 scale): PASS both adversarial (LangDom=0.7599, Jurist=0.5215)
- `center_projected_64dim` (1200 scale): PASS both adversarial (LangDom=0.7664, Jurist=0.5121)
- `linear_metric_epoch4` (1200 scale): PASS both adversarial (LangDom=0.6805, Jurist=0.6847)
- Results match legal-distance reported adversarial gate outcomes exactly.

---

## 5. Current Blockers

| Blocker | Type | Resolution |
|---------|------|------------|
| **No 174k dense embeddings in legal-distance accepted state** | External dependency | Legal-distance RUN (staged 174k CPU execution, year-split, TF-IDF first). Active run: gh 35935612800 |
| **No jurist human study** | External dependency | Requires 5-10 Swiss jurists recruited by repository owner; framework ready |

---

## 6. Next Steps

1. **Legal-distance lane** delivers 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids)
2. **Evaluation lane** auto-evaluates via `monitor_and_evaluate_174k.py` (full 12-benchmark suite + citation heritage + v17b)
3. **Fractal-map lane** consumes evaluated representations for zoom-quality testing
4. **Product lane** wires production defaults to full-corpus artifacts

---

## 7. Evidence References

| Artifact | Path |
|----------|------|
| 12-benchmark suite results | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` |
| Individual representation results | `results/evaluation/v25_174k_formal_suite/results/*.json` |
| Citation heritage dedicated | `results/evaluation/v25_174k_citation_heritage/*.json` |
| v17b label normalization | `results/evaluation/v25_174k_v17b/*.json` |
| Build manifest | `results/evaluation/v25_174k_formal_suite/embeddings/build_manifest.json` |
| Frozen protocol | `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` |
| Frozen config hash | `4323f833fa72366a` (v16 spec), `4047da047fb339c1` (full corpus harness) |
| Metadata | `evaluation/data/174k/metadata_174k.json` (173,963 decisions) |
| Citation pairs | `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` |

---

## 8. State Update

The evaluation lane state (`evaluation/state/evaluation.json`) correctly reflects:
- `evidence_tier`: REPRODUCED
- `cycle_status`: BLOCKED_ON_DEPENDENCIES
- `continue_recommended`: false
- `blocked_on`: legal-distance lane 174k dense embeddings
- `tfidf_family_completed`: 8 representations listed
- `production_representations_awaited`: 10 dense representations listed

**No state update required** — current state accurately reflects completion of TF-IDF family evaluation and blocking on dense embeddings.

---

*Report generated per Research Protocol: frozen hypothesis, corpus, baseline, metric, and success rule before outcome inspection. Negative results preserved as first-class evidence.*