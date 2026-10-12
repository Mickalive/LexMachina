"""OpenCaseLaw retrieval/cache adapter for LexMachina.

Turns a Swiss legal question into a normalised, provenance-preserving
``query_result_bundle`` **candidate set** without rebuilding a national corpus.

Public surface (see ``INTEGRATION_CONTRACT.json``)::

    from ocl_adapter import AdapterConfig, build_candidate_bundle
    from ocl_adapter import to_product_bundle, validate_candidate_bundle
"""
from __future__ import annotations

from .bundle import (
    ADAPTER_NAME,
    CANDIDATE_BUNDLE_VERSION,
    CANDIDATE_REQUIRED,
    PRODUCT_REQUIRED_DECISION,
    PRODUCT_REQUIRED_TOP,
    bundle_summary,
    rank_candidates,
    to_product_bundle,
    validate_against_product,
    validate_candidate_bundle,
)
from .cache import FileCache, request_key
from .client import OCLClient
from .config import AdapterConfig, config_from_env
from .dedupe import DedupeResult, dedupe, identity_key
from .errors import (
    OCLBudgetExceeded,
    OCLCacheMiss,
    OCLDecodeError,
    OCLError,
    OCLHTTPError,
    OCLTransportError,
    OCLValidationError,
)
from .expansion import QueryVariant, build_variants, tokenize
from .normalize import CHANNEL_PRIORITY, normalize_search_hit
from .pipeline import build_candidate_bundle as build_candidate_bundle_pipeline
from .pipeline import make_transport
from .ratelimit import RateLimiter, RequestBudget
from .transport import (
    CachedTransport,
    FixtureTransport,
    HttpTransport,
    RawResponse,
    ScriptedTransport,
    Transport,
)

__version__ = "1.0.0"

# `build_candidate_bundle` exists in both bundle.py (assembly) and pipeline.py
# (full run). The package-level name is the pipeline entry point.
build_candidate_bundle = build_candidate_bundle_pipeline

__all__ = [
    "__version__",
    "AdapterConfig",
    "config_from_env",
    "build_candidate_bundle",
    "make_transport",
    "to_product_bundle",
    "validate_candidate_bundle",
    "validate_against_product",
    "bundle_summary",
    "rank_candidates",
    "dedupe",
    "identity_key",
    "DedupeResult",
    "build_variants",
    "QueryVariant",
    "tokenize",
    "FileCache",
    "request_key",
    "OCLClient",
    "RateLimiter",
    "RequestBudget",
    "Transport",
    "HttpTransport",
    "CachedTransport",
    "FixtureTransport",
    "ScriptedTransport",
    "RawResponse",
    "normalize_search_hit",
    "CHANNEL_PRIORITY",
    "CANDIDATE_BUNDLE_VERSION",
    "CANDIDATE_REQUIRED",
    "PRODUCT_REQUIRED_TOP",
    "PRODUCT_REQUIRED_DECISION",
    "ADAPTER_NAME",
    "OCLError",
    "OCLTransportError",
    "OCLHTTPError",
    "OCLDecodeError",
    "OCLCacheMiss",
    "OCLBudgetExceeded",
    "OCLValidationError",
]
