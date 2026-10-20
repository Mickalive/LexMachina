"""Minimal in-budget emission repair: promote gate-passed heuristic proposals.

The adversarial retrieval stage already computed, per row, a gate-passed
heuristic proposal (``adversarial_retrieval_signal.heuristic_status`` +
``.evidence``, a verbatim sentence of the row's own text).  The accepted
classifier's entire design is abstain-and-disclose: it CONFIRMS or ABSTAINS
on a row's own proposed label under the frozen rubric.  This module is the
minimal, offline, deterministic handoff the missing LLM reviewer was supposed
to provide: it copies the already-verified heuristic proposal into the scored
status fields so the accepted classifier can decide on it.

The classifier is the safety net: any proposal whose evidence fails the
frozen emission gate becomes a COUNTED abstention, never a shipped label.
"""

from __future__ import annotations

import copy
from typing import Any

#: The repair's own identity, written into every mutated row and into the
#: bundle provenance so any consumer can see exactly which handoff ran.
REPAIR_ID = "heuristic_proposal_promotion_v1"

#: Minimum evidence length for a heuristic proposal to be promoted.  Frozen
#: in RULES.json; never tuned after a number is seen.
MIN_EVIDENCE_CHARS = 40

#: Deterministic uncertainty for a promoted proposal (not an emitted label).
PROPOSAL_UNCERTAINTY = 0.5


def _is_scored(status: str, scored_statuses: tuple[str, ...]) -> bool:
    return status in scored_statuses


def promote_heuristic_proposals(
    bundle: dict,
    *,
    scored_statuses: tuple[str, ...],
    min_evidence_chars: int = MIN_EVIDENCE_CHARS,
) -> dict[str, Any]:
    """Return a NEW bundle with gate-passed heuristic proposals promoted.

    Never touches geometry, ranks, clusters, existing scored labels, or the
    accepted classifier.  Pure function of (bundle bytes, this spec).
    """
    out = copy.deepcopy(bundle)
    promoted: list[dict[str, Any]] = []
    for d in out.get("decisions") or []:
        status = str(d.get("counter_status") or "")
        if _is_scored(status, scored_statuses):
            continue
        sig = d.get("adversarial_retrieval_signal") or {}
        heur = str(sig.get("heuristic_status") or "")
        evidence = str(sig.get("evidence") or "")
        if not heur or len(evidence) < min_evidence_chars:
            continue
        d["counter_status"] = heur
        d["counter_evidence"] = evidence[:400]
        d["counter_evidence_verified"] = False
        d["counter_uncertainty"] = PROPOSAL_UNCERTAINTY
        d["counter_proposal_source"] = REPAIR_ID
        d["counter_proposal_signal"] = {
            "heuristic_status": sig.get("heuristic_status"),
            "evidence": sig.get("evidence"),
            "markers": list(sig.get("markers") or []),
        }
        promoted.append({
            "decision_id": str(d.get("decision_id") or ""),
            "proposed_status": heur,
            "evidence_len": len(evidence),
        })

    prov = out.setdefault("provenance", {})
    prov["counter_label_emission_repair"] = {
        "repair_id": REPAIR_ID,
        "applied": True,
        "min_evidence_chars": min_evidence_chars,
        "n_promoted": len(promoted),
        "promoted": sorted(promoted, key=lambda r: r["decision_id"]),
        "claim_ceiling": (
            "Promoted rows carry the adversarial stage's own gate-passed "
            "heuristic proposal as a COUNTER PROPOSAL for the accepted "
            "classifier to confirm-or-abstain.  This module never asserts "
            "that any decision IS supporting/contrary/limiting."
        ),
    }
    return out


__all__ = [
    "MIN_EVIDENCE_CHARS",
    "PROPOSAL_UNCERTAINTY",
    "REPAIR_ID",
    "promote_heuristic_proposals",
]
