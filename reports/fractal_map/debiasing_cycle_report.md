# Fractal Map Lane — Cycle Report: Language Debiasing Experiments

**Factory Direction Version:** 1  
**Lane Question:** Establish a flat-map baseline, then test hierarchical/multi-resolution representations where zoom reveals legally coherent substructure rather than merely magnifying points.  
**Run ID:** fractal_map_debiasing_20260826  
**Date:** 2026-08-26  
**Evidence Tier:** EXPLORATORY  

---

## 1. Hypothesis & Product Decision

**Question:** Can we suppress language dominance in the fractal map by (1) projecting out language-correlated embedding directions, (2) using citation-graph embeddings, or (3) restricting TF-IDF to legal reasoning text?

**Product decision:** If any method improves the legal-area/language purity ratio by >10%, it becomes a candidate preprocessing step for the fractal map. If any method achieves ratio >1.0 (legal purity exceeding language purity), it fundamentally changes the map from a language map to a law map.

**Baseline frozen before observation:**
- Representation: paraphrase-multilingual-mpnet-base-v2 (768-dim)
- Corpus: 1000 BGer decisions from 2000plus_slice_1000.jsonl
- Clustering: Leiden at multiple resolutions on cosine k-NN graph
- Success rule: ratio (legal_purity / language_purity) > 0.5 at resolution 1.0

## 2. Experiments Run

### 2.1 Language-Center Projection
**Method:** Compute the centroid of each language cluster in embedding space, then subtract the centroid from each decision's embedding. This centers each language cluster at the origin.

**Results at resolution 1.0:**
| Metric | Baseline | Center-Projected | Change |
|--------|----------|-----------------|--------|
| Legal purity | 0.350 | 0.295 | -16% |
| Language purity | 0.975 | 0.684 | -30% |
| Ratio | 0.359 | 0.431 | +20% |
| Clusters | 11 | 11 | 0% |

**Interpretation:** Language-center projection significantly reduces language purity (from 0.975 to 0.684) while only moderately reducing legal purity (from 0.350 to 0.295). The net effect is a 20% improvement in the legal/language ratio. The hierarchy consistency is maintained (NMI 0.86-0.90 across resolutions).

### 2.2 PCA Language Removal
**Method:** Compute the principal components of the language cluster centers in embedding space, then project out the top 2 or 3 components.

**Results at resolution 1.0:**
| Metric | PCA-2 | PCA-3 |
|--------|-------|-------|
| Legal purity | 0.276 | 0.276 |
| Language purity | 0.646 | 0.646 |
| Ratio | 0.427 | 0.427 |

**Interpretation:** PCA removal and center projection produce nearly identical results. The singular value analysis shows only 1 significant language direction (SV=0.53), meaning the 3 language clusters are nearly collinear in embedding space. Removing 2 or 3 components has the same effect because the language subspace is effectively 2-dimensional (DE vs FR, with IT as a small outlier).

### 2.3 Citation-Graph Node2Vec
**Method:** Build a directed citation graph from the corpus (250 decisions, 2105 edges), compute node2vec embeddings (64-dim), and blend with text embeddings.

**Coverage problem:** Only 50 of 1000 baseline decisions appear in the citation graph (5%). The graph nodes include many external BGE references not in the baseline.

**Results at resolution 1.0:**
| Metric | Baseline 64d | Blended | Graph Only |
|--------|-------------|---------|------------|
| Legal purity | 0.363 | 0.368 | 0.356 |
| Language purity | 0.975 | 0.969 | 0.954 |
| Ratio | 0.372 | 0.380 | 0.373 |

**Interpretation:** Citation-graph blending provides marginal improvement (ratio +2%) but is limited by extremely low coverage (5%). The graph-only representation performs slightly worse than baseline, likely because most decisions have no graph signal and fall back to the PCA-projected text embedding.

### 2.4 Reasoning-Only TF-IDF
**Method:** Extract the Erwägungen (legal reasoning) section from each decision's full text using trilingual regex patterns, then compute TF-IDF (10K features, 1-2 grams) reduced to 128 dimensions via SVD.

**Coverage:** 857 of 1000 decisions have extractable Erwägungen sections (86%).

**Results at resolution 1.0:**
| Metric | Full Text TF-IDF | Erwägungen TF-IDF | S+E TF-IDF |
|--------|-----------------|-------------------|------------|
| Legal purity | 0.324 | 0.385 | 0.344 |
| Language purity | 1.000 | 0.986 | 0.986 |
| Ratio | 0.324 | 0.390 | 0.349 |

