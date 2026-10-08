# LEGAL DISTANCE V35 — CHARACTERIZATION COMPLETE VERIFICATION

**Run ID:** 37853284088  
**Date:** 2026-10-08  
**Factory Direction:** v35  
**Lane:** legal-distance  
**Status:** BLOCKED_ON_DEPENDENCIES | continue_recommended: false

---

## Executive Summary

The **PIVOT_WITHIN_MISSION** characterization of dense embeddings' complementary role alongside TF-IDF citation hybrids is **COMPLETE**. All validation tests pass (23/23). The lane has answered its question and is correctly blocked on corpus lane dependencies.

**Question Answered:** *What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?*

---

## Test Results — ALL PASS

| Test Suite | Tests | Result |
|------------|-------|--------|
| `test_complementary_role_v34.py` | 8 | ✅ PASS |
| `test_v29_final_results.py` | 15 | ✅ PASS |
| **TOTAL** | **23** | ✅ **ALL PASS** |

---

## Three Complementary Dense Modes — Characterized at Minimal Scales

### 1. CITATION HERITAGE VIEW
- **Minimal Scale:** 21 years / 137k decisions (2000–2020)
- **Best Mode:** `center_projected_64dim`
- **Performance:** AUC 0.77–0.85 > 0.75 threshold (PASSED at 21–24yr, 137k–158k)
- **Superiority:** Dense AUC > TF-IDF citation baseline (0.71–0.74) at all scales
- **Requirement:** Recent years (2019+) for sufficient citation pair density (≥100 pairs)

### 2. SECTION CROSS-LINGUAL VIEW
- **Minimal Scale:** 1K sample with section extractions
- **Best Mode:** `center_projected_64dim` per section
- **Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen
- **Results:**
  - Sachverhalt: cross_lang_same_branch = **0.282** > 0.2 ✅ PASS
  - Dispositiv: cross_lang_same_branch = **0.150** > 0.1 ✅ PASS
  - Erwaegungen: cross_lang_same_branch = **0.094** < 0.1 ❌ FAIL
- **Full Corpus:** BLOCKED on section extraction at 174k scale

### 3. LINEAR HYBRID COMPLEMENT
- **Minimal Scale:** 19 years / 122k decisions (2000–2018)
- **Optimal Weights:** w=0.3–0.4 (shifts toward semantic at larger scale)
- **Performance:** PASS both adversarial gates (JP 0.61–0.67)
- **Status:** BELOW TF-IDF baseline (JP 0.78–0.79) — **NOT primary**
- **Value:** Cross-lingual improvement over TF-IDF (+24–29%)

---

## Two-Mode Tradeoff — FUNDAMENTAL (Reproduced at All Scales)

| Representation | LangDom | JP | CiteIndep | Role |
|----------------|---------|-----|-----------|------|
| TF-IDF Citation Hybrids | ~0.48 | **~0.78** | ~14% | **PRIMARY** |
| Dense (center_projected) | ~0.83–0.98 | 0.05–0.43 | ~37% | **COMPLEMENTARY** |
| Linear Hybrids (w=0.3–0.4) | ~0.58–0.80 | 0.61–0.67 | Intermediate | **COMPLEMENTARY** |

**No single representation dominates all three metrics at any scale.** Multi-view architecture is necessary.

---

## True OOS Ceiling Confirmed
- **JuristPref ceiling:** ~0.53 (v8 holdout validation)
- **Factory target:** 0.7
- **Achievable:** ❌ NO — no representation achieves target under true OOS conditions

---

## Data Blockers — Require Corpus Lane Resumption

| Blocker | Status | Impact |
|---------|--------|--------|
| **bge_ ↔ bger_ ID mapping** | ❌ Missing | Cannot align evaluation corpus with canonical corpus |
| **Parquet 2024–2026** | ❌ Missing | 15,536 decisions missing from 174k target |
| **Section extraction at 174k** | ❌ Not run | Cross-lingual section evaluation blocked at full density |

**Note:** 2022–2023 embeddings **EXIST and PASS** citation heritage quality (center_projected AUC > 0.75 with 730 positive pairs). Only 2024–2026 are genuinely missing.

---

## Product Integration Contract (Frozen)

### v1.0 — OPERATIONAL NOW
- **Primary Navigation:** `cited_outcome_hybrid_0.5_174k` (TF-IDF)
- **Jurist Preference:** 0.735 (PASS adversarial)
- **Map Mode:** `center_projected_64dim_hierarchical` (TF-IDF hierarchical)
- **Scale:** Full 173,963 decisions

### v1.1+ — BLOCKED ON CORPUS
| View | Method | Acceptance Criteria | Status |
|------|--------|---------------------|--------|
| Citation Heritage | Dense `center_projected_64` | AUC > 0.75 | ✅ Validated 21–24yr; ⏳ Blocked 174k |
| Cross-Lingual (Sachverhalt) | Dense section `cp_64` | cross_lang > 0.2 | ✅ Validated sample; ⏳ Blocked 174k |
| Cross-Lingual (Dispositiv) | Dense section `cp_64` | cross_lang > 0.1 | ✅ Validated sample; ⏳ Blocked 174k |
| Linear Hybrid Complement | Dense + TF-IDF concat w=0.3–0.4 | PASS adversarial + cross-lang improvement | ✅ Validated 19–22yr; ⏳ Blocked 174k |

---

## Evidence References

### Primary Results
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json` (ACCEPTED)
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/` (21yr, 22yr, 24yr)
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`

### Evaluation Baselines
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` (TF-IDF 174k)
- `/tmp/lex_accepted/evaluation/results/evaluation/v8_holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json` (True OOS)

### Reports
- `legal_distance/reports/legal_distance_v34_complementary_characterization_complete.md` (Primary characterization)
- `legal_distance/reports/legal_distance_v34_minimal_dense_scale_characterization.md`
- `legal_distance/reports/LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37838941187.md` (Prior audit)

### Tests
- `tests/legal_distance/test_complementary_role_v34.py` (8 assertions)
- `tests/legal_distance/test_v29_final_results.py` (15 assertions)

---

## Lane State (Machine-Readable)

```json
{
  "lane": "legal-distance",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37838941187",
  "next_recommendation": "Characterization COMPLETE. No further same-question cycles justified. Corpus lane resumption required for 174k dense delivery.",
  "tests_passed": 23,
  "verification_run": 37853284088
}
```

---

## Recommendation

**BLOCKED** — The legal-distance lane has completed its PIVOT_WITHIN_MISSION characterization mandate. No further same-question cycles are justified. The lane is correctly `BLOCKED_ON_DEPENDENCIES` awaiting:

1. **Corpus lane**: bge_/bger_ ID mapping, parquet 2024–2026, section extraction at 174k
2. **Downstream lanes** (fractal-map, evaluation, product): Will integrate dense complementary views once corpus blockers resolve

**Scientific Integrity:** UNAFFECTED — all evidence ACCEPTED, all tests PASS, negative results preserved as first-class evidence.

---

*Verification complete. Report generated by Legal Distance lane for factory direction v35, run 37853284088.*