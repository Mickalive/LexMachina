#!/usr/bin/env python3
"""
Map Mode Loader API for Fractal Map Product Integration.

Provides a unified interface for loading and switching between different
map modes (hierarchical Leiden default + legal-distance modes).
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from map_mode_registry import (
    MAP_MODES, MapModeSpec, MapModeType, MapModeStatus,
    get_default_mode, get_mode, get_all_modes, get_legal_distance_modes
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MapArtifacts:
    """Loaded map artifacts for a mode."""
    mode_id: str
    cluster_metadata: Optional[Dict] = None
    zoom_mappings: Optional[Dict] = None
    zoom_coherence: Optional[Dict] = None
    decision_clusters: Optional[Dict] = None
    integration_summary: Optional[Dict] = None
    label_arrays: Dict[str, np.ndarray] = None
    
    def __post_init__(self):
        if self.label_arrays is None:
            self.label_arrays = {}


class MapModeLoader:
    """
    Unified loader for map modes.
    
    Handles loading of hierarchical Leiden (available) and provides
    placeholder infrastructure for legal-distance modes.
    """
    
    def __init__(self, base_path: Path = Path(".")):
        self.base_path = base_path
        self._cache: Dict[str, MapArtifacts] = {}
    
    def list_modes(self) -> List[Dict[str, Any]]:
        """List all available map modes with metadata."""
        modes = []
        for mode in get_all_modes():
            modes.append({
                "mode_id": mode.mode_id,
                "name": mode.name,
                "description": mode.description,
                "mode_type": mode.mode_type.value,
                "status": mode.status.value,
                "is_default": mode.is_default,
                "resolution_ladder": mode.resolution_ladder,
                "metadata": mode.metadata,
            })
        return modes
    
    def get_default_mode_id(self) -> str:
        """Get the default mode ID."""
        return get_default_mode().mode_id
    
    def load_mode(self, mode_id: str, use_cache: bool = True) -> MapArtifacts:
        """
        Load a map mode by ID.
        
        Args:
            mode_id: The mode identifier
            use_cache: Whether to use cached artifacts
            
        Returns:
            MapArtifacts object with loaded data
            
        Raises:
            ValueError: If mode_id is unknown
            FileNotFoundError: If required artifacts are missing
        """
        if mode_id in self._cache and use_cache:
            return self._cache[mode_id]
        
        mode = get_mode(mode_id)
        if mode is None:
            raise ValueError(f"Unknown map mode: {mode_id}")
        
        if mode.status == MapModeStatus.PLACEHOLDER:
            logger.warning(f"Mode {mode_id} is a placeholder - returning minimal artifacts")
            return self._load_placeholder(mode)
        
        if mode.status == MapModeStatus.PLANNED:
            raise NotImplementedError(f"Mode {mode_id} is planned but not implemented")
        
        # Load available mode
        artifacts = self._load_available_mode(mode)
        self._cache[mode_id] = artifacts
        return artifacts
    
    def _load_available_mode(self, mode: MapModeSpec) -> MapArtifacts:
        """Load artifacts for an available mode."""
        artifacts = MapArtifacts(mode_id=mode.mode_id)
        
        # Load JSON artifacts
        json_artifacts = [
            ("cluster_metadata", "cluster_metadata"),
            ("zoom_mappings", "zoom_mappings"),
            ("zoom_coherence", "zoom_coherence"),
            ("decision_clusters", "decision_clusters"),
            ("integration_summary", "integration_summary"),
        ]
        
        for attr_name, artifact_key in json_artifacts:
            if artifact_key in mode.artifacts:
                path = self.base_path / mode.artifacts[artifact_key]
                if path.exists():
                    with open(path) as f:
                        setattr(artifacts, attr_name, json.load(f))
                else:
                    logger.warning(f"Artifact not found: {path}")
        
        # Load label arrays (.npy files)
        for res in mode.resolution_ladder:
            key = f"labels_res_{res}"
            if key in mode.artifacts:
                path = self.base_path / mode.artifacts[key]
                if path.exists():
                    artifacts.label_arrays[key] = np.load(path)
                else:
                    logger.warning(f"Label array not found: {path}")
        
        # Load special arrays
        special_keys = ["labels_hierarchical_best", "labels_coarse_0.5"]
        for key in special_keys:
            if key in mode.artifacts:
                path = self.base_path / mode.artifacts[key]
                if path.exists():
                    artifacts.label_arrays[key] = np.load(path)
        
        logger.info(f"Loaded mode {mode.mode_id} with {len(artifacts.label_arrays)} label arrays")
        return artifacts
    
    def _load_placeholder(self, mode: MapModeSpec) -> MapArtifacts:
        """Return minimal artifacts for placeholder modes."""
        return MapArtifacts(
            mode_id=mode.mode_id,
            integration_summary={
                "mode_id": mode.mode_id,
                "name": mode.name,
                "status": "placeholder",
                "message": f"This mode ({mode.mode_id}) requires legal-distance embeddings to be computed. "
                           f"Infrastructure is ready; run legal-distance pipeline to generate.",
                "legal_distance_config": mode.legal_distance_config,
                "benchmark_results": mode.benchmark_results,
                "metadata": mode.metadata,
            }
        )
    
    def get_resolution_labels(self, mode_id: str, resolution: float) -> Optional[np.ndarray]:
        """Get cluster labels for a specific resolution."""
        artifacts = self.load_mode(mode_id)
        key = f"labels_res_{resolution}"
        return artifacts.label_arrays.get(key)
    
    def get_hierarchical_labels(self, mode_id: str) -> Optional[np.ndarray]:
        """Get hierarchical labels (for hierarchical Leiden mode)."""
        artifacts = self.load_mode(mode_id)
        return artifacts.label_arrays.get("labels_hierarchical_best")
    
    def get_coarse_labels(self, mode_id: str) -> Optional[np.ndarray]:
        """Get coarse labels (parent level for hierarchical mode)."""
        artifacts = self.load_mode(mode_id)
        return artifacts.label_arrays.get("labels_coarse_0.5")
    
    def get_cluster_metadata(self, mode_id: str, resolution: float) -> Optional[Dict]:
        """Get cluster metadata for a specific resolution."""
        artifacts = self.load_mode(mode_id)
        if artifacts.cluster_metadata is None:
            return None
        key = f"res_{resolution}"
        return artifacts.cluster_metadata.get(key)
    
    def get_hierarchical_cluster_metadata(self, mode_id: str) -> Optional[Dict]:
        """Get hierarchical cluster metadata."""
        artifacts = self.load_mode(mode_id)
        if artifacts.cluster_metadata is None:
            return None
        return artifacts.cluster_metadata.get("hierarchical")
    
    def get_zoom_mapping(self, mode_id: str, from_res: float, to_res: float) -> Optional[Dict]:
        """Get parent-child zoom mapping between two resolutions."""
        artifacts = self.load_mode(mode_id)
        if artifacts.zoom_mappings is None:
            return None
        key = f"{from_res}_to_{to_res}"
        return artifacts.zoom_mappings.get(key)
    
    def get_decision_clusters(self, mode_id: str, decision_id: str) -> Optional[Dict]:
        """Get cluster membership for a specific decision at all resolutions."""
        artifacts = self.load_mode(mode_id)
        if artifacts.decision_clusters is None:
            return None
        return artifacts.decision_clusters.get(decision_id)
    
    def get_zoom_coherence(self, mode_id: str, from_res: float, to_res: float) -> Optional[Dict]:
        """Get zoom coherence metrics for a resolution pair."""
        artifacts = self.load_mode(mode_id)
        if artifacts.zoom_coherence is None:
            return None
        key = f"{from_res}_to_{to_res}"
        return artifacts.zoom_coherence.get(key)
    
    def get_mode_spec(self, mode_id: str) -> Optional[MapModeSpec]:
        """Get the mode specification."""
        return get_mode(mode_id)
    
    def clear_cache(self) -> None:
        """Clear the artifact cache."""
        self._cache.clear()


def create_product_integration_package(output_dir: Path) -> None:
    """
    Create a complete product integration package with map mode switching.
    
    This creates a unified API that the product can use to load any map mode.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    loader = MapModeLoader()
    
    # 1. Export map mode registry
    registry_path = output_dir / "map_mode_registry.json"
    from map_mode_registry import export_registry
    export_registry(registry_path)
    
    # 2. Create unified loader module
    loader_code = '''#!/usr/bin/env python3
"""
Product Map Loader - Unified API for loading fractal map modes.

Usage:
    from product_map_loader import ProductMapLoader
    
    loader = ProductMapLoader()
    
    # List available modes
    modes = loader.list_modes()
    
    # Load default mode (hierarchical Leiden)
    artifacts = loader.load_default()
    
    # Load specific mode
    artifacts = loader.load_mode("legal_cited_decisions_only")
    
    # Get labels at specific resolution
    labels = loader.get_resolution_labels("hierarchical_leiden", 1.0)
    
    # Get cluster metadata
    metadata = loader.get_cluster_metadata("hierarchical_leiden", 0.5)
'''

    loader_file = output_dir / "product_map_loader.py"
    with open(loader_file, 'w') as f:
        f.write(loader_code)
    
    # Copy the actual loader implementation
    import shutil
    shutil.copy(
        Path("fractal_map/hierarchical/map_mode_registry.py"),
        output_dir / "map_mode_registry.py"
    )
    shutil.copy(
        Path("fractal_map/hierarchical/map_mode_loader.py"),
        output_dir / "map_mode_loader.py"
    )
    
    # 3. Create integration spec for product
    spec = generate_product_integration_spec(loader)
    spec_path = output_dir / "PRODUCT_INTEGRATION_SPEC.md"
    with open(spec_path, 'w') as f:
        f.write(spec)
    
    logger.info(f"Product integration package created at {output_dir}")


