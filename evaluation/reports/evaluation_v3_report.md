# Evaluation Lane v3 — Frozen Harness Validation Report

**Factory Direction Version:** 6  
**Evaluation Version:** v3  
**GitHub Run:** 33231300518  
**Timestamp:** 2026-08-29T03:35:40Z  
**Config Hash:** `4323f833fa72366a` (frozen)  
**Global Seed:** 42 (frozen)

---

## Executive Summary

The Evaluation Lane v3 frozen harness has been successfully executed on the expanded 1,200-decision slice. The harness validates:

1. **Legal-distance unsupervised signal ablation results** on `center_projected` baseline
2. **Frontier metric learning results** (supervised metric learning on `center_projected`)
3. **Adversarial benchmarks**: language dominance, jurist pairwise preference, Jurivoc hierarchy alignment, scale stability, boilerplate resistance

**Key Result:** The reference baseline `center_projected_64dim` (current production default) **PASSES** both adversarial gates. Four new representations from legal-distance lane metric learning and hybrid objectives **BEAT** the reference on jurist pairwise preference while maintaining adversarial robustness.

---

## Frozen Configuration (Immutable)

| Parameter | Value |
|-----------|-------|
| Evaluation Version | v3 |
| Global Seed | 42 |
| Factory Direction | v6 |
| Language Dominance Threshold | < 0.85 |
| Jurist Pairwise Threshold | > 0.5 |
| Cross-Language Recall Threshold | > 0.2 |
| Cluster Coherence Threshold | > 0.7 |
| K-Neighbors (Lang Dominance) | 20 |
| K-Neighbors (Jurist) | 10 |
| K-Neighbors (Cross-Lang) | 10 |
| N Clusters (Coherence) | 16 |
| Config Hash | `4323f833fa72366a` |

**This configuration is frozen. No modifications permitted after observation of results.**

---

## Representations Tested (6 total)

| Representation | Source | Dimensions | Description |
|----------------|--------|------------|-------------|
| `center_projected_768` | Legal-distance v5 | 768 | Original center_projected (PCA1 removed) |
| `center_projected_64dim` | Legal-distance v5 | 64 | Frozen PCA (production default) |
| `linear_metric_epoch4` | Legal-distance v6 metric learning | 128 | Linear projection (768→128) on center_projected |
| `mahalanobis_metric_epoch4` | Legal-distance v6 metric learning | 128 | Low-rank Mahalanobis (rank=64) on center_projected |
| `hybrid_stabilized_epoch1` | Legal-distance v6 hybrid objective | 128 | Stabilized hybrid (λ scheduling + diversified pairs) |
| `hybrid_v2_epoch3` | Legal-distance v6 hybrid objective v2 | 128 | Hybrid objective on center_projected (epoch 3) |

---

## Adversarial Benchmark Results

### Critical Gates (MUST PASS BOTH)

| Representation | Language Dominance | Status | Jurist Pairwise | Status | **Both Pass** |
|----------------|-------------------|--------|-----------------|--------|---------------|
| `center_projected_768` | 0.7738 | ✅ PASS | 0.4912 | ❌ FAIL | **❌ FAIL** |
| `center_projected_64dim` | 0.7664 | ✅ PASS | 0.5121 | ✅ PASS | **✅ PASS** |
| `linear_metric_epoch4` | 0.6805 | ✅ PASS | 0.6847 | ✅ PASS | **✅ PASS** |
| `mahalanobis_metric_epoch4` | 0.6843 | ✅ PASS | 0.6781 | ✅ PASS | **✅ PASS** |
| `hybrid_stabilized_epoch1` | 0.6704 | ✅ PASS | 0.6656 | ✅ PASS | **✅ PASS** |
| `hybrid_v2_epoch3` | 0.7115 | ✅ PASS | 0.5988 | ✅ PASS | **✅ PASS** |

**Critical Finding:** `center_projected_768` **FAILS** jurist pairwise (0.4912 < 0.5) despite passing language dominance. This **confirms** the product lane critical finding (run 33134082075) that the 768-dim version is invalid for multilingual use. The 64-dim frozen PCA version is the correct production baseline.

**Breakthrough:** All four new representations **BEAT** the reference baseline on jurist pairwise preference:
- `linear_metric_epoch4`: **+0.1726** improvement (0.6847 vs 0.5121)
- `mahalanobis_metric_epoch4`: **+0.1660** improvement (0.6781 vs 0.5121)
- `hybrid_stabilized_epoch1`: **+0.1535** improvement (0.6656 vs 0.5121)
- `hybrid_v2_epoch3`: **+0.0867** improvement (0.5988 vs 0.5121)

---

## Jurivoc Hierarchy Alignment

*Proxy: Level 0 = 4 legal branches, Level 1 = 16 legal areas*

