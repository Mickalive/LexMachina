#!/usr/bin/env python3
"""Real-socket smoke of the SHIPPED server's progressive query API.

Why this exists
---------------
Producer snapshot cycle 39905155175 (commit 845171a) claimed the progressive
endpoints ``/api/query/start``, ``/api/query/expand``, ``/api/query/enrich``,
``/api/query/status`` and ``/api/query/bundle`` were fixed in
``product/server.py`` (missing ``uuid`` import, ``_json`` -> ``_json_response``,
``expand_query_bundle`` import from ``product.query.progressive``), and that
claim sat in ``state/product.json`` without an artifact that exercises exactly
those endpoints through the shipped launch command.  Its run then failed in the
AUDIT job (exit 2, gate file absent), so the claim never met an independent
recomputation either.

This instrument boots ``python3 product/server.py <port> --query-mode`` as a
real subprocess, drives it over a real socket exactly as the browser does, and
re-derives the claim:

  1. ``/api/health`` answers in query mode (no 174k corpus load);
  2. ``/api/query/start`` returns a run_id + first-page bundle with
     decisions, clusters and x/y coordinates, and starts a background expand;
  3. ``/api/query/status`` reports job states and growing counts;
  4. ``/api/query/enrich`` completes with ``answer_status=ready``, cited
     decision ids, cluster labels and counter-status rows;
  5. ``/api/query/bundle`` returns the enriched bundle;
  6. ``/query.html`` and its assets are served with correct content types.

Everything runs in fixture mode: retrieval replays from the local query cache
and generation uses the fixture provider.  No network, no paid inference.

Usage
-----
    python3 product/progressive_smoke.py --run-id <id>            # write artifact
    python3 product/progressive_smoke.py --json                   # print only

Exit code is 0 only when every step passes.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# The ONE counter-status predicate module (stdlib-only, direction v56 RF1).
# This smoke used to re-state its broad inline test, which is exactly the
# scattered-copy defect product/tests/test_counter_authority_definition.py
# forbids; asking the owning module keeps the check's semantics identical.
from product.query.counter_status import (  # noqa: E402
    counter_status_bearing_count,
    counter_status_histogram,
)
SERVER = ROOT / "product" / "server.py"
FIXTURE_QUERY = "Kündigung Mietvertrag Mietrecht"
STEP_BUDGET_S = {
    "health": 60.0,
    "start": 120.0,
    "expand": 180.0,
    "enrich": 300.0,
    "bundle": 30.0,
    "status": 15.0,
    "static": 15.0,
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(port: int, path: str, timeout: float = 60.0):
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _json(port: int, path: str, timeout: float = 60.0) -> dict:
    status, _headers, body = _get(port, path, timeout=timeout)
    if status != 200:
        raise AssertionError(f"{path} -> HTTP {status}: {body[:400]!r}")
    return json.loads(body.decode("utf-8"))


class _Server:
    """The shipped server, launched exactly as the README launches it."""

    def __init__(self) -> None:
        self.port = _free_port()
        self.proc: subprocess.Popen | None = None
        self.log = ""
        self.boot_s = 0.0

    def __enter__(self) -> "_Server":
        started = time.time()
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER), str(self.port), "--query-mode"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.time() + STEP_BUDGET_S["health"]
        while time.time() < deadline:
            if self.proc.poll() is not None:
                out = self.proc.stdout.read() if self.proc.stdout else ""
                raise AssertionError("server exited before /api/health:\n" + out[-4000:])
            try:
                status, _h, _b = _get(self.port, "/api/health", timeout=5)
                if status == 200:
                    self.boot_s = round(time.time() - started, 3)
                    return self
            except Exception:
                time.sleep(0.2)
        raise AssertionError("server did not answer /api/health in budget")

    def __exit__(self, *_exc) -> None:
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc is not None and self.proc.stdout is not None:
            self.log = self.proc.stdout.read() or ""


def run(run_id: str) -> dict:
    checks: list[dict] = []
    timings: dict[str, float] = {}
    failures: list[str] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    with _Server() as srv:
        t0 = time.time()
        health = _json(srv.port, "/api/health")
        timings["health_s"] = round(time.time() - t0, 3)
        check("health_query_mode", health.get("mode") == "query", health.get("mode"))
        check("health_no_174k_corpus", health.get("corpus_decisions") == 0,
              health.get("corpus_decisions"))
        check("health_pipeline_ready", health.get("query_pipeline") == "ready",
              health.get("query_pipeline"))
        timings["server_boot_s"] = srv.boot_s

        # --- start -------------------------------------------------------
        q = urllib.parse.quote(FIXTURE_QUERY)
        t0 = time.time()
        start = _json(srv.port, f"/api/query/start?q={q}&n=100&mode=fixture",
                      timeout=STEP_BUDGET_S["start"])
        timings["start_s"] = round(time.time() - t0, 3)
        run_id_seen = start.get("run_id") or ""
        check("start_returns_run_id", bool(run_id_seen), run_id_seen[:80])
        first = start.get("bundle") or {}
        first_decisions = first.get("decisions") or []
        check("start_first_page_nonempty", len(first_decisions) >= 10,
              len(first_decisions))
        check("start_has_clusters", bool(first.get("clusters")),
              len(first.get("clusters") or []))
        check("start_points_have_xy",
              all("x" in d and "y" in d for d in first_decisions),
              f"{sum(1 for d in first_decisions if 'x' in d and 'y' in d)}"
              f"/{len(first_decisions)}")
        check("start_expand_started", bool(start.get("expand_started")) is not False,
              start.get("expand_started"))

        # --- status ------------------------------------------------------
        t0 = time.time()
        status = _json(srv.port, f"/api/query/status?run_id={run_id_seen}",
                       timeout=STEP_BUDGET_S["status"])
        timings["status_s"] = round(time.time() - t0, 3)
        check("status_reports_jobs", isinstance(status.get("jobs"), dict)
              and "expand" in (status.get("jobs") or {}),
              list((status.get("jobs") or {}).keys()))
        check("status_reports_counts", bool(status.get("counts")),
              status.get("counts"))

        # --- expand (wait) ------------------------------------------------
        t0 = time.time()
        try:
            expand = _json(srv.port,
                           f"/api/query/expand?run_id={run_id_seen}"
                           f"&wait_s={int(STEP_BUDGET_S['expand'])}",
                           timeout=STEP_BUDGET_S["expand"])
            expand_err = None
        except AssertionError as exc:  # HTTP 500 surfaces a failed job
            expand, expand_err = {}, str(exc)
        timings["expand_s"] = round(time.time() - t0, 3)
        if expand_err:
            check("expand_job_completed", False, expand_err[:300])
        else:
            expand_job = expand.get("job") or {}
            check("expand_job_completed",
                  expand_job.get("status") in (None, "done", "running"),
                  expand_job.get("status"))
            if expand.get("bundle"):
                check("expand_bundle_larger_or_equal",
                      len((expand["bundle"].get("decisions") or [])) >= len(first_decisions),
                      f"{len(expand['bundle'].get('decisions') or [])}"
                      f">={len(first_decisions)}")

        # --- enrich --------------------------------------------------------
        t0 = time.time()
        try:
            enrich = _json(srv.port,
                           f"/api/query/enrich?run_id={run_id_seen}"
                           f"&wait_s={int(STEP_BUDGET_S['enrich'])}",
                           timeout=STEP_BUDGET_S["enrich"])
            enrich_err = None
        except AssertionError as exc:
            enrich, enrich_err = {}, str(exc)
        timings["enrich_s"] = round(time.time() - t0, 3)
        if enrich_err:
            check("enrich_job_completed", False, enrich_err[:300])
            enriched: dict = {}
        else:
            enriched = enrich.get("bundle") or {}
            enrich_job = enrich.get("job") or {}
            check("enrich_job_done", enrich_job.get("status") == "done",
                  enrich_job.get("status"))

        answer = enriched.get("answer") or {}
        check("answer_status_ready", answer.get("status") == "ready",
              answer.get("status"))
        cited = answer.get("cited_decision_ids") or answer.get("cited") or []
        check("answer_has_citations", bool(cited), len(cited))
        # The bundle's answer schema is {status, prose, statements,
        # cited_decision_ids, method, model} - prose is the answer text and
        # statements are its sourced atomic propositions.
        prose = answer.get("prose") or answer.get("answer") or answer.get("text") or ""
        statements = answer.get("statements") or []
        check("answer_carries_text", bool(prose.strip()) and len(statements) >= 1,
              {"prose_chars": len(prose), "statements": len(statements)})
        rows = enriched.get("decisions") or []
        # Per-decision counter channel: counter_status in
        # {none, cited, candidate-limiting, ...} with counter_uncertainty /
        # counter_evidence_verified beside it.  "none" is unclassified, so it
        # does not count as a status-bearing row.  The enumeration is owned by
        # product/query/counter_status.py; this smoke ASKS it (the same
        # predicate, verbatim semantics) instead of restating the broad inline
        # test the RF1 scattering guard forbids.
        bearing = counter_status_bearing_count(rows)
        check("counter_status_rows_present", bearing > 0,
              {"rows": bearing,
               "statuses": sorted(k for k in counter_status_histogram(rows)
                                  if k != "none")})
        clusters = enriched.get("clusters") or []
        labelled = [c for c in clusters if (c.get("label") or c.get("name"))]
        check("cluster_labels_present", bool(labelled), f"{len(labelled)}/{len(clusters)}")
        check("enriched_points_have_xy",
              all("x" in d and "y" in d for d in rows), len(rows))

        # --- bundle ---------------------------------------------------------
        t0 = time.time()
        bundle_payload = _json(srv.port, f"/api/query/bundle?run_id={run_id_seen}",
                               timeout=STEP_BUDGET_S["bundle"])
        timings["bundle_s"] = round(time.time() - t0, 3)
        bundle = bundle_payload.get("bundle") or {}
        check("bundle_endpoint_returns_bundle", bool(bundle.get("decisions")),
              len(bundle.get("decisions") or []))
        check("bundle_status_counts",
              (bundle_payload.get("status") or {}).get("counts", {}).get("decisions", 0)
              == len(bundle.get("decisions") or []),
              (bundle_payload.get("status") or {}).get("counts"))

        # --- static assets ---------------------------------------------------
        for path_, expect in (("/query.html", "text/html"),
                              ("/static/query.html", "text/html")):
            t0 = time.time()
            status_code, headers, body = _get(srv.port, path_, timeout=STEP_BUDGET_S["static"])
            timings[f"static_{path_.strip('/').replace('/', '_')}_s"] = round(time.time() - t0, 3)
            ctype = (headers.get("Content-Type") or "")
            check(f"static {path_} served as {expect}",
                  status_code == 200 and ctype.startswith(expect) and len(body) > 0,
                  f"HTTP {status_code} {ctype} bytes={len(body)}")

    verdict = "PASS" if not failures else "FAIL"
    return {
        "schema": "product-progressive-smoke/1",
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "fixture (retrieval replays from the local cache, fixture generation, no network)",
        "launch": "python3 product/server.py <port> --query-mode (real subprocess, real socket)",
        "query": FIXTURE_QUERY,
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks),
        "checks": checks,
        "timings_s": timings,
        "budgets": {
            "server_boot_lt_60s": timings.get("server_boot_s", 999) < 60,
            "start_lt_120s": timings.get("start_s", 999) < 120,
            "local_after_upstream": "upstream is fixture-replayed; live OpenCaseLaw latency is measured elsewhere",
        },
        "failures": failures,
        "verdict": verdict,
        "claim_ceiling": (
            "Engineering smoke of the shipped progressive query API in fixture mode: it proves "
            "the endpoints answer over a real socket with a source-linked bundle, clusters, "
            "coordinates, a ready fixture answer and counter-status rows. It makes no live "
            "OpenCaseLaw latency claim, no answer-quality claim, no legal-usefulness claim and "
            "no gate-readiness claim; the fail-closed posture is unchanged."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default="MANUAL")
    ap.add_argument("--out", default=None,
                    help="artifact path (default: results/product/progressive_smoke/"
                         "CYCLE_<run-id>_progressive_smoke.json when --run-id given)")
    ap.add_argument("--json", action="store_true", help="print the record and exit")
    args = ap.parse_args(argv)

    record = run(args.run_id)
    print(f"progressive smoke: {record['verdict']} "
          f"({record['checks_passed']}/{record['checks_total']} checks) "
          f"timings={record['timings_s']}")
    for f in record["failures"]:
        print(f"  FAIL {f}")

    if args.out:
        out = Path(args.out)
    elif args.run_id != "MANUAL" and not args.json:
        out = (ROOT / "results" / "product" / "progressive_smoke"
               / f"CYCLE_{args.run_id}_progressive_smoke.json")
    else:
        out = None
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"wrote {out}")
    if args.json:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
