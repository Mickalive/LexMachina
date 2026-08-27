# Evaluation Cycle 10: Citation-Heritage Benchmark + Benchmark Sensitivity Validation

**Run ID:** eval_cycle_10_1787797258  
**Date:** 2026-08-27  
**GitHub Run:** 33032678575  
**Cycle Status:** COMPLETED  
**Evidence Tier:** REPRODUCED

---

## Hypothesis

A citation-heritage benchmark built from the real corpus citation graph (12,863 edges, 7,665 cited nodes) will discriminate between representations based on their ability to place citation-linked decisions close together. Additionally, a deliberately degraded representation (row-shuffled) should fail all benchmarks as a sanity check.

## Frozen Sample & Metrics

- **Corpus:** 1,000 BGer decisions (2020-2024) from fractal-map baseline metadata
- **Representations:** baseline (768-dim), language_debiased_pca2 (768-dim), citation_blended (64-dim), citation_graph_only (64-dim), random_degraded (768-dim, row-shuffled)
- **Citation graph:** From `bger_2000plus_slice_1000.jsonl` (997 decisions with citations, 12,863 edges)
- **Citation pairs:** 5,000 pairs with >=1 shared citation (max shared: 25, median: 3)
- **Success rule:** Citation-heritage AUC > 0.6 on at least one representation; random-degraded AUC < 0.55

## Key Findings

### 1. Citation-Heritage Benchmark VALIDATED

| Representation | Citation AUC | Similarity Gap | Dead Zones >0.95 | Language Dom | Branch k-NN@5 |
|---|---|---|---|---|---|
| baseline | 0.637 | 0.021 | 1,664 | 0.982 | 0.957 |
| language_debiased_pca2 | 0.673 | 0.017 | 1,752 | 0.818 | 0.967 |
| citation_blended | **0.679** | **0.226** | **0** | 0.982 | 0.955 |
| citation_graph_only | 0.668 | 0.215 | 2 | 0.964 | 0.942 |
| random_degraded | 0.520 | 0.003 | 8,847 | 0.493 | 0.379 |

**Citation-blended is BEST:** Highest AUC (0.679), highest similarity gap (0.226), zero dead zones.

### 2. Sanity Check PASSED

Random-degraded representation (row-shuffled) shows:
- AUC: 0.520 < 0.55 ✓
- Language dominance: 0.493 (random, ~4 branches × 3 languages)
- Branch coherence: 0.362 (near random baseline 0.25)
- k-NN accuracy: 0.379 (near random 0.25)
- Dead zones: 8,847 (massive, as expected)

**Note on degradation method:** Initial attempt used dimension permutation, which is ineffective for cosine similarity in high dimensions (preserves dot product distribution). Row shuffling correctly destroys embedding structure.

### 3. Citation Pairs Are Much More Similar

citation_blended has a similarity gap of 0.226 (citation-linked pairs are 0.226 more similar than random pairs), while baseline has only 0.021. This confirms that citation-blended embeddings successfully capture citation relationships.

### 4. Dead Zones Are Discriminating

- baseline: 1,664 dead zones (high similarity across branches)
- blended: 0 dead zones (citation awareness eliminates cross-branch confusion)
- degraded: 8,847 dead zones (random = all cross-branch)

### 5. Language Dominance NOT Resolved

All real representations still show high language dominance (>0.81). The product needs BOTH citation awareness AND explicit language debiasing.

## Benchmark Suite Status (13 benchmarks)

| Benchmark | Status | Discriminating |
|---|---|---|
| citation_heritage | NEW, PASSED | ✓ Yes |
| adversarial_falsification | PASSED | ✓ Yes |
| tf_metadata_human_indexing | PASSED | ✓ Yes |
| temporal_stability | PASSED | ✓ Yes |
| citation_graph_neighborhood | PASSED | ✓ Yes |
| citation_proximity | PASSED | ✓ Yes |
| legal_area_clustering | PASSED | ✓ Yes |
| zoom_coherence | PASSED | ✓ Yes |
| neighbor_relevance | PASSED | ✓ Yes |
| boilerplate_resistance | SKIPPED (needs real corpus) | - |
| multilingual_invariance | SKIPPED (needs parallel decisions) | - |
| hierarchy_coherence | SKIPPED (needs Jurivoc) | - |
| corpus_stability | SKIPPED (needs growth simulation) | - |

## Product Implications

1. **citation_blended** is the best representation for the product: highest citation-heritage AUC, zero dead zones, excellent branch k-NN.
2. **Language debiasing** is still needed: all representations have language dominance > 0.81.
3. **Citation-heritage benchmark** is ready for use by the legal-distance lane to evaluate new representations.
4. **Dead zone count** is a reliable adversarial metric: discriminating between real (0-1,752) and random (8,847) representations.

## Negative Results

1. **Dimension permutation is ineffective** for degrading cosine similarity in high dimensions. Row shuffling is required.
2. **Citation proximity** remains the hardest target (best AUC from previous cycles: 0.656 < 0.75).
3. **Jurivoc-based evaluation** not yet possible (no Jurivoc data in corpus).

## Next Recommendation

**CONTINUE:** The citation-heritage benchmark is validated and discriminating. Next cycle should:
1. Test language-debiased citation-blended representation (if legal-distance lane produces one)
2. Build real cross-language pairs from corpus for multilingual invariance test
3. Run boilerplate resistance on real corpus data
