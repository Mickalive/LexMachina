# FRACTAL MAP LANE — V34 LANE COMPLETION VERIFIED

**GitHub Run:** 37373175145  
**Lane State:** `state/fractal-map.json` (evidence_tier=ACCEPTED, cycle_status=BLOCKED_ON_DEPENDENCIES, continue_recommended=false, audit_ready=true)  
**Factory Direction:** v34  
**All Tests:** 245 passed, 2 skipped (7 test suites)

---

## LANE QUESTION STATUS: COMPLETE ✓

**Factory Direction v34 Question:** "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**Status:** **ALL DISCRIMINATING EXPERIMENTS COMPLETE**. No further same-question cycles justified.

---

## DELIVERABLES VERIFIED

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
| Mode | Embeddings | Scale | Fine Branch Purity | Artifacts |
|------|-----------|-------|-------------------|-----------|
| `full_text_tfidf_light` | Full text TF-IDF (light) | 173,963 | 0.906–0.930 | `hierarchical_map_174k/full_text_tfidf_light.npy`, `hierarchical_product_integration/hierarchical_full_text_tfidf/` |
| `regeste_full_text_hybrid_0.5` | Regeste + full text (50/50) | 173,963 | 0.906–0.930 | `hierarchical_map_174k/regeste_full_text_hybrid_0.5.npy`, `hierarchical_product_integration/hierarchical_regeste_tfidf/` |
| `regeste_full_text_hybrid_0.7` | Regeste + full text (70/30) | 173,963 | 0.906–0.930 | `hierarchical_map_174k/regeste_full_text_hybrid_0.7.npy` |

- **6/8 hierarchical_v1 protocol PASS** (3 text-based at full 174k, 3 citation-based at 52% scale)
- **16/16 scale simulation tests PASS**
- **WebGL pipeline <3s**
- **Product defaults:** `PRODUCT_SERVING_DEFAULT=cited_outcome_hybrid_0.5_174k`, `DEFAULT_MAP_MODE=center_projected_64dim_hierarchical`

### 2. Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k (Valid Negative Result)
- All 5 TF-IDF modes FAIL the multi-level protocol at 174k
- Level 0 (root) has single cluster; Levels 1–3 have multiple clusters
- Protocol fails on **level2 area_purity threshold (~0.134 < 0.15)** — NOT cluster collapse at all levels
- Correctly preserved as negative result in `results/fractal_map/multi_level_protocol_174k_tfidf/` and `_calibrated/`

### 3. Calibration — FAILS on TF-IDF (Valid Negative Result)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Correctly preserved as negative result

### 4. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN
**File:** `results/fractal_map/dense_embeddings_integration_contract_v34.json` (status: FROZEN, date_frozen: 2026-10-03)

| Complementary View | Acceptance Criterion | Validation Status |
|---|---|---|
| Citation Heritage | AUC > 0.75 (vs TF-IDF 0.71–0.74) | Contract frozen; 144k PASS (AUC 0.79–0.85) |
| Cross-Lingual Sachverhalt | same_branch > 0.20 | Contract frozen; 12k/144k PASS (gap 0.187, same_branch 0.28) |
| Cross-Lingual Dispositiv | same_branch > 0.10 | Contract frozen; 12k/144k PASS (gap 0.452, same_branch 0.15) |
| Cross-Lingual Erwaegungen | same_branch > 0.10 | **FAILED** at 1k/144k (same_branch ~0.09) — NOT INCLUDED |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3–0.4) | Contract frozen; 144k PASS (JP 0.61–0.67) |

**Critical:** These are **COMPLEMENTARY views only** — TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43).

### 5. Preparatory Dense Validation — COMPLETE
- **12k dense embeddings:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint (22/26 years, 2000–2021):** Hierarchical builder (2-level) validates scale extrapolation — fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99, fine_singletons ~4–5%
- **Note:** 144k metrics describe hierarchical builder (2-level), NOT multi-level recursive protocol (which FAILS at 144k)

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had nesting_score ≥0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs
- **Evidence:** `results/fractal_map/nesting_metric_defect_v1_audit.json`

### 7. Scale Extrapolation — VALIDATED
- 144k checkpoint confirms hierarchical builder (2-level) scale extrapolation
- Fine branch purity ~0.97, healthy improvement rates, nesting ≥0.99

---

## TEST VERIFICATION SUMMARY

| Test Suite | Total | Passed | Skipped |
|---|---|---|---|
| test_verify | 186 | 185 | 1 |
| test_pipeline_readiness | 14 | 14 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 |
| test_scale_dependency | 11 | 11 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** |

All test suites PASS. Lane state invariants verified:
- `evidence_tier: ACCEPTED` ✓
- `cycle_status: BLOCKED_ON_DEPENDENCIES` ✓
- `continue_recommended: false` ✓
- `audit_ready: true` ✓
- `accepted_run_id` set ✓
- All critical findings preserved ✓

---

## BLOCKER: UPSTREAM DATA DEPENDENCY (ZERO LANE DEFECT)

**Legal-distance 174k dense embeddings require:**
1. **BGE/bger ID mapping** (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. **Parquet generation for years 2022–2026** (29,520 decisions missing from pinned 2026 snapshot)
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density

**Factory Director action required:** Resume corpus lane for (a) BGE/bger ID mapping production, (b) parquet 2022–2026, (c) section extraction at 174k scale.

---

## CONTROL PLANE DISCREPANCY NOTE

The mounted control plane at `/tmp/lex_control/state/factory_direction.json` persists `fractal-map.status="RUN"` (line 16) while:
- Workspace state (`state/factory_direction.json`) correctly shows `BLOCKED_ON_DEPENDENCIES`
- Lane state (`state/fractal-map.json`) correctly shows `BLOCKED_ON_DEPENDENCIES`
- ALL prior audit reports (40+ runs) correctly show `BLOCKED_ON_DEPENDENCIES`

**Root Cause:** Persistent infrastructure defect in the control plane mounting/persistence mechanism (V28-pattern orchestration defect). Hourly reconciliation workflow has not corrected the mounted control plane.

**Impact:** **ZERO** on lane deliverable. The lane state is AUTHORITATIVE and CORRECT.

---

## FINAL RECOMMENDATION

**No further fractal-map cycles under factory direction v34.** The lane has delivered:
1. TF-IDF hierarchical production modes OPERATIONAL at full 174k scale
2. Multi-level protocol negative result correctly preserved
3. Calibration negative result correctly preserved
4. Dense embedding integration contract FROZEN with 4 complementary view criteria
5. Preparatory dense validation COMPLETE at 12k/144k
6. Scale extrapolation validated
7. NESTING_METRIC_DEFECT_v1 enforced
8. All evidence preserved, negative results intact, contract frozen

**Next factory decision:** Resume corpus lane to unblock legal-distance 174k dense embeddings → enables fractal-map multi-view deployment per frozen contract.

---

**Verification Timestamp:** 2026-10-05  
**Lane State File:** `state/fractal-map.json` (authoritative)  
**Control Plane Discrepancy:** Documented above — infrastructure defect, not lane failure