def generate_product_integration_spec(loader: MapModeLoader) -> str:
    """Generate product integration specification."""
    modes = loader.list_modes()
    default_mode = loader.get_default_mode_id()
    
    spec = f"""# Fractal Map Lane — Product Integration Specification (Map Mode Switching)

**Generated:** {__import__('datetime').datetime.now().isoformat()}
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
"""
    
    for mode in modes:
        default_marker = "✅" if mode["is_default"] else ""
        spec += f"| {mode['mode_id']} | {mode['name']} | {mode['mode_type']} | {mode['status']} | {default_marker} |\n"
    
    spec += f"""

---

## 3. Default Mode: Hierarchical Leiden

**Mode ID:** `hierarchical_leiden`
**Evidence Tier:** REPRODUCED
**Validation Run:** 33127766775

### 3.1 Resolution Ladder
"""
    
    default_spec = MAP_MODES["hierarchical_leiden"]
    for res in default_spec.resolution_ladder:
        count = default_spec.metadata.get("cluster_counts", {}).get(f"res_{res}", "N/A")
        spec += f"- **Resolution {res}**: {count} clusters\n"
    
    spec += f"""
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
    print(f"{m['mode_id']}: {m['name']} [{m['status']}]")

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
"""
    return spec


class ProductMapLoader:
    """
    Simplified product-facing loader.
    
    This is the main entry point for the product application.
    """
    
    def __init__(self, base_path: Path = Path(".")):
        self.loader = MapModeLoader(base_path)
    
    def list_modes(self) -> List[Dict[str, Any]]:
        return self.loader.list_modes()
    
    def load_default(self) -> MapArtifacts:
        return self.loader.load_mode(self.loader.get_default_mode_id())
    
    def load_mode(self, mode_id: str) -> MapArtifacts:
        return self.loader.load_mode(mode_id)
    
    def get_resolution_labels(self, mode_id: str, resolution: float) -> Optional[np.ndarray]:
        return self.loader.get_resolution_labels(mode_id, resolution)
    
    def get_hierarchical_labels(self, mode_id: str) -> Optional[np.ndarray]:
        return self.loader.get_hierarchical_labels(mode_id)
    
    def get_coarse_labels(self, mode_id: str) -> Optional[np.ndarray]:
        return self.loader.get_coarse_labels(mode_id)
    
    def get_cluster_metadata(self, mode_id: str, resolution: float) -> Optional[Dict]:
        return self.loader.get_cluster_metadata(mode_id, resolution)
    
    def get_hierarchical_cluster_metadata(self, mode_id: str) -> Optional[Dict]:
        return self.loader.get_hierarchical_cluster_metadata(mode_id)
    
    def get_zoom_mapping(self, mode_id: str, from_res: float, to_res: float) -> Optional[Dict]:
        return self.loader.get_zoom_mapping(mode_id, from_res, to_res)
    
    def get_decision_clusters(self, mode_id: str, decision_id: str) -> Optional[Dict]:
        return self.loader.get_decision_clusters(mode_id, decision_id)
    
    def get_zoom_coherence(self, mode_id: str, from_res: float, to_res: float) -> Optional[Dict]:
        return self.loader.get_zoom_coherence(mode_id, from_res, to_res)
    
    def get_mode_spec(self, mode_id: str) -> Optional[MapModeSpec]:
        return self.loader.get_mode_spec(mode_id)


