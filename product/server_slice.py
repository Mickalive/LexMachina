#!/usr/bin/env python3
"""One-command SERVED vertical slice: shipped HTTP server -> bundle -> clickable page.

    python product/server_slice.py --run-id 39202428670
    python product/server_slice.py --query "Kündigung Mietvertrag Mietrecht" --n 100
    python product/server_slice.py --out /tmp/opencode/served --no-write

Why this exists
---------------
``product/offline_slice.py`` proves the PIPELINE (query -> bundle -> sourced
answer -> counter pass -> map, network trapped). ``product/query_app.py`` and
``product/tests/test_progressive_query.py`` prove the SERVER (the three-stage job
contract over HTTP). ``product/verify_query_page.js`` proves the PAGE contract
on a bundle read from disk.

What no committed instrument proved is the combination a jurist actually
touches: the shipped ``Handler``, driven over a real socket exactly the way the
browser drives it (``/api/query/start`` -> expand -> ``/api/query/enrich`` ->
``/api/query/bundle``), returning a bundle that the shipped page then renders as
a clickable, source-linked map. This module is that seam, and it is deliberately
a *composition* of the accepted components above — it adds no retrieval, no
clustering, no generation and no scoring of its own.

Checks (each one is a row in the summary; one FAIL makes the verdict FAIL)
--------------------------------------------------------------------------
1. the non-loopback socket trap is armed and provably blocks an outbound connect;
2. the shipped server boots and answers ``/api/health`` in fixture mode;
3. ``GET /`` serves the shipped ``static/query.html`` byte-for-byte;
4. ``/api/query/start`` returns a valid first-page ``query_result_bundle`` with
   coordinates, cluster ids and a source link on every row;
5. the background expansion finishes and moves/drops no rendered point;
6. ``/api/query/enrich`` delivers a sourced answer (cited >= 1) over the same
   run, still without moving a rendered point;
7. ``/api/query/bundle`` round-trips the same bundle twice (reload contract);
8. both counter definitions are published, the broad one beside the narrow one;
9. ``node product/verify_query_page.js`` renders the SERVED bundle and the page
   contract passes.

Every non-loopback ``socket.connect`` during the whole run is trapped, so the
slice provably ran without leaving the machine.

Claim ceiling: wiring evidence for the SERVED fixture path on this machine. It
scores no frozen bar, measures no live OpenCaseLaw latency, makes no legal
usefulness claim and is not a human-gate input.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_QUERY = "Kündigung Mietvertrag Mietrecht"
SCHEMA = "product-server-slice/1"
CLAIM_CEILING = (
    "WIRING EVIDENCE for the served fixture path only: shipped HTTP handler -> "
    "query_result_bundle -> shipped page, run on this machine with the fixture "
    "retrieval/generation providers and every non-loopback connect trapped. It "
    "scores no frozen bar, measures no live OpenCaseLaw latency, evaluates no "
    "answer quality and makes no legal-usefulness or human-gate claim."
)

#: Hosts the served slice is ALLOWED to connect to: its own loopback server.
#: Everything else raises before a packet leaves the machine, so "no network"
#: is an enforced property of the run rather than a sentence in a docstring.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "0.0.0.0"})


def _host_of(address) -> str:
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, bytes):
        host = host.decode("utf-8", "replace")
    return str(host)


def install_loopback_guard():
    """Trap every non-loopback connect; return a callable that restores it."""
    real_connect = socket.socket.connect

    def guarded(self, address, *args, **kwargs):
        host = _host_of(address)
        if host in LOOPBACK_HOSTS:
            return real_connect(self, address, *args, **kwargs)
        raise AssertionError(f"non-loopback connect blocked in served slice: {address!r}")

    socket.socket.connect = guarded  # type: ignore[method-assign]

    def restore() -> None:
        socket.socket.connect = real_connect  # type: ignore[method-assign]

    return restore


def _geometry(bundle: dict) -> dict:
    return {
        d.get("decision_id"): (d.get("x"), d.get("y"), d.get("cluster_id"))
        for d in bundle.get("decisions") or []
    }


def _preserved(first: dict, later: dict) -> tuple[bool, list]:
    """Every point already rendered still exists at the same coordinates."""
    before, after = _geometry(first), _geometry(later)
    missing = sorted(str(k) for k in before if k not in after)
    moved = sorted(str(k) for k, geo in before.items() if after.get(k) != geo)
    return (not missing and not moved), missing + moved


class _Http:
    """Minimal client against one running query_app server (real socket)."""

    def __init__(self, base: str):
        self.base = base

    def get(self, path: str, timeout: float = 300.0) -> tuple[int, dict | str]:
        url = self.base + path
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                raw = resp.read()
                code = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read() or b""
            code = exc.code
        try:
            return code, json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            # Non-JSON (the HTML page): handed back as BYTES so a byte-for-byte
            # comparison against the shipped file cannot survive a decode round.
            return code, raw


def _rows(result: dict, claim: str, ok: bool, observed, definition: str) -> None:
    result["checks"].append({
        "claim": claim,
        "status": "PASS" if ok else "FAIL",
        "observed": observed,
        "definition_source": definition,
    })
    if not ok:
        result["failures"].append(claim)


def _await_job(http: _Http, run_id: str, name: str, limit_s: float) -> dict:
    deadline = time.time() + limit_s
    last: dict = {}
    while time.time() < deadline:
        code, st = http.get(f"/api/query/status?run_id={run_id}", timeout=60)
        if code == 200 and isinstance(st, dict):
            last = (st.get("jobs") or {}).get(name) or {}
            if last.get("status") in {"done", "error"}:
                return last
        time.sleep(0.25)
    return last


def execute(
    query: str = DEFAULT_QUERY,
    top_n: int = 100,
    *,
    expand_wait_s: float = 600.0,
    enrich_wait_s: float = 600.0,
    node_timeout: int = 300,
) -> dict:
    """Run the served slice end to end. Returns the summary dict (never raises
    for an ordinary product failure — a failure becomes a FAIL row)."""
    from query_app import make_server
    from query.bundle import validate_bundle
    from query.counter_status import (
        counter_authority_count,
        counter_status_bearing_count,
    )

    result: dict = {
        "schema": SCHEMA,
        "query": query,
        "top_n": top_n,
        "mode": "fixture",
        "checks": [],
        "failures": [],
        "verdict": "FAIL",
        "timing_s": {},
        "counts": {},
        "claim_ceiling": CLAIM_CEILING,
    }

    restore_guard = install_loopback_guard()
    srv = None
    thread = None
    t_start = time.time()
    try:
        # Non-vacuity, before anything else runs: the trap must actually block.
        probe = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("192.0.2.1", 80))  # TEST-NET-1, never reached
                probe = "CONNECTED - the trap is NOT armed"
            except AssertionError:
                probe = "blocked before any packet left the machine"
            finally:
                sock.close()
        except Exception as exc:  # pragma: no cover - defensive
            probe = f"{type(exc).__name__}: {exc}"
        _rows(result,
              "the non-loopback trap is armed and provably blocks an outbound connect",
              probe == "blocked before any packet left the machine",
              {"probe": probe},
              "product/server_slice.py::install_loopback_guard")

        from threading import Thread

        srv = make_server("127.0.0.1", 0, fixture_mode=True, verbose=False)
        thread = Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        http = _Http(f"http://127.0.0.1:{srv.server_address[1]}")

        # 1. health / fixture mode -------------------------------------------
        code, health = http.get("/api/health", timeout=30)
        _rows(result, "the shipped server answers /api/health in fixture mode",
              code == 200 and isinstance(health, dict)
              and health.get("ok") is True and health.get("fixture_mode") is True,
              {"http": code, "fixture_mode": (health or {}).get("fixture_mode")
               if isinstance(health, dict) else None,
               "pipeline": (health or {}).get("pipeline") if isinstance(health, dict) else None},
              "product/query_app.py Handler /api/health")

        # 2. the shipped page -------------------------------------------------
        code, page = http.get("/", timeout=30)
        shipped = (PRODUCT_ROOT / "static" / "query.html").read_bytes()
        served_bytes = page if isinstance(page, bytes) else b""
        _rows(result, "GET / serves the shipped query.html byte-for-byte",
              code == 200 and served_bytes == shipped,
              {"http": code, "served_bytes": len(served_bytes),
               "shipped_bytes": len(shipped)},
              "product/static/query.html")

        # 3. first page map ---------------------------------------------------
        t0 = time.time()
        code, payload = http.get(
            "/api/query/start?" + urllib.parse.urlencode({"q": query, "n": top_n}),
            timeout=600)
        result["timing_s"]["start_http_s"] = round(time.time() - t0, 3)
        run_id = payload.get("run_id") if isinstance(payload, dict) else None
        first = payload.get("bundle") if isinstance(payload, dict) else None
        first_errors = validate_bundle(first) if isinstance(first, dict) else ["no bundle"]
        rows = (first or {}).get("decisions") or []
        clusters = (first or {}).get("clusters") or []
        with_xy = sum(1 for d in rows if isinstance(d.get("x"), (int, float))
                      and isinstance(d.get("y"), (int, float)))
        with_cid = sum(1 for d in rows if d.get("cluster_id") is not None)
        with_url = sum(1 for d in rows if str(d.get("canonical_url") or "").startswith(
            "https://mcp.opencaselaw.ch/"))
        _rows(result,
              "the first page is a valid complete map bundle, not a placeholder",
              code == 200 and bool(run_id) and not first_errors
              and len(rows) >= 50 and len(clusters) >= 2
              and with_xy == with_cid == with_url == len(rows),
              {"http": code, "run_id": run_id, "validate_bundle": first_errors,
               "n_decisions": len(rows), "n_clusters": len(clusters),
               "rows_with_xy": with_xy, "rows_with_cluster_id": with_cid,
               "rows_with_source_url": with_url,
               "phase": (first or {}).get("provenance", {}).get("phase"),
               "answer_status": (first or {}).get("answer", {}).get("status")},
              "product/query/bundle.py::validate_bundle + product/query_app.py /api/query/start")
        if not run_id or not isinstance(first, dict) or first_errors:
            result["timing_s"]["total_s"] = round(time.time() - t_start, 3)
            result["verdict"] = "FAIL"  # never return an unset verdict
            return result

        result["_first_page_bundle"] = first
        result["counts"]["n_first_page"] = len(rows)
        result["counts"]["n_clusters_first_page"] = len(clusters)

        # 4. background expansion --------------------------------------------
        t0 = time.time()
        expand_job = _await_job(http, run_id, "expand", expand_wait_s)
        result["timing_s"]["expand_job_s"] = round(time.time() - t0, 3)
        code, after_expand = http.get(f"/api/query/bundle?run_id={run_id}", timeout=300)
        expanded = after_expand.get("bundle") if isinstance(after_expand, dict) else None
        ok_geo_expand, bad_expand = _preserved(first, expanded or {})
        prog = ((expanded or {}).get("provenance") or {}).get("progressive") or {}
        _rows(result,
              "expansion finished and moved or dropped no rendered point",
              code == 200 and isinstance(expanded, dict)
              and expand_job.get("status") == "done" and ok_geo_expand
              and prog.get("points_moved") == 0
              and validate_bundle(expanded) == [],
              {"http": code, "expand_job": expand_job.get("status"),
               "points_moved": prog.get("points_moved"),
               "geometry_preserved": ok_geo_expand,
               "moved_or_missing": bad_expand[:5],
               "n_before": prog.get("n_before"), "n_after": prog.get("n_after"),
               "expand_job_s": expand_job.get("elapsed_s")},
              "product/query_app.py::_expand_task + product/query/progressive.py")

        # 5. sourced answer + counter pass ------------------------------------
        t0 = time.time()
        code, ack = http.get(f"/api/query/enrich?run_id={run_id}", timeout=60)
        result["timing_s"]["enrich_accept_http_s"] = round(time.time() - t0, 3)
        t0 = time.time()
        enrich_job = _await_job(http, run_id, "enrich", enrich_wait_s)
        result["timing_s"]["enrich_job_s"] = round(time.time() - t0, 3)
        code, final_payload = http.get(f"/api/query/bundle?run_id={run_id}", timeout=300)
        final = final_payload.get("bundle") if isinstance(final_payload, dict) else None
        final = final if isinstance(final, dict) else {}
        answer = final.get("answer") or {}
        cited = answer.get("cited_decision_ids") or []
        final_errors = validate_bundle(final) if final.get("decisions") else ["no bundle"]
        ok_geo_final, bad_final = _preserved(first, final)
        _rows(result,
              "the served run ends with a sourced answer that cites retrieved decisions",
              code == 200 and not final_errors and answer.get("status") == "ready"
              and len(cited) >= 1 and (final.get("provenance") or {}).get("phase") == "complete",
              {"http": code, "validate_bundle": final_errors,
               "answer_status": answer.get("status"), "n_cited": len(cited),
               "cited_decision_ids": list(cited),
               "phase": (final.get("provenance") or {}).get("phase"),
               "method": answer.get("method")},
              "product/query/answer.py + product/query_app.py::_enrich_task")
        _rows(result,
              "enrichment preserved the geometry the map had already rendered",
              ok_geo_final and bool(final.get("decisions")),
              {"geometry_preserved": ok_geo_final,
               "moved_or_missing": bad_final[:5],
               "n_first_page": len(_geometry(first)),
               "n_final": len(_geometry(final))},
              "product/server_slice.py::_preserved")

        # 6. reload/bundle round-trip ----------------------------------------
        code2, again = http.get(f"/api/query/bundle?run_id={run_id}", timeout=300)
        again_bundle = again.get("bundle") if isinstance(again, dict) else None
        _rows(result,
              "/api/query/bundle round-trips the identical bundle on a reload",
              code == 200 and code2 == 200 and again_bundle == final,
              {"first_http": code, "second_http": code2,
               "identical": again_bundle == final},
              "product/query_app.py /api/query/bundle")

        # 7. both counter definitions ----------------------------------------
        rows_final = final.get("decisions") or []
        n_counter = counter_authority_count(rows_final)
        n_bearing = counter_status_bearing_count(rows_final)
        status_counts = (status_payload(http, run_id).get("counts") or {})
        result["counts"].update({
            "n_final": len(rows_final),
            "n_clusters_final": len(final.get("clusters") or []),
            "n_cited": len(cited),
            "counter_authorities": n_counter,
            "counter_status_bearing_rows": n_bearing,
            "rows_with_source_url": sum(
                1 for d in rows_final
                if str(d.get("canonical_url") or "").startswith("https://mcp.opencaselaw.ch/")),
        })
        _rows(result,
              "both counter definitions are published, broad beside narrow",
              n_counter >= 0 and n_bearing >= n_counter
              and "counter" not in status_counts
              and status_counts.get("counter_authorities") == n_counter
              and status_counts.get("counter_status_bearing_rows") == n_bearing,
              {"counter_authorities": n_counter,
               "counter_status_bearing_rows": n_bearing,
               "status_counts": status_counts},
              "product/query/counter_status.py (RF1 single source of truth)")

        # 8. page contract on the SERVED bundle ------------------------------
        result["_served_bundle"] = final
        t0 = time.time()
        page_ok, page_msg, page_rows = _page_contract(final, timeout=node_timeout)
        result["timing_s"]["page_contract_s"] = round(time.time() - t0, 3)
        result["counts"]["page_contract_assertions"] = page_rows
        _rows(result, "the shipped page renders the served bundle under its DOM contract",
              page_ok, page_msg, "product/verify_query_page.js on the served bundle")

        result["timing_s"]["total_s"] = round(time.time() - t_start, 3)
    except Exception as exc:  # a crash is a FAIL row, never a silent pass
        _rows(result, "the served slice completes without raising",
              False, f"{type(exc).__name__}: {exc}", "product/server_slice.py::execute")
        result["timing_s"]["total_s"] = round(time.time() - t_start, 3)
    finally:
        restore_guard()
        if srv is not None:
            try:
                srv.shutdown()
                srv.server_close()
            except Exception:  # pragma: no cover - cleanup only
                pass
        if thread is not None:
            thread.join(timeout=5)

    result["verdict"] = "PASS" if not result["failures"] else "FAIL"
    return result


def status_payload(http: _Http, run_id: str) -> dict:
    code, st = http.get(f"/api/query/status?run_id={run_id}", timeout=60)
    return st if code == 200 and isinstance(st, dict) else {}


def _page_contract(bundle: dict, *, timeout: int = 300) -> tuple[bool, str, int]:
    node = subprocess.run(["bash", "-lc", "command -v node"],
                          capture_output=True, text=True, check=False)
    if node.returncode != 0:
        return False, "node not found (page contract not checked)", 0

    with tempfile.TemporaryDirectory(prefix="server-slice-") as tmp:
        path = Path(tmp) / "served.bundle.json"
        path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(  # noqa: S603
            ["node", str(PRODUCT_ROOT / "verify_query_page.js"), str(path)],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=timeout,
            check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    ok_lines = [ln for ln in (proc.stdout or "").splitlines() if ln.startswith("ok - ")]
    last = out.strip().splitlines()[-1] if out.strip() else ""
    return (proc.returncode == 0 and "FAIL" not in (proc.stdout or "")), last, len(ok_lines)


def summarise(result: dict) -> str:
    lines = [f"served slice verdict: {result['verdict']}"]
    for row in result["checks"]:
        lines.append(f"  [{row['status']}] {row['claim']}")
    for key in ("n_first_page", "n_final", "n_clusters_final", "n_cited",
                "counter_authorities", "counter_status_bearing_rows",
                "rows_with_source_url", "page_contract_assertions"):
        if key in result.get("counts", {}):
            lines.append(f"  {key}: {result['counts'][key]}")
    for key, value in (result.get("timing_s") or {}).items():
        lines.append(f"  {key}: {value}")
    if result.get("failures"):
        lines.append(f"  failures: {result['failures']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--n", type=int, default=100, help="map size target (MVP: ~100-300)")
    ap.add_argument("--run-id", default=None,
                    help="stamped into the output directory name (cycle run id)")
    ap.add_argument("--out", default=None,
                    help="output directory (default results/product/server_slice/<run-or-stamp>)")
    ap.add_argument("--no-write", action="store_true", help="run and print only, write nothing")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    result = execute(args.query, args.n)
    bundle = result.pop("_served_bundle", None)
    first_page = result.pop("_first_page_bundle", None)

    if not args.no_write:
        stamp = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        out_dir = Path(args.out) if args.out else (
            REPO_ROOT / "results" / "product" / "server_slice" / stamp)
        out_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(bundle, dict):
            (out_dir / "served.bundle.json").write_text(
                json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8")
        if isinstance(first_page, dict):
            # The geometry-preservation claim is recomputable from these two
            # committed bundles (product/server_slice.py::_preserved), not from prose.
            (out_dir / "first_page.bundle.json").write_text(
                json.dumps(first_page, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8")
        (out_dir / "summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        result["artifact_dir"] = str(out_dir.relative_to(REPO_ROOT)
                                     if out_dir.is_relative_to(REPO_ROOT) else out_dir)
        # re-write with the artifact path recorded, so the artifact names itself
        (out_dir / "summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")

    if not args.quiet:
        print(summarise(result))
        if result.get("artifact_dir"):
            print(f"  artifact: {result['artifact_dir']}")
            print("  browse it: python product/query_app.py --fixture --port 8787")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
