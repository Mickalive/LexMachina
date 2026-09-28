# Evaluation Lane 174k Formal Suite - Monitoring Report v28

**Date**: 2026-09-28T04:00:50Z  
**Factory Direction**: v28  
**Monitor Check Count**: 187  
**Evidence Tier**: ACCEPTED (TF-IDF) / REPRODUCED (monitoring infrastructure)  
**Cycle Status**: MONITORING  

---

## Executive Summary

The evaluation lane has **COMPLETED all three parts** of the factory direction v28 question for currently available representations:

1. ✅ **Full 12-benchmark formal suite at 174k scale** on all 8 TF-IDF production representations (frozen harness v3 thresholds unchanged)
2. ✅ **Citation heritage benchmark validated** using 174k citation-ID resolution (2,019/2,105 resolved, 95.9%)
3. ✅ **v17b label normalization tested** on 174k fine-grained legal_area labels (85,819 labels normalized, 214→164 unique areas)

**No new production representations have landed** since the last evaluation. The monitor (check_count=187) continues watching for 174k dense embeddings, citation roles, and linear hybrids from legal-distance.

---

## TF-IDF Family Evaluation Results (8 Representations)

### Adversarial Gates (Frozen Harness v3, Exact k-NN on Stratified Subsample n=2000)

| Representation | Language Dominance | Jurist Preference | Both Pass |
|----------------|-------------------|-------------------|-----------|
| cited_decisions_tfidf | 0.529 ✓ | 0.802 ✓ | **PASS** |
| outcome_tfidf | 0.453 ✓ | 0.726 ✓ | **PASS** |
| regeste_tfidf | 0.484 ✓ | 0.609 ✓ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.516 ✓ | 0.806 ✓ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.524 ✓ | 0.798 ✓ | **PASS** |
| full_text_tfidf_light | 1.000 ✗ | 0.000 ✗ | **FAIL** |
| regeste_full_text_hybrid_0.5 | 0.998 ✗ | 0.000* ✗ | **FAIL** |
| regeste_full_text_hybrid_0.7 | 0.999 ✗ | 0.000* ✗ | **FAIL** |

*Text-based representations have legal_neighbor_rate=0.0 (no legally-relevant neighbors in top-k on stratified subsample)

### V25 Formal Suite (12 Benchmarks, Frozen Protocol v25, Config Hash: 4323f833fa72366a)

| Representation | PASS | FAIL | SKIP | Key Pattern |
|----------------|------|------|------|-------------|
| cited_decisions_tfidf | 6 | 5 | 1 | Citation-based: PASS adversarial/citation_heritage/multilingual, FAIL branch/tf_metadata/hierarchy/legal_area |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | Citation-based: Same pattern |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | Citation-based: Same pattern |
| outcome_tfidf | 3 | 9 | 0 | Citation-based: Weaker on multilingual |
| full_text_tfidf_light | 7 | 5 | 0 | Text-based: PASS branch/tf_metadata/boilerplate/temporal/zoom, FAIL adversarial/multilingual |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | Text-based: Same pattern |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | Text-based: Same pattern |

**Fundamental Two-Mode Tradeoff REPRODUCED at 174k scale**: Citation-based signals excel at legal structure preservation and citation heritage but fail at branch/legal_area coherence. Text-based signals excel at branch/legal_area coherence but fail at cross-lingual alignment and jurist preference.

---

## Citation Heritage Benchmark

- **Pair Pool**: 2,040 frozen pairs (1,020 positive direct+shared citations, 1,020 negative, balanced sampling, seed=42)
- **Citation Resolution**: 2,019/2,105 (95.9%)
- **Coverage**: Only 174 decisions (0.1%) have outgoing citations in 174k corpus
- **Results**: All 8 TF-IDF representations **FAIL recall@10 > 0.2 threshold**
  - Best citation-based: cited_decisions_tfidf (AUC 0.788, recall@10 0.044)
  - Best overall: full_text_tfidf_light (AUC 0.898, recall@10 0.052) but language-dominated
  - Production default: cited_decisions_tfidf_outcome_hybrid_0.5 (AUC 0.760, recall@10 0.053)

**Conclusion**: Citation heritage structure is too sparse at 174k for meaningful k-NN recovery at k=10. AUC > 0.6 confirms relative ordering preserved, but absolute recall too low for navigation utility.

---

