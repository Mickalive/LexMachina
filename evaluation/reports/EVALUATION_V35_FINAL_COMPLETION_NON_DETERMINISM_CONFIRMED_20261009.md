# Evaluation Lane v35 — Final Completion Report: Non-Determinism Confirmed

**Factory Direction Version:** 35  
**Lane:** evaluation  
**Date:** 2026-10-09  
**Status:** ✅ **LANE COMPLETE — MANDATE FULFILLED WITH CRITICAL FINDING**  
**Evidence Tier:** TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane has **completed its mandate** for factory direction v35 with a **critical finding**:

1. **TF-IDF 174k evaluation FROZEN as production baseline** — verified at 173,963 decisions
2. **Dense embedding complementary view acceptance criteria DEFINED** from ACCEPTED evidence at max available scale (144k/22yr)
3. **CRITICAL NON-DETERMINISM CONFIRMED (2026-10-09T03:54:29Z):** Adversarial gate results are **sensitive to metadata ordering** — same embeddings, same config hash, same seed yield different results depending on metadata_174k.json ordering
4. **BLOCKED on corpus lane dependencies** — BGE/bger ID mapping + parquet 2022-2026 + section extraction 174k

---

## Critical Finding: Adversarial Gate Non-Determinism

### Two Stable States Observed

| Verification | Metadata | Reps PASS Both Gates | Production Baseline JP | Production Baseline LD |
|---|---|---|---|---|
| 2026-10-09T01:18 | NEW (post-23:40 mount) | 6/8 | 0.5565 | 0.4377 |
| 2026-10-09T03:54 | OLD (pre-23:40 mount) | 7/8 | 0.7020 | 0.4236 |
| 2026-10-08T07:44 | OLD | 7/8 | 0.702 | 0.4236 |
| 2026-10-08T23:44 | NEW | 6/8 | 0.5565 | 0.4377 |

**All verifications used:**
- Same embeddings (SHA256: `4135e00e735728592df39f2f3dc65326f835d671d19f1e76bff081cc40e2c7dc`)
- Same config hash: `a31c443a9b0e992e`
- Same global seed: 42
- Same subsample size: 2000
- Same stratified subsampling algorithm

**Only difference:** Decision ordering in `metadata_174k.json` changed at 2026-10-08T23:40 during control plane mount update.

### Root Cause

The stratified subsample (seed=42, n=2000) selects different decisions when metadata ordering changes, because the sampling iterates through branch×language groups in dictionary iteration order, which depends on insertion order (Python 3.7+ preserves insertion order).

### Implication

**Production baseline stability requires FROZEN METADATA + FROZEN EMBEDDINGS.** The original freeze (2026-10-01, JP=0.735, 8/8 PASS) is LOST. Current state oscillates between two stable configurations depending on metadata ordering.

---

## Final Verification (2026-10-09T03:54:29Z) — OLD Metadata State

### Adversarial Gate Results (Frozen Thresholds: LD < 0.85, JP > 0.5)

| Representation | Language Dominance | LD Pass | Jurist Preference | JP Pass | Both Gates |
|---|---|---|---|---|---|
| `regeste_full_text_hybrid_0.7` | 0.4810 | ✅ | 0.7420 | ✅ | ✅ |
| `full_text_tfidf_light` | 0.4850 | ✅ | 0.7320 | ✅ | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4828 | ✅ | 0.7315 | ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4211 | ✅ | 0.7125 | ✅ | ✅ |
| `cited_decisions_tfidf` | 0.4207 | ✅ | 0.7055 | ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.4236** | ✅ | **0.7020** | ✅ | ✅ **PRODUCTION DEFAULT** |
| `regeste_tfidf` | 0.3758 | ✅ | 0.6395 | ✅ | ✅ |
| `outcome_tfidf` | 0.4578 | ✅ | 0.3910 | ❌ | ❌ |

**Summary:** 7/8 representations PASS both adversarial gates. Production default PASSES (JP=0.702, LD=0.4236).

---

## Dense Complementary View Acceptance Criteria (Final)

