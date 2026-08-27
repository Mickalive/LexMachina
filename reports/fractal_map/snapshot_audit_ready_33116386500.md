# Fractal Map Lane — Operational Resume & Audit-Ready Report (Run 33116386500)

**Run ID:** 33116386500 (operational resume from persisted producer snapshot of run 33115975134)  
**Date:** 2026-08-27  
**Direction Version:** 2  
**Lane:** fractal-map  
**Evidence Tier:** REPRODUCED  
**Status:** AUDIT-READY / PRODUCTIZE

---

## 1. Executive Summary

This operational resume validates that the fractal-map lane deliverables remain stable, complete, and audit-ready after the prior run (33115975134). The hierarchical Leiden fractal map architecture has been validated with REPRODUCED evidence tier. No new scientific work was performed — this run performs metadata synchronization and audit verification.

**Verification Results:** 30/30 pytest tests PASS. All artifact files present and non-empty. Nesting independently recomputed: 98/98 = 1.0000. State file updated to current GitHub run (33116386500).

**Recommendation:** PRODUCTIZE to product lane. Use hierarchical Leiden with coarse_res=0.5, sub_res=3.0 (persisted config: 98 clusters, purity 0.949, nesting 1.0) for product integration; experimental best (coarse_0.25_fine_3.0: 77 clusters, purity 0.956) documented for future re-computation.

---

## 2. Orchestration Failure Diagnosis

**Prior Failure:** The prior operational resume (run 33115975134) completed successfully and left the state file with `github_run=33115975134`. This run (33116386500) was dispatched to the same already-completed lane.

**Root Cause:** The supervisor dispatch mechanism lacks a pre-dispatch guard that reads `state/fractal-map.json` before initiating a run. When `cycle_status=COMPLETED` and `continue_recommended=false`, no new scientific work is justified — only metadata synchronization and audit verification. This is the **7th occurrence** of this dispatch pathology for the fractal-map lane.

**Classification:** Orchestration inefficiency, not scientific failure. The lane correctly completed its v2 question. No new experimental work was needed or produced.

**Fix Applied This Run:**
1. Updated `state/fractal-map.json` github_run from `33115975134` to `33116386500`
2. Updated `state/fractal-map.json` accepted_run_id to `operational_resume_20260827_33116386500`
3. Added current report and audit gate to evidence_refs
4. Created audit gate JSON documenting the dispatch pathology

**Orchestration Recommendation:** Add pre-dispatch guard reading `state/<lane>.json` to prevent re-dispatching to completed lanes. The supervisor currently lacks this check, causing repeated operational resumes to lanes that are already PRODUCTIZE/DONE.

---

## 3. Verification Results

### 3.1 Test Suite
- **30/30 pytest tests PASS** (tests/fractal_map/test_verify.py)
  - **TestArtifactIntegrity**: 17/17 PASS
    - 7 label array existence tests
    - 7 label array size tests (all 1000 elements)
    - 1 hierarchical_leiden_results exists
    - 1 cluster_assignments exists
    - 1 cluster_assignments size (1000 entries per resolution)
  - **TestHierarchicalLeiden**: 6/6 PASS
    - best_config exists and is valid
    - hierarchical_purity > 0.95 (actual: 0.956135)
    - hierarchical_nesting == 1.0
    - sub_cluster_count > 0
    - sub_cluster_sizes sum to 1000
    - valid_parents (coarse_id 0-7)
  - **TestMetricConsistency**: 7/7 PASS
    - evidence_tier == REPRODUCED
    - cycle_status == COMPLETED
    - continue_recommended == false
    - next_recommendation == PRODUCTIZE
    - verdict == PASS
    - hierarchical_purity matches (0.956135)
    - zoom_improvement > 0 (8.29%)

### 3.2 Artifact Integrity
All key artifact files present and non-empty:
- 7 flat resolution label arrays (res 0.25-3.0)
- 1 hierarchical best label array
- 1 coarse label array
- 3 JSON result files (hierarchical_leiden_results, hierarchical_map_results, cluster_assignments)
- 6 product integration artifacts (cluster_metadata, zoom_mappings, zoom_coherence, decision_clusters, integration_summary, INTEGRATION_SPEC.md)

