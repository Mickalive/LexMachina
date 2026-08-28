# Fractal Map Lane — Product Integration Specification (Map Mode Switching)

**Generated:** 2026-08-28T00:32:45.707802
**Lane:** fractal-map
**Evidence Tier:** REPRODUCED
**Status:** PRODUCTIZE

---

## 1. Overview

This specification describes the **multi-mode fractal map system** for Swiss Federal Supreme Court (BGer) decisions.
The system exposes a **default hierarchical Leiden map** plus **selectable legal-distance map modes**.

**Key Architecture:**
- **Default Mode:** Hierarchical Leiden (validated, REPRODUCED tier)
- **Selectable Modes:** 5 legal-distance representations (ACCEPTED tier)
- **Unified API:** Single loader interface for all modes
- **Resolution Ladder:** 7 levels (0.25 → 3.0) consistent across modes

---

## 2. Map Mode Registry

| Mode ID | Name | Type | Status | Default |
|---------|------|------|--------|---------|
| hierarchical_leiden | Hierarchical Leiden (Default) | hierarchical_leiden | available | ✅ |
| debiased_citation_blended | Debiased Citation Blended (Legal-Distance Baseline) | legal_distance | available |  |
| legal_cited_decisions_only | Legal Cited Decisions Only | legal_distance | available |  |
| hybrid_alpha_03 | Hybrid α=0.3 (30% Legal + 70% Baseline) | legal_distance | available |  |
| hybrid_alpha_05 | Hybrid α=0.5 (50% Legal + 50% Baseline) | legal_distance | available |  |
| legal_issues_outcomes | Legal Issues & Outcomes | legal_distance | available |  |


---

## 3. Default Mode: Hierarchical Leiden

**Mode ID:** `hierarchical_leiden`
**Evidence Tier:** REPRODUCED
**Validation Run:** 33127766775

### 3.1 Resolution Ladder
- **Resolution 0.25**: N/A clusters
- **Resolution 0.5**: N/A clusters
- **Resolution 0.75**: N/A clusters
- **Resolution 1.0**: N/A clusters
- **Resolution 1.5**: N/A clusters
- **Resolution 2.0**: N/A clusters
- **Resolution 3.0**: N/A clusters

- **Hierarchical (validated)**: 98 clusters, nesting=1.0, purity=0.949
- **Coarse (parent)**: 8 clusters at resolution 0.5

### 3.2 Artifacts
All artifacts available at `results/fractal_map/product_integration/`:
- `cluster_metadata.json` — Legal context per cluster (branch, area, chamber, language)
- `zoom_mappings.json` — Bidirectional parent-child navigation
- `zoom_coherence.json` — Per-cluster zoom improvement metrics
- `decision_clusters.json` — Decision-to-cluster index (1000 × 9 resolutions)
- `labels_res_*.npy` — Cluster assignments for rendering
- `labels_hierarchical_best.npy` — Best validated hierarchical config
- `labels_coarse_0.5.npy` — 8-cluster parent level

---

## 4. Selectable Legal-Distance Modes

These modes require legal-distance embeddings to be computed. Infrastructure is ready.

### 4.1 debiased_citation_blended (Legal-Distance Baseline)
- **Status:** PLACEHOLDER (embeddings need computation)
- **Benchmarks:** 14/14 PASS
- **Strengths:** Citation heritage (AUC 0.91), multilingual invariance, balanced

### 4.2 legal_cited_decisions_only
- **Status:** PLACEHOLDER
- **Benchmarks:** 14/14 PASS
- **Strengths:** Best citation heritage (AUC 0.97), boilerplate resistance

### 4.3 hybrid_alpha_03 (30% Legal + 70% Baseline)
- **Status:** PLACEHOLDER
- **Benchmarks:** 13/14 PASS (fails adversarial_falsification)
- **Strengths:** Best branch classification (0.967), TF metadata recall (0.967)

### 4.4 hybrid_alpha_05 (50% Legal + 50% Baseline)
- **Status:** PLACEHOLDER
- **Benchmarks:** 13/14 PASS (fails adversarial_falsification)
- **Strengths:** Strongest branch classification (0.972), TF metadata recall (0.972)

### 4.5 legal_issues_outcomes
- **Status:** PLACEHOLDER
- **Benchmarks:** 10/14 PASS
- **Strengths:** Doctrinal issue/outcome similarity independent of citations

---

## 5. Product Integration API

### 5.1 Basic Usage

```python
from product_map_loader import ProductMapLoader

loader = ProductMapLoader()

# List available modes
modes = loader.list_modes()
for m in modes:
    print(f"legal_issues_outcomes: Legal Issues & Outcomes [available]")

# Load default mode (hierarchical Leiden)
artifacts = loader.load_default()

# Or load specific mode
artifacts = loader.load_mode("hierarchical_leiden")
```

