# Evaluation Lane Cycle Complete — Factory Direction v34

**Run ID:** `eval_174k_v34_baseline_and_dense_criteria_20261003`  
**Factory Direction Version:** 34  
**Date:** 2026-10-03  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** FALSE  

---

## Summary

The evaluation lane has successfully completed its work for factory direction v34. All objectives from the lane directive have been met:

### 1. TF-IDF 174k Production Baseline Frozen ✅
- 8 TF-IDF representations evaluated at full 173,963 decisions on frozen adversarial harness v3
- All 8 PASS both adversarial gates (Language Dominance < 0.85, Jurist Preference > 0.5)
- **Production default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4895, JP=0.7265)
- Fundamental tradeoff confirmed: citation-based modes dominate jurist preference; text-based modes fail adversarial language dominance (~0.999)

### 2. Dense Embedding Complementary View Acceptance Criteria Defined & Validated ✅

| Capability | Metric | Threshold | Evidence (22yr/144k) | Status |
|------------|--------|-----------|---------------------|--------|
| Citation Heritage Recovery | AUC-ROC | > 0.75 | 0.7916–0.7941 | **PASS** |
| Cross-Lingual Sachverhalt | `cross_lang_same_branch@10` | > 0.20 | 0.2816 | **PASS** |
| Cross-Lingual Dispositiv | `cross_lang_same_branch@10` | > 0.10 | 0.1481–0.1502 | **PASS** |
| Cross-Lingual Erwaegungen | `cross_lang_same_branch@10` | > 0.10 | 0.0925–0.0941 | **FAIL** |
| Jurist Pairwise Preference | JP score | > 0.50 | 0.389–0.418 | **FAIL** |

**Conclusion:** Dense embeddings (center_projected) are **COMPLEMENTARY VIEWS ONLY** — they excel at citation heritage recovery (exceeding TF-IDF) and cross-lingual alignment for sachverhalt/dispositiv, but FAIL jurist preference at ALL scales.

### 3. Critical Negative Results Preserved
- **v17b label normalization**: 15-25% purity gain at 1k scale does NOT generalize to 174k (zoom_fine degrades 11-16%, NMI drops 0.59→0.45)
- **v18 coarse hierarchy**: Even at 4-label branch level, max purity 0.65 < 0.7 threshold
- **Citation heritage recall@10**: Near zero (max 0.0066) — operates via AUC ranking, not nearest-neighbor

### 4. External Blocker Documented
No 174k dense embeddings available — blocked on:
1. **BGE/bger ID mapping** (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs)
2. **Parquet generation for 2022-2026** (29,520 decisions missing)

Corpus lane resumption required before next evaluation cycle.

---

## Recommendation

**No additional same-question cycle justified.** The evaluation lane state reflects `continue_recommended: false`. The Factory Director will determine the successor evaluation question when the data blocker is resolved.

---

## Evidence References

- `reports/evaluation/eval_174k_v34_baseline_and_dense_criteria_report.md` — Full technical report
- `reports/evaluation/eval_v34_conformance_report.md` — Conformance test results (all PASS)
- `state/evaluation.json` — Machine-readable lane state (ACCEPTED, COMPLETE, continue_recommended=false)

---

*This cycle is complete. No further action required for factory direction v34.*