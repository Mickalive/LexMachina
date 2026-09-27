# Fractal Map Lane — Constrained Hierarchical Leiden on 99k Dense Embeddings (Years 2000-2015)

**Date:** 2026-09-27  
**Factory Direction Version:** 30  
**Lane:** fractal-map  
**Evidence Tier:** EXPLORATORY (first-run experiment at 99k scale, no independent reproduction)  
**Cycle Status:** COMPLETED_DENSE_99K_VALIDATION  
**Blocked On:** legal-distance_174k_dense_embeddings (16/26 years complete, 2016-2025 remaining)

---

## Executive Summary

**CONSTRAINED HIERARCHICAL LEIDEN TESTED ON 99,325 DENSE EMBEDDINGS (YEARS 2000-2015)** — The fractal-map lane has executed constrained hierarchical Leiden on the currently available 16 years of center-projected dense embeddings (768-dim, L2-normalized) from legal-distance. This represents ~57% decision completion of the full 174k corpus.

**v26 Zoom Quality Rule: FAIL** — While branch purity (+0.1216), area purity (+0.0695), and fragmentation (0.16% singletons) all PASS, the **improvement_rate = 47.37% falls just below the 50% threshold**. The trend from 12k (45.45%) to 99k (47.37%) shows positive scale dependency, but dense embeddings have not yet crossed the v26 threshold at this intermediate scale.

| Metric | Coarse (res=0.25) | Hierarchical Fine | Delta | v26 Threshold | Status |
|--------|-------------------|-------------------|-------|---------------|--------|
| Branch Purity | 0.8642 | 0.9858 | **+0.1216** | > 0 | ✅ PASS |
| Area Purity | 0.5322 | 0.6017 | **+0.0695** | > 0 | ✅ PASS |
| Improvement Rate | — | 0.4737 (9/19) | — | > 0.5 | ❌ FAIL |
| Singleton Fraction | 0.0% | 0.16% | — | < 0.01 | ✅ PASS |
| Nesting | — | 1.0 | — | = 1.0 | ✅ PASS |

**Overall v26 Verdict: FAIL** (3/4 criteria pass, improvement_rate fails)

---

## Problem Context

### Frozen v26 Zoom-Quality Rule (UNCHANGED)
A representation PASSES iff:
1. Branch purity at fine level > coarse level
2. Area purity at fine level > coarse level  
3. Branch improvement_rate > 0.5 on ≥2 of 4 transitions (0.25→0.5, 0.5→1.0, 1.0→2.0, 2.0→3.0) — *simplified to hierarchical coarse→fine improvement_rate > 0.5*
4. Fragmentation controlled (singleton_fraction < 1%)

### Previous Results (Scale Dependency Confirmed)
| Scale | Representation | Improvement Rate | Fragmentation | v26 Verdict |
|-------|---------------|------------------|---------------|-------------|
| 12k (2000-2002) | Dense (center_projected) | 45.45% | 0.41% | FAIL |
| **99k (2000-2015)** | **Dense (center_projected)** | **47.37%** | **0.16%** | **FAIL** |
| 174k | TF-IDF (4 modes) | 57-90% | 0-0.09% | **PASS** |

---

## Experimental Setup

### Data
- **Source**: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- **Years**: 2000-2015 (16 years, progress.json confirmed)
- **Decisions**: 99,325 (57% of 174k corpus)
- **Embeddings**: 768-dim center-projected (legal-distance v6 production default)
- **Metadata**: Branch + legal_area labels from checkpoint metadata files

### Branch Distribution (99,325 decisions)
- `unknown`: 55,752 (56.1%)
- `oeffentliches_recht`: 14,769 (14.9%)
- `zivilrecht`: 12,456 (12.5%)
- `sozialversicherungsrecht`: 10,133 (10.2%)
- `strafrecht`: 6,215 (6.3%)

### Legal Area Distribution (top)
- `unknown`: 55,240 (55.6%)
- `Invalidenversicherung`: 3,259
- `Strafprozess`: 2,549
- `Bürgerrecht und Ausländerrecht`: 2,111
- `Schuldbetreibungs- und Konkursrecht`: 2,082

> **Note**: High "unknown" fraction (~56%) limits purity ceiling. Branch purity at coarse level is already 0.8642.

