# Evaluation Lane — Regression Verification (GitHub Run 37195050857)

**Date:** 2026-10-04  
**Lane:** evaluation  
**Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Run ID:** `eval_174k_v34_baseline_and_dense_criteria_20261003` (re-verified)

---

## Purpose

Confirm the frozen TF-IDF 174k production baseline and dense embedding acceptance criteria remain valid and reproducible on GitHub run 37195050857.

---

## Verification Results

### 1. Frozen Adversarial Harness v3 Reproducibility — **PASS**
- Config hash: `b51701f5a9c11692` (exact match)
- Method: Exact k-NN on stratified subsample n=2000, seed=42
- All 8 TF-IDF representations PASS both adversarial gates:
  - Language Dominance < 0.85: range [0.485, 0.511] ✅
  - Jurist Preference > 0.5: range [0.614, 0.727] ✅
- Production default `cited_decisions_tfidf_outcome_hybrid_0.5`: LangDom=0.4895, JP=0.7265

### 2. Audit Correction Verification — **PASS (9/9)**
- `test_v34_state_structure` ✅
- `test_tfidf_174k_baseline_frozen` ✅
- `test_dense_embedding_acceptance_criteria` ✅
- `test_citation_heritage_174k_tfidf` ✅
- `test_v17b_label_normalization_174k` ✅
- `test_v18_coarse_hierarchy_negative` ✅
- `test_critical_findings` ✅
- `test_next_recommendation` ✅
- `test_evidence_refs` ✅

### 3. Cross-Lingual Alignment v10 — **PASS**
- Confirms Sachverhalt > Dispositiv > Erwaegungen hierarchy for dense embeddings

### 4. Dense Embedding Acceptance Criteria — **RECONFIRMED**
| Criterion | Threshold | 22-Year Evidence | Status |
|-----------|-----------|------------------|--------|
| Citation Heritage AUC | > 0.75 | center_projected: 0.7916–0.7946 | ✅ PASS |
| Cross-lang Same-Branch (Sachverhalt) | > 0.2 | center_projected: 0.2816 | ✅ PASS |
| Cross-lang Same-Branch (Dispositiv) | > 0.1 | center_projected: 0.148–0.150 | ✅ PASS |
| Cross-lang Same-Branch (Erwaegungen) | > 0.1 | center_projected: 0.093–0.094 | ❌ FAIL |
| Jurist Pairwise Preference | > 0.5 | center_projected: 0.39–0.43 | ❌ FAIL |

---

## State Update

Updated `state/evaluation.json`:
- `github_run`: 37195050857
- `last_verified_run`: 37195050857
- `last_verified_timestamp`: 2026-10-04T12:15:00Z
- `continue_recommended`: false (unchanged)

---

## Recommendation

**No additional same-question cycle justified.** The TF-IDF 174k production baseline remains frozen. Dense embedding complementary view acceptance criteria are defined and validated. Evaluation lane awaits 174k dense embeddings (blocked on corpus lane: bge_/bger_ ID mapping + parquet 2022-2026).

---

## Evidence References

- `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `results/evaluation/citation_heritage_174k_tfidf_latest.json`
- `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`
- `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`
- `reports/evaluation/eval_174k_v34_baseline_and_dense_criteria_report.md`