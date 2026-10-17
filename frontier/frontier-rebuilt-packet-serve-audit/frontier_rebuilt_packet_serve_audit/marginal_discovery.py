"""Half (c): COMPARATIVE marginal discovery on the REBUILT bytes.

For every ISSUED counter/contrary row on each rebuilt anchor bundle:
  * was its decision_id absent from the initial-pool top-K (K frozen = 20),
  * its least-ranked position in the shipped list,
  * whether a jurist scanning the ranked list top-K would encounter it
    before the map.
Reproduces-or-falsifies the accepted CLASSIFICATION_ONLY negative on the
rebuilt population (a different issued-counter set after classifier adoption).
"""
from __future__ import annotations

import json
from pathlib import Path

from .paths import QIDS

FROZEN_K = 20
ABSTAIN_MARKER = "abstained_unevidenced"
ISSUED_STATUSES = ("candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting")


def _initial_pool_order(bundle: dict) -> list[dict]:
    """Pre-rerank initial retrieval pool: retrieval_score_raw desc, rank asc."""
    rows = list(bundle.get("decisions") or [])

    def key(r):
        raw = r.get("retrieval_score_raw")
        raw = float(raw) if raw is not None else float("-inf")
        rank = r.get("rank")
        rank = int(rank) if rank is not None else 10**9
        return (-raw, rank)

    return sorted(rows, key=key)


def measure_bundle(packet_questions: Path, qid: str, k: int = FROZEN_K) -> dict:
    bundle_path = packet_questions / f"{qid}.bundle.json"
    bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    initial = _initial_pool_order(bundle)
    initial_top_k_ids = {r.get("decision_id") for r in initial[:k]}
    issued = [
        d for d in (bundle.get("decisions") or [])
        if (d.get("counter_status") or "none") in ISSUED_STATUSES
    ]
    per_row = []
    for row in sorted(issued, key=lambda r: int(r.get("rank") or 10**9)):
        rank = int(row.get("rank")) if row.get("rank") is not None else None
        did = row.get("decision_id")
        absent_initial = did not in initial_top_k_ids
        visible_list = rank is not None and rank <= k
        initial_pos = next(
            (i + 1 for i, r in enumerate(initial) if r.get("decision_id") == did), None
        )
        per_row.append({
            "decision_id": did,
            "counter_status": row.get("counter_status"),
            "rank": rank,
            "initial_pool_position": initial_pos,
            "absent_from_initial_pool_top_k": absent_initial,
            "visible_in_list_top_k": visible_list,
            "encountered_in_list_before_map": visible_list,
            "counter_only_in_map_effectively_invisible_in_list": bool(
                rank is not None and not visible_list
            ),
        })
    n_issued = len(per_row)
    n_absent = sum(1 for r in per_row if r["absent_from_initial_pool_top_k"])
    n_invisible = sum(1 for r in per_row if r["counter_only_in_map_effectively_invisible_in_list"])
    return {
        "qid": qid,
        "K": k,
        "n_decisions": len(bundle.get("decisions") or []),
        "n_issued": n_issued,
        "n_absent_from_initial_top_k": n_absent,
        "n_invisible_in_list_top_k": n_invisible,
        "marginal_discovery_exists": bool(n_absent > 0 or n_invisible > 0),
        "per_row": per_row,
    }


def measure(packet_questions: Path, k: int = FROZEN_K) -> dict:
    per_bundle = {qid: measure_bundle(packet_questions, qid, k) for qid in QIDS}
    total_issued = sum(b["n_issued"] for b in per_bundle.values())
    total_absent = sum(b["n_absent_from_initial_top_k"] for b in per_bundle.values())
    total_invisible = sum(b["n_invisible_in_list_top_k"] for b in per_bundle.values())
    any_marginal = any(b["marginal_discovery_exists"] for b in per_bundle.values())
    return {
        "half": "c_marginal_discovery",
        "K": k,
        "initial_pool_definition": "retrieval_score_raw DESC, rank ASC",
        "list_definition": "rank ASC (post rerank_product_bundle)",
        "per_bundle": per_bundle,
        "pooled": {
            "n_issued": total_issued,
            "n_absent_from_initial_top_k": total_absent,
            "n_invisible_in_list_top_k": total_invisible,
            "marginal_discovery_exists": any_marginal,
            "classification_only_negative_reproduced": (total_issued > 0 and not any_marginal),
            "no_issued_rows_at_all": total_issued == 0,
        },
    }
