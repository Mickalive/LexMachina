"""Frontier Query Concept Recall - Deterministic multilingual query expansion layer.

This module implements a corpus-derived, deterministic query-expansion layer that
closes the accepted query-concept coverage gap on the served retrieval path.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "ConceptExpander",
    "ExpansionConfig",
    "build_expanded_variants",
    "measure_concept_coverage",
    "measure_authority_recall",
]