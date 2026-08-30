# Legal-Distance Map Mode: hybrid_stabilized_epoch1

**Generated:** 2026-08-30T01:58:24.701847+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `hybrid_stabilized_epoch1`
**Description:** Metric Learning (Hybrid Stabilized Epoch 1) - HIGH PURITY pattern. Fine=0.9638, NMI=0.5788, ImpRate=73.8%. 128-dim embeddings.

**Legal-Distance Config:** {
  "type": "metric_learning",
  "config": {
    "method": "hybrid_stabilized",
    "base_embedding": "center_projected_64dim",
    "epoch": 1,
    "objective": "jurist_pairwise"
  }
}

**Benchmarks:** 14/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 4 |
| 0.5 | 6 |
| 0.75 | 9 |
| 1.0 | 10 |
| 1.5 | 12 |
| 2.0 | 17 |
| 3.0 | 23 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/hybrid_stabilized_epoch1/`:

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
artifacts = loader.load_mode("hybrid_stabilized_epoch1")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("hybrid_stabilized_epoch1", 1.0)
metadata = loader.get_cluster_metadata("hybrid_stabilized_epoch1", 0.5)
zoom = loader.get_zoom_mapping("hybrid_stabilized_epoch1", 0.5, 1.0)
```

---

## 5. Benchmark Results

{
  "summary": {
    "total_benchmarks": 14,
    "passed": 14,
    "failed": 0
  },
  "adversarial_both_pass": true,
  "jurist_preference": 0.6656,
  "language_dominance": 0.66,
  "hierarchical_purity": 0.9638
}

---

## 6. Known Limitations

1. **Embeddings required:** This mode requires legal-distance embeddings to be pre-computed.
2. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full corpus requires scaling.
3. **Language coverage:** Multilingual invariance varies by mode (see benchmark results).
4. **Boilerplate resistance:** Varies by mode (see adversarial_falsification benchmark).

---

*Built from ACCEPTED legal-distance evidence. Integrated into fractal-map product layer.*
