# Evaluation Lane — Factory Direction v35 Final Verification (GitHub Run 37979605042)

**Run ID:** EVALUATION_V35_RUN_37979605042_FINAL_VERIFICATION  
**Date:** 2026-10-09  
**GitHub Run:** 37979605042  
**Evidence Tier:** TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Executive Summary

This run performs the **final independent verification** of the evaluation lane's v35 deliverables. The lane question was:

> "Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."

**Both deliverables are confirmed FROZEN and VERIFIED:**

1. ✅ **TF-IDF 174k evaluation FROZEN as production baseline** — Deterministic adversarial verification with sorted groups fix shows 7/8 representations PASS both gates with production baseline `cited_decisions_tfidf_outcome_hybrid_0.5` achieving JP=0.6590, LangDom=0.4258. **Non-determinism from metadata ordering FIXED via sorted groups** — results match prior deterministic verification (2026-10-09T08:12/10:43).

2. ✅ **Dense embedding complementary view acceptance criteria FROZEN and VALIDATED at maximal available scale (144k/22yr)** — All four criteria defined with explicit thresholds, validated against ACCEPTED evidence from legal-distance and fractal-map lanes.

**No further same-question cycles are justified.** The lane is COMPLETE with `continue_recommended=false`.

---

## 1. Current Verification Results (GitHub Run 37979605042)

### 1.1 Environment
- **numpy:** 2.5.3
- **scikit-learn:** 1.9.1
- **scipy:** 1.18.1
- **Python:** 3.12

### 1.2 Adversarial Gate Results

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

**Result:** 7/8 representations PASS both adversarial gates. Production baseline passes both gates.

---

## 2. Cross-Environment Discrepancy Resolution

### 2.1 Three Environments Compared

| Environment | Run | PASS | Prod Baseline JP | Prod Baseline LangDom | Notes |
|-------------|-----|------|------------------|----------------------|-------|
| Prior env (local) | 2026-10-09T08:12 | 7/8 | 0.6590 | 0.4258 | Deterministic (sorted groups fix) |
| Prior env (local) | 2026-10-09T10:43 | 7/8 | 0.6590 | 0.4258 | Identical to 08:12 |
| GitHub 37975401319 | 2026-10-09T18:55 | 6/8 | 0.5925 | 0.3481 | Fresh env, different sklearn version |
| **GitHub 37979605042** | **2026-10-09T19:28** | **7/8** | **0.6590** | **0.4258** | **Matches prior env** |

### 2.2 Root Cause Confirmed
- **Identical inputs:** Same embeddings (SHA256: 4135e00e...), same metadata (SHA256: 34a0d467...), same config hash (a31c443a...), same global seed (42), same sorted groups fix
- **Different k-NN tie-breaking:** numpy/sklearn version differences cause different neighbor ordering when cosine distances are equal
- **Impact:** Affects `legal_neighbor_rate` calculation for borderline cases in `simulate_pairwise_preference`

### 2.3 Resolution
**The "frozen baseline" is environment-dependent.** The sorted groups fix ensures determinism *within* a given software environment, but cross-environment reproducibility requires pinned dependency versions. This is documented in the lane state.

**Critical:** The production baseline `cited_decisions_tfidf_outcome_hybrid_0.5` **passes both adversarial gates in ALL verified environments** (JP > 0.5, LangDom < 0.85). The mission criterion (beat simple semantic baseline JP=0.43) is satisfied in all environments.

---

## 3. Dense Embedding Complementary View Criteria — CONFIRMED FROZEN

### 3.1 Citation Heritage View ✅ PASSED
- **Metric:** AUC-ROC for recovering cited precedent pairs
- **Threshold:** AUC > 0.75
- **Evidence at 144k/22yr:** center_projected_64dim AUC = 0.7922 (CI [0.762, 0.822])
- **Baseline Comparison:** TF-IDF citation-based AUC 0.71-0.74; Dense **SUPERIOR**
- **Minimal Scale:** 130k decisions (21-year, 2000-2020)
- **Required Dense Modes:** center_projected_64dim, center_projected_128dim, center_projected_768dim
- **Product Integration:** Separate map mode `citation_heritage_view`
- **Status at 174k:** VALIDATION BLOCKED (corpus lane: BGE/bger ID mapping + parquet 2022-2026)

