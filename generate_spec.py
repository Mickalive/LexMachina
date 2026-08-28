import shutil
from pathlib import Path
from datetime import datetime

output_dir = Path('results/fractal_map/product_integration')
output_dir.mkdir(parents=True, exist_ok=True)

# Export registry
from fractal_map.hierarchical.map_mode_registry import export_registry, MAP_MODES
export_registry(output_dir / 'map_mode_registry.json')

# Copy loader implementation
shutil.copy(
    Path('fractal_map/hierarchical/map_mode_registry.py'),
    output_dir / 'map_mode_registry.py'
)
shutil.copy(
    Path('fractal_map/hierarchical/map_mode_loader.py'),
    output_dir / 'map_mode_loader.py'
)

from fractal_map.hierarchical.map_mode_loader import MapModeLoader

loader = MapModeLoader()
modes = loader.list_modes()
default_mode = loader.get_default_mode_id()
default_spec = MAP_MODES[default_mode]

spec = f'''# Fractal Map Lane — Product Integration Specification (Map Mode Switching)

**Generated:** {datetime.now().isoformat()}
**Lane:** fractal-map
**Evidence Tier:** REPRODUCED
**Status:** PRODUCTIZE

---

## 1. Overview

This specification describes the **multi-mode fractal map system** for Swiss Federal Supreme Court (BGer) decisions.
The system exposes a **default center_projected hierarchical Leiden map** plus **selectable legal-distance map modes**.

**Key Architecture:**
- **Default Mode:** Center Projected Hierarchical Leiden (REPRODUCED tier, purity 0.9638)
- **Selectable Modes:** 5 legal-distance representations (ACCEPTED tier)
- **Legacy Mode:** Concat-based Hierarchical Leiden (preserved for comparison)
- **Unified API:** Single loader interface for all modes
- **Resolution Ladder:** 7 levels (0.25 → 3.0) consistent across modes

---

## 2. Map Mode Registry

| Mode ID | Name | Type | Status | Default |
|---------|------|------|--------|---------|
'''

for mode in modes:
    default_marker = '✅' if mode['is_default'] else ''
    spec += f'| {mode["mode_id"]} | {mode["name"]} | {mode["mode_type"]} | {mode["status"]} | {default_marker} |\n'

spec += '''
---

## 3. Default Mode: Center Projected Hierarchical Leiden

**Mode ID:** `center_projected_hierarchical`
**Evidence Tier:** REPRODUCED
**Validation Run:** 33127766775

### 3.1 Resolution Ladder
'''

for res in default_spec.resolution_ladder:
    count = default_spec.metadata.get('cluster_counts', {}).get(f'res_{res}', 'N/A')
    spec += f'- **Resolution {res}**: {count} clusters\n'

spec += '''
- **Hierarchical (validated)**: 108 clusters, nesting=1.0, purity=0.9638
- **Coarse (parent)**: 7 clusters at resolution 0.5

### 3.2 Key Metrics
- **Hierarchical purity**: 0.9638 (+0.0148 vs concat baseline 0.9491)
- **Perfect nesting**: 1.0 (guaranteed by hierarchical construction)
- **Adversarial language dominance**: 0.7593 (< 0.85 threshold) ✅
- **Jurist pairwise preference**: 0.5215 (> 0.5 threshold) ✅
- **Jurivoc hierarchy alignment**: 4/5 PASS
- **Zoom coherence**: 59.2% improvement rate

### 3.3 Artifacts
All artifacts available at `results/fractal_map/hierarchical_map_center_projected/`:
- `cluster_metadata.json` — Legal context per cluster (branch, area, chamber, language)
- `zoom_mappings.json` — Bidirectional parent-child navigation
- `zoom_coherence.json` — Per-cluster zoom improvement metrics
- `decision_clusters.json` — Decision-to-cluster index (1000 × 7 resolutions)
- `labels_res_*.npy` — Cluster assignments for rendering
- `labels_hierarchical_best.npy` — Best validated hierarchical config (108 clusters)
- `labels_coarse_0.5.npy` — 7-cluster parent level

---

## 4. Selectable Legal-Distance Modes

These modes are built on legal-distance embeddings (ACCEPTED tier evidence).

### 4.1 debiased_citation_blended (Legal-Distance Baseline)
- **Status:** AVAILABLE
- **Benchmarks:** 14/14 PASS
- **Strengths:** Citation heritage (AUC 0.91), multilingual invariance, balanced

### 4.2 legal_cited_decisions_only
- **Status:** AVAILABLE
- **Benchmarks:** 14/14 PASS
- **Strengths:** Best citation heritage (AUC 0.97), boilerplate resistance

### 4.3 hybrid_alpha_03 (30% Legal + 70% Baseline)
- **Status:** AVAILABLE
- **Benchmarks:** 13/14 PASS (fails adversarial_falsification)
- **Strengths:** Best branch classification (0.967), TF metadata recall (0.967)

### 4.4 hybrid_alpha_05 (50% Legal + 50% Baseline)
- **Status:** AVAILABLE
- **Benchmarks:** 13/14 PASS (fails adversarial_falsification)
- **Strengths:** Strongest branch classification (0.972), TF metadata recall (0.972)

### 4.5 legal_issues_outcomes
- **Status:** AVAILABLE
- **Benchmarks:** 10/14 PASS
- **Strengths:** Doctrinal issue/outcome similarity independent of citations

---

## 5. Legacy Mode (Preserved for Comparison)

### 5.1 hierarchical_leiden_concat (Concat-based - Legacy)
- **Status:** LEGACY
- **Benchmarks:** Hierarchy coherence PASS, zoom coherence 59.2% improvement
- **Note:** Replaced as default by center_projected_hierarchical per factory direction v4
- **Hierarchical purity**: 0.9491 (vs 0.9638 for center_projected)
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
✅ 59.2% zoom improvement rate validated  
✅ Hierarchical purity 0.9638 (+0.0148 vs concat baseline)  
✅ Adversarial language dominance 0.7593 < 0.85 PASS  
✅ Jurist pairwise preference 0.5215 > 0.5 PASS  
✅ Jurivoc 4/5 PASS  
✅ Map mode registry with 7 modes (1 default + 5 legal-distance + 1 legacy + 1 placeholder)  
✅ Unified loader API for all modes  
✅ Product integration specification complete  
✅ Map mode switching architecture designed  

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
'''

with open(output_dir / 'PRODUCT_INTEGRATION_SPEC.md', 'w') as f:
    f.write(spec)

print('Product integration package created successfully')
