# Fractal Map Lane — 77k Dense Embeddings Hierarchical Clustering Report
**Factory Direction v28** | **Run ID:** `fractal_77k_hierarchical_dense_20260926` | **Evidence Tier:** REPRODUCED

---

## Executive Summary

This cycle tested hierarchical clustering on **77,169 Swiss Federal Supreme Court decisions** (years 2000–2012) using **768-dimensional center-projected dense embeddings** from the legal-distance lane. Three clustering approaches were evaluated against the **frozen v26 zoom-quality rule** (nesting_score ≥ 0.99 + monotonic purity improvement).

**Result: ALL THREE METHODS FAIL the frozen success rule at 77k scale.** The lane remains **BLOCKED** pending full 174k dense embeddings from legal-distance.

| Method | Nesting (0.25→3.0) | Mean Δ Purity | Zoom Quality | Clusters at res_3.0 | Verdict |
|--------|-------------------|---------------|--------------|---------------------|---------|
| Independent Leiden (flat) | 0.7207 | +0.0057 | 0.2893 | 111 | **FAIL** |
| True Hierarchical (sub-cluster from coarse) | 1.0000* | N/A (4 transitions) | — | 895 | **FAIL** (limited refinement) |
| Fully Recursive Hierarchical | 1.0000* | +0.0294 | 0.7177 | 77,169 | **FAIL** (trivial fragmentation) |

*By construction; not a meaningful hierarchy.

---

## Frozen Hypothesis & Success Rule

| Element | Value |
|---------|-------|
| **Hypothesis** | Hierarchical Leiden on dense embeddings at 77k scale produces monotonic zoom refinement and passes compressed ladder test |
| **Frozen Sample** | 77,169 BGer decisions (2000–2012), 768-dim center-projected dense embeddings |
| **Frozen Metric** | Zoom Quality Score (composite: purity_delta, meaningful_split_rate, stability, max_purity) |
| **Success Rule** | Mean purity_delta > 0 across all transitions **AND** nesting_score ≥ 0.99 |
| **Resolutions Tested** | [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0] |
| **Compressed Ladder** | [0.25, 0.5, 1.0, 2.0, 3.0] (dropped: 0.75, 1.5) |

---

## Method 1: Independent Leiden (Flat Baseline)

Run Leiden independently at each resolution on the full k-NN graph (k=30, cosine similarity).

### Resolution Metrics
| Resolution | Clusters | Branch Purity | Legal Area Purity | Language Purity |
|------------|----------|---------------|-------------------|-----------------|
| 0.25 | 32 | 0.8234 | 0.6980 | 0.8373 |
| 0.5 | 46 | 0.8715 | 0.7155 | 0.8493 |
| 0.75 | 55 | 0.9365 | 0.7470 | 0.8590 |
| 1.0 | 62 | 0.9376 | 0.7607 | 0.8616 |
| 1.5 | 78 | 0.9749 | 0.7800 | 0.8982 |
| 2.0 | 88 | 0.9618 | 0.7761 | 0.8995 |
| 3.0 | 111 | 0.9772 | 0.7847 | 0.9076 |

### Transition Analysis
| Transition | Nesting | Δ Purity | Split Rate | Meaningful Split Rate |
|------------|---------|----------|------------|----------------------|
| 0.25→0.5 | 0.6522 | **−0.0052** | 1.72 | 0.18 |
| 0.5→0.75 | 0.6182 | +0.0290 | 1.17 | 0.31 |
| 0.75→1.0 | 0.6613 | +0.0031 | 0.89 | 0.20 |
| 1.0→1.5 | 0.6282 | +0.0191 | 1.47 | 0.22 |
| 1.5→2.0 | 0.6136 | **−0.0153** | 1.38 | 0.05 |
| 2.0→3.0 | 0.5946 | +0.0036 | 1.51 | 0.14 |

**Overall nesting (0.25→3.0): 0.7207** — **FAILS** (≥0.99 required)

**Mean purity delta: +0.0057** — barely positive, with 2/6 transitions negative

**Zoom quality score: 0.2893** — well below evidence-backed 1k-scale leaders (citing_alpha0.3: 0.5401)

### Flat vs Hierarchical Identity
**Critical finding:** Independent Leiden with fixed seed produces **IDENTICAL** clusterings to "hierarchical" Leiden (NMI = 1.0 at every resolution). The nesting score of 0.72 comes from natural correlation, not hierarchical construction.

---

## Method 2: True Hierarchical (Sub-cluster from Coarse)

Cluster at coarse resolution (0.5), then recursively sub-cluster **within each coarse cluster** at finer resolutions.

### Resolution Metrics
| Resolution | Clusters | Branch Purity | Legal Area Purity | Language Purity |
|------------|----------|---------------|-------------------|-----------------|
| 0.5 | 46 | 0.8715 | 0.7155 | 0.8493 |
| 1.0 | 400 | 0.9877 | 0.8170 | 0.9577 |
| 1.5 | 508 | 0.9893 | 0.8211 | 0.9651 |
| 2.0 | 633 | 0.9914 | 0.8277 | 0.9684 |
| 3.0 | 895 | 0.9899 | 0.8314 | 0.9765 |

