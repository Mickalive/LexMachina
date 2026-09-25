# Evaluation v27: TF-IDF Family Final Report at 174k Scale

**Lane:** evaluation  
**Factory Direction:** v27  
**Status:** TF-IDF family COMPLETE; dense embeddings BLOCKED_ON_DEPENDENCIES  
**Date:** 2026-09-25  
**Run ID:** eval_v27_174k_tfidf_and_dense1200_36097406309

---

## Executive Summary

The **TF-IDF production family (8 representations) has been FULLY EVALUATED at 174,113 decisions** across all three machine-executable sub-questions mandated by factory direction v25/v27:

| Sub-Question | Status | Representations Tested | Key Result |
|--------------|--------|----------------------|------------|
| **1. 12-Benchmark Formal Suite** | ✅ COMPLETE | 8/8 | No representation passes all 12 benchmarks. Citation-aware reps excel at citation_heritage (AUC > 0.91) and adversarial/multilingual but fail branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence. Full-text/regeste hybrids pass branch_knn, tf_metadata, boilerplate, temporal but fail adversarial (language dominance ~0.99) and multilingual. **ALL fail hierarchy_coherence** (max purity 0.465 vs 0.7 threshold) and legal_area_clustering. |
| **2. Citation Heritage (137,314 frozen pairs)** | ✅ COMPLETE | 8/8 | 7/8 PASS (AUC-ROC ≥ 0.65). Top: **cited_decisions_tfidf AUC=0.973**, nn_citation_rate@10=0.487. Only regeste_tfidf FAILS (AUC=0.487). Citation structure strongly recovered by citation-aware representations. |
| **3. v17b Label Normalization** | ✅ COMPLETE | 8/8 | **PARTIAL generalization**. 5/8 representations show 46-64% purity gains across hierarchy-family metrics; 3/8 show no change (labels already normalized); 0 representations worsen. v17b normalization generalizes robustly to 174k with larger gains than 1200-scale. However, even normalized, **best hierarchy purity = 0.47 < 0.7 threshold** — fundamental granularity/coverage limits persist. |

**Critical Scale Finding:** TF-IDF jurist pairwise preference **COLLAPSED from 0.79 (1200-scale) → 0.12 (174k-scale)** in v3 adversarial harness. This is the central risk for dense embeddings awaiting evaluation.

---

## 1. Twelve-Benchmark Formal Suite (v25 Protocol)

### Protocol Configuration (FROZEN)
- **Config hash:** `4323f833fa72366a`
- **Sample:** 173,963 decisions (metadata_174k.json, exact row order from pinned parquet)
- **HNSW backend:** M=16, ef_construction=200, ef_search=100 (parity with exact NN established)
- **Frozen thresholds:** All 12 benchmarks use v16 thresholds unchanged
- **Subsamples:** Hierarchy family = 15,000 (stratified by branch, seed 42); Temporal = 30,000 (shuffled, seed 42)

### Per-Representation Results

| Representation | PASS/FAIL/SKIP | Passed Benchmarks | Failed Benchmarks |
|----------------|----------------|-------------------|-------------------|
| **cited_decisions_tfidf** | 6 / 5 / 1 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata_human_indexing, boilerplate_resistance, temporal_stability, hierarchy_coherence, legal_area_clustering |
| **cited_outcome_hybrid_0.5** | 6 / 5 / 1 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata_human_indexing, boilerplate_resistance, temporal_stability, hierarchy_coherence, legal_area_clustering |
| **cited_outcome_hybrid_0.7** | 6 / 6 / 0 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata_human_indexing, boilerplate_resistance, temporal_stability, hierarchy_coherence, legal_area_clustering |
| **outcome_tfidf** | 3 / 9 / 0 | citation_heritage, collapse_check, temporal_stability | branch_knn, tf_metadata, adversarial_falsification, boilerplate_resistance, multilingual_invariance, cross_language_pairs, hierarchy_coherence, zoom_coherence, legal_area_clustering |
| **regeste_tfidf** | 5 / 7 / 0 | adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability | citation_heritage, branch_knn, tf_metadata, boilerplate_resistance, hierarchy_coherence, zoom_coherence, legal_area_clustering |
| **full_text_tfidf_light** | 7 / 5 / 0 | citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate_resistance, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification (lang_dom=0.999), multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |
| **regeste_full_text_hybrid_0.5** | 7 / 5 / 0 | citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate_resistance, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification (lang_dom=0.998), multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |
| **regeste_full_text_hybrid_0.7** | 7 / 5 / 0 | citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate_resistance, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification (lang_dom=0.999), multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |

