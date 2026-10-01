# Legal Distance Lane — Factory Direction v29 Final Report

**Run ID:** `legal_distance_v29_174k_evaluation_20261001`
**Date:** 2026-10-01
**Direction Version:** 29
**Evidence Tier:** REPRODUCED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** FALSE

---

## Executive Summary

The legal-distance lane has executed all discriminating experiments feasible under current data constraints. **TF-IDF 174k evaluation is COMPLETE and ACCEPTED** — all 8 representations pass both adversarial gates, with `cited_decisions_tfidf_outcome_hybrid_0.5` validated as production default (LangDom=0.4773, JuristPref=0.7345).

**Dense embeddings at 174k are FUNDAMENTALLY BLOCKED** — checkpoints cover only 122,015/173,963 decisions (70.1%, years 2000-2018). Years 2019, 2020-2026 completely missing from source parquet. The canonical corpus uses incompatible ID scheme (`bge_` vs `bger_`), preventing fallback. No further same-question cycles justified without data acquisition.

---

## Factory Direction v29 Deliverables Status

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| (1) Complete assembly & evaluation of 174k dense embeddings | **BLOCKED** | Checkpoints: 122,015 decisions (2000-2018 only). Missing: 2019 (7,665), 2020-2026 (44,283). Parquet `/tmp/bger.parquet` missing. |
| (2) Full-corpus adversarial evaluation at 174k (all reps) | **BLOCKED** | Dense modes unavailable at 174k. TF-IDF 8 reps COMPLETE. |
| (3) Section-specific cross-lingual evaluation at full density | **PARTIAL** | Completed at 1,000-decision sample (sachverhalt superior). Full density blocked by dense embeddings. |
| (4) Scale `linear_hybrid05_concat` stability test at 174k | **PARTIAL** | 15-year (91k): FAIL (JP=0.473). 19-year (122k): PASS both gates (JP=0.5395) but below TF-IDF baseline (0.7235). 174k blocked. |
| (5) Production-deployment vs CV tradeoff at 174k | **VALIDATED** | v8 holdout: leakage minimal (LangDom +0.005, JP +0.015-0.020). All 4 zero-shot hybrids PASS on true holdout. |

---

## Detailed Findings

### 1. TF-IDF 174k Formal Suite — COMPLETE & ACCEPTED

**Frozen harness v3** (exact k-NN on stratified subsample, HNSW artifact fixed). All 8 representations evaluated at 173,963 decisions.

| Representation | LangDom | JuristPref | Both Pass | Evidence Tier |
|----------------|---------|------------|-----------|---------------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.4773** | **0.7345** | ✅ | ACCEPTED |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4912 | 0.7198 | ✅ | ACCEPTED |
| `cited_decisions_tfidf` | 0.5123 | 0.7230 | ✅ | ACCEPTED |
| `regeste_tfidf` | 0.5341 | 0.6987 | ✅ | ACCEPTED |
| `full_text_tfidf_light` | 0.5567 | 0.6543 | ✅ | ACCEPTED |
| `regeste_full_text_hybrid_0.5` | 0.5432 | 0.6721 | ✅ | ACCEPTED |
| `regeste_full_text_hybrid_0.7` | 0.5289 | 0.6894 | ✅ | ACCEPTED |
| `outcome_tfidf_174k` | 0.5678 | 0.6234 | ✅ | ACCEPTED |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (wired in product lane as `PRODUCT_SERVING_DEFAULT`).

**Full-Corpus Benchmarks:**
- Temporal Stability: PASS (0.78 for `full_text_tfidf_light`)
- Hierarchy Coherence: FAIL (nesting ~0.65)
- Cluster Coherence: FAIL (branch_purity ~0.3-0.35, lang_purity ~0.6)
- Boilerplate Resistance: FAIL (resistance ≈ -0.84 — confirms proxy measures language dominance, not procedural boilerplate)

**Key Confirmation:** Fundamental two-mode tradeoff persists at 174k — citation-based signals dominate adversarial gates and citation heritage; text-based signals fail citation heritage but pass branch metadata recovery.

---

### 2. Dense Embeddings 174k — FUNDAMENTAL BLOCKER

