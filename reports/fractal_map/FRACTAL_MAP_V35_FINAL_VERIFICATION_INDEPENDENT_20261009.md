# Fractal Map Lane — Independent Final Verification (Factory Direction v35)

**Lane:** fractal-map
**Direction Version:** 35
**GitHub Run:** 37878339983
**Timestamp:** 2026-10-09T00:00:00.000000Z
**Evidence Tier:** ACCEPTED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** false
**Audit Ready:** true

---

## Orchestration/Validation Failure Diagnosis

### The Defect

**V28-pattern control plane mounting defect** persists in the mounted control plane at `/tmp/lex_control/state/factory_direction.json`:

- **Mounted control plane** (v35, line 16): `fractal-map.status = "RUN"` ❌
- **Workspace state** (`state/factory_direction.json`, v35): `fractal-map.status = "BLOCKED_ON_DEPENDENCIES"` ✅
- **Lane state** (`state/fractal-map.json`): `cycle_status = "BLOCKED_ON_DEPENDENCIES"` ✅

### Root Cause

This is a **PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism**, NOT a lane failure. The lane state is authoritative and correct. The defect has been documented across 15+ operational resume cycles and persists despite correction attempts at the control plane level.

### Impact

- **Zero impact on lane deliverables** — all experiments complete, all tests pass
- **Zero impact on product** — TF-IDF modes operational, dense contract frozen
- **False signal** — external consumers reading mounted control plane see stale RUN status

### Resolution Path

Factory Director must address the control plane mounting infrastructure. The lane itself requires **no further work**.

---

## Independent Test Verification — Fresh Run (2026-10-09)

| Test Suite | Passed | Skipped | Status |
|------------|--------|---------|--------|
| `test_verify.py` | 185 | 1 | ✅ PASS |
| `test_pipeline_readiness.py` | 14 | 0 | ✅ PASS |
| `test_zoom_quality_174k_eval.py` | 4 | 0 | ✅ PASS |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 0 | ✅ PASS |
| `test_dense_embeddings_infrastructure.py` | 14 | 1 | ✅ PASS |
| `test_scale_dependency.py` | 11 | 0 | ✅ PASS |
| `test_12k_dense_comprehensive.py` | 10 | 0 | ✅ PASS |
| **TOTAL** | **245** | **2** | **✅ ALL PASS** |

**Matches state file exactly:** `verification_tests_passed: 245`, `verification_tests_skipped: 2`

---

## Lane Deliverables — ALL VERIFIED AND FROZEN

| Deliverable | Status | Key Evidence |
|-------------|--------|--------------|
| **TF-IDF hierarchical_v1 production modes** | OPERATIONAL at 174k (3 modes, full 173,963 decisions) | 6/8 PASS; fine_branch_purity 0.906–0.930 |
| **Multi-level recursive protocol (4+ levels)** | FAILS at 174k for all 5 TF-IDF modes | Valid negative — level2 area_purity ~0.134 < 0.15 |
| **Calibration protocol** | FAILS on TF-IDF | Thresholds too aggressive for TF-IDF signal density |
| **Dense embedding integration contract v34** | FROZEN (4 complementary views with acceptance criteria) | Citation Heritage AUC>0.75, Cross-Lingual Sachverhalt>0.20, Dispositiv>0.10, Linear Hybrid PASS adversarial |
| **12k dense preparatory validation** | COMPLETE | Multi-level PASS (4 levels, nesting=1.0, zero fragmentation) |
| **144k checkpoint (22/26 years)** | COMPLETE | Hierarchical builder: fine_purity~0.97, nesting≥0.99, singletons~4-5% |
| **NESTING_METRIC_DEFECT_v1** | ENFORCED | 7 compressed-family modes prohibited from universal nesting claims |
| **Product integration** | READY | 3 production modes, 16/16 scale tests PASS, WebGL <3s |

---

## Factory Direction v35 Question — ANSWERED

> **Question:** "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

### Answer: COMPLETE

#### 1. TF-IDF Hierarchical Production Modes — FINALIZED

**3 production modes at full 173,963 decisions:**

| Mode | Fine Branch Purity | Status |
|------|-------------------|--------|
| `full_text_tfidf_light` | 0.906–0.930 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.5` | 0.906–0.930 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.7` | 0.906–0.930 | ✅ PRODUCTION |

**2 citation-based modes at 52% scale (91,000 decisions):**

| Mode | Fine Branch Purity | Status |
|------|-------------------|--------|
| `cited_decisions_tfidf` | 0.609–0.685 | LIMITED (citation coverage) |
| `cited_outcome_hybrid_0.5` | 0.609–0.685 | LIMITED (citation coverage) |

#### 2. Multi-Level Recursive Protocol — VALID NEGATIVE

- **Protocol:** 4+ level hierarchical Leiden with area_purity ≥ 0.15 at each level
- **Result:** ALL 5 TF-IDF modes FAIL at 174k
- **Failure mode:** Level 0 (root) = single cluster; Levels 1-3 have multiple clusters but **level2 area_purity ~0.134 < 0.15** — NOT cluster collapse at all levels
- **Verdict:** Valid negative result, correctly preserved. Do NOT conflate with hierarchical_v1 (2-level) which PASSES.

#### 3. Calibration — VALID NEGATIVE

