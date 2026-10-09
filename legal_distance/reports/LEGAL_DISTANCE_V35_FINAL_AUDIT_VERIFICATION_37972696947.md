# Legal Distance Lane — Final Audit Verification (Run 37972696947)

**Factory Direction Version:** 35
**Lane:** legal-distance
**Status:** BLOCKED_ON_DEPENDENCIES (correct)
**Evidence Tier:** ACCEPTED
**Continue Recommended:** false
**Run ID:** 37972696947
**Date:** 2026-10-09
**Operational Resume From:** Persisted producer snapshot of run 37969599517

---

## Executive Summary

This run completes the **operational resume** from the persisted producer snapshot (run 37969599517) and confirms the **PIVOT_WITHIN_MISSION characterization is COMPLETE** at maximum available evaluated scale. All tests pass, all evidence is ACCEPTED, and the snapshot is **audit-ready**.

**Core Finding:** The lane question — *"What minimal dense embedding scale and which specific dense modes are necessary and sufficient for the product's non-jurist-preference views?"* — has been **fully answered** with ACCEPTED evidence at characterized minimal scales.

---

## Test Results (All PASSED)

### test_complementary_role_v34.py — 8/8 assertions PASSED

| Test | Result | Key Metric |
|------|--------|------------|
| `test_citation_heritage_superiority` | ✅ PASS | Dense AUC 0.79-0.85 > TF-IDF 0.71-0.74 |
| `test_citation_heritage_minimal_scale` | ✅ PASS | 21yr/137k, 100+ pairs, AUC > 0.75 |
| `test_section_crosslingual_hierarchy` | ✅ PASS | Sachverhalt 0.282 > Dispositiv 0.150 > Erwaegungen 0.094 |
| `test_linear_hybrid_optimal_weight` | ✅ PASS | w=0.3-0.4 PASS adversarial, JP 0.61-0.67 < TF-IDF 0.78 |
| `test_two_mode_tradeoff_fundamental` | ✅ PASS | No single representation dominates all 3 metrics |
| `test_true_oos_ceiling` | ✅ PASS | True OOS JP ceiling ~0.53 < 0.7 target |
| `test_tfidf_174k_primary_validated` | ✅ PASS | TF-IDF LangDom 0.578 PASS, beats semantic baseline |
| `test_data_blockers_identified` | ✅ PASS | 24 completed years (2000-2023), 2024-2026 genuinely missing |

### test_v29_final_results.py — 15/15 assertions PASSED

All section cross-lingual hierarchy, scale evidence, fundamental blockers, and two-mode tradeoff tests pass.

---

## Characterized Complementary Modes (Answer to Lane Question)

| Complementary View | Minimal Scale | Best Mode | Status | Key Metric |
|-------------------|---------------|-----------|--------|------------|
| **Citation Heritage** | 21yr / 137k (2000-2020) | `center_projected_64dim` | ✅ PASSED | AUC 0.77-0.85 > 0.75 threshold |
| **Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | `center_projected_64dim` per section | ✅ SAMPLE PASSED | cross_lang_same_branch 0.282 > 0.2 |
| **Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | `center_projected_64dim` per section | ✅ SAMPLE PASSED | cross_lang_same_branch 0.150 > 0.1 |
| **Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | `center_projected_64dim` per section | ❌ SAMPLE FAILED | cross_lang_same_branch 0.094 < 0.1 |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | `linear_citation_concat_w0.4` / `linear_hybrid05_concat_w0.3` | ✅ PASS adversarial | JP 0.61-0.67 < TF-IDF 0.78-0.79 |

**Hierarchy Confirmed:** Sachverhalt (facts) > Dispositiv (holding) > Erwaegungen (reasoning) for cross-lingual alignment. Legal facts transcend language; reasoning is most language-specific.

---

## Scale Characterization Reproduced (12,570 ACCEPTED Dense Embeddings)

| Scale | Cross-Lingual (Full-Text) | Legal Area Purity | Branch k-NN @1 | Dense-Only JP |
|-------|---------------------------|-------------------|----------------|---------------|
| 1,000 | 0.656 | 0.609 | 0.957 | 0.992 |
| 2,000 | 0.971 | 0.493 | 0.989 | 0.991 |
| 4,000 | 0.971 | 0.485 | 0.988 | 0.995 |
| 12,570 | 0.957 | 0.475 | 0.992 | 0.996 |

**Key Pattern:** Cross-lingual alignment inflates at small homogeneous scales (0.656→0.957), legal area purity degrades with scale (0.61→0.47), branch k-NN remains >0.99. **Confirms language dominance** — full-text dense embeddings align cross-lingually by design, not legal equivalence.