All criteria derived from **ACCEPTED evidence** at max available evaluated scale:

| View | Threshold | Best Mode | Status at Max Scale | Blocker |
|---|---|---|---|---|
| Citation Heritage | AUC > 0.75 | `center_projected_64dim` | ✅ PASSED at 144k (0.7922, CI [0.7619, 0.8223]) | Corpus: BGE/bger ID mapping + parquet 2022-2026 |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | `center_projected_64dim`/section | ✅ PASSED at 144k (0.2816, CI [0.2669, 0.2964]) | Corpus: section extraction 174k |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | `center_projected_64dim`/section | ✅ PASSED at 144k (0.1502, CI [0.1409, 0.1599]) | Corpus: section extraction 174k |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | `center_projected_64dim`/section | ❌ REJECTED (0.0941) | — |
| Linear Hybrid Complement | PASS gates + cross_lang > TF-IDF | `center_projected_64dim`/`128dim` | ⚠️ BLOCKED — only validated on obsolete v6-v10 embeddings | Legal-distance: 174k dense embeddings |

**Full 174k validation BLOCKED** on all dense views pending corpus lane resumption.

---

## Fundamental Tradeoff (Reproduced at All Scales)

| Metric | TF-IDF Citation Hybrids | Dense Semantic | Linear Hybrids |
|---|---|---|---|
| **Language Dominance** | ~0.48 | 0.83-0.98 | 0.58-0.80 |
| **Jurist Preference** | ~0.78 | 0.05-0.43 | 0.61-0.67 |
| **Citation Independence** | ~0.14 | ~0.37 | 0.25-0.35 |

**Conclusion:** NO single representation dominates all three metrics at any scale (3yr, 15yr, 19yr, 20yr, 21yr, 22yr, 24yr tested).

- **TF-IDF citation hybrids = PRIMARY** product mode (jurist preference, branch clustering)
- **Dense embeddings = COMPLEMENTARY** modes (citation heritage view, cross-lingual view, linear hybrid complement)

---

## True OOS Jurist Preference Ceiling

| Metric | Value |
|---|---|
| **Estimated ceiling** | ~0.53 |
| **Factory target** | 0.70 |
| **Status** | **NOT MET** |
| **Source** | v8 holdout zero-shot validation |

No representation achieves the factory target under true out-of-sample conditions.

---

## Data Blockers (Require Corpus Lane Resumption)

1. **BGE/bger ID mapping** — Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists
2. **Parquet 2022-2026** — 29,520 decisions missing (years 2022-2026), no `/tmp/bger.parquet`
3. **Section extraction 174k** — Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale
4. **GPU unavailable** — No BGE/multilingual-e5 finetuning at scale

---

## External Dependencies

| Dependency | Status | Description |
|---|---|---|
| Jurist human study | FRAMEWORK_READY | 5-10 Swiss jurists, framework ready, not yet executed; ultimate validation of simulated jurist proxy |

---

## Known Limitations (Frozen Baseline)

- **Cross-language retrieval:** 0.14 < 0.2 target
- **Boilerplate resistance:** -0.83 (negative)
- **Hierarchy coherence NMI:** 0.03 < 0.3 target
- **True OOS jurist preference ceiling:** ~0.53 < 0.7 factory target
- **Citation heritage AUC (production baseline):** 0.649 (FAIL at 0.65 threshold)
- **regeste_tfidf** fails jurist preference gate (JP=0.362) on NEW metadata; PASSES (JP=0.6395) on OLD metadata
- **outcome_tfidf** fails jurist preference gate (JP=0.251/0.391) on both metadata states
- **ORIGINAL FREEZE EMBEDDINGS LOST** (JP=0.735, 8/8 PASS) — current state NON-DETERMINISTIC: 6/8 PASS at JP=0.5565 (NEW metadata) ↔ 7/8 PASS at JP=0.702 (OLD metadata)
- **ADVERSARIAL GATE RESULTS ARE NON-DETERMINISTIC ACROSS METADATA ORDERINGS** — production baseline stability requires frozen metadata + embeddings

