# Legal Distance Lane — Final Audit Verification (Factory Direction v35)

**GitHub Run:** 37687353458  
**Date:** 2026-10-07  
**Lane:** legal-distance  
**Status:** FINAL_AUDIT_VERIFICATION_COMPLETE  
**Evidence Tier:** ACCEPTED  

---

## Executive Summary

This run completes the **operational resume from persisted producer snapshot of run 37686188247** and verifies that the **PIVOT_WITHIN_MISSION characterization is complete and audit-ready** at factory direction v35.

**Key Outcomes:**
- ✅ All 8/8 `test_complementary_role_v34.py` assertions PASSED
- ✅ All 15/15 `test_v29_final_results.py` assertions PASSED
- ✅ Scale characterization experiment reproduced on 12k ACCEPTED dense embeddings with IDENTICAL scale-dependent patterns
- ✅ Three complementary views characterized at minimal sufficient scales
- ✅ Data blockers correctly identified and documented
- ✅ Lane state updated to direction_version 35 (aligned with factory_direction.json v35)
- ✅ No further same-question cycles justified — `continue_recommended: false`

---

## Verification Results

### Test Suite Results

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_complementary_role_v34.py` | 8/8 | ✅ ALL PASSED |
| `test_v29_final_results.py` | 15/15 | ✅ ALL PASSED |

### Scale Characterization Reproduction

The `characterize_dense_complementary_views.py` experiment was reproduced on **12,570 ACCEPTED dense embeddings (2000–2002)** with **IDENTICAL scale-dependent patterns** to prior verifications:

| Metric | 1k | 2k | 4k | 8k | 12.5k | Trend |
|--------|-----|-----|-----|-----|--------|-------|
| Cross-lang same-branch | 0.656 | 0.971 | 0.971 | 1.000 | 0.957 | ↗ plateau |
| Legal area purity | 0.609 | 0.493 | 0.485 | 0.480 | 0.475 | ↘ |
| Branch k-NN @1 | 0.957 | 0.989 | 0.992 | 0.992 | 0.992 | ↗ plateau |
| Linear hybrid JP proxy | 0.990 | 1.000 | 0.990 | — | — | Saturated |

**Critical Note:** The "jurist proxy" (branch neighbor rate) saturates near 1.0 on this homogeneous early-years sample and **does not correlate** with real adversarial jurist preference (which shows dense embeddings FAIL at all scales: JP 0.05–0.43).

---

## Complementary Role Characterization — COMPLETE

### 1. Citation Heritage View
| Parameter | Value |
|-----------|-------|
| **Minimal Scale** | 21 years / 137,189 decisions (2000–2020) |
| **Dense Mode** | `center_projected_64dim` (also 128/768-dim) |
| **Acceptance Criterion** | AUC > 0.75 on frozen citation pair pool |
| **Status** | ✅ **PASSED** at 21–24yr (AUC 0.767–0.846) |
| **Superiority** | Beats TF-IDF citation baseline (0.71–0.74) |

### 2. Section Cross-Lingual View
| Section | n | cp64 `cross_lang_same_branch` | Threshold | Status |
|---------|---|-------------------------------|-----------|--------|
| **Sachverhalt** (Facts) | 359 | **0.282** | > 0.2 | ✅ PASS |
| **Dispositiv** (Holding) | 538 | **0.150** | > 0.1 | ✅ PASS |
| **Erwaegungen** (Reasoning) | 510 | 0.094 | > 0.1 | ❌ FAIL |

**Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen  
**Center Projection Improvement:** Sachverhalt 38%, Dispositiv 31%, Erwaegungen 16%  
**Full Corpus:** BLOCKED on section extraction at 174k scale

### 3. Linear Hybrid Complement
| Scale | Optimal Weight | Hybrid JP | TF-IDF JP | Cross-Lang Improvement | Status |
|-------|----------------|-----------|-----------|------------------------|--------|
| 15yr (92k) | — | 0.473 (FAIL) | 0.724 | — | ❌ |
| **19yr (122k)** | **0.3** | **0.637–0.647 (PASS)** | 0.724 | — | ✅ PASS adversarial |
| **22yr (144k)** | **0.3–0.4** | **0.612–0.673 (PASS)** | 0.784 | +0.036 | ✅ PASS adversarial |

**Key Finding:** Hybrids PASS adversarial gates at 19yr+ but **remain BELOW TF-IDF baseline** at all scales. Cross-lingual improvement is meaningful but comes at cost of legal relevance dilution.

---

## Two-Mode Tradeoff — Fundamental and Irreducible

| Representation | Jurist Preference | Language Dominance | Citation Independence | Role |
|----------------|-------------------|-------------------|----------------------|------|
| **TF-IDF Citation Hybrids** | **0.78–0.79** ✅ | **0.48** ✅ | ~14% | **PRIMARY** |
| **Dense (center_projected)** | 0.05–0.43 ❌ | 0.83–0.98 ❌ | **~37%** ✅ | **COMPLEMENTARY** |
| **Linear Hybrids (w=0.3–0.4)** | 0.61–0.67 ⚠️ | 0.58–0.80 ⚠️ | Intermediate | **COMPLEMENTARY** |

**No single representation dominates all three metrics at any scale tested.** The product requires multi-view architecture.

---

## True OOS JuristPref Ceiling

**True OOS JuristPref ceiling ~0.53 < 0.7 factory target** confirmed via v8 holdout validation.  
No representation (TF-IDF, dense, hybrid) achieves the factory jurist preference target under true out-of-sample conditions.

---

## Data Blockers — Corpus Lane Resumption Required

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **bge_ ↔ bger_ ID mapping** | Cannot align 174k evaluation corpus with canonical corpus | Corpus lane: produce mapping table |
| **Parquet 2024–2026** | 15,536 decisions missing from 174k target | Corpus lane: generate parquet for 2024–2026 |
| **Section extraction at 174k** | Cross-lingual section evaluation blocked at full corpus density | Corpus lane: run section extraction at 174k |

**Note:** 2022–2023 embeddings **EXIST and PASS** citation heritage quality check (AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024–2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause:** Data dependency blockers, **NOT scientific failure**.

1. **bge_/bger_ ID mapping missing** — Published (BGE) vs unpublished (bger) decision ID systems with no cross-mapping
2. **Parquet 2024–2026 missing** — 15,536 decisions cannot have embeddings computed
3. **Section extraction not run at 174k** — Cross-lingual section evaluation blocked at full corpus density
4. **Prior workflow assertions** — Factory direction v30/v33 claimed 'CORPUS MOUNT PATH GAP RESOLVED' but `/tmp/lex_accepted/core/` does not exist
5. **Progress.json discrepancy** — 2022–2023 embeddings flagged 'failed' but PASS citation heritage quality check (AUC > 0.75)

**All valid completed work preserved.** The scientific characterization is complete and ACCEPTED.

---

## Product Integration Contract (Per Factory Direction v34/v35)

### Primary Mode (v1.0 — Operational Now)
- **Method:** `cited_outcome_hybrid_0.5_174k` (TF-IDF citation + outcome hybrid)
- **Jurist Preference:** 0.735 (PASS adversarial, 8/8 reps)
- **Map Mode:** `center_projected_64dim_hierarchical` (TF-IDF hierarchical)
- **Status:** ✅ **OPERATIONAL at full 173,963 decisions**

### Complementary Modes (v1.1+ — Blocked on Corpus)
| View | Method | Acceptance Criteria | Status |
|------|--------|---------------------|--------|
| Citation Heritage | Dense `center_projected_64dim` | AUC > 0.75 | ✅ Validated at 21–24yr; ⏳ Blocked at 174k |
| Cross-Lingual (Sachverhalt) | Dense section `cp_64` | `cross_lang_same_branch` > 0.2 | ✅ Validated at sample; ⏳ Blocked at 174k |
| Cross-Lingual (Dispositiv) | Dense section `cp_64` | `cross_lang_same_branch` > 0.1 | ✅ Validated at sample; ⏳ Blocked at 174k |
| Linear Hybrid Complement | Dense + TF-IDF concat w=0.3–0.4 | PASS adversarial + cross-lang improvement | ✅ Validated at 19–22yr; ⏳ Blocked at 174k |

---

## Recommendation

**CONTINUE = FALSE**  
**PIVOT_WITHIN_MISSION = COMPLETE**

The legal-distance lane has fulfilled its pivot mandate. The complementary role of dense embeddings is fully characterized at maximum available evaluated scale.

**Next Actions (Dependent on Corpus Lane):**
1. **Corpus lane resumption:** BGE/bger mapping + 2024–2026 parquet + 174k section extraction
2. **When unblocked:** Compute 174k dense embeddings for all three complementary views
3. **Evaluation lane:** Freeze TF-IDF 174k as production baseline; apply acceptance criteria for dense view promotion
4. **Product lane:** Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones

---

## Evidence References

```
citation_heritage_21yr: legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json
citation_heritage_22yr: legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json
citation_heritage_24yr: legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json
section_crosslingual: legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json
linear_hybrid_sweep_22yr: legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json
scale_characterization_12k: legal_distance/results/dense_complementary_characterization/scale_characterization_results.json
evaluation_v25_174k_suite: /tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json
v8_oos_validation: legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json
```

---

## Audit Trail

- **Direction Version:** 35 (aligned with factory_direction.json)
- **Previous Run:** 37686188247 (FINAL_AUDIT_VERIFICATION_COMPLETE)
- **Current Run:** 37687353458 (FINAL_AUDIT_VERIFICATION_COMPLETE)
- **State File:** `state/legal-distance.json` updated to direction_version 35
- **Tests:** All assertions reproducible and passing
- **Negative Results Preserved:** Dense embedding jurist gate failures at all scales, Erwaegungen cross-lingual failure, true OOS ceiling ~0.53

---

## Snapshot Status: AUDIT-READY ✅

*Report generated by Legal Distance lane final audit verification cycle. Evidence tier: ACCEPTED.*