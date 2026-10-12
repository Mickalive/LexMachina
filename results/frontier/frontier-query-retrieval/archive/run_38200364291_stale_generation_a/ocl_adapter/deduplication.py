"""
Deterministic deduplication for OpenCaseLaw decisions.

Deduplicates by canonical decision identity to ensure stable, reproducible
candidate sets regardless of query expansion or pagination order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import OrderedDict
import hashlib

from .client import Decision


@dataclass(frozen=True)
class DecisionIdentity:
    """
    Immutable identity for a decision used for deterministic deduplication.
    
    Uses canonical_decision_id as primary key, with fallbacks for
    cases where canonical ID is not available.
    """
    canonical_decision_id: str
    decision_id: str
    docket_number: str
    court: str
    decision_date: str
    
    @classmethod
    def from_decision(cls, decision: Decision) -> "DecisionIdentity":
        """Create identity from a Decision object."""
        return cls(
            canonical_decision_id=decision.canonical_decision_id or decision.decision_id,
            decision_id=decision.decision_id,
            docket_number=decision.docket_number,
            court=decision.court,
            decision_date=decision.decision_date,
        )
    
    def to_key(self) -> str:
        """Generate a stable string key for this identity."""
        # Use canonical_decision_id as primary, fallback to composite
        if self.canonical_decision_id and self.canonical_decision_id != "?":
            return self.canonical_decision_id
        
        # Fallback: composite key
        parts = [
            self.court or "",
            self.docket_number or "",
            self.decision_date or "",
            self.decision_id or "",
        ]
        return "|".join(p for p in parts if p)
    
    def __hash__(self) -> int:
        return hash(self.to_key())
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, DecisionIdentity):
            return False
        return self.to_key() == other.to_key()


def deduplicate_decisions(
    decisions: List[Decision],
    prefer_provenance: Optional[List[str]] = None,
) -> Tuple[List[Decision], Dict[str, Any]]:
    """
    Deduplicate decisions by canonical identity.
    
    Deterministic: always keeps the first occurrence (by input order) of each
    unique decision identity. When provenance preference is specified, prefers
    decisions from preferred sources.
    
    Args:
        decisions: List of Decision objects (may contain duplicates)
        prefer_provenance: Optional ordered list of provenance values to prefer
                          (e.g., ["live", "cache", "fixture"])
    
    Returns:
        Tuple of (deduplicated_decisions, deduplication_report)
    """
    if not decisions:
        return [], {
            "input_count": 0,
            "output_count": 0,
            "duplicates_removed": 0,
            "duplicate_groups": 0,
            "provenance_distribution": {},
        }
    
    # Track seen identities and their best candidate
    seen: Dict[DecisionIdentity, Decision] = {}
    provenance_order = {p: i for i, p in enumerate(prefer_provenance)} if prefer_provenance else {}
    default_provenance_rank = len(provenance_order)
    
    duplicate_groups = 0
    provenance_counts: Dict[str, int] = {}
    duplicate_identity_keys: Set[str] = set()
    
    for decision in decisions:
        identity = DecisionIdentity.from_decision(decision)
        provenance = decision.provenance or "unknown"
        provenance_counts[provenance] = provenance_counts.get(provenance, 0) + 1
        
        if identity in seen:
            # Count each unique identity only once for duplicate_groups
            if identity.to_key() not in duplicate_identity_keys:
                duplicate_groups += 1
                duplicate_identity_keys.add(identity.to_key())
            
            existing = seen[identity]
            
            # Decide whether to replace based on provenance preference
            existing_rank = provenance_order.get(existing.provenance, default_provenance_rank)
            new_rank = provenance_order.get(provenance, default_provenance_rank)
            
            if new_rank < existing_rank:
                # New decision has preferred provenance
                seen[identity] = decision
            # If equal rank, keep first (existing) - deterministic
        else:
            seen[identity] = decision
    
    # Preserve input order for output
    output = []
    seen_keys = set()
    for decision in decisions:
        identity = DecisionIdentity.from_decision(decision)
        key = identity.to_key()
        if key not in seen_keys:
            # This is the canonical representative for this identity
            output.append(seen[identity])
            seen_keys.add(key)
    
    report = {
        "input_count": len(decisions),
        "output_count": len(output),
        "duplicates_removed": len(decisions) - len(output),
        "duplicate_groups": duplicate_groups,
        "provenance_distribution": provenance_counts,
        "unique_identities": len(seen),
    }
    
    return output, report


def deduplicate_by_fields(
    decisions: List[Decision],
    fields: Tuple[str, ...] = ("canonical_decision_id", "decision_id", "docket_number"),
) -> Tuple[List[Decision], Dict[str, Any]]:
    """
    Alternative deduplication by specific fields.
    
    Useful when canonical_decision_id is not reliable.
    """
    seen_keys: Set[str] = set()
    output = []
    duplicates = 0
    
    for decision in decisions:
        # Build composite key from specified fields
        key_parts = []
        for field_name in fields:
            value = getattr(decision, field_name, None)
            if value:
                key_parts.append(str(value))
        
        if not key_parts:
            # No identifying fields, keep anyway
            output.append(decision)
            continue
        
        key = "|".join(key_parts)
        if key in seen_keys:
            duplicates += 1
        else:
            seen_keys.add(key)
            output.append(decision)
    
    return output, {
        "input_count": len(decisions),
        "output_count": len(output),
        "duplicates_removed": duplicates,
        "fields_used": fields,
    }


class DecisionDeduplicator:
    """
    Stateful deduplicator for incremental processing.
    
    Maintains a set of seen identities across multiple batches.
    """
    
    def __init__(self, prefer_provenance: Optional[List[str]] = None):
        self.prefer_provenance = prefer_provenance
        self._seen: Dict[DecisionIdentity, Decision] = {}
        self._provenance_order = {p: i for i, p in enumerate(prefer_provenance)} if prefer_provenance else {}
        self._default_rank = len(self._provenance_order)
        self._stats = {"total_processed": 0, "total_unique": 0, "total_duplicates": 0}
    
    def add(self, decision: Decision) -> bool:
        """
        Add a decision to the deduplicator.
        
        Returns True if decision was added (new), False if duplicate.
        """
        self._stats["total_processed"] += 1
        identity = DecisionIdentity.from_decision(decision)
        
        if identity in self._seen:
            existing = self._seen[identity]
            existing_rank = self._provenance_order.get(existing.provenance, self._default_rank)
            new_rank = self._provenance_order.get(decision.provenance, self._default_rank)
            
            if new_rank < existing_rank:
                self._seen[identity] = decision
            self._stats["total_duplicates"] += 1
            return False
        else:
            self._seen[identity] = decision
            self._stats["total_unique"] += 1
            return True
    
    def add_batch(self, decisions: List[Decision]) -> Tuple[List[Decision], int]:
        """Add a batch of decisions, return new decisions and duplicate count."""
        new_decisions = []
        for decision in decisions:
            if self.add(decision):
                new_decisions.append(decision)
        return new_decisions, len(decisions) - len(new_decisions)
    
    def get_unique(self) -> List[Decision]:
        """Get all unique decisions in order of first insertion."""
        return list(self._seen.values())
    
    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)
    
    def clear(self) -> None:
        """Reset the deduplicator."""
        self._seen.clear()
        self._stats = {"total_processed": 0, "total_unique": 0, "total_duplicates": 0}


def compute_identity_hash(decision: Decision) -> str:
    """
    Compute a stable content hash for a decision.
    
    Useful for detecting content changes across fetches.
    """
    # Hash stable fields only
    stable_fields = [
        decision.canonical_decision_id,
        decision.docket_number,
        decision.decision_date,
        decision.court,
        decision.language,
        decision.regeste or "",
        decision.rule_statement or "",
    ]
    content = "|".join(str(f) for f in stable_fields if f)
    return hashlib.sha256(content.encode()).hexdigest()[:16]