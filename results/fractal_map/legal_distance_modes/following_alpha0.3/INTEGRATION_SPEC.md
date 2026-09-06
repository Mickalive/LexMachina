# Legal-Distance Map Mode: following_alpha0.3

**Generated:** 2026-08-30T02:21:57.610633+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `following_alpha0.3`
**Description:** Citation Role: Following (α=0.3) - HIGH ADVANTAGE pattern. ImpRate=82.2%, Fine=0.9501. 64-dim embeddings.

**Legal-Distance Config:** {
  "type": "citation_role",
  "config": {
    "role": "following",
    "alpha": 0.3
  }
}

**Benchmarks:** 14/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 1 |
| 0.5 | 1 |
| 0.75 | 1 |
| 1.0 | 3 |
| 1.5 | 656 |
| 2.0 | 985 |
| 3.0 | 986 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/following_alpha0.3/`:

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
artifacts = loader.load_mode("following_alpha0.3")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("following_alpha0.3", 1.0)
metadata = loader.get_cluster_metadata("following_alpha0.3", 0.5)
zoom = loader.get_zoom_mapping("following_alpha0.3", 0.5, 1.0)
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
  "jurist_preference": 0.5188,
  "language_dominance": 0.753,
  "hierarchical_purity": 0.9501
}

---

## 6. Known Limitations

1. **Embeddings required:** This mode requires legal-distance embeddings to be pre-computed.
2. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full corpus requires scaling.
3. **Language coverage:** Multilingual invariance varies by mode (see benchmark results).
4. **Boilerplate resistance:** Varies by mode (see adversarial_falsification benchmark).

---

*Built from ACCEPTED legal-distance evidence. Integrated into fractal-map product layer.*
