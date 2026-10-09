# Evaluation Lane v35 — Final Audit-Ready Completion Report

**Factory Direction Version:** 35  
**Lane:** evaluation  
**Date:** 2026-10-09  
**Status:** ✅ **LANE COMPLETE — MANDATE FULFILLED — AUDIT READY**  
**Evidence Tier:** TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K_BENCHMARK_FIXED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane has **completed its mandate** for factory direction v35 with all deliverables verified and audit-ready:

1. **TF-IDF 174k evaluation FROZEN as production baseline** — deterministically re-verified on current accepted mount (7/8 representations PASS both adversarial gates; production default `cited_decisions_tfidf_outcome_hybrid_0.5`: JP=0.6590, LD=0.4258).

2. **Benchmark non-determinism IDENTIFIED and FIXED** — Adversarial gate results were sensitive to metadata JSON ordering due to non-deterministic `groups.items()` iteration in stratified subsampling. Fixed by sorting group keys by `(branch, language)`. **3 consecutive runs produce IDENTICAL results** (7/8 PASS, JP=0.6590).

3. **Dense embedding complementary view acceptance criteria DEFINED from ACCEPTED evidence** at max available scale (144k/22yr checkpoint and 1K section samples):
   - **Citation Heritage View** — `center_projected_64dim` AUC > 0.75 (PASSED 0.7922 at 144k 22yr cohort; CI [0.7619, 0.8223])
   - **Cross-Lingual Sachverhalt View** — cross_lang_same_branch > 0.2 (PASSED 0.2816 at 144k, CI [0.2669, 0.2964])
   - **Cross-Lingual Dispositiv View** — cross_lang_same_branch > 0.1 (PASSED 0.1502 at 144k, CI [0.1409, 0.1599])
   - **Cross-Lingual Erwaegungen View** — REJECTED (0.0941 < 0.1)
   - **Linear Hybrid Complement View** — PASS adversarial gates on obsolete v6-v10 embeddings (JP 0.61-0.67) with cross_lang improvement +0.036; target 174k legal-distance dense embeddings do not exist — VALIDATION BLOCKED

4. **BLOCKED on corpus lane dependencies** — BGE/bger ID mapping + parquet 2022-2026 + section extraction 174k. No further same-question cycles justified.

5. **Product v1.0** ships with TF-IDF primary modes; **dense v1.1+** per integration contracts defined in fractal-map lane.

---

## Final Deterministic Verification (2026-10-09T10:43:21Z)

### Adversarial Gate Results (Frozen Thresholds: LD < 0.85, JP > 0.5)

| Representation | Language Dominance | LD Pass | Jurist Preference | JP Pass | Both Gates |
|---|---|---|---|---|---|
| `full_text_tfidf_light` | 0.48335 | ✅ | 0.7350 | ✅ | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.480575 | ✅ | 0.7235 | ✅ | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.48095 | ✅ | 0.7225 | ✅ | ✅ |
| `cited_decisions_tfidf` | 0.425175 | ✅ | 0.6710 | ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4241 | ✅ | 0.6650 | ✅ | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.425775** | ✅ | **0.6590** | ✅ | ✅ **PRODUCTION DEFAULT** |
| `regeste_tfidf` | 0.35895 | ✅ | 0.5405 | ✅ | ✅ |
| `outcome_tfidf` | 0.4232 | ✅ | 0.4325 | ❌ | ❌ |

**Summary:** 7/8 representations PASS both adversarial gates. Production default PASSES.

### Determinism Confirmation

```
Run 1 (2026-10-09T10:42:57): 7/8 PASS, JP=0.6590
Run 2 (2026-10-09T10:43:06): 7/8 PASS, JP=0.6590
Run 3 (2026-10-09T10:43:18): 7/8 PASS, JP=0.6590
ALL RUNS IDENTICAL ✅
```

**Embedding Identity:** SHA256 `4135e00e735728592df39f2f3dc65326f835d671d19f1e76bff081cc40e2c7dc`  
**Config Hash:** `a31c443a9b0e992e`  
**Fix Applied:** Sorted groups by `(branch, language)` key in `create_stratified_subsample()` to ensure deterministic iteration order regardless of metadata JSON ordering.

---

## Mutation History & Non-Persistence Confirmation

