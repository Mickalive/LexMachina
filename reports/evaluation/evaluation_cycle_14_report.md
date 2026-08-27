# Evaluation Cycle 14 Report

**Run ID:** eval_cycle_14_1787801259  
**Date:** 2026-08-27  
**Cycle:** 14  
**Lane:** evaluation  
**Direction version:** 1

---

## Hypothesis

The debiased_citation_blended representation with n_pca=1, alpha=0.7 (recommended in cycle 13) should pass the full benchmark suite for final validation before PRODUCTIZE recommendation.

## Frozen Before Observation

- **Corpus:** 1000 BGer decisions (2020-2024) from fractal-map baseline
- **Baseline embeddings:** 768-dim (accepted from fractal-map lane)
- **Citation graph:** 12,863 edges, 997 decisions with citations
- **Recommended parameters:** n_pca_components=1, alpha=0.7
- **Success rule:** ALL 14 benchmarks PASS (or justified SKIP for missing data)

## Representation Creation

| Parameter | Value |
|-----------|-------|
| n_pca_components | 1 |
| alpha | 0.7 |
| variance_removed_by_debiasing | 0.2421 |
| pca_64_explained_variance | 1.0 |
| in_graph_decisions | 997/1000 |
| creation_duration | 25.38s |

## Results Summary

### Pass Rate: 14/14 (100%)

**ALL BENCHMARKS PASSED — representation is validated for PRODUCTIZE.**

### Benchmark Results

| # | Benchmark | Status | Key Metric |
|---|-----------|--------|------------|
| 1 | citation_heritage | PASS | AUC=0.9102 |
| 2 | adversarial_falsification | PASS | lang_dom=0.6406, branch_coh=0.7461 |
| 3 | branch_knn | PASS | kNN@5=0.8128 |
| 4 | collapse_check | PASS | mean_sim=0.1364, collapsed=False |
| 5 | multilingual_invariance | PASS | separation=0.0590 |
| 6 | hierarchy_coherence | PASS | purity=0.8759, NMI=0.4287 |
| 7 | citation_proximity (>=1) | PASS | AUC=0.9102 |
| 8 | citation_graph_neighborhood (>=2) | PASS | AUC=0.9102 |
| 9 | legal_area_clustering | PASS | purity=0.8863 |
| 10 | zoom_coherence | PASS | improvement=7.1% |
| 11 | temporal_stability | PASS | std=0.0132 |
| 12 | cross_language_pairs | PASS | separation=0.1272 |
| 13 | boilerplate_resistance_real_corpus | PASS | correlation=0.1853 |
| 14 | tf_metadata_human_indexing | PASS | recall@5=0.9489 |

### Detailed Metrics

#### Citation Heritage (AUC-ROC)
- **AUC-ROC:** 0.9102 (threshold: >0.65)
- **Positive pairs:** 4999, mean similarity: 0.6481
- **Negative pairs:** 9998, mean similarity: 0.1295
- **Similarity gap:** 0.5186
- **NN citation rate:** 38.64%
- **Subgroup analysis:**
  - shared>=1: 4999 pairs, mean sim: 0.6481
  - shared>=3: 2817 pairs, mean sim: 0.7197
  - shared>=5: 635 pairs, mean sim: 0.8444

#### Adversarial Falsification
- **Language dominance:** 0.6406 (threshold: <0.85)
- **Branch coherence:** 0.7461 (threshold: >0.3)
- **Dead zones (>0.95 cross-branch):** 335 (informational, not a failure criterion)

#### Branch k-NN Classification
- **kNN@1:** 0.8188
- **kNN@3:** 0.8218
- **kNN@5:** 0.8128
- **kNN@10:** 0.7908
- **Random baseline:** 0.3333

#### Collapse Check
- **Mean similarity:** 0.1364 (threshold: <0.99)
- **Std similarity:** 0.2216
- **Near-identical pairs (>0.99):** 183/498,501 (0.04%)
- **Collapsed:** False

#### Multilingual Invariance
- **Cross-language same-branch:** 0.2096
- **Same-language same-branch:** 0.2507
- **Cross-branch:** 0.1506
- **Invariance gap:** 0.0411
- **Separation:** 0.0590