### Nesting (by construction)
| Transition | Nesting |
|------------|---------|
| 0.5→1.0 | 1.0000 |
| 1.0→1.5 | 0.5906 |
| 1.5→2.0 | 0.5640 |
| 2.0→3.0 | 0.5397 |

**Overall nesting (0.5→3.0): 1.0000** — only because we sub-cluster from the SAME coarse clusters each time. Nesting **degrades** at subsequent levels because fine clusters at 1.5 are not subsets of 1.0 clusters.

### Purity Deltas (Zoom Refinement)
| Transition | Δ Purity |
|------------|----------|
| 0.5→1.0 | **+0.1162** |
| 1.0→1.5 | +0.0016 |
| 1.5→2.0 | +0.0021 |
| 2.0→3.0 | **−0.0015** |

**Dramatic jump at first step (0.5→1.0), then plateaus near 0.99.** Only **7 of 46 coarse clusters (15.2%)** show meaningful improvement when zooming to finest level.

---

## Method 3: Fully Recursive Hierarchical

Each resolution sub-clusters the **previous resolution's** clusters, creating a true multi-level tree.

### Resolution Metrics
| Resolution | Clusters | Branch Purity | Legal Area Purity | Language Purity |
|------------|----------|---------------|-------------------|-----------------|
| 0.25 | 32 | 0.8234 | 0.6980 | 0.8373 |
| 0.5 | 248 | 0.9853 | 0.8048 | 0.9347 |
| 0.75 | 927 | 0.9930 | 0.8348 | 0.9794 |
| 1.0 | 3,132 | 0.9940 | 0.8525 | 0.9850 |
| 1.5 | 29,907 | 0.9952 | 0.8939 | 0.9907 |
| 2.0 | 71,803 | 0.9987 | 0.9804 | 0.9988 |
| 3.0 | **77,169** | **1.0000** | **1.0000** | **1.0000** |

### Nesting (by construction)
**ALL transitions: 1.0000** — perfect nesting guaranteed by recursive construction.

### Purity Deltas
| Transition | Δ Purity |
|------------|----------|
| 0.25→0.5 | **+0.1619** |
| 0.5→0.75 | +0.0078 |
| 0.75→1.0 | +0.0010 |
| 1.0→1.5 | +0.0011 |
| 1.5→2.0 | +0.0036 |
| 2.0→3.0 | +0.0013 |

**Mean purity delta: +0.0294** — all positive! **Zoom quality: 0.7177** — exceeds 1k-scale best (0.5401).

### The Fragmentation Problem
**At res_3.0: 77,169 clusters = one per decision.** The hierarchy "succeeds" by fragmenting to singletons. Purity reaches 1.0 trivially.

**Hierarchical coherence (0.5→3.0):**
- Coarse purity: 0.9853 (248 clusters)
- Fine purity: 1.0000 (77,169 clusters)  
- Improvement: +0.0147 (1.5%)
- Only **24 of 248 coarse clusters (9.7%)** improve

---

## Compressed Ladder Test (NESTING_METRIC_DEFECT_v1)

| Method | Full Δ | Compressed Δ | Retention | Full Nesting | Compressed Nesting | Δ Nesting | Passes? |
|--------|--------|--------------|-----------|--------------|-------------------|-----------|---------|
| Independent | 0.1669 | 0.1538 | 92.1% | 0.7207 | 0.7207 | 0.0000 | **NO** |
| True Hierarchical | 0.1766* | 0.1766* | 100% | 1.0000* | 1.0000* | 0.0000 | **TRIVIAL** |
| Fully Recursive | 0.1766 | 0.1766 | 100% | 1.0000 | 1.0000 | 0.0000 | **TRIVIAL** |

*True hierarchical only has 4 transitions.

**NESTING_METRIC_DEFECT_v1 CONFIRMED:** The compressed 5-level ladder passes for by-construction hierarchies (fully recursive) but represents a **trivial hierarchy** (fragmentation to singletons). The test is NOT universally valid for meaningful legal structure.

---

## Scale Dependency Analysis

| Scale | Method | Improvement Rate | Fragmentation | Nesting |
|-------|--------|------------------|---------------|---------|
| **1k** (citation roles) | — | — | — | — |
|  | citing_alpha0.3 | — | Low (928 clusters) | — |
| **12k** (years 2000–2002) | Hierarchical Leiden | **0.80** | Zero | — |
| **77k** (years 2000–2012) | Independent Leiden | — | Moderate (111) | 0.72 |
|  | True Hierarchical | **0.15** | Low (895) | 1.0* |
|  | Fully Recursive | — | **Complete (1:1)** | 1.0* |

