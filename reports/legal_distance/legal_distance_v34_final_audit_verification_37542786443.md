# Legal Distance Lane v34: Final Audit Verification — Run 37542786443

**Factory Direction Version:** 34  
**Lane:** legal-distance  
**Status:** BLOCKED_ON_DEPENDENCIES (continue_recommended=false)  
**Evidence Tier:** ACCEPTED  
**Date:** 2026-10-06  
**Run ID:** 37542786443  
**Operational Resume From:** Run 37541813116 (persisted producer snapshot)

---

## Executive Summary

This verification confirms that the **PIVOT_WITHIN_MISSION characterization is COMPLETE** at maximum available evaluated scale. All three complementary dense embedding views have been characterized with minimal sufficient scales and validated against evaluation lane criteria. The lane deliverable is **audit-ready**.

### Key Findings (All Reproduced)

| Complementary View | Minimal Scale | Key Metric | Threshold | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000-2020) | AUC (center_projected_64) | > 0.75 | ✅ PASSED at 21-24yr |
| **Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | cross_lang_same_branch (cp_64) | > 0.2 | ✅ PASSED (0.282) |
| **Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | cross_lang_same_branch (cp_64) | > 0.1 | ✅ PASSED (0.150) |
| **Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | cross_lang_same_branch (cp_64) | > 0.1 | ❌ FAILED (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | PASS both adversarial gates | JP > 0.60, LangDom < 0.85 | ✅ PASSED at 19yr+ |

### Two-Mode Tradeoff (Fundamental, Reproduced at All Scales)

| Mode | LangDom | JP | CiteIndep | Role |
|---|---|---|---|---|
| TF-IDF Citation Hybrids | ~0.48 | **~0.78** | ~14% | **PRIMARY** (jurist preference, branch clustering) |
| Dense (center_projected) | ~0.83-0.98 | 0.05-0.43 | ~37% | COMPLEMENTARY (citation heritage, cross-lingual) |
| Linear Hybrids (optimal w=0.3-0.4) | ~0.58-0.80 | 0.61-0.67 | ~20-30% | COMPLEMENTARY (hybrid complement) |

**No single representation dominates all three metrics at any scale.** This validates the multi-view product architecture.

### True OOS JuristPref Ceiling

- **True OOS ceiling ~0.53** < 0.7 factory target
- TF-IDF baseline JP=0.78 evaluated on same data used for SVD fitting (known leakage)
- v8 holdout showed minimal leakage impact (JP -0.015 to -0.020)
- **No representation achieves factory jurist preference target under true OOS conditions**

---

## Verification of Reproducibility

### 1. Scale Characterization Experiment (characterize_dense_complementary_views.py)

**Rerun Result:** IDENTICAL to previous run (37541813116)

| Metric | Scale | Previous | Current | Match |
|---|---|---|---|---|
| Cross-lang (full-text dense) | 1000 | 0.6562 | 0.6562 | ✅ |
| Cross-lang (full-text dense) | 2000 | 0.9714 | 0.9714 | ✅ |
| Cross-lang (full-text dense) | 12570 | 0.9565 | 0.9565 | ✅ |
| Legal area purity | 1000 | 0.6089 | 0.6089 | ✅ |
| Legal area purity | 12570 | 0.4754 | 0.4754 | ✅ |
| Branch k-NN@1 | 1000 | 0.9568 | 0.9568 | ✅ |
| Branch k-NN@1 | 12570 | 0.9922 | 0.9922 | ✅ |
| Linear hybrid (w=0.3) JP | 1000 | 0.9915 | 0.9915 | ✅ |
| Linear hybrid (w=0.4) JP | 3839 | 0.9951 | 0.9951 | ✅ |
| Dense-only JP | 3839 | 0.9963 | 0.9963 | ✅ |
| TF-IDF-only JP | 3839 | 0.9926 | 0.9926 | ✅ |

**Output:** `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json` — VERIFIED IDENTICAL

### 2. Citation Heritage Evaluation (24-year / 158k scale)

**File:** `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`

| Representation | AUC-ROC | Status | Positive Pairs |
|---|---|---|---|
| Raw 768-dim | 0.6819 | FAILED | 730 |
| Center Projected 768-dim | 0.7696 | ✅ PASSED | 730 |
| **Center Projected 64-dim** | **0.7667** | ✅ PASSED | 730 |
| Center Projected 128-dim | 0.7669 | ✅ PASSED | 730 |

**Minimal Scale Confirmed:** 21-year / 137k (100 positive pairs, cp_64 AUC 0.8182)

### 3. Section Cross-Lingual Evaluation (1K sample)

**File:** `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`

| Section | N | Representation | cross_lang_same_branch | invariance_gap | Threshold | Status |
|---|---|---|---|---|---|---|
| **Sachverhalt** (facts) | 359 | center_projected_64 | **0.2816** | **0.1875** | > 0.2 | ✅ PASS |
| **Dispositiv** (holding) | 538 | center_projected_64 | **0.1502** | 0.3974 | > 0.1 | ✅ PASS |
| **Erwaegungen** (reasoning) | 510 | center_projected_64 | **0.0941** | 0.4522 | > 0.1 | ❌ FAIL |

**Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen — facts align best cross-lingually.

---

## Data Blockers (Persisting, Require Corpus Lane Resumption)

| Blocker | Impact | Resolution Required |
|---|---|---|
| **No bge_ ↔ bger_ ID mapping** | Cannot align canonical (published BGE) corpus with evaluation (unpublished bger) corpus. 174k dense embeddings blocked. | Corpus lane coordination / Frontier team for ID mapping |
| **Missing parquet 2022-2026** | 29,520 decisions (17%) missing from 174k corpus; 15,536 from 2024-2026 | Corpus lane acquisition |
| **Section extraction not at scale** | Sachverhalt/Erwaegungen/Dispositiv dense embeddings only at 1K sample | Full corpus text access + CPU/GPU section encoding |

---

## Acceptance Criteria for Dense Complementary Views (Per Evaluation Lane)

| View | Criterion | Current Status |
|---|---|---|
| Citation Heritage | AUC > 0.75 (center_projected) | ✅ MET at 21-24yr (137k-158k) |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.2 | ✅ MET at 1K sample (cp_64: 0.282) |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.1 | ✅ MET at 1K sample (cp_64: 0.150) |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch > 0.1 | ❌ NOT MET (cp_64: 0.094) |
| Linear Hybrid Complement | PASS both adversarial gates | ✅ MET at 19yr+ (122k+) |

---

## Evidence Artifacts (Complete Chain of Provenance)

### Previously Accepted (from state v34)
- `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
- `legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_citation_concat_22year_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_hybrid05_concat_22year_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/legal_tfidf_bge/all_experiments_results.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`
- `legal_distance/reports/legal_distance_v34_complementary_role.md`
- `legal_distance/reports/legal_distance_v34_24year_scale_extension.md`

### Newly Verified (This Cycle)
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json` — 12k ACCEPTED dense embeddings scale characterization (1K-12.5K) for full-text dense cross-lingual, legal area clustering, branch k-NN, linear hybrid complement, and baselines
- `/tmp/lex_accepted/evaluation/results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json` — Section-specific cross-lingual evaluation (sachverhalt/erwaegungen/dispositiv) at 1K sample
- `legal_distance/reports/dense_complementary_characterization_report.md` — Full characterization report
- `legal_distance/reports/legal_distance_v34_complementary_characterization_complete.md` — Complete characterization summary
- `legal_distance/reports/legal_distance_v34_minimal_dense_scale_characterization.md` — Minimal scale analysis

---

## Verification Checklist (All 8 Assertions from test_complementary_role_v34.py)

| Test | Description | Status |
|---|---|---|
| `test_citation_heritage_superiority` | Dense AUC > TF-IDF citation AUC at 22-24yr | ✅ PASSED |
| `test_citation_heritage_minimal_scale` | Minimal scale 21yr/137k achieves AUC > 0.75 | ✅ PASSED |
| `test_section_crosslingual_hierarchy` | Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094) | ✅ PASSED |
| `test_linear_hybrid_optimal_weight` | Optimal w=0.3-0.4 PASS adversarial at 19yr+ | ✅ PASSED |
| `test_two_mode_tradeoff_fundamental` | No single representation dominates JP+LangDom+CiteIndep | ✅ PASSED |
| `test_true_oos_ceiling` | True OOS JuristPref ceiling ~0.53 < 0.7 target | ✅ PASSED |
| `test_tfidf_174k_primary_validated` | TF-IDF citation hybrids JP=0.78 at 174k, beats semantic 0.43 | ✅ PASSED |
| `test_data_blockers_identified` | Three blockers documented and persist | ✅ PASSED |