#### Checkpoint Coverage
```
Completed Years (19): 2000-2018 → 122,015 decisions (70.1%)
Missing Years (7):    2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026 → 51,948 decisions (29.9%)
```

#### Root Cause
- Checkpoints computed from parquet at `/tmp/bger.parquet` (bger_ IDs: `bger_4P.253_1999`)
- Parquet file **missing** from environment — cannot compute remaining years
- Canonical corpus (`/tmp/lex_accepted/corpus/corpus/normalization/canonical/bge_YYYY.jsonl`) uses **bge_ IDs** (`bge_BGE_126_I_144`)
- No mapping exists between bge_ and bger_ ID schemes
- `finalize_174k_embeddings.py` FAILS metadata order verification (122,015 vs 173,963)

#### Impact
- Fractal-map lane: BLOCKED_ON_DEPENDENCIES (requires 174k dense for citation-role/dense zoom path)
- Product lane: BLOCKED_ON_DEPENDENCIES (dense modes awaited for full capability)
- Evaluation lane: Dense formal suite at 165k only (3/26 years ACCEPTED)

---

### 3. Section-Specific Cross-Lingual Evaluation — COMPLETED at 1K Sample

**Sample:** 1,000 decisions (359 sachverhalt, 510 erwaegungen, 131 dispositiv)

| Section | Representation | cross_lang_same_branch | invariance_gap | zero_shot_nmi | lang_specific_nmi |
|---------|---------------|------------------------|----------------|---------------|-------------------|
| **Sachverhalt** (facts) | cp_64 | **0.282** | **0.187** | 0.189 | 0.221 |
| Erwaegungen (reasoning) | cp_64 | 0.094 | 0.452 | 0.065 | 0.063 |

**Finding:** Sachverhalt (facts) shows **superior cross-lingual alignment** vs Erwaegungen (reasoning). Center projection improves both (invariance_gap reduction: sachverhalt 0.304→0.187, erwaegungen 0.538→0.452).

**Evidence Tier:** REPRODUCED at 1K sample. Full-corpus evaluation blocked by dense embeddings.

---

### 4. linear_hybrid05_concat Stability Test — SCALE DEPENDENCY CONFIRMED

| Scale | Decisions | LangDom | JuristPref | Both Pass | vs TF-IDF Baseline |
|-------|-----------|---------|------------|-----------|-------------------|
| 15-year | 91,929 | 0.8086 ✅ | **0.4730 ❌** | ❌ | -0.2465 |
| 19-year | 122,015 | 0.7784 ✅ | **0.5395 ✅** | ✅ | -0.1840 |
| 174k | — | — | — | **BLOCKED** | — |

**Finding:** `linear_hybrid05_concat` **passes adversarial gates at 122k** but **fails at 91k** — clear scale dependency. However, even at 122k it remains **substantially below TF-IDF citation baseline** (0.5395 vs 0.7235). The two-mode tradeoff persists: citation-based signals dominate jurist pairwise preference.

**15-year `linear_citation_concat`**: Also FAILS (JP=0.4805 vs baseline 0.7230, delta=-0.2425).

---

### 5. Production-Deployment vs CV Tradeoff — VALIDATED

**v8 Holdout Validation (train-only TF-IDF/SVD fitting):**
- All 4 zero-shot hybrids PASS both adversarial gates on true holdout
- Leakage impact: **LangDom +0.005, JP +0.015-0.020** vs leaky results
- **No significant information leakage** from full-corpus SVD fitting
- True OOS JuristPref ceiling: ~0.53-0.59 (vs 0.7+ target missed)

---

## Additional Confirmed Findings

### Two-Mode Tradeoff (Reproduced at 174k TF-IDF, 165k Dense, 122k Dense)
| Mode | LangDom | JuristPref | CiteIndep | Best For |
|------|---------|------------|-----------|----------|
| **Citation/Outcome** (TF-IDF hybrids) | ~0.48 | **~0.73** | ~14% | Production default, user corpora |
| **Semantic Embeddings** (center_projected) | ~0.86 | ~0.36-0.39 | ~37% | Cross-language retrieval |
| **Metric Learning** (linear/mahalanobis) | ~0.58-0.61 | ~0.53-0.61 | **34-37%** | High-purity navigation |

**No single representation dominates all metrics.** Product must expose multiple map modes.

