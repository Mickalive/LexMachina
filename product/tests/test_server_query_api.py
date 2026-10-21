"""The LEGACY product server's query API must work when it is launched the way
the README and the reports launch it.

Why this exists
---------------
Producer cycle 39646409851 changed ``product/server.py``'s import bootstrap
from

    sys.path.insert(0, str(Path(__file__).parent.parent))   # repository root

to

    sys.path.insert(0, str(Path(__file__).parent))           # product/ only

and left it there.  The repository root is REQUIRED: ``product/query/bundle.py``
imports ``from product.query.counter_status import ...`` absolutely, and when
the server is started as ``python3 product/server.py`` the only entry on
``sys.path`` is the script's own directory (``product/``), so the package
``product`` is not importable at all.  Every ``/api/query/*`` endpoint then
dies with ``ModuleNotFoundError: No module named 'product'`` and the HTTP
handler returns an empty 500 - the query-map product is unreachable through
this server.

The defect is invisible to a test that only imports the pipeline from the
repository root (``pytest`` puts the root on ``sys.path``), which is why it
survived: the failure exists only in the SHIPPED LAUNCH COMMAND.  These tests
therefore spawn the real process, the way the browser and the operator do, and
drive it over a real socket.

What is pinned here
-------------------
1. ``python3 product/server.py <port> --query-mode`` answers ``/api/health``
   in query mode (no 174k corpus load): ``mode="query"``,
   ``corpus_decisions=0``, ``query_pipeline="ready"``;
2. ``/api/query/map?...&mode=fixture`` returns HTTP 200 and a real
   ``query_result_bundle`` with decisions, clusters and coordinates
   (the regression: this is the call that used to die on the import);
3. ``/api/query/answer?...&mode=fixture`` returns HTTP 200 and an answer;
4. the retrieval mode is part of the response cache key, so a fixture answer
   can never be served for a live request (observed through
   ``/api/cache/stats``);
5. ``/static/<file>`` serves the shipped assets with the right content type,
   including ``.html`` (serving the page as ``text/css`` would break it in a
   browser), and never escapes ``product/static/``.

The tests are offline and deterministic: fixture retrieval, fixture generation,
no outbound network, no paid inference.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
SERVER = PRODUCT / "server.py"

FIXTURE_QUERY = "Kündigung Mietvertrag Mietrecht"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(port: int, path: str, timeout: float = 120.0):
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as exc:  # pragma: no cover - failure path
        return exc.code, exc.headers, exc.read()


class _Server:
    """The shipped server, launched exactly as the reports launch it."""

    def __init__(self) -> None:
        self.port = _free_port()
        self.proc: subprocess.Popen | None = None
        self.log = ""

    def __enter__(self) -> "_Server":
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER), str(self.port), "--query-mode"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise AssertionError(
                    "the shipped server exited before answering /api/health:\n"
                    + (self.proc.stdout.read() if self.proc.stdout else "")
                )
            try:
                status, _headers, body = _get(self.port, "/api/health", timeout=5)
                if status == 200:
                    return self
            except Exception:
                time.sleep(0.2)
        raise AssertionError("the shipped server did not answer /api/health in 60s")

    def __exit__(self, *_exc) -> None:
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - failure path
                self.proc.kill()
        if self.proc is not None and self.proc.stdout is not None:
            self.log = self.proc.stdout.read() or ""


def _json(path: str, port: int) -> dict:
    status, _headers, body = _get(port, path)
    assert status == 200, f"{path} -> HTTP {status}: {body[:400]!r}"
    return json.loads(body.decode("utf-8"))


# ---------------------------------------------------------------------------
# 1. the server boots in query mode without loading the 174k corpus
# ---------------------------------------------------------------------------


def test_the_shipped_server_boots_in_query_mode_without_the_174k_corpus():
    with _Server() as server:
        health = _json("/api/health", server.port)
        assert health["nav_api_initialized"] is True
        assert health["mode"] == "query", health
        assert health["corpus_decisions"] == 0, health
        assert health["maps_loaded"] == 0, health
        assert health["query_pipeline"] == "ready", health


# ---------------------------------------------------------------------------
# 2./3. the query API works through the shipped launch command
# ---------------------------------------------------------------------------


def test_the_query_map_endpoint_returns_a_real_bundle_through_the_shipped_launch():
    """The regression: this call died on ``ModuleNotFoundError: product``."""
    with _Server() as server:
        status, headers, body = _get(
            server.port,
            "/api/query/map?q=" + urllib.parse.quote(FIXTURE_QUERY) + "&n=40&mode=fixture",
        )
        assert status == 200, (
            "the shipped server must answer /api/query/map; the server log was:\n"
            + server.log[-2000:]
        )
        payload = json.loads(body.decode("utf-8"))
        bundle = payload["bundle"]
        assert "error" not in payload, payload.get("error")
        decisions = bundle.get("decisions") or []
        assert len(decisions) >= 10, len(decisions)
        assert bundle.get("clusters"), "the map must carry clusters"
        assert all("x" in d and "y" in d for d in decisions), "every point needs coordinates"
        assert headers.get("X-Cache") in {"HIT", "MISS"}


def test_the_query_answer_endpoint_returns_an_answer_through_the_shipped_launch():
    with _Server() as server:
        payload = _json(
            "/api/query/answer?q=" + urllib.parse.quote(FIXTURE_QUERY) + "&n=40&mode=fixture",
            server.port,
        )
        assert "error" not in payload, payload.get("error")
        assert payload.get("prose"), payload
        assert payload.get("cited_decision_ids"), (
            "a served answer must carry the decision ids it cites, so a jurist "
            "can follow the provenance: " + repr(payload)
        )


# ---------------------------------------------------------------------------
# 4. the retrieval mode is part of the cache key
# ---------------------------------------------------------------------------


def test_the_retrieval_mode_is_part_of_the_response_cache_key():
    """A fixture answer must never be served for a live request."""
    with _Server() as server:
        _json(
            "/api/query/map?q=" + urllib.parse.quote(FIXTURE_QUERY) + "&n=40&mode=fixture",
            server.port,
        )
        stats = _json("/api/cache/stats", server.port)
        keys = stats.get("keys") or []
        fixture_keys = [k for k in keys if k.startswith("query_map:") and k.endswith(":fixture")]
        assert fixture_keys, (
            "the response cache key must carry the retrieval mode so a fixture "
            f"bundle cannot be served for a live request; observed keys: {keys}"
        )


# ---------------------------------------------------------------------------
# 5. static assets
# ---------------------------------------------------------------------------


def test_static_assets_are_served_with_their_own_content_type():
    with _Server() as server:
        status, headers, body = _get(server.port, "/static/lex_gate_switch.js")
        assert status == 200
        assert headers.get("Content-Type") == "application/javascript"
        assert body

        status, headers, body = _get(server.port, "/static/query.html")
        assert status == 200
        assert headers.get("Content-Type") == "text/html", (
            "the shipped page must be served as HTML; serving it as text/css "
            "would break the page in a browser"
        )
        assert b"<html" in body.lower()


def test_static_routes_cannot_escape_the_static_directory():
    with _Server() as server:
        status, _headers, _body = _get(server.port, "/static/../server.py")
        assert status == 404, "a traversal out of product/static must not be served"


if __name__ == "__main__":  # pragma: no cover - manual run
    with _Server() as server:
        print(json.dumps(_json("/api/health", server.port), indent=2))
