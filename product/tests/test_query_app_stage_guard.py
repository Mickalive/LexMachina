"""A late map expansion must never erase the sourced answer.

Defect measured on the shipped ``product/query_app.py`` (2026-11-13): the run
record is written by two jobs on the same thread pool.  *expand* and *enrich*
both call ``_set_bundle``, so if a researcher (or a retrying client) asks for
another expansion after enrichment has completed, the late ``map_expanded``
bundle overwrites the ``complete`` bundle.  ``/api/query/status`` then reports
``jobs.enrich.status=done`` and ``answer.status=ready`` while
``/api/query/bundle`` returns ``answer.status=pending`` with no cited
decisions -- the page reloads into a map whose answer silently disappeared.

The fix is a monotonic stage guard on the run record: ``first_page`` /
``map_ready`` < ``map_expanded`` < ``complete``; a lower stage may never
replace a higher one.

These tests are offline and deterministic: frozen OpenCaseLaw fixture,
fixture generation, no outbound network.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

QUERY = "Kündigung Mietvertrag Mietrecht"
APP = PRODUCT / "query_app.py"


# ---------------------------------------------------------------------------
# 1. the state-machine invariant, without a thread race
# ---------------------------------------------------------------------------


def test_a_late_lower_stage_bundle_cannot_replace_an_enriched_bundle():
    from query import expand_query_bundle, enrich_query_bundle, run_query_first_page
    import query_app

    first = run_query_first_page(QUERY, top_n=100, retrieval_mode="fixture")
    assert first["provenance"]["phase"] == "map_ready"
    run_id = query_app._remember(QUERY, 100, first, "fixture")

    final = enrich_query_bundle(
        first, retrieval_mode="fixture", fixture_generation=True)
    assert final["provenance"]["phase"] == "complete"
    assert final["answer"]["status"] == "ready"
    query_app._set_bundle(run_id, final)

    # The exact losing write: an expansion computed from the pre-enrich map
    # finishing after generation.  It must be ignored, not stored.
    late = expand_query_bundle(first, retrieval_mode="fixture", top_n=100)
    assert late["provenance"]["phase"] == "map_expanded"
    query_app._set_bundle(run_id, late)

    current = query_app._get(run_id)["bundle"]
    assert current["provenance"]["phase"] == "complete"
    assert current["answer"]["status"] == "ready"
    assert current["answer"]["cited_decision_ids"]


def test_stage_rank_ordering_is_explicit():
    import query_app

    ranks = [
        query_app._bundle_stage({"provenance": {"phase": "first_page"}}),
        query_app._bundle_stage({"provenance": {"phase": "map_ready"}}),
        query_app._bundle_stage({"provenance": {"phase": "map_expanded"}}),
        query_app._bundle_stage({"provenance": {"phase": "complete"}}),
    ]
    assert ranks[0] == ranks[1] < ranks[2] < ranks[3]
    assert query_app._bundle_stage({}) == 0


# ---------------------------------------------------------------------------
# 2. the shipped server: re-expanding after an answer keeps the answer
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(port: int, path: str, timeout: float = 120.0) -> dict:
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        assert resp.status == 200, f"{path} -> HTTP {resp.status}"
        return json.loads(resp.read().decode("utf-8"))


class _Server:
    def __init__(self) -> None:
        self.port = _free_port()
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> "_Server":
        self.proc = subprocess.Popen(
            [sys.executable, str(APP), "--fixture", "--port", str(self.port)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                out = self.proc.stdout.read() if self.proc.stdout else ""
                raise AssertionError(f"query_app exited early:\n{out}")
            try:
                _get(self.port, "/api/health", timeout=5)
                return self
            except Exception:
                time.sleep(0.2)
        raise AssertionError("query_app did not answer /api/health in 60s")

    def __exit__(self, *_exc) -> None:
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover
                self.proc.kill()


def _wait_job(port: int, run_id: str, name: str, limit: float = 120.0) -> dict:
    deadline = time.time() + limit
    while time.time() < deadline:
        status = _get(port, f"/api/query/status?run_id={run_id}")
        job = (status.get("jobs") or {}).get(name) or {}
        if job.get("status") in {"done", "error"}:
            return job
        time.sleep(0.2)
    raise AssertionError(f"{name} job did not finish in {limit}s")


def test_reexpanding_after_enrichment_does_not_drop_the_answer():
    with _Server() as server:
        started = _get(
            server.port,
            "/api/query/start?q=" + urllib.parse.quote(QUERY) + "&n=100",
        )
        run_id = started["run_id"]
        _wait_job(server.port, run_id, "expand")

        enriched = _get(
            server.port,
            f"/api/query/enrich?run_id={run_id}&wait_s=120",
        )
        assert enriched["job"]["status"] == "done", enriched
        assert enriched["bundle"]["answer"]["status"] == "ready"

        # Public API allows this call.  It used to erase the answer.
        _get(server.port, f"/api/query/expand?run_id={run_id}")
        _wait_job(server.port, run_id, "expand")

        payload = _get(server.port, f"/api/query/bundle?run_id={run_id}")
        bundle = payload["bundle"]
        assert bundle["provenance"]["phase"] == "complete"
        assert bundle["answer"]["status"] == "ready"
        assert bundle["answer"]["cited_decision_ids"]
        status = payload["status"]
        assert status["jobs"]["enrich"]["status"] == "done"
        assert status["counts"]["decisions"] == len(bundle["decisions"])
