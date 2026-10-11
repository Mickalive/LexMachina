"""Narrow integration contract for the product lane.

Product needs exactly one call to obtain an audited query_result_bundle::

    from generative_audit.integration_contract import run_generative_audit
    audited = run_generative_audit(product_bundle)      # dict in, dict out

``audited`` is a NEW dict (input untouched) shaped like the product's
``query_result_bundle`` v1.0 (product/query/bundle.py) with:

  * ``answer`` replaced by the generative sourced answer
    (``prose`` / ``statements`` / ``cited_decision_ids`` / ``method`` / ``model``);
  * every decision carrying ``counter_status`` + ``counter_evidence`` +
    ``counter_uncertainty`` derived from the merged adversarial statuses;
  * ``provenance.generative_audit`` recording provider, model, validation
    mode and adversarial info for the UI/evidence trail.

Granular seams (package_answer / to_product_answer /
apply_to_product_bundle) are exported for lanes that want finer control.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from .adversarial import AdversarialFinding, AdversarialPass
from .models import AnswerPackage, DecisionStatus, StatusLabel
from .provider import Provider, ProviderResult
from .source_packing import DecisionBundle, from_product_bundle

#: Product-facing counter_status vocabulary.  The product UI treats any value
#: other than "none"/"cited" as a discoverable counter-authority
#: (product/static/query.html: isCounter).
COUNTER_STATUS_FOR = {
    StatusLabel.SUPPORTING: "supporting-candidate",
    StatusLabel.LIMITING: "candidate-limiting",
    StatusLabel.CONTRARY_OR_EXCEPTION: "candidate-contrary",
    StatusLabel.UNCLASSIFIED: "none",
}

#: Adversarial reason -> merged status label.
REASON_TO_STATUS = {
    "supporting": StatusLabel.SUPPORTING,
    "limiting": StatusLabel.LIMITING,
    "distinguishing": StatusLabel.LIMITING,
    "contradictory": StatusLabel.CONTRARY_OR_EXCEPTION,
    "exception": StatusLabel.CONTRARY_OR_EXCEPTION,
    "minority_line": StatusLabel.CONTRARY_OR_EXCEPTION,
    "language_branch": StatusLabel.CONTRARY_OR_EXCEPTION,
    "unclassified": StatusLabel.UNCLASSIFIED,
}

CONTRACT_VERSION = "generative-audit-contract/2.1"


def package_answer(
    result: ProviderResult,
    findings: List[AdversarialFinding],
    bundle: DecisionBundle,
) -> AnswerPackage:
    """Merge a provider result + adversarial findings into structured statuses.

    Semantics (acceptance test 4):
      * every bundle decision gets a status (default ``unclassified``);
      * a cited decision is ``supporting`` unless adversarial evidence of
        higher priority (limiting / contrary) overrides it;
      * merge uncertainty is the minimum of the merged inputs.
    """
    package = AnswerPackage(
        answer=result.answer,
        cited_decision_ids=list(result.cited_decision_ids),
    )

    status_map: Dict[str, DecisionStatus] = {
        dec.decision_id: DecisionStatus(
            decision_id=dec.decision_id,
            label=StatusLabel.UNCLASSIFIED,
            uncertainty=1.0,
        )
        for dec in bundle.decisions
    }
    for did in bundle.decision_ids:
        status_map.setdefault(
            did, DecisionStatus(decision_id=did, label=StatusLabel.UNCLASSIFIED, uncertainty=1.0)
        )

    for cid in result.cited_decision_ids:
        if cid in status_map:
            status_map[cid] = status_map[cid].merge(
                DecisionStatus(
                    decision_id=cid,
                    label=StatusLabel.SUPPORTING,
                    uncertainty=0.4,
                    evidence_refs=["cited in generated answer"],
                    adversarial_rationale="cited in generated answer",
                )
            )

    for finding in findings:
        label = REASON_TO_STATUS.get(finding.reason, StatusLabel.UNCLASSIFIED)
        incoming = DecisionStatus(
            decision_id=finding.decision_id,
            label=label,
            uncertainty=finding.uncertainty,
            evidence_refs=list(finding.evidence_refs),
            adversarial_rationale=finding.reason,
        )
        if finding.decision_id in status_map:
            status_map[finding.decision_id] = status_map[finding.decision_id].merge(incoming)
        else:
            status_map[finding.decision_id] = incoming

    package.decision_statuses = status_map
    package.finalize_statuses()
    return package


def to_product_answer(package: AnswerPackage, bundle: DecisionBundle) -> Dict[str, Any]:
    """Answer dict compatible with product/query/answer.py ``build_answer`` output."""
    by_id = bundle.by_id()
    statements = []
    for did in package.cited_decision_ids:
        dec = by_id.get(did)
        text = " ".join((dec.text if dec else "").split())[:300]
        statements.append({"text": text, "decision_id": did})
    return {
        "prose": package.answer,
        "statements": statements,
        "cited_decision_ids": list(package.cited_decision_ids),
        "method": "generative_audit_llm_v2",
        "model": "",  # filled by callers that know the model
    }


def apply_to_product_bundle(
    product_bundle: Dict[str, Any],
    package: AnswerPackage,
    findings: List[AdversarialFinding],
    provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a NEW product bundle with generative answer + counter statuses."""
    out = copy.deepcopy(product_bundle)
    bundle = from_product_bundle(out)

    answer = to_product_answer(package, bundle)
    answer["model"] = (provenance or {}).get("model", "")
    out["answer"] = answer

    findings_by_id = {f.decision_id: f for f in findings}
    for dec in out.get("decisions", []):
        did = dec.get("decision_id")
        status = package.decision_statuses.get(did)
        if status is None:
            continue
        # A decision that is cited AND limited/contrary must remain a visible
        # counter-authority: the product UI hides only "none"/"cited".
        if status.label in (StatusLabel.LIMITING, StatusLabel.CONTRARY_OR_EXCEPTION):
            dec["counter_status"] = COUNTER_STATUS_FOR[status.label]
        elif did in package.cited_decision_ids:
            dec["counter_status"] = "cited"
        else:
            dec["counter_status"] = COUNTER_STATUS_FOR.get(status.label, "none")
        finding = findings_by_id.get(did)
        dec["counter_evidence"] = "; ".join(status.evidence_refs[:2])
        dec["counter_uncertainty"] = round(status.uncertainty, 4)
        if finding is not None:
            dec["counter_reason"] = finding.reason
            dec["counter_confidence"] = round(finding.confidence, 4)

    prov = dict(out.get("provenance") or {})
    prov["generative_audit"] = {
        "contract": CONTRACT_VERSION,
        "status_summary": package.summary(),
        **(provenance or {}),
    }
    out["provenance"] = prov
    return out


