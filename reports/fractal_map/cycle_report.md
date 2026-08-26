# Fractal Map Lane — Cycle Report

**Factory Direction Version:** 1  
**Lane Question:** Establish a flat-map baseline, then test hierarchical/multi-resolution representations where zoom reveals legally coherent substructure rather than merely magnifying points.

## Summary

Established flat-map baseline using multilingual sentence embeddings (paraphrase-multilingual-mpnet-base-v2) + UMAP on 1000 BGer decisions (2024). Tested three hierarchical clustering families (Leiden on k-NN graph, Agglomerative, HDBSCAN) across multiple resolutions, plus multi-scale UMAP and local/zoom UMAP.

**Key finding:** The baseline embeddings are **dominated by language** (DE/FR/IT), not legal content. All clustering methods achieve 93-100% language purity but only 17-58% legal-area purity. This confirms the anti-noise principle: boilerplate and language artifacts dominate geometry.

## Experiments Run

### 1. Flat-Map Baseline
- **Embeddings:** sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)
- **Projection:** UMAP (n_neighbors=15, min_dist=0.1, cosine metric)
- **Data:** 1000 BGer decisions from 2024 (605 DE, 343 FR, 52 IT)

### 2. Hierarchical Clustering

| Method | Resolution/Param | Clusters | Legal-Area Purity | Language Purity | Chamber Purity |
|--------|-----------------|----------|-------------------|-----------------|----------------|
| Leiden | 0.25 | 3 | 0.23 | 0.93 | 0.28 |
| Leiden | 1.0 | 11 | 0.35 | 0.98 | 0.67 |
| Leiden | 3.0 | 21 | 0.43 | 0.99 | 0.80 |
| Agglomerative | 10 | 10* | 0.17 | 0.63 | 0.18 |
| Agglomerative | 200 | 200 | 0.58 | 1.00 | 0.80 |
| HDBSCAN | min_size=5 | 8 | 0.30 | 1.00 | 0.30 |
| HDBSCAN | min_size=10 | 3 | 0.26 | 1.00 | 0.26 |

*Agglomerative at n=10 has one giant cluster (963/1000) — imbalanced.

### 3. Multi-Scale UMAP
Tested n_neighbors ∈ {5, 10, 15, 30, 50, 100}. Smaller n_neighbors preserves local structure; larger reveals global language separation.

### 4. Hierarchical Zoom UMAP
Computed local UMAP within each Leiden cluster at resolutions 0.25→3.0. Zoom reveals substructure but subclusters remain language-coherent.

### 5. Local UMAP (50-NN neighborhoods)
Sampled 9 decisions (3 per language). Local neighborhoods are language-homogeneous.

## Evaluation Results

### Legal Coherence
- **Best legal-area purity:** Agglomerative n=200 (0.58) — but language purity = 1.0 (clusters are monolingual)
- **Leiden at resolution 3.0:** Legal purity 0.43, language purity 0.99, chamber purity 0.80
- **Legal/language ratio** never exceeds 0.58 — clusters are primarily language groups

### Hierarchy Consistency (Leiden)
- NMI between adjacent resolutions: 0.79–0.91
- Clusters split cleanly (parent→children mapping is consistent)
- **But:** splits follow language boundaries, not legal doctrine

### Cluster Size Distribution
- Leiden: Well-balanced across resolutions (mean size 333→48)
- Agglomerative: Highly skewed (one giant cluster + many singletons)
- HDBSCAN: Few large clusters + high noise (36-63% noise points)

## Critical Issue: Language Dominance

The multilingual embedding model separates by language, not legal substance. Evidence:
- Leiden resolution 0.25: 3 clusters = DE (482), FR+IT (369), DE-social-insurance (149)
- All HDBSCAN clusters are 100% language-pure
- Chamber purity correlates with language (chambers operate in specific languages)

**This violates the multi-view requirement:** Legal issue/doctrinal proximity is not recovered.

## Recommendations

### 1. PIVOT_WITHIN_MISSION: Improve Legal Distance Before Fractal Map
The fractal-map lane depends on legal-distance lane producing legally meaningful similarities. Current baseline is a **language map**, not a **law map**.

**Required from legal-distance lane:**
- Legal-specific embeddings (norm/article extraction, issue segmentation, citation graphs)
- Boilerplate suppression (anti-noise principle)
- Cross-language legal alignment (DE/FR/IT decisions on same doctrine should be neighbors)

### 2. Immediate Next Steps for Fractal Map (Once Legal Distance Improves)
- Re-run hierarchical clustering on legally-structured embeddings
- Test multi-view fractal map: separate layers for legal issues, reasoning, facts, citations
- Evaluate hierarchy coherence against Jurivoc/human indexing
- Build zoom-conditioned neighborhood API for product

### 3. Negative Results Preserved
- Language-dominated baseline embeddings (EXPLORATORY tier)
- All clustering results on baseline (EXPLORATORY tier)
- Hierarchy consistency metrics on language clusters (EXPLORATORY tier)

## State Update

```json
{
  "lane": "fractal-map",
  "direction_version": 1,
  "evidence_tier": "EXPLORATORY",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "fractal_map_run_20260826_001",
  "evidence_refs": [
    "results/fractal_map/baseline/embeddings.npy",
    "results/fractal_map/baseline/projection_2d.npy",
    "results/fractal_map/baseline/metadata.json",
    "results/fractal_map/hierarchical/leiden_multi_resolution.json",
    "results/fractal_map/hierarchical/agglomerative_multi_resolution_with_coherence.json",
    "results/fractal_map/hierarchical/hdbscan_multi_resolution_with_coherence.json",
    "results/fractal_map/hierarchical/multiscale_global_umap.json",
    "results/fractal_map/hierarchical/hierarchical_zoom_umap.json",
    "results/fractal_map/hierarchical/local_umap_samples.json",
    "results/fractal_map/evaluation/evaluation_results.json"
  ],
  "next_recommendation": "PIVOT_WITHIN_MISSION",
  "notes": "Flat-map baseline established but embeddings are language-dominated. Legal-area purity max 0.58 (at cost of 1.0 language purity). Fractal hierarchy consistent (NMI 0.79-0.91) but splits follow language, not law. Pivot to legal-distance lane for legally-structured representations before further fractal-map cycles."
}
```

## Evidence Tier Justification

**EXPLORATORY** — Experiments are reproducible and discriminating, but the core finding (language dominance) is a negative result about the baseline representation. No legal navigation capability is demonstrated. Results are preserved for comparison when legal-distance produces better embeddings.