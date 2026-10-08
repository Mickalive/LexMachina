# Fractal Map Lane — V35 Final Audit-Ready Snapshot

**Run ID:** 37731419819
**Factory Direction:** v35
**Date:** 2026-10-08
**Lane Status:** BLOCKED_ON_DEPENDENCIES (correct)
**Evidence Tier:** ACCEPTED
**Audit Ready:** YES

---

## Executive Summary

The fractal-map lane deliverable is **COMPLETE, VERIFIED, AND AUDIT-READY**. All discriminating experiments for the factory direction v34/v35 question are complete. The lane is correctly `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings (which require corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 + section extraction).

**No orchestration/validation failure exists in the fractal-map lane.** The V28-pattern control plane mounting defect persists in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while the workspace state `/home/runner/work/LexMachina/LexMachina/state/fractal-map.json` and `state/factory_direction.json` correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, NOT a lane failure.

---

## Verification Results

### Test Suite Results (7 suites, 247 total tests)

| Test Suite | Tests | Passed | Skipped |
|------------|-------|--------|---------|
| `test_verify.py` | 186 | 186 | 0 |
| `test_pipeline_readiness.py` | 14 | 14 | 0 |
| `test_zoom_quality_174k_eval.py` | 4 | 4 | 0 |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 7 | 0 |
| `test_dense_embeddings_infrastructure.py` | 15 | 14 | 1 |
| `test_scale_dependency.py` | 11 | 11 | 0 |
| `test_12k_dense_comprehensive.py` | 10 | 10 | 0 |
| **TOTAL** | **247** | **246** | **1** |

All tests **PASS**. The single skipped test (`test_dense_mode_artifacts_exist`) is expected — dense embedding artifacts at 174k are blocked upstream.

---

## Deliverables Completed (All ACCEPTED Tier)

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
- **3 production modes at full 173,963 decisions:**
  - `full_text_tfidf_light` — fine_branch_purity **0.930**
  - `regeste_full_text_hybrid_0.5` — fine_branch_purity **0.906**
  - `regeste_full_text_hybrid_0.7` — fine_branch_purity **0.916**
- **All 3 PASS hierarchical_v1 protocol** (6/8 modes PASS overall; 2 citation-based at 52% scale PASS with 0.609-0.685; `outcome_tfidf` and `regeste_tfidf` FAIL as expected — weak signal / missing branch labels)
- **16/16 scale simulation tests PASS**
- **WebGL pipeline <3s at 174k**

### 2. Multi-Level Recursive Protocol (4+ levels) — VALID NEGATIVE at 174k
- **All 5 TF-IDF modes FAIL** the multi-level protocol at 174k
- **Root cause:** Level 0 (root) has single cluster; Levels 1-3 have multiple clusters but protocol fails on **level2 area_purity threshold (~0.134 < 0.15)**, NOT cluster collapse at all levels
- This is a **valid negative result**, correctly preserved and documented

### 3. Calibration on TF-IDF — VALID NEGATIVE
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### 4. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN
**File:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`

Four complementary views with frozen acceptance criteria:

| View | Acceptance Criterion | Evidence Status |
|------|---------------------|-----------------|
| **Citation Heritage** | AUC > 0.75 | PASSED at 144k (center_projected_768dim AUC 0.795) |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | PASSED at 144k (0.282) |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | PASSED at 144k (0.150) |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.10 | **FAILED** at 144k (0.094) — reasoning most language-specific |
| **Linear Hybrid Complement** | PASS adversarial gates (w=0.3-0.4) | PASSED at 144k (JP 0.61-0.67) but BELOW TF-IDF baseline (0.78-0.79) |

**Note:** Dense embeddings are COMPLEMENTARY views only. TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78-0.79 vs dense JP 0.05-0.43).

### 5. Preparatory 12k/144k Dense Validation — COMPLETE
- **12k dense:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint (22/26 years, 2000-2021):** Validates hierarchical builder (2-level) scale extrapolation:
  - fine_branch_purity ~0.97
  - improvement_rate 0.48-0.65 branch / 0.75-0.76 area
  - strict_nesting ≥0.99
  - fine_singletons ~4-5%

**Important:** These metrics describe the **hierarchical builder (2-level)**, NOT the multi-level recursive protocol (which FAILS at 144k).

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had `nesting_score≥0.99` without scope annotation
- `min_cluster_size` enforces nesting=1.0 by construction
- Enforcement active for all outputs

