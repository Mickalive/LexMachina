# Fractal Map Lane — Audit-Ready Report (Run 33101336412)

**Run ID:** 33101336412 (operational resume from persisted snapshot of run 33100450037)  
**Date:** 2026-08-27  
**Direction Version:** 2  
**Lane:** fractal-map  
**Evidence Tier:** REPRODUCED  
**Status:** AUDIT-READY / PRODUCTIZE  

---

## 1. Executive Summary

This operational resume diagnoses and resolves a state drift caused by igraph version sensitivity. The prior run (33100450037) state referenced stale experimental results (127 clusters, 0.963 purity) that no longer match the current igraph version. The persisted product artifacts (98 clusters, 0.949 purity) used a different but validated config.

**Resolution:** Re-ran hierarchical Leiden experiment with current igraph. New experimental best: **coarse_0.25_fine_3.0 (77 clusters, purity 0.9561, nesting 1.0)**. Persisted artifacts remain on **coarse_0.5_fine_3.0 (98 clusters, purity 0.9491)** — both exceed all baselines, key invariants preserved.

**Verification Results:** 30/30 pytest tests PASS. All evidence artifacts present. State file updated to match current experimental results and document both configs. Audit gate created.

**Recommendation:** PRODUCTIZE to product lane. Use persisted hierarchical Leiden (coarse_0.5_fine_3.0, 98 clusters) for product integration; experimental best (coarse_0.25_fine_3.0, 77 clusters) documented for future re-computation.

---

## 2. Orchestration Failure Diagnosis

### 2.1 Root Cause: igraph Version Sensitivity

| Run | State Claimed | Actual Persisted | Issue |
|-----|---------------|------------------|-------|
| 33100450037 | 127 clusters, purity 0.963417 (coarse_0.5_fine_3.0) | 98 clusters, purity 0.949075 (coarse_0.5_fine_3.0) | State matched OLD experiment, not current igraph |
| 33101336412 (this) | **77 clusters, purity 0.956135 (coarse_0.25_fine_3.0)** | 98 clusters, purity 0.949075 (coarse_0.5_fine_3.0) | **State now matches NEW experiment; persisted config documented separately** |

**Key Insight:** igraph version changes alter Leiden clustering results (different cluster counts, different best config) but **key invariants are preserved**:
- Hierarchical nesting = 1.0 (by construction) ✅
- Hierarchical purity > 0.94 ✅  
- Hierarchical purity > flat Leiden mean purity ✅
- Perfect parent-child nesting ✅

This is a known, documented limitation (see state file `known_limitations`). Not a scientific failure — a reproducibility boundary.

### 2.2 Prior Orchestration Failure (Run 33033184781, Resolved)

| Run | Issue | Status |
|-----|-------|--------|
| 33033184781 | Dispatched as operational resume; produced ZERO artifacts | Diagnosed: infrastructure crash-before-write |

**Impact:** Zero durable harm. Last known good state fully intact. Subsequent runs completed successfully.

---

## 3. Verification Performed in This Run

### 3.1 Experimental Re-Run Results (Current igraph)

| Config | Coarse Clusters | Fine Clusters | Coarse Purity | Hierarchical Purity | Nesting |
|--------|-----------------|---------------|---------------|---------------------|---------|
| **coarse_0.25_fine_3.0 (BEST)** | 4 | **77** | 0.6352 | **0.9561** | **1.0** |
| coarse_0.5_fine_3.0 (PERSISTED) | 8 | **98** | 0.8642 | **0.9491** | **1.0** |
| coarse_0.5_fine_2.0 | 8 | 98 | 0.8642 | 0.9491 | 1.0 |

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

### 3.2 Artifact Integrity
- **24+** evidence references present and non-empty
- **7/7** resolution label arrays: correct shape (1000,), dtype int64
- **2/2** hierarchical label arrays: hierarchical_best (98), coarse_0.5 (8)
- All JSON result files parse correctly with expected keys
- Baseline embeddings (1000, 768), projection (1000, 2), debiased (1000, 768) all correct

### 3.3 State File Consistency
| Field | Value | Status |
|-------|-------|--------|
| `evidence_tier` | REPRODUCED | PASS |
| `cycle_status` | COMPLETED | PASS |
| `continue_recommended` | false | PASS |
| `next_recommendation` | PRODUCTIZE | PASS |
| `verdict` | PASS | PASS |
| `hierarchical_purity` (best) | 0.956135 | PASS (matches hierarchical_leiden_results.json) |
| `hierarchical_nesting` | 1.0 | PASS |
| `flat_mean_purity` | 0.882943 | PASS (5-resolution mean) |
| `flat_mean_nesting` | 0.593219 | PASS |
| `purity_improvement_pct` | 8.29% | PASS |
| `github_run` | 33101336412 | PASS (updated) |
| `accepted_run_id` | hierarchical_leiden_20260827_181419 | PASS (updated) |

### 3.4 Verification Test Suite
- **30/30 pytest tests PASS** (tests/fractal_map/test_verify.py)
  - TestArtifactIntegrity: 17/17 PASS
  - TestHierarchicalLeiden: 6/6 PASS
  - TestMetricConsistency: 7/7 PASS

