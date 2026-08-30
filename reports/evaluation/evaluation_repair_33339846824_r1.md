# Evaluation v12 Temporal Holdout — Repair Report (Round 1)

**Original Audit:** CYCLE_33339846824 (REVISE)
**Repair Round:** 1
**Lane:** evaluation
**Date:** 2026-08-30
**GitHub Run:** 33340692528

---

## 1. Defects Repaired

### F-1: Incorrect Random CV Baselines in Experiment Code [MEDIUM → REPAIRED]

**Root cause:** The experiment code `evaluation/experiments/run_v12_temporal_holdout.py` (lines 688-694) hardcoded `random_cv_jps` values using fold-1 results instead of proper 5-fold CV means from `v12_cross_mode_cv_latest.json`.

**Incorrect values → Correct values:**
- `citation_tfidf`: 0.7333 → **0.7850** (was fold 1 value)
- `cited_outcome_hybrid_0.5`: 0.7250 → **0.7800** (was fold 1 value)
- `cited_outcome_hybrid_0.7`: 0.7417 → **0.7750** (was unknown source)
- `center_projected_64dim`: 0.7992 → 0.7992 (unchanged, correct)
- `linear_citation_ridge`: 0.8600 → 0.8600 (unchanged, correct)

**Repair:** Replaced hardcoded values with correct 5-fold CV means. Added source comment referencing `results/evaluation/v12_cross_mode_cv/v12_cross_mode_cv_latest.json`.

**Impact:** Comparison table deltas corrected. False claim "cited_outcome_hybrid_0.5 IMPROVES on temporal holdout (+0.0333)" removed. Corrected deltas: cited_outcome_hybrid_0.5 degrades -0.0258, citation_tfidf degrades -0.0308, cited_outcome_hybrid_0.7 degrades -0.0375.

### F-2: Incorrect Report Comparison Table [LOW → REPAIRED]

**Root cause:** Report `reports/evaluation/evaluation_v12_temporal_holdout_33339846824.md` used the same incorrect baseline values, leading to false claims about individual representation temporal behavior.

**Repairs applied:**
1. Updated "Temporal vs Random CV Comparison" table with corrected deltas
2. Removed false "Notable" claim about cited_outcome_hybrid_0.5 improving
3. Updated Key Findings point 4 to reflect corrected individual representation degradation
4. Updated Product Implications point 3 to remove false claim about outcome signal generalization
5. Updated Negative Results section with correct baseline values
6. Updated results file reference to new run ID

---

## 2. Core Finding Verification

The core finding is **UNCHANGED and VERIFIED**:
- v12 cross-mode combinations generalize to temporal holdout
- Best combination (linear_hybrid05_concat JP=0.8375) beats best baseline (center_projected_64dim JP=0.7750) by **+0.0625**
- Temporal degradation minimal (+0.0308 for ridge)
- All 9 representations pass both adversarial gates on temporal test set
- Verdict: **REPLICATED**

---

## 3. Negative Results Preserved

All 11 negative results from prior cycles preserved in state/evaluation.json:
1. center_projected_768 FAILS jurist pairwise
2. multilingual_e5_small_pretrained catastrophic hierarchy collapse
3. CCA and single Procrustes catastrophic for cross-lingual alignment
4. Distinguishing/overruling citation roles too sparse
5. Boilerplate resistance NEGATIVE for ALL representations
6. JuristPref > 0.7 NOT MET by any v11 representation
7. v11 hierarchy loss NOT load-bearing
8. v11 models WORSE than metric learning baselines
9. debiased_citation_blended FALSIFIED on canonical harness
10. Prior FALSIFICATION on 1000-decision corpus superseded
11. **NEW from this repair:** All individual representations degrade on temporal holdout (all negative deltas)

---

## 4. Test Verification

All 10 tests in `tests/evaluation/test_v12_temporal_holdout.py` PASS:
- test_results_file_exists ✅
- test_config_hash_consistent ✅
- test_v12_hypothesis_replicates ✅
- test_all_combinations_pass_adversarial_gates ✅
- test_best_combination_beats_baseline ✅
- test_center_projected_normal_on_temporal ✅
- test_temporal_degradation_minimal ✅
- test_temporal_improvement_positive ✅
- test_split_is_temporal ✅
- test_train_test_sizes_reasonable ✅

---

## 5. Delta Verification

**No frozen baselines weakened.** Config hash unchanged (4323f833fa72366a). Adversarial thresholds unchanged. Corpus unchanged.

**Durable delta achieved:** Corrected comparison table and report with accurate baseline values. Experiment re-run with correct 5-fold CV means. No zero-delta repair.

---

## 6. Files Modified

| File | Change |
|------|--------|
| `evaluation/experiments/run_v12_temporal_holdout.py` | Fixed hardcoded random_cv_jps (lines 687-700) |
| `reports/evaluation/evaluation_v12_temporal_holdout_33339846824.md` | Updated comparison table, key findings, product implications, negative results |
| `results/evaluation/v12_temporal_holdout/v12_temporal_holdout_eval_v12_temporal_1788131137.json` | New results file with corrected comparison |
| `results/audit/evaluation/CYCLE_33339846824_r1_GATE.json` | New gate file (PASS) |

---

*End of Repair Report — Evaluation 33339846824 Round 1*
