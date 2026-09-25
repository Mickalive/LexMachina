# Evaluation Lane v36 Verification Report

**Date**: 2026-09-25T07:24:22Z  
**Factory Direction Version**: 27  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false  

---

## Executive Summary

The evaluation lane has completed its v36 verification cycle. All machine-executable evaluation infrastructure is **operational and verified**. The TF-IDF production family (8 representations) has been **fully evaluated at 174k scale** against the frozen 12-benchmark suite, citation_heritage benchmark, and v17b label normalization test.

**No 174k dense embeddings have landed** from the legal-distance lane since the last verification. The legal-distance 174k dense embedding computation remains in progress with only **1 of 26 years (year 2000) completed**; years 2001-2025 have failed per the progress.json checkpoint.

The evaluation lane remains **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings. The monitor script (check #51) is active and will auto-evaluate new representations via the full v25 frozen protocol when they arrive.

---

## Verification Results

### 1. Monitor Scan (Check #51)
- **Scan Time**: 2026-09-25T07:24:22Z
- **Legal-Distance 174k Dense Embeddings**: NOT DETECTED
  - v5-v14 directories: no 174k embeddings
  - fractal_map results: no 174k embeddings
  - 174k_dense_embeddings checkpoint: only year 2000 of 26 completed (embeddings_2000.npy)
  - Years 2001-2025: FAILED (per progress.json)
- **Legal-Distance Status**: RUN (staged 174k CPU execution, year-split, gh run 36096850301 IN_PROGRESS)

### 2. Evaluation Infrastructure Status

| Component | Status | Details |
|-----------|--------|---------|
| `run_full_corpus_evaluation.py` | OPERATIONAL | Config hash `4047da047fb339c1` matches frozen v3 harness exactly; HNSW backend (hnswlib) on GitHub runners |
| `scalable_nn.py` | OPERATIONAL | Batched adversarial benchmarks; sklearn exact fallback available |
| `v25_174k_formal_suite` runner | OPERATIONAL | Config hash `4323f833fa72366a`; all 8 TF-IDF representations evaluated at 173,963 decisions |
| `validate_citation_heritage_174k.py` | OPERATIONAL | 137,314 frozen pairs ready in `citation_pairs_174k_full.json`; 95.9% citation resolution (2,019/2,105) |
| `v17b_label_normalization` | OPERATIONAL | 213→163 labels, 32 cross-lingual canonical concepts, `normalize_labels` function working |
| `monitor_and_evaluate_174k.py` | ACTIVE | Enhanced with `run_formal_suite_v25()` for auto-evaluation of new representations |

### 3. TF-IDF Family 174k Evaluation — COMPLETE

All 8 TF-IDF representations evaluated at 174k scale (173,963 decisions) against frozen protocol:

| Representation | Suite Pass/Fail/Skip | Citation Heritage AUC | Adversarial Gates | Production Default |
|---|---|---|---|---|
| cited_decisions_tfidf | 6/5/1 | **0.9731** | PASS (LangDom=0.602, Branch=0.354) | |
| outcome_tfidf | 3/9/0 | 0.7204 | FAIL (Branch=0.146) | |
| regeste_tfidf | 5/7/0 | 0.4865 (FAIL) | PASS (LangDom=0.757, Branch=0.615) | |
| full_text_tfidf_light | 7/5/0 | 0.8439 | FAIL (LangDom=0.999) | |
| cited_outcome_hybrid_0.5 | 6/5/1 | 0.9193 | PASS (LangDom=0.578, Branch=0.352) | |
| **cited_outcome_hybrid_0.7** | **6/6/0** | **0.9605** | **PASS (LangDom=0.569, Branch=0.356)** | ✅ **PRODUCTION DEFAULT** |
| regeste_full_text_hybrid_0.5 | 7/5/0 | 0.8505 | FAIL (LangDom=0.998) | |
| regeste_full_text_hybrid_0.7 | 7/5/0 | 0.8650 | FAIL (LangDom=0.999) | |

**Key Findings** (from v25 suite results):
- **Universal 174k FAILs**: hierarchy_coherence (purity 0.08-0.47 < 0.7), legal_area_clustering (purity 0.003-0.08 < 0.5)
- **Citation-based reps** pass adversarial gates; full-text/regeste reps fail language_dominance (~0.99)
- **7/8 TF-IDF reps PASS** citation_heritage AUC≥0.65
- **Best citation heritage**: cited_decisions_tfidf AUC=0.9731
- **v17b normalization partially generalizes**: 2/8 reps within ≤10% worsening rule (cited_decisions_tfidf, regeste_tfidf); 5/8 worsen hierarchy NMI by >10%

### 4. Pending Representations (Awaiting Legal-Distance)

| Category | Representations | Count |
|---|---|---|
| Dense Embeddings | center_projected_768dim, center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | 6 |
| Citation Roles | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | 3 |
| Linear Hybrids | linear_citation_concat, linear_hybrid05_concat | 2 |
| **Total Awaited** | | **11** |

### 5. External Dependencies

- **Jurist Human Study**: BLOCKED — requires 5-10 Swiss jurists recruited by repository owner; framework ready

---

## Recommendations

| Item | Recommendation | Rationale |
|---|---|---|
| **TF-IDF Family** | No additional cycles | All three machine-executable sub-questions COMPLETE at 174k; frozen thresholds; no tuning after results |
| **Dense Embeddings** | Continue waiting | Legal-distance RUN (year-split in progress, 1/26 years complete); monitor will auto-evaluate on landing |
| **Jurist Study** | Report as blocked | External dependency on repository owner for recruitment |
| **Monitor** | Keep active | Check #51 completed; `run_formal_suite_v25()` ready for auto-evaluation |

---

## Configuration Freeze Verification

- **v16 Benchmark Suite Hash**: `4323f833fa72366a` ✅ VERIFIED
- **v3 Harness Config Hash**: `4047da047fb339c1` ✅ VERIFIED
- **v3 Harness Hash**: `a31c443a9b0e992e` ✅ VERIFIED
- **Global Seed**: 42 ✅ FROZEN
- **Citation Heritage Pairs**: 137,314 positive + 137,314 negative (frozen) ✅
- **v17b Label Normalization**: Conservative cross-lingual canonical map frozen ✅

---

## Next Actions

1. **Legal-Distance Lane**: Complete year-split 174k dense embedding computation (years 2001-2025)
2. **Evaluation Lane**: Monitor will auto-detect and auto-evaluate via `run_formal_suite_v25()` when embeddings land
3. **Factory Director**: No direction change needed; v27 stands unchanged

---

## Evidence References

- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — 8/8 TF-IDF suite results
- `results/evaluation/v25_174k_formal_suite/results/*.json` — Individual representation results
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen 137,314 pairs
- `evaluation/data/174k/metadata_174k.json` — 173,963 decisions metadata
- `evaluation/monitor_and_evaluate_174k.py` — Monitor with auto-evaluation capability
- `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py` — Frozen protocol runner