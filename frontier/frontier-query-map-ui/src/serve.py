"""Local prototype server for the query-specific jurisprudence map.

Stdlib-only for static/file serving (owner-time invariant: no paid API, no extra service to provision).
The fixture query endpoint requires numpy/scikit-learn (documented in requirements).

Routes
-----
    /                        -> ui/query_map.html  (the prototype)
    /ui/<file>               -> frontier UI assets (read-only)
    /vendor/<file>           -> ACCEPTED product static assets, served read-only
                                 from `product/static/` (renderer / JS adapter
                                 reuse without copying product code into this
                                 team's namespace)
    /data/visualization.json -> adapted visualization payload (map geometry)
    /data/bundle.json        -> raw query_result_bundle (answer + provenance)
    /data/manifest.json      -> fixture manifest (checksums, provenance)
    /api/health              -> liveness + payload sizes
    /api/query/run?q=&n=     -> fixture-mode query pipeline (retrieval_mode='fixture',
                                 fixture_generation=True, adversarial_retrieval=False;
                                 read-only, no product compatibility shim)

Run (static/file serving only - no numpy required):
    python3 frontier/frontier-query-map-ui/src/serve.py --port 8787

Run (with fixture query - requires numpy + scikit-learn):
    pip install numpy scikit-learn
    python3 frontier/frontier-query-map-ui/src/serve.py --port 8787
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_HERE = Path(__file__).resolve().parent
TEAM_ROOT = _HERE.parent
REPO_ROOT = TEAM_ROOT.parent.parent
for p in (str(_HERE), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# product_compat shim is not installed; /api/query/run uses product.query.pipeline
# directly in fixture mode. Imports stay lazy where possible to avoid numpy import
# at startup for static/file serving.

UI_DIR = TEAM_ROOT / "ui"
FIXTURE_DIR = TEAM_ROOT / "fixtures"
PRODUCT_STATIC = REPO_ROOT / "product" / "static"

VIZ_PATH = FIXTURE_DIR / "visualization.json"
BUNDLE_PATH = FIXTURE_DIR / "query_result_bundle.json"
MANIFEST_PATH = FIXTURE_DIR / "FIXTURE_MANIFEST.json"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def _get_product_compat():
    """Legacy shim removed; not used by the fixture-mode endpoint."""
    raise RuntimeError("product_compat shim is disabled; /api/query/run uses fixture mode")


class QueryMapHandler(BaseHTTPRequestHandler):
    server_version = "LexMachinaQueryMap/1.0"
    protocol_version = "HTTP/1.1"

    # ---- helpers ---------------------------------------------------------
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # The prototype is loaded from a single origin; allow tests/CORS reuse.
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, payload, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _send_file(self, path: Path, code: int = 200) -> None:
        if not path.is_file():
            self._send_json({"error": "not found", "path": str(path)}, 404)
            return
        ctype = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        self._send(code, path.read_bytes(), ctype)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    # ---- routing ---------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        try:
            self._route("GET")
        except BrokenPipeError:
            pass

    def do_HEAD(self) -> None:  # noqa: N802
        try:
            self._route("HEAD")
        except BrokenPipeError:
            pass

    def do_POST(self) -> None:  # noqa: N802
        try:
            self._route("POST")
        except BrokenPipeError:
            pass

    def _route(self, method: str) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        params = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html", "/query_map.html"):
            return self._send_file(UI_DIR / "query_map.html")
        if path == "/favicon.ico":
            return self._send(b"", b"", "image/x-icon")

        if path.startswith("/ui/"):
            rel = path[len("/ui/"):]
            return self._send_file(UI_DIR / rel)

        # Read-only reuse of the ACCEPTED product renderer / JS bundle adapter.
        if path.startswith("/vendor/"):
            rel = path[len("/vendor/"):]
            if ".." in rel or rel.startswith("/"):
                return self._send_json({"error": "bad path"}, 400)
            return self._send_file(PRODUCT_STATIC / rel)

        if path == "/data/visualization.json":
            return self._send_file(VIZ_PATH)
        if path == "/data/bundle.json":
            return self._send_file(BUNDLE_PATH)
        if path == "/data/manifest.json":
            return self._send_file(MANIFEST_PATH)

        if path == "/api/health":
            return self._send_json({
                "ok": True,
                "viz_bytes": VIZ_PATH.stat().st_size if VIZ_PATH.exists() else 0,
                "bundle_bytes": BUNDLE_PATH.stat().st_size if BUNDLE_PATH.exists() else 0,
                "vendor_renderer": (PRODUCT_STATIC / "webgl_renderer.js").is_file(),
                "vendor_adapter": (PRODUCT_STATIC / "bundle_adapter.js").is_file(),
            })

        if path == "/api/query/run":
            q = (params.get("q") or [""])[0]
            n = int((params.get("n") or ["150"])[0])
            if not q.strip():
                return self._send_json({"error": "empty query"}, 400)
            try:
                from product.query.pipeline import run_query_initial, enrich_query_bundle
                initial = run_query_initial(q, top_n=n, retrieval_mode="fixture")
                bundle = enrich_query_bundle(
                    initial,
                    retrieval_mode="fixture",
                    evidence_count=12,
                    max_cites=8,
                    fixture_generation=True,
                    adversarial_retrieval=False,
                )
            except Exception as exc:  # pragma: no cover - surfaced to the UI
                return self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
            return self._send_json(bundle)

        if path == "/api/fixture":
            if not BUNDLE_PATH.exists():
                return self._send_json({"error": "fixture missing; run build_fixture.py"}, 500)
            return self._send_file(BUNDLE_PATH)

        self._send_json({"error": "not found", "path": path}, 404)


def make_server(host: str = "127.0.0.1", port: int = 8787, verbose: bool = False) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), QueryMapHandler)
    srv.verbose = verbose  # type: ignore[attr-defined]
    return srv


def serve_forever(host: str = "127.0.0.1", port: int = 8787, verbose: bool = True) -> None:
    srv = make_server(host, port, verbose)
    print(f"LexMachina query map prototype: http://{host}:{srv.server_address[1]}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def start_in_thread(host: str = "127.0.0.1", port: int = 0) -> tuple[ThreadingHTTPServer, threading.Thread]:
    srv = make_server(host, port, verbose=False)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, t


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    serve_forever(args.host, args.port, verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