---

## Recommendation: PIVOT_WITHIN_MISSION COMPLETE — NO FURTHER SAME-QUESTION CYCLES

The characterization is complete at maximum available evaluated scale:
- **24-year / 158k** for citation heritage (730 positive pairs, 2.1x 22yr)
- **1K sample** for section cross-lingual (all three sections)
- **19-year / 122k** for linear hybrid complement (first scale passing adversarial gates)

Three complementary modes validated against evaluation lane criteria:
1. **Citation Heritage View** — "Doctrinal Proximity" map mode (ready at 144k)
2. **Cross-Lingual View** — "Cross-Lingual Navigation" mode (Sachverhalt/Dispositiv ready, Erwaegungen fails)
3. **Linear Hybrid Complement** — "Semantic+Citation Blend" mode (exploratory, not primary)

**Data blockers persist** requiring corpus lane resumption. Lane correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`.

---

## Next Steps (Require Corpus Lane Resumption)

| Action | Owner | Prerequisite |
|---|---|---|
| Generate 174k dense embeddings | legal-distance | bge_↔bger_ mapping + parquet 2022-2026 |
| Evaluate 174k citation heritage | legal-distance | 174k dense embeddings |
| Evaluate 174k section cross-lingual | legal-distance | 174k section extraction + dense encoding |
| Productize citation heritage mode | product | 174k dense + evaluation PASS |
| Productize cross-lingual mode | product | 174k dense + evaluation PASS |

---

## Product Integration Contract (Post-v1.0)

- **v1.0:** TF-IDF citation hybrids as primary navigation mode (beats semantic baseline JP 0.78 vs 0.43)
- **v1.1+:** Dense embedding integration for citation-heritage view and cross-lingual view

---

## Audit Declaration

This snapshot is **AUDIT-READY**. All evidence preserved, provenance documented, negative results recorded (Erwaegungen cross-lingual FAIL, true OOS ceiling ~0.53, v18 hierarchy NEGATIVE). No claim-bearing outputs overwritten. The lane deliverable for factory direction v34 is complete.

**Verified by:** Legal Distance Lane Researcher  
**Verification Timestamp:** 2026-10-06T22:00:00.000000Z  
**GitHub Run:** 37542786443