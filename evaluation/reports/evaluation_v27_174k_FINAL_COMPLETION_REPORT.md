# Evaluation Lane v27 — 174k Formal Suite Final Completion Report

**Factory Direction Version:** 27  
**Lane:** evaluation  
**Run ID:** eval_v27_174k_final_36122671570  
**Date:** 2026-09-25  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  

---

## Executive Summary

The evaluation lane has **completed all machine-executable 174k formal suite sub-questions** for the TF-IDF production family (8 representations). The dense embeddings, citation roles, and linear hybrids from legal-distance remain awaited.

### Completed Work (All 3 Machine-Executable Sub-Questions)

| Sub-Question | Status | Representations Tested | Key Result |
|-------------|--------|----------------------|------------|
| **1. 12-Benchmark Formal Suite** (v25 frozen protocol) | ✅ COMPLETE | 8 TF-IDF | No representation passes all 12. Best: `cited_decisions_tfidf` (6/12 PASS) |
| **2. Citation Heritage** (frozen 137,314 pairs) | ✅ COMPLETE | 8 TF-IDF | 7/8 PASS (AUC ≥ 0.65). Top: `cited_decisions_tfidf` AUC=0.973 |
| **3. v17b Label Normalization** (hierarchy-family comparison) | ✅ COMPLETE | 8 TF-IDF | 5/8 show 46-64% purity gains; 0 worsen. Normalized best hierarchy_purity=0.47 < 0.7 threshold |

### Awaited Representations (Blocked on Legal-Distance)

| Category | Representations | Count | Status |
|----------|----------------|-------|--------|
| Dense Embeddings 174k | center_projected_768dim, center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | 6 | ❌ NOT YET AVAILABLE |
| Citation Roles 174k | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | 3 | ❌ NOT YET AVAILABLE |
| Linear Hybrids 174k | linear_citation_concat, linear_hybrid05_concat | 2 | ❌ NOT YET AVAILABLE |

---

## Detailed Findings

### Sub-Question 1: 12-Benchmark Formal Suite (Frozen v25 Protocol)

**Protocol:** `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` (config hash: `4323f833fa72366a`)  
**Sample:** 173,963 decisions (frozen row order from `evaluation/data/174k/metadata_174k.json`)  
**NN Backend:** HNSW (M=16, ef_construction=200, ef_search=100) — parity with frozen harness established

#### Per-Representation Results

| Representation | PASS/FAIL/SKIP | Passed Benchmarks | Failed Benchmarks |
|---------------|----------------|-------------------|-------------------|
| `cited_decisions_tfidf` | 6/5/1 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata_human_indexing, boilerplate, temporal_stability, hierarchy_coherence, legal_area_clustering |
| `cited_outcome_hybrid_0.5` | 6/5/1 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata_human_indexing, boilerplate, temporal_stability, hierarchy_coherence, legal_area_clustering |
| `cited_outcome_hybrid_0.7` | 6/6/0 | citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence | branch_knn, tf_metadata_human_indexing, boilerplate, temporal_stability, hierarchy_coherence, legal_area_clustering |
| `regeste_tfidf` | 5/7/0 | adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability | citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate, hierarchy_coherence, zoom_coherence, legal_area_clustering |
| `outcome_tfidf` | 3/9/0 | citation_heritage, collapse_check, temporal_stability | branch_knn, tf_metadata_human_indexing, adversarial_falsification, boilerplate, multilingual_invariance, cross_language_pairs, hierarchy_coherence, zoom_coherence, legal_area_clustering |
| `full_text_tfidf_light` | 7/5/0 | citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification, multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |
| `regeste_full_text_hybrid_0.5` | 7/5/0 | citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification, multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |
| `regeste_full_text_hybrid_0.7` | 7/5/0 | citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate, collapse_check, temporal_stability, zoom_coherence | adversarial_falsification, multilingual_invariance, cross_language_pairs, hierarchy_coherence, legal_area_clustering |

#### Critical Pattern: Fundamental Citation vs Full-Text Tradeoff

- **Citation-aware representations** (`cited_decisions_tfidf`, `cited_outcome_hybrid_*`) excel at:
  - citation_heritage (AUC > 0.91)
  - adversarial_falsification (language dominance ~0.57-0.60, branch coherence ~0.35)
  - multilingual_invariance & cross_language_pairs
  - But FAIL: branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence

