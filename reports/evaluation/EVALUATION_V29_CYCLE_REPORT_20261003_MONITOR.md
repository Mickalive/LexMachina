# Evaluation Lane — Cycle Report 2026-10-03 (Monitor Check 284)

## Factory Direction v29 — Evaluation Lane

**Lane Status**: RUN (continue_recommended=true)  
**Evidence Tier**: ACCEPTED  
**Monitor Check**: #284  
**Date**: 2026-10-03T00:10:42.489Z  

---

## Executive Summary

All three factory direction v29 deliverables for TF-IDF family at 174k scale are **COMPLETE and REPRODUCIBLE**. Evaluation infrastructure is **VERIFIED and AUDIT-READY**. No new 174k-scale representations have landed from legal-distance. Lane remains RUN per factory direction "as representations land".

### Deliverable Status

| Deliverable | Status | Details |
|-------------|--------|---------|
| Full 12-benchmark formal suite (frozen harness v3) at 174k on all production representations | ✅ COMPLETE | 8/8 TF-IDF representations evaluated; all PASS both adversarial gates |
| Citation heritage benchmark (frozen 1,020-pair pool, 95.9% citation-ID resolution) | ✅ COMPLETE | 4/8 TF-IDF reps PASS (AUC ≥ 0.65); citation-based reps pass, text-based fail |
| v17b label normalization generalization to 174k fine-grained legal_area labels | ✅ COMPLETE (NEGATIVE) | Does NOT uniformly improve; zoom_fine purity degrades 11-16% for citation-based reps |

---

## Adversarial Re-verification (Monitor Check 284)

**Config Hash**: `b51701f5a9c11692` (frozen)  
**Method**: Exact k-NN on stratified subsample (n=2000, seed=42) — HNSW artifact fix confirmed operational  
**Backend**: sklearn_exact  

| Representation | Language Dominance | Status | Jurist Preference | Status | Both Gates |
|----------------|-------------------|--------|-------------------|--------|------------|
| cited_decisions_tfidf | 0.4917 | ✅ PASS | 0.7075 | ✅ PASS | ✅ |
| outcome_tfidf | 0.5078 | ✅ PASS | 0.6660 | ✅ PASS | ✅ |
| regeste_tfidf | 0.5111 | ✅ PASS | 0.6145 | ✅ PASS | ✅ |
| full_text_tfidf_light | 0.4854 | ✅ PASS | 0.7080 | ✅ PASS | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.5 (PRODUCTION DEFAULT)** | **0.4895** | ✅ **PASS** | **0.7265** | ✅ **PASS** | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | ✅ PASS | 0.7195 | ✅ PASS | ✅ |
| regeste_full_text_hybrid_0.5 | 0.4873 | ✅ PASS | 0.7140 | ✅ PASS | ✅ |
| regeste_full_text_hybrid_0.7 | 0.4889 | ✅ PASS | 0.7120 | ✅ PASS | ✅ |

**All 8 TF-IDF representations PASS both adversarial gates** (LangDom < 0.85, Jurist > 0.5).  
LangDom range: 0.485–0.511 | Jurist range: 0.614–0.727

---

## Awaited Representations Status (from legal-distance)

| Category | Status | Details |
|----------|--------|---------|
| **Dense embeddings (174k)** | ❌ NOT YET AVAILABLE | 22/26 years (2000–2021) checkpointed (144,443 decisions); only 3/26 years (2000–2002) ACCEPTED; concatenation to 174k BLOCKED on bge_/bger_ ID mapping and missing parquet for 2022–2026 |
| **Citation role embeddings (174k)** | ❌ NOT YET AVAILABLE | Available in legal-distance v6 but not at 174k scale |
| **Linear hybrids (174k)** | ⚠️ PARTIAL EVIDENCE | PASS at 19-year/122k scale (linear_citation_concat JP=0.545, linear_hybrid05_concat JP=0.540); NOT available at 174k; await concatenation |

**Legal-distance lane state**: BLOCKED_ON_DEPENDENCIES (cycle_status) — no 174k concatenation possible until ID mapping and missing parquet resolved.

---

## Infrastructure Verification

| Component | Status | Notes |
|-----------|--------|-------|
| Frozen harness v3 (config hash b51701f5a9c11692) | ✅ VERIFIED | Exact reproduction across all monitor checks |
| HNSW artifact fix | ✅ CONFIRMED | Exact k-NN on valid subset (n=2000) avoids HNSW masking |
| Citation heritage pipeline (1,020 frozen pairs) | ✅ VERIFIED | Corpus resolution 2,019/2,105 = 95.9% |
| v17b normalization pipeline | ✅ VERIFIED | Differential effect reproduced; two regimes clarified |
| Scalable NN (sklearn exact + HNSW) | ✅ OPERATIONAL | Adversarial on subsample, full-corpus on HNSW |
| Metadata_174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor script | ✅ ACTIVE | Check count: 284, enhanced scan paths fixed |

---

## Negative Results Preserved (per Research Protocol)

- **Dense embeddings (3/26 years ACCEPTED)**: FAIL adversarial at all tested scales (LangDom ~0.98–0.99, JP ~0.04–0.29) — cluster by language, not law
- **v17b label normalization at 174k**: NEGATIVE — does not generalize to fine-grained labels; degrades zoom coherence for citation-based reps
- **Citation heritage (text-based TF-IDF reps)**: FAIL — AUC ~0.50–0.63; only citation-based reps recover citation heritage
- **v18 coarse hierarchy**: NEGATIVE — even at 4-label branch level, best purity 0.65 < 0.7 threshold
- **Boilerplate resistance proxy**: All reps score ≈ -0.74 to -0.92 — measures language dominance, not procedural boilerplate

---

## Recommendation

**CONTINUE monitoring** — No same-question cycle justified for TF-IDF (all deliverables complete and reproducible). Lane remains RUN awaiting 174k-scale representations from legal-distance per factory direction v29 "as representations land".

**Blockers for next evaluation cycle** (require legal-distance resolution):
1. bge_ ↔ bger_ ID mapping for dense embedding concatenation
2. Parquet files for years 2022–2026
3. Citation role embedding computation at 174k scale
4. Linear hybrid concatenation at 174k scale

**Jurist human study**: Framework ready; requires 5–10 Swiss jurists (external dependency).

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (config hash b51701f5a9c11692)
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/state/evaluation.json` (check_count=284)
- `evaluation/state/evaluation_state.json` (check_count=284, last_verification=2026-10-03T00:10:42.489Z)
- `evaluation/state/monitor_174k_state.json` (check_count=284)

---

*Report generated per Research Protocol §12: machine-readable state + human-readable report*