**Key finding:** The hierarchical Leiden pipeline that worked at 12k (improvement_rate=0.80, zero fragmentation) **degrades severely at 77k**:
- True hierarchical: improvement_rate drops from 0.80 → 0.15
- Fully recursive: fragments completely to singletons
- Independent: fails nesting (0.72 vs required 0.99)

**Scale dependency is CONFIRMED.** Methods that work at small scale do not generalize to 77k+ decisions with dense embeddings.

---

## Comparison with Evidence-Backed 1k-Scale Results

From accepted evidence (zoom_quality_diagnostic_results.json, 1k decisions):

| Mode | Zoom Quality | Clusters at res_3.0 | Status |
|------|--------------|---------------------|--------|
| **citing_alpha0.3** | **0.5401** | 928 | **BEST** |
| following_alpha0.3 | 0.5280 | 986 | Strong |
| criticizing_alpha0.3 | 0.4864 | 997 | Strong |
| cited_decisions_tfidf_hybrid_cp64_0.7 | 0.4781 | 29 | Moderate |
| **outcome_hybrid_0.5 (prod default)** | **0.2798** | 29 | Baseline |

**Our 77k dense embedding results:**
- Independent Leiden: 0.2893 (near production default at 1k)
- Fully Recursive: 0.7177 (exceeds 1k best) — **but trivial fragmentation**

The evidence-backed zoom path at 1k scale is **citation-role modes** (citing/following/criticizing_alpha0.3), not dense embeddings with hierarchical Leiden.

---

## Provenance & Reproducibility

| Artifact | Path |
|----------|------|
| Independent Leiden results | `results/fractal_map/77k_hierarchical_dense/hierarchical_dense_77k_results.json` |
| Flat vs Hierarchical comparison | `results/fractal_map/77k_hierarchical_dense/hierarchical_vs_flat_comparison.json` |
| True Hierarchical results | `results/fractal_map/77k_true_hierarchical/true_hierarchical_leiden_77k_results.json` |
| Fully Recursive results | `results/fractal_map/77k_fully_recursive_hierarchical/fully_recursive_hierarchical_77k_results.json` |
| Experiment scripts | `fractal_map/experiments/*.py` |
| Embeddings (13 years) | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` |

**Provenance chain:** 
- Corpus: `/tmp/lex_accepted/corpus/` (PAUSE, REPRODUCED, 174k decisions)
- Legal-distance: 13/26 years computed (2000–2012), 77,169 decisions
- Fractal-map: This cycle (RUN, BLOCKED)

---

## Blockers & Dependencies

| Blocker | Status | Impact |
|---------|--------|--------|
| **Legal-distance 174k dense embeddings** | 13/26 years (77k/174k decisions) | Cannot test full corpus scale |
| Corpus artifact publication gap | Unresolved | Legal-distance years 2003–2025 blocked |
| NESTING_METRIC_DEFECT_v1 | Enforced by audit | Compressed ladder claims prohibited |

---

## Recommendations

### For Fractal-Map Lane
1. **NO PRODUCT-READINESS CLAIM** while lane blocked
2. **WAIT** for legal-distance to deliver:
   - Full 174k dense embeddings (remaining 13 years: 2013–2025)
   - Citation-role modes at 174k scale (citing/following/criticizing_alpha0.3)
   - Linear hybrid modes at 174k scale
3. **DO NOT** invest in further hierarchical Leiden variants at current scale — scale dependency confirmed

### For Legal-Distance Lane (Priority)
1. Resolve corpus artifact publication gap (mount paths /tmp/lex_accepted/corpus/ vs /tmp/lex_accepted/core/corpus/)
2. Complete dense embeddings for years 2013–2025
3. Compute citation-role modes at 174k scale (evidence-backed path)

### For Evaluation Lane
1. Monitor for dense embedding deliveries
2. Run formal suite on citation-role modes when available
3. Validate whether 1k-scale ZQ advantage (0.54) generalizes to 174k

### For Product Lane
1. Continue with TF-IDF production defaults (cited_outcome_hybrid_0.5)
2. Wire dense embeddings as they land (starting with 77k available now)
3. Do not switch default map mode until dense embeddings pass 174k evaluation

---

## Conclusion

**The fractal-map lane has exhausted discriminating experiments at 77k scale.** Three hierarchical clustering approaches were tested; all fail the frozen v26 zoom-quality rule in ways that reveal fundamental limitations:

1. **Independent Leiden** lacks hierarchical structure (nesting=0.72)
2. **True Hierarchical** has limited zoom refinement (15% improvement rate)  
3. **Fully Recursive** achieves perfect metrics via trivial fragmentation (1:1 at finest level)

**Scale dependency is real and severe:** the hierarchical pipeline that worked at 12k fails at 77k. The evidence-backed path remains **citation-role modes** (validated at 1k scale), which legal-distance must deliver at 174k scale.

**Lane status: BLOCKED_ON_DEPENDENCIES.** No additional same-question cycle justified.