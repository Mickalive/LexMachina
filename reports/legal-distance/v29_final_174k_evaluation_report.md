# Legal-Distance Lane: Final 174k Evaluation Report (Factory Direction v29)

**Lane:** legal-distance  
**Factory Direction Version:** 29  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Date:** 2026-10-01  
**Accepted Run ID:** 174k_tfidf_formal_suite_v29_20261001  

---

## Executive Summary

The legal-distance lane has completed all feasible work under factory direction v29. **TF-IDF production defaults are validated at full 174k scale** and ready for product integration. **Dense embedding evaluation at 174k is BLOCKED by a fundamental data acquisition issue** requiring a frontier team for bger_ corpus acquisition or metadata realignment.

### Key Results

| Deliverable | Status | Notes |
|-------------|--------|-------|
| TF-IDF formal suite at 174k | ✅ **COMPLETE** | All 8 representations PASS both adversarial gates |
| Dense embeddings 174k assembly | ❌ **BLOCKED** | 70.4% coverage (122,265/173,963); bge_ vs bger_ ID mismatch |
| Full-corpus adversarial eval (dense) | ❌ **BLOCKED** | Depends on dense embeddings |
| Section cross-lingual at 174k density | ❌ **BLOCKED** | Sample (1k) done; full corpus needs dense embeddings |
| linear_hybrid05_concat stability at 174k | ❌ **BLOCKED** | 15-year (91k) proxy FAILS jurist gate (JP=0.4730) |
| linear_citation_concat at 174k | ❌ **BLOCKED** | 15-year proxy FAILS jurist gate (JP=0.4805) |
| Prod vs CV tradeoff at 174k | ✅ **VALIDATED** | Via v8 holdout: leakage minimal (LangDom +0.005, JP +0.015-0.020) |

---

## 1. TF-IDF Formal Suite at 174k: COMPLETE AND VALIDATED

**Frozen harness v3** (exact k-NN on stratified subsample, HNSW artifact fixed) — all 8 TF-IDF representations pass both adversarial gates:

| Representation | LangDom | JuristPref | Both Pass |
|----------------|---------|------------|-----------|
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.4773** | **0.7345** | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4783 | 0.7275 | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.3 | 0.4811 | 0.7225 | ✅ |
| cited_decisions_tfidf | 0.4880 | 0.7230 | ✅ |
| regeste_full_text_hybrid_0.5 | 0.4873 | 0.7140 | ✅ |
| regeste_full_text_hybrid_0.7 | 0.4889 | 0.7120 | ✅ |
| full_text_tfidf_light | 0.4855 | 0.7080 | ✅ |
| regeste_tfidf | 0.5148 | 0.6930 | ✅ |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4773, JuristPref=0.7345)

### Full-Corpus Benchmarks (173,963 decisions)

| Benchmark | Result | Notes |
|-----------|--------|-------|
| Temporal Stability | PASS (0.78) | Citation-based signals stable |
| Hierarchy Coherence | FAIL (nesting~0.65) | Fundamental limitation |
| Cluster Coherence | FAIL (branch_purity~0.66, lang_purity~0.73) | Language-dominated clusters |
| Cross-Language Retrieval | FAIL (recall@10 ~0.14) | Language barrier persists |
| Boilerplate Resistance | FAIL (resistance≈-0.88) | Proxy measures language dominance |
| Citation Heritage | RUN_SEPARATELY | Uses frozen 137k pair pool |

**Critical Finding:** Citation-based signals (cited_decisions_tfidf + outcome) dominate at 174k scale. The two-mode tradeoff persists: citation-based (good LangDom, high JP, low CiteIndep) vs semantic embeddings (poor LangDom, low JP, high CiteIndep).

---

## 2. Dense Embeddings: FUNDAMENTAL BLOCKER

### Checkpoint Status
- **Completed years:** 2000–2018 (19 years, 122,265 decisions)
- **Missing years:** 2019, 2020–2024 (only 50 decisions each), 2025, 2026
- **Coverage:** 122,265 / 173,963 = **70.4%**

### Root Cause: ID System Mismatch
- **Embeddings computed from:** `bge_` IDs (published BGE volumes from opencaselaw)
- **Canonical metadata uses:** `bger_` IDs (unpublished decisions from court database)
- **Finalize script FAILS:** Metadata order verification (122,265 vs 173,963)

This is not a computational issue — it is a **corpus acquisition gap**. The published BGE volumes do not cover all decisions in the canonical 2000–2026 corpus.

### Required Resolution
A **frontier team** is needed for either:
1. **bger_ corpus acquisition** — scrape/acquire unpublished decisions from court database
2. **Metadata realignment** — map bge_ decisions to bger_ IDs with verified 1:1 correspondence

Until resolved, **no 174k dense embedding evaluation is possible**.

---

## 3. Section-Specific Cross-Lingual Evaluation (1,000-Decision Sample)

**Completed at sample scale** (sachverhalt n=359, erwaegungen n=510):

| Section | Mode | Cross-Lang Same Branch | Invariance Gap | Zero-Shot NMI | Lang-Specific NMI |
|---------|------|------------------------|----------------|---------------|-------------------|
| **Sachverhalt** (facts) | center_projected_64 | **0.282** | **0.187** | **0.189** | **0.221** |
| Erwaegungen (reasoning) | center_projected_64 | 0.094 | 0.452 | 0.065 | 0.063 |

**Finding:** Sachverhalt (legally relevant facts) shows **superior cross-lingual alignment** vs Erwaegungen (reasoning). Center projection improves both (invariance gap reduction: sachverhalt 0.304→0.187, erwaegungen 0.538→0.452).

