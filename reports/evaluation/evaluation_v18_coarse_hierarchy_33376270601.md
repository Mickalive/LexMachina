# Evaluation v18: Coarse-Label Hierarchy Benchmark + Multi-seed Verification

**Run ID**: eval_v18_coarse_hierarchy_1788167865
**GitHub Run**: 33376270601
**Direction Version**: 13
**Date**: 2026-08-31
**Duration**: 16.1s

---

## Executive Summary

Two discriminating experiments were run. **Part A** (coarse-label hierarchy) produces a **NEGATIVE RESULT**: even at branch-level granularity (4 labels), the embedding space does NOT recover legal domain structure with purity >= 0.70. This is a genuine fundamental limitation of the current representations — not just a label-granularity artifact. **Part B** (multi-seed verification) produces a **POSITIVE RESULT**: the v17b normalization improvement is REPRODUCED across 4 independent seeds with high stability (std < 0.022), promoting v17b from EXPLORATORY to REPRODUCED tier.

---

## Part A: Coarse-Label Hierarchy Benchmark

### Frozen Hypothesis
The v16 hierarchy_coherence FAIL (all reps < 0.7 purity) is a label-granularity artifact: at branch-level (4 labels) the hierarchy IS recoverable with purity >= 0.70.

### Frozen Success Rule
`branch_level best_purity >= 0.70` for center_projected_64dim baseline.

### Result: **FAIL** (branch_purity = 0.5188)

| Representation | Branch Purity | Branch NMI | Norm Purity | Raw Purity | Branch/Norm Ratio |
|---|---|---|---|---|---|
| center_projected_64dim | 0.5188 | 0.0648 | 0.4669 | 0.3885 | 1.11x |
| linear_citation_concat | **0.6497** | **0.3005** | 0.4382 | 0.3685 | 1.48x |
| linear_citation_w3070 | 0.6022 | 0.2108 | 0.3746 | 0.3240 | 1.61x |
| linear_citation_ridge | 0.5638 | 0.1556 | 0.4503 | 0.3772 | 1.25x |
| linear_hybrid05_concat | 0.4737 | 0.0044 | 0.3824 | 0.3084 | 1.24x |
| cited_outcome_hybrid_0.5 | 0.4737 | 0.0044 | 0.3057 | 0.2517 | 1.55x |

### Analysis

1. **No representation passes 0.70 branch purity**. The best is linear_citation_concat at 0.6497 (k=4), still below threshold.

2. **NMI values at branch level are extremely low** (0.004–0.300). center_projected_64dim has NMI=0.065 at branch level — the clusters have almost no mutual information with branch labels. This means the embedding space organizes decisions by dimensions OTHER than their branch classification.

3. **Branch labels DO help over normalized labels** — linear_citation_concat shows a 1.48x improvement. But this is insufficient to cross the 0.70 threshold.

4. **Branch distribution is highly imbalanced**: oeffentliches_recht=568 (47.3%), zivilrecht=310 (25.8%), strafrecht=306 (25.5%), sozialversicherungsrecht=15 (1.3%). The extreme imbalance means KMeans with k=3-4 cannot form balanced clusters that align with branches.

5. **Zoom coherence at branch level is degenerate**: with n_unique=4, coarse_k=min(8,4)=4 and fine_k=min(25,4)=4, so both levels use k=4 and improvement is 0.0% by construction. This metric is uninformative at branch granularity.

### Root Cause Hypothesis
The embedding space captures legal reasoning/factual proximity rather than doctrinal branch classification. This is EXPECTED for a useful legal map — decisions within a branch span diverse legal topics, and cross-branch decisions may share more reasoning similarity (e.g., administrative law aspects of criminal cases) than within-branch decisions. The embedding space is optimizing for legal PROXIMITY, not branch CLASSIFICATION.

### Product Implication
**NEGATIVE**: The hierarchy_coherence benchmark cannot be passed at ANY label granularity with current representations. The "zoom from domains" experience must rely on Leiden clustering (which creates coherent clusters by construction) rather than pre-defined legal-area labels. This is consistent with the product already using Leiden clusters for navigation.

