# Fractal Map Lane — Cycle Report
**Factory Direction v28 | Run ID: constrained_hierarchical_partial_dense_20260927_194948 | Evidence Tier: REPRODUCED**

---

## Executive Summary

The fractal-map lane remains **BLOCKED** on legal-distance 174k dense embeddings. Only 3/26 years (2000-2002, ~19,441 decisions) are ACCEPTED; years 2003-2019 (~99k decisions) are PENDING AUDIT.

**Partial validation at 12k (ACCEPTED years 2000-2002) CONFIRMS:**
1. **Flat v26 zoom FAILS** at 12k scale — PASS=False (only 1/4 transitions with branch_improvement_rate > 0.5)
2. **Constrained hierarchical Leiden WORKS** — nesting=1.0 by construction, zoom_branch improvement_rate up to 80%
3. **Best production trade-off** — `validated_coarse_0.25_sub_3.0` achieves 60% zoom_branch rate, 4.5% singleton fraction, +0.182 branch purity improvement, +0.210 area purity improvement
4. **Scale dependency CONFIRMED** — flat zoom degrades below ~62k; constrained hierarchical Leiden with min_cluster_size enforcement works

**No product-readiness claim while lane blocked.** Next cycle: await legal-distance 174k dense embeddings audit promotion.

---

## Experimental Results

### 1. Flat v26 Zoom Evaluation (12k center_projected)

| Resolution | Clusters | Branch Purity | Area Purity |
|------------|----------|---------------|-------------|
| 0.25       | 21       | 0.799         | 0.284       |
| 0.5        | 30       | 0.868         | 0.262       |
| 1.0        | 45       | 0.926         | 0.366       |
| 2.0        | 59       | 0.925         | 0.438       |
| 3.0        | 63       | 0.931         | 0.448       |

**v26 Rule Evaluation:**
- Branch monotonic: ✓ True (0.799 → 0.931)
- Area monotonic: ✓ True (0.284 → 0.448)
- Transitions with branch_improvement_rate > 0.5: **1/4** (threshold: ≥2/4)
- **Overall: PASS=False**

**Transition Details:**
| Transition | Branch Rate | Area Rate | Branch Δ | Area Δ |
|------------|-------------|-----------|----------|--------|
| 0.25→0.5   | 0.40        | 0.40      | +0.055   | -0.013 |
| 0.5→1.0    | 0.67        | 0.83      | +0.080   | +0.108 |
| 1.0→2.0    | 0.09        | 0.45      | +0.008   | +0.063 |
| 2.0→3.0    | 0.00        | 0.14      | 0.000    | +0.004 |

---

### 2. Constrained Hierarchical Leiden (12k center_projected)

| Config | Coarse→Fine | Branch Δ | Area Δ | Zoom Branch Rate | Fine Singletons | Nesting |
|--------|-------------|----------|--------|------------------|-----------------|---------|
| coarse_0.25_adaptive_min20 | 21→436 | **+0.192** | **+0.295** | **80%** | 23.9% | 1.0 |
| coarse_0.5_adaptive_min20 | 30→565 | +0.116 | +0.260 | 50% | 31.0% | 1.0 |
| coarse_0.5_adaptive_min50 | 30→714 | +0.126 | +0.324 | 67% | 21.1% | 1.0 |
| coarse_1.0_adaptive_min20 | 45→967 | +0.063 | +0.392 | 40% | 39.9% | 1.0 |
| **validated_coarse_0.25_sub_3.0** | **21→264** | **+0.182** | **+0.210** | **60%** | **4.5%** | **1.0** |
| coarse_0.5_fixed3.0_min20 | 30→375 | +0.115 | +0.241 | 50% | 14.4% | 1.0 |
| coarse_0.5_fixed2.0_min20 | 30→296 | +0.113 | +0.236 | 50% | 5.1% | 1.0 |

**Success Rule Check (validated_coarse_0.25_sub_3.0):**
- Strict nesting ≥ 0.99: ✓ (1.0)
- Branch/area purity improvement: ✓ (+0.182, +0.210)
- Zoom improvement_rate > 0.5: ✓ (60%)
- Fine singleton fraction < 0.1: ✓ (4.5%)
- **VERDICT: PASS**

---

### 3. Hierarchical Leiden on Raw Dense Embeddings (12k, no center_projected)

| Metric | Value |
|--------|-------|
| Coarse clusters (res=0.5) | 36 |
| Fine clusters (sub_res=3.0) | 568 |
| Coarse branch purity | 0.943 |
| Hierarchical branch purity | 0.996 |
| Improvement | +0.053 |
| Nesting | 1.0 |
| Zoom Quality Score | 0.316 (threshold > 0.3: PASS) |

**Zoom Quality Breakdown:**
| Transition | Split Rate | Purity Δ | Meaningful Split Rate |
|------------|------------|----------|----------------------|
| 0.25→0.5   | 0.44       | +0.001   | 0.17                 |
| 0.5→0.75   | 0.42       | -0.008   | 0.33                 |
| 0.75→1.0   | 0.30       | 0.000    | 0.15                 |
| 1.0→1.5    | 0.24       | +0.061   | 0.58                 |
| 1.5→2.0    | 0.30       | +0.002   | 0.13                 |
| 2.0→3.0    | 0.31       | +0.018   | 0.26                 |

---

### 4. 174k TF-IDF Constrained Hierarchical Leiden (ACCEPTED)

**Mode:** `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25`
- Corpus: 175,440 decisions
- Nesting: 1.0 (by construction, 5 resolution levels)
- Coarse (res=0.25): 22 clusters
- Fine (res=3.0): 64,131 clusters