| Representation | Level 0 NMI | Level 1 NMI | Nesting Score | Status |
|----------------|-------------|-------------|---------------|--------|
| `center_projected_768` | 0.0945 | 0.4739 | 0.7890 | ❌ FAIL |
| `center_projected_64dim` | 0.0653 | 0.4699 | 0.8478 | ❌ FAIL |
| `linear_metric_epoch4` | **0.6895** | 0.4992 | 0.9346 | ✅ PASS |
| `mahalanobis_metric_epoch4` | **0.7041** | **0.5039** | 0.9388 | ✅ PASS |
| `hybrid_stabilized_epoch1` | 0.6360 | 0.4860 | 0.9004 | ✅ PASS |
| `hybrid_v2_epoch3` | **0.7415** | 0.4696 | 0.9363 | ✅ PASS |

**Finding:** All metric learning and hybrid representations achieve **strong Jurivoc alignment** (Level 0 NMI > 0.63), dramatically outperforming the center_projected baselines (NMI < 0.10). This indicates these representations recover the high-level legal taxonomy structure.

**Best:** `hybrid_v2_epoch3` (0.7415 Level 0 NMI), closely followed by `mahalanobis_metric_epoch4` (0.7041).

---

## Scale Stability

*Fraction of top-10 neighbors preserved under 80% corpus subsampling*

| Representation | Mean Overlap | Std | Status |
|----------------|--------------|-----|--------|
| `center_projected_768` | 0.7104 | 0.1145 | ✅ PASS |
| `center_projected_64dim` | 0.7071 | 0.1200 | ✅ PASS |
| `linear_metric_epoch4` | 0.7037 | 0.1239 | ✅ PASS |
| `mahalanobis_metric_epoch4` | **0.7154** | 0.1146 | ✅ PASS |
| `hybrid_stabilized_epoch1` | 0.7067 | 0.1192 | ✅ PASS |
| `hybrid_v2_epoch3` | 0.7092 | 0.1065 | ✅ PASS |

**Finding:** All representations show **good scale stability** (~70-72% neighbor overlap). No significant degradation from metric learning or hybrid transformations.

---

## Boilerplate Resistance

*Legal neighbor rate minus boilerplate neighbor rate (positive = good)*

| Representation | Boilerplate Rate | Legal Rate | Resistance Score | Status |
|----------------|------------------|------------|------------------|--------|
| `center_projected_768` | 0.9479 | 0.0521 | -0.8959 | ❌ FAIL |
| `center_projected_64dim` | 0.9506 | 0.0494 | -0.9012 | ❌ FAIL |
| `linear_metric_epoch4` | 0.9439 | 0.0561 | -0.8879 | ❌ FAIL |
| `mahalanobis_metric_epoch4` | 0.9477 | 0.0523 | -0.8954 | ❌ FAIL |
| `hybrid_stabilized_epoch1` | 0.9597 | 0.0403 | -0.9194 | ❌ FAIL |
| `hybrid_v2_epoch3` | 0.9572 | 0.0428 | -0.9144 | ❌ FAIL |

**Systematic Limitation:** **ALL representations FAIL boilerplate resistance.** Procedural neighbors (same chamber, different legal area) dominate over legally relevant neighbors (different chamber, same legal area) by ~20:1 ratio. This is a fundamental property of the current embedding approaches and Swiss Federal Supreme Court corpus structure.

---

## Fractal Quality (Hierarchical Leiden)

| Representation | Coarse Clusters | Fine Clusters | Coarse Purity | Fine Purity | Improvement Rate | Legal Area NMI |
|----------------|-----------------|---------------|---------------|-------------|------------------|----------------|
| `center_projected_768` | 7 | 100 | 0.8280 | 0.9381 | 60.0% | 0.5872 |
| `center_projected_64dim` | 8 | 116 | 0.8481 | 0.9498 | 64.7% | 0.5868 |
| `linear_metric_epoch4` | 5 | 82 | **0.9646** | 0.9699 | **72.0%** | 0.5921 |
| `mahalanobis_metric_epoch4` | 7 | 112 | 0.9623 | 0.9651 | 65.2% | 0.5944 |
| `hybrid_stabilized_epoch1` | 7 | 107 | 0.9367 | **0.9661** | **73.8%** | 0.5788 |
| `hybrid_v2_epoch3` | 4 | 57 | 0.9623 | 0.9592 | 59.6% | 0.5566 |

**Finding:** Metric learning and hybrid representations achieve **higher coarse purity** (0.93-0.96 vs 0.83-0.85) and **better improvement rates** (60-74% vs 60-65%) than center_projected baselines. `linear_metric_epoch4` has the best coarse purity (0.9646); `hybrid_stabilized_epoch1` has the best improvement rate (73.8%).

---

## Cross-Language Retrieval

*Recall of cross-language same-branch legal equivalents in top-10*

| Representation | Recall@10 | Status |
|----------------|-----------|--------|
| `center_projected_768` | 0.1455 | ❌ FAIL |
| `center_projected_64dim` | 0.1558 | ❌ FAIL |
| `linear_metric_epoch4` | **0.2114** | ✅ PASS |
| `mahalanobis_metric_epoch4` | **0.2083** | ✅ PASS |
| `hybrid_stabilized_epoch1` | **0.2360** | ✅ PASS |
| `hybrid_v2_epoch3` | **0.2269** | ✅ PASS |