### 3.2 Cross-Lingual View — Sachverhalt (Facts) ✅ PASSED
- **Metric:** cross_lang_same_branch_mean on Sachverhalt section
- **Threshold:** > 0.20
- **Evidence at 144k/22yr:** center_projected_64dim = 0.2816 (n=359, 36% coverage)
- **Hierarchy Rank:** 1 (best cross-lingual alignment)
- **Product Integration:** Separate map mode `cross_lingual_sachverhalt_view`
- **Status at 174k:** BLOCKED pending section extraction at 174k

### 3.3 Cross-Lingual View — Dispositiv (Holdings) ✅ PASSED
- **Metric:** cross_lang_same_branch_mean on Dispositiv section
- **Threshold:** > 0.10
- **Evidence at 144k/22yr:** center_projected_64dim = 0.1502 (n=538, 54% coverage)
- **Hierarchy Rank:** 2
- **Product Integration:** Separate map mode `cross_lingual_dispositiv_view`
- **Status at 174k:** BLOCKED pending section extraction at 174k

### 3.4 Cross-Lingual View — Erwaegungen (Reasoning) ❌ FAILED (Correctly Excluded)
- **Metric:** cross_lang_same_branch_mean on Erwaegungen section
- **Threshold:** > 0.10
- **Evidence at 144k/22yr:** center_projected_64dim = 0.0941 (n=510, 51% coverage)
- **Note:** Reasoning is most language-specific; not suitable for cross-lingual view
- **Product Integration:** NOT INCLUDED

### 3.5 Linear Hybrid Complement ⚠️ CONDITIONAL
- **Metric:** PASS both adversarial gates AND cross_lang_same_branch > TF-IDF baseline
- **Evidence at 144k/22yr:** w=0.3-0.4 PASS adversarial, cross_lang +26-29% over TF-IDF, but JP 0.61-0.67 < TF-IDF 0.78-0.79
- **Product Integration:** Separate map mode `linear_hybrid_complement_view` (marked **EXPLORATORY**)
- **Note:** Evidence from obsolete v6-v10 embeddings; target 174k dense embeddings do not exist

---

## 4. Fundamental Tradeoff — REPRODUCED AT ALL SCALES

| Scale | TF-IDF Citation Hybrids | Dense Semantic | Linear Hybrids |
|-------|------------------------|----------------|----------------|
| | LD / JP / CiteIndep | LD / JP / CiteIndep | LD / JP / CiteIndep |
| 3yr | 0.48 / 0.78 / 0.14 | 0.98 / 0.05 / 0.37 | 0.58 / 0.61 / 0.25 |
| 15yr | 0.48 / 0.78 / 0.14 | 0.98 / 0.15 / 0.37 | 0.62 / 0.65 / 0.30 |
| 19yr | 0.48 / 0.78 / 0.14 | 0.83 / 0.43 / 0.37 | 0.66 / 0.67 / 0.35 |
| 22yr | 0.48 / 0.78 / 0.14 | 0.84 / 0.40 / 0.37 | 0.74 / 0.67 / 0.35 |

**Conclusion:** **NO single representation dominates all three metrics at any scale.**

- **LD** = Language Dominance (lower = better)
- **JP** = Jurist Preference (higher = better)  
- **CiteIndep** = Citation Independence (higher = better doctrinal recovery)

---

## 5. True Out-of-Sample Ceiling

| Metric | Value | Factory Target | Achievable |
|--------|-------|----------------|------------|
| Jurist Preference Ceiling | ~0.53 | 0.7 | ❌ NO |

**Source:** v8 holdout zero-shot validation. Fundamental limitation of simulated jurist proxy.

---

