# FRACTAL_MAP_V35_FINAL_VERIFICATION_RUN_37866050416

## Summary
**OPERATIONAL RESUME from persisted producer snapshot.**  
**FRESH INDEPENDENT RE-VERIFICATION CONFIRMED: All 7 test suites PASS (245 passed, 2 skipped, 0 failed).**  
**Lane deliverable VERIFIED AND AUDIT-READY.**

## Diagnosis: Orchestration/Validation Failure Identified
**No orchestration/validation failure in fractal-map lane.** The V28-pattern control plane mounting defect PERSISTS in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16 for fractal-map lane) while workspace `state/factory_direction.json` and lane state `state/fractal-map.json` correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism, NOT a lane failure**.

The defect: The `/tmp/lex_control` mount (which is the control plane source for workflows) contains stale state where fractal-map shows `status: "RUN"` despite the lane being correctly `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings since factory direction v34. The workspace state (which is the source of truth for lane execution) correctly reflects `BLOCKED_ON_DEPENDENCIES`.

**This defect has been documented across 20+ verification runs (37707252501 through 37866050416) and persists.** It does not affect the lane's actual work, evidence, or deliverables — only the control plane display.

## Lane Status (Factory Direction v35)
- **Lane**: fractal-map
- **Evidence Tier**: ACCEPTED
- **Cycle Status**: BLOCKED_ON_DEPENDENCIES
- **Continue Recommended**: false
- **Accepted Run ID**: FRACTAL_MAP_V35_FINAL_AUDIT_READY_20261008_37763353403
- **Direction Version**: 35
- **GitHub Run**: 37866050416

## Verification Results (Fresh Execution)

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify | 186 | 185 | 1 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 | 0 |
| test_scale_dependency | 11 | 11 | 0 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** | **0** |

All tests executed in fresh Python environment with clean dependency install (numpy, scipy, scikit-learn, networkx, pandas, pyarrow, pytest).

## Key Findings (All Previously Accepted, Re-verified)

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k
- **3 text-based modes** at full 173,963 decisions: fine_branch_purity 0.906–0.930
- **3 citation-based modes** at 52% scale: fine_branch_purity 0.609–0.685
- All 6 PASS hierarchical_v1 protocol (fine_branch_purity > 0.5 threshold)
- 16/16 scale simulation tests PASS
- WebGL pipeline <3s

### 2. Multi-Level Recursive Protocol — FAILS at 174k (Valid Negative)
- All 5 TF-IDF modes FAIL the 4+ level recursive protocol at 174k
- Level 0 (root): single cluster
- Levels 1–3: multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15)
- **NOT** cluster collapse at all levels — structurally valid hierarchy exists but signal density insufficient for area_purity threshold
- Negative result correctly preserved

### 3. Calibration — FAILS on TF-IDF (Valid Negative)
- Thresholds too aggressive for TF-IDF signal density at 174k
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### 4. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with frozen acceptance criteria:
1. **Citation Heritage**: AUC > 0.75 (vs TF-IDF 0.71–0.74)
2. **Cross-Lingual Sachverhalt**: > 0.20 same-branch alignment
3. **Cross-Lingual Dispositiv**: > 0.10 same-branch alignment
4. **Linear Hybrid Complement**: PASS adversarial gates (w=0.3–0.4)

**These are COMPLEMENTARY views only** — TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43).

### 5. Preparatory Dense Validation — COMPLETE
- 12k ACCEPTED dense embeddings: multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation)
- Hierarchical builder SUCCESS (39 coarse → 412 fine)
- Frozen v26 flat Leiden FAIL (expected)

### 6. Scale Extrapolation — VALIDATED at 144k Checkpoint
- 144k checkpoint (22/26 years, 2000–2021): fine_branch_purity ~0.97
- Improvement rate: 0.48–0.65 branch / 0.75–0.76 area
- Strict nesting ≥ 0.99
- Fine singletons ~4–5%
- **Note**: These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k)

### 7. NESTING_METRIC_DEFECT_v1 — ENFORCED
- Strict definition: fine label's parent must match coarse label for that decision
- Previous lenient "any parent has child" inflated scores
- Enforcement active for all outputs

### 8. Upstream Blocker — UNCHANGED
- **BLOCKED on legal-distance 174k dense embeddings**
- Requires corpus lane resumption for:
  - BGE/bger ID mapping production
  - Parquet 2022–2026 (29,520 decisions missing)
  - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale
- **No fractal-map lane defect exists**

## Evidence References (Preserved, Immutable)
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_all_results.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/` (4 modes)
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json`
- `results/fractal_map/final_pipeline_validation/final_pipeline_validation_results.json`
- `results/fractal_map/hierarchical_product_integration/`
- `results/fractal_map/product_integration/INTEGRATION_SPEC.md`

## State Files (Authoritative)
- `state/fractal-map.json` — Lane state: BLOCKED_ON_DEPENDENCIES, continue_recommended=false, audit_ready=true
- `state/factory_direction.json` (workspace) — Lane status: BLOCKED_ON_DEPENDENCIES (correct)
- `/tmp/lex_control/state/factory_direction.json` (control plane mount) — Lane status: RUN (STALE, infrastructure defect)

## Recommendation
**No further same-question cycles justified.**  
**continue_recommended = false** — All discriminating experiments for factory direction v35 question COMPLETE (identical to v34).

**Factory Director action required**: Resume corpus lane for BGE/bger ID mapping, 2022–2026 parquet, section extraction at 174k scale.

## Verification Metadata
- **GitHub Run**: 37866050416
- **Factory Direction**: v35
- **Verification Timestamp**: 2026-10-09T00:00:00.000000Z
- **Verification Run ID**: RUN_37866050416
- **Tests Passed**: 245
- **Tests Skipped**: 2
- **Audit Ready**: true

## Audit Trail
This snapshot preserves:
- All 245 passing tests + 2 skipped (zero failures)
- All negative results (multi-level protocol FAIL, calibration FAIL, v26 flat FAIL)
- Frozen dense embedding integration contract v34
- NESTING_METRIC_DEFECT_v1 enforcement
- Scale extrapolation model at 144k
- Complete evidence references
- Correct lane state (BLOCKED_ON_DEPENDENCIES)
- Documented control plane mounting defect (does not affect lane deliverable)

**Lane deliverable is AUDIT-READY and COMPLETE for factory direction v35.**