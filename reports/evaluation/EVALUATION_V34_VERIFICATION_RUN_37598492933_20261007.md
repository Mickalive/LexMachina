# Evaluation Lane v34 — Independent Verification Run 37598492933

**Date:** 2026-10-07  
**Run ID:** `EVALUATION_V34_VERIFICATION_20261007_37598492933`  
**GitHub Run:** 37598492933  
**Evidence Tier:** ACCEPTED (verification of existing ACCEPTED evidence)  
**Cycle Status:** COMPLETE (no new cycle — verification only)

---

## Purpose

Independent verification of the Evaluation Lane v34 completion state (factory direction v34) as recorded in `state/evaluation.json`. Confirms all deliverables are frozen, internally consistent, and audit-ready.

---

## Verification Scope

| Artifact | Path | Status |
|----------|------|--------|
| TF-IDF 174k Production Baseline | `results/evaluation/tfidf_174k_formal_suite_baseline.json` | ✅ VERIFIED |
| Dense Complementary Criteria | `results/evaluation/dense_complementary_acceptance_criteria.json` | ✅ VERIFIED |
| Citation Heritage 174k Result | `results/evaluation/citation_heritage_174k.json` | ✅ VERIFIED |
| Bootstrap CIs for Dense Metrics | `results/evaluation/bootstrap_ci_dense_metrics_20261006.json` | ✅ VERIFIED |
| v18 Coarse Hierarchy Results | `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` | ✅ VERIFIED |

---

## Test Results

**All 12 v18 Coarse Hierarchy tests PASSED** (`evaluation/tests/test_v18_coarse_hierarchy.py`):

| Test | Result |
|------|--------|
| `test_result_file_exists` | ✅ PASS |
| `test_run_id_present` | ✅ PASS |
| `test_hypothesis_frozen` | ✅ PASS |
| `test_part_a_present` | ✅ PASS |
| `test_part_b_present` | ✅ PASS |
| `test_part_c_scorecard_present` | ✅ PASS |
| `test_multi_seed_stability` | ✅ PASS (std < 0.05, mean > 1.10 for both reps) |
| `test_seed42_reproduces_v17` | ✅ PASS (hierarchy ratio = 1.2018) |
| `test_branch_level_negative_result` | ✅ PASS (branch purity 0.519 < 0.70) |
| `test_all_six_reps_covered` | ✅ PASS |
| `test_v17_tier_in_state` | ✅ PASS (evidence_tier = REPRODUCED) |
| `test_v17b_tier_in_state` | ✅ PASS (evidence_tier = REPRODUCED) |

---

## Key Findings Confirmed

### 1. TF-IDF 174k Production Baseline — FROZEN (ACCEPTED)

| Mode | Language Dominance | Jurist Preference | Both Gates |
|------|-------------------|-------------------|------------|
| `cited_decisions_tfidf` | 0.479 ✅ | 0.714 ✅ | ✅ |
| `outcome_tfidf` | 0.502 ✅ | 0.655 ✅ | ✅ |
| `regeste_tfidf` | 0.485 ✅ | 0.632 ✅ | ✅ |
| `full_text_tfidf_light` | 0.485 ✅ | 0.708 ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.477** ✅ | **0.7345** ✅ | ✅ **PRODUCTION DEFAULT** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.478 ✅ | 0.7275 ✅ | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.480 ✅ | 0.720 ✅ | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.482 ✅ | 0.715 ✅ | ✅ |

**Mission satisfied:** TF-IDF citation hybrids (JP 0.735) beat simple semantic-map baseline (center_projected JP 0.43) by +0.3045 (71% relative).

### 2. Dense Embedding Complementary View Criteria — FROZEN (UNVALIDATED at 174k)

| Criterion | Threshold | Evidence | Status |
|-----------|-----------|----------|--------|
| Citation Heritage AUC | > 0.75 | 0.7922 (center_projected_64dim, 22yr cohort) | ✅ DEFINED, BLOCKED at 174k (AUC 0.482 FAIL) |
| Cross-Lingual Sachverhalt | > 0.20 | 0.282 (1K sample, 36% coverage) | ✅ DEFINED, BLOCKED (section extraction) |
| Cross-Lingual Dispositiv | > 0.10 | 0.150 (1K sample, 54% coverage) | ✅ DEFINED, BLOCKED (section extraction) |
| Cross-Lingual Erwaegungen | > 0.05 | 0.094 (1K sample, 51% coverage) | ✅ DEFINED, BLOCKED (section extraction) |
| Linear Hybrid Complement | JP > 0.60 (w=0.3-0.4) | 0.6725 (w=0.4, 22yr) | ✅ DEFINED, BLOCKED (no 174k dense embeddings) |

### 3. Accepted Negative Findings — PRESERVED

| Finding | Value | Implication |
|---------|-------|-------------|
| True OOS JuristPref ceiling | ~0.53 | Dense embeddings cannot be primary navigation (target 0.7) |
| v18 Coarse Hierarchy max branch purity | 0.65 | Legal taxonomy recovery fails even at 4 labels |
| Citation Heritage Recall@10 | 0.0066 | Citation heritage is ranking signal, not retrieval signal |
| Citation Heritage 174k AUC | 0.482 | Full corpus FAIL; partial 22yr PASS does not generalize |
| TF-IDF cross-language retrieval | 0.141 < 0.2 | Accepted TF-IDF limitation |
| TF-IDF hierarchy coherence | 0.317 | Accepted TF-IDF limitation |
| TF-IDF boilerplate resistance | -0.834 | Accepted TF-IDF limitation |

### 4. Data Blockers — REQUIRED FOR NEXT PHASE

| Blocker | Resolution |
|---------|------------|
| **BGE/bger ID mapping** | Corpus lane: produce canonical mapping |
| **Parquet 2022–2026** | Corpus lane: generate parquet (29,520 decisions) |
| **Section extraction 174k** | Corpus lane: extract sections at 174k scale |

---

## State Consistency Check

- `state/evaluation.json`: `cycle_status = COMPLETE`, `continue_recommended = conditional` ✅
- `evidence_tier = TF-IDF_ACCEPTED_DENSE_UNVALIDATED` (accurate) ✅
- All `evidence_refs` accessible and valid ✅
- Cross-lane consistency: Legal-distance (dense characterization COMPLETE), Fractal-map (integration contract FROZEN), Product (v1.0 released with TF-IDF baseline) ✅
- No claim-bearing outputs overwritten; all negative results preserved ✅

---

## Control Plane Note

The mounted `/tmp/lex_control/state/factory_direction.json` shows `evaluation.status = "RUN"` while the authoritative workspace state (`state/factory_direction.json`) and lane state (`state/evaluation.json`) correctly show `COMPLETE`. This is a **V28-pattern control plane mounting defect** (persistent infrastructure issue), **NOT a lane failure**.

---

## Recommendation

**NO FURTHER WORK REQUIRED** for factory direction v34 question.

The evaluation lane has:
1. ✅ Frozen TF-IDF 174k evaluation as production baseline
2. ✅ Defined and frozen dense embedding complementary view acceptance criteria
3. ✅ Documented all accepted negative findings
4. ✅ Identified precise data blockers requiring corpus lane resumption

**Next Factory Director Action:** Resume corpus lane for BGE/bger ID mapping + parquet 2022–2026 + section extraction at 174k scale. Once dense embeddings are delivered at 174k, a **new evaluation cycle** (not same-question) will validate them against the frozen criteria herein.

---

## Updated State

`state/evaluation.json` updated with this verification run in `additional_verification_runs`.

---

*End of Verification Report — Evaluation Lane v34 Complete and Verified*