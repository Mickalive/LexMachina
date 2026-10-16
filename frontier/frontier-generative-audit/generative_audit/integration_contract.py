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
from .evidence import is_quote_ref, source_check_findings, verified_evidence_refs
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

CONTRACT_VERSION = "generative-audit-contract/2.2"


def package_answer(
    result: ProviderResult,
    findings: List[AdversarialFinding],
    bundle: DecisionBundle,
    quote_auditor: Optional[Any] = None,
) -> AnswerPackage:
    """Merge a provider result + adversarial findings into structured statuses.

    Semantics (acceptance test 4):
      * every bundle decision gets a status (default ``unclassified``);
      * a cited decision is ``supporting`` unless adversarial evidence of
        higher priority (limiting / contrary) overrides it;
      * merge uncertainty is the minimum of the merged inputs;
      * every finding's ``evidence_refs`` is source-checked against the
        cited decision's retrieved text first (acceptance test 5 +
        audit repair 3): unverifiable quotes are dropped, never surfaced,
        and a finding with no verifiable quote is downgraded to
        uncertainty >= 0.95.
    """
    checked_findings, evidence_report = source_check_findings(
        findings, bundle, quote_auditor=quote_auditor
    )

    package = AnswerPackage(
        answer=result.answer,
        cited_decision_ids=list(result.cited_decision_ids),
    )
    package.evidence_check = evidence_report
    package.checked_findings = checked_findings

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

    for finding in checked_findings:
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
    """Return a NEW product bundle with generative answer + counter statuses.

    Evidence boundary guard: ``decisions[*].counter_evidence`` only ever
    receives quotes that occur verbatim in that decision's retrieved text
    (plus internal non-quote markers such as ``cited in generated answer``).
    Rejected quotes are counted in the provenance block, never displayed.
    """
    out = copy.deepcopy(product_bundle)
    bundle = from_product_bundle(out)
    by_text = {dec.decision_id: dec.text for dec in bundle.decisions}

    answer = to_product_answer(package, bundle)
    answer["model"] = (provenance or {}).get("model", "")
    out["answer"] = answer

    checked_findings = list(package.checked_findings or findings or [])
    findings_by_id = {f.decision_id: f for f in checked_findings}
    boundary_rejected = 0
    suppressed_challenges = 0
    numeric_scores = [
        float(d.get("score"))
        for d in out.get("decisions", [])
        if isinstance(d.get("score"), (int, float))
    ]
    max_score = max(numeric_scores, default=0.0)
    relevance_floor = max_score * 0.12 if max_score > 0.0 else 0.0

    for dec in out.get("decisions", []):
        did = dec.get("decision_id")
        status = package.decision_statuses.get(did)
        if status is None:
            continue

        finding = findings_by_id.get(did)
        quote_refs = [r for r in status.evidence_refs if is_quote_ref(r)]
        kept_refs, rejected = verified_evidence_refs(
            list(status.evidence_refs), by_text.get(did, "")
        )
        boundary_rejected += rejected
        verified_finding_refs = [
            r for r in (finding.evidence_refs if finding is not None else [])
            if is_quote_ref(r) and r in kept_refs
        ]

        try:
            rank = int(dec.get("rank") or 10**9)
        except (TypeError, ValueError):
            rank = 10**9
        score = dec.get("score")
        score_ok = (
            True
            if not isinstance(score, (int, float)) or max_score <= 0.0
            else float(score) >= relevance_floor
        )
        precision_gate = bool(
            finding is not None
            and verified_finding_refs
            and float(finding.uncertainty) < 0.9
            and float(finding.confidence) >= 0.5
            and rank <= 40
            and score_ok
        )

        # Fail closed on counter labels.  A challenge stays in the audit record,
        # but the product surface only labels it limiting/contrary when its own
        # decision supplies verified evidence and the row is still in the
        # high-relevance head.  The previous behaviour rendered every model
        # challenge, including empty-evidence and off-domain rows.
        if (
            status.label in (StatusLabel.LIMITING, StatusLabel.CONTRARY_OR_EXCEPTION)
            and precision_gate
        ):
            dec["counter_status"] = COUNTER_STATUS_FOR[status.label]
        elif did in package.cited_decision_ids:
            dec["counter_status"] = "cited"
        else:
            if status.label in (StatusLabel.LIMITING, StatusLabel.CONTRARY_OR_EXCEPTION):
                suppressed_challenges += 1
            dec["counter_status"] = "none"

        dec["counter_evidence"] = "; ".join(verified_finding_refs[:2]) if precision_gate else ""
        dec["counter_uncertainty"] = round(status.uncertainty, 4)
        dec["counter_evidence_verified"] = bool(precision_gate and verified_finding_refs)
        if finding is not None:
            dec["counter_reason"] = finding.reason
            dec["counter_confidence"] = round(finding.confidence, 4)
            dec["counter_surface_gate"] = {
                "passed": precision_gate,
                "rank": rank,
                "score": score,
                "relevance_floor": round(relevance_floor, 6),
                "verified_evidence_refs": len(verified_finding_refs),
            }

    prov = dict(out.get("provenance") or {})
    prov["generative_audit"] = {
        "contract": CONTRACT_VERSION,
        "status_summary": package.summary(),
        "evidence_source_check": package.evidence_check or None,
        "evidence_boundary_rejected_refs": boundary_rejected,
        "counter_surface_policy": "verified_evidence+rank<=40+relative_relevance+confidence>=0.5+uncertainty<0.9",
        "counter_surface_suppressed": suppressed_challenges,
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
    quote_auditor: Optional[Any] = None,
    validate_draft_live: bool = False,
) -> Dict[str, Any]:
    """ONE-CALL product seam: query_result_bundle in, audited bundle out.

    ``fixture_mode=True`` makes the whole pipeline deterministic and offline
    (used by the frozen test suite).  Otherwise a real free model path is
    used (OpenCode CLI by default).

    ``quote_auditor`` / ``validate_draft_live`` optionally attach the live
    OpenCaseLaw ``/api/attest`` quote audit (opt-in; the offline verbatim
    check is always the floor).
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
    prov["provider_attempts"] = list(result.attempts or [])
    prov["citation_validation"] = {
        k: result.validation_report.get(k)
        for k in ("mode", "api_base", "hallucinated_ids", "verified_ids", "unverified_ids")
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

    package = package_answer(result, findings, bundle, quote_auditor=quote_auditor)
    if validate_draft_live:
        prov["draft_source_validation"] = _live_draft_validation(result, bundle)
    audited = apply_to_product_bundle(product_bundle, package, findings, provenance=prov)
    return audited


def _live_draft_validation(result: ProviderResult, bundle: DecisionBundle) -> Optional[Dict[str, Any]]:
    """Optional live ``POST /api/attest`` audit of the surfaced answer prose."""
    from .opencaselaw import OpenCaseLawAttestor

    attestor = OpenCaseLawAttestor(enabled=True)
    res = attestor.attest_draft(result.answer or "", audit_quotes=True)
    return {
        "endpoint": res.endpoint,
        "verified": res.verified,
        "verdict": res.verdict,
        "error": res.error,
        "evidence": res.evidence,
    }


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
