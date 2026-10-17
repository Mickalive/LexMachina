#!/usr/bin/env python3
"""Deterministic evidence-pack recall harness for the four frozen reality legs.

Why this module exists
----------------------
``recall::citation_controlling_authority`` is the accepted RED leg of the frozen
four-question Product Reality Check: on the business-judgment-rule (BJR) question
the answer cited **zero of the five frozen direct-TF BJR authorities** at
executions 38920872324 / 38934722443 / 38945976309, and direction v50 (product
obligation (5)) recorded that the newest live leg did not repair it.

Cycle 38984833779 attacked that leg with a live head-recall change and honestly
recorded its own ceiling: **n=2 live runs, durability NOT established**. Two live
runs cannot separate a real improvement from provider variance, and each costs
100-300 s of provider time plus a network round trip, which is also why the lane
kept dying at the 45-minute workflow quantum (run 38984833779, rc 78).

The missing instrument is a measurement that needs neither. Citation recall is
decided *before* the generator runs:

    retrieval pool -> local legal rerank + head-recall splice
                   -> top-``evidence_count`` rows hydrated with ``full_text``
                   -> the generator may only cite a row it was given

So "can the generator cite authority X" is fully determined by the bundle that
reaches the generator, and that bundle is reproducible offline from the product
retrieval cache with no network and no provider. This module measures exactly
that. It is the durable instrument obligation (5) was missing.

It measures RECALL INTO THE EVIDENCE PACK, not citation. Citation still depends
on the generator choosing to cite a row it was given; nothing here claims
otherwise. See ``claim_ceiling`` in the emitted report.

Scope and honesty
-----------------
* Reads only ``results/product/query_cache`` (the product-owned cache root). No
  network, no provider, no paid dependency, no fixture rewriting.
* The frozen gate semantics are NOT re-implemented or re-tuned here. This module
  never asserts pass/fail against the frozen benchmark; it publishes the measured
  recall so a durable run can be compared against it. Every threshold that
  decides a gate lives in ``product/reality_check.py`` and stays untouched;
  ``test_evidence_pack_recall.py`` parses that frozen file and fails if this
  module's authority sets drift from it.
* ``bger_4A_228_2015`` is absent from the cached petty-theft pool entirely. That
  is a RETRIEVAL miss, not a ranking miss, and the harness reports the two
  separately so the distinction is never collapsed.

Usage
-----
    python product/evidence_pack_recall.py --json
    python product/evidence_pack_recall.py --out results/product/<dir>/recall.json
    python product/evidence_pack_recall.py --negative-control
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from reality_check import LEGS  # noqa: E402  (frozen question strings)

#: The authorities each frozen leg's truth gate is written against. Copied from
#: ``product/reality_check.py``'s truth gates; that file is never edited here and
#: a parity test asserts the two agree. ``required_any`` is the set the frozen
#: gate intersects with (the gate passes when the answer cites at least one);
#: ``direct`` is the named direct-Federal-authority set the direction counts as
#: the controlling authority for that question.
FROZEN_AUTHORITIES: dict[str, dict[str, object]] = {
    "business-judgment-rule": {
        "required_any": [
            "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
            "bger_4A_603_2014", "bger_4A_62_2024", "bge_BGE_139_III_24",
        ],
        "direct": [
            "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
            "bger_4A_603_2014", "bger_4A_62_2024",
        ],
    },
    "petty-theft-dismissal": {
        "required_any": ["bger_4A_228_2015", "bger_4A_177_2017"],
        "direct": ["bger_4A_228_2015", "bger_4A_177_2017"],
        # The frozen gate intersects with ``direct``: EITHER id satisfies it.
        "required_any_of_direct": True,
    },
    "corporate-criminal-liability": {
        "required_any": ["bge_BGE_142_IV_333", "bger_6B_124_2016"],
        "direct": ["bge_BGE_142_IV_333", "bger_6B_124_2016"],
    },
    "rent-default": {"required_any": [], "direct": []},
}

#: The served bundle size and the hydrated evidence-pack size used by the durable
#: leg harness (``product/ci_reality_legs.py``). ``product/reality_check.py``
#: defaults ``top_n`` to 100 and ``ci_reality_legs.py`` defaults
#: ``evidence_count`` to 10; the frozen structural gate
#: ``product/reality_check.py:119`` forbids serving more than 100 decisions.
SERVED_TOP_N = 100
EVIDENCE_PACK = 10


def _answer_channel_rank(pool: list[dict], decision_id: str) -> int | None:
    """1-based rank of ``decision_id`` inside the query-answering channel only.

    This is the SOURCE INDEX's own per-question ranking: the same channel
    vocabulary as ``query.relevance.REMOTE_RECALL_ANSWER_CHANNELS`` and the same
    ordering key as ``_remote_head_recall`` (raw score descending, ties in pool
    order), but computed on the retrieval pool rather than on the
    locally-reordered list, so it describes the upstream judgement and not the
    product's own reranking.

    ``leading_case`` (a global citation-count leaderboard) and the
    citation-expansion shells are excluded, because neither ranks answers to
    *this* question.
    """
    from query.relevance import REMOTE_RECALL_ANSWER_CHANNELS

    rows = [c for c in pool if set(c.get("channels") or ()) & REMOTE_RECALL_ANSWER_CHANNELS]
    rows.sort(key=lambda c: (-float(c.get("score") or 0.0),))
    for i, c in enumerate(rows, start=1):
        if c.get("decision_id") == decision_id:
            return i
    return None


def measure_leg(slug: str, *, top_n: int = SERVED_TOP_N,
                evidence_pack: int = EVIDENCE_PACK) -> dict:
    """Offline, network-free evidence-pack recall for one frozen leg."""
    from ocl_adapter.bundle import to_product_bundle
    from query.pipeline import _retrieve
    from query.relevance import rerank_product_bundle

    question = LEGS[slug]
    spec = FROZEN_AUTHORITIES[slug]
    direct: list[str] = list(spec["direct"])  # type: ignore[arg-type]

    bundle = _retrieve(question, top_n, mode="offline")
    pool = bundle.get("candidates", [])
    degraded = bool(bundle.get("provenance", {}).get("degraded"))

    product_bundle = rerank_product_bundle(to_product_bundle(bundle))
    served = list(product_bundle.get("decisions") or [])[:top_n]
    pack_ids = [d.get("decision_id") for d in served[:evidence_pack]]

    rows = []
    for decision_id in direct:
        in_pool = any(c.get("decision_id") == decision_id for c in pool)
        served_positions = [i + 1 for i, d in enumerate(served)
                            if d.get("decision_id") == decision_id]
        final_rank = served_positions[0] if served_positions else None
        rows.append({
            "decision_id": decision_id,
            "retrieved": in_pool,
            "answer_channel_rank": _answer_channel_rank(pool, decision_id),
            "served_rank": final_rank,
            "in_evidence_pack": decision_id in pack_ids,
        })

    recalled = [
        {"decision_id": m["decision_id"], "from_rank": m["from_rank"],
         "to_rank": m["to_rank"], "answer_channel_rank": m.get("remote_rank")}
        for m in ((product_bundle.get("provenance") or {})
                  .get("product_rerank", {})
                  .get("remote_head_recall", {})
                  .get("moved") or [])
    ]

    in_pack = sum(1 for r in rows if r["in_evidence_pack"])
    retrieved = sum(1 for r in rows if r["retrieved"])

    return {
        "slug": slug,
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "cache_degraded": degraded,
        "pool_size": len(pool),
        "served_size": len(served),
        "evidence_pack_size": evidence_pack,
        "direct_total": len(direct),
        "direct_retrieved": retrieved,
        "direct_in_evidence_pack": in_pack,
        "retrieval_miss_ids": [r["decision_id"] for r in rows if not r["retrieved"]],
        "ranking_miss_ids": [r["decision_id"] for r in rows
                             if r["retrieved"] and not r["in_evidence_pack"]],
        "authorities": rows,
        "head_recall_moved": recalled,
    }


def measure_all(*, top_n: int = SERVED_TOP_N, evidence_pack: int = EVIDENCE_PACK) -> dict:
    from query import relevance as R

    legs = [measure_leg(slug, top_n=top_n, evidence_pack=evidence_pack)
            for slug in LEGS]
    bjr = next(leg for leg in legs if leg["slug"] == "business-judgment-rule")
    return {
        "instrument": "evidence_pack_recall_v1",
        "mode": "offline_cache_only",
        "network": False,
        "llm_calls": 0,
        "served_top_n": top_n,
        "evidence_pack_size": evidence_pack,
        "head_recall_config": {
            "remote_top": R.REMOTE_HEAD_RECALL_REMOTE_TOP,
            "local_head": R.REMOTE_HEAD_RECALL_LOCAL_HEAD,
            "max_moved": R.REMOTE_HEAD_RECALL_MAX_MOVED,
            "insert_at": R.REMOTE_HEAD_RECALL_INSERT_AT,
            "evidence_pack_anchor": R.REMOTE_HEAD_RECALL_EVIDENCE_PACK,
            "reserved_tail_fits_evidence_pack":
                R.REMOTE_HEAD_RECALL_INSERT_AT + R.REMOTE_HEAD_RECALL_MAX_MOVED - 1
                <= evidence_pack,
        },
        "controlling_authority_recall": {
            "business_judgment_rule_direct_in_evidence_pack":
                bjr["direct_in_evidence_pack"],
            "business_judgment_rule_direct_total": bjr["direct_total"],
        },
        "legs": legs,
        "claim_ceiling": (
            "This measures RECALL INTO THE HYDRATED EVIDENCE PACK, not citation. "
            "A row inside the pack can still be ignored by the generator, and a "
            "row outside it cannot be cited because the generator never sees its "
            "text. The accepted RED leg recall::citation_controlling_authority is "
            "a citation metric and can only be moved by a live leg; this "
            "instrument makes its precondition measurable offline, repeatably, "
            "and at no provider cost."
        ),
    }


def negative_control(*, top_n: int = SERVED_TOP_N,
                     evidence_pack: int = EVIDENCE_PACK) -> dict:
    """Prove the harness is not vacuous.

    Disables the head-recall splice, re-measures, and requires the
    business-judgment-rule pack recall to DROP. A harness that cannot observe the
    mechanism it instruments cannot be used to claim the mechanism works.
    """
    from query import relevance as R

    baseline = measure_leg("business-judgment-rule", top_n=top_n,
                           evidence_pack=evidence_pack)
    saved = (R.REMOTE_HEAD_RECALL_MAX_MOVED, R.REMOTE_HEAD_RECALL_INSERT_AT)
    try:
        R.REMOTE_HEAD_RECALL_MAX_MOVED = 0
        R.REMOTE_HEAD_RECALL_INSERT_AT = 10 ** 6
        ablated = measure_leg("business-judgment-rule", top_n=top_n,
                              evidence_pack=evidence_pack)
    finally:
        R.REMOTE_HEAD_RECALL_MAX_MOVED, R.REMOTE_HEAD_RECALL_INSERT_AT = saved
    return {
        "baseline_in_evidence_pack": baseline["direct_in_evidence_pack"],
        "ablated_in_evidence_pack": ablated["direct_in_evidence_pack"],
        "mechanism_observable":
            ablated["direct_in_evidence_pack"] < baseline["direct_in_evidence_pack"],
        "baseline_served_ranks": {r["decision_id"]: r["served_rank"]
                                  for r in baseline["authorities"]},
        "ablated_served_ranks": {r["decision_id"]: r["served_rank"]
                                 for r in ablated["authorities"]},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--top-n", type=int, default=SERVED_TOP_N)
    parser.add_argument("--evidence-pack", type=int, default=EVIDENCE_PACK)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--out", type=Path, default=None, help="write the report here")
    parser.add_argument("--negative-control", action="store_true",
                        help="also run the non-vacuity control")
    args = parser.parse_args(argv)

    report = measure_all(top_n=args.top_n, evidence_pack=args.evidence_pack)
    if args.negative_control:
        report["negative_control"] = negative_control(
            top_n=args.top_n, evidence_pack=args.evidence_pack)

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    if args.json:
        print(text)
    else:
        cfg = report["head_recall_config"]
        print(f"offline cache-only recall  top_n={report['served_top_n']} "
              f"pack={report['evidence_pack_size']}")
        print(f"head_recall: remote_top={cfg['remote_top']} local_head={cfg['local_head']} "
              f"max_moved={cfg['max_moved']} insert_at={cfg['insert_at']} "
              f"tail_fits_pack={cfg['reserved_tail_fits_evidence_pack']}")
        for leg in report["legs"]:
            extra = (f"  retrieval_miss={leg['retrieval_miss_ids']}"
                     if leg["retrieval_miss_ids"] else "")
            flag = "  DEGRADED-CACHE" if leg["cache_degraded"] else ""
            print(f"  {leg['slug']:32s} pool={leg['pool_size']:4d} "
                  f"served={leg['served_size']:4d} "
                  f"direct_in_pack={leg['direct_in_evidence_pack']}/{leg['direct_total']}"
                  f"{extra}{flag}")
        bjr = report["controlling_authority_recall"]
        print(f"  recall::citation_controlling_authority precondition "
              f"(BJR direct in pack) = "
              f"{bjr['business_judgment_rule_direct_in_evidence_pack']}"
              f"/{bjr['business_judgment_rule_direct_total']}")
        if "negative_control" in report:
            nc = report["negative_control"]
            print(f"  negative control: baseline={nc['baseline_in_evidence_pack']} "
                  f"ablated={nc['ablated_in_evidence_pack']} "
                  f"observable={nc['mechanism_observable']}")
    return 0 if (not args.negative_control
                 or report["negative_control"]["mechanism_observable"]) else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())