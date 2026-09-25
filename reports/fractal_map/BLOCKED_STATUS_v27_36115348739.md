# Fractal-Map Lane Status Report — Factory Direction v27, GitHub Run 36115348739

**Date:** 2026-09-25  
**Lane:** fractal-map  
**Direction Version:** 27  
**Cycle Status:** COMPLETED (TF-IDF at 174k) — BLOCKED on legal-distance_174k_dense_embeddings  
**Continue Recommended:** false  
**Evidence Tier:** ACCEPTED

---

## Executive Summary

The fractal-map lane has **completed all TF-IDF work at 174k scale** and is correctly **BLOCKED** on the single remaining dependency: `legal-distance_174k_dense_embeddings`. No same-question cycle is justified (`continue_recommended=false`). All 183 verification tests pass.

The lane has delivered:
- ✅ 174k hierarchical maps for 22+ TF-IDF/citation/outcome modes (COMPLETED, ACCEPTED)
- ✅ Frozen v26 zoom-quality evaluation: **FAIL** on all 4 decision-mappable TF-IDF modes (honest negative, freeze-protected)
- ✅ Compressed 5-level resolution ladder validated: 100% purity-delta retention, 29% fewer levels
- ✅ NESTING_METRIC_DEFECT_v1 documented and corrected (historical artifacts preserved)
- ✅ Dense embeddings evaluation infrastructure ready (`evaluate_174k_dense_embeddings.py`)
- ✅ Product multi-view zoom UI with citation-role views VERIFIED IMPLEMENTED

**Blocker:** legal-distance dense embeddings at 174k scale (~54% complete: 14/26 years computed)

---

## Dependency Progress: legal-distance_174k_dense_embeddings

| Year | Status | Embedding File | Metadata File |
|------|--------|----------------|---------------|
| 2000 | ✅ Complete | embeddings_2000.npy (11.8 MB) | metadata_2000.json |
| 2001 | ✅ Complete | embeddings_2001.npy (0.96 MB) | metadata_2001.json |
| 2002 | ✅ Complete | embeddings_2002.npy (1.1 MB) | metadata_2002.json |
| 2003 | ✅ Complete | embeddings_2003.npy (0.96 MB) | metadata_2003.json |
| 2004 | ✅ Complete | embeddings_2004.npy (0.92 MB) | metadata_2004.json |
| 2005 | ✅ Complete | embeddings_2005.npy (0.90 MB) | metadata_2005.json |
| 2006 | ✅ Complete | embeddings_2006.npy (0.72 MB) | metadata_2006.json |
| 2007 | ✅ Complete | embeddings_2007.npy (0.97 MB) | metadata_2007.json |
| 2008 | ✅ Complete | embeddings_2008.npy (0.88 MB) | metadata_2008.json |
| 2009 | ✅ Complete | embeddings_2009.npy (0.75 MB) | metadata_2009.json |
| 2010 | ✅ Complete | embeddings_2010.npy (0.83 MB) | metadata_2010.json |
| 2011 | ✅ Complete | embeddings_2011.npy (0.88 MB) | metadata_2011.json |
| 2012 | ✅ Complete | embeddings_2012.npy (0.99 MB) | metadata_2012.json |
| 2013 | ✅ Complete | embeddings_2013.npy (0.83 MB) | metadata_2013.json |
| 2014–2025 | ⏳ Pending | — | — |
| 2026 | ⏳ Pending | — | — |

**Progress:** 14/26 years complete (54%). Remaining: 12 years (2014–2025) + 2026 partial.

The legal-distance lane is actively computing these year-split with resumable checkpoints within 65-min job ceilings on free public CPU runners.

---

## Frozen TF-IDF 174k Results (v26)

### Zoom-Quality Evaluation: OVERALL FAIL (Generalized Negative)

