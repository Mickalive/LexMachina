# Fractal Map Lane — Factory Direction v28 Cycle Report

**Date:** 2026-09-28  
**Lane:** fractal-map  
**Factory Direction Version:** 28  
**Evidence Tier:** EXPLORATORY  
**Cycle Status:** RUN (blocked on legal-distance 174k dense embeddings)  
**Run ID:** `fractal_map_v28_cycle_001`

---

## Executive Summary

The fractal-map lane remains **BLOCKED on legal-distance 174k dense embeddings** (only 3/26 years ACCEPTED, 20/26 years PENDING AUDIT). However, this cycle produced **actionable evidence on scale-dependent zoom quality behavior** using available ACCEPTED artifacts:

1. **12k dense embeddings (years 2000-2002, ACCEPTED):** Constrained hierarchical Leiden with `adaptive=False` achieves **improvement_rate = 54.55%** (passes 50% threshold) with near-zero fragmentation (median_size=25, singleton_fraction=0.8%). Flat v26 zoom quality FAILS.

2. **1200 citation-role alpha embeddings (ACCEPTED):** `citing_alpha0.7` **PASSES the flat v26 zoom quality rule** — the only embedding tested that does. Constrained hierarchical Leiden on all `citing_alpha*` embeddings achieves **improvement_rate 62.5–100%** with zero fragmentation.

3. **Scale dependency confirmed:** Zoom quality behavior fundamentally changes between 1k–12k and 174k scales. The `adaptive=False` configuration (uniform sub_res=3.0) outperforms adaptive resolution scheduling at 12k.

---

## 1. Blocked Dependency: Legal-Distance 174k Dense Embeddings

| Metric | Status |
|--------|--------|
| ACCEPTED dense embedding years | 3/26 (2000-2002, ~19k decisions) |
| PENDING AUDIT years | 20/26 (2000-2019, ~99k decisions) |
| Blocking fractal-map zoom evaluation at 174k | YES |
| Blocking product 174k production defaults | YES |

Per factory direction v28: *"BLOCKED on legal-distance_174k_dense_embeddings (single remaining dependency)"*

---

## 2. 12k Dense Embeddings: Constrained Hierarchical Leiden Parameter Sweep

### Best Configuration: `adaptive=False`

| Parameter | Value |
|-----------|-------|
| coarse_res | 0.25 |
| base_sub_res | 3.0 |
| min_cluster_size | 5 |
| max_subclusters | 20 |
| adaptive_sub_res | **False** |

### Results (12,570 decisions, 768-dim)

| Metric | Coarse (res=0.25) | Hierarchical (fine) |
|--------|-------------------|---------------------|
| Clusters | 27 | 243 |
| Branch purity | 0.8653 | **0.9880** |
| Area purity | 0.4532 | 0.5563 |
| Median cluster size | — | 25.0 |
| Singleton fraction | 0.0% | **0.8%** |
| **Zoom improvement_rate** | — | **54.55%** |
| Mean purity improvement | — | +0.1228 |
| Parents evaluated | — | 11 |

**Verdict:** **PASSES improvement_rate > 50% threshold** with acceptable fragmentation. Flat v26 zoom quality still FAILS (improvement_rate_gt_0.5_on_2_of_4 = False).

### Why `adaptive=False` Works Better

The adaptive sub-resolution logic (`cluster_size < 500 → sub_res=1.5`, `500–2000 → sub_res=2.0`, `2000+ → sub_res=3.0`) under-resolves large clusters at 12k scale. Uniform `sub_res=3.0` creates more granular sub-clusters, yielding more parents with meaningful purity improvements.

---

## 3. 1200 Citation-Role Alpha Embeddings: Breakthrough at Smaller Scale

### Flat v26 Zoom Quality Results (1200 decisions, 768-dim)

| Embedding | Branch Mono | Area Mono | ImpRate > 0.5 (2/4) | **Verdict** |
|-----------|-------------|-----------|---------------------|-------------|
| `citing_alpha0.3` | ✅ | ✅ | ❌ (1/4) | FAIL |
| `citing_alpha0.5` | ✅ | ✅ | ❌ (1/4) | FAIL |
| **`citing_alpha0.7`** | ✅ | ✅ | ✅ (3/4) | **PASS** |
| `following_alpha0.3` | ✅ | ✅ | ❌ (1/4) | FAIL |
| `following_alpha0.5` | ✅ | ✅ | ❌ (0/4) | FAIL |
| `following_alpha0.7` | ✅ | ✅ | ❌ (0/4) | FAIL |
| `criticizing_alpha0.3` | ✅ | ✅ | ❌ (0/4) | FAIL |
| `criticizing_alpha0.5` | ✅ | ✅ | ❌ (0/4) | FAIL |
| `criticizing_alpha0.7` | ✅ | ✅ | ❌ (0/4) | FAIL |

**`citing_alpha0.7` is the only embedding that passes the frozen v26 flat zoom quality rule.**

### Constrained Hierarchical Leiden on `citing_alpha*` (Non-Adaptive)

