# Evaluation Lane — Factory Direction v28 Cycle Report

**Lane**: evaluation  
**Direction Version**: 28  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: MONITORING  
**Date**: 2026-09-28  
**Config Hash**: `b51701f5a9c11692` (frozen harness v3_174k_fixed, seed=42)

---

## Executive Summary

All three deliverables from the factory direction v28 evaluation question have been **completed and verified**:

| Deliverable | Status | Evidence |
|------------|--------|----------|
| **12-benchmark formal suite at 174k** | ✅ COMPLETE | 8 TF-IDF representations evaluated on frozen harness v3 with HNSW artifact fix (exact k-NN on stratified subsample) |
| **Citation heritage validation at 174k** | ✅ COMPLETE | Validated against published citation-ID resolution (2,019/2,105 resolved = 95.9%); benchmark infrastructure built and run on all 8 TF-IDF reps |
| **v17b label normalization at 174k** | ✅ COMPLETE | Tested on 173,963 decisions with 214→164 unique legal_area labels (49.3% normalized); divergent results by signal type confirmed |

**Key Finding**: The fundamental **two-mode tradeoff persists at 174k scale** — citation-based representations pass adversarial gates but fail hierarchy/cluster coherence; text-based representations pass branch coherence but fail adversarial gates due to language dominance (~1.0).

---

## 1. 174k Formal Suite Results (TF-IDF Family)

### Adversarial Gate Results (Frozen Thresholds: lang_dom < 0.85, jurist > 0.5)

| Representation | Language Dominance | Jurist Preference | Both Gates | Verdict |
|---------------|-------------------|-------------------|------------|---------|
| cited_decisions_tfidf | 0.529 ✓ | 0.802 ✓ | ✓ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.516 ✓ | 0.806 ✓ | ✓ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.524 ✓ | 0.798 ✓ | ✓ | **PASS** |
| outcome_tfidf | 0.453 ✓ | 0.726 ✓ | ✓ | **PASS** |
| regeste_tfidf | 0.484 ✓ | 0.609 ✓ | ✓ | **PASS** |
| full_text_tfidf_light | 1.000 ✗ | 0.000 ✗ | ✗ | **FAIL** |
| regeste_full_text_hybrid_0.5 | 0.999 ✗ | 0.000 ✗ | ✗ | **FAIL** |
| regeste_full_text_hybrid_0.7 | 1.000 ✗ | 0.000 ✗ | ✗ | **FAIL** |

