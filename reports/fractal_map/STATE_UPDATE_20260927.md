# Fractal Map Lane — State Update for Factory Direction v30

**Date:** 2026-09-27  
**Lane:** fractal-map  
**Direction Version:** 30 (updated from 28)  
**Cycle Status:** BLOCKED_ON_DEPENDENCY  
**Evidence Tier:** EXPLORATORY  
**Continue Recommended:** false  

---

## Executive Summary

The fractal-map lane has completed all justified same-question work under the current factory direction. The lane is **blocked on legal-distance_174k_dense_embeddings**, with only **3/26 years** of dense embeddings actually computed (years 2000-2002), contrary to factory direction v30's claim of 16/26 years (2000-2015).

### Key Validated Results (ACCEPTED Tier)

| Result | Status | Evidence |
|--------|--------|----------|
| TF-IDF 174k flat zoom (v26 rule) | **FAIL** (0/4 modes pass) | `zoom_quality_174k_all_modes_v26.py` |
| TF-IDF 174k constrained hierarchical Leiden | **PASS** (4/4 modes pass) | 4 result files in `constrained_hierarchical_tests/` |
| Scale dependency (12k → 77k) | **CONFIRMED** | 3 hierarchical methods at 77k |
| NESTING_METRIC_DEFECT_v1 | **ENFORCED** | Audit CYCLE_36027099305 |
| Citation-role modes (1k) constrained | **PASS** (3/3 modes) | `constrained_hierarchical_citing_alpha0.3_*` etc. |
| Outcome hybrids (1k) constrained | **PASS** (4/4 modes) | `constrained_hierarchical_cited_decisions_tfidf_outcome_hybrid_*` |

---

## Factory Direction v30 Discrepancy

### Claim in Factory Direction v30
> "Legal-distance dense embedding progress is 16/26 years complete (2000-2015, ~99,325 decisions, ~57% decision completion)"

