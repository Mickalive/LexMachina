# Fractal Map Lane — Operational Resume & Audit-Ready Report (Run 33112374709)

**Run ID:** 33112374709 (operational resume from persisted producer snapshot of run 33109339667)  
**Date:** 2026-08-27  
**Direction Version:** 2  
**Lane:** fractal-map  
**Evidence Tier:** REPRODUCED  
**Status:** AUDIT-READY / PRODUCTIZE

---

## 1. Executive Summary

This operational resume validates that the fractal-map lane deliverables remain stable, complete, and audit-ready. The hierarchical Leiden fractal map architecture has been validated with REPRODUCED evidence tier.

**Verification Results:** 30/30 pytest tests PASS. All 21 artifact files present and non-empty. State file updated to current GitHub run (33112374709). Workspace factory_direction.json synced from v1 to v2.

**Recommendation:** PRODUCTIZE to product lane. Use hierarchical Leiden with coarse_res=0.5, sub_res=3.0 (persisted config: 98 clusters, purity 0.949, nesting 1.0) for product integration; experimental best (coarse_0.25_fine_3.0: 77 clusters, purity 0.956) documented for future re-computation.

---

## 2. Orchestration Failure Diagnosis

**Prior Failure:** The prior operational resume (run 33109339667) completed successfully but left the state file's `github_run` field pointing to the old run. This was pure metadata drift — no scientific or product failure.

**Root Cause:** The orchestration layer did not update `state/fractal-map.json` with the current `github_run` after the prior resume completed. All 30 validation tests passed in that run; the only issue was metadata synchronization.

**Fix Applied This Run:**
1. Updated `state/fractal-map.json` github_run from `33109339667` to `33112374709`
2. Updated `state/fractal-map.json` accepted_run_id to `operational_resume_20260827_33112374709`
3. Synced workspace `state/factory_direction.json` from v1 to v2 (matching control plane)

---

## 3. Verification Results

### 3.1 Artifact Integrity
- All 21 key artifact files present and non-empty
- 7 label arrays (res 0.25-3.0) + hierarchical + coarse labels correct shape (1000,)
- 3 JSON result files parse correctly
- 6 product integration artifacts validated

### 3.2 Label Array Consistency
| Resolution | Count | Unique Clusters |
|------------|-------|-----------------|
| 0.25 | 1000 | 4 |
| 0.5 | 1000 | 8 |
| 0.75 | 1000 | 12 |
| 1.0 | 1000 | 14 |
| 1.5 | 1000 | 19 |
| 2.0 | 1000 | 24 |
| 3.0 | 1000 | 27 |
| **hierarchical** | **1000** | **98** |
| **coarse_0.5** | **1000** | **8** |

### 3.3 Verification Test Suite
- **30/30 pytest tests PASS** (tests/fractal_map/test_verify.py)
  - TestArtifactIntegrity: 17/17 PASS
  - TestHierarchicalLeiden: 6/6 PASS
  - TestMetricConsistency: 7/7 PASS

### 3.4 State File Consistency
- evidence_tier=REPRODUCED ✅
- cycle_status=COMPLETED ✅
- continue_recommended=false ✅
- next_recommendation=PRODUCTIZE ✅
- verdict=PASS ✅
- hierarchical_purity=0.956135 (matches best config) ✅
- hierarchical_nesting=1.0 ✅
- flat_mean_purity=0.882943 (5-resolution mean) ✅
- purity_improvement_pct=8.29% ✅
- github_run updated to 33112374709 ✅
- accepted_run_id updated to operational_resume_20260827_33112374709 ✅
- factory_direction version=2 ✅

---

## 4. Validated Metrics

### 4.1 Hierarchical Leiden (Validated)
| Config | Coarse Clusters | Fine Clusters | Coarse Purity | Hierarchical Purity | Nesting |
|--------|-----------------|---------------|---------------|---------------------|---------|
| **coarse_0.25_fine_3.0 (BEST)** | 4 | **77** | 0.6352 | **0.9561** | **1.0** |
| coarse_0.5_fine_3.0 (PERSISTED) | 8 | **98** | 0.8642 | **0.9491** | **1.0** |

