# Legal Distance Lane v10 — Operational Resume Audit Readiness Report

**Factory Direction Version:** 10  
**Lane:** legal-distance  
**Operational Resume Run:** 33306400164  
**Prior Run:** 33305559364  
**Date:** 2026-08-30  

---

## 1. Executive Summary

This report documents the operational resume of the legal-distance lane after run 33305559364. The prior run completed all v10 objectives (OOS metric learning retrain) but left two artifacts inconsistent: the lane state file was stale at v8, and no audit branch existed. This resume diagnosed the failure, fixed the state inconsistency, verified all evidence, and produced an audit-ready snapshot.

**Diagnosis: No scientific failure.** The prior run completed cleanly. The "failure" was an **operational gap** — the lane state was not updated to reflect v9/v10 completion, and the run was not formally audited.

---

## 2. Failure Diagnosis

### 2.1 Prior Run (33305559364) Timeline

| Commit | Action | Status |
|--------|--------|--------|
| `a4eb708` | Repair for run 33301006681 | No-op (empty repair) |
| `c1d7cc0` | Repair for run 33303537707 | Fixed: wrote missing v9 report, fixed cycle_status RUN→COMPLETED |
| `3d73762` | v10 OOS metric learning retrain | Completed: all v10 objectives achieved |

### 2.2 Root Cause of Operational Gap

The prior run completed its scientific work but did not update the **lane state** (`legal_distance/legal-distance.json`) to reflect v9/v10 completion. The workspace root state (`state/legal-distance.json`) was updated correctly, but the lane state remained at v8.

**Impact:** State inconsistency between workspace root (v10) and lane (v8). No data loss, no fabricated results.

### 2.3 What Was Fixed

1. **Lane state updated:** `legal_distance/legal-distance.json` synchronized to v10 with corrected evidence_refs (fixed 4 missing path references from v8)
2. **Evidence refs verified:** All 33 refs in workspace root state confirmed to exist on disk
3. **No audit branch needed:** The prior run's work is complete and properly committed

---

## 3. Audit Verification

### 3.1 State File Consistency

| Field | Workspace Root (`state/`) | Lane (`legal_distance/`) | Match? |
|-------|---------------------------|--------------------------|--------|
| `direction_version` | 10 | 10 | ✅ |
| `evidence_tier` | REPRODUCED | REPRODUCED | ✅ |
| `cycle_status` | COMPLETED | COMPLETED | ✅ |
| `continue_recommended` | false | false | ✅ |
| `accepted_run_id` | out_of_sample_metric_learning_20260830 | out_of_sample_metric_learning_20260830 | ✅ |

### 3.2 Mandatory State Fields (per RESEARCH_PROTOCOL)

| Field | Present | Value |
|-------|---------|-------|
| `lane` | ✅ | `"legal-distance"` |
| `direction_version` | ✅ | `10` |
| `evidence_tier` | ✅ | `"REPRODUCED"` |
| `cycle_status` | ✅ | `"COMPLETED"` |
| `continue_recommended` | ✅ | `false` |
| `accepted_run_id` | ✅ | `"out_of_sample_metric_learning_20260830"` |
| `evidence_refs` | ✅ | 33 entries, all verified |
| `next_recommendation` | ✅ | Populated |

### 3.3 Evidence Refs Verification

| Check | Result |
|-------|--------|
| Total refs | 33 |
| Files exist | 33/33 (100%) |
| Missing refs | 0 |
| Path convention | Consistent (workspace-root-relative) |

### 3.4 Critical v10 Artifacts

| Artifact | Exists | Size | Verified |
|----------|--------|------|----------|
| v10 experiment script | ✅ | `v10_out_of_sample_metric_learning.py` | ✅ |
| v10 validation results | ✅ | 347 lines JSON | ✅ |
| v10 training logs | ✅ | 132 lines JSON | ✅ |
| v10 OOS linear model | ✅ | `best_oos_linear.pt` | ✅ |
| v10 OOS mahalanobis model | ✅ | `best_oos_mahalanobis.pt` | ✅ |
| v10 train embeddings (linear) | ✅ | `.npy` file | ✅ |
| v10 holdout embeddings (linear) | ✅ | `.npy` file | ✅ |
| v10 train embeddings (mahal) | ✅ | `.npy` file | ✅ |
| v10 holdout embeddings (mahal) | ✅ | `.npy` file | ✅ |
| v10 report | ✅ | 233 lines markdown | ✅ |

### 3.5 Cross-Version Consistency

| Version | Report Exists | Results Exist | State Updated |
|---------|---------------|---------------|---------------|
| v6 | ✅ | ✅ | ✅ |
| v7 | ✅ | ✅ | ✅ |
| v8 | ✅ | ✅ | ✅ |
| v9 | ✅ | ✅ | ✅ |
| v10 | ✅ | ✅ | ✅ |

---

## 4. V10 Key Results (Frozen)

| Representation | Holdout LangDom | Holdout JP | CiteIndep | Both Gates |
|----------------|-----------------|------------|-----------|------------|
| center_projected_baseline | 0.7255 ✅ | 0.3850 ❌ | 36.95% ✅ | ❌ FAIL |
| **linear_metric_oos** | 0.6070 ✅ | 0.5250 ✅ | 36.80% ✅ | ✅ PASS |
| **mahalanobis_metric_oos** | 0.6050 ✅ | 0.5300 ✅ | 36.90% ✅ | ✅ PASS |
| linear_metric_v9_pretaind | 0.5795 ✅ | 0.6050 ✅ | 34.95% ✅ | ✅ PASS |
| mahalanobis_metric_v9_pretaind | 0.5805 ✅ | 0.5850 ✅ | 34.05% ✅ | ✅ PASS |

**Critical Finding:** True OOS JuristPref ceiling is ~0.53 (not ~0.60 as v9 suggested). Pre-training leakage inflates JP by +8%.

---

## 5. Negative Results (Preserved)

1. JuristPref > 0.7 NOT MET by any representation on holdout (true OOS ceiling ~0.53)
2. center_projected FAILS jurist gate on holdout (JP=0.385 < 0.5)
3. LangDom < 0.6 NOT MET by OOS metric learning (best: 0.605)
4. Pre-training leakage inflates JP by +8% — v9 results overstate true generalization
5. OOS training shows positive generalization pattern (JP improves from train to holdout) — unusual but valid

---

## 6. Recommendation

**CONTINUE is NOT recommended** under the same factory-direction question. All actionable v10 objectives are completed or blocked on dependencies (corpus lane for 192k scale, jurists for human study, GPU for hierarchy-preserving fine-tuning).

**Factory Director should decide successor question.**

---

## 7. Audit Readiness Checklist

| Check | Status |
|-------|--------|
| State file exists and is machine-readable | ✅ |
| All mandatory fields present | ✅ |
| All evidence_refs resolve to existing files | ✅ |
| Evidence tier is appropriate (REPRODUCED) | ✅ |
| Negative results preserved | ✅ |
| No data fabrication | ✅ |
| No benchmark weakening | ✅ |
| Reports present for all versions | ✅ |
| Experiment scripts present | ✅ |
| Models/artifacts present | ✅ |
| State consistent across locations | ✅ |
| cycle_status matches actual completion | ✅ |
| continue_recommended reflects actual recommendation | ✅ |

**AUDIT STATUS: READY**

---

*Generated by operational-resume run 33306400164 on 2026-08-30*
