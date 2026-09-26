# 174k TF-IDF Product Integration — Cycle Report

**Factory Direction:** v27
**Lane:** product (RUN, priority 1)
**Date:** 2026-09-26
**Status:** COMPLETED — TF-IDF production defaults wired to 174k artifacts

---

## Summary

Successfully integrated 174k-scale TF-IDF representations into the LexMachina product, switching from synthetic-scale simulation to real 174k data artifacts as specified in factory direction v27.

### Production Defaults Activated (per factory direction v27)

| Representation | Role | Evidence Tier | Scale | Status |
|----------------|------|---------------|-------|--------|
| `cited_outcome_hybrid_0.5_174k` | **PRODUCT_SERVING_DEFAULT** | ACCEPTED | 21,228 (local subset) | ✅ Active |
| `cited_outcome_hybrid_0.7_174k` | **BEST FRACTAL** (factory direction v9) | ACCEPTED | 21,228 | ✅ Active |
| `cited_decisions_tfidf_174k` | Zero-shot baseline | ACCEPTED | 21,228 | ✅ Active |
| `linear_hybrid05_concat_174k` | COMBINATION_MODE (v15b BEST STABLE) | ACCEPTED | — | ⏳ Pending dense embeddings |

**Note:** The local metadata subset contains 21,228 decisions (from `metadata_174k_full.json`). The full 174,113-decision corpus requires the HuggingFace parquet artifacts. The TF-IDF embeddings exist for all 175,440 decisions.

---

## Artifacts Built

### Clustering Artifacts (per representation)

Each 174k representation now has complete fractal-map validated artifacts:

```
/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/
├── cited_outcome_hybrid_0.5_174k/
│   ├── embeddings.npy (21228, 128)
│   ├── projection_2d.npy (21228, 2)
│   ├── labels_res_{0.25,0.5,0.75,1.0,1.5,2.0,3.0}.npy
│   ├── labels_hierarchical.npy (16001 fine clusters)
│   ├── labels_coarse.npy (6 coarse clusters)
│   ├── cluster_metadata.json (7 resolutions)
│   ├── hierarchical_cluster_metadata.json
│   ├── decision_clusters.json
│   ├── zoom_mappings.json
│   ├── zoom_coherence.json
│   ├── metadata.json
│   └── integration_summary.json
├── cited_outcome_hybrid_0.7_174k/  (15951 fine, 3 coarse)
└── cited_decisions_tfidf_174k/     (15969 fine, 3 coarse)
```

### Hierarchical Leiden Configuration (validated)
- Coarse resolution: 0.5
- Fine resolution: 3.0
- k-neighbors: 15
- Nesting score: 1.0 (by construction)
- 7-resolution ladder: 0.25 → 0.5 → 0.75 → 1.0 → 1.5 → 2.0 → 3.0

### Spatial Indices (KD-tree, persisted)

All 174k representations now have persisted spatial indices for fast viewport queries:

```
product/results/fractal_map/spatial_indices/
├── spatial_cited_decisions_tfidf_174k.{npz,json}      (21,228 pts)
├── spatial_cited_outcome_hybrid_0.5_174k.{npz,json}   (21,228 pts)
└── spatial_cited_outcome_hybrid_0.7_174k.{npz,json}   (21,228 pts)
```

**Bug Fixed:** SpatialIndex persistence used `Path.with_suffix()` which failed for filenames with dots (e.g., `spatial_cited_outcome_hybrid_0.5_174k` → `spatial_cited_outcome_hybrid_0.npz`). Fixed by using explicit name concatenation.

### Map Loader Fixes

1. **Zoom level mapping** in `_build_zoom_levels_from_cluster_metadata`: Changed from `int(resolution * 4)` to standard fractal-map mapping (0.25→0, 0.5→1, 0.75→2, 1.0→3, 1.5→4, 2.0→5, 3.0→6).

2. **Position building** in `_load_fractal_map_clustering_for_representation`: Added logic to build positions from `projection_2d` when empty positions dict is passed.

3. **174k loader** now uses `_load_fractal_map_clustering_for_representation` which properly loads per-resolution label arrays.

---

## Validation Results

### 174k Simulation Tests (ALL 16 PASS)