---

## Critical Findings (from state/fractal-map.json)

```json
{
  "tfidf_hierarchical_v1_6_of_8_pass": "Text-based modes at full 174k achieve fine_branch_purity 0.906-0.930; citation-based at 52% scale achieve 0.609-0.685; outcome_tfidf and regeste_tfidf FAIL as expected",
  "multi_level_recursive_protocol_fails_174k": "All 5 TF-IDF modes FAIL the multi-level (4+ level) protocol at 174k: Level 0 (root) has single cluster; Levels 1-3 have multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15), NOT cluster collapse at all levels",
  "calibration_fails_tfidf": "Thresholds too aggressive for TF-IDF signal density; calibrated protocol does not improve over frozen v1",
  "dense_integration_contract_frozen": "Four complementary view criteria defined with acceptance thresholds; validated against 12k/144k evidence where available",
  "scale_extrapolation_validated": "144k checkpoint confirms hierarchical builder (2-level) fine_branch_purity ~0.97, improvement rates healthy, nesting >=0.99, fine singletons ~4-5%",
  "nesting_metric_defect_enforced": "7 compressed-family modes had nesting_score>=0.99 without scope annotation; min_cluster_size enforces nesting=1.0 by construction",
  "blocker_upstream_data": "Legal-distance 174k dense embeddings require BGE/bger ID mapping + parquet 2022-2026 from corpus lane; no fractal-map lane defect exists"
}
```

---

## Upstream Blockers (Require Factory Director Action)

1. **Corpus lane:** BGE/bger ID mapping production (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. **Corpus lane:** Parquet generation for years 2022-2026 (29,520 decisions missing from pinned 2026 snapshot)
3. **Corpus lane:** Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density
4. **Legal-distance lane:** 174k dense embeddings computation (currently 3/26 years complete, ~19,441 decisions, 11%)

---

## State File Integrity

The state file `/home/runner/work/LexMachina/LexMachina/state/fractal-map.json` correctly records:
- `evidence_tier: "ACCEPTED"`
- `cycle_status: "BLOCKED_ON_DEPENDENCIES"`
- `continue_recommended: false` — no further same-question cycles justified
- `audit_ready: true`
- `direction_version: 35`
- All evidence_refs point to actual result files
- 246 verification tests passed, 1 skipped

---

## V28-Pattern Control Plane Mounting Defect

**Diagnosis:** The mounted `/tmp/lex_control/state/factory_direction.json` shows fractal-map status as `"RUN"` (line 16) while the authoritative workspace state shows `"BLOCKED_ON_DEPENDENCIES"`.

**Classification:** **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism.

**Impact:** None on lane deliverable. All evidence, tests, and state in the workspace are correct and consistent.

**History:** This defect has been documented since v28 and persists across multiple factory direction versions. It does not affect the scientific integrity or audit readiness of the lane.

---

## Recommendation

**CONTINUE_RECOMMENDED = FALSE**

No further same-question cycles are justified for the factory direction v34/v35 question. All discriminating experiments are complete. The lane is correctly blocked on upstream dependencies.

**Factory Director Action Required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022-2026
3. Section extraction at 174k scale

Once legal-distance delivers 174k dense embeddings passing the four complementary view acceptance criteria, the fractal-map lane can integrate dense embedding complementary views per the frozen v34 contract.

---

## Evidence Artifacts (Immutable, Preserved)

All results preserved under `results/fractal_map/`:
- `hierarchical_v1_174k_tfidf/` — frozen spec + 6/8 PASS verdict
- `multi_level_protocol_174k_tfidf/` — 5 modes, valid negative
- `dense_embeddings_integration_contract_v34.json` — frozen contract
- `12k_dense_comprehensive/` — preparatory dense validation
- `144k_multi_level_validation/` — scale extrapolation
- `nesting_metric_defect_v1_audit.json` — enforcement record
- `hierarchical_product_integration/` — product-ready artifacts
- `hierarchical_map_174k/` — TF-IDF embeddings at full scale

All negative results preserved. No claim-bearing outputs overwritten.

---

**Signed:** Fractal Map Lane — Operational Resume Final Audit-Ready
**Timestamp:** 2026-10-08T05:16:00.000000Z
**GitHub Run:** 37731419819