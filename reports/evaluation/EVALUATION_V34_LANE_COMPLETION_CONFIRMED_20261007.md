# Evaluation Lane — Factory Direction v34 Completion Confirmed

**Run ID:** EVALUATION_V34_COMPLETION_CONFIRMED_20261007  
**Date:** 2026-10-07  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  
**GitHub Run:** 37565001275

---

## Summary

The evaluation lane has **completed all work** for factory direction v34. The current question was:

> "Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."

**Both objectives are fully satisfied and frozen.**

---

## Deliverables Verified

### 1. TF-IDF 174k Production Baseline — FROZEN ✅
**Artifact:** `results/evaluation/tfidf_174k_formal_suite_baseline.json`

| Metric | Value | Status |
|--------|-------|--------|
| Production mode | `cited_decisions_tfidf_outcome_hybrid_0.5` | FROZEN |
| Jurist preference | 0.7345 | PASS (>0.5 threshold) |
| Language dominance | 0.477 | PASS (<0.85 threshold) |
| Beats semantic baseline (0.43) | +0.3045 (71% improvement) | MISSION SATISFIED |
| Adversarial gates (8/8 modes) | All PASS | FROZEN |

### 2. Dense Embedding Complementary View Criteria — FROZEN ✅
**Artifact:** `results/evaluation/dense_complementary_acceptance_criteria.json`

| Criterion | Threshold | Current Evidence | Status |
|-----------|-----------|------------------|--------|
| Citation heritage AUC | > 0.75 | Dense: 0.79-0.85 (21-24yr scale) | DEFINED, AWAITING 174K |
| Cross-lingual Sachverhalt | > 0.20 | 0.282 at 1K sample | DEFINED, AWAITING 174K |
| Cross-lingual Dispositiv | > 0.10 | 0.150 at 1K sample | DEFINED, AWAITING 174K |
| Cross-lingual Erwaegungen | > 0.05 | 0.094 at 1K sample | DEFINED, AWAITING 174K |
| Linear hybrid complement JP | > 0.60 | 0.61-0.67 (19-22yr) | DEFINED, AWAITING 174K |

### 3. Accepted Negative Findings — PRESERVED ✅
| Finding | Value | Implication |
|---------|-------|-------------|
| True OOS JuristPref ceiling | ~0.53 | Dense cannot be primary (target 0.7) |
| v18 coarse hierarchy | max purity 0.65 < 0.7 | Coarse taxonomy unrecoverable |
| Citation heritage recall@10 | max 0.0066 | Ranking signal, not retrieval |
| TF-IDF cross-lang retrieval | recall@10 0.141 < 0.2 | Accepted limitation |
| TF-IDF boilerplate resistance | -0.834 | Accepted limitation |

### 4. Data Blockers — EXPLICIT ✅
| Blocker | Impact | Resolution |
|---------|--------|------------|
| BGE/bger ID mapping | Cannot align 174k dense embeddings | Corpus lane resumption |
| Parquet 2022-2026 | 29,520 decisions missing | Corpus lane resumption |
| Section extraction 174k | Cross-lingual needs sections at scale | Corpus lane resumption |

---

## Evidence Provenance (All ACCEPTED)

- `/tmp/lex_accepted/legal-distance/state/legal-distance.json` — Dense characterization complete, citation heritage AUC 0.79-0.85, true OOS JP ceiling ~0.53
- `/tmp/lex_accepted/legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — 8/8 TF-IDF modes PASS adversarial
- `/tmp/lex_accepted/fractal-map/state/fractal-map.json` — TF-IDF hierarchical operational at 174k, integration contract frozen
- All local result artifacts verified present and valid JSON

---

## Lane State Consistency

**Machine-readable state:** `state/evaluation.json` ✅
- `evidence_tier`: "ACCEPTED"
- `cycle_status`: "COMPLETE"
- `continue_recommended`: false
- `accepted_run_id`: "EVALUATION_V34_PRODUCTION_BASELINE_FROZEN_20261007"
- 9 evidence refs all accessible

**Control plane discrepancy noted:** `/tmp/lex_control/state/factory_direction.json` shows `evaluation.status = "RUN"` — this is a **known V28-pattern infrastructure defect** in control plane mounting. The authoritative workspace state and lane state correctly show COMPLETE. This does not affect scientific validity.

---

## Final Audit Readiness

| Criterion | Status |
|-----------|--------|
| Hypothesis frozen before measurement | ✅ |
| Corpus/sample frozen (173,963 decisions) | ✅ |
| Baseline frozen (8 TF-IDF modes) | ✅ |
| Metrics frozen (JP > 0.5, LangDom < 0.85) | ✅ |
| Success rule frozen (both gates PASS) | ✅ |
| Negative results preserved | ✅ (10 documented) |
| Strong baseline comparison | ✅ (semantic JP=0.43 vs TF-IDF JP=0.7345) |
| Jurist usefulness proxy | ✅ (adversarial pairwise) |
| Machine-readable state | ✅ |
| Human-readable report | ✅ |
| Provenance traceable | ✅ |
| Data blockers explicit | ✅ |
| Continue recommendation justified | ✅ (false — no same-question cycles remain) |

---

## Recommendation

**CONTINUE_RECOMMENDED = false** (already set in lane state)

No further same-question cycles are justified. The evaluation lane has:
1. Frozen TF-IDF 174k evaluation as production baseline
2. Defined and frozen dense embedding complementary view acceptance criteria
3. Documented all accepted negative findings
4. Identified precise data blockers requiring corpus lane resumption

**Factory Director Action Required:** Resume corpus lane for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale. Once dense embeddings are delivered at 174k, a **new evaluation cycle** (not same-question) will validate them against the frozen criteria.

---

## Immutable Artifacts (This Cycle)

- `state/evaluation.json` — Machine-readable lane state
- `results/evaluation/tfidf_174k_formal_suite_baseline.json` — Frozen production baseline
- `results/evaluation/dense_complementary_acceptance_criteria.json` — Frozen complementary criteria
- `results/evaluation/citation_heritage_174k.json` — Current citation heritage result
- `results/evaluation/v17b_label_normalization_174k_latest.json` — v17b generalization failure
- `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` — v18 NEGATIVE
- `results/evaluation/bootstrap_ci_dense_metrics_20261006.json` — Bootstrap CIs
- `reports/evaluation/EVALUATION_V34_PRODUCTION_BASELINE_FROZEN_20261007.md` — Final human-readable report
- `reports/evaluation/EVALUATION_V34_FINAL_AUDIT_READY_VERIFICATION_20261007.md` — Audit verification
- `reports/evaluation/EVALUATION_V34_LANE_COMPLETION_CONFIRMED_20261007.md` — This confirmation

**All negative results preserved. No claim-bearing outputs overwritten. Snapshot audit-ready.**