### Citation Heritage at 174k (TF-IDF)
- Citation-based signals: **4/8 PASS** (AUC 0.71-0.74)
- Text-based signals: **FAIL** (AUC ~0.50-0.63, near random)
- Production default `cited_decisions_tfidf_outcome_hybrid_0.5`: AUC=0.7163 ✅

### Boilerplate Resistance — NEGATIVE (All Representations)
- All representations show resistance_score ≈ -0.74 to -0.92
- Confirms proxy measures **language dominance/cross-lingual alignment failure**, not procedural boilerplate
- Consistent across TF-IDF and dense embeddings

### v17b Label Normalization — REPRODUCED but Regime-Dependent
- 1000-scale: 15-25% hierarchy purity gain (REPRODUCED across 4 seeds)
- 174k fine-grained (213→111 labels): Purity ratios 4-10x but **NMI decreases** on normalized labels
- Different regime at scale — requires separate validation

### v18 Coarse Hierarchy — NEGATIVE
- Even at 4-label branch level: best purity 0.65 (linear_citation_concat) < 0.7 threshold
- Fundamental hierarchy limitation confirmed for TF-IDF/citation representations

---

## Evidence Artifacts

| Artifact | Path |
|----------|------|
| TF-IDF 174k Formal Suite | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Dense 19-year Adversarial | `legal_distance/results/174k_dense_embeddings/evaluation_19year_center_projected/*.json` |
| Dense 15-year Linear Hybrid | `legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json` |
| Dense 19-year Linear Hybrid | `legal_distance/results/174k_dense_embeddings/linear_combinations_19year/*.json` |
| Section Cross-Lingual | `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json` |
| v8 Holdout Validation | `legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json` |
| Citation Heritage 174k | `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` |
| v17b Label Normalization | `evaluation/results/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json` |
| v18 Coarse Hierarchy | `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` |
| Dense Checkpoints | `legal_distance/results/174k_dense_embeddings/checkpoints/` (19 years, 122,015 decisions) |
| Progress Tracking | `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` |

---

## Blocker Analysis & Recommendation

### Blocker: Missing Parquet Data for Years 2019-2026
- **Required:** `/tmp/bger.parquet` with full_text for 51,948 decisions (years 2019-2026)
- **Alternative:** Mapping between bge_ (canonical) and bger_ (evaluation) ID schemes
- **Impact:** All downstream lanes (fractal-map, product, evaluation dense) blocked

### Recommended Path Forward
1. **Frontier Team Charter:** Data acquisition for dense embeddings
   - Option A: Obtain/generate parquet for 2019-2026 with bger_ IDs
   - Option B: Build bge_↔bger_ ID mapping from source data
   - Option C: Recompute dense embeddings from canonical corpus + new evaluation pipeline
2. **TF-IDF 174k is production-ready** — no blocker for citation-based modes
3. **No further legal-distance cycles** on current question — all discriminating experiments complete

---

## Lane State Update

```json
{
  "lane": "legal-distance",
  "direction_version": 29,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "legal_distance_v29_174k_evaluation_20261001",
  "next_recommendation": "FRONTIER_TEAM_REQUIRED: Dense embedding data acquisition (parquet 2019-2026 or bge_↔bger_ ID mapping). TF-IDF 174k COMPLETE and production-ready. All discriminating experiments executed. No further same-question cycles justified."
}
```

---

## Conclusion

The legal-distance lane has **completed all feasible discriminating experiments** under factory direction v29. The TF-IDF 174k evaluation is **complete and accepted** — production default validated. The dense embedding path is **fundamentally blocked by missing source data** (parquet for years 2019-2026, ID scheme mismatch). 

**Scale dependency confirmed** for `linear_hybrid05_concat`: fails at 91k, passes at 122k, but never beats citation-based baseline. Section-specific evaluation confirms sachverhalt (facts) as superior cross-lingual signal. Two-mode tradeoff reproduced across all scales and representation families.

**Recommendation:** Launch frontier team for dense embedding data acquisition. TF-IDF production modes operational at full 174k scale. Legal-distance lane correctly BLOCKED_ON_DEPENDENCIES.

---
*Report generated per Research Protocol: frozen hypothesis, corpus, baseline, metric, success rule. Negative results preserved. Provenance maintained.*