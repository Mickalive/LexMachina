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

Stage disclosure (why the verdict is three-valued, not two)
-----------------------------------------------------------
``--no-enrich`` is a real and useful mode: the product lane's runtime mandate
wants the query-specific map rendered *before* the answer and counter-authority
passes, and measuring that fast half alone is the point of it.  It is not,
however, a run of the canonical chain, and before this section the record had no
field saying which stages executed.  So a ``--no-enrich`` run published

    "verdict": "PASS"
    "claim_ceiling": "... sourced answer -> counter-authority pass -> ..."
    "answer": {"status": "pending", "n_cited": 0}
    "counters": {"counter_authorities": 0, "counter_status_bearing_rows": 0}

with nothing in the record to tell a reader that the answer and the independent
counter-authority pass never ran.  ``run_query_initial`` emits exactly that
``status: "pending"`` / ``cited_decision_ids: []`` placeholder
(``product/query/pipeline.py``, ``method="pending_generative_audit"``) and no
row carries a ``counter_status``, so the two zeroed fields are the fingerprint
of a map-only run, not a failed answer and not an empty result set.

That is the binding 2026-10-18 defect class - a published claim that does not
reproduce from the committed tree - so the record now publishes
``stages_executed`` and ``mode``, checks ``canonical_chain_ran``, and reports
``PASS_MAP_ONLY`` rather than ``PASS`` when the answer and counter-authority
stages were skipped.  A committed artifact of that class from before this change
is classified by ``product/cycle_verify.py`` check ``live_slice_stages`` and
named in the report of record; it is never silently re-read as a chain PASS.

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

# The status `run_query_initial` stamps on a bundle whose slow phase has not run
# yet. Named here so the stage disclosure and its tests read the same constant
# the placeholder in product/query/pipeline.py means.
PENDING_ANSWER_STATUS = "pending"


def stage_disclosure(*, n_rows: int, enrich: bool, enrich_error: str | None,
                     answer_status: object) -> dict[str, bool]:
    """Which stages of the canonical chain this run actually executed.

    Every term is defined by the code path that produces it, so this is derived
    from the run rather than declared by the caller:

    * ``answer`` is true unless the bundle still carries the ``pending``
      placeholder ``run_query_initial`` stamps (``method=
      "pending_generative_audit"``, ``cited_decision_ids: []``).  A pending
      status means the slow phase never ran; it does NOT mean the answer came
      back empty.
    * ``counter_authority`` is true iff enrichment completed, because
      ``counter_status`` is assigned nowhere else: ``run_query_initial`` writes
      the literal ``"none"`` for every row and only the enrichment phase
      promotes a row to ``cited`` / ``candidate-limiting`` /
      ``abstained_unevidenced``.
    """
    stages = {
        "retrieval": True,
        "map": bool(n_rows),
        "enrichment_attempted": bool(enrich),
        "enrichment_completed": bool(enrich) and not enrich_error,
        "answer": str(answer_status or "") not in ("", PENDING_ANSWER_STATUS),
        "counter_authority": bool(enrich) and not enrich_error,
    }
    stages["canonical_chain"] = all(stages.values())
    return stages


def verdict_for(checks: dict[str, bool], stages: dict[str, bool]) -> str:
    """Three-valued verdict: a map-only run is never reported as a chain PASS.

    ``canonical_chain_ran`` is excluded from the wiring decision because a
    skipped slow phase is not a wiring failure - it is a different, smaller
    claim, and the honest name for it is PASS_MAP_ONLY.
    """
    wiring_ok = all(v for k, v in checks.items() if k != "canonical_chain_ran")
    if not wiring_ok:
        return "FAIL"
    if stages.get("canonical_chain") or checks.get("canonical_chain_ran"):
        return "PASS"
    return "PASS_MAP_ONLY"


