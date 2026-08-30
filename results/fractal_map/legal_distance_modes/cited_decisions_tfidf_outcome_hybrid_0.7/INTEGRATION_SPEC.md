# Legal-Distance Map Mode: cited_decisions_tfidf_outcome_hybrid_0.7

**Generated:** 2026-08-30T01:58:26.193239+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `cited_decisions_tfidf_outcome_hybrid_0.7`
**Description:** Cited Decisions TF-IDF + Outcome Hybrid α=0.7 - BEST FRACTAL. ImpRate=90.3%, HierAdv=+0.3703. LangDom=0.4907, JP=0.7907. 2-dim embeddings.

**Legal-Distance Config:** {
  "type": "hybrid",
  "config": {
    "alpha": 0.7,
    "cited_decisions_weight": 0.7,
    "outcome_weight": 0.3,
    "boilerplate_suppression": true
  }
}

**Benchmarks:** 14/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 10 |
| 0.5 | 15 |
| 0.75 | 16 |
| 1.0 | 19 |
| 1.5 | 22 |
| 2.0 | 25 |
| 3.0 | 29 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/`:

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
artifacts = loader.load_mode("cited_decisions_tfidf_outcome_hybrid_0.7")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("cited_decisions_tfidf_outcome_hybrid_0.7", 1.0)
metadata = loader.get_cluster_metadata("cited_decisions_tfidf_outcome_hybrid_0.7", 0.5)
zoom = loader.get_zoom_mapping("cited_decisions_tfidf_outcome_hybrid_0.7", 0.5, 1.0)
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
  "jurist_preference": 0.7907,
  "language_dominance": 0.4907,
  "hierarchical_purity": 0.903
}

---

## 6. Known Limitations

1. **Embeddings required:** This mode requires legal-distance embeddings to be pre-computed.
2. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full corpus requires scaling.
3. **Language coverage:** Multilingual invariance varies by mode (see benchmark results).
4. **Boilerplate resistance:** Varies by mode (see adversarial_falsification benchmark).

---

*Built from ACCEPTED legal-distance evidence. Integrated into fractal-map product layer.*
