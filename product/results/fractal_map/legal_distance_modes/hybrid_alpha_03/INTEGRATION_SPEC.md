# Legal-Distance Map Mode: hybrid_alpha_03

**Generated:** 2026-08-28T00:28:46.597393+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `hybrid_alpha_03`
**Description:** Hybrid: 30% legal_full_signals + 70% baseline. 13/14 PASS. Best branch classification.

**Legal-Distance Config:** {
  "type": "hybrid",
  "alpha": 0.3,
  "legal_config": {
    "use_statutes": true,
    "use_erwaegungen": true,
    "use_cited_decisions": true,
    "use_legal_area": true,
    "use_outcome": true,
    "use_doctrine_refs": true,
    "use_erwaegungen_headings": true,
    "boilerplate_suppression": true,
    "max_features": 5000,
    "min_df": 2,
    "max_df": 0.95,
    "ngram_range": [
      1,
      2
    ]
  },
  "baseline_config": {}
}

**Benchmarks:** 13/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 5 |
| 0.5 | 7 |
| 0.75 | 10 |
| 1.0 | 11 |
| 1.5 | 15 |
| 2.0 | 17 |
| 3.0 | 22 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/hybrid_alpha_03/`:

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
artifacts = loader.load_mode("hybrid_alpha_03")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("hybrid_alpha_03", 1.0)
metadata = loader.get_cluster_metadata("hybrid_alpha_03", 0.5)
zoom = loader.get_zoom_mapping("hybrid_alpha_03", 0.5, 1.0)
```

---

## 5. Benchmark Results

{
  "summary": {
    "total_benchmarks": 14,
    "passed": 13,
    "failed": 1
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