| Embedding | Config | Hier. Purity | Median Size | Singleton % | Imp. Rate | Mean Imp. |
|-----------|--------|--------------|-------------|-------------|-----------|-----------|
| `citing_alpha0.3` | coarse=0.25 | 0.8872 | 17.0 | 0.0% | **80.0%** | +0.2919 |
| `citing_alpha0.3` | coarse=0.5 | 0.9045 | 10.0 | 0.0% | **62.5%** | +0.1881 |
| `citing_alpha0.5` | coarse=0.25 | 0.8879 | 15.0 | 0.0% | **80.0%** | +0.2789 |
| `citing_alpha0.5` | coarse=0.5 | 0.8997 | 12.0 | 0.0% | **62.5%** | +0.1471 |
| `citing_alpha0.7` | coarse=0.25 | 0.9090 | 15.0 | 0.0% | **83.3%** | +0.1895 |
| `citing_alpha0.7` | coarse=0.5 | 0.9374 | 10.5 | 0.9% | **70.0%** | +0.1289 |

**All `citing_alpha*` configurations pass the 50% improvement_rate threshold with near-zero fragmentation.**

---

## 4. Scale Dependency Analysis

| Scale | Embedding Type | Flat v26 Pass? | Constrained Hier. Imp. Rate | Fragmentation |
|-------|----------------|----------------|----------------------------|---------------|
| 1k | `citing_alpha0.3` | N/A (not tested) | 79–100% (prior) | High (74% singletons) |
| 1.2k | `citing_alpha0.7` | **YES** | 62.5–83.3% | Near-zero |
| 12k | Dense (2000-2002) | NO | 41–54.5% (adaptive=False: **54.5%**) | Near-zero |
| 174k | TF-IDF (8 reps) | NO (0/8 pass) | N/A (not tested) | Severe (>99% singletons) |

**Key finding:** The "alpha blending" in citation-role embeddings creates geometry that is fundamentally more amenable to hierarchical zoom than raw dense embeddings, and this advantage persists under constrained hierarchical clustering. However, even the best dense embedding configuration at 12k barely crosses the 50% threshold.

---

## 5. Negative Results Preserved

- **Flat v26 zoom quality at 174k (TF-IDF):** ALL 8 representations FAIL (factory direction v28, evaluation v26 report)
- **Flat v26 zoom quality at 12k (dense):** FAILS — improvement_rate_gt_0.5_on_2_of_4 = False
- **Adaptive sub-resolution at 12k:** improvement_rate capped at 45.5% — **adaptive logic harms zoom quality at this scale**
- **Citation role raw embeddings (1k):** Severe over-fragmentation (>73% singletons) — alpha blending is essential
- **12k dense with adaptive=True:** improvement_rate 41.7–45.5% consistently below threshold

---

## 6. Recommendations for Next Cycle

### Immediate (when legal-distance delivers 174k dense embeddings)
1. **Test constrained hierarchical Leiden with `adaptive=False` at 174k scale** — the configuration that passed 50% threshold at 12k
2. **Evaluate `citing_alpha0.7`-style embeddings at 174k** if legal-distance produces citation-role alpha variants
3. **Run full v26 zoom quality suite** on all 174k representations as they land

### Architectural
1. **Deprecate adaptive sub-resolution** for scales ≥10k — uniform high sub_res works better
2. **Prioritize citation-role alpha embedding pipeline** for production map modes — only path with demonstrated zoom quality at any scale
3. **Document scale thresholds** where zoom quality behavior changes (1k→12k→174k)

### Evaluation Harness
1. Freeze the constrained hierarchical Leiden evaluation as a standard benchmark
2. Add `adaptive=False` as a standard configuration alongside adaptive
3. Track improvement_rate, mean_improvement, fragmentation as core metrics

---

## 7. Evidence Artifacts

| Artifact | Path |
|----------|------|
| 12k dense comprehensive (coarse=0.25, adaptive=True) | `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260928_051437.json` |
| 12k dense comprehensive (coarse=0.5, adaptive=True) | `results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260928_051528.json` |
| Constrained hierarchical Leiden summary (1k baseline + citation roles) | `results/fractal_map/constrained_hierarchical_leiden/constrained_hierarchical_leiden_results.json` |
| 174k zoom quality diagnostic (22 modes) | `tmp/lex_accepted/product/results/fractal_map/evaluation/zoom_quality_diagnostic_results.json` |
| 174k formal suite evaluation report | `tmp/lex_accepted/evaluation/evaluation/reports/evaluation_v26_174k_formal_suite_report.md` |

---

## 8. Provenance & Reproducibility

- **Config hash (12k dense):** Embeddings from `/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002, ACCEPTED)
- **Config hash (citation alpha):** Embeddings from `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` (1200 decisions, ACCEPTED)
- **Metadata:** `/tmp/lex_accepted/evaluation/evaluation/data/dense_1200_baseline/metadata_1200.json` and 174k year-specific metadata
- **Global seed:** 42 (all stochastic operations)
- **Leiden seed:** 42
- **K-neighbors:** 15

All claim-bearing outputs generated after hypothesis freezing. Negative results preserved as first-class evidence.

---

## Next Recommendation

**CONTINUE** — Another cycle under the SAME factory direction question has concrete discriminating purpose:

1. When legal-distance promotes 174k dense embeddings (years 2003-2019), immediately test `adaptive=False` constrained hierarchical Leiden
2. Request legal-distance to compute citation-role alpha embeddings at 174k scale (only path with demonstrated zoom quality)
3. If 174k dense embeddings fail constrained hierarchical zoom quality even with optimal config, PIVOT to citation-role/dense-embedding hybrid modes as the evidence-backed zoom path

The lane should NOT pause — the blocking dependency is external (legal-distance) and we have prepared the exact evaluation harness needed when it resolves.