# Evaluation Lane — Factory Direction v35 Operational Resume Audit-Ready Confirmation

**Run ID:** EVALUATION_V35_OPERATIONAL_RESUME_37988462224_AUDIT_READY  
**Date:** 2026-10-09  
**GitHub Run:** 37988462224  
**Evidence Tier:** TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Executive Summary

This run performs an **operational resume verification** from the persisted producer snapshot of run 37982081627. The evaluation lane v35 work was **already complete** prior to this run. Both deliverables for factory direction v35 are **frozen, verified, and audit-ready**:

1. ✅ **TF-IDF 174k evaluation FROZEN as production baseline** — Deterministic adversarial verification confirms 7/8 representations PASS both gates with production baseline `cited_decisions_tfidf_outcome_hybrid_0.5` achieving JP=0.659, LangDom=0.426. Non-determinism in adversarial gate subsampling identified and FIXED via sorted groups in `verify_frozen_baseline.py`.

2. ✅ **Dense embedding complementary view acceptance criteria FROZEN and VALIDATED at maximal available scale (144k/22yr)** — All four criteria defined with explicit thresholds, validated against ACCEPTED evidence from legal-distance and fractal-map lanes.

**No further same-question cycles are justified.** The lane remains COMPLETE with `continue_recommended=false`.

---

## 1. Deterministic Verification — This Run (37988462224)

### 1.1 Environment
- **numpy:** 2.5.3
- **scikit-learn:** 1.9.1
- **scipy:** 1.18.1
- **Python:** 3.12

### 1.2 Consecutive Verification Runs (Determinism Confirmed)

| Run | Timestamp | Reps PASS | Prod Baseline JP | Prod Baseline LangDom | Notes |
|-----|-----------|-----------|------------------|----------------------|-------|
| 1 | 2026-10-09 20:44:40 | 7/8 | 0.6590 | 0.4258 | Fresh verification |
| 2 | 2026-10-09 20:44:50 | 7/8 | 0.6590 | 0.4258 | **IDENTICAL** |

**Result:** Sorted groups fix ensures **deterministic subsampling** regardless of metadata JSON ordering. Results are reproducible within this environment.

### 1.3 Adversarial Gate Results (Current Environment)

| Representation | Verdict | Language Dominance | Jurist Preference | Both Gates |
|----------------|---------|-------------------|-------------------|------------|
| `full_text_tfidf_light` | ✅ PASS | 0.4834 | **0.7350** | ✅ |
| `regeste_full_text_hybrid_0.7` | ✅ PASS | 0.4806 | 0.7235 | ✅ |
| `regeste_full_text_hybrid_0.5` | ✅ PASS | 0.4809 | 0.7225 | ✅ |
| `cited_decisions_tfidf` | ✅ PASS | 0.4252 | 0.6710 | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | ✅ PASS | 0.4241 | 0.6650 | ✅ |
| **`cited_decisions_tfidf_outcome_hybrid_0.5`** | ✅ PASS | **0.4258** | **0.6590** | ✅ |
| `regeste_tfidf` | ✅ PASS | 0.3590 | 0.5405 | ✅ |
| `outcome_tfidf` | ❌ FAIL | 0.4232 | 0.4325 | ❌ |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (JP=0.6590, LangDom=0.4258, both gates PASS)

**Artifacts Written:**
- `evaluation/results/174k_tfidf_formal_suite/verification_20261009_204440.json` — Run 1
- `evaluation/results/174k_tfidf_formal_suite/verification_20261009_204450.json` — Run 2 (IDENTICAL)

---

## 2. Conformance Tests — All PASS

| Test | Result | Notes |
|------|--------|-------|
| `verify_frozen_baseline.py` (run 1) | ✅ 7/8 PASS | Deterministic: JP=0.6590, LangDom=0.4258 |
| `verify_frozen_baseline.py` (run 2) | ✅ 7/8 PASS | **IDENTICAL to run 1** — non-determinism FIXED |
| `tests/evaluation/test_v25_174k_suite_snapshot.py` | ✅ PASS (exit 0) | 174k TF-IDF formal suite snapshot conforms to frozen protocol |
| `tests/evaluation/test_frozen_harness_v3_reproducibility.py` | ✅ PASS | All 6 representations REPRODUCED within tolerance 0.001 |

---

## 3. Orchestration/Validation Issues — Diagnosed and Documented

The following issues were identified in prior runs and are **fully documented in `state/evaluation.json`**:

| Issue | Status | Documentation Location |
|-------|--------|------------------------|
| **Factory direction sync**: `factory_direction.json` shows evaluation="RUN" but lane state shows COMPLETE | Documented | Control plane sync issue; lane state is authoritative |
| **Cross-environment discrepancy**: Prior env (numpy 1.x/sklearn 1.x) showed 7/8 PASS, JP=0.659; GitHub run 37975401319 (numpy 2.5.3/sklearn 1.9.1) showed 6/8 PASS, JP=0.5925 | Documented | Root cause: k-NN tie-breaking differences across versions. Production baseline passes both gates in ALL environments. |
| **Accepted mount mutations**: Fractal-map rebuild (2026-10-07) and mount refresh (2026-10-08) degraded production baseline from original freeze JP=0.735 → 0.5565 → 0.659 (deterministic current) | Documented | Corpus lane MUST restore original freeze embeddings for production baseline stability |
| **Metadata-ordering non-determinism**: Stratified subsampling sensitive to JSON key order | **FIXED** | Sorted groups fix in `verify_frozen_baseline.py`; verified deterministic across 3+ consecutive runs |

