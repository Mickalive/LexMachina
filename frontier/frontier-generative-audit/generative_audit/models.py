"""Structured status models for merged answer/counter-authority classification.

Status categories (charter acceptance test 4):
  supporting, limiting, contrary_or_exception, unclassified
— each carrying uncertainty in [0, 1] and evidence references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class StatusLabel(Enum):
    SUPPORTING = "supporting"
    LIMITING = "limiting"
    CONTRARY_OR_EXCEPTION = "contrary_or_exception"
    UNCLASSIFIED = "unclassified"


#: Merge priority: contrary evidence dominates limiting, which dominates supporting.
PRIORITY = {
    StatusLabel.CONTRARY_OR_EXCEPTION: 3,
    StatusLabel.LIMITING: 2,
    StatusLabel.SUPPORTING: 1,
    StatusLabel.UNCLASSIFIED: 0,
}


def clamp01(value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 1.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


@dataclass
class DecisionStatus:
    """Status of one decision relative to the generated answer."""

    decision_id: str
    label: StatusLabel
    uncertainty: float = 1.0
    evidence_refs: List[str] = field(default_factory=list)
    adversarial_rationale: str = ""

    def __post_init__(self) -> None:
        self.uncertainty = clamp01(self.uncertainty)
        if not isinstance(self.label, StatusLabel):
            self.label = StatusLabel.UNCLASSIFIED

    def merge(self, other: "DecisionStatus") -> "DecisionStatus":
        """Merge two statuses for the same decision.

        Higher priority wins; on a tie the more adversarial-leaning label is
        kept unless equal, in which case priority resolves.  Evidence and
        rationale are unioned; uncertainty is the minimum of the two.
        """
        if self.label == other.label:
            new_label = self.label
        elif PRIORITY[self.label] > PRIORITY[other.label]:
            new_label = self.label
        elif PRIORITY[other.label] > PRIORITY[self.label]:
            new_label = other.label
        else:  # pragma: no cover - unreachable, kept for safety
            new_label = StatusLabel.UNCLASSIFIED

        leading = self if new_label == self.label else other
        trailing = other if leading is self else self
        evidence: List[str] = []
        for ref in list(leading.evidence_refs) + list(trailing.evidence_refs):
            if ref and ref not in evidence:
                evidence.append(ref)
        return DecisionStatus(
            decision_id=self.decision_id,
            label=new_label,
            uncertainty=min(clamp01(self.uncertainty), clamp01(other.uncertainty)),
            evidence_refs=evidence,
            adversarial_rationale=leading.adversarial_rationale or trailing.adversarial_rationale,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "label": self.label.value,
            "uncertainty": round(self.uncertainty, 4),
            "evidence_refs": list(self.evidence_refs),
            "adversarial_rationale": self.adversarial_rationale,
        }


def uncertainty_from_evidence(evidence_count: int, total_snippets: int) -> float:
    """More evidence -> lower uncertainty.  No evidence -> 1.0."""
    if total_snippets <= 0:
        return 1.0
    if evidence_count >= total_snippets:
        return 0.0
    return 1.0 - (evidence_count / total_snippets)


@dataclass
class AnswerPackage:
    """Merged package: answer + citations + per-decision statuses."""

    answer: str
    cited_decision_ids: List[str]
    decision_statuses: Dict[str, DecisionStatus] = field(default_factory=dict)
    supporting_count: int = 0
    limiting_count: int = 0
    contrary_or_exception_count: int = 0
    unclassified_count: int = 0
    #: provenance of the adversarial evidence source-check (see evidence.py)
    evidence_check: Dict[str, Any] = field(default_factory=dict)
    #: findings after source-checking (quotes filtered / uncertainty raised)
    checked_findings: List[Any] = field(default_factory=list)

    def finalize_statuses(self) -> None:
        counts = {label: 0 for label in StatusLabel}
        for status in self.decision_statuses.values():
            counts[status.label] += 1
        self.supporting_count = counts[StatusLabel.SUPPORTING]
        self.limiting_count = counts[StatusLabel.LIMITING]
        self.contrary_or_exception_count = counts[StatusLabel.CONTRARY_OR_EXCEPTION]
        self.unclassified_count = counts[StatusLabel.UNCLASSIFIED]

    def summary(self) -> Dict[str, int]:
        return {
            "supporting": self.supporting_count,
            "limiting": self.limiting_count,
            "contrary_or_exception": self.contrary_or_exception_count,
            "unclassified": self.unclassified_count,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "cited_decision_ids": list(self.cited_decision_ids),
            "status_summary": self.summary(),
            "decision_statuses": {
                did: st.to_dict() for did, st in sorted(self.decision_statuses.items())
            },
            "evidence_check": self.evidence_check,
        }
