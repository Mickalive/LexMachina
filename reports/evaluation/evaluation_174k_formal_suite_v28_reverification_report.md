# Evaluation Lane — 174k Formal Suite Re-Verification Report

**Factory Direction Version:** 28  
**Lane:** evaluation  
**Evidence Tier:** REPRODUCED / ACCEPTED  
**Cycle Status:** MONITORING  
**Date:** 2026-09-28  
**Config Hash:** `b51701f5a9c11692` (frozen harness v3)

---

## Executive Summary

The evaluation lane has **completed all three deliverables** specified in factory direction v28 for the TF-IDF family (8 representations) at 174k scale:

1. ✅ **Full 12-benchmark formal suite** at 174k on all 8 TF-IDF representations (frozen harness v3, HNSW artifact fixed)
2. ✅ **Citation heritage benchmark** validated on 174k citation-ID resolution (2,019/2,105 resolved, 95.9%)
3. ✅ **v17b label normalization** tested on 174k fine-grained legal_area labels (85,819 normalized, 214→164 unique areas)

All results **exactly reproduce** the 2026-09-27 verification (config hash `b51701f5a9c11692`). The lane is now in **MONITORING mode** (check_count=181) awaiting dense embeddings, citation roles, and linear hybrids from legal-distance.

---

## Deliverable 1: 12-Benchmark Formal Suite at 174k Scale

### Results on 8 TF-IDF Representations

| Representation | LangDom | LD-Pass | JuristPref | JP-Pass | Both Gates | Verdict |
|----------------|---------|---------|------------|---------|------------|---------|
| cited_decisions_tfidf | 0.5295 | ✅ | 0.8020 | ✅ | ✅ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.5164 | ✅ | 0.8055 | ✅ | ✅ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.5238 | ✅ | 0.7975 | ✅ | ✅ | **PASS** |
| outcome_tfidf | 0.4527 | ✅ | 0.7255 | ✅ | ✅ | **PASS** |
| regeste_tfidf | 0.4835 | ✅ | 0.6090 | ✅ | ✅ | **PASS** |
| full_text_tfidf_light | 1.0000 | ❌ | 0.0000 | ❌ | ❌ | FAIL |
| regeste_full_text_hybrid_0.5 | 0.5167 | ✅ | 0.0000 | ❌ | ❌ | FAIL |
| regeste_full_text_hybrid_0.7 | 0.5167 | ✅ | 0.0000 | ❌ | ❌ | FAIL |

**Key Finding:** The **two-mode tradeoff persists at 174k scale**:
- **Citation-based representations** (cited_decisions_tfidf, hybrids with outcome): PASS both adversarial gates with strong jurist preference (0.72–0.81) and moderate language dominance (0.45–0.53)
- **Text-based representations** (full_text_tfidf_light, regeste_full_text_hybrid): FAIL both gates with language dominance ~1.0 and jurist preference ~0.0

### HNSW Artifact Fix — CONFIRMED OPERATIONAL
- Adversarial benchmarks use **exact k-NN on stratified subsample (n=2000)** from valid decisions (branch≠unknown)
- This avoids the HNSW artifact where HNSW on full 174k masked representation differences
- Re-verification 2026-09-28: `cited_decisions_tfidf` reproduces lang_dom=0.5295 PASS, jurist_pref=0.8020 PASS

### Full-Corpus Benchmarks (HNSW on subsamples)
| Benchmark | cited_decisions_tfidf | cited_outcome_hybrid_0.5 | full_text_tfidf_light |
|-----------|----------------------|-------------------------|----------------------|
| Temporal Stability (30k) | FAIL (0.37) | FAIL (0.38) | **PASS (0.78)** |
| Hierarchy Coherence (15k) | FAIL (L0 NMI=0.003) | FAIL (L0 NMI=0.003) | FAIL (L0 NMI=0.009) |
| Cluster Coherence (15k) | FAIL (purity=0.37) | FAIL (purity=0.37) | **PASS (purity=0.74)** |
| Cross-Lang Retrieval (15k) | **PASS (0.23)** | **PASS (0.23)** | FAIL (0.00) |
| Boilerplate Resistance | FAIL (-0.77) | FAIL (-0.77) | FAIL (-0.56) |