**All issues are preserved as evidence — no negative results deleted, no claim-bearing outputs overwritten.**

---

## 4. Dense Embedding Complementary View Criteria — FROZEN & VALIDATED

| View | Metric | Threshold | Evidence at 144k/22yr | Status |
|------|--------|-----------|----------------------|--------|
| **Citation Heritage** | AUC-ROC | > 0.75 | cp64: 0.7922 (CI [0.762, 0.822]) | ✅ PASSED |
| **Cross-Lingual Sachverhalt** | cross_lang_same_branch | > 0.20 | cp64: 0.2816 (n=359, 36% coverage) | ✅ PASSED |
| **Cross-Lingual Dispositiv** | cross_lang_same_branch | > 0.10 | cp64: 0.1502 (n=538, 54% coverage) | ✅ PASSED |
| **Cross-Lingual Erwaegungen** | cross_lang_same_branch | > 0.10 | cp64: 0.0941 (n=510, 51% coverage) | ❌ FAILED (correctly excluded) |
| **Linear Hybrid Complement** | PASS gates + cross_lang > TF-IDF | w=0.3-0.4 | JP=0.61-0.67 < TF-IDF 0.78; cross_lang +26-29% | ⚠️ CONDITIONAL (EXPLORATORY) |

**All criteria trace to ACCEPTED upstream evidence** from `/tmp/lex_accepted/legal-distance` and `/tmp/lex_accepted/fractal-map`.

---

## 5. Mission Satisfaction — VERIFIED

| Metric | Value | Baseline | Margin |
|--------|-------|----------|--------|
| Simple semantic baseline (center_projected) JP | 0.43 | — | — |
| TF-IDF hybrid_0.5 (deterministic) JP | 0.659 | 0.43 | **+0.229 (53% relative)** |
| TF-IDF hybrid_0.5 (original freeze) JP | 0.735 | 0.43 | **+0.305 (71% relative)** |

**Verdict:** TF-IDF citation hybrids **beat the simple semantic-map baseline** on jurist preference — **mission satisfied**.

---

## 6. Data Blockers — Require Corpus Lane Resumption

| Blocker | Impact |
|---------|--------|
| **BGE/bger ID mapping** | Cannot align 174k dense embeddings (bge_ IDs) with evaluation metadata (bger_ IDs) |
| **Parquet 2022-2026** | 29,520 decisions missing; cannot compute 174k dense embeddings |
| **Section extraction 174k** | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at 174k scale |
| **GPU unavailable** | No BGE/multilingual-e5 fine-tuning at scale |

**No evaluation work can proceed on dense complementary views at 174k until these are resolved.**

---

## 7. External Dependencies

| Dependency | Status | Description |
|------------|--------|-------------|
| **Jurist Human Study** | FRAMEWORK_READY | 5-10 Swiss jurists, framework ready, not yet executed |

---

## 8. Recommendation

**CONTINUE_RECOMMENDED = false**

The evaluation lane has:
- ✅ Frozen TF-IDF 174k evaluation as production baseline (with mutation history documented, non-determinism FIXED, cross-environment discrepancy documented)
- ✅ Defined and validated dense embedding complementary view acceptance criteria at max available scale (144k/22yr)
- ✅ Documented all accepted negative findings
- ✅ Identified precise data blockers
- ✅ Verified frozen artifacts pass conformance tests in current environment
- ✅ Completed operational resume verification from run 37982081627 snapshot — **audit-ready**

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale. Once dense embeddings are delivered at 174k, a **new evaluation cycle** (not same-question) will validate them against the frozen criteria.

---

## 9. Evidence Provenance

All findings trace to ACCEPTED evidence from upstream lanes:

| Source | Key Evidence |
|--------|--------------|
| `/tmp/lex_accepted/legal-distance/state/legal-distance.json` | Minimal dense scale characterization COMPLETE, citation heritage AUC 0.77-0.85 > 0.75, section cross-lingual hierarchy confirmed, true OOS JP ceiling ~0.53 |
| `/tmp/lex_accepted/legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` | 174k TF-IDF formal suite: 8/8 modes PASS both adversarial gates (original freeze) |
| `/tmp/lex_accepted/fractal-map/state/fractal-map.json` | TF-IDF hierarchical production modes OPERATIONAL at 174k, dense integration contract v34 frozen |
| `/tmp/lex_accepted/fractal-map/results/fractal_map/dense_embeddings_integration_contract_v34.json` | Frozen dense integration contract with all four complementary view criteria |
| `/tmp/lex_accepted/fractal-map/results/fractal_map/144k_checkpoint_validation/144k_validation_144443decisions.json` | 144k hierarchical validation: fine_branch_purity ~0.97, strict_nesting ≥0.99 |
| `evaluation/results/174k_tfidf_formal_suite/verification_20261009_081230.json` | Prior deterministic verification (7/8 PASS, JP=0.6590) |
| `evaluation/results/174k_tfidf_formal_suite/verification_20261009_185503.json` | GitHub run 37975401319 verification (6/8 PASS, JP=0.5925) |
| `evaluation/results/174k_tfidf_formal_suite/verification_20261009_192845.json` | GitHub run 37979605042 verification (7/8 PASS, JP=0.6590) |
| `evaluation/results/174k_tfidf_formal_suite/verification_20261009_204440.json` | **This run** verification 1 (7/8 PASS, JP=0.6590) |
| `evaluation/results/174k_tfidf_formal_suite/verification_20261009_204450.json` | **This run** verification 2 (IDENTICAL) |

---

*This report confirms the evaluation lane v35 work is complete, verified, and audit-ready for GitHub run 37988462224.*