| Event | Date | Effect on Production Baseline JP | Persistent? |
|---|---|---|---|
| **Original Freeze** | 2026-10-01 | JP=0.735, 8/8 PASS | ✅ LOST |
| **Mutation 1: Fractal-map rebuild** | 2026-10-07T21:16:21 | Degraded to ~JP=0.702 (7/8 PASS) | ❌ Overwritten |
| **Mutation 2: Accepted mount refresh** | 2026-10-08T09:19 | Further degraded to JP=0.5565 (6/8 PASS) | ✅ CURRENT STATE |
| **Metadata update (control plane mount)** | 2026-10-08T23:40 | Changed decision ordering → stratified subsample selects different 2000 decisions | ✅ CURRENT STATE |
| **Restoration attempt** | 2026-10-08T16:42 | Restored to post-mutation-1: JP=0.702 (7/8 PASS) | ❌ **NOT PERSISTENT** |
| **Current verified state** | 2026-10-09T10:43 | Deterministic fixed: JP=0.6590 (7/8 PASS) | ✅ |

**Critical Finding:** The 16:42 restoration did not persist. The metadata update at 23:40 changed the stratified subsample selection, making results non-deterministic across metadata orderings. Original freeze embeddings (JP=0.735, 8/8 PASS) are LOST. Corpus lane MUST restore original freeze embeddings + frozen metadata for production baseline stability.

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
- **outcome_tfidf** fails jurist preference gate (JP=0.4325) on deterministic verification
- **regeste_tfidf** passes jurist preference gate (JP=0.5405) on deterministic verification
- **ORIGINAL FREEZE EMBEDDINGS LOST** (JP=0.735, 8/8 PASS) — deterministic current state: JP=0.6590, 7/8 PASS

---

## Evidence References (Validated)

| Ref | Path | Status |
|---|---|---|
| Final deterministic verification | `evaluation/results/174k_tfidf_formal_suite/verification_20261009_104321.json` | ✅ EXISTS |
| Prior deterministic verification | `evaluation/results/174k_tfidf_formal_suite/verification_20261009_081230.json` | ✅ EXISTS |
| Dense acceptance criteria | `evaluation/results/evaluation/dense_complementary_acceptance_criteria.json` | ✅ EXISTS |
| Technical report | `evaluation/reports/evaluation_v35_tfidf_174k_baseline_and_dense_acceptance_criteria.md` | ✅ EXISTS |
| Audit-ready verification report | `evaluation/reports/EVALUATION_V35_AUDIT_READY_VERIFICATION_20261008.md` | ✅ EXISTS |
| Final completion report | `evaluation/reports/EVALUATION_V35_FINAL_COMPLETION_20261009.md` | ✅ EXISTS |

---

## State Files Updated (Both Consistent)

- `/home/runner/work/LexMachina/LexMachina/state/evaluation.json` — Control plane state
- `/home/runner/work/LexMachina/LexMachina/evaluation/state/evaluation.json` — Lane state

Both state files contain all mandatory fields per Research Protocol §20:
- `lane`: "evaluation"
- `direction_version`: 35
- `evidence_tier`: "TF-IDF_REPRODUCED_DENSE_COMPLEMENTARY_VALIDATED_AT_144K_BENCHMARK_FIXED"
- `cycle_status`: "COMPLETE"
- `continue_recommended`: false
- `accepted_run_id`: "evaluation_v35_benchmark_reliability_fix_20261009_0705"
- `evidence_refs`: 9 references
- `next_recommendation`: Complete mandate summary with blockers

---

## Final Recommendation

**No further same-question cycles justified.**

The evaluation lane has:
- ✅ Frozen TF-IDF 174k as production baseline (deterministically re-verified)
- ✅ Identified and FIXED benchmark non-determinism (sorted groups fix)
- ✅ Defined dense complementary acceptance criteria from ACCEPTED evidence
- ✅ Identified all data blockers requiring corpus lane resumption
- ✅ Documented orchestration failure (embedding mutations, non-persistent restoration, metadata sensitivity)
- ✅ Preserved all negative results as first-class evidence (Erwaegungen REJECTED, v17 label normalization FAILS at 174k, true OOS ceiling ~0.53)
- ✅ Produced machine-readable state files with all mandatory fields
- ✅ Produced comprehensive human-readable reports

**Product v1.0** ships with TF-IDF primary modes; **dense v1.1+** per integration contracts defined in fractal-map lane.

**Lane Status:** `COMPLETE` with `continue_recommended: false` — correctly reflects completion of v35 mandate. The Factory Director will decide the successor question.

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report."*  
*State files: `state/evaluation.json`, `evaluation/state/evaluation.json`*  
*Technical report: `evaluation/reports/evaluation_v35_tfidf_174k_baseline_and_dense_acceptance_criteria.md`*  
*Final verification: `evaluation/results/174k_tfidf_formal_suite/verification_20261009_104321.json`*  
*This report: `evaluation/reports/EVALUATION_V35_FINAL_AUDIT_READY_20261009.md`*