def _cache_fingerprint(root: Path | None = None) -> dict[str, int]:
    """relative path -> size for every cache file (an independent freshness probe).

    Sizes are part of the fingerprint on purpose: the adapter rewrites an entry
    in place, so a refreshed body of the same key shows up as a MODIFIED file,
    not as a removal. Reporting that as "removed" would understate what the
    network actually returned.

    ``root`` is the cache directory the ADAPTER is using.  Under
    ``--ephemeral-cache``, ``run()`` redirects ``pipeline.product_cache_dir``
    to a throwaway directory, so the probe must fingerprint THAT root - the
    tracked product cache stays untouched and a genuine fresh retrieval must
    not be reported as "0 files touched" (audit F2, live-measured FAIL 9/10
    against the public API before this parameter existed).
    """
    if root is None:
        root = product_cache_dir()
    out: dict[str, int] = {}
    for p in root.rglob("*"):
        if p.is_file():
            try:
                out[str(p.relative_to(root))] = p.stat().st_size
            except OSError:
                continue
    return out


def _cache_delta(before: dict[str, int], after: dict[str, int]) -> dict:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(p for p in (set(before) & set(after)) if before[p] != after[p])
    return {
        "cache_dir": "results/product/query_cache",
        "files_before": len(before),
        "files_after": len(after),
        "n_files_added": len(added),
        "n_files_modified": len(modified),
        "n_files_removed": len(removed),
        "files_added": added[:20],
        "files_modified": modified[:20],
        "files_removed": removed[:20],
        "n_files_touched": len(added) + len(modified) + len(removed),
    }


def _versions() -> dict:
    import numpy  # noqa: PLC0415

    mods = {"python": sys.version.split()[0], "numpy": numpy.__version__}
    for name, attr in (("scipy", "scipy"), ("sklearn", "sklearn")):
        try:
            mods[name] = getattr(__import__(attr), "__version__", "unknown")
        except Exception:  # pragma: no cover - disclosure only
            mods[name] = None
    return mods