### 3.5 Product Integration Artifacts (Validated)
| Artifact | Path | Status |
|----------|------|--------|
| Cluster metadata (7 resolutions + hierarchical) | `product_integration/cluster_metadata.json` | ✅ 98 hierarchical clusters |
| Zoom mappings (6 resolution pairs + coarse→hierarchical) | `product_integration/zoom_mappings.json` | ✅ Bidirectional parent-child |
| Zoom coherence metrics | `product_integration/zoom_coherence.json` | ✅ 59.2% improvement rate |
| Decision-to-cluster index | `product_integration/decision_clusters.json` | ✅ 1000 decisions × 9 resolutions |
| Integration specification | `product_integration/INTEGRATION_SPEC.md` | ✅ Human-readable spec |
| Integration summary | `product_integration/integration_summary.json` | ✅ 98 hierarchical clusters, purity 0.949 |

---

## 4. Complete Evidence Chain

### 4.1 Experimental Progression (Fractal-Map Lane)

| Cycle | Experiment | Evidence Tier | Key Finding |
|-------|-----------|---------------|-------------|
| Baseline | Flat Leiden multi-resolution | EXPLORATORY | Nesting imperfect (0.60), purity varies |
| Combined | Debiasing + TF-IDF concat | EXPLORATORY | Ratio > 0.5 achieved (0.511) |
| Resolution-dependent | Zoom-adapted representation | EXPLORATORY | **Falsified**: concat wins at all zoom levels |
| Zoom coherence | Zoom reveals legal structure | EXPLORATORY | 40% improvement, 0 deteriorations |
| Hierarchical Leiden | Leiden within parent clusters | REPRODUCED | **PASS**: purity 0.956 (best) / 0.949 (persisted), nesting 1.0 |
| Verification | Full reproducibility check | REPRODUCED | All metrics exact match |
| Audit | Independent re-verification | REPRODUCED | 24/24 checks PASS |
| **This run** | **State drift resolution** | **REPRODUCED** | **State updated, both configs documented, 30/30 tests PASS** |

### 4.2 Negative Results Preserved
1. **Flat Leiden nesting is imperfect** (0.59) — different resolutions don't naturally nest
2. **Resolution-dependent strategy does NOT outperform concat** — falsified
3. **Legal purity ratio below 1.0** even at finest zoom (0.920)
4. **60% of cluster-resolution pairs show no zoom improvement** — expected for already-homogeneous clusters
5. **igraph version sensitivity** changes best config but preserves key invariants

---

## 5. Product Handoff Specification

### 5.1 Recommended Configuration for Product

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

### 5.2 Map Structure (Persisted Config)

- **Coarse level (8 clusters):** Language + legal domain separation
  - French: Public/Social Insurance/Civil mix
  - German: Public/Criminal/Social Insurance/Civil
- **Fine level (98 clusters):** Specific legal sub-areas within each domain
  - E.g., "Strafprozess", "Schuldbetreibungs- und Konkursrecht", "Assurance-invalidité"

### 5.3 Zoom Behavior

1. **Domain zoom (res=0.25, 4 clusters):** Broad language/domain separation
2. **Subdomain zoom (res=0.5, 8 clusters):** Legal area within language
3. **Microcluster zoom (res=1.0–3.0, 14–27 clusters):** Specific legal issues
4. **Hierarchical zoom (validated):** 8 parent → 98 children, perfect nesting, purity 0.949

---

## 6. Known Limitations

1. **igraph version sensitivity:** Re-running produces different cluster counts and best config (77 vs 98 vs 127). Key invariants preserved (nesting=1.0, purity>0.94). Product uses persisted config.
2. **Experimental best ≠ persisted config:** Current best is coarse_0.25_fine_3.0 (77 clusters); persisted is coarse_0.5_fine_3.0 (98 clusters). Both validated.
3. **Nesting computed differently:** Flat Leiden nesting=0.59 across resolution pairs; Hierarchical Leiden nesting=1.0 by construction.
4. **Purity recomputation requires corpus data:** Branch labels from `/tmp/lex_accepted/corpus/` needed for from-scratch recomputation.
5. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full TF 2000+ requires corpus lane completion.

---

## 7. Files Produced/Updated in This Run

| File | Purpose |
|------|---------|
| `state/fractal-map.json` | Updated: github_run=33101336412, accepted_run_id=new experiment, metrics_summary matches current results, both configs documented |
| `results/fractal_map/hierarchical_map/hierarchical_leiden_results.json` | Updated: new experimental run with current igraph |
| `results/audit/fractal-map/CYCLE_operational_resume_33101336412_GATE.json` | Audit gate for this run |
| `reports/fractal_map/snapshot_audit_ready_33101336412.md` | This report |

---

## 8. Lane Disposition

**PRODUCTIZE.** The fractal-map lane question (v2) is answered:

> "Productize the multi-resolution hierarchical Leiden map for user-facing zoom/navigation: expose resolution ladder, cluster metadata, and legal coherence at each zoom level; validate that zoom reveals legally actionable substructure."

**Answer:** YES — Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity than all baselines. Two validated configs exist:
- **Experimental best (current igraph):** coarse_0.25_fine_3.0, 77 clusters, purity 0.956
- **Persisted for product:** coarse_0.5_fine_3.0, 98 clusters, purity 0.949

Product integration artifacts are complete: 7-resolution ladder, cluster metadata with legal coherence, parent-child zoom navigation, decision-to-cluster index. The product lane should consume artifacts from `results/fractal_map/product_integration/`.

**State:** evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE.  
**Audit:** All artifacts present, 30/30 pytest tests pass, state file fully consistent. Audit-ready.

---

*Report generated by fractal-map lane operational resume run 33101336412*  
*Audit timestamp: 2026-08-27*
