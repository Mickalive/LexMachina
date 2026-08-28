# Fractal Map Lane — Map Mode Productization Report

**Run ID:** map_mode_productization_20260828
**Date:** 2026-08-28
**Direction Version:** 5
**Lane:** fractal-map
**Evidence Tier:** REPRODUCED (hierarchical Leiden) / ACCEPTED (legal-distance)
**Status:** PRODUCTIZE

---

## 1. Executive Summary

The fractal-map lane has completed the **productization of the validated multi-resolution hierarchical Leiden map** and **integrated 5 legal-distance selectable map modes** as required by factory direction v5.

**Key Deliverables:**
1. ✅ **Hierarchical Leiden as default map structure** (REPRODUCED tier, validated)
2. ✅ **5 legal-distance map modes** built and integrated (ACCEPTED tier evidence)
3. ✅ **Unified map mode registry** with 6 selectable modes
4. ✅ **Product map loader API** for seamless mode switching
5. ✅ **Complete product integration package** at `results/fractal_map/product_integration/`

---

## 2. Validated Default Mode: Hierarchical Leiden

### 2.1 Metrics (Frozen Before Observation)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Hierarchical purity (98 clusters) | 0.949 | > 0.90 | ✅ PASS |
| Nesting consistency | 1.0 | == 1.0 | ✅ PASS |
| Flat Leiden mean purity (7 resolutions) | 0.845 | baseline | ✅ |
| Purity improvement (hierarchical vs flat) | +12.3% | > 0% | ✅ PASS |
| Zoom coherence improvement rate | 59.2% | > 50% | ✅ PASS |
| Resolution ladder | 7 levels (0.25→3.0) | 7 levels | ✅ PASS |

### 2.2 Architecture
- **Coarse resolution:** 0.5 (8 clusters)
- **Fine resolution:** 3.0 (98 sub-clusters, nested by construction)
- **Perfect nesting guaranteed:** 98/98 = 1.0
- **Legal coherence:** Branch purity ladder from 0.635 (domain) to 0.912 (microcluster)

### 2.3 Artifacts (at `results/fractal_map/product_integration/`)
- `cluster_metadata.json` — Legal context per cluster (branch, area, chamber, language)
- `zoom_mappings.json` — Bidirectional parent-child navigation (6 resolution pairs)
- `zoom_coherence.json` — Per-cluster zoom improvement metrics
- `decision_clusters.json` — Decision-to-cluster index (1000 × 9 resolutions)
- `labels_res_*.npy` — Cluster assignments for 7 resolutions
- `labels_hierarchical_best.npy` — 98-cluster hierarchical view
- `labels_coarse_0.5.npy` — 8-cluster parent level

---

## 3. Legal-Distance Selectable Map Modes

All 5 modes built from ACCEPTED legal-distance evidence (v3, 14/14 PASS for baseline modes):

| Mode ID | Name | Benchmarks | Key Strength |
|---------|------|------------|--------------|
| `debiased_citation_blended` | Legal-Distance Baseline | 14/14 PASS | Balanced, multilingual invariance |
| `legal_cited_decisions_only` | Citation-Only | 14/14 PASS | Best citation heritage (AUC 0.97) |
| `hybrid_alpha_03` | Hybrid 30/70 | 13/14 PASS | Best branch classification (0.967) |
| `hybrid_alpha_05` | Hybrid 50/50 | 13/14 PASS | Strongest branch classification (0.972) |
| `legal_issues_outcomes` | Issues & Outcomes | 10/14 PASS | Doctrinal similarity independent of citations |

### 3.1 Artifacts (at `results/fractal_map/legal_distance_modes/<mode_id>/`)
Each mode has identical artifact structure:
- `cluster_metadata.json` — 7 resolution levels
- `zoom_mappings.json` — 6 resolution pairs
- `zoom_coherence.json` — Zoom validation
- `decision_clusters.json` — Decision index
- `labels_res_*.npy` — 7 resolution label arrays
- `integration_summary.json` — Mode metadata
- `INTEGRATION_SPEC.md` — Mode-specific spec

### 3.2 Cluster Counts at Resolution 1.0

| Mode | Clusters | Modularity |
|------|----------|------------|
| hierarchical_leiden | 14 | 0.757 |
| debiased_citation_blended | 9 | 0.722 |
| legal_cited_decisions_only | 13 | 0.375 |
| hybrid_alpha_03 | 11 | 0.747 |
| hybrid_alpha_05 | 14 | 0.785 |
| legal_issues_outcomes | 11 | 0.665 |

---

## 4. Map Mode Registry & Loader API

### 4.1 Registry
**Location:** `results/fractal_map/product_integration/map_mode_registry.json`

```json
{
  "default_mode": "hierarchical_leiden",
  "modes": {
    "hierarchical_leiden": {"status": "available", "is_default": true, ...},
    "debiased_citation_blended": {"status": "available", ...},
    "legal_cited_decisions_only": {"status": "available", ...},
    "hybrid_alpha_03": {"status": "available", ...},
    "hybrid_alpha_05": {"status": "available", ...},
    "legal_issues_outcomes": {"status": "available", ...}
  }
}
```

### 4.2 Product Loader API
**Location:** `fractal_map/hierarchical/map_mode_loader.py`

