# Evaluation Lane v35 — Final Verification Report (2026-10-08T21:24)

**Factory Direction Version:** 35  
**Lane:** evaluation  
**Verification Date:** 2026-10-08T21:24:04Z  
**Status:** ✅ **LANE COMPLETE — BASELINE VERIFIED, RESTORATION NON-PERSISTENCE CONFIRMED**

---

## Executive Summary

This verification confirms the evaluation lane v35 mandate is complete:

1. **TF-IDF 174k production baseline RE-VERIFIED** on current accepted mount (degraded post-mutation-2 state): 6/8 representations PASS both adversarial gates. Production default `cited_decisions_tfidf_outcome_hybrid_0.5`: JP=0.5565 (PASS), LD=0.43775 (PASS).

2. **16:42 restoration was NOT PERSISTENT** — The accepted mount temporarily recovered to post-mutation-1 state (7/8 PASS, JP=0.702) at 16:42 but reverted to degraded state (6/8 PASS, JP=0.5565) by 21:24.

3. **Original freeze embeddings (JP=0.735, 8/8 PASS) are LOST** — Working directory and accepted mount embeddings are IDENTICAL (SHA256 verified) and match the degraded post-mutation-2 state.

4. **Corpus lane MUST restore original freeze embeddings** for production baseline stability.

5. **Dense complementary acceptance criteria DEFINED** from ACCEPTED evidence (unchanged from v35 report).

---

## Current Verified State (2026-10-08T21:24:04Z)

### Adversarial Gate Results (Frozen Thresholds: LD < 0.85, JP > 0.5)

| Representation | Language Dominance | LD Pass | Jurist Preference | JP Pass | Both Gates |
|---|---|---|---|---|---|
| `regeste_full_text_hybrid_0.7` | 0.4810 | ✅ | 0.7420 | ✅ | ✅ |
| `full_text_tfidf_light` | 0.4850 | ✅ | 0.7320 | ✅ | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4828 | ✅ | 0.7315 | ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4354 | ✅ | 0.5660 | ✅ | ✅ |
| `cited_decisions_tfidf` | 0.4349 | ✅ | 0.5580 | ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.43775** | ✅ | **0.5565** | ✅ | ✅ **PRODUCTION DEFAULT** |
| `regeste_tfidf` | 0.3999 | ✅ | 0.3620 | ❌ | ❌ |
| `outcome_tfidf` | 0.4915 | ✅ | 0.2510 | ❌ | ❌ |

**Summary:** 6/8 representations PASS both adversarial gates. Production default PASSES.

### Embedding Identity Verification

```
SHA256 (accepted mount):  4135e00e735728592df39f2f3dc65326f835d671d19f1e76bff081cc40e2c7dc
SHA256 (working directory): 4135e00e735728592df39f2f3dc65326f835d671d19f1e76bff081cc40e2c7dc
STATUS: IDENTICAL — both match degraded post-mutation-2 state
```

---

## Mutation History & Non-Persistence Confirmation

| Event | Date | Effect on Production Baseline JP | Persistent? |
|---|---|---|---|
| **Original Freeze** | 2026-10-01 | JP=0.735, 8/8 PASS | ✅ LOST |
| **Mutation 1: Fractal-map rebuild** | 2026-10-07T21:16:21 | Degraded to ~JP=0.702 (7/8 PASS) | ❌ Overwritten |
| **Mutation 2: Accepted mount refresh** | 2026-10-08T09:19 | Further degraded to JP=0.5565 (6/8 PASS) | ✅ CURRENT STATE |
| **Restoration attempt** | 2026-10-08T16:42 | Restored to post-mutation-1: JP=0.702 (7/8 PASS) | ❌ **NOT PERSISTENT** |
| **Current verified state** | 2026-10-08T21:24 | Degraded post-mutation-2: JP=0.5565 (6/8 PASS) | ✅ |

**Critical Finding:** The 16:42 restoration (verified in `verification_20261008_164224.json` showing 7/8 PASS, JP=0.702) did not persist. The accepted mount reverted to the degraded post-mutation-2 state. Both working directory and accepted mount now hold identical degraded embeddings.

---

## Required Remediation

**Corpus lane MUST restore original freeze embeddings (JP=0.735, 8/8 PASS) to accepted mount for production baseline stability.**

