"""Frozen-question quick-pick: SELECT a real Swiss-law fixture, get the map.

Why this exists
---------------
``product/fixture_question_replay_probe.py`` (cycle 42738229187) proves the four
frozen reality-check questions replay offline to renderable maps, and
``product/verify_served_page.js`` proves the shipped page drives the shipped
server for a query it is *given*.  Neither let a jurist *select* a frozen
question: the sidebar still demanded retyping a 150-character French sentence.

This suite pins the selection seam on the shipped ``product/static/query.html``:

* ``FROZEN_QUICKPICK`` in the page is byte-exact against
  ``product/reality_check.py`` ``LEGS`` for all four slugs (so the page can
  never drift from the frozen legs - the map the jurist clicks is the leg the
  reality check measures);
* one shipped button exists per slug and its click fills ``#q`` and calls the
  normal ``run()`` pipeline - no second pipeline, no hidden retrieval path;
* ``product/verify_quickpick.js`` drives that click through a real fixture
  socket and ends on a drawn, source-linked, clickable map;
* non-vacuity: the same driver against an unreachable server must FAIL.

No frozen gate, rubric, threshold or serve verdict is read, edited or
re-scored.  No network, no paid inference, no 174k work.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from reality_check import LEGS  # noqa: E402

HTML = PRODUCT / "static" / "query.html"
DRIVER = PRODUCT / "verify_quickpick.js"
SLUGS = ("rent-default", "petty-theft-dismissal",
         "corporate-criminal-liability", "business-judgment-rule")


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _quickpick_map() -> dict[str, str]:
    m = re.search(r"const FROZEN_QUICKPICK=(\{.*?\});", _html(), re.S)
    assert m, "query.html must define FROZEN_QUICKPICK"
    return json.loads(m.group(1))


def test_frozen_quickpick_is_byte_exact_with_reality_check_legs():
    """The page's four questions ARE the frozen legs, byte for byte."""
    qp = _quickpick_map()
    assert set(qp) == set(LEGS) == set(SLUGS), (sorted(qp), sorted(LEGS))
    for slug in SLUGS:
        assert qp[slug] == LEGS[slug], (
            f"FROZEN_QUICKPICK[{slug!r}] drifted from reality_check.LEGS")


def test_every_frozen_leg_has_a_shipped_quick_pick_button():
    html = _html()
    for slug in SLUGS:
        assert f'id="qp-{slug}"' in html, f"missing quick-pick button for {slug}"
        assert 'id="quickpick"' in html, "quick-pick container missing"


def test_quickpick_wiring_fills_the_box_and_runs_the_normal_pipeline():
    """One pipeline only: the click sets #q and calls the SAME run()."""
    html = _html()
    assert 'getElementById("qp-"+slug)' in html
    assert 'document.getElementById("q").value=FROZEN_QUICKPICK[slug]' in html
    assert re.search(r'addEventListener\("click",\s*function\(\)\{[^}]*run\(\);',
                     html, re.S), "click handler must call run()"


def _start_fixture_server():
    from query_app import make_server
    srv = make_server("127.0.0.1", 0, fixture_mode=True, verbose=False)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv, thread


def _run_driver(base_url: str, slug: str, timeout: int = 180):
    if shutil.which("node") is None:
        pytest.skip("node is not installed; the quick-pick seam cannot be exercised")
    proc = subprocess.run(
        ["node", str(DRIVER), base_url, slug, LEGS[slug], "150"],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    return proc


def _assert_pass(proc: subprocess.CompletedProcess) -> str:
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, (
        "verify_quickpick.js must exit 0 when the shipped quick-pick works:\n"
        + out)
    assert "PASS " in out and "FAIL " not in out, out
    return out


@pytest.mark.parametrize("slug", SLUGS)
def test_quickpick_click_renders_a_clickable_source_linked_map(slug):
    """Click a shipped button for a frozen leg -> drawn, source-linked map."""
    srv, _thread = _start_fixture_server()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        out = _assert_pass(_run_driver(base, slug))
        assert "clicking the quick-pick fills the search box" in out
        assert "called /api/query/start with the frozen question" in out
        assert "one canvas point per decision" in out
        assert "source-linked panel" in out
    finally:
        srv.shutdown()
        srv.server_close()


def test_quickpick_driver_fails_against_an_unreachable_server():
    """Non-vacuity: a dead server must FAIL the driver, never silently pass."""
    proc = _run_driver("http://127.0.0.1:1", "rent-default", timeout=60)
    assert proc.returncode != 0, (
        "a page that cannot reach its server must FAIL the driver:\n"
        + proc.stdout + proc.stderr)


def test_the_page_never_auto_runs_without_a_question():
    """The quick-pick is the selection path; boot alone must not start a run.

    The driver asserts this over a real socket (zero /api/query/start calls
    before the click); here we pin the deep-link contract itself so a future
    edit that auto-runs from the default box is caught without a server.
    """
    html = _html()
    # boot() only runs when ?q= or ?run_id= is present; the default box value
    # is never consumed at boot.
    assert 'if(q){await run();return}' in html
    assert 'await resumeLastRun();' in html
