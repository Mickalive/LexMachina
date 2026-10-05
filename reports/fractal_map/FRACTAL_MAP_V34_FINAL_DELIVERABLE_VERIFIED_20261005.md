# FRACTAL MAP LANE — V34 FINAL DELIVERABLE VERIFIED

**GitHub Run:** 37330853374  
**Lane State:** `state/fractal-map.json` (evidence_tier=ACCEPTED, cycle_status=BLOCKED_ON_DEPENDENCIES, continue_recommended=false, audit_ready=true)  
**Verification Tests:** 245 passed, 2 skipped (7 test suites)  
**Factory Direction:** v34  

---

## DELIVERABLE STATUS: COMPLETE ✓

All discriminating experiments for factory direction v34 question **COMPLETE**. No further same-question cycles justified.

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
- **3 production modes** at full 173,963 decisions:
  - `full_text_tfidf_light`
  - `regeste_full_text_hybrid_0.5`
  - `regeste_full_text_hybrid_0.7`
- **Fine branch purity:** 0.906–0.930 (6/8 hierarchical_v1 protocol PASS)
- **16/16 scale simulation tests PASS**
- **WebGL pipeline <3s**
- **Evidence:** `results/fractal_map/hierarchical_v1_174k_tfidf/`, `reports/fractal_map/hierarchical_v1_174k_report.md`

### 2. Multi-Level Recursive Protocol (4+ levels) — FAILS at 174k (Valid Negative Result)
- All 5 TF-IDF modes FAIL the multi-level protocol at 174k
- Level 0 (root) has single cluster; Levels 1–3 have multiple clusters
- Protocol fails on **level2 area_purity threshold (~0.134 < 0.15)** — NOT cluster collapse at all levels
- Correctly preserved as negative result
- **Evidence:** `results/fractal_map/multi_level_protocol_174k_tfidf/`, `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`

### 3. Calibration — FAILS on TF-IDF (Valid Negative Result)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Correctly preserved as negative result

### 4. Dense Embedding Integration Contract v34 — DEFINED AND FROZEN
Four complementary view criteria with frozen acceptance thresholds:
| Complementary View | Acceptance Criterion | Status |
|---|---|---|
| Citation Heritage | AUC > 0.75 (vs TF-IDF 0.71–0.74) | Contract frozen; awaits 174k dense embeddings |
| Cross-Lingual Sachverhalt | same_branch > 0.20 | Contract frozen; 12k validation PASS (gap 0.187) |
| Cross-Lingual Dispositiv | same_branch > 0.10 | Contract frozen; 12k validation PASS (gap 0.452) |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3–0.4) | Contract frozen; 174k validation PASS (JP 0.66–0.67) |

**Critical:** These are **COMPLEMENTARY views only** — TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43).

- **Evidence:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`, `results/fractal_map/12k_dense_comprehensive/`, `results/fractal_map/144k_multi_level_validation/`

### 5. Preparatory Dense Validation — COMPLETE
- **12k dense embeddings:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint (22/26 years, 2000–2021):** Hierarchical builder (2-level) validates scale extrapolation — fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99, fine_singletons ~4–5%
- **Note:** 144k metrics describe hierarchical builder (2-level), NOT multi-level recursive protocol (which FAILS at 144k)

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had nesting_score ≥0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs
- **Evidence:** `results/fractal_map/nesting_metric_defect_v1_audit.json`

---

## ORCHESTRATION/VALIDATION FAILURE DIAGNOSIS

**The Failure:** V28-pattern control plane mounting defect — the mounted control plane at `/tmp/lex_control/state/factory_direction.json` persists `fractal-map.status="RUN"` (line 16) while:
- Workspace state (`/home/runner/work/LexMachina/LexMachina/state/factory_direction.json`) correctly shows `BLOCKED_ON_DEPENDENCIES`
- Lane state (`/home/runner/work/LexMachina/LexMachina/state/fractal-map.json`) correctly shows `BLOCKED_ON_DEPENDENCIES`
- ALL prior audit reports (40+ runs) correctly show `BLOCKED_ON_DEPENDENCIES`

**Root Cause:** Persistent infrastructure defect in the control plane mounting/persistence mechanism — the hourly reconciliation workflow has not corrected the mounted control plane.

**Impact:** **ZERO** on lane deliverable. The lane state is AUTHORITATIVE and CORRECT. All discriminating experiments complete. All tests pass. Negative results preserved. Contract frozen.

**Resolution Path:** Factory Director action or hourly reconciliation workflow must update mounted control plane to match workspace state.

---

## BLOCKER: UPSTREAM DATA DEPENDENCY

**Legal-distance 174k dense embeddings** require:
1. **BGE/bger ID mapping** (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
2. **Parquet generation for years 2022–2026** (29,520 decisions missing)
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

**Factory Director action required:** Resume corpus lane for (a) BGE/bger ID mapping production, (b) parquet 2022–2026, (c) section extraction at 174k scale.

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