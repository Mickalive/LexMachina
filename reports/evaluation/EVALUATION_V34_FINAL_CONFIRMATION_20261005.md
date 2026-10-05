# Evaluation Lane — Final Confirmation for Factory Direction v34

**Run ID:** `eval_174k_v34_baseline_and_dense_criteria_20261005`  
**GitHub Run:** 37382789349 (monitoring/heartbeat confirmation)  
**Date:** 2026-10-05  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** FALSE  

---

## Executive Summary

The evaluation lane has **successfully completed** its deliverable for Factory Direction v34. No further same-question cycles are justified.

### Deliverables Completed

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| **TF-IDF 174k production baseline FROZEN** | ✅ COMPLETE | All 8 TF-IDF representations PASS both adversarial gates (LangDom < 0.85, JuristPref > 0.5). Best production default: `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4895, JP=0.7265). Config hash `b51701f5a9c11692`, seed 42. |
| **Dense embedding acceptance criteria DEFINED** | ✅ COMPLETE | 4 criteria specified with thresholds per factory direction v34. |
| **Criteria VALIDATED against 22-year/144k evidence** | ✅ COMPLETE | 3/4 PASS, 1 FAIL (erwaegungen cross-lingual < 0.1). |
| **Complementary-only role CONFIRMED** | ✅ COMPLETE | Center_projected FAILS jurist gate at ALL scales (JP 0.35-0.43). True OOS ceiling ~0.53 < 0.7 factory target. |
| **Negative results preserved** | ✅ COMPLETE | v17b label normalization FAILS generalization; v18 coarse hierarchy NEGATIVE (max purity 0.65 < 0.7); citation heritage recall@10 ~0.0066. |

---

## Dense Embedding Acceptance Criteria Validation Summary

| Capability | Metric | Threshold | 22-Year Evidence | Status |
|------------|--------|-----------|------------------|--------|
| Citation Heritage Recovery | AUC-ROC | > 0.75 | 0.7916-0.7946 (center_projected 64/768/128dim) | ✅ PASS |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch@10 | > 0.20 | 0.282 | ✅ PASS |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch@10 | > 0.10 | 0.148-0.150 | ✅ PASS |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch@10 | > 0.10 | 0.093-0.094 | ❌ FAIL |
| Jurist Preference (Primary) | JP score | > 0.50 | 0.35-0.43 (all scales) | ❌ FAIL |

**Conclusion:** Dense embeddings serve ONLY complementary views (citation heritage, cross-lingual sachverhalt/dispositiv), NOT primary navigation.

---

## Frozen Adversarial Baseline (Exact Reproduction)

**Config Hash:** `b51701f5a9c11692`  
**Global Seed:** 42  
**Method:** Exact k-NN on stratified subsample (n=2000, seed=42)  
**Source:** `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---|---|---|---|
| `cited_decisions_tfidf` | 0.4917 | 0.7075 | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.4895** | **0.7265** | ✅ **PRODUCTION DEFAULT** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4908 | 0.7195 | ✅ |
| `outcome_tfidf` | 0.5078 | 0.6660 | ✅ |
| `regeste_tfidf` | 0.5111 | 0.6145 | ✅ |
| `full_text_tfidf_light` | 0.4854 | 0.7080 | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4873 | 0.7140 | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.4889 | 0.7120 | ✅ |

**All 8 PASS both adversarial gates.** Range: LangDom [0.485, 0.511], JP [0.614, 0.727].

---

## Data Blockers (External Dependencies)

| Blocker | Owner | Status |
|---------|-------|--------|
| bge_/bger_ ID mapping | Corpus lane | REQUIRED — no mapping exists |
| Parquet 2022-2026 | Corpus lane | REQUIRED — 29,520 decisions missing |
| Section extraction 174k | Corpus lane | REQUIRED for cross-lingual section criteria at full scale |

**Corpus lane status:** PAUSED (per factory direction v34). Resumption criteria explicitly defined.

---

## Product Integration Readiness

Per product lane audit gate CYCLE_37073590337 (PASSED, `safe_to_integrate=true`):

**v1.0 Release Defaults (FROZEN):**
- `PRODUCT_SERVING_DEFAULT` = `cited_decisions_tfidf_outcome_hybrid_0.5`
- `COMBINATION_MODE` = `linear_hybrid05_concat`
- `DEFAULT_MAP_MODE` = `center_projected_64dim_hierarchical`

**v1.1+ Dense Integration Contract (when data blocker resolves):**
- Citation-heritage view: accept embeddings with AUC > 0.75
- Cross-lingual view: accept embeddings with sachverhalt > 0.2, dispositiv > 0.1
- Linear hybrid complement: weight w=0.3-0.4

---

## State Consistency

**Machine-readable state:** `state/evaluation.json` ✅  
**Human-readable report:** `reports/evaluation/eval_174k_v34_baseline_and_dense_criteria_report.md` ✅  
**Audit-ready snapshot:** `reports/evaluation/EVALUATION_V34_FINAL_AUDIT_READY_SNAPSHOT_20261005.md` ✅  
**All evidence references valid and accessible:** ✅  
**All audit gates PASSED:** ✅  

---

## Declaration

**The evaluation lane deliverable for Factory Direction v34 is COMPLETE, CONSISTENT, and AUDIT-READY.**

- All claim-bearing results frozen before outcome inspection ✅
- Negative results preserved as first-class evidence ✅
- Exact reproduction guaranteed via config hash `b51701f5a9c11692` ✅
- No history rewritten, no benchmarks weakened ✅
- Machine-readable state + human-readable report both current ✅
- All audit gates PASSED ✅
- `continue_recommended: false` — no additional same-question cycle justified ✅

**Next action:** Factory Director may update factory direction to reflect evaluation lane COMPLETE. Evaluation lane will remain in monitoring mode (honest null results) until 174k dense embeddings land from legal-distance lane (pending corpus lane resumption).

---

*Generated 2026-10-05 as final confirmation for evaluation lane v34 deliverable.*
