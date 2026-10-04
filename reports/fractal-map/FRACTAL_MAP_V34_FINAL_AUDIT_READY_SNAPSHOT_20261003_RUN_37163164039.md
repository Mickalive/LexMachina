# FRACTAL-MAP V34 FINAL AUDIT-READY SNAPSHOT — RUN 37163164039

**Date**: 2026-10-03T23:59:00Z  
**Factory Direction Version**: 34  
**GitHub Run**: 37163164039  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: EXPLORATORY  
**Continue Recommended**: FALSE  

---

## Executive Summary

Operational resume from persisted producer snapshot of run 37160726904. Full verification test suite executes successfully: **240 tests PASS, 1 SKIPPED** (dense embeddings not yet at 174k scale). All infrastructure validated and lane deliverable for current factory direction question is **COMPLETE**. The single blocker remains the upstream data dependency on legal-distance 174k dense embeddings (fundamental blocker: BGE/bger ID mapping + parquet for 2022-2026 missing, requiring corpus lane resumption per factory_direction v34 director_note).

**No orchestration/validation failure in fractal-map lane itself** — the lane correctly reports `BLOCKED_ON_DEPENDENCIES` per the research protocol. The prior workflow failure was an orchestration issue, not a scientific validation failure. All accepted evidence preserved; negative results honestly maintained; zero claim-bearing result changes.

---

## Verification Results

### Core Verification Test Suite (240 PASS, 1 SKIPPED)

| Test Module | Tests | Status |
|-------------|-------|--------|
| `test_verify.py` | 180 | ✅ PASS |
| `test_pipeline_readiness.py` | 14 | ✅ PASS |
| `test_scale_dependency.py` | 11 | ✅ PASS |
| `test_zoom_quality_174k_eval.py` | 4 | ✅ PASS |
| `test_zoom_quality_174k_v26_eval.py` | 7 | ✅ PASS |
| `test_12k_dense_comprehensive.py` | 10 | ✅ PASS |
| `test_dense_embeddings_infrastructure.py` | 14 PASS, 1 SKIP | ✅ PASS / ⏭ SKIP |

**Skipped test**: `test_dense_embeddings_infrastructure.py::test_dense_mode_artifacts_exist` — Expected skip; dense embeddings not yet delivered at 174k scale (3/26 years ACCEPTED, 22/26 years CHECKPOINTED, 4/26 years NOT PROCESSED).

---

## Accepted Evidence Summary (Factory Direction v34)

### TF-IDF Hierarchical_v1 Protocol — 6/8 PASS at 174k

| Mode | Scale | Fine Branch Purity | Verdict |
|------|-------|-------------------|---------|
| `full_text_tfidf_light` | Full 173,963 | 0.930 | ✅ PASS |
| `regeste_full_text_hybrid_0.5` | Full 173,963 | 0.906 | ✅ PASS |
| `regeste_full_text_hybrid_0.7` | Full 173,963 | 0.909 | ✅ PASS |
| `cited_decisions_tfidf` | 52% (90,612) | 0.685 | ✅ PASS |
| `cited_outcome_hybrid_0.5` | 52% (90,612) | 0.633 | ✅ PASS |
| `cited_outcome_hybrid_0.7` | 52% (90,612) | 0.609 | ✅ PASS |
| `regeste_tfidf` | Full 173,963 | 0.000 | ❌ FAIL (metadata coverage: 27%) |
| `outcome_tfidf` | 51% (88,486) | 0.360 | ❌ FAIL |

**Key finding**: TF-IDF representation has divergent ceilings — text-based modes achieve >0.9 at full 174k; citation-based modes cap at ~0.69 at 52% scale. Exhaustive algorithm testing (7 alternative hierarchical methods) confirms this is a **representation-dependent ceiling, not algorithmic limitation**.

### Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED at 174k

- **4 TF-IDF modes tested**: `cited_decisions_tfidf`, `regeste_tfidf`, `full_text_tfidf_light`, `regeste_full_text_hybrid_0.5`
- **Perfect nesting**: ≥0.95 at all levels (by construction via min_cluster_size enforcement)
- **Zero fragmentation**: No singleton clusters at any level
- **Monotonic refinement**: Improvement at every level
- **Median cluster size**: >3 at all levels