def run(query: str, *, top_n: int, enrich: bool, evidence_count: int,
        cache_root: Path | None = None) -> dict:
    # F1: these two names were imported here at db3891e and the import was
    # dropped by the 39128456801 resume (c1bda4a), so every invocation died
    # with NameError before any network I/O while 13 unit tests stayed green.
    # The import is deliberately INSIDE run(): product.query.pipeline pulls
    # the heavy stack (numpy/sklearn), and live_slice must stay importable
    # in a runtime-less interpreter so the environment check can fail closed.
    from product.query.pipeline import enrich_query_bundle, run_query_initial
    from product.query import pipeline

    if cache_root is not None:
        # A refresh rewrites cache entries IN PLACE, and the tracked product
        # cache is covered by a frozen claim-cache manifest
        # (results/product/CYCLE_38759730609_cache_manifest.json).  Measured
        # consequence of forgetting this: the 39128456801 freshness run turned
        # 19 manifest-covered entries into different bytes and took
        # test_cache_non_orphan.py::test_claim_cache_manifest_is_intact_and_
        # append_tolerant from green to red.  The frozen manifest is historical
        # evidence and is never rewritten from this lane, so a freshness run
        # that must not touch it points the adapter at its own directory.
        cache_root.mkdir(parents=True, exist_ok=True)
        pipeline.product_cache_dir = lambda: cache_root  # type: ignore[assignment]

    # F2: the probe must fingerprint the root the ADAPTER is redirected to,
    # not the module-level cache_path binding.  Resolving it through the
    # pipeline module (the same object run() patches above) makes the
    # independent probe and the adapter agree by construction in both modes.
    probe_root = pipeline.product_cache_dir()

    before = _cache_fingerprint(probe_root)
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

    after = _cache_fingerprint(probe_root)
    cache_delta = _cache_delta(before, after)
    cache_delta["cache_dir"] = str(probe_root.relative_to(REPO_ROOT)) if (
        probe_root.is_relative_to(REPO_ROOT)) else str(probe_root)
    rows = bundle.get("decisions") or []
    final_summary = summarise(bundle)
    languages: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for row in rows:
        lang = str(row.get("language") or "?")
        languages[lang] = languages.get(lang, 0) + 1
        key = str(row.get("counter_status") or "none")
        by_status[key] = by_status.get(key, 0) + 1
    initial_geom = {d.get("decision_id"): (d.get("x"), d.get("y"), d.get("cluster_id"))
                    for d in initial.get("decisions") or []}
    final_geom = {d.get("decision_id"): (d.get("x"), d.get("y"), d.get("cluster_id"))
                  for d in rows}
    # The invariant is "a point the researcher already looked at never moves",
    # NOT "the row set is frozen": enrichment may add adversarial rows and drop
    # shells. Comparing the two dicts outright would report that legitimate row
    # churn as a moved point, so only ids present in BOTH are compared.
    shared = sorted(set(initial_geom) & set(final_geom))
    moved_points = [i for i in shared if initial_geom[i] != final_geom[i]]
    prov = bundle.get("provenance") or {}
    retrieval = prov.get("retrieval") or {}
    remote = retrieval.get("remote") or {}
    summary = remote.get("request_summary") or {}
    cache_stats = remote.get("cache_stats") or {}
    timing = prov.get("timing") or {}
    answer = bundle.get("answer") or {}
    ga = (prov.get("generative_audit") or {})

    # Stage disclosure.  Derived, never asserted, and each term is defined by
    # the code path that produces it - see the module docstring for why this
    # section exists at all.
    stages = stage_disclosure(
        n_rows=len(rows),
        enrich=enrich,
        enrich_error=enrich_error,
        answer_status=answer.get("status"),
    )

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
            "independent_cache_probe": cache_delta,
        },
        "map": {
            "n_decisions": len(rows),
            "n_clusters": len(bundle.get("clusters") or []),
            "rows_with_xy": sum(1 for r in rows if r.get("x") is not None and r.get("y") is not None),
            "rows_with_source_url": sum(1 for r in rows if r.get("canonical_url")),
            "languages": languages,
            "rows_with_cluster_id": final_summary.get("rows_with_cluster_id"),
            "largest_cluster": final_summary.get("largest_cluster"),
            "geometry_preserved_by_enrich": not moved_points,
            "n_decisions_before_enrich": len(initial_geom),
            "n_points_shared_with_initial_map": len(shared),
            "n_points_moved_by_enrichment": len(moved_points),
            "points_moved_by_enrichment": moved_points[:10],
            "rows_added_by_enrichment": sorted(set(final_geom) - set(initial_geom))[:10],
            "n_rows_added_by_enrichment": len(set(final_geom) - set(initial_geom)),
            "n_rows_dropped_by_enrichment": len(set(initial_geom) - set(final_geom)),
        },
        "answer": {
            "status": answer.get("status"),
            "cited_ids": list(answer.get("cited_decision_ids") or []),
            "n_cited": len(answer.get("cited_decision_ids") or []),
            "provider": ga.get("provider") or ga.get("model"),
            "degraded": bool(ga.get("provider_error")) or bool(enrich_error),
            "provider_error": ga.get("provider_error") or enrich_error,
        },
        "stages_executed": stages,
        "mode": "full_chain" if stages["canonical_chain"] else (
            "map_only" if not enrich else "chain_incomplete"),
        "counters": {
            "definition_source": "product/query/counter_status.py (RF1 single source of truth)",
            "counter_authorities": counter_authority_count(rows),
            "counter_status_bearing_rows": counter_status_bearing_count(rows),
            "evidenced_counter_ids": sorted(evidenced_counter_ids(rows)),
            "unevidenced_counter_ids": sorted(unevidenced_counter_ids(rows)),
            "by_status": by_status,
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
            "fail-closed regardless of its verdict. SCOPE OF THIS RECORD IS "
            "stages_executed: a run whose stages_executed.canonical_chain is false "
            "measured only the stages named there, and the sourced answer and the "
            "independent counter-authority pass are NOT among them."
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
    ap.add_argument("--ephemeral-cache", action="store_true",
                    help="retrieve into a throwaway cache dir instead of the tracked "
                         "product cache, whose entries are covered by a frozen "
                         "claim-cache manifest (recommended for freshness checks)")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    cache_root = None
    tmp_cache = None
    if args.ephemeral_cache:
        import tempfile

        tmp_cache = tempfile.TemporaryDirectory(prefix="live-slice-cache-")
        cache_root = Path(tmp_cache.name) / "query_cache"

    try:
        out = run(args.query, top_n=args.n, enrich=not args.no_enrich,
                  evidence_count=args.evidence, cache_root=cache_root)
    finally:
        if tmp_cache is not None:
            tmp_cache.cleanup()
    record, bundle = out["record"], out["bundle"]
    record["run_id"] = tag
    record["cache_root"] = ("ephemeral (outside the tracked product cache)"
                            if cache_root is not None else
                            "results/product/query_cache")

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
        "independent_probe_saw_the_network": fresh["independent_cache_probe"]["n_files_touched"] > 0,
        "enrichment_never_moved_a_point_already_on_the_map":
            record["map"]["geometry_preserved_by_enrich"],
        "map_has_rows": record["map"]["n_decisions"] > 0,
        "every_row_has_xy": record["map"]["rows_with_xy"] == record["map"]["n_decisions"],
        "every_row_has_a_source_link": record["map"]["rows_with_source_url"] == record["map"]["n_decisions"],
        "bundle_validates": not record["bundle_contract"]["validate_bundle_errors"],
        "page_contract_ok": page_ok,
        # The claim-discipline check. Before this entry, `--no-enrich` published
        # verdict PASS together with the canonical chain's claim ceiling while
        # the answer and counter-authority stages demonstrably had not run; this
        # makes that state FAIL rather than PASS, so the three-valued verdict
        # below is the only place the distinction is made. It is reported in
        # n_failed_checks rather than hidden.
        "canonical_chain_ran": record["stages_executed"]["canonical_chain"],
    }
    record["checks"] = checks
    record["verdict"] = verdict_for(checks, record["stages_executed"])
    record["n_failed_checks"] = sorted(k for k, v in checks.items() if not v)
    record["verdict_note"] = (
        "PASS means the canonical chain ran: retrieval, map, enrichment, the "
        "sourced answer and the independent counter-authority pass. "
        "PASS_MAP_ONLY means every wiring, freshness, geometry and page check "
        "passed but stages_executed.canonical_chain is false, so the sourced "
        "answer and the counter-authority pass are NOT covered by this record; "
        "read stages_executed and mode for what was measured. mode=map_only "
        "means the slow phase was never requested (--no-enrich); "
        "mode=chain_incomplete means it was requested and did not finish - read "
        "answer.degraded and answer.provider_error, which name the failure. "
        "FAIL means a wiring, freshness, geometry or page check failed."
    )

    path = OUT_DIR / f"{tag}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{record['verdict']}: {len(checks) - len(record['n_failed_checks'])}/{len(checks)} checks")
    print(f"mode={record['mode']} stages={json.dumps(record['stages_executed'], sort_keys=True)}")
    print(f"n_decisions={record['map']['n_decisions']} n_clusters={record['map']['n_clusters']} "
          f"network_calls={fresh['adapter_network_calls']} cache_hits={fresh['adapter_cache_hits']} "
          f"cache_files_touched={fresh['independent_cache_probe']['n_files_touched']}")
    print(f"counter_authorities={record['counters']['counter_authorities']} "
          f"status_bearing={record['counters']['counter_status_bearing_rows']}")
    print(f"upstream={record['timing_s']['upstream_retrieval_s']}s "
          f"local_map={record['timing_s']['local_map_s']}s total={record['timing_s']['total_s']}s")
    print(f"wrote {path}")
    return 0 if record["verdict"] in ("PASS", "PASS_MAP_ONLY") else 1


if __name__ == "__main__":
    raise SystemExit(main())