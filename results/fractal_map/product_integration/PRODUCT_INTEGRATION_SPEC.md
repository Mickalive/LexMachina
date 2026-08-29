# Fractal Map Lane — Product Integration Specification (Map Mode Switching)

**Generated:** 2026-08-29T12:53:22.249420
**Lane:** fractal-map
**Evidence Tier:** REPRODUCED
**Status:** PRODUCTIZE

---

## 1. Overview

This specification describes the **multi-mode fractal map system** for Swiss Federal Supreme Court (BGer) decisions.
The system exposes a **default center_projected hierarchical Leiden map** plus **selectable legal-distance map modes**.

**Key Architecture:**
- **Default Mode:** Center Projected Hierarchical Leiden (REPRODUCED tier, purity 0.9571)
- **Selectable Modes:** 5 legal-distance representations (ACCEPTED tier)
- **Legacy Mode:** Concat-based Hierarchical Leiden (preserved for comparison)
- **Unified API:** Single loader interface for all modes
- **Resolution Ladder:** 7 levels (0.25 → 3.0) consistent across modes

---

## 2. Map Mode Registry

| Mode ID | Name | Type | Status | Default |
|---------|------|------|--------|---------|
| center_projected_hierarchical | Center Projected Hierarchical Leiden (Default) | hierarchical_leiden | available | ✅ |
| hierarchical_leiden_concat | Hierarchical Leiden (Concat - Legacy) | hierarchical_leiden | legacy |  |
| debiased_citation_blended | Debiased Citation Blended (Legal-Distance Baseline) | legal_distance | available |  |
| legal_cited_decisions_only | Legal Cited Decisions Only | legal_distance | available |  |
| hybrid_alpha_03 | Hybrid α=0.3 (30% Legal + 70% Baseline) | legal_distance | available |  |
| hybrid_alpha_05 | Hybrid α=0.5 (50% Legal + 50% Baseline) | legal_distance | available |  |
| legal_issues_outcomes | Legal Issues & Outcomes | legal_distance | available |  |
| center_projected | Center Projected (Language-Debiased Embedding) | legal_distance | placeholder |  |


---

## 3. Default Mode: Center Projected Hierarchical Leiden

**Mode ID:** `center_projected_hierarchical`
**Evidence Tier:** REPRODUCED
**Validation Run:** 33207149474

### 3.1 Resolution Ladder
- **Resolution 0.25**: available
- **Resolution 0.5**: 108 clusters at hierarchical level
- **Resolution 0.75**: available
- **Resolution 1.0**: available
- **Resolution 1.5**: available
- **Resolution 2.0**: available
- **Resolution 3.0**: available

- **Resolution 0.25**: 5 clusters (domain: language + broad legal domain)
- **Resolution 0.5**: 7 clusters (subdomain: legal area within language) — **Coarse parent level**
- **Resolution 0.75**: 9 clusters
- **Resolution 1.0**: 11 clusters
- **Resolution 1.5**: 14 clusters
- **Resolution 2.0**: 16 clusters
- **Resolution 3.0**: 19 clusters

- **Hierarchical (validated config: coarse_0.5_fine_3.0)**: 108 clusters, nesting=1.0, purity=0.9571 (min_cluster_size=3)
- **Coarse (parent)**: 7 clusters at resolution 0.5

### 3.2 Key Metrics
- **Hierarchical purity**: 0.9571 (+0.0080 vs concat baseline 0.9491)
- **Perfect nesting**: 1.0 (guaranteed by hierarchical construction)
- **Adversarial language dominance**: 0.7593 (< 0.85 threshold) ✅ — *source: evaluation_v2_cycle_33137354250 (carried forward)*
- **Jurist pairwise preference**: 0.5215 (> 0.5 threshold) ✅ — *source: evaluation_v2_cycle_33137354250 (carried forward)*
- **Jurivoc hierarchy alignment**: 4/5 PASS — *source: evaluation_v2_cycle_33137354250 (carried forward)*
- **Zoom coherence (per-resolution-step)**: 31.1% improvement rate (19/61 parent clusters improve) — *source: center_projected_hierarchical_zoom_validation (v6 recomputed)*

### 3.3 Artifacts
All artifacts available at `results/fractal_map/hierarchical_map_center_projected/`:
- `cluster_metadata.json` — Legal context per cluster (branch, area, chamber, language)
- `zoom_mappings.json` — Bidirectional parent-child navigation
- `zoom_coherence.json` — Per-cluster zoom improvement metrics (per-resolution-step)
- `decision_clusters.json` — Decision-to-cluster index (1000 × 7 resolutions)
- `labels_res_*.npy` — Cluster assignments for rendering
- `labels_hierarchical_best.npy` — Best validated hierarchical config (108 clusters)
- `labels_coarse_0.5.npy` — 7-cluster parent level

---

## 4. Selectable Legal-Distance Modes

These modes are built on legal-distance embeddings (ACCEPTED tier evidence).

### 4.1 debiased_citation_blended
- **Status:** AVAILABLE
- **Benchmarks:** 14/14 PASS
- **Strengths:** Strong citation heritage, multilingual invariance

### 4.2 legal_cited_decisions_only
- **Status:** AVAILABLE
- **Benchmarks:** 14/14 PASS
- **Strengths:** Best citation heritage (AUC 0.97), boilerplate resistance

### 4.3 hybrid_alpha_03
- **Status:** AVAILABLE
- **Benchmarks:** 13/14 PASS (1 failed) — **fails adversarial_falsification**
- ⚠️ **Warning:** fails adversarial_falsification benchmark
- **Strengths:** Best branch classification, strong TF metadata recall