```python
from fractal_map.hierarchical.map_mode_loader import ProductMapLoader

loader = ProductMapLoader()

# List modes
modes = loader.list_modes()

# Load default (hierarchical Leiden)
artifacts = loader.load_default()

# Load specific legal-distance mode
artifacts = loader.load_mode("hybrid_alpha_03")

# Access map data
labels = loader.get_resolution_labels("hierarchical_leiden", 1.0)
metadata = loader.get_cluster_metadata("hybrid_alpha_03", 0.5)
zoom = loader.get_zoom_mapping("legal_cited_decisions_only", 0.5, 1.0)
decision_info = loader.get_decision_clusters("hierarchical_leiden", "BGE_123_456")
```

---

## 5. Product Integration Specification

**Location:** `results/fractal_map/product_integration/PRODUCT_INTEGRATION_SPEC.md`

### 5.1 User Flows Enabled

**Flow A: Domain → Subdomain → Microcluster** (Hierarchical Leiden)
```
res=0.25 (4) → res=0.5 (8) → res=1.5 (19) → decisions
```

**Flow B: Search → Context Zoom**
```
Search "Strafprozess" → res=2.0 matches → show parents (res=0.5, 0.25)
```

**Flow C: Decision Inspection**
```
Decision X → all resolutions → cluster metadata → k-NN in finest cluster
```

**Flow D: Map Mode Switching**
```
Default (hierarchical Leiden) ↔ Legal-Distance modes
Side-by-side comparison view
```

---

## 6. Evidence Traceability

### 6.1 Hierarchical Leiden (Fractal-Map Lane)
- **State:** `state/fractal-map.json` (v5, REPRODUCED, COMPLETED)
- **Results:** `results/fractal_map/hierarchical_map/hierarchical_leiden_results.json`
- **Product Artifacts:** `results/fractal_map/product_integration/`
- **Validation:** 30/30 tests PASS (run 33127766775)

### 6.2 Legal-Distance Modes (Legal-Distance Lane)
- **State:** `/tmp/lex_accepted/legal-distance/state/legal-distance.json` (v3, ACCEPTED)
- **Benchmarks:** `/tmp/lex_accepted/legal-distance/legal_distance/results/all_experiments_results.json`
- **Embeddings:** `results/legal_distance/embeddings/*.npy` (generated)
- **Map Artifacts:** `results/fractal_map/legal_distance_modes/<mode_id>/`

---

## 7. Acceptance Criteria (Factory Direction v5)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Expose resolution ladder | ✅ | 7 resolutions in registry & loader |
| Cluster metadata with legal coherence | ✅ | branch/area/chamber/language per cluster |
| Legal coherence at each zoom level | ✅ | zoom_coherence.json per mode |
| Hierarchical Leiden as default map structure | ✅ | is_default=true, REPRODUCED tier |
| Integrate legal-distance selectable modes | ✅ | 5 modes built, loader API ready |
| Map mode switching architecture | ✅ | Unified registry + loader |

---

## 8. Known Limitations

1. **Corpus scope:** Validated on 1,000 decisions (2020-2024). Full 2000+ corpus requires corpus lane completion.
2. **igraph version sensitivity:** Cluster counts may vary; key invariants preserved (nesting=1.0, purity>0.94).
3. **Legal-distance embeddings:** Generated from TF-IDF on extracted sections; legal embeddings (Isaacus/Legal-BERT) not yet tested.
4. **Multilingual invariance:** Varies by mode (debiased_citation_blended best, legal_issues_outcomes weakest).
5. **Adversarial falsification:** Hybrid modes and legal_issues_outcomes fail this benchmark.

---

## 9. Next Steps (Product Lane)

1. **Consume hierarchical Leiden artifacts** from `results/fractal_map/product_integration/`
2. **Implement map mode selector UI** using registry at `map_mode_registry.json`
3. **Build zoom/navigation UI** using `zoom_mappings.json` and `cluster_metadata.json`
4. **Add side-by-side mode comparison** for legal-distance modes
5. **Integrate with corpus import** for user-provided corpora
6. **Scale to full TF 2000+ corpus** when corpus lane delivers

---

## 10. State File Update

The lane state should be updated to reflect completion of the v5 question:

```json
{
  "lane": "fractal-map",
  "direction_version": 5,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "map_mode_productization_20260828",
  "evidence_refs": [
    "results/fractal_map/product_integration/integration_summary.json",
    "results/fractal_map/product_integration/map_mode_registry.json",
    "results/fractal_map/legal_distance_modes/debiased_citation_blended/integration_summary.json",
    "results/fractal_map/legal_distance_modes/legal_cited_decisions_only/integration_summary.json",
    "results/fractal_map/legal_distance_modes/hybrid_alpha_03/integration_summary.json",
    "results/fractal_map/legal_distance_modes/hybrid_alpha_05/integration_summary.json",
    "results/fractal_map/legal_distance_modes/legal_issues_outcomes/integration_summary.json",
    "fractal_map/hierarchical/map_mode_registry.py",
    "fractal_map/hierarchical/map_mode_loader.py",
    "fractal_map/hierarchical/build_legal_distance_modes.py",
    "fractal_map/hierarchical/generate_legal_distance_embeddings.py"
  ],
  "next_recommendation": "PRODUCTIZE",
  "metrics_summary": {
    "hierarchical_leiden": {
      "hierarchical_purity": 0.949,
      "nesting_score": 1.0,
      "n_hierarchical_clusters": 98,
      "zoom_coherence_improvement_rate": 0.592
    },
    "legal_distance_modes_built": 5,
    "total_selectable_modes": 6,
    "all_modes_status": "available"
  }
}
```

---

*This report is generated from validated REPRODUCED/ACCEPTED evidence. All metrics frozen before observation.*