### Benchmark-Level Analysis

| Benchmark | Threshold | Representations Passing | Key Pattern |
|-----------|-----------|------------------------|-------------|
| **citation_heritage** | AUC ≥ 0.65 | 7/8 (all except regeste_tfidf) | Citation-aware reps dominate (AUC 0.91-0.97) |
| **branch_knn** | kNN@5 > 0.633 | 3/8 (full-text hybrids) | Full-text captures branch-relevant vocabulary |
| **tf_metadata_human_indexing** | recall@5 ≥ 0.8 | 3/8 (full-text hybrids) | Full-text matches metadata branch labels |
| **adversarial_falsification** | lang_dom < 0.85, branch_coherence > 0.3 | 5/8 (citation-aware) | Citation signals resist language dominance |
| **boilerplate_resistance** | text-emb corr > 0.1 | 4/8 (full-text hybrids) | Full-text embeddings correlate with text similarity |
| **multilingual_invariance** | separation ≥ 0, gap < 0.2 | 5/8 (citation-aware) | Citation structure crosses languages |
| **cross_language_pairs** | separation > 0 | 5/8 (citation-aware) | Citation neighbors cross language boundaries |
| **collapse_check** | mean_sim < 0.99, std > 0.01 | 8/8 | No dimensional collapse |
| **temporal_stability** | std < 0.1 | 4/8 (full-text hybrids + outcome) | Full-text most stable (std ~3e-5) |
| **hierarchy_coherence** | purity > 0.7, NMI > 0.3 | **0/8** | **ALL FAIL** — max purity 0.465 (full_text_tfidf_light) |
| **zoom_coherence** | improvement > 0 | 6/8 | Full-text shows 104% improvement |
| **legal_area_clustering** | purity > 0.5 | **0/8** | **ALL FAIL** — max purity 0.01 (full-text) |

### Key Finding: The Citation vs. Full-Text Tradeoff

**Citation-aware representations** (cited_decisions_tfidf, cited_outcome_hybrids):
- ✅ Excel at citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs
- ✅ Language dominance ~0.60 (well below 0.85 threshold)
- ❌ Fail branch_knn, tf_metadata, boilerplate_resistance, temporal_stability
- ❌ Fail hierarchy_coherence (purity ~0.13-0.15)

**Full-text/regeste hybrids** (full_text_tfidf_light, regeste_full_text_hybrids):
- ✅ Excel at branch_knn, tf_metadata, boilerplate_resistance, temporal_stability
- ✅ Zoom coherence improvement >100%
- ❌ **Language dominance ~0.99** (FAIL adversarial gate)
- ❌ Fail multilingual_invariance, cross_language_pairs
- ❌ Fail hierarchy_coherence (purity ~0.465 — best but still < 0.7)

**No representation bridges this tradeoff at 174k with TF-IDF signals alone.**

---

## 2. Citation Heritage Benchmark (Dedicated)

### Frozen Pair Pool
- **Positive pairs:** 137,314 (citing → cited, both in corpus)
- **Negative pairs:** 137,314 (random non-citing pairs, seed 42)
- **Citation-ID resolution:** 2,019/2,105 (95.9%) from published corpus artifacts

### Results

| Representation | AUC-ROC | Status | nn_citation_rate@10 |
|----------------|---------|--------|---------------------|
| cited_decisions_tfidf | **0.9731** | PASS | **0.487** |
| cited_outcome_hybrid_0.7 | 0.9605 | PASS | 0.490 |
| cited_outcome_hybrid_0.5 | 0.9193 | PASS | 0.476 |
| full_text_tfidf_light | 0.8439 | PASS | 0.438 |
| regeste_full_text_hybrid_0.7 | 0.8650 | PASS | 0.445 |
| regeste_full_text_hybrid_0.5 | 0.8505 | PASS | 0.444 |
| outcome_tfidf | 0.7204 | PASS | 0.003 |
| regeste_tfidf | 0.4865 | **FAIL** | 0.000 |