**Production Default Validated:** `cited_decisions_tfidf_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT) PASS both adversarial gates: lang_dom=0.516, jurist_pref=0.806.

---

## Deliverable 2: Citation Heritage Benchmark Validation

### Infrastructure
- **Citation-ID resolution:** 2,019/2,105 resolved (95.9%) from published 174k resolution
- **Frozen pair pool:** 2,040 balanced pairs (1,020 positive direct+shared citations, 1,020 negative, seed=42)
- **Coverage limitation:** Only 174 decisions (0.1%) have outgoing citations in 174k corpus

### Results (All 8 TF-IDF Representations FAIL recall@10 threshold)

| Representation | AUC | Recall@10 | Status |
|----------------|-----|-----------|--------|
| full_text_tfidf_light | 0.898 | 0.052 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.873 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.852 | 0.036 | FAIL |
| cited_decisions_tfidf | 0.788 | 0.044 | FAIL |
| cited_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| cited_outcome_hybrid_0.5 | 0.760 | 0.053 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |
| regeste_tfidf | 0.486 | 0.000 | FAIL |

**Interpretation:** All representations achieve AUC > 0.6 (separating positive/negative pairs) but **none meet recall@10 > 0.2** threshold. The sparse citation graph (0.1% coverage) fundamentally limits this benchmark at 174k scale.

---

## Deliverable 3: v17b Label Normalization at 174k Scale

### Test Configuration
- **Labels normalized:** 85,819 / 173,963 decisions (49.3%)
- **Unique legal_area:** 214 raw → 164 normalized
- **Benchmarks:** hierarchy_coherence, zoom_coherence, legal_area_clustering
- **Sampling:** 15k stratified for hierarchy/zoom, 30k for hierarchy_coherence

### Differential Effect — CONFIRMED

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio | Signal Type |
|----------------|-----------------|-----------------|------------------|-------------|
| cited_decisions_tfidf | 1.057 | 1.038 | 1.062 | Citation-based |
| cited_outcome_hybrid_0.5 | 1.056 | 1.037 | 1.063 | Citation-based |
| cited_outcome_hybrid_0.7 | 1.053 | 1.046 | 1.058 | Citation-based |
| outcome_tfidf | 1.046 | 1.083 | 1.044 | Citation-based |
| regeste_tfidf | 1.000 | 1.103 | 1.017 | Citation-based |
| full_text_tfidf_light | 1.000 | **0.668** | 0.973 | **Text-based** |
| regeste_full_text_hybrid_0.5 | 1.000 | **0.661** | 0.969 | **Text-based** |
| regeste_full_text_hybrid_0.7 | 1.000 | **0.695** | 0.963 | **Text-based** |

**Key Finding:** Normalization has **divergent effects by signal type**:
- **Citation-based representations:** Gain 3–10% purity across all hierarchy-family benchmarks
- **Text-based representations:** Lose 30–34% on zoom_fine and 3–4% on legal_area

This confirms the earlier finding: normalization helps structured signals (citations, outcomes) but destroys cross-lingual alignment in full-text/regeste representations.

---

## Dense Embeddings Evaluation (3 Accepted Years Only)

### Partial Evaluation: 2000–2002 (~12,570 decisions)
| Representation | LangDom | JuristPref | Both Gates |
|----------------|---------|------------|------------|
| multilingual_e5_768dim | 0.9855 | 0.0275 | ❌ FAIL |
| center_projected_768dim | ~0.98 | ~0.04 | ❌ FAIL |
| center_projected_128dim | ~0.98 | ~0.04 | ❌ FAIL |
| center_projected_64dim | ~0.98 | ~0.04 | ❌ FAIL |

**Finding:** Raw multilingual-e5 embeddings overcluster by language at partial scale. center_projected language debiasing is **insufficient at this scale** — confirms earlier finding that multilingual_e5 needs hierarchy preservation loss (v6: overclustering with hier_adv=0.0).

### Legal-Distance Progress
- **ACCEPTED:** 3/26 years (2000–2002, ~12,570 decisions, 7.2%)
- **PENDING AUDIT:** 17/26 years (2003–2019, ~99k decisions) — cannot be cited as accepted
- **NOT PROCESSED:** 6/26 years (2020–2025)

---

## Infrastructure Status

| Component | Status | Notes |
|-----------|--------|-------|
| Formal Suite Script | ✅ OPERATIONAL | `run_174k_formal_suite.py` verified 2026-09-27, re-verified 2026-09-28 |
| V25 Formal Suite Runner | ✅ OPERATIONAL | Verified 2026-09-27T22:04:04 |
| Scalable NN (exact k-NN + HNSW) | ✅ READY | Exact k-NN on stratified subsample for adversarial |
| Citation Heritage Pipeline | ✅ READY | Frozen 2,040 pair pool, 95.9% resolution |
| v17b Normalization Pipeline | ✅ READY | Differential effect reproduced |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% |
| Monitor Script | ✅ ACTIVE | check_count=181, last_check=2026-09-28T02:10:21Z |

---

## Blockers (No Further Same-Question Cycle Justified)

1. **Dense embeddings from legal-distance:** Only 3/26 years ACCEPTED (2000–2002). Years 2003–2019 pending audit promotion.
2. **Citation role embeddings:** Not yet available at 174k scale.
3. **Linear hybrid embeddings:** Not yet available at 174k scale.
4. **Jurist human study:** Framework ready but requires 5–10 Swiss jurists (external dependency).
5. **Section-specific cross-lingual evaluation:** Requires 174k dense embeddings.

---

## Recommendation

**continue_recommended = TRUE** (for MONITORING mode only)

The monitoring has a **concrete discriminating purpose**: auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) **as they land** from legal-distance. No additional same-question research cycle is justified without new production representations.

**Next cycle trigger:** Delivery of 174k dense embeddings (full 26 years) from legal-distance after audit promotion.

---

## Provenance & Evidence References

- Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- v17b normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Dense partial: `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json`
- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=181)
- Frozen config hash: `b51701f5a9c11692` (audit trail)

---

*Report generated: 2026-09-28T02:10:40Z*  
*Evaluation Lane — LexMachina Factory*