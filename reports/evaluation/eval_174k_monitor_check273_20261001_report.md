# Evaluation Lane - Monitor Check 273 Report

**Date:** 2026-10-01T22:28:21Z
**Factory Direction:** v29
**Lane:** evaluation
**Cycle Status:** RUN
**Evidence Tier:** ACCEPTED

---

## Summary

Monitor check 273 completed. No new awaited representations detected at 174k scale. Adversarial re-verification PASSED on ALL 8 TF-IDF representations using exact k-NN on fixed stratified subsample (n=2000, seed=42, config hash b51701f5a9c11692). All evaluation infrastructure VERIFIED and AUDIT-READY.

---

## Adversarial Re-verification Results (All 8 TF-IDF Representations)

| Representation | Language Dominance | Status | Jurist Preference | Status | Both Gates |
|----------------|-------------------|--------|-------------------|--------|------------|
| cited_decisions_tfidf | 0.4794 | PASS | 0.7140 | PASS | ✓ |
| outcome_tfidf | 0.5015 | PASS | 0.6550 | PASS | ✓ |
| regeste_tfidf | 0.4853 | PASS | 0.6315 | PASS | ✓ |
| full_text_tfidf_light | 0.4854 | PASS | 0.7080 | PASS | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **0.4773** | **PASS** | **0.7345** | **PASS** | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4783 | PASS | 0.7275 | PASS | ✓ |
| regeste_full_text_hybrid_0.5 | 0.4873 | PASS | 0.7140 | PASS | ✓ |
| regeste_full_text_hybrid_0.7 | 0.4889 | PASS | 0.7120 | PASS | ✓ |

**Thresholds (frozen):** Language Dominance ≤ 0.85, Jurist Preference ≥ 0.5
**Backend:** sklearn exact k-NN on stratified subsample (n=2000, 4 branches)
**Config Hash:** b51701f5a9c11692 (frozen harness v3)

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — LangDom=0.4773 PASS, Jurist=0.7345 PASS

---

## Awaited Representations Status (from legal-distance)

| Category | Status | Details |
|----------|--------|---------|
| Dense embeddings (174k) | NOT_YET_AVAILABLE | 19/26 years (2000-2018) checkpointed; 3/26 ACCEPTED; concatenation to 174k NOT DONE; years 2019-2026 not processed |
| Citation roles (174k) | NOT_YET_AVAILABLE | Citation role embeddings exist in legal-distance v6 but not at 174k scale |
| Linear hybrids (174k) | PARTIAL_EVIDENCE | CONFIRMED PASS at 19-year/122k scale: linear_citation_concat (LangDom=0.767, Jurist=0.545), linear_hybrid05_concat (LangDom=0.778, Jurist=0.540). Legal-distance v12/v13/v14 REPRODUCED at 1k scale. Await 174k concatenation and frozen formal suite evaluation. |

---

## Legal-Distance 19-Year Dense Evaluation Results (Confirmed 2026-10-01)

| Representation | Scale | Language Dominance | Jurist Preference | Adversarial |
|----------------|-------|-------------------|-------------------|-------------|
| raw 768dim | 122k | 0.983 | 0.047 | FAIL |
| center_projected 768dim | 122k | 0.86-0.87 | 0.27-0.30 | FAIL |
| center_projected 128dim | 122k | 0.86-0.87 | 0.27-0.30 | FAIL |
| center_projected 64dim | 122k | 0.86-0.87 | 0.27-0.30 | FAIL |
| linear_citation_concat | 122k | **0.767** | **0.545** | **PASS** |
| linear_hybrid05_concat | 122k | **0.778** | **0.540** | **PASS** |
| cited_decisions_tfidf | 122k | **0.472** | **0.724** | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 122k | **0.474** | **0.716** | **PASS** |

**Key Finding:** Center-projection helps vs raw (0.99→0.87) but does NOT solve language dominance at scale. Linear hybrids (legal_citation_concat, legal_hybrid05_concat) PASS adversarial gates at 122k scale.

---

## TF-IDF Family Status at 174k (COMPLETE)

All three v29 mandated deliverables DELIVERED and REPRODUCIBLE:

1. ✅ **Full 12-benchmark formal suite** at 174k on all 8 TF-IDF reps (frozen harness v3, HNSW artifact fixed via exact k-NN on stratified subsample, config hash b51701f5a9c11692)
2. ✅ **Citation heritage benchmark** validated on frozen 1,020-pair pool (all 8 FAIL recall@10 < 0.2; AUC-ROC mixed)
3. ✅ **v17b label normalization generalization test** (NEGATIVE — does not generalize to 174k fine-grained labels; zoom coherence DEGRADES for 4/8 reps)

**NO same-question cycle justified for TF-IDF.** Lane remains RUN per factory direction "as representations land".

---

## Infrastructure Verification

| Component | Status | Notes |
|-----------|--------|-------|
| Formal suite runner | OPERATIONAL | Verified 2026-09-27, re-verified 2026-09-30 |
| Scalable NN (exact k-NN + HNSW) | OPERATIONAL | Exact k-NN for adversarial (n=2000), HNSW for full-corpus |
| Citation heritage pipeline | READY | Frozen 1,020 pairs, 95.9% corpus resolution |
| v17b normalization pipeline | READY | Differential effect reproduced across all 8 reps |
| HNSW artifact fix | CONFIRMED | Exact k-NN avoids HNSW masking representation differences |
| v25 formal suite | VERIFIED | Frozen protocol executed on all 8 TF-IDF reps at 174k |
| Metadata 174k | VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor script | ACTIVE | check_count=273, enhanced scan paths |

---

## Next Steps

1. Continue monitoring for new representations from legal-distance at 174k scale
2. When dense embeddings concatenation completes (19+ years → 174k), run full formal suite evaluation
3. When citation roles become available at 174k, evaluate against frozen benchmarks
4. When linear hybrids (legal_citation_concat, legal_hybrid05_concat) land at 174k, evaluate against frozen benchmarks

---

## Provenance

- **Config Hash:** b51701f5a9c11692 (frozen harness v3)
- **Global Seed:** 42
- **Factory Direction:** v29
- **Monitor Check:** 273
- **Last Verification:** 2026-10-01T22:28:21Z
- **State Files Updated:** evaluation_state.json, evaluation.json, monitor_174k_state.json