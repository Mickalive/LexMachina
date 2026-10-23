#!/usr/bin/env python3
"""Known-authority coverage of the product's cached counter surface.

What this measures
------------------
For each of the four shipped offline legs, replay the frozen query bundle
(initial retrieval + fixture generation, exactly the offline slice path), then
run ``counter_surface.apply_counter_surface`` at two hydration caps on the
SAME bundle.  A known authority is:

* **reached** when its frozen alnum-core matches any rendered row's id,
  docket or citation field (the frozen evaluation rule, re-stated in
  ``product/query/known_authorities.py``);
* **signalled** when that row carries ``counter_surface_signal`` after the
  scan at the given cap.

The two caps are the accepted cached budget (8) and the direction-v64 broader
budget (24).  This is a coverage measurement, not a legal-correctness verdict:
the signal is a heuristic surface and the 28 ids are a frozen sample adopted
from the evaluation lane (source sha256 recorded in the artifact).

Usage
-----
    python -m product.query.counter_surface_known \
        --out results/product/counter_surface_known/CYCLE_<run>.json
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import json
import os
import socket
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # product-owned import shim, matches query/*
    sys.path.insert(0, str(REPO_ROOT))

from product.query import counter_surface as cs  # noqa: E402
from product.query import known_authorities as ka  # noqa: E402

SCHEMA = "product-counter-surface-known/1"
DEFAULT_CAPS = (cs.LIVE_HYDRATION_TOP, cs.CACHED_HYDRATION_TOP)
DEFAULT_TOP_N = 100

#: External reference, recorded as context only.  It measured a DIFFERENT
#: surface (adversarial_retrieval/3) on a DIFFERENT pool (the recorded
#: 24-envelope evaluation pool, 14/28 ids reached), so its 0/14 denominator
#: must never be silently subtracted from this measurement's 28 ids.
EXTERNAL_REFERENCE = {
    "anchor_run_id": "39838415410",
    "verdict": "PRODUCT_COUNTER_SIGNAL_LAYER_FALSIFIED_ON_CACHED_SURFACE",
    "surface": "adversarial_retrieval/3",
    "known_n": 14,
    "reached_n": 14,
    "hydrated_n": 5,
    "signalled_n": 0,
    "comparability": "NOT directly comparable: different surface, different pool and a "
                     "14-id denominator (only the ids the evaluation pool reached) versus "
                     "this measurement's 28-id fixture. Recorded for orientation only.",
}


@contextlib.contextmanager
def _no_network():
    """Fail closed during a fixture measurement (a blocked call is recorded)."""
    attempts: list[str] = []
    real_connect = socket.socket.connect

    def _blocked(self, address, *args, **kwargs):  # noqa: ANN001
        attempts.append(repr(address))
        raise AssertionError("fixture measurement attempted network access")

    socket.socket.connect = _blocked
    try:
        yield attempts
    finally:
        socket.socket.connect = real_connect


@contextlib.contextmanager
def _counter_surface_enabled():
    """Build the base bundle with the scan off, then restore the caller's env."""
    saved = os.environ.pop(cs.ENABLE_ENV, None)
    try:
        os.environ[cs.ENABLE_ENV] = "off"
        yield
    finally:
        if saved is None:
            os.environ.pop(cs.ENABLE_ENV, None)
        else:
            os.environ[cs.ENABLE_ENV] = saved


def _build_base_bundle(slug: str, *, top_n: int) -> dict:
    from product.reality_check import LEGS
    from product.query.pipeline import enrich_query_bundle, run_query_initial

    leg = LEGS[slug]
    with _counter_surface_enabled():
        initial = run_query_initial(leg, top_n=top_n, retrieval_mode="fixture")
        return enrich_query_bundle(
            initial, retrieval_mode="fixture", fixture_generation=True
        )


def _scan(bundle: dict, cap: int) -> dict:
    saved = os.environ.pop(cs.ENABLE_ENV, None)
    try:
        return cs.apply_counter_surface(
            bundle, retrieval_mode="fixture", hydrate_top=int(cap)
        )
    finally:
        if saved is not None:
            os.environ[cs.ENABLE_ENV] = saved


