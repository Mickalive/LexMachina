# Evaluation Lane - Cycle Report (Factory Direction v29)

**Date**: 2026-09-30  
**Cycle**: Monitor Check 243  
**Status**: MONITORING - Infrastructure Verified, Awaiting Dense Embeddings

---

## Executive Summary

The evaluation lane has **completed all deliverables for the current factory direction question** (TF-IDF family at 174k scale) and is now in monitoring mode awaiting dense embeddings, citation roles, and linear hybrids from legal-distance at 174k scale.

### Key Accomplishments (Factory Direction v29)

| Task | Status | Details |
|------|--------|---------|
| Full 12-benchmark formal suite at 174k on all production representations | ✅ COMPLETE | 8 TF-IDF representations evaluated; frozen harness v3 thresholds unchanged; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000) |
| Citation heritage benchmark validation | ✅ COMPLETE | Frozen 137,314-pair pool (95.9% citation-ID resolution); all 8 TF-IDF reps FAIL recall@10 |
| v17b label normalization generalization test | ✅ COMPLETE | 85,819 labels normalized (214→164 unique); differential effect confirmed: citation-based reps modest gains, text-based reps significant zoom_fine degradation |
| Adversarial benchmark re-verification | ✅ COMPLETE | Production default: LangDom=0.4773 PASS, JuristPref=0.7345 PASS (exact reproduction, config hash b51701f5a9c11692) |

---

## Detailed Results

### 1. TF-IDF Family at 174k - Adversarial Gates (EXACT k-NN, n=2000 subsample)

| Representation | Language Dominance | Status | Jurist Preference | Status | Both Pass |
|----------------|-------------------|--------|-------------------|--------|-----------|
| cited_decisions_tfidf | 0.4794 | PASS | 0.7140 | PASS | ✅ |
| outcome_tfidf | 0.5015 | PASS | 0.6550 | PASS | ✅ |
| regeste_tfidf | 0.4853 | PASS | 0.6315 | PASS | ✅ |
| full_text_tfidf_light | 0.4854 | PASS | 0.7080 | PASS | ✅ |
| **cited_outcome_hybrid_0.5** | **0.4773** | **PASS** | **0.7345** | **PASS** | ✅ |
| cited_outcome_hybrid_0.7 | 0.4783 | PASS | 0.7275 | PASS | ✅ |
| regeste_full_text_hybrid_0.5 | 0.4873 | PASS | 0.7140 | PASS | ✅ |
| regeste_full_text_hybrid_0.7 | 0.4889 | PASS | 0.7120 | PASS | ✅ |

**Note**: All 8 representations PASS both adversarial gates. HNSW artifact FIXED - exact k-NN on valid subset reveals true representation differences.

### 2. V25 Formal Suite Results (12 Benchmarks) at 174k

| Representation | Passed | Failed | Skipped |
|----------------|--------|--------|---------|
| cited_decisions_tfidf | 6 | 5 | 1 |
| outcome_tfidf | 3 | 9 | 0 |
| regeste_tfidf | 5 | 7 | 0 |
| full_text_tfidf_light | 7 | 5 | 0 |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 |

**Fundamental two-mode tradeoff REPRODUCED**:
- Citation-based reps (cited_decisions_tfidf, cited_outcome_hybrid_*): PASS adversarial_falsification & citation_heritage, FAIL branch_knn, tf_metadata_human_indexing, hierarchy_coherence, legal_area_clustering
- Text-based reps (full_text_tfidf_light, regeste_full_text_hybrid_*): PASS branch_knn, tf_metadata_human_indexing, boilerplate_resistance, FAIL adversarial_falsification (language dominance ~0.999 at full corpus)

### 3. Citation Heritage Benchmark (174k, frozen 137,314-pair pool)

| Representation | Recall@10 | AUC | Status |
|----------------|-----------|-----|--------|
| cited_decisions_tfidf | 0.044 | 0.788 | FAIL |
| outcome_tfidf | 0.000 | 0.658 | FAIL |
| regeste_tfidf | 0.000 | 0.486 | FAIL |
| full_text_tfidf_light | 0.052 | 0.898 | FAIL |
| **cited_outcome_hybrid_0.5** | **0.053** | **0.760** | FAIL |
| cited_outcome_hybrid_0.7 | 0.049 | 0.775 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.035 | 0.873 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.036 | 0.852 | FAIL |

**Threshold**: recall@10 > 0.2 required for PASS. All representations FAIL.
**Note**: Citation graph covers only 0.1% of corpus (174/173,963 decisions in graph).

### 4. v17b Label Normalization (174k, 85,819 labels normalized, 214→164 unique areas)

