#!/usr/bin/env python3
"""Span-gate probe on the three head-excluded known IDs (direction v65 item 4).

The accepted diagnosis ``results/product/counter_span/
CYCLE_39986094168_absent_ids.json`` established that ``gr_gerichte_PZ_2006_125``,
``zh_mietgericht_MB170006-L`` and ``ch_vb_JAAC_68.7__`` are pool-present but
head-excluded (rerank ranks 104, 118, 119 of the 100-row cut) with
``legal_anchor_score`` 0 and sub-0.01 query similarity.  The state's ordered
follow-up was: apply the same span probe to those IDs only AFTER the
retrieval-pool diagnosis is published, and do not force off-domain rows into
the head.

This script is that follow-up, and only that.  For each named row it runs the
accepted verbatim-span confirm-or-abstain gate
(:func:`product.query.counter_evidence_span.select_span`, shipped precision
guard ON) on the row's own cached text, and records whether ANY span the
frozen classifier would confirm exists at all.  It never changes a rank, a
pool, a budget or a threshold, and it makes no claim about whether the row
belongs in any head.

Reproduction (network-free, cached fixture envelopes):

    python3 -m product.probe_absent_id_spans \
        --out results/product/counter_span/CYCLE_<run>_absent_id_span_probe.json
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import json
import socket
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # product-owned import shim
    sys.path.insert(0, str(REPO_ROOT))

from product.diagnose_absent_ids import KNOWN_IDS, LEGS_TO_SCAN  # noqa: E402
from product.query.counter_anchor import (  # noqa: E402
    _import_component,
    load_frozen_rules,
    resolve_anchor_profile,
)
from product.query.counter_evidence_span import (  # noqa: E402
    SPAN_VERSION,
    guard_terms,
    select_span,
)
from product.query.pipeline import _candidate_to_product, _retrieve  # noqa: E402
from product.query.relevance import rerank_product_bundle  # noqa: E402
from product.reality_check import LEGS  # noqa: E402

SCHEMA = "product-absent-id-span-probe/1"
POOL_N = 100


@contextlib.contextmanager
def _no_network() -> Any:
    """Fail closed: a blocked call is recorded, never silently retried."""
    attempts: list[str] = []
    real_connect = socket.socket.connect

    def _blocked(self, address, *args, **kwargs):  # noqa: ANN001
        attempts.append(repr(address))
        raise AssertionError("probe attempted network access")

    socket.socket.connect = _blocked
    try:
        yield attempts
    finally:
        socket.socket.connect = real_connect


def probe_row(row: dict, *, rules: Any, query: str) -> dict[str, Any]:
    profile = resolve_anchor_profile(rules, query=query)
    profile_key = next(
        (k for k, v in (getattr(rules, "anchors", {}) or {}).items() if v is profile),
        None,
    )
    rec: dict[str, Any] = {
        "decision_id": str(row.get("decision_id") or ""),
        "post_rerank_rank": row.get("rank"),
        "query_similarity": row.get("query_similarity"),
        "legal_anchor_score": row.get("legal_anchor_score"),
        "resolved_profile_key": profile_key,
        "text_fields_present": [
            name for name in ("full_text", "regeste", "snippet", "title")
            if str(row.get(name) or "").strip()
        ],
        "n_text_chars": sum(
            len(str(row.get(name) or ""))
            for name in ("full_text", "regeste", "snippet", "title")
        ),
    }
    if profile is None:
        rec["span_probe"] = {
            "applied": False,
            "reason": "no_frozen_anchor_profile_for_query",
            "evidenced": False,
        }
        return rec
    decide_label, _load = _import_component()
    guard = guard_terms(profile, query)
    sel = select_span(
        row,
        rules=rules,
        profile=profile,
        decide_label=decide_label,
        guard=guard,
        precision_guard=True,  # shipped default
    )
    rec["span_probe"] = {
        "applied": True,
        "evidenced": bool(sel.selected),
        "reason_code": sel.reason_code,
        "field": sel.field or None,
        "quote_chars": len(sel.quote) if sel.quote else 0,
        "n_candidates": sel.n_candidates,
        "n_guard_rejected": sel.n_guard_rejected,
        "guard_available": bool(guard.get("available")),
        "guard_statutes": list(guard.get("statutes") or []),
        "guard_phrase_count": len(guard.get("phrases") or []),
    }
    return rec


def run() -> dict[str, Any]:
    rules, digest = load_frozen_rules()
    legs: list[dict[str, Any]] = []
    with _no_network() as attempts:
        for slug in LEGS_TO_SCAN:
            query = LEGS[slug]
            candidate = _retrieve(query, POOL_N, mode="fixture", hydrate_top=0)
            product = rerank_product_bundle(_candidate_to_product(candidate))
            by_id = {str(d.get("decision_id")): d for d in product.get("decisions") or []}
            rows = []
            for did in KNOWN_IDS[slug]:
                row = by_id.get(did)
                if row is None:
                    rows.append({"decision_id": did, "in_reranked_pool": False,
                                 "span_probe": {"applied": False,
                                                "reason": "not_in_reranked_pool",
                                                "evidenced": False}})
                    continue
                rows.append(probe_row(row, rules=rules, query=query))
            legs.append({
                "slug": slug,
                "query": query,
                "n_reranked": len(product.get("decisions") or []),
                "rows": rows,
            })
    all_rows = [r for leg in legs for r in leg["rows"]]
    return {
        "schema": SCHEMA,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mode": "fixture replay (network blocked; diagnostic only)",
        "span_version": SPAN_VERSION,
        "frozen_rules_sha256": digest,
        "upstream_diagnosis": (
            "results/product/counter_span/CYCLE_39986094168_absent_ids.json"
        ),
        "legs": legs,
        "summary": {
            "n_probed": len(all_rows),
            "n_in_reranked_pool": sum(
                1 for r in all_rows if r.get("in_reranked_pool") is not False
            ),
            "n_span_evidenced": sum(
                1 for r in all_rows if (r.get("span_probe") or {}).get("evidenced")
            ),
            "per_row": [
                {
                    "decision_id": r.get("decision_id"),
                    "resolved_profile_key": r.get("resolved_profile_key"),
                    "span_evidenced": bool((r.get("span_probe") or {}).get("evidenced")),
                    "reason_code": (r.get("span_probe") or {}).get("reason_code")
                    or (r.get("span_probe") or {}).get("reason"),
                }
                for r in all_rows
            ],
            "network_attempts": attempts,
        },
        "claim_ceiling": (
            "Diagnostic span probe on three named head-excluded rows of two "
            "named fixture legs. It answers only: does this row's own cached "
            "text contain ANY span the frozen confirm-or-abstain gate would "
            "confirm under the shipped precision guard? It never asserts a "
            "decision IS supporting, contrary or limiting, never changes a "
            "rank/pool/budget, and makes no precision, recall or head-"
            "membership claim."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    report = run()
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(json.dumps({"out": str(args.out) if args.out else None,
                      "summary": report["summary"]},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
