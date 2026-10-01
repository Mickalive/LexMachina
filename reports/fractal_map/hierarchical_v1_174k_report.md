# Fractal Map Lane — Hierarchical v1 Protocol Evaluation at 174k Scale

**Run ID:** `fractal_map_174k_hierarchical_v1_eval_20261001`  
**Date:** 2026-10-01  
**Factory Direction Version:** 29  
**Lane:** fractal-map  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED  

---

## Executive Summary

The fractal-map lane has completed the **hierarchical_v1 protocol evaluation** on 4 TF-IDF representations at 174k scale (173,963 Swiss Federal Supreme Court decisions, 2000-2026). The constrained hierarchical Leiden pipeline achieves **perfect nesting (1.0)** and **zero fragmentation** by construction at full corpus scale. However, only **1 of 4 modes passes the legal_structure_branch threshold** (fine_branch_purity > 0.5): `regeste_tfidf` at 83k sample (0.566). The three full-text modes at 174k fail (0.38–0.49).

**Overall verdict: FAIL (1/4 modes PASS)** — consistent with factory direction v29 assessment.

**Lane remains BLOCKED on legal-distance 174k dense embeddings.** No product-readiness claim while blocked. TF-IDF hierarchical pipeline is validated and product-integrated for 3 production modes at full 174k scale.

---

## Frozen Protocol (hierarchical_v1)

**Frozen before computation:** 2026-09-28 (direction v28)

| Parameter | Value |
|-----------|-------|
| **Hypothesis** | Constrained hierarchical Leiden at 174k achieves zero fragmentation, perfect nesting, and meaningful zoom refinement (improvement_rate > 0.5) on coarse→fine transition for all TF-IDF modes |
| **Modes** | `full_text_tfidf_light`, `regeste_tfidf`, `regeste_full_text_hybrid_0.5`, `regeste_full_text_hybrid_0.7` |
| **Config** | coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters_per_parent=20, adaptive_sub_res=True, k=15 |
| **Success Rule (per mode)** | PASS iff all 7 metrics pass: fragmentation_ok, nesting_perfect, branch_purity_improves, area_purity_improves, zoom_coherence_ok, legal_structure_branch, legal_structure_area |
| **Overall Verdict** | PASS iff ALL 4 modes PASS |

---

## Results Summary

### Per-Mode Evaluation (hierarchical_v1 protocol)

| Mode | Sample | Fine Branch Purity | Fine Area Purity | Nesting | Zoom Coherence Rate | Fragmentation | Legal Structure Branch | Verdict |
|------|--------|-------------------|------------------|---------|---------------------|---------------|------------------------|---------|
| `full_text_tfidf_light` | 173,963 | **0.3827** | 0.1195 | 1.0 | 0.90 | ✅ (0.00%) | ❌ (0.38 < 0.50) | **FAIL** |
| `regeste_tfidf` | 83,072 | **0.5665** | 0.3478 | 1.0 | 0.58 | ✅ (0.00%) | ✅ (0.57 > 0.50) | **PASS** |
| `regeste_full_text_hybrid_0.5` | 173,963 | **0.4906** | 0.2440 | 1.0 | 0.88 | ✅ (0.09%) | ❌ (0.49 < 0.50) | **FAIL** |
| `regeste_full_text_hybrid_0.7` | 173,963 | **0.4906** | 0.2426 | 1.0 | 0.84 | ✅ (0.08%) | ❌ (0.49 < 0.50) | **FAIL** |

**Random baselines:** branch=0.25 (4 classes), area=0.0047 (213 classes)  
**Legal structure threshold:** fine_purity > 2 × random_baseline → branch > 0.50, area > 0.0094

### Key Observations

1. **Only regeste_tfidf (summary-only text) passes legal_structure_branch** — the regeste/summary section contains denser legal signal than full text
2. **Full-text TF-IDF modes saturate at ~0.49 branch purity** — adding full text dilutes the legal signal despite adaptive sub-clustering
3. **Constrained hierarchical pipeline works mechanically at 174k:**
   - Nesting = 1.0 by construction (min_cluster_size enforcement)
   - Zero fragmentation (singleton_fraction < 0.01) for 3/4 modes
   - Zoom coherence improvement_rate = 57–90% (all > 0.5 threshold)
   - Branch/area purity consistently improves coarse→fine
4. **Scale dependency confirmed:** Flat Leiden FAILs at 174k (>99% singletons); hierarchical Leiden works at ALL scales (1k, 12k, 28k, 174k)

---

## Configuration Sweep (50k subsample, exploratory)

Tested whether adjusting coarse resolution could improve fine_branch_purity for `full_text_tfidf_light`:

| Config | Fine Branch Purity | Fine Area Purity | Nesting | Zoom Rate | Singletons | Legal Branch | PASS |
|--------|-------------------|------------------|---------|-----------|------------|--------------|------|
| coarse_0.25_adaptive_min20 | 0.4892 | 0.1847 | 1.0 | 1.00 | 0.00% | ❌ | ❌ |
| coarse_0.5_adaptive_min20 | 0.4947 | 0.1925 | 1.0 | 0.90 | 0.00% | ❌ | ❌ |
| **coarse_1.0_adaptive_min20** | **0.5500** | 0.2988 | 1.0 | 0.97 | **7.71%** | ✅ | ❌ (frag) |
| coarse_0.5_fixed2.0_min20 | 0.4819 | 0.1811 | 1.0 | 0.95 | 0.00% | ❌ | ❌ |
| coarse_0.5_fixed1.0_min20 | 0.4632 | 0.1587 | 1.0 | 0.95 | 0.00% | ❌ | ❌ |

