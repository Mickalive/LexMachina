"""One command serves a committed query_result_bundle as a clickable map.

The product's shortest offline vertical slice must not depend on retrieval, a
model, or a warm cache: ``query_app.py --bundle <path>`` loads a committed
bundle into the existing resumable-run path and the bare page redirects to
``/?run_id=<id>`` so the shipped UI restores it through code it already has.
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
APP = ROOT / "product" / "query_app.py"
BUNDLE = (ROOT / "results" / "product" / "offline_slice"
          / "CYCLE_42794322956" / "rent-default.bundle.json")
RUN_ID = "offline-demo"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(port: int, path: str, timeout: float = 5.0):
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401 - stdlib hook
        return None


def _wait_health(port: int, proc: subprocess.Popen, timeout: float = 30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise AssertionError(
                "query_app exited before answering /api/health:\n"
                + (proc.stdout.read() if proc.stdout else "")
            )
        try:
            status, _headers, body = _get(port, "/api/health")
            if status == 200:
                return json.loads(body)
        except Exception:
            time.sleep(0.1)
    raise AssertionError("query_app did not answer /api/health in 30s")


def test_preloaded_bundle_is_served_as_a_resumable_run():
    assert BUNDLE.is_file()
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-u", str(APP), "--port", str(port),
         "--bundle", str(BUNDLE), "--bundle-run-id", RUN_ID, "--quiet"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        health = _wait_health(port, proc)
        assert health["ok"] is True
        assert health["bundle_preloaded"] is True
        assert health["preloaded_run_id"] == RUN_ID
        assert health["fixture_mode"] is False

        status, _headers, body = _get(
            port, "/api/query/status?" + urllib.parse.urlencode({"run_id": RUN_ID})
        )
        assert status == 200
        run = json.loads(body)
        assert run["mode"] == "offline"
        assert run["counts"]["decisions"] == len(bundle["decisions"])
        assert run["counts"]["clusters"] == len(bundle["clusters"])

        status, _headers, body = _get(
            port, "/api/query/bundle?" + urllib.parse.urlencode({"run_id": RUN_ID})
        )
        assert status == 200
        served = json.loads(body)["bundle"]
        assert served["query"] == bundle["query"]
        assert len(served["decisions"]) == len(bundle["decisions"])
        assert served["answer"]["prose"]

        opener = urllib.request.build_opener(_NoRedirect)
        try:
            opener.open(f"http://127.0.0.1:{port}/", timeout=5)
            raise AssertionError("bare page did not redirect to the preloaded run")
        except urllib.error.HTTPError as exc:
            assert exc.code == 302
            assert exc.headers["Location"] == "/?run_id=" + RUN_ID

        status, _headers, body = _get(port, "/?run_id=" + RUN_ID)
        assert status == 200
        html = body.decode("utf-8")
        assert "<html" in html.lower()
        assert "run_id" in html or "query" in html.lower()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - failure path
            proc.kill()


def test_preloaded_run_is_not_evicted_by_later_queries(monkeypatch):
    import query_app

    monkeypatch.setattr(query_app, "RUNS", {})
    query_app._remember("bundle", 1, {}, "offline", run_id="pinned",
                        pinned=True)
    for i in range(query_app.MAX_STORED_RUNS + 3):
        query_app._remember("q", 1, {}, "fixture", run_id=f"r{i}")
    assert "pinned" in query_app.RUNS
    assert len(query_app.RUNS) <= query_app.MAX_STORED_RUNS + 1


def test_preload_rejects_an_invalid_bundle_before_serving():
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.json"
        bad.write_text('{"query": "x"}', encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(APP), "--port", "0",
             "--bundle", str(bad), "--bundle-run-id", "bad"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode != 0
        assert "invalid query_result_bundle" in (proc.stderr + proc.stdout)
