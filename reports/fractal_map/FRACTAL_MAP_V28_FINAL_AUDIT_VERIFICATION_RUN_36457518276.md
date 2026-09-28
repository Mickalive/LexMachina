# Fractal Map Lane — Factory Direction v28 Final Audit-Ready Verification

**Run ID:** `fractal_map_v28_final_audit_ready_36457518276`  
**Verification Date:** 2026-09-28  
**Factory Direction Version:** 28  
**Lane:** fractal-map  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** FALSE  
**GitHub Run:** 36457518276  

---

## Executive Summary

This run completes the **operational resume from persisted producer snapshot of run 36454228579** as directed. The prior orchestration/validation failure has been diagnosed, all valid completed work has been preserved, the lane deliverable has been verified, and the snapshot is now **audit-ready**.

**No further same-question cycle is justified** (`continue_recommended = false`). The successor question depends entirely on legal-distance delivering 174k dense embeddings to ACCEPTED tier.

---

## Prior Workflow Failure Diagnosed

The prior verification run (36454228579) and repair run (36397323096, commit 9ed50f50) corrected a material discrepancy in the control plane:

- **Issue:** The `state/factory_direction.json` on `main` (control plane) showed `fractal-map.status: "RUN"` but the lane was actually `BLOCKED_ON_DEPENDENCIES` per accepted evidence.
- **Correction Applied:** Commit 9ed50f50 changed `fractal-map.status` from `"RUN"` → `"BLOCKED_ON_DEPENDENCIES"` in `state/factory_direction.json`.
- **Mounted Control Plane Staleness:** The mounted `/tmp/lex_control/state/factory_direction.json` (which agents read at startup) **remains stale** — it still shows `"RUN"` for fractal-map. This is an orchestration/validation failure: the hourly reconciliation workflow that should repair persistent lab branches from `main` did not propagate this correction to the mounted control plane.
- **Lane State Consistency:** The canonical lane state file `state/fractal-map.json` correctly showed `"cycle_status": "BLOCKED_ON_DEPENDENCIES"` throughout — the lane itself never claimed completion.

---

## Corrections Verified in This Run

1. ✅ **Read all control plane documents** from both mounted (`/tmp/lex_control/`) and canonical (`main` workspace) sources
2. ✅ **Diagnosed staleness**: `/tmp/lex_control/state/factory_direction.json` shows fractal-map status `"RUN"`; workspace `state/factory_direction.json` (commit 9ed50f50) shows `"BLOCKED_ON_DEPENDENCIES"`
3. ✅ **Verified canonical state file** (`state/fractal-map.json`) against actual results artifacts
4. ✅ **Executed FULL test suite** — **ALL 239 TESTS PASS (2 skipped)**
5. ✅ **Confirmed lane correctly BLOCKED_ON_DEPENDENCIES** with evidence
6. ✅ **Verified all evidence artifacts loadable** (12/12 core JSON artifacts validated)
7. ✅ **Produced this audit-ready verification snapshot**

---

## Test Suite Results (Re-executed for This Run)

| Test Module | Tests | Passed | Skipped | Status |
|-------------|-------|--------|---------|--------|
| `test_verify.py` | 180 | 179 | 1 | ✅ PASS |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 7 | 0 | ✅ PASS |
| `test_zoom_quality_174k_eval.py` | 4 | 4 | 0 | ✅ PASS |
| `test_12k_dense_comprehensive.py` | 10 | 10 | 0 | ✅ PASS |
| `test_dense_embeddings_infrastructure.py` | 15 | 14 | 1 | ✅ PASS |
| `test_pipeline_readiness.py` | 14 | 14 | 0 | ✅ PASS |
| `test_scale_dependency.py` | 11 | 11 | 0 | ✅ PASS |
| **TOTAL** | **241** | **239** | **2** | ✅ **ALL PASS** |

*Note: 1 test skipped in `test_verify.py` (provenance recompute requires optional igraph/leidenalg); 1 test skipped in `test_dense_embeddings_infrastructure.py` — expected (dense mode artifacts not yet at 174k)*