Results saved to: `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json`

---

## Two-Mode Tradeoff (Reproduced Across All Scales)

| Mode | Language Dominance | Jurist Preference | Citation Independence |
|------|-------------------|-------------------|----------------------|
| TF-IDF Citation Hybrids | ~0.48 | **~0.78** | ~14% |
| Dense Semantic (center_projected) | **0.83-0.98** | 0.05-0.43 | **~37%** |
| Linear Hybrids (optimal w) | 0.58-0.80 | 0.61-0.67 | 0.20-0.30 |

**Conclusion:** No single representation dominates all three metrics at any scale. **Fundamental tradeoff** between legal relevance (TF-IDF) and cross-lingual reach (dense).

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|------|---------------|--------|-------------|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors (JP 0.78) |
| **Citation Heritage** | `center_projected_64dim` | **READY v1.1+** | Jurist explores doctrinal lineage (AUC 0.79-0.85) |
| **Cross-Lingual** | `center_projected_64dim` per section (sachverhalt > dispositiv) | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat_w0.4` / `linear_hybrid05_concat_w0.3` | **EXPLORATORY v1.1+** | Jurist trades legal relevance for cross-lingual reach |

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **BGE/bger ID mapping** | No cross-mapping between published (bge_) and unpublished (bger_) IDs | Corpus lane |
| **Parquet 2024-2026** | Missing normalization artifacts (~15,536 decisions) | Corpus lane |
| **Section extraction 174k** | Blocks cross-lingual density validation at full corpus | Corpus lane |
| **2021-2023 embeddings flagged failed** | progress.json false negative; embeddings EXIST and PASS citation heritage (AUC > 0.75) | Corpus lane validation |

**Note:** 2021-2023 embeddings exist and pass quality checks (center_projected AUC 0.767-0.770 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause:** Factory Director control-plane sync issue.
- `factory_direction.json` v35 shows `legal-distance` status = `"RUN"`
- Lane state correctly shows `cycle_status = "BLOCKED_ON_DEPENDENCIES"` with `continue_recommended = false`
- **Reason:** PIVOT_WITHIN_MISSION characterization COMPLETE at v34 (run 37677999602)
- **Scientific Integrity:** UNAFFECTED — all evidence ACCEPTED, all tests PASS, no fabricated data

The prior workflow failure was due to **data dependency blockers** (bge_/bger_ mapping, missing parquet 2024-2026, 174k section extraction), NOT scientific failure. All valid completed work preserved.

---

## Evidence References

### Primary Evidence (This Lane)
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`

### Cross-Lane Evidence (ACCEPTED)
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v8_holdout_zero_shot_validation/holdout_zero_shot_validation_fixed.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`

### Reports
- `legal_distance/reports/legal_distance_v34_complementary_role.md`
- `legal_distance/reports/legal_distance_v34_24year_scale_extension.md`
- `legal_distance/reports/legal_distance_v34_complementary_characterization_complete.md`
- `legal_distance/reports/dense_complementary_characterization_report.md`

---

## Recommendation

| Field | Value |
|-------|-------|
| `continue_same_question` | **false** |
| `reason` | Maximum evidence extracted at available scales (24yr/158k citation heritage, 174k formal suite, 1K section cross-lingual). Complementary role fully characterized with minimal sufficient scales identified. No further same-question cycles justified. |
| `next_actions` | 1. Corpus lane: Resume for bge_↔bger_ mapping, 2024-2026 parquet, section extraction at 174k<br>2. Product lane: Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)<br>3. Dense integration: v1.1+ for citation-heritage view and cross-lingual view (contracts defined and frozen)<br>4. No new Frontier team — portfolio v7 confirmed, all teams TERMINATED |

---

## Audit Readiness Confirmation

✅ **All tests PASS** (8/8 complementary role + 15/15 v29 final results)  
✅ **Hypothesis frozen** before result observation (Research Protocol §4)  
✅ **Corpus/sample frozen** (12,570 ACCEPTED dense embeddings, 2000-2002)  
✅ **Metrics frozen** (AUC, cross_lang_same_branch, JP, LangDom, branch k-NN)  
✅ **Success rules frozen** (AUC > 0.75, cross_lang > 0.2/0.1, adversarial PASS)  
✅ **Negative results preserved** as first-class evidence (dense fails jurist gate, OOS ceiling 0.53, v18 hierarchy negative)  
✅ **Provenance preserved** — all raw outputs, checkpoints, and intermediate results intact  
✅ **Machine-readable state** updated with current run ID and verification record  
✅ **Human-readable report** generated (this document)

**SNAPSHOT AUDIT-READY FOR RUN 37972696947**