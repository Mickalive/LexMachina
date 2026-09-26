# Fractal Map Lane — Final Operational Confirmation

**Factory Direction Version:** 27  
**Lane Status:** BLOCKED_ON_DEPENDENCY  
**Evidence Tier:** ACCEPTED  
**Run ID:** Operational confirmation cycle  
**Date:** 2026-09-26

---

## Executive Summary

The fractal-map lane remains **correctly BLOCKED** on the single dependency `legal-distance_174k_dense_embeddings`. No same-question cycle is justified (`continue_recommended: false`).

### Current State Verification

| Component | Status | Evidence |
|-----------|--------|----------|
| TF-IDF 174k zoom-quality evaluation | **COMPLETE (FAIL)** | All 4 decision-mappable TF-IDF modes fail frozen v26 success rule |
| Dense embeddings evaluation pipeline | **VERIFIED & READY** | All 14 infrastructure tests PASS; 1 skipped (no dense embeddings yet) |
| 174k metadata | **ACCESSIBLE** | `/tmp/lex_accepted/evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Legal-distance dense embeddings progress | **3/26 years (12,570/174,113 = ~7%)** | Years 2000-2002 complete; 2003-2025 pending |
| Hierarchical Leiden builder for 174k | **BUILT & VALIDATED** | `build_174k_dense_hierarchical.py` tested on 1000-scale center_projected_768 |

---

## Key Findings (Reconfirmed)

1. **TF-IDF 174k modes encode strong legal structure** (branch purity 0.51-0.55 vs 0.25 random; legal_area purity 0.24-0.31 vs ~0.005 random) but **FAIL all three frozen zoom-quality checks**; fine ladder over-fragmented (median cluster size 1.0, singleton fraction >99%)

2. **Strict nesting is LOW** at coarse transitions (0.44-0.61) because independent Leiden partitions don't respect hierarchy — NESTING_METRIC_DEFECT_v1 confirmed and enforced

3. **Evidence-backed zoom path confirmed at partial scale**: Dense embeddings (`center_projected_64dim`) + hierarchical Leiden (coarse=0.25, sub_res=3.0) = **coherent zoom path** — FIRST PASS of v26 success rule at 62k scale (2000-2010)

4. **64-dim is the optimal sweet spot** (consistent with legal-distance adversarial validation); 768-dim and 128-dim FAIL rate_ok

5. **Citation-role modes at 1000-scale** (citing_alpha0.3 ZQ=0.5401, following 0.5280, criticizing 0.4864) remain the evidence-backed zoom path but lack 174k dense embeddings

5. **Scale dependency confirmed**: 12k FAIL vs 62k PASS for center_projected_64dim+sub_res=3.0 demonstrates zoom refinement requires sufficient corpus density — correct behavior, not pipeline defect

---

## Preparatory Work Completed (This Cycle)

| Artifact | Description | Status |
|----------|-------------|--------|
| `fractal_map/hierarchical/build_174k_dense_hierarchical.py` | 174k-scale hierarchical Leiden pipeline for dense embeddings | ✅ Built & validated on 1000-scale |
| `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` | General zoom-quality + nesting evaluation for dense modes | ✅ Ready (frozen v26 success rule) |
| `tests/fractal_map/test_dense_embeddings_infrastructure.py` | Guard tests for evaluation pipeline | ✅ 14/15 PASS (1 skipped - expected) |
| Local UMAP zoom-conditioned neighborhoods | 5 coarse clusters → 2D local maps for fine-grained navigation | ✅ Implemented |
| ProductMapLoader compatibility | Verified existing dense hierarchical modes load successfully | ✅ Compatible |

---

## Evaluation Pipeline Readiness Checklist

✅ **Pipeline script**: `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` — functional  
✅ **Dependencies**: Leiden, igraph, scikit-learn, UMAP — installed and working  
✅ **Metadata**: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries, branch+legal_area 100% coverage) — accessible  
✅ **Success rule**: v26 frozen spec — implemented and validated  
✅ **Hierarchical Leiden**: Coarse (res=0.25) + fine (sub_res=3.0) — functional, guarantees nesting=1.0  
✅ **Flat Leiden at intermediate resolutions**: 0.5, 1.0, 2.0 — functional  
✅ **Metrics**: branch purity, area purity, zoom coherence, strict nesting, fragmentation — all implemented  
✅ **Output format**: JSON with full provenance (timestamp, embedding path, config) — compliant  

---

## Next Steps (When Dependency Resolves)

1. **Wait** for legal-distance to complete year-split dense embedding computation (2003-2025)
2. **Combine** year-split embeddings into full 174k matrix (or evaluate incrementally)
3. **Run** `evaluate_174k_dense_embeddings.py` on full 174k center_projected_64dim embeddings
4. **Test** hierarchical Leiden with sub_res=3.0 (validated sweet spot)
5. **Compare** against TF-IDF 174k baseline (already evaluated: FAIL — over-fragmented)
6. **Validate** citation-role modes at 174k scale (currently BLOCKED — placeholder-keyed)
7. **Update** fractal-map state with full 174k verdict

---

## Recommended State (Unchanged)

- **Lane status**: BLOCKED_ON_DEPENDENCY
- **continue_recommended**: false (no same-question cycle justified)
- **Evidence tier**: ACCEPTED (pipeline verified, partial-scale evidence confirmed)
- **Blocking dependency**: legal-distance_174k_dense_embeddings
- **Readiness**: EVALUATION PIPELINE READY — zero code changes needed

---

## Orchestration Note (Reconfirmed)

The supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (fractal-map.status=RUN) instead of workspace `state/fractal_map.json` (BLOCKED_ON_DEPENDENCY) — 60+ documented re-dispatch occurrences. Factory Director must update supervisor dispatch logic to read the authoritative workspace state.

---

## Evidence References

- `state/fractal_map.json` — Current lane state (BLOCKED_ON_DEPENDENCY, continue_recommended=false)
- `reports/fractal_map/DENSE_EMBEDDINGS_PIPELINE_VERIFICATION_20260926.md` — Pipeline verification report
- `reports/fractal_map/fractal_map_174k_zoom_quality_report_v27.md` — TF-IDF 174k evaluation report
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — Complete per-mode results
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json` — Frozen-before-compute specification
- `results/fractal_map/zoom_quality_174k_eval/dense_embeddings_2000_2010_*.json` — Partial validation artifacts (62k scale PASS)
- `fractal_map/hierarchical/build_174k_dense_hierarchical.py` — 174k builder pipeline
- `tests/fractal_map/test_dense_embeddings_infrastructure.py` — Infrastructure guard tests

---

## Conclusion

**The fractal-map lane is correctly blocked and the evaluation pipeline is production-ready.** No further work is justified on the current question until dense embeddings arrive. The factory director should monitor legal-distance progress and dispatch the next fractal-map cycle when 174k dense embeddings are available in accepted state.

All valid completed work preserved. Snapshot AUDIT-READY.
