# Fractal Map Lane — Final Verification Run 37748849374

**Factory Direction:** v35
**Lane:** fractal-map
**Run ID:** 37748849374
**Timestamp:** 2026-10-08
**Status:** VERIFIED AND AUDIT-READY
**Resume from:** Persisted producer snapshot of run 37747143739

---

## Executive Summary

This run performs an **operational resume from persisted producer snapshot of run 37747143739** with full independent re-verification. All **246 tests pass (1 skipped)**, confirming the fractal-map lane deliverable is **complete, verified, and audit-ready**. The lane correctly remains `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings, which require corpus lane resumption for BGE/bger ID mapping and parquet 2022-2026 generation.

**No orchestration/validation failure exists in the fractal-map lane.** The discrepancy between workspace state (correct: `BLOCKED_ON_DEPENDENCIES`) and mounted control plane (stale: `RUN`) is a **persistent infrastructure defect in the control plane mounting mechanism**, not a lane failure.

---

## Verification Results

### Test Suite Execution

| Test Suite | Total | Passed | Skipped | Status |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 186 | 0 | ✅ PASS |
| test_pipeline_readiness.py | 14 | 14 | 0 | ✅ PASS |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | ✅ PASS |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | ✅ PASS |
| test_scale_dependency.py | 11 | 11 | 0 | ✅ PASS |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | ✅ PASS |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | ✅ PASS |
| **Grand Total** | **247** | **246** | **1** | ✅ **ALL PASS** |

---

## Key Verification Points Confirmed

### 1. TF-IDF Hierarchical Production Modes OPERATIONAL at 174k
- **3 production modes at full 173,963 decisions:**
  - `full_text_tfidf_light` — fine branch purity: **0.930**
  - `regeste_full_text_hybrid_0.5` — fine branch purity: **0.906**
  - `regeste_full_text_hybrid_0.7` — fine branch purity: **0.914**
- 16/16 scale simulation tests PASS
- WebGL pipeline <3s

### 2. Multi-level Recursive Protocol (4+ levels) FAILS at 174k — Valid Negative Result Preserved
- All 5 TF-IDF modes fail on level2 area_purity threshold (~0.134 < 0.15)
- Not cluster collapse at all levels — Level 0 has single cluster, Levels 1-3 have multiple clusters
- Correctly recorded as ACCEPTED NEGATIVE evidence

### 3. Calibration FAILS on TF-IDF — Valid Negative Result Preserved
- Thresholds too aggressive for TF-IDF signal density
- Correctly recorded as ACCEPTED NEGATIVE evidence

### 4. Dense Embedding Integration Contract v34 FROZEN
| Complementary View | Acceptance Criterion | Evidence Status |
|-------------------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | PASSED at 144k (0.79-0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | PASSED at 1K/144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | PASSED at 1K/144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | FAILED (0.09) — correctly excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | PASSED (JP 0.61-0.67) but BELOW TF-IDF baseline (0.78-0.79) |

### 5. Preparatory 12k/144k Dense Validation COMPLETE
- 12k: Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation)
- 12k: Hierarchical builder SUCCESS (39 coarse → 412 fine)
- 144k checkpoint validates hierarchical builder scale extrapolation

### 6. NESTING_METRIC_DEFECT_v1 Enforced
- 7 compressed-family modes had nesting_score ≥ 0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs

### 7. Scale Extrapolation Validated
- 144k checkpoint (22/26 years, 2000–2021): fine_branch_purity ~0.97
- Improvement rate: 0.48–0.65 (branch) / 0.75–0.76 (area)
- Strict nesting: **≥0.99**
- Fine singletons: **~4–5%**
- Note: Metrics describe hierarchical builder (2-level), NOT multi-level recursive protocol

---

## Critical Findings (from state/fractal-map.json)

| Finding | Status | Detail |
|---------|--------|--------|
| tfidf_hierarchical_v1_6_of_8_pass | ✅ ACCEPTED | Text-based: 0.906–0.930 purity; Citation-based at 52%: 0.609–0.685 |
| multi_level_recursive_protocol_fails_174k | ✅ ACCEPTED NEGATIVE | Level2 area_purity ~0.134 < 0.15 threshold |
| calibration_fails_tfidf | ✅ ACCEPTED NEGATIVE | Thresholds too aggressive |
| dense_integration_contract_frozen | ✅ ACCEPTED | 4 complementary views with acceptance criteria |
| scale_extrapolation_validated | ✅ ACCEPTED | 144k hierarchical builder metrics healthy |
| nesting_metric_defect_enforced | ✅ ACCEPTED | Scope annotation required for nesting ≥ 0.99 |
| blocker_upstream_data | ✅ DOCUMENTED | Legal-distance 174k dense embeddings require corpus lane resumption |

---

## Orchestration/Validation Failure Diagnosis

### The Discrepancy

| Source | Fractal-Map Status | Correct? |
|--------|-------------------|----------|
| Workspace `state/factory_direction.json` (line 16) | `BLOCKED_ON_DEPENDENCIES` | ✅ YES |
| Workspace `state/fractal-map.json` (line 5) | `BLOCKED_ON_DEPENDENCIES` | ✅ YES |
| Mounted `/tmp/lex_control/state/factory_direction.json` (line 16) | `RUN` | ❌ NO — STALE |

### Root Cause

Persistent V28-pattern control plane mounting defect: the `/tmp/lex_control` mount does not reflect the latest `main` branch state. This is an **infrastructure defect in the control plane mounting/persistence mechanism**, NOT a fractal-map lane failure.

### Evidence History

This defect has been documented and reconfirmed across 15+ independent verification runs (37584654730 through 37747143739). Every fresh verification confirms:
- Lane correctly self-diagnosed and self-blocked
- All discriminating experiments for v34/v35 question COMPLETE
- No further same-question cycles justified (`continue_recommended=false`)

---

## Lane Deliverable Completeness

### Factory Direction v35 Question
> "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

### Deliverables — ALL COMPLETE

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| TF-IDF hierarchical_v1 protocol (3 text-based modes at full 173,963) | ✅ ACCEPTED | `hierarchical_v1_174k_tfidf/` results, 15x CI verified |
| TF-IDF hierarchical_v1 protocol (3 citation-based modes at 52% scale) | ✅ ACCEPTED | `hierarchical_v1_174k_tfidf/` results |
| Multi-level recursive protocol validation (4 TF-IDF modes at 174k) | ✅ ACCEPTED NEGATIVE | `multi_level_protocol_174k_tfidf/` — structurally validated, protocol FAILS |
| Calibration validation on TF-IDF | ✅ ACCEPTED NEGATIVE | `multi_level_protocol_174k_tfidf_calibrated/` — FAILS |
| Preparatory 12k dense validation | ✅ ACCEPTED | `dense_12k_prep_validation/` — multi-level PASS, builder SUCCESS |
| 144k checkpoint scale extrapolation | ✅ ACCEPTED | `144k_multi_level_validation/` — builder extrapolation validated |
| Dense embedding integration contract v34 | ✅ FROZEN | `dense_embeddings_integration_contract_v34.json` |
| NESTING_METRIC_DEFECT_v1 audit | ✅ ENFORCED | `nesting_metric_defect_v1_audit.json` |
| Product readiness confirmation | ✅ ACCEPTED | 3 production modes, 16/16 scale tests PASS, WebGL <3s |

---

## Blocker Status

**Blocked on:** Legal-distance 174k dense embeddings (requires corpus lane resumption)

**Corpus lane resumption criteria (per factory_direction.json v35):**
1. BGE/bger ID mapping production (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. Parquet generation for years 2022–2026 (29,520 decisions missing)
3. Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

**No fractal-map lane defect exists.** The lane has completed all work within its scope and correctly awaits upstream delivery.

---

## Recommendation

**No further same-question cycles justified.** The fractal-map lane has fully answered the factory direction v35 question. `continue_recommended=false` is correct and final.

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping, 2022–2026 parquet generation, and section extraction at 174k scale.

---

## Audit Readiness Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Provenance preserved | ✅ | All result files referenced in state/fractal-map.json |
| Negative results preserved | ✅ | Multi-level protocol FAIL, calibration FAIL, v26 flat zoom FAIL |
| Frozen benchmarks unchanged | ✅ | v26 frozen spec referenced, v34 contract frozen |
| Evidence tiers accurate | ✅ | ACCEPTED for TF-IDF production; EXPLORATORY for 12k/144k dense |
| Blockers documented | ✅ | 5 specific dependencies in state |
| Next steps unambiguous | ✅ | Await legal-distance 174k dense embeddings via corpus resumption |
| No fabricated data | ✅ | All results from actual computation |
| No overwritten claim-bearing outputs | ✅ | All historical results preserved in results/ |
| Test suite passes | ✅ | 246/247 tests pass (1 skipped for missing optional deps) |

---

## State File Status

The state file at `state/fractal-map.json` is **accurate and complete**. This verification run (37748849374) independently reconfirms all findings from previous verification runs (37741035034, 37734562417, 37729186215, etc.).

**No state file changes required** — the existing state is correct and audit-ready. A new verification entry has been appended to the state file.

---

## Sign-off

**Verification:** PASS (246/247 tests pass)
**Lane Status:** BLOCKED_ON_DEPENDENCIES (correct)
**Evidence Tier:** ACCEPTED
**Continue Recommended:** false
**Audit Ready:** true

**Next Action:** Factory Director to resume corpus lane per factory_direction.json v35 criteria.