"""Product-owned location for the OpenCaseLaw retrieval cache.

Why this module exists
----------------------
The accepted Frontier adapter (``frontier/frontier-query-retrieval/ocl_adapter``)
defaults its content-addressed cache to ``results/frontier/.../cache``.  That
is another lane's directory, so every *live* product run created new files
there and ``Enforce lane write scope`` (``.github/workflows/core-lane.yml``)
failed the team job *after* the cycle itself had succeeded.  That is the exact
orchestration failure of run 38575541439 (team job: steps 6 and 7 green,
step 9 ``exit 3``, audit/integrate skipped).

Only the root moves.  Envelope format, ``CACHE_VERSION`` and the
content-addressed layout are untouched, so entries are interchangeable with
the adapter's own cache and fixtures keep working unchanged.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_CACHE_DIR = REPO_ROOT / "results" / "product" / "query_cache"


def product_cache_dir() -> Path:
    """Return the product-owned cache root, creating it on demand."""
    PRODUCT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return PRODUCT_CACHE_DIR


__all__ = ["PRODUCT_CACHE_DIR", "product_cache_dir", "REPO_ROOT"]