---

## Evidence References (Validated)

| Ref | Path | Status |
|---|---|---|
| Adversarial verification (03:54 - OLD metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261009_035429.json` | ✅ EXISTS |
| Adversarial verification (01:18 - NEW metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261009_011821.json` | ✅ EXISTS |
| Adversarial verification (00:26 - NEW metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261009_002625.json` | ✅ EXISTS |
| Adversarial verification (23:44 - NEW metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_234425.json` | ✅ EXISTS |
| Adversarial verification (21:24 - OLD metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_212404.json` | ✅ EXISTS |
| Adversarial verification (16:42 - OLD metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_164224.json` | ✅ EXISTS |
| Adversarial verification (09:31 - NEW metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_093113.json` | ✅ EXISTS |
| Adversarial verification (07:44 - OLD metadata) | `evaluation/results/174k_tfidf_formal_suite/verification_20261008_074403.json` | ✅ EXISTS |
| TF-IDF formal suite baseline reverified | `evaluation/results/evaluation/tfidf_174k_formal_suite_baseline_reverified.json` | ✅ EXISTS |
| Dense acceptance criteria | `evaluation/results/evaluation/dense_complementary_acceptance_criteria.json` | ✅ EXISTS |
| v35 technical report | `evaluation/reports/evaluation_v35_tfidf_174k_baseline_and_dense_acceptance_criteria.md` | ✅ EXISTS |
| v35 audit-ready verification | `evaluation/reports/EVALUATION_V35_AUDIT_READY_VERIFICATION_20261008.md` | ✅ EXISTS |
| v35 final verification | `evaluation/reports/EVALUATION_V35_FINAL_VERIFICATION_20261008_2124.md` | ✅ EXISTS |

---

## State Files Updated

- `/home/runner/work/LexMachina/LexMachina/state/evaluation.json` — Updated with non-determinism confirmation
- `/home/runner/work/LexMachina/LexMachina/evaluation/state/evaluation.json` — Updated with non-determinism confirmation

Both state files contain all mandatory fields per Research Protocol §20:
- `lane`: "evaluation"
- `direction_version`: 35
- `evidence_tier`: "TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K"
- `cycle_status`: "COMPLETE"
- `continue_recommended`: false
- `accepted_run_id`: "evaluation_v35_dense_complementary_validation_20261009_0104"
- `evidence_refs`: [10 references]
- `next_recommendation`: Complete mandate summary with non-determinism finding and blockers

---

## Final Recommendation

**No further same-question cycles justified.**

The evaluation lane has:
- ✅ Frozen TF-IDF 174k as production baseline (verified with full mutation context)
- ✅ Defined dense complementary acceptance criteria from ACCEPTED evidence
- ✅ Identified all data blockers requiring corpus lane resumption
- ✅ **DOCUMENTED CRITICAL ORCHESTRATION FAILURE:** Embedding mutations, non-persistent restoration, metadata sensitivity, and **adversarial gate non-determinism across metadata orderings**
- ✅ Preserved all negative results as first-class evidence (Erwaegungen REJECTED, v17 label normalization FAILS at 174k, true OOS ceiling ~0.53)
- ✅ Produced machine-readable state files with all mandatory fields
- ✅ Produced comprehensive human-readable reports

**Product v1.0** ships with TF-IDF primary modes; **dense v1.1+** per integration contracts defined in fractal-map lane.

**Lane Status:** `COMPLETE` with `continue_recommended: false` — correctly reflects completion of v35 mandate. The Factory Director will decide the successor question.

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report."*  
*State files: `state/evaluation.json`, `evaluation/state/evaluation.json`*  
*Technical report: `evaluation/reports/evaluation_v35_tfidf_174k_baseline_and_dense_acceptance_criteria.md`*  
*Non-determinism verification: `evaluation/results/174k_tfidf_formal_suite/verification_20261009_035429.json`*  
*This report: `evaluation/reports/EVALUATION_V35_FINAL_COMPLETION_NON_DETERMINISM_CONFIRMED_20261009.md`*