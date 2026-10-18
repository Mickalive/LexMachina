"""One-command local server for the LexMachina query-map product.

    python product/query_app.py --port 8787
    python product/query_app.py --port 8787 --fixture     # offline, deterministic

The UI runs a three-stage job pipeline so a human never waits on a blocking
HTTP request:

    GET /api/query/start?q=&n=      -> first-page map in seconds (run_id)
    GET /api/query/expand?run_id=   -> starts/queries the background expansion
    GET /api/query/enrich?run_id=   -> starts the answer + counter-authority job
    GET /api/query/status?run_id=   -> progress for both jobs (polled by the UI)
    GET /api/query/bundle?run_id=   -> current bundle (resume after a reload)

Why jobs instead of one blocking call (measured live on 2026-10-15, run
38665681083): ``/api/query/start`` took **136.79 s** before the first point was
drawn (136.61 s of it upstream OpenCaseLaw) and ``/api/query/enrich`` a further
**150.70 s**.  A browser fetch that long is indistinguishable from a broken
product, and a reload loses the run.  Each stage now runs in a worker thread,
reports progress through ``/api/query/status`` and is deduplicated, so a
double-click cannot start two three-minute model runs.

Every stage is still reachable as one blocking call with ``&wait_s=<seconds>``
(scripts, CI, the reality-check legs), so nothing that worked before is lost.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from query import (  # noqa: E402
    enrich_query_bundle,
    expand_query_bundle,
    run_query,
    run_query_first_page,
)
from query.bundle import validate_bundle  # noqa: E402
from query.gate_admissibility import (  # noqa: E402
    counter_authority_count,
    counter_status_bearing_count,
)

STATIC_DIR = PRODUCT_ROOT / "static"

RUNS: dict[str, dict] = {}
RUNS_LOCK = threading.Lock()
MAX_STORED_RUNS = 20

#: Two background stages at a time. Generation is model-bound and retrieval is
#: upstream-bound; a third concurrent job only makes every wait longer.
JOB_WORKERS = 2
POOL = ThreadPoolExecutor(max_workers=JOB_WORKERS, thread_name_prefix="lex-job")


def _now() -> float:
    return time.time()


def _job(name: str) -> dict:
    return {"status": "idle", "started_at": None, "ended_at": None, "error": None, "detail": {}}


def _remember(query: str, top_n: int, bundle: dict, mode: str) -> str:
    run_id = uuid.uuid4().hex[:12]
    with RUNS_LOCK:
        while len(RUNS) >= MAX_STORED_RUNS:
            RUNS.pop(next(iter(RUNS)))
        RUNS[run_id] = {
            "run_id": run_id,
            "query": query,
            "top_n": top_n,
            "mode": mode,
            "bundle": bundle,
            "created_at": _now(),
            "jobs": {"expand": _job("expand"), "enrich": _job("enrich")},
        }
    return run_id


def _get(run_id: str) -> dict | None:
    with RUNS_LOCK:
        return RUNS.get(run_id)


def _set_bundle(run_id: str, bundle: dict) -> None:
    with RUNS_LOCK:
        record = RUNS.get(run_id)
        if record is not None:
            record["bundle"] = bundle


def _set_job(run_id: str, name: str, **fields) -> None:
    with RUNS_LOCK:
        record = RUNS.get(run_id)
        if record is not None:
            record["jobs"].setdefault(name, _job(name)).update(fields)


def _start_job(run_id: str, name: str, fn, detail: dict | None = None) -> tuple[dict, bool]:
    """Start ``fn`` unless that job is already running. Returns (job, started)."""
    with RUNS_LOCK:
        record = RUNS.get(run_id)
        if record is None:
            raise KeyError(run_id)
        job = record["jobs"].setdefault(name, _job(name))
        if job["status"] == "running":
            return dict(job), False
        job.update({
            "status": "running",
            "started_at": _now(),
            "ended_at": None,
            "error": None,
            "detail": detail or {},
        })
        snapshot = dict(job)

    def _run() -> None:
        try:
            fn()
        except Exception as exc:  # a failed job must never kill the server
            _set_job(run_id, name, status="error", ended_at=_now(),
                     error=f"{type(exc).__name__}: {exc}")
        else:
            _set_job(run_id, name, status="done", ended_at=_now())

    POOL.submit(_run)
    return snapshot, True


def _expand_task(run_id: str) -> None:
    record = _get(run_id)
    if record is None:
        return
    bundle = expand_query_bundle(
        record["bundle"],
        retrieval_mode=record["mode"],
        top_n=record["top_n"],
    )
    errors = validate_bundle(bundle)
    if errors:
        raise RuntimeError(f"expanded bundle invalid: {errors}")
    _set_bundle(run_id, bundle)
    prog = bundle.get("provenance", {}).get("progressive", {})
    _set_job(run_id, "expand", detail={
        "n_before": prog.get("n_before"),
        "n_after": prog.get("n_after"),
        "n_added": prog.get("n_added"),
        "points_moved": prog.get("points_moved"),
        "expand_upstream_s": prog.get("expand_upstream_s"),
    })


def _await_expand(run_id: str, limit_s: float = 900.0) -> None:
    """Block an enrich job until the background expansion of its run is done.

    The browser already runs the stages in order, but the API is public: an
    enrich started while expansion is still retrieving would answer from the
    partial first-page candidate set — exactly the candidates most likely to
    miss contrary authority found further out.  Bounded, so a wedged expansion
    can never hang generation forever.
    """
    deadline = _now() + limit_s
    while _now() < deadline:
        record = _get(run_id)
        if record is None:
            return
        if record["jobs"]["expand"]["status"] != "running":
            return
        time.sleep(0.25)


def _enrich_task(run_id: str) -> None:
    _await_expand(run_id)
    record = _get(run_id)
    if record is None:
        return
    final = enrich_query_bundle(
        record["bundle"],
        retrieval_mode=record["mode"],
        fixture_generation=record["mode"] == "fixture",
    )
    errors = validate_bundle(final)
    if errors:
        raise RuntimeError(f"invalid enriched bundle: {errors}")
    _set_bundle(run_id, final)
    answer = final.get("answer", {})
    _set_job(run_id, "enrich", detail={
        "answer_status": answer.get("status"),
        "method": answer.get("method"),
        "model": answer.get("model"),
        "cited": len(answer.get("cited_decision_ids") or []),
        # RF1: never label "rows carrying a non-empty counter_status" as
        # "counter authorities" - `cited` (every decision the answer cites) and
        # `supporting-candidate` / `context` / `unclassified` are provenance
        # values, not counter findings. Both numbers are published, each under
        # its own honest name (audit CYCLE_39069382456 / CYCLE_39065274887 F3).
        "counter_authorities": counter_authority_count(final.get("decisions") or []),
        "counter_status_bearing_rows": counter_status_bearing_count(
            final.get("decisions") or []),
        "enrich_total_s": final.get("provenance", {}).get("timing", {}).get("enrich_total_s"),
    })


def run_status(run_id: str) -> dict:
    """Compact, pollable progress for one run (never the full bundle)."""
    record = _get(run_id)
    if record is None:
        return {"error": "unknown or expired run_id", "run_id": run_id}
    bundle = record.get("bundle") or {}
    prov = bundle.get("provenance", {})
    jobs = {}
    for name, job in (record.get("jobs") or {}).items():
        elapsed = None
        if job.get("started_at"):
            elapsed = round((job.get("ended_at") or _now()) - job["started_at"], 1)
        jobs[name] = {
            "status": job.get("status"),
            "elapsed_s": elapsed,
            "error": job.get("error"),
            "detail": job.get("detail") or {},
        }
    return {
        "run_id": run_id,
        "query": record.get("query"),
        "mode": record.get("mode"),
        "age_s": round(_now() - record.get("created_at", _now()), 1),
        "phase": prov.get("phase"),
        "progressive": prov.get("progressive", {}),
        "answer": {
            "status": (bundle.get("answer") or {}).get("status"),
            "method": (bundle.get("answer") or {}).get("method"),
            "model": (bundle.get("answer") or {}).get("model"),
            "cited": len((bundle.get("answer") or {}).get("cited_decision_ids") or []),
        },
        "counts": {
            "decisions": len(bundle.get("decisions") or []),
            "clusters": len(bundle.get("clusters") or []),
            # RF1. `counter` counted every row whose counter_status was not
            # "none", which included every decision the answer cited; the demo
            # bundle reported 5 where 1 row is a real counter authority. The
            # honest name is kept as an explicit, clearly-labelled alias so no
            # consumer silently keeps reading the inflated number as
            # "counter authorities" - it is a breaking change on purpose.
            "counter_authorities": counter_authority_count(bundle.get("decisions") or []),
            "counter_status_bearing_rows": counter_status_bearing_count(
                bundle.get("decisions") or []),
        },
        "timing": prov.get("timing", {}),
        "jobs": jobs,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LexMachinaQuery/45"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload, code: int = 200) -> None:
        self._send(
            code,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _file(self, path: Path) -> None:
        if not path.is_file():
            return self._json({"error": "not found"}, 404)
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
        }.get(path.suffix.lower(), "application/octet-stream")
        self._send(200, path.read_bytes(), ctype)

    def do_HEAD(self) -> None:  # noqa: N802
        self._route()

    def do_GET(self) -> None:  # noqa: N802
        try:
            self._route()
        except BrokenPipeError:
            pass
        except Exception as exc:  # surface failures rather than silently swapping data sources
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    @staticmethod
    def _wait_for(run_id: str, name: str, wait_s: float, timeout: float) -> dict:
        """Poll a job up to ``wait_s``; return {} when it did not finish."""
        deadline = _now() + max(0.0, wait_s)
        while _now() < deadline:
            status = run_status(run_id).get("jobs", {}).get(name, {})
            if status.get("status") in {"done", "error"}:
                return status
            time.sleep(min(0.25, max(0.05, deadline - _now())))
        return {}

    def _route(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        params = urllib.parse.parse_qs(parsed.query)
        fixture_mode = bool(getattr(self.server, "fixture_mode", False))
        mode = "fixture" if fixture_mode else "live"

        if path in {"/", "/index.html", "/query.html"}:
            return self._file(STATIC_DIR / "query.html")
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            if ".." in rel or rel.startswith("/"):
                return self._json({"error": "bad path"}, 400)
            return self._file(STATIC_DIR / rel)

        if path == "/api/health":
            return self._json({
                "ok": True,
                "direction_version": 45,
                "pipeline": "progressive-jobs",
                "stages": ["first_page", "expand", "enrich"],
                "retrieval": "OpenCaseLaw accepted adapter v2",
                "generation": "generative-audit contract 2.2 with explicit degraded fallback",
                "runs": len(RUNS),
                "fixture_mode": fixture_mode,
            })

        if path == "/api/query/start":
            q = (params.get("q") or [""])[0].strip()
            n = _int_param(params, "n", 150)
            if not q:
                return self._json({"error": "empty query"}, 400)
            bundle = run_query_first_page(q, top_n=n, retrieval_mode=mode)
            run_id = _remember(q, n, bundle, mode)
            job, started = _start_job(run_id, "expand", lambda: _expand_task(run_id))
            return self._json({
                "run_id": run_id,
                "bundle": bundle,
                "jobs": {"expand": job},
                "expand_started": started,
            })

        if path == "/api/query/expand":
            run_id = (params.get("run_id") or [""])[0]
            if not _get(run_id):
                return self._json({"error": "unknown or expired run_id"}, 404)
            job, started = _start_job(run_id, "expand", lambda: _expand_task(run_id))
            wait_s = _float_param(params, "wait_s", 0.0)
            finished = self._wait_for(run_id, "expand", wait_s, 30) if wait_s > 0 else {}
            record = _get(run_id)
            payload = {"run_id": run_id, "expand_started": started, "job": job, "bundle": record["bundle"]}
            if finished:
                payload["job"] = finished
            return self._json(payload)

        if path == "/api/query/enrich":
            run_id = (params.get("run_id") or [""])[0]
            if not _get(run_id):
                return self._json({"error": "unknown or expired run_id"}, 404)
            job, started = _start_job(run_id, "enrich", lambda: _enrich_task(run_id))
            wait_s = _float_param(params, "wait_s", 0.0)
            if wait_s > 0:
                finished = self._wait_for(run_id, "enrich", wait_s, 0)
                record = _get(run_id)
                if finished.get("status") == "error":
                    return self._json({
                        "run_id": run_id, "error": finished.get("error"), "job": finished,
                    }, 500)
                if finished:
                    return self._json({"run_id": run_id, "bundle": record["bundle"], "job": finished})
            return self._json({
                "run_id": run_id,
                "status": "running" if job["status"] == "running" else job["status"],
                "enrich_started": started,
                "deduplicated": not started,
                "job": job,
                "poll": "/api/query/status?run_id=" + run_id,
            }, 202)

        if path == "/api/query/status":
            run_id = (params.get("run_id") or [""])[0]
            status = run_status(run_id)
            if status.get("error"):
                return self._json(status, 404)
            if (params.get("bundle") or ["0"])[0] in {"1", "true"} and \
                    status.get("jobs", {}).get("enrich", {}).get("status") == "done":
                status["bundle"] = _get(run_id)["bundle"]
            return self._json(status)

        if path == "/api/query/bundle":
            run_id = (params.get("run_id") or [""])[0]
            record = _get(run_id)
            if record is None:
                return self._json({"error": "unknown or expired run_id"}, 404)
            return self._json({"run_id": run_id, "status": run_status(run_id), "bundle": record["bundle"]})

        if path == "/api/query/run":
            q = (params.get("q") or [""])[0].strip()
            n = _int_param(params, "n", 150)
            if not q:
                return self._json({"error": "empty query"}, 400)
            return self._json(run_query(
                q,
                top_n=n,
                retrieval_mode=mode,
                fixture_generation=fixture_mode,
            ))

        return self._json({"error": "not found", "path": path}, 404)


def _int_param(params: dict, name: str, default: int) -> int:
    try:
        return int((params.get(name) or [default])[0])
    except (TypeError, ValueError):
        return default


def _float_param(params: dict, name: str, default: float) -> float:
    try:
        return float((params.get(name) or [default])[0])
    except (TypeError, ValueError):
        return default


def make_server(host: str, port: int, *, fixture_mode: bool, verbose: bool) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.fixture_mode = fixture_mode  # type: ignore[attr-defined]
    srv.verbose = verbose  # type: ignore[attr-defined]
    srv.daemon_threads = True
    return srv


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--fixture", action="store_true", help="deterministic offline OpenCaseLaw fixture + fixture generation")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    srv = make_server(args.host, args.port, fixture_mode=args.fixture, verbose=not args.quiet)
    mode = "fixture/offline" if args.fixture else "live OpenCaseLaw"
    print(f"LexMachina query map ({mode}): http://{args.host}:{srv.server_address[1]}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        POOL.shutdown(wait=False, cancel_futures=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())