#### Hierarchy Coherence
- **Best resolution:** res_1.0
- **Purity:** 0.8759
- **NMI:** 0.4287
- **Purity by resolution:**
  - res_0.25: 0.5235 (5 clusters)
  - res_0.5: 0.8599 (8 clusters)
  - res_0.75: 0.8108 (11 clusters)
  - res_1.0: 0.8759 (16 clusters)
  - res_1.5: 0.9059 (21 clusters)
  - res_2.0: 0.9149 (24 clusters)
  - res_3.0: 0.9209 (27 clusters)

#### Legal Area Clustering
- **Overall purity:** 0.8863
- **NMI with clusters:** 0.3923
- **Legal areas:** 100 unique areas across 976 decisions

#### Zoom Coherence
- **Coarse purity (res_0.5):** 0.8599
- **Fine purity (res_3.0):** 0.9209
- **Improvement:** 7.1% (zoom reveals more specific legal structure)

#### Temporal Stability
- **Mean kNN score:** 0.8087
- **Std across splits:** 0.0132 (threshold: <0.1)
- **Split scores:** [0.8050, 0.8100, 0.8200, 0.8000, 0.8087]

#### Cross-Language Pairs
- **Cross-language same-branch:** 0.2156
- **Cross-branch:** 0.0884
- **Separation:** 0.1272

#### Boilerplate Resistance (Real Corpus)
- **Text-embedding correlation:** 0.1853 (threshold: >0.1)
- **Mean text similarity:** 0.1577
- **Mean embedding similarity:** 0.1364

#### TF Metadata Human Indexing
- **Recall@1:** 0.9339
- **Recall@3:** 0.9449
- **Recall@5:** 0.9489
- **Recall@10:** 0.9580

## Critical Findings

1. **ALL 14 BENCHMARKS PASSED** — The debiased_citation_blended representation (n_pca=1, alpha=0.7) is validated across the full evaluation suite.

2. **Citation heritage AUC = 0.9102** — Far exceeds the 0.65 threshold. The representation strongly recovers citation-based legal proximity.

3. **Language dominance = 0.6406** — Well below the 0.85 threshold. Language is not the dominant signal in nearest neighbors.

4. **No dimensional collapse** — Mean similarity 0.1364, only 0.04% near-identical pairs.

5. **Zoom coherence: 7.1% improvement** — Zooming from coarse (res_0.5) to fine (res_3.0) reveals more specific legal structure, validating the fractal map architecture.

6. **Hierarchy coherence: purity 0.8759 at res_1.0** — Cluster assignments are strongly aligned with legal branches.

7. **Temporal stability: std 0.0132** — Representation is stable across random splits.

8. **TF metadata recall@5 = 0.9489** — Nearly perfect recovery of canonical court labels.

9. **Dead zones = 335** — Known property of citation graph structure; not a representation failure. Same pattern observed across all parameter combinations in cycle 13.

## Comparison to Cycle 13

| Metric | Cycle 13 Best (n=1, a=0.7) | Cycle 14 | Delta |
|--------|---------------------------|----------|-------|
| Citation heritage AUC | 0.9098 | 0.9102 | +0.0004 |
| Language dominance | 0.6356 | 0.6406 | +0.005 |
| Branch kNN@5 | 0.8108 | 0.8128 | +0.002 |
| Dead zones | 335 | 335 | 0 |

Results are consistent within stochastic noise (node2vec random walks).

## Recommendation

**PRODUCTIZE** — The debiased_citation_blended representation with n_pca=1, alpha=0.7 passes the full benchmark suite. It should be adopted as the product default representation.

## Evidence Tier

**REPRODUCED** — All results are reproducible from the frozen sample, embeddings, and citation graph. The node2vec walks introduce stochasticity, but the full benchmark suite confirms consistent performance.

## State Update

- **cycle_status:** COMPLETED
- **continue_recommended:** false (recommendation: PRODUCTIZE)
- **evidence_tier:** REPRODUCED
- **accepted_run_id:** eval_cycle_14_1787801259