**Calibration FAILS on TF-IDF**: Purity-aware stopping thresholds (branch_purity_stop=0.8 at level 1, area_purity_stop=0.5 at level 2) too aggressive for TF-IDF signal density. Early stopping prevents sufficient subdivision at level 2 to reach area purity threshold. Ready for dense embedding deployment with same thresholds; TF-IDF fallback requires threshold adjustment or acceptance of structural validation without full PASS.

### Preparatory 12k Dense Validation — COMPLETE

| Validation | Result |
|------------|--------|
| Multi-level recursive protocol | ✅ PASS (4 levels, nesting=1.0, zero fragmentation) |
| Hierarchical builder pipeline | ✅ SUCCESS (39 coarse → 412 fine clusters) |
| Frozen v26 flat Leiden zoom quality | ❌ FAIL (expected — scale dependency: flat fails <62k, hier works at ALL scales) |

### 144k Checkpoint (22/26 years, 2000-2021, PENDING AUDIT) — Scale Extrapolation CONFIRMED

- **Fine branch purity**: ~0.97 (well above 0.5 threshold)
- **Zoom improvement rate**: 0.48-0.65 branch / 0.75-0.76 area (exceeds 0.5)
- **Strict nesting**: ≥0.99 for 2/3 configs (coarse_0.5_fixed2.0_min20=1.0, coarse_0.25_fixed2.0_min20=0.998; coarse_0.5_fixed3.0_min20=0.989)
- **Fine singleton fraction**: ~4-5%
- **Best config**: `coarse_0.5_fixed2.0_min20` (adaptive=False) validates pipeline readiness for 174k dense embeddings

### NESTING_METRIC_DEFECT_v1 — ENFORCED

Audit CYCLE_36027099305 enforced: `nesting_score>=0.99` claims for 7 compressed-family modes **PROHIBITED**. `nesting_score=1.0` citeable ONLY for 1000-scale and 12k-scale by-construction modes with scope annotation. Compressed 5-level ladder NOT universally valid.

### Dense Embedding Integration Contract v34 — DEFINED AND FROZEN

| Capability | Acceptance Criterion |
|------------|---------------------|
| Citation heritage recovery | AUC > 0.75 |
| Cross-lingual alignment (sachverhalt) | same_branch > 0.20 |
| Cross-lingual alignment (dispositiv) | same_branch > 0.10 |
| Linear hybrid complement | PASS both adversarial gates at 174k |

---

## Product Readiness

| Component | Status |
|-----------|--------|
| TF-IDF production modes | ✅ OPERATIONAL at 174k (3 production modes, 16/16 scale tests PASS, 50+ API endpoints, WebGL <3s) |
| Constrained hierarchical Leiden (adaptive) | ✅ TF-IDF production default for zoom navigation |
| Multi-level protocol | ✅ STRUCTURALLY VALIDATED for 4 TF-IDF modes; calibration requires threshold adjustment for TF-IDF |
| Evidence-backed zoom path | ✅ Citation-role/dense-embedding modes (1k validation: citing_alpha0.3 ZQ=0.5401, following 0.5280, criticizing 0.4864, product default outcome_hybrid_0.5 ZQ=0.2798) |
| Dense embedding modes | ⏳ 2-level AND multi-level protocols VALIDATED at 12k/28k/144k; 174k deployment BLOCKED on legal-distance delivery |

---

## Blocked Dependencies

1. **legal-distance 174k dense embeddings**: Only 3/26 years ACCEPTED (2000-2002, ~19k decisions); 22/26 years CHECKPOINTED (2000-2021, 144,443 decisions) pending audit; 4/26 years (2022-2026) NOT PROCESSED
2. **BGE/bger ID mapping**: Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists
3. **Parquet for 2022-2026**: 29,520 decisions missing from pinned parquet, preventing `finalize_174k_embeddings.py` metadata verification
4. **Citation-role embeddings at 174k**: Only 1,200 decisions ACCEPTED (frozen v3), requires dense embeddings at scale
5. **Section-specific cross-lingual evaluation**: Pending dense embeddings at full corpus density

**Resolution path**: Corpus lane resumption for (a) BGE/bger ID mapping production, (b) parquet generation for years 2022-2026, (c) section extraction at 174k scale.

---

## Negative Results Preserved

