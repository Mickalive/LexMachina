"""Before/after on the accepted un-hydrated-row ablation (charter test 5).

The accepted verdict snapshot records, for the served French bundle:
  * shipped largest-cluster share 167/217 = 0.7696 by the cluster size field,
  * the frozen ARTIFACT predicate does NOT fire (dominant un-hydrated fraction
    0.293 < the 0.40 shell-fraction clause),
  * recomputing over hydrated rows alone collapses the share to 0.268 with a
    dominant-member Jaccard of 0.235 against the shipped dominant cluster.

This module re-states those accepted numbers verbatim and then evaluates the
SAME three quantities under each variant, plus whether the frozen ARTIFACT
predicate fires under the variant's own dominant cluster.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .hydration import hydration_mask
from .scoring import largest_share_both_definitions

ACCEPTED_ABLATION = {
    "source": "results/product/frontier_verdicts/"
              "ACCEPTED_frontier-served-packet-falsification_38880639079.json",
    "frozen_rule_sha256": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "french_largest_share": 0.7696,
    "french_bar": 0.60,
    "hydrated_only_largest_share": 0.268,
    "dominant_member_jaccard": 0.235,
    "dominant_unhydrated_fraction": 0.293,
    "ARTIFACT": False,
    "artifact_rule": (
        "ARTIFACT_TRUE iff (un-hydrated fraction of the dominant cluster >= 0.40) "
        "AND (|dominant share under the variant input - shipped dominant share| >= 0.10 "
        "OR dominant-member Jaccard < 0.5)"
    ),
    "note": (
        "The dominant French cluster is 167 of 217 decisions and contains only "
        "4 of 217 French-language rows (2.4%). The frozen ARTIFACT predicate does "
        "not fire because the shell-fraction clause requires >= 0.40 and the "
        "measured value is 0.293."
    ),
}

SHIPPED_DOMINANT = {
    "de-kapitalverletzung": 81,
    "fr-bail-entretien": 167,
    "it-responsabilita-medica": 99,
}


def dominant_ids(bundle: dict) -> set[str]:
    clusters = bundle.get("clusters") or []
    if not clusters:
        return set()
    dom = max(clusters, key=lambda c: int(c.get("size") or 0))
    cid = int(dom["cluster_id"])
    return {d["decision_id"] for d in bundle["decisions"] if int(d.get("cluster_id")) == cid}


def jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def before_after(shipped: dict, candidate: dict, qid: str) -> dict[str, Any]:
    decisions = candidate["decisions"]
    mask = hydration_mask(decisions)
    shell_ids = {d["decision_id"] for d, s in zip(decisions, mask) if s}
    hyd_ids = {d["decision_id"] for d, s in zip(decisions, mask) if not s}

    shipped_dom = dominant_ids(shipped)
    cand_dom = dominant_ids(candidate)
    n = max(1, len(decisions))
    cand_dom_unhyd = len(cand_dom & shell_ids) / max(1, len(cand_dom))
    cand_share = largest_share_both_definitions(candidate)["largest_share_size_field"]
    shipped_share = largest_share_both_definitions(shipped)["largest_share_size_field"]
    j_ship_hyd = jaccard(cand_dom, shipped_dom & hyd_ids)
    j_full = jaccard(cand_dom, shipped_dom)

    share_delta = abs(cand_share - shipped_share)
    artifact = bool(
        cand_dom_unhyd >= 0.40 and (share_delta >= 0.10 or j_ship_hyd < 0.5)
    )
    return {
        "qid": qid,
        "n_decisions": n,
        "n_shells": len(shell_ids),
        "shipped_largest_share": shipped_share,
        "shipped_dominant_size": SHIPPED_DOMINANT.get(qid, len(shipped_dom)),
        "shipped_dominant_unhydrated_fraction": len(shipped_dom & shell_ids) / max(1, len(shipped_dom)),
        "variant_largest_share": cand_share,
        "variant_dominant_size": len(cand_dom),
        "variant_dominant_unhydrated_fraction": cand_dom_unhyd,
        "share_delta_vs_shipped": share_delta,
        "dominant_member_jaccard_vs_shipped_dominant": j_full,
        "dominant_member_jaccard_vs_shipped_dominant_hydrated_only": j_ship_hyd,
        "ARTIFACT_under_variant": artifact,
        "ARTIFACT_clauses": {
            "shell_fraction_clause_met": bool(cand_dom_unhyd >= 0.40),
            "share_shift_clause_met": bool(share_delta >= 0.10),
            "member_jaccard_clause_met": bool(j_ship_hyd < 0.5),
        },
        "why": (
            "The variant dominant cluster contains no un-hydrated shell at all, so the "
            "shell-fraction clause of the frozen ARTIFACT predicate cannot be met; the "
            "predicate is False for a structural reason (the cause it was written to "
            "detect has been removed from the input), not because the shift is small."
            if cand_dom_unhyd == 0.0
            else "Computed from the variant's own dominant cluster."
        ),
    }