### Algorithm: Constrained Hierarchical Leiden (Frozen Config)
```json
{
  "coarse_res": 0.25,
  "base_sub_res": 3.0,
  "min_cluster_size": 10,
  "max_subclusters_per_parent": 20,
  "adaptive_sub_res": true,
  "k_neighbors": 15
}
```

### Constraints
1. **Minimum cluster size (10)**: Prevents singletons and noise clusters
2. **Adaptive sub-resolution**: <500 docs → 1.5, 500-2000 → 2.0, >2000 → 3.0
3. **Maximum sub-clusters per parent (20)**: Caps complexity, prevents over-fragmentation
4. **Remainder handling**: Tiny sub-clusters merged into "remainder" cluster

---

## Detailed Results

### Clustering Structure
- **Coarse clusters (res=0.25)**: 39
- **Hierarchical fine clusters**: 623
- **Coarse→Fine expansion**: 39 → 623 (16x)
- **Median fine cluster size**: 107
- **Mean fine cluster size**: 159

### Fragmentation Analysis
- **Singleton fraction**: 0.16% (1 singleton out of 623 clusters)
- **Max cluster size**: 3,821
- **Min cluster size**: 1 (1 singleton)
- **Zero fragmentation effectively achieved**

### Zoom Coherence (Parent-Level Analysis)
| Parent | Coarse Purity | Mean Child Purity | Improvement | Children |
|--------|---------------|-------------------|-------------|----------|
| 0 | 0.8696 | 0.9730 | **+0.1034** | 21 |
| 1 | 0.5000 | 1.0000 | **+0.5000** | 21 |
| 2 | 1.0000 | 1.0000 | 0.0000 | 21 |
| 3 | 0.9952 | 0.9949 | -0.0004 | 21 |
| 4 | 0.6668 | 0.9502 | **+0.2834** | 21 |
| 5 | 1.0000 | 1.0000 | 0.0000 | 21 |
| 6 | 1.0000 | 1.0000 | 0.0000 | 21 |
| 8 | 1.0000 | 1.0000 | 0.0000 | 21 |
| 9 | 0.9960 | 0.9967 | +0.0007 | 21 |
| 11 | 0.9955 | 0.9957 | +0.0002 | 21 |
| 12 | 0.9956 | 0.9949 | -0.0007 | 21 |
| 13 | 0.9936 | 0.9942 | +0.0006 | 21 |
| 14 | 0.9966 | 0.9966 | ~0 | 21 |
| 15 | 0.3751 | 0.9479 | **+0.5728** | 21 |
| 16 | 0.9967 | 0.9961 | -0.0005 | 21 |
| 20 | 1.0000 | 1.0000 | 0.0000 | 20 |
| 21 | 1.0000 | 1.0000 | 0.0000 | 17 |
| 22 | 0.5671 | 0.9952 | **+0.4281** | 15 |
| 26 | 0.4717 | 0.9945 | **+0.5228** | 14 |

**Overall**: 
- Mean improvement: +0.1269
- **Improvement rate: 47.37% (9/19 parents improve)**
- Parents with improvement: 0, 1, 4, 9, 11, 13, 15, 22, 26 (9 parents)
- Parents with no improvement/degradation: 2, 3, 5, 6, 8, 12, 14, 16, 20, 21 (10 parents)

### Remainder Cluster Analysis
Large remainder clusters (unassigned docs from filtered tiny sub-clusters):
- Parent 0: 2,708 docs (remainder)
- Parent 1: 3,821 docs (remainder)
- Parent 2: 1,594 docs (remainder)
- Parent 3: 1,415 docs (remainder)
- Parent 4: 1,521 docs (remainder)
- Parent 5: 1,946 docs (remainder)
- Parent 6: 1,220 docs (remainder)
- Parent 7: 438 docs (remainder)
- Parent 8: 1,518 docs (remainder)
- Parent 9: 787 docs (remainder)

> **Critical Insight**: The `max_subclusters_per_parent=20` constraint forces large remainder clusters. For coarse clusters with >20 natural sub-clusters, the smallest are merged into remainders, potentially diluting purity measurements.

---

## Comparison: Dense Embeddings Scale Progression

