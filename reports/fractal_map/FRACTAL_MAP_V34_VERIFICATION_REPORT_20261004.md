# Fractal Map Lane — v34 Verification Report

**Date:** 2026-10-04  
**Lane:** fractal-map  
**Factory Direction:** v34  
**GitHub Run:** 37169037027  
**Status:** BLOCKED_ON_DEPENDENCIES (complete for v34 question)

---

## Executive Summary

The fractal-map lane has **completed all discriminating experiments** for factory direction v34 question:
> "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**All deliverables are OPERATIONAL, FROZEN, and AUDIT-READY.**

---

## Validation Results

### Test Suite Execution (Independent Re-verification)

| Test Suite | Tests | Passed | Skipped | Status |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 186 | 0 | ✅ PASS |
| test_pipeline_readiness.py | 14 | 14 | 0 | ✅ PASS |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | ✅ PASS |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | ✅ PASS |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | ✅ PASS |
| test_scale_dependency.py | 11 | 11 | 0 | ✅ PASS |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | ✅ PASS |
| **TOTAL** | **247** | **246** | **1** | ✅ **ALL PASS** |

The 1 skipped test (`test_dense_mode_artifacts_exist`) correctly reflects the upstream blocker: dense embeddings not yet delivered at 174k.

---

## v34 Deliverables Confirmed

### 1. TF-IDF Hierarchical Production Modes at 174k — OPERATIONAL & FROZEN
- **3 production modes** at full 173,963 decisions:
  - `full_text_tfidf_light`
  - `regeste_full_text_hybrid_0.5`
  - `regeste_full_text_hybrid_0.7`
- **Fine branch purity:** 0.906–0.930 (text-based modes)
- **16/16 scale simulation tests PASS** (product readiness)
- **WebGL pipeline < 3s** at 174k

### 2. Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED at 174k
- **4 TF-IDF modes** pass structural validation:
  - Perfect nesting ≥0.95 (1.0 by construction)
  - Zero fragmentation
  - Monotonic refinement
  - 39 coarse → 412 fine clusters

### 3. Dense Embedding Integration Contract v34 — DEFINED & FROZEN
Four complementary view acceptance criteria:
| Criterion | Threshold | TF-IDF Baseline |
|-----------|-----------|-----------------|
| Citation Heritage AUC | > 0.75 | 0.71–0.74 |
| Cross-Lingual Sachverhalt | > 0.20 | — |
| Cross-Lingual Dispositiv | > 0.10 | — |
| Linear Hybrid Complement | PASS adversarial gates (w=0.3–0.4) | — |

**Role:** COMPLEMENTARY views only — TF-IDF citation hybrids remain PRIMARY product mode (JP 0.78–0.79 vs dense JP 0.05–0.43).

### 4. Preparatory Dense Validation — COMPLETE
- **12k dense embeddings:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS
- **144k checkpoint** (22/26 years, 2000–2021): Fine branch purity ~0.97, improvement rates healthy, strict nesting ≥0.99
- **Frozen v26 flat Leiden:** FAIL (expected — validates scale dependency)

### 5. Negative Results Correctly Preserved
- Calibration FAILS on TF-IDF (thresholds too aggressive for signal density)
- NESTING_METRIC_DEFECT_v1 enforced: all nesting_score ≥ 0.99 claims require scope annotation

---

## Upstream Blocker (No Lane Defect)

**Legal-distance 174k dense embeddings** require:
1. **BGE/bger ID mapping** (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists)
2. **Parquet generation for years 2022–2026** (29,520 decisions missing)
3. **Section extraction** (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

**Action required:** Factory Director decision for corpus lane resumption (per director_note in factory_direction.json v34).

---

## State File Validation

Updated `test_verify.py` to validate actual v34 state schema (was testing outdated v29/v30 schema). All mandatory RESEARCH_PROTOCOL.md fields present and correct:

```json
{
  "lane": "fractal-map",
  "direction_version": 34,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "fractal_map_v34_final_audit_20261004_37164951199",
  "evidence_refs": [...],
  "next_recommendation": "TF-IDF hierarchical production modes at 174k are OPERATIONAL and FROZEN..."
}
```

---

## Conclusion

**No further same-question cycles justified** (`continue_recommended: false`). The fractal-map lane deliverable for factory direction v34 is **COMPLETE and AUDIT-READY**.

**Next action:** Factory Director to (1) update factory_direction.json on main to `fractal-map.status="BLOCKED_ON_DEPENDENCIES"`, (2) resume corpus lane for data acquisition per director_note.