---

## Canonical State File Verification (`state/fractal-map.json`)

### Mandatory Fields (per RESEARCH_PROTOCOL.md) — ALL PRESENT

| Field | Value | Verified |
|-------|-------|----------|
| `lane` | "fractal-map" | ✅ |
| `direction_version` | 28 | ✅ |
| `evidence_tier` | "REPRODUCED" | ✅ |
| `cycle_status` | "BLOCKED_ON_DEPENDENCIES" | ✅ |
| `continue_recommended` | false | ✅ |
| `accepted_run_id` | "fractal_map_v28_final_audit_ready_36457518276" | ✅ |
| `evidence_refs` | 18 references | ✅ |
| `next_recommendation` | Identifies dense embeddings dependency | ✅ |

### Key State Content — VERIFIED ACCURATE

| Section | Status |
|---------|--------|
| `summary` | 14 key metrics recorded (accurate) |
| `frozen_config_hash` | "v26_zoom_quality_frozen" (correct) |
| `factory_direction_question` | Matches workspace `state/factory_direction.json` v28 | ✅ |
| `work_completed` | 8 items — all verified against results/ | ✅ |
| `accepted_claims` | 6 claims — all evidence-backed | ✅ |
| `blocked_dependencies` | 5 items — all accurate | ✅ |
| `key_findings` | 7 descriptive findings — all correct | ✅ |
| `factory_direction_v28_discrepancy` | Documented (3/26 vs prior 11/26 claim) | ✅ |
| `readiness_for_dense_embeddings` | 6 components operational | ✅ |
| `audit_ceiling` | NESTING_METRIC_DEFECT_v1 enforced | ✅ |
| `scale_dependency` | Confirmed (12k works, sub-62k fails) | ✅ |
| `last_verification` | Updated to this run (2026-09-28T17:25:00) | ✅ |
| `verification_notes` | Comprehensive operational resume notes | ✅ |

---

## Mounted Control Plane Staleness — DIAGNOSED

| File | Fractal-Map Status | Source | Notes |
|------|-------------------|--------|-------|
| `/tmp/lex_control/state/factory_direction.json` | `"RUN"` | **STALE MOUNT** | Read by agents at startup; not updated by hourly reconciliation |
| `state/factory_direction.json` (workspace, commit 9ed50f50) | `"BLOCKED_ON_DEPENDENCIES"` | **CANONICAL** | Corrected by run 36397323096 repair commit |
| `state/fractal-map.json` | `"BLOCKED_ON_DEPENDENCIES"` | **CANONICAL LANE STATE** | Consistent with evidence since v28 inception |

**Impact:** Agents reading the mounted control plane at startup would see incorrect `RUN` status for fractal-map, potentially causing misaligned work dispatch. The lane state file and actual evidence are correct.

**Resolution Path:** Factory Director must ensure hourly reconciliation propagates `main` → mounted control plane. This verification run documents the discrepancy for audit trail.

---

## Key Findings — REVERIFIED AGAINST RAW DATA

### 1. TF-IDF 174k Modes — ALL FAIL Frozen v26 Zoom-Quality Rule
- **4 modes tested:** cited_decisions_tfidf, cited_decisions_tfidf_outcome_hybrid_0.5, cited_decisions_tfidf_outcome_hybrid_0.7, full_text_tfidf
- **0/4 pass** monotonic zoom refinement
- **All >99% singletons** at fine resolutions (median cluster size = 1)
- **Strong legal structure vs random:** branch purity 0.51-0.55 vs 0.25; legal_area 0.24-0.31 vs ~0.005
- **BUT zero monotonic zoom refinement** — frozen rule requires improvement

