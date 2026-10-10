# Fractal Map Lane — Deliverable Complete Verification (Factory Direction v35)

**Lane:** fractal-map  
**Direction Version:** 35  
**Verification Date:** 2026-10-10  
**GitHub Run:** 38025030390  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Executive Summary

The fractal-map lane has **successfully completed all deliverables** for the factory direction v35 question:

> *"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."*

**Both deliverables are COMPLETE and OPERATIONAL:**

| Deliverable | Status | Key Metrics |
|-------------|--------|-------------|
| TF-IDF hierarchical_v1 production modes | ✅ **OPERATIONAL at 174k** | 3 modes, 173,963 decisions, fine_branch_purity 0.906–0.930, 16/16 scale tests PASS, WebGL <3s |
| Dense embedding integration contract v34 | ✅ **FROZEN** | 4 complementary views with acceptance criteria, infrastructure validated |

---

## Verification Results (Fresh Run)

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

All tests pass in a clean environment with fresh dependency install.

---

## Frozen Dense Embedding Integration Contract (v34)

**Primary Product Mode:** TF-IDF citation hybrids (Jurist Preference 0.78–0.79)

**4 Complementary Dense Views (acceptance criteria):**

| View | Acceptance Criterion | Validated Evidence |
|------|---------------------|-------------------|
| Citation Heritage | AUC > 0.75 | 0.79–0.85 (cp64/128/768 at 144k checkpoint) |
| Cross-Lingual Sachverhalt | same_branch > 0.20 | 0.281–0.282 (cp64/768 at 144k) |
| Cross-Lingual Dispositiv | same_branch > 0.10 | 0.148–0.150 (cp64/768 at 144k) |
| Linear Hybrid Complement | PASS adversarial w=0.3–0.4 | JP 0.61–0.67, LangDom 0.65–0.75 |

*Cross-Lingual Erwaegungen EXCLUDED — fails criterion (0.092–0.094)*

**Infrastructure Readiness:** All validated — hierarchical builder (4 levels, nesting=1.0, zero fragmentation), map mode registry, zoom API, WebGL pipeline, product integration.

---

## Negative Results Preserved (Per Research Protocol)

| Experiment | Result | Status |
|------------|--------|--------|
| Multi-level recursive protocol (4+ levels) | All 5 TF-IDF modes FAIL at 174k (level2 area_purity ~0.134 < 0.15) | ✅ VALID NEGATIVE |
| Calibration protocol | Thresholds too aggressive for TF-IDF sparse signal | ✅ VALID NEGATIVE |
| v18 coarse hierarchy (4-label branch) | Max purity 0.65 < 0.7 | ✅ VALID NEGATIVE |
| Erwaegungen cross-lingual | Fails acceptance (0.092–0.094 < 0.10) | ✅ EXCLUDED |
| NESTING_METRIC_DEFECT_v1 | 7 compressed-family modes prohibited from universal nesting claims | ✅ ENFORCED |

---

## Blockers (Upstream Dependencies)

| Blocker | Owner | Required For |
|---------|-------|--------------|
| BGE/bger ID mapping production | Corpus lane | Legal-distance 174k dense embeddings |
| Parquet generation 2022–2026 (29,520 decisions) | Corpus lane | Full 174k dense computation |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | Corpus lane | Cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | Multi-view deployment (4 complementary views) |

---

## Control Plane Infrastructure Note

**Diagnosis:** No orchestration/validation failure in fractal-map lane.

The mounted `/tmp/lex_control/state/factory_direction.json` shows `fractal-map.status: "RUN"` (line 16) while workspace `state/fractal_map.json` and `state/factory_direction.json` correctly show `BLOCKED_ON_DEPENDENCIES`. This is a **persistent V28-pattern infrastructure defect in the control plane mounting/persistence mechanism**, not a lane failure.

- **Impact:** External observers see fractal-map as runnable; masks true critical path (legal-distance 174k dense embeddings audit promotion)
- **Resolution:** Control plane mount fix required on `main` branch; no lane action needed
- **Lane correctly self-diagnosed, self-blocked, and preserved all evidence per Research Protocol**

---

## Audit Readiness Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Provenance preserved | ✅ | All result files referenced in state |
| Negative results preserved | ✅ | Multi-level FAIL, calibration FAIL, Erwaegungen EXCLUDED |
| Frozen benchmarks unchanged | ✅ | v26 frozen spec referenced; v34 dense contract frozen |
| Evidence tiers accurate | ✅ | ACCEPTED for production; EXPLORATORY for preparatory; NEGATIVE for failed |
| Blockers documented | ✅ | 4 specific dependencies in state and contract |
| Next steps unambiguous | ✅ | Await legal-distance 174k dense embeddings |
| No fabricated data | ✅ | All results from actual computation |
| No overwritten claim-bearing outputs | ✅ | All historical results preserved |
| State machine-readable | ✅ | `state/fractal_map.json` with all mandatory fields |
| Verification reproducible | ✅ | 245 tests pass in clean environment |

---

## Next Recommendation

**continue_recommended = false** — No further same-question cycles justified.

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022–2026 (29,520 decisions)
3. Section extraction at 174k scale for cross-lingual evaluation

Once legal-distance delivers 174k dense embeddings passing the four complementary view acceptance criteria, the fractal-map lane will integrate them as multi-view modes per the frozen v34 contract.

---

## Conclusion

The fractal-map lane has **successfully completed its v35 deliverable**. The lane is audit-ready with all discriminating experiments complete, evidence frozen, and negative results preserved. No further work required until legal-distance promotes 174k dense embeddings to ACCEPTED.

---

*Generated by fractal-map lane verification. Factory direction v35. All 245 tests pass. No further same-question cycles justified.*