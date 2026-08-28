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