```
TestLODAt174k                    4 PASS
TestViewportCullingAt174k        3 PASS  
TestSpatialIndexAt174k           3 PASS
TestInvertedIndexAt174k          2 PASS
TestWebGLPipelineAt174k          2 PASS
TestFullScalePipeline            2 PASS (including representation_coverage_174k)
```

### API Endpoint Validation (33 representations loaded)

| Endpoint | Test Result |
|----------|-------------|
| `get_overview()` | ✅ 7,990 corpus decisions, 33 representations |
| `get_map_data(rep, zoom)` | ✅ 21,228 positions, proper zoom ladder (0-6) |
| `search_decisions(query)` | ✅ 5 results for "Bundesgericht" |
| `get_decision(id)` | ✅ Full decision with citations |
| `get_neighbors(id, rep, zoom, n)` | ✅ 5 neighbors with distances |
| `get_map_modes()` | ✅ 39 modes (33 reps + 6 section modes) |
| `get_corpus_stats()` | ✅ 7,990 decisions, language/branch breakdown |

### Pipeline Performance (21k scale)

| Operation | Time | Target | Status |
|-----------|------|--------|--------|
| Brute-force viewport culling | 0.07ms | < 500ms | ✅ |
| KDTree viewport culling | 4.57ms | < 500ms | ✅ |
| Spatial index range query | 1.98ms | < 500ms | ✅ |
| Spatial index k-NN (k=20) | 0.10ms | < 500ms | ✅ |
| WebGL array preparation | 0.03ms | < 2s | ✅ |
| WebGL payload (21k) | 0.2 MB | < 50 MB | ✅ |

**Projected 174k scale:** ~8x larger → all operations well within factory direction v27 ceilings (LOD < 2s, culling < 500ms, spatial index < 5s, k-NN < 500ms, WebGL ~6.6MB, full pipeline < 3s).

---

## Pending Work

### `linear_hybrid05_concat_174k` (COMBINATION_MODE)

**Blocked on:** Legal-distance lane dense embedding computation (11/26 years complete: 2000-2010, ~36%).
- Requires: `linear_metric_best` 174k embeddings (not yet available)
- Factory direction v27: "dense modes attach as legal-distance delivers them year-split"
- Current progress: legal-distance 174k dense embeddings at 36% (years 2000-2010)

### Full 174k Metadata

The local `metadata_174k_full.json` contains only 21,228 decisions. Full 174,113-decision metadata requires downloading the HuggingFace parquet corpus artifacts. The TF-IDF embeddings (175,440 decisions) were computed from the full corpus on remote infrastructure.

---

## Files Modified

### New Build Scripts
- `product/build_174k_tfidf_clustering.py` — Initial build (subset)
- `product/build_174k_tfidf_clustering_full.py` — Full corpus build

### Product Code Fixes
- `product/app/map_loader.py`:
  - Fixed zoom level mapping in `_build_zoom_levels_from_cluster_metadata`
  - Added position building in `_load_fractal_map_clustering_for_representation`
  - Updated `_load_174k_tfidf_representation` to use proper clustering loader
- `product/app/spatial_index.py`:
  - Fixed persistence naming bug (`with_suffix()` issue with dots in filenames)

---

## Evidence References

- Factory direction v27: Product lane RUN, wire production defaults to 174k artifacts
- Legal-distance v9 ACCEPTED: `cited_outcome_hybrid_0.5` (JP=0.799, LangDom=0.491), `cited_outcome_hybrid_0.7` (HierAdv=+0.370)
- Evaluation v15b ACCEPTED: `linear_hybrid05_concat` (JP=0.838, std=0.027, BEST STABLE)
- Fractal-map REPRODUCED: Hierarchical Leiden config coarse_0.5_fine_3.0, nesting=1.0
- 174k simulation tests: All 16 PASS (validates infrastructure at scale)

---

## Next Steps

1. **Await legal-distance 174k dense embeddings** for `linear_hybrid05_concat_174k` activation
2. **Download full 174k metadata** from HuggingFace parquet when available for complete corpus coverage
3. **Run evaluation suite** on 174k TF-IDF representations (citation_heritage, adversarial, multilingual, etc.)
4. **Jurist human study** framework ready — blocked on recruitment (5-10 Swiss jurists)

---

**Report generated:** 2026-09-26T05:35:00Z
**Product state:** 174k TF-IDF production defaults ACTIVE