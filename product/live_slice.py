#!/usr/bin/env python3
"""Fresh-network vertical slice: OpenCaseLaw -> bundle -> answer -> counters -> map.

    python product/live_slice.py --run-id CYCLE_39128456801 --n 150
    python product/live_slice.py --query "..." --n 200 --no-enrich

Why this exists
---------------
``product/offline_slice.py`` proves the wiring from frozen envelopes, and
``product/slice_smoke.py`` drives the shipped server in *live* mode - but live
mode is ``mode="live"``, which is a **read-through cache**: on a warm cache the
run is indistinguishable from one that never touched the network.  So every
"live" claim so far has been ambiguous about the one thing that matters for the
canonical product (OpenCaseLaw is the canonical public source): did we actually
ask it, and what did it answer today?

The accepted adapter already ships the mode this needs -
``AdapterConfig(mode="refresh")`` = *always network, still writes the cache* -
and ``product/query/pipeline.py`` already forwards ``retrieval_mode`` straight
into it.  This script is therefore a thin, honest driver, not new
infrastructure: it pins ``retrieval_mode="refresh"`` end to end and records
**three independent proofs of freshness** in the artifact:

1. ``provenance.retrieval.remote.request_summary`` - the adapter's own counters
   (``cache_hits`` must be 0, ``network_calls`` must be > 0);
2. ``cache_stats`` - hits/misses/writes as the adapter measured them;
3. an independent before/after diff of the product-owned cache directory, so
   the proof does not rest on the same instrument twice.

What it claims
--------------
A **fresh-network wiring + budget** measurement of the canonical vertical slice
(``query -> query_result_bundle -> sourced answer -> counter-authority pass ->
clickable map``) executed against the live public API today, plus the measured
upstream-vs-local latency split and the counter-authority counts under the
accepted single source of truth.  It is NOT a bar score, NOT an audit verdict,
NOT a legal-usefulness claim and NOT a human-gate input.  Admission stays
fail-closed whatever it prints.

Writes: ``results/product/live_slice/<run_id>.json`` (+ ``<run_id>_bundle.json``).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
sys.path.insert(0, str(PRODUCT_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from product.offline_slice import summarise, verify_page  # noqa: E402
from product.query.bundle import validate_bundle  # noqa: E402
from product.query.cache_path import product_cache_dir  # noqa: E402
from product.query.counter_status import (  # noqa: E402
    counter_authority_count,
    counter_status_bearing_count,
    evidenced_counter_ids,
    unevidenced_counter_ids,
)

OUT_DIR = REPO_ROOT / "results" / "product" / "live_slice"

DEFAULT_QUERY = "Responsabilite penale de l'entreprise selon l'art. 102 CP"

# Directive budgets (product lane "Runtime performance mandate"). Upstream
# OpenCaseLaw time is measured separately and never charged to local code.
BUDGET_LOCAL_MAP_S = 1.5
BUDGET_GEOMETRY_S = 2.0


def _cache_fingerprint() -> set[tuple[str, int]]:
    """(relative path, size) for every cache file - an independent freshness probe."""
    root = product_cache_dir()
    out: set[tuple[str, int]] = set()
    for p in root.rglob("*"):
        if p.is_file():
            try:
                out.add((str(p.relative_to(root)), p.stat().st_size))
            except OSError:
                continue
    return out


def _versions() -> dict:
    import numpy  # noqa: PLC0415

    mods = {"python": sys.version.split()[0], "numpy": numpy.__version__}
    for name, attr in (("scipy", "scipy"), ("sklearn", "sklearn")):
        try:
            mods[name] = getattr(__import__(attr), "__version__", "unknown")
        except Exception:  # pragma: no cover - disclosure only
            mods[name] = None
    return mods


def run(query: str, *, top_n: int, enrich: bool, evidence_count: int) -> dict:
    from product.query.pipeline import enrich_query_bundle, run_query_initial

    before = _cache_fingerprint()
    t0 = time.time()
    initial = run_query_initial(query, top_n=top_n, retrieval_mode="refresh")
    t_initial = time.time() - t0

    bundle = initial
    enrich_error = None
    if enrich:
        t1 = time.time()
        try:
            bundle = enrich_query_bundle(
                initial, retrieval_mode="refresh", evidence_count=evidence_count
            )
        except Exception as exc:  # the map half is still real evidence
            enrich_error = f"{type(exc).__name__}: {exc}"
            bundle = initial
        enrich_s = time.time() - t1
    else:
        enrich_s = 0.0
    total_s = time.time() - t0

    after = _cache_fingerprint()
    written = sorted(p for p, _size in (after - before))
    removed = sorted(p for p, _size in (before - after))

    prov = bundle.get("provenance") or {}
    retrieval = prov.get("retrieval") or {}
    remote = retrieval.get("remote") or {}
    summary = remote.get("request_summary") or {}
    cache_stats = remote.get("cache_stats") or {}
    timing = prov.get("timing") or {}
    rows = bundle.get("decisions") or []
    answer = bundle.get("answer") or {}
    ga = (prov.get("generative_audit") or {})

    record = {
        "schema": "product-live-slice/1",
        "run_id": None,
        "produced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query": query,
        "retrieval_mode_requested": "refresh",
        "retrieval_mode_served": remote.get("mode"),
        "base_url": remote.get("base_url"),
        "freshness": {
            "claim": "retrieval went to the live OpenCaseLaw API, not to a warm cache",
            "adapter_cache_hits": summary.get("cache_hits"),
            "adapter_network_calls": summary.get("network_calls"),
            "adapter_requests_logged": summary.get("requests_logged"),
            "adapter_cache_stats": cache_stats,
            "adapter_failures": summary.get("failures"),
            "adapter_degraded": remote.get("degraded"),
            "independent_cache_probe": {
                "cache_dir": "results/product/query_cache",
                "files_before": len(before),
                "files_after": len(after),
                "files_written": written[:20],
                "n_files_written": len(written),
                "files_removed": removed[:20],
            },
        },
        "map": {
            "n_decisions": len(rows),
            "n_clusters": len(bundle.get("clusters") or []),
            "rows_with_xy": sum(1 for r in rows if r.get("x") is not None and r.get("y") is not None),
            "rows_with_source_url": sum(1 for r in rows if r.get("canonical_url")),
            "languages": summarise(bundle).get("languages"),
            "geometry_preserved_by_enrich": summarise(bundle).get("geometry_preserved_by_enrich"),
        },
        "answer": {
            "status": answer.get("status"),
            "cited_ids": list(answer.get("cited_decision_ids") or []),
            "n_cited": len(answer.get("cited_decision_ids") or []),
            "provider": ga.get("provider") or ga.get("model"),
            "degraded": bool(ga.get("provider_error")) or bool(enrich_error),
            "provider_error": ga.get("provider_error") or enrich_error,
        },
        "counters": {
            "definition_source": "product/query/counter_status.py (RF1 single source of truth)",
            "counter_authorities": counter_authority_count(rows),
            "counter_status_bearing_rows": counter_status_bearing_count(rows),
            "evidenced_counter_ids": sorted(evidenced_counter_ids(rows)),
            "unevidenced_counter_ids": sorted(unevidenced_counter_ids(rows)),
            "by_status": summarise(bundle).get("by_status"),
        },
        "timing_s": {
            "upstream_retrieval_s": timing.get("upstream_retrieval_s"),
            "local_map_s": timing.get("local_map_s"),
            "initial_total_s": round(t_initial, 3),
            "enrich_s": round(enrich_s, 3),
            "total_s": round(total_s, 3),
            "budget_local_map_s": BUDGET_LOCAL_MAP_S,
            "budget_geometry_s": BUDGET_GEOMETRY_S,
            "local_map_within_budget": (
                None if timing.get("local_map_s") is None
                else float(timing["local_map_s"]) <= BUDGET_LOCAL_MAP_S
            ),
        },
        "bundle_contract": {
            "validate_bundle_errors": validate_bundle(bundle),
        },
        "environment": _versions(),
        "claim_ceiling": (
            "A fresh-network wiring and latency measurement of the canonical vertical "
            "slice (query -> query_result_bundle -> sourced answer -> counter-authority "
            "pass -> clickable map) against the live public OpenCaseLaw API on this tree. "
            "It scores no frozen bar, reads no Frontier verdict, issues no serve "
            "recommendation and makes no legal-usefulness claim. Admission stays "
            "fail-closed regardless of its verdict."
        ),
        "posture": {
            "machine_gate_ready": False,
            "human_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
        },
    }
    return {"record": record, "bundle": bundle}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=None, help="stamped into the artifact name")
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--n", type=int, default=150, help="target decisions (100-300)")
    ap.add_argument("--evidence", type=int, default=12, help="decisions hydrated for the answer")
    ap.add_argument("--no-enrich", action="store_true",
                    help="map-only: skip the answer + counter-authority pass")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    out = run(args.query, top_n=args.n, enrich=not args.no_enrich, evidence_count=args.evidence)
    record, bundle = out["record"], out["bundle"]
    record["run_id"] = tag

    bundle_path = OUT_DIR / f"{tag}_bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=1, sort_keys=True), encoding="utf-8")
    page_ok, page_msg = verify_page(bundle_path)
    record["page_contract"] = {
        "verifier": "product/verify_query_page.js",
        "ok": page_ok,
        "message": page_msg,
        "note": "node absent means the DOM contract was not checked; the claim is "
                "reported as unchecked, never as a pass",
    }

    fresh = record["freshness"]
    checks = {
        "retrieval_mode_served_is_refresh": record["retrieval_mode_served"] == "refresh",
        "no_cache_hits_on_the_network_leg": fresh["adapter_cache_hits"] == 0,
        "adapter_made_network_calls": (fresh["adapter_network_calls"] or 0) > 0,
        "independent_probe_saw_new_cache_files": fresh["independent_cache_probe"]["n_files_written"] > 0,
        "map_has_rows": record["map"]["n_decisions"] > 0,
        "every_row_has_xy": record["map"]["rows_with_xy"] == record["map"]["n_decisions"],
        "every_row_has_a_source_link": record["map"]["rows_with_source_url"] == record["map"]["n_decisions"],
        "bundle_validates": not record["bundle_contract"]["validate_bundle_errors"],
        "page_contract_ok": page_ok,
    }
    record["checks"] = checks
    record["verdict"] = "PASS" if all(checks.values()) else "FAIL"
    record["n_failed_checks"] = sorted(k for k, v in checks.items() if not v)

    path = OUT_DIR / f"{tag}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{record['verdict']}: {len(checks) - len(record['n_failed_checks'])}/{len(checks)} checks")
    print(f"n_decisions={record['map']['n_decisions']} n_clusters={record['map']['n_clusters']} "
          f"network_calls={fresh['adapter_network_calls']} cache_hits={fresh['adapter_cache_hits']} "
          f"new_cache_files={fresh['independent_cache_probe']['n_files_written']}")
    print(f"counter_authorities={record['counters']['counter_authorities']} "
          f"status_bearing={record['counters']['counter_status_bearing_rows']}")
    print(f"upstream={record['timing_s']['upstream_retrieval_s']}s "
          f"local_map={record['timing_s']['local_map_s']}s total={record['timing_s']['total_s']}s")
    print(f"wrote {path}")
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())