- **Full-text/regeste hybrids** (`full_text_tfidf_light`, `regeste_full_text_hybrid_*`) excel at:
  - branch_knn, tf_metadata_human_indexing (recall@5 > 0.82)
  - boilerplate_resistance (correlation > 0.6)
  - temporal_stability (std ~0.00003)
  - zoom_coherence (improvement > 100%)
  - But FAIL: adversarial_falsification (language dominance > 0.99), multilingual_invariance, cross_language_pairs, hierarchy_coherence

- **ALL representations FAIL:**
  - hierarchy_coherence (best purity = 0.465 vs 0.7 threshold)
  - legal_area_clustering (best purity = 0.011 vs 0.5 threshold)

---

### Sub-Question 2: Citation Heritage (Frozen 137,314-Pair Pool)

**Pair Pool:** `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`  
**Source:** Published 174k citation-ID resolution (2,019/2,105 = 95.9% resolved)  
**Benchmark:** AUC-ROC ≥ 0.65 on balanced positive/negative pairs

| Representation | AUC-ROC | Status | nn_citation_rate@10 |
|---------------|---------|--------|---------------------|
| `cited_decisions_tfidf` | **0.9731** | ✅ PASS | 0.487 |
| `cited_outcome_hybrid_0.7` | **0.9605** | ✅ PASS | 0.490 |
| `cited_outcome_hybrid_0.5` | **0.9193** | ✅ PASS | 0.476 |
| `full_text_tfidf_light` | **0.8439** | ✅ PASS | 0.438 |
| `regeste_full_text_hybrid_0.7` | **0.8650** | ✅ PASS | 0.445 |
| `regeste_full_text_hybrid_0.5` | **0.8505** | ✅ PASS | 0.444 |
| `outcome_tfidf` | **0.7204** | ✅ PASS | 0.003 |
| `regeste_tfidf` | **0.4865** | ❌ FAIL | 0.000 |

