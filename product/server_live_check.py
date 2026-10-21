#!/usr/bin/env python3
"""Drive the SHIPPED query server over HTTP and prove what the owner sees.

    python product/server_live_check.py --run-id CYCLE_39667945530_SRV1
    python product/server_live_check.py --query "..." --n 150 --port 8787

Why this exists
---------------
``product/live_slice.py`` proves the *chain* (OpenCaseLaw -> bundle -> answer
-> counters -> map) by calling the product functions directly, and
``product/offline_slice.py`` proves the *wiring* from frozen envelopes.  Neither
one proves the thing the owner actually touches: the HTTP API of
``product/query_app.py`` that the browser page in ``product/static/query.html``
consumes.  The server runs the same ``enrich_query_bundle`` the slice runs, but
"same function" is a code-reading claim, not a measurement.

So this script starts the real server (in-process, on an ephemeral port, live
mode), drives the three public stages over HTTP exactly as the page does
(``/api/query/start`` -> ``/api/query/expand`` -> ``/api/query/enrich``), pulls
the served bundle back through ``/api/query/bundle``, and checks what the
browser would receive:

* the UI shell is served,
* the first-page map arrives with xy on every row,
* the enrich job finishes and the answer is a **sourced generative** answer
  (status ``ready``, prose, cited decision ids) and not the degraded
  extractive fallback,
* the independent counter-authority pass produced counter authorities,
* the served bundle passes the product's own bundle validation and the page
  contract (``product/verify_query_page.js``, the same check the offline slice
  runs),
* enrichment did not move a point that was already on the map.

What it claims
--------------
A measurement of the *served* product path (HTTP API -> bundle -> rendered
answer + counter authorities + map) executed today against the live public
API.  It is NOT a bar score, NOT an audit verdict, NOT a legal-usefulness
claim and NOT a human-gate input; admission stays fail-closed whatever it
prints.  Freshness of the retrieval is a separate claim: the server's ``live``
mode is a read-through cache, so the fresh-network proof lives in
``product/live_slice.py`` (``retrieval_mode="refresh"``).  This record publishes
the adapter's own counters so the reader can see which leg it was.

Writes: ``results/product/server_live_check/<run_id>.json``
(``+ <run_id>_bundle.json``, the bundle exactly as served).
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT_DIR = REPO_ROOT / "results" / "product" / "server_live_check"

DEFAULT_QUERY = "Kündigung Mietvertrag Mietrecht"


def _get(url: str, timeout: float) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, resp.read()


def _get_json(url: str, timeout: float) -> dict:
    status, body = _get(url, timeout=timeout)
    if status != 200:
        raise RuntimeError(f"GET {url} -> HTTP {status}")
    return json.loads(body.decode("utf-8"))


def _wait_job(base: str, run_id: str, name: str, wait_s: float) -> dict:
    """Block until a job is done, exactly like the page's ``&wait_s=`` calls."""
    url = f"{base}/api/query/status?run_id={urllib.parse.quote(run_id)}"
    deadline = time.time() + wait_s
    while time.time() < deadline:
        status = _get_json(url, timeout=30.0)
        job = (status.get("jobs") or {}).get(name) or {}
        if job.get("status") in {"done", "error"}:
            return job
        time.sleep(0.5)
    return {"status": "timeout", "waited_s": wait_s}