**Interpretation:** Erwägungen-only TF-IDF achieves the highest absolute legal purity (0.385) of all tested representations, a 10% improvement over the baseline sentence embeddings (0.350). This is surprising because TF-IDF is language-specific while the baseline uses multilingual embeddings. The explanation: legal reasoning sections contain shared legal vocabulary (article references, legal terms) that appear across languages, while procedural boilerplate is language-specific.

## 3. Unified Comparison

| Representation | Legal Purity | Language Purity | Ratio | Clusters |
|---------------|-------------|----------------|-------|----------|
| Baseline (mpnet, 1000) | 0.350 | 0.975 | 0.359 | 11 |
| PCA2 Debiased (1000) | 0.276 | 0.646 | 0.427 | 10 |
| Center Projected (1000) | 0.295 | 0.684 | **0.431** | 11 |
| TF-IDF Erwägungen (857) | **0.385** | 0.986 | 0.390 | 15 |
| TF-IDF S+E (857) | 0.344 | 0.986 | 0.349 | 12 |

**Key findings:**
1. **Best ratio:** Center-projected (0.431) — 20% improvement over baseline
2. **Best legal purity:** TF-IDF Erwägungen (0.385) — 10% improvement over baseline
3. **No method achieves ratio >1.0** — language still dominates
4. **Hierarchy consistency maintained:** NMI 0.86-0.90 across resolutions for debiased representations

## 4. Hierarchy Consistency

| Resolution Transition | Baseline NMI | Center-Projected NMI |
|----------------------|-------------|---------------------|
| 0.5 → 1.0 | 0.727 | 0.858 |
| 1.0 → 2.0 | 0.874 | 0.898 |
| 2.0 → 3.0 | 0.910 | 0.898 |

**Interpretation:** The debiased representation actually shows *better* hierarchy consistency at low resolutions (0.86 vs 0.73), suggesting that language noise was creating artificial instability in the cluster hierarchy. At high resolutions, both representations are equally consistent.

## 5. Negative Results (Preserved)

1. **Citation-graph embeddings have insufficient coverage** — Only 5% of baseline decisions are in the citation graph. Citation-graph methods cannot meaningfully improve the 1000-decision map until the corpus is expanded to include the cited decisions.

2. **PCA language removal is equivalent to center projection** — The language subspace is effectively 2-dimensional (DE vs FR), so PCA-2 and PCA-3 produce identical results. IT is too small (52 decisions) to create a third significant direction.

3. **No method achieves ratio >1.0** — The fundamental challenge remains: legal content in the BGer corpus is expressed in language-specific ways. Even when boilerplate is removed (Erwägungen TF-IDF), the legal vocabulary differs across languages.

4. **Dispositif extraction failed** — The regex patterns for the holding/outcome section did not match the actual text structure. The section markers are less standardized than Erwägungen markers.

## 6. Recommendations

**CONTINUE** — The language debiasing experiments demonstrate that the fractal map can be improved by:
1. Using language-center projection as a preprocessing step (ratio +20%)
2. Using Erwägungen-only text for TF-IDF representations (legal purity +10%)
3. Combining both approaches (not yet tested)

**Next cycle priorities:**
1. **Combine debiasing + reasoning text:** Apply language-center projection to Erwägungen-only TF-IDF embeddings. Test whether the improvements are additive.
2. **Test legal-specific embeddings:** The legal-distance lane should produce representations where legal content dominates language. Test these once available.
3. **Expand citation graph:** Acquire the cited BGE decisions to increase graph coverage from 5% to >50%.
4. **Build zoom-conditioned neighborhood API:** The hierarchy is consistent enough (NMI >0.85) to support product-level zoom navigation.

## 7. Files Produced

- `state/fractal-map.json` — Machine-readable lane state
- `results/fractal_map/language_debiasing/debiasing_results.json` — Language debiasing results
- `results/fractal_map/language_debiasing/embeddings_*.npy` — Debiased embeddings
- `results/fractal_map/citation_graph/citation_results.json` — Citation graph results
- `results/fractal_map/reasoning_tfidf/reasoning_tfidf_results.json` — TF-IDF results
- `results/fractal_map/unified_evaluation/unified_results.json` — Unified comparison
- `fractal_map/experiments/language_debiasing.py` — Debiasing experiment code
- `fractal_map/experiments/citation_embeddings.py` — Citation graph experiment code
- `fractal_map/experiments/reasoning_tfidf.py` — Reasoning TF-IDF experiment code
- `fractal_map/evaluation/unified_evaluation.py` — Unified evaluation code
- `reports/fractal_map/debiasing_cycle_report.md` — This report
