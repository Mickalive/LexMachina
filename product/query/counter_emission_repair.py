#!/usr/bin/env python3
"""Product-owned intake seam for ``frontier-counter-label-emission`` (Outcome A).

Why this module exists
----------------------
Factory direction v61, product ordered work (2):

    *"when that team's outcome is independently accepted, harvest it through
    the append-only intake pattern (as with product/query/serve_verdict.py) and
    re-run packet admission - this lane NEVER re-derives a frozen threshold,
    NEVER tunes the accepted classifier config to manufacture support, and NEVER
    asserts any case is supporting/contrary/limiting without the rubric's own
    sentence evidence."*

The Frontier team ``frontier-counter-label-emission`` (charter v1, team run
``39422328377``, independent audit ``CYCLE_39426324296_GATE.json`` gate=PASS /
``safe_to_integrate=true``, verification run ``39426324296``, promotion outcome
``A_EMISSION_RECOVERED``) measured why the shipped adversarial stage emitted
ZERO scored counter rows on the packet-of-record v3 bundles and built a minimal,
offline, deterministic repair.  Its ``INTEGRATION_CONTRACT.json`` names the exact
integration point:

    product/query/pipeline.py enrich_query_bundle, BETWEEN
    adversarial_retrieval_pass() and apply_anchor_labels()

This module is that seam.  It vendors the accepted repair byte-identically
(``product/vendored/frontier_counter_label_emission/PROVENANCE.json``) and
exposes ``apply_counter_emission_repair`` for the pipeline.  The repair is a
pure function of the bundle's own bytes: it copies the adversarial stage's
already gate-passed heuristic proposal (``adversarial_retrieval_signal``) into
the scored ``counter_status`` fields so the accepted abstain-and-disclose
classifier (``product/query/counter_anchor.py``) can confirm-or-abstain on it.

What this module never does
---------------------------
* never re-derives a frozen rubric, bar or threshold;
* never re-scores, re-tunes or re-assigns a counter label (the classifier
  decides; this seam only feeds it the proposal);
* never asserts that any specific decision IS supporting/contrary/limiting;
* never touches geometry, ranks, clusters, relations or an already-scored row;
* never sets ``human_gate_ready`` / ``ready_for_owner_session`` or an owner card.

Claim ceiling (binds every product artifact, copied from the accepted audit's
``claim_ceiling``):

    This seam measures and repairs the EMISSION PATH that feeds the accepted
    classifier. It NEVER asserts that any decision IS supporting/contrary/
    limiting. Support-among-issued, the abstention count and the yield are
    published together. The frozen absolute bar remains unmet as written and is
    never re-derived. No serve recommendation is produced.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDORED_ROOT = REPO_ROOT / "product" / "vendored" / "frontier_counter_label_emission"

#: Product-owned snapshot of the accepted Frontier measurement (committed; the
#: seam and admission never depend on the CI mount being present).
INTAKE_PATH = (REPO_ROOT / "results" / "product" / "frontier_verdicts"
               / "frontier-counter-label-emission_intake.json")

#: Acceptance provenance for every artifact this seam writes.
ADOPTION = {
    "component": "frontier-counter-label-emission",
    "charter_version": 1,
    "team_run_id": "39422328377",
    "audit_of_record": ("results/audit/frontier/frontier-counter-label-emission/"
                        "CYCLE_39426324296_GATE.json"),
    "audit_gate": "PASS",
    "safe_to_integrate": True,
    "audit_run_id": "39426324296",
    "verification_run_id": "39426324296",
    "promoted_in_commit": "44d4904becb6faa2f6deef896f00c071279c0067",
    "accept_branch": "lab/frontier/frontier-counter-label-emission",
    "accept_branch_head": "437c71172f86e21e6c3a461691d976cb60d09552",
    "promotion_outcome": "A_EMISSION_RECOVERED",
    "repair_id": "heuristic_proposal_promotion_v1",
    "integration_point": (
        "product/query/pipeline.py enrich_query_bundle, between "
        "adversarial_retrieval_pass() and apply_anchor_labels()"
    ),
}

SCHEMA = "product-counter-emission-repair-intake/1"

#: The accepted repair's own identity (frozen in the accepted RULES.json).
REPAIR_ID = "heuristic_proposal_promotion_v1"

#: Claim ceiling copied verbatim from the accepted audit gate.
CLAIM_CEILING = (
    "This seam measures and repairs the EMISSION PATH that feeds the accepted "
    "classifier. It NEVER asserts that any decision IS supporting/contrary/"
    "limiting. Support-among-issued, the abstention count and the yield are "
    "published together. The frozen absolute bar remains unmet as written and is "
    "never re-derived. No serve recommendation is produced."
)

#: The repair's own minimum evidence length (frozen in the accepted RULES.json).
MIN_EVIDENCE_CHARS = 40


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import_repair():
    """Import the vendored accepted repair lazily (keeps startup light)."""
    if str(VENDORED_ROOT) not in sys.path:
        sys.path.insert(0, str(VENDORED_ROOT))
    from frontier_counter_label_emission.emission import promote_heuristic_proposals  # noqa: E402

    return promote_heuristic_proposals


def verify_vendored() -> dict[str, Any]:
    """Prove the vendored repair still matches the accepted source, fail-closed.

    Any digest mismatch raises ``ValueError``: a re-frozen/edited component
    invalidates the measurement, so the seam refuses to run rather than silently
    applying a drifted repair.
    """
    prov_path = VENDORED_ROOT / "PROVENANCE.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    observed: dict[str, str | None] = {}
    mismatches: list[str] = []
    for rel, meta in (prov.get("vendored_files") or {}).items():
        path = VENDORED_ROOT / rel
        digest = _sha256_file(path) if path.exists() else None
        observed[rel] = digest
        if digest != meta.get("sha256"):
            mismatches.append(f"{rel}: {digest} != {meta.get('sha256')}")
    if mismatches:
        raise ValueError(
            "vendored frontier-counter-label-emission drifted from its accepted "
            f"source: {mismatches}; an edited component invalidates the run"
        )
    return {"ok": True, "component": prov["component"], "observed": observed}


def apply_counter_emission_repair(
    bundle: dict,
    *,
    scored_statuses: tuple[str, ...] | None = None,
    min_evidence_chars: int = MIN_EVIDENCE_CHARS,
) -> dict[str, Any]:
    """Return a NEW bundle with gate-passed heuristic proposals promoted.

    This is the product seam the accepted integration contract names.  It calls
    the vendored ``promote_heuristic_proposals`` read-only and merges the
    product-owned provenance so every consumer can see exactly which handoff
    ran.  It is a pure function of the bundle bytes plus the repair spec: it
    never touches geometry, ranks, clusters, relations or an already-scored row.
    """
    from .counter_anchor import SCORED_STATUSES as _SCORED

    statuses = tuple(scored_statuses) if scored_statuses is not None else _SCORED
    verify_vendored()
    promote = _import_repair()
    out = promote(bundle, scored_statuses=statuses, min_evidence_chars=min_evidence_chars)

    repair_prov = (out.get("provenance") or {}).get("counter_label_emission_repair") or {}
    prov = out.setdefault("provenance", {}).setdefault("counter_emission_repair", {})
    prov.update({
        "component": ADOPTION["component"],
        "charter_version": ADOPTION["charter_version"],
        "team_run_id": ADOPTION["team_run_id"],
        "audit_gate": ADOPTION["audit_gate"],
        "audit_run_id": ADOPTION["audit_run_id"],
        "promotion_outcome": ADOPTION["promotion_outcome"],
        "repair_id": ADOPTION["repair_id"],
        "integration_point": ADOPTION["integration_point"],
        "applied": True,
        "n_promoted": repair_prov.get("n_promoted", 0),
        "min_evidence_chars": min_evidence_chars,
        "scored_statuses": list(statuses),
        "claim_ceiling": CLAIM_CEILING,
    })
    return out


def harvest_intake() -> dict[str, Any]:
    """Return the product-owned intake snapshot of the accepted measurement.

    The snapshot is committed and self-contained, so admission and disclosure
    can consume it without the CI mount.  It carries the accepted audit gate and
    the three-number publication (n_scored / n_abstained / support-among-issued /
    yield) but re-derives no threshold.
    """
    try:
        return json.loads(INTAKE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "schema": SCHEMA,
            "record_type": "PRODUCT_OWNED_COUNTER_EMISSION_INTAKE",
            "status": "MISSING_INTAKE_SNAPSHOT",
            "accepted": False,
            "evidence_tier": "UNTESTED",
            "claim_ceiling": (
                "No accepted emission intake snapshot is committed yet; the "
                "adversarial emission repair is not applied and no claim is made."
            ),
        }


__all__ = [
    "ADOPTION",
    "CLAIM_CEILING",
    "INTAKE_PATH",
    "MIN_EVIDENCE_CHARS",
    "REPAIR_ID",
    "SCHEMA",
    "apply_counter_emission_repair",
    "harvest_intake",
    "verify_vendored",
]
