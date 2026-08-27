# Hierarchical Leiden Evaluation Report

**Run ID:** `hierarchical_leiden_eval_20260827_001`  
**Date:** 2026-08-27  
**Factory Direction Version:** 1  
**Lane:** evaluation  

---

## Hypothesis

The hierarchical Leiden clustering (validated in fractal-map lane with REPRODUCED evidence tier) passes the evaluation lane's hierarchy_coherence and zoom_coherence benchmarks when used as the product's default map representation.

---

## Frozen Sample & Metrics

- **Sample:** 1000 BGer decisions (2020-2024) — same frozen sample as fractal-map lane and cycle 14 evaluation
- **Metrics:** 
  - Hierarchy coherence: cluster purity > 0.7 AND NMI > 0.3 at best resolution
  - Zoom coherence: purity improvement > 0% from coarse (res_0.5) to fine (res_3.0)
- **Success Rule:** Both benchmarks PASS for the representation actually used in product

---

## Representations Tested

| Representation | Description | Source |
|---|---|---|
| **flat_leiden** | Flat Leiden at 7 resolutions [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0] | Fractal-map baseline embeddings + Leiden |
| **hierarchical_leiden_flat** | Hierarchical Leiden flat labels at each resolution (labels_res_*.npy) | Fractal-map hierarchical_map/ |
| **hierarchical_leiden_true** | True hierarchical structure: 8 coarse → 127 fine clusters (nested) | Fractal-map hierarchical_leiden_results.json (coarse_0.5_fine_3.0) |

**Critical Finding:** `hierarchical_leiden_flat` labels are **IDENTICAL** to `flat_leiden` labels at every resolution. The hierarchical Leiden implementation saves flat Leiden clusterings at each resolution as the per-resolution labels.

---

## Hierarchy Coherence Benchmark

**Pass Criteria:** Best resolution purity > 0.7 AND NMI > 0.3

| Representation | Best Resolution | Best Purity | Best NMI | PASS |
|---|---|---|---|---|
| flat_leiden | res_2.0 (24 clusters) | **0.9020** | **0.4492** | ✅ YES |
| hierarchical_leiden_flat | res_2.0 (24 clusters) | **0.9020** | **0.4492** | ✅ YES |
| hierarchical_leiden_true (global) | fine (127 clusters) | 0.5450 | 0.0850 | ❌ NO |

**Note on hierarchical_leiden_true:** The true hierarchical structure has coarse clusters that are language-dominated (not branch-dominated), so global purity against branch labels is low. However, the fractal-map lane reports **local hierarchical_purity = 0.9634** — computed as weighted average of sub-cluster purity *within each coarse cluster* using the coarse cluster's dominant branch as reference. This is a different (local) metric.

---

## Zoom Coherence Benchmark

**Pass Criteria:** Purity improvement > 0% from coarse to fine

| Representation | Coarse | Fine | Coarse Purity | Fine Purity | Improvement | PASS |
|---|---|---|---|---|---|---|
| flat_leiden | res_0.5 (8) | res_3.0 (27) | 0.8280 | 0.9010 | **+8.8%** | ✅ YES |
| hierarchical_leiden_flat | res_0.5 (8) | res_3.0 (27) | 0.8280 | 0.9010 | **+8.8%** | ✅ YES |
| hierarchical_leiden_true | coarse_0.5 (8) | fine_3.0 (127) | 0.4660 | 0.5450 | **+17.0%** | ✅ YES |

The true hierarchical structure shows higher *relative* improvement (17% vs 8.8%) but lower *absolute* purity because coarse clusters align with language, not legal branch.

---

## Product Implication

| Aspect | Status |
|---|---|
| **Current product default** | Hierarchical Leiden flat labels at zoom levels: 5 clusters (res_0.25) → 8 clusters (res_0.5) → 27 clusters (res_3.0) |
| **Hierarchy coherence** | ✅ PASSED — identical to validated flat Leiden |
| **Zoom coherence** | ✅ PASSED — 8.8% improvement |
| **True hierarchical structure** | Validated separately in fractal-map lane (nesting=1.0, hierarchical_purity=0.9634 local) |
| **Full benchmark suite (14/14)** | Remains validated on debiased_citation_blended embeddings (cycle 14) |

**No regression detected.** The product's map representation is validated for the clustering-based benchmarks.

---

## Evidence References

- `results/fractal_map/hierarchical_map/labels_res_*.npy` — flat cluster assignments per resolution
- `results/fractal_map/hierarchical_map/cluster_assignments.json` — flat Leiden assignments (identical)
- `results/fractal_map/hierarchical_map/hierarchical_leiden_results.json` — true hierarchical structure (nesting=1.0, hierarchical_purity=0.9634)
- `results/fractal_map/hierarchical_map/hierarchical_map_results.json` — branch coherence per resolution
- `results/fractal_map/baseline/metadata.json` — decision metadata (chamber, language, year)
- `corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl` — canonical corpus with branch field

---

## Verdict

**PRODUCTIZE** — The hierarchical Leiden map representation used in product (flat labels at multiple resolutions for zoom) passes both hierarchy_coherence and zoom_coherence benchmarks. The true hierarchical structure is validated in fractal-map lane for nesting and local purity. The full 14-benchmark suite remains validated on the debiased_citation_blended embedding representation.

**Recommendation:** Factory Director should advance to direction version 2. Evaluation lane complete for v1.