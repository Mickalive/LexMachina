# Fractal-Map Lane — Cycle Report: Citation-Role Evaluation & Scale Dependency

**Cycle ID**: fractal_map_citation_role_eval_v28_20260928  
**Direction Version**: 28  
**Date**: 2026-09-28  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: COMPLETED  
**Continue Recommended**: false  
**Next Recommendation**: BLOCKED

---

## Executive Summary

The fractal-map lane remains **correctly BLOCKED** on the legal-distance 174k dense embeddings dependency (only 3/26 years ACCEPTED). This cycle evaluated the three citation-role embeddings at 1000-scale (citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3) against the frozen v26 zoom-quality rule, and documented the critical **scale dependency** that determines whether hierarchical fractal structure can be recovered.

**Key Result**: All three citation-role embeddings **FAIL** the v26 zoom-quality rule due to severe over-fragmentation (99%+ singletons at all Leiden resolutions). Only the hybrid `linear_hybrid05_concat` representation at 1000-scale **PASSES** (improvement_rate=0.687, nesting_score=1.0).

---

## Frozen v26 Zoom-Quality Rule

> **Rule**: A representation passes if ANY adjacent resolution pair achieves:
> - `improvement_rate > 0.5` (fine resolution refines coarse clusters meaningfully)
> - `singleton_fraction < 0.99` (no severe over-fragmentation at fine resolution)

This rule was frozen per audit CYCLE_36027099305 and cannot be weakened.

---

## Citation-Role Embeddings at 1000-Scale: Evaluation Results

| Representation | n_decisions | Embedding Dim | v26 Pass | Singleton Fraction | Clusters at Res 0.1 |
|---|---|---|---|---|---|
| citing_alpha0.3 | 1,000 | 64 | ❌ FAIL | 0.993 | 993 |
| following_alpha0.3 | 1,000 | 64 | ❌ FAIL | 0.997 | 997 |
| criticizing_alpha0.3 | 1,000 | 64 | ❌ FAIL | 0.993 | 993 |

### Detailed Findings

**Constrained Leiden Clustering** (min_cluster_size=10 enforcement):
- At ALL resolutions (0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0): ~993-997 clusters
- Min_cluster_size enforcement **ineffective** because no large clusters exist to merge into
- Every point is essentially its own cluster — the distance structure does not support meaningful grouping

**HDBSCAN**: 0 clusters at all min_cluster_size settings (5-50); all 1,000 points classified as noise

**Previous Claim vs. Reality**: Factory direction v28 cited ZQ=0.5401 (citing), 0.5280 (following), 0.4864 (criticizing) at 1000-scale. These values appear to be from an earlier evaluation with different methodology. Our rigorous v26 evaluation shows **all three FAIL**.

---

## The ONE Working Representation at 1000-Scale: linear_hybrid05_concat

| Metric | Value |
|---|---|
| **v26 Pass** | ✅ PASS |
| **improvement_rate** | 0.687 |
| **nesting_score** | 1.0 |
| **Coarse clusters** | 7 |
| **Fine clusters** | 131 |
| **Coarse overall purity** | 0.711 |
| **Fine overall purity** | 0.958 |
| **Composition** | Equal-weight concat: linear_metric_best (128D) + cited_outcome_hybrid_0.5 (128D) = 256D |
| **Adversarial gates** | Both PASS (jurist_pairwise=0.838, language_dominance=0.672) |

This hybrid combines **text-derived linear metric** + **citation+outcome hybrid** — NOT a pure citation-role view. It validates that **hybrid signals** can produce fractal structure at 1000-scale, but pure citation-role signals cannot.

---

## Scale Dependency: CONFIRMED

| Scale | Representation | Method | Result |
|---|---|---|---|
| **12k (2000-2002)** | Dense (center_projected) | Hierarchical Leiden | ✅ improvement_rate=0.80, zero fragmentation |
| **12k (2000-2002)** | Dense (center_projected) | Flat 4→16 zoom | ❌ improvement=-0.30 (fine WORSE than coarse) |
| **1,000** | Citation-role (3 roles) | Leiden (all resolutions) | ❌ 99%+ singletons, no structure |
| **1,000** | linear_hybrid05_concat | Hierarchical (coarse 0.5→fine 3.0) | ✅ improvement_rate=0.687, nesting=1.0 |
| **174k** | TF-IDF (4 modes) | Flat UMAP/Leiden | ❌ 0/4 pass v26, >99% singletons, median cluster size=1 |
| **174k** | TF-IDF | Constrained Leiden (min_cluster_size) | ⚠️ nesting=1.0 **by construction**, improvement_rate 57-90% structural, but **FAILS v26** (singleton_fraction > 0.99) |

