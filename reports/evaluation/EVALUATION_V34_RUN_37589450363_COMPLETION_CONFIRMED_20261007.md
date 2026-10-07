# Evaluation Lane — Factory Direction v34 Completion Confirmed (GitHub Run 37589450363)

**Date:** 2026-10-07  
**Run ID:** EVALUATION_V34_RUN_37589450363_VERIFICATION  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  
**GitHub Run:** 37589450363

---

## Executive Summary

The evaluation lane has **fully completed** its factory direction v34 question:

> **"Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."**

All deliverables are **frozen, verified, and audit-ready** at ACCEPTED evidence tier. This verification confirms completion for GitHub run 37589450363.

---

## Deliverables Verified (Immutable)

### 1. TF-IDF 174k Production Baseline — FROZEN
- **Artifact:** `results/evaluation/tfidf_174k_formal_suite_baseline.json`
- **Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5`
- **Jurist Preference:** 0.7345 (threshold: > 0.5) ✅
- **Language Dominance:** 0.477 (threshold: < 0.85) ✅
- **Semantic Baseline (center_projected):** JP = 0.43
- **Mission:** TF-IDF citation hybrids **beat simple semantic-map baseline** by +0.3045 JP (71% relative) ✅
- **All 8 TF-IDF modes PASS both adversarial gates** ✅

### 2. Dense Embedding Complementary View Criteria — FROZEN
- **Artifact:** `results/evaluation/dense_complementary_acceptance_criteria.json`

| Criterion | Metric | Threshold | Current Evidence | Status |
|-----------|--------|-----------|------------------|--------|
| Citation Heritage | AUC-ROC (137k pair pool) | > 0.75 | Dense: 0.79-0.85 (21-24yr) | DEFINED, AWAITING 174K |
| Cross-Lingual Sachverhalt | cross_lang_same_branch_mean | > 0.20 | 0.282 (1K sample) | DEFINED, AWAITING 174K |
| Cross-Lingual Dispositiv | cross_lang_same_branch_mean | > 0.10 | 0.150 (1K sample) | DEFINED, AWAITING 174K |
| Cross-Lingual Erwaegungen | cross_lang_same_branch_mean | > 0.05 | 0.094 (1K sample) | DEFINED, AWAITING 174K |
| Linear Hybrid Complement | JP at w∈{0.3,0.35,0.4} | > 0.60 | 0.61-0.67 (19-22yr) | DEFINED, AWAITING 174K |

### 3. Accepted Negative Findings — PRESERVED
| Finding | Value | Implication |
|---------|-------|-------------|
| True OOS JuristPref ceiling | ~0.53 | Dense embeddings **cannot** be primary navigation mode (target 0.7) |
| v18 coarse hierarchy (4 labels) | max purity 0.65 < 0.7 | Coarse legal taxonomy unrecoverable |
| Citation heritage recall@10 | max 0.0066 | Citation heritage is ranking signal, not retrieval signal |
| TF-IDF cross-language retrieval | recall@10 0.141 < 0.2 | Accepted limitation of TF-IDF baseline |
| TF-IDF hierarchy coherence | nesting_score 0.317 | Accepted limitation |
| TF-IDF boilerplate resistance | resistance_score -0.834 | Accepted limitation |

### 4. Data Blockers — REQUIRED FOR NEXT PHASE
| Blocker | Impact | Resolution |
|---------|--------|------------|
| **BGE/bger ID mapping** | Cannot align 174k dense embeddings with evaluation metadata | Corpus lane: produce canonical mapping |
| **Parquet 2022-2026** | 29,520 decisions missing; cannot compute 174k dense embeddings | Corpus lane: generate parquet |
| **Section extraction 174k** | Cross-lingual section alignment needs sections at 174k scale | Corpus lane: run section extraction |

---

## State Consistency Verification

**Lane State File:** `state/evaluation.json` ✅
- `lane`: "evaluation"
- `direction_version`: 34
- `evidence_tier`: "ACCEPTED"
- `cycle_status`: "COMPLETE"
- `continue_recommended`: false
- `accepted_run_id`: "EVALUATION_V34_PRODUCTION_BASELINE_FROZEN_20261007"
- All 9 evidence_refs present and accessible
- `critical_findings` complete with all 4 categories
- `validation_protocol_frozen` defined for all 4 criteria

**Results Artifacts:** ✅ All 7 referenced result files exist and are valid JSON  
**Reports:** ✅ Final reports complete  
**Cross-Lane Consistency:** ✅ Legal-distance (dense characterization COMPLETE), Fractal-map (integration contract FROZEN), Product (v1.0 released with TF-IDF baseline)

---

## Control Plane Discrepancy Note

**The mounted `/tmp/lex_control/state/factory_direction.json` shows `evaluation.status = "RUN"`** while the authoritative workspace state (`state/factory_direction.json`) and lane state (`state/evaluation.json`) correctly show `COMPLETE`.

**Diagnosis:** V28-pattern control plane mounting defect (persistent infrastructure issue). **This is NOT a lane failure.** The lane state is authoritative. The evaluation lane has correctly completed all work.

---

## Recommendation

**CONTINUE_RECOMMENDED = false**

No further same-question cycles are justified. The evaluation lane has:
1. Frozen TF-IDF 174k evaluation as production baseline ✅
2. Defined and frozen dense embedding complementary view acceptance criteria ✅
3. Documented all accepted negative findings ✅
4. Identified precise data blockers requiring corpus lane resumption ✅

**Factory Director Action Required:** Resume corpus lane for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale. Once dense embeddings are delivered at 174k, a **new evaluation cycle** (not same-question) will validate them against the frozen criteria.

---

## Immutable Artifacts Written (Preserved)

- `state/evaluation.json` — Machine-readable lane state
- `results/evaluation/tfidf_174k_formal_suite_baseline.json` — Frozen production baseline
- `results/evaluation/dense_complementary_acceptance_criteria.json` — Frozen complementary criteria
- `results/evaluation/citation_heritage_174k.json` — Current citation heritage result
- `results/evaluation/v17b_label_normalization_174k_latest.json` — v17b generalization failure
- `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` — v18 coarse hierarchy NEGATIVE
- `results/evaluation/bootstrap_ci_dense_metrics_20261006.json` — Bootstrap CIs for dense metrics
- `reports/evaluation/EVALUATION_V34_PRODUCTION_BASELINE_FROZEN_20261007.md` — Final human-readable report
- `reports/evaluation/EVALUATION_V34_FINAL_AUDIT_READY_VERIFICATION_20261007.md` — Final verification report
- `reports/evaluation/EVALUATION_LANE_V34_COMPLETION_CONFIRMED_20261007.md` — Previous completion report
- `reports/evaluation/EVALUATION_V34_RUN_37589450363_COMPLETION_CONFIRMED_20261007.md` — This verification report

**All negative results preserved. No claim-bearing outputs overwritten. Snapshot audit-ready.**