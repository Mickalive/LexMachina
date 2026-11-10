#!/usr/bin/env python3
"""Offline replay smoke for the real Swiss-law questions the product ships.

    python product/fixture_question_replay_probe.py --run-id 42738229187

For each frozen reality question it asks the shipped first-page pipeline for
the server default ``n=150`` and records: decisions, clusters, every row's map
coordinates/source link, the replay source and the page-size-match count.  The
process traps non-loopback ``socket.connect`` so a green run proves the
developer-facing map came from the committed OpenCaseLaw cache, not network.

Engineering evidence only: this is not a frozen recall/truth gate, evaluates no
legal label and makes no juris-usefulness claim.
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
sys.path.insert(0, str(PRODUCT_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from query import run_query_first_page  # noqa: E402
from query.bundle import validate_bundle  # noqa: E402
from reality_check import LEGS  # noqa: E402

DEFAULT_N = 150
DEFAULT_RUN_ID = "42738229187"

#: A real cached German-language question that is recorded only at limit=10/12.
#: It is the page-size-drift regression witness, kept separate from the frozen
#: English/French reality legs.
GERMAN_RENT_QUESTION = (
    "Unter welchen Voraussetzungen kann der Vermieter einen Wohnmietvertrag "
    "wegen Zahlungsverzug kündigen, und welche Ausnahmen oder Grenzen der "
    "Rechtsprechung bestehen nach Schweizer Recht?"
)


def _no_remote_network(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise AssertionError(f"offline probe attempted remote network access: {address!r}")
    return _REAL_CONNECT(self, address)


_REAL_CONNECT = socket.socket.connect


def probe(question: str, n: int) -> dict:
    started = time.time()
    record: dict = {"question": question}
    try:
        bundle = run_query_first_page(question, top_n=n, retrieval_mode="fixture")
        records = bundle.get("decisions") or []
        replay = (bundle.get("provenance") or {}).get("product_fixture_replay") or {}
        record.update({
            "ok": True,
            "elapsed_s": round(time.time() - started, 3),
            "validation_errors": validate_bundle(bundle),
            "n_decisions": len(records),
            "n_clusters": len(bundle.get("clusters") or []),
            "rows_with_xy": sum(
                1 for d in records
                if isinstance(d.get("x"), (int, float)) and isinstance(d.get("y"), (int, float))
            ),
            "rows_with_cluster_id": sum(1 for d in records if d.get("cluster_id") is not None),
            "rows_with_source_link": sum(
                1 for d in records if d.get("canonical_url") or d.get("source_url")
            ),
            "replay_source": replay.get("source"),
            "replay_candidates": replay.get("n_candidates"),
            "question_matches": (replay.get("question_match") or {}).get("question_matches"),
            "network": replay.get("network"),
        })
    except Exception as exc:  # negative evidence is preserved
        record.update({
            "ok": False,
            "elapsed_s": round(time.time() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        })
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    socket.socket.connect = _no_remote_network
    try:
        results = [probe(question, args.n) for question in LEGS.values()]
        results.append(probe(GERMAN_RENT_QUESTION, 100))
    finally:
        socket.socket.connect = _REAL_CONNECT

    ok = all(
        r.get("ok")
        and r.get("n_decisions", 0) > 0
        and not r.get("validation_errors")
        and r.get("rows_with_xy") == r.get("n_decisions")
        and r.get("rows_with_cluster_id") == r.get("n_decisions")
        and r.get("rows_with_source_link") == r.get("n_decisions")
        for r in results
    )
    payload = {
        "schema": "product-fixture-question-replay/1",
        "run_id": args.run_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "fixture_offline",
        "n_param": args.n,
        "network": "none (non-loopback socket.connect trapped)",
        "claim_ceiling": (
            "OFFLINE WIRING EVIDENCE ONLY: proves real cached Swiss-law "
            "questions replay to a source-linked renderable map with no "
            "network. No frozen recall/truth gate is evaluated and no legal "
            "or usability claim is made."
        ),
        "all_ok": ok,
        "questions": results,
    }
    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "product" / "fixture_question_replay"
        / f"CYCLE_{args.run_id}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in results:
        status = "PASS" if r.get("ok") and r.get("n_decisions", 0) > 0 else "FAIL"
        print(f"[{status}] {r['question'][:72]!r} "
              f"n={r.get('n_decisions')} clusters={r.get('n_clusters')} "
              f"source={r.get('replay_source')}")
    print(f"wrote {out}")
    print("verdict:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
