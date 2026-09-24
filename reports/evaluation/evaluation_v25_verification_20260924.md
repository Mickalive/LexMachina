# Evaluation Lane v25 Verification Report

**Date:** 2026-09-24  
**GitHub Run:** 35990980088  
**Factory Direction Version:** 25  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED

---

## Executive Summary

This cycle performed fresh verification of all evaluation infrastructure ahead of 174k-scale execution. All frozen harnesses and benchmarks REPRODUCED exactly at 1200 scale, and 174k benchmark infrastructure is validated and ready. The lane remains **BLOCKED_ON_DEPENDENCIES** awaiting 174k production representations from legal-distance (active gh run 35935612800).

### Key Verification Results

| Verification | Status | Details |
|--------------|--------|---------|
| v3 Frozen Harness | ✅ REPRODUCED | 6 representations tested, config hash `a31c443a9b0e992e` |
| v16 Full Benchmark Suite | ✅ REPRODUCED | 6 representations, pass counts match accepted results |
| v17b Label Normalization | ✅ REPRODUCED | 6 representations, uniform 15-28% purity improvement |
| Citation Heritage 174k | ✅ VALIDATED | 1,020 positive + 1,020 negative pairs ready |
| Scalable NN (HNSW) | ✅ OPERATIONAL | Exact NN <10k, HNSW ≥10k, distributed support |

---

## Detailed Verification Results

### 1. v3 Frozen Evaluation Harness (1200 Scale)

**Config Hash:** `a31c443a9b0e992e` (matches frozen spec)  
**Seed:** 42  
**Representations Tested:** 6

| Representation | Verdict | LangDom | Jurist Pref | Both Adv Gates |
|----------------|---------|---------|-------------|----------------|
| center_projected_768 | FAIL | 0.7738 ✓ | 0.4912 ✗ | ✗ |
| center_projected_64dim | **PASS** | 0.7664 ✓ | 0.5121 ✓ | ✓ |
| linear_metric_epoch4 | **PASS** | 0.6805 ✓ | 0.6847 ✓ | ✓ |
| mahalanobis_metric_epoch4 | **PASS** | 0.6843 ✓ | 0.6781 ✓ | ✓ |
| hybrid_stabilized_epoch1 | **PASS** | 0.6704 ✓ | 0.6656 ✓ | ✓ |
| hybrid_v2_epoch3 | **PASS** | 0.7115 ✓ | 0.5988 ✓ | ✓ |

**Best Representation:** `linear_metric_epoch4` (jurist_pref=0.6847, lang_dom=0.6805)  
**Reference Baseline:** `center_projected_64dim` passes both adversarial gates (production default)

### 2. v16 Full 12-Benchmark Suite (1200 Scale)

**Config Hash:** `4323f833fa72366a`  
**Seed:** 42  
**Representations Tested:** 6

| Representation | Passed/Total | Key Failures |
|----------------|--------------|--------------|
| center_projected_64dim | 7/12 | hierarchy, zoom, legal_area, boilerplate |
| cited_outcome_hybrid_0.5 | 6/12 | tf_metadata, hierarchy, zoom, legal_area, boilerplate |
| linear_citation_concat | 7/12 | hierarchy, zoom, legal_area, boilerplate |
| linear_hybrid05_concat | 7/12 | hierarchy, zoom, legal_area, boilerplate |
| linear_citation_w3070 | 6/12 | tf_metadata, hierarchy, zoom, legal_area, boilerplate |
| linear_citation_ridge | 7/12 | hierarchy, zoom, legal_area, boilerplate |

**Universal PASS (all 6 reps):** branch_knn, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability  
**Universal FAIL (all 6 reps):** hierarchy_coherence, zoom_coherence, legal_area_clustering, boilerplate_resistance_real_corpus

**Note:** citation_heritage SKIP (0 positive pairs in 1200 slice). Universal failures are corpus/label limitations per v16/v18 findings.

### 3. v17b Label Normalization (1200 Scale, All 6 Representations)

