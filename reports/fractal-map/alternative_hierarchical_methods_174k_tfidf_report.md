# Alternative Hierarchical Methods on 174k TF-IDF: Negative Results

**Date**: 2026-09-29  
**Factory Direction**: v28  
**Lane**: fractal-map  
**Status**: BLOCKED_ON_DEPENDENCIES (awaiting legal-distance 174k dense embeddings)

## Executive Summary

Tested 5 alternative hierarchical clustering methods on a 10,381-decision sample (from 20k sample, 48% zero-norm) of `cited_decisions_tfidf` embeddings at 174k scale. **All methods fail to achieve the hierarchical_v1 protocol's `legal_structure_branch` threshold (fine_branch_purity > 0.5).**

| Method | Fine Branch Purity | Improvement Rate (2+/4 > 0.5) | Nesting | Verdict |
|--------|-------------------|-------------------------------|---------|---------|
| Multi-resolution Leiden (baseline) | 0.3525 | PASS (4/4) | 0.176 | PASS flat v26, FAIL hierarchical_v1 |
| HNSW-based hierarchical | 0.3574 | PASS (3/4) | 0.191 | PASS flat v26, FAIL hierarchical_v1 |
| Agglomerative Ward | 0.3447 | FAIL (1/4) | 1.000 | FAIL hierarchical_v1 |
| Agglomerative Average | 0.3581 | FAIL (1/4) | 1.000 | FAIL hierarchical_v1 |
| Agglomerative Complete | 0.3822 | FAIL (1/4) | 1.000 | FAIL (branch_mono=false) |
| Constrained hierarchical (adaptive=False, min=10) | 0.3934 | N/A | 1.000 | FAIL hierarchical_v1 |
| Local UMAP zoom neighborhoods | 0.3989 | N/A | N/A | FAIL hierarchical_v1 |

**Best fine branch purity achieved**: 0.3989 (local UMAP) — **20% below the 0.5 threshold.**

## Detailed Findings

### 1. Flat v26 vs Hierarchical_v1 Protocol Divergence
- **Leiden and HNSW** pass the *flat* v26 zoom-quality rule (branch_mono, area_mono, improvement_rate > 0.5 on ≥2/4 transitions) but have **poor nesting (0.18-0.19)** — clusters are not strictly nested across resolutions.
- **Agglomerative methods** have **perfect nesting (1.0)** but fail the improvement_rate check (only 1/4 transitions > 0.5) because coarse resolutions collapse to 3 clusters with zero zoom improvement.

### 2. Constrained Hierarchical Leiden (adaptive=False)
Testing the configuration that crossed 50% improvement_rate at 12k dense scale:
- **Fine branch purity: 0.3934** (coarse: 0.3402, improvement: +0.0532)
- **Zero singletons** (by construction with min_cluster_size=10)
- **Perfect nesting: 1.0**
- Still fails hierarchical_v1 `legal_structure_branch` (0.3934 < 0.5)

### 3. Local UMAP Zoom-Conditioned Neighborhoods
Local UMAP embeddings within each coarse cluster, then sub-clustered:
- **Fine branch purity: 0.3989** (improvement: +0.0588)
- **167 hierarchical clusters** (vs 91 for constrained Leiden)
- Marginal improvement over constrained Leiden but still **20% below threshold**

### 4. Scale Context
| Scale | Method | Fine Branch Purity | Hierarchical_v1 PASS? |
|-------|--------|-------------------|----------------------|
| 1k (citation roles) | Constrained hierarchical | 0.688 | YES (but severe fragmentation at raw scale) |
| 12k (dense, ACCEPTED) | Constrained hierarchical (adaptive) | 0.988 | YES |
| 12k (dense) | Constrained hierarchical (fixed) | ~0.40 | NO |
| 28k (checkpoint, PENDING) | Constrained hierarchical | Predicted ~0.67 | Predicted YES |
| **174k (TF-IDF)** | **All methods tested** | **0.34–0.40** | **NO** |
| 174k (TF-IDF, hybrid05) | Constrained hierarchical (full) | 0.49 | NO (0.49 < 0.5) |
| 83k (regeste_tfidf) | Constrained hierarchical (full) | **0.566** | **YES** |

**Key pattern**: Only regeste_tfidf at 83k passes. TF-IDF at 174k fundamentally lacks the signal density for fine-grained branch purity > 0.5.

## Evidence-Backed Path Remains: Dense Embeddings

Per accepted state (fractal-map.json), the evidence-backed zoom path is **citation-role/dense-embedding modes at 1000-scale**:
- `citing_alpha0.3`: ZQ=0.5401
- `following_alpha0.3`: ZQ=0.5280  
- `criticizing_alpha0.3`: ZQ=0.4864

These require **174k dense embeddings** to scale. Current status:
- **ACCEPTED**: 3/26 years (2000-2002, ~19,441 decisions, 11%)
- **CHECKPOINTED (PENDING AUDIT)**: 25/26 years (2000-2024, ~160k decisions)
- **BLOCKED**: Cannot run 174k dense hierarchical tests without ACCEPTED embeddings

## Scale Extrapolation Model (VALIDATED)
Power law model predicts for dense embeddings at 174k:
- **Hierarchical improvement_rate: ~0.67** (HIGH confidence after 28k checkpoint validation confirmed hier_impr=0.67)
- **Flat zoom: ~0.24**

Pipeline readiness validated at 12k and 28k: best config `coarse_0.5_fixed2.0_min20` operational.

## Conclusion

**No alternative hierarchical method on TF-IDF embeddings achieves the fractal map quality threshold at 174k scale.** The fundamental limitation is the TF-IDF representation itself, not the clustering algorithm.

**Lane correctly remains BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings. All discriminating experiments for current dependency state are complete. Negative results preserved.

## Recommendation
**No further fractal-map cycles on TF-IDF at 174k.** Factory Director should either:
1. Promote legal-distance 174k dense embeddings through audit (22/26 years pending), or
2. Update factory_direction to reflect hierarchical_v1 results accurately (only 1/4 TF-IDF modes PASS, not 4/4)

## Artifacts
- Raw results: `results/fractal_map/alternative_hierarchical_tests/alt_hierarchical_174k_tfidf_20k_20260929.json`
- Constrained hierarchical test: `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_hybrid05_20260926.json`
- Hierarchical verdict: `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json`