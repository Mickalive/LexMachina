"""Abstain-and-disclose adoption of the accepted counter-anchor classifier.

Integration seam (factory direction v50, product obligation (4)): the accepted
Frontier component ``frontier-counter-anchor-classifier`` (team run
38964146628, outcome A, ACCEPTED) is a pure decision function that decides
whether a row's OWN cited passage licenses the counter label the product
already proposed under the frozen support rubric.  Product adopts it in
``abstain_and_disclose`` mode exactly as its INTEGRATION_CONTRACT requires:

* an emitted label keeps the product's own ``counter_status`` (the component
  confirms a label, it never re-assigns a polarity the row did not carry);
* an abstained row stays visible with the explicit product marker
  ``counter_status="abstained_unevidenced"``, the component's deterministic
  per-reason ``counter_uncertainty`` and its ``reason_code`` recorded on the
  row — counted, never silently dropped;
* support/among-emitted and yield are published SIDE BY SIDE in
  ``provenance.counter_label_gate`` so the yield/support trade cannot be
  hidden.

Two ceilings this module must never breach:

1. It never asserts that a specific decision IS supporting, contrary or
   limiting.  The frozen ``forbidden_construction_patterns`` of the accepted
   team are machine-checked against every artifact this module writes
   (``product/tests/test_counter_label_gate.py``).
2. It never re-measures the frozen rubric.  Scoring label support is Frontier
   and Core Evaluation work; this adapter only *applies* the accepted
   component's decision and publishes counts.  The Frontier-measured support
   numbers are attached as attributed evidence, never as a product
   measurement of the current bundle.

Anchor profiles come only from the frozen ``RULES_LABEL.json``
(question_anchors, sha256 4457e971...) keyed by the bundle's ``qid`` (or by an
exact match on the bundle's query text against the frozen profile question).
A bundle with no frozen profile is run against the EMPTY profile, which makes
the component abstain by construction (``pivot_absent``): no frozen anchor
means no certification of support, and the abstention is disclosed rather than
papered over.  The adapter never authors new anchors.
"""
from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
# Vendored, byte-identical copy of the accepted Frontier component.  It lives
# under the product lane's own write scope (product/**): the core-lane workflow
# rejects any producer write outside product/, tests/product/, results/product/,
# reports/product/, state/product.json and data/product/.
COMPONENT_ROOT = REPO_ROOT / "product" / "vendor" / "counter_anchor_classifier"

if str(COMPONENT_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPONENT_ROOT))

from frontier_counter_anchor_classifier.counter_anchor_classifier import (  # noqa: E402
    LABEL_ABSTAIN,
    STATUS_TO_LABEL,
    decide_label,
)
from frontier_counter_anchor_classifier.vendored.rules import load_rules  # noqa: E402

#: Frozen rubric digest (factory direction v50 / accepted Frontier measurement).
#: Re-hashed before every use; a mismatch refuses to run instead of guessing.
FROZEN_RULES_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"

#: The product-visible abstain marker (INTEGRATION_CONTRACT.abstained_row_contract).
ABSTAINED_STATUS = "abstained_unevidenced"

#: The frozen scored population (RULES_LABEL.json rubric.scored_statuses).
#: The gate is applied to exactly this set; ``cited`` and every unlabelled
#: status are reported separately by the frozen rubric and stay untouched here.
SCORED_STATUSES = (
    "candidate-limiting",
    "candidate-contrary",
    "contrary_or_exception",
    "limiting",
)

#: Empty anchor profile: with no frozen PIVOT the component abstains on every
#: row (reason ``pivot_absent``).  Empty profile means "cannot certify", never
#: "certified".
EMPTY_PROFILE: dict[str, Any] = {
    "domain": [],
    "pivot": [],
    "expected_languages": [],
    "foreign_legal_area_fields": [],
}

CLAIM_CEILING = (
    "the component decides the SUPPORT of the counter labels as issued under the "
    "frozen rubric; it never asserts that any specific decision IS supporting, "
    "contrary or limiting. Abstained rows stay visible as explicitly-unevidenced "
    "rows and are counted, never dropped. Support-among-emitted and yield are "
    "published side by side."
)

#: Attributed Frontier measurement (HEAD_TO_HEAD.json, accepted team run
#: 38964146628) — attached as evidence about THAT population only.  It is not
#: a product measurement of any bundle this adapter touches.
FRONTIER_MEASURED = {
    "team_run_id": "38964146628",
    "measured_packet": "gate_packet/38839347028",
    "incumbent_support_rate": 0.07692307692307693,
    "incumbent_n_scored": 65,
    "incumbent_n_supported": 5,
    "candidate_support_rate_among_emitted": 1.0,
    "candidate_n_emitted": 5,
    "candidate_n_abstained": 60,
    "candidate_INVERTED": 0,
    "reproduced_byte_identical": True,
    "provenance": "results/product/counter_anchor_adoption/HEAD_TO_HEAD.json",
    "scope": "measured on the frozen packet population only; not a measurement of any other bundle",
}

_rules_cache: Any = None


def rules_path() -> Path:
    return COMPONENT_ROOT / "RULES_LABEL.json"


def load_frozen_rules():
    """Load RULES_LABEL.json, refusing any byte that is not the frozen one."""
    global _rules_cache
    payload = rules_path().read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != FROZEN_RULES_SHA256:
        raise RuntimeError(
            "frozen RULES_LABEL.json digest mismatch: "
            f"expected {FROZEN_RULES_SHA256}, got {digest}"
        )
    if _rules_cache is None or _rules_cache.sha256 != digest:
        _rules_cache = load_rules(str(rules_path()))
    return _rules_cache


