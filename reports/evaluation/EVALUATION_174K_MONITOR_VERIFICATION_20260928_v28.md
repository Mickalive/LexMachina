# Evaluation Lane - Monitoring Cycle Report v28
**Date:** 2026-09-28T02:32:21+00:00  
**Factory Direction:** v28  
**Cycle Type:** Monitoring Verification (no new representations)  
**Evidence Tier:** ACCEPTED

---

## Executive Summary

The evaluation lane remains in **MONITORING** mode with all factory direction v28 deliverables **COMPLETE and ACCEPTED**. The monitor (check_count=182) confirms:

- ✅ **8/8 TF-IDF representations** at 174k scale present and evaluated
- ❌ **0/12 awaited representations** detected (174k dense embeddings, citation roles, linear hybrids)
- ✅ Infrastructure operational (exact k-NN adversarial benchmarks, citation heritage, v17b normalization)

**No new same-question cycle justified** — monitoring has concrete discriminating purpose: auto-evaluate awaited representations as they land from legal-distance.

---

## Factory Direction v28 Compliance Status

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| Formal suite 12 benchmarks at 174k | ✅ COMPLETE | All 8 TF-IDF reps on frozen harness v3 |
| Citation heritage validation | ✅ COMPLETE | 174k citation-ID resolution (2,019/2,105) |
| v17b label normalization at 174k | ✅ COMPLETE | Tested on fine-grained legal_area labels |
| Dense embeddings evaluation (3 ACCEPTED years) | ✅ COMPLETE | All FAIL adversarial gates (lang_dom ~0.98) |
| HNSW artifact fix | ✅ VERIFIED | Exact k-NN on stratified subsample |

---

## Key Findings (Re-confirmed)

### 1. Two-Mode Tradeoff Persists at 174k
| Representation Type | Examples | Lang Dom | Jurist Pref | Verdict |
|---------------------|----------|----------|-------------|---------|
| **Citation-based** | cited_decisions_tfidf, cited_outcome_hybrid_0.5/0.7 | 0.45–0.53 | 0.72–0.81 | ✅ PASS |
| **Text-based** | full_text_tfidf_light, regeste_full_text_hybrid_0.5/0.7 | ~1.0 | ~0.0 | ❌ FAIL |

**Production default** (`cited_decisions_tfidf_outcome_hybrid_0.5`): lang_dom=0.516, jurist_pref=0.806 — **PASS both gates**

### 2. Citation Heritage Limited by Sparse Graph
- Only 174 decisions (0.1%) have outgoing citations in 174k corpus
- All reps AUC > 0.6 but recall@10 < 0.2 threshold
- Best citation-based: `cited_decisions_tfidf` (AUC 0.788)
- Best overall: `full_text_tfidf_light` (AUC 0.898) but language-dominated

### 3. v17b Normalization Diverges by Signal Type
| Signal Type | Hierarchy | Zoom Fine | Legal Area |
|-------------|-----------|-----------|------------|
| Citation-based | +3–8% | +3–4% | +3–8% |
| Text-based | ~0% | **−30–34%** | −3–4% |

Normalization helps structured signals but destroys cross-lingual alignment in text.

### 4. Dense Embeddings (3 ACCEPTED years) FAIL Adversarial
- Raw multilingual-e5 overclusters by language at 12.5k scale
- center_projected (language debiasing) insufficient: lang_dom ~0.98, jurist ~0.04
- Confirms: multilingual_e5 needs hierarchy preservation loss

---

## Monitor Status (check_count=182)

### Detected Representations
```
✅ COMPLETED (TF-IDF family at 174k):
   ✓ cited_decisions_tfidf
   ✓ outcome_tfidf
   ✓ cited_decisions_tfidf_outcome_hybrid_0.5
   ✓ cited_decisions_tfidf_outcome_hybrid_0.7
   ✓ regeste_tfidf
   ✓ full_text_tfidf_light
   ✓ regeste_full_text_hybrid_0.5
   ✓ regeste_full_text_hybrid_0.7

❌ AWAITED (dense embeddings, citation roles, linear hybrids):
   awaited_dense_174k:       0/8 detected
   awaited_citation_roles_174k: 0/3 detected
   awaited_linear_hybrids_174k: 0/2 detected
```

### Legal-Distance Dense Embeddings Progress (from checkpoints)
- **Completed in checkpoints:** 20/26 years (2000–2019, ~137k decisions, 79%)
- **ACCEPTED (promoted):** 3/26 years (2000–2002, ~12.5k decisions, 7.2%)
- **Pending audit:** 17/26 years (2003–2019)
- **Not yet processed:** 6/26 years (2020–2025)

*Monitor correctly scans only final concatenated directories in accepted state, not checkpoints.*

---

## Blocked Dependencies (Unchanged)

1. **Legal-distance 174k dense embeddings:** Only 3/26 years ACCEPTED
2. **Citation role embeddings:** Not yet available at 174k scale (v5/v6 at 1000-scale only)
3. **Linear hybrid embeddings:** Not yet available at 174k scale
4. **Section-specific cross-lingual evaluation:** Requires 174k dense embeddings

---

## Infrastructure Verification

| Component | Status | Notes |
|-----------|--------|-------|
| HNSW backend | OPERATIONAL | Fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) |
| Scalable NN | OPERATIONAL | sklearn exact fallback for adversarial benchmarks |
| v25 formal suite | OPERATIONAL | NoneType.lower bug fixed |
| Citation heritage | FROZEN | 2,040 pairs ready (174k citation-ID resolution) |
| v17b normalization | OPERATIONAL | 85,819 labels normalized (214→164 unique areas) |
| Monitor script | ACTIVE | Enhanced scan: fractal-map for TF-IDF, legal-distance for dense |

**HNSW Artifact Confirmed:** HNSW with fixed parameters produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale. Exact k-NN on valid subset (1199 decisions with known branch) shows jurist pairwise 0.73–0.80; HNSW on full corpus shows 0.12 for all.

---

## Recommendation

**CONTINUE MONITORING** — `continue_recommended=true`

The monitoring cycle has concrete discriminating purpose: automatically evaluate awaited representations (174k dense embeddings, citation roles, linear hybrids) as they land in accepted state from legal-distance. No additional same-question evaluation cycle is justified without new representation delivery.

**Next action trigger:** Legal-distance promotes 174k dense embeddings, citation roles, or linear hybrids to accepted state → monitor auto-evaluates full formal suite.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
3. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
4. `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
5. `evaluation/state/monitor_174k_state.json` (check_count=182)

---

*Report generated by evaluation lane monitoring verification cycle. All findings reproducible with config hash `b51701f5a9c11692` (frozen harness v3, seed=42).*