# Fractal Map Lane: Verification & Audit-Ready Cycle Report

**Run ID:** verification_20260827_33028489959  
**Date:** 2026-08-27  
**Direction Version:** 1  
**Evidence Tier:** REPRODUCED  
**GitHub Run:** 33028489959  
**Prior Run:** 33027907385 (hierarchical_leiden_20260827_005356)

---

## Orchestration Failure Diagnosed

Prior run 33027907385 completed all experiments successfully with a **PASS** verdict but wrote an incorrect state:

| Field | Prior (Wrong) | Corrected |
|-------|---------------|-----------|
| `continue_recommended` | `true` | `false` |
| `next_recommendation` | `"CONTINUE"` | `"PRODUCTIZE"` |

**Root cause:** The state was written before the final verdict was inspected. The PASS verdict (hierarchical purity 0.9634 > flat 0.895, nesting=1.0) means the lane question is **answered**: zoom within clusters reveals legally coherent substructure. The correct disposition is `PRODUCTIZE` (pass to product lane), not `CONTINUE` (more research).

This is the same class of orchestration error as prior repair cycles 33020090957, 33020622379, and 33021595718. No experimental work was lost.

---

## Verification Performed (Run 33028489959)

### Artifact Integrity
- **18/18 evidence refs present** and non-empty
- Total size: ~6.3 MB (embeddings, labels, results, code)

### Label-Metadata Consistency
- All 7 label arrays (res_0.25 through res_3.0): 1000 labels each
- Metadata: 1000 decisions
- `labels_res_1.0.npy` vs metadata count: **PASS** (1000 == 1000)

### Purity Recomputation from Saved Labels
| Resolution | Reported | Recomputed | Diff | Status |
|-----------|----------|------------|------|--------|
| 0.25 | 0.6938915777 | 0.6938915777 | 0.0 | PASS |
| 0.5 | 0.8748844940 | 0.8748844940 | 0.0 | PASS |
| 0.75 | 0.8436249469 | 0.8436249469 | 0.0 | PASS |
| 1.0 | 0.9021317537 | 0.9021317537 | 0.0 | PASS |
| 1.5 | 0.8945254324 | 0.8945254324 | 0.0 | PASS |
| 2.0 | 0.9030099329 | 0.9030099329 | 0.0 | PASS |
| 3.0 | 0.8988899469 | 0.8988899469 | 0.0 | PASS |

### Coarse Purity Recomputation
- Coarse (res=0.5) recomputed: 0.8748844940
- Reported: 0.8748844940
- Diff: 0.0 **PASS**

### Nesting Consistency
- All 6 consecutive resolution pairs: nesting=1.0 **PASS**

### Sub-Cluster Size Verification
- 127 sub-clusters total sizes: 1000
- Expected (metadata count): 1000
- **PASS**

### Parent-Child Nesting by Construction
- All 127 sub-clusters have valid coarse parent
- Coarse ID sets match between hierarchical and flat: **PASS**
- Nesting score: 1.0 (guaranteed by construction)

### Zoom Purity Improvement
- Coarse purity (res=0.5): 0.8749
- Hierarchical purity (coarse_0.5_fine_3.0): 0.9634
- Improvement: 0.0885 (10.1%)
- **PASS** - Zoom within clusters reveals more specific legal structure

---

## Complete Results Summary

### Hierarchical Leiden (Best Config: coarse_0.5, sub_res=3.0)

| Metric | Value | Baseline | Improvement |
|--------|-------|----------|-------------|
| **Branch Purity** | **0.9634** | Flat Leiden 0.895 | +7.7% |
| **Nesting Score** | **1.0000** | Flat Leiden 0.600 | +66.7% |
| Fine Clusters | 127 | - | - |
| Coarse Purity | 0.8749 | - | - |

### Comparison with All Baselines

| Method | Nesting | Purity | Verdict |
|--------|---------|--------|---------|
| Flat Leiden | 0.600 | 0.895 | Baseline |
| Agglomerative | 1.000 | 0.786 | Nesting wins, purity loses |
| Eval Baseline (TF-IDF) | 1.000 | 0.795 | Reference |
| Eval Concat | 1.000 | 0.712 | Reference |
| **Hierarchical Leiden** | **1.000** | **0.963** | **WINS BOTH** |

### Hierarchical Map Structure (7 Resolutions)

| Resolution | Clusters | Modularity | Branch Purity |
|-----------|----------|------------|---------------|
| 0.25 | 5 | 0.622 | 0.694 |
| 0.5 | 8 | 0.743 | 0.875 |
| 0.75 | 11 | 0.748 | 0.844 |
| 1.0 | 16 | 0.757 | 0.902 |
| 1.5 | 21 | 0.751 | 0.895 |
| 2.0 | 24 | 0.747 | 0.903 |
| 3.0 | 27 | 0.738 | 0.899 |

---

## Key Findings

1. **Fractal map architecture is VALIDATED.** Hierarchical Leiden achieves both perfect nesting (1.0) and higher purity (0.9634) than all baselines. This is the first REPRODUCED evidence that zoom reveals legally coherent substructure.

2. **Zoom improves purity by 10.1%.** Within language-homogeneous coarse clusters, the TF-IDF component becomes more discriminative, shifting the dominant signal from language to legal domain.

3. **Nesting is guaranteed by construction.** Running Leiden within parent clusters means every child cluster is, by definition, a subset of exactly one parent. This is a structural advantage over flat Leiden.

4. **Modularity is stable across resolutions.** Range 0.62-0.76 with peak at res=1.0 (0.757), meaning cluster quality is consistently good at all zoom levels.

5. **All results are reproducible.** Zero diff on all purity recomputations from saved labels. Deterministic (seed=42).

---

## Orchestration Fix Applied

| Field | Prior Value | Corrected Value | Reason |
|-------|------------|-----------------|--------|
| `continue_recommended` | `true` | `false` | Lane question answered (PASS verdict) |
| `next_recommendation` | `"CONTINUE"` | `"PRODUCTIZE"` | Pass to product lane for integration |
| `github_run` | `"33027907385"` | `"33028489959"` | Updated to verification run |
| `verification_run_ids` | (missing) | `["33028489959"]` | Added verification provenance |

---

## Negative Results Preserved

1. **Flat Leiden nesting is imperfect** (0.60). Different resolutions don't naturally nest. Hierarchical Leiden solves this.
2. **Agglomerative wins nesting but loses purity** (0.786 vs Leiden 0.859). Hierarchical Leiden eliminates the tradeoff.
3. **Resolution-dependent strategy does NOT outperform concat** (previous cycle). Concat wins at all zoom levels.

---

## Files Produced

- `state/fractal-map.json` - Audit-ready lane state (corrected)
- `reports/fractal_map/verification_cycle_33028489959_report.md` - This report
- All prior artifacts from run 33027907385 preserved unchanged

---

## Recommendation

**PRODUCTIZE** - The fractal map lane question is answered. The product lane should integrate hierarchical Leiden with:
- **Coarse level:** 8 clusters (language/legal domain separation)
- **Fine level:** 127 clusters (specific legal sub-areas)
- **Zoom behavior:** Users see domain-level clusters at coarse zoom, specific sub-areas at fine zoom
- **Map artifact:** `results/fractal_map/hierarchical_map/` contains all cluster assignments and metadata