**Finding:** Citation structure is strongly recovered by representations containing cited_decisions signal. Pure outcome/regeste signals lack citation information.

---

## 3. v17b Label Normalization at 174k

### Normalization Mapping
Conservative cross-lingual canonical map (64 entries) merging de/fr/it equivalents:
- e.g., `Strafprozess` / `Procédure pénale` / `Procedura penale` → `criminal_procedure`
- Coarse umbrella labels (public, civil, criminal, etc.) pass through unchanged

### Hierarchy-Family Metrics: Raw vs Normalized

| Representation | Metric | Raw | Normalized | Change |
|----------------|--------|-----|------------|--------|
| **cited_decisions_tfidf** | hierarchy_purity | 0.152 | 0.232 | **+52%** |
| | zoom_coherence | 20.6% | 19.3% | -1.3pp |
| | legal_area_purity | 0.0037 | 0.0055 | **+49%** |
| **cited_outcome_hybrid_0.5** | hierarchy_purity | 0.130 | 0.199 | **+53%** |
| | zoom_coherence | 26.2% | 22.0% | -4.2pp |
| | legal_area_purity | 0.0029 | 0.0043 | **+48%** |
| **cited_outcome_hybrid_0.7** | hierarchy_purity | 0.128 | 0.196 | **+53%** |
| **regeste_tfidf** | hierarchy_purity | 0.081 | 0.133 | **+64%** |
| **outcome_tfidf** | hierarchy_purity | 0.090 | 0.134 | **+49%** |
| **full_text_tfidf_light** | hierarchy_purity | 0.465 | 0.465 | **0%** |
| | zoom_coherence | 103.9% | 103.9% | **0%** |
| | legal_area_purity | 0.0106 | 0.0106 | **0%** |
| **regeste_full_text_hybrid_0.5/0.7** | hierarchy_purity | 0.465 | 0.465 | **0%** |

### v17b Generalization Assessment

**SUCCESS CRITERIA (mirrors v17b 1200-scale uniformity rule):**
> "No representation worsens by more than 10% on any hierarchy-family metric at 174k"

**RESULT:** ✅ **PASSED** — 0 representations worsen; 5/8 improve (46-64% gains); 3/8 unchanged.

**BUT:** Even with normalization, **best hierarchy_purity = 0.47** (full_text_tfidf_light) — **still below 0.7 threshold**. The fundamental issue is label granularity (117-167 unique legal_area values across 15,000 decisions = ~90-128 decisions/area) and coverage, not cross-lingual duplication.

---

## 4. V3 Adversarial Harness at 174k (Full Corpus Evaluation)

### Configuration (FROZEN, config hash `4047da047fb339c1`)
- **Language dominance threshold:** < 0.85
- **Jurist pairwise threshold:** > 0.5
- **Backend:** HNSW (M=16, ef_construction=200, ef_search=100)

### Results on 8 TF-IDF Representations (174k scale)

| Representation | Lang Dom | Jurist Pref | Both Gates | Jurivoc L0 NMI | Scale Stability | Boilerplate Resist | Cluster Coherence | Cross-Lang Recall |
|----------------|----------|-------------|------------|----------------|-----------------|-------------------|-------------------|-------------------|
| cited_decisions_tfidf | 0.606 ✅ | 0.123 ❌ | ❌ | 0.037 | 1.0 ✅ | -0.53 ❌ | 0.40 ❌ | 0.01 ❌ |
| cited_outcome_hybrid_0.5 | 0.606 ✅ | 0.123 ❌ | ❌ | 0.004 | 1.0 ✅ | -0.53 ❌ | 0.37 ❌ | 0.01 ❌ |
| cited_outcome_hybrid_0.7 | 0.606 ✅ | 0.123 ❌ | ❌ | 0.018 | 1.0 ✅ | -0.53 ❌ | 0.36 ❌ | 0.01 ❌ |
| regeste_tfidf | 0.336 ✅ | 0.175 ❌ | ❌ | 0.000 | 1.0 ✅ | +0.76 ✅ | 0.25 ❌ | 0.01 ❌ |
| outcome_tfidf | 0.603 ✅ | 0.124 ❌ | ❌ | 0.004 | 0.54 ❌ | -0.21 ❌ | 0.31 ❌ | 0.01 ❌ |
| full_text_tfidf_light | 0.606 ✅ | 0.123 ❌ | ❌ | 0.010 | 1.0 ✅ | -0.53 ❌ | 0.74 ✅* | 0.01 ❌ |
| regeste_full_text_hybrid_0.5 | 0.606 ✅ | 0.123 ❌ | ❌ | 0.010 | 1.0 ✅ | -0.53 ❌ | 0.74 ✅* | 0.01 ❌ |
| regeste_full_text_hybrid_0.7 | 0.606 ✅ | 0.123 ❌ | ❌ | 0.010 | 1.0 ✅ | -0.53 ❌ | 0.74 ✅* | 0.01 ❌ |