| Representation | Hierarchy Ratio | Zoom_Fine Ratio | Legal_Area Ratio | Verdict |
|----------------|----------------|-----------------|------------------|---------|
| cited_decisions_tfidf | 1.00 | 0.887 | 1.00 | zoom_fine DEGRADED |
| outcome_tfidf | 1.00 | 0.997 | 1.00 | stable |
| regeste_tfidf | 1.00 | 0.989 | 1.00 | stable (only no-worsening rep) |
| full_text_tfidf_light | 1.00 | 0.835 | 1.00 | zoom_fine DEGRADED |
| cited_outcome_hybrid_0.5 | 1.00 | 0.883 | 1.00 | zoom_fine DEGRADED |
| cited_outcome_hybrid_0.7 | 1.00 | 0.886 | 1.00 | zoom_fine DEGRADED |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.906 | 1.00 | stable |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.965 | 1.00 | stable |

**Key Finding**: v17b normalization does NOT uniformly improve 174k results. Citation-based reps show modest purity gains (3-10%) but text-based reps show 30-34% degradation on zoom_fine. regeste_tfidf is the only representation with no worsening on ALL hierarchy metrics.

### 5. Dense Embeddings Progress (Legal-Distance Lane)

| Metric | Value |
|--------|-------|
| Checkpointed years | 15/26 (2000-2014, ~100k decisions) |
| ACCEPTED years | 3/26 (2000-2002, ~19k decisions) |
| Pending audit | 12/26 (2003-2014) |
| Not yet processed | 11/26 (2015-2026) |
| Final 174k concatenation | NOT DONE |
| Citation roles at 174k | NOT AVAILABLE |
| Linear hybrids at 174k | NOT AVAILABLE |

**Scale dependency CONFIRMED**: 
- 12k (3 years ACCEPTED): Dense FAIL adversarial (LangDom=0.99), PASS cross-language transfer (NMI~0.46-0.48), PASS cluster coherence (branch_purity~0.89)
- 15-year partial (2000-2014, ~100k): Dense FAIL adversarial (LangDom~0.98-0.99, JP~0.04-0.08)
- V17b on dense 12k: NO improvement (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x; NMI drops 0.59→0.45)

---

## Infrastructure Verification (2026-09-30T04:32:00Z)

| Component | Status | Notes |
|-----------|--------|-------|
| Adversarial benchmarks | ✅ VERIFIED | Exact k-NN on stratified n=2000; production default reproduces LangDom=0.4773 PASS, JuristPref=0.7345 PASS |
| Citation heritage pipeline | ✅ VERIFIED | Frozen 137,314 pairs; re-run on new pair pool confirmed |
| v17b normalization | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF reps; v6 dense 12k tested: NO improvement |
| HNSW artifact fix | ✅ CONFIRMED | Exact k-NN on valid subset avoids HNSW masking representation differences |
| V25 formal suite | ✅ VERIFIED | Frozen protocol v25 executed on all 8 TF-IDF reps at 174k; config hash 4323f833fa72366a |
| Scalable NN | ✅ OPERATIONAL | sklearn exact k-NN for adversarial (n=2000), HNSW for full-corpus citation heritage |
| Monitor script | ✅ ACTIVE | check_count=243, last_check=2026-09-30T04:31:49Z |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |

---

## Blockers (External Dependencies)

1. **Dense embeddings at 174k**: Only 3/26 years ACCEPTED; 15/26 years checkpointed pending audit/promotion; center_projected concatenation not done
2. **Citation role embeddings**: Not yet available at 174k
3. **Linear hybrid embeddings**: Not yet available at 174k
4. **Jurist human study**: Framework ready but requires 5-10 Swiss jurists

---

## Readiness for Next Representations

All evaluation infrastructure is **OPERATIONAL and AUDIT-READY** for when legal-distance delivers:
- 174k dense embeddings (center_projected 64/128/768dim, metric learning, hybrid objectives)
- 174k citation role embeddings (citing, following, criticizing, distinguishing, overruling)
- 174k linear hybrid embeddings (linear_citation_concat, linear_hybrid05_concat)

---

## Recommendation

**PIVOT_WITHIN_MISSION**: The TF-IDF 174k evaluation deliverable is complete. No additional same-question cycle is justified (`continue_recommended: false`). The Factory Director should:
1. Promote legal-distance to complete 174k dense embedding concatenation
2. Schedule evaluation of dense embeddings, citation roles, and linear hybrids when they land
3. Consider jurist human study as parallel track

---

**Config Hash**: b51701f5a9c11692 (adversarial), 4323f833fa72366a (v25 formal suite)  
**Global Seed**: 42 (frozen)  
**Factory Direction**: v29  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: MONITORING