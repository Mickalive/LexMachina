# Evaluation Lane v29 Final Verification Report

**Date**: 2026-10-02T23:32:57Z  
**Factory Direction Version**: 29  
**Lane Status**: COMPLETE (PAUSE recommended)  
**Evidence Tier**: REPRODUCED

---

## Executive Summary

The evaluation lane has completed all three items in the factory direction v29 question for **available representations**. The lane is now **blocked on legal-distance delivering 174k-scale dense embeddings** (currently only 3/26 years ACCEPTED, 22/26 years evaluated at 144k scale).

---

## Factory Direction v29 Question Items — Status

| Item | Description | Status |
|------|-------------|--------|
| 1 | Full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3) | ✅ **COMPLETE** — TF-IDF family (8 reps) all PASS both adversarial gates |
| 2 | Validate citation_heritage benchmark using 174k citation-ID resolution (2,019/2,105 resolved) | ✅ **COMPLETE** — 4/8 PASS AUC≥0.65; citation signals dominate |
| 3 | Test v17b label normalization generalization to 174k fine-grained legal_area labels | ✅ **COMPLETE** — NEGATIVE: regime difference confirmed, NMI decreases on normalized |

---

## Key Results

### TF-IDF Family at 174k (8 representations)
- **All 8 PASS both adversarial gates** (LangDom < 0.85, JuristPref > 0.5)
- **Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` — LangDom=0.4895, JuristPref=0.7265
- **Citation heritage**: 3/8 PASS AUC≥0.7 (cited_decisions_tfidf family); 4/8 PASS AUC≥0.65
- **Two-mode tradeoff confirmed**: Citation signals recover citation heritage; text signals do not

### Dense Embeddings (checkpointed, not full 174k)
| Scale | Decisions | Center Projected | Linear Hybrids |
|-------|-----------|------------------|----------------|
| 15-year (2000-2014) | 91,929 | FAIL both gates | FAIL jurist gate |
| 19-year (2000-2018) | 122,015 | FAIL both gates | **PASS both gates** (JP=0.5395) but below TF-IDF baseline |
| 22-year (2000-2021) | 144,443 | FAIL jurist gate (JP 0.39-0.43) | **PASS both gates at w=0.3-0.4** but below TF-IDF baseline |

**Critical finding (corrected per audit CYCLE_37082047030)**: 
- **Citation heritage for dense embeddings**: Partial 16-year (2000-2015) evaluation shows AUC ~0.90 on center_projected_768dim (13,648 positive pairs). Full 15-year (2000-2014) and 19-year (2000-2018) evaluations **FAILED due to insufficient valid pairs**. 22-year (2000-2021) citation heritage **NOT YET EVALUATED** in this cycle. The prior claim "AUC 0.79-0.85 at 22-year scale" was unsupported.
- **Jurist gate**: Center projected representations FAIL at all scales tested (JP 0.39-0.43 at 22-year; 0.26-0.29 at 15-year; 0.47-0.48 at 19-year). Linear hybrids PASS jurist gate at 19/22-year but remain below TF-IDF baseline (JP ~0.54 vs 0.73).

### Label Normalization (v17b)
- **1000 scale**: 15-25% hierarchy purity gain REPRODUCED across 4 seeds
- **174k scale (15k subsample)**: Purity ratios 4-10x but **NMI decreases** — different regime
- **Conclusion**: Method reproduced, but does not generalize with same-magnitude effect

### Coarse Hierarchy (v18)
- **NEGATIVE**: Even at 4-label branch level, best purity 0.65 < 0.7 threshold
- **All 6 representations FAIL** — fundamental hierarchy limitation confirmed

---

## Evidence References

| Artifact | Path |
|----------|------|
| TF-IDF 174k formal suite | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| 15yr dense formal suite | `evaluation/results/174k/formal_suite/15year_dense/evaluation_15year_dense_formal_suite_latest.json` |
| 19yr dense formal suite | `evaluation/results/174k/formal_suite/19year_dense/evaluation_19year_dense_formal_suite_latest.json` |
| Citation heritage 174k | `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` |
| v17b 174k TF-IDF | `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` |
| v17b 174k generalization | `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_latest.json` |
| v17b dense partial | `evaluation/results/v17b_174k_dense_partial/v17b_174k_dense_partial_latest.json` |
| v18 coarse hierarchy | `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` |
| Legal-distance state | `/tmp/lex_accepted/legal-distance/state/legal-distance.json` |
| Corpus state | `/tmp/lex_accepted/corpus/state/corpus.json` |
| Final report | `evaluation/reports/evaluation_v29_final_report.md` |

---

## Verification Tests Passed

- ✅ Frozen harness v3 reproducibility
- ✅ V25 174k suite snapshot (6/8 PASS)
- ✅ Citation heritage spot check (AUC within 0.005 tolerance)
- ✅ Smoke test formal suite (production default PASS)
- ✅ Citation heritage benchmark operational
- ✅ v17b 174k generalization complete
- ✅ v18 coarse hierarchy complete (NEGATIVE)
- ✅ Dense formal suite 15yr complete
- ✅ Dense formal suite 19yr complete

---

## Blockers

**Legal-distance 174k dense embeddings delivery blocked on:**
1. Missing parquet file `/tmp/bger.parquet`
2. No bge_ ↔ bger_ ID mapping (corpus uses bge_, evaluation uses bger_)
3. Years 2022-2026 not processed (29,520 decisions missing)
4. `finalize_174k_embeddings.py` fails metadata order verification

Legal-distance recommends **FRONTIER_TEAM_REQUIRED** for dense embedding data acquisition.

---

## Next Recommendation

**PAUSE** — No additional same-question cycles justified. Factory Director to decide successor question.

The evaluation harness is **ready** for new representations when they land:
- Formal suite harness: operational
- Exact k-NN adversarial: verified (HNSW artifact fixed)
- Citation heritage pairs: frozen (1,020 pairs)
- v17b normalization pipeline: tested
- v18 coarse hierarchy test: validated as negative result

---

*Generated by Evaluation Lane v29 verification cycle*