### Verified Actual Progress
**File:** `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
```json
{
  "completed_years": ["2000", "2001", "2002"],
  "failed_years": []
}
```

**Actual completion:** 3/26 years (2000-2002), approximately 12,570 decisions (~7% decision completion)

**Discrepancy:** Factory direction v30 overstates progress by **13 years** and **~87k decisions**.

### Impact on Fractal Map Lane
- The lane remains **correctly BLOCKED** on `legal-distance_174k_dense_embeddings`
- No same-question cycle is justified until full 174k dense embeddings are delivered
- The evidence-backed zoom path (`constrained_hierarchical_leiden on dense embeddings + citation_role_modes + outcome_hybrids`) cannot be validated at 174k scale

---

## Validated Evidence Summary

### 1. TF-IDF 174k Constrained Hierarchical Leiden — PASS (4/4 modes)

| Mode | Coarse Clusters | Fine Clusters | Branch Purity (coarse→fine) | Area Purity (coarse→fine) | Improvement Rate | Singleton Fraction | Nesting |
|------|----------------|---------------|----------------------------|---------------------------|------------------|-------------------|---------|
| full_text_tfidf_light | 21 | 371 | 0.3530 → 0.3827 | 0.0886 → 0.1195 | 0.9000 | 0.0 | 1.0 |
| regeste_tfidf | 175 | 1,274 | 0.4786 → 0.5665 | 0.2129 → 0.3478 | 0.5752 | 0.0 | 1.0 |
| regeste_full_text_hybrid_0.5 | 85 | 1,118 | 0.4320 → 0.4906 | 0.1541 → 0.2440 | 0.8780 | 0.0009 | 1.0 |
| regeste_full_text_hybrid_0.7 | 107 | 1,326 | 0.4413 → 0.4906 | 0.1730 → 0.2426 | 0.8381 | 0.0008 | 1.0 |

**Config:** `coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters_per_parent=20, adaptive_sub_res=true`

### 2. Scale Dependency — CONFIRMED

| Scale | Method | Improvement Rate | Fragmentation | Nesting |
|-------|--------|------------------|---------------|---------|
| 12k (2000-2002) | Hierarchical Leiden | 0.80 | Zero | 1.0 |
| 77k (2000-2012) | Independent Leiden (flat) | 0.0057 (mean delta) | Low | 0.7207 |
| 77k (2000-2012) | True Hierarchical Leiden | 0.152 | Minimal | 1.0 (by construction) |
| 77k (2000-2012) | Fully Recursive Hierarchical | 0.097 | Severe (77k singletons) | 1.0 (by construction) |

**Finding:** Flat zoom refinement collapses between 12k and 77k; hierarchical Leiden by construction preserves nesting but loses zoom refinement at scale.

### 3. Citation-Role Modes (1k scale) — Constrained Hierarchical PASS

| Mode | Improvement Rate | Fragmentation |
|------|------------------|---------------|
| citing_alpha0.3 | 0.75 | 0% |
| following_alpha0.3 | 0.60 | 0% |
| criticizing_alpha0.3 | 0.625 | 0% |

### 4. Outcome Hybrids (1k scale) — Constrained Hierarchical PASS

| Mode | Improvement Rate | Fragmentation |
|------|------------------|---------------|
| cited_decisions_tfidf | 0.833 | 2.6% |
| cited_decisions_tfidf_outcome_hybrid_0.3 | 0.857 | 0% |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.857 | 0% |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.706 | 0% |

---

## Evidence-Backed Zoom Path (Per Audit CYCLE_36027099305)

The **only credible path** to a 174k fractal map with monotonic zoom refinement:

1. **Constrained hierarchical Leiden** on **dense embeddings** (center_projected_64dim, coarse=0.25, sub=3.0)
2. **Citation-role modes** (citing/following/criticizing) at scale
3. **Outcome hybrids** (cited_decisions_tfidf + outcome) at scale

All three components require **full 174k dense embeddings** from legal-distance lane.

---

## NESTING_METRIC_DEFECT_v1 — Enforced

Per independent audit CYCLE_36027099305 (PASS):

- **7 compressed-family modes:** `nesting_score >= 0.99` claims **PROHIBITED** (honest values: 0.3911–0.9632)
- **2 1000-scale by-construction modes:** `nesting_score = 1.0` **CITEABLE ONLY** with scope annotation + honest ladder means (0.8722 / 0.8644)
- **Compressed 5-level ladder:** NOT universally valid (honest mean change -0.0036, range [-0.0556, +0.115], 21/22 modes nonzero)
- **Accepted ladder claims limited to:** 100% purity-delta retention + identical zoom navigation at shared resolutions

---

## Test Suite Status

**All 230 tests PASS, 1 skipped** (tests/fractal_map/)

Key test categories validated:
- Artifact integrity (label arrays, hierarchical maps, cluster assignments)
- Metric consistency (state evidence_tier, cycle_status, continue_recommended=false, blocked_on)
- Constrained hierarchical validation (all 4 TF-IDF modes PASS, all citation/outcome modes PASS)
- Scale dependency confirmed
- NESTING_METRIC_DEFECT_v1 enforced
- Flat zoom v26 verdict FAIL
- Compressed resolution ladder (100% delta retention, navigation identical)
- Legal-distance scale readiness

---

## Next Recommendation

**No same-question cycle justified.** The lane remains BLOCKED on `legal-distance_174k_dense_embeddings` with only 3/26 years complete. 

**Required to unblock:**
- Legal-distance lane must complete dense embedding computation for years 2003-2025
- At current rate (3 years computed), approximately 23 more year-split jobs needed
- Each year-split job must complete within 65-min CI ceiling on free public runners

**When unblocked:**
1. Run `build_174k_dense_hierarchical.py` on full 174k dense embeddings
2. Evaluate constrained hierarchical Leiden at 174k with v26 success rule
3. Validate citation-role modes and outcome hybrids at 174k
4. If PASS: promote to ACCEPTED tier and wire into product

---

## Files Updated

- `state/fractal-map.json` — direction_version 28→30, added factory_direction_v30_discrepancy field
- `state/fractal_map.json` — direction_version 28→30, added factory_direction_v30_discrepancy field
- `reports/fractal_map/STATE_UPDATE_20260927.md` — This report

---

## Provenance

- All results independently verified by frozen test suite (230 tests)
- NESTING_METRIC_DEFECT_v1 corrections bit-exactly reproduced by independent auditor
- Legal-distance progress.json read directly from `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
- No historical artifacts overwritten; legacy values preserved in state