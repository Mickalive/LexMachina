"""Error taxonomy for the OpenCaseLaw retrieval adapter.

Every failure mode the adapter can encounter has a typed exception so callers
(and the degradation path) can distinguish "remote is down", "not found",
"cache miss while offline" and "we ran out of request budget" without
parsing free text.
"""
from __future__ import annotations


class OCLError(Exception):
    """Base class for all adapter errors."""


class OCLTransportError(OCLError):
    """Network/IO failure after retries were exhausted."""

    def __init__(self, message: str, *, url: str = "", attempts: int = 0):
        super().__init__(message)
        self.url = url
        self.attempts = attempts


class OCLHTTPError(OCLError):
    """The remote answered with a non-2xx HTTP status."""

    def __init__(self, status: int, detail: str = "", *, url: str = ""):
        super().__init__(f"HTTP {status} for {url}: {detail}"[:400])
        self.status = status
        self.detail = detail
        self.url = url


class OCLDecodeError(OCLError):
    """Remote returned a body that is not usable JSON."""


class OCLCacheMiss(OCLError):
    """Offline/cached mode asked for a key that is not in the cache."""


class OCLBudgetExceeded(OCLError):
    """Configured request budget was exhausted."""


class OCLValidationError(OCLError):
    """A produced bundle/contract failed validation."""
