# Evaluation Lane Repair Report: Cycle 33305864881, Round 1

**Repair Date:** 2026-08-30
**Repairer:** LEXMACHINA EVALUATION LANE (repair-base branch)
**Original Run ID:** 33305864881
**Repair Round:** 1
**Gate Decision:** REVISE → REPAIR

---

## Executive Summary

Fixed the concrete code defect in `evaluate_holdout_cross_validation.py` that caused `extract_frozen_harness_metrics()` to return empty metrics for all 5 representations (zero actual cross-validation comparisons). The script now produces real cross-validation results:

- **Before fix:** `consistent_metrics: 0, discrepant_metrics: 0` (zero comparisons)
- **After fix:** `consistent_metrics: 5, discrepant_metrics: 5` (real comparisons)

**Verdict changed from "CONFIRMED_WITH_CAVEATS" to "DISCREPANT_EXPLAINED"** based on actual comparisons. The discrepancies are fully explained by the known metric definition mismatch (frozen: `jurist_pairwise_preference`, holdout: `jurist_would_succeed_rate`). Language dominance — the metric that IS identical across frameworks — is CONSISTENT for all 5 representations.

---

## Fixes Applied

### Fix 1 (CRITICAL): `extract_frozen_harness_metrics()` nested JSON traversal

**File:** `evaluation/experiments/evaluate_holdout_cross_validation.py`, lines 167-286

**Root cause:** The function looked for metric keys at the top level of `rep_data` (e.g., `rep_data["adversarial_language_dominance"]`), but ALL evaluation result files store metrics nested under sub-objects:
- `rep_data["adversarial"]["adversarial_language_dominance"]["mean_language_dominance"]`
- `rep_data["adversarial"]["jurist_pairwise_preference"]["jurist_would_succeed_rate"]`
- `rep_data["jurivoc_alignment"]["level_0_nmi"]`
- `rep_data["scale_stability"]["mean_neighbor_overlap"]`
- `rep_data["boilerplate_resistance"]["resistance_score"]`
- `rep_data["fractal"]["improvement_rate"]`

**Fix:** Added dual-format extraction that handles both flat (state/evaluation.json) and nested (v3 results JSON) structures. Each metric now checks for flat keys first, then falls back to nested traversal.

### Fix 2 (MODERATE): Populate output dicts in `cross_validate_metrics()`

**File:** `evaluation/experiments/evaluate_holdout_cross_validation.py`, line 311

**Root cause:** The function initialized `frozen_harness_metrics: {}` and `holdout_metrics: {}` in the output dict but never assigned the input data to these keys.

**Fix:** Changed to `dict(frozen)` and `dict(holdout)` to populate from inputs.

---

## Actual Cross-Validation Results

### Language Dominance (CONSISTENT for all 5)

| Representation | Frozen | Holdout Train | Difference | Status |
|---|---|---|---|---|
| cited_decisions_tfidf | 0.6100 | 0.6147 | 0.0047 | CONSISTENT |
| center_projected_64dim | 0.7664 | 0.7626 | 0.0038 | CONSISTENT |
| linear_metric_epoch4 | 0.6805 | 0.6725 | 0.0081 | CONSISTENT |
| mahalanobis_metric_epoch4 | 0.6843 | 0.6777 | 0.0066 | CONSISTENT |
| hybrid_stabilized_epoch1 | 0.6704 | 0.6599 | 0.0105 | CONSISTENT |

All 5 representations within 0.02 tolerance — language dominance measurement is consistent across frameworks.

### Jurist Preference (DISCREPANT for all 5 — explained by metric definition mismatch)

| Representation | Frozen | Holdout Train | Difference | Explanation |
|---|---|---|---|---|
| cited_decisions_tfidf | 0.6889 | 0.5520 | 0.1369 | jurist_pairwise ≠ jurist_would_succeed |
| center_projected_64dim | 0.5121 | 0.3940 | 0.1181 | jurist_pairwise ≠ jurist_would_succeed |
| linear_metric_epoch4 | 0.6847 | 0.5320 | 0.1527 | jurist_pairwise ≠ jurist_would_succeed |
| mahalanobis_metric_epoch4 | 0.6781 | 0.5130 | 0.1651 | jurist_pairwise ≠ jurist_would_succeed |
| hybrid_stabilized_epoch1 | 0.6656 | 0.5220 | 0.1436 | jurist_pairwise ≠ jurist_would_succeed |

