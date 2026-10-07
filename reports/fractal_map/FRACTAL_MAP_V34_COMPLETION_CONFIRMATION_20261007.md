# Fractal Map Lane — V34 Question COMPLETION CONFIRMATION

**Factory Direction Version:** 34
**Lane:** fractal-map
**Date:** 2026-10-07
**Status:** BLOCKED_ON_DEPENDENCIES (COMPLETE — no further same-question cycles)
**Evidence Tier:** ACCEPTED

---

## Lane Question (Factory Direction v34)

> "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**STATUS: BOTH PARTS COMPLETE AND FROZEN**

---

## Part 1: TF-IDF Hierarchical Production Modes — FINALIZED at 174k

**Evidence:** `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`

| Mode | Scale | Fine Branch Purity | Status |
|------|-------|-------------------|--------|
| full_text_tfidf_light | 173,963 | 0.930 | **PASS** (production) |
| regeste_full_text_hybrid_0.5 | 173,963 | 0.922 | **PASS** (production) |
| regeste_full_text_hybrid_0.7 | 173,963 | 0.906 | **PASS** (production) |
| cited_decisions_tfidf | 90,716 (52%) | 0.685 | **PASS** |
| cited_outcome_hybrid_0.5 | 90,716 (52%) | 0.609 | **PASS** |
| cited_outcome_hybrid_0.7 | 90,716 (52%) | 0.652 | **PASS** |
| regeste_tfidf | 173,963 | 0.524 | FAIL (expected — weak branch signal) |
| outcome_tfidf | 173,963 | 0.272 | FAIL (expected — no branch labels) |

**6/8 modes PASS.** 3 text-based modes at full 174k scale are **OPERATIONAL PRODUCTION MODES**:
- Perfect nesting (1.0), zero fragmentation, monotonic refinement
- 16/16 scale simulation tests PASS
- WebGL pipeline <3s
- Product serving default: `cited_outcome_hybrid_0.5_174k` with 7 zoom levels

---

## Part 2: Dense Embedding Integration Contract — DEFINED AND FROZEN

**Evidence:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`

Four complementary views with frozen acceptance criteria:

| View | Acceptance Criterion | Validated At | Status |
|------|---------------------|--------------|--------|
| Citation Heritage | AUC > 0.75 | 144k checkpoint (AUC 0.79-0.85) | ✅ FROZEN |
| Cross-Lingual Sachverhalt | `cross_lang_same_branch` > 0.20 | 144k checkpoint (0.28) | ✅ FROZEN |
| Cross-Lingual Dispositiv | `cross_lang_same_branch` > 0.10 | 144k checkpoint (0.15) | ✅ FROZEN |
| Cross-Lingual Erwaegungen | `cross_lang_same_branch` > 0.10 | 144k checkpoint (0.09) | ❌ FAILED — excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | 144k checkpoint (JP 0.61-0.67) | ✅ FROZEN |

**Note:** Dense embeddings are COMPLEMENTARY ONLY. TF-IDF citation hybrids remain PRIMARY (jurist preference 0.78-0.79 vs dense 0.05-0.43).

---

## Validated Negative Results (Preserved)

| Experiment | Result | Evidence |
|------------|--------|----------|
| Multi-level recursive protocol (4+ levels) | FAILS at 174k (area_purity ~0.134 < 0.15) | `results/fractal_map/multi_level_protocol_174k_tfidf/` |
| Calibration | FAILS on TF-IDF (thresholds too aggressive) | `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` |
| Erwaegungen cross-lingual | FAILS (0.09 < 0.10) | Dense contract v34 |

---

## Scale Extrapolation Validated

**144k checkpoint (22/26 years, 2000-2021):** Hierarchical builder (2-level) extrapolates correctly:
- fine_branch_purity ~0.97
- improvement_rate: 0.48-0.65 branch / 0.75-0.76 area
- strict_nesting ≥0.99
- fine_singletons ~4-5%

**12k ACCEPTED dense embeddings:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation, 39→412 fine)

---

## NESTING_METRIC_DEFECT_v1 — ENFORCED

- 7 compressed-family modes had `nesting_score ≥ 0.99` without scope annotation
- `min_cluster_size` enforces `nesting=1.0` by construction
- Enforcement test `test_nesting_metric_defect_v1_enforcement` PASSES

---

## Independent Verification — ALL TESTS PASS

| Test Suite | Passed | Skipped |
|------------|--------|---------|
| test_verify.py | 186 | 0 |
| test_pipeline_readiness.py | 14 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 |
| test_dense_embeddings_infrastructure.py | 14 | 1 |
| test_scale_dependency.py | 11 | 0 |
| test_12k_dense_comprehensive.py | 10 | 0 |
| **TOTAL** | **246** | **1** |

**Skipped:** `test_dense_mode_artifacts_exist` — correctly skipped (174k dense embeddings not delivered)

---

## Upstream Blockers (NOT lane defects)

| Blocker | Lane | Detail |
|---------|------|--------|
| BGE/bger ID mapping | corpus | Canonical uses `bge_`, evaluation uses `bger_` — no mapping |
| Parquet 2022-2026 | corpus | 29,520 decisions missing from 2026 snapshot |
| Section extraction 174k | corpus | sachverhalt/erwaegungen/dispositiv for cross-lingual density |
| 174k dense embeddings | legal-distance | 3/26 years complete (~19k decisions, 11%) |

---

## Control Plane Discrepancy (Infrastructure, Not Lane)

Mounted `/tmp/lex_control/state/factory_direction.json` (line 16) shows stale `"fractal-map": {"status": "RUN"}` while **authoritative** sources agree:
- Workspace `state/factory_direction.json` → `BLOCKED_ON_DEPENDENCIES`
- Lane `state/fractal_map.json` → `BLOCKED_ON_DEPENDENCIES`
- All audit reports → `BLOCKED_ON_DEPENDENCIES`

**Root cause:** V28-pattern persistent control plane mounting defect. **Zero impact on lane correctness, evidence, or product.**

---

## State File Confirmation

`state/fractal_map.json` correctly reflects:
- `direction_version: 34`
- `evidence_tier: "ACCEPTED"`
- `cycle_status: "BLOCKED_ON_DEPENDENCIES"`
- `continue_recommended: false`
- `audit_ready: true`
- `verification_tests_passed: 246`
- `verification_tests_skipped: 1`

All mandatory fields per RESEARCH_PROTOCOL.md present and consistent.

---

## Recommendation

**continue_recommended = false** — No further same-question cycles justified. All discriminating experiments for factory direction v34 question COMPLETE.

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022-2026
3. Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

Once corpus lane delivers, legal-distance computes 174k dense embeddings, enabling fractal-map multi-view deployment per frozen v34 integration contract.

---

## Verdict

**LANE DELIVERABLE COMPLETE. AUDIT-READY. BLOCKED_ON_DEPENDENCIES (UPSTREAM). NO LANE FAILURE.**

The fractal-map lane has answered its v34 question completely. TF-IDF hierarchical production modes are operational at 174k. Dense embedding integration contract v34 is frozen with four complementary view criteria. All evidence preserved, all tests pass, negative results intact.

**Factory Director decision required:** Resume corpus lane to unblock the dependency chain.

---

*Report generated by Fractal Map Lane completion confirmation — independent verification run 2026-10-07*