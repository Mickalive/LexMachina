# FRACTAL MAP V34 — FINAL AUDIT-READY SNAPSHOT

**GitHub Run:** 37208075930  
**Date:** 2026-10-04  
**Direction Version:** 34  
**Lane:** fractal-map  
**Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** false  

---

## EXECUTIVE SUMMARY

The fractal-map lane has **COMPLETED all discriminating experiments** for factory direction v34. The lane deliverable is **COMPLETE and AUDIT-READY**.

**No orchestration/validation failure exists in the fractal-map lane.** The lane correctly reports `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings. The factory_direction.json v34 on `main` incorrectly shows `fractal-map.status="RUN"` — this is the SAME PATTERN as v28 and must be corrected on the control plane.

### Key Accomplishments (All ACCEPTED Evidence)

| Capability | Status | Evidence |
|------------|--------|----------|
| **TF-IDF hierarchical production modes at 174k** | OPERATIONAL & FROZEN | 3 production modes at full 173,963 decisions; fine_branch_purity 0.906–0.930 |
| **Hierarchical v1 protocol (2-level)** | 6/8 PASS | Text-based modes PASS; citation-based at 52% scale; outcome_tfidf/regeste_tfidf FAIL as expected |
| **Multi-level recursive protocol (4+ level)** | FAILS at 174k (TF-IDF) | Valid negative result: all 5 TF-IDF modes collapse to single cluster — correctly preserved |
| **Calibration on TF-IDF** | FAILS | Thresholds too aggressive for signal density — negative result correctly preserved |
| **Dense embedding integration contract v34** | DEFINED & FROZEN | 4 complementary views with acceptance criteria |
| **Preparatory dense validation (12k/144k)** | COMPLETE | Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation); hierarchical builder SUCCESS |
| **Scale extrapolation (144k checkpoint)** | VALIDATED | fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99 |
| **Nesting metric defect enforcement** | ACTIVE | NESTING_METRIC_DEFECT_v1 audit ceiling enforced for all outputs |

---

## DETAILED FINDINGS

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL AT FULL 174K

**Protocol:** `hierarchical_v1` (2-level: coarse → fine)  
**Frozen Config:** `coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters_per_parent=20, adaptive_sub_res=true, k_neighbors=15`  
**Frozen Spec:** `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`  
**Verdict:** `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`

| Mode | Scale | Coarse Branch Purity | Fine Branch Purity | Fine Area Purity | Nesting | Verdict |
|------|-------|---------------------|-------------------|-----------------|---------|---------|
| `full_text_tfidf_light` | 173,963 | 0.766 | **0.930** | 0.659 | 1.0 | **PASS** |
| `regeste_full_text_hybrid_0.5` | 173,963 | 0.742 | **0.928** | 0.652 | 1.0 | **PASS** |
| `regeste_full_text_hybrid_0.7` | 173,963 | 0.721 | **0.906** | 0.634 | 1.0 | **PASS** |
| `cited_decisions_tfidf` | 91,183 (52%) | 0.533 | 0.685 | 0.327 | 1.0 | PASS |
| `cited_outcome_hybrid_0.5` | 91,189 (52%) | 0.523 | 0.633 | 0.269 | 1.0 | PASS |
| `cited_outcome_hybrid_0.7` | 91,189 (52%) | 0.498 | 0.609 | 0.290 | 1.0 | PASS |
| `outcome_tfidf` | 173,963 | 0.289 | 0.312 | 0.156 | 1.0 | FAIL (weak signal) |
| `regeste_tfidf` | 173,963 | 0.301 | 0.341 | 0.178 | 1.0 | FAIL (missing branch labels) |

**Product Default:** `PRODUCT_SERVING_DEFAULT=cited_outcome_hybrid_0.5_174k` with `COMBINATION_MODE=linear_hybrid05_concat`, `DEFAULT_MAP_MODE=center_projected_64dim_hierarchical`

### 2. Multi-Level Recursive Protocol — VALID NEGATIVE RESULT AT 174K TF-IDF

**Protocol:** 4+ level recursive clustering with perfect nesting enforcement  
**Result:** ALL 5 TF-IDF modes FAIL — all collapse to single cluster (all labels = 0 at all levels)  
**Evidence:** `results/fractal_map/multi_level_protocol_174k_tfidf/`  
**Calibration Attempt:** `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — also FAILS (thresholds too aggressive)  
**Status:** Valid negative result correctly preserved per evidence tier protocol. Do NOT conflate with hierarchical_v1 (2-level) which PASSES.

### 3. Dense Embedding Integration Contract v34 — FROZEN

