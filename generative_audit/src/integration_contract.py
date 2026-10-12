"""
Narrow integration contract for the product lane.

This module defines the contract that the generative-audit team
implements and the product team can directly copy/adapt.  It is
purposely minimal — only the seams required for end-to-end operation.

The contract specifies:
  1. The query_result_bundle format (already defined in source_packing)
  2. The Provider.generate() -> ProviderResult contract
  3. The AdversarialPass.run() -> List[AdversarialFinding] contract
  4. The AnswerPackage structure with merged DecisionStatuses
  5. The narrow API surface that product needs to integrate
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional

from source_packing import DecisionBundle
from provider import Provider, ProviderResult
from adversarial import AdversarialFinding, AdversarialPass
from models import AnswerPackage, DecisionStatus, StatusLabel


# ---- Integration contract signature ----

#: The narrow integration contract — product can call these interfaces.
#:
#: generate(bundle: DecisionBundle) -> ProviderResult
#:   Given a query_result_bundle, produce a sourced, grounded answer.
#   All cited decision IDs are guaranteed to be a subset of bundle.decision_ids.
#:
#: run_adversarial(bundle: DecisionBundle, answer: str) -> List[AdversarialFinding]
#:   Run an independent counter-authority pass.  Findings cite only
#:   decision IDs from the bundle and have a reason from the approved set.
#:
#: package_answer(result: ProviderResult, findings: List[AdversarialFinding])
#:   Merge the provider result and adversarial findings into an AnswerPackage
#:   with structured DecisionStatuses for every decision in the bundle.

#: Provider contract — minimal implementation the product lane can copy/adapt.
ProviderContract = Provider

#: Adversarial pass contract.
AdversarialPassContract = AdversarialPass

#: The AnswerPackage is the contract product integrates with.
#: Product may redefine this as a Pydantic model or dict, but the
#: semantic fields (answer, decision_statuses, counts) must be preserved.
AnswerPackageContract = AnswerPackage


def package_answer(
    result: ProviderResult,
    findings: List[AdversarialFinding],
    bundle: DecisionBundle,
) -> AnswerPackage:
    """
    Merge a ProviderResult and adversarial findings into an AnswerPackage
    with structured DecisionStatuses for every decision in the bundle.

    This is the narrow integration point that product can directly copy/adapt.

    :param result: The ProviderResult from generate()
    :param findings: The List[AdversarialFinding] from run_adversarial()
    :param bundle: The original DecisionBundle
    :return: An AnswerPackage with all decision statuses filled in
    """
    package = AnswerPackage(
        answer=result.answer,
        cited_decision_ids=result.cited_decision_ids,
    )

    # Build a map from decision_id to DecisionStatus, initialized to unclassified
    status_map: Dict[str, DecisionStatus] = {}

    for dec in bundle.decisions:
        status_map[dec.decision_id] = DecisionStatus(
            decision_id=dec.decision_id,
            label=StatusLabel.UNCLASSIFIED,
            uncertainty=1.0,
            evidence_refs=[],
            adversarial_rationale="",
        )

    # Apply the generated answer's cited IDs as supporting
    for cid in result.cited_decision_ids:
        if cid in status_map:
            status_map[cid] = DecisionStatus(
                decision_id=cid,
                label=StatusLabel.SUPPORTING,
                uncertainty=0.5,
                evidence_refs=[f"Cited in generated answer"],
                adversarial_rationale="Cited in generated answer",
            )

    # Map adversarial reasons to StatusLabel values
    reason_to_status = {
        "supporting": StatusLabel.SUPPORTING,
        "limiting": StatusLabel.LIMITING,
        "contradictory": StatusLabel.CONTRARY_OR_EXCEPTION,
        "exception": StatusLabel.CONTRARY_OR_EXCEPTION,
        "distinguishing": StatusLabel.LIMITING,
        "minority_line": StatusLabel.CONTRARY_OR_EXCEPTION,
        "language_branch": StatusLabel.CONTRARY_OR_EXCEPTION,
        "unclassified": StatusLabel.UNCLASSIFIED,
    }

    # Apply adversarial findings — merge with existing statuses
    for finding in findings:
        status_label = reason_to_status.get(
            finding.reason, StatusLabel.UNCLASSIFIED,
        )

        if finding.decision_id in status_map:
            existing = status_map[finding.decision_id]
            merged = existing.merge(
                DecisionStatus(
                    decision_id=finding.decision_id,
                    label=status_label,
                    uncertainty=finding.uncertainty,
                    evidence_refs=finding.evidence_refs,
                    adversarial_rationale=finding.reason,
                )
            )
            status_map[finding.decision_id] = merged
        else:
            # Decision not in bundle but cited by findings — add it
            status_map[finding.decision_id] = DecisionStatus(
                decision_id=finding.decision_id,
                label=status_label,
                uncertainty=finding.uncertainty,
                evidence_refs=finding.evidence_refs,
                adversarial_rationale=finding.reason,
            )

    package.decision_statuses = status_map
    package.finalize_statuses()

    return package