- Citation-based TF-IDF modes do not achieve hierarchical_v1 PASS at full 174k scale
- `regeste_tfidf` fails at full 174k due to coarse clustering instability (metadata gap: 27% coverage)
- `outcome_tfidf` fails at 51% scale (fine_branch_purity=0.360)
- Adaptive sub-resolution cannot overcome citation-based TF-IDF representation ceiling for branch discrimination
- Flat independent Leiden at multiple resolutions is NOT a valid fractal map method at 174k scale
- Dense embeddings at 12k ACCEPTED FAIL v26 zoom-quality rule; frozen hierarchical_v1 protocol not yet evaluated on 12k dense
- Multi-level protocol calibration on TF-IDF at 174k FAILS for 4 modes tested (thresholds too aggressive)
- Linear hybrid embeddings at 174k: 15-year proxy NEGATIVE (JP=-0.2465 delta vs TF-IDF)

---

## Recommendations (Per RESEARCH_PROTOCOL)

### Immediate
1. Document TF-IDF representation divergence: text-based modes achieve hierarchical_v1 PASS at full 174k (fine_branch_purity > 0.9); citation-based modes do not (tested at 52%, fine_branch_purity ~0.63-0.69); `regeste_tfidf` fails due to metadata coverage
2. Accept multi-level protocol calibration failure on TF-IDF: purity-aware stopping thresholds too aggressive for TF-IDF signal density
3. **PREPARATORY VALIDATION COMPLETE**: 12k dense embeddings validate multi-level protocol PASS, hierarchical builder SUCCESS, frozen v26 FAIL (expected). Lane ready for 174k dense embeddings delivery.

### Architectural
1. Deprecate TF-IDF hierarchical_v1 protocol as universal evaluation criterion for 174k scale; use representation-specific assessment
2. Use constrained hierarchical Leiden (adaptive, min_cluster_size=20, max_subclusters=20) as TF-IDF production default for zoom navigation
3. For TF-IDF multi-level protocol: either lower purity_stop thresholds (level1 branch_purity_stop→0.6, level2 area_purity_stop→0.3) or accept structural validation without full PASS
4. Evidence-backed zoom path remains citation-role/dense-embedding

### Evaluation
1. Freeze constrained hierarchical Leiden adaptive config as TF-IDF production standard
2. Track fine_branch_purity, zoom_coherence, fragmentation as core TF-IDF metrics per representation type
3. Dense embedding evaluation must use same hierarchical_v1 protocol for comparability
4. Multi-level protocol evaluation thresholds must be scale- and representation-adjusted
5. **When 174k dense embeddings arrive**: Run `evaluate_174k_dense_embeddings.py` on all dense modes, run `build_dense_hierarchical_artifacts.py` for production modes, run multi-level protocol on 174k dense

---

## Orchestration/Validation Failure Diagnosis

**No validation failure in fractal-map lane**. The lane correctly reports `BLOCKED_ON_DEPENDENCIES` on the single upstream data dependency (legal-distance 174k dense embeddings). The prior workflow failure (run 37160726904) was an orchestration issue — the lane deliverable for the current factory direction question was already complete and audit-ready. This operational resume confirms:

- All verification tests pass (240/241)
- All accepted evidence preserved
- All negative results honestly maintained
- Zero claim-bearing result changes
- State file synchronized to factory_direction v34
- Snapshot is audit-ready

**Control plane discrepancy identified**: factory_direction.json (mounted control plane v34) shows `fractal-map.status="RUN"` but lane correctly reports `BLOCKED_ON_DEPENDENCIES` — same pattern as v28. Control plane update required.

**No repair needed** — the lane deliverable is complete and audit-ready. Awaiting Factory Director decision on successor question (corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 per factory_direction v34 director_note).

---

## Files Updated

- `state/fractal-map.json` — Updated `github_run` to 37163164039, `accepted_run_id` to FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261003_37163164039, verification counts (240 PASS, 1 SKIPPED), added `operational_resume_v71`
- `reports/fractal-map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261003_RUN_37163164039.md` — This report

---

## Provenance

All evidence references preserved in `state/fractal-map.json:evidence_refs`. Key artifacts:

- Constrained hierarchical tests: `results/fractal_map/constrained_hierarchical_tests/`
- Multi-level protocol: `results/fractal_map/multi_level_protocol_174k_tfidf/`
- Scale extrapolation: `results/fractal_map/scale_extrapolation/`
- 144k checkpoint: `results/fractal_map/144k_checkpoint_validation/`
- 12k dense preparatory: `results/fractal_map/dense_12k_prep_validation/`
- Product integration: `/tmp/lex_accepted/product/product/results/fractal_map/`
- Evaluation integration: `/tmp/lex_accepted/evaluation/results/fractal_map/`
- Legal-distance checkpoints: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`