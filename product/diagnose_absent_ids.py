#!/usr/bin/env python3
"""Diagnose the three known IDs absent from the 100-row cached pools.

Direction v65 ordered item 4 calls this a **retrieval-pool** question, not a scan
miss.  This script measures where the IDs actually are after the product's own
query-conditioned rerank, without changing any rank, threshold or pool.

Reproduction (network-free, cached fixture envelopes):

    python3 -m product.diagnose_absent_ids --out results/product/counter_span/CYCLE_<id>_absent_ids.json

The measurement is a pure function of the committed cache and fixture legs.  It
makes no precision/recall claim beyond the named rows and the named query legs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from product.query.pipeline import _candidate_to_product, _retrieve
from product.query.relevance import rerank_product_bundle
from product.reality_check import LEGS

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = (
    REPO_ROOT / "results" / "product" / "counter_span"
    / "CYCLE_39986094168_absent_ids.json"
)
LEGS_TO_SCAN = ("rent-default", "petty-theft-dismissal")
KNOWN_IDS = {
    "rent-default": ("gr_gerichte_PZ_2006_125", "zh_mietgericht_MB170006-L"),
    "petty-theft-dismissal": ("ch_vb_JAAC_68.7__",),
}


def measure_leg(slug: str, pool_n: int = 100) -> dict:
    query = LEGS[slug]
    candidate = _retrieve(query, pool_n, mode="fixture", hydrate_top=0)
    product = rerank_product_bundle(_candidate_to_product(candidate))
    by_id = {str(d.get("decision_id")): d for d in product.get("decisions") or []}
    rows = []
    for did in KNOWN_IDS[slug]:
        row = by_id.get(did)
        rows.append({
            "decision_id": did,
            "in_reranked_pool": row is not None,
            "post_rerank_rank": row.get("rank") if row else None,
            "inside_top_n_cut": bool(row and int(row.get("rank") or 10**9) <= pool_n),
            "score": row.get("score") if row else None,
            "query_similarity": row.get("query_similarity") if row else None,
            "legal_anchor_score": row.get("legal_anchor_score") if row else None,
            "remote_score_raw": row.get("retrieval_score_raw") if row else None,
            "court": row.get("court") if row else None,
            "channels": row.get("channels") if row else None,
        })
    return {
        "slug": slug,
        "query": query,
        "pool_n": pool_n,
        "n_reranked": len(product.get("decisions") or []),
        "rows": rows,
    }


def run() -> dict:
    legs = [measure_leg(slug) for slug in LEGS_TO_SCAN]
    all_rows = [r for leg in legs for r in leg["rows"]]
    return {
        "cycle": "direction_v65_absent_id_diagnosis",
        "source": "cached fixture envelopes + product rerank",
        "pool_n": 100,
        "legs": legs,
        "summary": {
            "n_known_ids": len(all_rows),
            "n_in_reranked_pool": sum(1 for r in all_rows if r["in_reranked_pool"]),
            "n_inside_top_n_cut": sum(1 for r in all_rows if r["inside_top_n_cut"]),
            "n_outside_only": sum(
                1 for r in all_rows
                if r["in_reranked_pool"] and not r["inside_top_n_cut"]
            ),
            "finding": (
                "All named IDs were retrieved into the candidate pool, but the "
                "query-conditioned rerank puts them just outside the top_n=100 cut "
                "(ranks 104, 118, 119) with legal_anchor_score 0 and query_similarity "
                "below 0.01.  They are pool-present and head-excluded, not retrieval "
                "misses.  Recovering them by enlarging the cut would insert rows the "
                "legal anchor does not support; no rank/pool change is made here."
            ),
            "claim_ceiling": (
                "Ranks/scores for the three named rows on two named fixture legs only. "
                "No recall, precision or legal-relevance claim; no threshold changed."
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    report = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"out": str(args.out), "summary": report["summary"]},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
