# Evaluation Lane — Factory Direction v28 Status Report

**Date:** 2026-09-28  
**Lane:** evaluation  
**Direction Version:** 28  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false

---

## Summary

The evaluation lane has **completed all three deliverables** specified in factory direction v28:

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| Full 12-benchmark formal suite at 174k on all production representations | ✅ COMPLETE | 8 TF-IDF reps evaluated on frozen harness v3 thresholds |
| Citation heritage benchmark validated on 174k citation-ID resolution | ✅ COMPLETE | 2,019/2,105 citation IDs resolved; benchmark run on frozen pair pool |
| v17b label normalization tested on 174k fine-grained legal_area labels | ✅ COMPLETE | Divergent results by signal type confirmed |

**Lane is BLOCKED_ON_DEPENDENCIES** — no further same-question cycle justified without legal-distance delivering 174k dense embeddings (only 3/26 years ACCEPTED).

---

## Key Results

### TF-IDF Family (8 representations) — 174k Scale

| Representation | Verdict | Lang Dominance | Jurist Preference | Both Gates |
|----------------|---------|----------------|-------------------|------------|
| cited_decisions_tfidf | PASS | 0.529 | 0.802 | ✅ |
| outcome_tfidf | PASS | 0.453 | 0.726 | ✅ |
| regeste_tfidf | PASS | 0.484 | 0.609 | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | PASS | 0.516 | 0.806 | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | PASS | 0.524 | 0.798 | ✅ |
| full_text_tfidf_light | FAIL | 1.000 | 0.000 | ❌ |
| regeste_full_text_hybrid_0.5 | FAIL | 0.999 | 0.000 | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 0.999 | 0.000 | ❌ |

**Fundamental two-mode tradeoff persists at 174k:**
- **Citation-based reps** (5/8): PASS both adversarial gates, strong jurist preference (0.72–0.81), moderate language dominance (0.45–0.53)
- **Text-based reps** (3/8): FAIL both gates, language dominance ~1.0, jurist preference ~0.0

### Citation Heritage Benchmark
- **Coverage limitation:** Only 174 decisions (0.1% of 174k) have outgoing citations
- All reps achieve AUC > 0.6 but recall@10 < 0.2 threshold
- `cited_decisions_tfidf` best citation-based (AUC 0.788)
- `full_text_tfidf_light` best overall AUC (0.898) but language-dominated

### v17b Label Normalization (174k fine-grained legal_area)
| Signal Type | Hierarchy | Zoom Fine | Legal Area |
|-------------|-----------|-----------|------------|
| Citation-based | +3–8% | +3–8% | +4–6% |
| Text-based | 0% | **-30–34%** | -3–4% |

Normalization helps structured signals (citations, outcomes) but destroys cross-lingual alignment in text.

### Dense Embeddings (3 ACCEPTED years: 2000–2002, ~12,570 decisions)
- **All FAIL adversarial gates** — language dominance ~0.98, jurist preference ~0.04
- `center_projected` (language debiasing) insufficient at this scale
- Confirms: multilingual-e5 needs hierarchy preservation loss, not just centering

### Production Default Validated
- `cited_decisions_tfidf_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT): **PASS both gates**
- lang_dom = 0.516, jurist_pref = 0.806
- Best stable combination per v15b evidence

---

## Infrastructure Verification (Re-verified 2026-09-28T08:30 UTC)

| Check | Status | Detail |
|-------|--------|--------|
| Embedding artifact integrity | ✅ PASSED | 8/8 embeddings: correct shape (173963, 128), dtype float32, all finite |
| Fixed subsample determinism | ✅ PASSED | Seed=42, stratified 2000-subsample deterministic; lang_dom=0.5295 exact match |
| Frozen harness v3 reproducibility | ✅ PASSED | All baseline reps reproduce within 0.001 tolerance |

---

## Blocked Dependencies

1. **Legal-distance 174k dense embeddings:** Only 3/26 years (2000–2002, ~12,570 decisions, 7.2%) ACCEPTED
2. **Citation role embeddings** not yet available at 174k scale
3. **Linear hybrid embeddings** not yet available at 174k scale
4. **Section-specific cross-lingual evaluation** requires 174k dense embeddings

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — The evaluation lane has no further work at 174k scale until legal-distance delivers dense embeddings, citation role embeddings, or linear hybrids at full corpus scale. The current evidence tier is ACCEPTED; all claim-bearing results are preserved. The Factory Director should advance the legal-distance lane to unblock evaluation.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- `state/evaluation.json` (machine-readable lane state)