### Critical Insight

**Hierarchical clustering works at small scale (12k dense) but collapses at large scale (174k TF-IDF).** The "constrained hierarchical Leiden" achieves nesting=1.0 **by construction** (enforcing minimum cluster size) but this is an artifact of the constraint, not evidence of genuine fractal structure. The v26 rule correctly rejects this because singleton_fraction remains > 0.99.

**Per Audit CYCLE_36027099305 (NESTING_METRIC_DEFECT_v1)**: Claims of nesting_score ≥ 0.99 for compressed-family modes are **PROHIBITED**. nesting_score=1.0 is citeable ONLY for 1000-scale by-construction modes with explicit scope annotation.

---

## Legal-Distance 174k Dense Embeddings Status

| Years | Status | Decisions | % of Corpus |
|---|---|---|---|
| 2000-2002 (3 years) | **ACCEPTED** | ~12,570 | 7.2% |
| 2003-2019 (17 years) | **PENDING AUDIT** | ~99k | ~57% |
| 2020-2025 (6 years) | **NOT STARTED** | ~62k | ~36% |

**Blocker**: Only 3/26 years (7.2%) have passed audit gate. The fractal-map lane cannot proceed with 174k dense evaluation until legal-distance delivers accepted embeddings.

---

## Evidence References

1. `product/results/fractal_map/citation_role_fractal_evaluation_v2.json` — This cycle's citation-role evaluation
2. `product/results/fractal_map/linear_hybrid05_concat/zoom_coherence.json` — Working hybrid at 1000-scale
3. `product/results/fractal_map/linear_hybrid05_concat/metadata.json` — Hybrid configuration
4. `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json` — 12k dense fractal metrics
5. `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json` — 3yr dense adversarial eval (all FAIL)
6. `evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — TF-IDF 174k formal suite (0/4 pass v26 zoom)
7. `product/results/fractal_map/hierarchical/leiden_multi_resolution.json` — 174k TF-IDF Leiden results
8. `product/results/fractal_map/hierarchical/hdbscan_multi_resolution.json` — 174k TF-IDF HDBSCAN results

---

## Recommendation: BLOCKED

**No further same-question cycles justified** without legal-distance 174k dense embeddings delivery.

### Why Not CONTINUE?
- Citation-role embeddings at 1000-scale are **exhaustively evaluated** and FAIL v26
- linear_hybrid05_concat works at 1000-scale but is a **hybrid**, not pure citation-role
- Scale dependency is **confirmed and documented** — no new information from further 1000-scale experiments
- 174k TF-IDF is **exhaustively evaluated** and FAILS v26
- Constrained Leiden at 174k achieves nesting=1.0 **by construction only** — rejected by v26 rule

### What Unblocks
Legal-distance lane delivering **ACCEPTED 174k dense embeddings** (all 26 years). Current progress: 3/26 years ACCEPTED.

### Product Decision Locked
- **NO product-readiness claim** while lane blocked (per factory direction v28)
- **Production default** remains `cited_outcome_hybrid_0.5` (TF-IDF hybrid, zero-shot, no GPU)
- **Evidence-backed zoom path** for future: hybrid text+citation representations (linear_hybrid05_concat pattern), NOT pure citation-role

---

## Appendix: v26 Zoom-Quality Rule Details

The rule requires **monotonic zoom refinement**: when zooming from coarse to fine resolution, clusters should become MORE pure (not less), and the fine resolution should not be dominated by singletons.

```
PASS if: improvement_rate > 0.5 AND singleton_fraction < 0.99
FAIL if: improvement_rate ≤ 0.5 OR singleton_fraction ≥ 0.99
```

This rule was frozen before any results were observed and has been applied consistently across all evaluations.

---

**End of Report**