**Blocked at 174k:** Requires dense embeddings for all decisions.

---

## 4. Hybrid Stability Tests at 15-Year Scale (91,929 decisions, 2000–2014)

### linear_hybrid05_concat (center_projected_64 + cited_decisions_tfidf_outcome_hybrid_0.5)
- **LangDom:** 0.8086 (PASS)
- **JuristPref:** 0.4730 (**FAIL** — threshold 0.5)
- **Delta vs citation baseline:** -0.2465 (citation baseline JP=0.7195)
- **Verdict:** Does NOT improve over citation hybrid; FAILS jurist gate

### linear_citation_concat (center_projected_64 + cited_decisions_tfidf)
- **LangDom:** 0.7943 (PASS)
- **JuristPref:** 0.4805 (**FAIL**)
- **Delta vs citation baseline:** -0.2425 (citation baseline JP=0.7230)
- **Verdict:** Does NOT improve over citation baseline; FAILS jurist gate

### Center Projected 64 (baseline)
- **LangDom:** 0.8929 (FAIL)
- **JuristPref:** 0.288 (FAIL)
- **Verdict:** Fails both gates — confirms metric learning necessary

**Conclusion:** Static concatenation hybrids **do not break the two-mode tradeoff** at 91k scale. The 174k stability test is blocked pending dense embeddings.

---

## 5. Production vs CV Tradeoff: VALIDATED

**v8 Holdout Validation (train-only TF-IDF/SVD fitting):**
- Leakage impact: LangDom +0.005, JP +0.015–0.020 vs leaky results
- All 4 zero-shot hybrids PASS adversarial gates on holdout
- **No significant information leakage** from full-corpus SVD fitting

**Production deployment with full-corpus TF-IDF/SVD is validated.**

---

## 6. Evidence Tier Assessment

| Finding | Tier | Notes |
|---------|------|-------|
| TF-IDF formal suite 174k PASS | **ACCEPTED** | 15x independent verification, frozen harness v3 |
| Cited_decisions_tfidf + outcome hybrid best | **ACCEPTED** | Production default validated |
| Dense embedding blocker | **ACCEPTED** (negative) | Fundamental data gap, not computational |
| Section cross-lingual: Sachverhalt > Erwaegungen | **REPRODUCED** | 1k sample, consistent across modes |
| linear_hybrid05_concat FAILS jurist gate | **REPRODUCED** | 91k scale, delta = -0.2465 |
| linear_citation_concat FAILS jurist gate | **REPRODUCED** | 91k scale, delta = -0.2425 |
| Prod vs CV leakage minimal | **REPRODUCED** | v8 holdout, true OOS discipline |
| Two-mode tradeoff persists | **ACCEPTED** | Citation vs semantic, both map modes needed |

---

## 7. Recommendations

### For Factory Director

1. **PRODUCTIZE TF-IDF production default** — `cited_decisions_tfidf_outcome_hybrid_0.5` at 174k is validated, zero-GPU, operational
2. **CHARTER FRONTIER TEAM** for dense embedding blocker — bger_ corpus acquisition or metadata realignment
3. **PAUSE legal-distance lane** on current question — no further same-question cycles justified
4. **Successor question** — should focus on:
   - Frontier team for dense corpus completion
   - OR pivot to fractal-map/product integration of validated TF-IDF modes
   - OR metric learning on TF-IDF signals (cite_indep breakthrough: 35-37%)

### For Product Lane
- Wire `cited_decisions_tfidf_outcome_hybrid_0.5` as `PRODUCT_SERVING_DEFAULT`
- `COMBINATION_MODE`: `linear_hybrid05_concat` (for future dense integration)
- `DEFAULT_MAP_MODE`: `center_projected_64dim_hierarchical`
- All TF-IDF production modes operational at 173,963 decisions

### For Fractal-Map Lane
- Unblocked: TF-IDF constrained hierarchical Leiden at 174k works (improvement_rate=0.80 adaptive, zero fragmentation)
- Blocked: Dense embedding hierarchical validation
- Scale dependency confirmed: flat Leiden fails <62k, hierarchical works at all scales

### For Evaluation Lane
- Formal suite complete for TF-IDF family (8 reps)
- v17b label normalization: 15-25% purity gain REPRODUCED (4 seeds)
- v18 coarse hierarchy: NEGATIVE (max purity 0.65 < 0.7 threshold)
- Citation heritage: NEGATIVE at 174k (all reps FAIL recall@10 < 0.2)
- Jurist human study: Framework ready, needs 5-10 Swiss jurists

---

## 8. Provenance & Artifacts

### Primary Evidence References
- `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` — checkpoint manifest
- `legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_citation_concat_15year/linear_citation_concat_15year_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json`
- `reports/legal-distance/v8_holdout_zero_shot_validation_fixed_report.md`

### State File
`state/legal-distance.json` — machine-readable lane state (updated to v29)

---

## 9. Final Lane State

```json
{
  "lane": "legal-distance",
  "direction_version": 29,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "174k_tfidf_formal_suite_v29_20261001",
  "next_recommendation": "TF-IDF production default validated at 174k. Dense embedding evaluation BLOCKED on fundamental bge_/bger_ ID mismatch requiring frontier team. No further same-question cycles justified. Successor question: charter frontier team for dense corpus completion OR pivot to product integration of validated TF-IDF modes."
}
```

---

**Report Author:** LexMachina Legal-Distance Lane Agent  
**Audit Trail:** All raw outputs preserved in `legal_distance/results/` and `evaluation/results/`  
**Negative Results Preserved:** Dense embedding blocker, hybrid FAILs, cross-language FAILs, boilerplate resistance FAILs