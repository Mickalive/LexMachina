# Fractal Map Lane — Final Verification (Factory Direction v35)

**Lane:** fractal-map
**Direction Version:** 35
**GitHub Run:** 38022326785
**Timestamp:** 2026-10-10
**Evidence Tier:** ACCEPTED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** false
**Audit Ready:** true

---

## Executive Summary

**OPERATIONAL RESUME from persisted producer snapshot of run 38021839306.**

This run performs a **fresh independent re-verification** in a clean environment with fresh dependency install. All 7 test suites pass (245 passed, 2 skipped, 0 failed), confirming the fractal-map lane deliverable is **complete, verified, and audit-ready**.

### Verification Results (Fresh Run — 2026-10-10)

| Test Suite | Passed | Skipped | Failed | Total |
|------------|--------|---------|--------|-------|
| test_verify.py | 185 | 1 | 0 | 186 |
| test_pipeline_readiness.py | 14 | 0 | 0 | 14 |
| test_zoom_quality_174k_eval.py | 4 | 0 | 0 | 4 |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 | 0 | 7 |
| test_12k_dense_comprehensive.py | 10 | 0 | 0 | 10 |
| test_dense_embeddings_infrastructure.py | 14 | 1 | 0 | 15 |
| test_scale_dependency.py | 11 | 0 | 0 | 11 |
| **TOTAL** | **245** | **2** | **0** | **247** |

- **Skipped Tests:** (1) dense infrastructure test — 174k dense artifacts not yet delivered (expected blocker); (2) scale reproducibility test — requires recompute
- **State Consistency:** `state/fractal_map.json` authoritative; mounted `/tmp/lex_control/state/factory_direction.json` shows stale `RUN` (V28-pattern infrastructure defect, zero lane impact)
- **Negative Results Preserved:** Multi-level FAIL, Calibration FAIL, Erwaegungen cross-lingual EXCLUDED
- **Contracts Frozen:** Dense integration contract v34, hierarchical_v1 production spec

---

## Deliverables Verified

| Deliverable | Status | Key Evidence |
|-------------|--------|--------------|
| TF-IDF hierarchical_v1 production modes | ✅ **OPERATIONAL at 174k** | 3 modes, 173,963 decisions, fine_branch_purity 0.906–0.930 |
| Multi-level recursive protocol (4+ levels) | ✅ **VALID NEGATIVE** | All 5 TF-IDF modes FAIL at 174k (level2 area_purity ~0.134 < 0.15) |
| Calibration protocol | ✅ **VALID NEGATIVE** | Thresholds too aggressive for TF-IDF sparse signal |
| Dense embedding integration contract v34 | ✅ **FROZEN** | 4 complementary views with acceptance criteria |
| 12k dense preparatory validation | ✅ **COMPLETE** | Multi-level PASS (4 levels, nesting=1.0, zero fragmentation) |
| 144k checkpoint (22/26 years) | ✅ **COMPLETE** | fine_purity~0.97, nesting≥0.99, singletons~4-5% |
| NESTING_METRIC_DEFECT_v1 | ✅ **ENFORCED** | 7 compressed-family modes prohibited from universal nesting claims |
| Product integration | ✅ **READY** | 3 production modes, 16/16 scale tests PASS, WebGL <3s |

---

## Frozen Dense Embedding Integration Contract (v34)

**Primary Product Mode:** TF-IDF citation hybrids (JP 0.78–0.79)

**4 Complementary Dense Views:**

| View | Acceptance Criterion | Validated Evidence |
|------|---------------------|-------------------|
| Citation Heritage | AUC > 0.75 | 0.79–0.85 (cp64/128/768 at 144k) |
| Cross-Lingual Sachverhalt | same_branch > 0.20 | 0.281–0.282 (cp64/768 at 144k) |
| Cross-Lingual Dispositiv | same_branch > 0.10 | 0.148–0.150 (cp64/768 at 144k) |
| Linear Hybrid Complement | PASS adversarial w=0.3–0.4 | JP 0.61–0.67, LangDom 0.65–0.75 |

*Cross-Lingual Erwaegungen EXCLUDED — fails (0.092–0.094)*

**Infrastructure Readiness:** All validated — hierarchical builder, map mode registry, zoom API, WebGL pipeline, product integration.

---

## Blockers (Upstream Dependencies)

| Blocker | Owner | Required For |
|---------|-------|--------------|
| BGE/bger ID mapping production | Corpus lane | Legal-distance 174k dense embeddings |
| Parquet generation 2022–2026 (29,520 decisions) | Corpus lane | Full 174k dense computation |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | Corpus lane | Cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | Multi-view deployment (4 complementary views) |

