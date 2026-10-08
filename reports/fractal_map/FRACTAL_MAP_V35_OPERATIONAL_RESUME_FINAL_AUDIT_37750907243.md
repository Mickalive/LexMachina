# FRACTAL MAP LANE — OPERATIONAL RESUME FINAL AUDIT (RUN 37750907243)

**Factory Direction**: v35  
**Lane**: fractal-map  
**Run ID**: 37750907243  
**Timestamp**: 2026-10-08T08:30:00Z  
**Status**: VERIFIED AND AUDIT-READY  

---

## Executive Summary

The fractal-map lane deliverable is **VERIFIED AND AUDIT-READY**. All discriminating experiments for the factory direction v35 question are complete. The lane is correctly **BLOCKED_ON_DEPENDENCIES** on upstream legal-distance 174k dense embeddings, which requires corpus lane resumption.

**No orchestration/validation failure exists in the fractal-map lane.** The V28-pattern control plane mounting defect persists in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace state (`state/factory_direction.json`, `state/fractal_map.json`, `state/fractal-map.json`) correctly shows `BLOCKED_ON_DEPENDENCIES`. This is a **PERSISTENT INFRASTRUCTURE DEFECT** in the control plane mounting/persistence mechanism, **NOT a lane failure**.

---

## Verification Results

### Test Suite Execution (7 suites, 247 tests)
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

**All tests PASS.** Zero failures.

---

## Discriminating Experiments — COMPLETE

### 1. TF-IDF Hierarchical Production Modes (v1 Protocol) — OPERATIONAL at 174k
- **3 text-based modes at full 173,963 decisions**: PASS fine_branch_purity 0.906–0.930
  - `full_text_tfidf_light`: branch_purity 0.930
  - `regeste_full_text_hybrid_0.5`: branch_purity 0.906
  - `regeste_full_text_hybrid_0.7`: branch_purity 0.909
- **3 citation-based modes at 52% scale (91k decisions)**: PASS fine_branch_purity 0.609–0.685
  - `cited_decisions_tfidf`: 0.685
  - `cited_outcome_hybrid_0.5`: 0.633
  - `cited_outcome_hybrid_0.7`: 0.609
- **2 modes FAIL as expected** (weak signal / missing branch labels):
  - `outcome_tfidf`, `regeste_tfidf`
- **16/16 scale simulation tests PASS**, WebGL pipeline <3s

### 2. Multi-Level Recursive Protocol (4+ levels) — VALID NEGATIVE at 174k
- **All 5 TF-IDF modes FAIL** the multi-level protocol at 174k
- Level 0 (root): single cluster
- Levels 1–3: multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15)
- **NOT cluster collapse at all levels** — structural hierarchy exists but purity threshold not met
- Negative result correctly preserved

### 3. Calibration — VALID NEGATIVE on TF-IDF
- Adaptive thresholds too aggressive for TF-IDF signal density at 174k
- Calibrated protocol does not improve over frozen v1
- Negative result correctly preserved

### 4. Dense Embedding Integration Contract v34 — FROZEN
Four complementary views with frozen acceptance criteria:

| View | Acceptance Criterion | Status |
|------|---------------------|--------|
| Citation Heritage | AUC > 0.75 | PASSED at 144k (0.79–0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | PASSED at 144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | PASSED at 144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | FAILED at 144k (0.09) — excluded |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3–0.4) | PASSED at 144k (JP 0.61–0.67) |

**Note**: Dense embeddings are COMPLEMENTARY only. TF-IDF citation hybrids remain PRIMARY (JP 0.78–0.79 vs dense 0.05–0.43).

### 5. Preparatory Dense Validation — COMPLETE
- **12k dense embeddings**: Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine)
- **144k checkpoint** (22/26 years, 2000–2021): Hierarchical builder (2-level) scale extrapolation validated:
  - fine_branch_purity ~0.97
  - improvement_rate 0.48–0.65 branch / 0.75–0.76 area
  - strict_nesting >=0.99
  - fine_singletons ~4–5%
- **Note**: These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k)

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED
- 7 compressed-family modes had nesting_score>=0.99 without scope annotation
- Root cause: `min_cluster_size` parameter enforces nesting=1.0 by construction regardless of actual hierarchy quality
- Enforcement active: all nesting_score >= 0.99 claims require explicit scope annotation (scale, representation, config)
- 1000-scale and 12k-scale by-construction modes permitted WITH scope annotation

---

## Upstream Blockers (Require Factory Director Action)

The fractal-map lane is **BLOCKED_ON_DEPENDENCIES** on legal-distance 174k dense embeddings, which requires **corpus lane resumption**:

| Blocker | Description | Impact |
|---------|-------------|--------|
| **BGE/bger ID mapping** | Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists | Cannot link dense embeddings to evaluation framework |
| **Parquet 2022–2026** | 29,520 decisions missing from pinned 2026 snapshot | 174k dense embeddings incomplete (~11% computed) |
| **Section extraction** | Sachverhalt/Erwaegungen/Dispositiv at 174k scale for cross-lingual evaluation density | Cross-lingual views blocked at full corpus density |

**Legal-distance lane status**: 3/26 years complete (~19,441 decisions, 11%)

---

## State File Consistency

| File | evidence_tier | cycle_status | continue_recommended | direction_version | audit_ready |
|------|--------------|--------------|---------------------|-------------------|-------------|
| `state/fractal_map.json` | ACCEPTED | BLOCKED_ON_DEPENDENCIES | false | 35 | true |
| `state/fractal-map.json` | ACCEPTED | BLOCKED_ON_DEPENDENCIES | false | 35 | true |
| `/tmp/lex_control/state/factory_direction.json` (mounted) | — | **RUN** (DEFECT) | — | 35 | — |

**Defect**: Mounted control plane shows `RUN` while workspace state correctly shows `BLOCKED_ON_DEPENDENCIES`. This is the persistent V28-pattern infrastructure defect.

---

## Evidence References (Key Artifacts)

- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/`
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`
- `results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json`

---

## Next Recommendation

> TF-IDF hierarchical production modes at 174k are OPERATIONAL and FROZEN (3 production modes at full 173,963 decisions; fine_branch_purity 0.906–0.930). Multi-level recursive protocol (4+ levels) FAILS at 174k for all TF-IDF modes — valid negative. Calibration FAILS — valid negative. Dense embedding integration contract v34 DEFINED AND FROZEN (4 complementary views with acceptance criteria). 144k checkpoint validates hierarchical builder scale extrapolation. NESTING_METRIC_DEFECT_v1 enforced. **No further same-question cycles justified.**

**Blocker**: Legal-distance 174k dense embeddings require corpus lane resumption for BGE/bger ID mapping + parquet 2022–2026 + section extraction at 174k scale.

**Factory Director decision required**: Resume corpus lane.

---

## Conclusion

The fractal-map lane deliverable is **complete, verified, and audit-ready**. The lane has executed all discriminating experiments for the factory direction v35 question, preserved all negative results, frozen contracts, and correctly identified the upstream blocker. The only remaining action is a **Factory Director decision to resume the corpus lane**.

**No orchestration/validation failure in fractal-map lane.** The V28-pattern control plane mounting defect is an infrastructure issue outside lane scope.
