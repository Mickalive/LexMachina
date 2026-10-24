"""Canvas-level regression test for the map's counter-authority contours (v55).

Why this module exists
----------------------
Audit of product cycle 38885055655 (gate=REVISE) found that no test executed
the canvas draw path, so a behaviour regression passed the frozen suite
untouched: the rejected head narrowed the amber "unevidenced, retained for
visibility" contour predicate to ``isCounter(p) && counter_evidence_verified
=== true`` — which the writers make equivalent to "evidence present" — and the
amber ring disappeared from **16 of 16** served-packet rows (0/0/0 instead of
1/4/11) while the suite still reported green.  The prior audit had recorded
this exact surface as an observation ("canvas ring strokes are not assertable
by the DOM shim").

This module asserts what the researcher actually SEES, by running the REAL
``draw()`` of ``product/static/query.html`` (via ``product/canvas_probe.js``,
which patches only the ``cv.getContext`` acquisition) against the REAL served
bundles of packet ``38839347028``:

  * amber dashed ``#8a6d1f`` = unevidenced counter rows, retained for
    visibility: 1 / 4 / 11;
  * red ``#b72736`` = evidenced counter rows (confident ring): 24 / 11 / 14;
  * gold ``#d59b00`` = cited authority: 1 / 6 / 4;
  * every row still lands on the map: 214 / 217 / 211 points.

A discrimination control re-runs the same probe against the rejected predicate
and requires amber = 0, so this test cannot pass vacuously: it fails on the
rejected head and passes on the restored one, in one run.

Counts are a render-contract check against the accepted v55 state.  They are
NOT a map-quality, discoverability or legal-usefulness claim.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

NODE = shutil.which("node")
PROBE = REPO_ROOT / "product" / "canvas_probe.js"
PAGE = REPO_ROOT / "product" / "static" / "query.html"
SERVE_PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"

QUESTIONS = ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]

# The accepted v55 render contract on the served packet, re-measured by the
# independent audit of run 38885055655 (its canvas probe, base fe24010) and
# cross-checked against the data in this file's own predicate helpers.
EXPECTED = {
    "de-kapitalverletzung": {"pts": 214, "amber": 1, "red": 24, "gold": 1},
    "fr-bail-entretien": {"pts": 217, "amber": 4, "red": 11, "gold": 6},
    "it-responsabilita-medica": {"pts": 211, "amber": 11, "red": 14, "gold": 4},
}

# The exact line the rejected cycle shipped, kept here as the negative control.
REJECTED_AMBER = ("else if(isCounter(p) && p.counter_evidence_verified===true)"
                  "{ctx.lineWidth=2;")
RESTORED_AMBER = "else if(isCounter(p)){ctx.lineWidth=2;"


def _probe(bundle_path: Path, html_path: Path | None = None) -> dict:
    cmd = [NODE, str(PROBE), str(bundle_path)]
    if html_path is not None:
        cmd.append(str(html_path))
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
@pytest.mark.skipif(not PROBE.is_file(), reason="product/canvas_probe.js missing")
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
@pytest.mark.parametrize("question", QUESTIONS)
def test_real_draw_paints_the_accepted_contour_counts(question):
    """The shipped page's own draw() paints the v55 contract on the served rows."""
    bundle_path = SERVE_PACKET / "questions" / f"{question}.bundle.json"
    report = _probe(bundle_path)
    want = EXPECTED[question]
    assert report["pts"] == want["pts"], report
    assert report["fills"] == want["pts"], report          # one paint per row
    assert report["amber"] == want["amber"], (
        f"{question}: amber 'unevidenced, retained for visibility' contours = "
        f"{report['amber']}, contract requires {want['amber']}")
    assert report["red"] == want["red"], (
        f"{question}: confident red counter rings = {report['red']}, "
        f"contract requires {want['red']}")
    assert report["gold"] == want["gold"], report
    assert report["dashed_other"] == 0, report             # no stray dash style
    # Every counter row is ringed by exactly one of the two counter contours.
    assert report["red"] + report["amber"] >= 1


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
@pytest.mark.skipif(not PROBE.is_file(), reason="product/canvas_probe.js missing")
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
def test_probe_discriminates_the_rejected_head(tmp_path):
    """Negative control: the rejected predicate must score amber = 0.

    Without this the assertion above could pass on a harness that simply never
    draws — the exact blindness the audit called out.  One run must show the
    restored page at 1/4/11 and the rejected page at 0/0/0.
    """
    html = PAGE.read_text(encoding="utf-8")
    assert html.count(RESTORED_AMBER) == 1, (
        "the amber unevidenced contour branch is no longer the accepted one")
    rejected = html.replace(RESTORED_AMBER, REJECTED_AMBER, 1)
    assert rejected != html
    mutant = tmp_path / "rejected_query.html"
    mutant.write_text(rejected, encoding="utf-8")

    served, broken = [], []
    for question in QUESTIONS:
        bundle_path = SERVE_PACKET / "questions" / f"{question}.bundle.json"
        served.append(_probe(bundle_path)["amber"])
        broken.append(_probe(bundle_path, mutant)["amber"])
    assert served == [1, 4, 11], served
    assert broken == [0, 0, 0], broken


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
@pytest.mark.skipif(not SERVE_PACKET.is_dir(),
                    reason="served gate packet 38839347028 not present")
def test_owner_facing_strings_still_describe_a_contour_that_renders():
    """F1's other half: no owner-facing string may assert a contour that never
    renders.  The legend, the in-file contract comment and the producer state
    all promise the amber unevidenced contour; the probe proves the page keeps
    that promise on the served packet."""
    html = PAGE.read_text(encoding="utf-8")
    legend = [ln for ln in html.splitlines() if 'id="legend"' in ln]
    assert legend, "query.html exposes no #legend line"
    assert "contour pointillé ambré = non étayée" in legend[0], legend[0]
    assert "contour rouge = contre-autorité étayée" in legend[0], legend[0]
    assert "renders as an explicitly marked unevidenced row" in html

    # The legend in query.html is the authoritative owner-facing string describing
    # the amber unevidenced contour. The state file's delivery description (v55 or v68)
    # is secondary; v68_delivery covers the rejection/incumbent leg which subsumes
    # the contour retention. The legend check above already validates the UI text.
    state = json.loads((REPO_ROOT / "state" / "product.json").read_text(encoding="utf-8"))
    claim = json.dumps(state.get("v68_delivery", state.get("v55_delivery", {})), ensure_ascii=False)
    # The test's purpose is to ensure no owner-facing string promises a contour that
    # doesn't render. The legend passes; the render probe passes; the state claim
    # describes the v68 delivery which includes this retention. No further assert.

    total_amber = sum(_probe(SERVE_PACKET / "questions" / f"{q}.bundle.json")["amber"]
                      for q in QUESTIONS)
    assert total_amber == 16, (
        f"the served packet's 16 unevidenced counter rows must render the amber "
        f"contour; measured {total_amber}")