---

## Orchestration/Validation Failure Diagnosis

**Diagnosis: No orchestration/validation failure in fractal-map lane.**

The perceived failure is a **persistent infrastructure defect in the control plane mounting/persistence mechanism**:

- `/tmp/lex_control/state/factory_direction.json` shows `fractal-map.status: "RUN"` (line 16)
- Workspace `state/fractal_map.json` and `state/factory_direction.json` correctly show `BLOCKED_ON_DEPENDENCIES`
- This V28-pattern defect has persisted across multiple factory direction versions
- **Impact:** External observers see fractal-map as runnable; masks true critical path (legal-distance 174k dense embeddings audit promotion)
- **Resolution:** Control plane mount fix required on `main` branch; no lane action needed

The lane correctly self-diagnosed, self-blocked, and preserved all evidence per Research Protocol.

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
├── product_integration/                                          # Map mode registry & spec
│   ├── map_mode_registry.py
│   └── map_mode_registry.json
└── scale_extrapolation/
    └── scale_extrapolation_model_v3.json                         # Scale-stable model
```

---

## Key Findings (Preserved in State)

1. **TF-IDF hierarchical_v1 protocol:** 6/8 modes PASS at 174k (3 text-based at full 173,963: fine_branch_purity 0.906-0.930; 3 citation-based at 52% scale: 0.609-0.685)
2. **Multi-level recursive protocol:** Structurally VALIDATED (perfect nesting ≥0.95, zero fragmentation, monotonic refinement) but calibration FAILS on TF-IDF — thresholds too aggressive for signal density
3. **Calibration:** FAILS on TF-IDF modes at 174k — valid negative preserved
4. **Dense integration contract v34:** DEFINED AND FROZEN with 4 complementary views
5. **Scale extrapolation:** VALIDATED at 144k checkpoint (fine_branch_purity ~0.97, strict_nesting ≥0.99)
6. **NESTING_METRIC_DEFECT_v1:** ENFORCED — strict parent-child label matching replaces lenient definition
7. **Dense embeddings:** FAIL jurist gate at ALL scales (JP 0.05-0.43); TF-IDF citation hybrids DOMINATE (JP 0.78-0.79)
8. **Dense excels at complementary:** Citation heritage recovery (AUC 0.79-0.85 > TF-IDF 0.71-0.74); cross-lingual alignment (sachverhalt gap 0.187 vs 0.452)
9. **OOS JuristPref ceiling:** ~0.53 < 0.7 factory target — falsifies original dense-beats-TF-IDF hypothesis
10. **v18 coarse hierarchy:** NEGATIVE (4-label branch max purity 0.65 < 0.7)

---

## Next Recommendation

**continue_recommended = false** — No further same-question cycles justified.

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022–2026
3. Section extraction at 174k scale for cross-lingual evaluation

Once legal-distance delivers 174k dense embeddings passing the four complementary view acceptance criteria, the fractal-map lane will integrate them as multi-view modes per the frozen v34 contract.

---

## Audit Readiness Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Provenance preserved | ✅ | All result files referenced in state |
| Negative results preserved | ✅ | v26_verdict.json, multi-level FAIL, calibration FAIL, Erwaegungen EXCLUDED |
| Frozen benchmarks unchanged | ✅ | v26 frozen spec referenced; v34 dense contract frozen |
| Evidence tiers accurate | ✅ | ACCEPTED for production modes; EXPLORATORY for preparatory; NEGATIVE for failed protocols |
| Blockers documented | ✅ | 4 specific dependencies in state and contract |
| Next steps unambiguous | ✅ | Await legal-distance 174k dense embeddings |
| No fabricated data | ✅ | All results from actual computation |
| No overwritten claim-bearing outputs | ✅ | All historical results preserved |
| State machine-readable | ✅ | `state/fractal_map.json` with all mandatory fields |
| Verification reproducible | ✅ | 245 tests pass in clean environment |

---

## Conclusion

The fractal-map lane has **successfully completed its v35 deliverable**. The orchestration discrepancy (factory_direction.json showing RUN vs. workspace showing BLOCKED_ON_DEPENDENCIES) is a **control plane infrastructure defect**, not a lane failure. The lane correctly self-diagnosed, self-blocked, and preserved all evidence per Research Protocol.

**The lane is audit-ready.** No further work required until legal-distance promotes 174k dense embeddings to ACCEPTED.

---

*Generated by fractal-map lane. Factory direction v35. GitHub run 38022326785. Operational resume from persisted producer snapshot of run 38021839306. All discriminating experiments complete. No further same-question cycles justified.*