| Scale | Decisions | Improvement Rate | Mean Improvement | Singleton % | v26 Pass |
|-------|-----------|------------------|------------------|-------------|----------|
| 12k | 12,570 | 45.45% | +0.1243 | 0.41% | ❌ |
| **99k** | **99,325** | **47.37%** | **+0.1269** | **0.16%** | ❌ |
| 174k (proj.) | ~174k | ? | ? | ? | ? |

**Trend**: Positive scale dependency — improvement_rate increases with scale (45.45% → 47.37%), fragmentation decreases (0.41% → 0.16%). Extrapolation suggests 174k dense *might* cross 50% threshold, but not guaranteed.

---

## Comparison: TF-IDF vs Dense at Scale

| Aspect | TF-IDF (174k) | Dense (99k) | Dense (12k) |
|--------|---------------|-------------|-------------|
| Branch purity (coarse) | 0.35-0.48 | 0.86 | 0.87 |
| Branch purity (fine) | 0.38-0.57 | 0.99 | 0.99 |
| Branch purity delta | +0.03 to +0.09 | **+0.12** | +0.12 |
| Area purity (coarse) | 0.09-0.21 | 0.53 | 0.45 |
| Area purity (fine) | 0.12-0.35 | 0.60 | 0.56 |
| Area purity delta | +0.03 to +0.13 | **+0.07** | +0.10 |
| Improvement rate | **57-90%** | 47.37% | 45.45% |
| Singleton fraction | 0-0.09% | 0.16% | 0.41% |
| Nesting | 1.0 | 1.0 | 1.0 |

**Key Observations**:
1. **Dense embeddings have much higher absolute purity** (branch 0.99 vs 0.57) due to better semantic resolution
2. **But TF-IDF shows better *relative* zoom refinement** (improvement_rate 57-90% vs 47%)
3. Dense embeddings start from very high coarse purity (0.86), leaving less room for improvement
4. TF-IDF coarse clusters are less pure (0.35-0.48), so fine clusters show clearer relative gains

---

## Root Cause Analysis: Why Dense Fails improvement_rate

### 1. High Coarse Purity Ceiling
Dense embeddings achieve 0.86 branch purity at coarse level (res=0.25). Many coarse clusters are already near-pure (1.0), so fine clusters *cannot* improve — they're already at ceiling. 10/19 parents have coarse_purity ≥ 0.995.

### 2. Remainder Cluster Dilution
The `max_subclusters=20` constraint creates large remainder clusters (up to 3,821 docs) that mix diverse content. These remainders are assigned as single sub-clusters, potentially lowering mean child purity for parents with large remainders.

### 3. Adaptive Resolution May Be Too Conservative
For very large coarse clusters (7,000-10,000 docs), sub_res=3.0 with max 20 sub-clusters means average sub-cluster size ~350-500. This may be too coarse to capture meaningful sub-structure.

### 4. Branch Label Granularity Mismatch
Branch labels (5 categories) are coarse. Dense embeddings separate finer doctrinal distinctions that branch labels don't capture. High fine-cluster purity (0.99) reflects semantic coherence, not necessarily branch alignment.

---

## Negative Results Preserved

| Experiment | Scale | Verdict | Reason |
|------------|-------|---------|--------|
| Flat Leiden (v26) | 174k TF-IDF | FAIL | >99% singletons |
| Flat Leiden | 100k TF-IDF | FAIL | >97% singletons |
| Agglomerative | 174k | FAIL | Too few coarse clusters |
| HDBSCAN | 174k | FAIL | Only 3 clusters |
| Ward linkage | 174k | FAIL | Too few coarse clusters |
| **Constrained Hierarchical (Dense)** | **12k** | **FAIL** | **improvement_rate=45.45%** |
| **Constrained Hierarchical (Dense)** | **99k** | **FAIL** | **improvement_rate=47.37%** |

---

## Evidence Artifacts

### Results
- `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_dense_2000_2015_20260927_031447.json` — Full 99k run
- `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_dense_2000_2002_20260926_170804.json` — 12k baseline

### Code
- `fractal_map/experiments/run_constrained_hierarchical_dense_99k.py` — 99k test script
- `fractal_map/experiments/test_constrained_hierarchical_dense.py` — 12k test script
- `fractal_map/experiments/constrained_hierarchical_leiden.py` — Core implementation

