# Legal-Distance Map Mode: debiased_citation_blended

**Generated:** 2026-08-28T00:28:44.323933+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `debiased_citation_blended`
**Description:** Baseline legal-distance: debiased citation graph blended with center-projected embeddings (n_pca=1, alpha=0.7). 14/14 PASS.

**Legal-Distance Config:** {
  "type": "baseline",
  "config": {}
}

**Benchmarks:** 14/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 5 |
| 0.5 | 8 |
| 0.75 | 9 |
| 1.0 | 9 |
| 1.5 | 12 |
| 2.0 | 13 |
| 3.0 | 19 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/debiased_citation_blended/`:

| Artifact | Path | Purpose |
|----------|------|---------|
| Cluster metadata | `cluster_metadata.json` | Legal context per cluster |
| Zoom mappings | `zoom_mappings.json` | Parent-child navigation |
| Zoom coherence | `zoom_coherence.json` | Validation metrics |
| Decision clusters | `decision_clusters.json` | Fast decision-to-cluster lookup |
| Label arrays | `labels_res_*.npy` | Rendering/visualization |

---

## 4. Product Integration

This mode is compatible with the unified `ProductMapLoader` API:

```python
from product_map_loader import ProductMapLoader

loader = ProductMapLoader()
artifacts = loader.load_mode("debiased_citation_blended")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("debiased_citation_blended", 1.0)
metadata = loader.get_cluster_metadata("debiased_citation_blended", 0.5)
zoom = loader.get_zoom_mapping("debiased_citation_blended", 0.5, 1.0)
```

---

## 5. Benchmark Results

{
  "summary": {
    "total_benchmarks": 14,
    "passed": 14,
    "failed": 0
  }
}

---

## 6. Known Limitations

1. **Embeddings required:** This mode requires legal-distance embeddings to be pre-computed.
2. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full corpus requires scaling.
3. **Language coverage:** Multilingual invariance varies by mode (see benchmark results).
4. **Boilerplate resistance:** Varies by mode (see adversarial_falsification benchmark).

---

*Built from ACCEPTED legal-distance evidence. Integrated into fractal-map product layer.*