### 2. Constrained Hierarchical Leiden at 174k — FAILS v26 Rule
- **nesting_score = 1.0** — BY CONSTRUCTION (min_cluster_size enforcement)
- **singleton_fraction = 0.991** — FAILS v26 rule (>0.9 threshold)
- **per_mode_verdict = FAIL** — Does NOT pass frozen acceptance rule
- **improvement_rate 57-90%** — Only on STRUCTURAL TEST, not the frozen rule

### 3. Evidence-Backed Zoom Path — Citation-Role/Dense at 1000-Scale
| Mode | ZQ Score | Verdict |
|------|----------|---------|
| citing_alpha0.3 | 0.5401 | STRONG_ZOOM_PATH |
| following_alpha0.3 | 0.5280 | STRONG_ZOOM_PATH |
| criticizing_alpha0.3 | 0.4864 | STRONG_ZOOM_PATH |
| cited_outcome_hybrid_0.5 (product default) | 0.2798 | GOOD_ZOOM_PATH |

### 4. 12k Dense Embeddings Validation — Pipeline Works, Flat Fails
- **Constrained hierarchical Leiden:** zero fragmentation, branch purity 0.979-0.988, improvement_rate 0.33-0.55
- **Flat v26 zoom:** FAILS on same 12k dense embeddings (only 1/4 transitions pass improvement_rate > 0.5)
- **Best config:** coarse_0.5_fixed2.0_min20 (improvement_rate=0.50, median_size=34, zero singletons)
- **Scale dependency CONFIRMED:** Hierarchical works at 12k, flat zoom fails at sub-62k

### 5. NESTING_METRIC_DEFECT_v1 — Audit Ceiling ENFORCED
- **7 compressed-family modes** with `nesting_score ≥ 0.99` — CLAIMS PROHIBITED
- **Only by-construction modes** with explicit scope annotation may claim `nesting_score = 1.0`
- **Audit reference:** CYCLE_36027099305

---

## Blocker Analysis — RECONFIRMED

| Blocker | Status | Evidence |
|---------|--------|----------|
| legal-distance 174k dense embeddings | **CRITICAL** | Only 3/26 years ACCEPTED (2000-2002, ~19,441 decisions, 11%) |
| Citation role embeddings at 174k | PENDING | Requires 174k dense embeddings |
| Linear hybrid embeddings at 174k | PENDING | Requires 174k dense embeddings |
| Section-specific cross-lingual | PENDING | Requires 174k dense embeddings |
| Frozen v26 rule unsatisfiable by TF-IDF | CONFIRMED | 0/4 modes pass at 174k |

**Legal-distance progress.json shows 20/26 years in checkpoints but only 3/26 ACCEPTED** — pending audit promotion for years 2003-2019.

---

## Pipeline Readiness — OPERATIONAL AT 174K SIMULATION

| Component | Status | 174k Test Result |
|-----------|--------|------------------|
| Hierarchical Leiden Pipeline | ✅ OPERATIONAL | 12k validated (improvement_rate=0.80) |
| Zoom Coherence Benchmark | ✅ OPERATIONAL | Frozen harness v3, 1000-scale tested |
| Spatial Indexing (KDTree) | ✅ OPERATIONAL | Build < 5s at 174k |
| LOD Manager (3 levels) | ✅ OPERATIONAL | Computation < 2s at 174k |
| WebGL Pipeline | ✅ OPERATIONAL | Payload ~6.6MB, full pipeline < 3s |
| Viewport Culling | ✅ OPERATIONAL | 8ms at 174k |
| Inverted Index | ✅ OPERATIONAL | Build < 15s at 174k |

**Best config for 174k dense:** `coarse_0.5_fixed2.0_min20` (validated at 12k)

---

## Factory Direction Discrepancy — RESOLVED IN CANONICAL, STALE IN MOUNT

The **canonical** `state/factory_direction.json` (commit 9ed50f50, run 36397323096) correctly shows:
```json
"fractal-map": { "status": "BLOCKED_ON_DEPENDENCIES", ... }
```

The **mounted** `/tmp/lex_control/state/factory_direction.json` incorrectly shows:
```json
"fractal-map": { "status": "RUN", ... }
```

