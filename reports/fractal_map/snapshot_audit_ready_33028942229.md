# Fractal Map Lane — Audit-Ready Snapshot Report

**Run ID:** 33028942229  
**Date:** 2026-08-27  
**Direction Version:** 1  
**Lane:** fractal-map  
**Evidence Tier:** REPRODUCED  
**Status:** AUDIT-READY / PRODUCTIZE

---

## 1. Executive Summary

The fractal-map lane has completed its mission under factory direction v1. **Hierarchical Leiden clustering** achieves the first REPRODUCED evidence that zoom reveals legally coherent substructure in a product-ready hierarchical format:

| Metric | Hierarchical Leiden | Flat Leiden | Improvement |
|--------|-------------------|-------------|-------------|
| **Branch Purity** | **0.9634** | 0.8749 | +10.1% |
| **Nesting Score** | **1.0000** | 0.6002 | +66.6% |
| **Zoom Purity Gain** | +10.1% | — | — |
| **Fine Clusters** | 127 | — | — |

**Recommendation:** PRODUCTIZE to product lane. Use hierarchical Leiden with coarse_res=0.5, sub_res=3.0.

---

## 2. Orchestration Failure Diagnosis

### 2.1 Root Cause

The same orchestration bug occurred 4 times: the state file was written **before** the final verdict was inspected. When a PASS verdict means the lane question is answered, the correct disposition is `PRODUCTIZE` (pass to product lane), not `CONTINUE` (more research).

| Run | Bug | Correction |
|-----|-----|------------|
| 33020090957 | continue_recommended=true after PASS | Fixed |
| 33020622379 | continue_recommended=true after PASS | Fixed |
| 33021595718 | continue_recommended=true after PASS | Fixed |
| 33027907385 | continue_recommended=true, next=CONTINUE after PASS | Fixed in 33028489959 |

### 2.2 Recommended Fix

Add a post-verdict state consistency check: if verdict=PASS, `continue_recommended` must be false and `next_recommendation` must not be CONTINUE (unless the lane question explicitly requires multiple cycles).

---

## 3. Verification Performed

### 3.1 Run 33028489959 (Verification)
- 18/18 evidence refs present
- All 7 flat purity recomputations: exact match (0.0 diff)
- Nesting: all 6 consecutive pairs = 1.0
- Sub-cluster size: 127 clusters sum to 1000
- Parent-child consistency: all valid
- Zoom improvement: 10.1% (0.8749 → 0.9634)

### 3.2 Run 33028942229 (Audit Verification)
- 22/24 checks passed (2 minor rounding discrepancies in state summary)
- All material metrics independently recomputed from saved .npy label arrays
- Artifact integrity: 18/18 refs present and non-empty
- State file fields correct: evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE

---

## 4. Complete Evidence Chain

### 4.1 Experimental Progression

| Cycle | Experiment | Evidence Tier | Key Finding |
|-------|-----------|---------------|-------------|
| Baseline | Flat Leiden multi-resolution | EXPLORATORY | Nesting imperfect (0.60), purity varies |
| Combined | Debiasing + TF-IDF concat | EXPLORATORY | Ratio > 0.5 achieved (0.511) |
| Resolution-dependent | Zoom-adapted representation | EXPLORATORY | **Falsified**: concat wins at all zoom levels |
| Zoom coherence | Zoom reveals legal structure | EXPLORATORY | 40% improvement, 0 deteriorations |
| Hierarchical Leiden | Leiden within parent clusters | REPRODUCED | **PASS**: purity=0.9634, nesting=1.0 |
| Verification (33028489959) | Full reproducibility check | REPRODUCED | All metrics exact match |
| Audit (33028942229) | Independent re-verification | REPRODUCED | 22/24 checks pass |

### 4.2 Negative Results Preserved

1. **Flat Leiden nesting is imperfect** (0.60) — different resolutions don't naturally nest
2. **Agglomerative wins nesting but loses purity** (0.786 vs Leiden 0.859)
3. **Resolution-dependent strategy does NOT outperform concat** — falsified
4. **Legal purity ratio below 1.0** even at finest zoom (0.920)
5. **60% of cluster-resolution pairs show no zoom improvement** — expected for already-homogeneous clusters

---

## 5. Product Handoff Specification

### 5.1 Recommended Configuration

```json
{
  "method": "hierarchical_leiden",
  "coarse_resolution": 0.5,
  "sub_resolution": 3.0,
  "representation": "concat_center_tfidf",
  "n_coarse_clusters": 8,
  "n_fine_clusters": 127,
  "nesting_guarantee": "by_construction",
  "expected_purity": 0.9634,
  "expected_nesting": 1.0
}
```

### 5.2 Map Structure

- **Coarse level (8 clusters):** Language + legal domain separation
  - French public/social insurance/civil
  - German public/criminal/civil/social insurance
- **Fine level (127 clusters):** Specific legal sub-areas within each domain
  - Within French "public": public law, criminal procedure, debt collection
  - Within German "social insurance": IV, UV, AHV specific

### 5.3 Zoom Behavior

1. **Domain zoom (coarse):** Users see 8 language/domain clusters
2. **Subdomain zoom (fine):** Within any cluster, zoom reveals 10-30 legal sub-areas
3. **Leaf zoom:** Individual decisions within sub-clusters

### 5.4 Artifact Locations

- Cluster assignments: `results/fractal_map/hierarchical_map/cluster_assignments.json`
- Label arrays: `results/fractal_map/hierarchical_map/labels_res_*.npy`
- Hierarchical Leiden results: `results/fractal_map/hierarchical_map/hierarchical_leiden_results.json`
- Full map metadata: `results/fractal_map/hierarchical_map/hierarchical_map_results.json`

---

## 6. Files Produced in This Run

| File | Purpose |
|------|---------|
| `fractal_map/evaluation/audit_verify_33028942229.py` | Independent verification script |
| `results/fractal_map/audit/audit_verify_33028942229_v2.json` | Verification results |
| `results/audit/fractal-map/CYCLE_verification_33028489959_GATE.json` | Gate for verification run |
| `results/audit/fractal-map/CYCLE_audit_verify_33028942229_GATE.json` | Gate for audit run |
| `state/fractal-map.json` | Updated audit-ready lane state |
| `reports/fractal_map/snapshot_audit_ready_33028942229.md` | This report |

---

## 7. Lane Disposition

**PRODUCTIZE.** The fractal-map lane question is answered:

> "Establish a flat-map baseline, then test hierarchical/multi-resolution representations where zoom reveals legally coherent substructure rather than merely magnifying points."

**Answer:** YES — Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity (0.9634) than all baselines. Zoom within language-homogeneous clusters reveals legally coherent substructure. The product should integrate hierarchical Leiden with coarse_res=0.5, sub_res=3.0.

**State:** evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE.

---

*Report generated by fractal-map lane audit verification run 33028942229*
*Audit timestamp: 2026-08-27T01:45:00Z*
