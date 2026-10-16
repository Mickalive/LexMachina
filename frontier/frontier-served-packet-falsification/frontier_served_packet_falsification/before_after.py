"""BEFORE/AFTER pairing: served-packet results vs accepted pre-repair baselines.

Every baseline is marked PRE-REPAIR so no reader can mistake it for a
served-packet result. DIRECTION and DELTA are stated for each paired number.
No baseline is re-measured; it is quoted from the accepted audit-gated runs.
"""

from __future__ import annotations

from typing import Any

from . import (
    BASELINE_GEOMETRY_LARGEST_SHARES,
    BASELINE_GEOMETRY_PASS_COUNTS,
    BASELINE_GEOMETRY_RUN,
    BASELINE_LABEL_RUN,
    BASELINE_LABEL_SUPPORT_RATE_PRIMARY,
    BASELINE_LABEL_SUPPORT_RATE_SECONDARY,
    BASELINE_LABEL_VERDICT,
    BUNDLES,
)


def _direction(new: float | None, old: float | None, *, higher_is_better: bool) -> str | None:
    if new is None or old is None:
        return None
    if new == old:
        return "SAME"
    improved = new > old if higher_is_better else new < old
    return "IMPROVED" if improved else "REGRESSED"


def _delta(new: float | None, old: float | None) -> float | None:
    if new is None or old is None:
        return None
    return new - old


def build_before_after(label_half: dict[str, Any], geometry_half: dict[str, Any]) -> dict[str, Any]:
    """Pair every served-packet number with its accepted pre-repair baseline."""
    label_new_rate = label_half.get("support_rate")
    label_new_verdict = label_half.get("verdict")
    label_dir = _direction(label_new_rate, BASELINE_LABEL_SUPPORT_RATE_PRIMARY, higher_is_better=True)

    # Geometry per-bundle pass counts and largest shares
    geo_pairs = []
    for b in geometry_half.get("bundles", []):
        qid = b["qid"]
        old_pass = BASELINE_GEOMETRY_PASS_COUNTS.get(qid)
        new_pass = b.get("n_pass")
        old_share = BASELINE_GEOMETRY_LARGEST_SHARES.get(qid)
        new_share = (b.get("largest_share_both_definitions") or {}).get("largest_share_size_field")
        geo_pairs.append(
            {
                "qid": qid,
                "n_pass_before": old_pass,
                "n_pass_after": new_pass,
                "n_pass_delta": _delta(new_pass, old_pass),
                "n_pass_direction": _direction(new_pass, old_pass, higher_is_better=True),
                "largest_share_size_field_before": old_share,
                "largest_share_size_field_after": new_share,
                "largest_share_delta": _delta(new_share, old_share),
                "largest_share_direction": _direction(new_share, old_share, higher_is_better=False),
                "overall_before": "FAIL",
                "overall_after": b.get("overall"),
                "criteria_detail_before": "quoted from accepted run " + BASELINE_GEOMETRY_RUN,
                "criteria_detail_after": b.get("criteria"),
            }
        )

    label_before = {
        "run_id": BASELINE_LABEL_RUN,
        "pre_repair": True,
        "pre_repair_definition": (
            "A bundle produced without results/product/adversarial_retrieval/** present, "
            "i.e. an artifact of the accepted head that has no product/query/adversarial_retrieval.py."
        ),
        "verdict": BASELINE_LABEL_VERDICT,
        "support_rate_primary": BASELINE_LABEL_SUPPORT_RATE_PRIMARY,
        "n_scored_primary": 7,
        "support_rate_secondary": BASELINE_LABEL_SUPPORT_RATE_SECONDARY,
        "n_scored_secondary": 39,
        "independent_audit_gate": "PASS",
        "independent_audit": "results/audit/frontier/frontier-counter-label-integrity/CYCLE_38841035773_GATE.json",
        "note": (
            "PRE-REPAIR baseline. This is a statement about the 38799024807 gate packets and "
            "accepted live bundles, NOT about the served packet 38839347028."
        ),
    }
    label_after = {
        "run_id": "this-run",
        "pre_repair": False,
        "population": "served gate packet 38839347028 (65 issued counter labels)",
        "verdict": label_new_verdict,
        "support_rate": label_new_rate,
        "n_scored": label_half.get("n_scored"),
        "n_supported": label_half.get("n_supported"),
        "defect_classes": (label_half.get("overall") or {}).get("defect_classes"),
        "counter_evidence_verified_distribution": (
            label_half.get("overall") or {}
        ).get("counter_evidence_verified_distribution"),
        "n_empty_evidence_at_uncertainty_ge_0_95": (
            label_half.get("overall") or {}
        ).get("n_empty_evidence_at_uncertainty_ge_0_95"),
    }

    return {
        "schema": "frontier-served-packet-falsification/before-after/1",
        "label_half": {
            "before": label_before,
            "after": label_after,
            "direction_support_rate": label_dir,
            "delta_support_rate": _delta(label_new_rate, BASELINE_LABEL_SUPPORT_RATE_PRIMARY),
            "note": (
                "Both are scored under the SAME frozen rubric "
                "(rules_sha256 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608). "
                "The BEFORE population is the 38799024807 packet; the AFTER population is the "
                "served 38839347028 packet. A different population, the same bar."
            ),
        },
        "geometry_half": {
            "before": {
                "run_id": BASELINE_GEOMETRY_RUN,
                "pre_repair": True,
                "verdict": "FAIL 0/3 bundles",
                "pass_counts": BASELINE_GEOMETRY_PASS_COUNTS,
                "largest_cluster_shares": BASELINE_GEOMETRY_LARGEST_SHARES,
                "independent_audit_gate": "PASS",
                "independent_audit": "results/audit/frontier/frontier-map-semantics/CYCLE_38846038296_GATE.json",
                "accept_commit": "15362f68867a8127401fb9d99959f3e731087dc4",
                "note": (
                    "PRE-REPAIR baseline. Measured on the 38799024807 packet (134/131/132 decisions). "
                    "NOT a statement about the served packet 38839347028."
                ),
            },
            "after": {
                "run_id": "this-run",
                "pre_repair": False,
                "population": "served gate packet 38839347028 (214/217/211 decisions)",
                "verdict": geometry_half.get("verdict"),
                "n_bundles_pass": geometry_half.get("n_bundles_pass"),
                "per_bundle": geo_pairs,
            },
            "note": (
                "Same frozen rule "
                "(rules_sha256 a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633), "
                "different (later) packet. The baselines are quoted, never re-measured."
            ),
        },
        "mark_every_baseline_pre_repair": True,
    }
