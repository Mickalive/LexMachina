# Evaluation Lane Verification Report

**Lane:** evaluation  
**Direction version:** 11  
**GitHub run:** 33356173706  
**Run ID:** verification_33356173706  
**Timestamp:** 2026-08-31  
**Cycle type:** Verification (no new science; state integrity check)

## Purpose

This cycle verifies the evaluation lane state is clean after the v15b combination-vs-hybrid findings were promoted to ACCEPTED. The factory dispatched this run despite `continue_recommended=false` to confirm no regressions and that all state files are consistent.

## Test Suite Results

**64/64 tests PASS** (0.93s execution time). All 10 test files collected and executed successfully.

| Test File | Tests | Status |
|---|---|---|
| test_anti_noise_procedural_sensitivity.py | 3 | PASS |
| test_boilerplate_resistance_real.py | 1 | PASS |
| test_cross_lingual_alignment_v10.py | 1 | PASS |
| test_frozen_harness_v3_reproducibility.py | 1 | PASS |
| test_product_integration_v11.py | 5 | PASS |
| test_v11_cross_validation.py | 8 | PASS |
| test_v12_cross_mode_cv.py | 10 | PASS |
| test_v12_temporal_holdout.py | 10 | PASS |
| test_v14_independent_rerun.py | 12 | PASS |
| test_v15_combination_vs_hybrid.py | 13 | PASS |

Three pytest warnings (return-type in test functions) — non-blocking, documented in prior cycles.

## V15b Findings Verification

Cross-checked state/evaluation.json against v15b results file:

| Metric | State File | Results File | Match |
|---|---|---|---|
| accepted_run_id | eval_v15b_cv_1788148695 | eval_v15b_cv_1788148695 | YES |
| config_hash | 4323f833fa72366a | 4323f833fa72366a | YES |
| linear_hybrid05_concat JP | 0.838 | 0.8383 | YES |
| linear_hybrid05_concat std | 0.027 | 0.0272 | YES |
| cited_outcome_hybrid_0.5 JP | 0.785 | 0.7850 | YES |
| Delta vs hybrid | +0.053 | +0.0533 | YES |
| Verdict | COMBINATION_BEATS_HYBRID | COMBINATION_BEATS_HYBRID | YES |

All v15b findings consistent. No discrepancies.

## State File Maintenance

**Problem found:** `evaluation/state/evaluation.json` was stale — pointing to run 33354034841 (v12 temporal holdout) instead of the authoritative run 33355160290 (v15b CV). Missing the v15 combination-vs-hybrid finding entirely.

**Action taken:** Synced `evaluation/state/evaluation.json` with authoritative `state/evaluation.json`. Both files now reference the same accepted run and findings.

## Stale Blockers Check

- **Blockers directory:** Does not exist in this checkout
- **Director note reference:** `state/blockers/legal-distance.json` AUDIT_BLOCKED from direction_version 10 — superseded by v11 clearance
- **Status:** CLEAN — no stale blocker files found in filesystem

## Current Lane State

| Field | Value |
|---|---|
| evidence_tier | ACCEPTED |
| cycle_status | COMPLETED |
| continue_recommended | false |
| accepted_run_id | eval_v15b_cv_1788148695 |
| github_run | 33356173706 (this cycle) |

### v9 Objectives: 4/6 Complete

| # | Objective | Status |
|---|---|---|
| 1 | Full corpus scale evaluation (192k) | BLOCKED — pending corpus lane |
| 2 | Citation role modeling | COMPLETED (2,988 annotations, 8/9 PASS) |
| 3 | Legal embeddings fine-tuning | COMPLETED (multilingual_e5 tested, hierarchy collapse) |
| 4 | Jurist human study | BLOCKED — needs 5-10 Swiss jurists |
| 5 | Cross-lingual alignment | COMPLETED (52 representations, proc_pairs LOSSLESS) |
| 6 | User corpus import | COMPLETED (45/45 tests PASS) |

### Blocked Dependencies

1. **Full corpus scale (192k):** Requires corpus lane OpenCaseLaw bulk ingestion from current 1,577 decisions. Critical path for section-specific evaluation and scale testing.
2. **Jurist human study:** Framework ready; needs recruitment of 5-10 Swiss jurists for pairwise preference evaluation.

## Key Accepted Findings (Summary)

- **Zero-shot hybrids remain dominant** for user-imported corpora: cited_decisions_tfidf_outcome_hybrid_0.5 (JP=0.7965, LangDom=0.4941)
- **Combinations beat hybrids in cross-validation:** linear_hybrid05_concat (JP=0.838, std=0.027) is BEST STABLE combination
- **linear_citation_concat** also valid (JP=0.838, std=0.030) — same JP, slightly higher variance
- **All representations pass adversarial gates** on canonical frozen harness v3
- **No regressions** in any test since v15b acceptance

## Recommendation

**CONTINUE_WITHIN_MISSION_FALSE** — All unblocked evaluation objectives are complete. The lane is blocked on two dependencies:
1. Corpus lane 192k delivery (for full-scale adversarial evaluation)
2. Jurist recruitment (for human study)

No additional same-question evaluation cycles are justified. The Factory Director should:
1. Monitor corpus lane progress toward 192k
2. Initiate jurist recruitment when ready
3. When dependencies resolve, dispatch a new cycle with the specific experiments:
   - Full corpus adversarial evaluation at 192k scale
   - Section-specific cross-lingual evaluation (sachverhalt/erwaegungen/dispositiv)
   - Jurist human study execution
   - multilingual-e5-small fine-tuned evaluation with hierarchy loss (GPU)

**Evidence tier:** ACCEPTED  
**Provenance:** 64/64 tests PASS, v15b findings verified, state files synced, no regressions.
