"""
OpenCaseLaw Retrieval Adapter for LexMachina Frontier Query Retrieval.

A production-ready adapter that turns a Swiss legal question into a normalized,
provenance-preserving query_result_bundle candidate set for downstream answer
generation and mapping.

Key features:
- OpenCaseLaw public REST API integration with pagination and rate limiting
- Multilingual query expansion (DE/FR/IT)
- Deterministic deduplication by decision_id/canonical identity
- Lazy full decision/structure retrieval
- Citation-neighborhood expansion (incoming/outgoing/leading cases)
- File-based caching for deterministic offline testing
- Configurable target result count (100-300 decisions)
"""

__version__ = "1.0.0"
__charter_version__ = 2

from .client import OpenCaseLawClient, RateLimiter, CacheManager
from .expansion import QueryExpander, SWISS_LEGAL_SYNONYMS
from .deduplication import deduplicate_decisions, DecisionIdentity
from .bundle import QueryResultBundle, build_bundle_from_retrieval, validate_bundle
from .cli import main as cli_main

__all__ = [
    "OpenCaseLawClient",
    "RateLimiter", 
    "CacheManager",
    "QueryExpander",
    "SWISS_LEGAL_SYNONYMS",
    "deduplicate_decisions",
    "DecisionIdentity",
    "QueryResultBundle",
    "build_bundle_from_retrieval",
    "validate_bundle",
    "cli_main",
]