### 4.2 Flat Leiden Baselines
| Resolution | Clusters | Purity |
|------------|----------|--------|
| 0.5 | 8 | 0.8642 |
| 1.0 | 14 | 0.8617 |
| 1.5 | 19 | 0.8777 |
| 2.0 | 24 | 0.8987 |
| 3.0 | 27 | 0.9124 |
| **Mean** | — | **0.8829** |

### 4.3 Zoom Coherence (Hierarchical)
- Coarse overall purity: 0.8642
- Fine overall purity: 0.9491
- Overall improvement: +9.8%
- Cluster-level improvements: 58, deteriorations: 14, no_change: 26
- Improvement rate: 59.2%

### 4.4 Zoom Coherence (Flat Leiden Ladder)
- 39.6% overall improvement rate, 19 improvements, 0 deteriorations
- Best zoom ratio 0.920 vs flat baseline 0.492

---

## 5. Product Integration Artifacts (All Validated)
| Artifact | Path | Status |
|----------|------|--------|
| Cluster metadata (7 resolutions + hierarchical) | `product_integration/cluster_metadata.json` | ✅ 98 hierarchical clusters |
| Zoom mappings (6 resolution pairs + coarse→hierarchical) | `product_integration/zoom_mappings.json` | ✅ Bidirectional parent-child |
| Zoom coherence metrics | `product_integration/zoom_coherence.json` | ✅ 59.2% improvement rate |
| Decision-to-cluster index | `product_integration/decision_clusters.json` | ✅ 1000 decisions × 9 resolutions |
| Integration specification | `product_integration/INTEGRATION_SPEC.md` | ✅ Human-readable spec |
| Integration summary | `product_integration/integration_summary.json` | ✅ 98 hierarchical clusters, purity 0.949 |

---

## 6. Negative Results Preserved
1. Flat Leiden nesting imperfect (0.59)
2. Agglomerative wins nesting but loses purity
3. Resolution-dependent representation strategy falsified
4. Legal purity ratio <1.0 even at finest zoom
5. ~60% of cluster-resolution pairs show no zoom improvement (already-homogeneous clusters)
6. igraph version sensitivity changes best config but preserves key invariants

---

## 7. Files Updated in This Run
| File | Purpose |
|------|---------|
| `state/fractal-map.json` | Updated: github_run=33112374709, accepted_run_id=operational_resume_20260827_33112374709 |
| `state/factory_direction.json` | Synced from v1 to v2 (matching control plane) |
| `results/audit/fractal-map/CYCLE_operational_resume_33112374709_GATE.json` | Audit gate for this run |
| `reports/fractal_map/snapshot_audit_ready_33112374709.md` | This report |

---

## 8. Lane Disposition

**PRODUCTIZE.** The fractal-map lane v2 question is answered:

> "Productize the multi-resolution hierarchical Leiden map for user-facing zoom/navigation: expose resolution ladder, cluster metadata, and legal coherence at each zoom level; validate that zoom reveals legally actionable substructure."

**Answer:** YES — Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity than all baselines. Two validated configs exist:
- **Experimental best (current igraph):** coarse_0.25_fine_3.0, 77 clusters, purity 0.956
- **Persisted for product:** coarse_0.5_fine_3.0, 98 clusters, purity 0.949

Product integration artifacts are complete: 7-resolution ladder, cluster metadata with legal coherence, parent-child zoom navigation, decision-to-cluster index. The product lane should consume artifacts from `results/fractal_map/product_integration/`.

**State:** evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE.  
**Audit:** All artifacts present, 30/30 pytest tests pass, state file fully consistent, factory_direction synced to v2. Audit-ready.

---

*Report generated by fractal-map lane operational resume run 33112374709*  
*Audit timestamp: 2026-08-27*