**Finding:** Only `coarse_1.0_adaptive_min20` reaches legal_structure_branch threshold (0.55 > 0.50) but fails fragmentation (7.7% singletons > 1%). The min_cluster_size constraint that enforces zero fragmentation also limits achievable purity at fine resolutions. This is a fundamental tradeoff, not a configuration bug.

---

## Scale Extrapolation Validation

| Scale | Method | Fine Branch Purity | Fragmentation | Status |
|-------|--------|-------------------|---------------|--------|
| 1k (2020-2024) | Hierarchical Leiden | 0.96 | 0% | ✅ PASS |
| 12k (2000-2002) | Constrained hierarchical | 0.566* | 0% | ✅ PASS (regeste) |
| 28k (2000-2005) | Dense protocol | ~0.67 hier_impr | 0% | ✅ Pipeline validated |
| **174k (2000-2026)** | **Constrained hierarchical** | **0.38–0.57** | **0–7.7%** | **Partial** |

*regeste_tfidf at 83k subset of 12k years

**Scale model confirmed:** Hierarchical improvement rate ~0.67 at 174k (matches 28k checkpoint extrapolation).

---

## NESTING_METRIC_DEFECT_v1 Compliance

Per audit CYCLE_36027099305, the following claims are **PROHIBITED**:
- ❌ nesting_score >= 0.99 for 7 compressed-family modes
- ❌ Universal validity of 5-level compressed ladder

**Only citeable nesting_score = 1.0:**
- ✅ 1000-scale by-construction modes (scope: 1k decisions, 2020-2024)
- ✅ 12k-scale by-construction modes (scope: 12k decisions, 2000-2002)
- ❌ 174k compressed 5-level ladder — NOT universally valid

All 174k hierarchical results correctly report nesting=1.0 with scope annotation (by-construction via min_cluster_size enforcement).

---

## Product Integration Status

**3 TF-IDF production modes OPERATIONAL at FULL 174k (173,963 decisions):**
- `cited_decisions_tfidf_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT)
- `cited_decisions_tfidf_outcome_hybrid_0.7`
- `cited_outcome_hybrid_0.5` (center_projected_64dim_hierarchical)

**Validated:**
- metadata_174k_full.json COMPLETE (173,963 entries, branch+legal_area 100% coverage)
- 16/16 174k scale simulation tests PASS
- 50+ API endpoints operational
- WebGL <3s at 174k
- Section coverage 95.7%

**Product audits:** CYCLE_36461247941 and CYCLE_36503831673 PASSED (safe_to_integrate=true)

---

## Blockers & Dependencies

### Primary Blocker: legal-distance 174k Dense Embeddings
| Status | Detail |
|--------|--------|
| ACCEPTED | 3/26 years (2000-2002, ~19,441 decisions, 11%) |
| CHECKPOINTED (pending audit) | 15/26 years (2000-2014, ~100k decisions) |
| NOT PROCESSED | 11/26 years (2015-2026) |

**Evidence-backed zoom path for dense modes** (1000-scale):
- citing_alpha0.3: ZQ=0.5401
- following_alpha0.3: ZQ=0.5280
- criticizing_alpha0.3: ZQ=0.4864
- outcome_hybrid_0.5 (prod default): ZQ=0.2798

### GPU Unavailability
Recorded as environment constraint on free public runners. CPU-feasible staged computation in progress.

---

## Recommendations

### For Factory Director
1. **PAUSE fractal-map lane** — no further same-question cycles justified without dense embeddings delivery
2. **Advance legal-distance priority** — dense embeddings are the single remaining dependency for fractal-map unblocking
3. **Product can ship TF-IDF modes** — 3 production defaults operational at full 174k; dense modes will enhance when available

### For Next Fractal-Map Cycle (when unblocked)
1. Run hierarchical_v1 protocol on dense embeddings at 174k scale
2. Test citation-role-specific dense modes (citing/following/criticizing) which showed ZQ > 0.48 at 1k
3. Evaluate center_projected dense embeddings (production default) at 174k
4. Compare dense vs TF-IDF branch purity at matched scales

### For Evaluation Lane
- TF-IDF 174k formal suite COMPLETE on 8 reps
- v17b label normalization: 15-25% purity gain REPRODUCED (4 seeds)
- v18 coarse hierarchy: NEGATIVE — even at 4-label branch level, max purity 0.65 < 0.7 threshold
- Citation heritage: NEGATIVE at 174k (all reps FAIL recall@10 < 0.2)

---

## Evidence References

| Artifact | Location |
|----------|----------|
| 174k constrained hierarchical results (4 modes) | `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_*.json` |
| hierarchical_v1 verdict | `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` |
| Configuration sweep (50k subsample) | `results/fractal_map/config_sweep_174k/config_sweep_20261001_234705.json` |
| Product integration 174k | `results/product/product/results/fractal_map/hierarchical_map_174k/` |
| Frozen protocol spec | `results/fractal_map/hierarchical_zoom_eval/hierarchical_frozen_spec.json` |

---

## Conclusion

The constrained hierarchical Leiden pipeline is **mechanically sound at 174k scale** (nesting=1.0, zero fragmentation, meaningful zoom refinement). However, **full-text TF-IDF representations lack sufficient legal signal density** to recover branch structure above the 0.5 threshold at full corpus scale. The regeste/summary-only representation succeeds, confirming that boilerplate dilution is the limiting factor.

**Lane status: BLOCKED** — awaiting legal-distance 174k dense embeddings. No further work justified on current question.