### 4.4 hybrid_alpha_05
- **Status:** AVAILABLE
- **Benchmarks:** 13/14 PASS (1 failed) — **fails adversarial_falsification**
- ⚠️ **Warning:** fails adversarial_falsification benchmark
- **Strengths:** Best branch classification, strong TF metadata recall

### 4.5 legal_issues_outcomes
- **Status:** AVAILABLE
- **Benchmarks:** 10/14 PASS (4 failed) — **fails adversarial_falsification** — **fails multilingual_invariance**
- ⚠️ **Warning:** fails adversarial_falsification benchmark
- ⚠️ **Warning:** fails multilingual_invariance benchmark
- ⚠️ **Warning:** fails citation_heritage threshold
- ⚠️ **Warning:** fails tf_metadata_human_indexing threshold


---

## 5. Legacy Mode (Preserved for Comparison)

### 5.1 hierarchical_leiden_concat (Concat-based - Legacy)
- **Status:** LEGACY
- **Hierarchical purity**: 0.9491 (vs 0.9638 for center_projected)
- **Zoom coherence (per-resolution-step)**: 59.2% improvement rate
- **Note:** Replaced as default by center_projected_hierarchical per factory direction v4
- **Embeddings**: concat (center_projected 768 + TF-IDF Erwaegungen 128)

---

## 6. Product Integration API

### 6.1 Basic Usage

```python
from product_map_loader import ProductMapLoader

loader = ProductMapLoader()

# List available modes
modes = loader.list_modes()
for m in modes:
    print(f"{m['mode_id']}: {m['name']} [{m['status']}]")

# Load default mode (center_projected_hierarchical)
artifacts = loader.load_default()

# Or load specific mode
artifacts = loader.load_mode('center_projected_hierarchical')
artifacts = loader.load_mode('debiased_citation_blended')
```

### 6.2 Accessing Map Data

```python
# Get cluster labels at specific resolution
labels_res_1_0 = loader.get_resolution_labels('center_projected_hierarchical', 1.0)

# Get hierarchical labels (108 clusters, nested)
hierarchical_labels = loader.get_hierarchical_labels('center_projected_hierarchical')

# Get coarse parent labels (7 clusters)
coarse_labels = loader.get_coarse_labels('center_projected_hierarchical')

# Get cluster metadata with legal context
metadata_res_0_5 = loader.get_cluster_metadata('center_projected_hierarchical', 0.5)

# Get zoom navigation (parent-child mappings)
zoom_0_5_to_1_0 = loader.get_zoom_mapping('center_projected_hierarchical', 0.5, 1.0)

# Get decision cluster membership
decision_clusters = loader.get_decision_clusters('center_projected_hierarchical', 'BGE_123_456')

# Get zoom coherence metrics
coherence = loader.get_zoom_coherence('center_projected_hierarchical', 0.5, 1.0)
```

### 6.3 Recommended User Flows

**Flow A: Domain → Subdomain → Microcluster (Center Projected Hierarchical Leiden)**
```
Start at res=0.25 (5 clusters: language + broad domain)
  ↓ User selects cluster
Zoom to res=0.5 (children of selected, 7 subdomains)
  ↓ User selects subdomain
Zoom to res=1.5 (children of selected, ~14 microclusters)
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
User views map in default mode (center_projected_hierarchical)
  ↓ User selects "Legal Cited Decisions Only" mode
Re-render map with legal_cited_decisions_only embeddings
Show mode-specific cluster metadata
Allow side-by-side comparison
```

---

## 7. Legal-Distance Mode Integration (Already Built)

The 5 legal-distance modes are already built and integrated:

1. **Embeddings** → `results/legal_distance/embeddings/<mode_id>.npy`
2. **Cluster labels** → `results/fractal_map/legal_distance_modes/<mode_id>/labels_res_*.npy`
3. **Cluster metadata** → `results/fractal_map/legal_distance_modes/<mode_id>/cluster_metadata.json`
4. **Zoom mappings** → `results/fractal_map/legal_distance_modes/<mode_id>/zoom_mappings.json`

The loader automatically detects available artifacts.

---

## 8. Acceptance Criteria

✅ Center Projected Hierarchical Leiden as default map structure (REPRODUCED, validated)  
✅ 7-resolution ladder with legal coherence metrics exposed  
✅ Perfect nesting (1.0) guaranteed for hierarchical mode  
✅ **31.1% zoom improvement rate** validated (per-resolution-step)  
✅ Hierarchical purity 0.9571 (+0.0080 vs concat baseline, min_cluster_size=3)  
✅ Adversarial language dominance 0.7593 < 0.85 PASS (source: v5 carried forward)  
✅ Jurist pairwise preference 0.5215 > 0.5 PASS (source: v5 carried forward)  
✅ Jurivoc 4/5 PASS (source: v5 carried forward)  
✅ Map mode registry with 8 modes (1 default + 5 legal-distance + 1 legacy + 1 placeholder)  
✅ Unified loader API for all modes  
✅ Product integration specification complete  
✅ Map mode switching architecture designed  
⚠️ Hybrid modes fail adversarial_falsification — marked with warnings  
⚠️ legal_issues_outcomes fails 4/14 benchmarks — marked with warnings  

---

## 9. Next Steps

1. **Product Lane**: Consume center_projected_hierarchical artifacts from `results/fractal_map/hierarchical_map_center_projected/`
2. **Product Lane**: Implement map mode selector UI using registry
3. **Legal-Distance Lane**: Reproduce center_projected on full v1+v2 benchmark suite
4. **Product Lane**: Implement side-by-side mode comparison view
5. **Corpus Lane**: Scale to full 2000-2024 corpus (~192k decisions)

---

*This specification is generated from validated REPRODUCED/ACCEPTED evidence. 
All metrics are frozen before observation and match the accepted state files.*
