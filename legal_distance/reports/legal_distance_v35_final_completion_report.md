# Legal Distance Lane — Final Completion Report (Factory Direction v35)

**Run ID**: 37954633332  
**Date**: 2026-10-09  
**Lane**: legal-distance  
**Direction Version**: 35  
**Status**: CHARACTERIZATION COMPLETE — BLOCKED_ON_DEPENDENCIES

---

## Executive Summary

The PIVOT_WITHIN_MISSION characterization (initiated at v34 per audit CYCLE_37090665528) is **COMPLETE**. The question *"What minimal dense embedding scale and which specific dense modes are necessary and sufficient for the product's non-jurist-preference views?"* has been **fully answered** with ACCEPTED evidence.

**No further same-question cycles are justified.** The lane is correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`.

---

## Answered Question

**Three complementary dense modes characterized at minimal sufficient scales:**

| View | Minimal Scale | Evidence | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage** | 21yr / 137k (2000-2020) | Dense center_projected_64dim AUC 0.77-0.85 at 21-24yr (137k-158k); TF-IDF citation baseline 0.71-0.74 | AUC > 0.75 | ✅ PASSED |
| **Section Cross-Lingual** | 1K sample with sections | Sachverhalt cp64 cross_lang_same_branch=0.282, Dispositiv=0.150, Erwaegungen=0.094 | Sachverhalt >0.2, Dispositiv >0.1, Erwaegungen >0.05 | ✅/✅/❌ |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | w=0.3-0.4 PASS both adversarial gates; JP 0.61-0.67 vs TF-IDF 0.78-0.79 | PASS adversarial, JP > 0.60 | ✅ PASSED |

---

## Key Accepted Findings (All Reproduced)

1. **Dense embeddings FAIL jurist gate at ALL scales** (JP 0.05-0.43) — cannot be primary navigation
2. **TF-IDF citation hybrids DOMINATE jurist preference** (JP 0.78-0.79) — PRIMARY product mode
3. **Dense embeddings SUPERIOR at citation heritage recovery** (AUC 0.79-0.85 vs TF-IDF 0.71-0.74)
4. **Section cross-lingual hierarchy**: Sachverhalt (facts) > Dispositiv (holdings) > Erwaegungen (reasoning)
5. **Linear hybrids PASS adversarial at optimal weight** (w=0.3-0.4) but remain BELOW TF-IDF baseline
6. **True OOS JuristPref ceiling ~0.53** < 0.7 factory target (v8 holdout confirmed)
7. **v18 coarse hierarchy NEGATIVE** (max branch purity 0.65 < 0.7)
8. **Two-mode tradeoff fundamental**: No single representation dominates JP + LangDom + CiteIndep

---

## Verification Results

| Test Suite | Tests | Result |
|---|---|---|
| `test_complementary_role_v34.py` | 8 | ✅ ALL PASSED |
| `test_v29_final_results.py` | 15 | ✅ ALL PASSED |
| `characterize_dense_complementary_views.py` | Scale characterization | ✅ REPRODUCED identical patterns |

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---|---|---|
| **BGE/bger ID mapping** | Cannot align 174k dense embeddings with evaluation metadata | Corpus lane resumption |
| **Parquet 2024-2026** | 15,536 decisions missing from dense embeddings | Corpus lane resumption |
| **174k section extraction** | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at scale | Corpus lane resumption |

---

## Evidence References (ACCEPTED)

- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/` — Citation heritage at 21/22/24yr
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/` — Section cross-lingual at 1K sample
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/` — Hybrid weight sweep
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/` — TF-IDF 174k formal suite (PRIMARY validated)
- `/tmp/lex_accepted/evaluation/results/evaluation/dense_complementary_acceptance_criteria.json` — Frozen acceptance criteria

---

## Recommendation

**PAUSE** this lane question. The characterization is complete. Resume ONLY when corpus lane delivers:
1. BGE/bger ID mapping
2. Parquet for 2024-2026
3. 174k section extraction

No new experiments, no new cycles on this question. All evidence is ACCEPTED and preserved.

---

## Lane State Consistency

| Source | Status | Notes |
|---|---|---|
| `state/legal-distance.json` | BLOCKED_ON_DEPENDENCIES, continue_recommended=false | **CORRECT** |
| `factory_direction.json` v35 | RUN | Orchestration discrepancy (known, documented in director_note) |
| Audit verification runs | 18+ consecutive PASS | All confirm same findings |

The lane state is the authoritative record per ARCHITECTURE.md invariant: "At most one active run per core lane" and "PASS required for accepted promotion."

---

*Report generated per Research Protocol step 13. All negative results preserved. No claim-bearing outputs overwritten.*