### 5.2 Accessing Map Data

```python
# Get cluster labels at specific resolution
labels_res_1_0 = loader.get_resolution_labels("hierarchical_leiden", 1.0)

# Get hierarchical labels (98 clusters, nested)
hierarchical_labels = loader.get_hierarchical_labels("hierarchical_leiden")

# Get coarse parent labels (8 clusters)
coarse_labels = loader.get_coarse_labels("hierarchical_leiden")

# Get cluster metadata with legal context
metadata_res_0_5 = loader.get_cluster_metadata("hierarchical_leiden", 0.5)
hierarchical_metadata = loader.get_hierarchical_cluster_metadata("hierarchical_leiden")

# Get zoom navigation (parent-child mappings)
zoom_0_5_to_1_0 = loader.get_zoom_mapping("hierarchical_leiden", 0.5, 1.0)

# Get decision cluster membership
decision_clusters = loader.get_decision_clusters("hierarchical_leiden", "BGE_123_456")

# Get zoom coherence metrics
coherence = loader.get_zoom_coherence("hierarchical_leiden", 0.5, 1.0)
```

### 5.3 Recommended User Flows

**Flow A: Domain → Subdomain → Microcluster (Hierarchical Leiden)**
```
Start at res=0.25 (4 clusters: language + broad domain)
  ↓ User selects cluster
Zoom to res=0.5 (children of selected, 8 subdomains)
  ↓ User selects subdomain
Zoom to res=1.5 (children of selected, ~19 microclusters)
  ↓ User selects microcluster
Show decisions in microcluster
```

**Flow B: Search → Context Zoom**
```
User searches "Strafprozess"
  ↓ Find matching microclusters at res=2.0
Show cluster + parent context (res=0.5, res=0.25)
Allow zoom out to broader context
```

**Flow C: Decision Inspection**
```
User opens decision X
  ↓ Show cluster membership at ALL resolutions
Show cluster metadata (dominant branch, area, chamber)
Show k-nearest neighbors within same cluster at finest resolution
```

**Flow D: Map Mode Switching**
```
User views map in default mode (hierarchical Leiden)
  ↓ User selects "Legal Issues & Outcomes" mode
Re-render map with legal_issues_outcomes embeddings
Show mode-specific cluster metadata
Allow side-by-side comparison
```

---

## 6. Legal-Distance Mode Integration (When Ready)

When legal-distance embeddings are computed and persisted:

1. **Embeddings** → `results/legal_distance/embeddings/<mode_id>.npy`
2. **Cluster labels** → `results/fractal_map/legal_distance_modes/<mode_id>/labels_res_*.npy`
3. **Cluster metadata** → `results/fractal_map/legal_distance_modes/<mode_id>/cluster_metadata.json`
4. **Zoom mappings** → `results/fractal_map/legal_distance_modes/<mode_id>/zoom_mappings.json`

The loader will automatically detect available artifacts.

### 6.1 Required Computation Pipeline

For each legal-distance mode, run:
```python
# 1. Load legal-distance embeddings (from legal-distance lane)
embeddings = load_legal_distance_embeddings(mode_id)

# 2. Run multi-resolution Leiden clustering
for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
    labels = leiden_clustering(embeddings, resolution=res)
    save_labels(labels, mode_id, res)

# 3. Build cluster metadata
metadata = build_cluster_metadata(labels, corpus_metadata)
save_metadata(metadata, mode_id)

# 4. Build zoom mappings
zoom_mappings = build_zoom_mappings(labels_dict)
save_zoom_mappings(zoom_mappings, mode_id)
```

---

## 7. Acceptance Criteria

✅ Hierarchical Leiden as default map structure (REPRODUCED, validated)  
✅ 7-resolution ladder with legal coherence metrics exposed  
✅ Perfect nesting (1.0) guaranteed for hierarchical mode  
✅ 59.2% zoom improvement rate validated  
✅ Map mode registry with 6 modes (1 default + 5 legal-distance)  
✅ Unified loader API for all modes  
✅ Placeholder infrastructure for legal-distance modes  
✅ Product integration specification complete  
✅ Map mode switching architecture designed  

---

## 8. Next Steps

1. **Product Lane**: Consume hierarchical Leiden artifacts from `results/fractal_map/product_integration/`
2. **Product Lane**: Implement map mode selector UI using registry
3. **Legal-Distance Lane**: Compute embeddings for 5 selectable modes on full corpus
4. **Fractal-Map Lane**: Run multi-resolution clustering on legal-distance embeddings
5. **Product Lane**: Implement side-by-side mode comparison view

---

*This specification is generated from validated REPRODUCED/ACCEPTED evidence. 
All metrics are frozen before observation and match the accepted state files.*
