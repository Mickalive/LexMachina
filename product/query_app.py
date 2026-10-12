"""One-command local server for the LEX v45 query-map product.

    python product/query_app.py --port 8787

The UI uses a two-phase API: /api/query/start returns the map as soon as
retrieval + local geometry are ready; /api/query/enrich then patches answer,
evidence and counter-authority statuses without moving the map.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from query import enrich_query_bundle, run_query, run_query_initial  # noqa: E402
from query.bundle import validate_bundle  # noqa: E402

STATIC_DIR = PRODUCT_ROOT / "static"
RUNS: dict[str, dict] = {}
RUNS_LOCK = threading.Lock()
MAX_STORED_RUNS = 20


def _remember(bundle: dict, mode: str) -> str:
    run_id = uuid.uuid4().hex[:12]
    with RUNS_LOCK:
        while len(RUNS) >= MAX_STORED_RUNS:
            RUNS.pop(next(iter(RUNS)))
        RUNS[run_id] = {"bundle": bundle, "mode": mode}
    return run_id


class Handler(BaseHTTPRequestHandler):
    server_version = "LexMachinaQuery/45"

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

    def _route(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        params = urllib.parse.parse_qs(parsed.query)

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
                "pipeline": "progressive",
                "retrieval": "OpenCaseLaw accepted adapter v2",
                "generation": "generative-audit contract 2.2 with explicit degraded fallback",
            })

        if path == "/api/query/start":
            q = (params.get("q") or [""])[0].strip()
            n = int((params.get("n") or ["150"])[0])
            if not q:
                return self._json({"error": "empty query"}, 400)
            mode = "fixture" if getattr(self.server, "fixture_mode", False) else "live"
            bundle = run_query_initial(q, top_n=n, retrieval_mode=mode)
            run_id = _remember(bundle, mode)
            return self._json({"run_id": run_id, "bundle": bundle})

        if path == "/api/query/enrich":
            run_id = (params.get("run_id") or [""])[0]
            with RUNS_LOCK:
                record = RUNS.get(run_id)
            if not record:
                return self._json({"error": "unknown or expired run_id"}, 404)
            final = enrich_query_bundle(
                record["bundle"],
                retrieval_mode=record["mode"],
                fixture_generation=getattr(self.server, "fixture_mode", False),
            )
            errors = validate_bundle(final)
            if errors:
                return self._json({"error": "invalid enriched bundle", "details": errors}, 500)
            with RUNS_LOCK:
                RUNS[run_id] = {"bundle": final, "mode": record["mode"]}
            return self._json({"run_id": run_id, "bundle": final})

        if path == "/api/query/run":
            q = (params.get("q") or [""])[0].strip()
            n = int((params.get("n") or ["150"])[0])
            if not q:
                return self._json({"error": "empty query"}, 400)
            mode = "fixture" if getattr(self.server, "fixture_mode", False) else "live"
            return self._json(run_query(
                q,
                top_n=n,
                retrieval_mode=mode,
                fixture_generation=getattr(self.server, "fixture_mode", False),
            ))

        return self._json({"error": "not found", "path": path}, 404)


def make_server(host: str, port: int, *, fixture_mode: bool, verbose: bool) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.fixture_mode = fixture_mode  # type: ignore[attr-defined]
    srv.verbose = verbose  # type: ignore[attr-defined]
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
    print(f"LexMachina v45 ({mode}): http://{args.host}:{srv.server_address[1]}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
