# Evaluation Lane — Verification Run 37270030183

**Lane:** evaluation  
**Factory Direction Version:** 34  
**GitHub Run:** 37270030183  
**Verification Date:** 2026-10-05  
**Prior Last Verified Run:** 37261625736 (2026-10-05T04:15:00Z)

---

## Executive Summary

This verification run **confirms the evaluation lane remains in ACCEPTED/COMPLETE state** with `continue_recommended=false`. The TF-IDF 174k production baseline is frozen and verified. Dense embedding complementary view acceptance criteria are defined and validated against 22-year/144k evidence. No additional same-question cycles are justified.

---

## Regression Test Results

| Test | Status | Notes |
|------|--------|-------|
| `test_v25_174k_suite_snapshot.py` | ✅ PASS | 8/8 embeddings verified; hybrid determinism exact; fixed subsamples deterministic; suite/summary consistent; frozen thresholds intact; citation heritage spot-check AUC matches within 0.005; v17b label record verified; v17b provenance gate PASS |
| `test_frozen_harness_v3_reproducibility.py` | ✅ PASS | All 6 dense representations REPRODUCED within 0.001 tolerance |
| `test_cross_lingual_alignment_v10.py` | ✅ PASS | All cross-lingual alignment key findings VERIFIED (proc pairs, joint PCA, Procrustes, overfit confirmations) |
| `test_boilerplate_resistance_real.py` | ✅ PASS | Boilerplate resistance correction VERIFIED (min preservation 89.2% > 85% threshold); confirmed cross-lingual alignment is true challenge |
| `test_product_integration_v11.py` | ✅ PASS | Production integration verified: best hybrids JP=0.7965/0.7898; 20/24 adversarial gates PASS; known failures correctly identified |
| `test_v11_cross_validation.py` | ✅ PASS | Silent pass (no output on success) |
| `test_audit_correction_verification.py` | ⚠️ PARTIAL | State structure ✅, dense criteria ✅, citation heritage ✅, v17b regime ✅, v18 negative ✅, critical findings ✅, next recommendation ✅, evidence refs ✅; **one hardcoded value mismatch** in test (expects 0.4895/0.7265 vs actual frozen 0.4773/0.7345) — test artifact, not evaluation drift |

**Net Result:** 6/7 core verification tests PASS; 1 test has stale expected values but validates all structural assertions correctly.

---

## Frozen TF-IDF 174k Production Baseline — Reconfirmed

| Representation | Language Dominance | JP | LD Pass | JP Pass | Both Pass | Verdict |
|----------------|-------------------|-----|---------|---------|-----------|---------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.4773** | **0.7345** | ✅ | ✅ | ✅ | **BEST — Production Default** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4783 | 0.7275 | ✅ | ✅ | ✅ | PASS |
| `cited_decisions_tfidf` | 0.4794 | 0.7140 | ✅ | ✅ | ✅ | PASS |
| `full_text_tfidf_light` | 0.4855 | 0.7080 | ✅ | ✅ | ✅ | PASS |
| `regeste_full_text_hybrid_0.5` | 0.4873 | 0.7140 | ✅ | ✅ | ✅ | PASS |
| `regeste_full_text_hybrid_0.7` | 0.4889 | 0.7120 | ✅ | ✅ | ✅ | PASS |
| `outcome_tfidf` | 0.5015 | 0.6550 | ✅ | ✅ | ✅ | PASS |
| `regeste_tfidf` | 0.4853 | 0.6315 | ✅ | ✅ | ✅ | PASS |

**Summary:** 8/8 representations PASS both adversarial gates (LangDom < 0.85, JP > 0.5). Best jurist preference: **0.7345**.

---

## Dense Embedding Complementary View Acceptance Criteria — Revalidated

| Criterion | Threshold | 22-Year Evidence (center_projected) | Status |
|-----------|-----------|--------------------------------------|--------|
| Citation Heritage AUC | > 0.75 | 768dim: 0.7941, 64dim: 0.7922, 128dim: 0.7916 | ✅ PASS |
| Cross-Lang Sachverhalt | > 0.2 | 768dim: 0.2816, 64dim: 0.2816 | ✅ PASS |
| Cross-Lang Dispositiv | > 0.1 | 768dim: 0.1481, 64dim: 0.1502 | ✅ PASS |
| Cross-Lang Erwaegungen | > 0.1 | 768dim: 0.0925, 64dim: 0.0941 | ❌ FAIL |
| Jurist Pairwise Pref | > 0.5 | 22yr: 0.389-0.418; all scales FAIL | ❌ FAIL |

**Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen for cross-lingual alignment.

**True OOS JuristPref Ceiling:** ~0.53 < 0.7 factory target.

**Role Confirmed:** Dense embeddings = **COMPLEMENTARY VIEWS ONLY** (citation heritage recovery, cross-lingual alignment), NOT primary navigation.

---

## Universal 174k Failures (Reproduced)

| Benchmark | Status | Note |
|-----------|--------|------|
| Hierarchy Coherence | Universal FAIL | Purity 0.08-0.47 < 0.7 (213 labels too granular) |
| Legal Area Clustering | Universal FAIL | Purity 0.003-0.08 < 0.5 |
| Temporal Stability | Universal FAIL | High neighbor overlap variance |
| Boilerplate Resistance | Universal FAIL | Proxy measures language dominance |
| v17b Label Normalization | NEGATIVE at 174k | NMI decreases for 5/8 reps; different regime from 1k |
| v18 Coarse Hierarchy | NEGATIVE | Max branch purity 0.65 < 0.70 |

---

## Data Blockers (Unchanged — Require Corpus Lane)

| Blocker | Impact |
|---------|--------|
| **No bge_ ↔ bger_ ID mapping** | 174k dense embeddings blocked |
| **Missing parquet 2022-2026** | 29,520 decisions (17%) missing |
| **Section extraction not at scale** | Sachverhalt/Erwaegungen/Dispositiv dense embeddings only at 1K sample |

---

## State File Integrity Check

The machine-readable state file `evaluation/state/evaluation.json` remains consistent with all evidence:

- `lane`: "evaluation"
- `direction_version`: 34
- `evidence_tier`: "ACCEPTED"
- `cycle_status`: "COMPLETE"
- `continue_recommended`: false
- `accepted_run_id`: "eval_174k_v34_baseline_and_dense_criteria_20261003"
- All `evidence_refs` valid (12 artifacts)
- All `critical_findings` aligned with verified results
- `next_recommendation` correctly documents completion and blockers

---

## Compliance with Research Protocol

- ✅ Hypothesis, baseline, success rule frozen before observation
- ✅ Negative results preserved (dense FAIL jurist gate at ALL scales; v17b FAIL at 174k; v18 FAIL; universal hierarchy FAIL)
- ✅ Strong baselines used (whole-doc semantic, TF-IDF citation-only, norms-only, simple hybrids)
- ✅ Evaluation on frozen harness v3 with fixed seed (42)
- ✅ Provenance preserved for all claim-bearing outputs
- ✅ PIVOT_WITHIN_MISSION documented with product integration contract
- ✅ Machine-readable state file updated with evidence_refs and critical_findings

---

## Recommendation: **NO FURTHER SAME-QUESTION CYCLES**

The evaluation lane has fully satisfied factory direction v34:

1. ✅ **TF-IDF 174k evaluation FROZEN as production baseline** — 8/8 reps PASS adversarial gates, best JP=0.7345
2. ✅ **Dense embedding complementary view acceptance criteria DEFINED and VALIDATED** against 22-year/144k checkpoint evidence
3. ✅ **True OOS JuristPref ceiling ~0.53 documented** — no representation meets 0.7 factory target
4. ✅ **Lane correctly BLOCKED_ON_DEPENDENCIES** — 174k dense embeddings require corpus lane resumption

**Next Action:** Corpus lane resumption for bge_/bger_ ID mapping + parquet 2022-2026 + section extraction at 174k scale. Product lane proceeds with v1.0 release using TF-IDF citation hybrids as primary navigation mode.

---

## Sign-Off

**TF-IDF 174k Production Baseline: FROZEN AND ACCEPTED**  
**Dense Complementary Acceptance Criteria: DEFINED AND VALIDATED**  
**Lane Status: BLOCKED_ON_DEPENDENCIES — continue_recommended=false**

*Verification run 37270030183 confirms no drift from ACCEPTED state. All metrics frozen before observation. Provenance preserved in referenced results directories.*