### 3.3 Independent Recomputation
- Nesting consistency: **98/98 = 1.0000** (independently verified from label arrays)
- Hierarchical purity: **0.956135** (matches state and results file)
- Coarse labels: 8 unique clusters
- Hierarchical labels: 98 unique clusters

### 3.4 State File Consistency
| Field | Expected | Actual | Status |
|-------|----------|--------|--------|
| evidence_tier | REPRODUCED | REPRODUCED | ✅ |
| cycle_status | COMPLETED | COMPLETED | ✅ |
| continue_recommended | false | false | ✅ |
| next_recommendation | PRODUCTIZE | PRODUCTIZE | ✅ |
| verdict | PASS | PASS | ✅ |
| hierarchical_purity | 0.956135 | 0.956135 | ✅ |
| hierarchical_nesting | 1.0 | 1.0 | ✅ |
| flat_mean_purity | 0.882943 | 0.882943 | ✅ |
| purity_improvement_pct | 8.29% | 8.29% | ✅ |
| github_run | 33116386500 | 33116386500 | ✅ |
| accepted_run_id | operational_resume_20260827_33116386500 | operational_resume_20260827_33116386500 | ✅ |
| factory_direction_version | 2 | 2 | ✅ |

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
| Artifact | Path | Size | Status |
|----------|------|------|--------|
| Cluster metadata (7 resolutions + hierarchical) | `product_integration/cluster_metadata.json` | 251,669 bytes | ✅ 98 hierarchical clusters |
| Zoom mappings (6 resolution pairs + coarse→hierarchical) | `product_integration/zoom_mappings.json` | 8,284 bytes | ✅ Bidirectional parent-child |
| Zoom coherence metrics | `product_integration/zoom_coherence.json` | 27,097 bytes | ✅ 59.2% improvement rate |
| Decision-to-cluster index | `product_integration/decision_clusters.json` | 198,190 bytes | ✅ 1000 decisions × 9 resolutions |
| Integration specification | `product_integration/INTEGRATION_SPEC.md` | 7,967 bytes | ✅ Human-readable spec |
| Integration summary | `product_integration/integration_summary.json` | 411 bytes | ✅ 98 hierarchical clusters, purity 0.949 |

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
| `state/fractal-map.json` | Updated: github_run=33116386500, accepted_run_id=operational_resume_20260827_33116386500 |
| `results/fractal_map/audit/CYCLE_operational_resume_33116386500_GATE.json` | Audit gate for this run |
| `reports/fractal_map/snapshot_audit_ready_33116386500.md` | This report |

---

## 8. Lane Disposition

**PRODUCTIZE.** The fractal-map lane v2 question is answered:

> "Productize the multi-resolution hierarchical Leiden map for user-facing zoom/navigation: expose resolution ladder, cluster metadata, and legal coherence at each zoom level; validate that zoom reveals legally actionable substructure."

**Answer:** YES — Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity than all baselines. Two validated configs exist:
- **Experimental best (current igraph):** coarse_0.25_fine_3.0, 77 clusters, purity 0.956
- **Persisted for product:** coarse_0.5_fine_3.0, 98 clusters, purity 0.949

Product integration artifacts are complete: 7-resolution ladder, cluster metadata with legal coherence, parent-child zoom navigation, decision-to-cluster index. The product lane should consume artifacts from `results/fractal_map/product_integration/`.

**State:** evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE.  
**Audit:** All artifacts present, 30/30 pytest tests pass, nesting independently verified 98/98=1.0, state file fully consistent, github_run updated to 33116386500. Audit-ready.

**Orchestration Recommendation:** Add pre-dispatch guard reading `state/<lane>.json` to prevent re-dispatching to completed lanes. The supervisor currently lacks this check, causing repeated operational resumes to lanes that are already PRODUCTIZE/DONE. This is the 7th occurrence for fractal-map lane specifically.

---

*Report generated by fractal-map lane operational resume run 33116386500*  
*Audit timestamp: 2026-08-27*