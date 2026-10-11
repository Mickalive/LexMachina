"""OpenCaseLaw Retrieval Adapter - Frontier Query Retrieval Team.

A production-ready adapter that turns a Swiss legal question into a normalized,
provenance-preserving query_result_bundle candidate set for downstream answer
generation and mapping.

Integration Contract: See contracts/INTEGRATION_CONTRACT.md
"""

from .ocl_adapter import (
    OpenCaseLawAdapter,
    OCLConfig,
    SearchRequest,
    SearchResult,
    Decision,
    CitationNeighborhood,
    build_query_bundle,
    expand_query_multilingual,
)

__all__ = [
    "OpenCaseLawAdapter",
    "OCLConfig",
    "SearchRequest",
    "SearchResult",
    "Decision",
    "CitationNeighborhood",
    "build_query_bundle",
    "expand_query_multilingual",
]