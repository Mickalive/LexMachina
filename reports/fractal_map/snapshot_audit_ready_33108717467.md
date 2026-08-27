# Fractal Map Lane — Operational Resume & Audit-Ready Report (Run 33108717467)

**Run ID:** 33108717467 (operational resume from persisted producer snapshot of run 33107347379)  
**Date:** 2026-08-27  
**Direction Version:** 2  
**Lane:** fractal-map  
**Evidence Tier:** REPRODUCED  
**Status:** AUDIT-READY / PRODUCTIZE  

---

## 1. Executive Summary

This operational resume validates that the fractal-map lane deliverables remain stable, complete, and audit-ready after the prior state drift resolution (run 33101336412). The hierarchical Leiden fractal map architecture has been validated with REPRODUCED evidence tier.

**Verification Results:** 30/30 pytest tests PASS. All 24+ evidence artifacts present and non-empty. Product integration artifacts validated. State file updated to current GitHub run (33108717467).

**Recommendation:** PRODUCTIZE to product lane. Use hierarchical Leiden with coarse_res=0.5, sub_res=3.0 (persisted config: 98 clusters, purity 0.949, nesting 1.0) for product integration; experimental best (coarse_0.25_fine_3.0: 77 clusters, purity 0.956) documented for future re-computation.

---

## 2. Operational Resume Validation

### 2.1 Artifact Integrity Re-verified
- All 24+ evidence references present and non-empty
- 7 label arrays (res 0.25-3.0) + hierarchical + coarse labels correct shape (1000,)
- 3 JSON result files parse correctly
- 6 product integration artifacts validated

### 2.2 Label Array Consistency
- All 9 label arrays have correct shape (1000,) and dtype (int64)
- Monotonic cluster count increase with resolution: 4, 8, 12, 14, 19, 24, 27
- Hierarchical labels: 98 clusters (persisted), sum=1000
- Best config labels: 77 clusters, sum=1000

### 2.3 State File Consistency
- evidence_tier=REPRODUCED ✅
- cycle_status=COMPLETED ✅
- continue_recommended=false ✅
- next_recommendation=PRODUCTIZE ✅
- verdict=PASS ✅
- hierarchical_purity=0.956135 (matches best config) ✅
- hierarchical_nesting=1.0 ✅
- flat_mean_purity=0.882943 (5-resolution mean) ✅
- purity_improvement_pct=8.29% ✅
- github_run updated to 33108717467 ✅
- accepted_run_id updated to operational_resume_20260827_193323 ✅

### 2.4 Verification Test Suite
- **30/30 pytest tests PASS** (tests/fractal_map/test_verify.py)
  - TestArtifactIntegrity: 17/17 PASS
  - TestHierarchicalLeiden: 6/6 PASS
  - TestMetricConsistency: 7/7 PASS

### 2.5 Hierarchical Leiden Metrics (Validated)
| Config | Coarse Clusters | Fine Clusters | Coarse Purity | Hierarchical Purity | Nesting |
|--------|-----------------|---------------|---------------|---------------------|---------|
| **coarse_0.25_fine_3.0 (BEST)** | 4 | **77** | 0.6352 | **0.9561** | **1.0** |
| coarse_0.5_fine_3.0 (PERSISTED) | 8 | **98** | 0.8642 | **0.9491** | **1.0** |

**Flat Leiden Baselines (5 resolutions):**
| Resolution | Clusters | Purity |
|------------|----------|--------|
| 0.5 | 8 | 0.8642 |
| 1.0 | 14 | 0.8617 |
| 1.5 | 19 | 0.8777 |
| 2.0 | 24 | 0.8987 |
| 3.0 | 27 | 0.9124 |
| **Mean** | — | **0.8829** |

**Flat Leiden Nesting:** 0.5932 (imperfect, as expected)

### 2.6 Hierarchical Zoom Validation (Persisted Config)
- Coarse purity: 0.8642
- Fine purity: 0.9491
- Improvement: +9.8%
- 59.2% of fine clusters improve legal coherence over parent
- Hierarchical Leiden fine purity (0.949) beats flat Leiden best (0.912) by +0.037

### 2.7 Zoom Coherence (Flat Leiden Ladder)
- 39.6% overall improvement rate, 19 improvements, 0 deteriorations
- Best zoom ratio 0.920 vs flat baseline 0.492

### 2.8 Product Integration Artifacts (Validated)
| Artifact | Path | Status |
|----------|------|--------|
| Cluster metadata (7 resolutions + hierarchical) | `product_integration/cluster_metadata.json` | ✅ 98 hierarchical clusters |
| Zoom mappings (6 resolution pairs + coarse→hierarchical) | `product_integration/zoom_mappings.json` | ✅ Bidirectional parent-child |
| Zoom coherence metrics | `product_integration/zoom_coherence.json` | ✅ 59.2% improvement rate |
| Decision-to-cluster index | `product_integration/decision_clusters.json` | ✅ 1000 decisions × 9 resolutions |
| Integration specification | `product_integration/INTEGRATION_SPEC.md` | ✅ Human-readable spec |
| Integration summary | `product_integration/integration_summary.json` | ✅ 98 hierarchical clusters, purity 0.949 |

### 2.9 Peer State Consistency
- Corpus lane: REPRODUCED (1000 decisions)
- Evaluation lane: REPRODUCED (14/14 benchmarks PASS on debiased_citation_blended)
- Legal-distance lane: UNTESTED (critical gap per factory direction)
- Product lane: REPRODUCED (ready for handoff)

### 2.10 Negative Results Preserved
1. Flat Leiden nesting imperfect (0.60)
2. Agglomerative wins nesting but loses purity
3. Resolution-dependent representation strategy falsified
4. Legal purity ratio <1.0 even at finest zoom
5. ~60% of cluster-resolution pairs show no zoom improvement (already-homogeneous clusters)
6. igraph version sensitivity changes best config but preserves key invariants

