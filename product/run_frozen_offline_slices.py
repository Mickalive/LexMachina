#!/usr/bin/env python3
"""Produce the four frozen-question offline slices as full query_result_bundles.

Why this exists
---------------
``product/minimal_vertical_slice.py --mode offline`` used to fail for the four
frozen reality questions: the committed OpenCaseLaw cache records them at page
sizes (10/12/25/30/...) that a ``top_n``-derived request never reproduces, so
the exact cache key missed and the slice raised
``OpenCaseLaw retrieval returned no decisions``.  The tolerant question-match
replay now fixes that path (see ``product/query/cache_replay.py`` and
``_retrieve`` in ``product/query/pipeline.py``).

This runner is the reproducible one-command way to materialise the four frozen
question -> query_result_bundle -> sourced answer -> counter-authority ->
clickable-map artifacts from the committed cache, with a non-loopback socket
trap armed for the whole run.  It writes both the full bundle (for the map and
downstream audit) and a compact summary.

    python3 product/run_frozen_offline_slices.py --run-id 42794322956

Claim ceiling: OFFLINE WIRING EVIDENCE ONLY.  It proves the shipped pipeline can
replay real cached Swiss-law questions into source-linked bundles with no
network.  It evaluates no frozen recall/truth bar and makes no legal or
juris-usefulness claim.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _root in (PRODUCT_ROOT, REPO_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from minimal_vertical_slice import run_minimal_slice  # noqa: E402
from reality_check import LEGS  # noqa: E402
from query.bundle import validate_bundle  # noqa: E402

DEFAULT_N = 150
DEFAULT_RUN_ID = "42794322956"
OUT_ROOT = REPO_ROOT / "results" / "product" / "offline_slice"

_REAL_CONNECT = socket.socket.connect


def _no_remote_network(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise AssertionError(f"offline slice attempted remote network access: {address!r}")
    return _REAL_CONNECT(self, address)


def _summary(slug: str, question: str, output: dict, bundle: dict,
             elapsed_s: float) -> dict:
    rows = bundle.get("decisions") or []
    answer = bundle.get("answer") or {}
    cited = list(answer.get("cited_decision_ids") or [])
    ids = {d.get("decision_id") for d in rows}
    viz = output.get("visualization") or {}
    replay = (bundle.get("provenance") or {}).get("product_offline_replay") or {}
    return {
        "slug": slug,
        "question": question,
        "ok": (
            bool(rows)
            and not validate_bundle(bundle)
            and len(cited) > 0
            and set(cited) <= ids
            and all(
                isinstance(d.get("x"), (int, float))
                and isinstance(d.get("y"), (int, float))
                and d.get("cluster_id") is not None
                and bool(d.get("canonical_url") or d.get("source_url"))
                for d in rows
            )
        ),
        "elapsed_s": round(elapsed_s, 3),
        "n_decisions": len(rows),
        "n_clusters": len(bundle.get("clusters") or []),
        "n_relations": viz.get("n_relations"),
        "n_counter_authorities": (output.get("counter_info") or {}).get(
            "n_counter_authorities"),
        "n_answer_citations": len(cited),
        "answer_method": answer.get("method"),
        "answer_citations_closed": set(cited) <= ids,
        "rows_with_xy": sum(
            1 for d in rows
            if isinstance(d.get("x"), (int, float))
            and isinstance(d.get("y"), (int, float))
        ),
        "rows_with_cluster_id": sum(
            1 for d in rows if d.get("cluster_id") is not None),
        "rows_with_source_link": sum(
            1 for d in rows if d.get("canonical_url") or d.get("source_url")),
        "languages": viz.get("languages"),
        "validation_errors": validate_bundle(bundle),
        "replay_source": replay.get("source"),
        "question_match": replay.get("question_match"),
        "network": "none (non-loopback socket.connect trapped)",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir) if args.out_dir else (
        OUT_ROOT / f"CYCLE_{args.run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    socket.socket.connect = _no_remote_network
    summaries = []
    try:
        for slug, question in LEGS.items():
            started = time.time()
            output, bundle = run_minimal_slice(
                question, top_n=args.n, mode="offline", with_bundle=True,
            )
            elapsed = time.time() - started
            (out_dir / f"{slug}.bundle.json").write_text(
                json.dumps(bundle, ensure_ascii=False, indent=2),
                encoding="utf-8")
            record = _summary(slug, question, output, bundle, elapsed)
            summaries.append(record)
            (out_dir / f"{slug}.summary.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print(f"[{'PASS' if record['ok'] else 'FAIL'}] {slug}: "
                  f"{record['n_decisions']} decisions, "
                  f"{record['n_clusters']} clusters, "
                  f"{record['n_answer_citations']} citations, "
                  f"{record['n_counter_authorities']} counter rows, "
                  f"{record['elapsed_s']}s")
    finally:
        socket.socket.connect = _REAL_CONNECT

    payload = {
        "schema": "product-frozen-offline-slices/1",
        "run_id": args.run_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "offline",
        "n_param": args.n,
        "network": "none (non-loopback socket.connect trapped)",
        "all_ok": all(r["ok"] for r in summaries),
        "claim_ceiling": (
            "OFFLINE WIRING EVIDENCE ONLY: real cached Swiss-law questions "
            "replay into source-linked query_result_bundles with no network. "
            "No frozen recall/truth gate is evaluated and no legal or "
            "usability claim is made."
        ),
        "slices": summaries,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_dir} (all_ok={payload['all_ok']})")
    return 0 if payload["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
