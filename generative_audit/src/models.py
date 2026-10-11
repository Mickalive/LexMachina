"""
Structured status models for adversarial findings and answer status.

Defines the classification system that merges the original generated
answer with the independent adversarial pass findings.

Status categories:
  - supporting:       the decision supports the provisional answer
  - limiting:         the decision narrows or restricts the answer's scope
  - contrary_or_exception: the decision contradicts the answer or creates an exception
  - unclassified:     the classification is uncertain or not well-supported

Each status carries uncertainty and evidence references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum


class StatusLabel(Enum):
    """The four possible status labels for a decision relative to the answer."""
    SUPPORTING = "supporting"
    LIMITING = "limiting"
    CONTRARY_OR_EXCEPTION = "contrary_or_exception"
    UNCLASSIFIED = "unclassified"


@dataclass
class DecisionStatus:
    """
    Status of a single decision relative to the generated answer.

    Attributes:
        decision_id: The ID of the decision.
        label: One of StatusLabel values.
        uncertainty: Uncertainty about the label in [0.0, 1.0].
        evidence_refs: Text spans from the decision that support the label.
        adversarial_rationale: Brief explanation of why this classification
            was chosen (from the adversarial pass).
    """
    decision_id: str
    label: StatusLabel
    uncertainty: float = 1.0
    evidence_refs: List[str] = field(default_factory=list)
    adversarial_rationale: str = ""

    def merge(self, other: "DecisionStatus") -> "DecisionStatus":
        """
        Merge another DecisionStatus for the same decision_id.

        Priority: if either classification is contrary_or_exception, the
        merged result is contrary_or_exception.  If one is supporting and
        the other limiting, the result is limiting.  If both are supporting,
        the result is supporting.  Uncertainty is minimized (taking the
        minimum of the two).
        """
        if self.label == other.label:
            # Same classification — keep it, minimize uncertainty
            new_uncertainty = min(self.uncertainty, other.uncertainty)
            return DecisionStatus(
                decision_id=self.decision_id,
                label=self.label,
                uncertainty=new_uncertainty,
                evidence_refs=self.evidence_refs + other.evidence_refs,
                adversarial_rationale=self.adversarial_rationale
                or other.adversarial_rationale,
            )

        # Classifications differ — apply priority hierarchy
        # contrary_or_exception > limiting > supporting
        hierarchy = {
            StatusLabel.CONTRARY_OR_EXCEPTION: 3,
            StatusLabel.LIMITING: 2,
            StatusLabel.SUPPORTING: 1,
            StatusLabel.UNCLASSIFIED: 0,
        }

        self_priority = hierarchy.get(self.label, 0)
        other_priority = hierarchy.get(other.label, 0)

        if self_priority > other_priority:
            # Self wins
            new_uncertainty = min(self.uncertainty, other.uncertainty)
            return DecisionStatus(
                decision_id=self.decision_id,
                label=self.label,
                uncertainty=new_uncertainty,
                evidence_refs=self.evidence_refs + other.evidence_refs,
                adversarial_rationale=self.adversarial_rationale
                or other.adversarial_rationale,
            )
        elif other_priority > self_priority:
            # Other wins
            new_uncertainty = min(self.uncertainty, other.uncertainty)
            return DecisionStatus(
                decision_id=other.decision_id,
                label=other.label,
                uncertainty=new_uncertainty,
                evidence_refs=other.evidence_refs + self.evidence_refs,
                adversarial_rationale=other.adversarial_rationale
                or self.adversarial_rationale,
            )
        else:
            # Same priority — default to unclassified, minimize uncertainty
            new_uncertainty = min(self.uncertainty, other.uncertainty)
            return DecisionStatus(
                decision_id=self.decision_id,
                label=StatusLabel.UNCLASSIFIED,
                uncertainty=new_uncertainty,
                evidence_refs=self.evidence_refs + other.evidence_refs,
                adversarial_rationale=self.adversarial_rationale
                or other.adversarial_rationale,
            )


def uncertainty_from_evidence(evidence_count: int, total_snippets: int) -> float:
    """
    Derive an uncertainty score from the amount of evidence.

    More evidence → lower uncertainty.  If evidence_count >= total_snippets,
    uncertainty is 0.0 (fully certain).  Otherwise, uncertainty decreases
    smoothly.

    :param evidence_count: Number of evidence snippets supporting the label
    :param total_snippets: Total available snippets for this decision
    :return: Uncertainty in [0.0, 1.0]
    """
    if total_snippets <= 0:
        return 1.0
    if evidence_count >= total_snippets:
        return 0.0
    # Smooth inverse: uncertainty = 1 - (evidence_count / total_snippets)
    return 1.0 - (evidence_count / total_snippets)


@dataclass
class AnswerPackage:
    """
    The complete packaged answer: the generated text, its citations,
    and the merged statuses for all decisions.
    """
    answer: str
    cited_decision_ids: List[str]
    decision_statuses: Dict[str, DecisionStatus] = field(default_factory=dict)
    # Summary counts
    supporting_count: int = 0
    limiting_count: int = 0
    contrary_or_exception_count: int = 0
    unclassified_count: int = 0

    def finalize_statuses(self) -> None:
        """Compute summary counts from the decision_statuses dict."""
        self.supporting_count = 0
        self.limiting_count = 0
        self.contrary_or_exception_count = 0
        self.unclassified_count = 0

        for status in self.decision_statuses.values():
            label = status.label
            if label == StatusLabel.SUPPORTING:
                self.supporting_count += 1
            elif label == StatusLabel.LIMITING:
                self.limiting_count += 1
            elif label == StatusLabel.CONTRARY_OR_EXCEPTION:
                self.contrary_or_exception_count += 1
            elif label == StatusLabel.UNCLASSIFIED:
                self.unclassified_count += 1