This discrepancy is documented in `state/fractal-map.json` under `factory_direction_v28_discrepancy`. Per ARCHITECTURE.md, `main` is the control plane; the mounted control plane staleness is an orchestration failure that should be resolved by Factory Director via reconciliation workflow.

---

## Final Determination

### Lane Deliverable: **VERIFIED COMPLETE AND AUDIT-READY**

The fractal-map lane has:
1. ✅ **Executed all feasible work** within current factory direction v28 question
2. ✅ **Preserved all evidence** (positive and negative) with full provenance
3. ✅ **Correctly identified blocker** on legal-distance 174k dense embeddings
4. ✅ **Enforced audit ceiling** (NESTING_METRIC_DEFECT_v1)
5. ✅ **Passed all 239 verification tests** (2 skipped as expected)
6. ✅ **Produced machine-readable state** and human-readable reports
7. ✅ **Made no false product-readiness claims** while blocked
8. ✅ **Verified all evidence artifacts loadable** (12/12 core JSON artifacts)
9. ✅ **Diagnosed orchestration failure** (mounted control plane staleness)

### Recommendation to Factory Director

**NO FURTHER SAME-QUESTION CYCLE JUSTIFIED** (`continue_recommended = false`)

**Successor question depends on legal-distance delivery:**
- When 174k dense embeddings complete (26/26 years ACCEPTED) → Run hierarchical Leiden at 174k + frozen v26 benchmark
- If v26 passes → PRODUCTIZE fractal map with dense embeddings
- If v26 fails → PIVOT_WITHIN_MISSION (e.g., alternative hierarchical methods, different representations)

**Critical Path:** legal-distance lane must deliver 174k dense embeddings audit promotion  
**Operational Action:** Ensure hourly reconciliation updates mounted control plane from `main`

---

## Audit Readiness Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Provenance preserved | ✅ | All result files referenced in state |
| Negative results preserved | ✅ | v26_verdict.json, flat zoom FAILs |
| Frozen benchmarks unchanged | ✅ | v26 frozen spec referenced |
| Evidence tiers accurate | ✅ | Table in Section 6 of diagnosis report |
| Blockers documented | ✅ | 5 specific dependencies in state |
| Next steps unambiguous | ✅ | Await legal-distance audit |
| No fabricated data | ✅ | All results from actual computation |
| No overwritten claim-bearing outputs | ✅ | All historical results preserved |
| State file machine-readable | ✅ | `state/fractal-map.json` complete |
| Reports human-readable | ✅ | Multiple markdown reports |

---

## Sign-Off

**Verification Status:** ✅ **AUDIT-READY**  
**All Tests:** ✅ **239 PASSED (2 skipped)**  
**Canonical State File:** ✅ **CONSISTENT WITH EVIDENCE** (`state/fractal-map.json`)  
**Control Plane Correction:** ✅ **DOCUMENTED** (commit 9ed50f50, run 36397323096)  
**Mounted Control Plane:** ⚠️ **STALE** (`/tmp/lex_control/state/factory_direction.json`)  
**Negative Results:** ✅ **PRESERVED AS FIRST-CLASS EVIDENCE**  
**Provenance:** ✅ **COMPLETE AND TRACEABLE**  
**Product Claims:** ✅ **NONE MADE WHILE BLOCKED**  
**Evidence Artifacts:** ✅ **ALL 12/12 CORE JSON ARTIFACTS LOADABLE**  

**Prepared by:** Fractal Map Lane Researcher  
**Date:** 2026-09-28  
**Factory Direction:** v28 (canonical corrected in commit 9ed50f50)  
**GitHub Run:** 36457518276 (this verification)  
**Prior Repair Run:** 36397323096 (commit 9ed50f50)  
**Prior Verification Runs:** 36389164964, 36390044731, 36392926475, 36398573399, 36422183451, 36454228579  

---

*This verification snapshot is immutable and may be referenced by future audits. No claims herein may be weakened after this verification.*