def run_generative_audit(
    product_bundle: Dict[str, Any],
    provider: Optional[Provider] = None,
    fixture_mode: bool = False,
    fixture_answer: Optional[str] = None,
    fixture_cited_ids: Optional[List[str]] = None,
    fixture_findings: Optional[List[AdversarialFinding]] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """ONE-CALL product seam: query_result_bundle in, audited bundle out.

    ``fixture_mode=True`` makes the whole pipeline deterministic and offline
    (used by the frozen test suite).  Otherwise a real free model path is
    used (OpenCode CLI by default).
    """
    bundle = from_product_bundle(product_bundle)
    prov: Dict[str, Any] = {"contract": CONTRACT_VERSION}

    provider = provider or Provider(
        model=model,
        fixture_mode=fixture_mode,
        fixture_answer=fixture_answer,
        fixture_cited_ids=fixture_cited_ids,
    )
    result = provider.generate(bundle)
    prov["model"] = result.model_used
    prov["provider_error"] = result.error
    prov["citation_validation"] = {
        k: result.validation_report.get(k)
        for k in ("mode", "hallucinated_ids", "verified_ids", "unverified_ids")
    }

    adv = AdversarialPass(
        bundle=bundle,
        answer=result.answer,
        model=model,
        fixture_mode=fixture_mode,
        fixture_findings=fixture_findings,
    )
    findings, adv_info = adv.run_with_info()
    prov["adversarial"] = adv_info

    package = package_answer(result, findings, bundle)
    audited = apply_to_product_bundle(product_bundle, package, findings, provenance=prov)
    return audited


#: Aliases kept for lane symmetry with the v2 contract.
ProviderContract = Provider
AdversarialPassContract = AdversarialPass
AnswerPackageContract = AnswerPackage

__all__ = [
    "CONTRACT_VERSION",
    "COUNTER_STATUS_FOR",
    "REASON_TO_STATUS",
    "ProviderContract",
    "AdversarialPassContract",
    "AnswerPackageContract",
    "package_answer",
    "to_product_answer",
    "apply_to_product_bundle",
    "run_generative_audit",
]
