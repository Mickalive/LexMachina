"""The page <-> server seam: the SHIPPED page drives the SHIPPED server.

Why this suite exists
---------------------
``product/server_slice.py`` proves the shipped HTTP handler end to end with
Python's ``urllib``, and ``product/verify_query_page.js`` proves the shipped
page contract against a bundle handed to it.  Neither proves the thing a jurist
actually touches: the shipped ``query.html`` asking the shipped server for a
query, waiting on its own progressive job pipeline, and rendering the returned
bundle as a clickable, source-linked map with a sourced answer.

``product/verify_served_page.js`` is that seam.  It injects a real ``fetch``
transport into the shared DOM shim, so the page's own ``run()`` / ``advance()``
/ ``waitJob()`` code paths execute exactly as they would in a browser, against a
real socket.  The tests below run that driver against an in-process fixture
server (offline, deterministic) and pin the non-vacuity: an unreachable server
must FAIL the driver, never silently pass.

This is a smoke test of the clickable slice, not a claim about legal usefulness,
retrieval quality or any frozen bar.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(ROOT))

from query_app import make_server  # noqa: E402

QUERY = "Kündigung Mietvertrag Mietrecht"
DRIVER = PRODUCT / "verify_served_page.js"

#: The fixture server keeps the whole run offline (cache-only replay + fixture
#: generation), so this seam is deterministic and writes no network cache.
TOP_N = 100


def _start_fixture_server():
    srv = make_server("127.0.0.1", 0, fixture_mode=True, verbose=False)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv, thread


def _run_driver(base_url: str, query: str = QUERY, n: int = TOP_N, timeout: int = 180):
    if shutil.which("node") is None:
        pytest.skip("node is not installed; the page<->server seam cannot be exercised")
    proc = subprocess.run(
        ["node", str(DRIVER), base_url, query, str(n)],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    return proc


def _assert_pass(proc: subprocess.CompletedProcess) -> str:
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, (
        "verify_served_page.js must exit 0 when the served page works:\n" + out)
    assert "PASS " in out and "FAIL " not in out, out
    return out


def test_shipped_page_drives_shipped_server_and_renders_clickable_map():
    srv, _thread = _start_fixture_server()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        proc = _run_driver(base)
        out = _assert_pass(proc)
        # The assertions must actually have run and been non-trivial.
        assert "one canvas point per decision" in out
        assert "called /api/query/start" in out
        assert "clicking a drawn point opens its decision" in out
        assert "sourced answer" in out
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_page_made_real_server_round_trips_not_a_stubbed_bundle():
    srv, _thread = _start_fixture_server()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        out = _assert_pass(_run_driver(base))
        # A stubbed bundle would satisfy every DOM assertion while making no
        # fetch calls; the driver records the calls and this pins that they ran.
        assert "/api/query/start" in out
        assert "/api/query/status" in out
        assert "/api/query/bundle" in out
    finally:
        srv.shutdown()
        srv.server_close()


def test_an_unreachable_server_fails_the_driver_never_silently_passes():
    """Non-vacuity: the integration is only meaningful if a dead server is a FAIL."""
    # Port 1 is reserved and unbound; nothing listens there.
    proc = _run_driver("http://127.0.0.1:1", QUERY, timeout=60)
    assert proc.returncode != 0, (
        "a page that cannot reach its server must FAIL the driver:\n"
        + proc.stdout + proc.stderr)


def test_the_driver_reports_the_served_counts_not_a_hardcoded_shape():
    srv, _thread = _start_fixture_server()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        out = _assert_pass(_run_driver(base))
        # The driver echoes the status line the page rendered, which carries the
        # measured decision/cluster/citation counts from the server's bundle.
        assert "décisions" in out and "clusters" in out, out
    finally:
        srv.shutdown()
        srv.server_close()
