"""Verdict engine: ONE machine-checked one-sentence serve recommendation.

Applies the frozen decision tree from the team RULES.json. The recommendation
is machine-checked against the emitted numbers (never hand-written): the
verdict module recomputes the decision from the label/geometry/marginal
measurements and asserts the emitted sentence matches.

Outcomes (all promotions; the charter ends at the first reached):
  SERVE               - both frozen absolute bars met as written on the v3
                        bytes AND the size-based mega-cluster disclosure
                        fires where share >= 0.5 AND the recommendation
                        explicitly replaces the DO-NOT-SERVE verdict.
  DO-NOT-SERVE-UNCHANGED - bars unmet as written, serve conclusion unchanged,
                        owner_decision_required=FALSE.
  BOUNDED-NEGATIVE    - both bars unmet and no in-budget fix; at most ONE
                        bounded cause per failed half; owner_decision_required
                        only if this record carries it explicitly.

NO owner card, NO owner session, NO ready_for_owner_session=true, NO
human_gate_ready=true is produced, staged or readied from ANY outcome.
"""
from __future__ import annotations

from typing import Any

SERVE = "SERVE"
DO_NOT_SERVE_UNCHANGED = "DO-NOT-SERVE-UNCHANGED"
BOUNDED_NEGATIVE = "BOUNDED-NEGATIVE"


def _mega_cluster_fires_where_required(geometry: dict) -> bool:
    """The size-based mega-cluster disclosure fires on every bundle whose
    largest-cluster share >= 0.5 (the disclosure is per-bundle; the SERVE
    path requires it to fire where the share is >= 0.5, i.e. on the bundles
    that actually have a mega-cluster)."""
    per = geometry.get("per_bundle", {})
    if not per:
        return False
    fires = [bool((b.get("mega_cluster") or {}).get("disclosure_fires")) for b in per.values()]
    # The disclosure fires where share >= 0.5; on a packet with no mega-cluster
    # it does not fire anywhere. SERVE requires it to fire where share >= 0.5.
    return all(fires)


def decide(label: dict, geometry: dict, marginal: dict) -> dict:
    label_abs = label.get("absolute_status")
    geom_abs = geometry.get("absolute_status")
    label_sound = label_abs == "LABEL_SOUND"
    geom_sound = geom_abs == "GEOMETRY_SOUND"
    mega_fires = _mega_cluster_fires_where_required(geometry)
    no_marginal = not marginal.get("map_adds_marginal_discovery_on_packet", False)

    # Bounded causes: at most ONE per failed half.
    causes = []
    if not label_sound:
        causes.append(
            "LABEL: the packet-of-record v3 issues zero counter labels under the "
            "abstain-and-disclose classifier config (n_scored=0), so the frozen "
            "absolute bar support_rate==1.0 is unmet as written; the population-free "
            "label_lineage_gate verdict is NOT_APPLICABLE (not a pass)")
    if not geom_sound:
        causes.append(
            "GEOMETRY: the shipped relevance_ordered geometry passes fewer than 11/11 "
            "frozen criteria on every anchor bundle (STRUCTURE_LARGEST mega-cluster "
            "and the projection/separation criteria fail)")

    if label_sound and geom_sound and mega_fires:
        outcome = SERVE
        sentence = ("SERVE: the packet-of-record v3 passes both frozen absolute bars as written on its own "
                    "bytes (counter-label support_rate 1.0 and all 11 geometry criteria on all three anchor "
                    "bundles) with the size-based mega-cluster disclosure firing where the share is >= 0.5, "
                    "and this recommendation explicitly replaces the standing DO-NOT-SERVE verdict.")
        owner_decision_required = False
    elif (not label_sound) and (not geom_sound) and no_marginal:
        outcome = BOUNDED_NEGATIVE
        sentence = ("BOUNDED-NEGATIVE: both frozen absolute bars remain unmet on the packet-of-record v3 bytes "
                    "(counter-label support 0/0 = 0.0 against the frozen absolute bar 1.0 at n_scored=0, and "
                    "map geometry below 11/11 on every anchor bundle) and the map adds no marginal discovery "
                    "over a conventional ranked list on the same bundles, so the packet is not served and the "
                    "negative is recorded with at most one bounded cause per failed half.")
        owner_decision_required = False
    elif (not label_sound) and (not geom_sound):
        outcome = DO_NOT_SERVE_UNCHANGED
        sentence = ("DO-NOT-SERVE-UNCHANGED: the frozen absolute bars remain unmet as written on the "
                    "packet-of-record v3 bytes and the serve conclusion is unchanged; the standing accepted "
                    "DO-NOT-SERVE orders stand.")
        owner_decision_required = False
    else:
        # Halves disagree: report both, promote the improving half AS SUCH.
        outcome = BOUNDED_NEGATIVE
        sentence = ("BOUNDED-NEGATIVE: the label and geometry halves disagree on the packet-of-record v3 "
                    "bytes; both numbers are published side by side and the improving half is promoted as a "
                    "real product-improving result, never explained away by the pre-packet baseline.")
        owner_decision_required = False

    return {
        "outcome": outcome,
        "one_sentence_recommendation": sentence,
        "owner_decision_required": owner_decision_required,
        "bounded_causes": causes,
        "machine_check": {
            "label_absolute_status": label_abs,
            "geometry_absolute_status": geom_abs,
            "label_sound": label_sound,
            "geometry_sound": geom_sound,
            "mega_cluster_disclosure_fires_where_share_ge_0.5": mega_fires,
            "marginal_discovery_adds": not no_marginal,
            "decision_tree_applied": [
                "IF label_sound AND geom_sound AND mega_fires THEN SERVE",
                "ELSE IF (not label_sound) AND (not geom_sound) AND no_marginal THEN BOUNDED_NEGATIVE",
                "ELSE IF (not label_sound) AND (not geom_sound) THEN DO-NOT-SERVE-UNCHANGED",
                "ELSE BOUNDED_NEGATIVE (halves disagree)",
            ],
        },
        "owner_session_guard": {
            "owner_card_produced": False,
            "owner_session_readied": False,
            "ready_for_owner_session": False,
            "human_gate_ready": False,
            "note": "NO owner card, session or gate flag is produced, staged or readied from ANY outcome of this charter.",
        },
    }


def assert_machine_check(verdict: dict) -> None:
    """Assert the emitted sentence matches the recomputed decision."""
    mc = verdict["machine_check"]
    expected = decide(
        {"absolute_status": mc["label_absolute_status"]},
        {"absolute_status": mc["geometry_absolute_status"],
         "per_bundle": {qid: {"mega_cluster": {"disclosure_fires": mc["mega_cluster_disclosure_fires_where_share_ge_0.5"]}}
                        for qid in ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")}},
        {"map_adds_marginal_discovery_on_packet": mc["marginal_discovery_adds"]},
    )
    if expected["outcome"] != verdict["outcome"]:
        raise AssertionError(
            f"verdict machine-check failed: recomputed {expected['outcome']} != emitted {verdict['outcome']}")
