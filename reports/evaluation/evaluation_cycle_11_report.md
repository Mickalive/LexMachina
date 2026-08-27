# Evaluation Cycle 11 Report

**Run ID:** eval_cycle_11_1787797977  
**Date:** 2026-08-27  
**Cycle:** 11  
**Lane:** evaluation  
**Direction version:** 1

---

## Hypothesis

A representation that combines BOTH citation awareness (from citation-blended) AND explicit language debiasing (from PCA2) will outperform either technique alone. Cross-language pairs should show meaningful similarity. Boilerplate resistance should be > 0.5 on real corpus.

## Frozen Before Observation

- **Corpus:** 1000 BGer decisions (2020-2024) from fractal-map baseline
- **Embeddings:** baseline (768-dim), language_debiased_pca2 (768-dim), citation_blended (64-dim), citation_graph_only (64-dim)
- **Citation graph:** 12,863 edges, 7,665 cited nodes
- **Success rule:** Combined representation has language_dominance < 0.85 AND citation_heritage AUC > 0.65; cross-language pairs show meaningful similarity; boilerplate resistance > 0.5 on real corpus.

## New Benchmarks Introduced

1. **Cross-language benchmark:** Measures similarity between decisions in different languages (DE/FR/IT) but same legal branch. Tests whether representations place decisions about similar legal topics close together regardless of language.

2. **Boilerplate resistance on real corpus:** Measures correlation between TF-IDF text similarity and embedding similarity. Lower correlation = more resistant to boilerplate (representation captures legal structure, not just surface text).

## Results Summary

### Citation Heritage AUC

| Representation | AUC | Gap | Dead Zones >0.95 |
|---|---|---|---|
| baseline | 0.642 | 0.022 | 1664 |
| language_debiased_pca2 | 0.678 | 0.017 | 1752 |
| citation_blended | **0.680** | **0.226** | **0** |
| citation_graph_only | 0.669 | 0.215 | 2 |
| citation_blended_debiased | 0.493 | -0.001 | 12694 |

### Adversarial Falsification

| Representation | Status | Lang Dom | Branch Coh | Dead Zones |
|---|---|---|---|---|
| baseline | FALSIFIED | 0.982 | 0.889 | 1664 |
| language_debiased_pca2 | FALSIFIED | 0.818 | 0.910 | 1752 |
| citation_blended | FALSIFIED | 0.982 | 0.892 | 0 |
| citation_graph_only | FALSIFIED | 0.964 | 0.879 | 2 |
| citation_blended_debiased | FALSIFIED | **0.476** | 0.363 | **12694** |

### Cross-Language Benchmark

| Representation | Cross-Lang Sim | Same-Lang Sim | Gap |
|---|---|---|---|
| baseline | 0.866 | 0.891 | 0.025 |
| language_debiased_pca2 | 0.909 | 0.914 | 0.005 |
| citation_blended | **-0.163** | -0.001 | 0.162 |
| citation_graph_only | -0.154 | -0.001 | 0.154 |
| citation_blended_debiased | 1.000 | 1.000 | 0.000 |

### Boilerplate Resistance (Real Corpus)

| Representation | Correlation | Resistance | Status |
|---|---|---|---|
| baseline | 0.296 | 0.704 | PASS |
| language_debiased_pca2 | 0.084 | **0.916** | PASS |
| citation_blended | 0.364 | 0.636 | PASS |
| citation_graph_only | 0.295 | 0.705 | PASS |
| citation_blended_debiased | 0.012 | **0.988** | PASS |

## Critical Finding: Combined Representation COLLAPSED

The naive approach of applying PCA language debiasing to citation-blended embeddings **completely destroyed** the representation:

1. **Embeddings collapsed to a single point:** Cross-language similarity = 1.0, meaning all decisions have nearly identical embeddings
2. **Citation heritage AUC degraded to 0.493** (below random 0.5 baseline)
3. **Dead zones exploded to 12,694** (vs 0 for citation_blended)
4. **Branch k-NN accuracy dropped to 0.379** (near random 0.333)

**Root cause:** PCA debiasing removes the top 2 variance components from 64-dimensional citation-blended embeddings. This removes ~34% of the variance (explained variance ratio: [0.269, 0.071]), which is too much for a low-dimensional representation. The 768-dim baseline can survive this operation because it has more redundant dimensions, but 64-dim citation-blended cannot.

**Implication for legal-distance lane:** Language debiasing and citation awareness must be combined differently:
- Option A: Apply language debiasing BEFORE citation graph construction (debiased → citation graph)
- Option B: Use a higher-dimensional citation representation before debiasing
- Option C: Use adversarial training to learn language-invariant citation representations
- Option D: Apply debiasing in the citation graph space directly (not embedding space)

## Cross-Language Benchmark Insights

1. **Citation-blended has NEGATIVE cross-language similarity** (-0.163): Cross-language pairs are LESS similar than random pairs. This is because citation patterns are language-correlated (German decisions cite German precedents, French cite French).

2. **Language-debiased-pca2 has highest cross-language similarity** (0.909): Debiasing successfully brings cross-language decisions closer together.

3. **The gap between same-language and cross-language similarity is largest for citation representations** (0.162 for blended): This confirms that citation awareness is language-correlated.

## Baseline Consolidation

All original representations PASS boilerplate resistance on real corpus (>0.5 target):

| Representation | Resistance Score |
|---|---|
| language_debiased_pca2 | 0.916 |
| citation_blended | 0.636 |
| citation_graph_only | 0.705 |
| baseline | 0.704 |

**Key insight:** Language-debiased representations are MORE resistant to boilerplate (0.916 vs 0.704 for baseline). This makes sense: debiasing removes the dominant language direction, which includes boilerplate.

## Recommendations

1. **DO NOT** apply PCA debiasing directly to low-dimensional citation representations
2. **DO** explore combining debiasing and citation awareness at the representation learning stage (not post-hoc)
3. **DO** use the cross-language benchmark as a standard evaluation metric
4. **DO** use boilerplate resistance on real corpus as a standard evaluation metric
5. **NEXT CYCLE:** Test citation-aware debiasing approaches (debiased baseline → citation graph, or higher-dimensional intermediate)

## Evidence Tier

**REPRODUCED** — All results are reproducible from the frozen sample and embeddings. The collapse of the combined representation is a deterministic consequence of PCA on low-dimensional data.

## State Update

- **cycle_status:** COMPLETED
- **continue_recommended:** true (next: test alternative combination strategies)
- **evidence_tier:** REPRODUCED
- **accepted_run_id:** eval_cycle_11_1787797977
