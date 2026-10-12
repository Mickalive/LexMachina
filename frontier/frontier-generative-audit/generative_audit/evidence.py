"""Source-checking of adversarial evidence quotes (defect repair, cycle 38181577763).

The adversarial pass asks the model for *short verbatim excerpts*.  A model
can still paraphrase or invent a quote; before cycle 38181577763 such a quote
was copied verbatim into product-visible ``decisions[*].counter_evidence``
with the finding's low uncertainty — i.e. the product would have displayed
fabricated source text as if it came from the decision.

This module closes that path:

* every ``evidence_refs`` entry is checked against the cited decision's
  retrieved bundle text (unicode-normalised verbatim substring);
* quotes that cannot be located are **rejected** — they never reach
  ``counter_evidence``;
* a finding whose quotes all fail the check is **downgraded**: its
  uncertainty is raised to at least ``DOWNGRADED_MIN_UNCERTAINTY`` and it is
  flagged ``evidence_backed=false`` (the finding itself stays visible — the
  product must never hide a possible counter-authority);
* the whole check is recorded in ``provenance.generative_audit``.

The check is always offline and deterministic.  When live OpenCaseLaw
attestation is enabled, quotes can additionally be audited by the service's
``POST /api/attest`` ``audit_quotes`` ledger (optional, injectable).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .adversarial import AdversarialFinding
from .source_packing import DecisionBundle

#: Unicode hyphens models substitute inside quotes/IDs.
_HYPHEN_TRANSLATION = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u2043"})

#: Internal (non-quote) evidence strings produced by the status merge.
NON_QUOTE_REFS = {"cited in generated answer"}

#: Shortest normalised quote length that can count as evidence.
MIN_QUOTE_CHARS = 8

#: A finding with no verifiable quote cannot claim high confidence.
DOWNGRADED_MIN_UNCERTAINTY = 0.95

#: Unicode ellipsis / three-dot placeholders a model may insert in a quote.
_ELLIPSIS = ("\u2026", "...")


def normalize_quote(text: Any) -> str:
    """Normalise a quote for verbatim matching.

    NFKC → hyphen fold → whitespace collapse → strip quotes/dashes → casefold.
    """
    if text is None:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = s.translate(_HYPHEN_TRANSLATION)
    s = re.sub(r"\s+", " ", s)
    s = s.strip().strip("\"'`\u00ab\u00bb\u201c\u201d\u2018\u2019\u2013\u2014- ")
    return s.casefold()


def is_quote_ref(ref: Any) -> bool:
    """True when ``ref`` is a purported source quote (not an internal marker)."""
    return bool(ref) and str(ref).strip() not in NON_QUOTE_REFS


def quote_in_source(quote: Any, source_text: Any) -> bool:
    """True when the (normalised) quote occurs verbatim in ``source_text``.

    Ellipsised quotes ("first part… second part") must have every segment
    present.  Quotes shorter than :data:`MIN_QUOTE_CHARS` cannot be verified
    and therefore return False (the OCL service likewise skips short quotes).
    """
    nq = normalize_quote(quote)
    if not nq:
        return False
    segments = [seg.strip() for seg in re.split("|".join(re.escape(e) for e in _ELLIPSIS), nq)]
    segments = [seg for seg in segments if seg]
    if not segments:
        return False
    if any(len(seg) < MIN_QUOTE_CHARS for seg in segments):
        return False
    haystack = normalize_quote(source_text)
    if not haystack:
        return False
    return all(seg in haystack for seg in segments)


@dataclass
class EvidenceCheckResult:
    """Per-finding outcome of the source check."""

    decision_id: str
    verified_refs: List[str] = field(default_factory=list)
    rejected_refs: List[str] = field(default_factory=list)
    evidence_backed: bool = False
    downgraded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "verified_refs": list(self.verified_refs),
            "rejected_refs": list(self.rejected_refs),
            "evidence_backed": self.evidence_backed,
            "downgraded": self.downgraded,
        }


def source_check_finding(
    finding: AdversarialFinding, source_text: Any
) -> EvidenceCheckResult:
    """Check one finding's quotes against the cited decision's text."""
    verified: List[str] = []
    rejected: List[str] = []
    for ref in finding.evidence_refs:
        if not is_quote_ref(ref):
            continue
        if quote_in_source(ref, source_text):
            verified.append(ref)
        else:
            rejected.append(ref)
    has_refs = any(is_quote_ref(r) for r in finding.evidence_refs)
    backed = bool(verified) and not rejected if has_refs else False
    # A finding with no quote at all is not evidence-backed either; it is
    # simply unverifiable (kept visible, high uncertainty).
    if not has_refs:
        backed = False
    return EvidenceCheckResult(
        decision_id=finding.decision_id,
        verified_refs=verified,
        rejected_refs=rejected,
        evidence_backed=backed,
        downgraded=has_refs and not verified,
    )


def source_check_findings(
    findings: List[AdversarialFinding],
    bundle: DecisionBundle,
    quote_auditor: Optional[Callable[[str, str], Optional[bool]]] = None,
) -> Tuple[List[AdversarialFinding], Dict[str, Any]]:
    """Source-check every finding; return checked copies + a provenance report.

    ``quote_auditor(decision_id, quote) -> bool | None`` is an optional live
    hook (OpenCaseLaw ``audit_quotes``).  ``None`` means inconclusive and
    never upgrades a locally rejected quote: the offline check is the floor.

    The input findings are not mutated.
    """
    by_id = bundle.by_id()
    checked: List[AdversarialFinding] = []
    per_finding: List[Dict[str, Any]] = []
    refs_checked = refs_verified = refs_rejected = 0
    live_verified = 0
    live_inconclusive = 0
    downgraded_ids: List[str] = []

    for finding in findings:
        source = by_id.get(finding.decision_id)
        source_text = source.text if source else ""
        result = source_check_finding(finding, source_text)

        # Optional live audit for locally rejected quotes (never upgrades
        # below the offline floor on its own: it can only confirm a quote
        # the service itself found verbatim).
        if quote_auditor is not None:
            for ref in list(result.rejected_refs):
                verdict = quote_auditor(finding.decision_id, ref)
                if verdict is True:
                    result.rejected_refs.remove(ref)
                    result.verified_refs.append(ref)
                    live_verified += 1
                elif verdict is None:
                    live_inconclusive += 1

        result.evidence_backed = bool(result.verified_refs) and not result.rejected_refs
        result.downgraded = bool(result.rejected_refs) and not result.verified_refs

        refs_checked += sum(1 for r in finding.evidence_refs if is_quote_ref(r))
        refs_verified += len(result.verified_refs)
        refs_rejected += len(result.rejected_refs)

        uncertainty = finding.uncertainty
        if result.downgraded:
            uncertainty = max(float(uncertainty), DOWNGRADED_MIN_UNCERTAINTY)
            downgraded_ids.append(finding.decision_id)

        checked.append(
            AdversarialFinding(
                decision_id=finding.decision_id,
                title=finding.title,
                reason=finding.reason,
                evidence_refs=list(result.verified_refs),
                uncertainty=uncertainty,
                confidence=finding.confidence,
            )
        )
        per_finding.append(
            {
                **result.to_dict(),
                "uncertainty_after": round(uncertainty, 4),
            }
        )

    report: Dict[str, Any] = {
        "method": "verbatim_quote_normalised_substring",
        "policy": (
            f"evidence_refs must occur verbatim (NFKC + hyphen-fold + "
            f"whitespace-collapse + casefold, min {MIN_QUOTE_CHARS} chars) in the "
            f"cited decision's retrieved bundle text; unverifiable quotes are "
            f"rejected before they reach counter_evidence and the finding's "
            f"uncertainty is raised to >= {DOWNGRADED_MIN_UNCERTAINTY}"
        ),
        "n_findings_checked": len(findings),
        "refs_checked": refs_checked,
        "refs_verified": refs_verified,
        "refs_rejected": refs_rejected,
        "n_downgraded": len(downgraded_ids),
        "downgraded_decision_ids": downgraded_ids,
        "findings": per_finding,
        "live_quote_audit": (
            None
            if quote_auditor is None
            else {"confirmed_after_local_reject": live_verified,
                  "inconclusive": live_inconclusive}
        ),
    }
    return checked, report


def verified_evidence_refs(refs: List[str], source_text: Any) -> Tuple[List[str], int]:
    """Boundary filter for ``counter_evidence``: keep only source-backed refs."""
    out: List[str] = []
    rejected = 0
    for ref in refs or []:
        if not is_quote_ref(ref):
            out.append(ref)
        elif quote_in_source(ref, source_text):
            out.append(ref)
        else:
            rejected += 1
    return out, rejected


__all__ = [
    "DOWNGRADED_MIN_UNCERTAINTY",
    "MIN_QUOTE_CHARS",
    "NON_QUOTE_REFS",
    "EvidenceCheckResult",
    "is_quote_ref",
    "normalize_quote",
    "quote_in_source",
    "source_check_finding",
    "source_check_findings",
    "verified_evidence_refs",
]