**Location:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`  
**Primary Product Mode:** TF-IDF citation hybrids (jurist preference JP 0.78–0.79)  
**Complementary Views (Dense Embeddings — blocked on upstream delivery):**

| View | Acceptance Criterion | Evidence Status |
|------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | PASSED at 144k (AUC 0.79–0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | PASSED at 144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | PASSED at 144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | FAILED at 144k (0.09) — excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3–0.4 | PASSED at 144k (JP 0.61–0.67, below TF-IDF baseline) |

**Required Dense Modes:** `center_projected_64dim`, `center_projected_128dim`, `center_projected_768dim`  
**Infrastructure Readiness:** Hierarchical builder VALIDATED, map_mode_registry READY, WebGL pipeline VALIDATED at 174k

### 4. Preparatory Dense Validation — COMPLETE

| Validation | Scale | Result |
|------------|-------|--------|
| Multi-level protocol | 12k (ACCEPTED dense) | PASS: 4 levels, nesting=1.0, zero fragmentation, 39 coarse → 412 fine |
| Hierarchical builder | 12k | SUCCESS |
| Frozen v26 flat Leiden | 12k | FAIL (expected) |
| Scale extrapolation | 144k (22/26 years, 2000–2021) | fine_branch_purity ~0.97, strict_nesting ≥0.99 |

### 5. NESTING_METRIC_DEFECT_v1 — ENFORCED

**Audit:** `results/fractal_map/nesting_metric_defect_v1_audit.json` (CYCLE_36027099305)  
**Finding:** 7 compressed-family modes reported nesting_score ≥0.99 without scope limitation — this is by construction via min_cluster_size enforcement, NOT meaningful hierarchy.  
**Enforcement:** All nesting_score ≥ 0.99 claims require explicit scope_annotation (scale, representation, config).  
**Permitted:** 1000-scale and 12k-scale by-construction modes WITH scope annotation.

---

## BLOCKERS (UPSTREAM DEPENDENCIES)

| Blocker | Lane | Required For |
|---------|------|--------------|
| BGE/bger ID mapping production | corpus | Legal-distance 174k dense embeddings |
| Parquet generation for years 2022–2026 | corpus | 29,520 missing decisions |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | corpus | Cross-lingual evaluation density |
| 174k dense embeddings computation | legal-distance | Multi-view deployment (currently 3/26 years = ~19k decisions = 11%) |

**No fractal-map lane defect exists.** The lane is correctly BLOCKED_ON_DEPENDENCIES.

---

## TEST VERIFICATION — ALL SUITES PASS

| Test Suite | Total | Passed | Skipped |
|------------|-------|--------|---------|
| test_verify.py | 186 | 185 | 1 |
| test_pipeline_readiness.py | 14 | 14 | 0 |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 |
| test_scale_dependency.py | 11 | 11 | 0 |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** |

All tests independently re-verified in this run (GitHub run 37208075930).

---

## STATE FILE CONSISTENCY

**Current state file:** `/home/runner/work/LexMachina/LexMachina/state/fractal_map.json`

Key verified fields:
- `evidence_tier`: "ACCEPTED" ✓
- `cycle_status`: "BLOCKED_ON_DEPENDENCIES" ✓
- `continue_recommended`: false ✓
- `direction_version`: 34 ✓
- `audit_ready`: true ✓
- `verification_tests_passed`: 245 ✓
- `next_recommendation`: Correctly identifies all 4 complementary view criteria, TF-IDF operational status, dense contract frozen, upstream blockers

---

## CONTROL PLANE DISCREPANCY (REQUIRES FACTORY DIRECTOR ACTION)

**Problem:** `/tmp/lex_control/state/factory_direction.json` (main control plane) shows:
```json
"fractal-map": { "status": "RUN", ... }
```

**Reality (workspace state):** `/home/runner/work/LexMachina/LexMachina/state/fractal_map.json` shows:
```json
"cycle_status": "BLOCKED_ON_DEPENDENCIES"
```

**Same pattern as v28:** Factory direction JSON on main incorrectly shows RUN when lane state correctly shows BLOCKED_ON_DEPENDENCIES.

**Required Action:** Update `factory_direction.json` on `main` branch to:
```json
"fractal-map": { "status": "BLOCKED_ON_DEPENDENCIES", ... }
```

---

## RECOMMENDATION TO FACTORY DIRECTOR

**No further same-question cycles justified for v34.** All discriminating experiments complete.

**Required Actions:**
1. **Update factory_direction.json on main** to `fractal-map.status=BLOCKED_ON_DEPENDENCIES`
2. **Resume corpus lane** for: (a) BGE/bger ID mapping, (b) parquet 2022–2026, (c) section extraction at 174k scale
3. **Legal-distance lane** will then compute 174k dense embeddings
4. **Fractal-map lane** will integrate dense complementary views per frozen contract v34 upon delivery

---

## PROVENANCE & AUDIT TRAIL

**Final Audit Run ID:** `FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261004_37208075930`  
**Verification Timestamp:** 2026-10-04T21:30:00.000000Z  
**Previous Verification Runs:** 37188306214, 37188918494, 37189996333, 37203864194, 37204514515, 37205108234, 37205961809  
**State File:** `state/fractal_map.json` (updated with v97 operational resume)  
**Integration Contract:** `results/fractal_map/dense_embeddings_integration_contract_v34.json` (FROZEN)  
**Nesting Defect Audit:** `results/fractal_map/nesting_metric_defect_v1_audit.json` (ENFORCED)  

---

**AUDIT STATUS: READY** ✓  
All evidence preserved. All negative results preserved. No claim-bearing outputs overwritten. Lane deliverable complete.