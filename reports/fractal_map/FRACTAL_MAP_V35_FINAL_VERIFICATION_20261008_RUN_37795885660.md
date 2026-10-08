# FRACTAL_MAP_V35_FINAL_VERIFICATION_20261008_RUN_37795885660

## Summary
**Lane:** fractal-map
**Factory Direction Version:** 35
**GitHub Run:** 37795885660
**Timestamp:** 2026-10-08T21:30:00.000000Z
**Evidence Tier:** ACCEPTED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** false
**Audit Ready:** true

## Test Verification Results
All 7 test suites PASS: **245 passed, 2 skipped, 0 failed**

| Test Suite | Total | Passed | Skipped | Failed |
|------------|-------|--------|---------|--------|
| test_verify | 186 | 185 | 1 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 | 0 |
| test_scale_dependency | 11 | 11 | 0 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 | 0 |
| **Grand Total** | **247** | **245** | **2** | **0** |

## Diagnosis
**NO ORCHESTRATION/VALIDATION FAILURE IN FRACTAL-MAP LANE.**

The V28-pattern control plane mounting defect PERSISTS in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, **NOT a lane failure**.

Lane correctly `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings.

## Deliverables Status

### TF-IDF Hierarchical Production Modes — OPERATIONAL
- **3 production modes** at full 173,963 decisions:
  - `full_text_tfidf_light`
  - `regeste_full_text_hybrid_0.5`
  - `regeste_full_text_hybrid_0.7`
- **Fine branch purity:** 0.906–0.930
- **16/16 scale tests PASS**
- **WebGL pipeline:** <3s at 174k

### Multi-Level Recursive Protocol (4+ levels) — FAIL (VALID NEGATIVE)
- All 5 TF-IDF modes FAIL at 174k
- Level 0 (root) = single cluster
- Levels 1-3 have multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15)
- **NOT cluster collapse at all levels** — valid negative result preserved
- Distinct from hierarchical_v1 (2-level) production protocol which PASSES for 3 text-based modes

### Calibration — FAIL (VALID NEGATIVE)
- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with frozen acceptance criteria:

| View | Criterion | Evidence | Status |
|------|-----------|----------|--------|
| Citation Heritage | AUC > 0.75 | 0.79–0.85 (vs TF-IDF 0.71–0.74) | PASSED |
| Cross-Lingual Sachverhalt | same_branch > 0.20 | 0.281–0.282 | PASSED |
| Cross-Lingual Dispositiv | same_branch > 0.10 | 0.148–0.150 | PASSED |
| Cross-Lingual Erwaegungen | same_branch > 0.10 | 0.092–0.094 | FAILED (below threshold) |
| Linear Hybrid Complement | PASS adversarial at w=0.3–0.4 | JP 0.61–0.67 | PASSED |

**Note:** These are COMPLEMENTARY views only. TF-IDF citation hybrids remain PRIMARY product mode (jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43).

### Scale Extrapolation — VALIDATED
144k checkpoint (22/26 years, 2000–2021) validates hierarchical builder (2-level):
- Fine branch purity: ~0.97
- Improvement rate: 0.48–0.65 (branch) / 0.75–0.76 (area)
- Strict nesting: >=0.99
- Fine singletons: ~4–5%
- **Note:** These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k)

### NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had nesting_score >= 0.99 without scope annotation
- min_cluster_size enforces nesting=1.0 by construction
- Enforcement active for all outputs

### Product Integration — READY
- 3 production modes operational
- 16/16 scale tests PASS
- WebGL pipeline <3s at 174k

## Blockers (Upstream — No Fractal-Map Lane Defect)
1. **BGE/bger ID mapping production** (corpus lane) — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs, no mapping exists
2. **Parquet generation 2022–2026** (corpus lane) — 29,520 decisions missing from pinned 2026 snapshot
3. **Section extraction at 174k** (corpus lane) — sachverhalt/erwaegungen/dispositiv for cross-lingual evaluation density
4. **174k dense embeddings computation** (legal-distance lane) — currently ~11% complete (3/26 years)

## Next Recommendation
**No further same-question cycles justified.**

Factory Director must resume corpus lane for:
- BGE/bger ID mapping
- Parquet 2022–2026 (29,520 decisions)
- Section extraction at 174k scale

All discriminating experiments for factory direction v35 question COMPLETE (identical to v34). Lane deliverable VERIFIED AND AUDIT-READY.

## Evidence References
- `results/fractal_map/hierarchical_v1_174k_tfidf/` — 8 hierarchical_v1 results (6 PASS, 2 expected FAIL)
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — 5 multi-level protocol results (all FAIL, valid negative)
- `results/fractal_map/12k_dense_comprehensive/` — 12k dense validation (multi-level PASS, hierarchical builder SUCCESS)
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — Defect enforcement record
- `results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json` — 144k checkpoint
- `results/fractal_map/final_pipeline_validation/final_pipeline_validation_results.json` — Pipeline validation
- `results/fractal_map/hierarchical_product_integration/` — Product integration artifacts
- `results/fractal_map/product_integration/INTEGRATION_SPEC.md` — Integration specification

## Critical Findings (Preserved)
1. **TF-IDF hierarchical_v1: 6/8 PASS** — Text-based modes at full 174k achieve fine_branch_purity 0.906–0.930; citation-based at 52% scale achieve 0.609–0.685; outcome_tfidf and regeste_tfidf FAIL as expected (weak signal / missing branch labels)
2. **Multi-level recursive protocol FAILS at 174k** — Valid negative; do not conflate with hierarchical_v1 (2-level) production protocol
3. **Calibration FAILS on TF-IDF** — Thresholds too aggressive; negative result correctly preserved
4. **Dense integration contract FROZEN** — Four complementary view criteria defined with acceptance thresholds
5. **Scale extrapolation VALIDATED** — 144k checkpoint confirms hierarchical builder (2-level) metrics
6. **NESTING_METRIC_DEFECT_v1 ENFORCED** — All nesting_score >= 0.99 claims require explicit scope annotation
7. **Blocker is UPSTREAM DATA** — Legal-distance 174k dense embeddings require corpus lane resumption; no fractal-map lane defect exists