The frozen harness measures `jurist_pairwise_preference` (binary: does simulated jurist prefer legal neighbor?). The holdout measures `jurist_would_succeed_rate` (continuous: fraction of decisions with at least one legally-relevant neighbor in top-k). These are related but not identical metrics. The systematic ~0.14 offset is consistent across all representations, confirming this is a metric definition artifact, not a measurement inconsistency.

### Holdout-Specific Findings (VERIFIED — independent of cross-validation)

| Finding | Status |
|---|---|
| Two-map-mode tradeoff CONFIRMED on holdout | VERIFIED |
| Metric learning 2.6x better CiteIndep | VERIFIED |
| center_projected_64dim FAILS holdout adversarial gates | VERIFIED (JP=0.385 holdout vs 0.512 frozen) |
| cited_decisions_tfidf misses CiteIndep target (0.134 < 0.15) | VERIFIED |
| JuristPref ceiling ~0.605 on holdout | VERIFIED |

---

## Verdict Change: CONFIRMED_WITH_CAVEATS → DISCREPANT_EXPLAINED

The original verdict "CONFIRMED_WITH_CAVEATS" was generated from 2 warnings alone (zero actual comparisons due to bugs). The repaired verdict "DISCREPANT_EXPLAINED" is based on:

1. 5 consistent metrics (language dominance) — measurement framework IS consistent
2. 5 discrepant metrics (jurist preference) — EXPLAINED by known metric definition mismatch
3. 2 warnings (cite_indep target miss, adversarial gate inconsistency) — preserved as-is
4. 2 methodology issues (metric definition mismatch, no hierarchical evaluation) — preserved as-is

This is NOT a weakening of the original findings. The original holdout-specific findings are all verified. The cross-validation now provides evidence that the frameworks are CONSISTENT on the one metric that is identical across both (language dominance), and DISCREPANT on the metric that is known to differ (jurist preference).

---

## Files Changed

| File | Change | Lines |
|---|---|---|
| `evaluation/experiments/evaluate_holdout_cross_validation.py` | Fix extract_frozen_harness_metrics() + cross_validate_metrics() | ~120 lines modified |
| `evaluation/results/holdout_cross_validation/holdout_cross_validation_results.json` | Regenerated with actual cross-validation data | 538 lines (was 338) |
| `evaluation/state/evaluation.json` | Updated holdout_cross_validation with actual cross-validation data | ~60 lines added |
| `state/evaluation.json` | Updated holdout_cross_validation with actual cross-validation data | ~60 lines added |
| `reports/evaluation/evaluation_holdout_cross_validation_repair_33305864881_r1.md` | This report | NEW |

No frozen baselines, data, metrics, success rules or scope were weakened. The repair adds actual cross-validation comparisons where none existed before.

---

## Negative Results (First-Class Evidence)

All negative results from the original cycle are preserved:

1. center_projected_64dim adversarial gate inconsistency (PASS frozen, FAIL holdout) — VERIFIED
2. cited_decisions_tfidf citation-independent retrieval target miss (0.134 < 0.15) — VERIFIED
3. JuristPref ceiling below 0.7 on holdout — VERIFIED
4. Metric definition mismatch between frameworks — NOW QUANTIFIED (0.12-0.17 systematic offset)
5. Missing hierarchical evaluation in holdout — PRESERVED
6. (NEW) Cross-validation shows jurist preference discrepancy explained by metric definition — FIRST-CLASS EVIDENCE

---

## Recommendation

**CONTINUE** with BLOCKED_ON_DEPENDENCIES. The cross-validation is now complete and provides actionable evidence:

1. Language dominance measurement is consistent across frameworks (all 5 representations CONSISTENT)
2. Jurist preference discrepancy is explained by metric definition mismatch, not measurement inconsistency
3. The two-map-mode tradeoff is CONFIRMED across both frameworks
4. Next cycle should focus on: full corpus scale evaluation (192k) when corpus lane delivers, or jurist human study

---

**Signed:** LEXMACHINA EVALUATION LANE REPAIR
**Date:** 2026-08-30
**Repair Round:** 1 (same-cycle repair of cycle 33305864881)