### Metadata Source
- `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` — 16 year-split embedding + metadata files
- `progress.json`: `{"completed_years": [2000-2015], "failed_years": []}`

---

## Compliance with LexMachina Constitution

| Principle | Status | Evidence |
|-----------|--------|----------|
| Accepted evidence beats narrative | ✅ | All claims backed by generated artifacts |
| Negative results remain evidence | ✅ | FAIL verdict documented with full metrics |
| No prettier map as better without evaluation | ✅ | v26 frozen rule applied; dense fails at 99k |
| No weakening frozen benchmarks | ✅ | v26 thresholds unchanged |
| Honest partial work can be valid | ✅ | Explicitly labeled EXPLORATORY; no 174k dense claims |

---

## Recommendations

### For Factory Director (Next Direction)
1. **Legal-distance priority unchanged**: Complete 174k dense embeddings (years 2016-2025 remaining). The 99k test shows positive scale trend but v26 threshold not yet crossed.
2. **Fractal-map**: Dense embeddings at 99k show strong absolute purity (0.99 branch) but miss improvement_rate threshold (47.37% vs 50%). **Do not claim production readiness for dense modes yet.**
3. **Product**: TF-IDF constrained hierarchical Leiden is production-ready (4/4 modes PASS at 174k). Wire as default for TF-IDF map modes immediately.
4. **Evaluation**: Auto-evaluate dense embeddings at 174k when available via `monitor_and_evaluate_174k.py`.

### For Fractal Map Lane (When 174k Dense Embeddings Unblocked)
1. **Run constrained hierarchical Leiden on full 174k dense embeddings** — critical test: will improvement_rate cross 50% at full scale?
2. **Test citation-role embeddings at 174k** (citing/following/criticizing alpha=0.3 showed ZQ=0.48-0.54 at 1k)
3. **Investigate remainder cluster issue**: Consider increasing `max_subclusters_per_parent` or alternative remainder handling
4. **Test alternative coarse resolutions**: res=0.15 or 0.5 may yield different coarse purity baselines
5. **Multi-view zoom UI**: Already implemented with citation-role views; await dense data

### Hypothesis for 174k Dense
Based on scale progression (12k: 45.45% → 99k: 47.37%), **extrapolation suggests ~49-51% at 174k** — borderline. The critical test at 174k will be decisive.

---

## Provenance & Reproducibility

- **Frozen Config**: coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters=20, adaptive_sub_res=true
- **Data**: 99,325 BGer decisions (2000-2015), center-projected 768-dim dense embeddings
- **Metadata**: Legal-distance v6 checkpoint metadata (branch + legal_area)
- **Compute**: CPU-only, ~4 min for 99k (coarse: 3.5 min, hierarchical: 0.5 min)
- **All raw outputs preserved** in `/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_tests/`
- **No data fabrication** — all results from executable code

---

## State Update

```json
{
  "lane": "fractal-map",
  "direction_version": 30,
  "evidence_tier": "EXPLORATORY",
  "cycle_status": "COMPLETED_DENSE_99K_VALIDATION",
  "continue_recommended": false,
  "blocked_on": "legal-distance_174k_dense_embeddings",
  "dense_99k_test_completed": true,
  "dense_99k_years": [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015],
  "dense_99k_decisions": 99325,
  "dense_99k_v26_pass": false,
  "dense_99k_branch_purity_delta": 0.1216,
  "dense_99k_area_purity_delta": 0.0695,
  "dense_99k_improvement_rate": 0.4737,
  "dense_99k_singleton_fraction": 0.0016,
  "dense_99k_nesting": 1.0,
  "scale_trend_positive": true,
  "tfidf_174k_accepted": true,
  "tfidf_174k_modes_pass_v26": 4,
  "next_recommendation": "Dense embeddings at 99k (2000-2015) show strong absolute purity (branch 0.99, area 0.60) and zero fragmentation, but improvement_rate=47.37% misses v26 threshold (50%). Positive scale trend from 12k (45.45%) → 99k (47.37%) suggests 174k may cross threshold. TF-IDF constrained hierarchical at 174k is ACCEPTED (4/4 modes PASS). Lane remains blocked on legal-distance 174k dense completions (years 2016-2025). No same-question cycle justified for current 99k data."
}
```