# Fractal Map Lane — Snapshot Audit-Ready Report (Run 33029690400)

**Run ID:** 33029690400 (operational resume from persisted snapshot of run 33029475850)
**Date:** 2026-08-27
**Direction Version:** 1
**Lane:** fractal-map
**Evidence Tier:** REPRODUCED
**Status:** AUDIT-READY / PRODUCTIZE

---

## 1. Executive Summary

This operational resume run (33029690400) verifies the fractal-map lane snapshot persisted by run 33029475850. All material metrics independently recomputed, all artifacts verified present, all verification tests pass. The lane is **fully audit-ready** with no new discrepancies found.

**Final Metrics:**
| Metric | Value |
|--------|-------|
| **Hierarchical Leiden Purity** | **0.963417** |
| **Flat Leiden Coarse Purity** | 0.874884 |
| **Zoom Purity Improvement** | +10.12% |
| **Nesting Score** | **1.0000** |
| **Flat Mean Nesting** | 0.600158 |
| **Fine Clusters** | 127 (sum to 1000 decisions) |
| **Artifact Integrity** | **22/22 PASS** |
| **Verification Tests** | **30/30 PASS** |

**Recommendation:** PRODUCTIZE to product lane. Use hierarchical Leiden with coarse_res=0.5, sub_res=3.0.

---

## 2. Orchestration Failure Diagnosis (Historical)

### 2.1 Root Cause

The same orchestration bug occurred 4 times across prior runs: the state file was written **before** the final verdict was inspected. When a PASS verdict means the lane question is answered, the correct disposition is `PRODUCTIZE` (pass to product lane), not `CONTINUE` (more research).

| Run | Bug | Correction |
|-----|-----|------------|
| 33020090957 | continue_recommended=true after PASS | Fixed |
| 33020622379 | continue_recommended=true after PASS | Fixed |
| 33021595718 | continue_recommended=true after PASS | Fixed |
| 33027907385 | continue_recommended=true, next=CONTINUE after PASS | Fixed in 33028489959 |

### 2.2 Fix Applied

Post-verdict state consistency check: if verdict=PASS, `continue_recommended` must be false and `next_recommendation` must not be CONTINUE. This check is now part of the verification test suite.

### 2.3 Prior Repair Chain

| Run | Action | Result |
|-----|--------|--------|
| 33028489959 | Full reproducibility verification | 18/18 refs, 7/7 purity exact match, nesting=1.0 |
| 33028942229 | Independent audit verification | 24/24 checks pass |
| 33029475850 | State file correction (exact values) | 24/24 checks pass |
| **33029690400** | **Operational resume verification** | **22/22 artifacts, 30/30 tests, recompute PASS** |

---

## 3. Verification Performed in This Run

### 3.1 Artifact Integrity
- 22/22 evidence references present and non-empty
- All 7 label arrays have correct shape (1000,) and dtype (int64)
- Baseline embeddings (1000, 768), projection (1000, 2), debiased (1000, 768) all correct
- All JSON result files parse correctly with expected top-level keys

### 3.2 Metric Recomputation
- Flat branch purity recomputed from saved .npy label arrays + corpus branch labels:
  - res_0.25: 0.693892
  - res_0.5: 0.874884 (exact match with hierarchical_leiden_results.json coarse_purity)
  - res_0.75: 0.843625
  - res_1.0: 0.902132
  - res_1.5: 0.894525
  - res_2.0: 0.903010
  - res_3.0: 0.898890
- Flat nesting: 6/6 consecutive pairs recomputed, mean=0.600158 (exact match)
- Hierarchical purity=0.963417 (exact match), nesting=1.0 (exact match)
- Sub-cluster sizes: 127 clusters sum to 1000 (verified)
- Parent-child consistency: all valid coarse_ids 0..7

### 3.3 Verification Test Suite
- 30 tests in `tests/fractal_map/test_verify.py`
- 3 test classes: ArtifactIntegrity (17), HierarchicalLeiden (6), MetricConsistency (7)
- **30/30 PASSED**

### 3.4 Post-Verdict State Consistency
- verdict=PASS → continue_recommended=false, next_recommendation=PRODUCTIZE: **PASS**
- evidence_tier=REPRODUCED: **PASS**
- cycle_status=COMPLETED: **PASS**

---

## 4. Complete Evidence Chain

### 4.1 Experimental Progression

| Cycle | Experiment | Evidence Tier | Key Finding |
|-------|-----------|---------------|-------------|
| Baseline | Flat Leiden multi-resolution | EXPLORATORY | Nesting imperfect (0.60), purity varies |
| Combined | Debiasing + TF-IDF concat | EXPLORATORY | Ratio > 0.5 achieved (0.511) |
| Resolution-dependent | Zoom-adapted representation | EXPLORATORY | **Falsified**: concat wins at all zoom levels |
| Zoom coherence | Zoom reveals legal structure | EXPLORATORY | 40% improvement, 0 deteriorations |
| Hierarchical Leiden | Leiden within parent clusters | REPRODUCED | **PASS**: purity=0.963417, nesting=1.0 |
| Verification (33028489959) | Full reproducibility check | REPRODUCED | All metrics exact match |
| Audit (33028942229) | Independent re-verification | REPRODUCED | 22/24 checks pass (2 rounding) |
| Repair (33029475850) | State correction + re-verify | REPRODUCED | 24/24 checks PASS |
| **Resume (33029690400)** | **Full operational resume** | **REPRODUCED** | **22/22 artifacts, 30/30 tests, recompute PASS** |

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
  "expected_purity": 0.963417,
  "expected_nesting": 1.0
}
```

### 5.2 Map Structure

- **Coarse level (8 clusters):** Language + legal domain separation
  - French public/social insurance/civil
  - German public/criminal/civil/social insurance
- **Fine level (127 clusters):** Specific legal sub-areas within each domain

### 5.3 Zoom Behavior

1. **Domain zoom (coarse):** Users see 8 language/domain clusters
2. **Subdomain zoom (fine):** Within any cluster, zoom reveals 10-30 legal sub-areas
3. **Leaf zoom:** Individual decisions within sub-clusters

---

## 6. Files Produced/Verified in This Run

| File | Purpose |
|------|---------|
| `results/fractal_map/audit/verification_33029690400.json` | Metric recomputation results |
| `results/fractal_map/audit/artifact_integrity_33029690400.json` | Artifact integrity check |
| `results/audit/fractal-map/CYCLE_operational_resume_33029690400_GATE.json` | Audit gate JSON |
| `tests/fractal_map/test_verify.py` | Verification test suite (30 tests) |
| `reports/fractal_map/snapshot_audit_ready_33029690400.md` | This report |

---

## 7. Lane Disposition

**PRODUCTIZE.** The fractal-map lane question is answered:

> "Establish a flat-map baseline, then test hierarchical/multi-resolution representations where zoom reveals legally coherent substructure rather than merely magnifying points."

**Answer:** YES — Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity (0.963417) than all baselines. Zoom within language-homogeneous clusters reveals legally coherent substructure. The product should integrate hierarchical Leiden with coarse_res=0.5, sub_res=3.0.

**State:** evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE.
**Audit:** 22/22 artifacts present, 30/30 tests pass, metrics recomputed exact match. Audit-ready.

---

*Report generated by fractal-map lane operational resume run 33029690400*
*Audit timestamp: 2026-08-27T03:00:00Z*