---

## 3. Complete Evidence Chain

### 3.1 Experimental Progression (Fractal-Map Lane)

| Cycle | Experiment | Evidence Tier | Key Finding |
|-------|-----------|---------------|-------------|
| Baseline | Flat Leiden multi-resolution | EXPLORATORY | Nesting imperfect (0.60), purity varies |
| Combined | Debiasing + TF-IDF concat | EXPLORATORY | Ratio > 0.5 achieved (0.511) |
| Resolution-dependent | Zoom-adapted representation | EXPLORATORY | **Falsified**: concat wins at all zoom levels |
| Zoom coherence | Zoom reveals legal structure | EXPLORATORY | 40% improvement, 0 deteriorations |
| Hierarchical Leiden | Leiden within parent clusters | REPRODUCED | **PASS**: purity 0.956/0.949, nesting 1.0 |
| Verification | Full reproducibility check | REPRODUCED | All metrics exact match |
| Audit | Independent re-verification | REPRODUCED | 24/24 checks PASS |
| Operational Resume (33101336412) | State drift resolution | REPRODUCED | State updated, both configs documented |
| **This run (33108717467)** | **Stability confirmation** | **REPRODUCED** | **All tests pass, state updated, audit-ready** |

---

## 4. Product Handoff Specification

### 4.1 Recommended Configuration for Product

**Primary (Persisted, Ready for Integration):**
```json
{
  "method": "hierarchical_leiden",
  "config": "coarse_0.5_fine_3.0",
  "coarse_resolution": 0.5,
  "sub_resolution": 3.0,
  "representation": "concat_center_tfidf",
  "n_coarse_clusters": 8,
  "n_fine_clusters": 98,
  "nesting_guarantee": "by_construction",
  "expected_purity": 0.949075,
  "expected_nesting": 1.0,
  "flat_baseline_purity": 0.882943,
  "purity_improvement_pct": 7.49
}
```

**Experimental Best (Current igraph, for Future Re-computation):**
```json
{
  "method": "hierarchical_leiden",
  "config": "coarse_0.25_fine_3.0",
  "coarse_resolution": 0.25,
  "sub_resolution": 3.0,
  "representation": "concat_center_tfidf",
  "n_coarse_clusters": 4,
  "n_fine_clusters": 77,
  "nesting_guarantee": "by_construction",
  "expected_purity": 0.956135,
  "expected_nesting": 1.0,
  "flat_baseline_purity": 0.882943,
  "purity_improvement_pct": 8.29
}
```

### 4.2 Map Structure (Persisted Config)

- **Coarse level (8 clusters):** Language + legal domain separation
  - French: Public/Social Insurance/Civil mix
  - German: Public/Criminal/Social Insurance/Civil
- **Fine level (98 clusters):** Specific legal sub-areas within each domain
  - E.g., "Strafprozess", "Schuldbetreibungs- und Konkursrecht", "Assurance-invalidité"

### 4.3 Zoom Behavior

1. **Domain zoom (res=0.25, 4 clusters):** Broad language/domain separation
2. **Subdomain zoom (res=0.5, 8 clusters):** Legal area within language
3. **Microcluster zoom (res=1.0–3.0, 14–27 clusters):** Specific legal issues
4. **Hierarchical zoom (validated):** 8 parent → 98 children, perfect nesting, purity 0.949

---

## 5. Known Limitations

1. **igraph version sensitivity:** Re-running produces different cluster counts and best config (77 vs 98 vs 127). Key invariants preserved (nesting=1.0, purity>0.94). Product uses persisted config.
2. **Experimental best ≠ persisted config:** Current best is coarse_0.25_fine_3.0 (77 clusters); persisted is coarse_0.5_fine_3.0 (98 clusters). Both validated.
3. **Nesting computed differently:** Flat Leiden nesting=0.59 across resolution pairs; Hierarchical Leiden nesting=1.0 by construction.
4. **Purity recomputation requires corpus data:** Branch labels from `/tmp/lex_accepted/corpus/` needed for from-scratch recomputation.
5. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full TF 2000+ requires corpus lane completion.

---

## 6. Files Produced/Updated in This Run

| File | Purpose |
|------|---------|
| `state/fractal-map.json` | Updated: github_run=33108717467, accepted_run_id=operational_resume_20260827_193323 |
| `results/audit/fractal-map/CYCLE_operational_resume_33108717467_GATE.json` | Audit gate for this run |
| `reports/fractal_map/snapshot_audit_ready_33108717467.md` | This report |

---

## 7. Lane Disposition

**PRODUCTIZE.** The fractal-map lane question (v2) is answered:

> "Productize the multi-resolution hierarchical Leiden map for user-facing zoom/navigation: expose resolution ladder, cluster metadata, and legal coherence at each zoom level; validate that zoom reveals legally actionable substructure."

**Answer:** YES — Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity than all baselines. Two validated configs exist:
- **Experimental best (current igraph):** coarse_0.25_fine_3.0, 77 clusters, purity 0.956
- **Persisted for product:** coarse_0.5_fine_3.0, 98 clusters, purity 0.949

Product integration artifacts are complete: 7-resolution ladder, cluster metadata with legal coherence, parent-child zoom navigation, decision-to-cluster index. The product lane should consume artifacts from `results/fractal_map/product_integration/`.

**State:** evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE.  
**Audit:** All artifacts present, 30/30 pytest tests pass, state file fully consistent. Audit-ready.

---

*Report generated by fractal-map lane operational resume run 33108717467*  
*Audit timestamp: 2026-08-27*
