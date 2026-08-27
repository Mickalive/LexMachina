# Fractal Map Lane — Audit-Ready Report (Run 33030404043)

**Run ID:** 33030404043 (operational resume from persisted snapshot of run 33029690400)
**Date:** 2026-08-27
**Direction Version:** 1
**Lane:** fractal-map
**Evidence Tier:** REPRODUCED
**Status:** AUDIT-READY / PRODUCTIZE

---

## 1. Executive Summary

This run diagnoses and fixes the flat_mean_purity discrepancy that caused the verification in run 33029690400 to report 13/14 checks (1 failure). The root cause is identified: repair run 33029475850 set `flat_mean_purity` to the res_0.5 purity (0.874884) instead of the 5-resolution mean (0.894688) that the original experiment actually computed.

**Corrected Metrics:**
| Metric | Prior (Wrong) | Corrected | Source |
|--------|--------------|-----------|--------|
| **Hierarchical Purity** | 0.963417 | 0.963417 | Unchanged |
| **Flat Mean Purity** | 0.874884 | **0.894688** | 5-resolution mean |
| **Purity Improvement** | 10.12% | **7.68%** | (hier - flat) / flat |
| **Nesting Score** | 1.0000 | 1.0000 | Unchanged |
| **Flat Mean Nesting** | 0.600158 | 0.600158 | Unchanged |

**Verification Results:** 15/15 checks PASS, 30/30 pytest tests PASS.

**Recommendation:** PRODUCTIZE to product lane. Use hierarchical Leiden with coarse_res=0.5, sub_res=3.0.

---

## 2. Orchestration/Validation Failure Diagnosis

### 2.1 Root Cause: flat_mean_purity Discrepancy

The discrepancy chain spans 3 runs:

| Run | What Happened | Value Produced |
|-----|---------------|----------------|
| Original experiment | `hierarchical_leiden.py` computes mean of 5 resolutions [0.5, 1.0, 1.5, 2.0, 3.0] | **0.894688** |
| Repair run 33029475850 | Set `flat_mean_purity` to `hierarchical_results.coarse_0.5_fine_3.0.coarse_purity` (res_0.5 only) | **0.874884** |
| Verification 33029690400 | Used 7 resolutions [0.25..3.0] for recomputation | **0.858708** |

None of these three values matched. The repair run picked the wrong field from the results JSON. The verification script used a different resolution set.

### 2.2 Fix Applied

1. **State file corrected**: `flat_mean_purity` set to 0.894688 (the 5-resolution mean matching `hierarchical_leiden.py` line 380).
2. **Derived metric corrected**: `purity_improvement_pct` updated from 10.12% to 7.68% (using correct baseline).
3. **Verification script written**: `verify_metrics_33030404043.py` explicitly documents the resolution set used and validates against both the original experiment output and the state file.
4. **Resolution set documented**: `[0.5, 1.0, 1.5, 2.0, 3.0]` — the 5 resolutions used for the flat baseline in `hierarchical_leiden.py`.

### 2.3 Historical Orchestration Bugs (All Fixed)

| Run | Bug | Status |
|-----|-----|--------|
| 33020090957 | continue_recommended=true after PASS | Fixed |
| 33020622379 | continue_recommended=true after PASS | Fixed |
| 33021595718 | continue_recommended=true after PASS | Fixed |
| 33027907385 | continue_recommended=true after PASS | Fixed |
| 33029475850 | flat_mean_purity set to res_0.5 instead of 5-resolution mean | **Fixed in this run** |
| 33029690400 | Verification used 7 resolutions instead of 5 | **Fixed in this run** |

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
  - res_0.5: 0.874884
  - res_0.75: 0.843625
  - res_1.0: 0.902132
  - res_1.5: 0.894525
  - res_2.0: 0.903010
  - res_3.0: 0.898890
- **5-resolution mean: 0.894688** (matches original experiment exactly, diff < 1e-10)
- Flat nesting: 6 pairs recomputed, mean=0.600158 (matches state file)
- Hierarchical purity=0.963417 (matches state file), nesting=1.0 (matches state file)
- Sub-cluster sizes: 127 clusters sum to 1000 (verified)
- Parent-child consistency: all valid coarse_ids 0..7

### 3.3 Verification Test Suite
- **15/15 custom verification checks PASS** (verify_metrics_33030404043.py)
- **30/30 pytest tests PASS** (tests/fractal_map/test_verify.py)

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
| Resume (33029690400) | Full operational resume | REPRODUCED | 22/22 artifacts, 30/30 tests, 1/14 verification fail |
| **This run (33030404043)** | **Discrepancy fix + verification** | **REPRODUCED** | **15/15 checks, 30/30 pytest, state corrected** |

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
  "expected_nesting": 1.0,
  "flat_baseline_purity": 0.894688,
  "purity_improvement_pct": 7.68
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

## 6. Files Produced in This Run

| File | Purpose |
|------|---------|
| `results/fractal_map/audit/verification_33030404043.json` | Metric recomputation results (15 checks) |
| `results/audit/fractal-map/CYCLE_verification_33030404043_GATE.json` | Audit gate JSON |
| `fractal_map/evaluation/verify_metrics_33030404043.py` | Fixed verification script |
| `state/fractal-map.json` | Updated with corrected flat_mean_purity |
| `reports/fractal_map/snapshot_audit_ready_33030404043.md` | This report |

---

## 7. Lane Disposition

**PRODUCTIZE.** The fractal-map lane question is answered:

> "Establish a flat-map baseline, then test hierarchical/multi-resolution representations where zoom reveals legally coherent substructure rather than merely magnifying points."

**Answer:** YES — Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity (0.963417) than all baselines (flat mean 0.894688, agglomerative 0.786, eval baseline 0.795). Zoom within language-homogeneous clusters reveals legally coherent substructure. The product should integrate hierarchical Leiden with coarse_res=0.5, sub_res=3.0.

**State:** evidence_tier=REPRODUCED, cycle_status=COMPLETED, continue_recommended=false, next_recommendation=PRODUCTIZE.
**Audit:** 22/22 artifacts present, 15/15 verification checks pass, 30/30 pytest tests pass, metrics recomputed exact match. Audit-ready.

---

*Report generated by fractal-map lane verification run 33030404043*
*Audit timestamp: 2026-08-27T04:00:00Z*