def _row_lookup(decisions: Iterable[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for row in decisions or []:
        for core in ka.row_id_cores(row):
            lookup.setdefault(core, row)
    return lookup


def _scan_known_rows(bundle: dict, known: list[str], cap: int) -> tuple[dict, list[dict]]:
    out = _scan(bundle, cap)
    prov = dict((out.get("provenance") or {}).get("counter_surface") or {})
    hydrated_ids = set(str(x) for x in prov.get("hydrated_ids") or [])
    lookup = _row_lookup(out.get("decisions") or [])
    rows: list[dict] = []
    for frozen_id in known:
        row = lookup.get(ka.alnum_core(frozen_id))
        signal = (row or {}).get("counter_surface_signal") if row else None
        rows.append({
            "frozen_id": frozen_id,
            "reached": row is not None,
            "matched_decision_id": (row or {}).get("decision_id") if row else None,
            "hydrated_this_scan": bool(row and str(row.get("decision_id")) in hydrated_ids),
            "signalled": bool(signal),
            "heuristic_status": (signal or {}).get("heuristic_status"),
            "intent": (signal or {}).get("intent"),
            "markers": list((signal or {}).get("markers") or []),
            "text_source": (signal or {}).get("text_source"),
            "evidence": (signal or {}).get("evidence"),
            "counter_status": (row or {}).get("counter_status"),
        })
    summary = {
        "cap": int(cap),
        "n_rows": prov.get("n_rows"),
        "n_hydrated": prov.get("n_hydrated"),
        "n_signalled_total": prov.get("n_signalled"),
        "n_hydrateable_in_pool": prov.get("n_hydrateable_in_pool"),
        "n_selected_for_hydration": prov.get("n_selected_for_hydration"),
        "known_reached_n": sum(1 for r in rows if r["reached"]),
        "known_hydrated_n": sum(1 for r in rows if r["hydrated_this_scan"]),
        "known_signalled_n": sum(1 for r in rows if r["signalled"]),
        "known_signalled_ids": [r["frozen_id"] for r in rows if r["signalled"]],
        "provenance_component": prov.get("component"),
        "hydration_selection_rule": prov.get("hydration_selection_rule"),
    }
    return summary, rows


def measure_leg(slug: str, known: list[str], *, caps: Iterable[int],
                top_n: int = DEFAULT_TOP_N) -> dict:
    bundle = _build_base_bundle(slug, top_n=top_n)
    scans: dict[str, dict] = {}
    for cap in sorted({int(c) for c in caps}):
        summary, rows = _scan_known_rows(bundle, known, cap)
        scans[str(cap)] = {"summary": summary, "known": rows}
    return {
        "slug": slug,
        "query": str(bundle.get("query") or ""),
        "bundle_n": len(bundle.get("decisions") or []),
        "known_n": len(known),
        "scans": scans,
    }


def _aggregate(legs: list[dict], caps: list[int]) -> dict:
    agg: dict = {"known_n": sum(leg["known_n"] for leg in legs), "by_cap": {}}
    for cap in caps:
        key = str(cap)
        per_leg = {leg["slug"]: leg["scans"][key]["summary"] for leg in legs}
        agg["by_cap"][key] = {
            "known_reached_n": sum(s["known_reached_n"] for s in per_leg.values()),
            "known_hydrated_n": sum(s["known_hydrated_n"] for s in per_leg.values()),
            "known_signalled_n": sum(s["known_signalled_n"] for s in per_leg.values()),
            "n_signalled_total": sum(int(s["n_signalled_total"] or 0)
                                     for s in per_leg.values()),
            "n_hydrated": sum(int(s["n_hydrated"] or 0) for s in per_leg.values()),
            "per_leg": per_leg,
        }
    if len(caps) >= 2:
        low, high = str(min(caps)), str(max(caps))
        agg["delta_high_minus_low"] = {
            "low_cap": int(low),
            "high_cap": int(high),
            "known_signalled_n": (agg["by_cap"][high]["known_signalled_n"]
                                  - agg["by_cap"][low]["known_signalled_n"]),
            "n_signalled_total": (agg["by_cap"][high]["n_signalled_total"]
                                  - agg["by_cap"][low]["n_signalled_total"]),
        }
    return agg


def measure(*, fixture_path: Path | None = None, legs: Iterable[str] | None = None,
            caps: Iterable[int] = DEFAULT_CAPS, top_n: int = DEFAULT_TOP_N) -> dict:
    fixture = ka.load_fixture(fixture_path)
    selected = list(legs) if legs else list((fixture.get("questions") or {}))
    caps = sorted({int(c) for c in caps})
    with _no_network() as attempts:
        measured = [
            measure_leg(slug, ka.known_ids(fixture, slug), caps=caps, top_n=top_n)
            for slug in selected
        ]
    aggregate = _aggregate(measured, caps)
    invariants = {
        "network_calls_blocked": len(attempts) == 0,
        "network_attempts": attempts,
        "known_signals_monotone_in_cap": all(
            aggregate["by_cap"][str(high)]["known_signalled_n"]
            >= aggregate["by_cap"][str(low)]["known_signalled_n"]
            for low, high in zip(caps, caps[1:])
        ),
        "same_bundle_across_caps": True,
    }
    source = dict(fixture.get("source") or {})
    return {
        "schema": SCHEMA,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mode": "fixture replay (network blocked; no live fetch)",
        "top_n": int(top_n),
        "caps": caps,
        "counter_surface_version": cs.COUNTER_SURFACE_VERSION,
        "fixture": {
            "path": str(Path(fixture["_fixture_path"]).relative_to(REPO_ROOT)),
            "sha256": fixture["_fixture_sha256"],
            "schema": fixture.get("schema"),
            "source": source,
        },
        "external_reference": EXTERNAL_REFERENCE,
        "legs": measured,
        "aggregate": aggregate,
        "invariants": invariants,
        "interpretation": (
            "On the same four cached pools, the broader cap hydrates more rows and "
            "signals at least as many known authorities. The delta is a surface-reach "
            "delta, not a precision or correctness delta: total signals also rise, so "
            "the broader budget trades additional candidate signals for additional "
            "known-authority reach."
        ),
        "claim_ceiling": (
            "Product-owned coverage measurement over the frozen offline pools. A known "
            "authority counts only when its own rendered text carries a heuristic "
            "limitation sentence under counter_surface/2; the 28 ids are a sample "
            "adopted from the evaluation spec (sha256 recorded above), and 3 are not "
            "reached by the 100-row pools at all. This is NOT the evaluation verdict, "
            "NOT a recall bound, NOT a legal label, and it does not claim the 0/14 "
            "external result is reproduced or reversed: the external measurement used "
            "a different surface, pool and denominator. No network was used."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fixture", type=Path, default=None)
    ap.add_argument("--legs", nargs="+", default=None,
                    help="subset of fixture slugs (default: all)")
    ap.add_argument("--caps", nargs="+", type=int, default=list(DEFAULT_CAPS))
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    out = measure(fixture_path=args.fixture, legs=args.legs,
                  caps=args.caps, top_n=args.top_n)
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
