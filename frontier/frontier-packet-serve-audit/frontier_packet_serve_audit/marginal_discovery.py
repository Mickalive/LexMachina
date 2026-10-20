"""Marginal-discovery measurement: map vs conventional ranked list.

Charter question (c): on these bytes, do the counter/contrary authorities the
MAP makes discoverable add anything a conventional ranked list over the SAME
already-loaded bundle would not already show near the top?

Frozen K and definition (from the team RULES.json, frozen before execution):
  K = 20 (the conventional top-20 named in the frozen RULES_LABEL reporting).
  The map's discoverable counter/contrary authorities are exactly the ISSUED
  counter rows (counter_status in scored_statuses).
  marginal_discovery_set = issued counter rows whose decision_id was absent
  from the initial-pool top-K (equivalently, whose least-ranked list position
  > K). Empty set => the map adds no marginal discovery on this packet.

Measured on the SAME already-loaded bundles for both views; no second
retrieval. Read-only, deterministic, stdlib only.
"""
from __future__ import annotations

from typing import Any

K = 20
SCORED_STATUSES = ("candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting")


def measure_bundle(bundle: dict[str, Any], k: int = K) -> dict:
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    n = len(decisions)
    # Ranked list: retrieval rank ascending, decision_id ascending (deterministic).
    by_rank = sorted(decisions, key=lambda d: (int(d.get("rank") or 10**9), str(d.get("decision_id") or "")))
    topk_ids = {d.get("decision_id") for d in by_rank[:k]}
    position = {d.get("decision_id"): i + 1 for i, d in enumerate(by_rank)}

    issued = [d for d in decisions if d.get("counter_status") in SCORED_STATUSES]
    rows = []
    for d in issued:
        did = d.get("decision_id")
        pos = position.get(did)
        absent = did not in topk_ids
        rows.append({
            "decision_id": did,
            "counter_status": d.get("counter_status"),
            "rank": d.get("rank"),
            "least_ranked_list_position": pos,
            "absent_from_initial_pool_topK": bool(absent),
            "counter_only_in_map_invisible_in_list": bool(absent),  # issued (map-discoverable) AND position > K
        })
    marginal = [r for r in rows if r["absent_from_initial_pool_topK"]]
    return {
        "K": k,
        "n_decisions": n,
        "n_issued_counter_rows": len(issued),
        "marginal_discovery_set": marginal,
        "n_marginal_discovery": len(marginal),
        "map_adds_marginal_discovery": bool(marginal),
        "issued_rows": sorted(rows, key=lambda r: (r["least_ranked_list_position"] or 10**9, str(r["decision_id"]))),
        "definition": ("marginal_discovery_set = issued counter rows whose decision_id was absent from "
                       "the initial-pool top-K (least-ranked list position > K); empty set => the map "
                       "adds no marginal discovery on this packet"),
    }


def measure_packet(bundles: dict[str, dict], k: int = K) -> dict:
    per_bundle = {qid: measure_bundle(b, k) for qid, b in bundles.items()}
    total_marginal = sum(b["n_marginal_discovery"] for b in per_bundle.values())
    total_issued = sum(b["n_issued_counter_rows"] for b in per_bundle.values())
    return {
        "K": k,
        "per_bundle": per_bundle,
        "n_issued_counter_rows_total": total_issued,
        "n_marginal_discovery_total": total_marginal,
        "map_adds_marginal_discovery_on_packet": bool(total_marginal),
        "headline": (
            f"{total_marginal} of {total_issued} issued counter rows are marginally discovered by the map "
            f"(absent from the initial-pool top-{k})"
        ),
    }