- **Protocol:** Adaptive thresholds per signal density
- **Result:** Calibrated protocol does NOT improve over frozen v1
- **Cause:** Thresholds too aggressive for TF-IDF sparse signal density
- **Verdict:** Negative result correctly recorded.

#### 4. Dense Embedding Integration Contract v34 — FROZEN

| Complementary View | Acceptance Criterion | Evidence (144k) | Status |
|--------------------|---------------------|-----------------|--------|
| **Citation Heritage** | AUC > 0.75 | 0.79–0.85 (center_projected 64/128/768) | ✅ PASSED |
| **Cross-Lingual Sachverhalt** | same_branch > 0.20 | 0.281–0.282 (64/768) | ✅ PASSED |
| **Cross-Lingual Dispositiv** | same_branch > 0.10 | 0.148–0.150 (64/768) | ✅ PASSED |
| **Cross-Lingual Erwaegungen** | same_branch > 0.10 | 0.092–0.094 | ❌ FAILED (excluded) |
| **Linear Hybrid Complement** | PASS adversarial at w=0.3–0.4 | JP 0.61–0.67, LangDom 0.65–0.75 | ✅ PASSED (but below TF-IDF baseline 0.78–0.79) |

**Role:** Dense embeddings are **COMPLEMENTARY views only**. TF-IDF citation hybrids remain **PRIMARY product mode** (jurist preference 0.78–0.79 vs dense 0.05–0.43).

#### 5. 144k Checkpoint — SCALE EXTRAPOLATION VALIDATED

| Metric | Value | Note |
|--------|-------|------|
| Fine branch purity | ~0.97 | Hierarchical builder (2-level), NOT multi-level protocol |
| Improvement rate (branch) | 0.48–0.65 | Scale-stable |
| Improvement rate (area) | 0.75–0.76 | Scale-stable |
| Strict nesting | ≥0.99 | By construction (min_cluster_size) |
| Fine singletons | ~4–5% | Healthy (vs TF-IDF ~99%) |

#### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED

- **Defect:** 7 compressed-family modes reported nesting_score ≥ 0.99 without scope annotation
- **Root cause:** `min_cluster_size` enforces nesting=1.0 by construction
- **Enforcement:** All nesting_score ≥ 0.99 claims require explicit scope annotation (scale, representation, config)
- **Permitted:** 1000-scale and 12k-scale by-construction modes WITH scope annotation
- **Prohibited:** Universal hierarchy validity claims from compressed-family modes

---

## Blocker Summary

| Blocker | Owner | Required For |
|---------|-------|--------------|
| BGE/bger ID mapping production | Corpus lane | Legal-distance 174k dense embeddings |
| Parquet generation 2022–2026 (29,520 decisions) | Corpus lane | Full 174k dense computation |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | Corpus lane | Cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | Multi-view deployment (4 complementary views) |

**No fractal-map lane defect exists.** All fractal-map deliverables are complete, frozen, and audit-ready.

---

## Next Recommendation

**continue_recommended = false** — No further same-question cycles justified.

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022–2026
3. Section extraction at 174k scale for cross-lingual evaluation

Once legal-distance delivers 174k dense embeddings passing the four complementary view acceptance criteria, the fractal-map lane will integrate them as multi-view modes per the frozen v34 contract.

---

## Critical Evidence Artifacts

```
results/fractal_map/
├── hierarchical_v1_174k_tfidf/
│   ├── hierarchical_v1_174k_tfidf_verdict_20261001_102442.json   # 6/8 PASS verdict
│   └── hierarchical_v1_frozen_spec.json                          # Frozen production spec
├── multi_level_protocol_174k_tfidf/                              # 4 TF-IDF modes, FAIL preserved
├── multi_level_protocol_174k_tfidf_calibrated/                   # Calibration FAIL preserved
├── 12k_dense_comprehensive/                                      # Dense multi-level PASS
├── 144k_multi_level_validation/
│   └── multi_level_144k_results.json                             # Scale extrapolation
├── nesting_metric_defect_v1_audit.json                           # Enforcement audit
├── dense_embeddings_integration_contract_v34.json                # FROZEN contract
├── hierarchical_product_integration/                             # 2 production modes integrated
├── product_integration/                                          # Map mode registry & spec
│   ├── PRODUCT_INTEGRATION_SPEC.md
│   ├── INTEGRATION_SPEC.md
│   ├── map_mode_registry.py
│   └── map_mode_registry.json
└── scale_extrapolation/
    └── scale_extrapolation_model_v3.json                         # Scale-stable model
```

---

## Sign-off

This snapshot is **audit-ready**. All evidence preserved, negative results intact, contracts frozen, provenance maintained.

**Lane State:** `state/fractal-map.json` — authoritative
**Workspace State:** `state/factory_direction.json` — consistent with lane state
**Mounted Control Plane:** `/tmp/lex_control/state/factory_direction.json` — stale (infrastructure defect)
**Test Verification:** 245 passed, 2 skipped across 7 independent test suites
**JSON Summary:** `results/fractal_map/FRACTAL_MAP_V35_FINAL_VERIFICATION_20261008_RUN_37850370721.json`
**Human Report:** This document

---

*Generated by fractal-map lane independent final verification from GitHub run 37878339983. Factory direction v35. All discriminating experiments complete. No further same-question cycles justified.*