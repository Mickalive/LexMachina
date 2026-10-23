#!/usr/bin/env python3
"""Cached counter-surface coverage measurement (direction v63 item 7(a)).

    python3 product/counter_surface_coverage.py
    python3 product/counter_surface_coverage.py --slugs rent-default --top-n 100

What it measures (offline, deterministic, zero network):

For each frozen reality leg, the full offline vertical slice
(``run_query_initial(retrieval_mode="fixture")`` + ``enrich_query_bundle(
fixture_generation=True)``) is executed twice — once with the pool
counter-surface scan disabled (``LEXMACHINA_COUNTER_SURFACE=off``), once with
it on — and the two bundles are compared field by field:

* how many rendered rows carry an ATTESTED heuristic counter-surface signal
  with and without the scan (the scan's before-state is 0 by construction:
  the field did not exist);
* how many unhydrated rows were marker-bearing, how many were selected for
  hydration, how many detail texts the cache actually supplied, and — since
  ``counter_surface/2`` — how many unhydrated rows the cache could supply at
  all (``n_hydrateable_in_pool``) together with the selection rule in force.
  That last field is what distinguishes "the selector wasted the budget"
  (``counter_surface/1``, measured 32 selected / 1 hydrated across the four
  legs) from "the cache has nothing left to give", which no selector change
  can fix;
* the invariants that make the scan safe: NO ``counter_status`` /
  ``counter_evidence`` / ``counter_uncertainty`` / ``counter_evidence_verified``
  difference and NO rendered coordinate / rank / cluster difference between
  the two runs.

Claim ceiling (printed into the artifact): this is a PRODUCT-OWNED cached
measurement on the four shipped offline legs.  It does NOT reproduce Core
Evaluation's frozen known-authority population (run 39838415410's 14 ids),
it scores no frozen bar and it asserts no legal label.  Evaluation re-measures
the coverage family under its OWN new run id; this artifact only shows the
capability landed, the direction of movement, and the invariants.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
sys.path.insert(0, str(PRODUCT_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from product.query.counter_surface import COUNTER_SURFACE_VERSION, ENABLE_ENV  # noqa: E402

CLAIM_CEILING = (
    "product-owned cached measurement of the counter-surface scan on the four "
    "shipped offline reality legs; it does NOT reproduce Core Evaluation's "
    "frozen known-authority population (run 39838415410), scores no frozen "
    "bar, proves no jurist usefulness and asserts no legal label; Evaluation "
    "re-measures coverage under its own new run id"
)


def _no_network(*_a, **_k):  # pragma: no cover - armed on every run
    raise AssertionError("coverage measurement attempted network access")


def _geometry_fingerprint(bundle: dict) -> str:
    rows = [
        (str(d.get("decision_id")), d.get("x"), d.get("y"),
         d.get("cluster_id"), d.get("rank"), bool(d.get("is_outlier")))
        for d in bundle.get("decisions") or []
    ]
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def _scored_fingerprint(bundle: dict) -> str:
    rows = [
        (str(d.get("decision_id")), d.get("counter_status"),
         d.get("counter_evidence"), d.get("counter_uncertainty"),
         d.get("counter_evidence_verified"))
        for d in bundle.get("decisions") or []
    ]
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def _run_offline(slug: str, query: str, top_n: int, scan: str) -> dict:
    if scan == "off":
        os.environ[ENABLE_ENV] = "off"
    else:
        os.environ.pop(ENABLE_ENV, None)
    from product.query.pipeline import enrich_query_bundle, run_query_initial

    started = time.time()
    initial = run_query_initial(query, top_n=top_n, retrieval_mode="fixture")
    bundle = enrich_query_bundle(initial, retrieval_mode="fixture",
                                 fixture_generation=True)
    return {
        "bundle": bundle,
        "wall_seconds": round(time.time() - started, 3),
        "geometry_fp": _geometry_fingerprint(bundle),
        "scored_fp": _scored_fingerprint(bundle),
    }


def measure(slug: str, query: str, top_n: int) -> dict:
    real_connect = socket.socket.connect
    socket.socket.connect = _no_network
    try:
        off = _run_offline(slug, query, top_n, "off")
        on = _run_offline(slug, query, top_n, "on")
    finally:
        socket.socket.connect = real_connect
        os.environ.pop(ENABLE_ENV, None)

    prov = (on["bundle"].get("provenance") or {}).get("counter_surface") or {}
    signals = [
        {
            "decision_id": d.get("decision_id"),
            "intent": (d.get("counter_surface_signal") or {}).get("intent"),
            "heuristic_status": (d.get("counter_surface_signal") or {}).get("heuristic_status"),
            "markers": (d.get("counter_surface_signal") or {}).get("markers"),
            "text_source": (d.get("counter_surface_signal") or {}).get("text_source"),
        }
        for d in on["bundle"].get("decisions") or []
        if d.get("counter_surface_signal")
    ]
    invariants = {
        "scored_counter_fields_identical": off["scored_fp"] == on["scored_fp"],
        "geometry_and_ranks_identical": off["geometry_fp"] == on["geometry_fp"],
        "n_decisions_identical": len(off["bundle"].get("decisions") or [])
        == len(on["bundle"].get("decisions") or []),
    }
    return {
        "slug": slug,
        "query": query,
        "top_n": top_n,
        "n_decisions": len(on["bundle"].get("decisions") or []),
        "scan_off": {
            "wall_seconds": off["wall_seconds"],
            "n_signalled": 0,
            "note": "field absent by construction: the scan did not run",
        },
        "scan_on": {
            "wall_seconds": on["wall_seconds"],
            "n_marker_bearing_unhydrated": prov.get("n_marker_bearing_unhydrated"),
            "n_selected_for_hydration": prov.get("n_selected_for_hydration"),
            "n_hydrated": prov.get("n_hydrated"),
            # counter_surface/2 (run 39879015785): WHY the selection is what it
            # is.  n_hydrateable_in_pool is the number of unhydrated rendered
            # rows the backing store can actually answer; when it is 0 the
            # binding constraint on this leg is cached detail coverage, not the
            # selection rule, and no selector change can raise n_hydrated.
            "hydrate_probe_used": prov.get("hydrate_probe_used"),
            "hydrate_probe_error": prov.get("hydrate_probe_error"),
            "n_hydrateable_in_pool": prov.get("n_hydrateable_in_pool"),
            "hydration_selection_rule": prov.get("hydration_selection_rule"),
            "hydration_budget_utilisation": (
                round(prov.get("n_hydrated", 0) / prov.get("n_selected_for_hydration"), 3)
                if prov.get("n_selected_for_hydration") else None
            ),
            "hydrate_error": prov.get("hydrate_error"),
            "n_signalled": prov.get("n_signalled"),
            "intent_histogram": prov.get("intent_histogram"),
            "counter_surface_status_histogram": prov.get(
                "counter_surface_status_histogram"),
            "signalled_ids": prov.get("signalled_ids"),
        },
        "signals": signals,
        "invariants": invariants,
        "invariants_hold": all(invariants.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slugs", default=",".join(
        ["rent-default", "petty-theft-dismissal", "corporate-criminal-liability",
         "business-judgment-rule"]))
    ap.add_argument("--top-n", type=int, default=100)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from product.reality_check import LEGS

    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    unknown = [s for s in slugs if s not in LEGS]
    if unknown:
        print(f"unknown slugs: {unknown}; known: {sorted(LEGS)}", file=sys.stderr)
        return 2

    run_id = os.environ.get("GITHUB_RUN_ID") or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ")
    out_path = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "product" / "counter_surface"
        / f"CYCLE_{run_id}_coverage.json")

    legs = [measure(slug, LEGS[slug], args.top_n) for slug in slugs]
    total_signalled = sum(l["scan_on"]["n_signalled"] or 0 for l in legs)
    total_selected = sum(l["scan_on"]["n_selected_for_hydration"] or 0 for l in legs)
    total_hydrated = sum(l["scan_on"]["n_hydrated"] or 0 for l in legs)
    total_pool = sum(l["scan_on"]["n_hydrateable_in_pool"] or 0 for l in legs)
    all_invariants = all(l["invariants_hold"] for l in legs)
    artifact = {
        "schema": "product-counter-surface-coverage/2",
        "record_type": "COUNTER_SURFACE_CACHED_COVERAGE",
        "component": COUNTER_SURFACE_VERSION,
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "network": "none (socket.connect booby-trapped)",
        "mode": "fixture replay of recorded OpenCaseLaw envelopes",
        "legs": legs,
        "aggregate": {
            "n_legs": len(legs),
            "n_signalled_total": total_signalled,
            "n_selected_for_hydration_total": total_selected,
            "n_hydrated_total": total_hydrated,
            # counter_surface/2: how much of the rendered pool the backing
            # store could still answer for at scan time.  When this totals 0
            # the scan's budget is not the limit — cached detail coverage is,
            # and only a refresh-mode re-recording can move it.
            "n_hydrateable_in_pool_total": total_pool,
            "hydration_budget_utilisation_total": (
                round(total_hydrated / total_selected, 3) if total_selected else None
            ),
            "all_invariants_hold": all_invariants,
        },
        "verdict": (
            "SCAN_LANDED_INVARIANTS_HOLD" if all_invariants
            else "INVARIANT_BROKEN_DO_NOT_SHIP"
        ),
        "claim_ceiling": CLAIM_CEILING,
        "not_claimed": [
            "no reproduction of the frozen 14-known-authority population",
            "no frozen bar scored",
            "no legal label asserted for any decision",
            "no jurist-usefulness claim",
            "no claim that the selection rule can raise hydration where the "
            "cache holds no detail body for an unhydrated row (that requires "
            "a refresh-mode re-recording of the envelopes, not a selector)",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(json.dumps({"out": str(out_path), "verdict": artifact["verdict"],
                      "aggregate": artifact["aggregate"]},
                     ensure_ascii=False, indent=2))
    return 0 if all_invariants else 1


if __name__ == "__main__":
    raise SystemExit(main())