def anchor_profile_for(bundle: dict, rules=None) -> tuple[str | None, dict, str]:
    """Return ``(qid, profile, status)``; status is ``frozen`` or ``absent``."""
    rules = rules or load_frozen_rules()
    anchors = rules.data.get("question_anchors") or {}
    qid = bundle.get("qid")
    if qid and qid in anchors:
        return str(qid), dict(anchors[qid]), "frozen"
    # Deterministic exact-text fallback: the frozen profiles carry the source
    # question text (anchor_authoring_provenance: bundle.query is a source).
    query = str(bundle.get("query") or "").strip().casefold()
    if query:
        for key in sorted(anchors):
            if str(anchors[key].get("question") or "").strip().casefold() == query:
                return key, dict(anchors[key]), "frozen"
    return (str(qid) if qid else None), dict(EMPTY_PROFILE), "absent"


def _component_row(decision: dict) -> dict[str, Any]:
    """Map a product decision row onto the component's row_fields contract."""
    return {
        "decision_id": str(decision.get("decision_id") or ""),
        "counter_status": str(decision.get("counter_status") or ""),
        "counter_evidence": str(decision.get("counter_evidence") or ""),
        "language": str(decision.get("language") or ""),
        "rank": decision.get("rank"),
        "title": str(decision.get("title") or ""),
        "regeste": str(decision.get("regeste") or ""),
        "legal_area": str(decision.get("legal_area") or ""),
    }


def apply_counter_label_gate(bundle: dict, *, enabled: bool = True) -> dict:
    """Apply the accepted component to every scored counter label of ``bundle``.

    Returns a NEW bundle.  Rows whose status is not in the frozen scored set
    (``none``, ``cited``, ``unclassified``, already-abstained rows, ...) are
    untouched.  Geometry is never read or written.
    """
    if not enabled:
        out = copy.deepcopy(bundle)
        out.setdefault("provenance", {})["counter_label_gate"] = {
            "component": "frontier-counter-anchor-classifier/decide_label",
            "enabled": False,
            "note": "gate disabled by caller; labels are the incumbent's own",
        }
        return out

    rules = load_frozen_rules()
    qid, profile, profile_status = anchor_profile_for(bundle, rules)
    out = copy.deepcopy(bundle)

    n_proposed = n_emitted = n_abstained = 0
    abstention_reasons: dict[str, int] = {}
    decisions = out.get("decisions") or []

    for decision in decisions:
        status = str(decision.get("counter_status") or "")
        if status not in SCORED_STATUSES:
            continue
        n_proposed += 1
        verdict = decide_label(_component_row(decision), rules, profile)
        anchor = {
            "abstained": bool(verdict.abstained),
            "reason_code": verdict.reason_code,
            "uncertainty": verdict.uncertainty,
            "label_confirmed": verdict.label,
            "proposed_status": status,
            "anchor_profile_qid": qid,
            "anchor_profile_status": profile_status,
        }
        decision["counter_label_anchor"] = anchor
        if verdict.abstained:
            n_abstained += 1
            abstention_reasons[verdict.reason_code] = (
                abstention_reasons.get(verdict.reason_code, 0) + 1
            )
            decision["counter_status"] = ABSTAINED_STATUS
            decision["counter_uncertainty"] = verdict.uncertainty
            # The row's own cited passage is kept so a jurist can read it; the
            # evidence-VERIFIED flag is false because the passage did not
            # license the label under the frozen rubric.
            decision["counter_evidence"] = verdict.cited_sentence
            decision["counter_evidence_verified"] = False
        else:
            n_emitted += 1
            # Emitted: the component confirms the product's own label.  The
            # row keeps its counter_status and its audit-seam verification;
            # the component's deterministic uncertainty is published on the
            # anchor record rather than overwriting the audit seam's value.

    yield_rate = round(n_emitted / n_proposed, 6) if n_proposed else None
    support_among_emitted = None  # never computed here: that is a rubric score
    out.setdefault("provenance", {})["counter_label_gate"] = {
        "component": "frontier-counter-anchor-classifier/decide_label",
        "component_version": "team_run_38964146628_outcome_A",
        "adopt_mode": "abstain_and_disclose",
        "enabled": True,
        "frozen_rules_sha256": FROZEN_RULES_SHA256,
        "frozen_rules_rehash_verified": True,
        "scored_statuses": list(SCORED_STATUSES),
        "anchor_profile": {
            "qid": qid,
            "status": profile_status,
            "note": (
                "profile read from the frozen RULES_LABEL.json question_anchors block"
                if profile_status == "frozen"
                else "no frozen anchor profile for this query: the component abstains by "
                     "construction (pivot_absent); anchors are never authored at runtime"
            ),
        },
        "n_proposed_labels": n_proposed,
        "n_emitted": n_emitted,
        "n_abstained": n_abstained,
        "abstention_reasons": dict(sorted(abstention_reasons.items())),
        "yield": yield_rate,
        "support_rate_among_emitted": support_among_emitted,
        "support_rate_computed_here": False,
        "side_by_side": {
            "n_proposed_labels": n_proposed,
            "n_emitted": n_emitted,
            "n_abstained": n_abstained,
            "yield": yield_rate,
        },
        "frontier_measured_reference": FRONTIER_MEASURED,
        "claim_ceiling": CLAIM_CEILING,
        "forbidden_construction_patterns_source":
            "results/product/frontier_verdicts/ACCEPTED_frontier-served-packet-falsification_38880639079.json",
    }
    return out


__all__ = [
    "ABSTAINED_STATUS",
    "CLAIM_CEILING",
    "EMPTY_PROFILE",
    "FROZEN_RULES_SHA256",
    "FRONTIER_MEASURED",
    "SCORED_STATUSES",
    "anchor_profile_for",
    "apply_counter_label_gate",
    "load_frozen_rules",
    "rules_path",
]