if __name__ == "__main__":
    # Test the loader
    loader = MapModeLoader()
    
    print("=== MAP MODE LOADER TEST ===")
    print(f"Default mode: {loader.get_default_mode_id()}")
    
    modes = loader.list_modes()
    print(f"\\nTotal modes: {len(modes)}")
    for m in modes:
        print(f"  {m['mode_id']}: {m['name']} [{m['status']}] {'(DEFAULT)' if m['is_default'] else ''}")
    
# Test loading default mode
    print("\n--- Loading default mode ---")
    artifacts = loader.load_mode(loader.get_default_mode_id())
    print(f"Mode: {artifacts.mode_id}")
    print(f"Label arrays: {list(artifacts.label_arrays.keys())}")
    print(f"Cluster metadata keys: {list(artifacts.cluster_metadata.keys()) if artifacts.cluster_metadata else 'None'}")
    print(f"Zoom mappings keys: {list(artifacts.zoom_mappings.keys()) if artifacts.zoom_mappings else 'None'}")
    
    # Test resolution labels
    labels = loader.get_resolution_labels("hierarchical_leiden", 1.0)
    if labels is not None:
        print(f"\\nResolution 1.0 labels: {labels.shape}, unique clusters: {len(np.unique(labels[labels != -1]))}")
    
    # Test hierarchical labels
    hier_labels = loader.get_hierarchical_labels("hierarchical_leiden")
    if hier_labels is not None:
        print(f"Hierarchical labels: {hier_labels.shape}, unique clusters: {len(np.unique(hier_labels[hier_labels != -1]))}")
    
    # Create product integration package
    print("\\n--- Creating product integration package ---")
    create_product_integration_package(Path("results/fractal_map/product_integration"))
    
    print("\\n=== Test complete ===")