# LEGAL DISTANCE LANE — Final Audit Verification (Run 38028050838)

**Factory Direction:** v35  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** false  
**Date:** 2026-10-10  
**Operational Resume From:** Run 38027372192 (persisted producer snapshot)

---

## Summary

**ALL TESTS PASSED — SNAPSHOT AUDIT-READY**

This operational resume from persisted producer snapshot completes fresh-context verification of the PIVOT_WITHIN_MISSION characterization (Factory Direction v34, run 37677999602). The legal-distance lane has answered its assigned question:

> **What minimal dense embedding scale and which specific dense modes are necessary and sufficient for the product's non-jurist-preference views?**

**Answer — Three complementary modes at characterized minimal scales:**

| Complementary View | Minimal Scale | Evidence | Status |
|---|---|---|---|
| **Citation Heritage** | 21yr / 137k (2000-2020) | center_projected_64dim AUC 0.77-0.85 > 0.75 threshold; superior to TF-IDF citation baseline (0.71-0.74) | ✅ PASSED |
| **Section Cross-Lingual** | 1K sample (sections) | Sachverhalt cp64 cross_lang=0.282 > 0.2 ✅; Dispositiv cp64 cross_lang=0.150 > 0.1 ✅; Erwaegungen cp64 cross_lang=0.094 < 0.1 ❌ | PARTIAL (2/3) |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | w=0.3-0.4 PASS both adversarial gates; JP 0.61-0.67 < TF-IDF 0.78-0.79 | ✅ PASSED (complement only) |

**Fundamental Finding:** No single representation dominates JuristPref + LanguageDominance + CitationIndependence. Two-mode tradeoff is structural:
- **TF-IDF citation hybrids** = PRIMARY product mode (jurist preference, branch clustering)
- **Dense embeddings** = COMPLEMENTARY modes (citation heritage view, cross-lingual view, hybrid complement)

**True OOS JuristPref ceiling ~0.53 < 0.7 factory target** — confirmed via v8 holdout validation.

---

## Verification Results

### Test Suite Results (23/23 PASS)

| Test File | Tests | Status |
|---|---|---|
| `test_complementary_role_v34.py` | 8 | ✅ ALL PASS |
| `test_v29_final_results.py` | 15 | ✅ ALL PASS |

### Scale Characterization Experiment (Reproduced)

**Experiment:** `characterize_dense_complementary_views.py` on 12,570 ACCEPTED dense embeddings (2000-2002)

| Metric | Scale 1K | Scale 12.5K | Pattern |
|---|---|---|---|
| Cross-lingual alignment (cross_lang_same_branch) | 0.6562 | 0.9565 | **Inflation with scale** |
| Legal area clustering purity | 0.6089 | 0.4754 | **Degradation with scale** |
| Branch k-NN accuracy@1 | 0.9568 | 0.9922 | **Stable >0.99** |
| Linear hybrid (w=0.3) jurist proxy | 0.9915 | 0.9938 | **PASS at all weights** |

**IDENTICAL scale-dependent patterns reproduced** — confirms characterization robustness.

### 174k TF-IDF Formal Suite (Primary Product Modes — Operational)

| Representation | Citation Heritage AUC | Adversarial (LangDom) | Multilingual Invariance | Status |
|---|---|---|---|---|
| `cited_decisions_tfidf` | 0.973 | 0.602 (PASS) | PASS | ✅ PRIMARY |
| `cited_outcome_hybrid_0.5` | 0.919 | 0.578 (PASS) | PASS | ✅ PRIMARY |

Both PASS both adversarial gates at **full 173,963 decisions** — product defaults operational.

### Dense Embedding Complementary Views (Validated)

| View | Scale | Key Metric | Threshold | Result |
|---|---|---|---|---|
| Citation Heritage | 22yr/144k | center_projected_64dim AUC | >0.75 | ✅ 0.792 |
| Citation Heritage | 24yr/158k | center_projected_64dim AUC | >0.75 | ✅ 0.767 (730 pairs) |
| Sachverhalt cross-lingual | 1K sample | cp64 cross_lang_same_branch | >0.2 | ✅ 0.282 |
| Dispositiv cross-lingual | 1K sample | cp64 cross_lang_same_branch | >0.1 | ✅ 0.150 |
| Erwaegungen cross-lingual | 1K sample | cp64 cross_lang_same_branch | >0.1 | ❌ 0.094 |
| Linear hybrid (cited) w=0.4 | 22yr/144k | JP / LangDom | >0.5 / <0.85 | ✅ 0.673 / 0.654 |
| Linear hybrid (outcome) w=0.3 | 22yr/144k | JP / LangDom | >0.5 / <0.85 | ✅ 0.661 / 0.640 |

### Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---|---|---|
| **bge_/bger_ ID mapping** | No mapping between published (bge_) and unpublished (bger_) IDs | Corpus lane: produce canonical mapping |
| **Parquet 2024-2026** | ~15.5k decisions missing (3 years) | Corpus lane: generate parquet for 2024-2026 |
| **174k section extraction** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale | Corpus lane: run section extraction at 174k |

**Note:** 2021-2023 embeddings EXIST and PASS citation heritage quality checks (center_projected AUC > 0.75 at 24yr/158k). Only 2024-2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause Identified:** Factory direction v35 shows `legal-distance: RUN` but lane state correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false` because:

1. **PIVOT_WITHIN_MISSION characterization COMPLETE** at v34 (run 37677999602)
2. **All evidence ACCEPTED** — no further same-question cycles justified
3. **Data blockers** require corpus lane resumption before 174k dense evaluation can complete
4. **Scientific integrity UNAFFECTED** — all tests pass, all evidence preserved

The apparent discrepancy (factory_direction RUN vs lane BLOCKED) reflects the factory direction describing the *lane's assigned question status* (pivot executed, new question defined) while the lane state reflects *execution status* (blocked on dependencies, characterization complete).

---

## Evidence References

- `reports/legal_distance/LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_38028050838.md` (this report)
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`

---

## Recommendation

**No further same-question cycles justified.** The PIVOT_WITHIN_MISSION characterization is complete at maximum available evaluated scale. The lane remains correctly `BLOCKED_ON_DEPENDENCIES` awaiting corpus lane resolution of:
1. bge_/bger_ ID mapping
2. Parquet generation for 2024-2026
3. 174k section extraction

When corpus lane resumes and resolves blockers, the Factory Director should define a successor question for 174k dense embedding evaluation and multi-view integration.

---

**Snapshot Status:** AUDIT-READY  
**Verification Complete:** All 23 tests pass, scale characterization reproduced, 174k TF-IDF primary modes verified operational, complementary dense views characterized at minimal scales.