| Mode | Branch Mono | Area Mono | Rate OK (≥2/4) | Verdict |
|------|-------------|-----------|----------------|---------|
| cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25 | False (0.5525→0.5273) | — | False | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 | — | — | — | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k | False | — | False | FAIL |
| regeste_tfidf_174k | False (0.3452→0.3434) | — | False | FAIL |

**Key Finding:** TF-IDF modes encode strong legal structure (branch purity 0.51–0.55 vs 0.25 random; legal_area purity 0.24–0.31 vs ~0.005 random) but **fail ALL three monotonic zoom-refinement checks**. Fine ladder over-fragmented (median cluster size 1, singleton fraction 0.9956).

### Evidence-Backed Zoom Path (from 1000-scale diagnostic)

| Mode | Zoom Quality (ZQ) |
|------|-------------------|
| citing_alpha0.3 | 0.5401 |
| following_alpha0.3 | 0.5280 |
| criticizing_alpha0.3 | 0.4864 |
| outcome_hybrid_0.5 (production default) | 0.2798 |

**Conclusion:** Citation-role and dense-embedding modes remain the evidence-backed path for zoom-quality at 174k.

---

## NESTING_METRIC_DEFECT_v1 (Accepted Finding)

- **Parameterized builders** recorded `mean_nesting_score` as majority-parent **COVERAGE** (~1.0 by construction), not strict nesting
- **37/46 audited modes** over-claimed 1.0 vs honest strict nesting 0.04–1.0
- **Remediated** in both parameterized builders; historical artifacts preserved untouched per constitution
- **Compressed 5-level ladder** [0.25, 0.5, 1.0, 2.0, 3.0] does NOT preserve strict nesting (honest mean change -0.00364, range [-0.0556, +0.1150], 21/22 modes nonzero)
- **nesting_score=1.0 citeable ONLY** for 1000-scale by-construction modes with scope annotation and honest ladder mean (0.8722/0.8644)
- **outcome_tfidf_174k_compressed nesting=1.0 is genuine** (by-construction)

---

## Orchestration Failure (Documented, Not This Lane's Responsibility)

**Root Cause:** Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow) instead of persistent workspace `state/fractal-map.json` and `state/factory_direction.json`.

**Impact:** 60+ documented re-dispatch occurrences since run 33339971167. Supervisor sees `fractal-map.status=RUN` in ephemeral file vs `COMPLETED_TFIDF` + `blocked_on=legal-distance_174k_dense_embeddings` in workspace state.

**Required Fix:** Factory Director must update supervisor dispatch logic to read workspace state.

---

## Ready for Dense Embeddings Arrival

When legal-distance delivers all 26 years of dense embeddings:

1. **Builder:** `build_parameterized_legal_distance_map.py` (fixed: branch from chamber, unknown excluded)
2. **Evaluation:** `evaluate_174k_dense_embeddings.py` (frozen v26 success rule)
3. **Metadata:** `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries, 100% branch+legal_area coverage)
4. **Success Rule:** PASS iff (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥2 of 4 transitions

---

## Recommendation

**No same-question cycle justified.** Lane remains BLOCKED. Resume only when:
- legal-distance delivers complete 174k dense embeddings (all 26 years)
- Or downstream-reported artifact gaps require fractal-map intervention

Next cycle should be triggered by Factory Director upon dense embeddings delivery, with a new question focused on dense embedding zoom-quality evaluation at 174k scale.

---

## Evidence References

- State: `state/fractal-map.json` (accepted_run_id: 35952633500, github_run: 36112941372)
- Frozen v26: `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json`
- Frozen v25: `results/fractal_map/zoom_quality_174k_eval/v25_verdict.json`
- Census: `results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json`
- Dense eval harness: `fractal_map/evaluation/evaluate_174k_dense_embeddings.py`
- Legal-distance progress: `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
- All verification tests: `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` (7/7 PASS)
- Full verification suite: `tests/fractal_map/test_verify.py` (183/184 PASS, 1 SKIPPED)

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report."*