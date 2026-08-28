# Legal-Distance Map Mode: legal_issues_outcomes

**Generated:** 2026-08-28T00:28:48.689380+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `legal_issues_outcomes`
**Description:** TF-IDF on legal_area + outcome + erwaegungen_headings. 10/14 PASS. Doctrinal issue/outcome similarity.

**Legal-Distance Config:** {
  "type": "legal_tfidf",
  "config": {
    "use_legal_area": true,
    "use_outcome": true,
    "use_erwaegungen_headings": true,
    "use_statutes": false,
    "use_erwaegungen": false,
    "use_cited_decisions": false,
    "use_doctrine_refs": false,
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

**Benchmarks:** 10/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 5 |
| 0.5 | 6 |
| 0.75 | 9 |
| 1.0 | 11 |
| 1.5 | 14 |
| 2.0 | 21 |
| 3.0 | 31 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/legal_issues_outcomes/`:

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
artifacts = loader.load_mode("legal_issues_outcomes")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("legal_issues_outcomes", 1.0)
metadata = loader.get_cluster_metadata("legal_issues_outcomes", 0.5)
zoom = loader.get_zoom_mapping("legal_issues_outcomes", 0.5, 1.0)
```

---

## 5. Benchmark Results

{
  "summary": {
    "total_benchmarks": 14,
    "passed": 10,
    "failed": 4
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
