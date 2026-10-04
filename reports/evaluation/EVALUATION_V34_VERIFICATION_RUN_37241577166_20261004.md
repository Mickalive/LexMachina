# Evaluation Lane Verification Report — Run 37241577166

**Date:** 2026-10-04  
**Factory Direction:** v34  
**Lane:** evaluation  
**Status:** ACCEPTED / COMPLETE / continue_recommended=false  

---

## Executive Summary

Regression verification confirms the **TF-IDF 174k production baseline remains FROZEN and VALID**. All 8 TF-IDF representations pass both adversarial gates on exact k-NN (n=2000, seed=42).

**Critical Discovery:** 24-year (2000–2023, 158,427 decisions) dense embeddings **EXIST** in the legal-distance lane checkpoints — the monitor was checking the wrong location. Citation heritage at 24-year scale validates the acceptance criterion (AUC 0.769–0.770 > 0.75). Only 2024–2026 remain missing (no parquet). The data blocker is **partially resolved**.

---

## 1. TF-IDF 174k Baseline — Regression Verification (PASS)

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---|---:|---:|:---:|
| cited_decisions_tfidf | 0.4917 | 0.7075 | ✅ PASS |
| **cited_decisions_tfidf_outcome_hybrid_0.5** (production default) | **0.4895** | **0.7265** | ✅ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | ✅ PASS |
| outcome_tfidf | 0.5078 | 0.6660 | ✅ PASS |
| regeste_tfidf | 0.5111 | 0.6145 | ✅ PASS |
| full_text_tfidf_light | 0.4854 | 0.7080 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.4873 | 0.7140 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.4889 | 0.7120 | ✅ PASS |

**All 8 PASS** (LangDom < 0.85, JP > 0.5).  
Method: Exact k-NN on stratified subsample (n=2000, seed=42). Config hash: `b51701f5a9c11692`.  
Source: `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`

---

## 2. Dense Embeddings — 24-Year Evidence (NEW)

### 2.1 Availability
**Location:** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`  
**Years:** 2000–2023 (24 years, 158,427 decisions)  
**Files:** `embeddings_2000.npy` through `embeddings_2023.npy` + metadata JSONs  
**Missing:** 2024, 2025, 2026 (no parquet source)  
**Progress:** `progress.json` confirms "2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs)"

### 2.2 Citation Heritage — 24-Year Validation (PASS)

| Representation | AUC-ROC | Positive Pairs | Decisions | Status |
|---|---:|---:|---:|:---:|
| center_projected_768dim | 0.7696 | 730 | 158,427 | ✅ PASS (>0.75) |
| center_projected_64dim | 0.7667 | 730 | 158,427 | ✅ PASS (>0.75) |
| center_projected_128dim | 0.7669 | 730 | 158,427 | ✅ PASS (>0.75) |

**Threshold:** 0.75  
**TF-IDF citation-based baseline:** AUC 0.71–0.74  
**Conclusion:** Dense embeddings **EXCEED** TF-IDF citation-based baseline and **PASS** the acceptance criterion at 24-year scale.

Source: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`

### 2.3 Adversarial Evaluation — 22-Year (Most Recent Evaluation Lane Run)

| Representation | LangDom | Jurist Pref | Both Gates |
|---|---:|---:|:---:|
| center_projected_768dim | 0.842 ✅ | 0.3975 ❌ | ❌ FAIL |
| center_projected_64dim | 0.832 ✅ | 0.4265 ❌ | ❌ FAIL |
| center_projected_128dim | 0.838 ✅ | 0.4080 ❌ | ❌ FAIL |

**Threshold:** LangDom < 0.85, JP > 0.5  
**Conclusion:** Center_projected **PASSES language dominance** but **FAILS jurist preference** at 22-year (144k) scale. True OOS ceiling ~0.43 < 0.5 factory target.  
**24-year adversarial evaluation: NOT YET RUN** — recommended next step.

Source: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`

### 2.4 Section Cross-Lingual — 3-Year Only (2000–2002)

| Section | cross_lang_same_branch (64/768dim) | Threshold | Status |
|---|---:|---:|:---:|
| Sachverhalt (facts) | 0.2816 | > 0.2 | ✅ PASS |
| Dispositiv (holdings) | 0.1481 / 0.1502 | > 0.1 | ✅ PASS |
| Erwaegungen (reasoning) | 0.0925 / 0.0941 | > 0.1 | ❌ FAIL |

**Hierarchy confirmed:** Sachverhalt > Dispositiv > Erwaegungen  
**24-year cross-lingual: NOT YET RUN**

Source: `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`

---

## 3. Dense Embedding Acceptance Criteria — Final Validation

| Criterion | Threshold | Evidence | Status |
|---|---:|---|:---:|
| Citation Heritage AUC | > 0.75 | 24-yr: 0.767–0.770 | ✅ PASS |
| Cross-lang Sachverhalt | > 0.2 | 3-yr: 0.282 | ✅ PASS |
| Cross-lang Dispositiv | > 0.1 | 3-yr: 0.148 | ✅ PASS |
| Cross-lang Erwaegungen | > 0.1 | 3-yr: 0.093 | ❌ FAIL |
| Jurist Pairwise Preference | > 0.5 | 22-yr: 0.39–0.43 | ❌ FAIL |

**Verdict:** Dense embeddings qualify as **COMPLEMENTARY VIEWS ONLY** — citation heritage view and cross-lingual sachverhalt/dispositiv views. They do NOT meet the jurist preference baseline for primary navigation.

---

## 4. Other Evaluations — Status Unchanged

- **v17b Label Normalization (174k):** Does NOT uniformly improve hierarchy metrics; NMI decreases for 5/8 reps. Different regime from 1k scale. (REPRODUCED)
- **v18 Coarse Hierarchy (4-label branch):** Best purity 0.65 < 0.7 threshold. Fundamental limitation confirmed. (NEGATIVE)
- **Citation Heritage 174k TF-IDF:** 4/8 representations PASS (AUC > 0.65), best: cited_decisions_tfidf (AUC=0.743)

---

## 5. Recommendations

1. **TF-IDF 174k baseline is FROZEN** as production default (`cited_decisions_tfidf_outcome_hybrid_0.5`). No further evaluation cycles needed for this question.

2. **Run 24-year adversarial evaluation** on center_projected (64/768/128dim) to confirm jurist preference ceiling at 158k scale. This is the highest-priority next evaluation task.

3. **Run 24-year section cross-lingual evaluation** to validate sachverhalt/dispositiv/erwaegungen hierarchy at full available scale.

4. **Corpus lane resumption** still needed for:
   - BGE/bger ID mapping (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs)
   - Parquet generation for 2024–2026 (29,520 decisions missing)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

5. **No additional same-question cycle justified** — current factory direction question is answered. Await 24-year adversarial results or full 174k dense embeddings before next evaluation cycle.

---

## 6. Evidence References

- TF-IDF adversarial re-verification: `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- 24-year citation heritage: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- 22-year adversarial: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`
- 3-year cross-lingual: `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`
- Legal-distance progress: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
- State file: `evaluation/state/evaluation.json`

---

**Verification Complete.** State updated to `last_verified_run: 37241577166`, `last_verified_timestamp: 2026-10-04T22:52:00Z`.