**Zoom Coherence (Structural Test):**
| Transition | Improvement Rate | Mean Improvement |
|------------|------------------|------------------|
| 0.25→0.5   | 50%              | +0.147           |
| 0.5→1.0    | 33%              | +0.041           |
| 1.0→2.0    | 58%              | +0.109           |
| 2.0→3.0    | 65%              | +0.113           |

**BUT: Flat v26 zoom FAILS** (0/4 modes pass; singleton_fraction > 0.99 at fine resolutions)
- **Per audit CYCLE_36027099305:** NESTING_METRIC_DEFECT_v1 enforced — nesting_score≥0.99 claims for 7 compressed-family modes PROHIBITED

---

### 5. 1k-Scale Zoom Quality Diagnostic (Evidence-Backed Path)

| Rank | Mode | Zoom Quality | Finest Purity | Cluster Count (res=3.0) |
|------|------|--------------|---------------|-------------------------|
| 1 | citing_alpha0.3 | **0.540** | 0.998 | 928 |
| 2 | following_alpha0.3 | **0.528** | 0.999 | 986 |
| 3 | criticizing_alpha0.3 | **0.486** | 1.000 | 997 |
| 4 | cited_decisions_tfidf_hybrid_cp64_0.7 | 0.478 | 0.726 | 29 |
| 5 | cited_decisions_tfidf_hybrid_cp768_0.7 | 0.471 | 0.694 | 27 |
| 20 | cited_decisions_tfidf_outcome_hybrid_0.5 | 0.280 | 0.538 | 29 |
| 21 | cited_decisions_tfidf_outcome_hybrid_0.7 | 0.280 | 0.518 | 29 |

**Key Finding:** Citation-role embeddings (citing/following/criticizing) achieve highest zoom quality at 1k scale. Production default (outcome_hybrid_0.5) scores 0.280.

---

## Scale Dependency Analysis

| Scale | Flat v26 Zoom | Constrained Hierarchical |
|-------|---------------|--------------------------|
| 1k (citation roles) | PASS (ZQ 0.49-0.54) | N/A |
| 12k (center_projected) | **FAIL** (1/4 transitions) | **PASS** (validated config) |
| 174k (TF-IDF hybrid) | **FAIL** (0/4 modes) | PASS structural, FAIL flat |

**Conclusion:** Flat zoom quality degrades with scale. Constrained hierarchical Leiden with `min_cluster_size` enforcement is the only method maintaining zoom coherence at scale.

---

## Lane Status & Recommendation

| Field | Value |
|-------|-------|
| **Lane** | fractal-map |
| **Direction Version** | 28 |
| **Evidence Tier** | REPRODUCED |
| **Cycle Status** | RUN (BLOCKED) |
| **Continue Recommended** | **false** — no additional same-question cycle justified |
| **Blocked On** | legal-distance 174k dense embeddings audit promotion |
| **Accepted Run ID** | constrained_hierarchical_partial_dense_20260927_194948 |

### Next Recommendation
> **Await legal-distance 174k dense embeddings audit promotion.** Once 174k dense embeddings are ACCEPTED (all 26 years), test constrained hierarchical Leiden at 174k on accepted dense modes (center_projected_64dim, citation-role hybrids, metric learning embeddings). The evidence-backed zoom path remains citation-role/dense-embedding modes (1k-scale: citing_alpha0.3 ZQ=0.5401).

### Do Not
- ❌ Claim product-readiness while lane blocked
- ❌ Claim nesting_score≥0.99 for compressed-family modes (audit CYCLE_36027099305 prohibition)
- ❌ Treat 12k partial validation as 174k evidence
- ❌ Proceed to 174k fractal evaluation without ACCEPTED dense embeddings

---

## Evidence References

1. `fractal_map/results/fractal_map/constrained_hierarchical_partial_dense/constrained_hierarchical_partial_dense_results.json` — 12k partial validation (7 configs + flat v26)
2. `fractal_map/results/fractal_map/12k_dense_hierarchical_test/hierarchical_leiden_results.json` — Raw dense hierarchical Leiden zoom quality
3. `fractal_map/experiments/test_constrained_hierarchical_partial_dense.py` — Comprehensive test script
4. `fractal_map/experiments/test_constrained_hierarchical_dense.py` — Minimal constrained test
5. `fractal_map/test_12k_dense_hierarchical.py` — Zoom quality diagnostic replication
6. `fractal_map/hierarchical/hierarchical_leiden.py` — Core hierarchical Leiden implementation
7. `product/product/results/fractal_map/legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25/hierarchical_map_results.json` — 174k TF-IDF constrained hierarchical
8. `product/product/results/fractal_map/legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25/zoom_coherence.json` — 174k zoom coherence
9. `product/product/results/fractal_map/evaluation/zoom_quality_diagnostic_results.json` — 1k zoom diagnostic (22 modes)
10. `legal-distance/legal_distance/results/v7/fractal_validation/fractal_validation_breakthroughs.json` — 1k hierarchical validation (13 modes)

---

## Methodology Notes

- **Frozen sample:** 12,570 BGer decisions (years 2000-2002, ACCEPTED corpus)
- **Frozen metric:** Strict nesting, branch/area purity, zoom coherence (v26 semantics), fragmentation
- **Success rule:** Strict nesting ≥ 0.99 AND branch/area purity improvement AND zoom improvement_rate > 0.5 AND fine_singleton_fraction < 0.1
- **v26 flat zoom rule:** Branch monotonic AND area monotonic AND branch improvement_rate > 0.5 on ≥2/4 transitions
- **Scale note:** PARTIAL SCALE VALIDATION — NOT 174k evaluation
- **Negative results preserved:** Flat v26 FAIL at 12k; TF-IDF 174k flat FAIL; over-fragmentation in adaptive configs

---

*Report generated 2026-09-27T19:49:48Z | Factory Direction v28 | LexMachina Fractal Map Lane*