# Evaluation Lane — Operational Resume Audit-Ready Snapshot (Factory Direction v10)

**GitHub Run:** 33321946599 (operational resume of producer snapshot 33321754632)
**Factory Direction Version:** 10
**Lane:** evaluation
**Evidence Tier:** ACCEPTED
**Cycle Status:** COMPLETED
**Continue Recommended:** false
**Next Recommendation:** BLOCKED_ON_DEPENDENCIES
**Date:** 2026-08-30
**Config Hash:** 4323f833fa72366a (frozen harness v3)
**Global Seed:** 42
**Repaired Producer Run:** 33321754632 (repair round 1)
**Previous Audit Run:** 33321015564 (PASS with 2 repairs)
**Last Audit-PASS Accepted Base:** 48b6bb9 (accept evaluation cycle 33321015564)

---

## Executive Summary

This operational resume verifies the evaluation lane snapshot is **audit-ready** following
the repair of run 33321015564 (which itself PASSED audit with 2 repairs). The prior
producer run (33321754632) applied those repairs and committed them. This run performs
independent verification of the complete snapshot state.

**Orchestration/validation failure diagnosed (from prior workflow 33317695932):** The
producer repair (33317312045) applied both REVISE fixes (F-1, F-2) but the producer branch
did **not** carry the independent auditor's output into its tree. Those artifacts lived
only on the audit branch. A snapshot missing its own audit evidence is not audit-ready.
This was resolved in operational resume 33317695932 by restoring audit artifacts verbatim.

**Current verification:** All 20 evaluation regression tests PASS. Frozen harness v3 config
intact. 59 of 60 evidence_refs present (1 missing report from legal-distance lane —
known dependency, not blocking). State file updated to reflect current run. Snapshot is
AUDIT_READY_VERIFIED.

---

## Orchestration/Validation Failure Diagnosis (Prior Workflow)

| Item | Result |
|------|--------|
| Repaired run | 33317312045 ("evaluation cycle 33317312045 repair 1", commit 79488b3) |
| Audit run (REVISE) | 33317001204 (commit 5020f02) |
| F-1 (HIGH): self-audit gate | **VERIFIED DELETED** (absent from tree) |
| F-2 (LOW): unauthorized factory-direction objective | **VERIFIED REMOVED** from key_findings |
| Independent audit artifacts in producer tree | **RESTORED** in operational resume 33317695932 |
| Failure mode | Producer repair fixed code-level defects but did not re-integrate independent audit evidence |
| Resolution | Audit evidence restored verbatim; re-verified fixes, tests, and evidence |
| Current status | **RESOLVED** — snapshot is audit-ready |

---

## Regression Test Verification

| Test | Status |
|------|--------|
| `test_anti_noise_procedural_sensitivity.py::test_shallow_reproduction` | ✅ PASS |
| `test_anti_noise_procedural_sensitivity.py::test_procedural_specific_excess_below_threshold` | ✅ PASS |
| `test_anti_noise_procedural_sensitivity.py::test_control_present` | ✅ PASS |
| `test_boilerplate_resistance_real.py::test_boilerplate_resistance` | ✅ PASS |
| `test_cross_lingual_alignment_v10.py::test_cross_lingual_findings` | ✅ PASS |
| `test_frozen_harness_v3_reproducibility.py::test_frozen_harness_reproducibility` | ✅ PASS |
| `test_product_integration_v11.py::test_product_integration_verification_results_exist` | ✅ PASS |
| `test_product_integration_v11.py::test_best_production_hybrids_identified` | ✅ PASS |
| `test_product_integration_v11.py::test_adversarial_gate_summary` | ✅ PASS |
| `test_product_integration_v11.py::test_all_3_regression_tests_pass` | ✅ PASS |
| `test_product_integration_v11.py::test_known_failures_correctly_excluded` | ✅ PASS |
| `test_v11_cross_validation.py::test_results_file_exists` | ✅ PASS |
| `test_v11_cross_validation.py::test_hierarchy_arm_passes_adversarial_gates` | ✅ PASS |
| `test_v11_cross_validation.py::test_nohierarchy_arm_passes_adversarial_gates` | ✅ PASS |
| `test_v11_cross_validation.py::test_hierarchy_loss_effect_is_positive` | ✅ PASS |
| `test_v11_cross_validation.py::test_hierarchy_loss_effect_is_small` | ✅ PASS |
| `test_v11_cross_validation.py::test_v11_beats_center_projected_baseline` | ✅ PASS |
| `test_v11_cross_validation.py::test_v11_jurivoc_alignment` | ✅ PASS |
| `test_v11_cross_validation.py::test_both_arms_generate_embeddings` | ✅ PASS |
| `test_v11_cross_validation.py::test_verdict_summary` | ✅ PASS |

**Result: 20/20 tests PASS**

---

## Evidence Refs Verification

| Category | Count | Status |
|----------|-------|--------|
| Total evidence_refs | 60 | — |
| Present in workspace | 52 | ✅ |
| Present in accepted lanes | 7 | ✅ (via /tmp/lex_accepted) |
| Missing | 1 | ⚠️ (non-blocking) |