def run(query: str, *, top_n: int, run_id: str, host: str = "127.0.0.1") -> dict:
    # Heavy imports (numpy/sklearn) live inside the product package; the
    # server imports them lazily, so the check script keeps the same shape.
    from product.offline_slice import summarise, verify_page
    from product.query.bundle import validate_bundle
    from product.query.counter_status import (
        counter_authority_count,
        counter_status_bearing_count,
    )
    import query_app

    srv = query_app.make_server(host, 0, fixture_mode=False, verbose=False)
    port = srv.server_address[1]
    base = f"http://{host}:{port}"
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()

    checks: dict[str, bool] = {}
    detail: dict[str, object] = {}
    t_all = time.time()
    try:
        health = _get_json(f"{base}/api/health", timeout=30.0)
        checks["server_health_ok"] = bool(health.get("ok"))
        detail["health"] = health

        status, shell = _get(f"{base}/", timeout=30.0)
        checks["ui_shell_served"] = (
            status == 200 and b'id="prose"' in shell and b"canvas" in shell.lower()
        )
        detail["ui_shell_bytes"] = len(shell)

        t0 = time.time()
        start = _get_json(
            f"{base}/api/query/start?q={urllib.parse.quote(query)}&n={top_n}", timeout=600.0)
        t_start = time.time() - t0
        run_id_served = start.get("run_id")
        if not run_id_served:
            raise RuntimeError(f"no run_id from /api/query/start: {start}")
        first = start.get("bundle") or {}
        first_rows = first.get("decisions") or []
        checks["first_page_map_served"] = bool(first_rows) and all(
            isinstance(r.get("x"), (int, float)) and isinstance(r.get("y"), (int, float))
            for r in first_rows
        )
        detail["first_page"] = {
            "n_decisions": len(first_rows),
            "answer_status": (first.get("answer") or {}).get("status"),
        }

        t1 = time.time()
        expand = _get_json(
            f"{base}/api/query/expand?run_id={urllib.parse.quote(run_id_served)}&wait_s=900",
            timeout=960.0)
        t_expand = time.time() - t1
        expand_job = (expand.get("job") or {})
        checks["expand_job_done"] = expand_job.get("status") == "done"

        t2 = time.time()
        enrich = _get_json(
            f"{base}/api/query/enrich?run_id={urllib.parse.quote(run_id_served)}&wait_s=1200",
            timeout=1260.0)
        t_enrich = time.time() - t2
        enrich_job = (enrich.get("job") or {})
        checks["enrich_job_done"] = enrich_job.get("status") == "done"
        detail["enrich_job"] = enrich_job

        served = _get_json(
            f"{base}/api/query/bundle?run_id={urllib.parse.quote(run_id_served)}", timeout=120.0)
        bundle = served.get("bundle") or {}
        rows = bundle.get("decisions") or []
        answer = bundle.get("answer") or {}
        prose = str(answer.get("prose") or "")
        cited = list(answer.get("cited_decision_ids") or [])

        errors = validate_bundle(bundle)
        checks["served_bundle_validates"] = not errors
        detail["bundle_validation_errors"] = errors

        checks["answer_is_generative_and_ready"] = (
            answer.get("status") == "ready"
            and not answer.get("degraded")
            and answer.get("method") != "extractive_tfidf_v1"
        )
        checks["answer_has_prose"] = len(prose.strip()) >= 200
        checks["answer_cites_decisions"] = bool(cited)
        checks["answer_prose_carries_citation_markers"] = "[" in prose and "]" in prose
        detail["answer"] = {
            "status": answer.get("status"),
            "degraded": answer.get("degraded"),
            "method": answer.get("method"),
            "model": answer.get("model"),
            "provider": answer.get("provider"),
            "n_cited": len(cited),
            "cited_decision_ids": cited,
            "prose_head": prose[:600],
        }

        n_counter = counter_authority_count(rows)
        n_bearing = counter_status_bearing_count(rows)
        checks["counter_authorities_found"] = n_counter >= 1
        detail["counters"] = {
            "counter_authorities": n_counter,
            "counter_status_bearing_rows": n_bearing,
        }

        checks["map_rows_have_xy"] = all(
            isinstance(r.get("x"), (int, float)) and isinstance(r.get("y"), (int, float))
            for r in rows) and bool(rows)
        checks["map_rows_have_source_link"] = all(r.get("canonical_url") for r in rows) and bool(rows)

        first_geom = {r.get("decision_id"): (r.get("x"), r.get("y"), r.get("cluster_id"))
                      for r in first_rows}
        final_geom = {r.get("decision_id"): (r.get("x"), r.get("y"), r.get("cluster_id"))
                      for r in rows}
        shared = sorted(set(first_geom) & set(final_geom))
        moved = [i for i in shared if first_geom[i] != final_geom[i]]
        checks["enrichment_moved_no_visible_point"] = not moved
        detail["moved_points"] = moved[:10]

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        bundle_path = OUT_DIR / f"{run_id}_bundle.json"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=1))
        page_ok, page_out = verify_page(bundle_path)
        checks["page_contract_ok"] = bool(page_ok)
        detail["page_contract"] = page_out

        summary = summarise(bundle)
        retrieval = (bundle.get("provenance") or {}).get("retrieval") or {}
        remote = retrieval.get("remote") or {}
        record = {
            "schema": "product-server-live-check/1",
            "run_id": run_id,
            "served_run_id": run_id_served,
            "produced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query": query,
            "server": {"host": host, "port": port, "mode": "live OpenCaseLaw (read-through cache)"},
            "timing_s": {
                "start_s": round(t_start, 3),
                "expand_s": round(t_expand, 3),
                "enrich_s": round(t_enrich, 3),
                "total_s": round(time.time() - t_all, 3),
            },
            "retrieval_counters": {
                "mode": remote.get("mode"),
                "base_url": remote.get("base_url"),
                "request_summary": remote.get("request_summary"),
                "cache_stats": remote.get("cache_stats"),
            },
            "map": {
                "n_decisions": len(rows),
                "n_clusters": len(bundle.get("clusters") or []),
                "rows_with_xy": summary.get("rows_with_xy"),
                "rows_with_source_url": summary.get("rows_with_source_url"),
                "largest_cluster": summary.get("largest_cluster"),
            },
            "answer": detail.get("answer"),
            "counters": detail.get("counters"),
            "checks": checks,
            "verdict": "PASS" if all(checks.values()) else "FAIL",
            "claim_ceiling": (
                "Measurement of the served product path (HTTP API -> query_result_bundle -> "
                "sourced generative answer -> independent counter-authority pass -> map) "
                "executed today against the live public API through the shipped server. "
                "Not a bar score, not an audit verdict, not a legal-usefulness claim and "
                "not a human-gate input; admission stays fail-closed. The server's live "
                "mode is a read-through cache, so the fresh-network proof is the separate "
                "live_slice artifact."
            ),
            "bundle_path": str(bundle_path.relative_to(REPO_ROOT)),
        }
    finally:
        srv.shutdown()
        srv.server_close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{run_id}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1))
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--run-id", default=time.strftime("CYCLE_%Y%m%dT%H%M%SZ", time.gmtime()))
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)

    record = run(args.query, top_n=args.n, run_id=args.run_id, host=args.host)
    for name, ok in record["checks"].items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{record['verdict']}: {sum(1 for v in record['checks'].values() if v)}"
          f"/{len(record['checks'])} checks")
    print("timing:", json.dumps(record["timing_s"]))
    print("answer:", json.dumps({
        "status": (record.get("answer") or {}).get("status"),
        "model": (record.get("answer") or {}).get("model"),
        "n_cited": (record.get("answer") or {}).get("n_cited"),
    }))
    print("counters:", json.dumps(record.get("counters")))
    print(f"wrote {OUT_DIR / (args.run_id + '.json')}")
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