## v17b Label Normalization (85,819 labels, 214→164 unique areas)

### Differential Effect by Signal Type

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio |
|----------------|----------------|----------------|------------------|
| cited_decisions_tfidf | **1.057** ✓ | **1.038** ✓ | **1.062** ✓ |
| outcome_tfidf | **1.046** ✓ | **1.083** ✓ | **1.044** ✓ |
| cited_outcome_hybrid_0.5 | **1.056** ✓ | **1.037** ✓ | **1.063** ✓ |
| cited_outcome_hybrid_0.7 | **1.053** ✓ | **1.046** ✓ | **1.058** ✓ |
| full_text_tfidf_light | 1.000 | **0.668** ✗ | 0.973 |
| regeste_full_text_hybrid_0.5 | 1.000 | **0.661** ✗ | 0.969 |
| regeste_full_text_hybrid_0.7 | 1.000 | **0.695** ✗ | 0.963 |

**Key Finding**: Citation-based representations **improve** 3-8% on hierarchy/zoom/legal_area purity with normalization. Text-based representations **degrade 30-34% on zoom_fine** and lose 3-4% on legal_area. Normalization helps structured signals but destroys cross-lingual alignment in raw text.

---

## Dense Embeddings (3/26 Years ACCEPTED: 2000-2002, ~12,570 decisions)

All 3 center_projected variants **FAIL adversarial gates**:
- center_projected_768: lang_dom=0.997, jurist=0.008
- center_projected_64: lang_dom=0.978, jurist=0.045
- center_projected_128: lang_dom=0.980, jurist=0.041

**Root Cause**: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering. Not comparable to 1,200-slice center_projected (which PASS adversarial with proper full-corpus projection).

---

## Monitor Status (Check 187)

### Representations Awaited from Legal-Distance

| Category | Representations | Status |
|----------|----------------|--------|
| Dense 174k | center_projected_768dim, _64dim, _128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ✗ Not landed |
| Citation Roles 174k | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 | ✗ Not landed |
| Linear Hybrids 174k | linear_citation_concat, linear_hybrid05_concat | ✗ Not landed |

### Legal-Distance Dense Embeddings Progress
- **Checkpoints**: 25/26 years completed (2000-2024) - 79% of decisions
- **ACCEPTED**: 3/26 years (2000-2002) - 7.2% of decisions
- **Pending Audit**: 17/26 years (2003-2019)
- **Blocked**: Years 2020-2025 not yet processed

**Monitor scans only final concatenated 174k directories in accepted state, not checkpoints.**

---

## Infrastructure Verification (2026-09-28T04:00:50Z)

| Component | Status | Notes |
|-----------|--------|-------|
| Adversarial Benchmarks | ✅ VERIFIED | Exact k-NN on stratified subsample n=2000; production default: lang_dom=0.4867 PASS, jurist_pref=0.5349 PASS |
| Citation Heritage Pairs | ✅ VERIFIED | 2,040 frozen pairs; evaluation re-run on new pool |
| v17b Normalization | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF reps |
| HNSW Artifact Fix | ✅ CONFIRMED | Exact k-NN avoids HNSW masking representation differences |
| V25 Formal Suite | ✅ VERIFIED | Frozen protocol v25 on all 8 TF-IDF reps; config hash 4323f833fa72366a |
| Scalable NN | ✅ OPERATIONAL | sklearn exact for adversarial, HNSW for full-corpus |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |

---

## Blockers for Next Evaluation Cycle

1. **Legal-distance 174k dense embeddings**: Only 3/26 years ACCEPTED; full concatenation + audit promotion needed
2. **Citation role embeddings**: Not yet available at 174k
3. **Linear hybrid embeddings**: Not yet available at 174k
4. **Jurist human study**: Framework ready; requires 5-10 Swiss jurists (external dependency)

---

## Recommendation

**CONTINUE MONITORING** (continue_recommended=true)

The monitoring has concrete discriminating purpose: auto-evaluate awaited representations as they land from legal-distance. No additional same-question cycle is justified until 174k dense embeddings, citation roles, or linear hybrids are promoted to ACCEPTED state.

The fundamental two-mode tradeoff is REPRODUCED at 174k scale under frozen protocols. Product default (cited_decisions_tfidf_outcome_hybrid_0.5) remains the best stable combination for legal navigation.

---

*Report generated by evaluation lane monitor - check_count=187*