**Labels Normalized:** 788/1200 (65.7%)  
**Unique Labels:** 104 → 54 (-48%)

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio |
|----------------|-----------------|-----------------|------------------|
| center_projected_64dim | 1.2018 ✓ | 1.2233 ✓ | 1.1476 ✓ |
| cited_outcome_hybrid_0.5 | 1.2145 ✓ | 1.2041 ✓ | 1.1514 ✓ |
| linear_citation_concat | 1.1891 ✓ | 1.1941 ✓ | 1.1273 ✓ |
| **linear_hybrid05_concat** | **1.2401** ✓ | **1.2768** ✓ | 1.1528 ✓ |
| linear_citation_w3070 | 1.1559 ✓ | 1.1798 ✓ | 1.1300 ✓ |
| linear_citation_ridge | 1.1940 ✓ | 1.2145 ✓ | 1.1524 ✓ |

**Uniform Improvement:** ✅ CONFIRMED — No representation worsens by >10% on any metric  
**Best:** `linear_hybrid05_concat` (hierarchy 1.24x, zoom 1.28x)

**Finding:** v16 hierarchy-family FAIL is primarily a label normalization artifact (cross-lingual duplication), not a representation defect. However, normalization alone does NOT flip benchmarks to PASS (hierarchy best_purity 0.467 < 0.7 threshold), indicating residual fine granularity.

### 4. Citation Heritage Benchmark (174k Scale)

**Corpus:** 173,963 decisions (de: 106,501, fr: 57,489, it: 9,973)  
**Citation Graph:** 174 decisions with outgoing citations, 2,105 total citations, 2,019 resolved (95.9%)  
**Mapped to Corpus:** 924 resolved citations  
**Positive Pairs:** 1,020 (direct + shared citations)  
**Negative Pairs:** 1,020 (sampled, no citation relation)  

**Status:** ✅ INFRASTRUCTURE READY — Benchmark ready for 174k embeddings when available

### 5. Scalable Evaluation Infrastructure

| Component | Status | Details |
|-----------|--------|---------|
| HNSW Backend | ✅ OPERATIONAL | hnswlib available, M=16, ef_construction=200, ef_search=100 |
| Exact NN Fallback | ✅ OPERATIONAL | sklearn brute-force for <10k decisions |
| Batched Processing | ✅ IMPLEMENTED | Batch size 5,000, all 12 benchmarks |
| Distributed Evaluation | ✅ SUPPORTED | Model-level sharding via DistributedEvaluator |
| Config Hash (full_corpus) | ✅ VERIFIED | `4047da047fb339c1` matches frozen spec |

---

## Blockers & Dependencies

### BLOCKED_ON_DEPENDENCIES
**Dependency:** legal-distance lane 174k production representations  
**Active Work:** gh run 35935612800 (year-split TF-IDF computation)  
**Representations Awaited (14):**
- TF-IDF modes: `cited_decisions_tfidf`, `outcome_tfidf`, `cited_outcome_hybrid_0.5`, `cited_outcome_hybrid_0.7`
- Dense: `center_projected_768dim`, `center_projected_64dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`
- Citation roles: `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3`
- Combinations: `linear_citation_concat`, `linear_hybrid05_concat`

### No HUMAN_DECISION_REQUIRED States
All infrastructure is machine-executable. Compute on free public runners is an operational constraint routed autonomously per Main Prompt anti-thrift clause.

---

## Next Steps

1. **WAIT** for legal-distance to deliver 174k production representations
2. **EXECUTE** full 174k formal suite automatically when representations land:
   - v3 frozen harness on all 14 representations (HNSW backend)
   - v16 12-benchmark suite on all 14 representations (scalable_nn)
   - v17b label normalization verification at 174k clustering level
   - citation_heritage AUC-ROC on 1,020 positive/negative pairs
3. **REPORT** results and update lane state

---

## Evidence Preservation

All raw outputs preserved in:
- `results/evaluation/v3/evaluation_v3_results.json` (v3 harness)
- `results/evaluation/v16_full_benchmark_suite/v16_full_benchmark_latest.json` (v16 suite)
- `results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json` (v17b)
- `results/evaluation/174k_citation_heritage/citation_pairs_174k.json` (citation heritage)

Negative results (universal FAIL on hierarchy/zoom/legal_area/boilerplate) preserved as first-class evidence per Research Protocol.

---

## Compliance with Research Protocol

✅ Hypothesis, baseline, and success rules frozen before observation  
✅ Smallest rigorous discriminating experiments executed  
✅ Raw outputs and failures preserved  
✅ Comparison with baseline (v16 accepted results) reported  
✅ Machine-readable lane state updated  
✅ Human-readable report written  
✅ Recommendation: BLOCKED_ON_DEPENDENCIES (no additional same-question cycle justified)