**Production Default Validated**: `cited_decisions_tfidf_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT) passes both gates with strong jurist preference (0.806) and moderate language dominance (0.516).

### Full-Corpus Benchmark Summary (HNSW on subsamples)

| Benchmark | Best Result | Status |
|-----------|-------------|--------|
| Temporal Stability (30k subsample) | full_text_tfidf_light: 0.782 | PASS (text) / FAIL (citation) |
| Hierarchy Coherence (15k subsample) | full_text_tfidf_light: L1 NMI 0.565 | FAIL (all) |
| Cluster Coherence | full_text_tfidf_light: 0.740 purity | PASS (text) / FAIL (citation) |
| Cross-Language Retrieval (15k) | cited_decisions_tfidf: 0.232 | PASS (citation) / FAIL (text) |
| Boilerplate Resistance | All FAIL (negative resistance_score) | FAIL |

---

## 2. Citation Heritage Benchmark Validation

### Citation Graph Coverage (174k corpus)
- **Decisions in citation graph**: 174 / 173,963 (0.1%)
- **Decisions with outgoing citations**: 174 (0.1%)
- **Total citations**: 2,105
- **Resolved citations**: 2,019 (95.9%)
- **Resolved citations mapping to 174k corpus**: 924

### Benchmark Pairs Generated
- **Positive pairs** (direct + shared citations): 1,020
- **Negative pairs** (no citation relationship): 1,020 (balanced)

### Citation Heritage Results at 174k (AUC / Recall@10)

| Representation | AUC | Recall@10 | Status |
|---------------|-----|-----------|--------|
| full_text_tfidf_light | **0.898** | 0.052 | FAIL (lang-dom) |
| regeste_full_text_hybrid_0.5 | 0.873 | 0.035 | FAIL (lang-dom) |
| regeste_full_text_hybrid_0.7 | 0.852 | 0.036 | FAIL (lang-dom) |
| cited_decisions_tfidf | 0.788 | 0.044 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.760 | 0.053 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |
| regeste_tfidf | 0.486 | 0.000 | FAIL |

**Critical Finding**: All representations **FAIL** the citation_heritage benchmark (recall@10 < 0.2 threshold) due to **extremely sparse citation graph coverage** (only 0.1% of corpus has outgoing citations). Even the best citation-based representation achieves only 4.4% recall@10.

---

## 3. v17b Label Normalization at 174k Scale — **CORRECTED PER AUDIT CYCLE_36521692234**

### Label Transformation
- **Raw legal_area labels**: 214 unique values
- **Normalized legal_area labels**: 164 unique values (23% reduction)
- **Decisions normalized**: 85,819 / 173,963 (49.3%)
- **Subsample**: hierarchy_subsample_15000_seed42 (fixed). All ratios are **purity ratios** (normalized_purity / raw_purity).

### Purity Ratios: Normalized / Raw — **CORRECTED**

| Representation | Hierarchy Purity Ratio | Zoom Fine Purity Ratio | Legal Area Purity Ratio |
|---------------|------------------------|------------------------|-------------------------|
| **Citation-based** | | | |
| cited_decisions_tfidf | **1.523x** | **1.557x** | **1.489x** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **1.536x** | **1.510x** | **1.503x** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **1.541x** | **1.564x** | **1.461x** |
| outcome_tfidf | **1.513x** | **1.513x** | **1.513x** |
| regeste_tfidf | **1.637x** | **1.637x** | **1.637x** |
| **Text-based** | | | |
| full_text_tfidf_light | **1.000x** | **1.000x** | **1.000x** |
| regeste_full_text_hybrid_0.5 | **1.000x** | **1.000x** | **1.000x** |
| regeste_full_text_hybrid_0.7 | **1.000x** | **1.000x** | **1.000x** |

### NMI Ratios (for reference)

| Representation | Hierarchy NMI Ratio | Legal Area NMI Ratio |
|---------------|---------------------|----------------------|
| cited_decisions_tfidf | 0.942x | 0.918x |
| full_text_tfidf_light | 0.724x | 0.757x |
| regeste_full_text_hybrid_0.5 | 0.724x | 0.757x |

### Interpretation — **CORRECTED**

The **prior report misrepresented the magnitude and direction** of the v17b effect. The actual verified data shows:

- **Citation-based representations (5 reps):** show **LARGE purity gains (~49–64%, 1.49–1.64x)** across ALL three hierarchy metrics.
- **Text-based representations (3 reps):** show **NO CHANGE on purity metrics (1.00x)** across ALL three hierarchy metrics.
- NMI metrics show modest degradation for both families, but this does NOT correspond to the previously claimed "30-34% zoom_fine degradation" for text-based representations.
- The differential effect is REAL and REPRODUCED: citation-based purity improves ~50%, text-based purity is stable.
- Uniform improvement claim requires clarification: **purity improves for citation-based, is stable for text-based.**

---

## 4. Dense Embeddings Evaluation (3 ACCEPTED Years: 2000-2002)

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---------------|-------------------|-------------------|------------|
| raw_multilingual_e5_768dim | ~0.98 | ~0.04 | ✗ FAIL |
| center_projected_64dim | ~0.98 | ~0.04 | ✗ FAIL |
| center_projected_768dim | ~0.98 | ~0.04 | ✗ FAIL |

**Finding**: Multilingual E5 embeddings **overcluster by language** even after center projection. Language debiasing insufficient at this scale. Confirms earlier finding: multilingual_e5 needs hierarchy preservation loss.

---

## 5. HNSW Artifact Fix — Verified

The formal suite uses **exact k-NN (sklearn) on a fixed stratified subsample (n=2000)** for all adversarial benchmarks, eliminating the HNSW artifact where approximate nearest neighbors on the full 174k corpus masked representation differences.

- **Subsample**: Fixed stratified by branch (seed=42), 2000 decisions with known branch
- **Backend**: sklearn_exact (confirmed in all results)
- **Reproduction**: Independent re-run of cited_decisions_tfidf yielded identical results (lang_dom=0.5295, jurist=0.8020)

---

## 6. Blocked Dependencies (Awaiting legal-distance)

| Dependency | Status | Notes |
|------------|--------|-------|
| 174k dense embeddings (center_projected, metric learning, hybrids) | **BLOCKED** | Only 3/26 years ACCEPTED (2000-2002, ~12.6k decisions, 7.2%) |
| Citation role embeddings (citing/following/criticizing) | **BLOCKED** | Not yet available at 174k |
| Linear hybrid embeddings (linear_hybrid05_concat, etc.) | **BLOCKED** | Not yet available at 174k |
| Section-specific cross-lingual evaluation | **BLOCKED** | Requires 174k dense embeddings |

---

## 7. Accepted State Compliance

All mandatory fields from RESEARCH_PROTOCOL.md satisfied in `/evaluation/state/evaluation.json`:

```json
{
  "lane": "evaluation",
  "direction_version": 28,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "MONITORING",
  "continue_recommended": true,
  "accepted_run_id": "eval_174k_formal_suite_v28_20260928_reverified",
  "evidence_refs": [
    "evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json",
    "evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json",
    "evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json",
    "evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json"
  ],
  "next_recommendation": "TF-IDF family complete. Monitoring active for dense embeddings delivery."
}
```

---

## 8. Recommendation

**CONTINUE MONITORING** — No additional same-question cycle justified. The evaluation lane has completed its v28 deliverables. The monitor (check_count=182) will auto-evaluate awaited representations (174k dense embeddings, citation roles, linear hybrids) as they land from legal-distance.

**Next factory direction decision**: Successor question depends on legal-distance promoting 174k dense embeddings to ACCEPTED state.

---

## Evidence Artifacts

| Artifact | Path |
|----------|------|
| Formal suite (8 TF-IDF reps) | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Citation heritage benchmark | `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` |
| Citation pairs infrastructure | `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` |
| v17b label normalization | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |
| Dense 3-year evaluation | `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json` |
| Lane state | `evaluation/state/evaluation.json` |

---

*Report generated per RESEARCH_PROTOCOL.md §8. All negative results preserved. No benchmark weakened post hoc.*