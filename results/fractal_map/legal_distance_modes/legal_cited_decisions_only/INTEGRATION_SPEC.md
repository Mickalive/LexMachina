# Legal-Distance Map Mode: legal_cited_decisions_only

**Generated:** 2026-08-28T00:28:45.491331+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `legal_cited_decisions_only`
**Description:** TF-IDF on cited decisions only. 14/14 PASS. Best citation heritage (AUC 0.97).

**Legal-Distance Config:** {
  "type": "legal_tfidf",
  "config": {
    "use_cited_decisions": true,
    "use_statutes": false,
    "use_erwaegungen": false,
    "use_legal_area": false,
    "use_outcome": false,
    "use_doctrine_refs": false,
    "use_erwaegungen_headings": false,
    "boilerplate_suppression": true,
    "max_features": 5000,
    "min_df": 2,
    "max_df": 0.95,
    "ngram_range": [
      1,
      2
    ]
  }
}

**Benchmarks:** 14/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 5 |
| 0.5 | 9 |
| 0.75 | 11 |
| 1.0 | 13 |
| 1.5 | 22 |
| 2.0 | 42 |
| 3.0 | 195 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/legal_cited_decisions_only/`:

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
artifacts = loader.load_mode("legal_cited_decisions_only")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("legal_cited_decisions_only", 1.0)
metadata = loader.get_cluster_metadata("legal_cited_decisions_only", 0.5)
zoom = loader.get_zoom_mapping("legal_cited_decisions_only", 0.5, 1.0)
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