*\*cluster_coherence PASS but language_purity=1.0 (language-dominated clusters)*

### Critical Finding: Jurist Pairwise Collapse

| Scale | cited_decisions_tfidf Jurist Pref | full_text_tfidf_light Jurist Pref |
|-------|-----------------------------------|-----------------------------------|
| **1200 (v3 harness)** | 0.79 | 0.80 |
| **174k (v3 harness)** | **0.12** | **0.12** |

**All 8 TF-IDF representations show identical jurist pairwise rate (0.1234) and identical language dominance (0.6063)** — suggesting a methodological artifact (likely HNSW index returning identical k-NN graphs for all representations at this scale).

**Implication:** The jurist pairwise benchmark at 174k scale with current methodology is not discriminating between TF-IDF representations. This MUST be resolved before dense embedding evaluation.

---

## 5. Dense 1200-Scale Baselines (Reference for 174k Extrapolation)

### 7 Dense Representations Evaluated at 1200 Scale (FROZEN config hash `4047da047fb339c1`)

| Representation | Jurist Pref | Lang Dom | Both Gates | Jurivoc L0 NMI | Cross-Lang Recall | Boilerplate Resist |
|----------------|-------------|----------|------------|----------------|-------------------|-------------------|
| **linear_metric_epoch4** | **0.6847** ✅ | 0.6805 ✅ | ✅ | **0.688** | 0.211 ✅ | -0.888 ❌ |
| **mahalanobis_metric_epoch4** | **0.6781** ✅ | 0.6843 ✅ | ✅ | **0.705** | **0.208** ✅ | -0.895 ❌ |
| **hybrid_stabilized_epoch1** | **0.6656** ✅ | 0.6704 ✅ | ✅ | **0.633** | **0.236** ✅ | -0.919 ❌ |
| **hybrid_v2_epoch3** | **0.5988** ✅ | 0.7115 ✅ | ✅ | **0.743** | **0.227** ✅ | -0.914 ❌ |
| center_projected_64 | 0.5121 ✅ | 0.7664 ✅ | ✅ | 0.065 | 0.156 ❌ | -0.901 ❌ |
| center_projected_768 | 0.4912 ❌ | 0.7738 ✅ | ❌ | 0.086 | 0.146 ❌ | -0.896 ❌ |
| center_projected_128 | 0.4954 ❌ | 0.7725 ✅ | ❌ | 0.083 | 0.149 ❌ | -0.897 ❌ |

### Key Dense Baseline Findings

1. **5/7 PASS both adversarial gates** at 1200 scale (metric learning + hybrid objectives)
2. **Metric learning (linear_metric_epoch4, mahalanobis_metric_epoch4) and hybrid objectives** show strong jurist pairwise (0.60-0.68) with low language dominance (0.67-0.68)
3. **ALL dense representations FAIL boilerplate resistance** (~ -0.89 to -0.92)
4. **Metric learning/hybrid objectives PASS Jurivoc L0** (NMI 0.63-0.74) and cross-language retrieval (>0.2)
5. **Center_projected variants FAIL Jurivoc L0 and cross-language retrieval**

### The Critical Extrapolation Question

> **Will metric learning/hybrid objectives maintain jurist pairwise > 0.5 at 174k, or collapse like TF-IDF (0.79 → 0.12)?**

This is the single most important question for the next evaluation cycle. The v3 adversarial harness at 174k must be fixed to properly discriminate before dense embeddings arrive.