**Missing artifact:** `reports/legal-distance/v7_citation_role_embeddings_report.md`
- This is a legal-distance lane report referenced in evaluation state
- Not present in workspace or accepted lanes
- **Impact:** Non-blocking — the underlying data (citation_roles_resolved.json, resolution_stats.json) and experiment script are present
- **Recommendation:** Legal-distance lane should produce this report in next cycle

---

## Frozen Harness v3 Integrity

| Check | Result |
|-------|--------|
| Config file exists | ✅ `evaluation/config/evaluation_v3_config.json` |
| Config unchanged since last commit | ✅ (git diff empty) |
| Global seed | 42 (matches state) |
| Adversarial thresholds | lang_dom=0.85, jurist=0.5, cross_lang=0.2, cluster_coherence=0.7 |
| Benchmark parameters | k_lang=20, k_jurist=10, k_cross_lang=10, n_clusters=16 |
| Regeneration instructions | Documented in config |

---

## Current State Summary

### Completed Objectives (4/6)

1. **Citation role modeling evaluation** — 2,988 annotations, 8/9 role hybrids PASS adversarial gates
2. **Legal embeddings fine-tuning evaluation** — multilingual_e5_small_pretrained tested, BEST adversarial scores but catastrophic hierarchy collapse
3. **Cross-lingual alignment deeper investigation** — 52 representations tested, proc_pairs LOSSLESS for cited_decisions_tfidf
4. **User corpus import evaluation** — 45/45 tests PASS

### Blocked Objectives (2/6)

1. **Full corpus scale evaluation (192k)** — pending corpus lane OpenCaseLaw bulk ingestion
2. **Jurist human study** — framework ready, needs 5-10 Swiss jurists

### Key Findings (Preserved as First-Class Evidence)

- 26 representations evaluated across 4 design patterns
- BEST PRODUCTION: cited_decisions_tfidf_outcome_hybrid_0.7 (JP=0.7898, LangDom=0.4922)
- BEST FRACTAL: cited_decisions_tfidf_outcome_hybrid_0.7 (HierAdv=+0.3703)
- BEST CROSS-LINGUAL: cited_decisions_tfidf_proc_pairs (LOSSLESS)
- Boilerplate resistance: CONCLUDED NOT a systemic issue (procedural passages NOT driving neighbors)
- Anti-noise procedural sensitivity: CONCLUDED NEGATIVE (conclusion robust)
- v11 OOS cross-validation: Both arms PASS adversarial gates, hierarchy loss NOT load-bearing
- Holdout cross-validation: DISCREPANT_EXPLAINED (metric definition mismatch)

### Negative Results (Preserved)

- center_projected_768 FAILS jurist pairwise (0.4912 < 0.5)
- criticizing_alpha0.7 FAILS jurist pairwise (0.4979 < 0.5)
- multilingual_e5_small_pretrained: catastrophic hierarchy collapse despite best adversarial scores
- Outcome-only embeddings overfit (Jurivoc L0≈0.007, scale=0.0)
- single Procrustes CATASTROPHIC (jurist=0.361)
- Section-specific embeddings BLOCKED on corpus lane

---

## Lane Recommendation

**BLOCKED_ON_DEPENDENCIES** — Evaluation lane has completed all work possible without
the full 192k corpus. No additional same-question cycles are justified under factory
direction v10. When corpus lane delivers:

1. Full corpus adversarial evaluation at 192k scale
2. multilingual-e5-small fine-tuned evaluation with hierarchy loss (GPU)
3. Jurist human study execution
4. Section-specific cross-lingual evaluation (needs sachverhalt/erwaegungen/dispositiv)

---

## Artifact Inventory

| Artifact | Action | Status |
|----------|--------|--------|
| `evaluation/state/evaluation.json` | UPDATED | github_run, previous_audit_run, timestamp, operational_resume_run, accepted_run_id |
| `reports/evaluation/evaluation_v10_operational_resume_33321946599_audit_ready.md` | CREATED | This report |
| All test files | UNCHANGED | 20/20 PASS |
| All result JSON files | UNCHANGED | Evidence intact |
| All frozen benchmarks | UNCHANGED | Integrity preserved |
| All negative results | PRESERVED | First-class evidence |

---

## Verification Checklist

| Check | Result |
|-------|--------|
| All regression tests pass | ✅ 20/20 |
| Frozen harness config intact | ✅ |
| Evidence refs verified | ✅ 59/60 (1 non-blocking) |
| State file updated | ✅ |
| No frozen baselines weakened | ✅ |
| No negative results deleted | ✅ |
| No benchmark gaming | ✅ |
| No prettiness-as-quality | ✅ |
| Provenance chain clean | ✅ |
| Audit trail complete | ✅ |
| Lane recommendation sound | ✅ BLOCKED_ON_DEPENDENCIES |

---

*End of Audit-Ready Snapshot — Evaluation 33321946599*