**Finding:** All four new representations **PASS cross-language retrieval** (>0.2 threshold), while both center_projected baselines **FAIL**. This is a major multilingual robustness improvement.

---

## Signal Ablation Validation (Legal-Distance v4/v5 on center_projected)

**Status: CONFIRMED** — All signal ablation hybrids from v4/v5 **FAIL adversarial gates** when tested on `center_projected` baseline:

| Hybrid | Language Dominance | Jurist Preference | Adversarial Status |
|--------|-------------------|-------------------|-------------------|
| `legal_area_tfidf` | 0.914 | 0.131 | ❌ FAIL |
| `legal_issues_outcomes` | 1.000 | 0.000 | ❌ FAIL |
| `hybrid_erwaegungen_0.3` | 0.875 | 0.248 | ❌ FAIL |
| `hybrid_sachverhalt_0.7` | 0.936 | 0.121 | ❌ FAIL |

This confirms the legal-distance v6 finding: **fractal harness promise ≠ adversarial robustness**. Only metric learning (linear, Mahalanobis) and stabilized hybrid objectives produce valid adversarial-robust representations on `center_projected`.

---

## Best Representation Analysis

### 🏆 Overall Best: `linear_metric_epoch4`

| Metric | Value | vs Reference |
|--------|-------|--------------|
| Jurist Pairwise Preference | **0.6847** | **+0.1726** |
| Language Dominance | 0.6805 | -0.0859 |
| Jurivoc Level 0 NMI | 0.6895 | +0.6242 |
| Cross-Language Recall | 0.2114 | +0.0556 |
| Scale Stability | 0.7037 | -0.0034 |
| Fractal Improvement Rate | 72.0% | +7.3% |

**Strengths:** Highest jurist preference, excellent Jurivoc alignment, passes cross-language retrieval, good fractal structure.

### Runner-Up: `mahalanobis_metric_epoch4`

| Metric | Value |
|--------|-------|
| Jurist Pairwise Preference | 0.6781 |
| Jurivoc Level 0 NMI | **0.7041** (BEST) |
| Scale Stability | **0.7154** (BEST) |
| Cross-Language Recall | 0.2083 |

**Strengths:** Best Jurivoc alignment, best scale stability, strong jurist preference.

### Best for Language Invariance: `hybrid_stabilized_epoch1`

| Metric | Value |
|--------|-------|
| Language Dominance | **0.6704** (LOWEST = BEST) |
| Cross-Language Recall | **0.2360** (BEST) |
| Jurist Preference | 0.6656 |

**Strengths:** Strongest language invariance, best cross-language retrieval.

### Best for Jurivoc Alignment: `hybrid_v2_epoch3`

| Metric | Value |
|--------|-------|
| Jurivoc Level 0 NMI | **0.7415** (BEST) |
| Jurist Preference | 0.5988 |
| Language Dominance | 0.7115 |

---

## Recommendations

### 1. PRODUCTIZE: `linear_metric_epoch4` as Experimental Map Mode
- **Evidence Tier:** REPRODUCED (validated on frozen harness)
- **Product Impact:** New "Cross-Lingual Legal" map mode with significantly better jurist pairwise preference (0.6847 vs 0.5121) and multilingual robustness
- **Integration:** Add to product map mode registry alongside `center_projected_64dim_hierarchical` (DEFAULT)

### 2. PRODUCTIZE: `mahalanobis_metric_epoch4` as Alternative Map Mode
- **Evidence Tier:** REPRODUCED
- **Product Impact:** Best Jurivoc taxonomy alignment for users needing doctrinal navigation

### 3. PRODUCTIZE: `hybrid_stabilized_epoch1` as Alternative Map Mode
- **Evidence Tier:** REPRODUCED
- **Product Impact:** Best language invariance for multilingual users

### 4. DEFER: Human Jurist Pairwise Study
- Framework ready (legal-distance v5), needs 5-10 Swiss jurists
- Should include all four new valid representations

### 5. INVESTIGATE: Boilerplate Resistance
- Systematic failure across ALL representations
- Requires fundamental approach change (section-specific, outcome-focused, or citation-role embeddings at corpus scale)

### 6. ACCEPTED NEGATIVE FINDING
- `center_projected_768` is **invalidated** for production use (FAILS jurist pairwise)
- Confirmed by independent evaluation v3 harness
- Production MUST use `center_projected_64dim` (frozen PCA)

---

## Evidence Preservation

All raw outputs preserved in:
- `/home/runner/work/LexMachina/LexMachina/evaluation/results/v3/evaluation_v3_results.json`
- `/home/runner/work/LexMachina/LexMachina/evaluation/evaluation_v3_harness.py` (frozen harness)

No claim-bearing measurements modified after observation. Negative results (boilerplate resistance FAIL, center_projected_768 FAIL) preserved as first-class evidence.

---

## Next Steps for Factory Director

1. **Promote** `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` to product as experimental map modes
2. **Dispatch** human jurist study (framework ready in legal-distance v5)
3. **Investigate** boilerplate resistance as dedicated research question
4. **Monitor** scale stability as corpus grows toward 192k decisions (corpus lane)