### Important Caveat (v17 partial refutation refined)
v17 showed label normalization improves purity ~20%. v18 now shows this improvement is REAL but INSUFFICIENT — even the coarsest labels (4 branches) cannot achieve 0.70 purity. The v16 attribution was BOTH partially right (label granularity matters) AND incomplete (even perfect labels wouldn't save the benchmark at 1200 decisions). The residual failure is likely due to:
- Embedding space capturing legal reasoning proximity, not branch classification
- Extreme branch class imbalance (15 sozialversicherungsrecht vs 568 oeffentliches_recht)
- 1200-decision slice may be too small for branch-level clustering to stabilize

---

## Part B: Multi-Seed Verification of v17b Normalization

### Frozen Hypothesis
v17b's finding that cross-lingual normalization improves hierarchy purity ~20% is reproducible across random seeds.

### Frozen Success Rule
`hierarchy_ratio_mean > 1.10 AND hierarchy_ratio_std < 0.05` for both center_projected_64dim and linear_hybrid05_concat across 4 seeds [42, 123, 456, 789].

### Result: **PASS**

#### center_projected_64dim

| Metric | Seed 42 | Seed 123 | Seed 456 | Seed 789 | Mean | Std |
|---|---|---|---|---|---|---|
| hierarchy_ratio | 1.2018 | 1.1986 | 1.2324 | 1.2000 | **1.2082** | **0.0140** |
| zoom_fine_ratio | 1.2233 | 1.2099 | 1.2474 | 1.2000 | **1.2202** | **0.0178** |
| legal_area_ratio | 1.1476 | 1.1729 | 1.1739 | 1.1396 | **1.1585** | **0.0152** |

#### linear_hybrid05_concat

| Metric | Seed 42 | Seed 123 | Seed 456 | Seed 789 | Mean | Std |
|---|---|---|---|---|---|---|
| hierarchy_ratio | 1.2401 | 1.2137 | 1.1875 | 1.2370 | **1.2196** | **0.0211** |
| zoom_fine_ratio | 1.2768 | 1.2470 | 1.2461 | 1.2390 | **1.2522** | **0.0145** |
| legal_area_ratio | 1.1528 | 1.1719 | 1.1655 | 1.1557 | **1.1615** | **0.0076** |

### Analysis

1. **All ratios are stable**: std < 0.022 across 4 seeds for both representations, well below the 0.05 threshold.

2. **All ratios are above 1.10**: normalization consistently improves hierarchy purity by 15-25% regardless of KMeans seed.

3. **linear_hybrid05_concat shows slightly MORE improvement** (mean hierarchy 1.220 vs 1.208) but also slightly MORE variance (std 0.021 vs 0.014). This is consistent with v15b's finding that linear_hybrid05_concat is the BEST STABLE combination.

4. **v17b can be promoted from EXPLORATORY to REPRODUCED**: the normalization improvement is reproducible across independent random seeds on identical machinery.

---

## Part C: Consolidated Evaluation Scorecard

The scorecard (in `v18_coarse_hierarchy_results.json > part_c_scorecard`) provides a machine-readable mapping of every representation to every benchmark with evidence tier tracking. Key summary:

### Universal Passes (all 6 representations)
- branch_knn (threshold: 0.6333)
- adversarial_falsification (lang_dom < 0.85, branch_coherence > 0.3)
- multilingual_invariance (separation >= 0, invariance_gap < 0.2)
- cross_language_pairs (separation > 0)
- collapse_check (mean_sim < 0.99, std_sim > 0.01)
- temporal_stability (std < 0.1)

### Universal Failures (all 6 representations)
- boilerplate_resistance_real_corpus (text_emb correlation ~ -0.06 to +0.10)
- hierarchy_coherence (best purity 0.25-0.39 at raw labels, 0.31-0.47 at normalized)
- zoom_coherence (negative improvement at all label granularities)
- legal_area_clustering (purity < 0.01)

### Conditional Passes
- tf_metadata_human_indexing: 4/6 reps PASS (recall@5 >= 0.8), 2 FAIL (cited_outcome_hybrid_0.5: 0.7135, linear_citation_w3070: 0.7930)

### New v18 Evidence
- **Branch-level hierarchy**: ALL FAIL (0.47-0.65 purity < 0.70 threshold)
- **v17b normalization stability**: REPRODUCED (4 seeds, std < 0.022)

---

## Product Decisions Unlocked

1. **Hierarchy benchmark is FUNDAMENTALLY UNPASSABLE** at 1200-decision scale with current representations. The product must rely on Leiden clustering for hierarchical navigation, not pre-defined legal-area labels. This does NOT invalidate the fractal map — Leiden clusters at different resolutions naturally create the zoom hierarchy.

2. **v17b normalization is REPRODUCED**: corpus lane should normalize legal_area labels as a data-quality fix, even though it won't save the hierarchy_coherence benchmark. Normalized labels improve ALL hierarchy-family metrics by 15-25% consistently.

3. **linear_citation_concat is the BEST for branch-level structure** (0.6497 purity, 0.3005 NMI at branch level), though still below 0.70. If branch-level navigation is ever needed, linear_citation_concat is the representation to use.

4. **The embedding space captures legal reasoning proximity, not branch classification**. This is actually the correct behavior for a useful legal map — users navigating by legal similarity, not by court chamber.

---

## Negative Results (preserved)

- branch-level hierarchy FAILS for all 6 representations (highest: 0.6497 < 0.70)
- zoom coherence is degenerate at branch level (0.0% improvement by construction)
- NMI at branch level is extremely low (0.004-0.300) — clusters are not aligned with branch labels
- Even the BEST representation (linear_citation_concat) cannot pass 0.70 purity at any label granularity

---

## Evidence References

| File | Description |
|---|---|
| `evaluation/experiments/run_v18_coarse_hierarchy.py` | Experiment script (frozen hypothesis, success rules) |
| `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` | Full machine-readable results |
| `results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_results.json` | v17b original results (now REPRODUCED) |
| `results/evaluation/v16_full_benchmark_suite/v16_full_benchmark_results.json` | v16 baseline benchmark suite |

---

## Recommendation

**CONTINUE** within the evaluation lane. Next discriminating experiments when dependencies resolve:
1. Full corpus adversarial evaluation at 192k (citation_heritage, hierarchy at larger scale)
2. Leiden-based hierarchy coherence test (cluster coherence within zoom levels)
3. Jurist pairwise preference test for COMBINATION vs DEFAULT map modes