## 6. Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **BGE/bger ID mapping** | Cannot align 174k dense embeddings (bge_ IDs) with evaluation metadata (bger_ IDs) | Corpus lane: produce canonical mapping |
| **Parquet 2022-2026** | 29,520 decisions missing; cannot compute 174k dense embeddings | Corpus lane: generate parquet for 2022-2026 |
| **Section extraction 174k** | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at 174k scale | Corpus lane: run section extraction at 174k |
| **GPU unavailable** | No BGE/multilingual-e5 fine-tuning at scale | Infrastructure: provision GPU |

**No evaluation work can proceed on dense complementary views at 174k until these are resolved.**

---

## 7. External Dependencies

| Dependency | Status | Description |
|------------|--------|-------------|
| **Jurist Human Study** | FRAMEWORK_READY | 5-10 Swiss jurists, framework ready, not yet executed. Purpose: ultimate validation of simulated jurist proxy. |

---

## 8. Evidence Provenance

All findings trace to ACCEPTED evidence from upstream lanes:

| Source | Key Evidence |
|--------|--------------|
| `/tmp/lex_accepted/legal-distance/state/legal-distance.json` | Minimal dense scale characterization COMPLETE, citation heritage AUC 0.77-0.85 > 0.75, section cross-lingual hierarchy confirmed, true OOS JP ceiling ~0.53 |
| `/tmp/lex_accepted/legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` | 174k TF-IDF formal suite: 8/8 modes PASS both adversarial gates (original freeze) |
| `/tmp/lex_accepted/fractal-map/state/fractal-map.json` | TF-IDF hierarchical production modes OPERATIONAL at 174k, dense integration contract v34 frozen |
| `/tmp/lex_accepted/fractal-map/results/fractal_map/dense_embeddings_integration_contract_v34.json` | Frozen dense integration contract with all four complementary view criteria |
| `/tmp/lex_accepted/fractal-map/results/fractal_map/144k_checkpoint_validation/144k_validation_144443decisions.json` | 144k hierarchical validation: fine_branch_purity ~0.97, strict_nesting ≥0.99 |

---

## 9. Conformance Verification

| Test | Result | Notes |
|------|--------|-------|
| `verify_frozen_baseline.py` (2026-10-09 19:28, THIS RUN) | ✅ 7/8 PASS | Matches prior env: JP=0.6590, LangDom=0.4258 |
| `verify_frozen_baseline.py` (2026-10-09T08:12, PRIOR ENV) | ✅ 7/8 PASS | Prior env: JP=0.6590, LangDom=0.4258 |
| `verify_frozen_baseline.py` (2026-10-09 18:55, GH 37975401319) | ✅ 6/8 PASS | Different env: JP=0.5925, LangDom=0.3481 |
| `test_v25_174k_suite_snapshot.py` | ✅ PASS | 174k TF-IDF formal suite snapshot conforms |
| `test_frozen_harness_v3_reproducibility.py` | ✅ PASS | All 6 representations REPRODUCED within tolerance 0.001 |

---

## 10. Recommendation

**CONTINUE_RECOMMENDED = false**

The evaluation lane has:
- ✅ Frozen TF-IDF 174k evaluation as production baseline (with mutation history documented, non-determinism FIXED within environment, cross-environment discrepancy documented)
- ✅ Defined and validated dense embedding complementary view acceptance criteria at max available scale (144k/22yr)
- ✅ Documented all accepted negative findings
- ✅ Identified precise data blockers
- ✅ Verified frozen artifacts pass conformance tests in current environment

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale. Once dense embeddings are delivered at 174k, a **new evaluation cycle** (not same-question) will validate them against the frozen criteria.

---

## 11. Artifacts Written This Run

- `evaluation/results/174k_tfidf_formal_suite/verification_20261009_192845.json` — Deterministic adversarial verification (7/8 PASS, JP=0.6590)
- `evaluation/results/174k_tfidf_formal_suite/verification_latest.json` — Latest verification symlink
- `state/evaluation.json` — Updated with GitHub run 37979605042 verification
- `reports/evaluation/EVALUATION_V35_RUN_37979605042_FINAL_VERIFICATION_20261009.md` — This report

All negative results preserved. No claim-bearing outputs overwritten.

---

*This report confirms the evaluation lane v35 work is complete and audit-ready for GitHub run 37979605042.*