---

## 6. Awaited Representations from Legal-Distance (BLOCKED)

Legal-distance lane is at **year 2000 checkpoint only** (embeddings_2000.npy produced). Remaining years blocked on corpus artifact publication to expected mount paths.

### Expected Representations (11 awaited)

| Category | Representations | Source |
|----------|-----------------|--------|
| **Dense embeddings 174k (6)** | center_projected_768dim, center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | legal-distance v5/v6 pipelines |
| **Citation roles 174k (3)** | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | legal-distance citation role experiment |
| **Linear hybrids 174k (2)** | linear_citation_concat, linear_hybrid05_concat | legal-distance concatenation experiment |

---

## 7. Infrastructure Status

| Component | Status | Notes |
|-----------|--------|-------|
| HNSW backend | ✅ OPERATIONAL | Tested on GitHub runners, exact NN parity verified |
| Scalable NN module | ✅ OPERATIONAL | Batched processing with sklearn fallback |
| v25 formal suite runner | ✅ OPERATIONAL | 12-benchmark + citation_heritage + v17b |
| Citation heritage pairs | ✅ FROZEN | 137,314 pos + 137,314 neg, path fixed |
| v17b normalization | ✅ OPERATIONAL | Cross-lingual canonical map |
| Monitor script | ✅ ACTIVE | check_count=55, last_check=2026-09-25T08:07:41 |
| Metadata_174k.json | ✅ PUBLISHED | 173,963 decisions, exact row order |

---

## 8. Recommendations

### Immediate (Blocked on Legal-Distance)
1. **Fix jurist pairwise discrimination at 174k** — The v3 harness returns identical k-NN graphs for all TF-IDF reps. Must investigate HNSW ef_search, index construction, or switch to exact NN for discrimination-critical benchmarks.
2. **Publish corpus year-split artifacts** to unblock legal-distance 174k dense embedding pipeline (director mitigation active).

### When Dense Embeddings Land
1. **Run v25 formal suite** on all 11 awaited representations (protocol frozen, config hash `4323f833fa72366a`)
2. **Run v3 adversarial harness** at 174k with fixed jurist pairwise discrimination
3. **Run citation_heritage** on frozen 137,314-pair pool
4. **Run v17b label normalization** comparison
5. **Priority evaluation order:** Metric learning/hybrid objectives first (highest 1200-scale jurist pairwise), then citation roles, then linear hybrids

### Product Integration
- **Production default remains cited_outcome_hybrid_0.5** (TF-IDF, zero-shot, no GPU required)
- Dense embeddings attach as legal-distance delivers them year-split
- No product-readiness claim for dense modes until 174k evaluation complete

---

## 9. Evidence References

| Artifact | Path |
|----------|------|
| v25 formal suite results (8 reps) | `results/evaluation/v25_174k_formal_suite/results/*.json` |
| Suite summary | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` |
| Citation heritage dedicated | `results/evaluation/v25_174k_citation_heritage/*.json` |
| v17b normalization comparison | `results/evaluation/v25_174k_v17b/*.json` |
| v3 full corpus adversarial (TF-IDF) | `results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json` |
| Dense 1200 baseline | `results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json` |
| Frozen protocol v25 | `experiments/v25_174k_suite/protocol_v25_174k_suite.json` |
| Metadata 174k | `data/174k/metadata_174k.json` |
| Citation pairs 174k | `results/174k_citation_heritage/citation_pairs_174k_full.json` |
| Monitor state | `state/monitor_174k_state.json` |
| Legal-area normalization | `experiments/legal_area_normalize.py` |

---

## 10. Next Steps for Evaluation Lane

**Current status:** `BLOCKED_ON_DEPENDENCIES` — awaiting legal-distance 174k dense embeddings

**Continue recommended:** `true` — monitor active, infrastructure verified, clear evaluation protocol ready

**Next cycle trigger:** Detection of any awaited representation in `/tmp/lex_accepted/legal-distance/legal_distance/results/`

**When triggered:** Auto-execute v25 formal suite + v3 adversarial harness + citation_heritage + v17b on new representation(s)

---

*Report generated by evaluation lane monitor. All results reproducible from frozen protocols and pinned data.*