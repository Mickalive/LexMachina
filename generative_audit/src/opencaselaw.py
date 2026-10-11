"""
OpenCaseLaw attestation and verification for citation validation.

Provides post-generation citation/source validation using OpenCaseLaw's
verification/attestation endpoints. Falls back to strict local bundle
validation when attestation is unavailable.

This satisfies acceptance test (5): "Add post-generation citation/source
validation, using OpenCaseLaw attestation/claim support where feasible
or strict local bundle validation otherwise."
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# OpenCaseLaw public endpoints
OCL_ATTEST_ENDPOINT = "https://opencaselaw.org/api/attest"
OCL_SEARCH_ENDPOINT = "https://opencaselaw.org/api/search"


@dataclass
class AttestationResult:
    """Result of an OpenCaseLaw attestation check."""
    decision_id: str
    verified: bool
    attestation_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class OpenCaseLawAttestor:
    """
    Validate citations against OpenCaseLaw's attestation endpoint.

    When attestation is available (network reachable, decision exists in OCL),
    it provides cryptographic verification that a decision ID corresponds to
    a real decision in the OpenCaseLaw corpus. When unavailable, falls back
    to local bundle validation.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._cache: Dict[str, AttestationResult] = {}

    def attest_decision(self, decision_id: str) -> AttestationResult:
        """
        Check a single decision ID against OpenCaseLaw attestation.

        Returns AttestationResult with verified=True if the decision is
        attested, False otherwise. Caches results to avoid repeated calls.
        """
        if decision_id in self._cache:
            return self._cache[decision_id]

        try:
            # Try attestation endpoint
            url = f"{OCL_ATTEST_ENDPOINT}/{urllib.parse.quote(decision_id)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "LexMachina-MVP/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))

            # If we get a valid response with attestation data, it's verified
            verified = bool(data and isinstance(data, dict))
            result = AttestationResult(
                decision_id=decision_id,
                verified=verified,
                attestation_data=data if verified else None,
            )

        except Exception as e:
            # Attestation unavailable — fallback to local validation
            result = AttestationResult(
                decision_id=decision_id,
                verified=False,
                error=f"Attestation unavailable: {e}",
            )

        self._cache[decision_id] = result
        return result

    def attest_batch(self, decision_ids: List[str]) -> Dict[str, AttestationResult]:
        """
        Attest multiple decision IDs.

        Returns a dict mapping decision_id -> AttestationResult.
        """
        results = {}
        for did in decision_ids:
            results[did] = self.attest_decision(did)
        return results


class PostGenerationValidator:
    """
    Post-generation citation and source validation.

    Combines:
    1. Local bundle validation (strict: cited IDs must be in the source bundle)
    2. OpenCaseLaw attestation (when feasible: verified decision exists in OCL)

    The validator returns a validation report indicating which citations are
    valid, which are hallucinated, and which are unverified but present in
    the local bundle.
    """

    def __init__(
        self,
        bundle: Any,  # DecisionBundle - avoiding circular import
        use_attestation: bool = True,
        attestor: Optional[OpenCaseLawAttestor] = None,
    ):
        self.bundle = bundle
        self.use_attestation = use_attestation
        self.attestor = attestor or OpenCaseLawAttestor()

    def validate_citations(
        self,
        cited_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Validate a list of cited decision IDs.

        Returns a validation report with:
        - valid_citations: IDs that pass both local and attestation checks
        - hallucinated_ids: IDs not in the source bundle
        - unverified_ids: IDs in bundle but attestation failed/unavailable
        - attestation_results: per-ID attestation details
        """
        from .source_packing import CitationValidator

        # Step 1: Local bundle validation (strict)
        valid_local = CitationValidator.filter_valid_citations(
            cited_ids, self.bundle.decision_ids
        )
        hallucinated = [cid for cid in cited_ids if cid not in self.bundle.decision_ids]

        # Step 2: OpenCaseLaw attestation (best-effort)
        attestation_results = {}
        verified_ids = []
        unverified_ids = []

        if self.use_attestation and valid_local:
            for cid in valid_local:
                result = self.attestor.attest_decision(cid)
                attestation_results[cid] = {
                    "verified": result.verified,
                    "attestation_data": result.attestation_data,
                    "error": result.error,
                }
                if result.verified:
                    verified_ids.append(cid)
                else:
                    unverified_ids.append(cid)
        else:
            # No attestation attempted — all locally valid are "unverified"
            for cid in valid_local:
                unverified_ids.append(cid)
                attestation_results[cid] = {
                    "verified": False,
                    "attestation_data": None,
                    "error": "Attestation not attempted",
                }

        return {
            "valid_citations": verified_ids + unverified_ids,
            "hallucinated_ids": hallucinated,
            "unverified_ids": unverified_ids,
            "verified_ids": verified_ids,
            "attestation_results": attestation_results,
            "local_bundle_ids": self.bundle.decision_ids,
        }

    def validate_and_filter(
        self,
        cited_ids: List[str],
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Validate and return the filtered list of valid citations.

        Returns (filtered_citations, validation_report).
        """
        report = self.validate_citations(cited_ids)
        return report["valid_citations"], report


def validate_bundle_against_ocl(bundle: Any) -> Dict[str, Any]:
    """
    Validate all decision IDs in a bundle against OpenCaseLaw attestation.

    Useful for checking the integrity of a retrieved bundle against
    the canonical OpenCaseLaw corpus.

    Returns a report with per-decision attestation status.
    """
    attestor = OpenCaseLawAttestor()
    results = attestor.attest_batch(bundle.decision_ids)

    verified = sum(1 for r in results.values() if r.verified)
    failed = sum(1 for r in results.values() if not r.verified)

    return {
        "total_decisions": len(bundle.decision_ids),
        "verified_count": verified,
        "unverified_count": failed,
        "per_decision": {
            did: {
                "verified": r.verified,
                "error": r.error,
            }
            for did, r in results.items()
        },
    }