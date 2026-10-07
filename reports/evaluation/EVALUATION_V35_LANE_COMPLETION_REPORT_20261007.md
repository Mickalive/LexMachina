# Evaluation Lane Completion Report — Factory Direction v35

**Run ID:** EVALUATION_V35_LANE_COMPLETION_20261007
**Lane:** evaluation
**Direction Version:** 35
**Status:** COMPLETE
**Continue Recommended:** false
**Date:** 2026-10-07

---

## Mission Summary

The evaluation lane has **successfully completed** its factory direction v35 question:

> **"Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."**

---

## TF-IDF 174k Production Baseline — FROZEN ✅

### Formal Suite Results (8/8 representations, all PASS both adversarial gates)

| Representation | Language Dominance (threshold < 0.85) | Jurist Preference (threshold > 0.5) | Both PASS |
|---|---|---|---|
| cited_decisions_tfidf | 0.4794 ✅ | 0.7140 ✅ | ✅ |
| outcome_tfidf | 0.5015 ✅ | 0.6550 ✅ | ✅ |
| regeste_tfidf | 0.4853 ✅ | 0.6315 ✅ | ✅ |
| full_text_tfidf_light | 0.4854 ✅ | 0.7080 ✅ | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **0.4773 ✅** | **0.7345 ✅** | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4783 ✅ | 0.7275 ✅ | ✅ |
| regeste_full_text_hybrid_0.5 | 0.4873 ✅ | 0.7140 ✅ | ✅ |
| regeste_full_text_hybrid_0.7 | 0.4889 ✅ | 0.7120 ✅ | ✅ |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (JP=0.7345, LangDom=0.4773)

**Verification:**
- Exact k-NN on fixed stratified subsample (n=2000, branch_only_stratified_500_per_branch, seed=42)
- Config hash: `b51701f5a9c11692` (frozen harness v3)
- 15x independent verification in CI
- Working directory embeddings reproduce frozen baseline exactly (JP=0.7345)

**Beats Semantic Baseline:** TF-IDF citation hybrids beat simple semantic-map baseline (center_projected JP 0.05-0.43) on jurist preference — **mission satisfied**.

---

## Dense Embedding Complementary View Acceptance Criteria — DEFINED & FROZEN ✅

### Citation Heritage View
- **Metric:** AUC for recovering cited precedent pairs (frozen 137k pair pool)
- **Threshold:** > 0.75
- **22-year/144k Evidence (Bootstrap 95% CI):** 
  - center_projected_768dim: 0.7941 [0.7638, 0.8241] ✅
  - center_projected_64dim: 0.7922 [0.7619, 0.8223] ✅
  - center_projected_128dim: 0.7916 [0.7613, 0.8218] ✅
- **174k Status:** **VALIDATION BLOCKED** — Full 174k corpus AUC=0.482 FAIL (cited_outcome_hybrid_0.5_174k); partial cohort PASS does not generalize
- **Target:** citation_based dense embeddings must exceed 0.75 AUC at FULL 174k scale

### Cross-Lingual View
| Section | Metric | Threshold | 3-year Evidence (Bootstrap 95% CI) | Status |
|---|---|---|---|---|
| Sachverhalt (facts) | cross_lang_same_branch_mean | > 0.2 | center_projected_64/768: 0.2816 [0.2669, 0.2964] | ✅ PASS |
| Dispositiv (holdings) | cross_lang_same_branch_mean | > 0.1 | center_projected_64: 0.1502 [0.1409, 0.1599] | ✅ PASS |
| Erwaegungen (reasoning) | cross_lang_same_branch_mean | > 0.05 | center_projected_64: 0.0941 [0.0863, 0.1022] | ✅ PASS (at 0.05) |

**Section Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen

### Linear Hybrid Complement
- **Metric:** Jurist pairwise preference (hybrid weights 0.3-0.4)
- **Threshold:** > 0.60 (below TF-IDF baseline 0.735, above dense-only 0.43)
- **174k Status:** **VALIDATION BLOCKED** — No 174k legal-distance dense embeddings exist

---

## Accepted Negative Findings (Preserved as First-Class Results) ❄️