The original freeze embeddings exist in the producer workspace (regenerated 2026-10-02 as `cited_outcome_hybrid_0.5_174k` with 7 zoom levels). These must be promoted to the accepted mount.

---

## Dense Complementary View Acceptance Criteria (Unchanged from v35)

All criteria derived from **ACCEPTED evidence** at max available evaluated scale:

| View | Threshold | Best Mode | Status at Max Scale |
|---|---|---|---|
| Citation Heritage | AUC > 0.75 | `center_projected_64dim` | ✅ PASSED at 144k (0.7922, CI [0.7619, 0.8223]) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | `center_projected_64dim`/section | ✅ PASSED at 144k (0.2816, CI [0.2669, 0.2964]) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | `center_projected_64dim`/section | ✅ PASSED at 144k (0.1502, CI [0.1409, 0.1599]) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | `center_projected_64dim`/section | ❌ REJECTED (0.0941) |
| Linear Hybrid Complement | PASS gates + cross_lang > TF-IDF | `center_projected_64dim`/`128dim` | ⚠️ BLOCKED — only validated on obsolete v6-v10 embeddings |

**Full 174k validation BLOCKED** on all dense views pending corpus lane: BGE/bger ID mapping + parquet 2022-2026 + section extraction 174k.

---

## Evidence References (Validated)

| Ref | Path | Status |
|---|---|---|
| Adversarial verification (current) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_212404.json` | ✅ EXISTS |
| Adversarial verification (16:42 restoration) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_164224.json` | ✅ EXISTS |
| Adversarial verification (09:31 degraded) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_093113.json` | ✅ EXISTS |
| TF-IDF formal suite baseline reverified | `evaluation/results/evaluation/tfidf_174k_formal_suite_baseline_reverified.json` | ✅ EXISTS |
| Dense acceptance criteria | `evaluation/results/evaluation/dense_complementary_acceptance_criteria.json` | ✅ EXISTS |
| v35 technical report | `evaluation/reports/evaluation_v35_tfidf_174k_baseline_and_dense_acceptance_criteria.md` | ✅ EXISTS |
| v35 audit-ready verification | `evaluation/reports/EVALUATION_V35_AUDIT_READY_VERIFICATION_20261008.md` | ✅ EXISTS |

---

## State File Updated

**File:** `/home/runner/work/LexMachina/LexMachina/state/evaluation.json`

Updated fields:
- `frozen_baseline.adversarial_gates` — Current verified state (6/8 PASS, JP=0.5565)
- `frozen_baseline.best_metrics_current_mount` — Updated with production baseline metrics
- `audit_corrections_applied.stability_confirmation_20261008_CORRECTED` — Note added: 16:42 restoration NOT PERSISTENT
- `audit_corrections_applied.adversarial_gate_reverification_20261008_0744` — Note updated

---

## Final Recommendation

**No further same-question cycles justified.** 

The evaluation lane has:
- ✅ Frozen TF-IDF 174k as production baseline (re-verified with full mutation context)
- ✅ Defined dense complementary acceptance criteria from ACCEPTED evidence
- ✅ Identified all data blockers requiring corpus lane resumption
- ✅ Documented orchestration failure (embedding mutations, non-persistent restoration)
- ✅ Preserved all negative results as first-class evidence
- ✅ Produced machine-readable state file with all mandatory fields
- ✅ Produced comprehensive human-readable reports

**Product v1.0** ships with TF-IDF primary modes; **dense v1.1+** per integration contracts defined in fractal-map lane.

**Lane Status:** `BLOCKED_ON_DEPENDENCIES` with `continue_recommended: false` — correctly reflects completion of v35 mandate.

---

*Verification executed per Research Protocol §8: "Write machine-readable lane state plus human-readable report."*
*State file: `evaluation/state/evaluation.json`*
*Technical report: `evaluation/reports/evaluation_v35_tfidf_174k_baseline_and_dense_acceptance_criteria.md`*
*Audit-ready verification: `evaluation/reports/EVALUATION_V35_AUDIT_READY_VERIFICATION_20261008.md`*
*This verification: `evaluation/reports/EVALUATION_V35_FINAL_VERIFICATION_20261008_2124.md`*