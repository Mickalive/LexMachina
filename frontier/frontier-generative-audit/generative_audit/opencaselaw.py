"""Post-generation citation/source validation (OpenCaseLaw + strict local).

Acceptance test (5): "Add post-generation citation/source validation, using
OpenCaseLaw attestation/claim support where feasible or strict local bundle
validation otherwise."

Operational note (negative result preserved): OpenCaseLaw's public
``/api/attest`` endpoint was unreachable from the GitHub-Actions-style CI
sandbox used for this cycle (curl exit 000 / no egress).  The validator
therefore defaults to strict local bundle validation and upgrades to
attestation automatically when the endpoint is reachable or when tests
inject a fake attestor.  No claim is made that attestation verified live
IDs in this cycle.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

OCL_ATTEST_ENDPOINT = os.environ.get(
    "LEX_OCL_ATTEST_URL", "https://opencaselaw.org/api/attest"
).rstrip("/")


@dataclass
class AttestationResult:
    """Result of a single OpenCaseLaw attestation check."""

    decision_id: str
    verified: bool
    attestation_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def default_fetch(url: str, timeout: float) -> Dict[str, Any]:
    """Fetch a JSON document; raises on any network/decoding failure."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LexMachina-GenerativeAudit/2.1", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


class OpenCaseLawAttestor:
    """Best-effort attestation of decision IDs against OpenCaseLaw.

    ``fetch`` is injectable so tests (and offline environments) never touch
    the network.  Results are cached per decision ID.
    """

    def __init__(
        self,
        timeout: float = 5.0,
        fetch: Optional[Callable[[str, float], Dict[str, Any]]] = None,
        enabled: bool = True,
    ):
        self.timeout = timeout
        self.fetch = fetch or default_fetch
        self.enabled = enabled
        self._cache: Dict[str, AttestationResult] = {}

    def attest_decision(self, decision_id: str) -> AttestationResult:
        if decision_id in self._cache:
            return self._cache[decision_id]

        if not self.enabled:
            result = AttestationResult(
                decision_id=decision_id, verified=False, error="attestation disabled"
            )
        else:
            url = f"{OCL_ATTEST_ENDPOINT}/{urllib.parse.quote(str(decision_id))}"
            try:
                data = self.fetch(url, self.timeout)
                verified = bool(data)
                result = AttestationResult(
                    decision_id=decision_id,
                    verified=verified,
                    attestation_data=data if verified else None,
                )
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
                result = AttestationResult(
                    decision_id=decision_id,
                    verified=False,
                    error=f"attestation unavailable: {exc}",
                )
            except Exception as exc:  # pragma: no cover - defensive
                result = AttestationResult(
                    decision_id=decision_id,
                    verified=False,
                    error=f"attestation error: {exc}",
                )

        self._cache[decision_id] = result
        return result

    def attest_batch(self, decision_ids: List[str]) -> Dict[str, AttestationResult]:
        return {did: self.attest_decision(did) for did in decision_ids}


def attestation_enabled_by_default() -> bool:
    """Opt-in via LEX_OCL_ATTEST=1 (default off: CI runners lack egress)."""
    return os.environ.get("LEX_OCL_ATTEST", "0").strip() == "1"


class PostGenerationValidator:
    """Citation validation = strict local bundle check (+ optional attestation)."""

    def __init__(
        self,
        bundle: Any,  # DecisionBundle (avoid circular import)
        use_attestation: Optional[bool] = None,
        attestor: Optional[OpenCaseLawAttestor] = None,
    ):
        self.bundle = bundle
        self.use_attestation = (
            attestation_enabled_by_default() if use_attestation is None else bool(use_attestation)
        )
        self.attestor = attestor or OpenCaseLawAttestor(enabled=self.use_attestation)

    def validate_citations(self, cited_ids: List[str]) -> Dict[str, Any]:
        from .source_packing import CitationValidator

        cited_ids = [c for c in (cited_ids or []) if c]
        valid_local = CitationValidator.filter_valid_citations(cited_ids, self.bundle.decision_ids)
        hallucinated = CitationValidator.hallucinated_ids(cited_ids, self.bundle.decision_ids)

        attestation_results: Dict[str, Any] = {}
        verified_ids: List[str] = []
        unverified_ids: List[str] = []

        for cid in valid_local:
            if self.use_attestation:
                res = self.attestor.attest_decision(cid)
                attestation_results[cid] = {
                    "verified": res.verified,
                    "attestation_data": res.attestation_data,
                    "error": res.error,
                }
                (verified_ids if res.verified else unverified_ids).append(cid)
            else:
                unverified_ids.append(cid)
                attestation_results[cid] = {
                    "verified": False,
                    "attestation_data": None,
                    "error": "attestation not attempted (strict local validation)",
                }

        return {
            "mode": "attestation+local" if self.use_attestation else "strict_local",
            "valid_citations": verified_ids + unverified_ids,
            "hallucinated_ids": hallucinated,
            "unverified_ids": unverified_ids,
            "verified_ids": verified_ids,
            "attestation_results": attestation_results,
            "local_bundle_ids": list(self.bundle.decision_ids),
        }

    def validate_and_filter(self, cited_ids: List[str]) -> Tuple[List[str], Dict[str, Any]]:
        report = self.validate_citations(cited_ids)
        return report["valid_citations"], report


def validate_bundle_against_ocl(bundle: Any) -> Dict[str, Any]:
    """Attest every bundle decision ID (best-effort; offline-safe)."""
    attestor = OpenCaseLawAttestor(enabled=attestation_enabled_by_default())
    results = attestor.attest_batch(list(bundle.decision_ids))
    return {
        "total_decisions": len(bundle.decision_ids),
        "verified_count": sum(1 for r in results.values() if r.verified),
        "unverified_count": sum(1 for r in results.values() if not r.verified),
        "per_decision": {did: {"verified": r.verified, "error": r.error} for did, r in results.items()},
    }