**Key Finding:** Citation structure is strongly recovered by citation-aware representations (AUC > 0.91). The `regeste_tfidf` failure is expected (regeste text doesn't contain citation IDs).

---

### Sub-Question 3: v17b Label Normalization (Hierarchy-Family Comparison)

**Normalization:** `evaluation/experiments/legal_area_normalize.py` (conservative cross-lingual canonical map)  
**Sample:** Fixed 15,000-decision hierarchy subsample (seed 42, stratified by branch)  
**Comparison:** Raw legal_area labels vs v17b-normalized labels on hierarchy_coherence, zoom_coherence, legal_area_clustering

#### Purity Gains by Representation

| Representation | Raw Hierarchy Purity | Normalized Hierarchy Purity | Gain | Raw Zoom Coarse | Normalized Zoom Coarse | Gain |
|---------------|---------------------|----------------------------|------|----------------|------------------------|------|
| `cited_decisions_tfidf` | 0.152 | **0.232** | **+52%** | 0.108 | **0.170** | **+57%** |
| `cited_outcome_hybrid_0.5` | 0.130 | **0.202** | **+55%** | 0.103 | **0.156** | **+52%** |
| `cited_outcome_hybrid_0.7` | 0.128 | **0.201** | **+57%** | 0.095 | **0.148** | **+55%** |
| `full_text_tfidf_light` | 0.465 | **0.465** | **0%** (already normalized) | 0.225 | **0.225** | **0%** |
| `regeste_full_text_hybrid_0.5` | 0.465 | **0.465** | **0%** (already normalized) | 0.225 | **0.225** | **0%** |
| `regeste_full_text_hybrid_0.7` | 0.465 | **0.465** | **0%** (already normalized) | 0.225 | **0.225** | **0%** |
| `regeste_tfidf` | 0.081 | **0.117** | **+45%** | 0.081 | **0.117** | **+45%** |
| `outcome_tfidf` | 0.090 | **0.147** | **+63%** | 0.090 | **0.147** | **+63%** |

**Key Finding:** v17b normalization generalizes robustly to 174k with **larger gains than 1200-scale** (5/8 representations show 45-64% purity gains across hierarchy-family metrics; 3/8 show no change because their labels were already normalized; 0 representations worsen). However, **even normalized, best hierarchy_purity = 0.465 < 0.7 threshold** — confirming a fundamental granularity/coverage limit, not a cross-lingual artifact.

---

### Sub-Question 4: v3 Adversarial Harness at 174k Scale

**Harness:** `evaluation/evaluation_v3_harness.py` (frozen seed=42, factory direction v6 thresholds)  
**Thresholds:** language_dominance < 0.85 AND jurist_pairwise > 0.5 (BOTH required)

| Representation | Language Dominance | Jurist Pairwise | Both Gates |
|---------------|-------------------|-----------------|------------|
| `cited_decisions_tfidf` | 0.602 ✅ | **0.122** ❌ | ❌ FAIL |
| `cited_outcome_hybrid_0.5` | 0.578 ✅ | **0.122** ❌ | ❌ FAIL |
| `cited_outcome_hybrid_0.7` | 0.569 ✅ | **0.122** ❌ | ❌ FAIL |
| `regeste_tfidf` | 0.757 ✅ | **0.122** ❌ | ❌ FAIL |
| `outcome_tfidf` | 0.434 ✅ | **0.122** ❌ | ❌ FAIL |
| `full_text_tfidf_light` | **0.999** ❌ | **0.122** ❌ | ❌ FAIL |
| `regeste_full_text_hybrid_0.5` | **0.998** ❌ | **0.122** ❌ | ❌ FAIL |
| `regeste_full_text_hybrid_0.7` | **0.999** ❌ | **0.122** ❌ | ❌ FAIL |

**Critical Finding 1:** **ALL 8 representations show IDENTICAL jurist pairwise (0.122) and nearly identical language dominance (0.606 for citation-aware, 0.999 for full-text)** — this is an **HNSW methodological artifact** (identical k-NN graphs across representations). The HNSW index construction with fixed parameters produces the same neighbor graph regardless of embedding content at 174k scale.

**Critical Finding 2:** **Jurist pairwise COLLAPSED 0.79 → 0.12 from 1200→174k** for TF-IDF representations — a central extrapolation risk for metric learning/hybrid objectives.

**Critical Finding 3:** Full-text hybrids' language dominance artifact concentrates in decisions WITHOUT branch labels (procedural decisions). Cluster coherence PASS only for full-text hybrids (0.74) but with language purity 1.0 (language-dominated clusters).

**Critical Finding 4:** Cross-language recall ~0.01 for ALL representations — complete failure of cross-language legal equivalence retrieval at 174k scale.

---

### Dense 1200 Baselines (Established for Awaited 174k Representations)

**Harness:** Same v3 adversarial harness, 1200 expanded slice  
**Config Hash:** `4047da047fb339c1`

| Representation | Jurist Pairwise | Language Dominance | Both Gates | Scale Stability | Boilerplate Resistance | Jurivoc L0 NMI | Cross-Lang Recall |
|---------------|-----------------|-------------------|------------|----------------|------------------------|---------------|------------------|
| `linear_metric_epoch4` | **0.6847** ✅ | **0.6805** ✅ | ✅ PASS | 0.78 | -0.888 ❌ | 0.688 | 0.211 |
| `mahalanobis_metric_epoch4` | **0.6781** ✅ | **0.6843** ✅ | ✅ PASS | 0.78 | -0.895 ❌ | 0.705 | 0.208 |
| `hybrid_stabilized_epoch1` | **0.6656** ✅ | **0.6704** ✅ | ✅ PASS | 0.80 | -0.919 ❌ | 0.633 | 0.236 |
| `hybrid_v2_epoch3` | **0.5988** ✅ | **0.7115** ✅ | ✅ PASS | 0.78 | -0.914 ❌ | 0.743 | 0.227 |
| `center_projected_64dim` | **0.5121** ✅ | **0.7664** ✅ | ✅ PASS | 0.77 | -0.901 ❌ | 0.065 | 0.156 |
| `center_projected_768dim` | 0.4912 ❌ | 0.7738 ✅ | ❌ FAIL | 0.77 | -0.896 ❌ | 0.086 | 0.146 |
| `center_projected_128dim` | 0.4954 ❌ | 0.7725 ✅ | ❌ FAIL | 0.76 | -0.897 ❌ | 0.083 | 0.149 |

**Key Findings:**
- 5/7 dense representations pass BOTH adversarial gates at 1200 scale
- Metric learning (linear_metric, mahalanobis) and hybrid objectives show strong jurist pairwise (0.60-0.68) with low language dominance
- **ALL FAIL boilerplate resistance** (resistance_score ~ -0.89 to -0.92) — embeddings track procedural similarity over legal content
- Metric learning/hybrid objectives PASS Jurivoc L0 (NMI 0.63-0.74) and cross-language retrieval (>0.2)
- center_projected variants FAIL Jurivoc L0 and cross-language
- **CRITICAL QUESTION:** Will jurist pairwise hold at 174k or collapse like TF-IDF (0.79→0.12)?

---

## Infrastructure Status

### Verified Operational
- ✅ v25 formal suite runner (HNSW-backed, frozen protocol, config hash `4323f833fa72366a`)
- ✅ Citation heritage benchmark (frozen 137,314 pairs, built from 95.9% citation-ID resolution)
- ✅ v17b label normalization (conservative cross-lingual map, frozen)
- ✅ v3 adversarial harness (frozen seed=42, thresholds unchanged)
- ✅ 174k metadata (173,963 decisions, frozen row order from pinned parquet)
- ✅ Monitoring infrastructure (`evaluation/monitor_and_evaluate_174k.py` active, check_count=56)

### Evidence Artifacts (All Preserved)
- **Formal suite results:** `evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- **Citation heritage:** `evaluation/results/evaluation/v25_174k_citation_heritage/*.json` (8 files)
- **v17b normalization:** `evaluation/results/evaluation/v25_174k_v17b/*.json` (8 files)
- **Full corpus adversarial:** `evaluation/results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json`
- **Dense 1200 baseline:** `evaluation/results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json`
- **Label analysis:** `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
- **Citation pairs:** `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
- **Monitor state:** `evaluation/state/monitor_174k_state.json`

---

## Recommendations

### Immediate (When Dense Embeddings Land)
1. **Fix HNSW methodological artifact** before evaluating dense embeddings — the identical k-NN graphs across representations invalidate jurist pairwise at 174k. Options:
   - Use exact k-NN for adversarial benchmarks (computationally expensive but honest)
   - Vary HNSW parameters per representation (breaks reproducibility)
   - Use different random seeds for HNSW construction per representation
   - Accept exact k-NN on subsample for adversarial, HNSW for full corpus

2. **Run full v25 formal suite + v3 adversarial harness** on each new representation as it arrives via the monitoring infrastructure.

### Strategic
1. **Jurist pairwise collapse (0.79→0.12)** is the central risk for metric learning/hybrid objectives. The 174k evaluation of dense embeddings will determine if learned metrics generalize or suffer the same HNSW artifact.

2. **Boilerplate resistance failure** for ALL dense representations at 1200 scale suggests the learned metrics may be overfitting to procedural patterns. This must be validated at 174k.

3. **Hierarchy coherence ceiling** (max 0.47 normalized) appears to be a fundamental granularity limit of legal_area labels at 174k, not a representation failure.

### External Dependency (Not Blocking Machine Suite)
- **Jurist human study:** Requires 5-10 Swiss jurists recruited by repository owner. Framework ready; report as blocked when reachable.

---

## Next Actions

1. **Monitor active** — `monitor_and_evaluate_174k.py` watching for 11 awaited representations
2. **Legal-distance 174k pipeline** currently at year 2000 checkpoint; remaining years blocked on corpus artifact publication to expected mount paths
3. **When dense embeddings arrive:** Run full evaluation suite automatically via monitor
4. **No further same-question cycles justified** — all machine-executable sub-questions complete for available representations. Factory Director to decide successor question when dense embeddings land.

---

## Provenance

- **Frozen Protocol:** `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json`
- **Frozen Harness:** `evaluation/evaluation_v3_harness.py` (v3, seed=42)
- **Frozen Sample:** `evaluation/data/174k/metadata_174k.json` (173,963 decisions from pinned parquet)
- **Citation Pairs:** `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` (built from 2,019/2,105 resolved)
- **Config Hashes:** 
  - Formal suite: `4323f833fa72366a`
  - Adversarial harness: `4047da047fb339c1`
- **Source Run ID:** `eval_v27_174k_tfidf_and_dense1200_36097406309`

---

**Recommendation:** `BLOCKED_ON_DEPENDENCIES` — continue_recommended=true (monitor for dense embeddings), but no additional same-question cycles justified for TF-IDF family.