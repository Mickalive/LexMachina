"""
Source packing and citation validation for generative audit.

Responsibilities:
  - Build a DecisionBundle from raw query/decision data
  - Validate that cited decision IDs belong to the source bundle
  - Reject hallucinated IDs programmatically
  - Provide a clean abstraction for the provider to consume

The DecisionBundle is the canonical input format for the provider:
  - query: the original legal research question
  - decision_ids: flat list of valid decision IDs from the retrieval set
  - decisions: list of decision objects with id, title, text, citations, metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Decision:
    """A single retrieved decision with its metadata."""
    decision_id: str
    title: str
    text: str  # full decision text or substantial snippet
    citations: List[str] = field(default_factory=list)  # decision IDs cited by this decision
    metadata: Dict[str, Any] = field(default_factory=dict)  # year, language, practice area, etc.


@dataclass
class DecisionBundle:
    """Canonical bundle format consumed by the provider.

    This is the "query_result_bundle" referenced in the charter.
    All decision IDs surfaced in the generated answer must be a subset
    of bundle.decision_ids.
    """
    query: str
    decision_ids: List[str]  # flat, ordered list of valid IDs
    decisions: List[Decision] = field(default_factory=list)
    # Optional: per-decision rerank / retrieval scores
    retrieval_scores: Dict[str, float] = field(default_factory=dict)


class CitationValidator:
    """Validate and filter citations against a DecisionBundle."""

    @staticmethod
    def filter_valid_citations(
        cited_ids: List[str],
        valid_ids: List[str],
    ) -> List[str]:
        """
        Filter a list of cited decision IDs, keeping only those present
        in the valid_ids list.

        Returns the filtered list preserving original order, de-duplicated.
        """
        valid_set = set(valid_ids)
        seen = set()
        result = []
        for cid in cited_ids:
            if cid in valid_set and cid not in seen:
                seen.add(cid)
                result.append(cid)
        return result

    @staticmethod
    def validate_bundle_integrity(bundle: DecisionBundle) -> bool:
        """
        Verify that every decision in the bundle has a non-empty ID
        and that the query is non-empty.  Returns True if the bundle
        is well-formed and ready for provider consumption.
        """
        if not bundle.query or not bundle.query.strip():
            return False
        if not bundle.decision_ids:
            return False
        for dec in bundle.decisions:
            if not dec.decision_id or not dec.decision_id.strip():
                return False
        return True

    @staticmethod
    def from_retrieval_result(
        query: str,
        decisions: List[Dict[str, Any]],
    ) -> DecisionBundle:
        """
        Construct a DecisionBundle from a retrieval result dict list.

        Each decision dict should have at minimum: decision_id, title, text.
        """
        decision_objs = []
        valid_ids = []

        for d in decisions:
            did = d.get("decision_id") or d.get("id") or ""
            if not did:
                continue
            decision_objs.append(
                Decision(
                    decision_id=did,
                    title=d.get("title", ""),
                    text=d.get("text", ""),
                    citations=d.get("citations", []),
                    metadata=d.get("metadata", {}),
                )
            )
            valid_ids.append(did)

        # Preserve order as provided, de-duplicate
        seen = set()
        ordered_ids = []
        for id_ in valid_ids:
            if id_ not in seen:
                seen.add(id_)
                ordered_ids.append(id_)

        return DecisionBundle(
            query=query,
            decision_ids=ordered_ids,
            decisions=decision_objs,
            retrieval_scores={},
        )