| Finding | Value | Implication |
|---|---|---|
| True OOS Jurist Preference Ceiling | ~0.53 | Dense embeddings cannot be primary navigation mode |
| v18 Coarse Hierarchy (4 branches) | max purity 0.65 < 0.7 | Coarse legal taxonomy recovery fails |
| Citation Heritage Recall@10 | max 0.0066 | Citation heritage is ranking signal, not retrieval |
| Boilerplate Resistance (dense) | FAIL | Dense embeddings more susceptible to procedural boilerplate |
| Citation Heritage 174k AUC | 0.482 (FAIL) | Partial 22yr PASS does not generalize to full 174k |
| 24-year Adversarial | center_projected FAILS jurist gate at ALL dims (JP 0.35-0.38) | True OOS ceiling ~0.38 < 0.5 |

---

## Data Blockers (Upstream Dependencies) 🔒

| Blocker | Status | Impact | Resolution |
|---|---|---|---|
| BGE/BGER ID Mapping | BLOCKING | Cannot align 174k dense embeddings with evaluation metadata (bger_ IDs) | Corpus lane resumption required |
| Parquet 2022-2026 | BLOCKING | 29,520 decisions missing, cannot compute 174k dense embeddings | Corpus lane resumption required |
| Section Extraction 174k | REQUIRED | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at 174k scale | Corpus lane resumption required |

**Legal-Distance Checkpoints Available:** 24 yearly checkpoints (2000-2023, 158k+ decisions) — concatenation blocked on above.

---

## Evidence References (Machine-Readable)

- `results/evaluation/tfidf_174k_adversarial_gates_formal_suite_latest.json` — Frozen formal suite
- `results/evaluation/tfidf_174k_formal_suite_baseline.json` — Production baseline summary
- `results/evaluation/dense_complementary_acceptance_criteria.json` — Frozen acceptance criteria
- `results/evaluation/citation_heritage_174k.json` — 174k citation heritage result (AUC 0.482 FAIL)
- `results/evaluation/bootstrap_ci_dense_metrics_20261006.json` — 22-year bootstrap CIs
- `results/evaluation/v17b_label_normalization_174k_latest.json` — Label normalization non-generalization
- `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json` — Coarse hierarchy FAIL
- `/tmp/lex_accepted/legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Legal-distance accepted formal suite
- `/tmp/lex_accepted/fractal-map/state/fractal-map.json` — Fractal-map accepted state

---

## Test Verification ✅

- `evaluation/tests/test_v18_coarse_hierarchy.py`: **12/12 tests PASSED** (v18 negative result integrity preserved)

---

## Next Recommendation

**No further same-question cycles justified.** The evaluation lane has:

1. ✅ **Frozen TF-IDF 174k evaluation as production baseline** (8/8 PASS both adversarial gates)
2. ✅ **Defined and frozen dense embedding complementary acceptance criteria** (citation heritage AUC > 0.75, cross-lang sachverhalt > 0.2, cross-lang dispositiv > 0.1, erwaegungen > 0.05, linear hybrid > 0.60)
3. 🔒 **Validation BLOCKED** at 174k scale pending corpus lane deliveries

**Next evaluation cycle triggers ONLY when legal-distance delivers 174k dense embeddings for validation against frozen criteria.**

---

## Lane State (evaluation/state/evaluation.json)

```json
{
  "lane": "evaluation",
  "direction_version": 35,
  "evidence_tier": "TF-IDF_ACCEPTED_DENSE_UNVALIDATED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": "EVALUATION_V34_PRODUCTION_BASELINE_FROZEN_20261007",
  "next_recommendation": "TF-IDF 174k evaluation FROZEN as production baseline (COMPLETE, no further cycles). Dense embedding complementary view acceptance criteria DEFINED and FROZEN but UNVALIDATED at 174k scale — validation BLOCKED pending corpus lane deliveries (bge_/bger_ ID mapping, parquet 2022-2026, section extraction at 174k). Next evaluation cycle triggers ONLY when legal-distance delivers 174k dense embeddings for validation against frozen criteria."
}
```

---

**Report Generated:** 2026-10-07T20:55:00Z  
**Evidence Tier:** TF-IDF_ACCEPTED_DENSE_UNVALIDATED  
**Cycle Status:** COMPLETE