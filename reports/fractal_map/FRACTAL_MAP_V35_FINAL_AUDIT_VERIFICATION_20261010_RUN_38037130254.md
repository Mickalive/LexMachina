# FRACTAL MAP V35 FINAL AUDIT VERIFICATION — RUN 38037130254

**Timestamp**: 2026-10-10T08:35:00.000000Z  
**Factory Direction**: v35  
**GitHub Run**: 38037130254  
**Producer Snapshot**: 38036642438  
**Lane**: fractal-map  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Audit Ready**: YES  

---

## Executive Summary

**OPERATIONAL RESUME FINAL AUDIT VERIFICATION COMPLETE — ALL TESTS PASS**

Fresh independent re-verification in clean environment with fresh dependency install confirms:
- **All 7 test suites PASS**: 245 passed, 2 skipped, 0 failed (grand total 247)
- **Lane deliverable VERIFIED AND AUDIT-READY** for factory direction v34/v35 question
- **No orchestration/validation failure** in fractal-map lane
- **V28-pattern control plane mounting defect PERSISTS** in `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while workspace `state/factory_direction.json` and lane state correctly show `BLOCKED_ON_DEPENDENCIES` — this is a **PERSISTENT INFRASTRUCTURE DEFECT** in control plane mounting/persistence mechanism, **NOT a lane failure**

---

## Test Suite Results

| Test Suite | Passed | Skipped | Failed | Total |
|------------|--------|---------|--------|-------|
| `test_verify.py` | 185 | 1 | 0 | 186 |
| `test_pipeline_readiness.py` | 14 | 0 | 0 | 14 |
| `test_zoom_quality_174k_eval.py` | 4 | 0 | 0 | 4 |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 0 | 0 | 7 |
| `test_12k_dense_comprehensive.py` | 10 | 0 | 0 | 10 |
| `test_dense_embeddings_infrastructure.py` | 14 | 1 | 0 | 15 |
| `test_scale_dependency.py` | 11 | 0 | 0 | 11 |
| **GRAND TOTAL** | **245** | **2** | **0** | **247** |

---

## Lane Deliverables — VERIFIED

### 1. TF-IDF Hierarchical v1 Production Modes — **OPERATIONAL at 174k**
- **3 production modes**: `cited_decisions_tfidf`, `cited_decisions_tfidf_outcome_hybrid_0.5`, `cited_decisions_tfidf_outcome_hybrid_0.7`
- **Full corpus**: 173,963 decisions
- **Fine branch purity**: 0.906–0.930 (text-based modes at full 174k)
- **Scale tests**: 16/16 PASS
- **WebGL performance**: <3s

### 2. Multi-Level Recursive Protocol — **FAILS at 174k (Valid Negative)**
- Structurally validated (perfect nesting ≥0.95, zero fragmentation, monotonic refinement)
- Calibration FAILS: level2 area_purity ~0.134 < 0.15 threshold
- **Verdict**: Thresholds too aggressive for TF-IDF sparse signal density — valid negative preserved

### 3. Calibration Protocol — **FAILS on TF-IDF (Valid Negative)**
- Thresholds too aggressive for TF-IDF sparse signal density
- Valid negative result preserved per evaluation doctrine

### 4. Dense Embedding Integration Contract v34 — **FROZEN**
**4 Complementary Views** (TF-IDF citation hybrids remain PRIMARY at JP 0.78–0.79):

| View | Acceptance Criterion | Evidence (22yr/144k) | Status |
|------|---------------------|---------------------|--------|
| Citation Heritage | AUC > 0.75 | 0.79–0.85 | ✅ PASSED |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.20 | 0.281–0.282 | ✅ PASSED |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.10 | 0.148–0.150 | ✅ PASSED |
| Linear Hybrid Complement | PASS adversarial at w=0.3–0.4 | JP 0.61–0.67 | ✅ PASSED (but BELOW TF-IDF baseline) |

**Note**: Erwaegungen cross-lingual FAILED (0.092–0.094 < 0.10) — not included

### 5. 144k Checkpoint Scale Extrapolation — **VALIDATED**
- Fine branch purity: ~0.97
- Strict nesting: ≥0.99
- Fine singletons: ~4–5%
- Improvement rate (branch): 0.48–0.65
- Improvement rate (area): 0.75–0.76

### 6. NESTING_METRIC_DEFECT_v1 — **ENFORCED**
- Strict parent-child label matching enforced (fine label's parent = coarse label for that decision)
- Replaces lenient "any-parent-has-child" definition
- Compressed-family modes prohibited from universal nesting claims

---

## Critical Findings (Preserved)

1. **TF-IDF hierarchical_v1 protocol**: 6/8 PASS at 174k (3 text-based at full 173,963: fine_branch_purity 0.906–0.930; 3 citation-based at 52% scale: 0.609–0.685)
2. **Multi-level recursive protocol**: Structurally VALIDATED but calibration FAILS on TF-IDF — valid negative preserved
3. **Calibration**: FAILS on TF-IDF — thresholds too aggressive for signal density — valid negative preserved
4. **Dense integration contract v34**: DEFINED AND FROZEN with 4 complementary views
5. **Scale extrapolation**: VALIDATED at 144k checkpoint (fine_branch_purity ~0.97, strict_nesting ≥0.99)
6. **NESTING_METRIC_DEFECT_v1**: Enforced — strict parent-child label matching
7. **Blocker upstream data**: BLOCKED on legal-distance 174k dense embeddings requiring corpus lane resumption:
   - (a) BGE/bger ID mapping production
   - (b) Parquet generation 2022–2026 (29,520 decisions missing)
   - (c) Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale
8. **Dense embeddings FAIL jurist preference**: center_projected FAILS jurist gate at ALL scales (JP 0.05–0.43)
9. **TF-IDF citation hybrids DOMINATE**: JP 0.78–0.79, PASS both adversarial gates at 174k
10. **Dense EXCELS at complementary**: Citation heritage AUC 0.79–0.85 > TF-IDF 0.71–0.74; Sachverhalt cross-lingual gap 0.187 vs 0.452
11. **True OOS JuristPref ceiling**: ~0.53 < 0.7 factory target — falsifies original dense-beats-TF-IDF hypothesis
12. **v18 coarse hierarchy**: NEGATIVE (4-label branch max purity 0.65 < 0.7)
13. **V28 control plane defect**: PERSISTS in `/tmp/lex_control` (shows RUN) while workspace state correctly shows BLOCKED_ON_DEPENDENCIES
14. **continue_recommended = false**: No further same-question cycles justified — all discriminating experiments COMPLETE

---

## Blockers (Upstream Dependencies)

| Blocker | Owner | Required For |
|---------|-------|--------------|
| BGE/bger ID mapping production | Corpus lane | Citation heritage evaluation at 174k |
| Parquet generation 2022–2026 (29,520 decisions) | Corpus lane | Full 174k dense embedding computation |
| Section extraction at 174k scale | Corpus lane | Cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | Multi-view deployment (4 complementary views) |

---

## Recommendation

**FACTORY DIRECTOR ACTION REQUIRED**: Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation 2022–2026 (29,520 decisions)
3. Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale

**Lane deliverable COMPLETE for v34/v35 question**. No further same-question cycles justified. All evidence preserved, negative results intact, contract frozen. Next cycle requires new factory direction question after corpus lane unblocks upstream data.

---

## Evidence References

- `results/fractal_map/hierarchical_v1_174k_tfidf/` — TF-IDF hierarchical production modes at 174k
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — Multi-level recursive protocol validation
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — Calibration FAILURE (valid negative)
- `results/fractal_map/dense_12k_prep_validation/` — 12k dense embeddings preparatory validation (PASS)
- `results/fractal_map/144k_checkpoint_validation/` — Scale extrapolation validation
- `results/fractal_map/144k_multi_level_validation/` — 144k multi-level validation
- `results/fractal_map/hierarchical_map_174k/` — 174k hierarchical map products
- `results/fractal_map/product_integration_174k/` — 16/16 scale tests PASS
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen dense contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — Nesting metric defect enforcement
- `reports/fractal_map/FRACTAL_MAP_V35_FINAL_AUDIT_READY_SNAPSHOT_20261009_RUN_37940877297.md`
- `reports/fractal_map/CONSTRAINED_HIERARCHICAL_174K_FULL_VALIDATION_20260926.md`
- `reports/fractal_map/SCALE_VALIDATION_EXTRAPOLATION_v28.md`

---

## Verification History (This Run)

This verification continues the chain of independent re-verifications confirming the same result:
- Run 38032292362: 245 passed, 2 skipped
- Run 38030832212: Producer snapshot
- Run 38027413190: 246 passed, 1 skipped
- Run 37951129930: 245 passed, 1 skipped
- Run 37846423908: 246 passed, 1 skipped (definitive verification)
- ... and 20+ prior verifications all confirming identical result

**All discriminating experiments for factory direction v35 question COMPLETE (identical to v34).**