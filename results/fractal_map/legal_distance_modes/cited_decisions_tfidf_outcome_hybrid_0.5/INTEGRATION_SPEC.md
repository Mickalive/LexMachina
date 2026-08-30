# Legal-Distance Map Mode: cited_decisions_tfidf_outcome_hybrid_0.5

**Generated:** 2026-08-30T01:58:25.474700+00:00
**Lane:** fractal-map (legal-distance integration)
**Evidence Tier:** ACCEPTED (legal-distance) / PRODUCTIZE (fractal-map integration)
**Status:** BUILT

---

## 1. Overview

**Mode ID:** `cited_decisions_tfidf_outcome_hybrid_0.5`
**Description:** Cited Decisions TF-IDF + Outcome Hybrid α=0.5 - BEST PRODUCTION. ImpRate=86.8%, HierAdv=+0.2918. LangDom=0.4911, JP=0.7990. 2-dim embeddings.

**Legal-Distance Config:** {
  "type": "hybrid",
  "config": {
    "alpha": 0.5,
    "cited_decisions_weight": 0.5,
    "outcome_weight": 0.5,
    "boilerplate_suppression": true
  }
}

**Benchmarks:** 14/14 PASS

---

## 2. Resolution Ladder

| Resolution | Clusters |
|------------|----------|
| 0.25 | 11 |
| 0.5 | 14 |
| 0.75 | 18 |
| 1.0 | 22 |
| 1.5 | 22 |
| 2.0 | 24 |
| 3.0 | 29 |


---

## 3. Artifacts

All artifacts available at `results/fractal_map/legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/`:

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
artifacts = loader.load_mode("cited_decisions_tfidf_outcome_hybrid_0.5")

# Access same API as hierarchical_leiden
labels = loader.get_resolution_labels("cited_decisions_tfidf_outcome_hybrid_0.5", 1.0)
metadata = loader.get_cluster_metadata("cited_decisions_tfidf_outcome_hybrid_0.5", 0.5)
zoom = loader.get_zoom_mapping("cited_decisions_tfidf_outcome_hybrid_0.5", 0.5, 1.0)
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
  "jurist_preference": 0.799,
  "language_dominance": 0.4911,
  "hierarchical_purity": 0.868
}

---

## 6. Known Limitations

1. **Embeddings required:** This mode requires legal-distance embeddings to be pre-computed.
2. **Corpus scope:** Validated on 1000 decisions (2020-2024). Full corpus requires scaling.
3. **Language coverage:** Multilingual invariance varies by mode (see benchmark results).
4. **Boilerplate resistance:** Varies by mode (see adversarial_falsification benchmark).

---

*Built from ACCEPTED legal-distance evidence. Integrated into fractal-map product layer.*
