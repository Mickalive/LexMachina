#!/usr/bin/env python3
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
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import the core loader classes
import sys
sys.path.insert(0, str(Path(__file__).parent))
from map_mode_loader import MapModeLoader, MapArtifacts
from map_mode_registry import MapModeSpec, MapModeType, MapModeStatus


@dataclass
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
    loader = ProductMapLoader()
    
    print("=== PRODUCT MAP LOADER TEST ===")
    print(f"Default mode: {loader.loader.get_default_mode_id()}")
    
    modes = loader.list_modes()
    print(f"\nTotal modes: {len(modes)}")
    for m in modes:
        print(f"  {m['mode_id']}: {m['name']} [{m['status']}] {'(DEFAULT)' if m['is_default'] else ''}")
    
    # Test loading default mode
    print("\n--- Loading default mode ---")
    artifacts = loader.load_default()
    print(f"Mode: {artifacts.mode_id}")
    print(f"Label arrays: {list(artifacts.label_arrays.keys())}")
    print(f"Cluster metadata keys: {list(artifacts.cluster_metadata.keys()) if artifacts.cluster_metadata else 'None'}")
    print(f"Zoom mappings keys: {list(artifacts.zoom_mappings.keys()) if artifacts.zoom_mappings else 'None'}")
